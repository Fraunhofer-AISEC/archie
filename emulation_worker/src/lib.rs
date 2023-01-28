use pyo3::{prelude::*, types::{PyDict, PyList}};
use std::collections::HashMap;
use unicorn_engine::Unicorn;
use unicorn_engine::unicorn_const::{
    Arch,
    Mode,
    Permission,
};
use unicorn_engine::RegisterARM;

fn initialize_arm_registers(emu: &mut Unicorn<()>, registerdump: &PyDict) {
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

#[pyfunction]
fn run_unicorn(pregoldenrun_data: &PyDict, config: &PyDict) -> PyResult<bool> {
    let memdumplist: &PyList = pregoldenrun_data.get_item("memdumplist").unwrap().extract()?;

    println!("{:?}", config);
    let mut unicorn = Unicorn::new(Arch::ARM, Mode::THUMB).expect("failed to initialize Unicorn instance");
    let emu = &mut unicorn;

    for obj in memdumplist.iter() {
        let memdump: &PyDict = obj.extract()?;
        let address: u64 = memdump.get_item("address").unwrap().extract()?;
        let length: usize = memdump.get_item("len").unwrap().extract()?;
        let dumps: &PyList = memdump.get_item("dumps").unwrap().extract()?;
        let dump: Vec<u8> = dumps.get_item(0).unwrap().extract()?;


        // TODO: Use correct permissions
        emu.mem_map(address, length, Permission::ALL).expect("failed to map code page");
        emu.mem_write(address, dump.as_slice()).expect("failed to write instructions");
    }

    let armregisters: &PyList = pregoldenrun_data.get_item("armregisters").unwrap().extract()?;
    let registerdump: &PyDict = armregisters.get_item(0).unwrap().extract()?;

    initialize_arm_registers(emu, registerdump);

    let max_instruction_count: usize = config.get_item("max_instruction_count").unwrap().extract()?;
    let start: HashMap<String, u64> = config.get_item("start").unwrap().extract()?;

    emu.emu_start(*start.get("address").unwrap()+1, 0, 0, max_instruction_count).expect("failed to emulate code");

    println!("{:?}", emu.reg_read(RegisterARM::PC).unwrap());
    Ok(true)
}

#[pymodule]
fn emulation_worker(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(run_unicorn, m)?)?;
    Ok(())
}
