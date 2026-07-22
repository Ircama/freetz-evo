# ja11-config-tui
  - Homepage: [https://github.com/Freetz-NG/freetz-ng](https://github.com/Freetz-NG/freetz-ng)
  - Repository (source): [master/make/pkgs/ja11-config-tui/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/ja11-config-tui/)
  - Library: [master/make/libs/hidapi/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/libs/hidapi/)
  - Hardware: FiiO JA11 (JadeAudio JA11) / KT Micro KT02H20
  - Protocol reference: [Audiocular-Aura](https://github.com/mandy321/Audiocular-Aura)

## What is ja11-config-tui

`ja11-config-tui` is a Text-based User Interface (TUI) program that configures the
FiiO JA11 USB DAC/Amp and other devices based on the KT Micro KT02H20 DSP chip
(JKALLY JM12, etc.).

The tool communicates directly with the hardware via raw HID (hidraw) — it sends
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
  `hidapi` (hidraw backend) and `ncurses`.

## How it works

### Communication protocol

The KT02H20 chip exposes a HID feature report with Report ID `0x02`. Commands
are wrapped in fixed-length packets with the following structure:

**Set (write) packet:**
```
0xaa 0x0a 0x00 0x00  <command> <length> [payload...] 0xee
```

**Read (response) packet:**
```
0xbb 0x0b 0x00 0x00  <command> <sub-command> [payload...] 0xee
```

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
- `hidapi`: `0.15.0` (shared library dependency)

## Source-based behavior map

Main files that define the current behaviour:

- `make/pkgs/ja11-config-tui/src/ja11-config-tui.c` — TUI logic, HID I/O,
  preset management, main loop.
- `make/pkgs/ja11-config-tui/src/ja11-config-tui.h` — Protocol constants,
  data structures, limits, i18n codes.
- `make/pkgs/ja11-config-tui/ja11-config-tui.mk` — Build recipe
  (PKG_LOCALSOURCE_PACKAGE, links hidapi + ncurses + m).
- `make/pkgs/ja11-config-tui/Config.in` — Menuconfig options
  (selects FREETZ_LIB_hidapi, FREETZ_LIB_libncurses).
- `make/pkgs/ja11-config-tui/external.files/in` — Externalisation manifest.
- `make/libs/hidapi/hidapi.mk` — CMake-based HIDAPI library build.
- `make/libs/hidapi/patches/` — Patches to make udev optional for freetz.
- `make/libs/hidapi/Config.in` — Library config symbol FREETZ_LIB_hidapi.

## Usage

With the FiiO JA11 connected via USB, run:

```
ja11-config-tui
```

Use `--italian` (or `-it`) for Italian UI:

```
ja11-config-tui -it
```

If the device is not accessible, ensure the udev rule is in place (see
[Udev rule](#udev-rule) below), or run as root.

### Interface layout

```
 ┌──────────────────────────────────────────────────────────────────────────────┐
 │  CONNESSO: FiiO JA11  Preamp: -3.5 dB  DAC: FAST-LL  All synced with device│ ← status bar
 ├──────┬──────────────┬──────────────┬──────────────┬──────────┬──────────────┤
 │ Band │ Freq (Hz)    │ Gain (dB)    │ Q            │ Type     │ Status       │
 ├──────┼──────────────┼──────────────┼──────────────┼──────────┼──────────────┤
 │ >1   │ 63           │ -2.0         │ 0.70         │ PK       │ ON           │ ← selected band
 │  2   │ 250          │ +3.5         │ 1.20         │ PK       │ ON           │
 │  3   │ 1000         │ 0.0          │ 0.70         │ LSQ      │ OFF          │
 │  4   │ 4000         │ +1.8         │ 1.50         │ HSQ      │ ON           │
 │  5   │ 14000        │ 0.0          │ 0.70         │ PK       │ ON           │
 ├──────┴──────────────┴──────────────┴──────────────┴──────────┴──────────────┤
 │                    ░░                                                        │ ← gain bar chart
 │                   ░░░░                                                       │
 │               ░░░░░░░░                                                       │
 │  ─══════════════════════════════════════════════════════════════════─        │
 │                   ░░░░              ░░                                       │
 │                   ░░░░              ░░                                       │
 │  ─══════════════════════════════════════════════════════════════════─        │
 ├──────────────────────────────────────────────────────────────────────────────┤
 │  English                        FiiO JA11 / KT02H20                         │ ← help panel
 │  === NAVIGATION ===                                                         │
 │    Arrows        Move between bands/params                                  │
 │    +/-           Change value (coarse step)                                 │
 │    </>           Change value (fine step)                                   │
 │    Space         Toggle band on/off                                         │
 │    t             Cycle filter type (PK/LSQ/HSQ)                             │
 │  === DEVICE ACTIONS ===                                                     │
 │    a             Apply changes to RAM                                       │
 │    s (then S)    Save to flash (permanent)                                  │
 │    r / R         Reload config from device                                  │
 │    g / G         Set global preamp gain                                     │
 │    f / F         Cycle DAC digital filter                                   │
 │  === PRESETS ===                                                            │
 │    p             Save current preset                                        │
 │    P             Load preset                                                │
 │    K             Delete current preset                                      │
 │  === OTHER ===                                                              │
 │    d             Reset to flat (0 dB, Q=0.7)                                │
 │    D             Reset to defaults (optimal freqs)                          │
 │    q / Q         Quit                                                       │
 ├──────────────────────────────────────────────────────────────────────────────┤
 │  OK: Saved to flash.                                                        │ ← status message
 └──────────────────────────────────────────────────────────────────────────────┘
```

### Controls reference

| Key(s)        | Action                     | Description                                              |
|---------------|----------------------------|----------------------------------------------------------|
| ↑/↓           | Select band                | Move cursor between the 5 PEQ bands.                     |
| ←/→           | Select parameter           | Move cursor between Freq, Gain, Q, Type columns.         |
| `+`/`-`       | Coarse adjust              | Change parameter by a large step (10 Hz, 1 dB, 0.1 Q).   |
| `<`/`>`       | Fine adjust                | Change parameter by a small step (1 Hz, 0.5 dB, 0.01 Q). |
| `Space`       | Toggle band                | Enable/disable the selected band (bypass filter).        |
| `t`/`T`       | Cycle filter type          | PK → LSQ → HSQ → PK …                                    |
| `a`/`A`       | Apply to RAM               | Write all bands + gain + filter to device RAM (hear changes instantly). |
| `s` then `S`  | Save to flash              | Apply + persist to flash. Confirms with a second keypress. |
| `r`/`R`       | Read from device           | Discard local changes and re-read full config from DSP.  |
| `g`/`G`       | Set global gain            | Opens an inline prompt to type a preamp value (-12…+12 dB). |
| `f`/`F`       | Cycle DAC filter           | FAST-LL → FAST-PC → Slow-LL → Slow-PC → NON-OS → …      |
| `p`           | Save preset                | Opens a prompt to name the current config and save it locally. |
| `P` (Shift+p) | Load preset                | Opens a prompt to select a previously saved preset by number. |
| `K` (Shift+k) | Delete preset              | Removes the active preset after confirmation.            |
| `d`           | Reset to flat              | All bands: 0 dB gain, 0.7 Q, PK type, enabled.          |
| `D` (Shift+d) | Reset to defaults          | All bands set to a useful frequency distribution (32/64/125/250/500 Hz). |
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

The tool also attempts to discover any device whose product string contains
"JA11", "ja11", "KT02H20" or "JM12" via HID enumeration.

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

## Integration into Freetz

The package appears in `make menuconfig` under:

```
Libraries  →  hidapi  (FREETZ_LIB_hidapi)
Packages   →  ja11-config-tui
```

`ja11-config-tui` automatically selects `hidapi` and `ncurses` as dependencies.

### Build targets

| Command                           | Effect                     |
|-----------------------------------|----------------------------|
| `make ja11-config-tui-recompile`  | Recompile from local source (fast iteration). |
| `make hidapi-recompile`           | Recompile HIDAPI library.  |
| `make`                            | Full firmware image build. |

### Deployment for testing

The `evo-eng-tools/` directory contains a deployment script
`deploy-ja11-config-tui.sh` (if created) that copies the binary and library to a
running device via `sshpass`. Typical iteration cycle:

```
# Edit source → recompile → deploy
make ja11-config-tui-recompile
./evo-eng-tools/deploy-ja11-config-tui.sh
ssh root@fritz.box '/usr/bin/ja11-config-tui'
```

### Externalisation

The binary is externalisable (`external.files/in` lists `/usr/bin/ja11-config-tui`).
The hidapi library is externalisable via `FREETZ_LIB_hidapi=external`.

**Library matching note**: Because the hidapi shared library is named
`libhidapi-hidraw.so*` (not `libhidapi.so*`), `fwmod` requires a specific case
for `hidapi` to find the files. This case has been added at line 1137 of `fwmod`:

```bash
hidapi)	files=$(shopt -s nullglob; echo ${TARGET_SPECIFIC_ROOT_DIR}/$dn/libhidapi*so*) ;;
```

Without this, externalisation of `FREETZ_LIB_hidapi` would fail with
"Library hidapi selected, but no files found".

## Building from source (standalone)

To compile outside the Freetz tree (e.g., on a desktop Linux for testing):

```bash
# Install dependencies
sudo apt install build-essential cmake libhidapi-dev libncurses-dev pkg-config

# Build
gcc -std=c11 -Wall -Wextra -Os \
    -D_DEFAULT_SOURCE -D_GNU_SOURCE \
    ja11-config-tui.c ja11-config-tui.h \
    -o ja11-config-tui \
    -lhidapi-hidraw -lncurses -lm
```

## Debugging

### Device not found

1. Check `lsusb` for `2972:0102` (FiiO) or `31b2:0111` (JKALLY).
2. Check kernel driver: `dmesg | grep -i hidraw`.
3. Check permissions: `ls -la /dev/hidraw*` — should be readable/writable by
   your user, either via udev rule or root.
4. Run with `sudo` as a quick test.

### Communication errors

- Ensure the device is not claimed by another program (check `lsof /dev/hidraw*`).
- On some kernels, the `usbhid` driver may need to be unbound first:
  ```
  echo -n "1-2:1.0" | sudo tee /sys/bus/usb/drivers/usbhid/unbind
  ```
  (Replace `1-2:1.0` with the actual USB path from `lsusb -t`.)

### Presets not loading

Presets are stored in `/tmp/ja11-presets.conf`, which is **volatile** and lost
on reboot. This is intentional — presets are meant as quick-load snapshots
during a session, not as long-term storage. Save your configuration to flash
(`s` then `S`) for permanent storage on the device.

## Known issues

- **Single-device**: The tool connects to the first compatible device found.
  Connecting multiple KT02H20 devices simultaneously is not supported.
- **HIDAPI library name**: The hidraw backend builds `libhidapi-hidraw.so*`.
  The `fwmod` externalisation matcher has a specific case for it (see
  [Externalisation](#externalisation) above).
- **Volatile presets**: Preset files live in `/tmp` and are cleared on reboot.

## Changelog (package)

| Version | Date       | Changes                                       |
|---------|------------|-----------------------------------------------|
| 1.0     | 2026-07-22 | Initial release: full PEQ, DAC filter, i18n.  |

## See also

- [Audiocular-Aura](https://github.com/mandy321/Audiocular-Aura) — Web-based
  configuration tool for the same chip family.
- [hidapi](https://github.com/libusb/hidapi) — Library used for raw HID I/O.
- [ncurses](https://invisible-island.net/ncurses/) — Terminal UI library.
- [FiiO](https://www.fiio.com/) — Official product page for JA11.
