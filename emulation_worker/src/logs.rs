use pyo3::{
    exceptions,
    prelude::*,
    types::{PyDict, PyList},
};
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

#[derive(Debug, Clone, Copy)]
pub enum FaultModel {
    Set0,
    Set1,
    Toggle,
    Overwrite,
}
impl<'a> FromPyObject<'a> for FaultModel {
    fn extract(arg: &'a PyAny) -> PyResult<FaultModel> {
        let id: u8 = arg.extract().unwrap();
        match id {
            0 => Ok(FaultModel::Set0),
            1 => Ok(FaultModel::Set1),
            2 => Ok(FaultModel::Toggle),
            3 => Ok(FaultModel::Overwrite),
            4..=u8::MAX => Err(exceptions::PyValueError::new_err("unknown fault model")),
        }
    }
}

#[derive(Debug, Clone, Copy)]
pub enum FaultType {
    Data,
    Instruction,
    Register,
}
impl<'a> FromPyObject<'a> for FaultType {
    fn extract(arg: &'a PyAny) -> PyResult<FaultType> {
        let id: u8 = arg.extract().unwrap();
        match id {
            0 => Ok(FaultType::Data),
            1 => Ok(FaultType::Instruction),
            2 => Ok(FaultType::Register),
            3..=u8::MAX => Err(exceptions::PyValueError::new_err("unknown fault type")),
        }
    }
}

#[derive(FromPyObject, Debug, Clone, Copy)]
pub struct Trigger {
    pub address: u64,
    pub hitcounter: u32,
}

#[derive(FromPyObject, Debug, Clone, Copy)]
pub struct Fault {
    pub trigger: Trigger,
    pub address: u64,
    #[pyo3(attribute("type"))]
    pub r#type: FaultType,
    pub model: FaultModel,
    pub mask: u128,
    pub lifespan: u32,
    pub num_bytes: u32,
}

pub struct Logs {
    pub meminfo: RwLock<HashMap<String, MemInfo>>,
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

pub struct State {
    pub last_tbid: RwLock<u64>,
    pub endpoints: RwLock<HashMap<u64, u32>>,
    pub faults: RwLock<HashMap<u64, Fault>>,

    pub logs: Logs,
}
