# aria2 1.37.0/AriaNg 1.3.13 (HTTP(s)/(s)FTP/Torrent/Metalink downloader)
  - Homepage: [https://aria2.github.io/](https://aria2.github.io/)
  - Manpage: [https://aria2.github.io/manual/en/html/](https://aria2.github.io/manual/en/html/)
  - Changelog: [https://github.com/aria2/aria2/releases](https://github.com/aria2/aria2/releases)
  - Repository: [https://github.com/aria2/aria2.git](https://github.com/aria2/aria2.git)
  - Package: [master/make/pkgs/aria2/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/aria2/)
  - Steward: Ircama
## AriaNg – Feature Overview

**AriaNg** is a lightweight web-based frontend for **aria2**, designed to provide a graphical interface over aria2’s RPC API without requiring a backend service.

AriaNg is a **pure frontend control plane for aria2**, providing:

* full download orchestration UI
* real-time monitoring via RPC
* zero backend overhead
* browser-based deployment simplicity

It runs entirely in the browser (static HTML/JS), connecting to a running aria2 instance via JSON-RPC or WebSocket.

AriaNg does not download files itself.

Instead it:

* connects to an existing aria2 process
* sends control commands via RPC
* renders download state in a web UI

Typical architecture:

Browser (AriaNg) ⇄ HTTP/WebSocket ⇄ aria2 daemon

AriaNg provides full lifecycle control:

* add new downloads (URL, magnet, torrent file)
* pause / resume / remove tasks
* per-task status monitoring
* global pause/resume

### Real-time statistics

* download speed
* upload speed (BitTorrent)
* ETA estimation
* active / waiting / stopped task counts

### Task inspection

* file list per task
* per-file progress
* piece-level progress (BitTorrent)

### BitTorrent integration (via aria2)

When aria2 is compiled with BitTorrent support:

* magnet link support
* DHT / PEX visibility
* tracker status display
* peer count monitoring

AriaNg exposes these as UI elements, not as a protocol implementation.

### Metalink and multi-source downloads

If supported by aria2:

* mirror selection display
* checksum verification status
* multi-source progress aggregation

### Configuration and session handling

* persistent RPC endpoint configuration
* multiple server profiles
* auto-reconnect on session loss
* optional authentication support (token-based)

### User experience design

* single-page application (SPA)
* no backend required
* responsive layout (desktop + mobile usable)
* dark/light themes depending on build

### Data flow model

1. User action in UI
2. AriaNg generates JSON-RPC request
3. aria2 executes download operation
4. aria2 returns state updates
5. AriaNg refreshes UI state

This is a stateless frontend model.


## aria2 – Feature Overview

**aria2** is a lightweight command-line download manager designed for high performance and embedded systems. It supports multiple protocols and can aggregate several sources into a single download stream.

**aria2** is essentially a **high-performance, protocol-agnostic download engine** optimized for:

* parallelism
* reliability
* low footprint deployments
* automation and remote control

---

## Supported protocols

* HTTP / HTTPS
* FTP
* SFTP / SCP (if libssh2 is enabled)
* BitTorrent (optional)
* Metalink (optional)

Key capability:

* multi-source downloads (mirrors, HTTP + torrent hybrid scenarios)

---

### Parallel downloads

* Splits files into multiple segments
* Downloads segments in parallel
* Uses multiple connections per server when allowed

### Smart scheduling

* Dynamic load balancing across connections
* Automatic retry on failures
* Adaptive chunk reassignment

### Resume support

* Fully supports HTTP range requests
* Can resume interrupted multi-source downloads

---

### BitTorrent support

Enabled with BitTorrent support:

* Magnet URI support
* DHT (Distributed Hash Table)
* Peer Exchange (PEX)
* Seeder/leecher participation
* Piece-level download optimization

### Metalink support (optional)

When enabled:

* Parses Metalink XML descriptions
* Automatically selects mirrors
* Performs integrity verification (hash-based checksums)
* Failover between sources

### Remote control interfaces

If XML-RPC support is enabled:

* External control API (start/stop/query downloads)
* Queue management
* Status monitoring

If WebSocket support is enabled:

* Low-latency real-time control channel
* Suitable for web dashboards or automation systems

---

### DNS

* Asynchronous DNS resolution via c-ares (default)
* Optional disabling for minimal builds

### TLS / HTTPS

Supports either:

* OpenSSL
* GnuTLS

Features:

* HTTPS download support
* certificate validation
* configurable CA bundle

---

### Storage and data handling

* SQLite-based cookie storage (optional)
* Firefox / Chromium cookie compatibility
* Pre-allocation of output files
* Efficient disk I/O handling

---

### Optional C++ library libaria2

When enabled:

* Provides programmatic API to aria2 core
* Allows embedding download engine into applications
* Useful for custom download services or GUIs

---

### Build-time optimizations

* jemalloc memory allocator (stability under uClibc)
* section-based linking (`-ffunction-sections`, `--gc-sections`)
* optional static linking
* reduced dependency set (no libuv, no tcmalloc, no libgcrypt)

**Build notes:**

aria2c 1.37.0 crashes with SIGFPE on MIPS when built with uClibc 1.0.57

aria2c terminates with Floating point exception (SIGFPE) immediately on startup when compiled against uClibc 1.0.57 on MIPS. The crash occurs before main() returns, during constructors execution.

Workaround: linking against jemalloc instead of uClibc's built-in allocator prevents the crash, suggesting the issue lies in uClibc's memory allocator implementation.
