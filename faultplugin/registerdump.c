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
 * read_registers
 *
 * update protobuf message with register information
 *
 * returns 0 on success, -1 on fail
 */
int read_registers(Archie__RegisterInfo* protobuf_reg_info);

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
		current = malloc(sizeof(registerdump_t) + sizeof(uint64_t[N_ARM_REGISTERS + 1]) );
		if(current == NULL)
		{
			qemu_plugin_outs("failed\n[ERROR]: Malloc error for registerdump_t");
			return -1;
		}
		readout_arm_registers(current);
		current->pc = current->regs[15];
	}
	if(arch == RISCV)
	{
		current = malloc(sizeof(registerdump_t) + sizeof(uint64_t[N_RISCV_REGISTERS + 1]));
		if(current == NULL)
		{
			qemu_plugin_outs("failed\n[ERROR]: Malloc error for registerdump_t");
			return -1;
		}
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
	for(int i = 0; i < N_RISCV_REGISTERS + 1; i++)
	{
		current->regs[i] = 0;
		current->regs[i] = qemu_plugin_read_reg(i);
	}
}

void readout_arm_registers(registerdump_t * current)
{
	// read r0 - r15
	for(int i = 0; i < N_ARM_REGISTERS; i++)
	{
		current->regs[i] = 0;
		current->regs[i] = qemu_plugin_read_reg(i);
	}
	// read XPSR
	current->regs[16] = qemu_plugin_read_reg(25);
}

size_t get_register_dump_count(void)
{
	size_t size = 0;
	registerdump_t* current = first_registerdump;
	while(current != NULL)
	{
		size++;
		current = current->next;
	}

	return size;
}

int read_registers(Archie__RegisterInfo* protobuf_reg_info)
{
	// Allocate memory for register info on protobuf message
	size_t n_register_dumps = get_register_dump_count();
	Archie__RegisterDump** protobuf_reg_dump_list;
	protobuf_reg_dump_list = malloc(sizeof(Archie__RegisterDump*) * n_register_dumps);
	if(protobuf_reg_dump_list == NULL)
	{
		qemu_plugin_outs("[ERROR]: Malloc for Archie__RegisterDump array failed\n");
		return -1;
	}

	uint64_t n_registers = 0;
	if(arch == ARM)
	{
		qemu_plugin_outs("[DEBUG]: start reading arm registerdumps\n");
		protobuf_reg_info->arch_type = ARM;

		// Extra register carries the XPSR register
		n_registers = N_ARM_REGISTERS + 1;
	}
	else if(arch == RISCV)
	{
		qemu_plugin_outs("[DEBUG]: start reading riscv registerdumps\n");
		protobuf_reg_info->arch_type = RISCV;

		// Extra register carries the program counter
		n_registers = N_RISCV_REGISTERS + 1;
	}
	else
	{
		qemu_plugin_outs("[ERROR]: [CRITICAL]: Unknown Architecture for register module");
		return -1;
	}

	registerdump_t* current = first_registerdump;
	int counter = 0;
	while(current != NULL)
	{
		protobuf_reg_dump_list[counter] = malloc(sizeof(Archie__RegisterDump));
		if(protobuf_reg_dump_list[counter] == NULL)
		{
			qemu_plugin_outs("[ERROR]: Malloc for Archie__RegisterDump failed\n");
			return -1;
		}

		archie__register_dump__init(protobuf_reg_dump_list[counter]);

		// Copy register values into current protobuf register info dump
		protobuf_reg_dump_list[counter]->n_register_values = n_registers;
		protobuf_reg_dump_list[counter]->register_values = malloc(sizeof(uint64_t) * n_registers);
		if(protobuf_reg_dump_list[counter]->register_values == NULL)
		{
			qemu_plugin_outs("[ERROR]: Malloc failed\n");
			return -1;
		}
		for(int i = 0; i < n_registers; i++)
		{
			protobuf_reg_dump_list[counter]->register_values[i] = current->regs[i];
		}

		protobuf_reg_dump_list[counter]->pc = current->pc;
		protobuf_reg_dump_list[counter]->tb_count = current->tbcount;

		counter++;
		current = current->next;
	}

	protobuf_reg_info->n_register_dumps = n_register_dumps;
	protobuf_reg_info->register_dumps = protobuf_reg_dump_list;

	return 0;
}

int read_register_module(Archie__Data* msg)
{
	// Allocate and init register info of protobuf data messages
	Archie__RegisterInfo* reg = malloc(sizeof(Archie__RegisterInfo));
	if(reg == NULL)
	{
		qemu_plugin_outs("[ERROR]: Malloc for Archie__RegisterInfo failed\n");
		return -1;
	}
	archie__register_info__init(reg);

	if(read_registers(reg) != 0)
	{
		qemu_plugin_outs("[ERROR]: read_registers() failed\n");
		return -1;
	}

	msg->register_info = reg;
	return 0;
}
