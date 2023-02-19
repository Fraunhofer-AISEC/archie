use capstone::{prelude::BuildsCapstone, Capstone};
use priority_queue::PriorityQueue;
use pyo3::{
    prelude::*,
    types::{PyDict, PyList},
};
use std::collections::HashMap;
use std::sync::{Arc, RwLock};

use unicorn_engine::unicorn_const::{Arch, Mode, Permission};
use unicorn_engine::Unicorn;

mod arm;
use crate::arm::{dump_arm_registers, initialize_arm_registers};

mod logs;
use crate::logs::{Fault, FaultModel, FaultType, Logs, MemDump, MemInfo, State};

mod hooks;
use crate::hooks::initialize_hooks;

#[pyfunction]
fn run_unicorn(
    pregoldenrun_data: &PyDict,
    faults: Vec<Fault>,
    config: &PyDict,
) -> PyResult<PyObject> {
    println!("{config:?}");

    let memorydump: Vec<HashMap<&str, u64>> = config.get_item("memorydump").unwrap().extract()?;

    let mut unicorn =
        Unicorn::new(Arch::ARM, Mode::THUMB).expect("failed to initialize Unicorn instance");
    let emu = &mut unicorn;

    let memdumplist: &PyList = pregoldenrun_data
        .get_item("memdumplist")
        .unwrap()
        .extract()?;
    for obj in memdumplist.iter() {
        let memdump: &PyDict = obj.extract()?;
        let address: u64 = memdump.get_item("address").unwrap().extract()?;
        let length: usize = memdump.get_item("len").unwrap().extract()?;
        let dumps: &PyList = memdump.get_item("dumps").unwrap().extract()?;
        let dump: Vec<u8> = dumps.get_item(0).unwrap().extract()?;

        // TODO: Use correct permissions
        emu.mem_map(address, length, Permission::ALL)
            .expect("failed to map code page");
        emu.mem_write(address, dump.as_slice())
            .expect("failed to write instructions");
    }

    let armregisters: &PyList = pregoldenrun_data
        .get_item("armregisters")
        .unwrap()
        .extract()?;
    let registerdump: &PyDict = armregisters.get_item(0).unwrap().extract()?;

    initialize_arm_registers(emu, registerdump);

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
        logs,
    };

    let state_arc: Arc<State> = Arc::new(state);
    initialize_hooks(emu, &state_arc, &faults, &memorydump, config)
        .expect("failed initializing hooks");

    let max_instruction_count: usize = config
        .get_item("max_instruction_count")
        .unwrap()
        .extract()?;
    let start: HashMap<String, u64> = config.get_item("start").unwrap().extract()?;
    emu.emu_start(
        *start.get("address").unwrap() + 1,
        0,
        0,
        max_instruction_count,
    )
    .unwrap_or_else(|_| panic!("failed to emulate code. PC: {}", emu.pc_read().unwrap()));

    Python::with_gil(|py| Ok(state_arc.logs.to_object(py)))
}

#[pymodule]
fn emulation_worker(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(run_unicorn, m)?)?;
    Ok(())
}
