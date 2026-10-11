# rtl-sdr 2.0.3
  - Homepage: [https://osmocom.org/projects/rtl-sdr/](https://osmocom.org/projects/rtl-sdr/)
  - Changelog: [https://github.com/osmocom/rtl-sdr/commits/master](https://github.com/osmocom/rtl-sdr/commits/master)
  - Repository: [https://github.com/osmocom/rtl-sdr](https://github.com/osmocom/rtl-sdr)
  - Package: [master/make/libs/rtl-sdr/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/libs/rtl-sdr/)

  - Depends on: libusb1
  - Provides: ${FREETZ_LIBRARY_DIR}/librtlsdr.so.2.0.3

rtl-sdr turns a Realtek RTL2832U based DVB-T USB dongle into an SDR receiver.
This library (librtlsdr) is the driver used by rtl_433 and other SDR
applications to access RTL-SDR devices.

## What is included

- `librtlsdr.so.2.0.3` — the shared library (SONAME: `librtlsdr.so.0`)
- `rtl-sdr.h` / `rtl-sdr_export.h` — public headers (staged for cross-compilation)
- `librtlsdr.pc` — pkg-config file (staged)

## Notes

- The library is built with CMake against the freetz `libusb1` package.
- Udev rules and kernel driver detaching are disabled (the target has no udev).
- The RTL-SDR kernel driver (`dvb_usb_rtl28xxu`) must be detached or
  blacklisted for the dongle to be usable.

Project homepage: https://osmocom.org/projects/rtl-sdr/