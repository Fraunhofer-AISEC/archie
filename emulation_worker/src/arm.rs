use pyo3::types::PyDict;
use std::collections::HashMap;
use std::sync::RwLockWriteGuard;
use unicorn_engine::{RegisterARM, Unicorn};

static ARM_REGISTERS: &[(&str, RegisterARM)] = &[
    ("pc", RegisterARM::PC),
    ("r0", RegisterARM::R0),
    ("r1", RegisterARM::R1),
    ("r2", RegisterARM::R2),
    ("r3", RegisterARM::R3),
    ("r4", RegisterARM::R4),
    ("r5", RegisterARM::R5),
    ("r6", RegisterARM::R6),
    ("r7", RegisterARM::R7),
    ("r8", RegisterARM::R8),
    ("r9", RegisterARM::R9),
    ("r10", RegisterARM::R10),
    ("r11", RegisterARM::R11),
    ("r12", RegisterARM::R12),
    ("r13", RegisterARM::R13),
    ("r14", RegisterARM::R14),
    ("r15", RegisterARM::R15),
    ("xpsr", RegisterARM::XPSR),
];

pub fn initialize_arm_registers(uc: &mut Unicorn<()>, registerdump: &PyDict) {
    for (name, reg) in ARM_REGISTERS {
        uc.reg_write(
            *reg,
            registerdump.get_item(*name).unwrap().extract().unwrap(),
        )
        .unwrap();
    }
}

pub fn dump_arm_registers(
    uc: &mut Unicorn<()>,
    mut registerlist: RwLockWriteGuard<Vec<HashMap<String, u64>>>,
    tbcounter: u64,
) {
    let mut dump = HashMap::new();
    for (name, reg) in ARM_REGISTERS {
        dump.insert(name.to_string(), uc.reg_read(*reg).unwrap());
    }
    dump.insert("tbcounter".to_string(), tbcounter);
    registerlist.push(dump);
}
