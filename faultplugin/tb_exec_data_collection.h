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
 *   This file contains the headers for collection tb execution information
 */

#ifndef TB_EXEC_DATA_COLLECTION
#define TB_EXEC_DATA_COLLECTION


#include <qemu/qemu-plugin.h>
#include "tb_info_data_collection.h"

typedef struct tb_exec_order_t tb_exec_order_t;
typedef struct tb_exec_order_t
{
	tb_info_t *tb_info;
	tb_exec_order_t *prev;
	tb_exec_order_t *next;
}tb_exec_order_t;


int tb_exec_order_init();

/**
 * tb_exec_order_free()
 *
 * Free linked list of tb_exec_order_t elements. It does not free the tb_info_t inside.
 * These must be freed separately with tb_info_free()
 */
void tb_exec_order_free();

/**
 * plugin_dump_tb_exec_order
 *
 * Print the order of translation blocks executed. Also provide a counter number, such that it can be later resorted in python
 */
void plugin_dump_tb_exec_order(Archie__Data* msg);

/**
 * tb_exec_data_event
 * 
 * Function to collect the exec data about translation blocks
 *
 * vcpu_index: current index of cpu the callback was triggered from
 * vcurrent: pointer to tb_info struct of the current tb
 */
void tb_exec_data_event(unsigned int vcpu_index, void *vcurrent);
#endif
