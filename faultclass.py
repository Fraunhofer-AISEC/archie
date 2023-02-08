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

from enum import IntEnum
import logging
from multiprocessing import Process
import os
import shlex
import signal
import subprocess
import time

import pandas as pd
import prctl

from emulation_worker import run_unicorn

import protobuf.control_pb2 as control_pb2
import protobuf.data_pb2 as data_pb2
import protobuf.fault_pb2 as fault_pb2
from util import gather_process_ram_usage

TB_EXEC_LIST_CHUNK_SIZE = 10000

logger = logging.getLogger(__name__)
qlogger = logging.getLogger("QEMU-" + __name__)


def detect_type(fault_type):
    """
    Translate type to enum value used in qemu
    """
    if fault_type == "flash" or fault_type == "instruction":
        return 1
    if fault_type == "sram" or fault_type == "data":
        return 0
    if fault_type == "register":
        return 2
    logger.critical(
        "Received wrong type. Expected instruction, data, or register. Got {}".format(
            fault_type
        )
    )
    raise ValueError(
        "A type was not detected. Maybe misspelled? got {} , needed instruction, data, or register".format(
            fault_type
        )
    )


def detect_model(fault_model):
    """
    Translate model to enum value used in qemu
    """
    if fault_model == "set1":
        return 1
    if fault_model == "set0":
        return 0
    if fault_model == "toggle":
        return 2
    if fault_model == "overwrite":
        return 3
    logger.critical(
        "Received wrong model. Expected set0, set1, toggle, or overwrite. Got {}".format(
            fault_model
        )
    )
    raise ValueError(
        "A model was not detected. Maybe misspelled? got {} , needed set0 set1 toggle overwrite".format(
            fault_model
        )
    )


class Timeout:
    raised = False

    def __init__(self):
        signal.signal(signal.SIGINT, self.raise_timeout)
        signal.signal(signal.SIGTERM, self.raise_timeout)

    def raise_timeout(self, *args):
        self.raised = True
        raise KeyboardInterrupt


class Register(IntEnum):
    ARM = 0
    RISCV = 1


class Trigger:
    def __init__(self, trigger_address, trigger_hitcounter):
        """
        Define attributes for trigger
        """
        self.address = trigger_address
        self.hitcounter = trigger_hitcounter


class Fault:
    def __init__(
        self,
        fault_address: int,
        fault_address_exclude: list,
        fault_type: int,
        fault_model: int,
        fault_lifespan: int,
        fault_mask: int,
        trigger_address: int,
        trigger_hitcounter: int,
        num_bytes: int,
        wildcard: bool,
    ):
        """
        Define attributes for fault types
        """
        self.trigger = Trigger(trigger_address, trigger_hitcounter)
        self.address = fault_address
        self.address_exclude = fault_address_exclude
        self.type = fault_type
        self.model = fault_model
        self.lifespan = fault_lifespan
        self.mask = fault_mask
        self.num_bytes = num_bytes
        self.wildcard = wildcard

    def __str__(self):
        return (
            f"{self.trigger.address}"
            f"{self.trigger.hitcounter}"
            f"{self.address}"
            f"{self.type}"
            f"{self.model}"
            f"{self.lifespan}"
            f"{self.mask}"
            f"{self.num_bytes}"
            f"{self.wildcard}"
        )


def write_fault_list_to_pipe(fault_list, fifo):
    fault_pack = fault_pb2.FaultPack()

    for fault_instance in fault_list:
        new_fault = fault_pack.faults.add()

        new_fault.address = fault_instance.address
        new_fault.type = fault_instance.type
        new_fault.model = fault_instance.model
        new_fault.lifespan = fault_instance.lifespan
        new_fault.trigger_address = fault_instance.trigger.address
        new_fault.trigger_hitcounter = fault_instance.trigger.hitcounter

        mask_upper = (fault_instance.mask >> 64) & (pow(2, 64) - 1)
        mask_lower = fault_instance.mask & (pow(2, 64) - 1)

        new_fault.mask_upper = mask_upper
        new_fault.mask_lower = mask_lower

        new_fault.num_bytes = fault_instance.num_bytes

    message_size = fault_pack.ByteSize()
    message_size_string = str(message_size) + "\n"

    n_char_written = fifo.write(message_size_string.encode())
    if n_char_written != len(message_size_string):
        return -1

    out = fault_pack.SerializeToString()

    n_char_written = fifo.write(out)
    if n_char_written != len(out):
        return -1

    fifo.flush()
    return 0


