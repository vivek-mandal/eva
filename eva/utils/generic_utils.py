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
import hashlib
import importlib
import inspect
import os
import pickle
import shutil
import sys
import uuid
from pathlib import Path
from typing import List

from aenum import AutoEnum, unique

from eva.configuration.configuration_manager import ConfigurationManager
from eva.utils.logging_manager import logger


def validate_kwargs(
    kwargs,
    allowed_keys: List[str],
    required_keys: List[str],
    error_message="Keyword argument not understood:",
):
    """Checks that all keyword arguments are in the set of allowed keys."""
    if required_keys is None:
        required_keys = allowed_keys
    for kwarg in kwargs:
        if kwarg not in allowed_keys:
            raise TypeError(error_message, kwarg)

    missing_keys = [key for key in required_keys if key not in kwargs]
    assert len(missing_keys) == 0, f"Missing required keys, {missing_keys}"


def str_to_class(class_path: str):
    """
    Convert string representation of a class path to Class

    Arguments:
        class_path (str): absolute path of import

    Returns:
        type: A Class for given path
    """
    module_path, class_name = class_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def load_udf_class_from_file(filepath, classname=None):
    """
    Load a class from a Python file. If the classname is not specified, the function will check if there is only one class in the file and load that. If there are multiple classes, it will raise an error.

    Args:
        filepath (str): The path to the Python file.
        classname (str, optional): The name of the class to load. If not specified, the function will try to load a class with the same name as the file. Defaults to None.

    Returns:
        The class instance.

    Raises:
        RuntimeError: If the class name is not found or there is more than one class in the file.
    """
    try:
        abs_path = Path(filepath).resolve()
        spec = importlib.util.spec_from_file_location(abs_path.stem, abs_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception as e:
        err_msg = f"Couldn't load UDF from {filepath} : {str(e)}. Ensure that the file exists and that it is a valid Python file."
        raise RuntimeError(err_msg)

    # Try to load the specified class by name
    if classname and hasattr(module, classname):
        return getattr(module, classname)

    # If class name not specified, check if there is only one class in the file
    classes = [
        obj
        for _, obj in inspect.getmembers(module, inspect.isclass)
        if obj.__module__ == module.__name__
    ]
    if len(classes) != 1:
        raise RuntimeError(
            f"{filepath} contains {len(classes)} classes, please specify the correct class to load by naming the UDF with the same name in the CREATE query."
        )
    return classes[0]


def is_gpu_available() -> bool:
    """
    Checks if the system has GPUS available to execute tasks
    Returns:
        [bool] True if system has GPUs, else False
    """
    try:
        import torch

        return torch.cuda.is_available()
    except ImportError:
        return False


def prefix_xdist_worker_id_to_path(path: str):
    try:
        worker_id = os.environ["PYTEST_XDIST_WORKER"]
        base = "eva_datasets"
        path = "build/" + str(worker_id) + "_" + base
    except KeyError:
        # Single threaded mode
        pass
    return path


def get_gpu_count() -> int:
    """
    Check number of GPUs through Torch.
    """
    try:
        import torch

        return torch.cuda.device_count()
    except ImportError:
        return 0


def generate_file_path(name: str = "") -> Path:
    """Generates a arbitrary file_path(md5 hash) based on the a random salt
    and name

    Arguments:
        name (str): Input file_name.

    Returns:
        Path: pathlib.Path object

    """
    dataset_location = ConfigurationManager().get_value("core", "datasets_dir")
    if dataset_location is None:
        logger.error("Missing dataset location key in eva.yml")
        raise KeyError("Missing datasets_dir key in eva.yml")

    dataset_location = prefix_xdist_worker_id_to_path(dataset_location)
    dataset_location = Path(dataset_location)
    dataset_location.mkdir(parents=True, exist_ok=True)

    salt = uuid.uuid4().hex
    file_name = hashlib.md5(salt.encode() + name.encode()).hexdigest()
    path = dataset_location / file_name
    return path.resolve()


def get_size(obj, seen=None):
    """Recursively finds size of objects
    https://goshippo.com/blog/measure-real-size-any-python-object/
    """
    size = sys.getsizeof(obj)
    if seen is None:
        seen = set()
    obj_id = id(obj)
    if obj_id in seen:
        return 0
    # Important mark as seen *before* entering recursion to gracefully handle
    # self-referential objects
    seen.add(obj_id)
    if isinstance(obj, dict):
        size += sum([get_size(v, seen) for v in obj.values()])
        size += sum([get_size(k, seen) for k in obj.keys()])
    elif hasattr(obj, "__dict__"):
        size += get_size(obj.__dict__, seen)
    elif hasattr(obj, "__iter__") and not isinstance(obj, (str, bytes, bytearray)):
        size += sum([get_size(i, seen) for i in obj])
    return size


def get_str_hash(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def get_file_checksum(fname: str) -> str:
    """Compute checksum of the file contents

    Args:
        fname (str): file path

    Returns:
        str: hash string representing the checksum of the file content
    """
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


class PickleSerializer(object):
    @classmethod
    def serialize(cls, data):
        return pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)

    @classmethod
    def deserialize(cls, data):
        return pickle.loads(data)


@unique
class EVAEnum(AutoEnum):
    def __str__(self):
        return self.name


def remove_directory_contents(dir_path):
    if os.path.exists(dir_path):
        for filename in os.listdir(dir_path):
            file_path = os.path.join(dir_path, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                logger.warning(f"Failed to delete {file_path}. Reason: {str(e)}")
