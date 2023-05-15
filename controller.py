#!/usr/bin/env python3

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

import argparse
import logging
import lzma
from multiprocessing import Manager, Process
from pathlib import Path
import pickle
import subprocess
import sys
import time

import pandas as pd
import prctl
from tqdm import tqdm

try:
    import json5 as json

    print("Found JSON5 library")
except ModuleNotFoundError:
    import json

    pass

from faultclass import detect_type, detect_model, Fault, Trigger
from faultclass import python_worker
from hdf5logger import hdf5collector
from goldenrun import run_goldenrun

clogger = logging.getLogger(__name__)


def build_ranges_dict(fault_dict):
    """
    build range, however allows to define type with a dict.
    """
    if fault_dict["type"] == "shift":
        ret = []
        if len(fault_dict["range"]) != 3:
            raise ValueError("For Shift 3 element list is needed")
        for i in range(fault_dict["range"][1], fault_dict["range"][2], 1):
            ret.append(fault_dict["range"][0] << i)
        return ret
    elif fault_dict["type"] == "dict":
        return [fault_dict["dict"]]
    raise ValueError("No known type for this framework {}".format(fault_dict))


def build_ranges(fault_range, wildcard=False):
    """
    Build a range based on fault_range which is either of type int, dict, or list

    isinstance(fault_range, list):
    ------------------------------
    fault_range of type list can contain at most three elements. The parsing
    depends on the element count similar to range. Three formats are supported:
        len(fault_range) == 1:    range(start=fault_range[0], stop=fault_range[0] + 1)
        len(fault_range) == 2:    range(start=fault_range[0], stop=fault_range[1])
        len(fault_range) == 3:    range(start=fault_range[0],
                                        stop=fault_range[1],
                                        step=fault_range[2])

    Be aware that for len(fault_range) == 1 this function behaves differently than range!
    """

    if isinstance(fault_range, int):
        return range(fault_range, fault_range + 1)

    if isinstance(fault_range, dict):
        return build_ranges_dict(fault_range)

    assert isinstance(
        fault_range, list
    ), "Invalid fault_range type: {type(fault_range)}"
    assert len(fault_range) in range(1, 4), f"Invalid fault_range length: {fault_range}"

    if not wildcard:
        start = fault_range[0]
        stop = fault_range[1] if len(fault_range) >= 2 else fault_range[0] + 1
        step = fault_range[2] if len(fault_range) == 3 else 1  # Default step is 1
        return range(start, stop, step)

    # Build wildcard_range
    wildcard_range = {"start": Trigger(0, 0), "end": Trigger(0, 0)}

    range_element = "start"
    for entry in fault_range:
        if entry == "*":
            # Got wildcard element,
            # either parsing the range end element next
            # or return if fault_range does only contain an asterisk
            range_element = "end"
            continue

        wildcard_range[range_element].hitcounter = 1  # Default hitcounter is 1

        if isinstance(entry, int):
            wildcard_range[range_element].address = entry
            continue

        # Split "address/hitcounter" string
        entry_expanded = entry.split("/")
        assert len(entry_expanded) <= 2, f"Invalid fault_range entry: {entry}"

        wildcard_range[range_element].address = int(entry_expanded[0], base=0)
        if len(entry_expanded) == 2:
            wildcard_range[range_element].hitcounter = int(entry_expanded[1], base=0)

    # Set local wildcard mode
    wildcard_range["local"] = (
        fault_range != ["*"]
        and wildcard_range["start"].hitcounter == 0
        and wildcard_range["end"].hitcounter == 0
    )

    return [wildcard_range]


