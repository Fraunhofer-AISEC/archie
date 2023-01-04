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
 *   This is the main part of the plugin. It contains all major callback
 *   functions
 */

#include <assert.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <stdio.h>
#include <sys/types.h>

#include "qemu/osdep.h"
#include <qemu/plugin.h>
#include <qemu/qemu-plugin.h>

#include "hw/core/cpu.h"

#include "lib/avl.h"

#include "faultdata.h"
#include "registerdump.h"
#include "singlestep.h"
#include "fault_list.h"
#include "fault_injection.h"
#include "tb_info_data_collection.h"
#include "tb_exec_data_collection.h"
#include "tb_faulted_collection.h"

#include "fault.pb-c.h"
#include "control.pb-c.h"

//DEBUG
#include <errno.h>
#include <string.h>

//#define DEBUG_QEMU
#ifndef DEBUG_QEMU
#define FIFO_READ O_RDONLY
#define FIFO_WRITE O_WRONLY
#else
#define FIFO_READ O_RDONLY | O_NONBLOCK
#define FIFO_WRITE O_WRONLY | O_NONBLOCK
#endif



typedef struct
{
	int control;
	int config;
	int data;
} fifos_t;


/* Global data structures */

fifos_t * pipes;


uint64_t *	fault_trigger_addresses;
fault_list_t  **live_faults;
int	fault_number;
int	live_faults_number;
int 	first_tb;

int tb_counter;
int tb_counter_max;

/* Start point struct (using fault struct) */
fault_trigger_t start_point;

/* End point struct (using fault struct) */
struct end_point_t
{
	fault_trigger_t location;
	struct end_point_t *next;
};
struct end_point_t *end_point = NULL;


int tb_info_enabled;


int tb_exec_order_enabled;
int tb_exec_order_ring_buffer;


/* data structures for memory access */
/* avl tree is used for insn address */
typedef struct mem_info_t mem_info_t;
typedef struct mem_info_t
{
	uint64_t ins_address;
	uint64_t size;
	uint64_t memmory_address;
	char	 direction;
	uint64_t counter;
	mem_info_t *next;
}mem_info_t;

mem_info_t *mem_info_list;
int mem_info_list_enabled;

struct avl_table *mem_avl_root;

static void free_end_point_list(struct end_point_t *list)
{
	struct end_point_t *cur = list, *tmp;

	while (cur != NULL)
	{
		tmp = cur->next;
		free(cur);
		cur = tmp;
	}
}

/**
 * mem_info_free()
 *
 * This function deletes all mem info elements in the global linked list mem_info_list.
 * Furthermore it deletes the associated avl tree
 */
void mem_info_free()
{
	mem_info_t *item;
	while(mem_info_list != NULL)
	{
		item = mem_info_list;
		mem_info_list = mem_info_list->next;
		free(item);
	}
	avl_destroy(mem_avl_root, NULL);
	mem_avl_root = NULL;
}

/**
 * mem_comparison_func()
 *
 * This function compares two elements of mem_info_t. It returns which element is larger
 * needed by gnuavl lib. Please see the gnuavl lib for more information
 *
 * tbl_a: Element a to be compared
 * tbl_b: Element b to be compared
 * tbl_param: Not used. Can be used to give additional information to comparison function
 *
 * return: if negative, a is larger. If positive, b is larger. If zero, a = b
 */
int mem_comparison_func(const void *tbl_a, const void *tbl_b, void *tbl_param)
{
	const mem_info_t *mem_a = tbl_a;
	const mem_info_t *mem_b = tbl_b;
	// Etchcase, memory_address is not the same as the element, but ins is the same
	if(mem_a->ins_address == mem_b->ins_address)
	{
		if (mem_a->memmory_address != mem_b->memmory_address)
		{
			return  mem_a->memmory_address -  mem_b->memmory_address;
		}
	}
	return mem_a->ins_address - mem_b->ins_address;
}

/* Other potential useful functions needed for gnuavl */
// void tbl_item_func(void *tbl_item, void *tbl_param)
// void * tbl_copy_func(void *tbl_item, void *tbl_param);
// void tbl_destry_funv(void *tbl_itme, void *tbl_param);


/* QEMU plugin version control. This is needed to specify for which qemu api version this plugin was build.
 * Qemu will block, if version is to old to handle incompatibility inside the api
 */
QEMU_PLUGIN_EXPORT int qemu_plugin_version = QEMU_PLUGIN_VERSION;


/**
 * memaccess_data_cb
 *
 * This is the callback, that is called for memaccess by the target cpu.
 * It will search the avl tree, if this memory access is already inside the avl tree. If not it creates the element
 * and inserts it into the tree. Then it increments the counter
 *
 * vcpu_index: Index of vcpu that made memory access
 * info: API object needed to query for additional information inside the api
 * vddr: Address in memory of the memory operation
 * userdata: Data provided by user. In this case it is the address of the instruction that triggered the memory operation
 */
static void memaccess_data_cb(unsigned int vcpu_index, qemu_plugin_meminfo_t info, uint64_t vddr, void *userdata)
{
	mem_info_t tmp;
	tmp.ins_address = (uint64_t)(userdata);
	tmp.memmory_address = vddr;
	mem_info_t *mem_access = avl_find(mem_avl_root,&tmp);
	if(mem_access == NULL)
	{
		mem_access = malloc(sizeof(mem_info_t));
		mem_access->ins_address = (uint64_t) userdata;
		mem_access->size = qemu_plugin_mem_size_shift(info);
		mem_access->memmory_address = vddr;
		mem_access->direction = qemu_plugin_mem_is_store(info);
		mem_access->counter = 0;
		avl_insert(mem_avl_root, mem_access);
		mem_access->next = mem_info_list;
		mem_info_list = mem_access;
	}
	mem_access->counter++;

}

