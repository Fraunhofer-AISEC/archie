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
 *   This function manages the fault description objects
 */

#include "fault_list.h"


/* Global data structures */

fault_list_t *first_fault;

void init_fault_list(void)
{
	first_fault = NULL;
}


/**
 * add fault
 *
 * This function appends one fault to the linked list. 
 *
 * fault_address: address of fault
 * fault_type: type of fault. See enum on implemented targets
 * fault_model: model of fault. See enum on implemented fault models
 * fault_lifetime: How long the fault should reside. 0 means indefinitely
 * fault_mask: bit mask on which bits should be targeted.
 * fault_trigger_address: Address of trigger location. Fault will be injected if this location is reached
 * fault_trigger_hitcounter: Set how many times the location needs to be reached before the fault is injected
 * num_bytes: Used by overwrite to determen the number of bytes to overwrite
 * 
 * return -1 if fault
 */
int add_fault(uint64_t fault_address, uint64_t fault_type, uint64_t fault_model, uint64_t fault_lifetime, uint8_t fault_mask[16], uint64_t fault_trigger_address, uint64_t fault_trigger_hitcounter, uint8_t num_bytes)
{
	fault_list_t *new_fault;
	new_fault = malloc(sizeof(fault_list_t));
	if( new_fault == NULL)
	{
		return -1;
	}
	new_fault->next = NULL;
	new_fault->fault.address = fault_address;
	new_fault->fault.type = fault_type;
	new_fault->fault.model = fault_model;
	new_fault->fault.lifetime = fault_lifetime;
	//new_fault->fault.mask = fault_mask;
	new_fault->fault.trigger.address = fault_trigger_address;
	new_fault->fault.trigger.hitcounter = fault_trigger_hitcounter;
	new_fault->fault.num_bytes = num_bytes;
	for(int i = 0; i < 16; i++)
	{	
		new_fault->fault.restoremask[i] = 0;
		new_fault->fault.mask[i] = fault_mask[i];
	}
	if(first_fault != NULL)
	{
		new_fault->next = first_fault;
	}
	first_fault = new_fault;
	return 0;
}


/**
 *
 * delete_fault_queue
 *
 * This function removes faults from linked list
 *
 */
void delete_fault_queue(void)
{
	fault_list_t *del_item = NULL;
	while(first_fault != NULL)
	{
		del_item = first_fault;
		first_fault = first_fault->next;
		free(del_item);
	}
}


/**
 * return first
 *
 * This function exists to separate fault list management from the rest of the code base
 */
fault_list_t* return_first_fault(void)
{
	return first_fault;
}

/**
 * return_next
 *
 * function to return next pointer.
 * This is to be able to change the current link list if desired
 */
fault_list_t * return_next(fault_list_t * current)
{
	return current->next;
}

/**
 * get_fault_trigger_address
 *
 * function to return the fault address. 
 * This is to be able to change the current data structure if needed
 */
uint64_t get_fault_trigger_address(fault_list_t * current)
{
	return current->fault.trigger.address;
}

/**
 * set_fault_trigger_num
 *
 * Function sets the trigger number field. This is done to separate between two triggers with the same address
 */
void set_fault_trigger_num(fault_list_t * current, uint64_t trignum)
{
	current->fault.trigger.trignum = trignum;
}

fault_list_t * get_fault_struct_by_trigger(uint64_t fault_trigger_address, uint64_t fault_trigger_number)
{
	fault_list_t * current = first_fault;
	while(current != NULL)
	{
		if(current->fault.trigger.address == fault_trigger_address)
		{
			if(current->fault.trigger.trignum == fault_trigger_number)
			{
				return current;
			}
		}
		current = current->next;
	}
	return NULL;
}
