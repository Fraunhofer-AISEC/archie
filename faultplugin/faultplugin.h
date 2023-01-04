/*
 *   Copyright 2021 Florian Andreas Hauschild
 *   Copyright (c) 2021 Fraunhofer AISEC
 *   Fraunhofer-Gesellschaft zur Foerderung der angewandten Forschung e.V.
 *
 *   Licensed under the Apache License, Version 2.0 (the "License");
 *   you may not use this file except in compliance with the License.
 *   You may obtain a copy of the License at
 *
 *       http://www.apache.org/licenses/LICENSE-2.0
 *
 *   Unless required by applicable law or agreed to in writing, software
 *   distributed under the License is distributed on an "AS IS" BASIS,
 *   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *   See the License for the specific language governing permissions and
 *   limitations under the License.
 *
 *   This file contains the header for the main part of the plugin.
 */

#ifndef QEMU_FAULTPLUGIN
#define QEMU_FAULTPLUGIN


#include <inttypes.h>
#include <glib.h>
#include "fault_list.h"

enum{ DATA, INSTRUCTION, REGISTER};
enum{ SET0, SET1, TOGGLE, OVERWRITE};
enum Pipe_type { CONFIG_PIPE, CONTROL_PIPE, DATA_PIPE};


int register_live_faults_callback(fault_list_t *fault);

void invalidate_fault_trigger_address(int fault_trigger_number);

int plugin_write_to_data_pipe(char *str, size_t len);
 

#endif
