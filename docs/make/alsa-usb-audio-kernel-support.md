# ALSA USB Audio Kernel Support
  - Package area: kernel modules exposed in menuconfig
  - Scope: ALSA core, USB audio, USB MIDI stack

This page documents kernel-side audio support in Freetz-EVO for targets that ship ALSA USB support in the underlying AVM kernel tree.

## What this enables

When enabled for compatible targets, the kernel can expose USB audio interfaces (playback/capture) and USB-MIDI devices through ALSA.

Typical modules involved:

- soundcore
- snd
- snd-timer
- snd-pcm
- snd-hwdep
- snd-rawmidi
- snd-usbmidi-lib
- snd-usb-audio

## Target compatibility

Compatibility depends on the target kernel configuration and available in-tree drivers.

Example: on GRX5-based targets where AVM ships ALSA USB support in kernel sources, Freetz can expose the corresponding module toggles in menuconfig.

## Menuconfig behavior

This entry refers to kernel support only.

It is not a standalone user-space package, and it does not by itself provide mixers, device listing tools, or playback utilities.

Pair it with user-space components such as:

- alsa-lib
- alsa-utils
- applications using ALSA (for example mpd, cmus, shairport-sync, snapcast)

## Runtime checks on the box

After boot, useful checks are:

- `lsmod | grep -E "snd|usb_audio|snd_usb"`
- `dmesg | grep -i "usb.*audio\|snd-usb"`
- `aplay -l`
- `arecord -l`

If devices are present in `dmesg` but not usable from applications, verify ALSA user-space packages and runtime configuration.

## Troubleshooting hints

- If USB audio appears only after unplug/replug, ensure USB host init order and module autoload are correct at boot.
- If ALSA modules are loaded but playback fails, verify PCM device selection (`hw:X,Y` vs `default`) and sample format/rate compatibility.
- If no ALSA USB modules are available in menuconfig, the active target/kernel variant likely does not expose them for that profile.
