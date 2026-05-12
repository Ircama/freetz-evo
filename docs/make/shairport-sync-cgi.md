# shairport-sync CGI (AirPlay config/status web UI)
  - Package: [master/make/pkgs/shairport-sync-cgi/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/shairport-sync-cgi/)
  - Steward: Ircama

  - Depends on: `shairport-sync`
  - CGI: `/usr/lib/cgi-bin/shairport-sync.cgi`
  - Status CGI: `/usr/lib/cgi-bin/shairport-sync/status.cgi`
  - Configuration URL: `http://fritz.box:81/cgi-bin/conf/shairport-sync`

`shairport-sync-cgi` adds the Freetz web integration for `shairport-sync`: startup handling, configuration persistence, daemon registration and the live status page.

The status page consumes the cached output of the metadata FIFO reader and exposes the currently active client, playback state and track metadata directly in the Freetz UI.

## Included integration pieces

- default config template and config generator
- init script with daemon registration and metadata collector management
- configuration CGI for AirPlay and ALSA settings
- status CGI for playback state, metadata and recent logs