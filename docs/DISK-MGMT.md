# Freetz-EVO — The Disk Management Subsystem

Freetz-EVO integrates a comprehensive set of Unix storage and filesystem tools into the firmware. While these tools provide the building blocks for advanced disk management, performing complete operations often requires executing multiple low-level commands in the correct sequence, with the appropriate options and safety checks.

The Disk Management subsystem provides a high-level interface to these tools. Through a web-based frontend, complex disk operations are expressed as user-oriented actions and translated into the corresponding sequences of low-level commands. This makes advanced storage management accessible without requiring the user to know the individual tools, their syntax, or the sequence in which they must be executed.

A FRITZ!Box can therefore perform operations such as partitioning, formatting, cloning, imaging, migration, diagnosis, monitoring, and repair of USB drives, SD cards, and loop devices directly from a web browser.

All disk management tools are integrated into the custom firmware and remain available from the command line, while the frontend provides a higher-level interface for composing and executing complete operations. The centrepiece is the **Disk Management CGI** (`disk-mgmt`) — a comprehensive, browser-based interface providing capabilities comparable to desktop tools such as GParted and Clonezilla, directly on the box with no additional client software required.

All configuration options related to disk management are included in the dedicated **Packages → Disk Tools** section of `make menuconfig`. The Disk Management CGI itself is also enabled under **Packages → Web tools**.

---

## The Disk Management CGI

