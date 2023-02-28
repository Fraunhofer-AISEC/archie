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
#include "memmapdump.h"

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

bool dump_memmap_information(Int128 start, Int128 len, const MemoryRegion *mr, hwaddr offset_in_region, void *opaque) {
	g_autoptr(GString) out = g_string_new("");
	g_string_printf(out, "$$ 0x%lx | 0x%lx \n", int128_get64(start), int128_get64(len));
	plugin_write_to_data_pipe(out->str, out->len);
	return false;
}

void flatview_for_each_range(FlatView *fv, flatview_cb cb , void *opaque)
{
    FlatRange *fr;

    assert(fv);
    assert(cb);

    for (fr = fv->ranges; fr < fv->ranges + fv->nr; ++fr) {
        if (cb(fr->addr.start, fr->addr.size, fr->mr,
               fr->offset_in_region, opaque)) {
            break;
        }
    }
}

void read_memmap_information_module(void)
{
	g_autoptr(GString) out = g_string_new("");
	g_string_printf(out, "$$$[Memory Map]\n");
	plugin_write_to_data_pipe(out->str, out->len);

	AddressSpace *addr_space = qemu_plugin_get_address_space();
	flatview_for_each_range(address_space_to_flatview(addr_space), dump_memmap_information, NULL);
}
