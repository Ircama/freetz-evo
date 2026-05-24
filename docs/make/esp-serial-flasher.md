# esp-serial-flasher git-f1cccac
  - Homepage: [https://github.com/espressif/esp-serial-flasher](https://github.com/espressif/esp-serial-flasher)
  - Changelog: [https://github.com/espressif/esp-serial-flasher/releases](https://github.com/espressif/esp-serial-flasher/releases)
  - Repository: [https://github.com/espressif/esp-serial-flasher](https://github.com/espressif/esp-serial-flasher)
  - Package: [master/make/pkgs/esp-serial-flasher/](https://github.com/Ircama/freetz-evo/tree/master/make/pkgs/esp-serial-flasher/)
  - Steward: -

  - Depends on: none
  - Provides: /usr/bin/linux_flasher, /usr/bin/esp_fw_upload
  - Externalization: supported

The package ships two command line tools:

- linux_flasher: generic upstream utility using address/file pairs
- esp_fw_upload: Freetz-oriented helper for common ESP32-C3 layouts (bootloader, partition table, app image)

Both tools also accept an optional chip check:

- `-c, --chip <name>` validates the detected chip (`esp32c3`, `esp32s3`, `esp32c6`, ...)

## Complete usage examples

Flash with generic linux_flasher:

linux_flasher -p /dev/ttyACM0 -c esp32c3 0x0 bootloader.bin 0x8000 partition-table.bin 0x10000 firmware.bin

Flash with helper esp_fw_upload defaults:

esp_fw_upload -p /dev/ttyACM0

Flash with explicit files and baudrate:

esp_fw_upload -p /dev/ttyACM0 -c esp32c3 -b 460800 -B bootloader.bin -T partition-table.bin -A ble50_scan.bin

Dry-run command validation:

esp_fw_upload -p /dev/ttyACM0 -n

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

`esp_fw_upload` uses this layout by default for ESP32-C3. `linux_flasher` always uses explicit `<addr> <file>` pairs.

## Externalization

`Externalization: supported` means the package can be externalized, but it is enabled only if
`EXTERNAL_FREETZ_PACKAGE_ESP_SERIAL_FLASHER=y` is selected in menuconfig.

If that symbol is not enabled, binaries remain in `/usr/bin` as usual.
