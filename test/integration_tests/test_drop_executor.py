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
import unittest
from pathlib import Path
from test.util import create_sample_video, file_remove

import pytest

from eva.catalog.catalog_manager import CatalogManager
from eva.catalog.catalog_utils import get_video_table_column_definitions
from eva.executor.executor_utils import ExecutorError
from eva.server.command_handler import execute_query_fetch_all


@pytest.mark.notparallel
class DropExecutorTest(unittest.TestCase):
    def setUp(self):
        # reset the catalog manager before running each test
        CatalogManager().reset()
        self.video_file_path = create_sample_video()

    def tearDown(self):
        file_remove("dummy.avi")

    # integration test
    def test_should_drop_table(self):
        catalog_manager = CatalogManager()
        query = f"""LOAD VIDEO '{self.video_file_path}' INTO MyVideo;"""
        execute_query_fetch_all(query)

        # catalog should contain video table and the metadata table
        table_catalog_entry = catalog_manager.get_table_catalog_entry("MyVideo")
        video_dir = table_catalog_entry.file_url
        self.assertFalse(table_catalog_entry is None)
        column_objects = catalog_manager.get_column_catalog_entries_by_table(
            table_catalog_entry
        )
        # no of column objects should equal what we have defined plus one for row_id
        self.assertEqual(
            len(column_objects), len(get_video_table_column_definitions()) + 1
        )
        self.assertTrue(Path(video_dir).exists())
        video_metadata_table = (
            catalog_manager.get_multimedia_metadata_table_catalog_entry(
                table_catalog_entry
            )
        )
        self.assertTrue(video_metadata_table is not None)

        drop_query = """DROP TABLE IF EXISTS MyVideo;"""
        execute_query_fetch_all(drop_query)
        self.assertTrue(catalog_manager.get_table_catalog_entry("MyVideo") is None)
        column_objects = catalog_manager.get_column_catalog_entries_by_table(
            table_catalog_entry
        )
        self.assertEqual(len(column_objects), 0)
        self.assertFalse(Path(video_dir).exists())

        # Fail if table already dropped
        drop_query = """DROP TABLE MyVideo;"""
        with self.assertRaises(ExecutorError):
            execute_query_fetch_all(drop_query)


@pytest.mark.notparallel
class DropUDFExecutorTest(unittest.TestCase):
    def setUp(self):
        CatalogManager().reset()

    def tearDown(self):
        pass

    def run_create_udf_query(self):
        create_udf_query = """CREATE UDF DummyObjectDetector
            INPUT  (Frame_Array NDARRAY UINT8(3, 256, 256))
            OUTPUT (label NDARRAY STR(10))
            TYPE  Classification
            IMPL  'test/util.py';"""
        execute_query_fetch_all(create_udf_query)

    def test_should_drop_udf(self):
        catalog_manager = CatalogManager()
        self.run_create_udf_query()
        udf_name = "DummyObjectDetector"
        udf = catalog_manager.get_udf_catalog_entry_by_name(udf_name)
        self.assertTrue(udf is not None)

        # Test that dropping the UDF reflects in the catalog
        drop_query = "DROP UDF IF EXISTS {};".format(udf_name)
        execute_query_fetch_all(drop_query)
        udf = catalog_manager.get_udf_catalog_entry_by_name(udf_name)
        self.assertTrue(udf is None)

    def test_drop_wrong_udf_name(self):
        catalog_manager = CatalogManager()
        self.run_create_udf_query()
        right_udf_name = "DummyObjectDetector"
        wrong_udf_name = "FakeDummyObjectDetector"
        udf = catalog_manager.get_udf_catalog_entry_by_name(right_udf_name)
        self.assertTrue(udf is not None)

        # Test that dropping the wrong UDF:
        # - does not affect UDFs in the catalog
        # - raises an appropriate exception
        drop_query = "DROP UDF {};".format(wrong_udf_name)
        try:
            execute_query_fetch_all(drop_query)
        except Exception as e:
            err_msg = "UDF {} does not exist, therefore cannot be dropped.".format(
                wrong_udf_name
            )
            self.assertTrue(str(e) == err_msg)
        udf = catalog_manager.get_udf_catalog_entry_by_name(right_udf_name)
        self.assertTrue(udf is not None)
