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
import time

import numpy
import prctl
import tables


logger = logging.getLogger(__name__)


# Tables for storing the elements from queue
class translation_block_table(tables.IsDescription):
    identity = tables.UInt64Col()
    size = tables.UInt64Col()
    ins_count = tables.UInt64Col()
    num_exec = tables.UInt64Col()
    assembler = tables.StringCol(1000)


class translation_block_faulted_table(tables.IsDescription):
    faultaddress = tables.UInt64Col()
    assembler = tables.StringCol(1000)


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


binary_atom = tables.UInt8Atom()


def process_tb_faulted(f, group, tbfaulted_list, myfilter):
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


def process_faults(f, group, faultlist, endpoint, end_reason, myfilter):
    # create table
    faulttable = f.create_table(
        group,
        "faults",
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
        faultrow.append()
    faulttable.flush()
    faulttable.close()


def process_tbinfo(f, group, tbinfolist, myfilter):
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


def hdf5collector(
    hdf5path, mode, queue_output, num_exp, compressionlevel, logger_postprocess=None
):
    prctl.set_name("logger")
    prctl.set_proctitle("logger")
    f = tables.open_file(hdf5path, mode)
    if "fault" in f.root:
        fault_group = f.root.fault
    else:
        fault_group = f.create_group("/", "fault", "Group containing fault results")
    myfilter = tables.Filters(complevel=compressionlevel, complib="zlib")
    t0 = time.time()
    tmp = "{}".format(num_exp)
    groupname = "experiment{:0" + "{}".format(len(tmp)) + "d}"
    while num_exp > 0:
        # readout queue and get next output from qemu. Will block
        exp = queue_output.get()
        t1 = time.time()
        logger.info(
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
        elif exp["index"] == -2:
            if "Pregoldenrun" in f.root:
                raise ValueError("Pregoldenrun already exists!")
            exp_group = f.create_group(
                "/",
                "Pregoldenrun",
                "Group containing all information regarding firmware running before start point is reached",
            )
        elif exp["index"] == -1:
            if "Goldenrun" in f.root:
                raise ValueError("Goldenrun already exists!")
            exp_group = f.create_group(
                "/", "Goldenrun", "Group containing all information about goldenrun"
            )
        else:
            raise ValueError("Index is not supposed to be negative")

        datasets = []
        datasets.append((process_tbinfo, "tbinfo"))
        datasets.append((process_tbexec, "tbexec"))
        datasets.append((process_memory_info, "meminfo"))
        datasets.append((process_dumps, "memdumplist"))
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

    f.close()
    logger.info("Data Logging done")
