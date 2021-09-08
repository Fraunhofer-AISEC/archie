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
 *   This file contains all functions needed to collect register data and send
 *   it over the data pipe
 */
#include "registerdump.h"


typedef struct registerdump_t registerdump_t;
typedef struct registerdump_t
{
	uint64_t pc;
	uint64_t tbcount;
	registerdump_t *next;
	uint64_t regs[];
} registerdump_t;

registerdump_t *first_registerdump;
int arch;

/**
 * readout_arm_registers
 *
 * readout arm registers from QEMU.
 *
 * @params current the current registerdump_t struct. It fills the regs part
 */
void readout_arm_registers(registerdump_t * current);


/**
 * readout_riscv_registers
 *
 * readout riscv registers from QEMU.
 *
 * @params current the current registerdump_t struct. It fills the regs part
 */
void readout_riscv_registers(registerdump_t * current);

/**
 * read_arm_registers
 *
 * write registers to data pipe
 */
void read_arm_registers(void);

void read_riscv_registers(void);

void init_register_module(int architecture)
{
	first_registerdump = NULL;
	arch = architecture; 
}

void delete_register_module(void)
{
	registerdump_t* current;
	while(first_registerdump != NULL)
	{
		current = first_registerdump;
		first_registerdump = first_registerdump->next;
		free(current);
	}
}

int add_new_registerdump(uint64_t tbcount)
{
	registerdump_t* current = NULL;
	if(arch == ARM)
	{
		current = malloc(sizeof(registerdump_t) + sizeof(uint64_t[17]) );
		readout_arm_registers( current);
		current->pc = current->regs[15];
	}
	if(arch == RISCV)
	{
		current = malloc(sizeof(registerdump_t) + sizeof(uint64_t[33]));
		readout_riscv_registers(current);
		current->pc = current->regs[32];
	}
	current->next = first_registerdump;
	current->tbcount = tbcount;
	first_registerdump = current;
	return 0;
}

void readout_riscv_registers(registerdump_t * current)
{
	//read all registers (32 is PC)
	for(int i = 0; i < 33; i++)
	{
		current->regs[i] = 0;
		current->regs[i] = read_reg(i);
	}
}

void readout_arm_registers(registerdump_t * current)
{
	// read r0 - r15
	for(int i = 0; i < 16; i++)
	{
		current->regs[i] = 0;
		current->regs[i] = read_reg(i); 
	}
	// read XPSR
	current->regs[16] = read_reg(25);
}


void read_register_module(void)
{
	if(arch == ARM)
	{
		qemu_plugin_outs("[DEBUG]: start reading arm registerdumps\n");
		read_arm_registers();
		return;
	}
	if(arch == RISCV)
	{
		qemu_plugin_outs("[DEBUG]: start reading riscv registerdump\n");
		read_riscv_registers();
		return;
	}
	qemu_plugin_outs("[ERROR]: [CRITICAL]: Unknown Architecture for register module");
}

void read_riscv_registers(void)
{
	g_autoptr(GString) out = g_string_new("");
	g_string_printf(out, "$$$[RiscV Registers]\n");
	plugin_write_to_data_pipe(out->str, out->len);
	registerdump_t* current = first_registerdump;
	while(current != NULL)
	{
		g_string_printf(out, "$$ %lx | %lx ", current->pc, current->tbcount);
		for(int i = 0; i < 33; i++)
		{
			g_string_printf(out, "| %lx ", current->regs[i]);
		}
		g_string_append(out, "\n");
		plugin_write_to_data_pipe(out->str, out->len);
		current = current->next;
	}
}

void read_arm_registers(void)
{
	g_autoptr(GString) out = g_string_new("");
	g_string_printf(out, "$$$[Arm Registers]\n");
	plugin_write_to_data_pipe(out->str, out->len);
	registerdump_t* current = first_registerdump;
	while(current != NULL)
	{
		g_string_printf(out, "$$ %li | %li ", current->pc, current->tbcount);
		for(int i = 0; i < 17; i++)
		{
			g_string_append_printf(out, "| %li ", current->regs[i]);
		}
		g_string_append(out, "\n");
		plugin_write_to_data_pipe(out->str, out->len);
		current = current->next;
	}
}
