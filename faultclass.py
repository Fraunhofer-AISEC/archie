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
from multiprocessing import Process
import os
import shlex
import subprocess
import time

import pandas as pd
import prctl

import fault_pb2
from util import gather_process_ram_usage

logger = logging.getLogger(__name__)
qlogger = logging.getLogger("QEMU-" + __name__)


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
        self.type = fault_type
        self.model = fault_model
        self.lifespan = fault_lifespan
        self.mask = fault_mask
        self.num_bytes = num_bytes
        self.wildcard = wildcard

def write_fault_list_to_pipe(fault_list, fifo):
    fault_pack = fault_pb2.Fault_Pack()

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

    out = fault_pack.SerializeToString()

    tmp = fifo.write(out)
    fifo.flush()
    return tmp


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
                f = open(f"log_{index}.txt", "wt", encoding="utf-8")
                f.write(tmp.decode("utf-8"))
                qlogger.debug(tmp.decode("utf-8"))
        qlogger.info(f"Ended qemu for exp {index}! Took {time.time() - t0}")
    except KeyboardInterrupt:
        ps.kill()
        logger.warning(f"Terminate QEMU {index}")


def readout_tbinfo(line):
    """
    Builds the dict for tb info from line provided by qemu
    """
    split = line.split("|")
    tb = {}
    tb["id"] = int(split[0], 0)
    tb["size"] = int(split[1], 0)
    tb["ins_count"] = int(split[2], 0)
    tb["num_exec"] = int(split[3], 0)
    tb["assembler"] = split[4].replace("!!", "\n")
    return tb


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


def readout_tbexec(line, tbexeclist, tbinfo, goldenrun):
    """
    Builds the dict for tb exec from line provided by qemu
    """
    split = line.split("|")
    # generate list element
    execdic = {}
    execdic["tb"] = int(split[0], 0)
    execdic["pos"] = int(split[1], 0)
    return execdic


def build_filters(tbinfogolden):
    """
    Build for each tb in tbinfo a filter
    """
    filter_return = []
    """Each assembler string"""
    for tb in tbinfogolden["assembler"]:
        tb_filter = []
        """remove first split, as it is empty"""
        split = tb.split("[ ")
        """For each line"""
        for sp in split[1:]:
            """select address"""
            s = sp.split("]")
            """Add to filter"""
            tb_filter.append(int("0x" + s[0].strip(), 0))
        """Sort addresses"""
        tb_filter.sort()
        """Reverse list so that last element is first"""
        tb_filter.reverse()
        """Append to filter list"""
        filter_return.append(tb_filter)
    """Filter list for length of filter, so that the longest one is tested first"""
    filter_return.sort(key=len)
    filter_return.reverse()
    return filter_return


def recursive_filter(tbexecpd, tbinfopd, index, filt):
    """
    Search if each element in filt exists in tbexec after index
    """
    """Make sure we do not leave Pandas frame"""
    if not ((index >= 0) and index < len(tbexecpd)):
        return [False, tbexecpd, tbinfopd]
    """Select element to test"""
    tb = tbexecpd.loc[index]
    """Make sure it is part of filter"""
    if tb["tb"] == filt[0]:
        if len(filt) == 1:
            """Reached start of original tb"""
            return [True, tbexecpd, tbinfopd]
        else:
            """pop filter element and increase index in tbexec pandas frame"""
            fi = filt.pop(0)
            index = index + 1
            """Call recursively"""
            [flag, tbexecpd, tbinfopd] = recursive_filter(
                tbexecpd, tbinfopd, index, filt
            )
            index = index - 1
            """If true, we have a match"""
            if flag is True:
                """Invalidate element in tb exec list"""
                tbexecpd.at[index, "tb"] = -1
                tbexecpd.at[index, "tb-1"] = -1
                """Search tb in tb info"""
                idx = tbinfopd.index[tbinfopd["id"] == fi]
                for ind in idx:
                    """Only invalidate if tb only contains one element, as these are artefacts of singlestep"""
                    if tbinfopd.at[ind, "ins_count"] == 1:
                        tbinfopd.at[ind, "num_exec"] = tbinfopd.at[ind, "num_exec"] - 1
            return [flag, tbexecpd, tbinfopd]
    else:
        return [False, tbexecpd, tbinfopd]


def decrese_tb_info_element(tb_id, number, tbinfopd):
    """Find all matches to the tb id"""
    idx = tbinfopd.index[tbinfopd["id"] == tb_id]
    """Decrement all matches by number of occurrence in tb exec"""
    for i in idx:
        tbinfopd.at[i, "num_exec"] = tbinfopd.at[i, "num_exec"] - number


