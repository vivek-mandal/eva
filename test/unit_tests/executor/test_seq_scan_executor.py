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
from test.unit_tests.executor.utils import DummyExecutor
from test.util import create_dataframe

import pandas as pd
from mock import MagicMock

from evadb.executor.seq_scan_executor import SequentialScanExecutor
from evadb.models.storage.batch import Batch


class SeqScanExecutorTest(unittest.TestCase):
    def test_should_return_only_frames_satisfy_predicate(self):
        dataframe = create_dataframe(3)
        batch = Batch(frames=dataframe)
        expression = type(
            "AbstractExpression",
            (),
            {
                "evaluate": lambda x: Batch(pd.DataFrame([False, False, True])),
                "find_all": lambda expr: [],
            },
        )

        plan = type(
            "ScanPlan", (), {"predicate": expression, "columns": None, "alias": None}
        )
        predicate_executor = SequentialScanExecutor(MagicMock(), plan)
        predicate_executor.append_child(DummyExecutor([batch]))

        expected = Batch(batch.frames[batch.frames.index == 2].reset_index(drop=True))
        filtered = list(predicate_executor.exec())[0]
        self.assertEqual(expected, filtered)

    def test_should_return_all_frames_when_no_predicate_is_applied(self):
        dataframe = create_dataframe(3)

        batch = Batch(frames=dataframe)

        plan = type("ScanPlan", (), {"predicate": None, "columns": None, "alias": None})
        predicate_executor = SequentialScanExecutor(MagicMock(), plan)
        predicate_executor.append_child(DummyExecutor([batch]))

        filtered = list(predicate_executor.exec())[0]
        self.assertEqual(batch, filtered)

    def test_should_return_projected_columns(self):
        dataframe = create_dataframe(3)

        batch = Batch(frames=dataframe)
        proj_batch = Batch(frames=pd.DataFrame(dataframe["data"]))
        expression = [
            type(
                "AbstractExpression",
                (),
                {
                    "evaluate": lambda x: Batch(pd.DataFrame(x.frames["data"])),
                    "find_all": lambda expr: [],
                },
            )
        ]

        plan = type(
            "ScanPlan", (), {"predicate": None, "columns": expression, "alias": None}
        )
        proj_executor = SequentialScanExecutor(MagicMock(), plan)
        proj_executor.append_child(DummyExecutor([batch]))

        actual = list(proj_executor.exec())[0]
        self.assertEqual(proj_batch, actual)


if __name__ == "__main__":
    unittest.main()
