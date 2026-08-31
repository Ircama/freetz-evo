# Freetz-EVO — The Flasher Tools Subsystem

Thanks to USB peripherals, FRITZ!Box devices can greatly expand their functional perimeter, opening scenarios such as sensing, home automation, robotics, audio features, and the integration of high-end audio amplifiers.

To integrate USB peripherals and simplify their management, Freetz-EVO includes **flasher tools** that make it possible to update USB peripherals connected directly to the device — microcontrollers such as Arduino, AVR ATtiny, ESP32, USB DACs, and more — as well as to configure devices that implement the HID protocol. It also ships dedicated configuration programs for specific devices, such as the FiiO JA11 USB DAC. For example, thanks to [ADV_BLE2UART](https://github.com/pvvx/ADV_BLE2UART) it is possible to efficiently connect BLE devices via USB serial even though the FRITZ!Box kernel does not support BLE, offloading the BLE processing to the peripheral itself.

All the tools described in this document are available in the **Packages → Flasher tools** section of `make menuconfig`. The related kernel drivers (`cdc-acm`, HID support) and the HID libraries are exposed in the kernel and libraries menus.

## The governing idea: the FRITZ!Box as a USB host and gateway

A FRITZ!Box with Freetz-EVO is not limited to routing and telephony: with its USB host port it becomes a small Linux appliance that can talk to arbitrary USB hardware. Many useful peripherals — microcontroller boards, BLE-to-UART bridges, USB DACs with configurable DSPs — expose either a **USB serial (CDC ACM)** interface or a **HID** interface. Freetz-EVO provides both the kernel-side drivers and the userspace tooling to work with them directly on the box, without needing a separate PC:

- **Kernel drivers** — the `cdc-acm` USB serial driver for native USB CDC ACM devices (USB-to-serial adapters, BLE bridges, Arduino-class boards) and the HID kernel support (`hid`, `hid-generic`) for HID-class devices are exposed in menuconfig on compatible targets.
- **HID userspace stack** — `hidapi` (C library) and `python3-hidapi` (Python bindings) allow scripts and applications to enumerate, open and communicate with HID devices.
- **Flashers and configurators** — a set of command-line tools to update firmware on microcontrollers and to configure specific devices, described below.

A typical chain looks like this:

> **USB peripheral (MCU / BLE bridge / DAC) → `cdc-acm` or HID kernel driver → hidapi or serial port → flasher/configurator tool**

## The flasher and configurator tools

### `avrdude` 8.1 — the AVR/Arduino programmer

[avrdude](https://github.com/avrdudes/avrdude) is the standard AVR Downloader/Uploader for Microchip (formerly Atmel) AVR microcontrollers — the family powering classic Arduino boards, ATtiny and ATmega devices. The Freetz-EVO package installs the main `avrdude` CLI programmer together with the `elf2tag` helper tool to generate UPDI tags. It links against `libusb1`, `libftdi`, `libelf`, `readline` and `ncurses`, so it can drive programmers connected over USB (both libusb-based and FTDI-based) directly from the FRITZ!Box. With it, the box itself can update the firmware of an attached Arduino, ATtiny or any other AVR MCU — useful for home-automation and sensing nodes that are deployed near the router.

### `esp-serial-flasher` — ESP32/ESP8266 flashing over UART

[esp-serial-flasher](https://github.com/espressif/esp-serial-flasher) is Espressif's portable flashing library, built here as a Linux host-style CLI tool (`linux_flasher`) that programs ESP32/ESP8266-class chips over a serial connection using address/file pairs. Combined with the `cdc-acm` driver and a USB-to-UART adapter, it lets the FRITZ!Box update ESP-based devices in the field — for example sensor nodes or BLE bridges deployed around the house — without pulling them off the wall.

### `micronucleus` 2.6 — ATtiny USB bootloader tool

[Micronucleus](https://github.com/micronucleus/micronucleus) is the command-line utility for the Micronucleus USB bootloader, commonly flashed on ATtiny85-class boards (Digispark and similar). The tool talks to the bootloader over USB (libusb) directly, so a Digispark-style board plugged into the FRITZ!Box can be reprogrammed from the box itself — a convenient way to update tiny sensing/automation nodes.

### `telink_tools` 1.0 — Telink BLE bootloader utility

`telink_tools` is a Telink BLE chip bootloader utility implemented in C. It supports firmware flashing and flash utility operations for Telink-based BLE devices. Together with USB serial bridges such as [ADV_BLE2UART](https://github.com/pvvx/ADV_BLE2UART), it enables efficient BLE device connectivity via USB serial even though the FRITZ!Box kernel does not support BLE: the BLE processing is offloaded to the peripheral, and the box only sees a plain serial stream.

### `hidws` 1.3.x — the HID/WebSocket gateway (with CGI)

`hidws` is a HID/WebSocket gateway: it exposes HID devices attached to the FRITZ!Box over a WebSocket protocol, so that browser-based web applications (running on a PC or phone) can interact with the HID hardware connected to the box. It links against `hidapi` and `libwebsockets` (with SSL). The optional **hidws CGI** companion package adds a Freetz configuration web page for the service. This is the enabling piece for browser-based HID tools — such as the [webhid-explorer](https://github.com/Ircama/webhid-explorer) and the FiiO control web app — to operate on devices plugged into the FRITZ!Box instead of the client computer.

### `ja11-config` 1.0 — the FiiO JA11 DAC configurator

`ja11-config` is a dedicated configurator for the FiiO JA11 and other KT02H20 DSP-based USB DACs. It provides a TUI (ncurses) equalizer/PEQ/filter/gain interface plus the `ja11-boot` and `ja11-flash` helpers for firmware update on the DAC. It is the practical realization of the design decision described in the [Audio Subsystem](AUDIO.md) documentation: since many FRITZ!Box SoCs lack a hardware FPU, equalization and digital filtering are best performed inside the DAC's own DSP — and `ja11-config` is the tool that programs that DSP over HID. See the [Audio Subsystem overview](AUDIO.md) for the full context.

### HID support: kernel modules, `hidapi` and `python3-hidapi`

The HID stack is available at three levels:

- **Kernel** — the `hid` and `hid-generic` modules are exposed in menuconfig on targets where AVM does not already ship them built-in or as modules;
- **C library** — `hidapi` provides a cross-platform HID API used by `hidws` and `ja11-config`;
- **Python** — `python3-hidapi` (hidapi 0.15.0) exposes the same functionality to Python scripts, enabling quick custom integrations for sensing, automation and device control scenarios.

## Summary table

| Tool | Purpose | Typical hardware |
|---|---|---|
| `avrdude` | AVR MCU programmer (CLI) | Arduino, ATtiny, ATmega |
| `esp-serial-flasher` | ESP chip flashing over UART | ESP32, ESP8266 |
| `micronucleus` | Micronucleus USB bootloader client | Digispark, ATtiny85 boards |
| `telink_tools` | Telink BLE bootloader utility | Telink BLE devices |
| `hidws` (+ CGI) | HID over WebSocket gateway | Any HID device, browser apps |
| `ja11-config` | JA11/KT02H20 DAC DSP configurator | FiiO JA11 USB DAC |
| `hidapi` / `python3-hidapi` | HID userspace libraries | Custom scripts and apps |
| `cdc-acm` (kernel) | USB CDC ACM serial driver | USB-serial adapters, BLE bridges |

## See also

- [Audio Subsystem](AUDIO.md) — USB DAC support, ALSA stack, and the FPU-related design decisions behind `ja11-config`
- [Disk Management](DISK-MGMT.md) — managing the USB storage that typically hosts the externalized firmware
- [NEW-PACKAGES.md](NEW-PACKAGES.md) — complete package listing
