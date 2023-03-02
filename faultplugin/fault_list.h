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
 *   This file contains the headers for managing fault descriptions
 */

#ifndef FAULT_LIST
#define FAULT_LIST
#include <inttypes.h>
#include <stdlib.h>


typedef struct
{
	uint64_t address; //uint64_t?
	uint64_t hitcounter;
	uint64_t trignum;
} fault_trigger_t;

typedef struct
{
	uint64_t address; //uint64_t?
	uint64_t type; //Typedef enum?
	uint64_t model;
	uint64_t lifetime;
	uint8_t num_bytes; // Used by overwrite to find out how many bytes to overwrite
	uint8_t mask[16]; // uint8_t array?
	uint8_t restoremask[16];
	fault_trigger_t trigger;
} fault_t;

typedef struct fault_list_t fault_list_t;
typedef struct fault_list_t
{
	fault_list_t *next;
	fault_t fault;
} fault_list_t;



void init_fault_list(void);

/**
 * add fault
 *
 * This function appends one fault to the linked list. 
 *
 * fault_address: address of fault
 * fault_type: type of fault. see enum on implemented targets
 * fault_model: model of fault. see enum on implemented fault models
 * fault_lifetime: How long should the fault reside. 0 means indefinitely
 * fault_mask: bit mask on which bits should be targeted.
 * fault_trigger_address: Address of trigger location. Fault will be injected if this location is reached
 * fault_trigger_hitcounter: set how many times the location needs to be reached before the fault is injected
* num_bytes: Used by overwrite to determen the number of bytes to overwrite 
 * 
 * return -1 if fault
 */
int add_fault(uint64_t fault_address, uint64_t fault_type, uint64_t fault_model, uint64_t fault_lifetime, uint8_t fault_mask[16], uint64_t fault_trigger_address, uint64_t fault_trigger_hitcounter, uint8_t num_bytes);

/**
 *
 * delete_fault_queue
 *
 * This function removes faults from linked list
 *
 */
void delete_fault_queue(void);

/**
 * return_first_fault
 *
 * This function exists to separate fault list management from the rest of the code base
 */
fault_list_t* return_first_fault(void);

/**
 * return_next
 *
 * function to return next pointer.
 * This is to be able to change the current link list if desired
 */
fault_list_t * return_next(fault_list_t * current);

/**
 * get_fault_trigger_address
 *
 * function to return the fault address. 
 * This is to be able to change the current data structure if needed
 */
uint64_t get_fault_trigger_address(fault_list_t * current);

/**
 * set_fault_trigger_num
 *
 * Function sets the trigger number field. This is done to separate between two triggers with the same address
 */
void set_fault_trigger_num(fault_list_t * current, uint64_t trignum);

/**
 * get_fault_struct_by_trigger
 *
 * Function returns the corresponding fault to a trigger address and trigger number
 */
fault_list_t * get_fault_struct_by_trigger(uint64_t fault_trigger_address, uint64_t fault_trigger_number);
#endif
