# Welcome to Freetz-EVO

```
    ______               __             _______    ______
   / ____/_______  ___  / /_____       / ____/ |  / / __ \
  / /_  / ___/ _ \/ _ \/ __/_  /______/ __/  | | / / / / /
 / __/ / /  /  __/  __/ /_  / //_____/ /___  | |/ / /_/ /
/_/   /_/   \___/\___/\__/ /___/    /_____/  |___/\____/

```

Freetz-EVO is a fork of [Freetz-NG](https://github.com/Freetz-NG/freetz-ng). More features - less bugs!

Compared to Freetz-NG, Freetz-EVO includes GCC on-device compilation, nginx, rtorrent, ruTorrent, PHP,
aria2, AI translation for foreign languages, more explicit error/warning messages, an advanced GitHub
Action for testing new developments, and many other new packages.

Freetz-EVO is continuously kept in sync with the upstream [Freetz-NG](https://github.com/Freetz-NG/freetz-ng)
repository: all upstream fixes, new firmware support, and toolchain updates are regularly merged into
Freetz-EVO so that it always builds on the latest Freetz-NG foundation.

---

### Improvements over Freetz-NG

#### New packages

| Package | Description | Status |
|---|---|---|
| **aria2** / **AriaNg** / libcares | Multi-protocol download utility (HTTP, FTP, BitTorrent, Metalink) with a full web UI (AriaNg) and CGI integration. | EVO only |
| **rTorrent** / **ruTorrent** | Feature-rich BitTorrent client with a complete web interface, CGI backend, and config editor. | EVO only |
| **Nginx** 1.29 | High-performance HTTP/reverse-proxy server with MIPS/ARM cross-compilation fixes and optional externalization. | EVO only |
| **PHP** 8.4 / 8.5 | Modern PHP interpreter with multi-version selection (5.6 legacy, 8.4, 8.5), bzip2, libxml2, libatomic support. | upstream has PHP 5.6 only |
| **Python 3.14** | Python 3.14.2 with zip-importer fix, patchelf RPATH support, and build scripts for external deployment. | upstream has 3.14.2 too (merged) |
| **python3-\*** (11 modules) | New Python 3 third-party packages: `cffi`, `cryptography`, `lxml`, `markupsafe`, `numpy`, `pandas`, `pillow`, `pip`, `pycryptodome`, `pyyaml`, `setuptools`. | EVO only |
| **GCC On Device** | Full GCC toolchain for on-device compilation; optional externalization; removed gprofng for i686 compatibility. | EVO only |
| **GitHub CLI** (`gh`) | GitHub CLI tool with Go host-tool integration, allowing GitHub API interaction from the FritzBox. | EVO only |
| **util-linux** | Dual-version support (2.36 / 2.40) with Disk Tools category and utilities like `lsblk`, `fdisk`, `blkid`. | upstream has basic version |
| **MediaInfo** / libmediainfo / libzen / libxmlrpc | Media file analysis tool with full library stack; reports codecs, bitrates, resolution, and metadata. | EVO only |
| **proc-ps** | Improved `ps` replacement backed by procps-ng with richer process information output. | EVO only |
| **cpulimit** | Limits the CPU usage of a process to a given percentage; prevents runaway processes from overloading the device. | merged upstream |
| **microperl** 5.38 | Minimal Perl 5.38.2 interpreter (alongside legacy 5.10.1) with full stub library set for embedded use. | upstream has 5.38 too (merged) |
| **zip** 3.0 (infozip) | Standard `zip` archiver for creating ZIP archives directly on the device. | upstream has infozip |
| **gdb** 17.1 | GNU Debugger version 17.1 for on-device debugging of binaries and crash analysis. | merged upstream |
| **patchelf** (target) | ELF binary patcher for fixing RPATH and dynamic linker paths on cross-compiled binaries. | merged upstream |
| **binutils-tools** (`c++filt`, `elfedit`, `nm`, `objdump`) | Additional binutils utilities for binary inspection and symbol demangling on the device. | merged upstream |
| **libnettle** | Low-level cryptographic library (AES, SHA, RSA) used by GnuTLS and other packages. | upstream has nettle |
| **libzen** | Helper library required by MediaInfo for portable C++ utilities. | EVO only |
| **libxmlrpc** | XML-RPC library for rTorrent's SCGI/RPC interface; host tool gennmtab moved to `make/host-tools`. | EVO only |
| **libcares** (c-ares) | Asynchronous DNS resolver library used by aria2 and curl. | EVO only |

#### Python 2 third-party modules fix

All 13 `python-*` cross-compilation modules (`python-bjoern`, `python-cffi`, `python-cheetah`,
`python-pycurl`, `python-pycryptodome`, `python-pyopenssl`, etc.) were broken during cross-compilation
due to missing environment variables. Freetz-EVO fixes `python-module-macros.mk.in` by properly
setting `CC`, `CXX`, `LDSHARED`, `CFLAGS`, `PYTHONPATH`, and `build_ext --library-dirs` to point
to the target staging directory instead of the host.

#### Enhanced packages

| Package | Enhancement |
|---|---|
| **curl** | Added CA-bundle toggle option; rTorrent uses the curl CA bundle for HTTPS validation. |
| **pcre** | Fixed parallel install race condition; JIT disabled for kernel 2.6.39.3. |
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

#### CI / tooling

| Feature | Description |
|---|---|
| **make_package workflow** | Advanced GitHub Actions workflow for per-package build testing with matrix parallelism and detailed failure diagnostics. |
| **sync-upstream workflow** | Automated workflow to merge upstream Freetz-NG changes into Freetz-EVO on a schedule. |
| **AI translation** | Automatic translation of web UI labels to foreign languages via LLM, with curated override cache. |
| **ssh_firmware_update.py** | Python tool to flash a Freetz firmware image to a FRITZ!Box over SSH/SCP, emulating the web update process with interactive/batch modes, progress bars, dry-run and debug options. Merged upstream. |
| **make_progress_monitor.sh** | Bash script to monitor Freetz cross-compilation build progress in real time (run alongside `make` in a second terminal). Merged upstream. |

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
```
  git clone https://github.com/Ircama/freetz-evo ~/freetz-evo
```

### Or clone a single [tag](../../tags):
```
  git clone https://github.com/Ircama/freetz-evo ~/freetz-evo --single-branch --branch TAGNAME
```

### Install prerequisites:
```
  cd ~/freetz-evo
  tools/prerequisites install # -y
```

### Build firmware:
```
  cd ~/freetz-evo
  make menuconfig
  make
  # make help
```

### Flash firmware:
```
  cd ~/freetz-evo
  tools/push_firmware -h
```

### Update freetz firmware via SSH:
```
  cd ~/freetz-evo
  tools/ssh_firmware_update.py --host <myIP> --password <myPassword> --batch
```

### Show GIT states:
```
  git status
  git diff --no-prefix # --cached # > file.patch
  git log --graph # --oneline
```

### Delete local changes:
```
  git checkout master ; git fetch --all --prune ; git reset --hard origin/HEAD ; git clean -fd
```

### Update GIT:
```
  git pull
```

### Checkout old revision:
```
  git checkout HASH-OF-COMMIT # -b NEW-BRANCH
```
### Checkout another branch:
```
  git checkout EXISTING-BRANCH
```

### Mirrors:
```
  git clone https://github.com/Ircama/freetz-evo ~/freetz-evo
```

### Documentation:
See [https://ircama.github.io/freetz-evo/](https://ircama.github.io/freetz-evo/) (or [docs/](docs/README.md)).


<details>
  <summary>Testing your Documentation changes localy</summary>

When working on this repo, it is advised that you review your changes locally before committing them. The `mkdocs serve` command can be used to live preview your changes (as you type) on your local machine.

Please make sure you fork the repo and change the clone URL in the example below for your fork:

- Linux Mint / Ubuntu 20.04 LTS / 23.10 and later:
    - Preparations (only required once):

    ```bash
    git clone https://github.com/YOUR-USERNAME/freetz-evo
    cd freetz-evo
    sudo apt install python3-pip python3-venv
    python3 -m venv .venv
    source .venv/bin/activate
    pip3 install -r .github/mkdocs/requirements.txt
    ```

    - Enter the virtual environment (if exited):

    ```bash
    source .venv/bin/activate
    ```

    - Running the docs server:

    ```bash
    mkdocs serve --dev-addr 0.0.0.0:8000 --config-file .github/mkdocs/mkdocs.yml
    ```

- Fedora Linux instructions (tested on Fedora Linux 28):
    - Preparations (only required once):

    ```bash
    git clone https://github.com/YOUR-USERNAME/freetz-evo
    cd freetz-evo
    pip install --user -r .github/mkdocs/requirements.txt
    ```

    - Running the docs server:

    ```bash
    mkdocs serve --dev-addr 0.0.0.0:8000 --config-file .github/mkdocs/mkdocs.yml
    ```

After these commands, the current branch is accessible through your favorite browser at <http://localhost:8000>

</details>
