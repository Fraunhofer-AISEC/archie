use pyo3::{prelude::*, types::{PyDict, PyList}};
use std::collections::HashMap;
use std::sync::RwLock;

pub struct MemInfo {
    pub ins: u64,
    pub counter: u32,
    pub direction: u8,
    pub address: u64,
    pub tbid: u64,
    pub size: usize,
}

impl ToPyObject for MemInfo {
    fn to_object(&self, py: Python<'_>) -> PyObject {
        let dict = PyDict::new(py);
        dict.set_item("ins", self.ins).unwrap();
        dict.set_item("counter", self.counter).unwrap();
        dict.set_item("direction", self.direction).unwrap();
        dict.set_item("address", self.address).unwrap();
        dict.set_item("tbid", self.tbid).unwrap();
        dict.set_item("size", self.size).unwrap();

        dict.to_object(py)
    }
}


pub struct Logs {
    pub meminfo: RwLock<HashMap<String, MemInfo>>,

    pub last_tbid: RwLock<u64>,
    pub endpoints: RwLock<HashMap<u64, u32>>
}

impl ToPyObject for Logs {
    fn to_object(&self, py: Python<'_>) -> PyObject {
        let dict = PyDict::new(py);

        let meminfo = self.meminfo.read().expect("RwLock poisoned");
        let meminfo_list = PyList::new(py, meminfo.values());

        dict.set_item("meminfo", meminfo_list.to_object(py))
            .unwrap();
        drop(meminfo);

        dict.to_object(py)
    }
}

