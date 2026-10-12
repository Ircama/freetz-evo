# Freetz-EVO — Package Reference

This page lists all packages, libraries, and tooling additions in Freetz-EVO, organized into three sections: new packages (EVO-only or significantly extended), enhanced packages (improvements to existing Freetz-NG packages), and CI/tooling additions.

For deeper coverage of specific areas, see also:

- [Audio Subsystem](AUDIO.md) — ALSA stack, MPD ecosystem, USB DAC, AirPlay
- [Home Automation](HOME-AUTOMATION.md) — Domoticz, Matter (Node-free), Thread, MQTT, 433 MHz, Home Assistant
- [Matter](MATTER.md) — protocol, Node-free architecture, verification results
- [Disk Management](DISK-MGMT.md) — Disk Management CGI, partition tools, cloning, recovery
- [Multimedia](MULTIMEDIA.md) — torrent clients, elFinder, Gerbera UPnP/DLNA, miniupnpd
- [Rust](RUST.md) — rust-host, 650-rust-cargo.mk, Rust package collection
- [Go](GO.md) — go-host, Go cross-compilation, Go package collection
- [Python](PYTHON.md) — Python 3.14, 70+ packages, tkinter/X11, Home Assistant
- [EVO Skin](EVO-SKIN.md) — responsive UI, dark mode, PWA, session login, freetz_proxy

---

## New packages

