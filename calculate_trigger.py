# Copyright (c) 2021 Florian Andreas Hauschild
# Copyright (c) 2021 Fraunhofer AISEC
# Fraunhofer-Gesellschaft zur Foerderung der angewandten Forschung e.V.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging

import pandas

from faultclass import build_filters

logger = logging.getLogger(__name__)


def find_tb_info_row(tb_id, goldenrun_tb_info):
    idx = goldenrun_tb_info.index[goldenrun_tb_info["id"] == tb_id]
    return idx[0]


def allign_fault_to_instruction(address, tbinfo_size, tbinfo_assembler, tbinfo_id):
    asm_addresses = []
    "Start searching for instruction addresses"
    split = tbinfo_assembler.split("[ ")
    for sp in split[1:]:
        "Find end of address"
        s = sp.split("]")
        "Convert and append to list"
        asm_addresses.append(int("0x" + s[0].strip(), 0))
    asm_addresses.append(tbinfo_id + tbinfo_size)
    for i in range(0, len(asm_addresses) - 1, 1):
        if address >= asm_addresses[i] and address < asm_addresses[i + 1]:
            return asm_addresses[i]


def calculate_lifespan_from_start(
    filter_lists,
    fault_address,
    goldenrun_tb_exec,
    goldenrun_tb_info,
    trigger_occurrences,
):
    [idx, instruction_address] = find_fault(
        fault_address, goldenrun_tb_exec, goldenrun_tb_info, trigger_occurrences
    )
    tb_id = goldenrun_tb_exec.at[idx, "tb"]
    lifespan = 0
    for filt in filter_lists:
        if filt[0] != tb_id:
            continue
        for ins in filt:
            lifespan += 1
            if ins == instruction_address:
                break
        break
    for itter in range(0, idx):
        idtbinfo = find_tb_info_row(
            goldenrun_tb_exec.at[itter, "tb"], goldenrun_tb_info
        )
        lifespan += goldenrun_tb_info.at[idtbinfo, "ins_count"]
    return lifespan


def find_fault(
    fault_address, goldenrun_tb_exec, goldenrun_tb_info, trigger_occurrences
):
    idx = pandas.Index([])
    for index, tb in goldenrun_tb_info.iterrows():
        if fault_address < tb["id"] or fault_address >= (tb["id"] + tb["size"]):
            continue
        tmp = goldenrun_tb_exec.index[goldenrun_tb_exec["tb"] == tb["id"]]
        idx = idx.union(tmp)
    """Identify desired occurrence"""
    if trigger_occurrences > len(idx):
        return [-1, 0]
    idx = idx[trigger_occurrences - 1]
    idtbinfo = find_tb_info_row(goldenrun_tb_exec.at[idx, "tb"], goldenrun_tb_info)
    ins = allign_fault_to_instruction(
        fault_address,
        goldenrun_tb_info.at[idtbinfo, "size"],
        goldenrun_tb_info.at[idtbinfo, "assembler"],
        goldenrun_tb_info.at[idtbinfo, "id"],
    )
    return [idx, ins]


