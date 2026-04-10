# Disk Management (disk-mgmt)
  - Package: [master/make/pkgs/disk-mgmt-cgi/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/disk-mgmt-cgi/)
  - Steward: -
  - CGI: `/usr/lib/cgi-bin/disk-mgmt.cgi`
  - Init script: `/etc/init.d/rc.disk-mgmt`
  - Configuration URL: `http://fritz.box:81/cgi-bin/conf/disk-mgmt`

`Disk Management` (`disk-mgmt`) provides a comprehensive web interface for disk, partition, and filesystem operations, integrated into the Freetz web server (`httpd`) through a shell CGI (`ash`/`sh`).

## Main features

- Graphical device and partition map (`print free` via `parted -m`)
- Partition creation
- Drag-and-drop chips for `New partition`, `New partition with filesystem`, `Move partition`, `Clone partition`
- Partition deletion
- Partition resize (with optional ext filesystem resize)
- Partition clone workflow (unmount source, create target, clone with `ddrescue` fallback to `dd`, mount target)
- Partition move workflow (clone workflow + source deletion)
- Filesystem creation (`ext2/ext3/ext4`, `fat16/fat32/vfat`)
- Filesystem checks (`e2fsck`, `fsck.fat`)
- Filesystem label updates (`e2label`/`tune2fs`, `fatlabel`)
- GPT partition name updates (`parted name`)
- Partition flag updates (`parted set`)
- Kernel partition table refresh (`partprobe`)
- SMART diagnostics (`smartctl`) and drive identify (`hdparm`)
- GPT analysis (`sgdisk -p` or `gdisk -l`)
- Automatic detection of available tools, including `-ng` fallback binaries

## Commands invoked by the CGI backend

Below are the external commands that the CGI actually resolves and executes.

### 1) Partitioning and disk map tools

- `parted`
  - map listing: `parted -s -m <device> unit s print free`
  - partition creation: `parted -s <device> unit s mkpart ...`
  - partition deletion: `parted -s <device> rm <n>`
  - partition resize: `parted -s <device> unit s resizepart <n> <end>s`
  - partition naming: `parted -s <device> name <n> <name>`
  - partition flag update: `parted -s <device> set <n> <flag> on|off`
- `partprobe`
  - kernel partition table refresh: `partprobe <device>`
- `lsblk`
  - partition path resolution: `lsblk -ln -o PATH,PARTN <device>`

### 1b) Clone/move copy tools

- `ddrescue` (preferred when available)
  - block clone: `ddrescue -f -n <source_partition> <target_partition>`
- `dd` (fallback when `ddrescue` is not available)
  - block clone: `dd if=<source_partition> of=<target_partition> bs=1M`

### 2) FAT filesystem tools (dosfstools)

- `mkfs.fat`
  - `mkfs.fat -F 16 <partition>`
  - `mkfs.fat -F 32 <partition>`
- `fsck.fat`
  - read-only check: `fsck.fat -n <partition>`
  - check/repair: `fsck.fat -a <partition>`
- `fatlabel`
  - label update: `fatlabel <partition> <label>`

### 3) ext filesystem tools (e2fsprogs / e2fsprogs-ng)

Automatically resolved with fallback:

- `mke2fs-ng` or `mke2fs`
- `e2fsck-ng` or `e2fsck`
- `resize2fs-ng` or `resize2fs`
- `tune2fs-ng` or `tune2fs`
- `e2label-ng` or `e2label`

Main invocations:

- ext FS creation: `mke2fs(-ng) -F -t ext[2|3|4] <partition>`
- ext FS read-only check: `e2fsck(-ng) -f -n <partition>`
- ext FS check/repair: `e2fsck(-ng) -f -p <partition>`
- ext FS resize: `resize2fs(-ng) <partition>`
- ext label update: `e2label(-ng) <partition> <label>`
  - fallback: `tune2fs(-ng) -L <label> <partition>`

### 4) Advanced GPT/MBR tools

- `gdisk`
  - GPT summary: `gdisk -l <device>`
- `cgdisk`
  - detected and shown in toolchain analysis (interactive curses UI)
- `sgdisk`
  - GPT summary: `sgdisk -p <device>`
- `fixparts`
  - detected and shown in toolchain analysis (MBR/GPT repair utility)

### 5) Disk diagnostics

- `smartctl`
  - health + attributes: `smartctl -H -A <device>`
- `hdparm`
  - identify report: `hdparm -I <device>`

### 6) Filesystem/signature detection

- `blkid-util-linux` or `blkid-ng` or `blkid`
  - filesystem type detection: `blkid ... -o value -s TYPE <partition>`

## Internal shell support commands

The CGI also uses core utilities for parsing and validation:

- `command -v`
- `awk`
- `sed`
- `grep`
- `cat`
- `head`

These do not modify partitions directly; they are used to detect tools, validate input, parse output, and build JSON responses.

## Operational safety

Mutating operations require an explicit confirmation token:

- `ack=YES_I_UNDERSTAND`

The CGI also validates:

- device path (`/dev/...` and existing block device)
- partition numbers and sectors (non-negative integers only)
- labels and flags using character whitelists

These checks reduce the risk of invalid or malicious command invocations.

## Drag-and-drop workflow notes

- `New partition`: drag into a free region for quick create with default values.
- `New partition with filesystem`: drag into a free region to include Role, Filesystem and Partition name from the form.
- `Move partition` chip: drag into a free region to queue an orchestrated move plan:
  - unmount source partition,
  - create target partition,
  - clone source to target (`ddrescue` if available, otherwise `dd`),
  - delete source partition,
  - mount target partition.
- `Clone partition` chip: same plan without deleting the source partition.
- Classic drag remains available: drag partition edges for resize and drag a partition into free space for move planning.
