# Freetz-EVO — Multimedia, Download, and Media Server

Freetz-EVO extends the standard Freetz package set with a comprehensive suite of tools for downloading, transferring, and serving media. The area covers three distinct concerns: **download and torrent clients** with modern web frontends, a **UPnP/DLNA media server** for streaming content to network devices, and **UPnP-IGD support** for automatic port-forwarding.

All relevant options are available under **Packages** in `make menuconfig`.

---

## Download and torrent tools

### rTorrent 0.16.7 with ruTorrent 5.2.10

rTorrent is a high-performance, low-footprint BitTorrent client running as a daemon, controllable over an SCGI/XML-RPC interface. Freetz-EVO ships version 0.16.7 — a significant improvement over the version available in Freetz-NG — along with a completely reworked **ruTorrent 5.2.10** web interface. ruTorrent is served via an integrated PHP backend and provides a full-featured, browser-based torrent management UI: adding/removing torrents, per-torrent priority and bandwidth settings, tracker management, file selection, RSS feeds, and plugin-based extensibility.

The ruTorrent integration in Freetz-EVO includes a CGI backend, an init script, and a dedicated configuration page in the Freetz web interface. The package depends on `libxmlrpc` for the SCGI/RPC interface and on `curl` (with CA bundle) for HTTPS tracker validation.

### aria2 with AriaNg

**aria2** is a multi-protocol, multi-source download utility supporting HTTP, HTTPS, FTP, BitTorrent, and Metalink. It can download from multiple sources simultaneously and supports segmented downloads, making it significantly faster than single-connection tools for large files. aria2 exposes a JSON-RPC and XML-RPC interface, which is consumed by the bundled **AriaNg** web frontend — a responsive, single-page application that provides a full download manager UI: adding URIs and torrent/metalink files, per-download settings, global bandwidth limits, and real-time transfer stats.

The Freetz-EVO integration provides:

- `aria2c` binary with HTTP/HTTPS, FTP, BitTorrent, and Metalink support
- `libaria2` shared library for external consumers (externalization-ready)
- The AriaNg web frontend integrated into the Freetz web interface via a CGI backend
- An init script for daemon management and a configuration page for the RPC secret, ports, and listen settings

aria2 on MIPS requires `libjemalloc` to avoid a `SIGFPE` bug in uClibc 1.0.57's allocator; `libjemalloc` is auto-selected when aria2 is enabled on affected targets.

### Transmission with multiple web frontends

Transmission is a lightweight BitTorrent client available in Freetz-NG. Freetz-EVO extends it with four selectable static web frontends, each installable under `/usr/mww/transmission/`:

| Frontend | Version | Description |
|---|---|---|
| **flood-for-transmission** | 1.0.1 | Flood UI adapted for Transmission — a modern, responsive React interface |
| **TrguiNG web** | 1.5.1 | Angular-based UI with a clean dashboard layout |
| **Transmissionic web UI** | 1.8.0 | Vue-based UI with mobile-friendly design |
| **transmission-web-control** | snapshot | The classic enhanced Transmission web UI |

Each frontend is independently selectable in `make menuconfig` and is installed alongside (not replacing) the default Transmission web interface, allowing the user to switch between them via URL.

---

## elFinder — web-based file manager

**elFinder** 2.1.66 is a full-featured browser-based file manager for the FRITZ!Box with a rich set of Freetz-EVO-specific enhancements:

- **Drag-and-drop UI** with a context menu and toolbar
- **PHP connector** (squashfs-safe) for reliable file operations on the compressed firmware filesystem
- **FTP remote volumes** for accessing remote servers directly from the browser
- **Video preview** with complete seek-back and limited seek-forward support
- **Movie plugin** (Freetz-EVO specific): scrapes metadata from TMDb, OMDb, IMDb, and Wikipedia, presenting a rich info card for video files
- **MediaInfo plugin** (Freetz-EVO specific): shows codec, bitrate, resolution, and audio/subtitle track details via `libmediainfo`
- **VLC plugin** (Freetz-EVO specific): opens files directly in VLC via a URL handler
- **unrar and 7-Zip support** for inline archive extraction
- **Optional themes** with a theme-selection plugin (Freetz-EVO specific)
- **Multilingual** (de/en/it and others)
- **Better status bar** (Freetz-EVO specific) with richer information on selected files

