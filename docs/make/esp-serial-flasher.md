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

## Complete usage examples

Flash with generic linux_flasher:

linux_flasher /dev/ttyACM0 0x0 bootloader.bin 0x8000 partition-table.bin 0x10000 firmware.bin

Flash with helper esp_fw_upload defaults:

esp_fw_upload -p /dev/ttyACM0

Flash with explicit files and baudrate:

esp_fw_upload -p /dev/ttyACM0 -b 460800 -B bootloader.bin -T partition-table.bin -A ble50_scan.bin

Dry-run command validation:

esp_fw_upload -p /dev/ttyACM0 -n

Typical ESP32-C3 map used by these examples:

- 0x0000 bootloader.bin
- 0x8000 partition-table.bin
- 0x10000 application image
