use pyo3::{prelude::*, types::{PyDict, PyList}};
use std::collections::HashMap;
use std::sync::Arc;
use std::sync::RwLock;

use unicorn_engine::Unicorn;
use unicorn_engine::unicorn_const::{
    Arch,
    Mode,
    Permission,
    MemType,
    HookType
};
use unicorn_engine::RegisterARM;

#[derive(Clone)]
struct MemInfo(u64, u32, u8, u64, usize);
impl ToPyObject for MemInfo {
    fn to_object(&self, py: Python<'_>) -> PyObject {
        let dict = PyDict::new(py);
        dict.set_item("ins", self.0).unwrap();
        dict.set_item("counter", self.1).unwrap();
        dict.set_item("direction", self.2).unwrap();
        dict.set_item("address", self.3).unwrap();
        dict.set_item("size", self.4).unwrap();

        dict.to_object(py)
    }
}

struct Logs {
    meminfo: RwLock<HashMap<String, MemInfo>>
}

impl ToPyObject for Logs {
    fn to_object(&self, py: Python<'_>) -> PyObject {
        let dict = PyDict::new(py);
        let map = self.meminfo.read().expect("RwLock poisoned");
        dict.set_item("meminfo", map.to_object(py)).unwrap();
        drop(map);

        dict.to_object(py)
    }
}


fn initialize_arm_registers(emu: &mut Unicorn<()>, registerdump: &PyDict) {
    emu.reg_write(RegisterARM::R0, registerdump.get_item("r0").unwrap().extract().unwrap()).unwrap();
    emu.reg_write(RegisterARM::R1, registerdump.get_item("r1").unwrap().extract().unwrap()).unwrap();
    emu.reg_write(RegisterARM::R2, registerdump.get_item("r2").unwrap().extract().unwrap()).unwrap();
    emu.reg_write(RegisterARM::R3, registerdump.get_item("r3").unwrap().extract().unwrap()).unwrap();
    emu.reg_write(RegisterARM::R4, registerdump.get_item("r4").unwrap().extract().unwrap()).unwrap();
    emu.reg_write(RegisterARM::R5, registerdump.get_item("r5").unwrap().extract().unwrap()).unwrap();
    emu.reg_write(RegisterARM::R6, registerdump.get_item("r6").unwrap().extract().unwrap()).unwrap();
    emu.reg_write(RegisterARM::R7, registerdump.get_item("r7").unwrap().extract().unwrap()).unwrap();
    emu.reg_write(RegisterARM::R8, registerdump.get_item("r8").unwrap().extract().unwrap()).unwrap();
    emu.reg_write(RegisterARM::R9, registerdump.get_item("r9").unwrap().extract().unwrap()).unwrap();
    emu.reg_write(RegisterARM::R10, registerdump.get_item("r10").unwrap().extract().unwrap()).unwrap();
    emu.reg_write(RegisterARM::R11, registerdump.get_item("r11").unwrap().extract().unwrap()).unwrap();
    emu.reg_write(RegisterARM::R12, registerdump.get_item("r12").unwrap().extract().unwrap()).unwrap();
    emu.reg_write(RegisterARM::R13, registerdump.get_item("r13").unwrap().extract().unwrap()).unwrap();
    emu.reg_write(RegisterARM::R14, registerdump.get_item("r14").unwrap().extract().unwrap()).unwrap();
    emu.reg_write(RegisterARM::R15, registerdump.get_item("r15").unwrap().extract().unwrap()).unwrap();
}

fn hook_mem_callback(uc: &mut Unicorn<'_, ()>, mem_type: MemType, address: u64, size: usize, _value: i64, logs: &Arc<Logs>) -> bool {
    let pc = uc.reg_read(RegisterARM::PC).unwrap();

    let identifier = format!("{address}|{pc}");

    let mut map = logs.meminfo.write().expect("RwLock poisoned");

    if map.contains_key(&identifier) {
        if let Some(mut element) = map.get_mut(&identifier) {
            element.1 += 1;
        }
    } else {
        map.insert(identifier, MemInfo(address, 1, if mem_type == MemType::READ { 0 } else { 1 }, pc, size));
    }

    drop(map);

    true
}

#[pyfunction]
fn run_unicorn(pregoldenrun_data: &PyDict, config: &PyDict) -> PyResult<PyObject> {
    let memdumplist: &PyList = pregoldenrun_data.get_item("memdumplist").unwrap().extract()?;

    println!("{:?}", config);
    let mut unicorn = Unicorn::new(Arch::ARM, Mode::THUMB).expect("failed to initialize Unicorn instance");
    let emu = &mut unicorn;

    for obj in memdumplist.iter() {
        let memdump: &PyDict = obj.extract()?;
        let address: u64 = memdump.get_item("address").unwrap().extract()?;
        let length: usize = memdump.get_item("len").unwrap().extract()?;
        let dumps: &PyList = memdump.get_item("dumps").unwrap().extract()?;
        let dump: Vec<u8> = dumps.get_item(0).unwrap().extract()?;


        // TODO: Use correct permissions
        emu.mem_map(address, length, Permission::ALL).expect("failed to map code page");
        emu.mem_write(address, dump.as_slice()).expect("failed to write instructions");
    }

    let armregisters: &PyList = pregoldenrun_data.get_item("armregisters").unwrap().extract()?;
    let registerdump: &PyDict = armregisters.get_item(0).unwrap().extract()?;

    initialize_arm_registers(emu, registerdump);

    let logs = Logs { meminfo: RwLock::new(HashMap::new()) };

    let logs_arc : Arc<Logs> = Arc::new(logs);
    {
        let logs_arc = Arc::clone(&logs_arc);
        let hook_mem_closure = move |uc: &mut Unicorn<'_, ()>, mem_type: MemType, address: u64, size: usize, value: i64| -> bool {
            hook_mem_callback(uc, mem_type, address, size, value, &logs_arc)
        };

        emu.add_mem_hook(HookType::MEM_READ | HookType::MEM_WRITE, 0, u64::MAX, hook_mem_closure).expect("failed to add read mem hook");
    }

    let max_instruction_count: usize = config.get_item("max_instruction_count").unwrap().extract()?;
    let start: HashMap<String, u64> = config.get_item("start").unwrap().extract()?;
    emu.emu_start(*start.get("address").unwrap()+1, 0, 0, max_instruction_count).expect("failed to emulate code");

    println!("{:?}", emu.reg_read(RegisterARM::PC).unwrap());

    let gil = Python::acquire_gil();
    let py = gil.python();

    Ok(logs_arc.to_object(py))
}

#[pymodule]
fn emulation_worker(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(run_unicorn, m)?)?;
    Ok(())
}
