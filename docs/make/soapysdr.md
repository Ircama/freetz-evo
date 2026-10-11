# soapysdr 0.8.1
  - Homepage: [https://github.com/pothosware/SoapySDR](https://github.com/pothosware/SoapySDR)
  - Changelog: [https://github.com/pothosware/SoapySDR/blob/master/CHANGELOG.md](https://github.com/pothosware/SoapySDR/blob/master/CHANGELOG.md)
  - Repository: [https://github.com/pothosware/SoapySDR](https://github.com/pothosware/SoapySDR)
  - Package: [master/make/libs/soapysdr/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/libs/soapysdr/)

  - Depends on: cmake (host)
  - Provides: ${FREETZ_LIBRARY_DIR}/libSoapySDR.so.0.8.1

SoapySDR is a vendor and platform neutral SDR support library and API. It is
used by applications (e.g. rtl_433) to talk to all kinds of SDR hardware
through a single interface.

## What is included

- `libSoapySDR.so.0.8.1` — the shared library (SONAME: `libSoapySDR.so.0.8`)
- `include/SoapySDR/*` — public headers (staged for cross-compilation)
- `SoapySDR.pc` — pkg-config file (staged)
- `share/cmake/SoapySDR/*` — CMake package config used by `find_package(SoapySDR)`
  (staged)

## Runtime modules

The library alone cannot talk to any radio: hardware support is provided by
loadable modules, which are **not** part of this package. They are looked up in

```
/usr/lib/SoapySDR/modules0.8/
```

or in the directories listed in the `SOAPY_SDR_PLUGIN_PATH` environment
variable. Typical modules are `soapyrtlsdr` (RTL-SDR), `soapyairspy`,
`soapyhackrf` or `soapyremote`. Without at least one module only the built-in
`null` device is available.

## Notes

- Only the runtime library is built: `SoapySDRUtil`, the unit tests and the
  SWIG based Python bindings are disabled.
- SoapySDR 0.8.1 still declares `cmake_minimum_required(VERSION 3.1.0)`, which
  CMake 4.x rejects; the package therefore passes
  `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`.
- Requires uClibc 1.0.58 or newer (C++11 toolchain).
- Used by rtl_433, which enables SoapySDR input support when this library is
  selected.

Project homepage: https://github.com/pothosware/SoapySDR
