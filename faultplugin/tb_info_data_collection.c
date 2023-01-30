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
 *   This file contains the functions to manage the collection about tb information
 */

#include "tb_info_data_collection.h"
#include "faultplugin.h"

#include <stdio.h>

tb_info_t *tb_info_list; 
/* AVL global variables */
struct avl_table *tb_avl_root;

void tb_info_init()
{
	// Linked list of tb structs inside tb. Used to delete them.
	tb_info_list = NULL;
	tb_avl_root = NULL;
}

int tb_info_avl_init()
{
	// AVL tree used in collecting data. This contains the tbs info of all generated tbs.
	// The id of a tb is its base address
	tb_avl_root = avl_create( &tb_comparison_func, NULL, NULL);
	if(tb_avl_root == NULL)
	{
		return -1;
	}
	return 0;
}


/**
 * tb_info_free()
 *
 * Function to delete the translation block information
 * structs from memory. Also deletes the avl tree
 */
void tb_info_free()
{
	tb_info_t *item;
	while(tb_info_list != NULL)
	{
		item = tb_info_list;
		tb_info_list = tb_info_list->next;
		free(item);
	}
	if(tb_avl_root != NULL)
	{
		avl_destroy( tb_avl_root, NULL);
		tb_avl_root = NULL;
	}
}

/**
 * tb_comparison_func
 *
 * Needed for avl library. It will determine which element is larger, of type tb_info_t.
 * See documentation of gnuavl lib for more information
 *
 * tbl_a: Element a to be compared
 * tbl_b: Element b to be compared
 * tbl_param: Is not used by this avl tree. But can be used to give additional information
 * to the comparison function
 *
 * return if negative, a is larger. If positive, b is larger. If 0, it is the same element.
 */
int tb_comparison_func(const void *tbl_a, const void *tbl_b, void * tbl_param)
{
	const tb_info_t * tb_a = tbl_a;
	const tb_info_t * tb_b = tbl_b;
	if(tb_a->base_address < tb_b->base_address)
	{

		return -1;
	}
	else if(tb_a->base_address > tb_b->base_address) return 1;
	else return 0;
}

size_t get_tb_info_list_size(){
    tb_info_t *item = tb_info_list;
    size_t size = 0;
    while(item != NULL)
    {
        size++;
        item = item->next;
    }

    return size;
}

/**
 * plugin_dump_tb_information()
 *
 * Function that reads the tb information structs and prints each one to the data pipe. Furthermore, writes the command to python, such that it knows tb information is provided
 *
 *
 */
void plugin_dump_tb_information(Archie__Data* protobuf_msg)
{
	if(tb_info_list == NULL)
	{
		return;
	}

    // Allocate and init list for protobuf tb information dumps
    size_t size = get_tb_info_list_size();
    Archie__TbInformation** tb_information_list;
    tb_information_list = malloc(sizeof(Archie__TbInformation*) * size);
    protobuf_msg->n_tb_informations = size;


	tb_info_t *item = tb_info_list;
    int counter = 0;
	while(item != NULL)
	{
        tb_information_list[counter] = malloc(sizeof(Archie__TbInformation));
        archie__tb_information__init(tb_information_list[counter]);

        tb_information_list[counter]->base_address = item->base_address;
        tb_information_list[counter]->size = item->size;
        tb_information_list[counter]->instruction_count = item->instruction_count;
        tb_information_list[counter]->num_of_exec = item->num_of_exec;
        tb_information_list[counter]->assembler = item->assembler->str;

        counter++;

		item = item->next;
	}

    protobuf_msg->tb_informations = tb_information_list;
}

tb_info_t * add_tb_info(struct qemu_plugin_tb *tb)
{
	g_autoptr(GString) out = g_string_new("");
	g_string_printf(out, "\n");
	tb_info_t tmp;
	tmp.base_address = tb->vaddr;
	g_string_append_printf(out, "[TB Info]: Search TB......");
	tb_info_t * tb_information = (tb_info_t *) avl_find(tb_avl_root, &tmp); 	
	if(tb_information == NULL)
	{
		tb_information = malloc(sizeof(tb_info_t));
		if(tb_information == NULL)
		{
			return NULL;
		}
		tb_information->base_address = tb->vaddr;
		tb_information->instruction_count = tb->n;
		tb_information->assembler = decode_assembler(tb);
		tb_information->num_of_exec = 0;
		tb_information->size = calculate_bytesize_instructions(tb);
		tb_information->next = tb_info_list;
		tb_info_list = tb_information;
		g_string_append(out, "Not Found\n");
		if( avl_insert(tb_avl_root, tb_information) != NULL)
		{
			qemu_plugin_outs("[ERROR]: Something went wrong in avl insert");
			return NULL;
		}
		else
		{
			if(avl_find(tb_avl_root, &tmp) != tb_information)
			{
				qemu_plugin_outs("[ERROR]: Content changed!");
				return NULL;
			}
		}
		g_string_append(out, "[TB Info]: Done insertion into avl\n");
	}
	else
	{
		g_string_append(out, "Found\n");
	}
	qemu_plugin_outs(out->str);
	return tb_information;
}

/**
 * decode_assembler()
 *
 * build string that is later provided to python. !! is the replacement for \n, as this would directly affect decoding.
 * 
 * tb: tb struct, that contains the information needed to get the assembler for the instructions inside the translation block.
 *
 * return: gstring object, that contains the assembly instructions. The object needs to be deleted by the function that called this function
 */
GString* decode_assembler(struct qemu_plugin_tb *tb)
{
	GString* out = g_string_new("");

	for(int i = 0; i < tb->n; i++)
	{
		struct qemu_plugin_insn * insn = qemu_plugin_tb_get_insn(tb, i);
		g_string_append_printf(out, "[ %8lx ]: %s !!", insn->vaddr, qemu_plugin_insn_disas(insn));
	}
	return out;
}

/*
 * calculate_bytesize_instructions
 *
 * Function to calculate size of TB. It uses the information of the TB and the last insn to determine the byte size of the instructions inside the translation block
 */
size_t calculate_bytesize_instructions(struct qemu_plugin_tb *tb)
{
	struct qemu_plugin_insn * insn_first = qemu_plugin_tb_get_insn(tb, 0);
	struct qemu_plugin_insn * insn_last = qemu_plugin_tb_get_insn(tb, tb->n -1);
	uint64_t size = (insn_last->vaddr - insn_first->vaddr) + insn_last->data->len;
	return (size_t) size;
}
