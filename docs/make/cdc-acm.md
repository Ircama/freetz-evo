# cdc-acm kernel driver
  - Package area: kernel module exposure in menuconfig
  - Provides: cdc-acm.ko on compatible targets

The cdc-acm kernel driver enables USB CDC ACM serial devices, typically visible as /dev/ttyACM*.

## Typical use cases

- ESP32-C3 and similar boards in native USB serial mode
- USB serial modems and embedded ACM peripherals
- Development boards requiring ACM transport for flashing/logging

## Notes

This is a kernel driver entry, not a standalone user-space binary package.
