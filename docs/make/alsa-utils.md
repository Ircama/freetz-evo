# alsa-utils 1.2.13
  - Homepage: [https://www.alsa-project.org/wiki/Main_Page](https://www.alsa-project.org/wiki/Main_Page)
  - Changelog: [https://www.alsa-project.org/wiki/Detailed_changes_v1.2.12_v1.2.13](https://www.alsa-project.org/wiki/Detailed_changes_v1.2.12_v1.2.13)
  - Package: [master/make/pkgs/alsa-utils/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/alsa-utils/)
  - Steward: -

  - Depends on: `alsa-lib`
  - Provides: `aplay`, `arecord`, `amixer`, `alsactl`, `speaker-test`, MIDI and sequencer tools
  - Externalization: supported

`alsa-utils` provides the core command-line tools for exercising and debugging the ALSA stack on the box. It is the practical companion to `alsa-lib`: playback and capture, mixer control, MIDI/sequencer utilities, and speaker testing all land here.

On compatible targets, selecting `alsa-utils` also auto-selects the USB audio kernel driver stack exposed in menuconfig, so a USB DAC can be brought up without manually chasing the required `snd*` modules.

## Typical uses

- list and inspect sound cards with `aplay -l` / `arecord -l`
- control mixer state with `amixer` and `alsactl`
- test playback and capture paths with `speaker-test`, `aplay`, and `arecord`
- exercise MIDI and sequencer devices on systems that expose them