def filter_function(tbexecpd, filt, tbinfopd):
    """Find all possible matches for first element of filter"""
    idx = tbexecpd.index[(tbexecpd["tb"] == filt[0])]
    for f in filt[1:]:
        """Increment to next possible match position"""
        idx = idx + 1
        """Find all possible matches for next filter value"""
        tmp = tbexecpd.index[(tbexecpd["tb"]) == f]
        """Find matching indexes between both indexes"""
        idx = idx.intersection(tmp)
    """We now will step through the filter backwards"""
    filt.reverse()
    for f in filt[1:]:
        """Decrement positions"""
        idx = idx - 1
        for i in idx:
            """Invalidate all positions"""
            tbexecpd.at[i, "tb"] = -1
            tbexecpd.at[i, "tb-1"] = -1
        """Decrement artefacts in tb info list"""
        decrese_tb_info_element(f, len(idx), tbinfopd)


def filter_tb(tbexeclist, tbinfo, tbexecgolden, tbinfogolden, id_num):
    """
    First create filter list, then find start of filter, then call recursive filter
    """
    filters = build_filters(tbinfogolden)
    tbexecpd = tbexeclist
    """Sort and re-index tb exec list"""
    tbexecpd.sort_values(by=["pos"], ascending=False, inplace=True)
    tbexecpd.reset_index(drop=True, inplace=True)
    tbexecpd["tb-1"] = tbexecpd["tb"].shift(periods=-1, fill_value=0)
    """Generate pandas frame for tbinfo"""
    tbinfopd = pd.DataFrame(tbinfo)
    for filt in filters:
        """Only if filter has more than one element"""
        if len(filt) > 1:
            """Perform search and invalidation of found matches"""
            filter_function(tbexecpd, filt, tbinfopd)

    diff = len(tbexecpd)
    """ Search found filter matches """
    idx = tbexecpd.index[tbexecpd["tb-1"] == -1]
    """Drop them from table"""
    tbexecpd.drop(idx, inplace=True)
    """Drop temporary column"""
    tbexecpd.drop(columns=["tb-1"], inplace=True)
    """Reverse list, because it is given reversed from qemu"""
    tbexecpd.sort_values(by=["pos"], inplace=True)
    """ Fix broken position index"""
    tbexecpd.reset_index(drop=True, inplace=True)
    tbexecpd["pos"] = tbexecpd.index
    """Again reverse list to go back to original orientation"""
    tbexecpd = tbexecpd.iloc[::-1]
    logger.debug(
        "worker {} length diff of tbexec {}".format(id_num, diff - len(tbexecpd))
    )
    diff = len(tbinfopd)
    """Search each tb info, that was completely removed from tbexec list"""
    idx = tbinfopd.index[tbinfopd["num_exec"] <= 0]
    """Drop the now not relevant tbinfo elements"""
    tbinfopd.drop(idx, inplace=True)
    logger.debug(
        "worker {} Length diff of tbinfo {}".format(id_num, diff - len(tbinfopd))
    )
    return [tbexecpd, tbinfopd.to_dict("records")]


def readout_meminfo(line):
    """
    Builds the dict for memory info from line provided by qemu
    """
    split = line.split("|")
    mem = {}
    mem["ins"] = int(split[0], 0)
    mem["size"] = int(split[1], 0)
    mem["address"] = int(split[2], 0)
    mem["direction"] = int(split[3], 0)
    mem["counter"] = int(split[4], 0)
    mem["tbid"] = 0
    return mem


def connect_meminfo_tb(meminfolist, tblist):
    for meminfo in meminfolist:
        for tbinfo in tblist:
            if (
                meminfo["ins"] > tbinfo["id"]
                and meminfo["ins"] < tbinfo["id"] + tbinfo["size"]
            ):
                meminfo["tbid"] = tbinfo["id"]
                break


