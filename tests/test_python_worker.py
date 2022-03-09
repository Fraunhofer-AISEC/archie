import json
from multiprocessing import Queue, cpu_count
import pytest
import pickle
import lzma

import controller
from faultclass import python_worker, Fault
from test_analysisfunctions import assert_experiment


class test_args:
    def __init__(self):
        self.append = False
        self.indexbase = None
        self.worker = cpu_count()
        self.queuedepth = 15
        self.compressionlevel = None
        self.qemu = "qemuconf.json"
        self.gdb = False
        self.faults = "tests/testdata/fault.json"
        self.hdf5file = "tests/test.hdf5"
        self.debug = False

    def open_files(self):
        self.qemu = open(self.qemu)
        self.faults = open(self.faults)


def pythonworker_enviroment():
    args = test_args()
    args.open_files()
    parguments = controller.process_arguments(args)
    return parguments


# fmt: off
@pytest.mark.parametrize(
    "fault, comparedata",
    [
        (
            [Fault(134217954, 1, 1, 10, 4, 134217986, 1, 0)],
            "tests/testdata/worker_instructions.xz",
        ),
        (
            [Fault(134217728, 0, 2, 1000, 3, 134217950, 1, 0)],
            "tests/testdata/worker_data.xz",
        ),
        (
            [Fault(3, 2, 1, 0, 4, 134217954, 1, 0)],
            "tests/testdata/worker_register.xz"
        ),
        (
            [Fault(0x80000C0, 1, 3, 0, 191, 0x800019C, 1, 2)],
            "tests/testdata/worker_overwrite.xz",
        ),
    ],
)
@pytest.mark.order(2)
# fmt: on
def test_python_worker(fault, comparedata):
    parguments = pythonworker_enviroment()
    parguments["qemu_conf"]["max_instruction_count"] = 4000288
    parguments["qemu_conf"]["end"]["counter"] = 0
    queue_output = Queue()
    python_worker(
        fault,
        parguments["qemu_conf"],
        0,
        queue_output,
        False,
    )
    experimentdata = queue_output.get()
    # pickle.dump(experimentdata, lzma.open(comparedata, "wb"))
    comparedata = pickle.load(lzma.open(comparedata, "rb"))
    assert_experiment(comparedata, experimentdata)