/**
 *
 * parse_args
 *
 * Read in command line parameters. These are the control, config and data pipe paths.
 * They will be opened here. Commands are send over the control pipe.
 * Configuration for faults is send over the config pipe
 * Data is send from this module to the outside over the data pipe
 *
 * argv: contains the different path strings
 * argc: number of strings
 *
 * return: Return -1 if something went wrong
 *
 * */

int parse_args(int argc, char **argv, GString *out)
{
	g_string_append_printf(out, "[Info]: Starting argparsing\n");
	if(argc != 3)
	{
		g_string_append_printf(out, "[ERROR]: Not the right amount of arguments! %i\n", argc);
		return -1;
	}

	for (int i = 0; i < argc; i++)
	{
		char *opt = argv[i];
		if (g_str_has_prefix(opt, "control="))
		{
			char *p = opt + 8;
			g_string_append_printf(out, "[Info]: Start readout of control fifo %s\n", p);
			mkfifo(p, 0660);
			pipes->control = open(p, FIFO_READ);
		}
		else if (g_str_has_prefix(opt, "config="))
		{
			char *p = opt + 7;
			g_string_append_printf(out, "[Info]: Start readout of config fifo %s\n", p);
			mkfifo(p, 0660);
			pipes->config = open(p, FIFO_READ);
		}
		else if (g_str_has_prefix(opt, "data="))
		{
			char *p = opt + 5;
			g_string_append_printf(out, "[Info]: Start readout of data fifo %s\n", p);
			pipes->data = open(p, FIFO_WRITE);
		}
		else
		{
			g_string_append_printf(out, "[ERROR] Unknown option: %s\n", opt);
			return -1;
		}
	}

	if (pipes->control == -1 || pipes->config == -1 || pipes->data == -1)
	{
		g_string_append(out, "[ERROR]: Could not open all FIFOs!\n");
		return -1;
	}

	return 0;
}

/**
 * char_to_uint64()
 *
 * Converts the characters of string provided by c from ascii hex to ascii
 *
 * c: pointer to string
 * size_c: length of string
 *
 * return number converted
 */
uint64_t char_to_uint64(char *c, int size_c)
{
	g_autoptr(GString) out = g_string_new("");
	uint64_t tmp = 0;
	int i = 0;
	g_string_printf(out, "[Info]: This is the conversion function: ");
	for(i = 0; i < size_c; i++)
	{
		g_string_append_printf(out, " 0x%x",(char) *(c + i));
		tmp = tmp << 8;
		tmp += 0xff & (char) *(c + i);
	}
	g_string_append(out, "\n");
	qemu_plugin_outs(out->str);
	return tmp;
}


/**
 * print_assembler
 *
 * print assembler to console from translation block
 */
void print_assembler(struct qemu_plugin_tb *tb)
{
	g_autoptr(GString) out = g_string_new("");
	g_string_printf(out, "\n");

	for(int i = 0; i < tb->n; i++)
	{
		struct qemu_plugin_insn *insn = qemu_plugin_tb_get_insn(tb, i);
		g_string_append_printf(out, "%8lx ", insn->vaddr);
		g_string_append_printf(out, "%s\n", qemu_plugin_insn_disas( insn));
	}
	qemu_plugin_outs(out->str);
}



int qemu_setup_config_contains_char(GString* out, char c);
void qemu_setup_config_find_char(GString* out, char c);

void qemu_setup_config_find_char(GString* out, char c)
{
	int i = qemu_setup_config_contains_char(out, c);
	if(i == -1)
		return;
	i++;
	g_string_erase(out, 0, i++);
}

int qemu_setup_config_contains_char(GString* out, char c)
{
	int i = 0;
	char *s = out->str;
	
	while(*s != c)
	{
		if(*s == '\0')
			return -1;
		i++;
		s++;
	}
	return i;
}


int readout_pipe(size_t max, uint8_t *out, enum Pipe_type type);

/**
 *
 * qemu_setup_config
 *
 * This function reads the config from the config pipe. It will read all fault configurations.
 *
 */

