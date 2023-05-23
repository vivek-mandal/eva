# coding=utf-8
# Copyright 2018-2022 EVA
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from __future__ import annotations

import re
from typing import TYPE_CHECKING, List

from eva.catalog.catalog_type import TableType
from eva.catalog.catalog_utils import (
    get_video_table_column_definitions,
    is_string_col,
    is_video_table,
)
from eva.expression.function_expression import FunctionExpression
from eva.parser.alias import Alias

if TYPE_CHECKING:
    from eva.binder.statement_binder_context import StatementBinderContext

from eva.catalog.catalog_manager import CatalogManager
from eva.catalog.models.table_catalog import TableCatalogEntry
from eva.expression.tuple_value_expression import TupleValueExpression
from eva.parser.table_ref import TableInfo, TableRef
from eva.utils.logging_manager import logger


class BinderError(Exception):
    pass


def bind_table_info(table_info: TableInfo) -> TableCatalogEntry:
    """
    Uses catalog to bind the table information .

    Arguments:
         table_info (TableInfo): table information obtained from SQL query

    Returns:
        TableCatalogEntry  -  corresponding table catalog entry for the input table info
    """
    catalog = CatalogManager()
    obj = catalog.get_table_catalog_entry(
        table_info.table_name,
        table_info.database_name,
    )

    # Users should not be allowed to directly access or modify the SYSTEM tables, as
    # doing so can lead to the corruption of other tables. These tables include
    # metadata tables associated with unstructured data, such as the list of video
    # files in the video table. Protecting these tables is crucial in order to maintain
    # the integrity of the system.
    if obj and obj.table_type == TableType.SYSTEM_STRUCTURED_DATA:
        err_msg = (
            "The query attempted to access or modify the internal table"
            f"{table_info.table_name} of the system, but permission was denied."
        )
        logger.error(err_msg)
        raise BinderError(err_msg)

    if obj:
        table_info.table_obj = obj
    else:
        error = "{} does not exist. Create the table using" " CREATE TABLE.".format(
            table_info.table_name
        )
        logger.error(error)
        raise BinderError(error)


def extend_star(
    binder_context: StatementBinderContext,
) -> List[TupleValueExpression]:
    col_objs = binder_context._get_all_alias_and_col_name()

    target_list = list(
        [
            TupleValueExpression(col_name=col_name, table_alias=alias)
            for alias, col_name in col_objs
        ]
    )
    return target_list


def check_groupby_pattern(groupby_string: str) -> None:
    # match the pattern of group by clause (e.g., 16f or 8s)
    pattern = re.search(r"^\d+[fs]$", groupby_string)
    # if valid pattern
    if not pattern:
        err_msg = "Incorrect GROUP BY pattern: {}".format(groupby_string)
        raise BinderError(err_msg)
    match_string = pattern.group(0)
    if not match_string[-1] == "f":
        err_msg = "Only grouping by frames (f) is supported"
        raise BinderError(err_msg)
    # TODO ACTION condition on segment length?


def check_table_object_is_video(table_ref: TableRef) -> None:
    if not is_video_table(table_ref.table.table_obj):
        err_msg = "GROUP BY only supported for video tables"
        raise BinderError(err_msg)


def check_column_name_is_string(col_ref) -> None:
    if not is_string_col(col_ref.col_object):
        err_msg = "LIKE only supported for string columns"
        raise BinderError(err_msg)


def resolve_alias_table_value_expression(node: FunctionExpression):
    default_alias_name = node.name.lower()
    default_output_col_aliases = [str(obj.name.lower()) for obj in node.output_objs]
    if not node.alias:
        node.alias = Alias(default_alias_name, default_output_col_aliases)
    else:
        if not len(node.alias.col_names):
            node.alias = Alias(node.alias.alias_name, default_output_col_aliases)
        else:
            output_aliases = [
                str(col_name.lower()) for col_name in node.alias.col_names
            ]
            node.alias = Alias(node.alias.alias_name, output_aliases)

    assert len(node.alias.col_names) == len(
        node.output_objs
    ), f"""Expected {len(node.output_objs)} output columns for {node.alias.alias_name}, got {len(node.alias.col_names)}."""


def handle_bind_extract_object_function(
    node: FunctionExpression, binder_context: StatementBinderContext
):
    """Handles the binding of extract_object function.
        1. Bind the source video data
        2. Create and bind the detector function expression using the provided name.
        3. Create and bind the tracker function expression.
            Its inputs are id, data, output of detector.
        4. Bind the EXTRACT_OBJECT function expression and append the new children.
        5. Handle the alias and populate the outputs of the EXTRACT_OBJECT function

    Args:
        node (FunctionExpression): The function expression representing the extract object operation.
        binder_context (StatementBinderContext): The context object used to bind expressions in the statement.

    Raises:
        AssertionError: If the number of children in the `node` is not equal to 3.
    """
    assert (
        len(node.children) == 3
    ), f"Invalid arguments provided to {node}. Example correct usage, (data, Detector, Tracker)"

    # 1. Bind the source video
    video_data = node.children[0]
    binder_context.bind(video_data)

    # 2. Construct the detector
    # convert detector to FunctionExpression before binding
    # eg. YoloV5 -> YoloV5(data)
    detector = FunctionExpression(None, node.children[1].col_name)
    detector.append_child(video_data.copy())
    binder_context.bind(detector)

    # 3. Construct the tracker
    # convert tracker to FunctionExpression before binding
    # eg. ByteTracker -> ByteTracker(id, data, labels, bboxes, scores)
    tracker = FunctionExpression(None, node.children[2].col_name)
    # create the video id expression
    columns = get_video_table_column_definitions()
    tracker.append_child(
        TupleValueExpression(
            col_name=columns[1].name, table_alias=video_data.table_alias
        )
    )
    tracker.append_child(video_data.copy())
    binder_context.bind(tracker)
    # append the bound output of detector
    for obj in detector.output_objs:
        col_alias = "{}.{}".format(obj.udf_name.lower(), obj.name.lower())
        child = TupleValueExpression(
            obj.name,
            table_alias=obj.udf_name.lower(),
            col_object=obj,
            col_alias=col_alias,
        )
        tracker.append_child(child)

    # 4. Bind the EXTRACT_OBJECT expression and append the new children.
    node.children = []
    node.children = [video_data, detector, tracker]

    # 5. assign the outputs of tracker to the output of extract_object
    node.output_objs = tracker.output_objs
    node.projection_columns = [obj.name.lower() for obj in node.output_objs]

    # 5. resolve alias based on the what user provided
    # we assign the alias to tracker as it governs the output of the extract object
    resolve_alias_table_value_expression(node)
    tracker.alias = node.alias
