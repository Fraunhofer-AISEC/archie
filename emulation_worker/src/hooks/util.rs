use crate::structs::{TbExecEntry, TbInfoBlock};
use crate::{Fault, FaultModel, FaultType, MemDump};
use log::debug;
use num::{BigUint, ToPrimitive};
use priority_queue::PriorityQueue;
use std::collections::HashMap;
use std::sync::{RwLockReadGuard, RwLockWriteGuard};
use unicorn_engine::Unicorn;

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

        // Formatting may look a bit weird, but this needs to conform to QEMU's disassembly output
        let mut assembler = String::from(" ");
        let instructions = cs.disasm_all(code.as_slice(), address).unwrap();
        for insn in instructions.iter() {
            assembler += format!(
                "[  {:x} ]: {} {} \n",
                insn.address(),
                insn.mnemonic().unwrap(),
                insn.op_str().unwrap()
            )
            .as_str();
        }
        assembler += " \n";

        tbinfo.insert(
            (address, size as usize),
            TbInfoBlock {
                id: address,
                size,
                ins_count: assembler.matches('\n').count() as u32 - 1,
                num_exec: 1,
                assembler,
            },
        );
    }
}

pub fn log_tb_exec(address: u64, mut tbexec: RwLockWriteGuard<Vec<TbExecEntry>>) {
    let pos: u64 = tbexec.len() as u64 - 1;
    tbexec.push(TbExecEntry { pos, tb: address });
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

// Undo active faults. Returns fault that has been undone
pub fn undo_faults(
    uc: &mut Unicorn<'_, ()>,
    instruction_count: u64,
    faults: RwLockReadGuard<HashMap<u64, Fault>>,
    mut live_faults: RwLockWriteGuard<PriorityQueue<(u64, BigUint), u64>>,
) -> Option<Fault> {
    if live_faults.len() == 0 {
        return None;
    }

    let ((_, _), priority) = live_faults.peek().unwrap();
    let lifespan = u64::MAX - priority;

    if lifespan > instruction_count {
        return None;
    }

    let ((address, prefault_data), _) = live_faults.pop().unwrap();

    let fault = faults.get(&address).unwrap();

    debug!("Undoing fault");
    match fault.r#type {
        FaultType::Register => {
            uc.reg_write(fault.address as i32, prefault_data.to_u64().unwrap())
                .expect("failed restoring register value");
        }
        FaultType::Data | FaultType::Instruction => {
            uc.mem_write(fault.address, prefault_data.to_bytes_le().as_slice())
                .expect("failed restoring memory value");
        }
    }

    Some(*fault)
}

pub fn dump_memory(
    uc: &mut Unicorn<'_, ()>,
    address: u64,
    size: u32,
    mut memdumps: RwLockWriteGuard<HashMap<u64, MemDump>>,
) {
    let dump = uc.mem_read_as_vec(address, size as usize).unwrap();

    if let Some(mem_dump) = memdumps.get_mut(&address) {
        mem_dump.dumps.push(dump);
    } else {
        let mem_dump = MemDump {
            address,
            len: size,
            dumps: Vec::from([dump]),
        };
        memdumps.insert(address, mem_dump);
    }
}

pub fn calculate_fault_size(fault: &Fault) -> u32 {
    if matches!(fault.model, FaultModel::Overwrite) {
        return fault.num_bytes;
    }

    ((fault.mask as f64).log2() / 8_f64).floor() as u32 + 1
}
