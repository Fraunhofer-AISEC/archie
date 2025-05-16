use log::{debug, error, info, warn, LevelFilter};
use priority_queue::PriorityQueue;
use pyo3::{
    prelude::*,
    types::{PyDict, PyList},
};
use std::collections::HashMap;
use std::rc::Rc;
use std::sync::RwLock;
use time::macros::format_description;

use unicorn_engine::unicorn_const::Permission;

mod architecture;
use crate::architecture::{
    Architecture, ArchitectureDependentOperations, ArchitectureDependentOperator,
};

mod structs;
use crate::structs::{Fault, FaultModel, FaultType, Logs, MemDump, MemInfo, State};

mod hooks;
use crate::hooks::initialize_hooks;

fn setup_logging(index: u64, debug: bool) {
    let config = simplelog::ConfigBuilder::new()
        .set_time_format_custom(format_description!(
            "[year]-[month]-[day] [hour]:[minute]:[second],[subsecond digits:3]"
        ))
        .build();
    let mut loggers: Vec<Box<dyn simplelog::SharedLogger>> = Vec::new();
    if debug {
        loggers.push(simplelog::WriteLogger::new(
            LevelFilter::Debug,
            config.clone(),
            std::fs::File::create(format!("log_{index:?}.txt")).unwrap(),
        ));
    }
    let log_level = if debug {
        LevelFilter::Debug
    } else {
        LevelFilter::Info
    };
    loggers.push(simplelog::SimpleLogger::new(log_level, config));

    simplelog::CombinedLogger::init(loggers).unwrap();
}

#[pyfunction]
fn run_unicorn(
    pregoldenrun_data: &PyDict,
    faults: Vec<Fault>,
    config: &PyDict,
    index: u64,
    engine_output: bool,
) -> PyResult<PyObject> {
    setup_logging(index, engine_output);

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
        let size: usize = memmap.get_item("size").unwrap().extract()?;
        debug!(
            "Mapping memory at 0x{:x} size 0x{:x}",
            address & (u64::MAX ^ 0xfff),
            usize::max(size, 0x1000)
        );
        match emu.mem_map(
            address & (u64::MAX ^ 0xfff),
            usize::max(size, 0x1000),
            Permission::ALL,
        ) {
            Ok(()) => {}
            Err(unicorn_engine::unicorn_const::uc_error::MAP) => {
                warn!("Memory space is already mapped. Ignoring...")
            }
            Err(unicorn_engine::unicorn_const::uc_error::NOMEM) => {
                warn!("Memory space too big, cannot allocate. Ignoring...")
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
        debug!("writing {:?} bytes to 0x{:x}", dump.len(), address);

        emu.mem_write(address, dump.as_slice())
            .unwrap_or_else(|_| error!("failed to write dumped data at 0x{:X}", address));
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
        cs_engine: arch_operator.initialize_cs_engine(),
        arch_operator: arch_operator.clone(),
        logs,
    };

    let state_rc: Rc<State> = Rc::new(state);
    initialize_hooks(emu, &state_rc, &faults, &memorydump, config)
        .expect("failed initializing hooks");

    let max_instruction_count: usize = config
        .get_item("max_instruction_count")
        .unwrap()
        .extract()?;

    info!("Starting emulation at 0x{:x}", start_address);
    emu.emu_start(start_address, 0, 0, max_instruction_count)
        .unwrap_or_else(|_| error!("failed to emulate code at 0x{:x}", emu.pc_read().unwrap()));

    {
        let state = Rc::clone(&state_rc);
        state.arch_operator.dump_registers(
            emu,
            state.logs.registerlist.write().unwrap(),
            *state.tbcounter.read().unwrap(),
        );
    }
    info!("Finished emulation");

    Python::with_gil(|py| Ok(state_rc.logs.to_object(py)))
}

#[pymodule]
fn emulation_worker(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(run_unicorn, m)?)?;
    Ok(())
}