def readout_memdump(line, memdumplist, memdumpdict, memdumptmp):
    """
    This function will readout the lines. If it receives memorydump, it
    means a new configured dump will be transmitted. Therefore the
    dictionary is initialised. If only B: is received, Binary data is
    transmitted. If Dump end is received, the dump is finished and needs
    to be appended to the dic, as multiple dumps are possible. If
    memorydump end is received, the current memorydump is finished and
    is added to the memdumplist
    """

    if "[memorydump]" in line:
        split = line.split("]:")
        info = split[1]
        split = info.split("|")
        memdumpdict["address"] = int(split[0], 0)
        memdumpdict["len"] = int(split[1], 0)
        memdumpdict["numdumps"] = int(split[2], 0)
        memdumpdict["dumps"] = []
    if "B:" in line:
        split = line.split("B: ")
        binary = split[1].split(" ")
        for b in binary:
            memdumptmp.append(int(b, 0))
    if "[Dump end]" in line:
        memdumpdict["dumps"].append(memdumptmp)
        memdumptmp = []
    if "[memorydump end]" in line:
        memdumplist.append(memdumpdict)
        memdumpdict = {}
    return [memdumplist, memdumpdict, memdumptmp]


def readout_arm_registers(line):
    split = line.split("|")
    armregisters = {}
    armregisters["pc"] = int(split[0])
    armregisters["tbcounter"] = int(split[1])
    for i in range(0, 16):
        armregisters[f"r{i}"] = int(split[i + 2])
    armregisters["xpsr"] = int(split[18])
    return armregisters


def readout_riscv_registers(line):
    split = line.split("|")
    riscvregisters = {}
    riscvregisters["pc"] = int(split[0], 16)
    riscvregisters["tbcounter"] = int(split[1], 16)
    for i in range(0, 33):
        riscvregisters[f"x{i}"] = int(split[i + 2], 16)
    return riscvregisters


def readout_tb_faulted(line):
    split = line.split("|")
    tbfaulted = {}
    tbfaulted["faultaddress"] = int(split[0], 0)
    tbfaulted["assembly"] = split[1].replace("!!", "\n")
    return tbfaulted


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
    state = "None"
    tblist = []
    tbexeclist = []
    pdtbexeclist = None
    memlist = []
    memdumpdict = {}
    memdumplist = []
    memdumptmp = []
    registerlist = []
    tbfaultedlist = []
    tbinfo = 0
    tbexec = 0
    meminfo = 0
    memdump = 0
    endpoint = 0
    end_reason = ""
    max_ram_usage = 0
    regtype = None
    tbfaulted = 0

    while 1:
        line = pipe.readline()

        if "$$$" in line:
            line = line[3:]

            if "[Endpoint]" in line:
                split = line.split("]:")
                endpoint = int(split[1], 0)

            elif "[End Reason]" in line:
                split = line.split("]:")
                end_reason = split[1].strip()

            elif "[TB Information]" in line:
                state = "tbinfo"
                tbinfo = 1

            elif "[TB Exec]" in line:
                state = "tbexec"
                tbexec = 1

            elif "[Mem Information]" in line:
                tbexeclist.reverse()
                state = "meminfo"
                meminfo = 1

            elif "[Memdump]" in line:
                state = "memdump"
                memdump = 1

            elif "[END]" in line:
                state = "none"
                logger.info(
                    f"Data received now on post processing for Experiment {index}"
                )

                if tbexec == 1:
                    if pdtbexeclist is not None:
                        tmp = pd.DataFrame(tbexeclist)
                        pdtbexeclist = pd.concat([pdtbexeclist, tmp], ignore_index=True)
                    else:
                        pdtbexeclist = pd.DataFrame(tbexeclist)
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

                if tbinfo == 1 and meminfo == 1:
                    connect_meminfo_tb(memlist, tblist)

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

                output = {}
                for flag, keyword, data in datasets:
                    if not flag:
                        continue
                    if keyword.endswith("registers"):
                        output[keyword] = data.to_dict("records")
                    else:
                        output[keyword] = write_output_wrt_goldenrun(
                            keyword, data, goldenrun_data
                        )

                if tbfaulted == 1:
                    output["tbfaulted"] = tbfaultedlist

                output["index"] = index
                output["faultlist"] = faultlist
                output["endpoint"] = endpoint
                output["end_reason"] = end_reason

                if memdump == 1:
                    output["memdumplist"] = memdumplist

                max_ram_usage = gather_process_ram_usage(queue_ram_usage, max_ram_usage)

                if callable(qemu_post):
                    output = qemu_post(qemu_pre_data, output)
                queue_output.put(output)

                max_ram_usage = gather_process_ram_usage(queue_ram_usage, max_ram_usage)

                break

            elif "[Arm Registers]" in line:
                state = "armregisters"
                regtype = "arm"
            elif "[RiscV Registers]" in line:
                state = "riscvregisters"
                regtype = "riscv"
            elif "[TB Faulted]" in line:
                state = "tbfaulted"
                tbfaulted = 1
            else:
                logger.warning(
                    "Command in exp {} not understood {}".format(index, line)
                )
                state = "None"

        elif "$$" in line:
            line = line[2:]
            if "tbinfo" in state:
                tblist.append(readout_tbinfo(line))
            elif "tbexec" in state:
                tbexeclist.append(
                    readout_tbexec(line, tbexeclist, tblist, goldenrun_data)
                )
                if len(tbexeclist) > 10000:
                    if pdtbexeclist is None:
                        pdtbexeclist = pd.DataFrame(tbexeclist)
                    else:
                        tmp = pd.DataFrame(tbexeclist)
                        pdtbexeclist = pd.concat([pdtbexeclist, tmp], ignore_index=True)
                    tbexeclist = []
            elif "meminfo" in state:
                memlist.append(readout_meminfo(line))
            elif "memdump" in state:
                [memdumplist, memdumpdict, memdumptmp] = readout_memdump(
                    line, memdumplist, memdumpdict, memdumptmp
                )
            elif "armregisters" in state:
                registerlist.append(readout_arm_registers(line))
            elif "riscvregisters" in state:
                registerlist.append(readout_riscv_registers(line))
            elif "tbfaulted" in state:
                tbfaultedlist.append(readout_tb_faulted(line))
            else:
                logger.warning("In exp {} unknown state {}".format(index, line))
    return max_ram_usage


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


