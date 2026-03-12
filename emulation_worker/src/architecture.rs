use capstone::{prelude::BuildsCapstone, prelude::BuildsCapstoneExtraMode, Capstone};
use pyo3::types::PyDict;
use std::collections::HashMap;
use std::sync::RwLockWriteGuard;
use unicorn_engine::{
    unicorn_const::{Arch, Mode},
    RegisterARM, RegisterARM64, RegisterRISCV, Unicorn,
};

static RISCV_REGISTERS: &[(&str, u16)] = &[
    ("pc", RegisterRISCV::PC as u16),
    ("x0", RegisterRISCV::X0 as u16),
    ("x1", RegisterRISCV::X1 as u16),
    ("x2", RegisterRISCV::X2 as u16),
    ("x3", RegisterRISCV::X3 as u16),
    ("x4", RegisterRISCV::X4 as u16),
    ("x5", RegisterRISCV::X5 as u16),
    ("x6", RegisterRISCV::X6 as u16),
    ("x7", RegisterRISCV::X7 as u16),
    ("x8", RegisterRISCV::X8 as u16),
    ("x9", RegisterRISCV::X9 as u16),
    ("x10", RegisterRISCV::X10 as u16),
    ("x11", RegisterRISCV::X11 as u16),
    ("x12", RegisterRISCV::X12 as u16),
    ("x13", RegisterRISCV::X13 as u16),
    ("x14", RegisterRISCV::X14 as u16),
    ("x15", RegisterRISCV::X15 as u16),
    ("x16", RegisterRISCV::X16 as u16),
    ("x17", RegisterRISCV::X17 as u16),
    ("x18", RegisterRISCV::X18 as u16),
    ("x19", RegisterRISCV::X19 as u16),
    ("x20", RegisterRISCV::X20 as u16),
    ("x21", RegisterRISCV::X21 as u16),
    ("x22", RegisterRISCV::X22 as u16),
    ("x23", RegisterRISCV::X23 as u16),
    ("x24", RegisterRISCV::X24 as u16),
    ("x25", RegisterRISCV::X25 as u16),
    ("x26", RegisterRISCV::X26 as u16),
    ("x27", RegisterRISCV::X27 as u16),
    ("x28", RegisterRISCV::X28 as u16),
    ("x29", RegisterRISCV::X29 as u16),
    ("x30", RegisterRISCV::X30 as u16),
    ("x31", RegisterRISCV::X31 as u16),
];

static ARM_REGISTERS: &[(&str, u16)] = &[
    ("pc", RegisterARM::PC as u16),
    ("r0", RegisterARM::R0 as u16),
    ("r1", RegisterARM::R1 as u16),
    ("r2", RegisterARM::R2 as u16),
    ("r3", RegisterARM::R3 as u16),
    ("r4", RegisterARM::R4 as u16),
    ("r5", RegisterARM::R5 as u16),
    ("r6", RegisterARM::R6 as u16),
    ("r7", RegisterARM::R7 as u16),
    ("r8", RegisterARM::R8 as u16),
    ("r9", RegisterARM::R9 as u16),
    ("r10", RegisterARM::R10 as u16),
    ("r11", RegisterARM::R11 as u16),
    ("r12", RegisterARM::R12 as u16),
    ("r13", RegisterARM::R13 as u16),
    ("r14", RegisterARM::R14 as u16),
    ("r15", RegisterARM::R15 as u16),
    ("xpsr", RegisterARM::XPSR as u16),
];