def search_for_fault_location(
    filter_lists,
    trigger_position,
    fault_address,
    trigger_occurrences,
    fault_lifespan,
    goldenrun_tb_exec,
    goldenrun_tb_info,
):
    logger.info(f"Search trigger to fault INSN at 0x{fault_address:08x}")
    [idx, ins] = find_fault(
        fault_address, goldenrun_tb_exec, goldenrun_tb_info, trigger_occurrences
    )
    if idx < 0:
        return [-1, trigger_occurrences, fault_lifespan]
    trigger_not_in_same_tb = 0
    lifespan_diff = trigger_position + fault_lifespan
    trigger_position = trigger_position * (-1)
    while trigger_position != 0:
        if idx < 0:
            if fault_lifespan > 0:
                fault_lifespan = calculate_lifespan_from_start(
                    filter_lists,
                    fault_address,
                    goldenrun_tb_exec,
                    goldenrun_tb_info,
                    trigger_occurrences,
                )
                fault_lifespan += lifespan_diff
            return [fault_address, 0, fault_lifespan]
        idtbinfo = find_tb_info_row(goldenrun_tb_exec.at[idx, "tb"], goldenrun_tb_info)
        if trigger_not_in_same_tb == 1:
            """Is current tb to short for trigger position"""
            if trigger_position > goldenrun_tb_info.at[idtbinfo, "ins_count"]:
                idx = idx - 1
                trigger_position = (
                    trigger_position - goldenrun_tb_info.at[idtbinfo, "ins_count"]
                )
            else:
                for filt in filter_lists:
                    if filt[0] == goldenrun_tb_info.at[idtbinfo, "id"]:
                        ins = filt[len(filt) - trigger_position]
                        trigger_position = 0
                        break
        else:
            tb_id = goldenrun_tb_exec.at[idx, "tb"]
            for filt in filter_lists:
                """found matching filter"""
                if filt[0] == tb_id:
                    for i in range(0, len(filt), 1):
                        if filt[i] == ins:
                            """Case ins is in the current tb"""
                            if i >= trigger_position:
                                i -= trigger_position
                                ins = filt[i]
                                trigger_position = 0
                            else:
                                """Case ins is not in the current tb"""
                                trigger_not_in_same_tb = 1
                                trigger_position -= i
                                idx -= 1
                            break
    # Got trigger address, now calculate the trigger hitcounter
    trigger_tb = goldenrun_tb_exec.at[idx, "tb"]
    tb_hitcounters = goldenrun_tb_exec.iloc[0 : idx + 1].tb.value_counts()
    trigger_hitcounter = tb_hitcounters[trigger_tb]

    tb_start = goldenrun_tb_info["id"].copy()
    tb_start.index = goldenrun_tb_info["id"]

    tb_end = goldenrun_tb_info["id"] + goldenrun_tb_info["size"] - 1
    tb_end.index = goldenrun_tb_info["id"]

    tb_start_end = pandas.DataFrame(
        {
            "tb_start": tb_start,
            "tb_end": tb_end,
        }
    )

    # Is the trigger TB a sub-TB?
    sub_tbs = tb_start_end[
        (trigger_tb > tb_start_end["tb_start"]) & (trigger_tb <= tb_start_end["tb_end"])
    ]

    for sub_tb, _ in sub_tbs.iterrows():
        # Filter out TBs we did not execute yet
        if sub_tb not in tb_hitcounters:
            continue

        trigger_hitcounter += tb_hitcounters[sub_tb]

    # Does the trigger TB contain a sub-TB?
    last_instr = tb_start_end.loc[trigger_tb, "tb_end"]

    sub_tbs = tb_start_end[
        (trigger_tb < tb_start_end["tb_start"])
        & (last_instr > tb_start_end["tb_start"])
        & (last_instr <= tb_start_end["tb_end"])
    ]

    for sub_tb, sub_tb_data in sub_tbs.iterrows():
        # Filter out TBs we did not execute yet
        if sub_tb not in tb_hitcounters:
            continue

        # Is the trigger instruction part of the sub-TB?
        if ins >= sub_tb_data["tb_start"]:
            trigger_hitcounter += tb_hitcounters[sub_tb]

    logger.info(
        "Found trigger for faulting instruction address {} at {} with "
        "hitcounter {}".format(fault_address, ins, trigger_hitcounter)
    )
    return [ins, trigger_hitcounter, fault_lifespan]


def calculate_trigger_addresses(fault_list, goldenrun_tb_exec, goldenrun_tb_info):
    """"""
    "check every fault list"
    cachelist = []
    lists = build_filters(goldenrun_tb_info)
    for list in lists:
        list = list.reverse()
    for faults in fault_list:
        for fault in faults["faultlist"]:
            if fault.trigger.address >= 0 or fault.trigger.hitcounter == 0:
                continue

            found = False
            for tdict in cachelist:
                if (
                    tdict["faultaddress"] == fault.address
                    and tdict["faultlifespan"] == fault.lifespan
                    and tdict["triggerhitcounter"] == fault.trigger.hitcounter
                    and tdict["triggeraddress"] == fault.trigger.address
                ):
                    fault.trigger.address = tdict["answer"][0]
                    fault.trigger.hitcounter = tdict["answer"][1]
                    fault.lifespan = tdict["answer"][2]
                    found = True
                    break
            if found is True:
                continue

            if fault.lifespan != 0 and fault.trigger.address + fault.lifespan < 0:
                logger.warning(
                    f"Lifespan is too short to take effect for 0x{fault.address:0x}"
                    f" with hitcounter {fault.trigger.hitcounter}, trigger address"
                    f" {fault.trigger.address} and lifespan {fault.lifespan}"
                )
                tbs = [-1, fault.trigger.hitcounter, fault.lifespan]
            else:
                tbs = search_for_fault_location(
                    lists,
                    fault.trigger.address,
                    fault.address,
                    fault.trigger.hitcounter,
                    fault.lifespan,
                    goldenrun_tb_exec,
                    goldenrun_tb_info,
                )
            d = dict()
            d["faultaddress"] = fault.address
            d["triggerhitcounter"] = fault.trigger.hitcounter
            d["triggeraddress"] = fault.trigger.address
            d["faultlifespan"] = fault.lifespan
            d["answer"] = tbs
            cachelist.insert(0, d)
            fault.trigger.address = tbs[0]
            fault.trigger.hitcounter = tbs[1]
            fault.lifespan = tbs[2]
