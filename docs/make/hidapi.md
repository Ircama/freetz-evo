# hidapi 0.15.0
  - Homepage: [https://libusb.info/hidapi/](https://libusb.info/hidapi/)
  - Changelog: [https://github.com/libusb/hidapi/releases](https://github.com/libusb/hidapi/releases)
  - Repository: [https://github.com/libusb/hidapi](https://github.com/libusb/hidapi)
  - Package: [master/make/libs/hidapi/](https://github.com/Ircama/freetz-evo/tree/master/make/libs/hidapi/)
  - Steward: -

  - Depends on: `cmake-host`, `libusb1`
  - Provides: `libhidapi-libusb.so.0` (always) and, optionally,
    `libhidapi-hidraw.so.0` (`FREETZ_LIB_hidapi_hidraw`)
  - Externalization: supported

`hidapi` is a multi-platform library that enables applications to interface with
Bluetooth and USB HID-class devices.

In Freetz-EVO:

- The **libusb** backend (`libhidapi-libusb`) is **always** built. It talks to
  the device via the kernel's usbfs interface directly, so it does **not**
  require the kernel HID/INPUT subsystem. This is the backend used by
  `hidws` and `ja11-config-tui`, and it is the only one that works on
  GRX5 routers (e.g. 7590AX), where the AVM kernel lacks `CONFIG_INPUT` and
  `hid.ko` cannot load.
- The **hidraw** backend (`libhidapi-hidraw`) is optional and controlled by
  `FREETZ_LIB_hidapi_hidraw`. It requires the kernel HID modules
  (`hid.ko`, `hid-generic.ko`, `usbhid.ko`) and is **not** compatible with
  GRX5 devices.

The package includes a minimal stub `libudev` implementation to satisfy hidapi's
build-time dependency on udev without pulling in the full systemd/libudev stack.

## Runtime interface

- shared library `libhidapi-libusb.so.0.15.0` plus SONAME symlinks
  (and `libhidapi-hidraw.so.0.15.0` when the hidraw backend is enabled)
- ABI-compatible runtime for applications communicating with HID-class devices
