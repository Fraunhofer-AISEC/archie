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

import queue
import signal
import logging
import time

import numpy
import prctl
import tables
from tqdm import tqdm

logger = logging.getLogger(__name__)


def register_signal_handlers():
    """
    Ignore signals, they will be handled by the controller.py anyway
    """
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGINT, signal.SIG_IGN)


# Tables for storing the elements from queue
class translation_block_exec_table(tables.IsDescription):
    tb = tables.UInt64Col()
    pos = tables.UInt64Col()


class memory_information_table(tables.IsDescription):
    insaddr = tables.Int64Col()
    tbid = tables.UInt64Col()
    size = tables.UInt64Col()
    address = tables.Int64Col()
    direction = tables.UInt8Col()
    counter = tables.UInt64Col()


class fault_table(tables.IsDescription):
    trigger_address = tables.UInt64Col()
    trigger_hitcounter = tables.UInt64Col()
    fault_address = tables.UInt64Col()
    fault_type = tables.UInt8Col()
    fault_model = tables.UInt8Col()
    fault_lifespan = tables.UInt64Col()
    fault_mask_upper = tables.UInt64Col()
    fault_mask = tables.UInt64Col()
    fault_num_bytes = tables.UInt8Col()
    fault_wildcard = tables.BoolCol()


class memory_dump_table(tables.IsDescription):
    address = tables.UInt64Col()
    length = tables.UInt64Col()
    numdumps = tables.UInt64Col()


class arm_registers_table(tables.IsDescription):
    pc = tables.UInt64Col()
    tbcounter = tables.UInt64Col()
    r0 = tables.UInt64Col()
    r1 = tables.UInt64Col()
    r2 = tables.UInt64Col()
    r3 = tables.UInt64Col()
    r4 = tables.UInt64Col()
    r5 = tables.UInt64Col()
    r6 = tables.UInt64Col()
    r7 = tables.UInt64Col()
    r8 = tables.UInt64Col()
    r9 = tables.UInt64Col()
    r10 = tables.UInt64Col()
    r11 = tables.UInt64Col()
    r12 = tables.UInt64Col()
    r13 = tables.UInt64Col()
    r14 = tables.UInt64Col()
    r15 = tables.UInt64Col()
    xpsr = tables.UInt64Col()


class riscv_registers_table(tables.IsDescription):
    pc = tables.UInt64Col()
    tbcounter = tables.UInt64Col()
    x0 = tables.UInt64Col()
    x1 = tables.UInt64Col()
    x2 = tables.UInt64Col()
    x3 = tables.UInt64Col()
    x4 = tables.UInt64Col()
    x5 = tables.UInt64Col()
    x6 = tables.UInt64Col()
    x7 = tables.UInt64Col()
    x8 = tables.UInt64Col()
    x9 = tables.UInt64Col()
    x10 = tables.UInt64Col()
    x11 = tables.UInt64Col()
    x12 = tables.UInt64Col()
    x13 = tables.UInt64Col()
    x14 = tables.UInt64Col()
    x15 = tables.UInt64Col()
    x16 = tables.UInt64Col()
    x17 = tables.UInt64Col()
    x18 = tables.UInt64Col()
    x19 = tables.UInt64Col()
    x20 = tables.UInt64Col()
    x21 = tables.UInt64Col()
    x22 = tables.UInt64Col()
    x23 = tables.UInt64Col()
    x24 = tables.UInt64Col()
    x25 = tables.UInt64Col()
    x26 = tables.UInt64Col()
    x27 = tables.UInt64Col()
    x28 = tables.UInt64Col()
    x29 = tables.UInt64Col()
    x30 = tables.UInt64Col()
    x31 = tables.UInt64Col()
    x32 = tables.UInt64Col()


