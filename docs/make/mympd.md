# myMPD 25.0.2
  - Homepage: [https://github.com/jcorporation/myMPD](https://github.com/jcorporation/myMPD)
  - Manpage: [https://github.com/jcorporation/myMPD#readme](https://github.com/jcorporation/myMPD#readme)
  - Changelog: [https://github.com/jcorporation/myMPD/releases](https://github.com/jcorporation/myMPD/releases)
  - Repository: [https://github.com/jcorporation/myMPD](https://github.com/jcorporation/myMPD)
  - Package: [master/make/pkgs/mympd/](https://github.com/Ircama/freetz-evo/tree/master/make/pkgs/mympd/)
  - Steward: Ircama

  - Depends on: `openssl`, `pcre2`
  - Provides: `/usr/bin/mympd`
  - Configuration URL: `http://fritz.box:81/cgi-bin/conf/mympd` (with `mympd-cgi`)
  - Status URL: `http://fritz.box:81/cgi-bin/status/mympd` (with `mympd-cgi`)
  - Externalization: supported

`myMPD` is a lightweight standalone web client for `MPD`. In Freetz-EVO it is packaged as a self-contained daemon with embedded web assets and embedded `libmpdclient`, so the target only needs a compact runtime stack.

This makes it a good companion to `mpd` on devices where you want a browser-based control surface directly on the box, without deploying a separate external frontend.

## Freetz integration

- optional `mympd-cgi` package for bootstrap settings, daemon control, and live status in the web UI
- native web UI served by `myMPD` itself on the configured HTTP or HTTPS port
- bootstrap config initialized from the Freetz init script using the selected workdir and cachedir

## Build characteristics

- embedded web assets enabled
- embedded `libmpdclient` enabled
- OpenSSL runtime support
- PCRE2 runtime support
- docs, manpages, Lua, FLAC, libid3tag, IPv6, UTF-8 extras, and experimental features disabled to keep the package compact