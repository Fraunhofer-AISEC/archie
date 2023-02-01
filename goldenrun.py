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

import copy
import logging
from multiprocessing import Queue

import pandas as pd

from calculate_trigger import calculate_trigger_addresses
from faultclass import Fault
from faultclass import python_worker


logger = logging.getLogger(__name__)


def run_goldenrun(
    config_qemu, qemu_output, data_queue, faultconfig, qemu_pre=None, qemu_post=None
):
    dummyfaultlist = [Fault(0, 0, 0, 0, 0, 0, 100, 0, False)]

    queue_output = Queue()

    goldenrun_config = {}
    goldenrun_config["qemu"] = config_qemu["qemu"]
    goldenrun_config["kernel"] = config_qemu["kernel"]
    goldenrun_config["plugin"] = config_qemu["plugin"]
    goldenrun_config["machine"] = config_qemu["machine"]
    goldenrun_config["additional_qemu_args"] = config_qemu["additional_qemu_args"]
    goldenrun_config["bios"] = config_qemu["bios"]
    goldenrun_config["ring_buffer"] = config_qemu["ring_buffer"]
    if "mem_info" in config_qemu:
        goldenrun_config["mem_info"] = config_qemu["mem_info"]
    if "max_instruction_count" in config_qemu:
        goldenrun_config["max_instruction_count"] = config_qemu["max_instruction_count"]
    if "memorydump" in config_qemu:
        goldenrun_config["memorydump"] = config_qemu["memorydump"]

    experiments = []
    if "start" in config_qemu:
        pre_goldenrun = {"type": "pre_goldenrun", "index": -2, "data": {}}
        experiments.append(pre_goldenrun)
    goldenrun = {"type": "goldenrun", "index": -1, "data": {}}
    experiments.append(goldenrun)

    for experiment in experiments:
        if experiment["type"] == "pre_goldenrun":
            goldenrun_config["end"] = [config_qemu["start"]]
            # Set max_insn_count to ridiculous high number to never reach it
            goldenrun_config["max_instruction_count"] = 10000000000000

        elif experiment["type"] == "goldenrun":
            if "start" in config_qemu:
                goldenrun_config["start"] = config_qemu["start"]
            if "end" in config_qemu:
                goldenrun_config["end"] = config_qemu["end"]
            if "start" in config_qemu and "end" in config_qemu:
                # Set max_insn_count to ridiculous high number to never reach it
                goldenrun_config["max_instruction_count"] = 10000000000000

        logger.info(f"{experiment['type']} started...")
        python_worker(
            dummyfaultlist,
            goldenrun_config,
            experiment["index"],
            queue_output,
            qemu_output,
            None,
            False,
            None,
            qemu_pre,
            qemu_post,
        )
        experiment["data"] = queue_output.get()
        if experiment["data"]["end_reason"] == "max tb":
            logger.critical(
                f"{experiment['type']} not finished after "
                f"{goldenrun_config['max_instruction_count']} tb counts."
            )
            raise ValueError(
                f"{experiment['type']} not finished. Probably no valid instruction! "
                f"If valid increase tb max for golden run"
            )

        logger.info(f"{experiment['type']} successfully finished.")
        data_queue.put(experiment["data"])

        if experiment["type"] != "goldenrun":
            continue

        tbexec = pd.DataFrame(experiment["data"]["tbexec"])
        tbinfo = pd.DataFrame(experiment["data"]["tbinfo"])
        process_wildcard_faults(faultconfig, tbexec, tbinfo)
        calculate_trigger_addresses(faultconfig, tbexec, tbinfo)
        faultconfig = checktriggers_in_tb(faultconfig, experiment["data"])

        if "end" in config_qemu:
            for tb in experiment["data"]["tbinfo"]:
                config_qemu["max_instruction_count"] += tb["num_exec"] * tb["ins_count"]
            logger.info(
                "Max instruction count is {}".format(
                    config_qemu["max_instruction_count"]
                )
            )

    return [config_qemu["max_instruction_count"], experiment["data"], faultconfig]


