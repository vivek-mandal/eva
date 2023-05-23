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
from test.util import NUM_FRAMES, create_sample_video, file_remove, shutdown_ray

import pandas as pd
import pytest

from eva.catalog.catalog_manager import CatalogManager
from eva.models.storage.batch import Batch
from eva.server.command_handler import execute_query_fetch_all


@pytest.mark.notparallel
class CascadeOptimizer(unittest.TestCase):
    def setUp(self):
        CatalogManager().reset()
        self.video_file_path = create_sample_video(NUM_FRAMES)

    def tearDown(self):
        shutdown_ray()
        file_remove("dummy.avi")

    def test_logical_to_physical_udf(self):
        load_query = f"LOAD VIDEO '{self.video_file_path}' INTO MyVideo;"
        execute_query_fetch_all(load_query)

        create_udf_query = """CREATE UDF DummyObjectDetector
                  INPUT  (Frame_Array NDARRAY UINT8(3, 256, 256))
                  OUTPUT (label NDARRAY STR(10))
                  TYPE  Classification
                  IMPL  'test/util.py';
        """
        execute_query_fetch_all(create_udf_query)

        select_query = """SELECT id, DummyObjectDetector(data)
                    FROM MyVideo
                    WHERE DummyObjectDetector(data).label = ['person'];
        """
        actual_batch = execute_query_fetch_all(select_query)
        actual_batch.sort()
        expected = [
            {"myvideo.id": i * 2, "dummyobjectdetector.label": ["person"]}
            for i in range(NUM_FRAMES // 2)
        ]
        expected_batch = Batch(frames=pd.DataFrame(expected))
        self.assertEqual(actual_batch, expected_batch)

        execute_query_fetch_all("DROP TABLE IF EXISTS MyVideo;")
