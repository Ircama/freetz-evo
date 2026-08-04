# ja11-config
  - Homepage: [https://github.com/Freetz-NG/freetz-ng](https://github.com/Freetz-NG/freetz-ng)
  - Repository (source): [master/make/pkgs/ja11-config/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/ja11-config/)
  - Library: [master/make/libs/hidapi/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/libs/hidapi/)
  - Hardware: FiiO JA11 (JadeAudio JA11) / KT Micro KT02H20
  - Protocol reference: [Audiocular-Aura](https://github.com/mandy321/Audiocular-Aura)

## What is ja11-config

`ja11-config` is a set of tools for the FiiO JA11 USB DAC/Amp and other devices
based on the KT Micro KT02H20 DSP chip (JKALLY JM12, etc.):

- **`ja11-config-tui`** — an interactive Text-based User Interface (TUI) that
  configures the device over HID: 5-band Parametric EQ (PEQ), DAC digital
  filters and global preamp gain, with persistent Save-to-Flash.
- **`ja11-boot`** — puts the device into firmware-update (boot) mode; the
  device then re-enumerates as a USB CDC virtual serial port.
- **`ja11-flash`** — flashes firmware over the update-mode serial port created
  by `ja11-boot`.

The TUI communicates directly with the hardware via HID — it sends
binary commands to the chip's Digital Signal Processor (DSP) to set the 5-band
Parametric Equalizer (PEQ), DAC digital filters, and global preamp gain.

Because commands target the hardware directly, settings can be made persistent:
with the **Save to Flash** feature, your custom sound signature remains even when
you unplug the DAC and connect it to a phone, tablet, or game console.

## Features

- **Full TUI control** — Interactive ncurses interface with real-time feedback.
- **5-band Parametric EQ** — Independent control of Frequency, Gain, Q-Factor and
  Filter Type (Peaking / Low-Shelf / High-Shelf) for each band.
- **Global Preamp (Gain)** — Overall volume trim to prevent digital clipping when
  boosting EQ bands.
- **DAC Digital Filter selection** — Five filters of the KT02H20 DAC: FAST-LL,
  FAST-PC, Slow-LL, Slow-PC, NON-OS.
- **Hardware-level changes** — Settings are written directly to the DSP over HID;
  no audio server (ALSA/PulseAudio) configuration needed.
- **Persistent flash memory** — Save your configuration to the device's internal
  flash so it survives power cycles and host changes.
- **Preset management** — Save, load, and delete EQ profiles stored locally on
  the host (`/tmp/ja11-presets.conf`).
- **i18n** — English (default) and Italian (`--italian` / `-it`).
- **Lightweight** — Written in C with only two external dependencies:
  `hidapi` (libusb backend, like `hidws`) and `ncurses`.

## How it works

### Communication protocol

The KT02H20 chip uses a HID **output** report with Report ID `0x02`. All commands (including read requests) are sent via the interrupt OUT endpoint (`hid_write`), and the responses come back as **input** reports on the interrupt IN endpoint. Commands are wrapped in fixed-length packets with the following structure:

**Set (write) packet:**
```
0xaa 0x0a 0x00 0x00  <command> <length> [payload...] 0xee
```

**Read (response) packet:**
```
0xbb 0x0b 0x00 0x00  <command> <sub-command> [payload...] 0xee
```

> **Note:** hidapi's libusb backend (and the `hidws` WebSocket bridge) returns
> the report **ID byte (0x02)** as the first byte of numbered **input**
> reports, i.e. the buffer is `0x02 0xbb 0x0b …`. The TUI strips it
> (`find_packet_start()`) before parsing.

Key commands:

| Cmd | Name              | Purpose                                |
|-----|-------------------|----------------------------------------|
| 17  | DAC_FILTER        | Set DAC digital filter (1-5)           |
| 21  | FILTER_PARAMS     | Write a single PEQ band (freq, gain, Q, type) |
| 23  | GLOBAL_GAIN       | Read/write global preamp gain          |
| 24  | APPLY             | Commit current settings to RAM         |
| 25  | SAVE_FLASH        | Persist settings to flash memory       |

Data encoding:
- **Gain**: signed Q12 fixed-point (value × 10), 2-byte big-endian; negative
  values are 16-bit two's complement (65536 + value).
- **Frequency**: Hz as unsigned 2-byte big-endian.
- **Q factor**: Q2 fixed-point (value × 100), 2-byte big-endian.
- **Global gain**: signed value × 2560, 2-byte little-endian; negative values
  are 16-bit two's complement.

### Pipeline

```
User edits params in TUI
       ↓
   (key 'a')  →  sync_all_bands() + apply_changes()  →  DSP RAM
       ↓
   (key 's' then 'S')  →  sync_all_bands() + save_to_flash()  →  DSP flash
       ↓
   (key 'r'/'R')  →  read_device_config()  →  reload from DSP → UI
```

The Apply step (`a`) is instantaneous — you hear the change immediately. The
Save step (`s` → `S`) writes all current bands plus the global gain and DAC
filter to non-volatile flash, making the setting permanent.

## Current packaged versions

- `ja11-config-tui`: `1.0`
- `ja11-boot`: `1.0`
- `ja11-flash`: `1.0`
- `hidapi`: `0.15.0` (shared library dependency)

## Firmware update (ja11-boot and ja11-flash)

Firmware updates use a two-step workflow:

1. **`ja11-boot`** puts the device into update (boot) mode. It sends the HID
   output report used by the official FiiO web app (`updateBeforeReset`), after
   which the device resets and **re-enumerates as a USB CDC virtual serial
   port** (VID 0x8888, "KT Virtual Com Port", 9600 baud) — usually
   `/dev/ttyACM0` or `/dev/ttyACM1`.
2. **`ja11-flash`** flashes the firmware over that virtual serial port using
   the KT-family bootloader protocol (SYNC ".KTM", CHP, CFG, PWO, KSTA, write
   frames with CRC32, STP, ZRST).

Example:

```
ja11-boot                          # enter update mode
# ... device now appears as /dev/ttyACM1 ...
ja11-flash /dev/ttyACM1 /path/to/JadeAudio_JA11_V2.2.bin
```

> **WARNING:** flashing the wrong firmware can brick the device. Only use a firmware intended for the JA11 / KT02H20.

### Forcing the vendor/product ID of ja11-boot

`ja11-boot` looks for the FiiO JadeAudio JA11 by default (VID `0x2972`,
PID `0x0102`). On some devices (e.g. a **native KTMicro** dongle) the HID
interface reports a different VID/PID, so `ja11-boot` fails with a
"device ... not found" error. You can force the values, given **in decimal**,
with `-v`/`-p`:

For a native KTMicro device:

```
Vendor ID   : 0x0BDA = 3034
Product ID  : 0x0023 = 35

ja11-boot -v 3034 -p 35
```

`ja11-boot -l` lists all HID devices so you can read the VID/PID of your own
device, and `ja11-boot -c` performs a safe connection test without sending the
boot trigger.

## Usage

With the FiiO JA11 connected via USB, run:

```
ja11-config-tui
```

Use `--italian` (or `-it`) for Italian UI:

```
ja11-config-tui -it
```

### Device selection

On startup the tool enumerates **all** HID devices (via the hidapi **libusb**
backend, the same approach used by `hidws`) and shows a picker:

```
┌────────────────────────────── Select HID device ─────────────────────────────┐
│   VID:PID     Product                                                        │
│ * 2972:0102  JadeAudio JA11                ← known KT02H20 device (auto ✓)   │
|                                                                              |
│  Up/Down: move    Enter: connect    q: quit                                  │
└──────────────────────────────────────────────────────────────────────────────┘
```

- Devices whose VID/PID or product string matches a known KT02H20 device
  (`2972:0102`, `31b2:0111`, or names containing `JA11`/`ja11`/`KT02H20`/`JM12`)
  are marked with `*` and pre-selected.
- **Enter** connects to the highlighted device; **q** quits.
- In the main screen, press **`c`** to reopen the picker (reconnect or switch
  to another device).

If no HID device is found at all, the tool shows the error/hint and stays on
the (disconnected) main screen.

If a device is not accessible, run as root (normal on the router). On desktop
hosts see the [udev rule](#udev-rule) below for non-root access.

### Interface layout

```
  FiiO JA11 (KT02H20) - Full PEQ Configurator
  CONNECTED: JadeAudio JA11  Global Preamp:6.0 dB  DAC Digital Filter:FAST-LL  All synced with device
  Band    Freq (Hz)     Gain (dB)     Q             Type      Status
> 25            +3.5          0.70          PK        ON
  150           +0.0          0.70          PK        ON
  1500          +1.4          0.70          PK        ON
  6500          +9.0          0.70          PK        ON
  15660         +12.0         0.25          PK        ON

  +12 │                          │                                    │                       @@@@@@@@@@@@@@@@@@@@@@@@│
                                 │                                    │                     @@│            │          @
                                 │                                    │                   @@│              │
                                 │                                    │               @@@@│                │
   +6 │                          │                                    │           @@@@│                    │
       @@@@@@@@@@@│              │                                    │   @@@@@@@@│                        │
                  @@@@@@@@@@│    │                             @@@@@@@@@@@│                                │
   +0 │─────────────────────@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@│──────·────────────────────────────────────·───────────
                                 │                                    │                                    │
                                 │                                    │                                    │
                                 │                                    │                                    │
   -6 │                          │                                    │                                    │
                                 │                                    │                                    │
                                 │                                    │                                    │
  -12 │                          │                                    │                                    │
       20                       100                                 1k                                   10k        20k
  Press ? or h for full help

```

The **frequency-response curve** is the real RBJ biquad magnitude of the active
bands (summed in dB, evaluated at 48 kHz) — the same function used by the FiiO
Control reference and the web apps. It is plotted on a log frequency axis
(20 Hz – 20 kHz, −12…+12 dB) and is recomputed on every redraw, so it updates
live while you edit.

The graph mirrors the Python TUI (`ktmicro_tui.py`) UX:

- **Left axis**: dB labels `+12` … `-12` with a `│` separator.
- **0 dB reference line**: `─`, with `·` at decade crossings.
- **Decade grid**: dimmed vertical `│` lines at 100 Hz, 1 kHz and 10 kHz.
- **Curve**: a connected line (`o` at each sample, `│` vertical connectors).
- **Bottom row**: frequency labels `20`, `100`, `1k`, `10k`, `20k`.

It spans the full terminal width and its height adapts to the terminal size
(up to 16 rows); the leftover vertical space is used by the help panel.

The help panel at the bottom is drawn only if the terminal is tall enough;
on small terminals it is replaced by a `Press ? or h for full help` hint, and
the full, scrollable help is available anytime with **`?`** / **`h`** / **`H`**.

### Controls reference

| Key(s)        | Action                     | Description                                              |
|---------------|----------------------------|----------------------------------------------------------|
| ↑/↓           | Select band                | Move cursor between the 5 PEQ bands.                     |
| ←/→           | Select parameter           | Move cursor between Freq, Gain, Q, Type columns.         |
| `Tab`/`Shift+Tab` | Cycle cells (fwd/back) | Move forward/backward across all cells (band × Freq/Gain/Q/Type/Status). |
| `+`/`-`       | Coarse adjust              | Change parameter by a large step (10 Hz, 1 dB, 0.1 Q); on Type it cycles the filter, on Status it toggles the band. |
| `<`/`>`       | Fine adjust                | Change parameter by a small step (1 Hz, 0.5 dB, 0.01 Q). |
| `Space`       | Toggle band                | Enable/disable the selected band (bypass filter).        |
| `t`/`T`       | Cycle filter type          | PK → LSQ → HSQ → PK …                                    |
| `a`/`A`       | Apply to RAM               | Write all bands + gain + filter to device RAM (hear changes instantly). |
| `s` then `S`  | Save to flash              | Apply + persist to flash. Confirms with a second keypress. |
| `r`/`R`       | Read from device           | Discard local changes and re-read full config from DSP.  |
| `g`/`G`       | Set global gain            | Opens an inline prompt to type a preamp value (-12…+12 dB); applies it to the device immediately. |
| `f`/`F`       | Cycle DAC filter           | FAST-LL → FAST-PC → Slow-LL → Slow-PC → NON-OS → …      |
| `p`           | Save preset                | Opens a prompt to name the current config and save it locally. |
| `P` (Shift+p) | Load preset                | Opens a prompt to select a previously saved preset by number. |
| `K` (Shift+k) | Delete preset              | Removes the active preset after confirmation.            |
| `d`           | Reset to flat              | All bands: 0 dB gain, 0.7 Q, PK type, enabled.          |
| `D` (Shift+d) | Reset to defaults          | All bands set to a useful frequency distribution (32/64/125/250/500 Hz). |
| `?`/`h`/`H`   | Full help                  | Opens a full-screen, scrollable help viewer (useful on small terminals). |
| `q`/`Q`       | Quit                       | Exits the program; prompts if there are unsaved changes. |

**Important**: `q` will refuse to exit while the `"** MODIFICATIONS NOT APPLIED **"`
warning is shown. Apply or revert first.

## Understanding the parameters

### Parametric EQ (PEQ)

A Parametric Equalizer is the most flexible type of EQ. Unlike a Graphic EQ
(which offers fixed frequency sliders), a PEQ gives you independent control of
three parameters per band:

#### Frequency (Hz)

The centre frequency of the filter — the point in the audio spectrum that will
be boosted or cut.

| Range             | Perceived region | Common sources                          |
|-------------------|------------------|-----------------------------------------|
| 20 – 160 Hz       | Sub-bass / Bass  | Kick drum, bass guitar, low synth pads  |
| 160 – 500 Hz      | Low mids         | Low vocals, cello, warmth / mud         |
| 500 – 2000 Hz     | Midrange         | Vocals, snare, guitar body              |
| 2000 – 6000 Hz    | Upper mids       | Presence, attack, nasality              |
| 6000 – 20000 Hz   | Treble / Air     | Cymbals, hi-hat, sibilance, sparkle     |

#### Gain (dB)

The amount of boost or cut applied at the centre frequency.

- **Positive values** (e.g. +3.0 dB) = make that range louder.
- **Negative values** (e.g. -4.5 dB) = make that range quieter.
- A +3 dB change is generally perceived as a doubling of loudness for that band.

**Warning**: Excessive boost without a corresponding negative preamp will cause
digital clipping (harsh distortion). See [Global Preamp](#global-preamp-below).

#### Q Factor (Quality Factor)

The **width** of the filter — arguably the most powerful and least understood PEQ
parameter.

- **High Q** (≈ 3.0–10.0): narrow, "surgical" curve. Targets a very specific
  frequency without affecting neighbours. Use for removing a single resonant
  peak or ringing artefact.
- **Low Q** (≈ 0.5–1.4): wide, "musical" curve. Affects a broad range around
  the centre frequency. Use for general tonal shaping — warming the bass,
  brightening the treble.

When Q is very low (< 0.7) the filter starts to affect a very wide range,
including frequencies far from the centre. This can be desirable for shelving
behaviour (e.g. a low-Q peaking filter at 80 Hz acts almost like a bass shelf).

### Filter types

| Type | Abbreviation | Description | Typical use case |
|------|-------------|-------------|------------------|
| Peaking | PK | Standard bell-shaped curve that boosts or cuts a range centred on the chosen frequency. | General EQ, most corrections. |
| Low-Shelf | LSQ | Affects **all frequencies below** the centre frequency. Think of a classic "Bass" tone knob. | Add or remove overall low-end weight. |
| High-Shelf | HSQ | Affects **all frequencies above** the centre frequency. Think of a classic "Treble" tone knob. | Add air/sparkle or tame harsh highs. |

**Shelving filters** in the KT02H20 are implemented with a fixed slope and are
most effective when the centre frequency is placed near the edge of the region
you want to affect (e.g., an LSQ at 200 Hz for bass, an HSQ at 3000 Hz for
treble).

### Global Preamp (gain)

The Global Preamp is a single gain value applied to the **entire signal before**
the PEQ stage. Its main purpose is **headroom management**:

- Boosting EQ bands increases the overall signal level. If the total exceeds
  0 dBFS, digital clipping (harsh, crackling distortion) occurs.
- The preamp should be set to a negative value equal to (or greater than) the
  largest positive boost across all bands.

**Rule of thumb**: if your highest band boost is +5.5 dB, set Global Preamp to
**-5.0 dB** or lower. A safe starting point is to match it to the maximum boost.

The preamp range is **-12.0 dB to +12.0 dB** (positive values are rarely useful
and will likely cause clipping; they are included for completeness).

### DAC Digital Filters

The KT02H20 DAC includes a digital reconstruction filter that processes the
audio stream after D/A conversion. This filter removes ultrasonic imaging
artefacts and can subtly colour the sound. Five filter profiles are available:

| # | Name              | Short name | Characteristics                                         |
|---|-------------------|------------|---------------------------------------------------------|
| 1 | Fast roll-off, Linear Phase (low latency) | **FAST-LL** | Steep cut above 22 kHz, no phase distortion, the default. |
| 2 | Fast roll-off, Phase Compensation         | **FAST-PC** | Steep cut, slight phase shift, warmer character.        |
| 3 | Slow roll-off, Linear Phase (low latency) | **Slow-LL** | Gentle roll-off, clean phase response.                  |
| 4 | Slow roll-off, Phase Compensation         | **Slow-PC** | Gentle roll-off, coloured phase, "analogue" feel.       |
| 5 | Non-Oversampling                          | **NON-OS**  | No digital filter — passes ultrasonic noise but sounds very "raw". |

The DAC filter is independent of the PEQ; it affects the final analogue output
stage. Cycle through them with `f`/`F` while listening — the difference is
subtle but noticeable on good headphones.

## Presets

Presets are stored locally on the host machine in `/tmp/ja11-presets.conf`
(format: plain text, one preset per block). They are **not** stored on the
device itself. Use presets to:

- quickly switch between different listening profiles (night mode, loudness,
  neutral),
- experiment without losing a known-good configuration,
- share configurations with other users (the file is human-readable).

To use a preset after loading it, you must still press **`a` (Apply)** to send
it to the device, or **`s` (Save)** to make it persistent.

## Device support

### Known compatible devices

| Vendor   | VID      | PID      | Product                   | Chip    |
|----------|----------|----------|---------------------------|---------|
| FiiO     | `0x2972` | `0x0102` | JadeAudio JA11            | KT02H20 |
| JKALLY   | `0x31b2` | `0x0111` | JM12                      | KT02H20 |

The picker lists every HID device found on the system. Devices whose VID/PID
or product string matches a known KT02H20 device (`2972:0102`, `31b2:0111`, or
names containing `JA11`/`ja11`/`KT02H20`/`JM12`) are marked `*` and pre-selected,
so the correct device is normally highlighted automatically.

### udev rule

To allow non-root users to access the device, install this udev rule at
`/etc/udev/rules.d/99-fiio-ja11.rules`:

```
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="2972", MODE="0660", GROUP="plugdev"
```

Reload udev and re-plug the device:

```
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Add your user to the `plugdev` group if not already:

```
sudo usermod -aG plugdev $USER
```

**Without the rule**, run the tool as root (`sudo ja11-config-tui`).

> The tool uses the hidapi **libusb** backend (not hidraw), so on the router
> (where it runs as root) no udev rule is needed. The rule above only matters
> for non-root desktop use.

## Debugging

### Device not found

1. The picker only lists devices found by `hid_enumerate()`. If the list is
   empty, run `lsusb` — the JA11 should appear as `2972:0102` (FiiO) or
   `31b2:0111` (JKALLY).
2. The libusb backend does **not** need `/dev/hidraw*` or the kernel HID/INPUT
   subsystem (important on GRX5 routers, where `hid.ko` cannot load).
3. Check permissions: running as root (normal on the router) is sufficient.
4. Run with `sudo` as a quick test on desktop hosts.

### Communication errors

- Ensure the device is not claimed by another program (e.g. close `hidws`
  or the browser's WebHID session first).
- The libusb backend claims the USB interface directly via usbfs; on hosts
  where the kernel `usbhid` driver grabs the device, hidapi detaches it
  automatically on open.

### Presets not loading

Presets are stored in `/tmp/ja11-presets.conf`, which is **volatile** and lost
on reboot. This is intentional — presets are meant as quick-load snapshots
during a session, not as long-term storage. Save your configuration to flash
(`s` then `S`) for permanent storage on the device.

## Known issues

- **Single-device**: The tool connects to the device selected in the picker.
  Connecting multiple KT02H20 devices simultaneously is not supported.
- **HIDAPI library name**: The package links the **libusb** backend
  (`libhidapi-libusb.so.0`, like `hidws`), not hidraw.
- **Volatile presets**: Preset files live in `/tmp` and are cleared on reboot.

## See also

- [hidapi](https://github.com/libusb/hidapi) — Library used for raw HID I/O.
- [FiiO](https://www.fiio.com/) — Official product page for JA11.
