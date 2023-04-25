use num::{BigUint, ToPrimitive};
use pyo3::types::{PyDict, PyList};
use std::io;
use std::sync::Arc;
use unicorn_engine::unicorn_const::{HookType, MemType};
use unicorn_engine::Unicorn;

use crate::{Fault, FaultModel, FaultType, MemInfo, State};

mod util;
use util::{apply_model, log_tb_exec, log_tb_info, undo_faults};

fn block_hook_cb(uc: &mut Unicorn<'_, ()>, address: u64, size: u32, state: &Arc<State>) {
    // Save current tbid for meminfo logs
    let mut last_tbid = state.last_tbid.write().unwrap();
    *last_tbid = address;

    let live_faults = state.live_faults.read().unwrap();
    let mut single_step_hook_handle = state.single_step_hook_handle.write().unwrap();

    if live_faults.len() == 0 && single_step_hook_handle.is_some() {
        uc.remove_hook(single_step_hook_handle.unwrap())
            .expect("failed removing single step hook");
        *single_step_hook_handle = None;
    }

    if single_step_hook_handle.is_some() {
        return;
    }

    let faults = state.faults.read().unwrap();

    for fault in faults.values() {
        if fault.lifespan == 0 {
            continue;
        }

        if fault.trigger.hitcounter == 1
            && fault.trigger.address >= address
            && fault.trigger.address <= (address + size as u64)
        {
            let state_arc = Arc::clone(state);
            let single_step_hook_closure =
                move |uc: &mut Unicorn<'_, ()>, address: u64, size: u32| {
                    single_step_hook_cb(uc, address, size, &state_arc);
                };
            *single_step_hook_handle = Some(
                uc.add_code_hook(u64::MIN, u64::MAX, single_step_hook_closure)
                    .unwrap(),
            );
            return;
        }
    }

    let tbinfo = state.logs.tbinfo.write().unwrap();
    log_tb_info(uc, address, size, &state.cs_engine, tbinfo);
    let tbexec = state.logs.tbexec.write().unwrap();
    log_tb_exec(address, tbexec);
}

fn end_hook_cb(
    uc: &mut Unicorn<'_, ()>,
    address: u64,
    size: u32,
    state: &Arc<State>,
    first_endpoint: u64,
) {
    let mut endpoints = state.endpoints.write().unwrap();

    let counter = endpoints.get_mut(&address).unwrap();
    if *counter > 1 {
        println!(
            "Decreasing endpoint counter for {:?} to {:?}",
            address, *counter
        );
        *counter -= 1;
    } else {
        let mut endpoint = state.logs.endpoint.write().unwrap();
        *endpoint = (address == first_endpoint, address, 1);
        println!("Reached endpoint at {address:?}");

        // Since this hook has been registered before the single step hook we need to call it
        // manullay to log the last instruction, since the callback would not be called otherwise
        let single_step_hook_handle = state.single_step_hook_handle.read().unwrap();
        if single_step_hook_handle.is_some() {
            single_step_hook_cb(uc, address, size, state);
        }

        uc.emu_stop()
            .expect("failed terminating the emulation engine");
    }
}

fn single_step_hook_cb(uc: &mut Unicorn<'_, ()>, address: u64, size: u32, state: &Arc<State>) {
    let mut instruction_count = state.instruction_count.write().unwrap();
    undo_faults(
        uc,
        *instruction_count,
        state.faults.read().unwrap(),
        state.live_faults.write().unwrap(),
    );
    *instruction_count += 1;

    let tbinfo = state.logs.tbinfo.write().unwrap();
    log_tb_info(uc, address, size, &state.cs_engine, tbinfo);
    let tbexec = state.logs.tbexec.write().unwrap();
    log_tb_exec(address, tbexec);
}

fn mem_hook_cb(
    uc: &mut Unicorn<'_, ()>,
    mem_type: MemType,
    address: u64,
    size: usize,
    _value: i64,
    state: &Arc<State>,
) -> bool {
    let pc = uc.pc_read().unwrap();

    let mut meminfo = state.logs.meminfo.write().unwrap();

    if let Some(mut element) = meminfo.get_mut(&(address, pc)) {
        element.counter += 1;
    } else {
        let last_tbid = *state.last_tbid.read().unwrap();
        meminfo.insert(
            (address, pc),
            MemInfo {
                ins: address,
                counter: 1,
                direction: if mem_type == MemType::READ { 0 } else { 1 },
                address: pc,
                tbid: last_tbid,
                size,
            },
        );
    }

    true
}

fn fault_hook_cb(uc: &mut Unicorn<'_, ()>, address: u64, _size: u32, state: &Arc<State>) {
    let mut faults = state.faults.write().unwrap();

    let fault = faults.get_mut(&address).unwrap();
    if fault.trigger.hitcounter == 0 {
        return;
    }
    fault.trigger.hitcounter -= 1;
    if fault.trigger.hitcounter >= 1 {
        return;
    }

    println!("Executing fault at {address:?}");

    let prefault_data;

    match fault.kind {
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
            prefault_data = data.clone();
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
            prefault_data = register_value.clone();
            let new_value = apply_model(&register_value, fault);
            uc.reg_write(fault.address as i32, new_value.to_u64().unwrap())
                .expect("failed writing register fault");
        }
    }

    if fault.lifespan != 0 {
        let mut live_faults = state.live_faults.write().unwrap();
        let instruction_count = *state.instruction_count.read().unwrap();
        live_faults.push(
            (fault.trigger.address, prefault_data),
            u64::MAX - fault.lifespan as u64 + instruction_count,
        );
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

fn initialize_end_hook(
    emu: &mut Unicorn<()>,
    state_arc: &Arc<State>,
    config: &PyDict,
    first_endpoint: u64,
) -> io::Result<()> {
    let config_endpoints: &PyList = config.get_item("end").unwrap().extract()?;
    for obj in config_endpoints {
        let end: &PyDict = obj.extract()?;
        let address: u64 = end.get_item("address").unwrap().extract()?;
        let counter: u32 = end.get_item("counter").unwrap().extract()?;

        let state_arc = Arc::clone(state_arc);

        let mut endpoints = state_arc.endpoints.write().unwrap();
        endpoints.insert(address, counter);
        drop(endpoints);

        let state_arc = Arc::clone(&state_arc);

        let end_hook_closure = move |uc: &mut Unicorn<'_, ()>, address: u64, size: u32| {
            end_hook_cb(uc, address, size, &state_arc, first_endpoint);
        };
        emu.add_code_hook(address, address, end_hook_closure)
            .expect("failed to add end hook");
    }

    Ok(())
}

fn initialize_fault_hook(
    emu: &mut Unicorn<()>,
    state_arc: &Arc<State>,
    faults: Vec<Fault>,
) -> io::Result<()> {
    for fault in faults {
        let state_arc = Arc::clone(state_arc);

        let mut state_faults = state_arc.faults.write().unwrap();
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
    initialize_end_hook(emu, state_arc, config, faults[0].trigger.address)?;
    initialize_fault_hook(emu, state_arc, faults)?;

    Ok(())
}
