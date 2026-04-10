# Disk Management (disk-mgmt)
  - Package: [master/make/pkgs/disk-mgmt-cgi/](https://github.com/Ircama/freetz-evo/tree/master/make/pkgs/disk-mgmt-cgi/)
  - Steward: -
  - CGI: `/usr/lib/cgi-bin/disk-mgmt.cgi`
  - Init script: `/etc/init.d/rc.disk-mgmt`
  - Configuration URL: `http://fritz.box:81/cgi-bin/conf/disk-mgmt`

`Disk Management` is a comprehensive, browser-based disk, partition, and filesystem management console that runs entirely on the FRITZ!Box. It is integrated into the Freetz web server (`httpd`) as a shell CGI (`ash`/`sh`) and provides capabilities comparable to desktop tools such as GParted and Clonezilla — directly from a web browser, with no additional client software required.

## Overview

Disk Management turns the FRITZ!Box into a fully featured storage workstation. USB drives, SD cards, and loop devices attached to the router can be partitioned, formatted, cloned, imaged, migrated, diagnosed, and monitored from any device with a web browser.

All destructive operations are queued first, reviewed in a command preview, then applied in order — providing a safety workflow similar to GParted's "apply pending operations" model. A real-time streaming output panel shows every command invoked, its full argument list, and its exit status as it runs.

## Feature reference

### Partition operations

| Feature | Description |
|---|---|
| **Create partition** | Create primary, extended, or logical partitions on GPT or MBR disks. Drag-and-drop a "New partition" chip onto free space for quick creation, or "New partition with filesystem" to include filesystem type and label. |
| **Delete partition** | Queue partition deletion with safety confirmation. Context-menu "Delete all partitions" batch mode. |
| **Resize partition** | Drag the left or right edge of a partition on the graphical map to queue resize. Supports ext2/3/4 (automatic `resize2fs`), NTFS (`ntfsresize`), and FAT (`fatresize`) filesystem co-resize. Retry logic handles kernel busy-partition scenarios. |
| **Move partition** | Drag a partition onto free space (smart move) or use the move/clone chip for sector-by-sector copy. Orchestrated plan: unmount → create target → clone → delete source → mount target. |
| **Clone partition** | Same orchestrated workflow as move, but keeps the source partition intact. Supports smart (filesystem-aware via `partclone`) and sector-by-sector (`dd`/`ddrescue`) methods. |
| **Set partition name** | Update GPT partition name via `parted name`. |
| **Set partition flag** | Toggle partition flags (boot, esp, lvm, raid, etc.) via `parted set`. |

### Filesystem operations

| Feature | Description |
|---|---|
| **Create filesystem** | Supported types: `ext2`, `ext3`, `ext4`, `FAT16`, `FAT32/VFAT`, `exFAT`, `NTFS`. Optional label applied automatically after creation. |
| **Check filesystem** | Read-only check or repair mode. Tools: `e2fsck` (ext), `fsck.fat` (FAT), `fsck.exfat` (exFAT), `ntfsfix` (NTFS). |
| **Resize filesystem** | Standalone filesystem resize (without partition table change). Shrink or grow ext2/3/4, NTFS, and FAT filesystems. |
| **Set filesystem label** | Per-filesystem label tools: `e2label`/`tune2fs` (ext), `fatlabel` (FAT), `exfatlabel`/`tune.exfat` (exFAT), `ntfslabel` (NTFS). |
| **Mount / Unmount** | Mount partitions with optional filesystem type and mount options. Auto-creates mountpoint under `/var/media/ftp/`. Unmount by partition path or mountpoint. |

### Disk cloning and imaging (Clonezilla-class features)

These features use the `partition_image.sh` and `disk_migration.sh` helper scripts, which orchestrate `partclone`, `ddrescue`, `dd`, and compression tools.

| Feature | Description |
|---|---|
| **Export partition to image** | Filesystem-aware backup via `partclone` with optional compression (`gzip`, `pigz`, `lz4`, `zstd`, `bzip2`, `xz`, `lzop`). Fallback to `dd` for unsupported filesystem types. Verify option checks image integrity after export. |
| **Import (restore) from image** | Restore a `partclone` or `dd` image to a partition. Auto-detects compression format. |
| **Network send** | Stream a partition image over the network using `partclone` + netcat. Configurable TCP port. |
| **Network receive** | Receive a partition image from the network and write it to a target partition. |
| **ddrescue clone** | Resilient block-level copy to an image file using GNU `ddrescue`, with mapfile support for interrupted/resumed clones. |
| **Disk migration** | Full disk-to-disk migration: copies partition table (MBR/GPT header), clones each partition with optional per-partition verify, handles alignment, tail sectors, and wipe-before-write. Comparable to Clonezilla's disk-to-disk workflow. |
| **Partition verify** | Byte-level comparison of two partitions (read-only). |

### Diagnostics and metadata

| Feature | Description |
|---|---|
| **Graphical partition map** | Visual representation of all partitions and free space, rendered from `parted -s -m print free`. Shows filesystem type, label, size, used/free space, and mount status. |
| **Partition metadata** | Detailed metadata view: filesystem geometry, bytes used/free, device model/serial, and GPT/MBR table details. |
| **SMART diagnostics** | Display SMART health and attribute data via `smartctl -H -A`. Fallback chain: `smartctl` → `hdparm` → kernel `dmesg`. |
| **hdparm identify** | Drive identification and capability report via `hdparm -I`. |
| **GPT analysis** | GPT/MBR partition table summary via `sgdisk -p` or `gdisk -l`. |
| **Toolchain analysis** | Runtime detection report of all available disk management commands, categorized as required or optional. |

### User interface

| Feature | Description |
|---|---|
| **Operation queue** | All mutating operations are queued for review before execution. Edit parameters, reorder, or remove items before applying. |
| **Command preview** | Auto-generated preview of the exact UNIX commands that will run, with editable JSON parameters. |
| **Drag-and-drop workflow** | Intuitive chip-based drag-and-drop: drag "New partition", "Move", or "Clone" chips onto free space. Drag partition edges to resize. |
| **Context menu** | Right-click any partition for quick access to all operations via a rich context menu. |
| **Real-time streaming output** | Background job execution with live polling (500 ms interval). Each command shows a Unicode-decorated separator, the full command line, output, and exit status as it runs. |
| **Dry-run mode** | Preview all commands without executing them. Shows exactly what would happen. |
| **Safety confirmation** | Destructive operations require explicit `YES_I_UNDERSTAND` token plus per-operation confirmation modal. |
| **Multi-language UI** | Full translations: English, Italian, German. Partial: French, Spanish. Browser language auto-detection. |
| **Keyboard shortcuts** | Arrows to move to next or previous partition, `Ctrl+R` (refresh), `Ctrl+Shift+A` (analyze toolchain), `Ctrl+M` (metadata), `Ctrl+Enter` (apply queue), `Delete` (queue delete), `F1`/`?` (help). |

## Companion disk tools

Disk Management relies on a rich set of command-line tools available under  `make menuconfig` → **Disk Tools**. Together they provide a complete storage management stack:

| Tool package | Version | Key binaries | Purpose |
|---|---|---|---|
| **parted** | 3.6 | `parted`, `partprobe` | GPT/MBR partition table manipulation and kernel notify |
| **gptfdisk** | 1.0.10 | `gdisk`, `sgdisk`, `cgdisk`, `fixparts` | Advanced GPT editing, scripted operations, MBR↔GPT conversion |
| **e2fsprogs** / **e2fsprogs-ng** | 1.47.3 | `mke2fs`, `e2fsck`, `resize2fs`, `tune2fs`, `e2label` | ext2/3/4 create, check, resize, tune, label |
| **dosfstools** | 4.2 | `mkfs.fat`, `fsck.fat`, `fatlabel` | FAT12/16/32 create, check, label |
| **exfatprogs** | 1.3.2 | `mkfs.exfat`, `fsck.exfat`, `exfatlabel`, `tune.exfat` | exFAT filesystem utilities |
| **ntfs** (ntfs-3g) | 2025.2.28 | `mkntfs`, `ntfsfix`, `ntfslabel`, `ntfsresize`, `ntfsinfo` | NTFS create, check, label, resize |
| **fatresize** | snapshot | `fatresize` | Non-destructive FAT16/32 partition resize |
| **partclone** | 0.3.31 | `partclone.ext4`, `partclone.ntfs`, `partclone.fat32`, `partclone.dd`, … | Filesystem-aware block-level backup/restore |
| **ddrescue** | 1.30 | `ddrescue` | Resilient data recovery and block copy |
| **smartmontools** | 7.5 | `smartctl` | S.M.A.R.T. health monitoring |
| **hdparm** | 9.75 | `hdparm` | Drive identification and tuning |
| **util-linux** | 2.41 | `lsblk`, `blkid`, `blockdev`, `fdisk`, `mount`, `umount` | Block device enumeration, probing, mounting |
| **testdisk** | 7.2 | `testdisk`, `photorec` | Partition and file recovery |
| **fsarchiver** | 0.8.9 | `fsarchiver` | Filesystem-level archives |
| **udpcast** | 20250223 | `udp-sender`, `udp-receiver` | Multicast disk image distribution |
| **clonezilla** | 5.15.23 | Shell script collection (still under development) | Disk cloning framework (needs additional porting activities) |

## Architecture

### Backend

The CGI backend is a single POSIX shell script (`disk-mgmt.cgi`, ~10 700 lines) that:

1. Validates all inputs (device paths, partition numbers, sectors, labels, flags) against strict whitelists
2. Resolves available tools at runtime with `-ng` suffix fallback (e.g., `e2fsck-ng` before `e2fsck`)
3. Executes operations through `exec_cmd` (true streaming) or `exec_cmd_c` (captured + streaming) wrappers
4. Supports background execution via `start_job`/`poll_job` for long-running operations
5. Returns JSON responses wrapped in the standard Freetz AJAX format

### Frontend

The frontend is embedded JavaScript providing:

- Interactive SVG-like partition map with selectable and draggable elements
- Queue management with command preview (ACE editor for parameter editing)
- Real-time streaming output panel via polling
- Responsive layout with modals for confirmations and advanced operations

### Streaming execution model

When the frontend applies queued operations:

1. `callApiStreaming()` sends a `start_job` request with `job_action=<action>`
2. The backend spawns a background subshell that executes the action
3. Output is written to `/tmp/disk-mgmt-job-<token>.log` in real time
4. The frontend polls `poll_job` every 500 ms, appending new output to the display
5. Each command is decorated with Unicode separators: `══════`, `▶ label`, `── cmd:`, `── exit: N (OK/FAILED)`
6. When the job completes, a `.done` file signals final status (success/failure, return code, message)

## Operational safety

- **Queue-before-apply model**: all changes are queued, reviewed, then applied — nothing runs immediately
- **Explicit safety token**: `YES_I_UNDERSTAND` must be typed before any destructive operation
- **Per-operation confirmation**: each operation shows a confirmation modal with description
- **Dry-run mode**: toggle to preview every command that would execute, without side effects
- **Command preview**: auto-generated preview of exact shell commands, editable as JSON
- **Input validation**: device paths, sectors, labels, and options are validated with strict pattern matching
- **Stale job cleanup**: abandoned streaming job files are automatically cleaned after 1 hour

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
