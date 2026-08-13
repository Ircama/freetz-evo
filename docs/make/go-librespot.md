# go-librespot 0.7.1 (binary only)
  - Homepage: [https://github.com/devgianlu/go-librespot](https://github.com/devgianlu/go-librespot)
  - Manpage: [https://github.com/devgianlu/go-librespot#readme](https://github.com/devgianlu/go-librespot#readme)
  - Changelog: [https://github.com/devgianlu/go-librespot/releases](https://github.com/devgianlu/go-librespot/releases)
  - Repository: [https://github.com/devgianlu/go-librespot](https://github.com/devgianlu/go-librespot)
  - Package: [master/make/pkgs/go-librespot/](https://github.com/Ircama/freetz-evo/tree/master/make/pkgs/go-librespot/)
  - Steward: Ircama
  - Toolchain: requires GCC 4.7 or newer (built with `-tags netgo` so Go uses its pure-Go resolver instead of `-lresolv`, which uClibc does not provide; Go 1.25's cgo runtime needs the C11 atomic builtins `__atomic_*`, missing in the old GCC 4.6.4 toolchain)

  - Depends on: `alsa-lib`, `flac`, `libogg`, `libvorbis`
  - Provides: `/usr/bin/go-librespot`
  - Configuration URL: `http://fritz.box:81/cgi-bin/conf/go-librespot` (with `go-librespot-cgi`)
  - Status URL: `http://fritz.box:81/cgi-bin/status/go-librespot` (with `go-librespot-cgi`)
  - Externalization: supported

`go-librespot` turns the box into a Spotify Connect endpoint. The Freetz-EVO package cross-compiles the upstream Go daemon with CGO enabled so it can talk to the local ALSA and codec stack directly on the target.

On compatible targets, selecting the package also auto-selects the exposed ALSA USB audio driver stack, making USB DAC based Spotify playback practical without manually chasing the `snd*` kernel modules.

## Freetz integration

- optional `go-librespot-cgi` package for configuration, runtime YAML generation, daemon control, and live status in the web UI
- startup handled through the Freetz init script model
- generated runtime configuration persisted under `/mod/etc/default.go-librespot/`

## Enabled audio stack

- ALSA playback via `alsa-lib`
- FLAC support via `libFLAC`
- Ogg/Vorbis support via `libogg` and `libvorbis`
- target-native Go build with CGO enabled