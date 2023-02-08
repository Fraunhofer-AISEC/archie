use num::{BigUint, ToPrimitive};
use pyo3::types::{PyDict, PyList};
use std::io;
use std::sync::Arc;
use unicorn_engine::unicorn_const::{HookType, MemType};
use unicorn_engine::RegisterARM;
use unicorn_engine::Unicorn;

use crate::{Fault, FaultModel, FaultType, MemInfo, State};

fn mem_hook_cb(uc: &mut Unicorn<'_, ()>, mem_type: MemType, address: u64, size: usize, _value: i64, state: &Arc<State>) -> bool {
    let pc = uc.reg_read(RegisterARM::PC).unwrap();

    let identifier = format!("{address}|{pc}");

    let mut meminfo = state.logs.meminfo.write().expect("RwLock poisoned");

    if meminfo.contains_key(&identifier) {
        if let Some(mut element) = meminfo.get_mut(&identifier) {
            element.counter += 1;
        }
    } else {
        let last_tbid = *state.last_tbid.read().unwrap();
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

fn block_hook_cb(_uc: &mut Unicorn<'_, ()>, address: u64, _size: u32, state: &Arc<State>) {
    // Save current tbid for meminfo logs
    let mut last_tbid = state.last_tbid.write().expect("RwLock poisoned");
    *last_tbid = address;
}

fn end_hook_cb(uc: &mut Unicorn<'_, ()>, address: u64, _size: u32, state: &Arc<State>) {
    let mut endpoints = state.endpoints.write().expect("RwLock poisoned");

    let counter = endpoints.get_mut(&address).unwrap();
    if *counter > 1 {
        println!(
            "Decreasing endpoint counter for {:?} to {:?}",
            address, *counter
        );
        *counter -= 1;
    } else {
        println!("Reached endpoint at {address:?}");
        uc.emu_stop()
            .expect("failed terminating the emulation engine");
    }
}

fn apply_model(data: &BigUint, fault: &Fault) -> BigUint {
    let mask_big = BigUint::from_bytes_le(&fault.mask.to_le_bytes());
    match fault.model {
        FaultModel::Set0 => data ^ (data & mask_big),
        FaultModel::Set1 => data | mask_big,
        FaultModel::Toggle => data & data,
        FaultModel::Overwrite => mask_big
    }
}

fn fault_hook_cb(uc: &mut Unicorn<'_, ()>, address: u64, _size: u32, state: &Arc<State>) {
    let mut faults = state.faults.write().expect("RwLock poisoned");

    let fault = faults.get_mut(&address).unwrap();
    if fault.trigger.hitcounter == 0 {
        return;
    }
    fault.trigger.hitcounter -= 1;
    if fault.trigger.hitcounter >= 1 {
        return;
    }

    println!("Reached fault trigger at {:?}", address);

    match fault.r#type {
        FaultType::Data | FaultType::Instruction => {
            let fault_size = if matches!(fault.model, FaultModel::Overwrite) {
                fault.num_bytes
            } else {
                1
            };
            let data = BigUint::from_bytes_le(
                uc.mem_read_as_vec(fault.address, fault_size as usize)
                    .unwrap()
                    .as_slice(),
            );
            println!(
                "Overwriting {:?} with {:?}",
                data,
                apply_model(&data, fault)
            );
            uc.mem_write(
                fault.address,
                apply_model(&data, fault).to_bytes_le().as_slice(),
            )
            .expect("failed writing fault data to memory");
        }
        FaultType::Register => {
            let register_value = BigUint::from(
                uc.reg_read(fault.address as i32)
                    .expect("failed reading from register"),
            );
            let new_value = apply_model(&register_value, fault);
            uc.reg_write(fault.address as i32, new_value.to_u64().unwrap())
                .expect("failed writing register fault");
            debug!(
                "Faulted register {} from {:x} to {:x}",
                fault.address, register_value, new_value
            );
        }
    }
}

fn initialize_mem_hook(emu: &mut Unicorn<()>, state_arc: &Arc<State>) -> io::Result<()> {
    let state_arc = Arc::clone(state_arc);
    let mem_hook_closure =
        move |uc: &mut Unicorn<'_, ()>,
              mem_type: MemType,
              address: u64,
              size: usize,
              value: i64|
              -> bool { mem_hook_cb(uc, mem_type, address, size, value, &state_arc) };
    emu.add_mem_hook(
        HookType::MEM_READ | HookType::MEM_WRITE,
        0,
        u64::MAX,
        mem_hook_closure,
    )
    .expect("failed to add read mem hook");

    Ok(())
}

fn initialize_block_hook(emu: &mut Unicorn<()>, state_arc: &Arc<State>) -> io::Result<()> {
    let state_arc = Arc::clone(state_arc);
    let block_hook_closure = move |uc: &mut Unicorn<'_, ()>, address: u64, size: u32| {
        block_hook_cb(uc, address, size, &state_arc);
    };
    emu.add_block_hook(block_hook_closure)
        .expect("failed to add block hook");

    Ok(())
}

fn initialize_end_hook(emu: &mut Unicorn<()>, state_arc: &Arc<State>, config: &PyDict) -> io::Result<()> {
    let config_endpoints: &PyList = config.get_item("end").unwrap().extract()?;
    for obj in config_endpoints {
        let end: &PyDict = obj.extract()?;
        let address: u64 = end.get_item("address").unwrap().extract()?;
        let counter: u32 = end.get_item("counter").unwrap().extract()?;

        let state_arc = Arc::clone(state_arc);

        let mut endpoints = state_arc.endpoints.write().expect("RwLock poisoned");
        endpoints.insert(address, counter);
        drop(endpoints);

        let state_arc = Arc::clone(&state_arc);

        let end_hook_closure = move |uc: &mut Unicorn<'_, ()>, address: u64, size: u32| {
            end_hook_cb(uc, address, size, &state_arc);
        };
        emu.add_code_hook(address, address, end_hook_closure)
            .expect("failed to add end hook");
    }

    Ok(())
}

fn initialize_fault_hook(emu: &mut Unicorn<()>, state_arc: &Arc<State>, faults: Vec<Fault>, config: &PyDict) -> io::Result<()> {
    for fault in faults {
        let state_arc = Arc::clone(state_arc);

        let mut state_faults = state_arc.faults.write().expect("RwLock poisoned");
        state_faults.insert(fault.trigger.address, fault);
        drop(state_faults);

        let state_arc = Arc::clone(&state_arc);

        let fault_hook_closure = move |uc: &mut Unicorn<'_, ()>, address: u64, size: u32| {
            fault_hook_cb(uc, address, size, &state_arc);
        };
        emu.add_code_hook(
            fault.trigger.address,
            fault.trigger.address,
            fault_hook_closure,
        )
        .expect("failed to add fault hook");
    }

    Ok(())
}

pub fn initialize_hooks(
    emu: &mut Unicorn<()>,
    state_arc: &Arc<State>,
    faults: Vec<Fault>,
    config: &PyDict,
) -> io::Result<()> {
    initialize_mem_hook(emu, state_arc)?;
    initialize_block_hook(emu, state_arc)?;
    initialize_end_hook(emu, state_arc, config)?;
    initialize_fault_hook(emu, state_arc, faults, config)?;

    Ok(())
}
