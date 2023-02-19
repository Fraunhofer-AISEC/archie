use capstone::{prelude::BuildsCapstone, Capstone};
use priority_queue::PriorityQueue;
use pyo3::{
    prelude::*,
    types::{PyDict, PyList},
};
use std::collections::HashMap;
use std::sync::{Arc, RwLock};

use unicorn_engine::unicorn_const::Permission;

mod architecture;
use crate::architecture::{
    Architecture, ArchitectureDependentOperations, ArchitectureDependentOperator,
};

mod structs;
use crate::structs::{Fault, FaultModel, FaultType, Logs, MemDump, MemInfo, State};

mod hooks;
use crate::hooks::initialize_hooks;

#[pyfunction]
fn run_unicorn(
    pregoldenrun_data: &PyDict,
    faults: Vec<Fault>,
    config: &PyDict,
) -> PyResult<PyObject> {
    let arch_str = pregoldenrun_data
        .get_item("architecture")
        .unwrap()
        .extract()?;
    let arch: Architecture = match arch_str {
        "arm" => Architecture::Arm,
        "riscv64" => Architecture::Riscv,
        _ => panic!("Unsupported architecture"),
    };

    let memorydump: Vec<HashMap<&str, u64>> = config
        .get_item("memorydump")
        .map_or_else(Vec::new, |obj| obj.extract().unwrap());

    let arch_operator = ArchitectureDependentOperator { architecture: arch };
    let emu = &mut arch_operator.initialize_unicorn();

    let registerdumps: &PyList = pregoldenrun_data
        .get_item(String::from(arch_str) + "registers")
        .unwrap()
        .extract()?;
    let start: HashMap<String, u64> = config.get_item("start").unwrap().extract()?;
    let mut start_address = *start.get("address").unwrap();
    arch_operator.initialize_registers(
        emu,
        registerdumps.get_item(0).unwrap().extract()?,
        &mut start_address,
    );

    let memmaplist: &PyList = pregoldenrun_data
        .get_item("memmaplist")
        .unwrap()
        .extract()?;

    for obj in memmaplist.iter() {
        let memmap: &PyDict = obj.extract()?;
        let address: u64 = memmap.get_item("address").unwrap().extract()?;
        let length: usize = memmap.get_item("length").unwrap().extract()?;
        //println!("Mapping memory at {:x} size {:x}", address & (u64::MAX ^0xfff), cmp::max(length, 0x1000));
        match emu.mem_map(
            address & (u64::MAX ^ 0xfff),
            usize::max(length, 0x1000),
            Permission::ALL,
        ) {
            Ok(()) => {}
            Err(unicorn_engine::unicorn_const::uc_error::MAP) => {
                println!("Memory space is already mapped. Ignoring...")
            }
            Err(unicorn_engine::unicorn_const::uc_error::NOMEM) => {
                println!("Memory space too big, cannot allocate. Ignoring...")
            }
            Err(err) => panic!("failed mapping memory: {err:?}"),
        }
    }

    let memdumplist: &PyList = pregoldenrun_data
        .get_item("memdumplist")
        .unwrap()
        .extract()?;
    for obj in memdumplist.iter() {
        let memdump: &PyDict = obj.extract()?;
        let address: u64 = memdump.get_item("address").unwrap().extract()?;
        let dumps: &PyList = memdump.get_item("dumps").unwrap().extract()?;
        let dump: Vec<u8> = dumps.get_item(0).unwrap().extract()?;

        emu.mem_write(address, dump.as_slice())
            .expect("failed to write instructions");
    }

    let logs = Logs {
        meminfo: RwLock::new(HashMap::new()),
        endpoint: RwLock::new((false, 0, 0)),
        tbinfo: RwLock::new(HashMap::new()),
        tbexec: RwLock::new(Vec::new()),
        registerlist: RwLock::new(Vec::new()),
        memdumps: RwLock::new(HashMap::new()),
    };

    let state = State {
        last_tbid: RwLock::new(0),
        tbcounter: RwLock::new(0),
        endpoints: RwLock::new(HashMap::new()),
        faults: RwLock::new(HashMap::new()),
        live_faults: RwLock::new(PriorityQueue::new()),
        instruction_count: RwLock::new(0),
        single_step_hook_handle: RwLock::new(None),
        cs_engine: Capstone::new()
            .arm()
            .mode(capstone::arch::arm::ArchMode::Thumb)
            .build()
            .unwrap(),
        arch_operator: arch_operator.clone(),
        logs,
    };

    let state_arc: Arc<State> = Arc::new(state);
    initialize_hooks(emu, &state_arc, &faults, &memorydump, config)
        .expect("failed initializing hooks");

    let max_instruction_count: usize = config
        .get_item("max_instruction_count")
        .unwrap()
        .extract()?;

    emu.emu_start(start_address, 0, 0, max_instruction_count)
        .unwrap_or_else(|_| println!("failed to emulate code at 0x{:x}", emu.pc_read().unwrap()));

    Python::with_gil(|py| Ok(state_arc.logs.to_object(py)))
}

#[pymodule]
fn emulation_worker(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(run_unicorn, m)?)?;
    Ok(())
}
