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
 *   This file contains the functions needed to keep track of tb execution order.
 */

#include "tb_exec_data_collection.h"
#include "faultplugin.h"
#include <stdint.h>
#include <stdlib.h>

extern int tb_exec_order_ring_buffer;

tb_exec_order_t *tb_exec_order_list;

uint64_t num_exec_order;

struct tb_exec_rb_element {
	tb_info_t *tb_info;
	uint64_t pos;
};

#define TB_EXEC_RB_SIZE 100
struct tb_exec_rb_element *tb_exec_rb_list = NULL;
int tb_exec_rb_list_index;

int tb_exec_order_init()
{
	// List of execution order of tbs.
	tb_exec_order_list = NULL;
	num_exec_order = 0;

	if (tb_exec_order_ring_buffer)
	{
		tb_exec_rb_list_index = 0;
		tb_exec_rb_list = (struct tb_exec_rb_element *)malloc(
			TB_EXEC_RB_SIZE * sizeof(struct tb_exec_rb_element));
		if (tb_exec_rb_list == NULL)
		{
			return -1;
		}
	}

	return 0;
}


/**
 * tb_exec_order_free()
 *
 * Free linked list of tb_exec_order_t elements. It does not free the tb_info_t inside.
 * These must be freed separately with tb_info_free()
 */
void tb_exec_order_free()
{
	tb_exec_order_t *item;
	while(tb_exec_order_list != NULL)
	{
		item = tb_exec_order_list;
		tb_exec_order_list = tb_exec_order_list->prev;
		free(item);
	}

	if (tb_exec_order_ring_buffer && tb_exec_rb_list != NULL)
	{
		free(tb_exec_rb_list);
	}
}


/**
 * plugin_dump_tb_exec_order
 *
 * Write the order of translation blocks executed. Also provide a counter number, such that it can be later resorted in python
 */
void plugin_dump_tb_exec_order(Archie__Data* protobuf_msg)
{
	uint64_t i = 0;

	Archie__TbExecOrder** msg_tb_exec_order_list;
	if (tb_exec_order_ring_buffer)
	{
		/*
		 * If we logged less than TB_EXEC_RB_SIZE, the start of the buffer is
		 * at index 0. Otherwise, it is stored in tb_exec_rb_list_index.
		 */
		if (num_exec_order >= TB_EXEC_RB_SIZE) {
			i = tb_exec_rb_list_index;
			msg_tb_exec_order_list = malloc(sizeof(Archie__TbExecOrder *) * TB_EXEC_RB_SIZE);
			protobuf_msg->n_tb_exec_orders = TB_EXEC_RB_SIZE;
		}
		else
		{
			msg_tb_exec_order_list = malloc(sizeof(Archie__TbExecOrder*) * num_exec_order);
			protobuf_msg->n_tb_exec_orders = num_exec_order;
		}
		for (int j = 0; j < TB_EXEC_RB_SIZE && j < num_exec_order; j++)
		{
			msg_tb_exec_order_list[j] = malloc(sizeof(Archie__TbExecOrder));
			archie__tb_exec_order__init(msg_tb_exec_order_list[j]);

			if (tb_exec_rb_list[i].tb_info == NULL)
			{
				msg_tb_exec_order_list[j]->tb_base_address = 0;
				msg_tb_exec_order_list[j]->pos = tb_exec_rb_list[i].pos;
			}
			else
			{
				msg_tb_exec_order_list[j]->tb_base_address = tb_exec_rb_list[i].tb_info->base_address;
				msg_tb_exec_order_list[j]->pos = tb_exec_rb_list[i].pos;
			}

			i++;
			if (i == TB_EXEC_RB_SIZE)
			{
				i = 0;
			}
		}
	}
	else
	{
		tb_exec_order_t *item =  tb_exec_order_list;

		msg_tb_exec_order_list = malloc(sizeof(Archie__TbExecOrder*) * num_exec_order);
		if(msg_tb_exec_order_list == NULL)
		{
			qemu_plugin_outs("[DEBUG]: Tb_exec_order could not saved to protobuf message\n");
		}
		protobuf_msg->n_tb_exec_orders = num_exec_order;

		if(item == NULL)
		{
			return;
		}

		while(item->prev != NULL)
		{
			i++;
			item = item->prev;
		}
		i++;
		if(i != num_exec_order)
		{
			qemu_plugin_outs("[WARNING]: i and numexec differ!\n");
		}
		i = 0;
		while(item != NULL)
		{
			msg_tb_exec_order_list[i] = malloc(sizeof(Archie__TbExecOrder));
			if(msg_tb_exec_order_list[i] == NULL)
			{
				qemu_plugin_outs("[DEBUG]: Tb_exec_order could not saved to protobuf message\n");
			}
			archie__tb_exec_order__init(msg_tb_exec_order_list[i]);

			if(item->tb_info == NULL)
			{
				msg_tb_exec_order_list[i]->tb_base_address = 0;
				msg_tb_exec_order_list[i]->pos = i;
			}
			else
			{
				msg_tb_exec_order_list[i]->tb_base_address = item->tb_info->base_address;
				msg_tb_exec_order_list[i]->pos = i;
			}

			item = item->next;
			i++;
		}
	}

	protobuf_msg->tb_exec_orders = msg_tb_exec_order_list;
}

/**
 * tb_exec_data_event
 * 
 * Function to collect the exec data about translation blocks
 *
 * vcpu_index: current index of cpu the callback was triggered from
 * vcurrent: pointer to tb_info struct of the current tb
 */
void tb_exec_data_event(unsigned int vcpu_index, void *vcurrent)
{
	tb_info_t *tb_info = vcurrent;
	if(tb_info != NULL)
	{
		tb_info->num_of_exec++;
	}

	if (tb_exec_order_ring_buffer)
	{
		tb_exec_rb_list[tb_exec_rb_list_index].tb_info = tb_info;
		tb_exec_rb_list[tb_exec_rb_list_index].pos = num_exec_order;

		tb_exec_rb_list_index++;
		if (tb_exec_rb_list_index == TB_EXEC_RB_SIZE)
		{
			tb_exec_rb_list_index = 0;
		}
	}
	else
	{
		tb_exec_order_t *last = malloc(sizeof(tb_exec_order_t));
		last->tb_info = tb_info;
		last->next = NULL;
		last->prev = tb_exec_order_list;
		if(tb_exec_order_list != NULL)
		{
			tb_exec_order_list->next = last;
		}
		tb_exec_order_list = last;
	}

	num_exec_order++;
}
