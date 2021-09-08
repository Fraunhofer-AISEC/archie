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
 *   This file contains all functions needed to inject a fault in qemu
 */

#include "fault_injection.h"
#include "faultplugin.h"
#include "registerdump.h"
#include "tb_faulted_collection.h"
#include "faultdata.h"

#include <qemu/qemu-plugin.h>
//#include <glib.h>

/**
 * inject_fault
 *
 * At this point the fault needs to be injected. This is the function to select the right model and call the injection function
 *
 * current: Struct address containing the fault information needed
 */
void inject_fault(fault_list_t * current)
{
	g_autoptr(GString) out = g_string_new("");
	if( current != NULL)
	{
		if(current->fault.type == INSTRUCTION)
		{
			insert_memorydump_config(current->fault.address, 16);
			read_specific_memoryregion(current->fault.address);
			tb_faulted_register(current->fault.address);
			qemu_plugin_outs("[Fault] Inject instruction fault\n");
			inject_memory_fault( current);
			plugin_flush_tb();
			read_specific_memoryregion(current->fault.address);
			qemu_plugin_outs("Flushed tb\n");
		}
		if(current->fault.type == DATA)
		{
			insert_memorydump_config(current->fault.address, 16);
			read_specific_memoryregion(current->fault.address);
			qemu_plugin_outs("[Fault] Inject memory fault\n");
			inject_memory_fault( current);
			plugin_flush_tb();
			read_specific_memoryregion(current->fault.address);
			qemu_plugin_outs("Flushed tb\n");
		}
		if(current->fault.type == REGISTER)
		{
			qemu_plugin_outs("[Fault] Inject register fault\n");
			inject_register_fault( current);
			//TODO
		}
		invalidate_fault_trigger_address(current->fault.trigger.trignum);
		rem_singlestep_req();
		if(current->fault.lifetime != 0)
		{
				current->fault.trigger.trignum = register_live_faults_callback(current);
		}
		add_new_registerdump(current->fault.trigger.trignum);
	}
}

/**
 * reverse_fault
 *
 * Reverse the fault injected
 *
 * current: fault description pointer 
 */
void reverse_fault(fault_list_t * current)
{
	g_autoptr(GString) out = g_string_new("");
	if(current != NULL)
	{
		if(current->fault.type == INSTRUCTION)
		{
			qemu_plugin_outs("[Fault] Reverse instruction fault\n");
			process_reverse_fault(current->fault.address, current->fault.mask, current->fault.restoremask);
			plugin_flush_tb();
			read_specific_memoryregion(current->fault.address);
			qemu_plugin_outs("Flushed tb\n");
		}
		if(current->fault.type == DATA)
		{
			qemu_plugin_outs("[Fault] Reverse memory fault\n");
			process_reverse_fault(current->fault.address, current->fault.mask, current->fault.restoremask);
			plugin_flush_tb();
			read_specific_memoryregion(current->fault.address);
			qemu_plugin_outs("Flushed tb\n");
		}
		if(current->fault.type == REGISTER)
		{
			qemu_plugin_outs("[Fault] Reverse register fault\n");
			reverse_register_fault( current);
		}
	}
	rem_singlestep_req();
	add_new_registerdump(current->fault.trigger.trignum);
}

/**
 * inject_register_fault
 *
 * Inject fault into registers. Reads the current string and determines the register that is attacked, loads it and performs the fault required
 */
void inject_register_fault(fault_list_t * current)
{
	g_autoptr(GString) out = g_string_new("");
	//TODO: Remove if not needed
/*	if(current->fault.address > 14)
	{
		qemu_plugin_outs("[ERROR] Register not valid\n");
		return;
	}*/
	uint64_t reg = read_reg(current->fault.address);
	uint64_t mask = 0;
	for(int i = 0; i < 8; i++)
	{
		current->fault.restoremask[i] = (reg >> 8*i) & current->fault.mask[i];
		mask += (current->fault.mask[i] << 8*i);
	}
	g_string_printf(out," Changing registers %li from %08lx", current->fault.address, reg);
	switch(current->fault.model)
	{
		case SET0:
			reg = reg & ~(mask);
			break;
		case SET1:
			reg = reg | mask;
			break;
		case TOGGLE:
			reg = reg ^ mask;
			break;
		default:
			g_string_append_printf(out, "Fault model is wrong %li", current->fault.model);
			break;
	}
	write_reg(current->fault.address, reg);
	g_string_append_printf(out, " to %08lx, with mask %08lx\n", reg, mask);
	qemu_plugin_outs(out->str);
}

