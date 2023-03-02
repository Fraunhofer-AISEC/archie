use pyo3::types::PyDict;
use unicorn_engine::{RegisterARM, Unicorn};

pub fn initialize_arm_registers(emu: &mut Unicorn<()>, registerdump: &PyDict) {
    emu.reg_write(RegisterARM::R0, registerdump.get_item("r0").unwrap().extract().unwrap()).unwrap();
    emu.reg_write(RegisterARM::R1, registerdump.get_item("r1").unwrap().extract().unwrap()).unwrap();
    emu.reg_write(RegisterARM::R2, registerdump.get_item("r2").unwrap().extract().unwrap()).unwrap();
    emu.reg_write(RegisterARM::R3, registerdump.get_item("r3").unwrap().extract().unwrap()).unwrap();
    emu.reg_write(RegisterARM::R4, registerdump.get_item("r4").unwrap().extract().unwrap()).unwrap();
    emu.reg_write(RegisterARM::R5, registerdump.get_item("r5").unwrap().extract().unwrap()).unwrap();
    emu.reg_write(RegisterARM::R6, registerdump.get_item("r6").unwrap().extract().unwrap()).unwrap();
    emu.reg_write(RegisterARM::R7, registerdump.get_item("r7").unwrap().extract().unwrap()).unwrap();
    emu.reg_write(RegisterARM::R8, registerdump.get_item("r8").unwrap().extract().unwrap()).unwrap();
    emu.reg_write(RegisterARM::R9, registerdump.get_item("r9").unwrap().extract().unwrap()).unwrap();
    emu.reg_write(RegisterARM::R10, registerdump.get_item("r10").unwrap().extract().unwrap()).unwrap();
    emu.reg_write(RegisterARM::R11, registerdump.get_item("r11").unwrap().extract().unwrap()).unwrap();
    emu.reg_write(RegisterARM::R12, registerdump.get_item("r12").unwrap().extract().unwrap()).unwrap();
    emu.reg_write(RegisterARM::R13, registerdump.get_item("r13").unwrap().extract().unwrap()).unwrap();
    emu.reg_write(RegisterARM::R14, registerdump.get_item("r14").unwrap().extract().unwrap()).unwrap();
    emu.reg_write(RegisterARM::R15, registerdump.get_item("r15").unwrap().extract().unwrap()).unwrap();
}

