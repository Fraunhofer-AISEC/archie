/*
 *   Copyright 2023 Kevin Schneider
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
 *   This file contains the header functions for managing register data.
 */

#ifndef FAULTPLUGIN_MEMMAPDUMP_H
#define FAULTPLUGIN_MEMMAPDUMP_H

#include "qemu/osdep.h"
#include <qemu/qemu-plugin.h>

#include "protobuf/data.pb-c.h"

#include "exec/memory.h"

#include "faultplugin.h"

int plugin_dump_memmap_information(Archie__Data* protobuf_msg);

void free_memmap_info();

#endif