Disk Management turns the FRITZ!Box into a fully featured storage management system. It is implemented as a single large shell script ([source on GitHub](https://github.com/Ircama/freetz-evo/blob/master/docs/make/disk-mgmt.md)), integrated into the Freetz web server as a shell CGI and providing, through an embedded JavaScript frontend, an interactive graphical environment for all disk operations. The toolchain requires uClibc 1.0.58 or newer.

All operations are queued first, reviewed through editable operation parameters and an auto-generated command preview, then applied in order — providing a safety workflow similar to GParted's "apply pending operations" model. A real-time streaming output panel shows every command invoked, its full argument list, and its exit status as it runs.

### Partition operations

Disk Management supports the full lifecycle of partition table management. Partitions can be created (primary, extended, or logical on GPT or MBR disks) via drag-and-drop: drag a "New partition" chip onto free space for quick creation, or "New partition with filesystem" to include filesystem type and label. Deletion is queued with safety confirmation, and a context-menu "Delete all partitions" is also available.

**Resizing** is performed by dragging partition edges on the graphical map. For ext2/3/4 filesystems, a `resize2fs` co-resize is triggered automatically; NTFS uses `ntfsresize` and FAT uses `fatresize`, with retry logic for kernel busy-partition scenarios.

**Moving** a partition is done by dragging it onto free space. The orchestrated plan is: unmount → create target → clone/copy → delete source → mount target. Cloning follows the same workflow but keeps the source partition intact, supporting both filesystem-aware (`partclone`) and sector-by-sector (`dd`/`ddrescue`) methods. For precise in-disk relocation, a dedicated **in-place move modal** exposes the `sfdisk --move-data` path directly, allowing the user to specify the exact target sector and inspect low-level move constraints.

MBR extended-container boundary moves are also supported through a scripted `sfdisk` path when the container itself must be shifted rather than just the logical partitions inside it. GPT partition names are set via `parted name`; partition flags (boot, esp, lvm, raid, etc.) are toggled via `parted set`.

### Filesystem operations

Supported filesystem types for creation are `ext2`, `ext3`, `ext4`, `FAT16`, `FAT32/VFAT`, `exFAT`, and `NTFS`, with optional labels applied automatically. Filesystem checks use the appropriate tool per filesystem: `e2fsck` for ext, `fsck.fat` for FAT, `fsck.exfat` for exFAT, and `ntfsfix` for NTFS — in both read-only and repair modes. Standalone filesystem resize (without changing the partition table) is supported for ext2/3/4, NTFS, and FAT. Label management uses per-filesystem tools: `e2label`/`tune2fs` (ext), `fatlabel` (FAT), `exfatlabel`/`tune.exfat` (exFAT), `ntfslabel` (NTFS).

Mount and unmount operations are integrated into the UI, with optional filesystem type and mount options, auto-creating mountpoints under `/var/media/ftp/`.

### Partition-table and identity operations

The partition table can be backed up as a `sfdisk --dump` text export and restored later to rebuild a disk layout. The table type can be converted between `gpt`, `msdos`, and others via `parted mklabel`. Legacy MBR type bytes are rewritten with `sfdisk --part-type`.

UUID management is fully covered: partition UUIDs are displayed, regenerated, or set with `sfdisk --part-uuid`; disk UUIDs and disk IDs are handled via `sfdisk --disk-id`. Stale filesystem, RAID, or LVM signatures are removed with `wipefs -a`. Partition ordering is normalized with `sfdisk --reorder`, structural issues are caught with `sfdisk --verify`, and the kernel partition view is refreshed on demand via `partprobe`.

### Disk cloning and imaging

These Clonezilla-class features use the `partition_image.sh` and `disk_migration.sh` helper scripts, which orchestrate `partclone`, `ddrescue`, `dd`, and compression tools.

Partition export produces filesystem-aware images via `partclone` with optional compression (`gzip`, `pigz`, `lz4`, `zstd`, `bzip2`, `xz`, `lzop`). Supported filesystems include ext, FAT, exFAT, NTFS and, when the matching backend is installed, XFS, Btrfs, F2FS, HFS+, APFS and more. Raw sector-based export via `partclone.dd` is available for unknown or intentionally sector-based workflows. A verify mode checks image integrity after export. Import restores a `partclone` or raw image to a partition, with compression format auto-detected.

**Network cloning** is also supported: a partition image can be streamed over the network using the same `partition_image.sh` engine (configurable TCP port), either sent from or received on the box, enabling direct machine-to-machine transfer without intermediate storage. For resilient block-level recovery, GNU `ddrescue` is invoked with mapfile support, allowing interrupted clones to be resumed.

**Disk migration** performs a full disk-to-disk workflow: it copies the partition table (MBR/GPT header), clones each partition with optional per-partition verify, and handles alignment, tail sectors, and wipe-before-write — comparable to Clonezilla's disk-to-disk mode. A partition verify operation performs a byte-level comparison of two partitions.

### Diagnostics and metadata

The **graphical partition map** renders all partitions and free space from `parted -s -m print free`, showing filesystem type, label, size, used/free space, mount status, and enriched tooltip data. A **detailed metadata view** provides partition geometry, bytes used/free, model/vendor/serial, logical sector size, partition UUID/PARTUUID, disk UUID/ID, type IDs, and GPT/MBR table details.

SMART health and attribute data is displayed via `smartctl -H -A`, with a fallback chain to `hdparm` and kernel `dmesg`. A **SMART self-test** can be started from the UI, with polling of the self-test log until completion or timeout. A **badblocks scan** runs a read-only `badblocks -sv` pass for low-level media inspection. Drive identification uses `hdparm -I`. GPT partition table summary uses `sgdisk -p` or `gdisk -l`. Low-level geometry is dumped via `sfdisk -g`. A **toolchain analysis** panel reports runtime availability of all required and optional backend commands.

### User interface features

The frontend is embedded JavaScript providing an interactive SVG-like partition map with selectable and draggable elements, queue management with parameter editing and read-only command preview regeneration, dedicated modal flows for advanced jobs, a real-time streaming output panel via polling, and a responsive layout with confirmations, diagnostics panels, built-in help, and translations.

The UI provides a rich interactive environment for managing disk operations:

- **Context menu**: right-click any partition for quick access to all operations.
- **Drag-and-drop**: chip-based drag-and-drop for new partitions, moves, clones, and partition resize by dragging edges.
- **Advanced modals**: dedicated modal flows for `sfdisk --move-data`, partition-table backup/restore, UUID changes, partclone export/import, network send/receive, ddrescue imaging, and disk migration.
- **Operation queue**: all mutating operations are queued for review, with the ability to reopen, edit parameters, reorder, or remove items before applying.
- **Command preview**: read-only preview of the exact UNIX commands that will run, regenerated automatically from the queued operation parameters.
- **Real-time streaming output**: background job execution with live polling every 500 ms; each command shows a Unicode-decorated separator, the full command line, output, and exit status.
- **Dry-run mode**: preview all commands without executing them.
- **Safety confirmation**: destructive operations require an explicit `YES_I_UNDERSTAND` token plus per-operation confirmation.
- **Multi-language UI**: full translations in English, Italian, and German; partial French and Spanish; browser language auto-detection.
- **Keyboard shortcuts**: arrows to move between partitions, `Ctrl+R` (refresh), `Ctrl+Shift+A` (analyze toolchain), `Ctrl+M` (metadata), `Ctrl+Enter` (apply queue), `Delete` (queue delete), `F1`/`?` (help).

### Creating the Freetz-EVO external disk

#### Storage layout on FRITZ!Box devices

Most FRITZ!Box devices provide two distinct storage areas: a very limited firmware area (typically a few tens of MB) and a larger data area (typically a few hundred MB) accessible at `/var/media/ftp/uStor01`. To overcome the tight firmware space constraint, Freetz supports package *externalization*: packages are installed on a separate filesystem and each file is linked back into the firmware area through symbolic links, so the system sees them in the expected locations without consuming firmware flash.

The recommended approach for a large Freetz-EVO installation is to keep only the bare minimum non-externalized — in particular `dropbear` and `zlib` should always remain in the firmware area, so that SSH access to the device is available even if the external disk is not present or not yet mounted. Everything else can and should be externalized.

The internal data area at `/var/media/ftp/uStor01` is too limited to host a full Freetz-EVO installation. An **external USB drive** (preferably a USB SSD, or a USB HDD) is the recommended externalization target. The external drive is also the right place for a swap partition if swap is desired — creating a swap file on `/var/media/ftp/uStor01/swapfile` is discouraged, as it would cause continuous wear on the device's internal NAND flash.

#### The "Freetz-EVO disk setup" wizard

Disk Management provides a dedicated disk context-menu option — **Freetz-EVO disk setup** — that guides the user through creating a complete, ready-to-use partition layout for Freetz-EVO on an attached USB drive. Selecting it opens a setup modal with the following fields:

- **Partition table**: GPT (recommended) or MBR.
- **Alignment**: optimal 1 MiB boundaries are pre-selected for best performance.
- **Delete existing partitions first**: if checked, all existing partitions on the disk are erased before creating the new layout.
- **Mount all partitions after creation**: if checked, each newly created partition is mounted immediately after formatting.
- **Partitions to create**: an editable list of partitions (name/label, filesystem, size, and mountpoint), pre-populated with the recommended Freetz-EVO layout. Partitions can be resized, removed, or supplemented with additional entries using the **+ Add partition** button.
- **Disk layout preview**: a live visual bar showing the proportional placement and size of each defined partition and any remaining free space.

Clicking **Run setup** translates the defined layout into an ordered operation queue, which can be reviewed and then executed by clicking **Apply pending operations**.

#### Default partition layout

The pre-populated layout creates three partitions:

**`NTFS_Data`** (NTFS) — a Windows-compatible volume for file exchange between the FRITZ!Box and a PC. Because NTFS is readable and writable on both Linux and Windows without additional drivers, this partition serves as a convenient transfer area for large files that need to be moved between the box and a Windows machine.

**`MediaServer`** (ext4) — a Linux-native volume for multimedia assets such as audio libraries, video collections, and images. The ext4 filesystem offers better performance and reliability for large file workloads than NTFS or FAT. This partition is the natural home for MPD music libraries, Gerbera media server content, and similar storage-intensive data.

**`FRITZBOX`** (ext4) — the core Freetz-EVO partition, hosting two subdirectories: `external/` (the externalization directory, mounted by Freetz as the package store) and `swap` (the swap file or swap partition). All sizes are adjustable in the setup modal; the defaults provide a balanced starting point that can be tailored to the available disk.

#### What the wizard queues

When the setup runs, it queues one operation per partition plus a table initialization step. For the default three-partition layout, the queue contains seven operations: (1) initialize a GPT partition table on the disk; (2–3) create the `NTFS_Data` partition and mount it; (4–5) create the `MediaServer` ext4 partition, format it with `mke2fs`, and mount it; (6–7) create the `FRITZBOX` ext4 partition, format it, and mount it. Each step is decorated in the streaming output panel with its full command line and exit status, so the exact `parted`, `mke2fs`, and `mount` invocations are visible as they run.

#### Bootstrap procedure

Because the full Disk Management tool suite may exceed the firmware flash capacity, setting up the external disk for a full Freetz-EVO installation is a two-phase process.

**Phase 1 — bootstrap firmware.** Build a minimal Freetz-EVO image via `make menuconfig` that includes Disk Management and all desired packages configured as *external*, except `zlib` and `dropbear` which must stay internal. Set the external directory to the device's internal storage: `/var/media/ftp/uStor01/external`. Flash this image using `tools/push_firmware`.

Boot the device and open the web interface at `http://fritz.box:81`. Upload the externalization archive to the device's internal storage using the web update pages at `http://fritz.box:81/cgi-bin/update/firmware.cgi` (firmware) and `http://fritz.box:81/cgi-bin/update/external.cgi` (external file), writing the externalization to `/var/media/ftp/uStor01/external`. Connect the target USB drive to the device.

Open Disk Management, select the external USB drive, and choose **Freetz-EVO disk setup** from the disk context menu. Configure the partition sizes as needed, then click **Run setup** and **Apply** to create and format the partitions.

**Phase 2 — full firmware.** Build the complete Freetz-EVO image via `make menuconfig`, selecting all required packages and marking them as external (except `zlib` and `dropbear`). The externalization archive for a large installation can approach or exceed 2 GB. In the Freetz settings page at `http://fritz.box:81/cgi-bin/conf/mod`, change the external directory to `/var/media/ftp/FRITZBOX/external`. Install the new firmware and its externalization over SSH using `tools/ssh_firmware_update.py`.

---

## Quick start

1. In `make menuconfig`, enable **Disk Management CGI** under **Packages → Web tools** and the desired disk tools under **Packages → Disk Tools**.
2. Build and flash the firmware image.
3. Navigate to `http://fritz.box:81/cgi-bin/conf/disk-mgmt`.
4. Click **Refresh devices** to scan attached storage.
5. Click a disk in the device strip to load its partition map.
6. Queue operations via drag-and-drop, context menu, or the toolbar form.
7. Review the operation queue and command preview.
8. Type `YES_I_UNDERSTAND` in the safety field.
9. Click **Apply** to execute all queued operations with live streaming output.

---

## The disk tools stack

Disk Management relies on a rich set of command-line tools available under `make menuconfig` → **Packages → Disk Tools**. Together they form a complete storage management stack.

### dosfstools 4.2

dosfstools provides FAT filesystem utilities: `mkfs.fat` (create FAT12/16/32 filesystems), `fsck.fat` (check and repair FAT filesystems), and `fatlabel` (read and set FAT volume labels). Each tool can be individually selected in `make menuconfig`.

### E2fsprogs 1.47.4

E2fsprogs is the standard collection for ext2/ext3/ext4 filesystem management. In Freetz-EVO it requires either the `Remove e2fsprogs` AVM patch or the `-ng` suffix mode (the latter is forced when the AVM patch is not active, renaming binaries as `e2fsck-ng`, `mke2fs-ng`, etc. to avoid conflicts with AVM's bundled e2fsprogs). The `make menuconfig` tree organizes its tools into groups:

**Checking tools** — `e2fsck` (filesystem check and repair) and `fsck` (generic filesystem checker front-end).

**Making tools** — `mke2fs` (create ext2/ext3/ext4 filesystems) and `mklost+found` (create a `lost+found` directory).

**Tuning tools** — `tune2fs` (adjust tunable filesystem parameters), `dumpe2fs` (dump filesystem superblock and block-group information), `chattr`/`lsattr` (change/list extended file attributes), `e2label` (read/set ext2/3/4 volume labels), and `findfs` (find a filesystem by label or UUID).

**Debugging tools** — `e2image` (save critical ext2/3/4 filesystem metadata to a file), `e2undo` (replay an undo log), `debugfs` (interactive ext2/3/4 filesystem debugger), and `logsave` (save the output of a command to a logfile).

**Repair and misc. tools** — `badblocks` (scan for bad blocks on a device), `filefrag` (report on file fragmentation), `e2freefrag` (report free-space fragmentation), `uuidd` (UUID daemon), and `uuidgen` (generate new UUIDs).

**Resize tools** — `resize2fs` (resize ext2/3/4 filesystems). Static or dynamic linking of e2fsprogs libraries is selectable in `make menuconfig`.

**blkid** — identify block devices by UUID, label, or filesystem type (renamed `blkid-ng` when the AVM patch is not active).

### exfatprogs 1.3.2

exfatprogs provides exFAT filesystem utilities: `mkfs.exfat` (create exFAT filesystems), `fsck.exfat` (check and repair), `exfatlabel` (read/set labels), and `tune.exfat` (adjust exFAT parameters).

### f2fs-tools 1.9.0

f2fs-tools provides Flash-Friendly File System support: `mkfs.f2fs` (create F2FS filesystems) and `fsck.f2fs` (check and repair).

### fatresize

fatresize (snapshot 2026-04-03, master branch) provides non-destructive resize of FAT16 and FAT32 partitions — the FAT-specific backend used by the Disk Management CGI when co-resizing a FAT filesystem with a partition boundary change.

### hdparm 9.65

hdparm provides drive identification (`hdparm -I`), low-level ATA/SATA parameter tuning, and serves as a fallback SMART data source when `smartctl` is unavailable. The Disk Management CGI uses it for drive identification and as part of the SMART diagnostics fallback chain.

### NTFS-3G 2022.10.3

NTFS-3G provides full read/write NTFS support. The `ntfs-3g` mount binary enables NTFS volume mounting; the `ntfsprogs` tools set covers: `mkntfs` (create NTFS), `ntfscat` (print files to stdout), `ntfsclone` (clone NTFS volumes), `ntfscluster` (identify files in a cluster range), `ntfscmp` (compare two NTFS volumes), `ntfscp` (copy a file into an NTFS volume), `ntfsfix` (fix common NTFS inconsistencies), `ntfsinfo` (display NTFS volume information), `ntfslabel` (read/set NTFS volume labels), `ntfsls` (list directory contents), `ntfsresize` (resize NTFS filesystems), and `ntfsundelete` (recover deleted NTFS files). Each tool is individually selectable in `make menuconfig`.

### parted 3.6

parted is the primary partition table manipulation backend used throughout the Disk Management CGI. It provides `parted` (interactive and scriptable GPT/MBR partition editor) and `partprobe` (inform the kernel of partition table changes). The CGI drives parted to create, delete, resize, move, and flag partitions, as well as to generate the partition map data used by the graphical UI.

### gptfdisk 1.0.10

gptfdisk provides GPT-aware partitioning and recovery tools complementing classic fdisk-like workflows. Tools included: `gdisk` (GPT fdisk interactive utility), `cgdisk` (curses-based GPT partition editor), `sgdisk` (scriptable GPT partition manipulator — used by Disk Management for UUID operations and GPT analysis), and `fixparts` (convert or repair damaged MBR partition tables).

### Smartmontools 7.2/7.5

Smartmontools provides `smartctl`, the S.M.A.R.T. health monitoring tool. From the Freetz web interface it shows the drive model, storage capacity, overall health assessment, current temperature, runtime hours, power-on count, and all available SMART attribute values. The Disk Management CGI also uses it for inline SMART health checks and self-test execution. Note that opening the status page spins up a parked drive; this is expected. Version 7.5 requires GCC 4.7 or newer (it is built as C++11); version 7.2 is available for older toolchains. The desired version is selectable in `make menuconfig`.

### testdisk 7.2

testdisk provides partition and file recovery tools for damaged or accidentally modified storage media. Tools included: `testdisk` (interactive partition recovery and repair), `photorec` (file recovery by file-signature matching), and `fidentify` (identify a file type by signature database). A GCC-version-specific build patch (`001-fix-gpt-sys-types-static-init.patch`) is applied to work around a static-initializer restriction in GCC 4.6.

### util-linux (Linux disk utilities)

util-linux is available in two versions selectable in `make menuconfig`. The **legacy 2.27.1** build provides only `blkid-util-linux` and is intended for FRITZ!Box devices with AVM firmware 06.5X and earlier (requires `FREETZ_PATCH_FREETZMOUNT`). The **modern 2.41** build — the default for firmware 07.XX and later — provides a much broader set of utilities for full disk and filesystem management:

- `blkid` — identify block devices (renamed `blkid-ng`)
- `fdisk` — partition table manipulator (renamed `fdisk-ng`)
- `sfdisk` — scriptable partition table tool (renamed `sfdisk-ng`)
- `blockdev` — call block-device ioctls (renamed `blockdev-ng`)
- `partx`/`addpart`/`delpart`/`resizepart` — partition table helpers
- `findfs` — find filesystem by label or UUID
- `wipefs` — wipe filesystem and partition signatures
- `losetup` — manage loop devices (renamed `losetup-ng`)
- `mkswap` — create swap area (renamed `mkswap-ng`)
- `swapon`/`swapoff` — enable/disable swap (renamed to `-ng`)
- `lsblk` — list block devices
- `lsfd` — list open file descriptors
- `cfdisk` — curses-based partition editor
- `findmnt` — find mounted filesystems
- `unshare` — run program with unshared namespaces (renamed `unshare-ng`)
- `uuidgen` — create UUIDs (renamed `uuidgen-ng`)
- `uuidparse` — parse and format UUIDs
- `lastlog2` — display recent login information
- `mountpoint` — check if a directory is a mount point

All binaries are installed with a `-ng` or `-util-linux` suffix to avoid conflicts with BusyBox equivalents, allowing both implementations to coexist. The modern 2.41 build requires uClibc 1.0.58 or newer. All relevant `sfdisk` and `lsblk` operations in the Disk Management CGI use these utilities.

### ncdu and ncdu-cgi — disk usage analysis

**ncdu** 1.19 is an ncurses-based disk usage analyzer. It provides a fast, interactive terminal view of storage consumption on any mounted filesystem, allowing the user to drill down directory trees and identify large files or directories. It is a natural companion to the Disk Management CGI: after partitioning and formatting a disk, or before a cloning operation, `ncdu` gives a quick overview of what is actually occupying the space.

**ncdu-cgi** integrates ncdu into the Freetz web interface as a browser-accessible usage analysis tool, accessible from the configuration pages without opening an SSH session. Both are EVO-only packages.

---

## Data migration and disaster recovery tools

A dedicated submenu under **Packages → Disk Tools → Data Migration and Disaster Recovery** groups the tools oriented towards cloning, imaging, and network-based disk distribution.

### partclone 0.3.31

partclone provides filesystem-aware block-level backup and restore, used as the primary imaging engine by the Disk Management CGI. It exports only the used blocks of a filesystem (rather than every sector), producing smaller images and faster transfers than raw `dd`. Per-filesystem backends are compiled as separate binaries (`partclone.ext4`, `partclone.ntfs`, `partclone.fat32`, `partclone.exfat`, `partclone.f2fs`, `partclone.dd`, etc.) so that only the required backends need be selected. Additional tools include `partclone.info` (display image metadata), `partclone.restore` (restore an image), `partclone.chkimg` (verify image integrity), `partclone.imager` (raw imaging), and `partclone.ntfsfixboot` (NTFS boot record fixup after restore). Requires uClibc 1.0.58 or newer.

### GNU ddrescue 1.30

GNU ddrescue (`gddrescue`) is a robust data-recovery and block-copy tool with mapfile support, allowing interrupted copies to be resumed from where they left off rather than restarted from scratch. This makes it especially suited to copying failing drives, where sectors may become unreadable during the transfer. Tools included: `ddrescue` (the main copy tool) and `ddrescuelog` (manipulate and display mapfiles). The Disk Management CGI uses it for the ddrescue clone workflow and as a resilient alternative to `dd` for sector-by-sector partition operations.

### fsarchiver 0.8.9

fsarchiver is a filesystem-level archiver that saves the content of a filesystem to a compressed archive file, preserving all POSIX attributes, extended attributes, and filesystem metadata. Unlike `partclone`, it can restore to a different-size partition and to different filesystem types (subject to driver availability). In Freetz-EVO, compression support is intentionally conservative to keep dependencies small (lzma/lzo/lz4/zstd disabled). Requires uClibc 1.0.58 or newer.

### udpcast 20250223

udpcast is a multicast transfer tool for one-to-many disk image distribution. `udp-sender` broadcasts a data stream (typically a disk image piped through it) over UDP multicast; `udp-receiver` on multiple machines receives the same stream simultaneously, enabling parallel deployment of an image to an entire cluster in the time it takes to image a single machine. In the Disk Management context, udpcast provides the transport layer for multicast disk image distribution scenarios.

---

## All disk tools at a glance

| Tool package | Version | Key binaries | Purpose |
|---|---|---|---|
| **Disk Management CGI** | — | `disk-mgmt.cgi` | Browser-based disk console (partition, format, clone, diagnose) |
| **dosfstools** | 4.2 | `mkfs.fat`, `fsck.fat`, `fatlabel` | FAT12/16/32 create, check, label |
| **e2fsprogs** / **e2fsprogs-ng** | 1.47.4 | `mke2fs`, `e2fsck`, `resize2fs`, `tune2fs`, `e2label`, `blkid`, `debugfs`, … | ext2/3/4 create, check, resize, tune, label, debug |
| **exfatprogs** | 1.3.2 | `mkfs.exfat`, `fsck.exfat`, `exfatlabel`, `tune.exfat` | exFAT filesystem utilities |
| **f2fs-tools** | 1.9.0 | `mkfs.f2fs`, `fsck.f2fs` | Flash-Friendly File System utilities |
| **fatresize** | 2026-04-03 snapshot | `fatresize` | Non-destructive FAT16/32 resize |
| **hdparm** | 9.65 | `hdparm` | Drive identification, ATA tuning, SMART fallback |
| **NTFS-3G** | 2022.10.3 | `ntfs-3g`, `mkntfs`, `ntfsfix`, `ntfslabel`, `ntfsresize`, `ntfsclone`, … | NTFS mount, create, check, label, resize, recover |
| **parted** | 3.6 | `parted`, `partprobe` | GPT/MBR partition table manipulation and kernel notify |
| **gptfdisk** | 1.0.10 | `gdisk`, `sgdisk`, `cgdisk`, `fixparts` | Advanced GPT editing, scripted operations, MBR↔GPT conversion |
| **Smartmontools** | 7.2/7.5 | `smartctl` | S.M.A.R.T. health monitoring |
| **testdisk** | 7.2 | `testdisk`, `photorec`, `fidentify` | Partition and file recovery |
| **util-linux** | 2.41 (modern) | `lsblk`, `blkid-ng`, `fdisk-ng`, `sfdisk-ng`, `wipefs`, `losetup-ng`, … | Block device enumeration, partition scripting, mounting |
| **partclone** | 0.3.31 | `partclone.ext4`, `partclone.ntfs`, `partclone.fat32`, `partclone.dd`, … | Filesystem-aware block-level backup/restore |
| **GNU ddrescue** | 1.30 | `ddrescue`, `ddrescuelog` | Resilient data recovery and block copy with mapfile |
| **fsarchiver** | 0.8.9 | `fsarchiver` | Filesystem-level archives with metadata preservation |
| **udpcast** | 20250223 | `udp-sender`, `udp-receiver` | Multicast disk image distribution |
| **ncdu** | 1.19 | `ncdu` | ncurses disk usage analyzer for mounted filesystems |
| **ncdu-cgi** | — | CGI page | Browser-based disk usage analysis via Freetz web interface |
