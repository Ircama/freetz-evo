# telink_tools 1.0
  - Homepage: [https://github.com/Ircama/freetz-ble](https://github.com/Ircama/freetz-ble)
  - Package: [master/make/pkgs/telink_tools/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/telink_tools/)
  - Steward: -
  - Source reference: [https://raw.githubusercontent.com/Ircama/freetz-ble/refs/heads/main/ble-adv-telink/make/Telink_Tools.py](https://raw.githubusercontent.com/Ircama/freetz-ble/refs/heads/main/ble-adv-telink/make/Telink_Tools.py)

  - Depends on: none
  - Provides: /usr/bin/telink_tools

telink_tools is a native C implementation of [Telink_Tools.py](https://github.com/Ircama/freetz-ble/blob/main/ble-adv-telink/make/Telink_Tools.py), designed for Telink BLE bootloader workflows on devices such as TB-03F-KIT and TB-04-KIT.

Supported operations:

- burn: full firmware upload with chip handshake and staged erase/write
- burn_triad: write ProductID + MAC + Secret triad at 0x78000
- erase_flash: erase 4K sectors
- read_flash: read up to 255 bytes
- write_flash: write up to 255 bytes
- write_flash_fill: write and pad to 256 bytes with FF
- test: continuous DTR toggle test

## Complete usage examples

Flash firmware to TB-03F-KIT on CDC ACM port:

telink_tools -p /dev/ttyACM0 burn tb03f_fw.bin

Flash firmware to TB-04-KIT on USB serial adapter:

telink_tools -p /dev/ttyUSB0 burn tb04_fw.bin

Erase 176 KB application area (44 sectors from 0x4000):

telink_tools -p /dev/ttyACM0 erase_flash 0x4000 44

Read back triad area (26 bytes):

telink_tools -p /dev/ttyACM0 read_flash 0x78000 26

Write triad values:

telink_tools -p /dev/ttyACM0 burn_triad 123456 112233445566 AABBCCDDEEFF00112233445566778899AABBCCDD

Write raw bytes at address:

telink_tools -p /dev/ttyACM0 write_flash 0x78000 01020304AABBCCDD

Write bytes and fill remaining page with FF:

telink_tools -p /dev/ttyACM0 write_flash_fill 0x78000 01020304
