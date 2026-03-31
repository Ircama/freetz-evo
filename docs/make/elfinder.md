# elFinder web file manager
  - Homepage: [https://github.com/Studio-42/elFinder](https://github.com/Studio-42/elFinder)
  - Manpage: [https://github.com/Studio-42/elFinder/wiki](https://github.com/Studio-42/elFinder/wiki)
  - Changelog: [https://github.com/Studio-42/elFinder/releases](https://github.com/Studio-42/elFinder/releases)
  - Repository: [https://github.com/Studio-42/elFinder](https://github.com/Studio-42/elFinder)
  - Package: [master/make/pkgs/elfinder/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/elfinder/)
  - Steward: -
  - Maintainer: [@Ircama](https://github.com/Ircama)

elFinder is a full-featured web-based file manager for the FritzBox, inspired by the Finder application in Mac OS X. It provides a familiar drag-and-drop interface to browse, upload, download, copy, move, rename, archive and manage files on the FritzBox storage via a browser.

## Features

- **PHP LocalFileSystem connector** — reads `/mod/etc/conf/elfinder.cfg` at runtime; works on read-only squashfs
- **FTP remote volumes** — optional driver for mounting remote FTP servers as elFinder volumes
- **MediaInfo integration** — detailed information for media files (codec, bitrate, duration, resolution)
- **Archive support** — optional unrar and 7-Zip (7za) integration
- **Visual themes** — optional 3rd-party themes: Moono, Windows 10, Material Design, Bootstrap/LibreICONS
- **Multilingual UI** — Italian-first interface with de/en/fr/es/it/… translations

## URLs

  - Web interface: `http://fritz.box:81/elfinder/`
  - CGI configuration: `http://fritz.box:81/cgi-bin/conf/elfinder`

-----------

# elFinder on Freetz (full technical overview)

## Summary

This package integrates **elFinder 2.1.66** in Freetz as a web file manager for FritzBox environments.

- Web UI: `/elfinder/`
- webcfg page: `/cgi-bin/conf/elfinder`
- PHP connector: `php/connector.php`

The implementation targets practical home NAS workflows: file browsing, upload/download, archive handling, media preview, metadata integration, optional themes, and webcfg authentication integration.

## Architecture

## Main components

- `make/pkgs/elfinder/Config.in`
- `make/pkgs/elfinder/elfinder.mk`
- `make/pkgs/elfinder/files/root/usr/lib/cgi-bin/elfinder.cgi`
- `make/pkgs/elfinder/files/root/usr/mww/elfinder/index.html`
- `make/pkgs/elfinder/files/root/usr/mww/elfinder/php/connector.php`
- `make/pkgs/elfinder/files/root/usr/mww/elfinder/php/plugins/MovieInfo/plugin.php`
- `make/pkgs/elfinder/files/root/usr/mww/elfinder/php/plugins/MediaInfo/plugin.php`
- `make/pkgs/elfinder/files/root/etc/default.elfinder/elfinder.cfg`
- `make/pkgs/elfinder/files/root/etc/default.elfinder/elfinder.save`
- `make/pkgs/elfinder/files/root/etc/init.d/rc.elfinder`

## Config model

- default exported values live in `default.elfinder/elfinder.cfg`.
- saved values are loaded from:
  - `/var/mod/etc/conf/elfinder.cfg` (preferred when present)
  - `/mod/etc/conf/elfinder.cfg`
- save hook logic in `elfinder.save` is lightweight runtime apply logic (for example, runtime directory creation).

Important runtime note:

- current implementation uses the deployed `php/connector.php` directly at runtime.
- `conf/connector.php.template` is kept for compatibility/history, not as the primary runtime path in this version.

## User-facing feature set

## File manager core

- browse, upload, download, rename, copy/cut/paste, quicklook, info, archive/extract.
- contextual menus for navbar/current directory/files.
- LocalFileSystem root plus Trash volume.

## Media preview and seek behavior

Actual seek behavior depends on browser/player combination and HTTP range support.

Connector highlights:

- custom connector class intercepts `cmd=file` for media.
- single-range parsing and correct `206 Partial Content` responses.
- explicit `Accept-Ranges`, `Content-Range`, and `Content-Length` handling.
- session lock is released before streaming to reduce seek blocking across concurrent requests.
- native seek with chunked fallback strategy.

## MovieInfo plugin

- dedicated toolbar button in UI.
- filename-based movie title/year inference.
- providers: `auto`, `tmdb`, `omdb`, `wikipedia`, `imdb`.
- auto order: `tmdb -> omdb -> wikipedia -> imdb`.
- cache file: `/tmp/elfinder-movieinfo-cache.json`.
- API keys can be used as request overrides or persisted through the authenticated connector command path.

## MediaInfo plugin

- integrated on `cmd=info`.
- intentionally activated only when UI requests `with_mediainfo=1`.
- avoids unnecessary MediaInfo execution during MovieInfo flows.

## Open in VLC

- dedicated toolbar button.
- builds an absolute connector media URL.
- attempts `vlc:` protocol launch.
- fallback dialog provides copyable URL when protocol handler is not registered.

## Archive support

- standard archive tools from base system.
- optional package-based support for RAR and 7z operations.

## Themes

Build-time optional themes include:

- moono
- windows-10
- material
- bootstrap (LibreICONS-based)

If a theme directory provides `css/theme.css`, it can be selected in config/UI.

## i18n

- frontend language bundle is loaded dynamically from browser language.
- CGI page text is localized for de/en/it.

## CGI analysis (elfinder.cgi)

## AJAX response format

AJAX responses are intentionally wrapped in HTML and include an embedded JSON marker (`Content-Type: application/json`).

Clients must parse extracted JSON from response text, not use direct `response.json()`.

## Implemented actions

- `set_movieinfo_keys`
- `set_movieinfo_tmdb_key`
- `set_movieinfo_omdb_key`
- `check_directory`
- `get_status`

## Validation and guardrails

- path checks for directory probes.
- API key format validation.
- endpoint alias fallback handling in frontend for environment differences.

## Connector analysis (php/connector.php)

## Authentication and session behavior

- uses webcfg auth helper when available.
- allows unauthenticated `cmd=file` path where required for media serving flow.
- supports `cmd=auth_ping` for frontend auth probing and redirect behavior.

## Config loading behavior

- resilient default config discovery across multiple locations.
- saved config override loading from both `/mod/etc/conf` and `/var/mod/etc/conf`.

## Plugin binding model

- MovieInfo and MediaInfo are bound on `info` events via top-level plugin/bind options.
- MediaInfo remains explicitly request-gated.

## Media response handling

- extension-to-mime fallback map for common media types.
- single-range validation and `416` handling for invalid ranges.
- explicit streaming/logging flow designed for constrained systems.

## Init script behavior

`rc.elfinder` is a CGI package registration script, not a daemon manager.

It supports expected framework actions (`load`, `unload`, `start`, `stop`, `restart`, `status`) and registers/unregisters CGI endpoints.

## Operational notes

- always consider both saved config locations (`/var/mod/etc/conf` and `/mod/etc/conf`).
- CGI endpoint aliases may differ across devices; multi-endpoint probing in frontend is expected.
- after editing shell CGI files, run shell syntax checks (`sh -n`) to catch heredoc/parsing issues early.
- keep MovieInfo provider values consistent across connector/plugin/frontend/CGI UI options.
- keep MediaInfo trigger request-gated to avoid side effects on MovieInfo calls.

## Troubleshooting quick checklist

## AJAX errors / Unknown action

- verify which CGI alias is active in your setup.
- verify JSON extraction logic for wrapped responses.

## MovieInfo no-match behavior

- validate provider selection and filename parse quality.
- verify API key validity and HTTPS connectivity from the box.

## Seek/preview instability

- compare behavior across browsers/players.
- inspect `/tmp/elfinder.log`.
- verify range requests and `206` responses.

## Config not applied

- inspect active saved config file content.
- verify configured base directory exists and is accessible.

## Reference files

- [make/pkgs/elfinder/Config.in](../make/pkgs/elfinder/Config.in)
- [make/pkgs/elfinder/elfinder.mk](../make/pkgs/elfinder/elfinder.mk)
- [make/pkgs/elfinder/files/root/usr/lib/cgi-bin/elfinder.cgi](../make/pkgs/elfinder/files/root/usr/lib/cgi-bin/elfinder.cgi)
- [make/pkgs/elfinder/files/root/usr/mww/elfinder/index.html](../make/pkgs/elfinder/files/root/usr/mww/elfinder/index.html)
- [make/pkgs/elfinder/files/root/usr/mww/elfinder/php/connector.php](../make/pkgs/elfinder/files/root/usr/mww/elfinder/php/connector.php)
- [make/pkgs/elfinder/files/root/usr/mww/elfinder/php/plugins/MovieInfo/plugin.php](../make/pkgs/elfinder/files/root/usr/mww/elfinder/php/plugins/MovieInfo/plugin.php)
- [make/pkgs/elfinder/files/root/usr/mww/elfinder/php/plugins/MediaInfo/plugin.php](../make/pkgs/elfinder/files/root/usr/mww/elfinder/php/plugins/MediaInfo/plugin.php)
- [make/pkgs/elfinder/files/root/etc/default.elfinder/elfinder.cfg](../make/pkgs/elfinder/files/root/etc/default.elfinder/elfinder.cfg)
- [make/pkgs/elfinder/files/root/etc/default.elfinder/elfinder.save](../make/pkgs/elfinder/files/root/etc/default.elfinder/elfinder.save)
- [make/pkgs/elfinder/files/root/etc/init.d/rc.elfinder](../make/pkgs/elfinder/files/root/etc/init.d/rc.elfinder)
