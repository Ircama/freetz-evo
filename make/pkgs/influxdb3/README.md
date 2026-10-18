# InfluxDB 3 Core: Experimental Freetz Port

This package attempts to build upstream **3.12.1**, not the older Go-based
InfluxDB 1.x server. The source archive is pinned and SHA-256 verified.

## Status

Package registration, source extraction and Cargo workspace parsing pass.
A complete MIPS/uClibc release build and package staging now pass. The packaged
32-bit big-endian MIPS ELF has valid headers and the Freetz interpreter selected
at link time. A real-router smoke test passes startup, line-protocol writes,
SQL queries and recovery of the same rows after a graceful restart. This is
not certification of production workloads or the other target architectures.
No init script, automatic startup or public listener is installed.

The reported `rustix` 1.1.4 uClibc errors have passed a feature-equivalent MIPS
cross-compilation probe. The subsequent DataFusion disk-space counter error is
addressed with `portable-atomic` on targets lacking native 64-bit atomics,
without substituting 32-bit counters; the patched `datafusion-execution` crate
also passes MIPS cross-compilation. The dependency source and single lockfile
edge are patched together, with revision checks and idempotency validation.
The basic MIPS database execution and WAL-recovery checks also pass.

The internal `metric` crate also passes MIPS cross-compilation with the same
full-width fallback. Its source patch includes the corresponding lockfile edge
and has been checked against the pristine archive with zero fuzz.

The `influxdb3_id` crate also passes its focused MIPS build with full-width
Parquet file IDs, checked increments and monotonic recovery preserved. The
WASI HTTP written-byte counter compiles in the production feature graph with
the same fallback and unchanged length checks. Its dependency override is
extracted from the checksum-verified 48.0.1 archive and declared explicitly to
Cargo; production fetch/build operations remain locked.

The table-index cache correction in `influxdb3_write` also compiles in the
production MIPS server graph, retaining full-width atomic access timestamps.
The final server link and the basic real-router runtime checks pass.

The object-store memory cache and Python processing engine also pass the
production MIPS compilation gate with full-width generation counters. Native
64-bit atomic targets retain their original types and memory ordering.

Prometheus 0.14.0 uses a checksum-verified private source override for signed,
unsigned and floating-point-bit atomics on targets without native 64-bit atomics.
Its locked MIPS dependency graph, reproducible patch application and complete
production compilation now pass.

The recipe uses the repository's Rust target mapping for MIPS/MIPSEL, ARM,
x86 and AArch64, including supported endianness variants. These are build
targets, not a tested compatibility matrix. Targets other than MIPS/uClibc still
need compilation and runtime testing. MIPS/uClibc has a passing basic
write/query/restart smoke test, not a complete workload compatibility matrix.

## Build Scope

The build selects the `influxdb3` executable without its top-level default
features: optional cloud CLI backends, large-string offsets and jemalloc
replacement are not requested. Transitive dependencies can still include cloud
libraries. Embedded Python and the SQL/WASM dependency chain remain present.
No authentication, bounds checking or storage-format checks are bypassed.

On targets without native 64-bit atomics, including the current MIPS target,
WASM UDF creation/loading returns an explicit unsupported error. Wasmtime's
required epoch interruption is not available there; it is not silently disabled.
The native-64-bit path retains the original epoch and timeout behavior. The
unsupported-target path compiles in the server graph. The basic database smoke
test does not validate Python plugins or WASM execution.

Protocol Buffers generation uses the source-built `protobuf-host` tool, pinned
to compiler version 3.21.12 with a verified source checksum. The recipe passes
its private compiler and standard include directory explicitly; no system
installation of `protoc` is required and no Protobuf runtime is added to the
router by this host dependency. Protobuf generation and the complete
`generated_types` crate pass the focused MIPS cross-build.

The existing Rust cross-compilation helpers choose the target and build `std`
where required. Rust compilation is serial with LTO disabled to constrain host
memory. Upstream specifies Rust 1.98.1; the first attempt uses the installed
1.98.0 nightly for Freetz's `build-std` workflow, so compiler requirements are
part of the verification rather than assumed satisfied.

The recipe applies the existing Freetz compatibility helpers to its private
Cargo sources: `getrandom` uses the Linux syscall where uClibc lacks the libc
wrapper, and `rustix` uses the Linux ABI constants and uClibc-compatible vectored
I/O aliases. The latter addresses the observed missing constants/types and
termios signedness errors; the complete MIPS server build passes with these
fixes. Database counters, offsets, authentication and random-source semantics
are not narrowed or disabled by these fixes.

The pinned `rustix-linux-procfs` dependency also passes MIPS cross-compilation
after comparing the procfs magic constant in the actual `statfs.f_type` type.
The filesystem identity check is retained; the private registry patch is
version-checked and idempotent.

```sh
make influxdb3-unpacked
make influxdb3-precompiled
```

Size-unit multipliers, including terabytes, are represented exactly in `u64`.
Parsed byte counts are checked before conversion to the target's `usize`:
oversized values are rejected on 32-bit systems, not wrapped or saturated.
Existing memory-size and disk-size APIs keep their native-width byte counts.

## Build Cache And Focused Checks

Cargo dependency sources and target artifacts are kept in a private cache keyed
by release and target architecture under `build/cargo-influxdb3-cache`. Package
source regeneration reconnects that cache instead of discarding all downloads
and compiled dependencies. The source checkout still has its own configuration.
`make influxdb3-clean` removes the package executables, retaining compiled
dependencies. Use `make influxdb3-cargo-clean` only when an intentional full
recompilation is needed; it removes the target cache but retains downloads.

`tests/rustix` contains the focused dependency probe and `atomic64-check`:
the latter checks values above 4 GiB and concurrent increments. Host execution
and MIPS cross-compilation pass. Execution on the MIPS/uClibc router also passes
with `value=4295015487 lock_free=false`; the separate database smoke test also
confirms recovery after restart.

The recipe selects the Freetz ELF interpreter at link time. Post-link interpreter
rewriting with the local `patchelf` produced invalid MIPS program headers and a
startup crash in this probe. The directly linked executable has valid headers
and passes the same runtime test.

## Router Runtime Smoke Test

The verified executable is copied to `/mod/external/usr/bin/influxdb3`. Tests
use a private directory on external USB storage and `127.0.0.1:18281`, with
telemetry, file cache and package management disabled. Authentication is
disabled only for this isolated loopback test, not as a deployment default.

Two integer/float samples are written through the line-protocol API and queried
through SQL before and after a clean stop/start using the same data directory.
Both processes exit successfully and no test listener is left running.
This checks catalog/WAL recovery, not Parquet snapshot/compaction coverage.

The small test uses one I/O thread, one DataFusion thread and a 32 MiB query
pool. Observed resident memory after the query is about 88 MiB; this is not a
load benchmark or a memory bound for production. No autostart is configured.

## Storage And Resources

The database needs substantial RAM, CPU and persistent storage; producing a
cross-compiled binary would not prove it is practical on a low-memory FRITZ!Box.
Externalize the executable rather than putting a large server binary in flash.
Database files must also be placed on persistent storage, never the flash
configuration archive or a small RAM filesystem.

## Upstream

- Source: https://github.com/influxdata/influxdb/tree/v3.12.1
- Build: https://github.com/influxdata/influxdb/blob/v3.12.1/CONTRIBUTING.md
- Product: https://docs.influxdata.com/influxdb3/core/