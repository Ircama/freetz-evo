# alsa-lib 1.2.13

  - Package: [master/make/libs/alsa-lib/](https://github.com/Ircama/freetz-evo/tree/master/make/libs/alsa-lib/)
  - Homepage: [https://www.alsa-project.org/wiki/Main_Page](https://www.alsa-project.org/wiki/Main_Page)
  - Provides: `libasound.so.2`, `/usr/share/alsa`
  - Used by: `alsa-utils`, `cmus`, `shairport-sync`
  - Externalization: supported

`alsa-lib` is the userspace runtime library for ALSA. Besides `libasound`, the package also installs the shared ALSA configuration tree under `/usr/share/alsa`, which is essential for normal device discovery and PCM definitions on the target.

In the new audio stack it is the common base for playback, capture, mixer access and AirPlay output.

## Soft-float MIPS / FPU emulation

Many FritzBox SoCs (e.g. GRX550 MIPS32) lack a hardware FPU. Floating-point
operations in audio processing (sample rate conversion, equalization) are
emulated in software, which overwhelms the CPU and causes stuttering.

By default, the build system sets:
- `defaults.pcm.rate_converter linear` (integer-only, no FPU)
- `pcm.default pcm.plughw` (bypasses ALSA mixer, uses hw-native rates)

Applications should be configured to use ALSA device `hw:0,0` (direct
hardware access) instead of `default` (which may trigger resampling).

### Rate converter quality notes

The following rate converter plugins produce **low audio quality** and are
**not recommended for music playback**:

| Plugin | Alias / option | Quality issue |
|---|---|---|
| **linear** | `--disable-resample` in MPD | Fastest but lowest quality; only 0th-order hold |
| **lavcrate_faster** | ffmpeg `soxr` or `lavc` faster preset | Heavy aliasing, audible artifacts |
| **samplerate_order** | `libsamplerate` zero-order hold | Same as linear, DC-like distortion |
| **samplerate_linear** | `libsamplerate` linear interpolation | Noticeable high-frequency roll-off and aliasing |

For music, stick with `hw:0,0` to avoid resampling entirely.

Also use an audio card supporting both native 44.1 and 48 kHz sampling frequencies. A card only supporting 48000 Hz will require software resampling for 44100 Hz content.
