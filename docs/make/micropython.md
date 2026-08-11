# MicroPython 1.27.0 (binary + lib)
  - Homepage: [https://micropython.org/](https://micropython.org/)
  - Manpage: [https://docs.micropython.org/en/latest/](https://docs.micropython.org/en/latest/)
  - Changelog: [https://github.com/micropython/micropython/releases](https://github.com/micropython/micropython/releases)
  - Repository: [https://github.com/micropython/micropython](https://github.com/micropython/micropython)
  - Package: [master/make/pkgs/micropython/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/micropython/)
  - Steward: Ircama
  - Toolchain: requires GCC 8 or newer (`FREETZ_TARGET_GCC_8_MIN` in `Config.in`): the unix port Makefile uses `-Wfloat-conversion` (GCC 4.9+) and the package adds `-Wno-stringop-overflow` (GCC 8+); the old GCC 4.6.4 toolchain rejects both with "unrecognized command line option", failing the qstr header generation. This is a GCC issue, not uClibc-specific: uClibc 1.0.14 with GCC 5.5 would also fail on `-Wno-stringop-overflow`, so a uClibc gate would be wrong.
