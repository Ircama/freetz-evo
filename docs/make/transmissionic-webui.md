# Transmissionic web UI — 1.8.0

| | |
|---|---|
| **Homepage** | [github.com/6c65726f79/Transmissionic](https://github.com/6c65726f79/Transmissionic) |
| **Changelog** | [github.com/6c65726f79/Transmissionic/releases](https://github.com/6c65726f79/Transmissionic/releases) |
| **Repository** | [github.com/6c65726f79/Transmissionic](https://github.com/6c65726f79/Transmissionic) |
| **Package** | [`make/pkgs/transmissionic-webui/`](../../make/pkgs/transmissionic-webui/) |
| **Steward** | Ircama |

---

## Overview

**Transmissionic web UI** is a static Transmission frontend packaged for Freetz-EVO.

Installed files are static and deployed to:

- `/usr/mww/transmissionic/`

The package itself does not provide backend services; Transmission RPC backend must be available.

## Installation

Enable in `make menuconfig`:

```
Packages -> T -> transmission -> Transmissionic web UI (static frontend)
```

This selector is integrated in the Transmission menu and automatically activates the hidden package symbol.

## Access URL

- `http://fritz.box:81/transmissionic/`

## Relevant files

| File | Purpose |
|---|---|
| [`make/pkgs/transmissionic-webui/transmissionic-webui.mk`](../../make/pkgs/transmissionic-webui/transmissionic-webui.mk) | Download ZIP, unpack and install `/web` assets |
| [`make/pkgs/transmissionic-webui/external.in`](../../make/pkgs/transmissionic-webui/external.in) | Externalization option |
| [`make/pkgs/transmissionic-webui/external.files`](../../make/pkgs/transmissionic-webui/external.files) | Externalized paths list |
| [`make/pkgs/transmission/Config.in`](../../make/pkgs/transmission/Config.in) | Integrated frontend selection option |
