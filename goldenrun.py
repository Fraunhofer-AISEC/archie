from faultclass import Fault
from faultclass import python_worker

import pandas as pd

from calculate_trigger import calculate_trigger_addresses

from multiprocessing import Queue

import logging

logger = logging.getLogger(__name__)


def run_goldenrun(
    config_qemu, qemu_output, data_queue, faultconfig, qemu_pre=None, qemu_post=None
):
    dummyfaultlist = [Fault(0, 0, 0, 0, 0, 0, 100, 0)]

    queue_output = Queue()

    goldenrun_config = {}
    goldenrun_config["qemu"] = config_qemu["qemu"]
    goldenrun_config["kernel"] = config_qemu["kernel"]
    goldenrun_config["plugin"] = config_qemu["plugin"]
    goldenrun_config["machine"] = config_qemu["machine"]
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
            goldenrun_config["end"] = config_qemu["start"]
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
        if experiment["data"]["endpoint"] == 1:
            logger.info(f"{experiment['type']} successfully finished.")
        else:
            logger.critical(
                f"{experiment['type']} not finished after "
                f"{goldenrun_config['max_instruction_count']} tb counts."
            )
            raise ValueError(
                f"{experiment['type']} not finished. Probably no valid instruction! "
                f"If valid increase tb max for golden run"
            )
        data_queue.put(experiment["data"])

        if experiment["type"] != "goldenrun":
            continue

        tbexec = pd.DataFrame(experiment["data"]["tbexec"])
        tbinfo = pd.DataFrame(experiment["data"]["tbinfo"])
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
    tmp = tmp.query("delete == False")
    tmp.reset_index(drop=True, inplace=True)
    tmp["index"] = tmp.index
    faultconfig = tmp.to_dict("records")

    logger.info(f"{len(faultconfig)}/{len_faultlist} faults passed the filter.")

    return faultconfig
