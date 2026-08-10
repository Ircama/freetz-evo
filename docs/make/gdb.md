# gdb GNU debugger 6.8/7.9.1/17.1 (binary only)
  - Toolchain: gdb 17.1 requires uClibc 1.0.58 or newer (C++17 compiler); on older toolchains use gdb 7.9.1 or 6.8
  - Package: [master/make/pkgs/gdb/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/gdb/)
  - Steward: -

GNU Debugger for on-device debugging and remote debugging scenarios.
The package supports multiple selectable versions to match different
compatibility and footprint requirements.

Typical tools included by this package:

- `gdb`: interactive debugger
- `gdbserver`: remote debug server for target processes
