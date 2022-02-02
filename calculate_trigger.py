from faultclass import build_filters

import logging
import pandas

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
    goldenrun_tb_exec,
    goldenrun_tb_info,
):
    logger.info(f"Search trigger to fault INSN at 0x{fault_address:08x}")
    [idx, ins] = find_fault(
        fault_address, goldenrun_tb_exec, goldenrun_tb_info, trigger_occurrences
    )
    if idx < 0:
        return [-1, trigger_occurrences]
    trigger_not_in_same_tb = 0
    trigger_position = trigger_position * (-1)
    while trigger_position != 0:
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
    # Got trigger address, now calculate the adjusted hitcounter. If the trigger
    # address is in a different TB to the fault address, it may be executed more
    # often than the TB with the fault address itself. To still trigger the
    # correct fault, the hitcounter has to be adjusted.
    if trigger_not_in_same_tb == 1:
        trigger_tb = goldenrun_tb_exec.at[idx, "tb"]
        trigger_hitcounter = goldenrun_tb_exec.iloc[0 : idx + 1].tb.value_counts()[
            trigger_tb
        ]
    else:
        trigger_hitcounter = trigger_occurrences

    logger.info(
        "Found trigger for faulting instruction address {} at {} with "
        "hitcounter {}".format(fault_address, ins, trigger_hitcounter)
    )
    return [ins, trigger_hitcounter]


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
                    and tdict["triggerhitcounter"] == fault.trigger.hitcounter
                    and tdict["triggeraddress"] == fault.trigger.address
                ):
                    fault.trigger.address = tdict["answer"][0]
                    fault.trigger.hitcounter = tdict["answer"][1]
                    found = True
                    break
            if found is True:
                continue

            tbs = search_for_fault_location(
                lists,
                fault.trigger.address,
                fault.address,
                fault.trigger.hitcounter,
                goldenrun_tb_exec,
                goldenrun_tb_info,
            )
            d = {}
            d["faultaddress"] = fault.address
            d["triggerhitcounter"] = fault.trigger.hitcounter
            d["triggeraddress"] = fault.trigger.address
            d["answer"] = tbs
            cachelist.insert(0, d)
            fault.trigger.address = tbs[0]
            fault.trigger.hitcounter = tbs[1]
