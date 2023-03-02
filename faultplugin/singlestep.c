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
 *   This file contains the functions for managing singlestep mode inside
 *   the plugin
 */

#include "singlestep.h"

#include <qemu/qemu-plugin.h>
#include <glib.h>


volatile uint64_t req_singlestep = 0;

void init_singlestep_req(void)
{
	req_singlestep = 0;
}

void check_singlestep(void)
{
	if(req_singlestep == 0)
	{
		qemu_plugin_single_step(0);
	}
	else
	{
		qemu_plugin_single_step(1);
	}
	qemu_plugin_flush_tb();
}

void add_singlestep_req(void)
{
	g_autoptr(GString) out = g_string_new("");
	qemu_plugin_outs("[SINGLESTEP]: increase request\n");
	req_singlestep++;
	g_string_printf(out, "[SINGLESTEP]: requests %li\n", req_singlestep);
	qemu_plugin_outs(out->str);
	check_singlestep();
}

void rem_singlestep_req(void)
{
	if(req_singlestep != 0)
	{
		g_autoptr(GString) out = g_string_new("");
		qemu_plugin_outs("[SINGLESTEP]: decrease request\n");
		req_singlestep--;
		g_string_printf(out, "[SINGLESTEP]: requests %li\n", req_singlestep);
		qemu_plugin_outs(out->str);
		check_singlestep();
	}
}
