# MPD 0.24.7
  - Homepage: [https://www.musicpd.org/](https://www.musicpd.org/)
  - Manpage: [https://mpd.readthedocs.io/en/stable/user.html](https://mpd.readthedocs.io/en/stable/user.html)
  - Changelog: [https://github.com/MusicPlayerDaemon/MPD/releases](https://github.com/MusicPlayerDaemon/MPD/releases)
  - Repository: [https://github.com/MusicPlayerDaemon/MPD](https://github.com/MusicPlayerDaemon/MPD)
  - Package: [master/make/pkgs/mpd/](https://github.com/Ircama/freetz-evo/tree/master/make/pkgs/mpd/)
  - Steward: Ircama

  - Depends on: `alsa-lib`, `flac`, `libid3tag`, `libmad`, `libogg`, `libvorbis`, `zlib`
  - Optional runtime dependencies: `libcurl` for URI input, `libsqlite3` for the SQLite database backend, `libbz2` for bzip2 support, and FFmpeg libraries for the optional FFmpeg decoder backend
  - Provides: `/usr/bin/mpd`
  - Configuration URL: `http://fritz.box:81/cgi-bin/conf/mpd` (with `mpd-cgi`)
  - Status URL: `http://fritz.box:81/cgi-bin/status/mpd` (with `mpd-cgi`)
  - Externalization: supported

`MPD` is the classic Music Player Daemon for local or network-controlled playback. The Freetz-EVO build is trimmed to the embedded use case: local database, TCP control interface, UNIX socket support, ALSA output, and the MP3/FLAC/Vorbis decoder stack.

Menuconfig toggles allow the package to stay compact by default while still exposing a few optional upstream features. Libcurl-based remote URI input for common `http://` and `https://` streams is enabled by default and can be disabled if a smaller build is preferred. Optional `sqlite`, `bzip2`, and `ffmpeg` backends remain disabled by default.

On compatible targets, selecting the package also auto-selects the exposed ALSA USB audio driver stack, making USB DAC playback practical without separate manual driver selection.

## Freetz integration

- optional `mpd-cgi` package for configuration, generated `mpd.conf`, daemon control, and live status in the web UI
- runtime config generation via `/mod/etc/default.mpd/mpd_conf`
- init integration tailored for the Freetz daemon and status registration flow

## Enabled feature set

- local music database
- TCP control interface and local UNIX socket
- daemon mode and inotify monitoring
- ALSA output backend
- MP3 via `libmad`
- FLAC via `libFLAC`
- Ogg/Vorbis via `libogg` and `libvorbis`
- libcurl input backend for remote HTTP/HTTPS URIs enabled by default
- optional SQLite database backend
- optional bzip2 support
- optional FFmpeg decoder backend

## Deliberately disabled upstream features

To keep the target footprint small and predictable, the Freetz package still disables many heavier optional integrations such as zeroconf, UPnP, WebDAV, PulseAudio, PipeWire, JACK, and the bundled HTTP server. The libcurl input backend is enabled by default, while SQLite, bzip2, and FFmpeg are exposed as explicit opt-in toggles.