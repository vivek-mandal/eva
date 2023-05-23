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
import os
from pathlib import Path
from typing import Dict, List

import pandas as pd

from eva.catalog.catalog_manager import CatalogManager
from eva.catalog.catalog_utils import get_metadata_properties
from eva.catalog.models.udf_catalog import UdfCatalogEntry
from eva.catalog.models.udf_io_catalog import UdfIOCatalogEntry
from eva.configuration.constants import EVA_DEFAULT_DIR
from eva.executor.abstract_executor import AbstractExecutor
from eva.models.storage.batch import Batch
from eva.plan_nodes.create_udf_plan import CreateUDFPlan
from eva.third_party.huggingface.create import gen_hf_io_catalog_entries
from eva.udfs.decorators.utils import load_io_from_udf_decorators
from eva.utils.errors import UDFIODefinitionError
from eva.utils.generic_utils import load_udf_class_from_file
from eva.utils.logging_manager import logger


class CreateUDFExecutor(AbstractExecutor):
    def __init__(self, node: CreateUDFPlan):
        super().__init__(node)

    def handle_huggingface_udf(self):
        """Handle HuggingFace UDFs

        HuggingFace UDFs are special UDFs that are not loaded from a file.
        So we do not need to call the setup method on them like we do for other UDFs.
        """
        impl_path = f"{EVA_DEFAULT_DIR}/udfs/abstract/hf_abstract_udf.py"
        io_list = gen_hf_io_catalog_entries(self.node.name, self.node.metadata)
        return (
            self.node.name,
            impl_path,
            self.node.udf_type,
            io_list,
            self.node.metadata,
        )

    def suffix_pytest_xdist_worker_id_to_dir(self, path: Path):
        try:
            worker_id = os.environ["PYTEST_XDIST_WORKER"]
            path = path / str(worker_id)
        except KeyError:
            pass
        return path

    def handle_ultralytics_udf(self):
        """Handle Ultralytics UDFs"""
        initial_eva_config_dir = Path(EVA_DEFAULT_DIR)
        updated_eva_config_dir = self.suffix_pytest_xdist_worker_id_to_dir(
            initial_eva_config_dir
        )
        impl_path = (
            Path(f"{updated_eva_config_dir}/udfs/yolo_object_detector.py")
            .absolute()
            .as_posix()
        )
        udf = self._try_initializing_udf(
            impl_path, udf_args=get_metadata_properties(self.node)
        )
        io_list = self._resolve_udf_io(udf)
        return (
            self.node.name,
            impl_path,
            self.node.udf_type,
            io_list,
            self.node.metadata,
        )

    def handle_generic_udf(self):
        """Handle generic UDFs

        Generic UDFs are loaded from a file. We check for inputs passed by the user during CREATE or try to load io from decorators.
        """
        impl_path = self.node.impl_path.absolute().as_posix()
        udf = self._try_initializing_udf(impl_path)
        io_list = self._resolve_udf_io(udf)

        return (
            self.node.name,
            impl_path,
            self.node.udf_type,
            io_list,
            self.node.metadata,
        )

    def exec(self, *args, **kwargs):
        """Create udf executor

        Calls the catalog to insert a udf catalog entry.
        """
        catalog_manager = CatalogManager()
        # check catalog if it already has this udf entry
        if catalog_manager.get_udf_catalog_entry_by_name(self.node.name):
            if self.node.if_not_exists:
                msg = f"UDF {self.node.name} already exists, nothing added."
                logger.warn(msg)
                yield Batch(pd.DataFrame([msg]))
                return
            else:
                msg = f"UDF {self.node.name} already exists."
                logger.error(msg)
                raise RuntimeError(msg)

        # if it's a type of HuggingFaceModel, override the impl_path
        if self.node.udf_type == "HuggingFace":
            name, impl_path, udf_type, io_list, metadata = self.handle_huggingface_udf()
        elif self.node.udf_type == "ultralytics":
            name, impl_path, udf_type, io_list, metadata = self.handle_ultralytics_udf()
        else:
            name, impl_path, udf_type, io_list, metadata = self.handle_generic_udf()

        catalog_manager.insert_udf_catalog_entry(
            name, impl_path, udf_type, io_list, metadata
        )
        yield Batch(
            pd.DataFrame([f"UDF {self.node.name} successfully added to the database."])
        )

    def _try_initializing_udf(
        self, impl_path: str, udf_args: Dict = {}
    ) -> UdfCatalogEntry:
        """Attempts to initialize UDF given the implementation file path and arguments.

        Args:
            impl_path (str): The file path of the UDF implementation file.
            udf_args (Dict, optional): Dictionary of arguments to pass to the UDF.
            Defaults to {}.

        Returns:
            UdfCatalogEntry: A UdfCatalogEntry object that represents the initialized
            UDF.

        Raises:
            RuntimeError: If an error occurs while initializing the UDF.
        """

        # load the udf class from the file
        try:
            # loading the udf class from the file
            udf = load_udf_class_from_file(impl_path, self.node.name)
            # initializing the udf class calls the setup method internally
            udf(**udf_args)
        except Exception as e:
            err_msg = f"Error creating UDF: {str(e)}"
            logger.error(err_msg)
            raise RuntimeError(err_msg)

        return udf

    def _resolve_udf_io(self, udf: UdfCatalogEntry) -> List[UdfIOCatalogEntry]:
        """Private method that resolves the input/output definitions for a given UDF.
        It first searches for the input/outputs in the CREATE statement. If not found, it resolves them using decorators. If not found there as well, it raises an error.

        Args:
            udf (UdfCatalogEntry): The UDF for which to resolve input and output definitions.

        Returns:
            A List of UdfIOCatalogEntry objects that represent the resolved input and
            output definitions for the UDF.

        Raises:
            RuntimeError: If an error occurs while resolving the UDF input/output
            definitions.
        """
        io_list = []
        try:
            if self.node.inputs:
                io_list.extend(self.node.inputs)
            else:
                # try to load the inputs from decorators, the inputs from CREATE statement take precedence
                io_list.extend(load_io_from_udf_decorators(udf, is_input=True))

            if self.node.outputs:
                io_list.extend(self.node.outputs)
            else:
                # try to load the outputs from decorators, the outputs from CREATE statement take precedence
                io_list.extend(load_io_from_udf_decorators(udf, is_input=False))

        except UDFIODefinitionError as e:
            err_msg = f"Error creating UDF, input/output definition incorrect: {str(e)}"
            logger.error(err_msg)
            raise RuntimeError(err_msg)

        return io_list
