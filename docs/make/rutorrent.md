# ruTorrent web interface

## Current packaged version

- ruTorrent: `5.3.1`
- Upstream release: `v5.3.1`
- Package recipe: `make/pkgs/rutorrent/rutorrent.mk`

## Package role in this tree

This package installs the full ruTorrent web interface under `/usr/mww/rutorrent` and is designed to work with the separate `rtorrent` daemon and `rtorrent-cgi` configuration UI.

The package can install:

1. ruTorrent core only.
2. ruTorrent with official base plugins.
3. Additional bundled third-party plugins selected at build time.

## Freetz-specific customizations kept on top of upstream

The ruTorrent package in this tree is not a plain upstream copy. After unpacking the upstream release, the recipe preserves and reapplies several local customizations:

1. `php/settings.php` is overridden with the local Freetz version for rTorrent 0.16+ compatibility.
2. `conf/config.php` is patched to auto-load `freetz_config.php` for dynamic SCGI and top-directory configuration.
3. `index.php` is provided locally as a WebCFG auth gate for direct `/rutorrent/` access.
4. `rtorrent_xmlrpc_proxy.php` is provided locally to expose an authenticated XMLRPC-to-SCGI proxy.
5. Local config templates and fallback `share/settings` data are copied after the upstream files.

These customizations are intentionally preserved during upgrades.

## Build-time plugin model

The package supports official/base plugin installation plus several bundled third-party plugins, including:

- `autodl-irssi`
- `mobile`
- `chat`
- `nfo`
- `hostname`
- `filemanager` or the Freetz-enhanced `freetz-filemanager`
- `mediastream`
- `fileshare`
- `logoff`
- `pausewebui`
- `instantsearch`
- `toggle_details_button`
- `trackerstatus`

## Notes for this version bump

Upstream `v5.3.1` keeps the paths used by the local Freetz overlays, including:

- `conf/config.php`
- `php/settings.php`
- `index.html`
- `plugins/httprpc/action.php`

This allows the package to move from `5.2.10` to `5.3.1` without changing the local overlay strategy.

## Related packages

1. `rtorrent` for the daemon and libtorrent stack.
2. `rtorrent-cgi` for setup wizard, save/apply handling, and config editors.
3. `php` and `httpd-webcfg` for serving the UI.
