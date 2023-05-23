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
from typing import Iterator, List

import numpy as np
import pandas as pd
from sqlalchemy import Table, inspect
from sqlalchemy.sql.expression import ColumnElement

from eva.catalog.catalog_type import ColumnType
from eva.catalog.models.base_model import BaseModel
from eva.catalog.models.column_catalog import ColumnCatalogEntry
from eva.catalog.models.table_catalog import TableCatalogEntry
from eva.catalog.schema_utils import SchemaUtils
from eva.catalog.sql_config import IDENTIFIER_COLUMN, SQLConfig
from eva.models.storage.batch import Batch
from eva.parser.table_ref import TableInfo
from eva.storage.abstract_storage_engine import AbstractStorageEngine
from eva.utils.generic_utils import PickleSerializer, get_size
from eva.utils.logging_manager import logger

# Leveraging Dynamic schema in SQLAlchemy
# https://sparrigan.github.io/sql/sqla/2016/01/03/dynamic-tables.html


class SQLStorageEngine(AbstractStorageEngine):
    def __init__(self):
        """
        Grab the existing sql session
        """
        self._sql_session = SQLConfig().session
        self._sql_engine = SQLConfig().engine
        self._serializer = PickleSerializer

    def _dict_to_sql_row(self, dict_row: dict, columns: List[ColumnCatalogEntry]):
        # Serialize numpy data
        for col in columns:
            if col.type == ColumnType.NDARRAY:
                dict_row[col.name] = self._serializer.serialize(dict_row[col.name])
            elif isinstance(dict_row[col.name], (np.generic,)):
                # Sqlalchemy does not consume numpy generic data types
                # convert numpy datatype to python generic datatype using tolist()
                # eg. np.int64 -> int
                # https://stackoverflow.com/a/53067954
                dict_row[col.name] = dict_row[col.name].tolist()
        return dict_row

    def _sql_row_to_dict(self, sql_row: tuple, columns: List[ColumnCatalogEntry]):
        # Deserialize numpy data
        dict_row = {}
        for idx, col in enumerate(columns):
            if col.type == ColumnType.NDARRAY:
                dict_row[col.name] = self._serializer.deserialize(sql_row[idx])
            else:
                dict_row[col.name] = sql_row[idx]
        return dict_row

    def _try_loading_table_via_reflection(self, table_name: str):
        metadata_obj = BaseModel.metadata
        if table_name in metadata_obj.tables:
            return metadata_obj.tables[table_name]
        # reflection
        insp = inspect(self._sql_engine)
        if insp.has_table(table_name):
            table = Table(table_name, metadata_obj)
            insp.reflect_table(table, None)
            return table
        else:
            err_msg = f"No table found with name {table_name}"
            logger.exception(err_msg)
            raise Exception(err_msg)

    def create(self, table: TableCatalogEntry, **kwargs):
        """
        Create an empty table in sql.
        It dynamically constructs schema in sqlaclchemy
        to create the table
        """
        attr_dict = {"__tablename__": table.name}

        # During table creation, assume row_id is automatically handled by
        # the sqlalchemy engine.
        table_columns = [col for col in table.columns if col.name != IDENTIFIER_COLUMN]
        sqlalchemy_schema = SchemaUtils.xform_to_sqlalchemy_schema(table_columns)

        attr_dict.update(sqlalchemy_schema)
        # dynamic schema generation
        # https://sparrigan.github.io/sql/sqla/2016/01/03/dynamic-tables.html
        new_table = type("__placeholder_class_name__", (BaseModel,), attr_dict)()
        table = BaseModel.metadata.tables[table.name]
        if not table.exists():
            BaseModel.metadata.tables[table.name].create(self._sql_engine)
        self._sql_session.commit()
        return new_table

    def drop(self, table: TableCatalogEntry):
        try:
            table_to_remove = self._try_loading_table_via_reflection(table.name)
            table_to_remove.drop()
            # In-memory metadata does not automatically sync with the database
            # therefore manually removing the table from the in-memory metadata
            # https://github.com/sqlalchemy/sqlalchemy/issues/5112
            BaseModel.metadata.remove(table_to_remove)
            self._sql_session.commit()
        except Exception as e:
            err_msg = f"Failed to drop the table {table.name} with Exception {str(e)}"
            logger.exception(err_msg)
            raise Exception(err_msg)

    def write(self, table: TableCatalogEntry, rows: Batch):
        """
        Write rows into the sql table.

        Arguments:
            table: table metadata object to write into
            rows : batch to be persisted in the storage.
        """
        try:
            table_to_update = self._try_loading_table_via_reflection(table.name)
            columns = rows.frames.keys()
            data = []

            # During table writes, assume row_id is automatically handled by
            # the sqlalchemy engine. Another assumption we make here is the
            # updated data need not to take care of row_id.
            table_columns = [
                col for col in table.columns if col.name != IDENTIFIER_COLUMN
            ]

            # Todo: validate the data type before inserting into the table
            for record in rows.frames.values:
                row_data = {col: record[idx] for idx, col in enumerate(columns)}
                data.append(self._dict_to_sql_row(row_data, table_columns))
            self._sql_engine.execute(table_to_update.insert(), data)
            self._sql_session.commit()
        except Exception as e:
            err_msg = f"Failed to update the table {table.name} with exception {str(e)}"
            logger.exception(err_msg)
            raise Exception(err_msg)

    def read(
        self, table: TableCatalogEntry, batch_mem_size: int = 30000000
    ) -> Iterator[Batch]:
        """
        Reads the table and return a batch iterator for the
        tuples.

        Argument:
            table: table metadata object of the table to read
            batch_mem_size (int): memory size of the batch read from storage
        Return:
            Iterator of Batch read.
        """
        try:
            table_to_read = self._try_loading_table_via_reflection(table.name)
            result = self._sql_engine.execute(table_to_read.select())
            data_batch = []
            row_size = None
            for row in result:
                # Todo: Verify the order of columns in row matches the table.columns
                # For table read, we provide row_id so that user can also retrieve
                # row_id from the table.
                data_batch.append(self._sql_row_to_dict(row, table.columns))
                if row_size is None:
                    row_size = 0
                    row_size = get_size(data_batch)
                if len(data_batch) * row_size >= batch_mem_size:
                    yield Batch(pd.DataFrame(data_batch))
                    data_batch = []
            if data_batch:
                yield Batch(pd.DataFrame(data_batch))

        except Exception as e:
            err_msg = f"Failed to read the table {table.name} with exception {str(e)}"
            logger.exception(err_msg)
            raise Exception(err_msg)

    def delete(
        self, table: TableCatalogEntry, sqlalchemy_filter_clause: ColumnElement[bool]
    ):
        """Delete tuples from the table where rows satisfy the where_clause.
        The current implementation only handles equality predicates.

        Argument:
            table: table metadata object of the table
            where_clause: clause used to find the tuples to remove.
        """
        try:
            table_to_delete_from = self._try_loading_table_via_reflection(table.name)
            d = table_to_delete_from.delete().where(sqlalchemy_filter_clause)
            self._sql_engine.execute(d)
            self._sql_session.commit()
        except Exception as e:
            err_msg = (
                f"Failed to delete from the table {table.name} with exception {str(e)}"
            )
            logger.exception(err_msg)
            raise Exception(err_msg)

    def rename(self, old_table: TableCatalogEntry, new_name: TableInfo):
        raise Exception("Rename not supported for structured data table")
