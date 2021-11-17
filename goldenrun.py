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
    goldenrun_config = {}
    dummyfault = Fault(0, 0, 0, 0, 0, 0, 100)
    dummyfaultlist = []
    dummyfaultlist.append(dummyfault)
    queue_output = Queue()
    data_end = {}
    goldenrun_config["qemu"] = config_qemu["qemu"]
    goldenrun_config["kernel"] = config_qemu["kernel"]
    goldenrun_config["plugin"] = config_qemu["plugin"]
    goldenrun_config["machine"] = config_qemu["machine"]
    goldenrun_config["max_instruction_count"] = 10000000000000
    if "memorydump" in config_qemu:
        goldenrun_config["memorydump"] = config_qemu["memorydump"]
    if "start" in config_qemu:
        goldenrun_config["end"] = config_qemu["start"]
        logger.info("Start testing and recording firmware till start")
        python_worker(
            dummyfaultlist,
            goldenrun_config,
            -2,
            queue_output,
            qemu_output,
            None,
            False,
            None,
            qemu_pre,
            qemu_post,
        )
        data_start = queue_output.get()
        if data_start["endpoint"] == 1:
            logger.info("Start successfully reached")
        else:
            logger.critical(
                "Start not reached. Was not reached after {} tb counts. Probably an error.".format(
                    goldenrun_config["max_instruction_count"]
                )
            )
            raise ValueError(
                "Start not reached. Probably no valid instruction! If valid increase tb max for golden run"
            )
        data_queue.put(data_start)
    if "end" in config_qemu:
        goldenrun_config["end"] = config_qemu["end"]
        if "start" in config_qemu:
            goldenrun_config["start"] = config_qemu["start"]
        logger.info("End testing and recording firmware from start till end")
        python_worker(
            dummyfaultlist,
            goldenrun_config,
            -1,
            queue_output,
            qemu_output,
            None,
            False,
            None,
            qemu_pre,
            qemu_post,
        )
        data_end = queue_output.get()
        if data_end["endpoint"] == 1:
            logger.info("End point successfully reached")
        else:
            logger.critical(
                "End point not reached. Was not reached after {} tb counts. Probably an error.".format(
                    goldenrun_config["max_instruction_count"]
                )
            )
            raise ValueError(
                "End point not reached. Probably not valid instruction! If valid increase tb max for golden run"
            )
        data_queue.put(data_end)
        tbexec = pd.DataFrame(data_end["tbexec"])
        tbinfo = pd.DataFrame(data_end["tbinfo"])
        calculate_trigger_addresses(faultconfig, tbexec, tbinfo)
        faultconfig = checktriggers_in_tb(faultconfig, data_end)
        ins_max_absolut = 0
        for tb in data_end["tbinfo"]:
            ins_max_absolut = ins_max_absolut + tb["num_exec"] * tb["ins_count"]
        ins_max_absolut = ins_max_absolut + config_qemu["max_instruction_count"]
        logger.info("Max instruction count is {}".format(ins_max_absolut))
    return [ins_max_absolut, data_end, faultconfig]


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
                faultdescription["del"] = True
                continue

            if find_insn_addresses_in_tb(fault.trigger.address, data):
                valid_triggers.append(fault.trigger.address)
                continue

            invalid_triggers.append(fault.trigger.address)
            faultdescription["del"] = True

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

    logger.info("Convert to pandas")
    tmp = pd.DataFrame(faultconfig)
    logger.info("filter for del items")
    idx = tmp.index[tmp["del"] == True]
    logger.info("remove del items")
    tmp.drop(idx, inplace=True)
    logger.info("fix index")
    tmp.reset_index(drop=True, inplace=True)
    tmp["index"] = tmp.index
    logger.info("convert back")
    faultconfig = tmp.to_dict("records")
    print(faultconfig[0])
    print(len(faultconfig))
    return faultconfig
