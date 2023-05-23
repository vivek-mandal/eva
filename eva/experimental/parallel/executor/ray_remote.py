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
from typing import Callable, Dict, List

import ray
from ray.exceptions import RayTaskError
from ray.util.queue import Queue

from eva.executor.executor_utils import ExecutorError


class StageCompleteSignal:
    pass


@ray.remote(num_cpus=0)
def ray_wait_and_alert(tasks: List[ray.ObjectRef], queue: Queue):
    try:
        ray.get(tasks)
        queue.put(StageCompleteSignal)
    except RayTaskError as e:
        queue.put(ExecutorError(e.cause))


# Max calls set to 1 to forcefully release GPU resource when the job is
# complete. We choose to bypass resource management of Ray, but instead
# control GPU resource ourselves by configuring the environmental variables
# when the job enters the Ray process. Due to that, resource release is not
# cleanly done on the Ray side, we need to set this to prevent memory leak.
# More detailed explaination can be found in
# https://github.com/georgia-tech-db/eva/pull/731
@ray.remote(max_calls=1)
def ray_parallel(
    conf_dict: Dict[str, str],
    executor: Callable,
    input_queue: Queue,
    output_queue: Queue,
):
    for k, v in conf_dict.items():
        os.environ[k] = v

    gen = executor(input_queue=input_queue)
    for next_item in gen:
        output_queue.put(next_item)


@ray.remote(max_calls=1)
def ray_pull(conf_dict: Dict[str, str], executor: Callable, input_queue: Queue):
    for k, v in conf_dict.items():
        os.environ[k] = v

    for next_item in executor():
        input_queue.put(next_item)
