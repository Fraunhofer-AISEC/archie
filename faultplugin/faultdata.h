#ifndef QEMU_FAULTPLUGIN_DATA
#define QEMU_FAULTPLUGIN_DATA
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
 *   This File contains the headers for functions managing memory dumps
 */



#include <inttypes.h>
#include <stdlib.h>
#include "faultplugin.h"

#include <glib.h>

#include <qemu/qemu-plugin.h>


/**
 * init_memory_module()
 *
 * Initialise the global variables.
 * This only makes sure the plugin can deliver a valid response to memory_module_configured
 */
void init_memory_module(void);


/**
 * memory_module_configured()
 *
 * returns 1 if configured otherwise 0
 */
int memory_module_configured(void);

/**
 * init_memory
 * 
 * Initialise the global pointer with the number_of_regions amount of structs.
 *
 * @param number_of_regions: Number of structs to initialise
 */
int init_memory(int number_of_regions);

/**
 * delete_memory_dump
 *
 * Free the complete internal data structure. After this all data is no longer accessible
 */
void delete_memory_dump(void);

/**
 * insert_memorydump_config
 *
 * Initialise one vector element with the memory region, that should be read. 
 *
 * @param baseaddress: Baseaddress of memory region
 * @param len: length of memory region in bytes
 */
int insert_memorydump_config(uint64_t baseaddress, uint64_t len);

/**
 * read_all_memory
 *
 * Read all client memory regions defined by user.
 */
void read_all_memory(void);


/**
 * read_specific_memoryregion
 *
 * Read a specific memory region as defined by baseaddress
 *
 * @param baseaddress: the start location provided by insert_memory_dump_config
 */
void read_specific_memoryregion(uint64_t baseaddress);

/**
 * read_memoryregion
 *
 * Read one client memory region defined by user 
 *
 * @param memorydump_position: select which region should be read in vector element position
 */
int read_memoryregion(uint64_t memorydump_position);

/**
 * readout_memorydump_dump
 *
 * generate the string for data pipe for one memory region dump taken. It then writes each line directly to data pipe.
 *
 * @param memorydump_position: select which region should be read in vector element
 * @param dump_pos: select which data dump should be written to pipe. Multiple can be taken during the execution of the config.
 */
int readout_memorydump_dump(uint64_t memorydump_position, uint64_t dump_pos);

/**
 * readout_memorydump
 *
 * Call read_memorydump_dump for all available dumps inside the struct. All
 * dumps are printed to data pipe. Also print config for this memorydump to data pipe
 *
 */
int readout_memorydump(uint64_t memorydump_position);

/**
 * readout_all_memorydump
 *
 * This function will send all memorydumps through the data pipe 
 */
int readout_all_memorydump(void);

#endif
