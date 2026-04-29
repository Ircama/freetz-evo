# flood-for-transmission — 1.0.1

| | |
|---|---|
| **Homepage** | [github.com/johman10/flood-for-transmission](https://github.com/johman10/flood-for-transmission) |
| **Changelog** | [github.com/johman10/flood-for-transmission/releases](https://github.com/johman10/flood-for-transmission/releases) |
| **Repository** | [github.com/johman10/flood-for-transmission](https://github.com/johman10/flood-for-transmission) |
| **Package** | [`make/pkgs/transmission-flood/`](../../make/pkgs/transmission-flood/) |
| **Steward** | Ircama |

---

## Overview

**flood-for-transmission** is a static web frontend for Transmission RPC.

In Freetz-EVO this package installs only static assets under:

- `/usr/mww/transmission-flood/`

It does not run a daemon and requires a configured/running `transmission-daemon`.

## Installation

Enable in `make menuconfig`:

```
Packages -> T -> transmission -> flood-for-transmission (static web frontend)
```

This option is integrated in the Transmission submenu and selects the hidden package symbol automatically.

## Access URL

- `http://fritz.box:81/transmission-flood/`

## Relevant files

| File | Purpose |
|---|---|
| [`make/pkgs/transmission-flood/transmission-flood.mk`](../../make/pkgs/transmission-flood/transmission-flood.mk) | Download/unpack/install static frontend files |
| [`make/pkgs/transmission-flood/external.in`](../../make/pkgs/transmission-flood/external.in) | Externalization option |
| [`make/pkgs/transmission-flood/external.files`](../../make/pkgs/transmission-flood/external.files) | Externalized paths list |
| [`make/pkgs/transmission/Config.in`](../../make/pkgs/transmission/Config.in) | Integrated frontend selection option |
