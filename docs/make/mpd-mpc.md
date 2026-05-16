# mpc 0.35 (MPD CLI client)
  - Homepage: [https://www.musicpd.org/clients/mpc/](https://www.musicpd.org/clients/mpc/)
  - Manpage: [https://www.musicpd.org/doc/mpc/html/](https://www.musicpd.org/doc/mpc/html/)
  - Changelog: [https://github.com/MusicPlayerDaemon/mpc/releases](https://github.com/MusicPlayerDaemon/mpc/releases)
  - Repository: [https://github.com/MusicPlayerDaemon/mpc](https://github.com/MusicPlayerDaemon/mpc)
  - Package: [master/make/pkgs/mpd-mpc/](https://github.com/Ircama/freetz-evo/tree/master/make/pkgs/mpd-mpc/)
  - Steward: -

  - Depends on: `libmpdclient`
  - Provides: `/usr/bin/mpc`
  - Externalization: supported

`mpc` is the lightweight command-line client for `MPD`. It provides shell-friendly access to common player operations such as status queries, play/pause control, queue edits, playlist browsing, and volume changes against a local or remote Music Player Daemon.

In Freetz-EVO the package installs only the `mpc` CLI binary and links it against the shared `libmpdclient` package instead of bundling a private copy of the client library.

## Freetz integration

- intended companion to the local `mpd` package, but can control any reachable MPD server
- useful for shell scripts, cron jobs, SSH sessions, and other low-overhead automation
- externalizable to move the client binary out of internal flash

## Build characteristics

- Meson build with fallback downloads disabled
- documentation and tests disabled to reduce build time and package size
- runtime connection defaults inherited from `libmpdclient`