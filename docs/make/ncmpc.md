# ncmpc 0.52
  - Homepage: [https://www.musicpd.org/clients/ncmpc/](https://www.musicpd.org/clients/ncmpc/)
  - Changelog: [https://github.com/MusicPlayerDaemon/ncmpc/releases](https://github.com/MusicPlayerDaemon/ncmpc/releases)
  - Repository: [https://github.com/MusicPlayerDaemon/ncmpc](https://github.com/MusicPlayerDaemon/ncmpc)
  - Package: [master/make/pkgs/ncmpc/](https://github.com/Ircama/freetz-evo/tree/master/make/pkgs/ncmpc/)
  - Steward: -

  - Depends on: `libmpdclient`, `ncursesw`
  - Optional dependencies: `iconv` (character set conversion), `pcre2` (regex support), `gettext` (NLS), `lirc` (infrared remote control)
  - Provides: `/usr/bin/ncmpc`
  - Externalization: supported

`ncmpc` is the official ncurses client for the Music Player Daemon (MPD). It provides a full-featured terminal user interface for browsing the music library, editing the playlist, searching for songs, displaying lyrics, and controlling playback.

In Freetz-EVO the package is built with Meson with most optional screens enabled, offering a rich interactive experience over SSH or a local terminal. All major screens are included: help, library, search, song, key bindings, outputs, and lyrics.

## Freetz integration

- intended companion to the local `mpd` package, but can control any reachable MPD server
- useful for interactive SSH sessions and direct terminal usage on the device
- configurable via `~/.ncmpc/config` or `/mod/etc/default.ncmpc/` defaults
- externalizable to move the binary out of internal flash

## Optional features

- **iconv**: character set conversion for non-UTF-8 tags
- **PCRE2**: regular expression search support
- **NLS**: native language support for localized messages
- **LIRC**: infrared remote control support via `liblirc_client`

## Build characteristics

- Meson build system with documentation disabled
- colors, mouse support, and all screens (help, library, search, song, key, outputs, lyrics) enabled
- locale and multibyte support enabled