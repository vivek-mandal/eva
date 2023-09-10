# coding=utf-8
# Copyright 2018-2023 EvaDB
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
import unittest

import mock
import pytest
from mock import ANY, MagicMock

from evadb.catalog.catalog_manager import CatalogManager
from evadb.catalog.catalog_type import ColumnType, TableType
from evadb.catalog.catalog_utils import get_video_table_column_definitions
from evadb.catalog.models.column_catalog import ColumnCatalogEntry
from evadb.catalog.models.function_catalog import FunctionCatalogEntry
from evadb.parser.table_ref import TableInfo
from evadb.parser.types import FileFormatType


@pytest.mark.notparallel
class CatalogManagerTests(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def setUpClass(cls) -> None:
        cls.mocks = [
            mock.patch("evadb.catalog.catalog_manager.SQLConfig"),
            mock.patch("evadb.catalog.catalog_manager.init_db"),
        ]
        for single_mock in cls.mocks:
            single_mock.start()
            cls.addClassCleanup(single_mock.stop)

    @mock.patch("evadb.catalog.catalog_manager.init_db")
    def test_catalog_bootstrap(self, mocked_db):
        x = CatalogManager(MagicMock(), MagicMock())
        x._bootstrap_catalog()
        mocked_db.assert_called()

    @mock.patch(
        "evadb.catalog.catalog_manager.CatalogManager.create_and_insert_table_catalog_entry"
    )
    def test_create_multimedia_table_catalog_entry(self, mock):
        x = CatalogManager(MagicMock(), MagicMock())
        name = "myvideo"
        x.create_and_insert_multimedia_table_catalog_entry(
            name=name, format_type=FileFormatType.VIDEO
        )

        columns = get_video_table_column_definitions()

        mock.assert_called_once_with(
            TableInfo(name),
            columns,
            table_type=TableType.VIDEO_DATA,
        )

    @mock.patch("evadb.catalog.catalog_manager.init_db")
    @mock.patch("evadb.catalog.catalog_manager.TableCatalogService")
    def test_insert_table_catalog_entry_should_create_table_and_columns(
        self, ds_mock, initdb_mock
    ):
        catalog = CatalogManager(MagicMock(), MagicMock())
        file_url = "file1"
        table_name = "name"

        columns = [(ColumnCatalogEntry("c1", ColumnType.INTEGER))]
        catalog.insert_table_catalog_entry(table_name, file_url, columns)
        ds_mock.return_value.insert_entry.assert_called_with(
            table_name,
            file_url,
            identifier_column="id",
            table_type=TableType.VIDEO_DATA,
            column_list=[ANY] + columns,
        )

    @mock.patch("evadb.catalog.catalog_manager.init_db")
    @mock.patch("evadb.catalog.catalog_manager.TableCatalogService")
    def test_get_table_catalog_entry_when_table_exists(self, ds_mock, initdb_mock):
        catalog = CatalogManager(MagicMock(), MagicMock())
        table_name = "name"
        database_name = "database"
        row_id = 1
        table_obj = MagicMock(row_id=row_id)
        ds_mock.return_value.get_entry_by_name.return_value = table_obj

        actual = catalog.get_table_catalog_entry(
            table_name,
            database_name,
        )
        ds_mock.return_value.get_entry_by_name.assert_called_with(
            database_name, table_name
        )
        self.assertEqual(actual.row_id, row_id)

    @mock.patch("evadb.catalog.catalog_manager.init_db")
    @mock.patch("evadb.catalog.catalog_manager.TableCatalogService")
    @mock.patch("evadb.catalog.catalog_manager.ColumnCatalogService")
    def test_get_table_catalog_entry_when_table_doesnot_exists(
        self, dcs_mock, ds_mock, initdb_mock
    ):
        catalog = CatalogManager(MagicMock(), MagicMock())
        table_name = "name"

        database_name = "database"
        table_obj = None

        ds_mock.return_value.get_entry_by_name.return_value = table_obj

        actual = catalog.get_table_catalog_entry(table_name, database_name)
        ds_mock.return_value.get_entry_by_name.assert_called_with(
            database_name, table_name
        )
        dcs_mock.return_value.filter_entries_by_table_id.assert_not_called()
        self.assertEqual(actual, table_obj)

    @mock.patch("evadb.catalog.catalog_manager.FunctionCatalogService")
    @mock.patch("evadb.catalog.catalog_manager.FunctionIOCatalogService")
    @mock.patch("evadb.catalog.catalog_manager.FunctionMetadataCatalogService")
    @mock.patch("evadb.catalog.catalog_manager.get_file_checksum")
    def test_insert_function(
        self, checksum_mock, functionmetadata_mock, functionio_mock, function_mock
    ):
        catalog = CatalogManager(MagicMock(), MagicMock())
        function_io_list = [MagicMock()]
        function_metadata_list = [MagicMock()]
        actual = catalog.insert_function_catalog_entry(
            "function",
            "sample.py",
            "classification",
            function_io_list,
            function_metadata_list,
        )
        functionio_mock.return_value.insert_entries.assert_called_with(function_io_list)
        functionmetadata_mock.return_value.insert_entries.assert_called_with(
            function_metadata_list
        )
        function_mock.return_value.insert_entry.assert_called_with(
            "function", "sample.py", "classification", checksum_mock.return_value
        )
        checksum_mock.assert_called_with("sample.py")
        self.assertEqual(actual, function_mock.return_value.insert_entry.return_value)

    @mock.patch("evadb.catalog.catalog_manager.FunctionCatalogService")
    def test_get_function_catalog_entry_by_name(self, function_mock):
        catalog = CatalogManager(MagicMock(), MagicMock())
        actual = catalog.get_function_catalog_entry_by_name("name")
        function_mock.return_value.get_entry_by_name.assert_called_with("name")
        self.assertEqual(
            actual, function_mock.return_value.get_entry_by_name.return_value
        )

    @mock.patch("evadb.catalog.catalog_manager.FunctionCatalogService")
    def test_delete_function(self, function_mock):
        CatalogManager(MagicMock(), MagicMock()).delete_function_catalog_entry_by_name(
            "name"
        )
        function_mock.return_value.delete_entry_by_name.assert_called_with("name")

    @mock.patch("evadb.catalog.catalog_manager.FunctionIOCatalogService")
    def test_get_function_outputs(self, function_mock):
        mock_func = function_mock.return_value.get_output_entries_by_function_id
        function_obj = MagicMock(spec=FunctionCatalogEntry)
        CatalogManager(MagicMock(), MagicMock()).get_function_io_catalog_output_entries(
            function_obj
        )
        mock_func.assert_called_once_with(function_obj.row_id)

    @mock.patch("evadb.catalog.catalog_manager.FunctionIOCatalogService")
    def test_get_function_inputs(self, function_mock):
        mock_func = function_mock.return_value.get_input_entries_by_function_id
        function_obj = MagicMock(spec=FunctionCatalogEntry)
        CatalogManager(MagicMock(), MagicMock()).get_function_io_catalog_input_entries(
            function_obj
        )
        mock_func.assert_called_once_with(function_obj.row_id)