class config_table(tables.IsDescription):
    qemu = tables.StringCol(1000)
    kernel = tables.StringCol(1000)
    plugin = tables.StringCol(1000)
    machine = tables.StringCol(1000)
    additional_qemu_args = tables.StringCol(1000)
    bios = tables.StringCol(1000)
    ring_buffer = tables.BoolCol()
    tb_exec_list = tables.BoolCol()
    tb_info = tables.BoolCol()
    mem_info = tables.BoolCol()
    max_instruction_count = tables.UInt64Col()
    memory_dump = tables.BoolCol()
    fault_count = tables.UInt64Col()


class hash_table(tables.IsDescription):
    qemu_hash = tables.StringCol(32)
    fault_hash = tables.StringCol(32)
    kernel_hash = tables.StringCol(32)
    bios_hash = tables.StringCol(32)
    hash_function = tables.StringCol(16)


class address_table(tables.IsDescription):
    address = tables.UInt64Col()
    counter = tables.UInt64Col()


class memmap_table(tables.IsDescription):
    address = tables.UInt64Col()
    size = tables.UInt64Col()


binary_atom = tables.UInt8Atom()


def process_tb_faulted(f, group, tbfaulted_list, myfilter):
    assembler_size = max(
        (len(tbfaulted["assembly"]) for tbfaulted in tbfaulted_list), default=1
    )

    class translation_block_faulted_table(tables.IsDescription):
        faultaddress = tables.UInt64Col()
        assembler = tables.StringCol(assembler_size)

    tbfaultedtable = f.create_table(
        group,
        "tbfaulted",
        translation_block_faulted_table,
        "Table contains the faulted assembly instructions",
        expectedrows=(len(tbfaulted_list)),
        filters=myfilter,
    )
    tbfaultedrow = tbfaultedtable.row
    for tbfaulted in tbfaulted_list:
        tbfaultedrow["faultaddress"] = tbfaulted["faultaddress"]
        tbfaultedrow["assembler"] = tbfaulted["assembly"]
        tbfaultedrow.append()
    tbfaultedtable.flush()
    tbfaultedtable.close()


def process_riscv_registers(f, group, riscvregister_list, myfilter):
    riscvregistertable = f.create_table(
        group,
        "riscvregisters",
        riscv_registers_table,
        "Table contains riscv registers at specific points.",
        expectedrows=(len(riscvregister_list)),
        filters=myfilter,
    )
    riscvregsrow = riscvregistertable.row
    for regs in riscvregister_list:
        riscvregsrow["pc"] = regs["pc"]
        riscvregsrow["tbcounter"] = regs["tbcounter"]
        for i in range(0, 33):
            riscvregsrow[f"x{i}"] = regs[f"x{i}"]
        riscvregsrow.append()
    riscvregistertable.flush()
    riscvregistertable.close()


def process_arm_registers(f, group, armregisters_list, myfilter):
    armregisterstable = f.create_table(
        group,
        "armregisters",
        arm_registers_table,
        "Table contains arm registers at specific points.",
        expectedrows=(len(armregisters_list)),
        filters=myfilter,
    )
    armregsrow = armregisterstable.row
    for regs in armregisters_list:
        armregsrow["pc"] = regs["pc"]
        armregsrow["tbcounter"] = regs["tbcounter"]
        for i in range(0, 16):
            armregsrow[f"r{i}"] = regs[f"r{i}"]
        armregsrow["xpsr"] = regs["xpsr"]
        armregsrow.append()
    armregisterstable.flush()
    armregisterstable.close()


def process_dumps(f, group, memdumplist, myfilter):
    memdumpsgroup = f.create_group(group, "memdumps")
    memdumpstable = f.create_table(
        memdumpsgroup,
        "memdumps",
        memory_dump_table,
        "Table containing description about the dumps, that are saved as carry.",
        expectedrows=(len(memdumplist)),
        filters=myfilter,
    )
    memdumpsrow = memdumpstable.row
    for memdump in memdumplist:
        name = "location_{:08x}_{:d}_{:d}".format(
            memdump["address"], memdump["len"], memdump["numdumps"]
        )
        if name not in memdumpsgroup._v_children:
            memdumpsrow["address"] = memdump["address"]
            memdumpsrow["length"] = memdump["len"]
            memdumpsrow["numdumps"] = memdump["numdumps"]
            # shape = (len(memdump['dumps']), memdump['len'])
            dumpnarray = numpy.array(memdump["dumps"])
            dumparray = f.create_carray(
                memdumpsgroup, name, binary_atom, dumpnarray.shape, filters=myfilter
            )
            dumparray[:] = dumpnarray
            memdumpsrow.append()
    memdumpstable.flush()
    memdumpstable.close()


