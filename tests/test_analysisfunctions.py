import pickle
import lzma
import tables
import pytest
from deepdiff import DeepDiff
import pandas as pd
import analysis.analysisfunctions as af


@pytest.fixture
def readtestdata():
    return pickle.load(lzma.open("tests/testdata/test_goldenrun_results.xz", "rb"))


def test_goldenrun_data_file_load(readtestdata, filename="tests/testdata/golden.hdf5"):
    with tables.open_file(filename, "r") as f:
        golden_data = af.get_goldenrun_data(f)
        #       pickle.dump(golden_data, lzma.open("test_goldenrun_results2.xz", "wb"))
        assert not DeepDiff(golden_data["tbinfo"], readtestdata["tbinfo"])
        assert not DeepDiff(golden_data["tbexec"], readtestdata["tbexec"])
        assert not DeepDiff(golden_data["meminfo"], readtestdata["meminfo"])
