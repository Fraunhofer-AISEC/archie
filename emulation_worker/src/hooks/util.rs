use std::collections::HashMap;
use priority_queue::PriorityQueue;
use unicorn_engine::Unicorn;
use std::sync::{RwLockReadGuard, RwLockWriteGuard};
use crate::logs::TbInfoBlock;
use num::{ToPrimitive, BigUint};
use crate::{Fault, FaultModel, FaultType};

pub fn log_tb_info(
    uc: &mut Unicorn<'_, ()>,
    address: u64,
    size: u32,
    cs: &capstone::Capstone,
    mut tbinfo: RwLockWriteGuard<HashMap<(u64, usize), TbInfoBlock>>,
) {
    if let Some(tbinfo) = tbinfo.get_mut(&(address, size as usize)) {
        tbinfo.num_exec += 1;
    } else {
        let code = uc.mem_read_as_vec(address, size as usize).unwrap();
        let assembler = cs.disasm_all(code.as_slice(), address).unwrap().to_string();
        tbinfo.insert(
            (address, size as usize),
            TbInfoBlock {
                id: address,
                size,
                ins_count: assembler.matches('\n').count() as u32,
                num_exec: 1,
                assembler,
            },
        );
    }
}

pub fn apply_model(data: &BigUint, fault: &Fault) -> BigUint {
    let mask_big = BigUint::from_bytes_le(&fault.mask.to_le_bytes());
    match fault.model {
        FaultModel::Set0 => data ^ (data & mask_big),
        FaultModel::Set1 => data | mask_big,
        FaultModel::Toggle => {
            let mask = (BigUint::from(1u32) << data.bits()) - BigUint::from(1u32);
            data ^ mask
        }
        FaultModel::Overwrite => mask_big,
    }
}

pub fn undo_faults(
    uc: &mut Unicorn<'_, ()>,
    instruction_count: u64,
    faults: RwLockReadGuard<HashMap<u64, Fault>>,
    mut live_faults: RwLockWriteGuard<PriorityQueue<(u64, BigUint), u64>>,
) {
    if live_faults.len() == 0 {
        return;
    }

    let ((_, _), priority) = live_faults.peek().unwrap();
    let lifespan = u64::MAX - priority;

    if lifespan > instruction_count {
        return;
    }

    let ((address, prefault_data), _) = live_faults.pop().unwrap();

    let fault = faults.get(&address).unwrap();

    println!("Undoing fault");
    match fault.kind {
        FaultType::Register => {
            uc.reg_write(fault.address as i32, prefault_data.to_u64().unwrap())
                .expect("failed restoring register value");
        }
        FaultType::Data | FaultType::Instruction => {
            uc.mem_write(fault.address, prefault_data.to_bytes_le().as_slice())
                .expect("failed restoring memory value");
        }
    }
}