int qemu_setup_config()
{
	size_t message_buff_size = 1024;

	uint8_t* conf = (uint8_t*) malloc(sizeof(char) * message_buff_size);
	if(conf == NULL){
		qemu_plugin_outs("[DEBUG]: Error allocating memory for incoming config message\n");
		return -1;
	}

	g_autoptr(GString) out = g_string_new("");
	g_string_printf(out, "[Info]: Start readout of FIFO\n");
	
	int msg_size = readout_pipe(message_buff_size, conf, CONFIG_PIPE);
	if(msg_size <= 0){
		qemu_plugin_outs("[DEBUG]: No message on FIFO\n");
		return -1;
	}
	
	Archie__FaultPack* fault_pack = archie__fault__pack__unpack(NULL, msg_size, conf);	
	if (fault_pack == NULL)
	{
		qemu_plugin_outs("[DEBUG]: Error unpacking the message from pipe\n");
		return -1;
	}

	size_t num_faults = fault_pack->n_faults;
	Archie__Fault* fault_array = *fault_pack->faults;

	uint8_t fault_mask[16];

	for(int i = 0; i < num_faults; ++i)
	{
		g_string_append_printf(out, "[Info]: fault number %d\n", i);
		g_string_append_printf(out, "[Info]: fault address: 0x%lx\n", fault_array[i].address);
		g_string_append_printf(out, "[Info]: fault type: 0x%lx\n", fault_array[i].type);
		g_string_append_printf(out, "[Info]: fault model: 0x%lx\n", fault_array[i].model);
		g_string_append_printf(out, "[Info]: fault lifespan: 0x%lx\n", fault_array[i].lifespan);
		g_string_append_printf(out, "[Info]: fault trigger address: 0x%lx\n", fault_array[i].trigger_address);
		g_string_append_printf(out, "[Info]: fault trigger hitcounter: 0x%lx\n", fault_array[i].trigger_hitcounter);
		g_string_append_printf(out, "[Info]: num_bytes for Overwrite: 0x%x\n", fault_array[i].num_bytes);

		for(int j = 0; j < 8; j++)
		{
			fault_mask[j] = (fault_array[i].mask_lower >> j * 8) & 0xFF;
			fault_mask[j+8] = (fault_array[i].mask_upper >> j * 8) & 0xFF;
			g_string_append_printf(out, " 0x%x", fault_mask[j]);
		}
		for(int j = 0; j < 8; j++)
		{
			g_string_append_printf(out, " 0x%x", fault_mask[j+8]);
		}

		g_string_append(out, "\n");
		g_string_append(out, "[Info]: Fault end\n");
		
		int res = add_fault(fault_array[i].address, fault_array[i].type, 
							fault_array[i].model, fault_array[i].lifespan,
							fault_mask, fault_array[i].trigger_address, 
				  			fault_array[i].trigger_hitcounter, (uint8_t) fault_array[i].num_bytes);

		
		if(res < 0){
			qemu_plugin_outs("[DEBUG]: Fault could not be added\n");
			return -1;
		}
	}
	
	free(conf);
	archie__fault__pack__free_unpacked(fault_pack, NULL);

	g_string_append(out, "[Info]: Fault pipe read done\n");
	qemu_plugin_outs(out->str);
	
	return 0;
}

/**
 * register_fault_address
 *
 * This function will fill the global fault trigger address array and fault address array
 */
int register_fault_trigger_addresses()
{
	g_autoptr(GString) out = g_string_new("");
	g_string_printf(out, "[Info]: Calculate number of faults .......");
	/* Select first element of list */
	fault_list_t * current = return_first_fault();
	int i = 0;
	/* Traverse list */
	while(current != NULL)
	{
		i++;
		current = return_next(current);
	}
	g_string_append_printf(out, "%i\n",i);
	if(i == 0)
	{
		g_string_append(out, "[ERROR]: No fault found!\n");
		qemu_plugin_outs(out->str);
		return -1;
	}
	/* Reset back to firs element */
	current = return_first_fault();
	fault_number = i;
	g_string_append_printf(out, "[DEBUG]: Fault number %i\n", fault_number);
	/* Reserve Memory for "Vector" */
	fault_trigger_addresses = malloc(sizeof(fault_trigger_addresses) * fault_number);
	live_faults = malloc(sizeof(*live_faults) * fault_number);
	if(fault_trigger_addresses == NULL || live_faults == NULL)
	{
		g_string_append_printf(out, "[ERROR]: malloc failed here in registerfaulttrigger\n");
		qemu_plugin_outs(out->str);
		return -1;
	}
	g_string_append(out, "[Info]: Start registering faults\n");
	for(int j = 0; j < i; j++)
	{
		/* Fill Vector with value */
		*(fault_trigger_addresses + j) = get_fault_trigger_address(current);
		set_fault_trigger_num(current, j);
		*(live_faults + j) = NULL;	
		g_string_append_printf(out, "[Fault]: fault trigger addresses: %p\n", fault_trigger_addresses+j);
		g_string_append_printf(out, "[Fault]: live faults addresses: %p\n", live_faults+j);
		current = return_next(current);	
	}
	qemu_plugin_outs(out->str);
	return 0;	
}

void invalidate_fault_trigger_address(int fault_trigger_number)
{
	*(fault_trigger_addresses + fault_trigger_number) = 0;
}

/**
 * delete_fault_trigger_address()
 *
 * delete the vector containing the fault triggers
 */
void delete_fault_trigger_addresses()
{
	free(fault_trigger_addresses);
}


/**
 * register_live_faults_callback
 *
 * This function is called, when the live faults callback is needed. This vector is used, if fault is inserted.
 * It is checked to locate the faults struct, that where inserted
 */
int register_live_faults_callback(fault_list_t *fault)
{
	if(live_faults_number == fault_number )
	{	
		g_autoptr(GString) out = g_string_new("");
		g_string_printf(out, "[ERROR]: Reached max exec callbacks. Something went totally wrong!\n[ERROR]: live_callback %i\n[ERROR]: fault_number %i", live_faults_number, fault_number);
		qemu_plugin_outs(out->str);
		return -1;
	}
	qemu_plugin_outs("[Fault]: Register exec callback\n");
	add_singlestep_req();
	*(live_faults + live_faults_number) = fault;
	live_faults_number++;
	return live_faults_number - 1;
}





/**
 * handle_first_tb_fault_insertion
 *
 * This function is called in the first used tb block
 * This function is maybe a TODO
 */
