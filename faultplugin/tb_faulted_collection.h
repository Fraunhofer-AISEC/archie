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
 *   This file contains the functions needed to collect faulted instruction assembler.
 */

#ifndef TB_FAULTED_COLLECTION_H
#define TB_FAULTED_COLLECTION_H

#include "singlestep.h"
#include "faultplugin.h"
#include <stdint.h>

/**
 * tb_faulte_init
 *
 * This function initalises the plugin
 *
 * @param number_faults: Number of faults in the plugin
 */
void tb_faulted_init(int number_faults);

/**
 * tb_faulted_free
 *
 * Free all allocated memory by this module
 */
void tb_faulted_free(void);

/**
 * tb_faulted_register
 *
 * Register a callback for getting a faulted assembly
 */
void tb_faulted_register(uint64_t fault_address);

/**
 * check_tb_faulted
 *
 * Check if a register faulted assembly is available
 *
 * @param tb: Pointer to tb struct given by qemu.
 */
void check_tb_faulted(struct qemu_plugin_tb *tb);

/**
 * dump_tb_faulted_data
 *
 * Write collected data protobuf message
 */
int dump_tb_faulted_data(Archie__Data* protobuf_msg);

#endif