def process_memmap(f, group, memmaplist, myfilter):
    _memmap_table = f.create_table(
        group,
        "memory_map",
        memmap_table,
        "Table containing a list of memory regions.",
        expectedrows=(len(memmaplist)),
        filters=myfilter,
    )
    memmap_row = _memmap_table.row
    for mem_region in memmaplist:
        memmap_row["address"] = mem_region["address"]
        memmap_row["size"] = mem_region["size"]
        memmap_row.append()
    _memmap_table.flush()
    _memmap_table.close()


def process_faults(f, group, faultlist, endpoint, end_reason, myfilter, name="faults"):
    # create table
    faulttable = f.create_table(
        group,
        name,
        fault_table,
        "Fault list table that contains the fault configuration used for this experiment",
        expectedrows=(len(faultlist)),
        filters=myfilter,
    )
    faulttable.attrs.endpoint = endpoint
    faulttable.attrs.end_reason = end_reason
    faultrow = faulttable.row
    for fault in faultlist:
        faultrow["trigger_address"] = fault.trigger.address
        faultrow["trigger_hitcounter"] = fault.trigger.hitcounter
        faultrow["fault_address"] = fault.address
        faultrow["fault_type"] = fault.type
        faultrow["fault_model"] = fault.model
        faultrow["fault_lifespan"] = fault.lifespan
        faultrow["fault_mask_upper"] = (fault.mask >> 64) & (pow(2, 64) - 1)
        faultrow["fault_mask"] = fault.mask & (pow(2, 64) - 1)
        faultrow["fault_num_bytes"] = fault.num_bytes
        faultrow["fault_wildcard"] = fault.wildcard
        faultrow.append()
    faulttable.flush()
    faulttable.close()


def process_tbinfo(f, group, tbinfolist, myfilter):
    assembler_size = max((len(tbinfo["assembler"]) for tbinfo in tbinfolist), default=1)

    class translation_block_table(tables.IsDescription):
        identity = tables.UInt64Col()
        size = tables.UInt64Col()
        ins_count = tables.UInt64Col()
        num_exec = tables.UInt64Col()
        assembler = tables.StringCol(assembler_size)

    tbinfotable = f.create_table(
        group,
        "tbinfo",
        translation_block_table,
        "Translation block table containing all information collected by qemu",
        expectedrows=(len(tbinfolist)),
        filters=myfilter,
    )
    tbinforow = tbinfotable.row
    for tbinfo in tbinfolist:
        tbinforow["identity"] = tbinfo["id"]
        tbinforow["size"] = tbinfo["size"]
        tbinforow["ins_count"] = tbinfo["ins_count"]
        tbinforow["num_exec"] = tbinfo["num_exec"]
        tbinforow["assembler"] = tbinfo["assembler"]
        tbinforow.append()
    tbinfotable.flush()
    tbinfotable.close()


def process_tbexec(f, group, tbexeclist, myfilter):
    tbexectable = f.create_table(
        group,
        "tbexeclist",
        translation_block_exec_table,
        "Translation block execution list table",
        expectedrows=(len(tbexeclist)),
        filters=myfilter,
    )
    tbexecrow = tbexectable.row
    for tbexec in tbexeclist:
        tbexecrow["tb"] = tbexec["tb"]
        tbexecrow["pos"] = tbexec["pos"]
        tbexecrow.append()
    tbexectable.flush()
    tbexectable.close()