void handle_first_tb_fault_insertion()
{

	g_autoptr(GString) out = g_string_new("");
	g_string_printf(out, "Look into if we need to insert a fault!\n");
	fault_list_t * current = return_first_fault();
	qemu_plugin_outs(out->str);
	g_string_printf(out, " ");
	while(current != NULL)
	{
		if(current->fault.trigger.hitcounter == 0 && current->fault.type == INSTRUCTION )
		{
			add_singlestep_req(); // force singlestep mode for compatibility
			qemu_plugin_outs("Insert first fault\n");
			inject_fault(current);
			*(fault_trigger_addresses + current->fault.trigger.trignum) = 0; //Remove trigger from vector
		}
		if(current->fault.trigger.hitcounter == 1)
		{
			//we need to force singlestep mode for precision reasons
			add_singlestep_req();
		}
		current = return_next( current);
	}
	qemu_plugin_outs(out->str);

}



/**
 * trigger_insn_cb
 *
 * This function is registered on insn exec of trigger
 * It will determine, if the current fault should be injected or needs to wait. If yes, will call the fault injection function 
 */
void trigger_insn_cb(unsigned int vcpu_index, void *vcurrent)
{
	fault_list_t *current = (fault_list_t *) vcurrent;

	//current->fault.trigger.hitcounter = current->fault.trigger.hitcounter - 1;
	if(current->fault.trigger.hitcounter != 0)
	{
		current->fault.trigger.hitcounter = current->fault.trigger.hitcounter - 1;
		qemu_plugin_outs("Trigger eval function reached\n");
		if(current->fault.trigger.hitcounter == 0 )
		{
			/*Trigger met, Inject fault*/
			qemu_plugin_outs("Trigger reached level, inject fault\n");
			inject_fault(current);
		}
		if(current->fault.trigger.hitcounter == 1)
		{
			add_singlestep_req();
		}
	}
	else
	{
		qemu_plugin_outs("[ERROR]: The hitcounter was already 0\n");
	}
}

/**
 * tb_exec_cb
 *
 * This function 
 */
void tb_exec_cb(unsigned int vcpu_index, void *userdata)
{
	fault_list_t *current = (fault_list_t *) userdata;

	if(current->fault.lifetime != 0)
	{
		current->fault.lifetime = current->fault.lifetime - 1;
		qemu_plugin_outs("[live fault] live fault eval function reached\n");
		if(current->fault.lifetime == 0)
		{
			qemu_plugin_outs("[live fault] lifetime fault reached, reverse fault\n");
			reverse_fault(current);
			*(live_faults + current->fault.trigger.trignum) = NULL;
		}
	}
	else
	{
		qemu_plugin_outs("[ERROR]: The lifetime was already 0\n");
	}
	//qemu_plugin_outs("[TB] exec tb exec cb\n");
}

/**
 *  evaluate_trigger
 *
 *  This function takes the trigger address number and evaluates the trigger condition
 *  
 *  tb: Struct containing information about the translation block
 *  trigger_address_num: the location in the trigger vector. Is used to find the current fault
 */
void evaluate_trigger(struct qemu_plugin_tb *tb,int trigger_address_number)
{

	/* Get fault description */
	fault_list_t *current = get_fault_struct_by_trigger((uint64_t) *(fault_trigger_addresses + trigger_address_number), trigger_address_number);
	if(current == NULL)
	{
		// This case only happens, if fault_trigger_address does not match fault address in struct after it was invalidated.
		// We throw warning for debugging, however continue to run.
		qemu_plugin_outs("[TB] [WARNING]: We did not find a fault.\n");
		return;
	}
	/* Trigger tb met, now registering callback for exec to see, if we need to inject fault */
	for(int i = 0; i < tb->n; i++)
	{
		struct qemu_plugin_insn *insn = qemu_plugin_tb_get_insn(tb, i);
		if((current->fault.trigger.address >= qemu_plugin_insn_vaddr(insn))&&(current->fault.trigger.address < qemu_plugin_insn_vaddr(insn) + qemu_plugin_insn_size(insn)))
		{
			/* Trigger address met */
			qemu_plugin_outs("[TB] Reached injection of callback\n");
			qemu_plugin_register_vcpu_insn_exec_cb(insn, trigger_insn_cb, QEMU_PLUGIN_CB_RW_REGS, current);
			//qemu_plugin_register_vcpu_tb_exec_cb(tb, tb_exec_cb, QEMU_PLUGIN_CB_RW_REGS, current);

		}
	}
	print_assembler(tb);
}

// Callback for instruction exec TODO: remove?
void insn_exec_cb(unsigned int vcpu_index, void *userdata)
{
	g_autoptr(GString) out = g_string_new("");
	g_string_append(out, "Next instruction\n");
	g_string_append_printf(out, " reg[0]: %08x\n", (uint32_t) qemu_plugin_read_reg(0));

	qemu_plugin_outs(out->str);
}

/**
 * eval_live_fault_callback
 *
 * This function evaluates if the exec callback is needed to be registered. Also makes sure that fault is reverted, if lifetime is zero
 *
 * tb: Information provided by the api about the translated block
 * live_fault_callback_number: Position in vector. Needed to find fault struct
 */
