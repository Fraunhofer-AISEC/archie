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
 *   This file contains the header functions for managing register data.
 */

#ifndef FAULTPLUGIN_REGISTERDUMP_H
#define FAULTPLUGIN_REGISTERDUMP_H

#include "faultplugin.h"
#include <qemu/qemu-plugin.h>

#include "protobuf/data.pb-c.h"

/**
 * This enum is the internal value for all available architectures supported
 */
enum architecture {ARM = 0, RISCV = 1};

#define N_ARM_REGISTERS 16
#define N_RISCV_REGISTERS 32

/**
 * init_register_module
 *
 * This function initialises the module. Must be called in setup.
 *
 * @param architecture is used to select the current simulated hardware. See architecture enum for which value represents what
 */
void init_register_module(int architecture);


/**
 * delete_register_module
 *
 * Clear all internal datastructures to free memory. All data is lost, if this function is called to early
 */
void delete_register_module(void);

/**
 * add_new_registerdump
 *
 * Readout all architecture registers and save value. Then save the value to internal linked list
 *
 * @param tbcount Value that is saved in the tbcount
 *
 * @return return negative value, if something went wrong
 */
int add_new_registerdump(uint64_t tbcount);


/**
 * read_register_module
 *
 * Readout structs and write them to protobuf message
 */
void read_register_module(Archie__Data* protobuf_msg);


#endif