elFinder is integrated into the Freetz web interface with an init script, configuration page, and status page.

---

## Gerbera 3.2.1 — UPnP/DLNA media server

**Gerbera** is a UPnP/DLNA-compliant media server that streams audio, video, and images to compatible network players and renderers — smart TVs, AV receivers, media players, game consoles, and any UPnP/DLNA client. It maintains a content directory, performs metadata extraction, and supports transcoding for format conversion on the fly.

### Features and configuration

Gerbera 3.2.1 in Freetz-EVO includes:

- A **CGI web config editor** with an embedded **ACE editor** for syntax-highlighted JSON/XML editing of the Gerbera configuration file
- A **setup wizard** that guides the user through initial configuration (media directories, transcoding profiles, port)
- Support for audio (MP3, FLAC, Ogg, AAC, WMA, APE, WavPack, AIFF, DSD), video (MP4, MKV, AVI, MOV), and image (JPEG, PNG, TIFF) formats
- Metadata extraction via `libmagic`, `exiv2` (images), `libebml`/`libmatroska` (MKV), and `libffmpegthumbnailer` (video thumbnails)
- Transcoding via FFmpeg profiles
- Config schema v2 (modern Gerbera configuration format)

### Library stack

Gerbera depends on a large set of libraries, all ported exclusively for Freetz-EVO and all supporting externalization:

| Library | Version | Purpose |
|---|---|---|
| `libupnp` (Portable UPnP SDK) | 1.14.31 | Core UPnP protocol stack |
| `libnpupnp` | 6.3.0 | Next-generation UPnP library |
| `pugixml` | 1.16 | Fast XML processing |
| `spdlog` | 1.17.0 | Fast C++ logging |
| `libfmt` | 12.2.0 | C++ string formatting |
| `icu` | 76.1 | Unicode and internationalization |
| `exiv2` | 0.28.8 | Image metadata (EXIF, IPTC, XMP) |
| `libebml` / `libmatroska` | 1.4.5 / 1.7.1 | MKV/Matroska container parsing |
| `libffmpegthumbnailer` | 2.2.3 | Video thumbnail generation |
| `libmagic` | 5.47 | File type detection |
| `libmicrohttpd` | 0.9.77 | Embedded HTTP server |
| `xmlrpc` | 1.64.03 | XML-RPC support |

Gerbera is integrated into the Freetz web interface with a daemon init script and a configuration page at `/cgi-bin/conf/gerbera`.

### MediaInfo companion

The **MediaInfo** package (with its `libmediainfo`, `libzen`, and `libxmlrpc` dependency stack) is available as a companion to Gerbera and elFinder. `mediainfo` provides detailed codec, bitrate, resolution, subtitle, and chapter information for audio and video files — the same data displayed by the elFinder MediaInfo plugin.

---

## miniupnpd 2.3.10 — UPnP-IGD daemon

**miniupnpd** is a lightweight UPnP Internet Gateway Device (IGD) daemon. It advertises the FRITZ!Box as a UPnP-IGD device on the local network, allowing UPnP-capable applications (games, VoIP clients, torrent clients) to automatically add and remove port-forwarding rules without manual configuration. This complements the download and streaming tools above: a torrent client running on the FRITZ!Box or on another device can use miniupnpd to open the ports it needs automatically.

miniupnpd is integrated into the Freetz web interface with an init script and a configuration page.

---

## ncdu — disk usage analysis for media storage

**ncdu** 1.19 (NCurses Disk Usage) and its web frontend **ncdu-cgi** are available as companion tools. They provide a fast, interactive view of storage consumption on mounted filesystems — useful for monitoring how much space a growing media library occupies on an external drive. See [Disk Management](DISK-MGMT.md) for details.
