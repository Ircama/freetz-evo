# hidws-cgi 1.0 (binaries only)
  - Package: [master/make/pkgs/hidws-cgi/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/hidws-cgi/)
  - Steward: Ircama
  - Backend: [hidws](hidws.md) — [github.com/Ircama/hidws](https://github.com/Ircama/hidws)

`hidws-cgi` provides the freetz web configuration page and the daemon control
(init script `rc.hidws`) for the `hidws` WebSocket ↔ USB HID gateway.

It depends on the `hidws` package and installs:

- `/etc/init.d/rc.hidws` — daemon lifecycle (`start`/`stop`/`restart`/`status`)
  with `modreg cgi` alias, so it appears under **Packages > Web interfaces**
- `/etc/default.hidws/hidws.cfg` — default configuration (`HIDWS_ENABLED`,
  `HIDWS_PORT`, `HIDWS_NICE`)
- `/usr/lib/cgi-bin/hidws.cgi` — the web page at
  `http://fritz.box:81/cgi-bin/conf/hidws`

## Web page

- Start type (manual / automatic), WebSocket port and nice level
- Running status (green/red) with the WebSocket endpoint
- Execution log windows: `/tmp/rc.hidws.log` (init script actions) and
  `/tmp/hidws.log` (daemon stdout/stderr)
- Links to the web apps that connect to the daemon over WebSocket:
  - [kt02h20-control](https://ircama.github.io/kt02h20-control/)
  - [Audiocular-Aura (AuraPEQ)](https://ircama.github.io/Audiocular-Aura/)
  - [fiiocontrol-oss](https://ircama.github.io/fiiocontrol-oss/)

## Configuration variables

| Variable | Default | Meaning |
|---|---|---|
| `HIDWS_ENABLED` | `no` | Start hidws at boot (automatic) |
| `HIDWS_PORT` | `9001` | WebSocket listen port |
| `HIDWS_NICE` | `5` | Process priority (nice level) |

Saving the web page does **not** restart the daemon; restart it manually if
the port changed.
