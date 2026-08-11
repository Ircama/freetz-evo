# libmatroska 1.7.1
  - Package: [master/make/libs/libmatroska/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/libs/libmatroska/)
  - Homepage: [https://github.com/Matroska-Org/libmatroska](https://github.com/Matroska-Org/libmatroska)
  - Provides: `libmatroska.so` — Matroska (MKV) container parser
  - Used by: —
  - Externalization: supported

libmatroska is a C++ library for reading and writing Matroska multimedia container files (MKV, MKA, MKS). It extends the EBML parser in libebml with Matroska-specific element handling.

## Build notes

- Requires uClibc 1.0.58 or newer (`FREETZ_TARGET_UCLIBC_1_0_58_MIN` in `Config.in`): libmatroska 1.7.1 sets `CMAKE_CXX_STANDARD 14` (required) in `CMakeLists.txt`, which the old GCC 4.6.4 toolchain does not support. It also depends on libebml, which has the same requirement.