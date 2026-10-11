# soapyrtlsdr (SoapySDR module for RTL-SDR)
  - Homepage: [https://github.com/pothosware/SoapyRTLSDR](https://github.com/pothosware/SoapyRTLSDR)
  - Changelog: [https://github.com/pothosware/SoapyRTLSDR/blob/master/CHANGELOG.TXT](https://github.com/pothosware/SoapyRTLSDR/blob/master/CHANGELOG.TXT)
  - Repository: [https://github.com/pothosware/SoapyRTLSDR](https://github.com/pothosware/SoapyRTLSDR)
  - Package: [master/make/pkgs/soapyrtlsdr/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/soapyrtlsdr/)
  - Steward: Ircama

  - Depends on: cmake (host), soapysdr, rtl-sdr
  - Provides: /usr/lib/SoapySDR/modules0.8/libsoapyrtlsdr.so

SoapyRTLSDR is the SoapySDR hardware module for Realtek RTL2832U based DVB-T
dongles (RTL-SDR sticks). It makes the stick usable through the vendor neutral
SoapySDR API, e.g. by `rtl_433 -d driver=rtlsdr` or by any other SoapySDR
client, instead of talking to `librtlsdr` directly.

## What is included

- `/usr/lib/SoapySDR/modules0.8/libsoapyrtlsdr.so` — the loadable module

The module is a plain shared object; SoapySDR enumerates the module directory
(it does not use a fixed file name) and `dlopen()`s every entry it finds. The
upstream CMake target is called `rtlsdrSupport`, so the build product is
`librtlsdrSupport.so`, which this package installs under the conventional
`libsoapyrtlsdr.so` name.

Nothing else of the upstream project is shipped: SoapyRTLSDR contains no
command line tool of its own.

## Usage

```sh
# let rtl_433 pick the dongle through SoapySDR instead of librtlsdr
rtl_433 -d driver=rtlsdr

# a different RTL-SDR instance / tuner gain
rtl_433 -d driver=rtlsdr,rtl_tuner_gain=40.2
```

Module discovery can be redirected with the `SOAPY_SDR_PLUGIN_PATH`
environment variable, which is useful when several module sets are installed.

## Notes

- Requires uClibc 1.0.58 or newer (C++11 toolchain).
- SoapyRTLSDR 0.3.3 still declares `cmake_minimum_required(VERSION 2.8.7)`,
  which CMake 4.x rejects; the package therefore passes
  `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`.
- `SoapySDRUtil` is **not** part of this package, so the module cannot be
  listed from the command line; `rtl_433 -d driver=rtlsdr` is the quickest
  functional test.
- Version 0.3.3 is the last release; the tarball is named
  `soapy-rtl-sdr-0.3.3.tar.gz` (upstream changed the archive naming after
  0.3.0).

