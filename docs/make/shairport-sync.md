# shairport-sync 5.0.4
  - Homepage: [https://github.com/mikebrady/shairport-sync](https://github.com/mikebrady/shairport-sync)
  - Changelog: [https://github.com/mikebrady/shairport-sync/releases](https://github.com/mikebrady/shairport-sync/releases)
  - Repository: [https://github.com/mikebrady/shairport-sync](https://github.com/mikebrady/shairport-sync)
  - Package: [master/make/pkgs/shairport-sync/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/shairport-sync/)
  - Steward: -

  - Depends on: `alsa-lib`, `libconfig`, `libdaemon`, `popt`, `libssl`
  - Provides: `/usr/bin/shairport-sync`, `/usr/bin/shairport-sync-status-cache`
  - Configuration URL: `http://fritz.box:81/cgi-bin/conf/shairport-sync` (with `shairport-sync-cgi`)
  - Status URL: `http://fritz.box:81/cgi-bin/status/shairport-sync` (with `shairport-sync-cgi`)
  - Externalization: supported

`shairport-sync` turns the box into an AirPlay audio receiver with ALSA output. The Freetz package is intentionally trimmed to the embedded use case: ALSA backend, OpenSSL, metadata support, tinysvcmdns, and a small status-cache helper for the live Freetz status page.

On compatible targets, selecting the package also auto-selects the exposed ALSA USB audio driver stack. This makes USB DAC setups practical without extra manual driver selection.

## Freetz integration

- optional `shairport-sync-cgi` package for configuration and daemon control in the web UI
- generated runtime config via `modlib_config`
- metadata FIFO reader feeding the live status page with title, artist, album, client and playback state
- startup model tailored for the Freetz init and status registration flow