def build_fault_list(conf_list, combined_faults, ret_faults):
    """
    Unrolling of multiple faults, that are combined. Will use recursive until
    no fault in list is remaining. Then build unrolled fault list, that has
    lists inside of faults executed together
    """
    wildcard_fault = False
    ret_int_faults = ret_faults
    faultdev = conf_list.pop()
    if "fault_livespan" in faultdev:
        print(
            "Unknown fault configuration property 'fault_livespan'. Did you "
            "mean 'fault_lifespan'?"
        )
        exit(1)
    if "num_bytes" not in faultdev:
        faultdev["num_bytes"] = [0]
    if faultdev["fault_address"] == "*":
        faultdev["fault_address"] = ["*"]
    if type(faultdev["fault_address"]) == list and "*" in faultdev["fault_address"]:
        wildcard_fault = True

    ftype = detect_type(faultdev["fault_type"])
    fmodel = detect_model(faultdev["fault_model"])

    faddress_exclude = (
        [build_ranges(lst) for lst in faultdev["fault_address_exclude"]]
        if "fault_address_exclude" in faultdev
        else []
    )

    for faddress in build_ranges(faultdev["fault_address"], wildcard_fault):
        # At this time we can only filter "explicit" fault addresses (non-wildcard)
        # Wildcard faults have to be filtered after the execution of the goldenrun
        # to be aware of the executed instructions (within generate_wildcard_faults)
        if any(faddress in region for region in faddress_exclude):
            clogger.debug(f"Exclude {faddress_exclude} filtered {hex(faddress)}")
            continue

        for flifespan in build_ranges(faultdev["fault_lifespan"]):
            for fmask in build_ranges(faultdev["fault_mask"]):
                for taddress in build_ranges(faultdev["trigger_address"]):
                    for tcounter in build_ranges(faultdev["trigger_counter"]):
                        for numbytes in build_ranges(faultdev["num_bytes"]):
                            if isinstance(fmask, dict):
                                assert (
                                    wildcard_fault
                                ), "only wildcard faults can be evaluated, if fault.mask is a dict"
                                assert ftype == detect_type(
                                    "instruction"
                                ), "fault.type has to be 'instruction', if fault.mask is a dict"
                                assert fmodel == detect_model(
                                    "overwrite"
                                ), "fault.model has to be 'overwrite', if fault.mask is a dict"
                                assert (
                                    numbytes == 0
                                ), "numbytes is overwritten, if fault.mask is a dict"

                            int_faults = (
                                combined_faults.copy()
                            )  # copy list, otherwise int fault referres to the same list as combined_faults
                            if faddress == -1:
                                faddress = taddress

                            int_faults.append(
                                Fault(
                                    faddress,
                                    faddress_exclude,
                                    ftype,
                                    fmodel,
                                    flifespan,
                                    fmask,
                                    taddress,
                                    tcounter,
                                    numbytes,
                                    wildcard_fault,
                                )
                            )
                            if len(conf_list) == 0:
                                ret_int_faults.append(int_faults)
                            else:
                                ret_int_faults = build_fault_list(
                                    conf_list.copy(), int_faults.copy(), ret_faults
                                )
    return ret_int_faults


def mem_limit_calc(mem_max, num_worker, queue_depth, time_max):
    if mem_max > 1500000:
        mem_estimate = mem_max * num_worker * 1.5 + queue_depth * mem_max
    else:
        mem_estimate = 1600000 * num_worker + queue_depth * mem_max
    time_max = 1 + time_max / 120.0
    mem_estimate = mem_estimate * time_max
    return mem_estimate


def get_system_ram():
    command = "cat /proc/meminfo"
    ps = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    tmp, _ = ps.communicate()
    sp = str(tmp).split("kB")
    t = sp[0]
    mem = int(t.split(":")[1], 0)
    clogger.debug("system ram is {}kB".format(mem))
    return mem


