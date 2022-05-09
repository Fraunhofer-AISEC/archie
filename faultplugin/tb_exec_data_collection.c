/*                                                                                                          
 *   Copyright 2021 Florian Andreas Hauschild
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
 * Print the order of translation blocks executed. Also provide a counter number, such that it can be later resorted in python
 */
void plugin_dump_tb_exec_order()
{
	uint64_t i = 0;
	g_autoptr(GString) out = g_string_new("");
	g_string_printf(out, "$$$[TB Exec]:\n");
	plugin_write_to_data_pipe(out->str, out->len);

	if (tb_exec_order_ring_buffer)
	{
		/*
		 * If we logged less than TB_EXEC_RB_SIZE, the start of the buffer is
		 * at index 0. Otherwise, it is stored in tb_exec_rb_list_index.
		 */
		if (num_exec_order >= TB_EXEC_RB_SIZE)
		{
			i = tb_exec_rb_list_index;
		}

		for (int j = 0; j < TB_EXEC_RB_SIZE && j < num_exec_order; j++)
		{
			if (tb_exec_rb_list[i].tb_info == NULL)
			{
				g_string_printf(out, "$$ 0x0000 | %li \n", tb_exec_rb_list[i].pos);
			}
			else
			{
				g_string_printf(out, "$$ 0x%lx | %li \n",
								tb_exec_rb_list[i].tb_info->base_address,
								tb_exec_rb_list[i].pos);
			}
			plugin_write_to_data_pipe(out->str, out->len);

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
			if(item->tb_info == NULL)
			{
				g_string_printf(out, "$$ 0x0000 | %li \n", i);
			}
			else
			{
				g_string_printf(out, "$$ 0x%lx | %li \n", item->tb_info->base_address, i);
			}
			plugin_write_to_data_pipe(out->str, out->len);
			item = item->next;
			i++;
		}
	}
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
