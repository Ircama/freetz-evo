# TrguiNG web — 1.5.1

| | |
|---|---|
| **Homepage** | [github.com/openscopeproject/TrguiNG](https://github.com/openscopeproject/TrguiNG) |
| **Changelog** | [github.com/openscopeproject/TrguiNG/releases](https://github.com/openscopeproject/TrguiNG/releases) |
| **Repository** | [github.com/openscopeproject/TrguiNG](https://github.com/openscopeproject/TrguiNG) |
| **Package** | [`make/pkgs/trguing-web/`](../../make/pkgs/trguing-web/) |
| **Steward** | Ircama |

---

## Overview

**TrguiNG web** is a static web interface for Transmission RPC.

In Freetz-EVO this package installs static frontend files under:

- `/usr/mww/trguing/`

No daemon is started by this package; it requires Transmission daemon running and reachable.

## Installation

Enable in `make menuconfig`:

```
Packages -> T -> transmission -> TrguiNG web (static frontend)
```

The option is integrated in the Transmission package menu and auto-selects the internal package symbol.

## Access URL

- `http://fritz.box:81/trguing/`

## Relevant files

| File | Purpose |
|---|---|
| [`make/pkgs/trguing-web/trguing-web.mk`](../../make/pkgs/trguing-web/trguing-web.mk) | Download ZIP, unpack and install static assets |
| [`make/pkgs/trguing-web/external.in`](../../make/pkgs/trguing-web/external.in) | Externalization option |
| [`make/pkgs/trguing-web/external.files`](../../make/pkgs/trguing-web/external.files) | Externalized paths list |
| [`make/pkgs/transmission/Config.in`](../../make/pkgs/transmission/Config.in) | Integrated frontend selection option |