def run_qemu(
    control,
    config,
    data,
    config_qemu,
    qemu_output,
    index,
    qemu_custom_paths=None,
):
    """
    This function calls qemu with the required arguments.
    """
    ps = None
    try:
        prctl.set_name(f"qemu{index}")
        prctl.set_proctitle(f"qemu_for_{index}")
        t0 = time.time()
        qlogger.debug(f"start qemu for exp {index}")

        # fmt: off
        qemustring = [
            config_qemu["qemu"],
            "-plugin", f"{config_qemu['plugin']},control={control},config={config},data={data}",
            "-M", config_qemu["machine"],
            "-monitor", "none",
        ]
        # fmt: on
        if qemu_output is True:
            qemustring += ["-d", "plugin"]
        if qemu_custom_paths is not None:
            qemustring += shlex.split(qemu_custom_paths)
        if config_qemu["bios"] != "":
            qemustring += ["-bios", config_qemu["bios"]]
        if config_qemu["kernel"] != "":
            qemustring += ["-kernel", config_qemu["kernel"]]
        if config_qemu["additional_qemu_args"] != "":
            qemustring += shlex.split(config_qemu["additional_qemu_args"])
        if "gdb" in config_qemu and config_qemu["gdb"] is True:
            qemustring += ["-S", "-s"]

        ps = subprocess.Popen(
            qemustring,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        while ps.poll() is None:
            tmp = ps.stdout.read()
            if qemu_output is True:
                with open(f"log_{index}.txt", "wt", encoding="utf-8") as f:
                    f.write(tmp.decode("utf-8"))
                qlogger.debug(tmp.decode("utf-8"))
        qlogger.debug(f"Ended qemu for exp {index}! Took {time.time() - t0}")
    except KeyboardInterrupt:
        ps.kill()
        logger.warning(f"Terminate QEMU {index}")


def readout_tbinfo(data_protobuf):
    """
    Builds a list of dicts for tb info from provided by qemu
    """
    tb_list = []
    for tb_info in data_protobuf.tb_informations:
        tb = {}
        tb["id"] = tb_info.base_address
        tb["size"] = tb_info.size
        tb["ins_count"] = tb_info.instruction_count
        tb["num_exec"] = tb_info.num_of_exec
        tb["assembler"] = tb_info.assembler.replace("!!", "\n")

        tb_list.append(tb)
    return tb_list


def write_output_wrt_goldenrun(keyword, data, goldenrun_data):
    """
    Panda dataframes for performance reasons. Naive implementation is too slow
    for larger datasets. golden_data twice concated to only get the diff
    (golden_data cancels it out)

    data            pd.data_frame
    goldenrun_data  pd.data_frame
    """
    if not isinstance(data, pd.DataFrame):
        data = pd.DataFrame(data)

    if goldenrun_data:
        data = [data, goldenrun_data[keyword], goldenrun_data[keyword]]
        data = pd.concat(data).drop_duplicates(keep=False)

    return data.to_dict("records")


def readout_tbexec(data_protobuf):
    """
    Builds a list of dicts for tb exec provided by qemu
    """
    pdtbexeclist = pd.DataFrame()
    tbexeclist = []
    for tb_exec_order in data_protobuf.tb_exec_orders:
        # generate list element
        execdic = {"tb": tb_exec_order.tb_base_address, "pos": tb_exec_order.pos}
        tbexeclist.append(execdic)

        if len(tbexeclist) <= TB_EXEC_LIST_CHUNK_SIZE:
            continue

        tmp = pd.DataFrame(tbexeclist)
        pdtbexeclist = pd.concat([pdtbexeclist, tmp], ignore_index=True)
        tbexeclist = []

    if tbexeclist:
        tmp = pd.DataFrame(tbexeclist)
        pdtbexeclist = pd.concat([pdtbexeclist, tmp], ignore_index=True)

    return pdtbexeclist


def build_filters(tbinfogolden):
    """
    Build for each tb in tbinfo a filter
    """
    filter_return = []
    # Each assembler string
    for tb in tbinfogolden["assembler"]:
        tb_filter = []
        # remove first split, as it is empty
        split = tb.split("[ ")
        # For each line
        for sp in split[1:]:
            # select address
            s = sp.split("]")
            # Add to filter
            tb_filter.append(int("0x" + s[0].strip(), 0))
        # Sort addresses
        tb_filter.sort()
        # Reverse list so that last element is first
        tb_filter.reverse()
        # Append to filter list
        filter_return.append(tb_filter)
    # Filter list for length of filter, so that the longest one is tested first
    filter_return.sort(key=len)
    filter_return.reverse()
    return filter_return


def recursive_filter(tbexecpd, tbinfopd, index, filt):
    """
    Search if each element in filt exists in tbexec after index
    """
    # Make sure we do not leave Pandas frame
    if not ((index >= 0) and index < len(tbexecpd)):
        return [False, tbexecpd, tbinfopd]
    # Select element to test
    tb = tbexecpd.loc[index]
    # Make sure it is part of filter
    if tb["tb"] == filt[0]:
        if len(filt) == 1:
            # Reached start of original tb
            return [True, tbexecpd, tbinfopd]
        else:
            # pop filter element and increase index in tbexec pandas frame
            fi = filt.pop(0)
            index = index + 1
            # Call recursively
            [flag, tbexecpd, tbinfopd] = recursive_filter(
                tbexecpd, tbinfopd, index, filt
            )
            index = index - 1
            # If true, we have a match
            if flag is True:
                # Invalidate element in tb exec list
                tbexecpd.at[index, "tb"] = -1
                tbexecpd.at[index, "tb-1"] = -1
                # Search tb in tb info
                idx = tbinfopd.index[tbinfopd["id"] == fi]
                for ind in idx:
                    # Only invalidate if tb only contains one element, as these are artefacts of singlestep
                    if tbinfopd.at[ind, "ins_count"] == 1:
                        tbinfopd.at[ind, "num_exec"] = tbinfopd.at[ind, "num_exec"] - 1
            return [flag, tbexecpd, tbinfopd]
    else:
        return [False, tbexecpd, tbinfopd]


def decrese_tb_info_element(tb_id, number, tbinfopd):
    """Find all matches to the tb id"""
    idx = tbinfopd.index[tbinfopd["id"] == tb_id]
    # Decrement all matches by number of occurrence in tb exec
    for i in idx:
        tbinfopd.at[i, "num_exec"] = tbinfopd.at[i, "num_exec"] - number


def filter_function(tbexecpd, filt, tbinfopd):
    """Find all possible matches for first element of filter"""
    idx = tbexecpd.index[(tbexecpd["tb"] == filt[0])]
    for f in filt[1:]:
        # Increment to next possible match position
        idx = idx + 1
        # Find all possible matches for next filter value
        tmp = tbexecpd.index[(tbexecpd["tb"]) == f]
        # Find matching indexes between both indexes
        idx = idx.intersection(tmp)
    # We now will step through the filter backwards
    filt.reverse()
    for f in filt[1:]:
        # Decrement positions
        idx = idx - 1
        for i in idx:
            # Invalidate all positions
            tbexecpd.at[i, "tb"] = -1
            tbexecpd.at[i, "tb-1"] = -1
        # Decrement artefacts in tb info list
        decrese_tb_info_element(f, len(idx), tbinfopd)


def filter_tb(tbexeclist, tbinfo, tbexecgolden, tbinfogolden, id_num):
    """
    First create filter list, then find start of filter, then call recursive filter
    """
    filters = build_filters(tbinfogolden)
    tbexecpd = tbexeclist
    # Sort and re-index tb exec list
    tbexecpd.sort_values(by=["pos"], ascending=False, inplace=True)
    tbexecpd.reset_index(drop=True, inplace=True)
    tbexecpd["tb-1"] = tbexecpd["tb"].shift(periods=-1, fill_value=0)
    # Generate pandas frame for tbinfo
    tbinfopd = pd.DataFrame(tbinfo)
    for filt in filters:
        # Only if filter has more than one element
        if len(filt) > 1:
            # Perform search and invalidation of found matches
            filter_function(tbexecpd, filt, tbinfopd)

    diff = len(tbexecpd)
    # Search found filter matches
    idx = tbexecpd.index[tbexecpd["tb-1"] == -1]
    # Drop them from table
    tbexecpd.drop(idx, inplace=True)
    # Drop temporary column
    tbexecpd.drop(columns=["tb-1"], inplace=True)
    # Reverse list, because it is given reversed from qemu
    tbexecpd.sort_values(by=["pos"], inplace=True)
    # Fix broken position index
    tbexecpd.reset_index(drop=True, inplace=True)
    tbexecpd["pos"] = tbexecpd.index
    # Again reverse list to go back to original orientation
    tbexecpd = tbexecpd.iloc[::-1]
    logger.debug(
        "worker {} length diff of tbexec {}".format(id_num, diff - len(tbexecpd))
    )
    diff = len(tbinfopd)
    # Search each tb info, that was completely removed from tbexec list
    idx = tbinfopd.index[tbinfopd["num_exec"] <= 0]
    # Drop the now not relevant tbinfo elements
    tbinfopd.drop(idx, inplace=True)
    logger.debug(
        "worker {} Length diff of tbinfo {}".format(id_num, diff - len(tbinfopd))
    )
    return [tbexecpd, tbinfopd.to_dict("records")]


def readout_meminfo(data_protobuf):
    """
    Builds a list of dicts for memory info from protobuf message provided by qemu
    """
    memlist = []
    for meminfo in data_protobuf.mem_infos:
        mem = {}
        mem["ins"] = meminfo.ins_address
        mem["size"] = meminfo.size
        mem["address"] = meminfo.memmory_address
        mem["direction"] = meminfo.direction
        mem["counter"] = meminfo.counter
        mem["tbid"] = 0

        memlist.append(mem)

    return memlist


def connect_meminfo_tb(meminfolist, tblist):
    for meminfo in meminfolist:
        for tbinfo in tblist:
            if (
                meminfo["ins"] > tbinfo["id"]
                and meminfo["ins"] < tbinfo["id"] + tbinfo["size"]
            ):
                meminfo["tbid"] = tbinfo["id"]
                break


def readout_memdump(protobuf_msg):
    """
    This function parses memory dumps received from data pipe and returns
    a list containing them
    """
    memdumplist = []

    for mem_dump_info in protobuf_msg.mem_dump_infos:
        memdumpdict = {}
        memdumpdict["address"] = mem_dump_info.address
        memdumpdict["len"] = mem_dump_info.len
        memdumpdict["dumps"] = []

        memdumpdict["dumps"] = [list(dump.mem) for dump in mem_dump_info.dumps]
        n_dumps = len(memdumpdict["dumps"])

        memdumpdict["numdumps"] = n_dumps
        memdumplist.append(memdumpdict)

    return memdumplist


def readout_registers(data_protobuf):
    register_list = []
    reg_type = data_protobuf.register_info.arch_type
    reg_size = 0
    reg_name = ""

    if reg_type == Register.ARM:
        reg_size = 16
        reg_name = "r"
    elif reg_type == Register.RISCV:
        reg_size = 32
        reg_name = "x"

    for reg_dump in data_protobuf.register_info.register_dumps:
        register = {"pc": reg_dump.pc, "tbcounter": reg_dump.tb_count}
        for i in range(0, reg_size):
            register[f"{reg_name}{i}"] = reg_dump.register_values[i]

        # Last element of register_values is XPSR for Arm, PC for RISCV
        if reg_type == Register.ARM:
            register["xpsr"] = reg_dump.register_values[reg_size]
        elif reg_type == Register.RISCV:
            register[f"{reg_name}{reg_size}"] = reg_dump.register_values[reg_size]

        register_list.append(register)

    return register_list


def readout_tb_faulted(data_protobuf):
    tb_faulted_list = []

    for tb_fault in data_protobuf.faulted_datas:
        tbfaulted = {}
        tbfaulted["faultaddress"] = tb_fault.trigger_address
        tbfaulted["assembly"] = tb_fault.assembler.replace("!!", "\n")

        tb_faulted_list.append(tbfaulted)

    return tb_faulted_list


def readout_data(
    pipe,
    index,
    queue_output,
    faultlist,
    goldenrun_data,
    config_qemu,
    queue_ram_usage=None,
    qemu_post=None,
    qemu_pre_data=None,
):
    """
    This function will permanently try to read data from data pipe
    Furthermore it then builds the internal representation, which is collected
    by the process writing to hdf 5 file
    """
    tblist = []
    pdtbexeclist = None
    memlist = []
    memdumplist = []
    registerlist = []
    tbfaultedlist = []
    tbinfo = 0
    tbexec = 0
    meminfo = 0
    endpoint = 0
    end_reason = ""
    max_ram_usage = 0
    regtype = None

    timeout = Timeout()

    # Load data from the pipe
    data_protobuf = data_pb2.Data()
    data_protobuf.ParseFromString(pipe.read())

    # Process loaded information
    output = {}

    endpoint = data_protobuf.end_point
    end_reason = data_protobuf.end_reason

    if len(data_protobuf.tb_informations) != 0:
        tbinfo = 1
        tblist = readout_tbinfo(data_protobuf)

    if len(data_protobuf.mem_infos) != 0:
        meminfo = 1
        memlist = readout_meminfo(data_protobuf)

    if tbinfo == 1 and meminfo == 1:
        connect_meminfo_tb(memlist, tblist)

    # Process tb exec order
    if len(data_protobuf.tb_exec_orders) != 0:
        tbexec = 1
        pdtbexeclist = readout_tbexec(data_protobuf)
        pdtbexeclist.sort_values(by="pos", inplace=True)

        gather_process_ram_usage(queue_ram_usage, 0)

        if goldenrun_data:
            if config_qemu["ring_buffer"]:
                pdtbexeclist = pdtbexeclist.iloc[::-1]
            else:
                [pdtbexeclist, tblist] = filter_tb(
                    pdtbexeclist,
                    tblist,
                    goldenrun_data["tbexec"],
                    goldenrun_data["tbinfo"],
                    index,
                )

    if len(data_protobuf.mem_dump_infos) != 0:
        memdumplist = readout_memdump(data_protobuf)
        output["memdumplist"] = memdumplist

    if data_protobuf.register_info.arch_type == Register.ARM:
        regtype = "arm"
        registerlist = readout_registers(data_protobuf)
    elif data_protobuf.register_info.arch_type == Register.RISCV:
        regtype = "riscv"
        registerlist = readout_registers(data_protobuf)

    if len(data_protobuf.faulted_datas) != 0:
        tbfaultedlist = readout_tb_faulted(data_protobuf)
        output["tbfaulted"] = tbfaultedlist

    logger.debug(f"Data received now on post processing for Experiment {index}")

    max_ram_usage = gather_process_ram_usage(queue_ram_usage, max_ram_usage)

    datasets = []
    datasets.append((tbinfo, "tbinfo", tblist))
    datasets.append((tbexec, "tbexec", pdtbexeclist))
    datasets.append((meminfo, "meminfo", memlist))
    datasets.append(
        (
            regtype,
            f"{regtype}registers",
            pd.DataFrame(registerlist, dtype="UInt64"),
        )
    )

    for flag, keyword, data in datasets:
        if not flag:
            continue
        if keyword.endswith("registers"):
            output[keyword] = data.to_dict("records")
        else:
            output[keyword] = write_output_wrt_goldenrun(keyword, data, goldenrun_data)

    output["index"] = index
    output["faultlist"] = faultlist
    output["endpoint"] = endpoint
    output["end_reason"] = end_reason

    max_ram_usage = gather_process_ram_usage(queue_ram_usage, max_ram_usage)

    if callable(qemu_post):
        output = qemu_post(qemu_pre_data, output)
    queue_output.put(output)

    max_ram_usage = gather_process_ram_usage(queue_ram_usage, max_ram_usage)

    return (max_ram_usage, timeout.raised)


def create_fifos():
    """
    Function to create the FIFOs needed between qemu and python worker
    pattern is /tmp/qemu_fault/[UID]/fifo
    Returns the paths to the created fifos
    """
    # path for FIFOs to reside
    path = "/tmp/"
    # set mode for filesystem in tmp
    mode = 0o664
    path = path + "qemu_fault/"
    if not os.path.exists(path):
        os.mkdir(path)
    path = path + "{}/".format(os.getpid())
    if not os.path.exists(path):
        os.mkdir(path)
    control = path + "control"
    config = path + "config"
    data = path + "data"
    if not os.path.exists(control):
        os.mkfifo(control, mode)
    if not os.path.exists(config):
        os.mkfifo(config, mode)
    if not os.path.exists(data):
        os.mkfifo(data, mode)
    paths = {}
    paths["control"] = control
    paths["config"] = config
    paths["data"] = data
    return paths


def delete_fifos():
    path = "/tmp/qemu_fault/{}/".format(os.getpid())

    os.remove(path + "control")
    os.remove(path + "config")
    os.remove(path + "data")

    os.rmdir(path)


def configure_qemu(control, config_qemu, num_faults, memorydump_list, index):
    """
    Creates a protobuf message instance and writes it to the control pipe
    """

    # Protobuf control message
    control_message = control_pb2.Control()

    control_message.max_duration = config_qemu["max_instruction_count"]
    control_message.num_faults = num_faults
    control_message.tb_exec_list = config_qemu["tb_exec_list"]
    control_message.tb_info = config_qemu["tb_info"]
    control_message.mem_info = config_qemu["mem_info"]

    if "start" in config_qemu:
        control_message.has_start = True
        control_message.start_address = (config_qemu["start"])["address"]
        control_message.start_counter = (config_qemu["start"])["counter"]

    if "end" in config_qemu:
        for end_loc in config_qemu["end"]:
            new_end_point = control_message.end_points.add()

            new_end_point.address = end_loc["address"]
            new_end_point.counter = end_loc["counter"]

    # If enabled, use the ring buffer for all runs except for the goldenrun
    control_message.tb_exec_list_ring_buffer = config_qemu["ring_buffer"] and index >= 0

    control_message.full_mem_dump = index == -2

    if index != -2 and memorydump_list is not None:
        for memorydump in memorydump_list:
            memory_region = control_message.memorydumps.add()

            memory_region.address = memorydump["address"]
            memory_region.length = memorydump["length"]

    # Writing protobuf message to pipe
    # Size is also sent for correct parsing on the faultplugin side
    message_size = control_message.ByteSize()
    message_size_string = str(message_size) + "\n"
    control.write(message_size_string.encode())

    out = control_message.SerializeToString()
    control.write(out)

    control.flush()


def python_worker(
    fault_list,
    config_qemu,
    index,
    queue_output,
    qemu_output,
    goldenrun_data=None,
    change_nice=False,
    queue_ram_usage=None,
    qemu_pre=None,
    qemu_post=None,
):
    """
    Qemu worker creates qemu controller, fills the pipes and collects the
    output of qemu
    """

    # Setup qemu python part
    p_qemu = None
    try:
        if index >= 0:
            prctl.set_name("job{}".format(index))
            prctl.set_proctitle("Python_worker_for_{}".format(index))
        t0 = time.time()
        if change_nice:
            os.nice(19)
        paths = create_fifos()
        if callable(qemu_pre):
            [qemu_pre_data, qemu_custom_paths] = qemu_pre()
        else:
            qemu_pre_data = None
            qemu_custom_paths = None
        p_qemu = Process(
            target=run_qemu,
            args=(
                paths["control"],
                paths["config"],
                paths["data"],
                config_qemu,
                qemu_output,
                index,
                qemu_custom_paths,
            ),
        )

        p_qemu.start()
        logger.debug("Started QEMU process")
        control_fifo = open(paths["control"], mode="wb")
        config_fifo = open(paths["config"], mode="wb")
        data_fifo = open(paths["data"], mode="rb")
        logger.debug("opened fifos")
        if "memorydump" in config_qemu:
            memorydump = config_qemu["memorydump"]
        else:
            memorydump = None
        logger.debug("Start configuring")

        configure_qemu(control_fifo, config_qemu, len(fault_list), memorydump, index)

        logger.debug("Started QEMU")
        # Write faults to config pipe
        res = write_fault_list_to_pipe(fault_list, config_fifo)
        if res != 0:
            logger.error("Fault message could not be written to the config pipe!")
        logger.debug("Wrote config to qemu")

        # From here Qemu has started execution. Now prepare for
        # data extraction
        (mem, timeout_raised) = readout_data(
            data_fifo,
            index,
            queue_output,
            fault_list,
            goldenrun_data,
            config_qemu,
            queue_ram_usage,
            qemu_post=qemu_post,
            qemu_pre_data=qemu_pre_data,
        )

        if timeout_raised:
            logger.error(f"Terminate process {index}")
            p_qemu.terminate()

        p_qemu.join()
        delete_fifos()

        logger.debug(
            "Python worker for experiment {} done. Took {}s, mem usage {}KiB".format(
                index, time.time() - t0, mem
            )
        )
        if queue_ram_usage is not None:
            queue_ram_usage.put(mem)
    except KeyboardInterrupt:
        p_qemu.terminate()
        p_qemu.join()
        logger.warning("Terminate Worker {}".format(index))


def python_worker_unicorn(
    fault_list,
    config_qemu,
    index,
    queue_output,
    pregoldenrun_data,
    goldenrun_data,
    change_nice=False,
):
    t0 = time.time()
    if change_nice:
        os.nice(19)

    logs = run_unicorn(pregoldenrun_data, fault_list, config_qemu)
    logger.info(f"Ended qemu for exp {index}! Took {time.time() - t0}")

    logs["index"] = index

    queue_output.put(logs)

    logger.info(
        "Python worker for experiment {} done. Took {}s".format(
            index, time.time() - t0
        )
    )

    return
