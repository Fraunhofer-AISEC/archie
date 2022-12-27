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
 *   This part of the plugin manages the memory data dumps collected and how to 
 *   send them to the data pipe
 */

#include "faultdata.h"


typedef struct
{
	uint64_t address;
	uint64_t len;
	uint64_t num_dumps;
	uint64_t used_dumps;
	uint8_t **buf;
}memorydump_t;

memorydump_t **memdump;
uint64_t num_memdump;
uint64_t used_memdump;


void init_memory_module(void)
{
	memdump = NULL;
	num_memdump = 0;
	used_memdump = 0;
}

int memory_module_configured(void)
{
	if(memdump == NULL)
	{
		return 0;
	}
	return 1;
}
// Initialise vector with empty elements
int init_memory(int number_of_regions)
{
	num_memdump = number_of_regions;
	used_memdump = 0;
	// Initialise vector
	memdump = NULL;
	memdump = malloc(sizeof(memorydump_t *) * number_of_regions);
	if(memdump == NULL)
	{
		return -1;
	}
	// Clear pointers with NULL
	for(int i = 0; i < number_of_regions; i++)
	{
		*(memdump + i) = NULL;
	}
	// Fill vector with struct
	for(int i = 0; i < number_of_regions; i++)
	{
		memorydump_t *tmp = malloc(sizeof(memorydump_t));
		if(tmp == NULL)
		{
			goto Abort;
		}
		tmp->address = 0;
		tmp->len = 0;
		tmp->num_dumps = 0;
		tmp->used_dumps = 0;
		tmp->buf = NULL;
		*(memdump + i) = tmp;
	}
	return 0;
  Abort:
	delete_memory_dump();
	return -1;
}

void delete_memory_dump(void)
{
	if(memdump != NULL)
	{
		for(int i = 0; i < num_memdump; i++)
		{
			if(*(memdump + i) != NULL)
			{
				memorydump_t *tmp = *(memdump + i);
				if(tmp->buf != NULL)
				{
					for(int j = 0; j < tmp->num_dumps; j++)
					{
						free(*((tmp->buf) + j));
					}
					free(tmp->buf);
				}
				free(*(memdump + i));
			}
		}
		free(memdump);
	}
	memdump = NULL;
}
// Fill in one vector element
int insert_memorydump_config(uint64_t baseaddress, uint64_t len)
{	
	g_autoptr(GString) out = g_string_new("");
	if(memdump == NULL)
	{
		qemu_plugin_outs("[ERROR]: Memorydump: Not initialised!\n");
		return -1;
	}
	if(num_memdump == used_memdump)
	{
		qemu_plugin_outs("[DEBUG]: memorydump: Increase memory dump vector.........");
		memorydump_t **buf = malloc(sizeof(memorydump_t *) * (num_memdump + 1));
		if(buf == NULL)
		{
			qemu_plugin_outs("failed\n[ERROR]: Could not increase memorydump vector! Malloc failed\n");
			return -1;
		}
		for(int i = 0; i < num_memdump; i++)
		{
			*(buf + i) = *(memdump + i);
		}
		free(memdump);
		memdump = NULL;
		memdump = buf;
		*(memdump + num_memdump) = malloc(sizeof(memorydump_t));
		memorydump_t *tmp = *(memdump + num_memdump);
		tmp->buf = NULL;
		tmp->address = 0;
		tmp->len = 0;
		tmp->num_dumps = 0;
		tmp->used_dumps = 0;
		num_memdump++;
		qemu_plugin_outs("done\n");
	}
	memorydump_t *tmp = *(memdump + used_memdump);
	used_memdump++;
	tmp->address = baseaddress;
	tmp->len = len;
	tmp->num_dumps = 1;
	tmp->buf = malloc(sizeof(uint8_t*) * tmp->num_dumps);
	if(tmp->buf == NULL)
	{
		qemu_plugin_outs("[ERROR]: Could not allocate memory vor buffer!\n");
		tmp->address = 0;
		return -1;
	}
	for(int j = 0; j < tmp->num_dumps; j++)
	{
		*(tmp->buf + j)  = malloc(sizeof(uint8_t) * len);
		for( int i = 0; i < len; i++)
		{
			*(*(tmp->buf + j) + i) = 0;
		}
	}
	g_string_printf(out,"[DEBUG]: Memorydump: config was address %08lx len %li\n", baseaddress, len);
	qemu_plugin_outs(out->str);
	return 1;
}

