# testdisk 7.2
  - Homepage: [https://www.cgsecurity.org/wiki/TestDisk](https://www.cgsecurity.org/wiki/TestDisk)
  - Changelog: [https://github.com/cgsecurity/testdisk/releases](https://github.com/cgsecurity/testdisk/releases)
  - Repository: [https://github.com/cgsecurity/testdisk](https://github.com/cgsecurity/testdisk)
  - Package: [master/make/pkgs/testdisk/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/testdisk/)
  - Steward: Ircama

## Build notes

- **Patch `001-fix-gpt-sys-types-static-init.patch`** (`src/partgpt.c`): testdisk's `gpt_sys_types[]` static array is initialized with the `GPT_ENT_TYPE_*` macros, which are compound literals with a `(const efi_guid_t)` cast. The old GCC 4.6.4 toolchain rejects such casts in static initializers (`initializer element is not constant`). The patch expands the array entries to plain brace initializers (no cast) inside the array only; the macros keep the cast because they are also used as expressions (`guid_cmp`). This is a GCC 4.6 quirk, not uClibc-specific, so a source patch is used instead of a gate (no regression on any toolchain).
testdisk provides partition and file recovery tools for damaged or
accidentally modified storage media.

Typical tools included by this package:

- `testdisk`: interactive partition recovery and repair utility
- `photorec`: file recovery tool based on file signatures
- `fidentify`: identify file type by signature database

Check https://www.cgsecurity.org/testdisk_doc/ dor documentation.
