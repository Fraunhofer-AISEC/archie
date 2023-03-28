# Copyright (c) 2021 Florian Andreas Hauschild
# Copyright (c) 2021 Fraunhofer AISEC
# Fraunhofer-Gesellschaft zur Foerderung der angewandten Forschung e.V.
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

import resource


def gather_process_ram_usage(queue_ram_usage, max_ram_usage):
    process_ram_usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

    if queue_ram_usage is not None:
        queue_ram_usage.put(process_ram_usage)

    if process_ram_usage > max_ram_usage:
        max_ram_usage = process_ram_usage

    return max_ram_usage
