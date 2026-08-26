# Freetz-EVO — Rust Cross-Compilation

Freetz-EVO provides cross-compilation of Rust packages for FRITZ!Box targets. The implementation spans two layers: a host-tool wrapper that wires the system Rust toolchain into the build environment, and a comprehensive macro library in `make/include/650-rust-cargo.mk` that handles all the uClibc-specific compatibility work needed to build Rust crates for MIPS, x86, ARM, and Aarch64 targets.

The result is a collection of ~30 Rust packages available for FRITZ!Box devices — terminal tools, music players, system monitors, file managers, and more — none of which would run out of the box on uClibc without the patches Freetz-EVO applies.

All relevant options are available under **Packages** in `make menuconfig`.

---

## rust-host — the host toolchain bridge

`make/host-tools/rust-host/` is a lightweight host-tool makefile that does not download or build a Rust toolchain. Instead, it locates the host system's `rustc` and `cargo` binaries (both the stable channel for simple targets and the nightly channel where `build-std` is required) and creates symbolic links from `$(HOST_TOOLS_DIR)/usr/bin/` into the build environment. This keeps the host system as the single source of truth for toolchain management (`rustup` handles updates, channel switching, and component installs on the host) while still giving the Freetz build system reliable paths to invoke.

In addition to the symlinks, `rust-host` materializes **custom target specification JSON files** from `make/include/rust/` into `toolchain/rust/targets/`. These files define architectures and ABIs that Rust does not ship built-in — for example the `mips-unknown-linux-uclibc` variants, 32-bit x86 uClibc, and armeb (big-endian ARM) uClibc targets. Without these specs, `cargo` would refuse to cross-compile for those targets.

---

## 650-rust-cargo.mk — cross-compilation macro library

The core of the Freetz-EVO Rust support lives in `make/include/650-rust-cargo.mk`. This file provides a set of Make macros that package makefiles call to configure `cargo build --target <triple>` for uClibc cross-compilation. The main macros are:

**`RUST_TARGET_VARS`** sets the environment variables needed for each cross target: `CC`, `AR`, `RUSTFLAGS`, target-specific `CARGO_TARGET_*_LINKER`, and the sysroot paths. On MIPS targets it also adds `-C link-arg=-Wl,-no-pie` to `RUSTFLAGS` because PIE executables crash with `ld-uClibc.so.1` on MIPS.

**`RUST_CARGO_HOME_VARS`** gives each package a private, isolated `CARGO_HOME` directory under `$(PKG_DIR)/.cargo` rather than sharing the global `~/.cargo`. This prevents registry lock contention when packages build in parallel and allows per-package crate patching (the patch files live alongside the package makefile).

**`RUST_CARGO_BUILD_STD_VARS`** activates `cargo +nightly build -Z build-std=std,panic_abort` for targets whose standard library is not pre-compiled and bundled with the toolchain — currently x86, aarch64, and armeb uClibc targets. On these architectures `rustup` does not ship a `std` for the custom uClibc target triple, so `cargo` must rebuild `std` from source. This macro sets the nightly channel, the `-Z build-std` flag, and the `RUSTFLAGS` for `std` itself.

**`RUST_DEPENDS_VARS`** records inter-package and host-tool dependencies so the Freetz dependency resolver knows to build `rust-host` (and optionally `openssl`) before any Rust package.

**`RUST_OPENSSL_CROSS_ENV__INT`** exports the `OPENSSL_DIR`, `OPENSSL_LIB_DIR`, and `OPENSSL_INCLUDE_DIR` variables that the `openssl-sys` crate needs to find the pre-built cross OpenSSL libraries.

---

## uClibc compatibility patches

The most significant engineering in Freetz-EVO's Rust support is the set of **in-registry patches** applied to popular crates that do not build cleanly on uClibc. These patches are applied by Make macros that `sed`-edit the crate source inside `CARGO_HOME` before `cargo build` runs — without forking the crates or maintaining downstream patch queues. Where possible, patches are idempotent.

### rustix

The `rustix` crate (a safe Rust interface to Unix system calls) uses glibc-specific constants and type definitions that uClibc does not provide. Freetz-EVO applies five categories of fixes:

- **Type casts**: `CRDLY`, `FFDLY`, `VTDLY`, and `CMSPAR` constants in `termios.rs` require explicit casts to the type uClibc exposes rather than the glibc type. Without these casts the build fails with type-mismatch errors on any serial/terminal code path.
- **HWPOISON errno**: uClibc's `errno.h` does not define `EHWPOISON`. A compatibility shim injects the numeric value so `rustix` can compile without conditionals for this rare error code.
- **`preadv`/`pwritev` signatures**: uClibc 1.x changed the function signature for `preadv`/`pwritev` relative to what `rustix` expects. The patch adjusts the FFI declaration.
- **Missing constants**: `MFD_CLOEXEC`, `MFD_ALLOW_SEALING`, and several `STATX_*` constants are absent from older uClibc headers. The patch injects the numeric values from the Linux kernel headers directly.
- **Missing symbols**: `AF_XDP` and `EHWPOISON` are injected for build paths that reference them unconditionally.

### nix (versions 0.22 and 0.26)

The `nix` crate provides safe Rust bindings for POSIX APIs. Two version ranges require separate patches:

