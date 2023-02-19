use pyo3::types::PyDict;
use std::collections::HashMap;
use std::sync::RwLockWriteGuard;
use unicorn_engine::{
    unicorn_const::{Arch, Mode},
    RegisterARM, RegisterRISCV, Unicorn,
};

static RISCV_REGISTERS: &[(&str, u8)] = &[
    ("pc", RegisterRISCV::PC as u8),
    ("x0", RegisterRISCV::X0 as u8),
    ("x1", RegisterRISCV::X1 as u8),
    ("x2", RegisterRISCV::X2 as u8),
    ("x3", RegisterRISCV::X3 as u8),
    ("x4", RegisterRISCV::X4 as u8),
    ("x5", RegisterRISCV::X5 as u8),
    ("x6", RegisterRISCV::X6 as u8),
    ("x7", RegisterRISCV::X7 as u8),
    ("x8", RegisterRISCV::X8 as u8),
    ("x9", RegisterRISCV::X9 as u8),
    ("x10", RegisterRISCV::X10 as u8),
    ("x11", RegisterRISCV::X11 as u8),
    ("x12", RegisterRISCV::X12 as u8),
    ("x13", RegisterRISCV::X13 as u8),
    ("x14", RegisterRISCV::X14 as u8),
    ("x15", RegisterRISCV::X15 as u8),
    ("x16", RegisterRISCV::X16 as u8),
    ("x17", RegisterRISCV::X17 as u8),
    ("x18", RegisterRISCV::X18 as u8),
    ("x19", RegisterRISCV::X19 as u8),
    ("x20", RegisterRISCV::X20 as u8),
    ("x21", RegisterRISCV::X21 as u8),
    ("x22", RegisterRISCV::X22 as u8),
    ("x23", RegisterRISCV::X23 as u8),
    ("x24", RegisterRISCV::X24 as u8),
    ("x25", RegisterRISCV::X25 as u8),
    ("x26", RegisterRISCV::X26 as u8),
    ("x27", RegisterRISCV::X27 as u8),
    ("x28", RegisterRISCV::X28 as u8),
    ("x29", RegisterRISCV::X29 as u8),
    ("x30", RegisterRISCV::X30 as u8),
    ("x31", RegisterRISCV::X31 as u8),
];

static ARM_REGISTERS: &[(&str, u8)] = &[
    ("pc", RegisterARM::PC as u8),
    ("r0", RegisterARM::R0 as u8),
    ("r1", RegisterARM::R1 as u8),
    ("r2", RegisterARM::R2 as u8),
    ("r3", RegisterARM::R3 as u8),
    ("r4", RegisterARM::R4 as u8),
    ("r5", RegisterARM::R5 as u8),
    ("r6", RegisterARM::R6 as u8),
    ("r7", RegisterARM::R7 as u8),
    ("r8", RegisterARM::R8 as u8),
    ("r9", RegisterARM::R9 as u8),
    ("r10", RegisterARM::R10 as u8),
    ("r11", RegisterARM::R11 as u8),
    ("r12", RegisterARM::R12 as u8),
    ("r13", RegisterARM::R13 as u8),
    ("r14", RegisterARM::R14 as u8),
    ("r15", RegisterARM::R15 as u8),
    ("xpsr", RegisterARM::XPSR as u8),
];

#[derive(Clone, Copy)]
pub enum Architecture {
    Arm,
    Riscv,
}

pub trait ArchitectureDependentOperations {
    fn initialize_unicorn(&self) -> Unicorn<'_, ()>;
    fn initialize_registers(
        &self,
        uc: &mut Unicorn<()>,
        registerdump: &PyDict,
        start_address: &mut u64,
    );
    fn dump_registers(
        &self,
        uc: &mut Unicorn<()>,
        registerlist: RwLockWriteGuard<Vec<HashMap<String, u64>>>,
        tbcounter: u64,
    );
}

#[derive(Clone)]
pub struct ArchitectureDependentOperator {
    pub architecture: Architecture,
}

impl ArchitectureDependentOperations for ArchitectureDependentOperator {
    fn initialize_unicorn(self: &ArchitectureDependentOperator) -> Unicorn<'_, ()> {
        match self.architecture {
            Architecture::Arm => {
                Unicorn::new(Arch::ARM, Mode::THUMB).expect("failed to initialize Unicorn instance")
            }
            Architecture::Riscv => Unicorn::new(Arch::RISCV, Mode::RISCV64)
                .expect("failed to initialize Unicorn instance"),
        }
    }

    fn initialize_registers(
        self: &ArchitectureDependentOperator,
        uc: &mut Unicorn<()>,
        registerdump: &PyDict,
        start_address: &mut u64,
    ) {
        let registers;
        match self.architecture {
            Architecture::Arm => {
                registers = ARM_REGISTERS;
                let xpsr_value: u64 = registerdump.get_item("xpsr").unwrap().extract().unwrap();
                *start_address |= (xpsr_value >> 24) & 1; // Activate thumb mode by setting least
                                                          // significant bit of pc if T-bit is set
                                                          // in xpsr register
            }
            Architecture::Riscv => registers = RISCV_REGISTERS,
        }
        for (name, reg) in registers {
            uc.reg_write(
                *reg,
                registerdump.get_item(*name).unwrap().extract().unwrap(),
            )
            .unwrap();
        }
    }

    fn dump_registers(
        self: &ArchitectureDependentOperator,
        uc: &mut Unicorn<()>,
        mut registerlist: RwLockWriteGuard<Vec<HashMap<String, u64>>>,
        tbcounter: u64,
    ) {
        let mut dump = HashMap::new();
        let registers = match self.architecture {
            Architecture::Arm => ARM_REGISTERS,
            Architecture::Riscv => RISCV_REGISTERS,
        };
        for (name, reg) in registers {
            dump.insert(name.to_string(), uc.reg_read(*reg).unwrap());
        }
        dump.insert("tbcounter".to_string(), tbcounter);
        registerlist.push(dump);
    }
}
