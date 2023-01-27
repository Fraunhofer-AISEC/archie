use pyo3::types::{PyDict, PyList};
use std::io;
use std::sync::Arc;
use unicorn_engine::unicorn_const::{HookType, MemType};
use unicorn_engine::RegisterARM;
use unicorn_engine::Unicorn;

use crate::{MemInfo, Logs};

fn hook_mem_cb(uc: &mut Unicorn<'_, ()>, mem_type: MemType, address: u64, size: usize, _value: i64, logs: &Arc<Logs>) -> bool {
    let pc = uc.reg_read(RegisterARM::PC).unwrap();

    let identifier = format!("{address}|{pc}");

    let mut meminfo = logs.meminfo.write().expect("RwLock poisoned");

    if meminfo.contains_key(&identifier) {
        if let Some(mut element) = meminfo.get_mut(&identifier) {
            element.counter += 1;
        }
    } else {
        let last_tbid = *logs.last_tbid.read().unwrap();
        meminfo.insert(identifier, MemInfo{
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

fn hook_block_cb(_uc: &mut Unicorn<'_, ()>, address: u64, _size: u32, logs: &Arc<Logs>) {
    // Save current tbid for meminfo logs
    let mut last_tbid = logs.last_tbid.write().expect("RwLock poisoned");
    *last_tbid = address;
}

fn end_hook_cb(uc: &mut Unicorn<'_, ()>, address: u64, _size: u32, logs: &Arc<Logs>) {
    let mut endpoints = logs.endpoints.write().expect("RwLock poisoned");

    let counter = endpoints.get_mut(&address).unwrap();
    if *counter > 1 {
        *counter -= 1;
    } else {
        println!("Reached endpoint at {address:?}");
        uc.emu_stop()
            .expect("failed terminating the emulation engine");
    }
}

fn initialize_mem_hook(emu: &mut Unicorn<()>, logs_arc: &Arc<Logs>) -> io::Result<()> {
    let logs_arc = Arc::clone(&logs_arc);
    let hook_mem_closure = move |uc: &mut Unicorn<'_, ()>, mem_type: MemType, address: u64, size: usize, value: i64| -> bool {
        hook_mem_cb(uc, mem_type, address, size, value, &logs_arc)
    };
    emu.add_mem_hook(HookType::MEM_READ | HookType::MEM_WRITE, 0, u64::MAX, hook_mem_closure).expect("failed to add read mem hook");

    Ok(())
}

fn initialize_block_hook(emu: &mut Unicorn<()>, logs_arc: &Arc<Logs>) -> io::Result<()> {
    let logs_arc = Arc::clone(&logs_arc);
    let hook_block_closure = move |uc: &mut Unicorn<'_, ()>, address: u64, size: u32| {
        hook_block_cb(uc, address, size, &logs_arc);
    };
    emu.add_block_hook(hook_block_closure).expect("failed to add block hook");

    Ok(())
}

fn initialize_end_hook(emu: &mut Unicorn<()>, logs_arc: &Arc<Logs>, config: &PyDict) -> io::Result<()> {
    let config_endpoints: &PyList = config.get_item("end").unwrap().extract()?;
    for obj in config_endpoints {
        let end: &PyDict = obj.extract()?;
        let address: u64 = end.get_item("address").unwrap().extract()?;
        let counter: u32 = end.get_item("counter").unwrap().extract()?;

        let logs_arc = Arc::clone(&logs_arc);

        let mut endpoints = logs_arc.endpoints.write().expect("RwLock poisoned");
        endpoints.insert(address, counter);
        drop(endpoints);

        let logs_arc = Arc::clone(&logs_arc);

        let end_hook_closure = move |uc: &mut Unicorn<'_, ()>, address: u64, size: u32| {
            end_hook_cb(uc, address, size, &logs_arc);
        };
        emu.add_code_hook(address, address, end_hook_closure).expect("failed to add block hook");
    }

    Ok(())
}

pub fn initialize_hooks(emu: &mut Unicorn<()>, logs_arc: &Arc<Logs>, config: &PyDict) -> io::Result<()> {
    initialize_mem_hook(emu, logs_arc)?;
    initialize_block_hook(emu, logs_arc)?;
    initialize_end_hook(emu, logs_arc, config)?;

    Ok(())
}
