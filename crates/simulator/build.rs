//! Record the toolchain that builds the simulator for run manifests.
use std::{env, process::Command};

fn version(program: &str) -> String {
    Command::new(program)
        .arg("--version")
        .output()
        .ok()
        .filter(|o| o.status.success())
        .map(|o| String::from_utf8_lossy(&o.stdout).trim().to_owned())
        .unwrap_or_else(|| "unknown".into())
}

fn main() {
    // Cargo passes the exact compiler and Cargo used for this build.
    let rustc = env::var("RUSTC").unwrap_or_else(|_| "rustc".into());
    let cargo = env::var("CARGO").unwrap_or_else(|_| "cargo".into());
    println!("cargo:rustc-env=DOND_BUILD_RUSTC={}", version(&rustc));
    println!("cargo:rustc-env=DOND_BUILD_CARGO={}", version(&cargo));
    println!("cargo:rerun-if-changed=build.rs");
}
