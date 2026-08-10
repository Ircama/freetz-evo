# libfmt 12.2.0
  - Package: [master/make/libs/libfmt/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/libs/libfmt/)
  - Homepage: [https://fmt.dev/](https://fmt.dev/)
  - Provides: `libfmt.so` — Modern C++ formatting library
  - Used by: `spdlog`, `gerbera`
  - Externalization: supported
  - Toolchain: requires uClibc 1.0.58 or newer

libfmt is a modern C++ formatting library that provides a fast, safe alternative to C stdio and C++ iostreams, inspired by Python's string formatting.

Requires uClibc 1.0.58 or newer: it uses C++ features not supported by
the old GCC/uClibc toolchains (0.9.x, 1.0.14), which fail to compile
`include/fmt/base.h`. The option is disabled on older toolchains
(`FREETZ_TARGET_UCLIBC_1_0_58`).