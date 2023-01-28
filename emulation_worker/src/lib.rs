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

mod arm;
use crate::arm::initialize_arm_registers;

mod logs;
use crate::logs::{Logs, MemInfo};

fn hook_mem_callback(uc: &mut Unicorn<'_, ()>, mem_type: MemType, address: u64, size: usize, _value: i64, logs: &Arc<Logs>) -> bool {
    let pc = uc.reg_read(RegisterARM::PC).unwrap();

    let identifier = format!("{address}|{pc}");

    let mut map = logs.meminfo.write().expect("RwLock poisoned");

    if map.contains_key(&identifier) {
        if let Some(mut element) = map.get_mut(&identifier) {
            element.counter += 1;
        }
    } else {
        let last_tbid = *logs.last_tbid.read().unwrap();
        map.insert(identifier, MemInfo{
            ins: address,
            counter: 1,
            direction: if mem_type == MemType::READ { 0 } else { 1 },
            address: pc,
            tbid: last_tbid,
            size
        });
    }

    true
}

fn hook_block_callback(uc: &mut Unicorn<'_, ()>, address: u64, size: u32, logs: &Arc<Logs>) {
    // Save current tbid for meminfo logs
    let mut last_tbid = logs.last_tbid.write().expect("RwLock poisoned");
    *last_tbid = address;
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

    let logs = Logs {
        meminfo: RwLock::new(HashMap::new()),
        last_tbid: RwLock::new(0)
    };
    let logs_arc : Arc<Logs> = Arc::new(logs);

    {
        let logs_arc = Arc::clone(&logs_arc);
        let hook_mem_closure = move |uc: &mut Unicorn<'_, ()>, mem_type: MemType, address: u64, size: usize, value: i64| -> bool {
            hook_mem_callback(uc, mem_type, address, size, value, &logs_arc)
        };
        emu.add_mem_hook(HookType::MEM_READ | HookType::MEM_WRITE, 0, u64::MAX, hook_mem_closure).expect("failed to add read mem hook");
    }

    {
        let logs_arc = Arc::clone(&logs_arc);
        let hook_blcok_closure = move |uc: &mut Unicorn<'_, ()>, address: u64, size: u32| {
            hook_block_callback(uc, address, size, &logs_arc);
        };
        emu.add_block_hook(hook_blcok_closure).expect("failed to add block hook");
    }

    let max_instruction_count: usize = config.get_item("max_instruction_count").unwrap().extract()?;
    let start: HashMap<String, u64> = config.get_item("start").unwrap().extract()?;
    emu.emu_start(*start.get("address").unwrap()+1, 0, 0, max_instruction_count).expect("failed to emulate code");

    let gil = Python::acquire_gil();
    let py = gil.python();

    Ok(logs_arc.to_object(py))
}

#[pymodule]
fn emulation_worker(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(run_unicorn, m)?)?;
    Ok(())
}
