# aMUTorrent — 3.5.0

| | |
|---|---|
| **Homepage** | [github.com/got3nks/amutorrent](https://github.com/got3nks/amutorrent) |
| **Changelog** | [github.com/got3nks/amutorrent/releases](https://github.com/got3nks/amutorrent/releases) |
| **Repository** | [github.com/got3nks/amutorrent](https://github.com/got3nks/amutorrent) |
| **Package** | [`make/pkgs/amutorrent/`](../../make/pkgs/amutorrent/) |
| **Maintainer** | @Ircama |

---

## Overview

**aMUTorrent** is a static web frontend compatible with Transmission-style RPC backends.

In Freetz-EVO this package is standalone (not nested under Transmission options) and installs files to:

- `/usr/mww/amutorrent/`

No daemon is included; backend RPC service must be configured at runtime.

## Installation

Enable in `make menuconfig`:

```
Packages -> A -> aMUTorrent 3.5.0 (frontend statico)
```

## Access URL

- `http://fritz.box:81/amutorrent/`

## Relevant files

| File | Purpose |
|---|---|
| [`make/pkgs/amutorrent/amutorrent.mk`](../../make/pkgs/amutorrent/amutorrent.mk) | Download, unpack and install static frontend files |
| [`make/pkgs/amutorrent/Config.in`](../../make/pkgs/amutorrent/Config.in) | Package selection option |
| [`make/pkgs/amutorrent/external.in`](../../make/pkgs/amutorrent/external.in) | Externalization option |
| [`make/pkgs/amutorrent/external.files`](../../make/pkgs/amutorrent/external.files) | Externalized paths list |
