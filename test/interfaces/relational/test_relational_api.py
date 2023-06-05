# coding=utf-8
# Copyright 2018-2023 EVA
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
    DummyObjectDetector,
    create_sample_video,
    load_udfs_for_testing,
    shutdown_ray,
    suffix_pytest_xdist_worker_id_to_dir,
)

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

from eva.configuration.constants import EVA_DATABASE_DIR, EVA_ROOT_DIR
from eva.executor.executor_utils import ExecutorError
from eva.interfaces.relational.db import connect
from eva.models.storage.batch import Batch
from eva.server.command_handler import execute_query_fetch_all


class RelationalAPI(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def setUpClass(cls):
        cls.db_dir = suffix_pytest_xdist_worker_id_to_dir(EVA_DATABASE_DIR)
        cls.conn = connect(cls.db_dir)
        cls.evadb = cls.conn._evadb

    def setUp(self):
        self.evadb.catalog().reset()
        self.mnist_path = f"{EVA_ROOT_DIR}/data/mnist/mnist.mp4"
        load_udfs_for_testing(
            self.evadb,
        )
        self.images = f"{EVA_ROOT_DIR}/data/detoxify/*.jpg"

    def tearDown(self):
        shutdown_ray()
        # todo: move these to relational apis as well
        execute_query_fetch_all(self.evadb, """DROP TABLE IF EXISTS mnist_video;""")
        execute_query_fetch_all(self.evadb, """DROP TABLE IF EXISTS meme_images;""")

    def test_relation_apis(self):
        cursor = self.conn.cursor()
        rel = cursor.load(
            self.mnist_path,
            table_name="mnist_video",
            format="video",
        )
        rel.execute()

        rel = cursor.table("mnist_video")
        assert_frame_equal(rel.df(), cursor.query("select * from mnist_video;").df())

        rel = rel.select("_row_id, id, data")
        assert_frame_equal(
            rel.df(),
            cursor.query("select _row_id, id, data from mnist_video;").df(),
        )

        rel = rel.filter("id < 10")
        assert_frame_equal(
            rel.df(),
            cursor.query(
                "select _row_id, id, data from mnist_video where id < 10;"
            ).df(),
        )

        rel = (
            rel.cross_apply("unnest(MnistImageClassifier(data))", "mnist(label)")
            .filter("mnist.label = 1")
            .select("_row_id, id")
        )

        query = """ select _row_id, id
                    from mnist_video
                        join lateral unnest(MnistImageClassifier(data)) AS mnist(label)
                    where id < 10 AND mnist.label = 1;"""
        assert_frame_equal(rel.df(), cursor.query(query).df())

        rel = cursor.load(
            self.images,
            table_name="meme_images",
            format="image",
        )
        rel.execute()

        rel = cursor.table("meme_images").select("_row_id, name")
        assert_frame_equal(
            rel.df(), cursor.query("select _row_id, name from meme_images;").df()
        )

        rel = rel.filter("_row_id < 3")
        assert_frame_equal(
            rel.df(),
            cursor.query(
                "select _row_id, name from meme_images where _row_id < 3;"
            ).df(),
        )

    def test_relation_api_chaining(self):
        cursor = self.conn.cursor()

        rel = cursor.load(
            self.mnist_path,
            table_name="mnist_video",
            format="video",
        )
        rel.execute()

        rel = (
            cursor.table("mnist_video")
            .select("id, data")
            .filter("id > 10")
            .filter("id < 20")
        )
        assert_frame_equal(
            rel.df(),
            cursor.query(
                "select id, data from mnist_video where id > 10 AND id < 20;"
            ).df(),
        )

    def test_interleaving_calls(self):
        cursor = self.conn.cursor()

        rel = cursor.load(
            self.mnist_path,
            table_name="mnist_video",
            format="video",
        )
        rel.execute()

        rel = cursor.table("mnist_video")
        filtered_rel = rel.filter("id > 10")

        assert_frame_equal(
            rel.filter("id > 10").df(),
            cursor.query("select * from mnist_video where id > 10;").df(),
        )

        assert_frame_equal(
            filtered_rel.select("_row_id, id").df(),
            cursor.query("select _row_id, id from mnist_video where id > 10;").df(),
        )

    def test_create_index(self):
        cursor = self.conn.cursor()

        # load some images
        rel = cursor.load(
            self.images,
            table_name="meme_images",
            format="image",
        )
        rel.execute()

        # todo support register udf
        cursor.query(
            f"""CREATE UDF IF NOT EXISTS SiftFeatureExtractor
                IMPL  '{EVA_ROOT_DIR}/eva/udfs/sift_feature_extractor.py'"""
        ).df()

        # create a vector index using QDRANT
        cursor.create_vector_index(
            "faiss_index",
            table_name="meme_images",
            expr="SiftFeatureExtractor(data)",
            using="QDRANT",
        ).df()

        # do similarity search
        base_image = f"{EVA_ROOT_DIR}/data/detoxify/meme1.jpg"
        rel = (
            cursor.table("meme_images")
            .order(
                f"Similarity(SiftFeatureExtractor(Open('{base_image}')), SiftFeatureExtractor(data))"
            )
            .limit(1)
            .select("name")
        )
        similarity_sql = """SELECT name FROM meme_images
                            ORDER BY
                                Similarity(SiftFeatureExtractor(Open("{}")), SiftFeatureExtractor(data))
                            LIMIT 1;""".format(
            base_image
        )
        assert_frame_equal(rel.df(), cursor.query(similarity_sql).df())

    def test_create_udf_with_relational_api(self):
        video_file_path = create_sample_video(10)

        cursor = self.conn.cursor()
        # load video
        rel = cursor.load(
            video_file_path,
            table_name="dummy_video",
            format="video",
        )
        rel.execute()

        create_dummy_object_detector_udf = cursor.create_udf(
            "DummyObjectDetector", if_not_exists=True, impl_path="test/util.py"
        )
        create_dummy_object_detector_udf.execute()

        args = {"task": "automatic-speech-recognition", "model": "openai/whisper-base"}

        create_speech_recognizer_udf_if_not_exists = cursor.create_udf(
            "SpeechRecognizer", if_not_exists=True, type="HuggingFace", **args
        )
        query = create_speech_recognizer_udf_if_not_exists.sql_query()
        self.assertEqual(
            query,
            """CREATE UDF SpeechRecognizer IF NOT EXISTS TYPE HuggingFace 'task' 'automatic-speech-recognition' 'model' 'openai/whisper-base'""",
        )
        create_speech_recognizer_udf_if_not_exists.execute()

        # check if next create call of same UDF raises error
        create_speech_recognizer_udf = cursor.create_udf(
            "SpeechRecognizer", if_not_exists=False, type="HuggingFace", **args
        )
        query = create_speech_recognizer_udf.sql_query()
        self.assertEqual(
            query,
            "CREATE UDF SpeechRecognizer TYPE HuggingFace 'task' 'automatic-speech-recognition' 'model' 'openai/whisper-base'",
        )
        with self.assertRaises(ExecutorError):
            create_speech_recognizer_udf.execute()

        select_query_sql = (
            "SELECT id, DummyObjectDetector(data) FROM dummy_video ORDER BY id;"
        )
        actual_batch = cursor.query(select_query_sql).execute()
        labels = DummyObjectDetector().labels
        expected = [
            {
                "dummy_video.id": i,
                "dummyobjectdetector.label": np.array([labels[1 + i % 2]]),
            }
            for i in range(10)
        ]
        expected_batch = Batch(frames=pd.DataFrame(expected))
        self.assertEqual(actual_batch, expected_batch)
