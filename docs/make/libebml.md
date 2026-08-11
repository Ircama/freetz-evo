# libebml 1.4.5
  - Package: [master/make/libs/libebml/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/libs/libebml/)
  - Homepage: [https://github.com/Matroska-Org/libebml](https://github.com/Matroska-Org/libebml)
  - Provides: `libebml.so` — Extensible Binary Meta Language parser
  - Used by: `libmatroska`
  - Externalization: supported

libebml is a C++ library for parsing EBML (Extensible Binary Meta Language) files, the container format used by the Matroska multimedia container (MKV).

## Build notes

- Requires uClibc 1.0.58 or newer (`FREETZ_TARGET_UCLIBC_1_0_58_MIN` in `Config.in`): libebml 1.4.5 sets `CMAKE_CXX_STANDARD 14` (required) in `CMakeLists.txt`, which the old GCC 4.6.4 toolchain does not support (CMake error `Target "ebml" requires the language dialect "CXX14"`). The new toolchain (GCC 13.4 + uClibc 1.0.58) supports it.