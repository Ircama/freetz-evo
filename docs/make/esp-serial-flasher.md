# esp-serial-flasher
  - Homepage: [https://github.com/espressif/esp-serial-flasher](https://github.com/espressif/esp-serial-flasher)
  - Changelog: [https://github.com/espressif/esp-serial-flasher/releases](https://github.com/espressif/esp-serial-flasher/releases)
  - Repository: [https://github.com/espressif/esp-serial-flasher](https://github.com/espressif/esp-serial-flasher)
  - Package: [master/make/pkgs/esp-serial-flasher/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/esp-serial-flasher/)
  - Steward: -

  - Depends on: none
  - Provides: /usr/bin/esp-flasher
  - Externalization: supported

The package ships one command line tool:

- esp-flasher: CLI using explicit address/file pairs (`esp_flasher.c`,
  derived from the upstream `examples/linux_example` of the library)

Both tools also accept an optional chip check:

- `-c, --chip <name>` validates the detected chip (`esp32c3`, `esp32s3`, `esp32c6`, ...)

## Automatic reset (no BOOT/RESET buttons)

The tool drives the same reset sequences as esptool, so an ESP32-C3/C6/H2/S3
wired through its built-in USB Serial/JTAG does not need the buttons:

- `-m auto` (default) the flasher drives DTR/RTS itself; the library is told
  not to touch them (`LINUX_GPIO_NONE`)
- `-m dtr-rts` let esp-serial-flasher drive them (classic auto-reset circuit)
- `-m gpio` reset/boot through libgpiod lines
- `-m none` no reset handling: the target must already be in download mode
- `--before auto|usb-jtag|classic|no-reset` how to enter download mode
  (`auto` picks `usb-jtag` on `/dev/ttyACM*`, `classic` elsewhere)
- `--after hard-reset|no-reset` restart into the new firmware when done (default)

With the defaults, flashing from the router is:

```bash
esp-flasher -p /dev/ttyACM0 -c esp32c3 0x0 build/bootloader/bootloader.bin \
  0x8000 build/partition_table/partition-table.bin 0x10000 build/ble50_scan.bin
```

## Complete usage examples

Flash ESP32-C3 bootloader + partition table + app image:

esp-flasher -p /dev/ttyACM0 -c esp32c3 0x0 bootloader.bin 0x8000 partition-table.bin 0x10000 firmware.bin

Flash with explicit baudrate and no stub (ROM mode):

esp-flasher -p /dev/ttyACM0 -b 460800 -n -c esp32c3 0x0 bootloader.bin 0x8000 partition-table.bin 0x10000 firmware.bin

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

`esp-flasher` always uses explicit `<addr> <file>` pairs.

## Externalization

`Externalization: supported` means the package can be externalized, but it is enabled only if
`EXTERNAL_FREETZ_PACKAGE_ESP_SERIAL_FLASHER=y` is selected in menuconfig.

If that symbol is not enabled, binaries remain in `/usr/bin` as usual.

## Note on `cdc_acm` and AVM devices

On FRITZ!Box models such as the 7590 AX, `cdc_acm` may already be provided by AVM in the stock firmware,
so you do not necessarily need to enable a separate kernel option in Freetz.

If `/dev/ttyACM0` appears only after a replug, the practical fix is to make sure `cdc_acm` is loaded at boot
through the Freetz module list (`/tmp/flash/mod/modules`), not to add a package dependency.
That means the package can stay usable with a simple module autoload, while the replug symptom usually points
to USB enumeration timing rather than to `esp-serial-flasher` itself.
