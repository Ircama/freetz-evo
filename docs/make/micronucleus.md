# micronucleus 2.6
  - Homepage: [https://github.com/micronucleus/micronucleus](https://github.com/micronucleus/micronucleus)
  - Changelog: [https://github.com/micronucleus/micronucleus/releases](https://github.com/micronucleus/micronucleus/releases)
  - Repository: [https://github.com/micronucleus/micronucleus](https://github.com/micronucleus/micronucleus)
  - Package: [master/make/pkgs/micronucleus/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/micronucleus/)
  - Steward: -

  - Depends on: libusb
  - Provides: /usr/bin/micronucleus

micronucleus is a USB bootloader uploader used by Digispark and other ATTiny boards with Micronucleus bootloader.

## Complete usage examples

Upload Intel HEX and run immediately:

micronucleus --run firmware.hex

Upload raw binary:

micronucleus --type raw --run firmware.bin

Erase only:

micronucleus --erase-only

Print bootloader/device information:

micronucleus --info

Timeout after 20 seconds while waiting for device plug-in:

micronucleus --timeout 20 --run firmware.hex

Use fast mode when stable on your hardware:

micronucleus --fast-mode --run firmware.hex
