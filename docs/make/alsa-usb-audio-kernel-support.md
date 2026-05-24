# ALSA / USB audio kernel support
  - Package area: kernel modules exposed in menuconfig
  - Scope: soundcore, ALSA core, USB audio, USB MIDI stack

This entry documents the kernel-side audio support exposed by Freetz-EVO on compatible targets.

Enabled modules may include:

- soundcore
- snd
- snd-timer
- snd-pcm
- snd-hwdep
- snd-rawmidi
- snd-usbmidi-lib
- snd-usb-audio

## Notes

This is kernel support, not a standalone user-space package.

Typical userspace companions are:

- alsa-lib
- alsa-utils
- players such as MPD, cmus, shairport-sync, snapcast