void eval_live_fault_callback(struct qemu_plugin_tb *tb, int live_fault_callback_number)
{

	fault_list_t * current = *(live_faults + live_fault_callback_number);
	if(current == NULL)
	{
		qemu_plugin_outs("[ERROR]: Found no exec to be called back!\n");
		return;
	}
	if(current->fault.lifetime == 0)
	{
		// Remove exec callback
		*(live_faults + live_fault_callback_number) = NULL;
		qemu_plugin_outs("[Live faults WARNING]: Remove live faults callback\n");
		rem_singlestep_req();
	}
	else
	{
		/* Register exec callback */
		for(int i = 0; i < tb->n; i++)
		{
			struct qemu_plugin_insn *insn = qemu_plugin_tb_get_insn(tb, i);
			qemu_plugin_outs("[TB Exec]: Register exec callback function\n");
			qemu_plugin_register_vcpu_insn_exec_cb(insn, tb_exec_cb, QEMU_PLUGIN_CB_RW_REGS, current);	
		}
	}
}


/**
 * plugin_write_to_data_pipe
 *
 * Function that handles the write to the data pipe
 * 
 * str: pointer to string to be printed
 * len: length of string to be printed
 * 
 * return negative if failed
 */
int plugin_write_to_data_pipe(char *str, size_t len)
{
	g_autoptr(GString) out = g_string_new("");
	ssize_t ret = 0;
	while(len != 0)
	{
		ret = write( pipes->data, str, len);
		if(ret == -1)
		{
			g_string_printf(out, "[DEBUG]: output string was: %s\n", str);
			g_string_append_printf(out, "[DEBUG]: Value is negative. Something happened in write: %s\n", strerror(errno));
			g_string_append_printf(out, "[DEBUG]: File descriptor is : %i\n", pipes->data);
			qemu_plugin_outs(out->str);
			return -1;
		}
		str = str + ret;
		len = len - ret;
	}
	return 0;
}




/**
 * plugin_dump_mem_information
 *
 * Write collected information about the memory accesses to data pipe
 */
void plugin_dump_mem_information()
{
	if(mem_info_list == NULL)
	{
		return;
	}
	g_autoptr(GString) out = g_string_new("");
	g_string_printf(out, "$$$[Mem Information]:\n");
	plugin_write_to_data_pipe(out->str, out->len);

	mem_info_t *item = mem_info_list;
	while(item != NULL)
	{
		g_string_printf(out, "$$ 0x%lx | 0x%lx | 0x%lx | 0x%x | 0x%lx \n", item->ins_address, item->size, item->memmory_address, item->direction, item->counter);
		plugin_write_to_data_pipe(out->str, out->len);
		item = item->next;
	}
}

/**
 * plugin_end_information_dump
 *
 * This function first writes all collected data to data pipe, then deletes all information structs
 * Then it will cause a segfault to crash qemu to end it for the moment
 */
void plugin_end_information_dump(GString *end_reason)
{
	int *error = NULL;
	if(end_point->location.trignum == 4)
	{
		plugin_write_to_data_pipe("$$$[Endpoint]: 1\n", 17);
	}
	else
	{
		plugin_write_to_data_pipe("$$$[Endpoint]: 0\n", 17);
	}
	free_end_point_list(end_point);
	plugin_write_to_data_pipe("$$$[End Reason]:", 16);
	plugin_write_to_data_pipe(end_reason->str, end_reason->len);
	plugin_write_to_data_pipe("\n", 1);
	if(memory_module_configured())
	{
		qemu_plugin_outs("[DEBUG]: Read memory regions configured\n");
		read_all_memory();
	}
	qemu_plugin_outs("[DEBUG]: Read registers\n");
	add_new_registerdump(tb_counter);
	qemu_plugin_outs("[DEBUG]: Start printing to data pipe tb information\n");
	plugin_dump_tb_information();
	if(tb_exec_order_enabled == 1)
	{
		qemu_plugin_outs("[DEBUG]: Start printing to data pipe tb exec\n");
		plugin_dump_tb_exec_order();
	}
	qemu_plugin_outs("[DEBUG]: Start printing to data pipe tb mem\n");
	plugin_dump_mem_information();
	if(memory_module_configured())
	{
		qemu_plugin_outs("[DEBUG]: Start printing to data pipe memorydump\n");
		readout_all_memorydump();
	}
	qemu_plugin_outs("[DEBUG]: Start printing to data pipe registerdumps\n");
	read_register_module();
	qemu_plugin_outs("[DEBUG]: Start printing to data pipe tb faulted\n");
	dump_tb_faulted_data();
	qemu_plugin_outs("[DEBUG]: Information now in pipe, start deleting information in memory\n");
	qemu_plugin_outs("[DEBUG]: Delete tb_info\n");
	tb_info_free();
	qemu_plugin_outs("[DEBUG]: Delete tb_exec\n");
	tb_exec_order_free();
	qemu_plugin_outs("[DEBUG]: Delete mem\n");
	mem_info_free();
	qemu_plugin_outs("[DEBUG]: Delete memorydump\n");
	delete_memory_dump();
	qemu_plugin_outs("[DEBUG]: Delete tb_faulted\n");
	tb_faulted_free();
	qemu_plugin_outs("[DEBUG]: Finished\n");
	plugin_write_to_data_pipe("$$$[END]\n", 9);
	//Stop Qemu executing
	exit(0);
	*error = 0;
}


void tb_exec_end_max_event(unsigned int vcpu_index, void *vcurrent)
{
	size_t ins = (size_t) vcurrent;
	if(start_point.trignum != 3)
	{	
		if(tb_counter >= tb_counter_max)
		{
			qemu_plugin_outs("[Max tb]: max tb counter reached");

			g_autoptr(GString) reason = g_string_new("max tb");
			plugin_end_information_dump(reason);
		}
		tb_counter = tb_counter + ins;
	}
}

