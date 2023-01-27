use pyo3::prelude::*;
use std::collections::HashMap;

/*
struct Trigger {
    address: u64,
    hitcounter: u64
}

struct Fault {
    trigger: Fault,
    address: u64,
    _type: u64,
    model: u64,
    lifespan: u64,
    mask: u64,
    num_bytes: u64,
    wildcard: bool
}
*/

/// Formats the sum of two numbers as string.
#[pyfunction]
fn run_unicorn(pregoldenrun_data: HashMap<String, &PyAny>, config: HashMap<String, &PyAny>) -> PyResult<bool> {
    for entry in config {
        println!("{:?} {:?}", pregoldenrun_data, entry);
    }
    Ok(true)
}

/// A Python module implemented in Rust.
#[pymodule]
fn emulation_worker(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(run_unicorn, m)?)?;
    Ok(())
}
