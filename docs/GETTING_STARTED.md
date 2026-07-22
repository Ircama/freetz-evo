# Getting Started with Freetz-EVO

This guide describes the complete workflow: preparing a Linux build environment, configuring firmware options, compiling the image, and flashing it onto the device.

A Linux build environment with approximately 100–200 GB of free disk space is required.

Before the practical steps, this document introduces the ecosystem in the correct order: FRITZ!Box, AVM/FRITZ!, Freetz, Freetz-NG, and finally Freetz-EVO.

---

## Table of Contents

1. [FRITZ!Box, AVM, Freetz, Freetz-NG, and Freetz-EVO](#1-fritzbox-avm-freetz-freetz-ng-and-freetz-evo)
2. [What is Freetz-EVO?](#2-what-is-freetz-evo)
3. [What You Need](#3-what-you-need)
4. [Setting Up a Linux Environment](#4-setting-up-a-linux-environment)
   - [Option A — Native Linux](#option-a--native-linux)
   - [Option B — WSL on Windows](#option-b--wsl-on-windows)
5. [Cloning the Repository](#5-cloning-the-repository)
6. [Installing Freetz-EVO Prerequisites](#6-installing-freetz-evo-prerequisites)
7. [Configuring Your Firmware](#7-configuring-your-firmware)
8. [Building the Firmware](#8-building-the-firmware)
9. [Flashing the Firmware](#9-flashing-the-firmware)
10. [First Login](#10-first-login)
11. [Keeping Freetz-EVO Up to Date](#11-keeping-freetz-evo-up-to-date)
12. [Enabling Swap in the Web Interface (Optional)](#12-enabling-swap-in-the-web-interface-optional)

---

## 1. FRITZ!Box, AVM, Freetz, Freetz-NG, and Freetz-EVO

### What is a FRITZ!Box?

A [FRITZ!Box](https://en.wikipedia.org/wiki/Fritz!Box) is a family of residential gateway devices made for home and small-office networking. Depending on the model, it combines broadband access (DSL, cable, fiber, or mobile uplink), routing, Wi-Fi, switching, telephony features, and USB-based services in a single device.

FRITZ!Box devices run FRITZ!OS, a Linux-based firmware with an integrated web interface and strong support for features such as VoIP, DECT, NAS/media services, and network management.

### AVM and the FRITZ! brand

The [FRITZ!](https://en.wikipedia.org/wiki/Fritz!) product line is developed by AVM (now branded as FRITZ! at company level in recent communications), a German networking vendor known for consumer broadband and telephony products. In practice, when the community speaks about "AVM firmware" for FRITZ!Box, it refers to the original FRITZ!OS firmware provided by the manufacturer.

### What is Freetz?

[Freetz](https://freetz.github.io/wiki/freetz.html) is a build and customization framework for FRITZ!Box firmware. It does not start from a blank operating system; instead, it takes the original AVM firmware as base and modifies selected components.

In practical terms, [Freetz](https://freetz.github.io/wiki/freetz.en.html) can:

- add extra software packages and services;
- change configuration defaults and expose more advanced tuning options;
- remove unneeded components to free up space for custom additions.

This is why Freetz is best described as a firmware augmentation framework.

Freetz does not replace AVM firmware with a fully independent third-party firmware. It produces a derived firmware image that extends the existing AVM image while preserving the AVM platform stack, including FRITZ!OS core behaviors and features such as DSL integration, VoIP stack, DECT support, Wi-Fi handling/tuning, and the AVM web interface.

The major advantage is compatibility: users keep the native FRITZ!OS functionality and gain additional packages selected at build time.

Freetz also does not perform a full operating-system rebase and does not update the kernel to a new upstream major branch on its own. The result remains anchored to the vendor firmware baseline for that device/firmware generation.

### Legal Background

The original Freetz documentation explicitly explains a mixed legal model:

- part of FRITZ!Box firmware is open source and can be modified/redistributed under its licenses;
- another part is proprietary AVM (or AVM-licensed) code required for a fully working image.

Because of that proprietary portion, complete prebuilt firmware images that include AVM-protected components are not distributed by the Freetz project.

Therefore, Freetz distributes tooling and build logic, and each user must build their own image locally from the original vendor firmware.

The same legal guidance also warns against publishing self-built full images publicly, and reminds users that once a self-built firmware is installed, official AVM support should not be expected for issues related to that modified system.

### What is Freetz-NG?

[Freetz-NG](https://freetz-ng.github.io/freetz-ng/) is the actively maintained modern continuation of the Freetz ecosystem. It keeps the same core philosophy (augmenting original FRITZ!OS firmware), while extending device support, toolchains, package sets, and build-system maintenance.

---

## 2. What is Freetz-EVO?

Freetz-EVO is a fork of [Freetz-NG](https://github.com/Freetz-NG/freetz-ng).
It keeps Freetz-NG as technical foundation and adds UX improvements, additional packages, and project-specific enhancements.
It extends the original project with a redesigned web interface (the **EVO skin**, fully responsive with dark
mode and PWA support).

Some highlights compared to stock Freetz-NG:

| Feature | Details |
|---|---|
| **EVO skin** | Responsive UI, dark mode, mobile bottom bar, PWA-installable |
| **Nginx 1.29** | High-performance HTTP/reverse-proxy server |
| **PHP 8.4 / 8.5** | Modern PHP (upstream only has 5.6) |
| **Python 3.14** | With 11 additional third-party modules |
| **rTorrent + ruTorrent** | Full BitTorrent client with web UI |
| **elFinder** | Web-based file manager with drag-and-drop |
| **ttyd** | Web terminal (xterm.js in the browser) |
| **GCC on device** | Full compiler toolchain running on the device |
| **freetz_proxy** | HTTPS reverse proxy, accessible via MyFRITZ! |

> The default Freetz-EVO web interface listens on **port 81** (`http://fritz.box:81/`).
> If `freetz_proxy` is enabled, it can also be accessed from the standard [FRITZ!Box](http://fritz.box/) interface at `http://fritz.box/`, either by clicking the corresponding icon or [directly](http://fritz.box/cgi-bin/freetz_proxy?service=freetz) via `http://fritz.box/cgi-bin/freetz_proxy?service=freetz`.
> Default credentials: username `admin`, password `freetz`.

---

## 3. What You Need

- An **AVM FRITZ!Box** device (tested primarily on FRITZ!Box 7590 AX with FRITZ!OS 8.25)
- A **Linux build machine** — either native Linux or Windows with WSL2 (see next section)
- About **100–200 GB of free disk space** for the build environment (configuring a comprehensive set of Freetz-EVO tools for a single device target requires around 70 GB; additionally, each compressed image occupies over 2 GB, split between a large external archive and a small 40–50 MB firmware file)
- A reasonably fast internet connection to download source packages (the downloaded zipped source archives can take 4 GB or more)
- Basic familiarity with the Linux command line

---

## 4. Setting Up a Linux Environment

The Freetz-EVO build system runs on Linux. If you already have a Debian/Ubuntu Linux machine,
skip to [Section 6](#6-installing-freetz-evo-prerequisites).

### Option A — Native Linux

Any up-to-date Debian or Ubuntu installation works. Tested distributions include:
Fedora, Debian, Devuan, Ubuntu, Mint, Kali, and Arch.

> **Note:** Ubuntu 25.10 and some WSL versions are listed as potentially problematic. Ubuntu 24.04
> LTS is the recommended choice.

---

### Option B — WSL on Windows

Windows Subsystem for Linux (WSL2) lets you run a full Linux environment on Windows 10/11 without
a virtual machine or dual boot. The steps below install **Ubuntu 24.04 LTS** in an isolated WSL
instance on a drive of your choice.

#### Step 1 — Download Ubuntu 24.04 for WSL

Open **PowerShell** (or Windows Terminal) and run:

```powershell
winget download Canonical.Ubuntu.2404
```

Alternatively, download the bundle manually:

```
https://publicwsldistros.blob.core.windows.net/wsldistrostorage/Ubuntu2404-240425.AppxBundle
```

#### Step 2 — Extract the installation archive

Using [7-Zip](https://www.7-zip.org/), open the downloaded `.AppxBundle` file and extract the
file named `install.tar.gz` from the `Canonical.Ubuntu.2404_*.x64` sub-package (the x86_64
variant).

#### Step 3 — Import the distro to a drive of your choice

This lets you place the WSL image on any drive (e.g. `E:`) instead of the system drive:

```powershell
wsl --import Ubuntu-24.04-Freetz E:\Ubuntu2404Freetz Canonical.Ubuntu.2404_2404.0.5.0\install.tar.gz --version 2
```

Verify the import:

```powershell
wsl --list --verbose
```

#### Step 4 — First login and user setup

```powershell
wsl -d Ubuntu-24.04-Freetz
```

Inside the WSL shell, create a regular user and enable systemd:

```bash
cd
adduser myuser
usermod -aG sudo myuser
```

Edit `/etc/wsl.conf` (create it if it does not exist):

```bash
vi /etc/wsl.conf  # or use nano
```

Add the following content:

```ini
[boot]
systemd=true

[user]
default=myuser
```

Exit the WSL shell with **Ctrl+D**, then restart the instance to apply the changes:

```powershell
wsl --shutdown
wsl -d Ubuntu-24.04-Freetz
```

You should now be logged in as `myuser`.

> For the complete official guide to installing WSL, see:
> <https://learn.microsoft.com/windows/wsl/install>

---

## 5. Cloning the Repository

Once inside your Linux/WSL environment, clone the [Freetz-EVO](https://github.com/Ircama/freetz-evo) repository.

```bash
cd ~
git clone https://github.com/Ircama/freetz-evo
cd freetz-evo
```

---

## 6. Installing Freetz-EVO Prerequisites

Update the system and install all build dependencies.
The `tools/prerequisites` script automates this for you.

```bash
sudo apt update
sudo apt -y upgrade          # may take a few minutes
```

```bash
tools/prerequisites install  # may take a few minutes
```

The script detects your distribution and installs all required packages automatically.

---

## 7. Configuring Your Firmware

Freetz-EVO uses the same **Kconfig** system as the Linux kernel. An interactive
text-based menu lets you choose your device model, packages, language, and more.

```bash
make menuconfig
```

Use the arrow keys to navigate, **Space** to toggle options, and **Enter** to enter sub-menus.

### Key settings to adjust

| Menu location | What to set |
|---|---|
| **Target** | Select your exact FRITZ!Box model |
| **Packages** | Choose optional packages (Nginx, PHP, Python, elFinder, …) |
| **Web Interface → Freetz language** | Select UI language (English, German, Italian, …) |
| **Advanced Options → User competence level** | Start with **Beginner**; switch to Expert later |

When you are satisfied, press **Esc** until you reach the "Save configuration?" prompt and
confirm. This writes a `.config` file in the repository root.

> **Tip — Beginner level:** The default *Beginner* competence level shows only the most commonly
> used options. This is the recommended starting point; Expert level unlock
> additional useful options like Busybox configuration and shared libraries.
> Developer level typically shows uncompleted packages, which still need development work to get ready.

### About externalization

FRITZ!Box devices have limited internal flash memory. If you select many packages and see a
**"Filesystem image too big"** error, enable externalization for selected packages under
**Advanced Options → External**. Externalized components are stored on a USB drive plugged into
the device and loaded at boot time.

---

## 8. Building the Firmware

```bash
make
```

Or, better, to perform the same action with a cleaner and less verbose output:

```bash
make FREETZ_VERBOSITY_LEVEL=0
```

Using `make FREETZ_VERBOSITY_LEVEL=0`, the detailed output can be analyzed using another terminal, via `tail -f .build.log`.

The build process:
1. Downloads all required source packages and the original FRITZ!OS firmware
2. Builds a cross-compilation toolchain (GCC, binutils, …)
3. Compiles the selected packages
4. Assembles the final firmware image

The first build can take **one to several hours** depending on your machine. A wide Freetz-EVO setup with a 20 core Intel i7 system might take 15 hours (an old 4 core i5 system takes almost two days). Subsequent builds are much faster because intermediate results are cached.

The output files are placed in the `images/` directory:
- **`*.image`** — the firmware image to flash to your device
- **`*.external`** (if externalization is enabled) — the archive to upload to external storage

### Useful make targets

| Command | Purpose |
|---|---|
| `make menuconfig` | Open the configuration menu |
| `make` | Build the full firmware |
| `make help` | List all available make targets |
| `make olddefconfig` | Update `.config` after a `git pull` adds new options |
| `make distclean` | Full reset — removes everything while keeping your configuration (`.config`) and downloaded sources (`dl/`). |
| `make dirclean` | Full clean — removes the build directories and extracted sources while keeping the existing toolchain and configuration. |
| `make clean` | Clean tools and caches, keep downloaded source packages |
| `make cacheclean` | Minimal cleanup, keep compiled packages |

---

## 9. Flashing the Firmware

### Method 1 — via FTP bootloader (initial installation)

For first-time installation when no Freetz is yet running:

```bash
tools/push_firmware -h   # prints usage
```

> **Note:** The FTP bootloader method only installs the core `*.image` file. After the device
> reboots with Freetz, upload the `*.external` file (if any) via `tools/ssh_firmware_update.py` or the web interface.

### Method 2 — via SSH (fully automated, recommended for updates)

If Freetz is already running on the device:

```bash
tools/ssh_firmware_update.py --host <device-IP> --password <freetz-password> --batch
```

This script updates both the firmware image and the external file in a single unattended step.

### Method 3 — via Freetz web interface

1. Open your device's existing Freetz interface (if already installed) at `http://fritz.box:81/`
2. Go to **System → Firmware-Update**
3. Upload the `*.image` file
4. If you have an `*.external` file, also upload it using the *external file upload* option

---

## 10. First Login

After flashing, the device reboots. Access the Freetz-EVO web interface at:

```
http://fritz.box:81/
```

| | Default value |
|---|---|
| **Username** | `admin` |
| **Password** | `freetz` |

Change the password immediately after your first login under **System → Password**.

For SSH/telnet shell access, the default credentials are `root` / `freetz`.

> **Tip:** The EVO skin is fully responsive. On Android, we suggest installing the **Samsung Internet** browser; open the URL
> and use *Add to Home Screen* for a full PWA experience.

With `freetz_proxy`, you can access the device remotely via MyFRITZ!, then click on the icon — no port-forwarding required.

---

## 11. Keeping Freetz-EVO Up to Date

Pull the latest commits:

```bash
git pull
make olddefconfig   # merge any new config options into your .config
make                # rebuild
```

For developers, to sync Freetz-EVO with the upstream Freetz-NG project:

```bash
tools/sync-upstream-manual.sh             # interactive merge
tools/sync-upstream-manual.sh --log       # show pending upstream commits
tools/sync-upstream-manual.sh --diff      # show diff with upstream
tools/sync-upstream-manual.sh --dry-run   # test the merge without pushing
tools/sync-upstream-manual.sh             # perform the interactive merge
```

See [docs/SYNC_UPSTREAM.md](docs/SYNC_UPSTREAM.md) for full details.

---

## 12. Enabling Swap in the Web Interface (Optional)

If you do not see **Settings -> Swap** in the running WebIF, the option was not included at build time.

Enable it in `make menuconfig`:

1. Open **Additional patches**.
2. Enable **Add swap options** (`FREETZ_ADD_SWAPOPTIONS`).
3. Save config and rebuild/flash your firmware.

After flashing, open:

```text
http://fritz.box:81/cgi-bin/conf/mod
```

You should now see the **Swap** section, where you can:

- Set the swap file path (or partition path)
- Choose automatic/manual start behavior
- Create a swap file from the WebIF
- Configure swappiness

For a complete step-by-step guide, see [`docs/wiki/20_Advanced/create_swap.md`](wiki/20_Advanced/create_swap.md).

---

For more detail, see:
- Full documentation: <https://ircama.github.io/freetz-evo/>
- Prerequisites list: [`docs/prerequisites/README.md`](prerequisites/README.md)
- Source repository: <https://github.com/Ircama/freetz-evo>
- Build system reference: [`docs/TESTING_WORKFLOW.md`](TESTING_WORKFLOW.md)
