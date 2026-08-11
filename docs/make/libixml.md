# libixml 1.14.31
  - Package: [master/make/libs/libixml/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/libs/libixml/)
  - Homepage: [https://github.com/pupnp/pupnp](https://github.com/pupnp/pupnp)
  - Provides: `libixml.so` — XML parsing library (part of libupnp)
  - Used by: —
  - Externalization: supported

libixml is an XML parsing library distributed as part of the Portable UPnP SDK (libupnp). It provides minimal XML document object model parsing for UPnP device descriptions and control messages.

## Build notes

- Requires uClibc 1.0.58 or newer (`FREETZ_TARGET_UCLIBC_1_0_58_MIN` in `Config.in`): libixml is built from the same source as libupnp, which requires C++14 (`CMAKE_CXX_STANDARD 14`), unsupported by the old GCC 4.6.4 toolchain. It also depends on the libupnp binary.