void tb_exec_end_cb(unsigned int vcpu_index, void *vcurrent)
{
	struct end_point_t *end_point = (struct end_point_t *)vcurrent;

	if(start_point.trignum != 3)
	{
		qemu_plugin_outs("[End]: CB called\n");
		if(end_point->location.hitcounter == 1)
		{
			qemu_plugin_outs("[End]: Reached end point\n");
			end_point->location.trignum = 4;

			g_autoptr(GString) reason = g_string_new(NULL);
			g_string_printf(reason, "endpoint %" PRIu64 "/%" PRIu64,
							end_point->location.address,
							end_point->location.hitcounter);

			plugin_end_information_dump(reason);
		}
		end_point->location.hitcounter--;
	}
}

void tb_exec_start_cb(unsigned int vcpu_index, void *vcurrent)
{
	if(start_point.hitcounter == 1)
	{
		qemu_plugin_outs("[Start]: Start point reached");
		start_point.trignum = 0;
		qemu_plugin_flush_tb();
	}
	start_point.hitcounter--;
}

/**
 * handle_tb_translate_event
 *
 * This function takes the tb struct and triggers the needed evaluation functions
 *
 */
void handle_tb_translate_event(struct qemu_plugin_tb *tb)
{
	size_t tb_size = calculate_bytesize_instructions(tb);
	qemu_plugin_outs("Reached tb handle function\n");
	/**Verify, that no trigger is called*/
	for( int i = 0; i < fault_number; i++)
	{
		if((tb->vaddr <= *(fault_trigger_addresses + i))&&((tb->vaddr + tb_size) > *(fault_trigger_addresses + i)))
		{
			g_autoptr(GString) out = g_string_new("");
			g_string_printf(out, "Met trigger address: %lx\n", *(fault_trigger_addresses + i) );
			qemu_plugin_outs(out->str);
			evaluate_trigger( tb, i);
		}
	}
	/* Verify, if exec callback is requested */
	for(int i = 0; i < live_faults_number; i++)
	{
		if(*(live_faults + i) != NULL)
		{
			g_autoptr(GString) out = g_string_new("");
			g_string_printf(out, "[TB exec] Reached live fault callback event\n");
			qemu_plugin_outs(out->str);
			eval_live_fault_callback(tb, i);
		}
	}
}


/**
 * handle_tb_translate_data
 *
 * Find the current info struct of translation blocks inside avl tree.
 * If there is no struct in avl, create struct and place it into avl.
 * Also register tb_callback_event to fill in runtime information
 *
 * tb: API struct containing information about the translation block
 */
void handle_tb_translate_data(struct qemu_plugin_tb *tb)
{
	g_autoptr(GString) out = g_string_new("");
	tb_info_t *tb_information = NULL;
	if(tb_info_enabled == 1)
	{
		tb_information = add_tb_info(tb);
	}
	if(tb_exec_order_enabled == 1)
	{
		qemu_plugin_register_vcpu_tb_exec_cb(tb, tb_exec_data_event, QEMU_PLUGIN_CB_RW_REGS, tb_information);
	}
	// inject counter
	qemu_plugin_register_vcpu_tb_exec_cb(tb, tb_exec_end_max_event, QEMU_PLUGIN_CB_RW_REGS, (void *) tb->n);
	if( mem_info_list_enabled == 1)
	{
		for(int i = 0; i < tb->n; i++)
		{
			struct qemu_plugin_insn *insn = qemu_plugin_tb_get_insn(tb, i);
			qemu_plugin_register_vcpu_mem_cb( insn, memaccess_data_cb, QEMU_PLUGIN_CB_RW_REGS, QEMU_PLUGIN_MEM_RW, (void *) insn->vaddr);
		}
	}
	// DEBUG
	GString *assembler = decode_assembler(tb);
	g_string_append_printf(out, "[TB Info] tb id: %8lx\n[TB Info] tb size: %li\n[TB Info] Assembler:\n%s\n", tb->vaddr, tb->n, assembler->str);
	g_string_free(assembler, TRUE);


	qemu_plugin_outs(out->str);

}


/**
 * vcpu_translateblock_translation_event
 *
 * main entry point for tb translation event
 */
static void vcpu_translateblock_translation_event(qemu_plugin_id_t id, struct qemu_plugin_tb *tb)
{
	g_autoptr(GString) out = g_string_new("");
	g_string_printf(out, "\n");

	qemu_plugin_outs(out->str);
	g_string_printf(out, " ");
	if(start_point.trignum != 3)
	{
		if(first_tb != 0)
		{
			qemu_plugin_outs(out->str);
			g_string_printf(out, " ");
			handle_tb_translate_event( tb);
		}
		else
		{
			g_string_append_printf(out, "This is the first time the tb is translated\n");
			first_tb = 1;
			qemu_plugin_outs(out->str);
			g_string_printf(out, " ");
			handle_first_tb_fault_insertion();
		}
		qemu_plugin_outs(out->str);
		handle_tb_translate_data(tb);
		check_tb_faulted(tb);
		for (struct end_point_t *cur = end_point; cur != NULL; cur = cur->next)
		{
			if(cur->location.trignum == 3)
			{
				size_t tb_size = calculate_bytesize_instructions(tb);
				qemu_plugin_outs("[End]: Check endpoint\n");
				if((tb->vaddr <= cur->location.address)&&((tb->vaddr + tb_size) > cur->location.address))
				{
					for(int i = 0; i < tb->n; i++)
					{
						struct qemu_plugin_insn *insn = qemu_plugin_tb_get_insn(tb, i);
						if((cur->location.address >= qemu_plugin_insn_vaddr(insn))&&(cur->location.address < qemu_plugin_insn_vaddr(insn) + qemu_plugin_insn_size(insn)))
						{
							/* Trigger address met*/
							qemu_plugin_outs("[End]: Inject cb\n");
							qemu_plugin_register_vcpu_insn_exec_cb(insn, tb_exec_end_cb, QEMU_PLUGIN_CB_RW_REGS, cur);
						}
					}
				}
			}
		}
	}
	else
	{
		size_t tb_size = calculate_bytesize_instructions(tb);
		if((tb->vaddr <= start_point.address)&&((tb->vaddr + tb_size) > start_point.address))
		{
			qemu_plugin_register_vcpu_tb_exec_cb(tb, tb_exec_start_cb, QEMU_PLUGIN_CB_RW_REGS, NULL);
		}

	}
}