def process_memory_info(f, group, meminfolist, myfilter):
    meminfotable = f.create_table(
        group,
        "meminfo",
        memory_information_table,
        "",
        expectedrows=(len(meminfolist)),
        filters=myfilter,
    )
    meminforow = meminfotable.row
    for meminfo in meminfolist:
        meminforow["insaddr"] = meminfo["ins"]
        meminforow["tbid"] = meminfo["tbid"]
        meminforow["size"] = meminfo["size"]
        meminforow["address"] = meminfo["address"]
        meminforow["direction"] = meminfo["direction"]
        meminforow["counter"] = meminfo["counter"]
        meminforow.append()
    meminfotable.flush()
    meminfotable.close()


def process_config(f, configgroup, exp, myfilter):
    hashtable = f.create_table(
        configgroup,
        "hash",
        hash_table,
        "",
        expectedrows=1,
        filters=myfilter,
    )

    hash_table_row = hashtable.row
    for file, f_hash in exp["hash"].items():
        hash_table_row[file] = f_hash
    hash_table_row["hash_function"] = exp["hash_function"]

    hash_table_row.append()

    hashtable.flush()
    hashtable.close()

    configtable = f.create_table(
        configgroup,
        "parameters",
        config_table,
        "",
        expectedrows=1,
        filters=myfilter,
    )

    config_row = configtable.row
    config_row["qemu"] = exp["qemu"]
    config_row["kernel"] = exp["kernel"]
    config_row["plugin"] = exp["plugin"]
    config_row["machine"] = exp["machine"]
    config_row["additional_qemu_args"] = exp["additional_qemu_args"]
    config_row["bios"] = exp["bios"]
    config_row["ring_buffer"] = exp["ring_buffer"]
    config_row["tb_exec_list"] = exp["tb_exec_list"]
    config_row["tb_info"] = exp["tb_info"]
    config_row["mem_info"] = exp["mem_info"]
    config_row["max_instruction_count"] = exp["max_instruction_count"]
    config_row["fault_count"] = exp["fault_count"]

    config_row.append()

    configtable.flush()
    configtable.close()

    starttable = f.create_table(
        configgroup,
        "start_address",
        address_table,
        "",
        expectedrows=(len(exp["start"])),
        filters=myfilter,
    )

    start_row = starttable.row
    start_row["address"] = exp["start"]["address"]
    start_row["counter"] = exp["start"]["counter"]

    start_row.append()

    starttable.flush()
    starttable.close()

    endtable = f.create_table(
        configgroup,
        "end_addresses",
        address_table,
        "",
        expectedrows=(len(exp["end"])),
        filters=myfilter,
    )

    end_row = endtable.row
    for endpoint in exp["end"]:
        end_row["address"] = endpoint["address"]
        end_row["counter"] = endpoint["counter"]

        end_row.append()

    endtable.flush()
    endtable.close()


def process_backup(f, configgroup, exp, myfilter, stop_signal):
    exp["config"]["fault_count"] = len(exp["expanded_faultlist"])

    process_config(f, configgroup, exp["config"], myfilter)

    fault_expanded_group = f.create_group(
        configgroup, "expanded_faults", "Group containing expanded input faults"
    )

    tmp = "{}".format(len(exp["expanded_faultlist"]))
    exp_name = "experiment{:0" + "{}".format(len(tmp)) + "d}"

    for exp_number in tqdm(
        range(len(exp["expanded_faultlist"])), desc="Creating backup"
    ):
        if stop_signal.value == 1:
            break

        exp_group = f.create_group(
            fault_expanded_group, exp_name.format(exp_number), "Group containing faults"
        )

        process_faults(
            f,
            exp_group,
            exp["expanded_faultlist"][exp_number]["faultlist"],
            0,
            "not executed",
            myfilter,
        )