void read_all_memory(void)
{
	for(int i = 0; i < used_memdump; i++)
	{
		read_memoryregion( i);
	}
}

void read_specific_memoryregion(uint64_t baseaddress)
{
	for(int i = 0; i < used_memdump; i++)
	{
		memorydump_t *current = *(memdump + i);
		if(current->address == baseaddress)
		{
			read_memoryregion(i);
		}
	}
}

int read_memoryregion(uint64_t memorydump_position)
{
	g_autoptr(GString) out = g_string_new("");
	uint64_t ret;
	memorydump_t *current = *(memdump + memorydump_position);
	if(current->num_dumps == current->used_dumps)
	{
		qemu_plugin_outs("[DEBUG]: Memorydump: Allocate new buffer......");
		//We need to add a new memory dump arrea
		uint8_t **buf = malloc(sizeof(uint8_t *) * (current->num_dumps + 1));
		if(buf == NULL)
		{
			qemu_plugin_outs("failed\n[ERROR]: Could not create new buffer vector for memory region! Malloc error\n");
			return -1;
		}
		for(int i = 0; i < current->num_dumps; i++)
		{
			*(buf + i) = *(current->buf + i);
		}
		*(buf + current->num_dumps) = malloc(sizeof(uint8_t) * current->len);
		if(*(buf + current->num_dumps) == NULL)
		{
			qemu_plugin_outs("failed\n[ERROR]: Could not create buffer! Malloc Error\n");
			free(buf);
			return -1;
		}
		for( int i = 0; i < current->len; i++)
		{
			*(*(buf + current->num_dumps) + i) = 0;
		}
		free(current->buf);
		current->buf = buf;
		current->num_dumps++;
		qemu_plugin_outs("done\n");
	}
	qemu_plugin_outs("[DEBUG]: start reading memory memdump");
	ret = qemu_plugin_rw_memory_cpu(current->address, *(current->buf + current->used_dumps), current->len, 0);
	current->used_dumps++;
	qemu_plugin_outs("..... done\n");
	return ret;
}

void readout_memorydump_dump(uint64_t memorydump_position, uint64_t dump_pos)
{
	g_autoptr(GString) out = g_string_new("");
	memorydump_t *current = *(memdump + memorydump_position);
	uint8_t *dump = *(current->buf + dump_pos);
	int i = 0;
	while( i < current->len)
	{
		if(i + 8 < current->len)
		{
			g_string_printf(out, "$$ B: 0x%02hhx 0x%02hhx 0x%02hhx 0x%02hhx 0x%02hhx 0x%02hhx 0x%02hhx 0x%02hhx\n", *(dump + i + 0), *(dump + i + 1), *(dump + i + 2), *(dump + i + 3), *(dump + i + 4), *(dump + i + 5), *(dump + i + 6), *(dump + i + 7));
			i = i+8;
		}
		else
		{
			if(i % 8 == 0)
			{
				g_string_printf(out, "$$ B: 0x%02hhx", *(dump + i));
			}
			else
			{
				g_string_printf(out, " 0x%02hhx", *(dump + i));
			}
			if((i % 8 == 7) || (i == current->len - 1))
			{
				g_string_append(out, "\n");
			}
			i++;
		}
		plugin_write_to_data_pipe(out->str, out->len);

	}
}

void readout_memorydump(uint64_t memorydump_position)
{
	g_autoptr(GString) out = g_string_new("");
	memorydump_t *current = *(memdump + memorydump_position);
	g_string_printf(out, "$$[memorydump]: %li | %li | %li \n",current->address, current->len, current->used_dumps);
	for(int i = 0; i < current->used_dumps; i++)
	{
		g_string_append_printf(out, "$$[Dump start]\n");
		plugin_write_to_data_pipe(out->str, out->len);
		readout_memorydump_dump(memorydump_position, i);
		g_string_printf(out, "$$[Dump end]\n");
	}
	g_string_append(out, "$$[memorydump end]\n");
	plugin_write_to_data_pipe(out->str,  out->len);
}


void readout_all_memorydump(void)
{
	g_autoptr(GString) out = g_string_new("");
	g_string_printf(out, "$$$[Memdump] \n");
	plugin_write_to_data_pipe(out->str, out->len);
	for(int i = 0; i < used_memdump; i++)
	{
		readout_memorydump(i);
	}
}
