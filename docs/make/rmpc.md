# rmpc 0.11.0
  - Homepage: [https://github.com/mierak/rmpc](https://github.com/mierak/rmpc)
  - Changelog: [https://github.com/mierak/rmpc/releases](https://github.com/mierak/rmpc/releases)
  - Package: [master/make/pkgs/rmpc/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/rmpc/)
  - Steward: -
  - Toolchain: requires uClibc 1.0.58 or newer

  - Depends on: `rust-host` (Rust/Cargo cross-compilation toolchain)
  - Provides: `/usr/bin/rmpc`
  - Externalization: supported

`rmpc` is a beautiful, configurable terminal user interface (TUI) client for the Music Player Daemon (MPD), written in Rust. It features album art display, lyrics integration, playlist management, and a modern terminal interface with mouse support. The package is cross-compiled from upstream Rust sources using the Freetz-EVO Rust toolchain.

## Freetz integration

- intended companion to the local `mpd` package, but can control any reachable MPD server
- requires Rust support enabled in the toolchain settings
- useful for interactive SSH sessions and direct terminal usage on the device
- externalizable to move the binary out of internal flash

## Build characteristics

- Rust/Cargo build with `--release --locked`
- Cross-compiled using the target-specific Rust toolchain; uses `build-std` for targets requiring a custom std build (e.g., MIPS/uClibc with `+nightly`)
- Cargo fetches dependencies during the build; vendored dependencies from the Freetz source mirror
- Rustix uClibc patches, getrandom MIPS syscall patches applied during build for compatibility