# ALSA USB Audio Kernel Support

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

## Soft-float / FPU emulation

Many FritzBox SoCs (e.g. GRX550 MIPS32) lack a hardware FPU. Software sample rate conversion and equalization rely on floating-point arithmetic emulated in software, which can overwhelm the CPU.

Always use ALSA device `hw:0,0` in applications (MPD, etc.) rather than
`default`.

## USB audio card requirements

USB audio cards used with soft-float MIPS targets should support the most
common sample rates **44100 Hz** and **48000 Hz** natively in hardware. If a card does not support these rates, ALSA must resample in software, which
triggers FPU emulation and overloads the CPU. Cards that rely on rate
matching (e.g. adaptive USB audio) may also introduce stuttering.

See also [alsa-lib.md](alsa-lib.md).

  - Package area: kernel modules exposed in menuconfig
  - Scope: ALSA core, USB audio, USB MIDI stack

## Menuconfig behavior

This entry refers to kernel support only.

It is not a standalone user-space package, and it does not by itself provide mixers, device listing tools, or playback utilities.

Pair it with user-space components such as:

- alsa-lib
- alsa-utils
- applications using ALSA (for example mpd, cmus, shairport-sync, snapcast)

## Runtime checks on the box

- `lsmod | grep -E "snd|usb_audio|snd_usb"`
- `cat cat /proc/asound/card*/stream0`
- `cat cat /proc/asound/card*/usbmixer`
- `aplay -l`
- `arecord -l`