def controller(
    hdf5path,
    hdf5mode,
    faultlist,
    config_qemu,
    num_workers,
    queuedepth,
    compressionlevel,
    qemu_output,
    goldenrun_only,
    istart,
    iend,
    goldenrun=True,
    logger=hdf5collector,
    qemu_pre=None,
    qemu_post=None,
    logger_postprocess=None,
):
    """
    This function builds the unrolled fault structure, performs golden run and
    then schedules the worker depending on ram usage and allowed number of
    workers
    """
    clogger.info("Controller start")

    t0 = time.time()

    m = Manager()
    m2 = Manager()
    queue_output = m.Queue()
    queue_ram_usage = m2.Queue()

    prctl.set_name("Controller")
    prctl.set_proctitle("Python_Controller")

    # Write flags to HDF5
    queue_output.put(config_qemu)

    # Storing and restoring goldenrun_data with pickle is a temporary fix
    # A better solution is to parse the goldenrun_data from the existing hdf5 file
    goldenrun_data = {}
    if goldenrun:
        [
            config_qemu["max_instruction_count"],
            goldenrun_data,
            faultlist,
        ] = run_goldenrun(
            config_qemu, qemu_output, queue_output, faultlist, qemu_pre, qemu_post
        )
        pickle.dump(
            (config_qemu["max_instruction_count"], goldenrun_data, faultlist),
            lzma.open("bkup_goldenrun_results.xz", "wb"),
        )

        clogger.info(f"Got {len(faultlist)} fault entries")
        if goldenrun_only:
            return config_qemu
    else:
        (
            config_qemu["max_instruction_count"],
            goldenrun_data,
            faultlist,
        ) = pickle.load(lzma.open("bkup_goldenrun_results.xz", "rb"))

    if iend != -1:
        faultlist = faultlist[: iend + 1]

    if istart != -1:
        faultlist = faultlist[istart:]

    p_logger = Process(
        target=logger,
        args=(
            hdf5path,
            hdf5mode,
            queue_output,
            len(faultlist),
            compressionlevel,
            logger_postprocess,
        ),
    )

    p_logger.start()

    p_list = []

    p_time_list = []
    p_time_list.append(60)
    p_time_mean = 60

    times = []
    time_max = 0

    mem_list = []
    max_ram = get_system_ram() * 0.8 - 2000000
    mem_max = max_ram / 2
    mem_list.append(max_ram / (num_workers))

    keywords = ["tbexec", "tbinfo", "meminfo", "armregisters", "riscvregisters"]
    for keyword in keywords:
        if keyword not in goldenrun_data:
            continue
        goldenrun_data[keyword] = pd.DataFrame(goldenrun_data[keyword])

    if len(faultlist) != 0:
        clogger.info("Simulating faults")

    pbar = tqdm(total=len(faultlist))
    itter = 0
    while 1:
        if len(p_list) == 0 and itter == len(faultlist):
            clogger.debug("Done inserting qemu jobs")
            break

        if (
            mem_limit_calc(mem_max, len(p_list), queue_output.qsize(), time_max)
            < max_ram
            and len(p_list) < num_workers
            and itter < len(faultlist)
            and queue_output.qsize() < queuedepth
        ):
            faults = faultlist[itter]
            itter += 1

            p = Process(
                name=f"worker_{faults['index']}",
                target=python_worker,
                args=(
                    faults["faultlist"],
                    config_qemu,
                    faults["index"],
                    queue_output,
                    qemu_output,
                    goldenrun_data,
                    True,
                    queue_ram_usage,
                    qemu_pre,
                    qemu_post,
                ),
            )
            p.start()
            p_list.append({"process": p, "start_time": time.time()})
            clogger.debug(f"Started worker {faults['index']}. Running: {len(p_list)}.")
            clogger.debug(f"Fault address: {faults['faultlist'][0].address}")
            clogger.debug(
                f"Fault trigger address: {faults['faultlist'][0].trigger.address}"
            )
        else:
            time.sleep(0.005)  # wait for workers to finish, scheduler can wait

        for i in range(queue_ram_usage.qsize()):
            mem = queue_ram_usage.get_nowait()
            mem_list.append(mem)

        if len(mem_list) > 6 * num_workers + 4:
            del mem_list[0 : len(mem_list) - 6 * num_workers + 4]
        mem_max = max(mem_list)

        # Calculate length of running processes
        times.clear()
        time_max = 0
        current_time = time.time()
        for i in range(len(p_list)):
            p = p_list[i]
            tmp = current_time - p["start_time"]
            # If the current processing time is lower than moving average, do not punish the time
            if tmp < p_time_mean:
                times.append(0)
            else:
                times.append(tmp - p_time_mean)
        # Find max time in list (This list will show the longest running
        # process minus the moving average)
        if len(times) > 0:
            time_max = max(times)

        for i in range(len(p_list)):
            p = p_list[i]
            # Find finished processes
            p["process"].join(timeout=0)
            if p["process"].is_alive() is False:
                # Update the progress bar
                pbar.update(1)
                # Recalculate moving average
                p_time_list.append(current_time - p["start_time"])
                len_p_time_list = len(p_time_list)
                if len_p_time_list > num_workers + 2:
                    p_time_list.pop(0)
                p_time_mean = sum(p_time_list) / len_p_time_list
                clogger.debug("Current running Average {}".format(p_time_mean))
                # Remove process from list
                p_list.pop(i)
                break

    clogger.debug("{} experiments remaining in queue".format(queue_output.qsize()))
    pbar.close()
    p_logger.join()

    clogger.debug("Done with qemu and logger")

    t1 = time.time()
    m, s = divmod(t1 - t0, 60)
    h, m = divmod(m, 60)
    clogger.info(
        "Took {}:{}:{} to complete all experiments".format(int(h), int(m), int(s))
    )

    if len(faultlist) != 0:
        tperindex = (t1 - t0) / len(faultlist)
    else:
        tperindex = (t1 - t0)

    tperworker = tperindex / num_workers
    clogger.debug(
        "Took average of {}s per fault, python worker rough runtime is {}s".format(
            tperindex, tperworker
        )
    )

    clogger.debug("controller exit")
    return config_qemu


