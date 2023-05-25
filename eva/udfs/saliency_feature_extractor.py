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
import cv2
import kornia
import numpy as np
import pandas as pd
import torch
import torchvision
import torch.nn as nn
import torch.nn.functional as F

from eva.catalog.catalog_type import NdArrayType
from eva.udfs.abstract.abstract_udf import AbstractUDF
from eva.udfs.decorators.decorators import forward, setup
from eva.udfs.decorators.io_descriptors.data_types import PandasDataframe
from eva.udfs.gpu_compatible import GPUCompatible
from torchvision.transforms import Compose, ToTensor, Resize
from PIL import Image


class SaliencyFeatureExtractor(AbstractUDF, GPUCompatible):
    @setup(cacheable=False, udf_type="FeatureExtraction", batchable=False)
    def setup(self):
        # self.model = kornia.feature.SIFTDescriptor(100)
        self.model = torchvision.models.resnet18(pretrained=True)
        num_features = self.model.fc.in_features
        self.model.fc = nn.Linear(num_features, 2) # binary classification (num_of_class == 2)
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model_state = torch.load("data/saliency/model.pth", map_location=device)
        self.model.load_state_dict(model_state)
        self.model.eval()

    def to_device(self, device: str) -> GPUCompatible:
        self.model = self.model.to(device)
        return self

    @property
    def name(self) -> str:
        return "SaliencyFeatureExtractor"

    @forward(
        input_signatures=[
            PandasDataframe(
                columns=["data"],
                column_types=[NdArrayType.UINT8],
                column_shapes=[(None, None, 3)],
            )
        ],
        output_signatures=[
            PandasDataframe(
                columns=["saliency"],
                column_types=[NdArrayType.FLOAT32],
                column_shapes=[(1, 224,224)],
            )
        ],
    )
    def forward(self, df: pd.DataFrame) -> pd.DataFrame:
        def _forward(row: pd.Series) -> np.ndarray:
            rgb_img = row[0]

            composed = Compose([
            Resize((224, 224)),            
            ToTensor()
            ])
            transfromed_img = composed(Image.fromarray(rgb_img[:, :, ::-1])).unsqueeze(0)
            transfromed_img.requires_grad_()
            outputs = self.model(transfromed_img)
            score_max_index = outputs.argmax()
            score_max = outputs[0,score_max_index]
            score_max.backward()
            saliency, _ = torch.max(transfromed_img.grad.data.abs(),dim=1)

            return saliency

        ret = pd.DataFrame()
        ret["saliency"] = df.apply(_forward, axis=1)
        return ret