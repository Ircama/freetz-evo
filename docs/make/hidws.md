# hidws 1.3.1 (binary only)
  - Homepage: [https://github.com/Ircama/hidws](https://github.com/Ircama/hidws)
  - Changelog: [https://github.com/Ircama/hidws/releases](https://github.com/Ircama/hidws/releases)
  - Repository: [https://github.com/Ircama/hidws](https://github.com/Ircama/hidws)
  - Package: [master/make/pkgs/hidws/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/hidws/)
  - Steward: -
  - Toolchain: requires uClibc 1.0.58 or newer (links libwebsockets/libuv, which fail to link on older uClibc with "undefined reference to pthread_atfork")
  - Upstream: [github.com/Ircama/hidws](https://github.com/Ircama/hidws) — tag `v1.3.1`

`hidws` is a WebSocket/USB HID gateway daemon. It lets web apps (and
any WebSocket client) talk to USB HID devices remotely through a small JSON
protocol, without the browser needing direct USB access.

It uses libwebsockets for the WebSocket server and hidapi with the **libusb**
backend for HID access, so it also works on routers where the kernel
HID/INPUT subsystem is unavailable (e.g. GRX5 models — no `/dev/hidraw*`).

`hid-list` is a small diagnostic tool that enumerates all USB HID devices and
shows the reports they support.

## Runtime details in Freetz

- Binary paths: `/usr/bin/hidws`, `/usr/bin/hid-list`
- WebSocket port: `9001` by default (`hidws [port]`)
- Runtime dependency profile: `hidapi` (libusb) + `libwebsockets` (SSL)

## TLS / WSS support

By default (`hidws [port]`) serves **both** plain `ws://` and encrypted
`wss://` on the **same** port, using a **temporary self-signed certificate
kept only in memory** (no file, regenerated on every start; warning in the
log and on the diagnostic page). For a persistent certificate (stable
browser exception across restarts) use `--cert FILE [--key FILE]` — if the
cert file is missing, a self-signed certificate/key is generated
automatically at first start (`/mod/etc/hidws/server.crt` by default via
`rc.hidws`). `--no-ssl` forces plain `ws://` only.

- Default cert/key paths: `/mod/etc/hidws/server.crt`, `/mod/etc/hidws/server.key`
- Configured through the hidws web config page
  (`http://fritz.box:81/cgi-bin/conf/hidws`): enable/disable SSL, cert/key paths
- The certificate is self-signed; browsers will show a one-time warning.

## Diagnostic page

Opening `http://fritz.box:9001/` or `https://fritz.box:9001/` in a browser
serves a small diagnostic page (version, port, endpoints) with **"Test ws://" /
"Test wss://"** buttons that open a real WebSocket and report success/failure,
plus a warning banner when a temporary in-memory certificate is in use.
Useful to confirm access and to accept the one-time self-signed-cert exception
for `wss://`: visit `https://192.168.178.1:9001/` once, accept the warning,
then reconnect.

## Access control (optional)

All access control is **disabled by default** (open server, fully backwards
compatible). It only activates when credentials are configured on the hidws
web config page (`http://fritz.box:81/cgi-bin/conf/hidws`).

Credentials and the allowlist can be supplied through **three sources**
(lowest to highest precedence):

1. **Config file** — `--config FILE` (or the `HIDWS_CONFIG` env var) reads a
   simple `key=value` file (`#` comments allowed):
   `token=`, `user=`, `password=`, `allow=`.
2. **Environment variables** — `HIDWS_TOKEN`, `HIDWS_USER`,
   `HIDWS_PASSWORD`, `HIDWS_ALLOW` (comma-separated allowlist).
3. **Command line** — `--token SECRET`, `--user USER --password PASS`,
   `--allow <ip|cidr>,...`.

In Freetz the `rc.hidws` init script writes the configured values to a
**0600 config file** (`/mod/etc/hidws/hidws.conf`) and passes it with
`--config`, so the secrets never appear in the process command line (`ps`).

- `token` — bearer token; clients must authenticate with
  `{"cmd":"auth","token":SECRET}` (or `?token=SECRET` in the WebSocket URL,
  or an `Authorization: Bearer SECRET` header).
- `user`/`password` — alternative user/password pair
  (`{"cmd":"auth","user":...,"password":...}` or Basic auth header).
- `allow` — IPv4 allowlist (addresses and CIDR prefixes); connections from
  any other address are dropped **before** the WebSocket handshake.

When enabled, sessions start **unauthenticated**: all HID commands
(`list`, `open`, `send_report`, ...) are answered with
`{"type":"error","message":"not authenticated"}` until the client
authenticates. Success → `{"type":"auth_ok"}`; failure → `auth failed`
(connection closed after 5 consecutive failures — brute-force guard).
Constant-time secret comparison; the diagnostic page shows the auth/allowlist
state.

> For exposure beyond the LAN use `wss://` on top of the token: without TLS
the token travels in clear text.

## Wire protocol (JSON over WebSocket)

Client → Server:

- `{"cmd":"auth","token":SECRET}` or `{"cmd":"auth","user":...,"password":...}`
- `{"cmd":"list"}`
- `{"cmd":"open","vendorId":<int>,"productId":<int>}`
- `{"cmd":"send_report","reportId":<int>,"data":[...]}`
- `{"cmd":"send_feature_report","reportId":<int>,"data":[...]}`
- `{"cmd":"close"}`

Server → Client:

- `{"type":"auth_ok"}`
- `{"type":"device_list","devices":[...]}`
- `{"type":"opened","vendorId":...,"productId":...,"productName":"..."}`
- `{"type":"input_report","reportId":<int>,"data":[...]}`
- `{"type":"ok"}`
- `{"type":"error","message":"..."}`
- `{"type":"closed"}`

## Typical usage

- On the router: `/usr/bin/hidws 9001` (serves `ws://fritz.box:9001`)
  or with a cert: `/usr/bin/hidws 9001 --cert /mod/etc/hidws/server.crt`
  (serves `ws://` **and** `wss://fritz.box:9001`)
- With access control: `/usr/bin/hidws 9001 --config /mod/etc/hidws/hidws.conf`
  (rc.hidws builds this file from the web config page values) — web apps must
  then send `{"cmd":"auth","token":"mysecret"}` (or use
  `ws://fritz.box:9001/?token=mysecret`). Configured via the hidws web config
  page (token/user/password/allow fields).
- From a web app served locally or over HTTPS (avoid mixed content), connect
  to `ws://fritz.box:9001` or `wss://fritz.box:9001`
- The HID device is released automatically when the client disconnects.

## Notes

- The KT02H20 family (FiiO JA11 etc.) uses OUTPUT reports; frontends must send
  data with `send_report` (report ID 0x02), not feature reports.
- `input_report` data received over WebSocket includes the report-ID byte as the
  first element for numbered input reports; WebHID strips it, so remote
  frontends must strip it to match.
- `hidws` must be compiled with `-O0` on the MIPS/uClibc toolchain (reader
  thread miscompiled at `-O1+`).

