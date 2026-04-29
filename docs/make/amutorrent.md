# aMUTorrent 3.5.0 - DEVELOPER
  - Homepage: [https://github.com/got3nks/amutorrent](https://github.com/got3nks/amutorrent)
  - Changelog: [https://github.com/got3nks/amutorrent/releases](https://github.com/got3nks/amutorrent/releases)
  - Repository: [https://github.com/got3nks/amutorrent](https://github.com/got3nks/amutorrent)
  - Package: [master/make/pkgs/amutorrent/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/amutorrent/)
  - Steward: Ircama
| | |
|---|---|
| **Homepage** | [github.com/got3nks/amutorrent](https://github.com/got3nks/amutorrent) |
| **Changelog** | [github.com/got3nks/amutorrent/releases](https://github.com/got3nks/amutorrent/releases) |
| **Repository** | [github.com/got3nks/amutorrent](https://github.com/got3nks/amutorrent) |
| **Package** | [`make/pkgs/amutorrent/`](../../make/pkgs/amutorrent/) |
| **Steward** | Ircama |

---

## Overview

**aMUTorrent** is an experimental developer-only package.

In Freetz-EVO it is packaged as a full Node.js service with:

- `/usr/lib/amutorrent/` for the compiled frontend and backend runtime
- `/usr/lib/cgi-bin/amutorrent.cgi` for the redirect/diagnostic CGI
- `/usr/mww/amutorrent/` for the web entrypoint redirect
- `/etc/init.d/rc.amutorrent` and `/etc/default.amutorrent/`

The package remains disabled by default and is intentionally gated behind developer mode because it depends on the target `nodejs` port.

At the moment that target-side Node.js port is not considered working/reliable in this tree, so aMUTorrent should be treated as experimental and not ready for normal deployment.

## Installation

Enable in `make menuconfig`:

```
Packages -> A -> aMUTorrent 3.5.0 - DEVELOPER
```

## Access URL

- `http://fritz.box:81/amutorrent/`

When the service is not running, that URL redirects to the CGI diagnostic page instead of serving the frontend directly.

## Relevant files

| File | Purpose |
|---|---|
| [`make/pkgs/amutorrent/amutorrent.mk`](../../make/pkgs/amutorrent/amutorrent.mk) | Download, build and install the full aMUTorrent package |
| [`make/pkgs/amutorrent/Config.in`](../../make/pkgs/amutorrent/Config.in) | Package selection option |
| [`make/pkgs/amutorrent/external.in`](../../make/pkgs/amutorrent/external.in) | Externalization option |
| [`make/pkgs/amutorrent/external.files`](../../make/pkgs/amutorrent/external.files) | Externalized paths list |