For **nix 0.22**: modules for `aio` (asynchronous I/O), `personality` (Linux execution domain), `ptrace` (process tracing), and `statfs` (filesystem statistics) are guarded by glibc-only `#[cfg]` attributes that exclude uClibc. The patches add uClibc-compatible guards or stub implementations so these modules compile correctly. Socket options (`SO_REUSEPORT`, `SO_BINDTODEVICE`) and signal type definitions also need adjustments.

For **nix 0.26**: the same categories of issues recur in updated form due to nix's internal refactoring between releases.

### getrandom (versions 0.2, 0.3, 0.4)

The `getrandom` crate provides cryptographically secure random bytes. On MIPS uClibc, the `libc::getrandom` symbol is absent (uClibc 1.0.x on MIPS did not expose the `getrandom(2)` syscall wrapper). The patch replaces the `libc::getrandom` call with a direct `syscall(SYS_getrandom, ...)` invocation, bypassing the missing libc symbol. All three actively-used version branches (0.2, 0.3, 0.4) receive this patch independently because each has a different internal call site.

### libc crate — injected uClibc modules

The upstream `libc` crate ships modules for glibc, musl, and several BSD targets but historically included no `uclibc` modules for x86 32-bit or aarch64. Freetz-EVO injects complete `x86/uclibc.rs` and `aarch64/uclibc.rs` modules into the crate source, providing the type definitions, constants, and function declarations that Rust code compiled for these targets needs. These injected modules follow the same structure as the upstream `linux/musl` modules.

---

## MIPS AtomicU64 fallback

MIPS processors in FRITZ!Box devices are 32-bit, and uClibc on MIPS provides only 32-bit atomic operations. Several Rust crates use `AtomicU64` for performance counters, timestamps, or lock-free data structures — all of which fail to compile on 32-bit MIPS because the hardware lacks a 64-bit compare-and-swap instruction.

Freetz-EVO provides `BOX_CAR_APPLY_ATOMICU64_MUTEX_FALLBACK__INT` and related macros that replace `AtomicU64` with `Mutex<u64>` (or in simpler cases `AtomicU32` with a narrowing cast) in the following crates: `boxcar`, `tui-textarea`, `log2src`, `asyncgit` (from gitui), `russh-sftp`, and `nucleo`. The replacements are applied via the same in-registry `sed` patching mechanism as the uClibc fixes.

---

## Rust package collection

The following Rust packages are available in Freetz-EVO. All are EVO-only additions unless noted.

| Package | Version | Description |
|---|---|---|
| `ncspot` | 1.2.0 | Terminal-based Spotify client |
| `rmpc` | 0.10.0 | Terminal MPD client with album art |
| `ripgrep` | 14.1.1 | Fast recursive grep (`rg`) |
| `bottom` | 0.10.3 | System monitor (CPU, memory, processes) |
| `bandwhich` | 0.23.1 | Network utilization monitor by process |
| `procs` | 0.14.10 | Modern `ps` replacement |
| `broot` | 1.44.8 | Interactive directory navigator |
| `eza` | 0.21.3 | Modern `ls` with colour and icons |
| `gitui` | 0.27.0 | Terminal-based Git UI |
| `jless` | 0.9.0 | Pager for JSON |
| `termscp` | 0.15.2 | Terminal SCP/SFTP/S3 file transfer UI |
| `rainfrog` | 0.2.7 | TUI database client |
| `atuin` | 18.6.1 | Shell history with sync |
| `oxker` | 0.10.0 | TUI Docker container manager |
| `yazi` | 25.4.8 | Terminal file manager |
| `zoxide` | 0.9.7 | Smarter `cd` with frecency ranking |
| `restic` | — | Backup tool (also listed in Go packages) |
| `vhs` | — | Terminal GIF recorder (also in Go) |
| `sha256sum` | — | Standalone `sha256sum` for targets lacking it |
| `tac` | — | Reverse-line-order utility |
| `python3-uv` | — | `uv` Python package manager (maturin build) |
| `python3-cryptography` | — | Python `cryptography` library (maturin build) |
| `lnav-rs` | — | Logfile navigator (Rust components) |

Packages marked with `—` for version are updated to the latest stable at each Freetz-EVO release cycle.

---

## Porting a new Rust package

To add a Rust package to Freetz-EVO, the package makefile should call the standard macros in order:

```makefile
$(call RUST_DEPENDS_VARS, pkg-name)
$(call RUST_TARGET_VARS, pkg-name)
$(call RUST_CARGO_HOME_VARS, pkg-name)
# For non-builtin targets (x86, aarch64, armeb):
$(call RUST_CARGO_BUILD_STD_VARS, pkg-name)
```

If the package transitively depends on any of the patched crates, the relevant patch macros (`RUSTIX_APPLY_UCLIBC_PATCHES_*`, `NIX_APPLY_UCLIBC_MIPS_PATCHES_*`, etc.) should be called in the package's `configure` or `compile` step before `cargo build`. The easiest way to discover which patches are needed is to attempt a build on MIPS and inspect the first compile error — the patched crate list above covers the most common cases.

Packages that use `openssl-sys` should add `$(call RUST_OPENSSL_CROSS_ENV__INT)` to their `$(PKG)_CONFIGURE_ENV` so `openssl-sys` finds the cross-compiled headers and libraries.
