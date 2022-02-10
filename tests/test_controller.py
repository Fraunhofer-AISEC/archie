import pytest
import tables

import analysis.analysisfunctions as af
from test_python_worker import pythonworker_enviroment
import controller
from hdf5logger import hdf5collector
from test_analysisfunctions import assert_experiment


def compare_hdf5_files():
    goldenfile = tables.open_file("tests/testdata/golden.hdf5")
    testfile = tables.open_file("tests/test.hdf5")
    goldenfault = goldenfile.root.fault
    testfault = testfile.root.fault
    gexpnum = sum(1 for x in af.generate_groupname_list(goldenfault))
    fexpnum = sum(1 for x in af.generate_groupname_list(testfault))
    assert gexpnum == fexpnum
    for goldenexp in af.generate_groupname_list(goldenfault):
        gdict = af.get_experiment_group(goldenfault, goldenexp)
        gfault = gdict["fault"]["faults"]
        print(gfault)
        ilist = af.filter_experiment_fault_address(
            testfault, gfault["fault_address"][0]
        )
        ilist = af.filter_experiment_model(
            testfault, gfault["fault_model"][0], interestlist=ilist
        )
        ilist = af.filter_experiment_faultmask(
            testfault, gfault["fault_mask"][0], interestlist=ilist
        )
        ilist = af.filter_experiment_fault_lifespan(
            testfault, gfault["fault_lifespan"][0], interestlist=ilist
        )
        ilist = af.filter_experiment_trigger_address(
            testfault, gfault["trigger_address"][0], interestlist=ilist
        )
        ilist = af.filter_experiment_trigger_counter(
            testfault, gfault["trigger_hitcounter"][0], interestlist=ilist
        )
        assert len(ilist) == 1
        assert goldenexp == ilist[0]
        fdict = af.get_experiment_group(testfault, ilist[0])
        assert_experiment(gdict, fdict)
    gdict = af.get_goldenrun_data(goldenfile)
    fdict = af.get_goldenrun_data(testfile)
    assert_experiment(gdict, fdict)


def test_controller():
    parguments = pythonworker_enviroment()
    controller.controller(
        "tests/test.hdf5",
        parguments["hdf5mode"],
        parguments["faultlist"],
        parguments["qemu_conf"],
        parguments["num_workers"],
        parguments["queuedepth"],
        parguments["compressionlevel"],
        False,
        parguments["goldenrun"],
        hdf5collector,
        qemu_pre,
        qemu_post,
        logger_postprocess,
    )
    compare_hdf5_files()


def qemu_pre():
    qemu_pre_data = 1000  # data to be shared with qemu post
    qemu_custom_path = None  # string to be given to qemu call
    return [qemu_pre_data, qemu_custom_path]


def qemu_post(qemu_pre_data, output):
    assert qemu_pre_data == 1000
    output["testbench"] = qemu_pre_data  # Change output or do postprocessing
    return output


def logger_postprocess(f, exp_group, exp, myfilter):
    assert exp["testbench"] == 1000
