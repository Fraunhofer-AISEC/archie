import pickle
import lzma
import tables
import pytest
import pandas as pd
import analysis.analysisfunctions as af


@pytest.fixture
def readtestdata():
    return pickle.load(lzma.open("tests/testdata/test_goldenrun_results.xz", "rb"))


def assert_experiment(golden_data, fault_data):
    faultkeys = [
        "tbexeclist",
        "tbinfo",
        "tbfaulted",
        "meminfo",
        "armregisters",
        "riscvregisters",
    ]
    assert_experiment_data_pd(golden_data, fault_data, faultkeys)
    faultkeys = ["endpoint", "index"]
    assert_experiment_data(golden_data, fault_data, faultkeys)
    if "fault" in golden_data:
        assert "fault" in fault_data
        faultkeys = ["faults"]
        assert_experiment_data_pd(golden_data["fault"], fault_data["fault"], faultkeys)
        faultkeys = ["index", "endpoint"]
        assert_experiment_data(golden_data["fault"], fault_data["fault"], faultkeys)


def assert_experiment_data(golden_data, fault_data, faultkeys):
    for key in faultkeys:
        if not (key in golden_data):
            print(f"{key} not found in golden_data")
            continue
        assert key in fault_data
        print(key)
        print(f"Golden_data {golden_data[key]}")
        print(f"Fault data {fault_data[key]}")
        assert fault_data[key] == golden_data[key]


def assert_experiment_data_pd(golden_data, fault_data, faultkeys):
    for key in faultkeys:
        if not (key in golden_data):
            print(f"{key} not found in golden_data")
            continue
        assert key in fault_data
        print(key)
        print(golden_data[key])
        data = [pd.DataFrame(golden_data[key]), pd.DataFrame(fault_data[key])]
        data = pd.concat(data).drop_duplicates(keep=False)
        print(data)
        assert data.empty


@pytest.mark.order(1)
def test_goldenrun_data_file_load(readtestdata, filename="tests/testdata/golden.hdf5"):
    with tables.open_file(filename, "r") as f:
        golden_data = af.get_goldenrun_data(f)
        #       pickle.dump(golden_data, lzma.open("test_goldenrun_results2.xz", "wb"))
        assert_experiment(golden_data, readtestdata)
