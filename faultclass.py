import os
import subprocess
from multiprocessing import Process
import time
import pandas as pd
import prctl


import logging

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

    def write_to_fifo(self, fifo):
        "Write data to the config fifo, which sends binary data"
        numbytes = fifo.write(self.address.to_bytes(8, byteorder="big"))
        numbytes = numbytes + fifo.write(self.type.to_bytes(8, byteorder="big"))
        numbytes = numbytes + fifo.write(self.model.to_bytes(8, byteorder="big"))
        numbytes = numbytes + fifo.write(self.lifespan.to_bytes(8, byteorder="big"))
        numbytes = numbytes + fifo.write(self.mask.to_bytes(16, byteorder="big"))
        numbytes = numbytes + fifo.write(
            self.trigger.address.to_bytes(8, byteorder="big")
        )
        numbytes = numbytes + fifo.write(
            self.trigger.hitcounter.to_bytes(8, byteorder="big")
        )
        fifo.flush()
        return numbytes

    def write_to_fifo_new(self, fifo):
        out = "\n$$[Fault]\n"
        out = out + "% {:d} | {:d} | {:d} | {:d} | {:d} | {:d} | ".format(
            self.address,
            self.type,
            self.model,
            self.lifespan,
            self.trigger.address,
            self.trigger.hitcounter,
        )
        tmp = self.mask - pow(2, 64)
        if tmp < 0:
            tmp = 0
        out = out + " {:d} {:d} \n".format(tmp, self.mask - tmp)
        out = out + "$$[Fault_Ende]\n"
        tmp = fifo.write(out)
        fifo.flush()
        return tmp