def get_argument_parser():
    parser = argparse.ArgumentParser(
        description="Read args for qemu fault injection tool"
    )
    parser.add_argument(
        "--qemu",
        "-q",
        help="Configuration for qemu. Needs to contain path to qemu, kernel and plugin in json format",
        type=argparse.FileType("r", encoding="UTF-8"),
        required=True,
    )
    parser.add_argument(
        "--faults",
        "-f",
        help="Faults for qemu. Needs to contain a valid config for faults",
        type=argparse.FileType("r", encoding="UTF-8"),
        required=True,
    )
    parser.add_argument(
        "--indexbase",
        "-b",
        help="Move index-base to arbitrary number. It is used in the hdf5 file",
        type=int,
        required=False,
    )
    parser.add_argument("hdf5file", help="Destination of hdf5 file")
    parser.add_argument(
        "--append",
        "-a",
        action="store_true",
        help="append data to file instead of overwriting it",
        required=False,
    )
    parser.add_argument(
        "--worker",
        "-w",
        help="Number of workers spawned. Default 1",
        type=int,
        required=False,
    )
    parser.add_argument(
        "--queuedepth",
        help="Maximum number of elements in queue before scheduler blocks start of new workers. This allows to control the memory usage, default is 15",
        type=int,
        required=False,
    )
    parser.add_argument(
        "--compressionlevel",
        "-c",
        help="Set the compression level inside the hdf5 file. Valid values are between 0 to 9, 0 is no compression, 1 the highest, 9 the least. Default 1",
        type=int,
        required=False,
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="This enables the output of qemu for debug purposes",
        required=False,
    )
    parser.add_argument(
        "--gdb",
        action="store_true",
        help="Enables connection to the target with gdb. Port 1234",
        required=False,
    )
    parser.add_argument(
        "--disable-ring-buffer",
        help="Disable use of the ring buffer for storing TB execution order information",
        action="store_true",
        required=False,
    )
    parser.add_argument(
        "--goldenrun-only",
        help="Only run goldenrun to create the goldenrun backup file",
        action="store_true",
        required=False,
    )
    parser.add_argument(
        "--istart",
        "-s",
        help="Index of fault in fault list to start with",
        type=int,
        required=False,
        default=-1,
    )
    parser.add_argument(
        "--iend",
        "-e",
        help="Index of fault in fault list to end with",
        type=int,
        required=False,
        default=-1,
    )
    return parser


