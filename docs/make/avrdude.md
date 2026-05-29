# avrdude 8.1
  - Homepage: [https://github.com/avrdudes/avrdude](https://github.com/avrdudes/avrdude)
  - Manpage: [https://avrdudes.github.io/avrdude/](https://avrdudes.github.io/avrdude/)
  - Changelog: [https://github.com/avrdudes/avrdude/releases](https://github.com/avrdudes/avrdude/releases)
  - Repository: [https://github.com/avrdudes/avrdude](https://github.com/avrdudes/avrdude)
  - Package: [master/make/pkgs/avrdude/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/avrdude/)
  - Steward: -
  - Documentation: [https://avrdudes.github.io/avrdude/](https://avrdudes.github.io/avrdude/)

  - Depends on: libelf, libusb, libusb1, libftdi, readline, ncurses
  - Provides: /usr/bin/avrdude, /usr/bin/elf2tag, /etc/avrdude.conf

avrdude is the reference CLI uploader/programmer for AVR devices, including the standard configuration database and the helper utility elf2tag.

## Typical workflow

1. Identify available programmers and parts.
2. Read device signature.
3. Program firmware.
4. Verify flash contents.

## Complete usage examples

List programmers:

avrdude -c ?

List MCU parts:

avrdude -p ?

Read target signature from an Arduino-style serial bootloader:

avrdude -c arduino -P /dev/ttyUSB0 -b 115200 -p atmega328p -v

Flash firmware to ATmega328P:

avrdude -c arduino -P /dev/ttyUSB0 -b 115200 -p atmega328p -D -U flash:w:firmware.hex:i

Read flash back to file:

avrdude -c arduino -P /dev/ttyUSB0 -b 115200 -p atmega328p -U flash:r:backup.hex:i

Set fuses (example values, verify before use):

avrdude -c usbasp -P usb -p atmega328p -U lfuse:w:0xFF:m -U hfuse:w:0xDE:m -U efuse:w:0xFD:m

Use custom config file path:

avrdude -C /etc/avrdude.conf -c usbasp -P usb -p atmega32u4 -U flash:w:firmware.hex:i
