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
 *   This file contains all functions needed to collect register data and send
 *   it over the data pipe
 */
#include "memmap_collection.h"

Archie__MemMapInfo **mem_map_infos;
size_t mem_map_size;


typedef struct AddrRange AddrRange;
struct AddrRange {
    Int128 start;
    Int128 size;
};

struct FlatRange {
    MemoryRegion *mr;
    hwaddr offset_in_region;
    AddrRange addr;
    uint8_t dirty_log_mask;
    bool romd_mode;
    bool readonly;
    bool nonvolatile;
};

void flatview_for_each_range(FlatView *fv, flatview_cb cb , void* opaque)
{
	FlatRange *fr;

	assert(fv);
	assert(cb);

	for (fr = fv->ranges; fr < fv->ranges + fv->nr; ++fr) {
		if (cb(fr->addr.start, fr->addr.size, fr->mr, fr->offset_in_region, opaque)) break;
	}
}

bool add_memmap_entry(Int128 start, Int128 len, const MemoryRegion *mr, hwaddr offset_in_region, void* opaque) {
	Archie__Data *protobuf_msg = opaque;
	if (mr->ram) {
	    Archie__MemMapInfo *mme = malloc(sizeof(Archie__MemMapInfo));
	    archie__mem_map_info__init(mme);
	    mme->address = int128_get64(start);
	    mme->size = int128_get64(len);
	    protobuf_msg->mem_map_infos[protobuf_msg->n_mem_map_infos++] = mme;
	}
	return false;
}

int plugin_dump_memmap_information(Archie__Data* protobuf_msg)
{
	AddressSpace *addr_space = qemu_plugin_get_address_space();
	FlatView *addr_space_fv = address_space_to_flatview(addr_space);

	protobuf_msg->n_mem_map_infos = 0;
	mem_map_infos = malloc(sizeof(Archie__MemMapInfo*) * addr_space_fv->nr);
	if (!mem_map_infos) return -1;
	protobuf_msg->mem_map_infos = mem_map_infos;

	flatview_for_each_range(addr_space_fv, add_memmap_entry, protobuf_msg);

	mem_map_size = protobuf_msg->n_mem_map_infos;

	return 0;
}

void free_memmap_info() {
    for (int i=0; i<mem_map_size; i++) {
	free(mem_map_infos[i]);
    }
    free(mem_map_infos);
}
