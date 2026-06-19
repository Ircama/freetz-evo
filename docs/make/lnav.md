# lnav 0.14.0
  - Homepage: [https://lnav.org/](https://lnav.org/)
  - Manpage: [https://docs.lnav.org/](https://docs.lnav.org/)
  - Changelog: [https://github.com/tstack/lnav/releases](https://github.com/tstack/lnav/releases)
  - Repository: [https://github.com/tstack/lnav](https://github.com/tstack/lnav)
  - Package: [master/make/pkgs/lnav/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/lnav/)
  - Steward: -

- Homepage: https://lnav.org/
- Documentation: https://docs.lnav.org/
- Changelog: https://github.com/tstack/lnav/releases
- Repository: https://github.com/tstack/lnav
- Package: ../../make/pkgs/lnav/

`lnav` is an advanced terminal log viewer and analyzer that can merge,
filter, search, and inspect mixed log files directly on the target device.

## Menuconfig options

- `lnav`: builds the native C/C++ target binary `/usr/bin/lnav`.
- `Build optional Rust extensions (PRQL support)`: enables the bundled
  Rust/Cargo extension library used by upstream `lnav` for PRQL-related
  functionality.

The package keeps `--disable-system-paths` hard-disabled in the recipe because
this is a cross-build safety setting, not a target feature toggle: enabling it
would make configure search host include/library paths such as `/usr` and
`/usr/local`, which is undesirable for freetz cross-compilation.

## Build notes

- GitHub release tarballs do not ship a generated `configure`, so the package
  runs `autoreconf` before configure.
- On 32-bit MIPS targets the final link also needs `libatomic`.
- The package is externalizable through the standard `external` menu and ships
  `/usr/bin/lnav` as external payload when selected.