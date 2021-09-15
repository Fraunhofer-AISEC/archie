from faultclass import build_filters

import logging
logger = logging.getLogger(__name__)


def find_tb_info_row(tb_id, goldenrun_tb_info):
    idx = goldenrun_tb_info.index[goldenrun_tb_info['id'] == tb_id]
    return idx[0]


def allign_fault_to_instruction(address, tbinfo_size, tbinfo_assembler, tbinfo_id):
    asm_addresses = []
    "Start seraching for instruction addresses"
    split = tbinfo_assembler.split('[ ')
    for sp in split[1:]:
        "Find end of address"
        s = sp.split(']')
        "Convert and append to list"
        asm_addresses.append(int("0x"+s[0].strip(), 0))
    asm_addresses.append(tbinfo_id + tbinfo_size)
    for i in range(0, len(asm_addresses)-1, 1):
        if address >= asm_addresses[i] and address < asm_addresses[i + 1]:
            return asm_addresses[i]


def search_for_fault_location(filter_lists, trigger_position, fault_address, trigger_occurences, goldenrun_tb_exec, goldenrun_tb_info):
    """Automatically search for trigger instruction"""
    found_tbs = []
    logger.info("search trigger for faulting instruction address {}".format(fault_address))
    for index, tb in goldenrun_tb_info.iterrows():
        if fault_address >= tb['id'] and (fault_address < tb['id'] + tb['size']):
            found_tbs.append(tb['id'])
    idx = None
    first = 0
    for tbs in found_tbs:
        tmp = goldenrun_tb_exec.index[goldenrun_tb_exec['tb'] == tbs]
        if first == 0:
            first = 1
            idx = tmp
        else:
            idx = idx.union(tmp)
    """Identify desired occurrence"""
    if trigger_occurences >= len(idx):
        return -1
    idx = idx[trigger_occurences]
    idtbinfo = find_tb_info_row(goldenrun_tb_exec.at[idx, 'tb'], goldenrun_tb_info)
    ins = allign_fault_to_instruction(fault_address, goldenrun_tb_info.at[idtbinfo, 'size'], goldenrun_tb_info.at[idtbinfo, 'assembler'], goldenrun_tb_info.at[idtbinfo, 'id'])
    is_first_instruction = 0
    trigger_position = trigger_position * (-1)
    while trigger_position != 0:
        idtbinfo = find_tb_info_row(goldenrun_tb_exec.at[idx, 'tb'], goldenrun_tb_info)
        if is_first_instruction == 1:
            """Is current tb to short for trigger position"""
            if trigger_position > goldenrun_tb_info.at[idtbinfo, 'ins_count']:
                idx = idx - 1
                trigger_position = trigger_position - goldenrun_tb_info.at[idtbinfo, 'ins_count']
            else:
                for filt in filter_lists:
                    if filt[0] == goldenrun_tb_info.at[idtbinfo, 'id']:
                        ins = filt[len(filt) - trigger_position]
                        trigger_position = 0
                        break
        else:
            tb_id = goldenrun_tb_exec.at[idx, 'tb']
            for filt in filter_lists:
                """found matching filter"""
                if filt[0] == tb_id:
                    for i in range(0, len(filt), 1):
                        if filt[i] == ins:
                            is_first_instruction = 1
                            """Case ins is in the current tb"""
                            if i >= trigger_position:
                                i = i - trigger_position
                                ins = filt[i]
                                trigger_position = 0
                            else:
                                """Case ins is not in the current tb"""
                                trigger_position = trigger_position - i
                                idx = idx - 1
                            break
    logger.info("Found trigger for faulting instruction address {} at {}".format(fault_address, ins))
    return ins


def calculate_trigger_addresses(fault_list, goldenrun_tb_exec, goldenrun_tb_info):
    """"""
    "check every fault list"
    cachelist = []
    lists = build_filters(goldenrun_tb_info)
    for l in lists:
        l = l.reverse()
    for faults in fault_list:
        "Check each fault"
        for fault in faults['faultlist']:
            if fault.trigger.address < 0:
                if fault.trigger.hitcounter != 0:
                    found = False
                    for tdict in cachelist:
                        if tdict['faultaddress'] == fault.address:
                            if tdict['triggerhitcounter'] == fault.trigger.hitcounter:
                                if tdict['triggeraddress'] == fault.trigger.address:
                                    fault.trigger.address = tdict['answer']
                                    found = True
                                    break
                    if found is False:
                        tbs = search_for_fault_location(lists,
                                                       fault.trigger.address,
                                                       fault.address,
                                                       fault.trigger.hitcounter,
                                                       goldenrun_tb_exec,
                                                       goldenrun_tb_info)
                        d = {}
                        d['faultaddress'] = fault.address
                        d['triggerhitcounter'] = fault.trigger.hitcounter
                        d['triggeraddress'] = fault.trigger.address
                        d['answer'] = tbs
                        cachelist.insert(0, d)
                        fault.trigger.address = tbs
