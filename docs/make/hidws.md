# hidws 1.1.0 (binaries only)
  - Package: [master/make/pkgs/hidws/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/hidws/)
  - Steward: Ircama
  - Protocol reference: [Audiocular-Aura](https://github.com/mandy321/Audiocular-Aura)

`hidws` is a generic WebSocket ↔ USB HID gateway daemon. It lets web apps (and
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
- Runtime dependency profile: `hidapi` (libusb) + `libwebsockets`
- Externalization: supported for both binaries

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

- On the router: `/usr/bin/hidws 9001`
- From a web app served locally or over HTTPS (avoid mixed content), connect to
  `ws://fritz.box:9001`
- The HID device is released automatically when the client disconnects, so
  there is no dangling handle and no need to `kill` the daemon.

## Notes

- The KT02H20 family (FiiO JA11 etc.) uses OUTPUT reports; frontends must send
  data with `send_report` (report ID 0x02), not feature reports.
- `input_report` data received over WebSocket includes the report-ID byte as the
  first element for numbered input reports; WebHID strips it, so remote
  frontends must strip it to match.
