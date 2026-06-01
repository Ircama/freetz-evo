# Welcome to Freetz-EVO

```text
  _____              _            _______     _____
 |  ___| __ ___  ___| |_ ____    | ____\ \   / / _ \
 | |_ | '__/ _ \/ _ \ __|_  /____|  _|  \ \ / / | | |
 |  _|| | |  __/  __/ |_ / /_____| |___  \ V /| |_| |
 |_|  |_|  \___|\___|\__/___|    |_____|  \_/  \___/

```

Freetz-EVO is a fork of [Freetz-NG](https://github.com/Freetz-NG/freetz-ng), which remains the technical foundation of this project.
Freetz-EVO builds on that foundation with additional packages, UX improvements, and workflow tooling. Freetz-EVO is easier, sleeker, with more features and less bugs.

Freetz-EVO includes:

- over 100 new packages and libraries, including exclusive applications,
- over 60 python3 libraries,
- about 20 added packages,
- about 40 improved packages and libraries,
- USB audio stack, playback tools, and web radio functions,
- microcontroller flasher tools to enable USB peripheral devices.
- built-in Go and Rust toolchains to compile Go and Rust packages.

Relevant new packages include rtorrent with improved ruTorrent web tool, aria2 with AriaNg web tool, a Disk Management interactive web tool, ncdu web tool, improved elfinder Web tool, GCC on-device, nginx and many others.

New subsystems also include ALSA userspace audio packages, exposed ALSA/USB audio kernel drivers on compatible targets, and the `cdc-acm` USB serial driver for native USB CDC ACM devices.

On compatible targets, enabling the exposed ALSA/USB audio drivers together with the ALSA userspace stack allows audio playback through a USB headset or, preferably, a USB HiFi DAC. Combined with the available MPD, mpc, myMPD, and related web interfaces, Freetz-EVO also offers web radio browsing, playback, and control functions directly from the browser.

Additionally, Freetz-EVO offers AI translation for non EN and DE languages, more explicit error/warning messages, an advanced GitHub Action for testing new developments, and many other new features.

Freetz-EVO is continuously kept in sync with the upstream [Freetz-NG](https://github.com/Freetz-NG/freetz-ng)
repository: upstream fixes, new firmware support, and toolchain updates are periodically merged, so Freetz-EVO keeps evolving on top of recent Freetz-NG base.

### Getting Started

New to Freetz-EVO? The **[Getting Started guide](docs/GETTING_STARTED.md)** walks you through the complete workflow: setting up a Linux build environment (including WSL on Windows), configuring the firmware, building it, and flashing your device.

### Improvements over Freetz-NG

Note: all new packages are currently developed and tested on an AVM FRITZ!Box 7590 AX with firmware FRITZ!OS 8.20.

Freetz-EVO is still in development.

#### UX and Web Interface

The Freetz-EVO web interface features a completely redesigned, fully responsive, mobile first skin ("EVO skin"). On mobile devices, the navigation adapts to a fixed bottom bar with a slide-up drawer for sub-menus and sub-pages; on desktop and tablet a horizontal top menu with hover dropdowns is used, with an optional hamburger mode that collapses the top bar into a right-side slide-in panel. Dark mode, page-width toggle, and per-device preferences are persisted in cookies for a consistent experience across page loads and devices.

The web interface can be added to the home screen on any smartphone (Android or iOS) for an app-like experience; on Android, [Samsung Internet](https://play.google.com/store/apps/details?id=com.sec.android.app.sbrowser) delivers a full PWA-quality install. With `freetz_proxy` and HTTPS the full PWA install prompt is available, and the same HTTPS URL works remotely via [MyFRITZ!](https://www.myfritz.net) without port-forwarding. See [docs/mobile.md](docs/mobile.md) for detailed setup instructions.

The authentication layer has been updated to support a **form-based session login** (in addition to the legacy HTTP Basic Auth mode). When the *New login with session id* option is enabled, the web interface presents a custom HTML login page instead of the native browser credential dialog; access is protected by a session cookie with a configurable inactivity timeout, persisted across browser restarts, so re-opening the browser within an active session no longer forces re-authentication. A bug in `passwd_save.sh` that caused the stored password hash to include the username prefix — making any password change break subsequent logins — has been fixed. The session cookie has been hardened: the session ID is now generated from `/dev/urandom` (128-bit CSPRNG) instead of a predictable MD5 of the login timestamp, and the cookie is issued with `HttpOnly` (blocks JavaScript access, preventing XSS-based session hijacking) and `SameSite=Strict` (blocks all cross-site request forgery, including top-level navigation from external links) flags.

[Interactive UI Mockup](screenshots/evo-demo.html) — live preview of the Freetz-EVO web interface (no device needed)

#### New packages

| Package | Description | Status |
|---|---|---|
| **[`Disk tools`](docs/make/disk-mgmt.md)** | Complete storage toolkit centered on the **[Disk Management Web UI](docs/make/disk-mgmt.md)** (`disk-mgmt-cgi`), a web console for partitioning, formatting, cloning, recovery, and disk diagnostics; backed by `parted`, `util-linux`, `gptfdisk`, `e2fsprogs`, `dosfstools`, `exfatprogs`, `ntfs-3g`, `fatresize`, `partclone`, `ddrescue`, `smartmontools`, `hdparm`, `testdisk`, `fsarchiver`, `clonezilla`, and `udpcast`. | EVO only |
| **[`util-linux`](docs/make/util-linux.md)** | Dual-version support (2.27.1 / 2.41) with Disk Tools category and utilities like `lsblk`, `fdisk`, `blkid`. | upstream has 2.27.1; EVO adds 2.41 |
| **[`ncdu`](docs/make/ncdu.md)** 1.19 | NCurses disk usage analyzer for quick inspection of storage usage on mounted filesystems. | EVO only |
| **[`ncdu CGI`](docs/make/ncdu-cgi.md)** (`ncdu-cgi`) | Web frontend for ncdu integrated into the Freetz configuration pages for browser-based usage analysis. | EVO only |
| **[`ALSA / USB audio kernel support`](docs/make/alsa-usb-audio-kernel-support.md)** | Exposes `soundcore`, `snd`, `snd-timer`, `snd-pcm`, `snd-hwdep`, `snd-rawmidi`, `snd-usbmidi-lib`, and `snd-usb-audio` in menuconfig on compatible targets. | EVO only |
| **[`alsa-utils`](docs/make/alsa-utils.md)** 1.2.13 / **[`alsa-lib`](docs/make/alsa-lib.md)** 1.2.13 | ALSA userspace toolchain and runtime library for playback, capture, mixer control, MIDI/sequencer tools, and `/usr/share/alsa` configuration data; both support external deployment. | EVO only |
| **[`alsaequal`](docs/make/alsaequal.md)** 0.7.1 | ALSA equalizer bridge exposing LADSPA EQ plugins as standard ALSA PCM/control devices; optional Freetz config/status web UI via `alsaequal-cgi`. | EVO only |
| **[`cmus`](docs/make/cmus.md)** 2.11.0 | Ncurses music player with ALSA output and MP3/FLAC/Vorbis playback. | EVO only |
| **[`go-librespot`](docs/make/go-librespot.md)** 0.7.1 | Spotify Connect audio daemon cross-compiled from upstream Go sources with CGO, using ALSA output plus FLAC and Ogg/Vorbis support; optional Freetz config/status web UI via `go-librespot-cgi`. | EVO only |
| **[`ncspot`](docs/make/ncspot.md)** 1.3.4 | Terminal Spotify client built from upstream Rust sources with ALSA playback and crossterm UI backend, packaged for target-side interactive use. | EVO only |
| **[`MPD`](docs/make/mpd.md)** 0.24.7 | Music Player Daemon with local database, TCP control interface, UNIX socket, ALSA output, and MP3/FLAC/Vorbis decoding; optional Freetz config/status web UI via `mpd-cgi`. | EVO only |
| **[`libmpdclient`](docs/make/libmpdclient.md)** 2.22 | Official MPD client library packaged as a shared runtime for target-side MPD frontends; includes Freetz defaults for `localhost`, port `6600`, and `/var/run/mpd/socket`. | EVO only |
| **[`mpc`](docs/make/mpd-mpc.md)** 0.35 (`mpd-mpc`) | Minimal MPD command-line client using shared `libmpdclient`; suitable for shell scripts, SSH sessions, and queue/player control against local or remote MPD servers. | EVO only |
| **[`myMPD`](docs/make/mympd.md)** 25.0.2 | Standalone lightweight web-based MPD client with embedded web assets and embedded `libmpdclient`; optional Freetz config/status web UI via `mympd-cgi`. | EVO only |
| **[`shairport-sync`](docs/make/shairport-sync.md)** 5.0.4 | AirPlay receiver with ALSA output, metadata FIFO processing, and a Freetz config/status web UI. | EVO only |
| **[`snapcast`](docs/make/snapcast.md)** 0.35.0 | Multiroom audio server/client package with `snapserver`, `snapclient`, ALSA output, and FLAC/Ogg/Vorbis support. | EVO only |
| **[`btop`](docs/make/btop.md)** 1.4.7 | Modern terminal resource monitor for CPU, memory, disks, network, and processes, with optional upstream themes. | EVO only |
| **[`nmon`](docs/make/nmon.md)** 16s | Curses-based Linux performance monitor for CPU, memory, disks, network, filesystems, and processes, with optional capture-to-file mode for later analysis. | EVO only |
| **[`wavemon`](docs/make/wavemon.md)** 0.9.7 | Ncurses wireless monitor for signal quality, bitrate, channels, and interface statistics. | EVO only |
| **[`cdc-acm` kernel driver](docs/make/cdc-acm.md)** | Exposes `cdc-acm.ko` in menuconfig on compatible targets, enabling native USB CDC ACM serial devices such as ESP32-C3 boards and other USB serial gadgets. | EVO only |
| **[`avrdude`](docs/make/avrdude.md)** 8.1 | AVR downloader/uploader toolchain with `avrdude`, `elf2tag`, and default `/etc/avrdude.conf` for full AVR flash/program workflows. | EVO only |
| **[`esp-serial-flasher`](docs/make/esp-serial-flasher.md)** git-f1cccac | ESP serial flashing toolkit shipping `linux_flasher` and `esp_fw_upload` for multi-image ESP32-family firmware upload layouts. | EVO only |
| **[`micronucleus`](docs/make/micronucleus.md)** 2.6 | USB bootloader uploader for Digispark/ATTiny devices using Micronucleus (`/usr/bin/micronucleus`). | EVO only |
| **[`telink_tools`](docs/make/telink_tools.md)** 1.0 | Native C Telink BLE bootloader CLI for TB-03F-KIT/TB-04-KIT style devices; supports burn, triad programming, and flash read/write/erase operations. | EVO only |
| **[`lazygit`](docs/make/lazygit.md)** 0.61.1 | Full-screen terminal UI for Git repositories. | EVO only |
| **[`lf`](docs/make/lf.md)** r41 | Terminal file manager with a Miller-column layout, keyboard-driven navigation, and customizable key bindings. Built with Go cross-compilation. | EVO only |
| **[`age`](docs/make/age.md)** 1.3.1 | Modern file encryption tool. | EVO only |
| **[`caddy`](docs/make/caddy.md)** 2.11.2 | General-purpose web server and reverse proxy with automatic HTTPS capabilities. | EVO only |
| **[`fzf`](docs/make/fzf.md)** 0.72.0 | Command-line fuzzy finder for interactive shell filtering. | EVO only |
| **[`glow`](docs/make/glow.md)** 2.1.2 | Terminal Markdown renderer for browsing README files and notes. | EVO only |
| **[`gum`](docs/make/gum.md)** 0.17.0 | Terminal UI helper toolkit for shell scripts. | EVO only |
| **[`hey`](docs/make/hey.md)** 0.1.5 | Small HTTP load generator for smoke tests and benchmarks. | EVO only |
| **[`hugo`](docs/make/hugo.md)** 0.161.1 | Static site generator for content trees stored on writable media. | EVO only |
| **[`prometheus`](docs/make/prometheus.md)** 3.11.3 | Monitoring and alerting server with local TSDB storage. | EVO only |
| **[`rclone`](docs/make/rclone.md)** 1.74.1 | Cloud and remote storage synchronization tool. | EVO only |
| **[`ripgrep`](docs/make/ripgrep.md)** 14.1.1 | Fast recursive text search tool (`rg`) based on Rust regex/search engines. | EVO only |
| **[`bat`](docs/make/bat.md)** 0.26.1 | Syntax-highlighting `cat` replacement for reading config files, logs, and source files directly on the device. | EVO only |
| **[`bottom`](docs/make/bottom.md)** 0.12.3 | Terminal system monitor (`btm`) for CPU, memory, disk, network, and process metrics. | EVO only |
| **[`bandwhich`](docs/make/bandwhich.md)** 0.23.1 | Terminal bandwidth utilization monitor by process/connection. | EVO only |
| **[`procs`](docs/make/procs.md)** 0.14.11 | Modern process viewer as an enhanced alternative to `ps`. | EVO only |
| **[`broot`](docs/make/broot.md)** 1.56.4 | Tree-style terminal file browser and launcher. | EVO only |
| **[`eza`](docs/make/eza.md)** 0.23.4 | Modern `ls` replacement with richer directory listings, colors, and tree-style output. | EVO only |
| **[`gitui`](docs/make/gitui.md)** 0.28.1 | Terminal UI for interactive Git workflows. | EVO only |
| **[`rainfrog`](docs/make/rainfrog.md)** 0.3.18 | Terminal PostgreSQL database exploration/query client. | EVO only |
| **[`jless`](docs/make/jless.md)** 0.9.0 | JSON pager/reader with interactive navigation and search. | EVO only |
| **[`lnav-rs`](docs/make/lnav-rs.md)** 0.9.0 | Rust-based log/JSON pager package (alias build based on `jless`). | EVO only |
| **[`lnav`](docs/make/lnav.md)** 0.14.0 | Advanced terminal log viewer and analyzer with optional Rust/PRQL extensions exposed in menuconfig and support for external deployment. | EVO only |
| **[`sha256sum`](docs/make/sha256sum.md)** 0.9.0 | SHA-256 checksum utility packaged from uutils/coreutils for target-side integrity verification. | EVO only |
| **[`tac`](docs/make/tac.md)** 0.9.0 | Reverse concatenation utility packaged from uutils/coreutils for target-side text processing workflows. | EVO only |
| **[`termscp`](docs/make/termscp.md)** 1.0.0 | Terminal SCP/SFTP client and remote file browser. | EVO only |
| **[`atuin`](docs/make/atuin.md)** 18.16.1 | Shell history synchronization and improved history search utility. | EVO only |
| **[`oxker`](docs/make/oxker.md)** 0.13.2 | Terminal Docker container monitor/manager UI. | EVO only |
| **[`yazi`](docs/make/yazi.md)** 26.5.6 | Fast terminal file manager package shipping `yazi` and helper `ya`. | EVO only |
| **[`zoxide`](docs/make/zoxide.md)** 0.9.9 | Smarter directory-jump helper that complements interactive shells with ranked path lookup. | EVO only |
| **[`restic`](docs/make/restic.md)** 0.18.1 | Encrypted backup tool for local and remote repositories. | EVO only |
| **[`vhs`](docs/make/vhs.md)** 0.11.0 | Scripted terminal-session recorder for demo generation. | EVO only |
| **[`NeoMutt`](docs/make/neomutt.md)** 20260504 | Console email client (MUA) with IMAP/POP3/SMTP, SSL/TLS via OpenSSL, wide-character ncurses UI, threading, sidebar, and a rich `muttrc` scripting language. | EVO only |
| **[`yq`](docs/make/yq.md)** 4.53.2 | YAML, JSON, and XML processor for config automation. | EVO only |
| **[`ttyd`](docs/make/ttyd.md)** 1.7.7 | Web-based terminal server: exposes any shell command over WebSocket; CGI page embeds a full xterm.js terminal with 7 themes, fullscreen, search, font-size controls, and canvas renderer. | EVO only |
| **[`aria2`](docs/make/aria2.md)** / **AriaNg** | Multi-protocol download utility (HTTP, FTP, BitTorrent, Metalink) with a full web UI (AriaNg) and CGI integration. | EVO only |
| **[`rTorrent`](docs/make/rtorrent.md)** 0.16.7 / **[`ruTorrent`](docs/make/rutorrent.md)** 5.2.10 | Feature-rich BitTorrent client with a complete web interface, CGI backend, and config editor. | EVO only |
| **[`transmission`](docs/make/transmission.md)** | Added integrated static frontend selectors in the Transmission submenu (`flood-for-transmission` 1.0.1, `TrguiNG web` 1.5.1, `Transmissionic web UI` 1.8.0, `transmission-web-control` commit snapshot), with package-level installation under `/usr/mww/*`; all available as selectable static frontends integrated in the Transmission package menu. | EVO only |
| **[`freetz_proxy`](docs/make/freetz-proxy.md)** | Lightweight CGI HTTPS↔HTTP reverse proxy and index gateway, with HTML/CSS/JS URL rewriting and CDN proxying. Accessible via MyFRITZ! and from the internet without port-forwarding. When included, the Fritz logo and the AVM user menu gain direct links to the Freetz menus (through the proxy). | EVO only |
| **[`melcloud`](docs/make/melcloud.md)** | MELCloud integration package with daemon, init script, CGI endpoint, and web UI for Mitsubishi Electric devices. | EVO only |
| **[`Nginx`](docs/make/nginx.md)** 1.29 | High-performance HTTP/reverse-proxy server with MIPS/ARM cross-compilation fixes and optional externalization. | EVO only |
| **[`krb5`](docs/make/krb5.md)** | MIT Kerberos/GSSAPI runtime libraries (`libkrb5`, `libgssapi_krb5`) for target packages requiring Kerberos authentication features. | EVO only |
| **[`OpenLDAP`](docs/make/openldap.md)** 2.6.8 | Client-library package exporting `liblber` and `libldap` for target-side LDAP consumers; server-side slapd pieces are intentionally not built. | EVO only |
| **[`PostgreSQL`](docs/make/postgresql.md)** 16.3 | PostgreSQL package exporting `libpq` for target-side SQL consumers and optionally installing minimal server binaries (`postgres`, `pg_ctl`, `initdb`). | EVO only |
| **[`pdns-authoritative`](docs/make/pdns-authoritative.md)** 5.0.5 | PowerDNS Authoritative Server port with optional `pdnsutil`, `pdns_control`, `zone2sql`, `zone2json`, `ixfrdist`, diagnostic tools, externalization support, selectable OpenSSL/GnuTLS DNS-over-TLS, optional libsodium and remote ZeroMQ support, and selectable `bind`/`pipe`/`godbc`/`gmysql`/`gpgsql`/`gsqlite3`/`geoip`/`lmdb`/`lua2`/`remote`/`tinydns` backends. Requires modern targets because upstream PowerDNS 5 needs GCC 8+ / C++17. | EVO only |
| **[`pdns-dnsdist`](docs/make/pdns-dnsdist.md)** 1.9.7 | DNS load-balancer/front-end from the PowerDNS suite, useful for policy routing, load balancing, and DNS traffic filtering. | EVO only |
| **[`pdns-recursor`](docs/make/pdns-recursor.md)** 5.3.4 | Recursive DNS resolver daemon from the PowerDNS suite, packaged separately from authoritative and dnsdist components. | EVO only |
| **[`unixODBC`](docs/make/unixodbc.md)** 2.3.12 | ODBC driver-manager library package exporting `libodbc`, `libodbcinst`, and `libodbccr` for target-side database consumers such as PowerDNS `godbc`. | EVO only |
| **[`PHP`](docs/make/php.md)** 8.4 / 8.5 | Modern PHP interpreter with multi-version selection (5.6 legacy, 8.4, 8.5), bzip2, libxml2, libatomic support. | upstream has PHP 5.6 only |
| **[`QuickJS`](docs/make/quickjs.md)** (2026-03-23 git snapshot) | Lightweight embeddable JavaScript engine, packaged with `qjs` and optional `qjsc` compiler support. | EVO only |
| **[`Python 3.14`](docs/make/python3.md)** | Python 3.14.3 with zip-importer fix, patchelf RPATH support, and build scripts for external deployment. | upstream has 3.14 too |
| **[`MicroPython`](docs/make/micropython.md)** 1.27.0 | Lightweight Python implementation for constrained environments, including REPL, script execution, and optional micropython-lib modules. | EVO only |
| **[`python3-cryptography`](docs/make/python3-cryptography.md)** 48.0.0 | Python cryptography package with OpenSSL bindings and Rust-backed components, built for target using cross-compiled Rust/Cargo support. | EVO only |
| **[`python3-ulid-transform`](docs/make/python3-ulid-transform.md)** 2.2.9 | ULID creation/transformation module built via pyproject/pip with Rust/Cargo cross-build support. | EVO only |
| **[`python3-uv`](docs/make/python3-uv.md)** 0.11.16 | Rust-based Python package/project manager built via pyproject/pip (`maturin`) with Rust/Cargo cross-build target support. | EVO only |
| **[`python3-*`](docs/make/python3.md)** (58 modules) | New Python 3 third-party packages: `aiodns 4.0.0`, `aiohttp 3.13.3`, `aiohttp-asyncmdnsresolver 0.1.1`, `aiohttp-fast-zlib 0.3.0`, `aiohappyeyeballs 2.6.1`, `aiosignal 1.4.0`, `annotatedyaml 1.0.2`, `async-timeout 5.0.1`, `attrs 26.1.0`, `av 16.0.1`, `audioop-lts 0.2.1`, `bcrypt 3.2.2`, `brotli 1.2.0`, `cffi 1.17.1`, `charset-normalizer 3.4.6`, `ciso8601 2.3.3`, `dateutil 2.9.0.post0`, `dbus-fast 4.0.0`, `faust-cchardet 2.1.19`, `fnv-hash-fast 1.6.0`, `fnvhash 0.2.1`, `frozenlist 1.8.0`, `grpcio 1.78.0`, `grpcio-reflection 1.78.1`, `grpcio-status 1.78.1`, `h11 0.16.0`, `ha-ffmpeg 3.2.2`, `httpcore 1.0.9`, `httpx 0.28.1`, `idna 3.11`, `lru-dict 1.4.1`, `lxml 6.0.2`, `markupsafe 3.0.3`, `multidict 6.7.1`, `numpy 2.4.3`, `pandas 3.0.1`, `pillow 12.1.1`, `pip 26.0.1`, `propcache 0.4.1`, `psutil 7.2.2`, `pycares 5.0.1`, `pycparser 3.0`, `pycryptodome 3.23.0`, `pymicro-vad 2.0.1`, `pynacl 1.6.2`, `pyspeex-noise 2.0.0`, `pyturbojpeg 2.2.0`, `pyyaml 6.0.3`, `setuptools 82.0.1`, `six 1.17.0`, `voluptuous 0.16.0`, `webrtc-models 0.3.0`, `yarl 1.23.0`, `zeroconf 0.148.0`, `python3-certifi 2025.10.5`, `python3-ifaddr 0.2.0`,  `python3-mashumaro 3.17`, `python3-orjson 3.10.7`, `typing_extensions 4.15.0`. Of which, pure-Python runtime modules (no compiled extensions) are: aiohappyeyeballs, aiosignal, async-timeout, attrs, charset-normalizer, dateutil, fnvhash, h11, idna, pycparser, six, voluptuous, certifi, ifaddr, mashumaro, typing_extensions. Build-time tooling (not required at runtime): pip, setuptools. | EVO only |
| **[`GitHub CLI`](docs/make/gh.md)** (`gh`) 2.83.2 | GitHub CLI tool with Go host-tool integration, allowing GitHub API interaction from the FritzBox. | EVO only |
| **[`GNU ddrescue`](docs/make/ddrescue.md)** 1.30 | Resilient data recovery and block-copy utility with mapfile-based resume support. | EVO only |
| **[`exfatprogs`](docs/make/exfatprogs.md)** 1.3.2 | User-space exFAT utilities for formatting, checking, labeling, and tuning exFAT filesystems. | EVO only |
| **[`fatresize`](docs/make/fatresize.md)** (snapshot) | FAT16/FAT32 resize utility for non-destructive partition resizing tasks. | EVO only |
| **[`fsarchiver`](docs/make/fsarchiver.md)** 0.8.9 | Filesystem-level backup and restore archiver with compressed image support. | EVO only |
| **[`partclone`](docs/make/partclone.md)** 0.3.31 | Block-level partition backup/restore/check tools frequently used in cloning workflows. | EVO only |
| **[`testdisk`](docs/make/testdisk.md)** 7.2 | Partition and file recovery toolkit for damaged media and lost partition tables. | EVO only |
| **[`udpcast`](docs/make/udpcast.md)** 20250223 | Multicast transfer utility for one-to-many image distribution in cloning operations. | EVO only |
| **[`elFinder`](docs/make/elfinder.md)** 2.1.66 | Full-featured web-based file manager for the FritzBox with enhancements: drag-and-drop UI, PHP connector (squashfs-safe), FTP remote volumes, video preview (with complete seek back and limited seek forward features), Movie plugin (scaping metadata from TMDb, OMDb, IMDb, Wikipedia; specific for Freetz-EVO), MediaInfo plugin (specific for Freetz-EVO), VLC plugin (specific for Freetz-EVO), unrar/7-Zip support, optional themes with theme selection plugin (specific for Freetz-EVO), multilingual (de/en/it/…), better status bar (specific for Freetz-EVO). | EVO only |
| **[`MediaInfo`](docs/make/mediainfo.md)** / libmediainfo / libzen / libxmlrpc | Media file analysis tool with full library stack; reports codecs, bitrates, resolution, and metadata. | EVO only |
| **[`proc-ps`](docs/make/procps-ng.md)** | Improved `ps` replacement backed by procps-ng with richer process information output. | merged upstream |
| **[`cpulimit`](docs/make/cpulimit.md)** 0.2 | Limits the CPU usage of a process to a given percentage; prevents runaway processes from overloading the device. | package improvement |
| **[`microperl`](docs/make/microperl.md)** 5.38 | Minimal Perl 5.38.2 interpreter (alongside legacy 5.10.1) with full stub library set for embedded use. | upstream has 5.10.1; EVO adds 5.38.2 |
| **[`zip`](docs/make/infozip.md)** 3.0 (infozip) | Standard `zip` archiver for creating ZIP archives directly on the device. | merged upstream |
| **[`gdb`](docs/make/gdb.md)** 17.1 | GNU Debugger version 17.1 for on-device debugging of binaries and crash analysis. | EVO only for 17.1 (upstream has 6.8/7.9.1) |
| **[`patchelf`](docs/make/patchelf.md)** (target) | ELF binary patcher for fixing RPATH and dynamic linker paths on cross-compiled binaries. | merged upstream |
| **[`binutils-tools`](docs/make/binutils-tools.md)** (`c++filt`, `elfedit`, `nm`, `objdump`) | Additional binutils utilities for binary inspection and symbol demangling on the device. | merged upstream |
| **[`libnettle`](docs/make/libnettle.md)** | Low-level cryptographic library (AES, SHA, RSA) used by GnuTLS and other packages. | upstream has nettle |
| **[`libzen`](docs/make/libzen.md)** | Helper library required by MediaInfo for portable C++ utilities. | EVO only |
| **[`libxmlrpc`](docs/make/libxmlrpc.md)** | XML-RPC library for rTorrent's SCGI/RPC interface; host tool gennmtab moved to `make/host-tools`. | EVO only |
| **[`libwebsockets`](docs/make/libwebsockets.md)** 4.3.9 | Canonical C WebSocket library; optional SSL/TLS support via OpenSSL. | EVO only |
| **[`json-c`](docs/make/json-c.md)** 0.17 | Lightweight JSON parser/serialiser library. | EVO only |
| **[`libcares`](docs/make/libcares.md)** (c-ares) | Asynchronous DNS resolver library used by aria2 and curl. | EVO only |
| **[`libsodium`](docs/make/libsodium.md)** 1.0.20 | Modern cryptographic library exporting `libsodium` for Ed25519 signatures, authenticated encryption, keyed hashes, and other high-level primitives. | EVO only |
| **[`libnl`](docs/make/libnl.md)** 3.11.0 | Netlink userspace library stack (`libnl-3`, `libnl-cli-3`, `libnl-genl-3`, `libnl-nf-3`, `libnl-route-3`). | EVO only |
| **[`libzmq`](docs/make/libzmq.md)** 4.3.5 | ZeroMQ messaging library exporting `libzmq` for asynchronous request/reply, pub/sub, and brokerless messaging patterns. | EVO only |
| **[`libjemalloc`](docs/make/libjemalloc.md)** 5.3.0 | General-purpose allocator replacing uClibc malloc; required by aria2 to avoid SIGFPE on MIPS/uClibc-1.0.57. | EVO only |
| **[`LMDB`](docs/make/lmdb.md)** 0.9.33 | Lightning Memory-Mapped Database shared library (`liblmdb`) for compact embedded key/value storage without a separate daemon. | EVO only |
| **[`libtcmalloc_minimal`](docs/make/libtcmalloc_minimal.md)** (gperftools) | Thread-caching allocator from gperftools; low-overhead alternative to the system allocator. | EVO only |
| **[`libprofiler`](docs/make/libprofiler.md)** (gperftools) | CPU profiler from gperftools; co-installed with libtcmalloc_minimal. | EVO only |
| **[`libssl`](docs/make/openssl.md)** (OpenSSL) | OpenSSL SSL/TLS library; legacy provider module `legacy.so` added for OpenSSL 3.x compatibility (deprecated algorithms via provider API). | EVO only |
| **[`openlibm`](docs/make/openlibm.md)** | Portable standalone C math library (`libopenlibm.so`) for consistent libm behavior across platforms and toolchains. | EVO only |
| **[`tinycdb`](docs/make/tinycdb.md)** 0.81 | Compact constant-database library exporting `libcdb` for read-mostly key/value lookups and TinyDNS-style consumers. | EVO only |
| **[`tflite-micro`](docs/make/tflite-micro.md)** (TFLM) 20260318 | TensorFlow Lite for Microcontrollers: static library (`libtflm.a`) for on-device ML inference. Builds the full TFLM kernel set (conv2d, depthwise conv, LSTM, softmax, fully connected, etc.) from the official flat-source-tree generator. | EVO only |
| **[`llama.cpp`](docs/make/llama-cpp.md)** b8575 | CPU-only LLM inference engine for running quantized GGUF language models on-device (no GPU). Includes `llama-cli` (interactive inference), `llama-server` (OpenAI-compatible REST API on port 8080), `llama-quantize` (model quantization), and optional tools (`llama-bench`, `llama-perplexity`, `llama-tokenize`, `llama-imatrix`, `llama-gguf-split`, `llama-tts`, `llama-mtmd-cli`). Models stored on USB/NAS storage. Shared libraries (`libllama.so`, `libggml*.so`). | EVO only |
| **[`yaml-cpp`](docs/make/yaml-cpp.md)** 0.8.0 | C++ YAML parser/emitter library exporting `libyaml-cpp` for configuration-driven C++ packages such as PowerDNS `geoip` and `ixfrdist`. | EVO only |

For a full description of `freetz_proxy`, see [docs/make/freetz-proxy.md](docs/make/freetz-proxy.md).

#### Python 2 third-party modules fix

Added python-pip for python2. All 13 `python-*` cross-compilation modules (`python-bjoern`, `python-cffi`, `python-cheetah`,
`python-pycurl`, `python-pycryptodome`, `python-pyopenssl`, etc.) were broken during cross-compilation
due to missing environment variables. Freetz-EVO fixes `python-module-macros.mk.in` by properly
setting `CC`, `CXX`, `LDSHARED`, `CFLAGS`, `PYTHONPATH`, and `build_ext --library-dirs` to point
to the target staging directory instead of the host.

#### Enhanced packages

| Package | Enhancement |
|---|---|
| **curl** | Added CA-bundle toggle option; rTorrent uses the curl CA bundle for HTTPS validation. |
| **busybox** (`httpd`) | Added support for HTTP `Range` header handling for CGI responses, enabling partial-content workflows with CGI-backed endpoints. |
| **pcre** | Fixed parallel install race condition; removed stray dev/test files; fixed double-indirection via `$(PKG)` causing stray root symlinks; JIT disabled for kernel 2.6.39.3. |
| **pcre2** / libpcre2-posix | Added `select FREETZ_LIB_libpcre2_posix` to `FREETZ_LIB_libpcre2` (posix wrapper is always built alongside pcre2-8); `EXTERNAL_FREETZ_LIB_libpcre2_posix` changed to `default y` so `libpcre2-posix.so.3.0.7` is automatically externalized. |
| **libyaml** | Fixed broken `find "$FILESYSTEM_MOD_DIR/..."` pattern in `external.files` (replaced with `${FREETZ_LIBRARY_DIR}/libyaml-0.so.2.0.9`, matching the working pcre2 approach); `EXTERNAL_FREETZ_LIB_libyaml` changed to `default y` so it is auto-enabled when libyaml is selected. |
| **iptables** | Fixed missing `$` in `external.files` for `VERSION_KERNEL4` conditions, preventing broken externalization. |
| **ffmpeg** | Fixed missing `$` in `external.files` for `VERSION_ABANDON` condition, preventing broken externalization. |
| **fwmod** | Augmented `Module.symvers` with inter-module CRC symbols before the `depmod` check; pre-existing AVM inter-module symbol version disagreements are now ignored to avoid false build failures. |
| **p7zip** | Uses `FREETZ_RPATH` for correct library path at runtime (merged upstream as PR #1433). |
| **socat** | Fixed `posix_memalign` for old uClibc; added VSOCK compatibility for kernels < 4.8 (merged upstream). |
| **bzip2** | Library porting for PHP dependency chain (merged upstream). |
| **sqlite** | Disabled math functions for uClibc 0.9.28/29 compatibility (merged upstream as PR #1346). |
| **iconv** / libiconv | Forced ABANDON version for uClibc 0.9.28 compatibility. |
| **unrar** | Variable naming fix and version bump (merged upstream as PR #1384). |
| **patchelf** | Synced host and target tools; used for RPATH fixing in Python and GCC toolchain. |
| **binutils** | Fixed RPATH; disabled for armeb; c++filt / elfedit added (merged upstream). |
| **ldd** | Bumped to version matching current uClibc toolchain (merged upstream). |
| **RRDTool** | aarch64 support; no border fix for v1.2; no v1.2 without libart_lgpl (merged upstream). |
| **libatomic** | Externalization with dynamic versioning for PHP dependency (merged upstream). |
| **PSL** (libpsl) | Uses crosscompiling Python tool instead of host Python. |
| **glib2** | Meson cross-build fixes: normalized cross-file tool keys and forced host Python for Meson internal generators to avoid target `python3` execution. |

#### CI / tooling

| Feature | Description |
|---|---|
| **make_package workflow** | Advanced GitHub Actions workflow for per-package build testing with matrix parallelism and detailed failure diagnostics. |
| **sync-upstream workflow** | Automated workflow to merge upstream Freetz-NG changes into Freetz-EVO on a schedule. |
| **AI translation** | Automatic translation of web UI labels to foreign languages via LLM, with curated override cache. |
| **ssh_firmware_update.py** | Python tool to flash a Freetz firmware image to a FRITZ!Box over SSH/SCP, emulating the web update process with interactive/batch modes, progress bars, dry-run and debug options. Merged upstream. |
| **make_progress_monitor.sh** | Bash script to monitor Freetz cross-compilation build progress in real time (run alongside `make` in a second terminal). Merged upstream. |
| **sync-upstream-manual.sh** | Interactive script to merge upstream Freetz-NG changes into Freetz-EVO on demand, with `--dry-run`, `--diff`, and `--log` modes. See [docs/SYNC_UPSTREAM.md](docs/SYNC_UPSTREAM.md). |

---

### Basic infos:
  * A web interface will be started on [port :81](http://fritz.box:81/), credentials: `admin`/`freetz`<br>
  * Default credentials for shell/ssh/telnet access are: `root`/`freetz`<br>
  * For more see: [ircama.github.io/freetz-evo](https://ircama.github.io/freetz-evo/)

### Requirements:
  * You need an up to date Linux System with some [prerequisites](docs/prerequisites/README.md).
  * Or download a ready-to-use VM like Gismotro's [Freetz-Linux](https://freetz.digital-eliteboard.com/?dir=Teamserver/Freetz/Freetz-VM/VirtualBox/) (user & pass: `freetz`).
  * There are also Docker images available like [pfichtner-freetz](https://hub.docker.com/r/pfichtner/freetz) ([README](https://github.com/pfichtner/pfichtner-freetz#readme)).

### Clone the main branch:
```bash
  git clone https://github.com/Ircama/freetz-evo ~/freetz-evo
```

### Or clone a single [tag](../../tags):
```bash
  git clone https://github.com/Ircama/freetz-evo ~/freetz-evo --single-branch --branch TAGNAME
```

### Install prerequisites:
```bash
  cd ~/freetz-evo
  tools/prerequisites install # -y
```

### Build firmware:
```bash
  cd ~/freetz-evo
  make menuconfig
  make
  # make help
```

### Flash firmware:
```bash
  cd ~/freetz-evo
  tools/push_firmware -h
```

### Update freetz firmware via SSH:
```bash
  cd ~/freetz-evo
  tools/ssh_firmware_update.py --host <myIP> --password <myPassword> --batch
```

### Show GIT states:
```bash
  git status
  git diff --no-prefix # --cached # > file.patch
  git log --graph # --oneline
```

### Delete local changes:
```bash
  git checkout master ; git fetch --all --prune ; git reset --hard origin/HEAD ; git clean -fd
```

### Update GIT:
```bash
  git pull
```

### Sync with upstream Freetz-NG:
```bash
  tools/sync-upstream-manual.sh              # interactive merge
  tools/sync-upstream-manual.sh --log        # show pending upstream commits
  tools/sync-upstream-manual.sh --diff       # show diff with upstream
  tools/sync-upstream-manual.sh --dry-run    # test merge without pushing
```
See [docs/SYNC_UPSTREAM.md](docs/SYNC_UPSTREAM.md) for full details.

### Checkout old revision:
```bash
  git checkout HASH-OF-COMMIT # -b NEW-BRANCH
```
### Checkout another branch:
```bash
  git checkout EXISTING-BRANCH
```

### Mirrors:
```bash
  git clone https://github.com/Ircama/freetz-evo ~/freetz-evo
```

### Documentation:
See [https://ircama.github.io/freetz-evo/](https://ircama.github.io/freetz-evo/) (or [docs/](docs/README.md)).

#### Testing Documentation changes
```bash
  cd ~/freetz-evo
  tools/zensical_httpserver.sh
```

---

> **Language**: This repository uses **English** as its primary language for code, documentation, commit messages, and issues.

---

## License

This repository contains two distinct components under different licences:

- **Freetz-NG base** (all content inherited from the upstream [Freetz-NG](https://github.com/Freetz-NG/freetz-ng) project) is licensed under the **GNU General Public License v2.0 (GPL-2.0)**. See [COPYING](COPYING) for the full GPL-2.0 text.

- **Freetz-EVO extensions** (all additions, modifications, and new packages introduced by this fork) are licensed under the **European Union Public Licence v1.2 (EUPL-1.2)**. See [LICENSE](LICENSE) for the full EUPL-1.2 text.

- **Reuse of Freetz-EVO-original files**: when files that are original to Freetz-EVO (e.g., package makefiles or other code not derived from upstream [Freetz-NG](https://github.com/Freetz-NG/freetz-ng)) are reused in other projects, including upstream, their licence remains **EUPL-1.2**. Reusers should keep the original copyright/licence notices and clearly indicate that those specific files are under EUPL-1.2.

The EUPL-1.2 and GPL-2.0 are explicitly compatible: the EUPL-1.2 Appendix lists GPL v.2 as a *Compatible Licence* under Article 5. When distributing the combined work, it may be distributed under the terms of the GPL-2.0 via the EUPL-1.2 compatibility clause.
