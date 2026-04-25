# rTorrent/ruTorrent
  - Homepage: [https://github.com/rakshasa/rtorrent](https://github.com/rakshasa/rtorrent)
  - Manpage: [https://github.com/rakshasa/rtorrent/wiki](https://github.com/rakshasa/rtorrent/wiki)
  - Changelog: [https://github.com/rakshasa/rtorrent/releases](https://github.com/rakshasa/rtorrent/releases)
  - Repository: [https://github.com/rakshasa/rtorrent](https://github.com/rakshasa/rtorrent)
  - Package: [master/make/pkgs/rtorrent/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/rtorrent/)
  - Steward: -

- rTorrent homepage: [https://github.com/rakshasa/rtorrent](https://github.com/rakshasa/rtorrent)
- rTorrent wiki/manpage: [https://github.com/rakshasa/rtorrent/wiki](https://github.com/rakshasa/rtorrent/wiki)
- rTorrent releases: [https://github.com/rakshasa/rtorrent/releases](https://github.com/rakshasa/rtorrent/releases)
- Freetz package path: [master/make/pkgs/rtorrent/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/rtorrent/)
- Maintainer: [@Ircama](https://github.com/Ircama)

## What is included

In this tree, the BitTorrent stack is split into three parts:

1. `rtorrent` daemon (download/seeding engine).
2. `rtorrent-cgi` web configuration interface and setup wizard.
3. `rutorrent` optional full-featured web UI for daily use.

## Current packaged versions

- `rtorrent`: `0.16.10`
- `libtorrent-rakshasa`: `0.16.10`
- `rutorrent`: `5.3.1`

For ruTorrent-specific packaging details and the preserved Freetz overlays, see [rutorrent.md](rutorrent.md).

## Source-based behavior map

Main files that define the current behavior:

- `make/pkgs/rtorrent-cgi/files/root/usr/lib/cgi-bin/rtorrent.cgi`
- `make/pkgs/rtorrent-cgi/files/root/etc/default.rtorrent/rtorrent.cfg`
- `make/pkgs/rtorrent-cgi/files/root/etc/default.rtorrent/rtorrent.save`
- `make/pkgs/rtorrent-cgi/files/root/etc/init.d/rc.rtorrent`
- `make/pkgs/rutorrent/Config.in.inc`
- `make/pkgs/rutorrent/rutorrent.mk`

## What rtorrent.cgi provides

### AJAX service endpoints

The CGI supports an `ajax=1` mode with wrapped JSON output and includes actions for:

- checking and creating the base directory,
- checking/creating `.rtorrent.rc`,
- creating the standard runtime directory structure,
- reading configured peer port from `.rtorrent.rc`,
- saving base path only,
- saving + starting the daemon,
- secure file read/write helpers for rTorrent and ruTorrent config files,
- soft-delete behavior for `.rtorrent.rc` by timestamped archive rename.

### Initial setup wizard

If no base path is configured or no `.rtorrent.rc` exists, the wizard is shown automatically.

Wizard flow:

1. choose storage location (RW mount suggestions are listed),
2. create/select base folder,
3. create `.rtorrent.rc` from template,
4. create runtime folders,
5. read active peer port and show forwarding reminder,
6. show ruTorrent availability and launch links.

The wizard also supports keyboard navigation and explicit close confirmation.

### Standard configuration page

Once setup is complete, the normal page exposes:

- service start mode,
- base directory,
- process priority,
- peer and bandwidth settings,
- DHT settings,
- hash-check behavior,
- boot wait behavior,
- SCGI communication port,
- memory limit tuning for pieces,
- boot monitoring settings,
- ruTorrent section (when installed),
- forwarding status section,
- integrated config editors,
- startup log viewer.

### Integrated config editors

The page links to:

- `/rtorrent/rtorrent_config_editor.html`
- `/rtorrent/rutorrent_config_editor.html`

Supported ruTorrent config targets include:

- `config.php`
- `freetz_config.php`
- `plugins.ini`
- `access.ini`

The backend applies path validation, whitelist checks, backup-before-write, and rollback on write failure.

## Save/apply and service behavior

### Save hook behavior

The save hook updates `.rtorrent.rc` after the framework save step, keeping runtime configuration aligned with form input.

It updates rate/peer/DHT/hash/SCGI/memory lines and writes debug traces to:

- `/var/tmp/rtorrent-save-debug.log`

### Init script behavior

The init script supports both manual lifecycle control and boot-time startup strategy:

- verifies required resources,
- supports immediate or delayed startup mode,
- can run a short boot monitor window with automatic restart attempts,
- writes startup logs to:
  - `/tmp/rc.rtorrent.log`
  - `/tmp/rtorrent.startup.out`
  - `/tmp/rtorrent.startup.err`

## ruTorrent plugin overview

### Core and base plugin model

From `Config.in.inc` and `rutorrent.mk`:

- ruTorrent can be installed with or without the official base plugin set,
- optional package-time plugin selection is supported,
- several third-party plugins are integrated by the package recipe.

### Included/optional plugin groups

Package-managed plugin set includes entries such as:

- `autodl-irssi`
- `mobile`
- `chat`, `nfo`, `hostname`
- `filemanager` (original or Freetz-enhanced variant)
- `mediastream`
- `fileshare`
- `logoff`
- `pausewebui`
- `instantsearch`
- `toggle_details_button`
- `trackerstatus`

### Freetz filemanager plugin variant

When enabled, the Freetz variant replaces the default filemanager plugin and adds embedded-oriented improvements (for example BusyBox-friendly behavior and improved archive handling).

For full plugin capability, additional tools such as `p7zip`, `unrar`, and `mediainfo` are recommended.

## Initial setup tutorial (user-focused)

This tutorial intentionally uses UI language only.

### 1) Build prerequisites

Enable at least:

1. rTorrent daemon package
2. rTorrent CGI package
3. ruTorrent package (recommended)

Optional but useful:

1. AVM rules package (forwarding workflow)
2. p7zip/unrar/mediainfo (plugin enhancements)

### 2) Open the configuration page

Open:

- `/cgi-bin/conf/rtorrent`

If prompted with the setup wizard:

1. pick a persistent storage location (USB/NAS),
2. create the main folder,
3. generate the default rTorrent config file,
4. create runtime subfolders,
5. confirm the detected peer port for router forwarding.

### 3) Validate setup results

After wizard completion, verify:

1. `.rtorrent.rc` exists in the selected main folder,
2. download/session/watch folders are present,
3. startup log section shows no fatal errors.

### 4) Tune runtime settings from the UI

In the regular form:

1. decide whether service should auto-start at boot,
2. set startup wait behavior for USB/NAS availability,
3. tune upload/download caps to match your line,
4. tune peer/session limits for your device RAM,
5. keep SCGI communication port consistent with ruTorrent.

### 5) Configure router forwarding

In the forwarding section:

1. read the active peer port detected from config,
2. forward both TCP and UDP for that same port in router rules.

Without proper forwarding, incoming connectivity is limited.

### 6) Launch ruTorrent and verify connection

Open:

- `/rutorrent/`

Confirm torrents load correctly and there is no SCGI/XMLRPC connection error.

## Daily usage quick guide

1. add torrents or magnet links in ruTorrent,
2. use watch folders for automatic loading/start policies,
3. use editor pages for controlled config edits,
4. review startup logs after major changes,
5. restart service when making structural configuration changes.

## Troubleshooting quick guide

### Service does not start

Check:

- `/tmp/rc.rtorrent.log`
- `/tmp/rtorrent.startup.err`

### Changes saved but not applied

Check:

- `/var/tmp/rtorrent-save-debug.log`

### ruTorrent cannot connect to backend

Check:

- service status,
- configured SCGI communication port alignment,
- XMLRPC proxy accessibility from ruTorrent.

### Permission/path issues

Check:

- ownership and write permissions on base folder and runtime subfolders,
- availability of mounted storage at boot time.

## Tree references

- `make/pkgs/rtorrent-cgi/files/root/usr/lib/cgi-bin/rtorrent.cgi`
- `make/pkgs/rtorrent-cgi/files/root/etc/default.rtorrent/rtorrent.cfg`
- `make/pkgs/rtorrent-cgi/files/root/etc/default.rtorrent/rtorrent.save`
- `make/pkgs/rtorrent-cgi/files/root/etc/init.d/rc.rtorrent`
- `make/pkgs/rutorrent/Config.in.inc`
- `make/pkgs/rutorrent/rutorrent.mk`