def hdf5collector(
    hdf5path,
    mode,
    queue_output,
    num_exp,
    stop_signal,
    compressionlevel,
    logger_postprocess=None,
    log_goldenrun=True,
    log_config=False,
    overwrite_faults=False,
):
    register_signal_handlers()

    prctl.set_name("logger")
    prctl.set_proctitle("logger")
    f = tables.open_file(hdf5path, mode, max_group_width=65536)
    if "fault" in f.root:
        fault_group = f.root.fault
    else:
        fault_group = f.create_group("/", "fault", "Group containing fault results")
    myfilter = tables.Filters(complevel=compressionlevel, complib="zlib")
    t0 = time.time()
    tmp = "{}".format(num_exp)
    groupname = "experiment{:0" + "{}".format(len(tmp)) + "d}"

    log_pregoldenrun = log_goldenrun

    if overwrite_faults:
        for n in tqdm(
            f.root.fault._f_iter_nodes(),
            desc="Clearing old faults",
            total=f.root.fault._v_nchildren,
        ):
            n._f_remove(recursive=True)

    pbar = tqdm(total=num_exp, desc="Simulating faults", disable=not num_exp)
    while num_exp > 0 or log_goldenrun or log_pregoldenrun or log_config:
        if stop_signal.value == 1:
            break
        # readout queue and get next output from qemu. Will block
        try:
            exp = queue_output.get_nowait()
        except queue.Empty:
            continue

        t1 = time.time()
        logger.debug(
            "got exp {}, {} still need to be performed. Took {}s. Elements in queu: {}".format(
                exp["index"], num_exp, t1 - t0, queue_output.qsize()
            )
        )
        t0 = t1
        # create experiment group in file
        if exp["index"] >= 0:
            index = exp["index"]
            while groupname.format(index) in fault_group:
                index = index + 1
            exp_group = f.create_group(fault_group, groupname.format(index))
            if exp["index"] != index:
                logger.warning(
                    "The index provided was already used. found new one: {}".format(
                        index
                    )
                )
            num_exp = num_exp - 1
            pbar.update(1)
        elif exp["index"] == -2 and log_pregoldenrun:
            if "Pregoldenrun" in f.root:
                raise ValueError("Pregoldenrun already exists!")
            exp_group = f.create_group(
                "/",
                "Pregoldenrun",
                "Group containing all information regarding firmware running before start point is reached",
            )
            exp_group._v_attrs["architecture"] = exp["architecture"]
            log_pregoldenrun = False
        elif exp["index"] == -1 and log_goldenrun:
            if "Goldenrun" in f.root:
                raise ValueError("Goldenrun already exists!")
            exp_group = f.create_group(
                "/", "Goldenrun", "Group containing all information about goldenrun"
            )
            log_goldenrun = False
        elif exp["index"] == -3 and log_config:
            if "backup" in f.root:
                raise ValueError("Backup already exists!")
            exp_group = f.create_group(
                "/", "Backup", "Group containing backup and run information"
            )

            process_backup(f, exp_group, exp, myfilter, stop_signal)
            log_config = False
            continue
        else:
            continue

        datasets = []
        datasets.append((process_tbinfo, "tbinfo"))
        datasets.append((process_tbexec, "tbexec"))
        datasets.append((process_memory_info, "meminfo"))
        datasets.append((process_dumps, "memdumplist"))
        datasets.append((process_memmap, "memmaplist"))
        datasets.append((process_arm_registers, "armregisters"))
        datasets.append((process_riscv_registers, "riscvregisters"))
        datasets.append((process_tb_faulted, "tbfaulted"))

        for fn_ptr, keyword in datasets:
            if keyword not in exp:
                continue
            fn_ptr(f, exp_group, exp[keyword], myfilter)

        # safe fault config
        process_faults(
            f, exp_group, exp["faultlist"], exp["endpoint"], exp["end_reason"], myfilter
        )

        if callable(logger_postprocess):
            logger_postprocess(f, exp_group, exp, myfilter)

        del exp

    pbar.close()
    f.close()
    logger.debug("Data Logging done")
