# Installation

Freetz provides build scripts for creating a modified firmware image from
an original AVM firmware image.

Important:

- Distributing original or modified firmware images may violate licensing
  terms.
- Installing modified firmware can void the manufacturer's warranty.
- For problems caused by modified firmware, do not contact AVM support.

Speedport users should also see
[speedport2fritz](http://wiki.ip-phone-forum.de/skript:speedport2fritz#was_mach_ich_mit_dem_fertigen_kernel.image).
Starting with script version 2.2.2008, using speed2fritz is possible.

New users should read [Freetz for Beginners](newbie.md) first.

### Recommended Build Environment

Use a Linux environment:

- A native Linux installation, or
- A virtual Linux environment, especially if your main OS is Windows or macOS.

A maintained VM-based environment is often the easiest entry point for
beginners. Do not build Freetz on FAT or NTFS partitions; use a Linux
filesystem.

### Current Freetz-NG Quick Path

For current Freetz-NG sources, use Git:

```sh
git clone https://github.com/Freetz-NG/freetz-ng ~/freetz-ng
cd ~/freetz-ng
```

Install the packages required by your Linux distribution and verify the
toolchain prerequisites. See [PREREQUISITES](../../prerequisites/README.md).
If dependency installation fails, update the package indexes and retry.

Configure Freetz:

```sh
make menuconfig
```

In `menuconfig`:

1. Select your exact hardware model.
2. Select the firmware version.
3. Enable only a minimal package set for the first build.

Build the image:

```sh
make
```

The first build can take a while because toolchains and source archives
are prepared. The resulting image is placed in the `images` directory.

Flash the image through a supported path:

- Web interface upload, or
- `tools/push_firmware` for a bootloader-based workflow.

Always keep a recovery path ready before flashing.

After flashing:

1. Confirm that the device is reachable.
2. Check the internet and telephony baseline.
3. Open the Freetz interface and verify the enabled packages.
4. Apply package settings gradually.

For later changes, update the sources, re-run `menuconfig` if needed,
rebuild, flash, and validate after each iteration.

### Virtual Linux: FriBoLi, StinkyLinux, Freetz-Linux

[StinkyLinux](http://www.ip-phone-forum.de/showthread.php?p=1019861),
formerly FriBoLi, was a virtual Linux operating system for building
FRITZ!Box firmware images on Windows. Support for StinkyLinux was
discontinued, so using it for Freetz now requires extra update work.

Because of that, a newer build environment,
[Freetz-Linux](http://www.ip-phone-forum.de/showthread.php?t=194433),
was created and maintained by Silent-Tears (cinereous). Use this
environment if native Linux is not available.

The following instructions were initially adopted from
[Saphir](http://www.ip-phone-forum.de/member.php?u=118161), then
expanded and edited by many users. They are intended to stay current for
the recommended VM and Freetz versions, but most steps can also be used
for other Freetz VMs with minor changes.

### Preparation for a VM Build

See also:

- [Installing Freetz-Linux](http://www.ip-phone-forum.de/showthread.php?t=194433)
- [Installing StinkyLinux](http://wiki.ip-phone-forum.de/skript:stinkylinux)
  (obsolete)
- [Installing Freetz and Speed-to-Fritz](http://wiki.ip-phone-forum.de/skript:freetz_und_speed-to-fritz)
  (Speedport users only)
- [StinkyLinux Homepage](http://stinkylinux.slightlystinky.servebbs.net/)
  (instructions and images are outdated)

### Running a VM Build

1. Required files:
   - [VMware Player](http://www.vmware.com/products/player/overview.html)
   - [Freetz-Linux](http://www.ip-phone-forum.de/showthread.php?t=194433),
     as a VMware Player image. Older StinkyLinux VMware Player images were
     also distributed as `StinkyLinux-v1.06.7z` through mirrors.
   - Freetz sources.
   - Optional Freetz patches from the
     [Freetz forum](http://www.ip-phone-forum.de/showthread.php?t=135258).
2. Unpack Freetz-Linux under Windows with
   [7-Zip](http://downloads.sourceforge.net/sevenzip/7z442.exe) or
   [WinRAR](http://www.rarlab.com/rar/wrar380d.exe).
3. Start VMware Player. Leave the default settings at first; the player
   should be able to connect to the internet by itself. If not, configure
   internet access manually, for example:

   ```
   ifconfig eth0 192.168.178.xx netmask 255.255.255.0 broadcast 192.168.178.255
   ```

   Replace `eth0` with the configured network interface if necessary.
   `ifconfig -a` lists all network interfaces available to the VM.

4. In VMware Player, log in as user `freetz` with password `freetz`.
   You can work directly on the Freetz-Linux console or use one of these
   connection methods:
   - SSH/SCP: connect to the VM with a client such as
     [PuTTY](http://www.chiark.greenend.org.uk/~sgtatham/putty/download.html)
     or [WinSCP](http://winscp.net/eng/download.php#download2). Enter the
     VM hostname or IP address as the server name, and use the credentials
     above.
   - Samba: exchange files between Windows and Freetz-Linux through Samba.
     Enter `\\Freetz-Linux` or `\\<Freetz-Linux-IP-Address>` in Windows
     Explorer's address bar, then copy files as usual.

   These connection options are preconfigured in Freetz-Linux and should
   work out of the box. If problems occur, check the network connection,
   firewall settings, and VMware Player's network mode. By default,
   VMware Player uses bridged mode. Start by running
   `ping <IP-Address-of-Freetz-Linux>` from a Windows command prompt.

5. Check out or unpack the Freetz sources. Older documentation used
   Subversion:

   ```
   svn co URL
   ```

   Replace `freetz-1.1.x` with any valid tag, or use the development
   `/trunk` if needed. Current Freetz-NG uses Git; see the quick path
   above.

6. Optional: apply patches.
7. Change into the checked-out or unpacked Freetz directory:

   ```
   cd freetz-*/
   ```

8. Configure Freetz. The ncurses interface is similar to Linux kernel
   configuration:

   ```
   make menuconfig
   ```

9. Build the modified firmware. The original firmware, selected packages,
   and required build tools are downloaded automatically according to your
   configuration. The first build takes some time.

   ```
   unset CFLAGS CXXCFLAGS
   make
   ```

10. The new firmware image is placed in `~/freetz-*/images`, for example
    `7170_04.76freetz-devel-3790.de_20091021-180742.image`.
11. Upload the image, named like
    `<BOX_VERSION>_<ORIG_FIRMWARE_VERSION>freetz-devel-VVVV.<LANG>_YYYYMMDD-HHMMSS.image`,
    as a firmware update to the FRITZ!Box. After a successful upload, a
    secondary web interface on port 81 provides instructions to finalize
    installation. If the box is still unreachable several minutes after
    the INFO LED stopped flashing, especially if all LEDs light up at
    regular intervals, recover the original firmware. Recovery is possible
    on most box types.

### Linux

#### Required Packages

See [PREREQUISITES](../../prerequisites/README.md).

Knoppix can also be used to build firmware, so a permanent Linux
installation is not strictly required. Do not compile the mod from a FAT
or NTFS partition.

#### freetz-1.0

Older `freetz-1.0` builds required these host packages:

- `gcc`: GNU C compiler
- `g++`: GNU C++ compiler
- `binutils`: GNU assembler, linker, and binary tools
- `autoconf`: GNU-standard generator for configure scripts; helps prepare
  portable software for a platform-specific build
- `automake` 1.10 or newer: GNU-standard Makefile generator; not needed by
  every DS-Mod package, but required by packages such as privoxy. Package
  managers usually install `autoconf` as a dependency.
- `automake-1.9`: additionally required by `tar-1.15.1` from `tools`
- `libtool`: helps create static and dynamic libraries; may be needed when
  running `autoreconf`
- GNU `make` 3.81 or newer: script-controlled build system
- `bzip2`: packing and unpacking software archives
- `libncurses5-dev`: development library for ncurses, used by text-based
  user interfaces such as `make menuconfig`
- `zlib1g-dev`: development library for gzip compression
- `flex`: lex-compatible generator for lexical analysis
- `bison`: YACC-compatible parser generator
- `patch`: applies patches
- `texinfo`: creates online and print documentation from a shared source
- `gettext`: internationalization for program text
- `pkg-config`: helper tool required for building binaries and libraries;
  needed by packages such as ntfs and transmission
- `ecj-bootstrap`: Eclipse Java Compiler; in newer distributions this may
  also be `libecj-java` and `ecj`. Only needed for package `classpath`
  from version 0.95 or ds26-14.5.
- `perl`: Perl interpreter; needed for `make recover`
- `libstring-crc32-perl`: Perl module for CRC32 checksums; needed for
  `make recover`
- `intltool`: needed by `make menuconfig`

#### freetz-1.3

- `xz-utils`: packing and unpacking software archives in xz format

#### Current Development Versions and Special Packages

In addition to the packages listed for `freetz-1.0`, older development
versions and special packages needed these packages:

- `svn`: Subversion, used to check out current Freetz versions
- `ruby1.8`: object-oriented scripting language, version 1.8.6. Needed
  only for package `ruby` from `freetz-devel`. The cross-compile for
  `ruby-1.8.6` strangely needs an installed copy of itself. Some
  distributions install `/usr/bin/ruby1.8` or a similar binary, but the
  Makefile expects a binary named `ruby`. In that case, use
  `sudo ln -s ruby1.8 /usr/bin/ruby`, or run the `ln` command as `root`.
- `gawk`: GNU awk. Needed by `tools/extract-images` from `freetz-devel`,
  for example when splitting a recovery EXE to extract `urlader.image`
  and `kernel.image`. The script uses `strtonum`, which is not available
  in every awk variant.
- `python`: Python interpreter. Needed by `tools/mklibs.py` to remove
  unused symbols from libraries and save space.
- `libusb-dev`: userspace USB development library. Needed only for SANE,
  for example when connecting multifunction printers or scanners to the
  FRITZ!Box. See the related
  [forum post](http://www.ip-phone-forum.de/showpost.php?p=1075181&postcount=199).
- `realpath`: needed only by developers who use patch auto-fixing inside
  `fwmod` from ds26-15 onward through `AUTO_FIX_PATCHES` in the environment.
  If you do not know what this means, you do not need it.
- `fastjar`: implementation of the Java jar utility; needed only for
  package `classpath`
- `graphicsmagick`: includes `composite`, which can combine images; needed
  only if you want to tag the AVM web interface

#### Old Development Versions

Older development versions additionally needed:

- `automake-1.8`: specifically required by `libid3tag`; no longer required
  from Freetz 1.0 onward
- `jikes`: Java bytecode compiler; needed only for package `classpath` up
  to version 0.93 or ds26-14.4

### Installing the Required Packages

This information has moved to [PREREQUISITES](../../prerequisites/README.md).

### Build and Installation from an Archive

1. Open a shell, change to the directory containing `freetz-xxx.tar.bz2`,
   and unpack it with `tar -xvjf ds-x.y.z.tar.bz2`.
2. Optional: apply a patch.
3. Change into the unpacked Freetz directory with `cd freetz-xxx/`.
4. Choose a configuration. The ncurses interface is similar to Linux kernel
   configuration. See the `make menuconfig` documentation for option
   details.
5. Modify the firmware. In this step, the original firmware and packages
   matching the selected configuration, plus the required tool sources, are
   downloaded automatically and the modified firmware is created in three
   steps by running `make`.
6. Upload the `*.image` file as a firmware update to the box. After a
   successful upload, another web interface is available on port 81 and
   contains instructions for completing installation. If the box is still
   unreachable several minutes after the INFO LED stopped flashing, and
   especially if all LEDs periodically light up, recover the original
   firmware as described in the recovery how-to.

### coLinux, andLinux, speedLinux

See also: [Installing andLinux under Vista](http://wiki.ip-phone-forum.de/skript:andlinux).

[coLinux](http://colinux.org) can be used as an alternative. It uses fewer
resources than VMware Player. With speedLinux, everything is prepared for
Freetz or speed-to-fritz; running `./freetz` performs the required
preparation and installation steps. This note reflects the state on
2009-10-25.

Alexander Kriegisch (kriegaex) noted on 2008-02-24 that he used the
preconfigured [andLinux](http://www.andlinux.org) variant with Ubuntu
Gutsy and XFCE, optionally KDE. It can run either as a service or as an
application and ships with a simple installer. It may be somewhat slower
than pure Linux, but it allows native Linux windows alongside Windows
windows through the included Xming X server. He used it headless through
SSH/PuTTY most of the time, occasionally running Synaptic or the SciTE
editor after installing it. Building all Freetz packages from scratch,
including downloads, worked like in VMware or native Linux.

Disadvantages of coLinux, andLinux, and speedLinux:

- Only one CPU core is used on multicore processors.
- No 64-bit support.
- Major system changes, such as a special kernel, are needed when updating
  the system.

Advantages:

- Lower RAM usage than VMware.
- Native Windows windows.

### Cygwin

Freetz definitely does not build under Cygwin. Even for `ds-0.2.9`
(kernel 2.4), Linux is recommended because Cygwin can cause problems and
also leads to a very large build-time penalty.

Because Freetz itself cannot be built under Cygwin, the following legacy
description applies only to ds-mod.

A Cygwin how-to by dsl123 for compiling ds-mod is available
[here](http://www.ip-phone-forum.de/showthread.php?t=98657). To unpack
`ds-*.tar.bz2` under Windows, use only Cygwin `tar`, as described in the
how-to.

1. Download and run the Cygwin installer from
   [http://www.cygwin.com/](http://www.cygwin.com/).
2. Install Cygwin with these packages:
   - Archive -> `unzip`
   - Devel -> `gcc`, `libncurses-devel`, `make`, `patchutils`
   - Interpreters -> `perl`
   - Web -> `wget`
3. Download `ds-*.tar.bz2` into the Cygwin home directory, for example
   `C:/Cygwin/home/<Windows-username>/`.
4. Open the Cygwin shell and unpack ds-mod with `tar -xvjf ds-x.y.z.tar.bz2`.
5. Optional: apply a patch.
6. Change into the unpacked ds-mod directory with `cd ds-*/`.
7. Choose a configuration through the ncurses interface with
   `make menuconfig`.
8. Modify the firmware. The matching original firmware, packages, and tool
   sources are downloaded automatically and the modified firmware is created
   in three steps by running `make`.
9. Upload `firmware_*.image` as a firmware update to the box. After a
   successful upload, another web interface is available on port 81 with
   instructions for completing installation. If the box is still unreachable
   several minutes after the INFO LED stopped flashing, and especially if all
   LEDs periodically light up, restore the original firmware with AVM's
   `recover.exe`.

### Mac OS X

In principle, and with a few patches, a current ds-mod can work under
Mac OS X. At least `ds-0.2.9_26-14.2` was successfully made to work.

First, meet these prerequisites:

1. Create a data partition with HFS+ configured as case-sensitive.
2. Install Xcode. This provides suitable versions of tools including:
   - `gcc`
   - `g++`
   - `autoconf`
   - `automake`
   - `make`
   - [ncurses](http://de.wikipedia.org/wiki/Ncurses)
   - `zlib`
   - `flex`
   - `bison`

Additional GNU utilities are needed and can be installed through Darwin
Ports, for example:

- `gettext`
- `texinfo`
- `dos2unix`
- `gawk`
- `coreutils`
- `findutils`
- `gsed`

Additional packages may be required depending on the selected Freetz
packages.

These utilities are usually installed under names starting with `g` to
avoid conflicts with native Mac OS X utilities. Some configure scripts
expect GNU utility behavior even when calling the standard names. One
solution is to create a directory containing symlinks from standard names
to GNU utilities and add it to the search path:

```
~/gnubin $ ls -l
total 64
-rwxr-xr-x   1 enrik  enrik  106 20 Mar 17:23 as
lrwxr-xr-x   1 enrik  enrik   19 20 Mar 17:18 awk -> /opt/local/bin/gawk
lrwxr-xr-x   1 enrik  enrik   18 20 Mar 18:32 cp -> /opt/local/bin/gcp
lrwxr-xr-x   1 enrik  enrik   22 11 Apr 10:11 cpp -> /usr/local/bin/cpp-3.3
lrwxr-xr-x   1 enrik  enrik   20 11 Apr 10:11 find -> /opt/local/bin/gfind
lrwxr-xr-x   1 enrik  enrik   23 20 Mar 17:18 install -> /opt/local/bin/ginstall
-rwxr-xr-x   1 enrik  enrik  106 20 Mar 17:24 ld
lrwxr-xr-x   1 enrik  enrik   21 20 Mar 17:18 sed -> /opt/local/bin/gnused
```

The pseudo-commands `as` and `ld` are used only to pretend suitable
binutils versions to the glibc build for the kernel compiler created by
crosstool. The files look like this:

```
~/gnubin $ cat as
#! /bin/sh

# fake as version for crosstool

[ "$1" = -v ] && echo GNU assembler 2.13 || /usr/bin/as "$@"
```

```
~/gnubin $ cat ld
#! /bin/sh

# fake ld version for crosstool

[ "$1" = --version ] && echo GNU ld 2.13 || /usr/bin/ld "$@"
```

Add the directory to `PATH`:

```
~/gnubin $ PATH=$HOME/gnubin:$PATH
```

A patch for ds-mod was also required and was available here:

- [ds-0.2.9_26-14.2-macosx.patch.gz](http://www.akk.org/~enrik/fbox/ds-mod/ds-0.2.9_26-14.2-macosx.patch.gz)

This setup was only lightly tested, and no image built this way had been
tested at the time of the original note.

### Updating

After Freetz has been running on the box for some time, AVM may release a
new firmware version and Freetz development may have continued as well.
Updating works like the first installation: build a new Freetz image and
install it through the box's firmware update mechanism.

If the installation was made from a repository checkout, update that
checkout first. Older Subversion-based workflows used:

```
# Change into the checked-out Freetz directory:
cd freetz
# Update source files:
svn up
# Review package selection, change options, enable new patches, etc.:
make menuconfig
# Build image:
make
```

For current Freetz-NG Git checkouts, use the corresponding Git update
workflow, then build the finished image and upload it to the box.

### Troubleshooting Basics

- Build fails early: check for missing dependencies and host OS limitations.
- Build fails after configuration changes: revert recent options and rebuild
  incrementally.
- Device is unstable after flashing: recover to stock firmware and retry from
  a minimal configuration.

### Safety Checklist

1. Correct device model selected.
2. Correct firmware selected.
3. Recovery image available.
4. Backup completed.
5. Minimal first-image strategy applied.