def find_insn_addresses_in_tb(insn_address, data):
    tb_list_found = []
    tbinfolist = data["tbinfo"]
    for tbinfo in tbinfolist:
        if (insn_address >= tbinfo["id"]) and (
            insn_address < tbinfo["id"] + tbinfo["size"]
        ):
            tb_list_found.append(tbinfo)

    if len(tb_list_found) == 0:
        return False
    else:
        return True


def checktriggers_in_tb(faultconfig, data):
    valid_triggers = []
    invalid_triggers = []
    for faultdescription in faultconfig:
        logger.info(
            "Check Fault {}/{} for valid trigger".format(
                faultdescription["index"] + 1, len(faultconfig)
            )
        )
        for fault in faultdescription["faultlist"]:
            if fault.trigger.address in valid_triggers:
                continue

            if fault.trigger.address in invalid_triggers:
                faultdescription["delete"] = True
                continue

            if find_insn_addresses_in_tb(fault.trigger.address, data):
                valid_triggers.append(fault.trigger.address)
                continue

            """
            If Fault is instruction fault and hitcounter 0 let it pass independent
            of the fault trigger address, as it is not used by the faultplugin
            """
            if fault.trigger.hitcounter == 0 and fault.model == 3:
                continue

            invalid_triggers.append(fault.trigger.address)
            faultdescription["delete"] = True

            error_message = (
                f"Trigger address {fault.trigger.address} not found in tbs "
                f"executed in golden run! \nInvalid fault description: "
                f"{faultdescription}"
            )
            for fault in faultdescription["faultlist"]:
                error_message += (
                    f"\nfault: {fault}, "
                    f"triggeraddress: {fault.trigger.address}, "
                    f"faultaddress: {fault.address}"
                )
            logger.critical(error_message)

    logger.info("Filtering faultlist ...")
    len_faultlist = len(faultconfig)

    tmp = pd.DataFrame(faultconfig)
    tmp = tmp.query("delete == False").copy()
    tmp.reset_index(drop=True, inplace=True)
    tmp["index"] = tmp.index
    faultconfig = tmp.to_dict("records")

    logger.info(f"{len(faultconfig)}/{len_faultlist} faults passed the filter.")

    return faultconfig


