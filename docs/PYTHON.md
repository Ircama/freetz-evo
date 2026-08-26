# Freetz-EVO — Python Support

Freetz-EVO includes an extensive Python 3 ecosystem for FRITZ!Box devices, covering the interpreter itself, over 70 third-party packages, X11/tkinter support, Rust-built extension modules, and installation support for [Home Assistant](https://www.home-assistant.io). The Python 2 cross-compilation infrastructure has also been fixed for the 13 legacy `python-*` modules.

All relevant options are available under **Packages** in `make menuconfig`.

---

## Python 3.14 interpreter

Freetz-EVO ships **Python 3.14.3** with a number of FRITZ!Box-specific additions on top of the Freetz-NG base:

- A **zip-importer fix** that correctly handles compressed `.zip` archives on the cramfs/squashfs firmware filesystem.
- **patchelf RPATH support**: the Python binary's RPATH is fixed at install time so shared extension modules resolve correctly regardless of the firmware's library paths.
- **Build scripts for external deployment**: Python and its extension modules can be placed on an external USB drive (via the standard Freetz externalization mechanism) rather than in the squashed firmware, keeping the firmware image size manageable.

---

## Rust-built Python packages

Two Python packages in Freetz-EVO are built using the Rust/`maturin` toolchain rather than the standard `setuptools` pipeline. They depend on the Rust cross-compilation infrastructure described in [RUST.md](RUST.md).

**`python3-uv`** 0.11.16 is the `uv` Python package manager — a fast, Rust-native replacement for `pip` and `venv`. It is built with `maturin` and cross-compiled for the target architecture using the same `CARGO_HOME` isolation and uClibc patch machinery described in [RUST.md](RUST.md).

**`python3-cryptography`** 48.0.0 is the Python `cryptography` library. Its low-level cryptographic operations are implemented in Rust (via the `cryptography-rust` backend); the package is built with `maturin` and linked against the cross-compiled OpenSSL libraries.

**`python3-ulid-transform`** 2.2.9 is a ULID creation and transformation module, also built via `maturin` with Rust cross-build target support.

---

## tkinter and X11 support

Python's `tkinter` module is enabled in Freetz-EVO via a full set of X11 client libraries and the Tcl/Tk runtime. The complete library stack ported exclusively for Freetz-EVO includes: `libXau` (X authorization), `libxcb` (XCB protocol), `libX11` (core X11 protocol), `libXext` (X extensions), `libICE` (inter-client exchange), `libSM` (session management), `libXt` (X Toolkit intrinsics), `libXmu` (miscellaneous utilities), `libXaw` (Athena widgets), `libXpm` (pixmap), `libXfixes` (fixes extension), and `libXi` (input extension), along with the header-only packages `xorgproto`, `xcb-proto`, `xtrans`, and `util-macros`.

**Tcl/Tk 8.6.16** provides `libtcl8.6.so` and `libtk8.6.so`, along with the optional `wish` shell for interactive Tk sessions. With `DISPLAY=<host>:0` set, Python GUI applications built with tkinter run on the FRITZ!Box and display on a remote X11 server.

Companion X11 applications (`xclock`, `xeyes`, `xterm`) are also available for testing X11 connectivity.

---

## Home Assistant

The Python 3 package set in Freetz-EVO is sized for running **Home Assistant** on-device. The combination of the full interpreter, the async runtime packages (`aiohttp`, `aiodns`, `aiosignal`, `async-timeout`), cryptographic packages (`python3-cryptography`, `pynacl`, `bcrypt`), and the various protocol/format libraries covers the bulk of Home Assistant's dependencies.

---

## Third-party package list

The following Python 3 packages are available in Freetz-EVO:

| Package | Version | Notes |
|---|---|---|
| `aiodns` | 4.0.0 | Async DNS resolution via c-ares |
| `aiohttp` | 3.13.3 | Async HTTP client/server |
| `aiohttp-asyncmdnsresolver` | 0.1.1 | mDNS resolver for aiohttp |
| `aiohttp-fast-zlib` | 0.3.0 | Fast zlib for aiohttp |
| `aiohappyeyeballs` | 2.6.1 | Happy Eyeballs (RFC 6555) for asyncio |
| `aiosignal` | 1.4.0 | Async signal handlers |
| `annotatedyaml` | 1.0.2 | Annotated YAML parser |
| `async-timeout` | 5.0.1 | Timeout context manager for asyncio |
| `attrs` | 26.1.0 | Classes without boilerplate |
| `av` | 16.0.1 | FFmpeg bindings for Python |
| `audioop-lts` | 0.2.1 | Backport of audioop module (removed in Python 3.13) |
| `bcrypt` | 3.2.2 | bcrypt password hashing |
| `brotli` | 1.2.0 | Brotli compression |
| `cffi` | 1.17.1 | C Foreign Function Interface |
| `charset-normalizer` | 3.4.6 | Charset detection |
| `ciso8601` | 2.3.3 | Fast ISO 8601 datetime parser |
| `dateutil` | 2.9.0.post0 | Date/time utilities |
| `dbus-fast` | 4.0.0 | Fast D-Bus client for asyncio |
| `faust-cchardet` | 2.1.19 | Character encoding detection |
| `fnv-hash-fast` | 1.6.0 | Fast FNV hash (Rust extension) |
| `fnvhash` | 0.2.1 | FNV hash (pure Python) |
| `frozenlist` | 1.8.0 | List that can be made immutable |
| `grpcio` | 1.78.0 | gRPC runtime |
| `grpcio-reflection` | 1.78.1 | gRPC server reflection |
| `grpcio-status` | 1.78.1 | gRPC status proto |
| `h11` | 0.16.0 | Pure-Python HTTP/1.1 implementation |
| `ha-ffmpeg` | 3.2.2 | Home Assistant FFmpeg helper |
| `httpcore` | 1.0.9 | Low-level async HTTP client |
| `httpx` | 0.28.1 | Async HTTP client |
| `idna` | 3.11 | Internationalized domain names |
| `lru-dict` | 1.4.1 | LRU dictionary |
| `lxml` | 6.0.2 | XML and HTML processing |
| `markupsafe` | 3.0.3 | Safe string escaping for Jinja2 |
| `multidict` | 6.7.1 | Multi-value dictionary |
| `numpy` | 2.4.3 | Numerical arrays |
| `pandas` | 3.0.1 | Data analysis |
| `pillow` | 12.1.1 | Image processing |
| `pip` | 26.0.1 | Package installer |
| `propcache` | 0.4.1 | Property caching |
| `psutil` | 7.2.2 | Process and system utilities |
| `pycares` | 5.0.1 | Python bindings for c-ares |
| `pycparser` | 3.0 | C parser for cffi |
| `pycryptodome` | 3.23.0 | Cryptographic library |
| `pymicro-vad` | 2.0.1 | Voice activity detection |
| `pynacl` | 1.6.2 | libsodium bindings |
| `pyspeex-noise` | 2.0.0 | Speex noise suppression |
| `pyturbojpeg` | 2.2.0 | libjpeg-turbo bindings |
| `pyyaml` | 6.0.3 | YAML parser and emitter |
| `setuptools` | 82.0.1 | Build system for Python packages |
| `six` | 1.17.0 | Python 2/3 compatibility |
| `voluptuous` | 0.16.0 | Data validation |
| `webrtc-models` | 0.3.0 | WebRTC models |
| `yarl` | 1.23.0 | URL handling |
| `zeroconf` | 0.148.0 | mDNS/DNS-SD |
| `python3-bluetooth-data-tools` | 1.29.18 | Bluetooth data helpers |
| `python3-cached-ipaddress` | 1.1.2 | Cached IP address parsing |
| `python3-certifi` | 2025.10.5 | Mozilla CA bundle |
| `python3-cryptography` | 48.0.0 | Cryptographic recipes (Rust-built) |
| `python3-habluetooth` | 6.8.3 | Home Assistant Bluetooth |
| `python3-ifaddr` | 0.2.0 | Network interface enumeration |
| `python3-mashumaro` | 3.17 | Data class serialization |
| `python3-orjson` | 3.10.7 | Fast JSON (Rust extension) |
| `python3-pyqrcode` | 1.2.1 | QR code generator |
| `python3-pyric` | 0.1.6.3 | Linux wireless (nl80211) |
| `python3-regex` | 2026.5.9 | Enhanced regex module |
| `python3-ulid-transform` | 2.2.9 | ULID handling (Rust-built) |
| `python3-uv` | 0.11.16 | Fast package manager (Rust-built) |
| `typing_extensions` | 4.15.0 | Typing backports |

---

## Python 2 modules fix

All 13 `python-*` cross-compilation modules (`python-bjoern`, `python-cffi`, `python-cheetah`, `python-pycurl`, `python-pycryptodome`, `python-pyopenssl`, and others) were broken during cross-compilation due to missing environment variables in the shared build infrastructure. Freetz-EVO fixes `python-module-macros.mk.in` by properly setting `CC`, `CXX`, `LDSHARED`, `CFLAGS`, `PYTHONPATH`, and the `build_ext --library-dirs` argument to point to the target staging directory instead of the host. `python-pip` for Python 2 is also added.

---

## MicroPython 1.27.0

**MicroPython** is available as a lightweight alternative to the full Python 3 interpreter for constrained use cases. It provides a REPL, script execution, and optional `micropython-lib` standard library modules in a much smaller binary footprint.