| Package | Description | Status |
|---|---|---|
| **[`Disk tools`](make/disk-mgmt.md)** | Complete storage toolkit centered on the **[Disk Management Web UI](make/disk-mgmt.md)** (`disk-mgmt-cgi`), a web console for partitioning, formatting, cloning, recovery, and disk diagnostics; backed by `parted`, `util-linux`, `gptfdisk`, `e2fsprogs`, `dosfstools`, `exfatprogs`, `ntfs-3g`, `fatresize`, `partclone`, `ddrescue`, `smartmontools`, `hdparm`, `testdisk`, `fsarchiver`, `clonezilla`, and `udpcast`. | EVO only |
| **[`util-linux`](make/util-linux.md)** | Dual-version support (2.27.1 / 2.41) with Disk Tools category and utilities like `lsblk`, `fdisk`, `blkid`. | upstream has 2.27.1; EVO adds 2.41 |
| **[`ncdu`](make/ncdu.md)** 1.19 | NCurses disk usage analyzer for quick inspection of storage usage on mounted filesystems. | EVO only |
| **[`ncdu CGI`](make/ncdu-cgi.md)** (`ncdu-cgi`) | Web frontend for ncdu integrated into the Freetz configuration pages for browser-based usage analysis. | EVO only |
| **[`ALSA / USB audio kernel support`](make/alsa-usb-audio-kernel-support.md)** | Exposes `soundcore`, `snd`, `snd-timer`, `snd-pcm`, `snd-hwdep`, `snd-rawmidi`, `snd-usbmidi-lib`, and `snd-usb-audio` in menuconfig on compatible targets. | EVO only |
| **[`alsa-utils`](make/alsa-utils.md)** 1.2.13 / **[`alsa-lib`](make/alsa-lib.md)** 1.2.13 | ALSA userspace toolchain and runtime library for playback, capture, mixer control, MIDI/sequencer tools, and `/usr/share/alsa` configuration data; both support external deployment. | EVO only |
| **[`alsaequal`](make/alsaequal.md)** 0.7.1 | ALSA equalizer bridge exposing LADSPA EQ plugins as standard ALSA PCM/control devices; optional Freetz config/status web UI via `alsaequal-cgi`. | EVO only |
| **[`alsa-plugins`](make/alsa-plugins.md)** 1.2.12 | ALSA output and rate conversion plugins (samplerate, speexrate, lavrate) for extending PCM capability | EVO only |
| **[`caps-ladspa`](make/caps-ladspa.md)** 1.0 | CAPS LADSPA plugin suite: amplifiers, equalizers, delays, reverbs, and modulation audio effects | EVO only |
| **[`cmus`](make/cmus.md)** 2.11.0 | Ncurses music player with ALSA output and MP3/FLAC/Vorbis playback. | EVO only |
| **[`go-librespot`](make/go-librespot.md)** 0.7.1 | Spotify Connect audio daemon cross-compiled from upstream Go sources with CGO, using ALSA output plus FLAC and Ogg/Vorbis support; optional Freetz config/status web UI via `go-librespot-cgi`. | EVO only |
| **[`ncspot`](make/ncspot.md)** 1.3.4 | Terminal Spotify client built from upstream Rust sources with ALSA playback and crossterm UI backend, packaged for target-side interactive use. | EVO only |
| **[`MPD`](make/mpd.md)** 0.24.13 | Music Player Daemon with local database, TCP control interface, UNIX socket, ALSA output, and MP3/FLAC/Vorbis decoding; optional Freetz config/status web UI via `mpd-cgi`. | EVO only |
| **[`libmpdclient`](make/libmpdclient.md)** 2.22 | Official MPD client library packaged as a shared runtime for target-side MPD frontends; includes Freetz defaults for `localhost`, port `6600`, and `/var/run/mpd/socket`. | EVO only |
| **[`mpc`](make/mpd-mpc.md)** 0.35 (`mpd-mpc`) | Minimal MPD command-line client using shared `libmpdclient`; suitable for shell scripts, SSH sessions, and queue/player control against local or remote MPD servers. | EVO only |
| **[`myMPD`](make/mympd.md)** 25.0.2 | Standalone lightweight web-based MPD client with embedded web assets and embedded `libmpdclient`; optional Freetz config/status web UI via `mympd-cgi`. | EVO only |
| **[`ncmpc`](make/ncmpc.md)** 0.52 | Official ncurses client for MPD with library browser, playlist editor, search, lyrics screen, key bindings help, output configuration, and mouse support; optional iconv, LIRC, NLS, and PCRE2 regex support. | EVO only |
| **[`ncmpcpp`](make/ncmpcpp.md)** 0.10.1 | Feature-rich ncurses MPD client with tag editor, media library, playlist management, search, clock, outputs screen, visualizer, and Boost-backed configuration parsing; depends on `libmpdclient`, `ncursesw`, `curl`, `taglib`. | EVO only |
| **[`rmpc`](make/rmpc.md)** 0.11.0 | Beautiful, configurable TUI client for MPD written in Rust with album art, lyrics, and playlist management; built from upstream Rust sources via cross-compiled Cargo. | EVO only |
| **[`shairport-sync`](make/shairport-sync.md)** 5.0.4 | AirPlay receiver with ALSA output, metadata FIFO processing, and a Freetz config/status web UI. | EVO only |
| **[`snapcast`](make/snapcast.md)** 0.35.0 | Multiroom audio server/client package with `snapserver`, `snapclient`, ALSA output, and FLAC/Ogg/Vorbis support. | EVO only |
| **[`SoX`](make/sox.md)** 14.4.2 | Sound eXchange — command-line audio converter, player, and recorder with multi-format and effect support | EVO only |
| **[`Gerbera`](make/gerbera.md)** 3.2.1 | UPnP/DLNA media server with content directory, transcoding, and metadata extraction; includes CGI web config editor with ACE editor and setup wizard | EVO only |
| **[`miniupnpd`](make/miniupnpd.md)** 2.3.10 | Lightweight UPnP-IGD daemon for automatic port forwarding via UPnP | EVO only |
| **[`btop`](make/btop.md)** 1.4.7 | Modern terminal resource monitor for CPU, memory, disks, network, and processes, with optional upstream themes. | EVO only |
| **[`nmon`](make/nmon.md)** 16s | Curses-based Linux performance monitor for CPU, memory, disks, network, filesystems, and processes, with optional capture-to-file mode for later analysis. | EVO only |
| **[`wavemon`](make/wavemon.md)** 0.9.7 | Ncurses wireless monitor for signal quality, bitrate, channels, and interface statistics. | EVO only |
| **[`cdc-acm` kernel driver](make/cdc-acm.md)** | Exposes `cdc-acm.ko` in menuconfig on compatible targets, enabling native USB CDC ACM serial devices such as ESP32-C3 boards and other USB serial gadgets. | EVO only |
| **[`avrdude`](make/avrdude.md)** 8.1 | AVR downloader/uploader toolchain with `avrdude`, `elf2tag`, and default `/etc/avrdude.conf` for full AVR flash/program workflows. | EVO only |
| **[`esp-serial-flasher`](make/esp-serial-flasher.md)** git-f1cccac | ESP serial flashing toolkit shipping `linux_flasher` and `esp_fw_upload` for multi-image ESP32-family firmware upload layouts. | EVO only |
| **[`micronucleus`](make/micronucleus.md)** 2.6 | USB bootloader uploader for Digispark/ATTiny devices using Micronucleus (`/usr/bin/micronucleus`). | EVO only |
| **[`telink_tools`](make/telink_tools.md)** 1.0 | Native C Telink BLE bootloader CLI for TB-03F-KIT/TB-04-KIT style devices; supports burn, triad programming, and flash read/write/erase operations. | EVO only |
| **[`ja11-config`](make/ja11-config.md)** 1.0 | FiiO JA11 / KT02H20 tool set: `ja11-config-tui` (5-band parametric EQ, DAC digital filters, global preamp gain, preset management, persistent flash save, i18n EN/IT), `ja11-boot` (enter firmware-update mode), and `ja11-flash` (firmware flashing over the update-mode serial port). | EVO only |
| **[`rtl_433`](make/rtl_433.md)** 25.12 | Generic ISM-band data receiver decoding 433.92/868/315/345/915 MHz transmissions from wireless sensors, weather stations, TPMS, and remotes via an RTL-SDR dongle; depends on the new `rtl-sdr` library (`librtlsdr`). | EVO only |
| **[`rtl-sdr`](make/rtl-sdr.md)** 2.0.3 | `librtlsdr` shared library turning a Realtek RTL2832U DVB-T dongle into an SDR receiver; used by `rtl_433`. | EVO only |
| **[`soapysdr`](make/soapysdr.md)** 0.8.1 | `libSoapySDR` vendor and platform neutral SDR support library/API; hardware support comes from separately installed modules (e.g. `soapyrtlsdr`) below `/usr/lib/SoapySDR/modules0.8`; used by `rtl_433`. | EVO only |
| **[`soapyrtlsdr`](make/soapyrtlsdr.md)** 0.3.3 | SoapySDR hardware module for RTL2832U based dongles, installed as `/usr/lib/SoapySDR/modules0.8/libsoapyrtlsdr.so`; lets `rtl_433` (and other SoapySDR clients) reach an RTL-SDR stick through the SoapySDR API. | EVO only |
| **[`tuyapp`](make/tuyapp.md)** git-5a3a462 | C++ client library for the **Local Tuya API** shipped with five CLI clients (`tuya_switch`, `tuya_status`, `tuya_kwh_meter`, `tuya_multi_kwh_meter`, `tuya_monitor_and_control`) that talk to Tuya devices directly on the LAN; supports protocol versions 3.3/3.4/3.5 and reads credentials from `tuya-devices.json`. | EVO only |
| **[`tuya-iot-core-sdk`](make/tuya-iot-core-sdk.md)** git-0208bad | Tuya IoT Core SDK for C: MQTT/TLS client for the **Tuya Cloud** (bundled mbedTLS, coreMQTT, coreJSON, coreHTTP) shipped as four demo binaries (`custom_protocol_basic_demo`, `data_model_basic_demo`, `ota_basic_demo`, `subdevice_basic_demo`); device credentials are read from the environment. | EVO only |
| **[`lazygit`](make/lazygit.md)** 0.61.1 | Full-screen terminal UI for Git repositories. | EVO only |
| **[`neovim`](make/neovim.md)** 0.12.2 | Modern terminal-based text editor, fork of Vim with Lua scripting, built-in LSP client, and tree-sitter syntax highlighting; cross-compiled with CMake and Ninja | EVO only |
| **[`lf`](make/lf.md)** r41 | Terminal file manager with a Miller-column layout, keyboard-driven navigation, and customizable key bindings. Built with Go cross-compilation. | EVO only |
| **[`age`](make/age.md)** 1.3.1 | Modern file encryption tool. | EVO only |
| **[`caddy`](make/caddy.md)** 2.11.2 | General-purpose web server and reverse proxy with automatic HTTPS capabilities. | EVO only |
| **[`fzf`](make/fzf.md)** 0.72.0 | Command-line fuzzy finder for interactive shell filtering. | EVO only |
| **[`ripgrep`](make/ripgrep.md)** 15.1.0 | Ultra-fast text search tool built from Rust sources with cross-compilation support; recursively searches file contents with grep-compatible patterns | EVO only |
| **[`glow`](make/glow.md)** 2.1.2 | Terminal Markdown renderer for browsing README files and notes. | EVO only |
| **[`gum`](make/gum.md)** 0.17.0 | Terminal UI helper toolkit for shell scripts. | EVO only |
| **[`hey`](make/hey.md)** 0.1.5 | Small HTTP load generator for smoke tests and benchmarks. | EVO only |
| **[`hugo`](make/hugo.md)** 0.161.1 | Static site generator for content trees stored on writable media. | EVO only |
| **[`prometheus`](make/prometheus.md)** 3.11.3 | Monitoring and alerting server with local TSDB storage. | EVO only |
| **[`rclone`](make/rclone.md)** 1.74.1 | Cloud and remote storage synchronization tool. | EVO only |
| **[`bat`](make/bat.md)** 0.26.1 | Syntax-highlighting `cat` replacement for reading config files, logs, and source files directly on the device. | EVO only |
| **[`bottom`](make/bottom.md)** 0.12.3 | Terminal system monitor (`btm`) for CPU, memory, disk, network, and process metrics. | EVO only |
| **[`bandwhich`](make/bandwhich.md)** 0.23.1 | Terminal bandwidth utilization monitor by process/connection. | EVO only |
| **[`procs`](make/procs.md)** 0.14.11 | Modern process viewer as an enhanced alternative to `ps`. | EVO only |
| **[`broot`](make/broot.md)** 1.56.4 | Tree-style terminal file browser and launcher. | EVO only |
| **[`eza`](make/eza.md)** 0.23.4 | Modern `ls` replacement with richer directory listings, colors, and tree-style output. | EVO only |
| **[`gitui`](make/gitui.md)** 0.28.1 | Terminal UI for interactive Git workflows. | EVO only |
| **[`jless`](make/jless.md)** 0.9.0 | JSON pager/reader with interactive navigation and search. | EVO only |
| **[`lnav-rs`](make/lnav-rs.md)** 0.9.0 | Rust-based log/JSON pager package (alias build based on `jless`). | EVO only |
| **[`lnav`](make/lnav.md)** 0.14.0 | Advanced terminal log viewer and analyzer with optional Rust/PRQL extensions exposed in menuconfig and support for external deployment. | EVO only |
| **[`sha256sum`](make/sha256sum.md)** 0.9.0 | SHA-256 checksum utility packaged from uutils/coreutils for target-side integrity verification. | EVO only |
| **[`tac`](make/tac.md)** 0.9.0 | Reverse concatenation utility packaged from uutils/coreutils for target-side text processing workflows. | EVO only |
| **[`termscp`](make/termscp.md)** 1.0.0 | Terminal SCP/SFTP client and remote file browser. | EVO only |
| **[`rainfrog`](make/rainfrog.md)** 0.3.18 | Terminal database explorer and query tool for SQLite (via `sqlx`), built from Rust sources | EVO only |
| **[`atuin`](make/atuin.md)** 18.16.1 | Shell history synchronization and improved history search utility. | EVO only |
| **[`oxker`](make/oxker.md)** 0.13.2 | Terminal Docker container monitor/manager UI. | EVO only |
| **[`yazi`](make/yazi.md)** 26.5.6 | Fast terminal file manager package shipping `yazi` and helper `ya`. | EVO only |
| **[`zoxide`](make/zoxide.md)** 0.9.9 | Smarter directory-jump helper that complements interactive shells with ranked path lookup. | EVO only |
| **[`restic`](make/restic.md)** 0.18.1 | Encrypted backup tool for local and remote repositories. | EVO only |
| **[`vhs`](make/vhs.md)** 0.11.0 | Scripted terminal-session recorder for demo generation. | EVO only |
| **[`NeoMutt`](make/neomutt.md)** 20260504 | Console email client (MUA) with IMAP/POP3/SMTP, SSL/TLS via OpenSSL, wide-character ncurses UI, threading, sidebar, and a rich `muttrc` scripting language. | EVO only |
| **[`yq`](make/yq.md)** 4.53.2 | YAML, JSON, and XML processor for config automation. | EVO only |
| **[`ttyd`](make/ttyd.md)** 1.7.7 | Web-based terminal server: exposes any shell command over WebSocket; CGI page embeds a full xterm.js terminal with 7 themes, fullscreen, search, font-size controls, and canvas renderer. | EVO only |
| **[`aria2`](make/aria2.md)** / **AriaNg** | Multi-protocol download utility (HTTP, FTP, BitTorrent, Metalink) with a full web UI (AriaNg) and CGI integration. | EVO only |
| **[`rTorrent`](make/rtorrent.md)** 0.16.7 / **[`ruTorrent`](make/rutorrent.md)** 5.2.10 | Feature-rich BitTorrent client with a complete web interface, CGI backend, and config editor. | EVO only |
| **[`aMUTorrent`](make/amutorrent.md)** 3.5.0 | Experimental torrent client with full Node.js backend and Express/WebSocket frontend. Bootstrap preconfigures local rTorrent via SCGI. DEVELOPER only. | EVO only |
| **[`transmission`](make/transmission.md)** | Added integrated static frontend selectors in the Transmission submenu (`flood-for-transmission` 1.0.1, `TrguiNG web` 1.5.1, `Transmissionic web UI` 1.8.0, `transmission-web-control` commit snapshot), with package-level installation under `/usr/mww/*`; all available as selectable static frontends integrated in the Transmission package menu. | EVO only |
| **[`freetz_proxy`](make/freetz-proxy.md)** | Lightweight CGI HTTPS↔HTTP reverse proxy and index gateway, with HTML/CSS/JS URL rewriting and CDN proxying. Accessible via MyFRITZ! and from the internet without port-forwarding. When included, the Fritz logo and the AVM user menu gain direct links to the Freetz menus (through the proxy). | EVO only |
| **[`melcloud`](make/melcloud.md)** | MELCloud integration package with daemon, init script, CGI endpoint, and web UI for Mitsubishi Electric devices. | EVO only |
| **[`Nginx`](make/nginx.md)** 1.29 | High-performance HTTP/reverse-proxy server with MIPS/ARM cross-compilation fixes and optional externalization. | EVO only |
| **[`krb5`](make/krb5.md)** | MIT Kerberos/GSSAPI runtime libraries (`libkrb5`, `libgssapi_krb5`) for target packages requiring Kerberos authentication features. | EVO only |
| **[`OpenLDAP`](make/openldap.md)** 2.6.8 | Client-library package exporting `liblber` and `libldap` for target-side LDAP consumers; server-side slapd pieces are intentionally not built. | EVO only |
| **[`PostgreSQL`](make/postgresql.md)** 16.3 | PostgreSQL package exporting `libpq` for target-side SQL consumers and optionally installing minimal server binaries (`postgres`, `pg_ctl`, `initdb`). | EVO only |
| **[`pdns-authoritative`](make/pdns-authoritative.md)** 5.0.5 | PowerDNS Authoritative Server port with optional `pdnsutil`, `pdns_control`, `zone2sql`, `zone2json`, `ixfrdist`, diagnostic tools, externalization support, selectable OpenSSL/GnuTLS DNS-over-TLS, optional libsodium and remote ZeroMQ support, and selectable `bind`/`pipe`/`godbc`/`gmysql`/`gpgsql`/`gsqlite3`/`geoip`/`lmdb`/`lua2`/`remote`/`tinydns` backends. Requires modern targets because upstream PowerDNS 5 needs GCC 8+ / C++17. | EVO only |
| **[`pdns-dnsdist`](make/pdns-dnsdist.md)** 1.9.7 | DNS load-balancer/front-end from the PowerDNS suite, useful for policy routing, load balancing, and DNS traffic filtering. | EVO only |
| **[`pdns-recursor`](make/pdns-recursor.md)** 5.3.4 | Recursive DNS resolver daemon from the PowerDNS suite, packaged separately from authoritative and dnsdist components. | EVO only |
| **[`unixODBC`](make/unixodbc.md)** 2.3.12 | ODBC driver-manager library package exporting `libodbc`, `libodbcinst`, and `libodbccr` for target-side database consumers such as PowerDNS `godbc`. | EVO only |
| **[`PHP`](make/php.md)** 8.4 / 8.5 | Modern PHP interpreter with multi-version selection (5.6 legacy, 8.4, 8.5), bzip2, libxml2, libatomic support. | upstream has PHP 5.6 only |
| **[`QuickJS`](make/quickjs.md)** (2026-03-23 git snapshot) | Lightweight embeddable JavaScript engine, packaged with `qjs` and optional `qjsc` compiler support. | EVO only |
| **[`Python 3.14`](make/python3.md)** | Python 3.14.3 with zip-importer fix, patchelf RPATH support, and build scripts for external deployment. | upstream has 3.14 too |
| **[`MicroPython`](make/micropython.md)** 1.27.0 | Lightweight Python implementation for constrained environments, including REPL, script execution, and optional micropython-lib modules. | EVO only |
| **[`python3-cryptography`](make/python3-cryptography.md)** 48.0.0 | Python cryptography package with OpenSSL bindings and Rust-backed components, built for target using cross-compiled Rust/Cargo support. | EVO only |
| **[`python3-ulid-transform`](make/python3-ulid-transform.md)** 2.2.9 | ULID creation/transformation module built via pyproject/pip with Rust/Cargo cross-build support. | EVO only |
| **[`python3-uv`](make/python3-uv.md)** 0.11.16 | Rust-based Python package/project manager built via pyproject/pip (`maturin`) with Rust/Cargo cross-build target support. | EVO only |
| **[`python3-*`](make/python3.md)** (64 modules) | New Python 3 third-party packages — see [Python](PYTHON.md) for the full list. | EVO only |
| **[`GitHub CLI`](make/gh.md)** (`gh`) 2.83.2 | GitHub CLI tool with Go host-tool integration, allowing GitHub API interaction from the FritzBox. | EVO only |
| **[`GNU ddrescue`](make/ddrescue.md)** 1.30 | Resilient data recovery and block-copy utility with mapfile-based resume support. | EVO only |
| **[`exfatprogs`](make/exfatprogs.md)** 1.3.2 | User-space exFAT utilities for formatting, checking, labeling, and tuning exFAT filesystems. | EVO only |
| **[`f2fs-tools`](make/f2fs-tools.md)** 1.9.0 | Flash-Friendly File System utilities: `mkfs.f2fs`, `fsck.f2fs`, `dump.f2fs` for managing F2FS filesystems | EVO only |
| **[`fatresize`](make/fatresize.md)** (snapshot) | FAT16/FAT32 resize utility for non-destructive partition resizing tasks. | EVO only |
| **[`fsarchiver`](make/fsarchiver.md)** 0.8.9 | Filesystem-level backup and restore archiver with compressed image support. | EVO only |
| **[`partclone`](make/partclone.md)** 0.3.31 | Block-level partition backup/restore/check tools frequently used in cloning workflows. | EVO only |
| **[`testdisk`](make/testdisk.md)** 7.2 | Partition and file recovery toolkit for damaged media and lost partition tables. | EVO only |
| **[`udpcast`](make/udpcast.md)** 20250223 | Multicast transfer utility for one-to-many image distribution in cloning operations. | EVO only |
| **[`elFinder`](make/elfinder.md)** 2.1.66 | Full-featured web-based file manager for the FritzBox with enhancements: drag-and-drop UI, PHP connector (squashfs-safe), FTP remote volumes, video preview, Movie plugin, MediaInfo plugin, VLC plugin, unrar/7-Zip support, optional themes, multilingual (de/en/it/…), better status bar. | EVO only |
| **[`MediaInfo`](make/mediainfo.md)** / libmediainfo / libzen / libxmlrpc | Media file analysis tool with full library stack; reports codecs, bitrates, resolution, and metadata. | EVO only |
| **[`proc-ps`](make/procps-ng.md)** | Improved `ps` replacement backed by procps-ng with richer process information output. | merged upstream |
| **[`cpulimit`](make/cpulimit.md)** 0.2 | Limits the CPU usage of a process to a given percentage; prevents runaway processes from overloading the device. | package improvement |
| **[`microperl`](make/microperl.md)** 5.38 | Minimal Perl 5.38.2 interpreter (alongside legacy 5.10.1) with full stub library set for embedded use. | upstream has 5.10.1; EVO adds 5.38.2 |
| **[`zip`](make/infozip.md)** 3.0 (infozip) | Standard `zip` archiver for creating ZIP archives directly on the device. | merged upstream |
| **[`gdb`](make/gdb.md)** 17.1 | GNU Debugger version 17.1 for on-device debugging of binaries and crash analysis. | EVO only for 17.1 (upstream has 6.8/7.9.1) |
| **[`valgrind`](make/valgrind.md)** 3.27.0 | Dynamic analysis framework for memory debugging, leak detection, and profiling; requires kernel 3.x+ | EVO only |
| **[`patchelf`](make/patchelf.md)** (target) | ELF binary patcher for fixing RPATH and dynamic linker paths on cross-compiled binaries. | merged upstream |
| **[`binutils-tools`](make/binutils-tools.md)** (`c++filt`, `elfedit`, `nm`, `objdump`) | Additional binutils utilities for binary inspection and symbol demangling on the device. | merged upstream |
| **[`autotools`](make/autotools.md)** 2.72 | GNU Autoconf, Automake, and Libtool on-device for building configure-based source packages directly on the target. DEVELOPER only. | EVO only |
| **[`libnettle`](make/libnettle.md)** | Low-level cryptographic library (AES, SHA, RSA) used by GnuTLS and other packages. | upstream has nettle |
| **[`libzen`](make/libzen.md)** | Helper library required by MediaInfo for portable C++ utilities. | EVO only |
| **[`libxmlrpc`](make/libxmlrpc.md)** | XML-RPC library for rTorrent's SCGI/RPC interface; host tool gennmtab moved to `make/host-tools`. | EVO only |
| **[`libwebsockets`](make/libwebsockets.md)** 4.3.9 | Canonical C WebSocket library; optional SSL/TLS support via OpenSSL. | EVO only |
| **[`json-c`](make/json-c.md)** 0.17 | Lightweight JSON parser/serialiser library. | EVO only |
| **[`libcares`](make/libcares.md)** (c-ares) | Asynchronous DNS resolver library used by aria2 and curl. | EVO only |
| **[`libsodium`](make/libsodium.md)** 1.0.20 | Modern cryptographic library exporting `libsodium` for Ed25519 signatures, authenticated encryption, keyed hashes, and other high-level primitives. | EVO only |
| **[`libnl`](make/libnl.md)** 3.11.0 | Netlink userspace library stack (`libnl-3`, `libnl-cli-3`, `libnl-genl-3`, `libnl-nf-3`, `libnl-route-3`). | EVO only |
| **[`libzmq`](make/libzmq.md)** 4.3.5 | ZeroMQ messaging library exporting `libzmq` for asynchronous request/reply, pub/sub, and brokerless messaging patterns. | EVO only |
| **[`libjemalloc`](make/libjemalloc.md)** 5.3.0 | General-purpose allocator replacing uClibc malloc; required by aria2 to avoid SIGFPE on MIPS/uClibc-1.0.57. | EVO only |
| **[`LMDB`](make/lmdb.md)** 0.9.33 | Lightning Memory-Mapped Database shared library (`liblmdb`) for compact embedded key/value storage without a separate daemon. | EVO only |
| **[`libtcmalloc_minimal`](make/libtcmalloc_minimal.md)** (gperftools) | Thread-caching allocator from gperftools; low-overhead alternative to the system allocator. | EVO only |
| **[`libprofiler`](make/libprofiler.md)** (gperftools) | CPU profiler from gperftools; co-installed with libtcmalloc_minimal. | EVO only |
| **[`libssl`](make/openssl.md)** (OpenSSL) | OpenSSL SSL/TLS library; legacy provider module `legacy.so` added for OpenSSL 3.x compatibility (deprecated algorithms via provider API). | EVO only |
| **[`hidapi`](make/hidapi.md)** 0.15.0 | Multi-platform HID library (`libhidapi-hidraw.so`) using the Linux kernel's hidraw interface; enables applications to interface with HID-Class USB devices without libusb. Used by `ja11-config`. | EVO only |
| **[`lame`](make/lame.md)** 3.100 | High-quality MPEG Audio Layer 3 (MP3) encoding library (`libmp3lame.so`); provides the LAME encoder for audio applications needing MP3 output. | EVO only |
| **[`libixml`](make/libixml.md)** 11.1.7 | Lightweight XML parser library (`libixml.so`) distributed as part of the Portable UPnP SDK (libupnp); used by Gerbera and other UPnP applications for XML parsing. | EVO only |
| **[`lirc`](make/lirc.md)** 0.10.2 | LIRC (Linux Infrared Remote Control) client library (`liblirc_client.so`); provides infrared remote control support for applications like `ncmpc`. | EVO only |
| **[`openlibm`](make/openlibm.md)** | Portable standalone C math library (`libopenlibm.so`) for consistent libm behavior across platforms and toolchains. | EVO only |
| **[`tinycdb`](make/tinycdb.md)** 0.81 | Compact constant-database library exporting `libcdb` for read-mostly key/value lookups and TinyDNS-style consumers. | EVO only |
| **[`tflite-micro`](make/tflite-micro.md)** (TFLM) 20260318 | TensorFlow Lite for Microcontrollers: static library (`libtflm.a`) for on-device ML inference. Builds the full TFLM kernel set (conv2d, depthwise conv, LSTM, softmax, fully connected, etc.) from the official flat-source-tree generator. | EVO only |
| **[`llama.cpp`](make/llama-cpp.md)** b8575 | CPU-only LLM inference engine for running quantized GGUF language models on-device (no GPU). Includes `llama-cli` (interactive inference), `llama-server` (OpenAI-compatible REST API on port 8080), `llama-quantize` (model quantization), and optional tools (`llama-bench`, `llama-perplexity`, `llama-tokenize`, `llama-imatrix`, `llama-gguf-split`, `llama-tts`, `llama-mtmd-cli`). Models stored on USB/NAS storage. Shared libraries (`libllama.so`, `libggml*.so`). | EVO only |
| **[`yaml-cpp`](make/yaml-cpp.md)** 0.8.0 | C++ YAML parser/emitter library exporting `libyaml-cpp` for configuration-driven C++ packages such as PowerDNS `geoip` and `ixfrdist`. | EVO only |
| **[`boost`](make/boost.md)** 1.87.0 | Boost C++ libraries (`libboost_thread.so`, `libboost_system.so`) cross-built with `b2`; ships a hand-written `BoostConfig.cmake` because CMake 4 removed the `FindBoost` module. Consumed by Domoticz (Boost.Asio, Boost.Signals2, Boost.Thread). | EVO only |
| **[`Domoticz`](make/domoticz.md)** 2026.4 | Home automation system with a web interface (default port 8080) for switches, sensors, thermostats, media players and MQTT devices, with Lua/dzVents event scripts and Python plugin support. Ships a Freetz init script plus configuration for the user data folder, HTTP/HTTPS ports and the USB/NAS boot wait; the binary can be externalized because the init script passes `-approot`/`-wwwroot` explicitly. | EVO only |
| **[`OpenThread`](make/openthread.md)** 2026.10.0 | Google's implementation of the Thread protocol, built for the POSIX platform: `ot-cli` (interactive CLI, FTD/MTD), `ot-daemon` (Thread stack as a daemon) and `ot-ctl` (control client). The radio is an external 802.15.4 Radio Co-Processor (e.g. nRF52840 dongle running the OpenThread RCP firmware) reached over spinel/UART; the pinned mbedTLS submodule is fetched as a separate tarball. Depends on uClibc ≥ 1.0.58. | EVO only |
| **[`OpenThread Border Router`](make/ot-br-posix.md)** (`ot-br-posix`) 2026.10.0 | `otbr-agent` turns the box into a Thread Border Router: it owns the RCP, acts as Thread Routing Manager and advertises the border router with OpenThread's own mDNS/DNS-SD stack. Ships `/usr/sbin/otbr-agent`, `/usr/sbin/ot-ctl`, the `rc.otbr` init script and the Freetz configuration (infrastructure interface, spinel URL, log level, boot wait for the RCP device in background). All optional upstream components (D-Bus, web GUI, REST, NAT64, DHCPv6-PD, backbone router, nftables) are disabled, so no protobuf/dbus/jsoncpp/cJSON/cpp-httplib/mDNSResponder dependency is needed; it reuses the `openthread` package's source tree (upstream hardcodes the submodule path). | EVO only |
| **[`matter-bridge`](make/matter-bridge.md)** 0.1 | Native (C++, `libwebsockets` + `jsoncpp`) WebSocket server implementing the **python-matter-server JSON API** that the Domoticz Matter driver talks to on port 5580, so no Node.js is needed on the box: flat `server_info` handshake, `start_listening`/`get_nodes`, `read_attribute`, `device_command`, `write_attribute`, `attribute_updated` events and error replies, plus a JSON node/attribute store (seed in the image, state in `/mod/etc`). Ships `rc.matter-bridge`, the Freetz configuration and two runnable protocol tests (`tests/conformance-python-matter-server.py`, `tests/domoticz-driver-test.py`). **Compatibility verified** against the dataclasses/constants of `python-matter-server` 8.1.2 (`SCHEMA_VERSION=11`, `MIN_SCHEMA_VERSION=9`, `ErrorResultMessage`, `EventType.ATTRIBUTE_UPDATED`, error codes 5/8/9) and against the message dispatch of `hardware/Matter.cpp`; the tests found and fixed four wire-format defects. **Milestone 1**: the Matter controller backend (commissioning, CASE, subscriptions) is not implemented yet — such commands answer with a clear error; the store is the integration point for it. | EVO only |
| **[`Home Assistant`](make/homeassistant.md)** (`homeassistant`) 1.0 | Setup helper and autorun integration for Home Assistant on the box: ships `/usr/bin/ha-setup` (`--check`, `--install`, `--version`, `--index-url`, `--update`, `--status`, `--uninstall`), which bootstraps pip (`--with-ensurepip=no` in Freetz) and installs Home Assistant with `pip --prefix` into external storage — no `venv` module needed. Kconfig *Minimal*/*Full* profiles select the Python interpreter modules and libraries it needs (SSL, ctypes, sqlite3, multiprocessing, …), the modconf set keeps the base directory, port, PyPI mirror, nice level and boot wait configurable in the web UI, and `rc.homeassistant` autostarts the service after waiting for the storage in a background subshell. | EVO only |
| **[`freetz-matter`](make/freetz-matter.md)** (`freetz-matter`) 0.1 | Exposes the **FRITZ!Box itself as a Matter device** with no Node.js and no hub software on the box, built on the pure-Rust [`project-chip/rs-matter`](https://github.com/project-chip/rs-matter) stack (pinned revision `7d5684f`, Matter 0.4.1 API) cross-compiled for uClibc/MIPS. Endpoints: Temperature Sensor (`0x0302`/cluster `0x0402`) fed by the same sensor chain as the `box_info` page (`/proc/chip_temperature` → thermal zone → AVM power-management temperature → `/proc/avm/temp_sensors`), Smart Speaker (`0x0022` with `OnOff` + `LevelControl`) driving ALSA through `amixer` (mute/unmute + volume 1..254 → 0..100 %), and root `BasicInformation` filled with the real model, FRITZ!OS version, AVM revision and LAN MAC. Ships `/usr/bin/freetz-matter`, `rc.freetz-matter` (QR/manual pairing code in the service log while uncommissioned) and the Freetz configuration (Matter port, flash-backed fabric store in `/mod/etc`, verbosity). Three build fixes were required and two of them are now shared: a new `RUSTIX_APPLY_UCLIBC_PATCHES_LIBC_NORAW__INT` macro for rustix on the **libc backend without `linux_raw_dep`** (the combination rs-matter pulls, where `linux_raw_sys` is not linked and the ABI values must be substituted at the use sites), the existing `getrandom` syscall macro, and a memory-conservative Cargo profile (`opt-level=1`, `lto=false`, `codegen-units=256`, one cargo job, `-Zthreads=1`) because rs-matter's IDL codegen produces ~30 MB of Rust and a single `rustc` job peaks at ~5.6 GB RSS, which SIGKILLs it with the upstream fat-LTO profile on an 8 GB build host. | EVO only |
| **[`Gerbera dependency libraries`](make/gerbera.md)** | Library stack for the Gerbera UPnP media server, including `libupnp` 1.14.31 (Portable UPnP SDK), `libnpupnp` 6.3.0 (new-gen UPnP), `pugixml` 1.16 (XML processing), `spdlog` 1.17.0 (logging), `libfmt` 12.2.0 (C++ formatting), `icu` 76.1 (Unicode), `exiv2` 0.28.8 (image metadata), `libebml` 1.4.5 / `libmatroska` 1.7.1 (MKV container), `libffmpegthumbnailer` 2.2.3 (video thumbnails), `libmagic` 5.47 (file type detection), `libmicrohttpd` 0.9.77 (embedded HTTP server), and `xmlrpc` 1.64.03 (XML-RPC). All support externalization. | EVO only |
| **[`Audio libraries`](make/mpg123.md)** | Audio codec and processing libraries: `mpg123` 1.32.10 (MP3 decoder), `faad2` 2.11.1 (AAC decoder), `shine` 3.1.1 (fixed-point MP3 encoder), `tremor` (fixed-point Vorbis decoder), `libtheora` 1.1.1 (Theora video), `libsndfile` 1.2.2 (audio file I/O), `libsamplerate` 0.2.2 (sample rate conversion), `soxr` 0.1.3 (high-quality resampler), `libwavpack` 5.7.0 (WavPack compression), `libshout` 2.4.6 (Icecast streaming), `libwildmidi` 0.4.6 (MIDI playback), `fluidsynth` 2.3.5 (SoundFont MIDI synthesizer). All support externalization. | EVO only |
| **[`Data and utility libraries`](make/libarchive.md)** | Additional data handling and utility libraries: `libarchive` 3.8.2 (multi-format archive), `duktape` 2.6.0 (embeddable JS engine), `jsoncpp` 1.9.8 (JSON), `libunistring` 1.4 (Unicode strings), `libnfs` 5.0.3 (NFSv2/v3/v4 client), `jemalloc` 5.3.0 (general-purpose allocator), `libaria2` (download library, external-only), `liblastfm` 1.0.9 (Last.fm client), `caps` 0.9.26 (C++ thread-safe containers). All support externalization. | EVO only |
| **[`X11 graphics libraries`](wiki/60_Development/coding_guide.md)** | X11 client libraries providing protocol support for remote display via `DISPLAY=<host>:<screen>`. Includes: `libXau`, `libxcb`, `libX11`, `libXext`, `libICE`, `libSM`, `libXt`, `libXmu`, `libXaw`, `libXpm`, `libXfixes`, `libXi`, and header-only packages `xorgproto`, `xcb-proto`, `xtrans`, `util-macros`. Required for Python tkinter and X11 applications. | EVO only |
| **[`Tcl/Tk`](make/tcl-tk.md)** 8.6.16 | Tcl scripting library and Tk GUI toolkit, providing `libtcl8.6.so` and `libtk8.6.so`. Required by Python's tkinter module for building GUI applications displayed on a remote X11 server via `DISPLAY=<host>:<screen>`. Optional `wish` shell included with the Tk package for interactive Tk sessions (`DISPLAY=<host>:0 wish`). | EVO only |
| **[`wish`](make/wish.md)** 1.0 | Symbolic link wrapper for Tk's `wish` interpreter at `/usr/bin/wish` | EVO only |
| **[`xclock`](make/xclock.md)** 1.1.1 | X11 clock application displaying an analog or digital clock on a remote display via `DISPLAY=<host>:<screen>`. | EVO only |
| **[`xeyes`](make/xeyes.md)** 1.3.1 | X11 eyes application: a pair of eyes follow the mouse cursor on a remote display via `DISPLAY=<host>:<screen>`. | EVO only |
| **[`xterm`](make/xterm.md)** 410 | X11 terminal emulator providing a remote terminal window via `DISPLAY=<host>:<screen>`. Includes the `resize` utility for terminal size negotiation. | EVO only |

---

## Enhanced packages

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
| **mosquitto** | `libmosquitto.so` (the MQTT client library) can now be selected on its own, without the command line clients: `FREETZ_PACKAGE_MOSQUITTO_CLIENTS` is titled "libmosquitto (shared library)" and no longer requires the client tools. The library, its unversioned symlink and `mosquitto.h` are staged for dependent packages, and `WITH_HTTP_API` is turned off because the tree's libmicrohttpd 1.x no longer exports the deprecated basic-auth API (link errors otherwise). |

---

## CI / tooling

| Feature | Description |
|---|---|
| **make_package workflow** | Advanced GitHub Actions workflow for per-package build testing with matrix parallelism and detailed failure diagnostics. |
| **sync-upstream workflow** | Automated workflow to merge upstream Freetz-NG changes into Freetz-EVO on a schedule. |
| **AI translation** | Automatic translation of web UI labels to foreign languages via LLM, with curated override cache. |
| **ssh_firmware_update.py** | Python tool to flash a Freetz firmware image to a FRITZ!Box over SSH/SCP, emulating the web update process with interactive/batch modes, progress bars, dry-run and debug options. Merged upstream. |
| **sync-upstream-manual.sh** | Interactive script to merge upstream Freetz-NG changes into Freetz-EVO on demand, with `--dry-run`, `--diff`, and `--log` modes. See [docs/SYNC_UPSTREAM.md](SYNC_UPSTREAM.md). |
