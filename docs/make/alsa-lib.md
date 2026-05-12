# alsa-lib 1.2.13

  - Package: [master/make/libs/alsa-lib/](https://github.com/Ircama/freetz-evo/tree/master/make/libs/alsa-lib/)
  - Homepage: [https://www.alsa-project.org/wiki/Main_Page](https://www.alsa-project.org/wiki/Main_Page)
  - Provides: `libasound.so.2`, `/usr/share/alsa`
  - Used by: `alsa-utils`, `cmus`, `shairport-sync`
  - Externalization: supported

`alsa-lib` is the userspace runtime library for ALSA. Besides `libasound`, the package also installs the shared ALSA configuration tree under `/usr/share/alsa`, which is essential for normal device discovery and PCM definitions on the target.

In the new audio stack it is the common base for playback, capture, mixer access and AirPlay output.