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
 */

#ifndef TB_INFO_DATA_COLLECTION
#define TB_INFO_DATA_COLLECTION

#include "lib/avl.h"
//#include "glib.h"
#include "stdint.h"
#include "qemu/osdep.h"
#include <qemu/plugin.h>
#include <qemu/qemu-plugin.h>
#include "protobuf/data.pb-c.h"

/* Output TB data structures */
typedef struct tb_info_t tb_info_t;
typedef struct tb_info_t
{
	uint64_t base_address;
	uint64_t size;
	uint64_t instruction_count;
	GString * assembler;
	uint64_t num_of_exec; // Number of executions(aka a counter)
	tb_info_t *next;
}tb_info_t;

/**
 * tb_info_init()
 *
 * This function initialises all global variables used in module
 */
void tb_info_init(void);

/**
 * tb_info_avl_init()
 *
 * function initialises avl tree for tb info
 */
int tb_info_avl_init(void);

/**
 * tb_info_free()
 *
 * function to delete the translation block information
 * structs from memory. Also deletes the avl tree
 */
void tb_info_free(void);

/**
 * tb_comparison_func
 *
 * Needed for avl library. it will determine which element is larger, of type tb_info_t.
 * See documentation of gnuavl lib for more information
 *
 * tbl_a: Element a to be compared
 * tbl_b: Element b to be compared
 * tbl_param: Is not used by this avl tree. But can be used to give additional information
 * to the comparison function
 *
 * return if negative, a is larger. If positive, b is larger. If 0, it is the same element.
 */
int tb_comparison_func(const void *tbl_a, const void *tbl_b, void * tbl_param);

/**
 * plugin_dump_tb_information()
 *
 * Function that reads the tb information structs and writes them to protobuf message.
 * Furthermore writes the command to python, such that it knows tb information is provided
 *
 *
 */
int plugin_dump_tb_information(Archie__Data* protobuf_msg);

tb_info_t * add_tb_info(struct qemu_plugin_tb *tb);

GString* decode_assembler(struct qemu_plugin_tb *tb);

size_t calculate_bytesize_instructions(struct qemu_plugin_tb *tb);

#endif
