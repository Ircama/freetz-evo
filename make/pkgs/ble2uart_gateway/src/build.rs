//! Link the optional Theengs Decoder static library.
//!
//! The library is C++ (GPL-3.0-or-later) and is built by the freetz package
//! (`FREETZ_PACKAGE_BLE2UART_GATEWAY_THEENGS`) with the target `g++`. The
//! package passes `THEENGS_LIB_DIR` with `libtheengs.a`; nothing is downloaded
//! or compiled here, so a host `cargo test` without the variable keeps working.
//!
//! libstdc++ is linked statically: the FRITZ!Box image ships an older
//! libstdc++.so than the cross compiler and mixing them breaks the symbol
//! versions.

use std::env;

fn main() {
    println!("cargo:rerun-if-env-changed=THEENGS_LIB_DIR");
    println!("cargo:rerun-if-changed=build.rs");
    let Ok(dir) = env::var("THEENGS_LIB_DIR") else {
        return;
    };
    if dir.trim().is_empty() {
        return;
    }
    println!("cargo:rustc-link-search=native={dir}");
    println!("cargo:rustc-link-lib=static=theengs");
    println!("cargo:rustc-link-lib=static=stdc++");
    println!("cargo:rustc-link-lib=static=supc++");
    println!("cargo:rustc-link-lib=m");
}
