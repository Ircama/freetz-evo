# libnpupnp 6.3.0
  - Package: [master/make/libs/libnpupnp/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/libs/libnpupnp/)
  - Homepage: [https://github.com/OpenRGB/libnpupnp](https://github.com/OpenRGB/libnpupnp)
  - Provides: `libnpupnp.so` — New generation UPnP SDK
  - Used by: `gerbera`
  - Externalization: supported
  - Toolchain: requires uClibc 1.0.58 or newer

libnpupnp is a newer, refactored UPnP SDK library based on libupnp, providing UPnP device and control point functionality with improved threading and modern C++ integration.

Requires uClibc 1.0.58 or newer: it uses C++17 `std::scoped_lock`,
which the old GCC toolchains (uClibc 0.9.x, 1.0.14) do not support, so
the option is disabled on older toolchains (`FREETZ_TARGET_UCLIBC_1_0_58_MIN`).