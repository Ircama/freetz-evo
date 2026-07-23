# lirc 0.10.2 (LIRC client library)
  - Homepage: [https://lirc.org/](https://lirc.org/)
  - Changelog: [https://sourceforge.net/projects/lirc/files/LIRC/](https://sourceforge.net/projects/lirc/files/LIRC/)
  - Repository: [https://sourceforge.net/p/lirc/git/](https://sourceforge.net/p/lirc/git/)
  - Package: [master/make/libs/lirc/](https://github.com/Ircama/freetz-evo/tree/master/make/libs/lirc/)
  - Steward: -

  - Depends on: `python3-host` (build only)
  - Provides: `liblirc_client.so.0` shared runtime
  - Externalization: supported

LIRC (Linux Infrared Remote Control) is a package that supports receiving and sending infrared signals. In Freetz-EVO, only the client library (`liblirc_client`) is packaged to provide infrared remote control support for applications such as `ncmpc`.

## Runtime interface

- shared library `liblirc_client.so.0.6.0` plus SONAME symlinks
- ABI-compatible runtime for applications that receive LIRC remote control events
- `lirc.pc` installed for `pkg-config` consumers (required by Meson-based packages like `ncmpc`)

## Freetz integration

- only the client library is built; the LIRC daemon, tools, and plugins are disabled
- used by `ncmpc` for optional infrared remote control support
- externalizable to move the shared object out of internal flash

## Build characteristics

- Autotools build with shared and static library enabled
- daemon, tools, and plugins explicitly disabled (`--disable-daemon`, `--disable-tools`, `--disable-plugins`)
- requires `python3-host` for the build system's Python integration
- only the `lib/` subdirectory is built and installed