void reverse_register_fault(fault_list_t * current)
{
	g_autoptr(GString) out = g_string_new("");
	uint64_t reg = read_reg(current->fault.address);

	g_string_printf(out, " Change register %li back from %08lx", current->fault.address, reg);
	for(int i = 0; i < 8; i++)
	{
		reg = reg & ~((uint64_t)current->fault.mask[i] << 8*i); // clear manipulated bits
		reg = reg | ((uint64_t) current->fault.restoremask[i] << 8*i); // restore manipulated bits
	}
	write_reg(current->fault.address, reg);
	g_string_printf(out, " to %08lx\n", reg);
	qemu_plugin_outs(out->str);
}

/**
 * inject_memory_fault
 *
 * injects fault into memory regions
 * Reads current struct to determine the location, model, and mask of fault.
 * Then performs the fault injection
 *
 * current: Struct address containing the fault information
 */
void inject_memory_fault(fault_list_t * current)
{
	g_autoptr(GString) out = g_string_new("");
	switch(current->fault.model)
	{
		case SET0:
			g_string_append_printf(out, "Set 0 fault to address %lx\n", current->fault.address);
			process_set0_memory(current->fault.address, current->fault.mask, current->fault.restoremask);
			break;
		case SET1:
			g_string_append_printf(out, "Set 1 fault to address %lx\n", current->fault.address);
			process_set1_memory(current->fault.address, current->fault.mask, current->fault.restoremask);
			break;
		case TOGGLE:
			g_string_append_printf(out, "Toggle fault to address %lx\n", current->fault.address);
			process_toggle_memory(current->fault.address, current->fault.mask, current->fault.restoremask);
			break;
		default:
			break;
	}
	qemu_plugin_outs(out->str);

}

/**
 * process_set1_memory
 *
 * Read memory, then set bits according to mask, then write memory back
 * 
 * address: base address of lowest byte
 * mask: mask containing which bits need to be flipped to 1
 */
void process_set1_memory(uint64_t address, uint8_t  mask[], uint8_t restoremask[])
{
	uint8_t value[16];
	int ret;
	ret = plugin_rw_memory_cpu( address, value, 16, 0);
	for(int i = 0; i < 16; i++)
	{
		restoremask[i] = value[i] & mask[i]; // generate restore mask
		value[i] = value[i] | mask[i]; // inject fault
	}
	ret += plugin_rw_memory_cpu( address, value, 16, 1);
	if (ret < 0)
	{
		qemu_plugin_outs("[ERROR]: Something went wrong in read/write to cpu in process_set1_memory\n");
	}
}

/**
 * process_reverse_fault
 *
 * Read memory, then apply restore mask according to fault mask, then write memory back
 *
 * address: base address of fault
 * mask: location mask of bits set to 0 for reverse
 */
void process_reverse_fault(uint64_t address, uint8_t mask[], uint8_t restoremask[])
{
	uint8_t value[16];
	int ret;
	ret = plugin_rw_memory_cpu( address, value, 16, 0);
	for(int i = 0; i < 16; i++)
	{
		value[i] = value[i] & ~(mask[i]); // clear value in mask position
		value[i] = value[i] | restoremask[i]; // insert restore mask to restore positions
	}
	ret += plugin_rw_memory_cpu( address, value, 16, 1);
	qemu_plugin_outs("[Fault]: Reverse fault!");
	if (ret < 0)
	{
		qemu_plugin_outs("[ERROR]: Something went wrong in read/write to cpu in process_reverse_fault\n");
	}
}

/**
 * process_set0_memory
 *
 * Read memory, then clear bits according to mask, then write memory back
 *
 * address: base address of fault
 * mask: location mask of bits set to 0 
 */
void process_set0_memory(uint64_t address, uint8_t  mask[], uint8_t restoremask[])
{
	uint8_t value[16];
	int ret;
	ret = plugin_rw_memory_cpu( address, value, 16, 0);
	for(int i = 0; i < 16; i++)
	{
		restoremask[i] = value[i] & mask[i]; // generate restore mask
		value[i] = value[i] & ~(mask[i]); // inject fault
	}
	ret += plugin_rw_memory_cpu( address, value, 16, 1);
	if (ret < 0)
	{
		qemu_plugin_outs("[ERROR]: Something went wrong in read/write to cpu in process_set0_memory\n");
	}
}



/**
 * process_toggle_memory
 *
 * Read memory, then toggle bits according to mask, then write memory back
 *
 * address: base address of fault
 * mask: location mask of bits to be toggled
 */
void process_toggle_memory(uint64_t address, uint8_t  mask[], uint8_t restoremask[])
{
	uint8_t value[16];
	int ret;
	ret = plugin_rw_memory_cpu( address , value, 16, 0);
	for(int i = 0; i < 16; i++)
	{
		restoremask[i] = value[i] & mask[i]; // generate restore mask
		value[i] = value[i] ^ mask[i]; // inject fault
	}
	ret += plugin_rw_memory_cpu( address, value, 16, 1);
	if (ret < 0)
	{
		qemu_plugin_outs("[ERROR]: Something went wrong in read/write to cpu in process_toggle_memory\n");
	}
}