def configure_qemu(control, config_qemu, num_faults, memorydump_list, goldenrun):
    """
    Function to write commands and configuration needed to start qemu plugin
    """
    out = "\n$$$[Config]\n"
    out = out + "$$ max_duration: {}\n".format(config_qemu["max_instruction_count"])
    out = out + "$$ num_faults: {}\n".format(num_faults)

    if "tb_exec_list" in config_qemu:
        if config_qemu["tb_exec_list"] is False:
            out = out + "$$disable_tb_exec_list\n"
        else:
            out = out + "$$enable_tb_exec_list\n"

    if "tb_info" in config_qemu:
        if config_qemu["tb_info"] is False:
            out = out + "$$disable_tb_info\n"
        else:
            out = out + "$$enable_tb_info\n"

    if "mem_info" in config_qemu and config_qemu["mem_info"]:
        out = out + "$$enable_mem_info\n"
    else:
        out = out + "$$disable_mem_info\n"

    if "start" in config_qemu:
        out = out + "$$ start_address: {}\n".format((config_qemu["start"])["address"])
        out = out + "$$ start_counter: {}\n".format((config_qemu["start"])["counter"])

    if "end" in config_qemu:
        for end_loc in config_qemu["end"]:
            out = out + "$$ end_address: {}\n".format(end_loc["address"])
            out = out + "$$ end_counter: {}\n".format(end_loc["counter"])

    # If enabled, use the ring buffer for all runs except for the goldenrun
    if config_qemu["ring_buffer"] is True and goldenrun is False:
        out = out + "$$tb_exec_list_ring_buffer\n"

    if memorydump_list is not None:
        out = out + "$$num_memregions: {}\n".format(len(memorydump_list))
        out = out + "$$$[Memory]\n"
        for memorydump in memorydump_list:
            out = out + "$$memoryregion: {} || {}\n".format(
                memorydump["address"], memorydump["length"]
            )
    control.write(out)
    control.flush()


def enable_qemu(control):
    """
    Starts qemu plugin. Until this point it actively reads from control pipe.
    """
    control.write("\n$$$[Start]\n")
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

    """Setup qemu python part"""
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
        control_fifo = open(paths["control"], mode="w")
        config_fifo = open(paths["config"], mode="wb")
        data_fifo = open(paths["data"], mode="r", buffering=1)
        logger.debug("opened fifos")
        if "memorydump" in config_qemu:
            memorydump = config_qemu["memorydump"]
        else:
            memorydump = None
        logger.debug("Start configuring")
        if goldenrun_data is None:
            goldenrun = True
        else:
            goldenrun = False
        configure_qemu(
            control_fifo, config_qemu, len(fault_list), memorydump, goldenrun
        )
        enable_qemu(control_fifo)
        logger.debug("Started QEMU")
        """Write faults to config pipe"""
        write_fault_list_to_pipe(fault_list, config_fifo)
        logger.debug("Wrote config to qemu")
        """
        From here Qemu has started execution. Now prepare for
        data extraction
        """
        mem = readout_data(
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
        p_qemu.join()
        delete_fifos()
        logger.info(
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