def process_arguments(args):
    parguments = {}
    if args.append is False:
        parguments["hdf5mode"] = "w"
        parguments["goldenrun"] = True
    else:
        parguments["hdf5mode"] = "a"
        parguments["goldenrun"] = False

    indexbase = args.indexbase
    if args.indexbase is None:
        indexbase = 0

    parguments["num_workers"] = args.worker
    if args.worker is None:
        parguments["num_workers"] = 1

    parguments["queuedepth"] = args.queuedepth
    if args.queuedepth is None:
        parguments["queuedepth"] = 15

    parguments["compressionlevel"] = args.compressionlevel
    if args.compressionlevel is None:
        parguments["compressionlevel"] = 1

    hdf5file = Path(args.hdf5file)
    if hdf5file.parent.exists() is False:
        print(
            f"Parent folder of specified HDF5 file does not exist: "
            f"{hdf5file.parent}"
        )
        exit(1)

    parguments["goldenrun_only"] = args.goldenrun_only
    if parguments["goldenrun_only"]:
        parguments["goldenrun"] = True

    parguments["istart"] = args.istart
    parguments["iend"] = args.iend

    qemu_conf = json.load(args.qemu)
    args.qemu.close()
    print(qemu_conf)
    if args.gdb:
        qemu_conf["gdb"] = True
        # hard set to 1 worker, because all qemus use the same port
        parguments["num_workers"] = 1
    if "additional_qemu_args" not in qemu_conf:
        qemu_conf["additional_qemu_args"] = ""
    if "bios" not in qemu_conf:
        qemu_conf["bios"] = ""

    faultlist = json.load(args.faults)
    if "start" in faultlist:
        if faultlist["start"]["counter"] == 0:
            print("A start counter of 0 in the fault configuration is invalid")
            exit(1)

        qemu_conf["start"] = faultlist["start"]
    if "end" in faultlist:
        if type(faultlist["end"]) == dict:
            faultlist["end"] = [faultlist["end"]]
        for endpoint in faultlist["end"]:
            if endpoint["counter"] == 0:
                print("An end counter of 0 in the fault configuration is invalid")
                exit(1)

        qemu_conf["end"] = faultlist["end"]

    if "memorydump" in faultlist:
        qemu_conf["memorydump"] = faultlist["memorydump"]
    if "max_instruction_count" in faultlist:
        qemu_conf["max_instruction_count"] = faultlist["max_instruction_count"]
    else:
        print("WARNING: missing max_instruction_count in json")
        qemu_conf["max_instruction_count"] = 100

    # If value not specified use the default one
    qemu_conf["tb_exec_list"] = faultlist.get("tb_exec_list", True)
    qemu_conf["tb_info"] = faultlist.get("tb_info", True)
    qemu_conf["mem_info"] = faultlist.get("mem_info", False)
    qemu_conf["ring_buffer"] = faultlist.get("ring_buffer", True)

    # Command line argument takes precedence
    if args.disable_ring_buffer:
        qemu_conf["ring_buffer"] = False

    parguments["qemu_conf"] = qemu_conf

    ret_list = []
    for faults in faultlist["faults"]:
        tmp_list = []
        ret_list = build_fault_list(faults, tmp_list, ret_list)

    faultlist.clear()
    faultlist = []
    for i in range(len(ret_list)):
        faultconfig = {}
        faultconfig["index"] = i + indexbase
        faultconfig["faultlist"] = ret_list.pop()
        faultconfig["delete"] = False
        faultlist.append(faultconfig)

    parguments["faultlist"] = faultlist
    return parguments


def init_logging():
    logging_level = logging.INFO
    handler_list = []

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)
    handler_list.append(stream_handler)

    if args.debug:
        file_handler = logging.FileHandler("log.txt")
        handler_list.append(file_handler)
        logging_level = logging.DEBUG

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s : %(message)s",
        level=logging_level,
        handlers=handler_list,
    )


if __name__ == "__main__":
    """
    Main function to programm
    """

    parser = get_argument_parser()
    args = parser.parse_args()

    parguments = process_arguments(args)

    init_logging()

    controller(
        args.hdf5file,  # hdf5path
        parguments["hdf5mode"],  # hdf5mode
        parguments["faultlist"],  # faultlist
        parguments["qemu_conf"],  # config_qemu
        parguments["num_workers"],  # num_workers
        parguments["queuedepth"],  # queuedepth
        parguments["compressionlevel"],  # compressionlevel
        args.debug,  # qemu_output
        parguments["goldenrun_only"],
        parguments["istart"],
        parguments["iend"],
        parguments["goldenrun"],  # goldenrun
        hdf5collector,  # logger
        None,  # qemu_pre
        None,  # qemu_post
        None,  # logger_postprocess
    )
