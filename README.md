# Welcome to Freetz-EVO

```text
  _____              _            _______     _____
 |  ___| __ ___  ___| |_ ____    | ____\ \   / / _ \
 | |_ | '__/ _ \/ _ \ __|_  /____|  _|  \ \ / / | | |
 |  _|| | |  __/  __/ |_ / /_____| |___  \ V /| |_| |
 |_|  |_|  \___|\___|\__/___|    |_____|  \_/  \___/

```

Freetz-EVO is a fork of [Freetz-NG](https://github.com/Freetz-NG/freetz-ng), which remains the technical foundation of this project.
Freetz-EVO builds on that foundation with additional packages, UX improvements, and workflow tooling.

Freetz-EVO is easier, sleeker, with more features and less bugs.

Freetz-EVO includes:

- over 120 new packages and libraries, including exclusive applications, Go and Rust support,
- over 70 python3 packages, including Rust support,
- over 70 libraries,
- over 40 improved packages and libraries,
- USB audio stack, extensive playback and recording tools, local playlist management and web radio functions — see the [Audio Subsystem](docs/AUDIO.md),
- hidapi support for HID-Class USB device access and ja11-config support for configuring FiiO JA11 and other KT02H20 DSP-based USB DACs (TUI EQ configurator plus ja11-boot/ja11-flash firmware update),
- X11 client libraries and tools,
- microcontroller flasher tools to enable USB peripheral devices.
- built-in Go and Rust toolchains to compile Go and Rust packages.

The extensive Python3 support allows installing and running [Home Assistant](https://www.home-assistant.io).

Relevant new packages include rtorrent with improved ruTorrent web tool, aria2 with AriaNg web tool, Gerbera, a Disk Management interactive web tool, ncdu web tool, improved elfinder Web tool, GCC on-device, nginx and many others.

New subsystems also include ALSA userspace audio packages, exposed ALSA/USB audio kernel drivers on compatible targets, and the `cdc-acm` USB serial driver for native USB CDC ACM devices.

On compatible targets, enabling the exposed ALSA/USB audio drivers together with the ALSA userspace stack allows audio playback through a USB headset or, preferably, a USB HiFi DAC. Combined with the available MPD, mpc, myMPD, and related web interfaces, Freetz-EVO also offers web radio browsing, playback, and control functions directly from the browser.

Additionally, Freetz-EVO offers AI translation for non EN and DE languages, more explicit error/warning messages, an advanced GitHub Action for testing new developments, and many other new features.

Freetz-EVO tracks the upstream [Freetz-NG](https://github.com/Freetz-NG/freetz-ng) repository: fixes, new firmware support, and toolchain updates are periodically merged. Keeping the two trees in sync is a complex and time-consuming process, so there may be gaps between upstream changes and their appearance in Freetz-EVO.

### Getting Started

New to Freetz-EVO? The **[Getting Started guide](docs/GETTING_STARTED.md)** walks you through the complete workflow: setting up a Linux build environment (including WSL on Windows), configuring the firmware, building it, and flashing your device.

### Compatibility

Packages available only in Freetz-EVO, and not in Freetz-NG, are compiled for MIPS, MIPSel, 32-bit x86, 32-bit ARM and [Aarch64](docs/5690_XGS_08.25.md) architectures using GCC >= 13.4.0 and uClibc >= 1.0.58. Packages inherited from Freetz-NG retain the compatibility of their original Freetz-NG implementations. On older devices, such as those using the MIPSel architecture, only a subset of the Freetz-EVO enhancements is available.

All Freetz-EVO-only packages are currently developed and tested on an AVM FRITZ!Box 7590 AX running FRITZ!OS 8.25.

Freetz-EVO is still under development.

#### UX and Web Interface

Freetz-EVO features a fully responsive, mobile-first EVO skin with dark mode, PWA support, hardened form-based session login (CSPRNG cookie, HttpOnly, SameSite=Strict), and the `freetz_proxy` HTTPS reverse proxy for remote access via MyFRITZ!. See [docs/EVO-SKIN.md](docs/EVO-SKIN.md) for details, or try the [interactive UI mockup](screenshots/evo-demo.html).

#### Packages and tooling

For the full listing of new packages, enhanced packages, and CI/tooling additions, see **[docs/NEW-PACKAGES.md](docs/NEW-PACKAGES.md)**. Topic-specific deep dives are available for the [Audio Subsystem](docs/AUDIO.md), [Disk Management](docs/DISK-MGMT.md), [Multimedia and Downloads](docs/MULTIMEDIA.md), [Rust packages](docs/RUST.md), [Go packages](docs/GO.md), and [Python ecosystem](docs/PYTHON.md).

Highlights include:

| Package | Description |
|---|---|
| **[Disk Management](docs/DISK-MGMT.md)** | Web console for partitioning, formatting, cloning, and recovery, backed by 15+ disk tools. |
| **[Audio subsystem](docs/AUDIO.md)** | ALSA stack, MPD ecosystem, USB DAC support, AirPlay/Spotify receivers. |
| **[Multimedia and downloads](docs/MULTIMEDIA.md)** | rTorrent/ruTorrent, aria2/AriaNg, Gerbera UPnP/DLNA, elFinder file manager, miniupnpd. |
| **[Rust packages](docs/RUST.md)** | ~30 cross-compiled tools (ripgrep, gitui, yazi, ncspot, rmpc…) with full uClibc compatibility. |
| **[Go packages](docs/GO.md)** | Go 1.25 cross-compilation; lazygit, hugo, rclone, caddy, prometheus, and more. |
| **[Python ecosystem](docs/PYTHON.md)** | Python 3.14 with 70+ packages, tkinter/X11, Rust-built extensions, Home Assistant support. |
| **[All packages](docs/NEW-PACKAGES.md)** | Complete listing: 150+ new packages, enhanced packages, CI/tooling. This includes GCC on-device, llama.cpp, Nginx, PostgreSQL, PowerDNS, GDB, Valgrind, and much more. |

For the complete listing, see **[docs/NEW-PACKAGES.md](docs/NEW-PACKAGES.md)**.

---

## How to use

### Basic infos:
  * After flashing the formware, a web interface will be started on [port :81](http://fritz.box:81/), credentials: `admin`/`freetz`<br>
  * Default credentials for shell/ssh/telnet access are: `root`/`freetz`<br>
  * For more see: [ircama.github.io/freetz-evo](https://ircama.github.io/freetz-evo/)

### Requirements:
  * You need an up to date Linux System with some [prerequisites](docs/prerequisites/README.md).
  * Or download a ready-to-use VM like Gismotro's [Freetz-Linux](https://freetz.digital-eliteboard.com/?dir=Teamserver/Freetz/Freetz-VM/VirtualBox/) (user & pass: `freetz`). To update it to Freetz-EVO, run again the installation of the prerequisites after cloning this repository.
  * There are also Docker images available like [pfichtner-freetz](https://hub.docker.com/r/pfichtner/freetz) ([README](https://github.com/pfichtner/pfichtner-freetz#readme)). To update it to Freetz-EVO, run again the installation of the prerequisites after cloning this repository.

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
tools/prerequisites install -y
```

### Build firmware:
```bash
cd ~/freetz-evo
make menuconfig  # Configure your setup
make  # Long-running operation
# make help
```

After running `make menuconfig`, select the options appropriate for your target device and desired packages, then save the configuration when prompted. The selected configuration will be written to `.config`. If `.config` does not exist, it is created, otherwise it is updated.

### Flash firmware (if SSH is not yet installed):
```bash
cd ~/freetz-evo
tools/push_firmware -h
```

### Update freetz firmware via SSH:
```bash
cd ~/freetz-evo
tools/ssh_firmware_update.py --host <myIP> --password <myPassword> --batch
```

### host-tools tarball missing:

When the host tools download fails because missing from the freetz-NG portal (e.g., `tools-yyy-mm-dd.tar.xz`, like `tools-2026-08-14.tar.xz`), host-tools tarball needs to be locally recreated using the following commands:

```bash
cp .config .config.backup  # This is important because the following command modifies the .config file.
tools/dl-hosttools own --no-clean
cp .config.backup .config
```

### Show GIT states:
```bash
git status
git diff --no-prefix # --cached # > file.patch
git log --graph # --oneline
```

#### Rebuild everything

To rebuild everything while keeping your configuration (`.config`) and downloaded sources (`dl/`):

```bash
make distclean
make
```

This removes all generated build artifacts, including the images and the toolchain, but preserves `.config` and the download cache.

#### Rebuild without rebuilding the toolchain

```bash
make dirclean
make
```

This removes the build directories and extracted sources while keeping the existing toolchain, resulting in a much faster rebuild. Also the `images` directory is preserved; notice that this directory can grow indefinitely as firmware images and their corresponding backup files are accumulated with each successful build. When running `make` multiple times, periodically check and manually clean the `images/` directory to prevent your build environment from running out of disk space.

#### Delete all local Git changes

To completely restore the repository to the current remote revision and remove all untracked files:

```bash
git checkout master ; git fetch --all --prune ; git reset --hard origin/HEAD ; git clean -fd
```

**Warning:** this permanently discards:

- local commits;
- modifications to tracked files;
- untracked files and directories.

Use this command only when you want to reset the Git working tree. It is **not** required for performing a clean rebuild.

### Update GIT:
```bash
git pull
```

### Checkout old revision:
```bash
git checkout HASH-OF-COMMIT # -b NEW-BRANCH
```

### Checkout another branch:
```bash
git checkout EXISTING-BRANCH
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

## AI disclosure

The enhancements that turned Freetz-NG into Freetz-EVO are the result of a year of development, carried out largely with the assistance of AI coding agents such as DeepSeek V4 Flash/Pro, GPT-5.x, and Claude Sonnet 4.x. Humans have remained responsible for the ideas, software selection, architecture, in-depth testing, revision, and optimization.

If you are not comfortable with AI-assisted code, this software is not for you.

Freetz-EVO would not exist without Freetz-NG, whose foundations were designed and developed by humans, by hand.

We are deeply thankful and indebted to Freetz-NG and its contributors; their implementation, kernels, tests, design choices, and patient support provided an essential reference throughout the development of Freetz-EVO.

---

## License

This repository contains two distinct components under different licences:

- **Freetz-NG base** (all content inherited from the upstream [Freetz-NG](https://github.com/Freetz-NG/freetz-ng) project) is licensed under the **GNU General Public License v2.0 (GPL-2.0)**. See [COPYING](COPYING) for the full GPL-2.0 text.

- **Freetz-EVO extensions** (all new packages introduced by this fork, not available upstream) are licensed under the **European Union Public Licence v1.2 (EUPL-1.2)**. See [LICENSE](LICENSE) for the full EUPL-1.2 text.

- **Reuse of Freetz-EVO-original files**: when files that are original to Freetz-EVO (e.g., package makefiles or other code not derived from upstream [Freetz-NG](https://github.com/Freetz-NG/freetz-ng)) are reused in other projects, including upstream, their licence remains **EUPL-1.2**. Reusers should keep the original copyright/licence notices and clearly indicate that those specific files are under EUPL-1.2.
