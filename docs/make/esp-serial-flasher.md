# esp-serial-flasher git-f1cccac
  - Homepage: [https://github.com/espressif/esp-serial-flasher](https://github.com/espressif/esp-serial-flasher)
  - Changelog: [https://github.com/espressif/esp-serial-flasher/releases](https://github.com/espressif/esp-serial-flasher/releases)
  - Repository: [https://github.com/espressif/esp-serial-flasher](https://github.com/espressif/esp-serial-flasher)
  - Package: [master/make/pkgs/esp-serial-flasher/](https://github.com/Ircama/freetz-evo/tree/master/make/pkgs/esp-serial-flasher/)
  - Steward: -

  - Depends on: none
  - Provides: /usr/bin/linux_flasher
  - Externalization: supported

The package ships one command line tool:

- linux_flasher: upstream utility using explicit address/file pairs

Both tools also accept an optional chip check:

- `-c, --chip <name>` validates the detected chip (`esp32c3`, `esp32s3`, `esp32c6`, ...)

## Complete usage examples

Flash ESP32-C3 bootloader + partition table + app image:

linux_flasher -p /dev/ttyACM0 -c esp32c3 0x0 bootloader.bin 0x8000 partition-table.bin 0x10000 firmware.bin

Flash with explicit baudrate and no stub (ROM mode):

linux_flasher -p /dev/ttyACM0 -b 460800 -n -c esp32c3 0x0 bootloader.bin 0x8000 partition-table.bin 0x10000 firmware.bin

Typical ESP32-C3 map used by these examples:

- 0x0000 bootloader.bin
- 0x8000 partition-table.bin
- 0x10000 application image

## Notes compared to esptool

Equivalent address layout for:

`esptool --chip esp32c3 ... write_flash 0x0 bootloader.bin 0x8000 partition-table.bin 0x10000 app.bin`

is exactly:

- bootloader at `0x0`
- partition table at `0x8000`
- app image at `0x10000`

`linux_flasher` always uses explicit `<addr> <file>` pairs.

## Externalization

`Externalization: supported` means the package can be externalized, but it is enabled only if
`EXTERNAL_FREETZ_PACKAGE_ESP_SERIAL_FLASHER=y` is selected in menuconfig.

If that symbol is not enabled, binaries remain in `/usr/bin` as usual.
