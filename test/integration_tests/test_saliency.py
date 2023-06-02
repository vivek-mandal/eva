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
from test.util import (
    shutdown_ray,
)

import pytest

from eva.catalog.catalog_manager import CatalogManager
from eva.server.command_handler import execute_query_fetch_all


@pytest.mark.notparallel
class SaliencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        CatalogManager().reset()
       
    @classmethod
    def tearDownClass(cls):
        shutdown_ray()
        # execute_query_fetch_all("DROP TABLE IF EXISTS MyVideo;")
        execute_query_fetch_all("DROP TABLE IF EXISTS SALIENCY;")
        # file_remove("dummy.avi")

    def test_saliency(self):
        Saliency1 = f"data/saliency/test1.jpeg"
        create_udf_query = f"LOAD IMAGE '{Saliency1}' INTO SALIENCY;"
       
        execute_query_fetch_all(create_udf_query)
        create_udf_query = """CREATE UDF IF NOT EXISTS SaliencyFeatureExtractor
                    IMPL  'eva/udfs/saliency_feature_extractor.py';
        """
        execute_query_fetch_all(create_udf_query)

        select_query_saliency = """SELECT data, SaliencyFeatureExtractor(data)
                  FROM SALIENCY
        """
        actual_batch_saliency = execute_query_fetch_all(select_query_saliency)
        self.assertEqual(len(actual_batch_saliency.columns), 2)