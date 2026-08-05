# hidws 1.2.6 (binaries only)
  - Package: [master/make/pkgs/hidws/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/hidws/)
  - Upstream: [github.com/Ircama/hidws](https://github.com/Ircama/hidws) — tag `v1.2.6`
  - Steward: Ircama

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

hidws serves **both** plain `ws://` and encrypted `wss://` on the **same**
port. A self-signed certificate/key pair is generated automatically on first
start if it does not exist yet, so `wss://fritz.box:9001` works out of the
box. This is required by HTTPS-hosted web apps (e.g. GitHub Pages), which
block plain `ws://` connections.

- Default cert/key paths: `/mod/etc/hidws/server.crt`, `/mod/etc/hidws/server.key`
- Configured through the hidws web config page
  (`http://fritz.box:81/cgi-bin/conf/hidws`): enable/disable SSL, cert/key paths
- The certificate is self-signed; browsers will show a one-time warning.

## Diagnostic page

Opening `http://fritz.box:9001/` or `https://fritz.box:9001/` in a browser
serves a small diagnostic page (version, port, endpoints) with **"Test ws://" /
"Test wss://"** buttons that open a real WebSocket and report success/failure.
Useful to confirm access and to accept the one-time self-signed-cert exception
for `wss://`: visit `https://192.168.178.1:9001/` once, accept the warning,
then reconnect.

## Wire protocol (JSON over WebSocket)

Client → Server:

- `{"cmd":"list"}`
- `{"cmd":"open","vendorId":<int>,"productId":<int>}`
- `{"cmd":"send_report","reportId":<int>,"data":[...]}`
- `{"cmd":"send_feature_report","reportId":<int>,"data":[...]}`
- `{"cmd":"close"}`

Server → Client:

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

