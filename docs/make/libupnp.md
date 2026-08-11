# libupnp 1.14.31
  - Package: [master/make/libs/libupnp/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/libs/libupnp/)
  - Homepage: [https://github.com/pupnp/pupnp](https://github.com/pupnp/pupnp)
  - Provides: `libupnp.so`, `libixml.so` — Portable UPnP SDK
  - Used by: `gerbera`
  - Externalization: supported

libupnp (pupnp) is the Portable UPnP SDK, providing APIs for building UPnP devices and control points. Supports Device and Service descriptions, eventing, and control messaging.

## Build notes

- Requires uClibc 1.0.58 or newer (`FREETZ_TARGET_UCLIBC_1_0_58_MIN` in `Config.in`): libupnp 1.14.31 sets `CMAKE_CXX_STANDARD 14` (required) in `CMakeLists.txt`, which the old GCC 4.6.4 toolchain does not support (CMake error `Target ... requires the language dialect "CXX14"`). The new toolchain (GCC 13.4 + uClibc 1.0.58) supports it.