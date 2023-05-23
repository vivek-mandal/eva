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

import numpy as np
import pandas as pd
from numpy import asarray
from PIL import Image

from eva.configuration.constants import EVA_ROOT_DIR
from eva.udfs.ndarray.horizontal_flip import HorizontalFlip
from eva.udfs.ndarray.vertical_flip import VerticalFlip


class FlipTests(unittest.TestCase):
    def setUp(self):
        self.horizontal_flip_instance = HorizontalFlip()
        self.vertical_flip_instance = VerticalFlip()

    def test_flip_name_exists(self):
        assert hasattr(self.horizontal_flip_instance, "name")
        assert hasattr(self.vertical_flip_instance, "name")

    def test_should_flip_horizontally(self):
        img = Image.open(
            f"{EVA_ROOT_DIR}/test/data/uadetrac/small-data/MVI_20011/img00001.jpg"
        )
        arr = asarray(img)
        df = pd.DataFrame([[arr]])
        flipped_arr = self.horizontal_flip_instance(df)[
            "horizontally_flipped_frame_array"
        ]

        self.assertEqual(np.sum(arr[:, 0] - np.flip(flipped_arr[0][:, -1], 1)), 0)

    def test_should_flip_vertically(self):
        img = Image.open(
            f"{EVA_ROOT_DIR}/test/data/uadetrac/small-data/MVI_20011/img00001.jpg"
        )
        arr = asarray(img)
        df = pd.DataFrame([[arr]])
        flipped_arr = self.vertical_flip_instance(df)["vertically_flipped_frame_array"]

        self.assertEqual(np.sum(arr[0, :] - np.flip(flipped_arr[0][-1, :], 1)), 0)
