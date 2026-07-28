# hidapi 0.15.0
  - Homepage: [https://libusb.info/hidapi/](https://libusb.info/hidapi/)
  - Changelog: [https://github.com/libusb/hidapi/releases](https://github.com/libusb/hidapi/releases)
  - Repository: [https://github.com/libusb/hidapi](https://github.com/libusb/hidapi)
  - Package: [master/make/libs/hidapi/](https://github.com/Ircama/freetz-evo/tree/master/make/libs/hidapi/)
  - Steward: -

  - Depends on: `cmake-host`
  - Provides: `libhidapi-hidraw.so.0` shared runtime
  - Externalization: supported

`hidapi` is a multi-platform library that enables applications to interface with Bluetooth and USB HID-class devices. In Freetz-EVO, only the hidraw backend is built (`libhidapi-hidraw`), which uses the Linux kernel's hidraw interface directly and does not require libusb.

The package includes a minimal stub `libudev` implementation to satisfy hidapi's build-time dependency on udev without pulling in the full systemd/libudev stack.

## Runtime interface

- shared library `libhidapi-hidraw.so.0.15.0` plus SONAME symlinks
- ABI-compatible runtime for applications communicating with HID-class devices
