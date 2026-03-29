# transmission-web-control — 20190919 snapshot

| | |
|---|---|
| **Homepage** | [github.com/nurzico/transmission-web-control](https://github.com/nurzico/transmission-web-control) |
| **Changelog** | [github.com/nurzico/transmission-web-control/commits/master](https://github.com/nurzico/transmission-web-control/commits/master) |
| **Repository** | [github.com/nurzico/transmission-web-control](https://github.com/nurzico/transmission-web-control) |
| **Package** | [`make/pkgs/transmission-web-control/`](../../make/pkgs/transmission-web-control/) |
| **Maintainer** | @Ircama |

---

## Overview

**transmission-web-control** is a static web frontend for Transmission.

In Freetz-EVO it is pinned to commit:

- `cab9182a9a42329cc058555d846eabd5737ae9d4`

and installs static files to:

- `/usr/mww/transmission-web-control/`

No service process is started by this package; it needs a running Transmission daemon.

## Installation

Enable in `make menuconfig`:

```
Packages -> T -> transmission -> transmission-web-control (static frontend)
```

The option is integrated in Transmission and selects this package internally.

## Access URL

- `http://fritz.box:81/transmission-web-control/`

## Relevant files

| File | Purpose |
|---|---|
| [`make/pkgs/transmission-web-control/transmission-web-control.mk`](../../make/pkgs/transmission-web-control/transmission-web-control.mk) | Download, unpack and install static frontend files |
| [`make/pkgs/transmission-web-control/external.in`](../../make/pkgs/transmission-web-control/external.in) | Externalization option |
| [`make/pkgs/transmission-web-control/external.files`](../../make/pkgs/transmission-web-control/external.files) | Externalized paths list |
| [`make/pkgs/transmission/Config.in`](../../make/pkgs/transmission/Config.in) | Integrated frontend selection option |
