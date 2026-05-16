# libmpdclient 2.22 (Music Player Daemon client library)
  - Homepage: [https://www.musicpd.org/libs/libmpdclient/](https://www.musicpd.org/libs/libmpdclient/)
  - Manpage: [https://www.musicpd.org/doc/libmpdclient/](https://www.musicpd.org/doc/libmpdclient/)
  - Changelog: [https://github.com/MusicPlayerDaemon/libmpdclient/releases](https://github.com/MusicPlayerDaemon/libmpdclient/releases)
  - Repository: [https://github.com/MusicPlayerDaemon/libmpdclient](https://github.com/MusicPlayerDaemon/libmpdclient)
  - Package: [../../make/libs/libmpdclient/](../../make/libs/libmpdclient/)
  - Steward: -

  - Provides: `libmpdclient.so.2` shared runtime
  - Externalization: supported

`libmpdclient` is the official client library for `MPD`. In Freetz-EVO it is packaged as a reusable shared runtime for small frontends such as `mpc` and for other target-side tools that connect to a local or remote Music Player Daemon.

The library carries sensible Freetz defaults for embedded deployments, so clients automatically start with `localhost`, TCP port `6600`, and the UNIX socket path `/var/run/mpd/socket` unless they are configured otherwise.

## Runtime interface

- shared library `libmpdclient.so.2.22` plus SONAME symlinks
- ABI-compatible runtime for MPD client applications on target
- headers and `pkg-config` metadata installed only in staging for cross-build consumers

## Freetz integration

- packaged separately so multiple MPD clients can share one runtime library
- externalizable to move the shared object out of internal flash
- Meson build with documentation and tests disabled to keep the package lean