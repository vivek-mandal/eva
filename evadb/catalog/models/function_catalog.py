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
from __future__ import annotations

from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

from evadb.catalog.models.association_models import depend_function_and_function_cache
from evadb.catalog.models.base_model import BaseModel
from evadb.catalog.models.utils import FunctionCatalogEntry


class FunctionCatalog(BaseModel):
    """The `FunctionCatalog` catalog stores information about the user-defined functions (Functions) in the system. It maintains the following information for each Function
    `_row_id:` an autogenerated identifier
    `_impl_file_path: ` the path to the implementation script for the Function
    `_type:` an optional tag associated with the function (useful for grouping similar Functions, such as multiple object detection Functions)
    """

    __tablename__ = "function_catalog"

    _name = Column("name", String(128), unique=True)
    _impl_file_path = Column("impl_file_path", String(128))
    _type = Column("type", String(128))
    _checksum = Column("checksum", String(512))

    # FunctionIOCatalog storing the input/output attributes of the function
    _attributes = relationship(
        "FunctionIOCatalog",
        back_populates="_function",
        cascade="all, delete, delete-orphan",
    )
    _metadata = relationship(
        "FunctionMetadataCatalog",
        back_populates="_function",
        cascade="all, delete, delete-orphan",
    )

    _dep_caches = relationship(
        "FunctionCacheCatalog",
        secondary=depend_function_and_function_cache,
        back_populates="_function_depends",
        cascade="all, delete",
    )

    def __init__(self, name: str, impl_file_path: str, type: str, checksum: str):
        self._name = name
        self._impl_file_path = impl_file_path
        self._type = type
        self._checksum = checksum

    def as_dataclass(self) -> "FunctionCatalogEntry":
        args = []
        outputs = []
        for attribute in self._attributes:
            if attribute._is_input:
                args.append(attribute.as_dataclass())
            else:
                outputs.append(attribute.as_dataclass())

        metadata = []
        for meta_key_value in self._metadata:
            metadata.append(meta_key_value.as_dataclass())

        return FunctionCatalogEntry(
            row_id=self._row_id,
            name=self._name,
            impl_file_path=self._impl_file_path,
            type=self._type,
            checksum=self._checksum,
            args=args,
            outputs=outputs,
            metadata=metadata,
            dep_caches=[entry.as_dataclass() for entry in self._dep_caches],
        )