static AARCH64_REGISTERS: &[(&str, u16)] = &[
    ("pc", RegisterARM64::PC as u16),
    ("x0", RegisterARM64::X0 as u16),
    ("x1", RegisterARM64::X1 as u16),
    ("x2", RegisterARM64::X2 as u16),
    ("x3", RegisterARM64::X3 as u16),
    ("x4", RegisterARM64::X4 as u16),
    ("x5", RegisterARM64::X5 as u16),
    ("x6", RegisterARM64::X6 as u16),
    ("x7", RegisterARM64::X7 as u16),
    ("x8", RegisterARM64::X8 as u16),
    ("x9", RegisterARM64::X9 as u16),
    ("x10", RegisterARM64::X10 as u16),
    ("x11", RegisterARM64::X11 as u16),
    ("x12", RegisterARM64::X12 as u16),
    ("x13", RegisterARM64::X13 as u16),
    ("x14", RegisterARM64::X14 as u16),
    ("x15", RegisterARM64::X15 as u16),
    ("x16", RegisterARM64::X16 as u16),
    ("x17", RegisterARM64::X17 as u16),
    ("x18", RegisterARM64::X18 as u16),
    ("x19", RegisterARM64::X19 as u16),
    ("x20", RegisterARM64::X20 as u16),
    ("x21", RegisterARM64::X21 as u16),
    ("x22", RegisterARM64::X22 as u16),
    ("x23", RegisterARM64::X23 as u16),
    ("x24", RegisterARM64::X24 as u16),
    ("x25", RegisterARM64::X25 as u16),
    ("x26", RegisterARM64::X26 as u16),
    ("x27", RegisterARM64::X27 as u16),
    ("x28", RegisterARM64::X28 as u16),
    ("x29", RegisterARM64::X29 as u16),
    ("x30", RegisterARM64::X30 as u16),
    ("sp", RegisterARM64::SP as u16),
    ("cpsr", RegisterARM64::PSTATE as u16),
];

#[derive(Clone, Copy)]
pub enum Architecture {
    Aarch64,
    Arm,
    Riscv64,
}

pub trait ArchitectureDependentOperations {
    fn initialize_unicorn(&self) -> Unicorn<'_, ()>;
    fn initialize_cs_engine(&self) -> Capstone;
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
            Architecture::Aarch64 => {
                Unicorn::new(Arch::ARM64, Mode::ARM).expect("failed to initialize Unicorn instance")
            }
            Architecture::Arm => {
                Unicorn::new(Arch::ARM, Mode::THUMB).expect("failed to initialize Unicorn instance")
            }
            Architecture::Riscv64 => Unicorn::new(Arch::RISCV, Mode::RISCV64)
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
            Architecture::Aarch64 => registers = AARCH64_REGISTERS,
            Architecture::Arm => {
                registers = ARM_REGISTERS;
                let xpsr_value: u64 = registerdump.get_item("xpsr").unwrap().extract().unwrap();
                *start_address |= (xpsr_value >> 24) & 1; // Activate thumb mode by setting least
                                                          // significant bit of pc if T-bit is set
                                                          // in xpsr register
            }
            Architecture::Riscv64 => registers = RISCV_REGISTERS,
        }
        for (name, reg) in registers {
            uc.reg_write(
                *reg,
                registerdump.get_item(*name).unwrap().extract().unwrap(),
            )
            .unwrap();
        }
    }

    fn initialize_cs_engine(self: &ArchitectureDependentOperator) -> Capstone {
        match self.architecture {
            Architecture::Aarch64 => Capstone::new()
                .arm64()
                .mode(capstone::arch::arm64::ArchMode::Arm)
                .build()
                .unwrap(),
            Architecture::Arm => Capstone::new()
                .arm()
                .mode(capstone::arch::arm::ArchMode::Thumb)
                .build()
                .unwrap(),
            Architecture::Riscv64 => Capstone::new()
                .riscv()
                .mode(capstone::arch::riscv::ArchMode::RiscV64)
                .extra_mode(std::iter::once(
                    capstone::arch::riscv::ArchExtraMode::RiscVC,
                ))
                .build()
                .unwrap(),
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
            Architecture::Aarch64 => AARCH64_REGISTERS,
            Architecture::Arm => ARM_REGISTERS,
            Architecture::Riscv64 => RISCV_REGISTERS,
        };
        for (name, reg) in registers {
            dump.insert(name.to_string(), uc.reg_read(*reg).unwrap());
        }
        dump.insert("tbcounter".to_string(), tbcounter);
        registerlist.push(dump);
    }
}
