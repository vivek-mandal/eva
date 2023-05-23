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
from typing import Iterator

from eva.catalog.catalog_type import TableType
from eva.executor.abstract_executor import AbstractExecutor
from eva.executor.executor_utils import ExecutorError
from eva.models.storage.batch import Batch
from eva.plan_nodes.storage_plan import StoragePlan
from eva.storage.storage_engine import StorageEngine
from eva.utils.logging_manager import logger


class StorageExecutor(AbstractExecutor):
    def __init__(self, node: StoragePlan):
        super().__init__(node)

    def exec(self, *args, **kwargs) -> Iterator[Batch]:
        try:
            storage_engine = StorageEngine.factory(self.node.table)

            if self.node.table.table_type == TableType.VIDEO_DATA:
                return storage_engine.read(
                    self.node.table,
                    self.node.batch_mem_size,
                    predicate=self.node.predicate,
                    sampling_rate=self.node.sampling_rate,
                    sampling_type=self.node.sampling_type,
                    read_audio=self.node.table_ref.get_audio,
                    read_video=self.node.table_ref.get_video,
                )
            elif self.node.table.table_type == TableType.IMAGE_DATA:
                return storage_engine.read(self.node.table)
            elif self.node.table.table_type == TableType.DOCUMENT_DATA:
                return storage_engine.read(self.node.table)
            elif self.node.table.table_type == TableType.STRUCTURED_DATA:
                return storage_engine.read(self.node.table, self.node.batch_mem_size)
            else:
                raise ExecutorError(
                    f"Unsupported TableType  {self.node.table.table_type} encountered"
                )
        except Exception as e:
            logger.error(e)
            raise ExecutorError(e)