def generate_wildcard_faults(fault, tbexec, tbinfo):
    # Initialize list of TBs used during fault generation
    tb_start = tbinfo["id"].copy()
    tb_start.index = tbinfo["id"]

    tb_end = tbinfo["id"] + tbinfo["size"] - 1
    tb_end.index = tbinfo["id"]

    tb_hitcounters = pd.DataFrame(
        {
            "hitcounter": pd.Series(0, index=tbinfo["id"]),
            "tb_start": tb_start,
            "tb_end": tb_end,
        }
    )

    wildcard_faults = []
    range_start_counter = fault.address["start"].hitcounter
    range_end_counter = 0
    wildcard_range_end_reached = False
    wildcard_local_active = False

    for tb in tbexec["tb"]:
        tb_hitcounters_analyzed = False
        # Instruction-specific hitcounters
        instr_hitcounters = []

        # Get and update TB-specific hitcounter
        tb_hitcounter = tb_hitcounters.loc[tb, "hitcounter"]
        tb_hitcounters.loc[tb, "hitcounter"] += 1

        # Iterate over instructions in the translation block
        tb_info_asm = tbinfo.at[tbinfo.index[tbinfo["id"] == tb][0], "assembler"]
        tb_info_asm = tb_info_asm.split("[ ")

        for i in range(1, len(tb_info_asm)):
            instr = int(tb_info_asm[i].split("]")[0], 16)

            # Evaluate start and stop conditions (global)

            # Detect range end address if specified (hitcounter != 0)
            if fault.address["end"].hitcounter != 0:
                if instr == fault.address["end"].address:
                    range_end_counter += 1

                    # Range start and end conditions met, stop after this
                    # instruction
                    if (
                        range_start_counter == 0
                        and range_end_counter == fault.address["end"].hitcounter
                    ):
                        wildcard_range_end_reached = True

            # If we already encountered the range start address, the counter
            # will be 0. If no range start address is specified, it will be 0
            # as well.
            if range_start_counter != 0:
                if instr == fault.address["start"].address:
                    range_start_counter -= 1
                else:
                    continue

                if range_start_counter != 0:
                    # Range start condition is not met. It will also not be met
                    # with the remaining instructions in the current TB. We
                    # continue anyways in case the range end address is in the
                    # current TB to update the range_end_counter.
                    continue

            # Evaluate start and stop conditions (local)

            if fault.address["local"]:
                # Start local wildcard range
                if instr == fault.address["start"].address:
                    wildcard_local_active = True

                if wildcard_local_active is False:
                    continue

                # Stop local wildcard fault generation with this instruction
                # until the next range start address is found
                if instr == fault.address["end"].address:
                    wildcard_local_active = False

            # Analyze TB to find TB and instruction specific adjustments to
            # the hitcounter of the expanded fault

            if tb_hitcounters_analyzed is False:
                tb_hitcounters_analyzed = True

                # Are we a sub-TB?
                sub_tbs = tb_hitcounters[
                    (tb > tb_hitcounters["tb_start"]) & (tb <= tb_hitcounters["tb_end"])
                ]

                for _, sub_tb_data in sub_tbs.iterrows():
                    tb_hitcounter += sub_tb_data["hitcounter"]

                # Calculate instruction-specific hitcounter -> do we contain
                # sub-TBs?
                last_instr = tb_hitcounters.loc[tb, "tb_end"]

                sub_tbs = tb_hitcounters[
                    (tb < tb_hitcounters["tb_start"])
                    & (last_instr > tb_hitcounters["tb_start"])
                    & (last_instr <= tb_hitcounters["tb_end"])
                ]

                for _, sub_tb_data in sub_tbs.iterrows():
                    instr_hitcounters.append(
                        {
                            "start_address": sub_tb_data["tb_start"],
                            "hitcounter": sub_tb_data["hitcounter"],
                        }
                    )

            # Generate expanded wildcard fault

            # Copy wildcard fault and modify it to target the current
            # instruction
            instr_fault = copy.deepcopy(fault)
            instr_fault.wildcard = False
            instr_fault.address = instr
            # Add TB-specific hitcounter
            instr_fault.trigger.hitcounter = 1 + tb_hitcounter

            # Add instruction-specific hitcounter if present
            for instr_hitcounter in instr_hitcounters:
                if instr >= instr_hitcounter["start_address"]:
                    instr_fault.trigger.hitcounter += instr_hitcounter["hitcounter"]

            wildcard_faults.append(instr_fault)

            if wildcard_range_end_reached:
                break

        if wildcard_range_end_reached:
            break

    # Detect unmet range conditions

    if range_start_counter != 0:
        logger.critical(
            "Start of wildcard fault range not encountered: address "
            f"0x{fault.address['start'].address:x}, hitcounter "
            f"{fault.address['start'].hitcounter}"
        )
        exit(1)

    if fault.address["end"].hitcounter != 0 and wildcard_range_end_reached is False:
        logger.critical(
            "End of wildcard fault range not encountered: address "
            f"0x{fault.address['end'].address:x}, hitcounter "
            f"{fault.address['end'].hitcounter}"
        )
        exit(1)

    return wildcard_faults


def process_wildcard_faults(faultconfig, tbexec, tbinfo):
    logger.info("Identifying and processing wildcard faults")

    # Construct index base from last fault entry
    index_base = faultconfig[-1]["index"] + 1

    wildcard_faults = []
    for faultentry in faultconfig:
        expanded_faults = []

        for fault in faultentry["faultlist"]:
            if fault.wildcard:
                wildcard_faults += generate_wildcard_faults(fault, tbexec, tbinfo)

                # The wildcard fault entry has been expanded, mark it for
                # removal
                expanded_faults.append(fault)

        # Remove expanded wildcard fault entries
        for fault in expanded_faults:
            faultentry["faultlist"].remove(fault)
        if len(faultentry["faultlist"]) == 0:
            faultentry["delete"] = True

    # Add generated fault entries to faultconfig
    for i in range(len(wildcard_faults)):
        new_fault_entry = {}
        new_fault_entry["index"] = index_base + i
        new_fault_entry["faultlist"] = [wildcard_faults[i]]
        new_fault_entry["delete"] = False
        faultconfig.append(new_fault_entry)
