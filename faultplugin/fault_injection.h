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
 *   This file contains the header for injecting faults in qemu
 */

#ifndef FAULT_INJECTION
#define FAULT_INJECTION

#include "fault_list.h"
#include "singlestep.h"

/**
 * inject_fault
 *
 * At this point the fault needs to be injected. This is the function to select the right model and call the injection function
 *
 * current: Struct address containing the fault information needed
 */
void inject_fault(fault_list_t * current);

/**
 * reverse_fault
 *
 * Reverse the fault injected
 *
 * current: fault description 
 */
void reverse_fault(fault_list_t * current);

/**
 * inject_register_fault
 *
 * Inject fault into registers. Reads the current string and determines the register that is attacked, loads it and performs the fault required
 */
void inject_register_fault(fault_list_t * current);

/**
 * reverse_register_fault
 */
void reverse_register_fault(fault_list_t * current);

/**
 * inject_memory_fault
 *
 * injects fault into memory regions
 * Reads current struct to determine the location, model, and mask of fault.
 * Then performs the fault injection
 *
 * current: Struct address containing the fault information
 */
void inject_memory_fault(fault_list_t * current);

/**
 * process_set1_memory
 *
 * Read memory, then set bits according to mask, then write memory back
 * 
 * address: base address of lowest byte
 * mask: mask containing which bits need to be flipped to 1
 */
void process_set1_memory(uint64_t address, uint8_t  mask[], uint8_t restoremask[]);

/**
 * process_reverse_fault
 *
 * Read memory, then apply restore mask according to fault mask, then write memory back
 *
 * address: base address of fault
 * mask: location mask of bits set to 0 for reverse
 */
void process_reverse_fault(uint64_t address, uint8_t mask[], uint8_t restoremask[]);

/**
 * process_set0_memory
 *
 * Read memory, then clear bits according to mask, then write memory back
 *
 * address: base address of fault
 * mask: location mask of bits set to 0 
 */
void process_set0_memory(uint64_t address, uint8_t  mask[], uint8_t restoremask[]);

/**
 * process_toggle_memory
 *
 * Read memory, then toggle bits according to mask, then write memory back
 *
 * address: base address of fault
 * mask: location mask of bits to be toggled
 */
void process_toggle_memory(uint64_t address, uint8_t  mask[], uint8_t restoremask[]);
#endif