int readout_pipe(size_t max, uint8_t *out, enum Pipe_type type)
{
	int n_read = 0;

	switch(type){
		case CONFIG_PIPE:
			n_read = read(pipes->config, out, max);
			break;
		case CONTROL_PIPE:
			n_read = read(pipes->control, out, max);
			break;
		case DATA_PIPE:
			n_read = read(pipes->data, out, max);
			break;
	}

	if(n_read == -1)
	{
		qemu_plugin_outs("[DEBUG]: Readout pipe, no character found or too much read\n");
		return -1;
	}

	return n_read;
}

int readout_control_qemu()
{
	size_t message_buff_size = 2048;
	
	uint8_t* control = (uint8_t*) malloc(sizeof(char) * message_buff_size);
	if(control == NULL){
		qemu_plugin_outs("[DEBUG]: Error allocating memory for incoming control message\n");
		return -1;
	}

	int msg_size = readout_pipe(message_buff_size, control, CONTROL_PIPE);
	if(msg_size <= 0){
		qemu_plugin_outs("[DEBUG]: No message on FIFO\n");
		return -1;
	}

	// Unpack message from protobuf binary format
	Archie__Config* config;
	config = archie__config__unpack(NULL, msg_size, control);
	if (config == NULL)
	{
		qemu_plugin_outs("[DEBUG]: Error unpacking the message from pipe\n");
		return -1;
	}

	// Parse the control config
	tb_counter_max = (int) config->max_duration;
	fault_number = (int) config->num_faults;
	
	if(config->exists_start){
		start_point.address = config->start_address;
		start_point.trignum = start_point.trignum | 2;

		start_point.hitcounter = config->start_counter;
		start_point.trignum = start_point.trignum | 1;
	}

	size_t size_end_points = config->n_end_list;
    struct end_point_t *cur = end_point;
    if(size_end_points > 0)
    {
        /* Head of the end_point is already malloced */
        cur->location.address = config->end_list[0]->address;
        cur->location.hitcounter = config->end_list[0]->counter;
        cur->location.trignum |= 3; 
    }

	for(size_t i = 1; i < size_end_points; ++i)
	{
		cur->next = malloc(sizeof(struct end_point_t));
		cur = cur->next;

		cur->location.address = config->end_list[i]->address;
		cur->location.hitcounter = config->end_list[i]->counter;
        /* location.trignum is not initialized as 0 thus |= can not be used */
		cur->location.trignum = 3;
        cur->next = NULL;
	}

	mem_info_list_enabled = config->mem_info;

	if(config->exists_tb_info){
		tb_info_enabled = config->tb_info;
	}

	if(config->exists_tb_exec_list){
		tb_exec_order_enabled= config->tb_exec_list;
	}

	if(config->exists_ring_buffer){
		tb_exec_order_ring_buffer = config->tb_exec_list_ring_buffer;
	}
	// End of control config

	// Parse memory config
	if(config->exists_memory_dump){
        int status = init_memory(config->num_memregions);
        if(status < 0){
            qemu_plugin_outs("[DEBUG]: Error initializing memory\n");
            return -1;
        }

		size_t n_memory_region = config->n_memorydump;
		for(int i = 0; i < n_memory_region; ++i){
			uint64_t baseaddress = (uint64_t) config->memorydump[i]->address;
			uint64_t len = (uint64_t) config->memorydump[i]->length;

			if(insert_memorydump_config(baseaddress, len) < 0){
				qemu_plugin_outs("[DEBUG]: Error inserting memorydump\n");
				return -1;
			}
		}
	}
	// End of memory config
	free(control);
	archie__config__free_unpacked(config, NULL);
	
	if(memory_module_configured() == 0)
	{
		init_memory(1);
	}
	qemu_plugin_outs("[DEBUG]: Finished readout control. Now start readout of config\n");
	if(qemu_setup_config() < 0)
	{
		qemu_plugin_outs("[ERROR]: Something went wrong in readout of config pipe\n");
		return -1;
	}
	qemu_plugin_outs("[DEBUG]: Finished readout config.\n");
	return 1;
}

