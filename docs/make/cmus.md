# cmus 2.11.0
  - Homepage: [https://cmus.github.io/](https://cmus.github.io/)
  - Changelog: [https://github.com/cmus/cmus/releases](https://github.com/cmus/cmus/releases)
  - Repository: [https://github.com/cmus/cmus](https://github.com/cmus/cmus)
  - Package: [master/make/pkgs/cmus/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/cmus/)
  - Steward: -

  - Depends on: `alsa-lib`, `libatomic`, `ncursesw`, `libmad`, `FLAC`, `libvorbisfile`
  - Provides: `/usr/bin/cmus`, `/usr/bin/cmus-remote`, `/usr/lib/cmus`, `/usr/share/cmus`
  - Externalization: supported

`cmus` is a lightweight ncurses music player for local audio playback on the box. This build is configured around ALSA output and the common fixed-point audio codec stack needed on resource-constrained MIPS targets.

The package auto-selects the exposed ALSA USB audio driver stack when available, making it a good fit for USB DAC based playback scenarios.

## Enabled playback stack

- ALSA output backend
- MP3 via `libmad`
- FLAC via `libFLAC`
- Vorbis via `libvorbisfile`
- wide-character terminal UI via `ncursesw`