def run_qemu(
    controll,
    config,
    data,
    qemu_monitor_fifo,
    qemu_path,
    kernel_path,
    plugin_path,
    machine,
    qemu_output,
    index,
    qemu_custom_paths=None,
):
    """
    This function calls qemu with the required arguments.
    """
    ps = None
    try:
        prctl.set_name("qemu{}".format(index))
        prctl.set_proctitle("qemu_for_{}".format(index))
        t0 = time.time()
        qlogger.debug("start qemu for exp {}".format(index))
        if qemu_output is True:
            output = "-d plugin"
        else:
            output = " "
        if qemu_custom_paths is None:
            qemu_custom_paths = " "

        qemustring = '{3!s} -plugin {5!s},arg="{0!s}",arg="{1!s}",arg="{2!s}" {6!s} {7!s} -M {8!s} -monitor none  -kernel {4!s}'.format(
            controll,
            config,
            data,
            qemu_path,
            kernel_path,
            plugin_path,
            output,
            qemu_custom_paths,
            machine,
        )
        ps = subprocess.Popen(
            qemustring, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        while ps.poll() is None:
            tmp = ps.stdout.read()
            if qemu_output is True:
                f = open("log_{}.txt".format(index), "wt", encoding="utf-8")
                f.write(tmp.decode("utf-8"))
                qlogger.debug(tmp.decode("utf-8"))
        qlogger.info("Ended qemu for exp {}! Took {}".format(index, time.time() - t0))
    except KeyboardInterrupt:
        ps.kill()
        logger.warning("Terminate QEMU {}".format(index))


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


def get_diff_wrt_goldenrun(data, goldenrun_data):
    """
    Panda dataframes for performance reasons. Naive implementation is too slow
    for larger datasets. golden_data twice concated to only get the diff
    (golden_data cancels it out)

    data            pd.data_frame
    goldenrun_data  pd.data_frame
    """
    data = [data, goldenrun_data, goldenrun_data]
    diff_data = pd.concat(data).drop_duplicates(keep=False)

    return diff_data.to_dict("records")


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
    riscvregister = {}
    riscvregister["pc"] = int(split[0])
    riscvregister["tbcounter"] = int(split[1])
    for i in range(0, 33):
        riscvregisters[f"x{i}"] = int(split[i + 2])
    return riscvregister


def readout_tb_faulted(line):
    split = line.split("|")
    tbfaulted = {}
    tbfaulted["faultaddress"] = int(split[0], 0)
    tbfaulted["assembly"] = split[1].replace("!!", "\n")
    return tbfaulted


def readout_data(
    pipe,
    index,
    q,
    faultlist,
    goldenrun_data,
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
                    "Data received now on post processing for Experiment {}".format(
                        index
                    )
                )
                tmp = 0
                if tbexec == 1:
                    if pdtbexeclist is not None:
                        tmp = pd.DataFrame(tbexeclist)
                        pdtbexeclist = pd.concat([pdtbexeclist, tmp], ignore_index=True)
                    else:
                        pdtbexeclist = pd.DataFrame(tbexeclist)

                    gather_process_ram_usage(queue_ram_usage, 0)

                    if goldenrun_data is not None:
                        [pdtbexeclist, tblist] = filter_tb(
                            pdtbexeclist,
                            tblist,
                            goldenrun_data["tbexec"],
                            goldenrun_data["tbinfo"],
                            index,
                        )
                if tbinfo == 1 and meminfo == 1:
                    connect_meminfo_tb(memlist, tblist)
                output = {}

                max_ram_usage = gather_process_ram_usage(queue_ram_usage, max_ram_usage)

                if tbinfo == 1:
                    if goldenrun_data is not None:
                        output["tbinfo"] = get_diff_wrt_goldenrun(
                            pd.DataFrame(tblist), goldenrun_data["tbinfo"]
                        )
                    else:
                        output["tbinfo"] = tblist

                if tbexec == 1:
                    if goldenrun_data is not None:
                        output["tbexec"] = get_diff_wrt_goldenrun(
                            pdtbexeclist, goldenrun_data["tbexec"]
                        )
                    else:
                        output["tbexec"] = pdtbexeclist.to_dict("records")

                if meminfo == 1:
                    if goldenrun_data is not None:
                        output["meminfo"] = get_diff_wrt_goldenrun(
                            pd.DataFrame(memlist), goldenrun_data["meminfo"]
                        )
                    else:
                        output["meminfo"] = memlist

                if goldenrun_data is not None:
                    if regtype == "arm":
                        output["armregisters"] = get_diff_wrt_goldenrun(
                            pd.DataFrame(registerlist), goldenrun_data["armregisters"]
                        )
                    if regtype == "riscv":
                        output["riscvregisters"] = get_diff_wrt_goldenrun(
                            pd.DataFrame(registerlist), goldenrun_data["riscvregisters"]
                        )

                else:
                    if regtype == "arm":
                        output["armregisters"] = registerlist
                    if regtype == "riscv":
                        output["riscvregisters"] = registerlist

                if tbfaulted == 1:
                    output["tbfaulted"] = tbfaultedlist

                output["index"] = index
                output["faultlist"] = faultlist
                output["endpoint"] = endpoint

                if memdump == 1:
                    output["memdumplist"] = memdumplist

                max_ram_usage = gather_process_ram_usage(queue_ram_usage, max_ram_usage)

                if callable(qemu_post):
                    output = qemu_post(qemu_pre_data, output)
                q.put(output)

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
    controll = path + "controll"
    config = path + "config"
    data = path + "data"
    qemu = path + "qemu"
    if not os.path.exists(controll):
        os.mkfifo(controll, mode)
    if not os.path.exists(config):
        os.mkfifo(config, mode)
    if not os.path.exists(data):
        os.mkfifo(data, mode)
    if not os.path.exists(qemu):
        os.mkfifo(qemu, mode)
    paths = {}
    paths["controll"] = controll
    paths["config"] = config
    paths["data"] = data
    paths["qemu"] = qemu
    return paths


def delete_fifos():
    path = "/tmp/qemu_fault/{}/".format(os.getpid())

    os.remove(path + "controll")
    os.remove(path + "config")
    os.remove(path + "data")
    os.remove(path + "qemu")

    os.rmdir(path)


def configure_qemu(controll, config_qemu, num_faults, memorydump_list):
    """
    Function to write commands and configuration needed to start qemu plugin
    """
    out = "\n$$$[Config]\n"
    out = out + "$$ max_duration: {}\n".format(config_qemu["max_instruction_count"])
    out = out + "$$ num_faults: {}\n".format(num_faults)

    if "tb_exec_list" in config_qemu:
        if config_qemu["tb_exec_list"] is False:
            out = out + "$$disable_tb_exec_list"
        else:
            out = out + "$$enable_tb_exec_list"

    if "tb_info" in config_qemu:
        if config_qemu["tb_info"] is False:
            out = out + "$$disable_tb_info"
        else:
            out = out + "$$enable_tb_info"

    if "mem_info" in config_qemu:
        if config_qemu["mem_info"] is False:
            out = out + "$$disable_mem_info"
        else:
            out = out + "$$enable_mem_info"

    if "start" in config_qemu:
        out = out + "$$ start_address: {}\n".format((config_qemu["start"])["address"])
        out = out + "$$ start_counter: {}\n".format((config_qemu["start"])["counter"])

    if "end" in config_qemu:
        out = out + "$$ end_address: {}\n".format((config_qemu["end"])["address"])
        out = out + "$$ end_counter: {}\n".format((config_qemu["end"])["counter"])

    if memorydump_list is not None:
        out = out + "$$num_memregions: {}\n".format(len(memorydump_list))
        out = out + "$$$[Memory]\n"
        for memorydump in memorydump_list:
            out = out + "$$memoryregion: {} || {}\n".format(
                memorydump["address"], memorydump["length"]
            )
    controll.write(out)
    controll.flush()


def enable_qemu(controll):
    """
    Starts qemu plugin. Until this point it actively reads from control pipe.
    """
    controll.write("\n$$$[Start]\n")
    controll.flush()


def python_worker(
    fault_list,
    config_qemu,
    index,
    q,
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
        if "gdb" in config_qemu:
            if qemu_custom_paths is None:
                qemu_custom_paths = " -S -s "
            else:
                qemu_custom_paths = qemu_custom_paths + " -S -s "
        p_qemu = Process(
            target=run_qemu,
            args=(
                paths["controll"],
                paths["config"],
                paths["data"],
                paths["qemu"],
                config_qemu["qemu"],
                config_qemu["kernel"],
                config_qemu["plugin"],
                config_qemu["machine"],
                qemu_output,
                index,
                qemu_custom_paths,
            ),
        )
        p_qemu.start()
        logger.debug("Started QEMU process")
        controll_fifo = open(paths["controll"], mode="w")
        config_fifo = open(paths["config"], mode="w")
        data_fifo = open(paths["data"], mode="r", buffering=1)
        logger.debug("opened fifos")
        if "memorydump" in config_qemu:
            memorydump = config_qemu["memorydump"]
        else:
            memorydump = None
        logger.debug("Start configuring")
        configure_qemu(controll_fifo, config_qemu, len(fault_list), memorydump)
        enable_qemu(controll_fifo)
        logger.debug("Started QEMU")
        """Write faults to config pipe"""
        for fault in fault_list:
            fault.write_to_fifo_new(config_fifo)
        logger.debug("Wrote config to qemu")
        """
        From here Qemu has started execution. Now prepare for
        data extraction
        """
        mem = readout_data(
            data_fifo,
            index,
            q,
            fault_list,
            goldenrun_data,
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