int initialise_plugin(GString * out, int argc, char **argv, int architecture)
{
	// Global FIFO data structure for control, data and config
	pipes = NULL;
	// Start pointer for linked list of faults
	init_fault_list();
	// Number of faults registered in plugin
	fault_number = 0;
	// Pointer for array, that is dynamically scaled for the number of faults registered.
	// It is used to quickly look if a trigger condition might be reached
	fault_trigger_addresses = NULL;
	// Pointer to array, that is dynamically scaled for the number of faults registered
	// It contains the pointer to fault structs whose lifetime is not zero
	// If lifetime of fault reaches zero, it undoes the fault. If zero, it is permanent.
	live_faults = NULL;
	//
	mem_info_list = NULL;
	//
	live_faults_number = 0;
	// Used to determine if the tb generating is first executed
	first_tb = 0;
	// counter of executed tbs since start
	tb_counter = 0;
	// Maximum number of tbs executed after start
	tb_counter_max = 1000;
	// Start point initialization
	start_point.address = 0;
	start_point.hitcounter = 0;
	start_point.trignum = 0;
	// End point initialization
	end_point = malloc(sizeof(struct end_point_t));
	end_point->location.trignum = 0;
	end_point->next = NULL;

	// Init tb_info
	tb_info_init();

	// enable mem info logging
	mem_info_list_enabled = 1;
	// enable tb info logging
	tb_info_enabled = 1;
	// enable tb exec logging
	tb_exec_order_enabled = 1;
	// disable tb exec ring buffer
	tb_exec_order_ring_buffer = 0;

	/* Initialisation of pipe struct */
	pipes = malloc(sizeof(fifos_t));
	if(pipes == NULL)
	{	g_string_append(out, "[ERROR]: Pipe struct not malloced\n");
		return -1;
	}
	pipes->control = -1;
	pipes->config = -1;
	pipes->data = -1;
	/*Start Argparsing and open up the Fifos*/
	if(parse_args(argc, argv, out) != 0)
	{
		g_string_append_printf(out, "[ERROR]: Initialisation of FIFO failed!\n");
		qemu_plugin_outs(out->str);
		return -1;
	}
	g_string_append_printf(out, "[Info]: Initialisation of FIFO.......Done!\n");
	init_memory_module();
	init_register_module(architecture);
	init_singlestep_req();
	return 0;
}

/**
 *
 * qemu_plugin_install
 *
 * This is the first called function.
 * It needs to setup all needed parts inside the plugin
 *
 */
QEMU_PLUGIN_EXPORT int qemu_plugin_install(qemu_plugin_id_t id, 
		const qemu_info_t *info,
		int argc, char **argv)
{
	g_autoptr(GString) out = g_string_new("");
	g_string_printf(out, "QEMU Injection Plugin\n Current Target is %s\n", info->target_name);
	g_string_append_printf(out, "Current Version of QEMU Plugin is %i, Min Version is %i\n", info->version.cur, info->version.min);
	int valid_architecture = -1;
	if(strcmp(info->target_name, "arm") == 0)
	{
		valid_architecture = ARM;
	}
	if(strcmp(info->target_name, "riscv32") == 0 || strcmp(info->target_name, "riscv64") == 0)
	{
		valid_architecture = RISCV;
	}

	if(valid_architecture == -1)
	{
		g_string_append(out, "[ERROR]: Abort plugin, as this architecture is currently not supported!\n");
		qemu_plugin_outs(out->str);
		return -1;
	}
	// Initialise all global datastructures and open FIFOs
	if(initialise_plugin(out, argc, argv, valid_architecture) == -1)
	{
		goto ABORT;
	}

	g_string_append_printf(out, "[Info]: Readout config FIFO\n");
	qemu_plugin_outs(out->str);
	g_string_printf(out, " ");
	//	if( qemu_setup_config() < 0)
	if( readout_control_qemu() < 0)
	{
		goto ABORT;
	}
	g_string_append_printf(out, "[Info]: Linked list entry address: %p\n", return_first_fault());	
	tb_faulted_init(fault_number);	
	g_string_append_printf(out, "[Info]: Register fault trigger addresses\n");
	qemu_plugin_outs(out->str);
	g_string_printf(out, " ");
	if(register_fault_trigger_addresses() < 0 )
	{
		goto ABORT;
	}
	g_string_append_printf(out, "[Info]: Number of triggers: %i\n", fault_number);
	g_string_append(out, "[Info]: Register VCPU tb trans callback\n");
	qemu_plugin_register_vcpu_tb_trans_cb( id, vcpu_translateblock_translation_event);
	g_string_append(out, "[Info]: Initialise TB avl tree ....");
	if(tb_info_avl_init() == -1)
	{
		g_string_append(out, "ERROR\n[ERROR] TB avl tree initialisation failed\n");
		goto ABORT;
	}
	g_string_append(out, "Done\n");
	g_string_append(out, "[Info] Initialise mem avl tree ....");
	mem_avl_root = avl_create( &mem_comparison_func, NULL, NULL);
	if(mem_avl_root == NULL)
	{
		g_string_append(out, "ERROR\n[ERROR] mem avl tree initialisation failed");
		goto ABORT;
	}
	g_string_append(out, "Done\n");

	if (tb_exec_order_init())
	{
		g_string_append_printf(out, "[ERROR]: Initialisation of executed translation blocks list failed!\n");
		return -1;
	}

	g_string_append_printf(out, "[Start]: Reached end of initialisation, starting guest now\n");
	qemu_plugin_outs(out->str);
	return 0;
ABORT:
	if(mem_avl_root != NULL)
	{
		avl_destroy(mem_avl_root, NULL);
	}
	tb_info_free();
	delete_fault_trigger_addresses();
	delete_fault_queue();
	tb_faulted_free();
	tb_exec_order_free();
	g_string_append(out, "[ERROR]: Something went wrong. Aborting now!\n");
	qemu_plugin_outs(out->str);
	return -1;
}
