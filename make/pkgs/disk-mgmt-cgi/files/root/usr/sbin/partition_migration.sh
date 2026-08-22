#!/bin/sh

# ==============================================================================
# PARTITION MIGRATION / CLONE SCRIPT
# Version: 3.0 | partclone v0.3.31 | POSIX ASH compliant
# ==============================================================================

# ==============================================================================
# DEFAULTS
# ==============================================================================

DEVICE=""           # -d  target disk device             (required)
SOURCE_DEVICE=""    # -D  source disk device             (required)
SOURCE_PART=""      # -p  source partition node          (required)
SOURCE_PARTNUM=""   # -n  source partition number        (required)
START=""            # -S  target start sector            (required)
END=""              # -E  target end sector              (required)
TARGET_MOUNT=""     # -t  mount point after operation    (required if -o)

MOVE_MODE=0         # -M  flag: move (delete source after clone)
CLONE_MODE="smart"  # -c  smart | dd
ALIGN_BYTES=1048576 # -a  512 | 4096 | 1048576
UMOUNT_BEFORE=0     # -u  flag: unmount before starting
MOUNT_AFTER=0       # -o  flag: mount target when done
PARTCLONE_EXTRA=""  # -x  extra options passed to partclone verbatim
PARTCLONE_LOGFILE="/tmp/partclone.log"  # -L  logfile path for partclone (empty = disable)
SKIP_WRITE_ERROR=0  # -W  1=pass --skip_write_error to partclone (continue on write errors)
STEP_DELAY=1        # -w  seconds to wait between steps (0 = none)
VERIFY_CLONE=0      # -V  flag: run partclone.chkimg verify after clone
FORCE_FSTYPE=""     # -f  force filesystem type (skip auto-detection)
DRY_RUN=0           # -r  flag: simulate only, no writes
COMPARE_PART=""     # -Z  compare mode: compare SOURCE_PART with this partition (read-only)
FAT_FSCK_PASSES=2   # -F  number of pre-clone fsck passes for FAT (0 = skip)

# ==============================================================================
# HELPER FUNCTIONS (defined before usage() so usage can call hr)
# ==============================================================================

hr() { echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; }

die() { echo "❌  FATAL: $*" >&2; exit 1; }

run() {
    # Executes a command, or in dry-run mode prints it and returns 0.
    if [ "$DRY_RUN" -eq 1 ]; then
        printf '\033[33m\U1F538  [DRY-RUN]\033[0m %s\n' "$*"
        return 0
    fi
    printf '\033[36m── cmd:\033[0m \033[1;33m%s\033[0m\n' "$*"
    "$@"
}

step_pause() {
    [ "${STEP_DELAY:-0}" -le 0 ] && return
    # Only show countdown if delay > 3 seconds; otherwise sleep silently
    if [ "${STEP_DELAY:-0}" -le 3 ]; then
        sleep "$STEP_DELAY"
        return
    fi
    remaining=$STEP_DELAY
    printf "⏳  Continuing in "
    while [ "$remaining" -gt 0 ]; do
        if [ "$remaining" -eq 1 ]; then
            printf "1 second… "
        else
            printf "%d seconds… " "$remaining"
        fi
        sleep 1
        remaining=$(( remaining - 1 ))
    done
    echo ""
}

align_up() {
    # align_up VALUE MULTIPLE → smallest int >= VALUE that is a multiple of MULTIPLE
    val=$1; mul=$2
    rem=$(( val % mul ))
    [ "$rem" -eq 0 ] && echo "$val" || echo $(( val - rem + mul ))
}

# Patch FAT BPB total_sectors_32 if it exceeds actual partition size.
# Prevents partclone.vfat "out of boundary" read errors on partitions
# whose superblock was not updated after a shrink (stale BPB).
fat_fix_total_sectors() {
    _p="$1"
    _psec512=$(blockdev --getsz "$_p" 2>/dev/null)
    if [ -z "$_psec512" ] || [ "$_psec512" -le 0 ] 2>/dev/null; then
        _dev=$(basename "$_p")
        _psec512=$(cat /sys/class/block/"$_dev"/size 2>/dev/null)
    fi
    [ -z "$_psec512" ] || [ "$_psec512" -le 0 ] 2>/dev/null && return
    _bps=$(dd if="$_p" bs=1 skip=11 count=2 2>/dev/null |
        hexdump -v -e '/1 " %u"' 2>/dev/null |
        awk '{print ($1+0) + ($2+0)*256}')
    ( [ -z "$_bps" ] || [ "$_bps" -le 0 ] ) 2>/dev/null && _bps=512
    _pfat_sec=$(awk -v p="$_psec512" -v b="$_bps" 'BEGIN { printf "%.0f", p * 512 / b }')
    _bpb_sec=$(dd if="$_p" bs=1 skip=32 count=4 2>/dev/null |
        hexdump -v -e '/1 " %u"' 2>/dev/null |
        awk '{print ($1+0) + ($2+0)*256 + ($3+0)*65536 + ($4+0)*16777216}')
    [ -z "$_bpb_sec" ] && return
    if [ "$_bpb_sec" -gt "$_pfat_sec" ] 2>/dev/null; then
        _b0=$(( _pfat_sec        & 0xff ))
        _b1=$(((_pfat_sec >>  8) & 0xff ))
        _b2=$(((_pfat_sec >> 16) & 0xff ))
        _b3=$(((_pfat_sec >> 24) & 0xff ))
        _hex=$(printf "\\$(printf '%03o' "$_b0")\\$(printf '%03o' "$_b1")\\$(printf '%03o' "$_b2")\\$(printf '%03o' "$_b3")")
        printf '%s' "$_hex" | dd of="$_p" bs=1 seek=32 count=4 conv=notrunc 2>/dev/null
        _bbsec=$(dd if="$_p" bs=1 skip=50 count=2 2>/dev/null |
            hexdump -v -e '/1 " %u"' 2>/dev/null |
            awk '{print ($1+0) + ($2+0)*256}')
        if [ -n "$_bbsec" ] && [ "$_bbsec" -gt 0 ] 2>/dev/null; then
            printf '%s' "$_hex" | dd of="$_p" bs=1 seek=$(( _bbsec * _bps + 32 )) count=4 conv=notrunc 2>/dev/null
        fi
        echo "     ⚠️  FAT BPB patched: total_sectors ${_bpb_sec} → ${_pfat_sec}"
    fi
}

# Patch FAT BPB hidden_sectors field at offset 28 with the new partition start sector.
# Required after clone/move to a different disk position: hidden_sectors must match
# the new LBA start so that the FAT driver and fatresize locate the volume correctly.
# Arguments: PARTITION_PATH  NEW_START_SECTOR_512
fat_fix_hidden_sectors() {
    _p="$1"
    _new_start="$2"
    [ -z "$_new_start" ] && return
    _b0=$(( _new_start        & 0xff ))
    _b1=$(((_new_start >>  8) & 0xff ))
    _b2=$(((_new_start >> 16) & 0xff ))
    _b3=$(((_new_start >> 24) & 0xff ))
    _hhex=$(printf "\\$(printf '%03o' "$_b0")\\$(printf '%03o' "$_b1")\\$(printf '%03o' "$_b2")\\$(printf '%03o' "$_b3")")
    printf '%s' "$_hhex" | dd of="$_p" bs=1 seek=28 count=4 conv=notrunc 2>/dev/null
    # Also patch backup BPB (FAT32 only: backup sector index at offset 50)
    _hbps=$(dd if="$_p" bs=1 skip=11 count=2 2>/dev/null |
        hexdump -v -e '/1 " %u"' 2>/dev/null |
        awk '{print ($1+0) + ($2+0)*256}')
    ( [ -z "$_hbps" ] || [ "$_hbps" -le 0 ] ) 2>/dev/null && _hbps=512
    _hbbsec=$(dd if="$_p" bs=1 skip=50 count=2 2>/dev/null |
        hexdump -v -e '/1 " %u"' 2>/dev/null |
        awk '{print ($1+0) + ($2+0)*256}')
    if [ -n "$_hbbsec" ] && [ "$_hbbsec" -gt 0 ] 2>/dev/null; then
        printf '%s' "$_hhex" | dd of="$_p" bs=1 seek=$(( _hbbsec * _hbps + 28 )) count=4 conv=notrunc 2>/dev/null
    fi
    echo "     ✔ FAT BPB hidden_sectors patched: → ${_new_start}"
    unset _p _new_start _b0 _b1 _b2 _b3 _hhex _hbps _hbbsec
}

# partition_path DEVICE PARTNUM
# Returns the partition device node, honouring mmcblk/nvme naming (pN suffix).
partition_path() {
    _pdev="$1"; _pnum="$2"
    case "$_pdev" in
        *[0-9]) echo "${_pdev}p${_pnum}" ;;
        *)      echo "${_pdev}${_pnum}" ;;
    esac
    unset _pdev _pnum
}

# detect_fs PARTITION
# Prints the lower-case filesystem type, or empty on failure.
detect_fs() {
    _fs=''
    if command -v blkid >/dev/null 2>&1; then
        _fs=$(blkid -o value -s TYPE "$1" 2>/dev/null | head -n 1)
    fi
    if [ -z "$_fs" ] && command -v lsblk >/dev/null 2>&1; then
        _fs=$(lsblk -ln -o FSTYPE "$1" 2>/dev/null | head -n 1)
    fi
    printf '%s' "$_fs" | tr '[:upper:]' '[:lower:]'
    unset _fs
}

# ==============================================================================
# USAGE / HELP
# ==============================================================================

usage() {
    cat <<'EOF'

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PARTITION MIGRATION / CLONE SCRIPT  v3.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SYNOPSIS
    partition_migration.sh -d DEV -D SDEV -p SPART -n SPARTNUM -S SEC -E SEC [OPTIONS]

DESCRIPTION
    Clones or moves a partition from a source device to a free slot on a target
    device using partclone v0.3.31.  All read-only checks (size, alignment, MBR
    limits) are always performed.  Invasive commands are guarded by -r (dry-run).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 REQUIRED OPTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  -d DEV        Target disk device where the new partition will be created.
                Example: -d /dev/sda

  -D SDEV       Source disk device that contains the partition to copy.
                Example: -D /dev/sdc

  -p SPART      Source partition device node (block device).
                Example: -p /dev/sdc1

  -n SPARTNUM   Source partition number (integer, as listed by parted).
                Example: -n 1
                Note: Required for source deletion in move mode (-M).

  -S SEC        Start sector (inclusive) for the new partition on the target disk.
                Must be a positive integer.  Automatically aligned if needed.
                Example: -S 42469624

  -E SEC        End sector (inclusive) for the new partition on the target disk.
                Must be greater than -S.  Automatically aligned if needed.
                Example: -E 55622693

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 OPERATION MODE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  -M            Move mode: after a successful clone AND validation mount, the
                source partition (-n) is deleted from -D.
                Default: clone mode (source is preserved).

  -c MODE       Clone method.  Allowed values:
                  smart   Filesystem-aware clone via the matching partclone
                          backend (partclone.ext4, partclone.fat32, etc.).
                          Only used blocks are transferred; faster than dd.
                  dd      Byte-to-byte clone via partclone.dd regardless of
                          filesystem type.  Slower but always works.
                Default: smart

                Supported filesystems in smart mode:
                  apfs  btrfs  exfat  ext2  ext3  ext4  f2fs  fat/fat12
                  fat16  fat32  hfs+  hfsplus  minix  ntfs  vfat  xfs

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 ALIGNMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  -a BYTES      Sector alignment granularity in bytes.  Allowed values:
                  512     Legacy alignment (one logical sector).  Use for old
                          disks or special embedded environments.
                  4096    Modern 4K-page alignment (8 x 512 B sectors).
                          Recommended for all contemporary drives (HDD, SSD,
                          USB flash, eMMC).
                Default: 4096
                Note: -S and -E are automatically rounded to the nearest aligned
                boundary if they are not already aligned; a warning is printed.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 LIFECYCLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  -u            Unmount before starting: unmounts the source partition (-p) and
                the target mountpoint (-t) at the very beginning.
                Default: do not unmount.

  -o            Mount after completion: mounts the newly created target partition
                at -t once all steps succeed.  Requires -t.
                Default: do not mount.

  -t MOUNTPOINT Path where the target partition will be mounted when -o is used.
                Created automatically if it does not exist.
                Example: -t /var/media/ftp/LG_TV

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PARTCLONE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  -x OPTS       Extra options appended verbatim to the partclone command line.
                Must be quoted if they contain spaces.
                Example: -x "--debug"

  -L FILE       Log file path for partclone (--logfile FILE).
                Default: /tmp/partclone.log
                Set to empty string to disable logging: -L ""
                The log captures partclone's internal progress, errors and
                bad-block events.  Useful for post-mortem analysis.

  -W            Pass --skip_write_error to partclone: continue restoring even
                when write errors occur (e.g. errno=5 / EIO on target).
                The clone may be incomplete but avoids a hard abort on
                intermittent I/O errors.

  -V            Verify clone integrity after step 6 using partclone.chkimg.
                If partclone.chkimg is not available the step is skipped with
                a warning rather than aborting.

  -f FSTYPE     Force filesystem type, bypassing auto-detection (blkid/lsblk).
                Useful when header detection is unreliable.
                Example: -f ext4

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 EXECUTION CONTROL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  -w SECS       Seconds to pause between each major step with a live countdown.
                Set to 0 to disable all delays.
                Default: 1
                Example: -w 3

  -Z PART       Compare mode: instead of cloning, compare SOURCE_PART (-p) with
                PART byte-by-byte using cmp(1).  Read-only — no disk writes.
                Only -p, -Z, -u, -w, -r are used in this mode; -d/-D/-S/-E/-n
                are optional and ignored.
                Example: -Z /dev/sdb1

  -r            Dry-run mode: all read-only checks (alignment, size, MBR limit,
                filesystem detection) are executed normally.  Every command that
                would write data, create/delete partitions, or mount/unmount is
                printed with a [DRY-RUN] prefix but NOT executed.
                Use this to verify parameters before a real run.

  -h            Print this help and exit.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 STEPS PERFORMED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  0  Validate and auto-correct sector alignment of -S / -E
  1  Pre-flight size checks (source size, disk capacity, MBR partition limit)
  2  Unmount source and target                    [only if -u]
  3  Detect filesystem on source; select partclone backend
  4  Create target partition with parted
  5  Resolve target partition device node
  6  Clone data with partclone
  6v Verify clone integrity with partclone.chkimg [only if -V]
  7  Post-clone integrity: UUID refresh (ext*), dosfsck (fat*), ntfsfix (ntfs)
  8  Read-only validation mount of target
  9  Delete source partition                      [only if -M]
     Final mount of target                        [only if -o]

  On any error the script aborts immediately with a descriptive message.
  No fallback logic is attempted.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 EXAMPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  # Clone /dev/sdc1 into a free slot on /dev/sda (smart mode, 4K alignment):
  partition_migration.sh \
      -d /dev/sda  -D /dev/sdc  -p /dev/sdc1  -n 1 \
      -S 42469624  -E 55622693

  # Same as above but move (delete source), unmount first, mount after:
  partition_migration.sh \
      -d /dev/sda  -D /dev/sdc  -p /dev/sdc1  -n 1 \
      -S 42469624  -E 55622693 \
      -M -u -o -t /var/media/ftp/LG_TV

  # Byte-to-byte copy, legacy 512 B alignment, 3-second step delay:
  partition_migration.sh \
      -d /dev/sda  -D /dev/sdc  -p /dev/sdc1  -n 1 \
      -S 42469624  -E 55622693 \
      -c dd  -a 512  -w 3

  # Dry-run: verify all parameters without touching any disk:
  partition_migration.sh \
      -d /dev/sda  -D /dev/sdc  -p /dev/sdc1  -n 1 \
      -S 42469624  -E 55622693 \
      -M -u -o -t /var/media/ftp/LG_TV  -r

  # Smart clone with extra partclone logging, no inter-step delay:
  partition_migration.sh \
      -d /dev/sda  -D /dev/sdc  -p /dev/sdc1  -n 1 \
      -S 42469624  -E 55622693 \
      -x "-L /tmp/partclone.log"  -w 0

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF
}

# ==============================================================================
# ARGUMENT PARSING
# ==============================================================================

while getopts ":d:D:p:n:S:E:t:Mc:a:uox:L:Ww:Vf:Z:F:b:rh" OPT; do
    case "$OPT" in
        d)  DEVICE="$OPTARG"               ;;
        D)  SOURCE_DEVICE="$OPTARG"        ;;
        p)  SOURCE_PART="$OPTARG"          ;;
        n)  SOURCE_PARTNUM="$OPTARG"       ;;
        S)  START="$OPTARG"                ;;
        E)  END="$OPTARG"                  ;;
        t)  TARGET_MOUNT="$OPTARG"         ;;
        M)  MOVE_MODE=1                    ;;
        c)  CLONE_MODE="$OPTARG"           ;;
        a)  ALIGN_BYTES="$OPTARG"          ;;
        u)  UMOUNT_BEFORE=1                ;;
        o)  MOUNT_AFTER=1                  ;;
        x)  PARTCLONE_EXTRA="$OPTARG"      ;;
        L)  PARTCLONE_LOGFILE="$OPTARG"    ;;
        W)  SKIP_WRITE_ERROR=1             ;;
        w)  STEP_DELAY="$OPTARG"           ;;
        V)  VERIFY_CLONE=1                 ;;
        f)  FORCE_FSTYPE="$OPTARG"         ;;
        Z)  COMPARE_PART="$OPTARG"         ;;
        F)  FAT_FSCK_PASSES="$OPTARG"      ;;
        b)  : # legacy flag, accepted for backward compat but ignored
            ;;
        r)  DRY_RUN=1                      ;;
        h)  usage; exit 0                  ;;
        :)  echo "❌  Option -${OPTARG} requires an argument." >&2
            echo "    Run with -h for help." >&2; exit 1 ;;
        ?)  echo "❌  Unknown option: -${OPTARG}" >&2
            echo "    Run with -h for help." >&2; exit 1 ;;
    esac
done

# ==============================================================================
# INPUT VALIDATION
# ==============================================================================

ERRORS=""

_require() {
    # _require VALUE FLAG DESCRIPTION
    [ -z "$1" ] && ERRORS="${ERRORS}\n    -${2}  ${3} is required."
}

_require "$SOURCE_PART"    "p" "source partition node"
if [ -z "$COMPARE_PART" ]; then
    _require "$DEVICE"         "d" "target disk device"
    _require "$SOURCE_DEVICE"  "D" "source disk device"
    _require "$SOURCE_PARTNUM" "n" "source partition number"
    _require "$START"          "S" "target start sector"
    _require "$END"            "E" "target end sector"
fi

if [ "$MOUNT_AFTER" -eq 1 ] && [ -z "$TARGET_MOUNT" ] && [ -z "$COMPARE_PART" ]; then
    ERRORS="${ERRORS}\n    -t  mountpoint is required when -o (mount after) is used."
fi

case "$CLONE_MODE" in
    smart|dd) ;;
    *) ERRORS="${ERRORS}\n    -c  invalid value '${CLONE_MODE}'. Allowed: smart | dd" ;;
esac

case "$ALIGN_BYTES" in
    512|4096|1048576) ;;
    *) ERRORS="${ERRORS}\n    -a  invalid value '${ALIGN_BYTES}'. Allowed: 512 | 4096 | 1048576" ;;
esac

case "$FAT_FSCK_PASSES" in
    ''|*[!0-9]*) ERRORS="${ERRORS}\n    -F  '${FAT_FSCK_PASSES}' is not a valid non-negative integer." ;;
esac

case "$STEP_DELAY" in
    ''|*[!0-9]*)
        ERRORS="${ERRORS}\n    -w  '${STEP_DELAY}' is not a valid non-negative integer." ;;
esac

if [ -z "$COMPARE_PART" ]; then
    case "$START" in
        ''|*[!0-9]*)
            ERRORS="${ERRORS}\n    -S  '${START}' is not a valid positive integer." ;;
    esac

    case "$END" in
        ''|*[!0-9]*)
            ERRORS="${ERRORS}\n    -E  '${END}' is not a valid positive integer." ;;
    esac

    # Sector range sanity check (only when both are valid non-negative integers)
    _start_ok=1; _end_ok=1
    case "$START" in ''|*[!0-9]*) _start_ok=0 ;; esac
    case "$END"   in ''|*[!0-9]*) _end_ok=0   ;; esac
    if [ "$_start_ok" -eq 1 ] && [ "$_end_ok" -eq 1 ] && [ "$END" -le "$START" ]; then
        ERRORS="${ERRORS}\n    -E  end sector (${END}) must be greater than start sector (${START})."
    fi
    unset _start_ok _end_ok
fi

if [ -n "$ERRORS" ]; then
    echo "❌  The following options are missing or invalid:" >&2
    printf "%b\n" "$ERRORS" >&2
    echo "    Run with -h for full help." >&2
    exit 1
fi

ALIGN_SECTORS=$(( ALIGN_BYTES / 512 ))

# ==============================================================================
# COMPARE MODE (-Z) — Read-only byte-by-byte partition comparison
# ==============================================================================

if [ -n "$COMPARE_PART" ]; then
    hr
    echo "🔍  PARTITION COMPARE MODE"
    hr
    echo "  Partition A : ${SOURCE_PART}"
    echo "  Partition B : ${COMPARE_PART}"
    echo "  Unmount     : $( [ \"$UMOUNT_BEFORE\" -eq 1 ] && echo \"yes\" || echo \"no\" )"
    echo "  Step delay  : ${STEP_DELAY}s"
    [ "$DRY_RUN" -eq 1 ] && echo "  ⚠️  DRY-RUN  : NO data will be read — comparison is simulated."
    hr

    if [ "$UMOUNT_BEFORE" -eq 1 ]; then
        echo "⏏️   [1/3] Unmounting partitions before comparison…"
        run umount "$SOURCE_PART" 2>/dev/null \
            && echo "     ✔ Unmounted ${SOURCE_PART}." \
            || echo "     ℹ ${SOURCE_PART} was not mounted."
        run umount "$COMPARE_PART" 2>/dev/null \
            && echo "     ✔ Unmounted ${COMPARE_PART}." \
            || echo "     ℹ ${COMPARE_PART} was not mounted."
        step_pause
    else
        echo "⏭️   [1/3] Unmount step skipped (-u not set)."
    fi

    echo "📐  [2/3] Checking partition sizes…"
    if [ "$DRY_RUN" -eq 0 ]; then
        SIZE_A=''
        SIZE_B=''
        if command -v blockdev >/dev/null 2>&1; then
            SIZE_A=$(blockdev --getsize64 "$SOURCE_PART" 2>/dev/null)
            SIZE_B=$(blockdev --getsize64 "$COMPARE_PART" 2>/dev/null)
        fi
        [ -z "$SIZE_A" ] && SIZE_A=$(wc -c < "$SOURCE_PART" 2>/dev/null)
        [ -z "$SIZE_B" ] && SIZE_B=$(wc -c < "$COMPARE_PART" 2>/dev/null)
        echo "     Size A : ${SIZE_A:-unknown} bytes"
        echo "     Size B : ${SIZE_B:-unknown} bytes"
        if [ -n "$SIZE_A" ] && [ -n "$SIZE_B" ] && [ "$SIZE_A" != "$SIZE_B" ]; then
            echo "⚠️   Partitions have different sizes — cmp stops at end of smaller partition."
        fi
    fi
    step_pause

    echo "🔍  [3/3] Comparing partition content (may take a while for large partitions)…"
    if [ "$DRY_RUN" -eq 1 ]; then
        echo "🔸  [DRY-RUN] cmp \"${SOURCE_PART}\" \"${COMPARE_PART}\""
        echo "     ✔ [DRY-RUN] Compare simulated — no actual read performed."
        hr
        echo "🔸  DRY-RUN COMPARE SIMULATION COMPLETED"
        hr
        exit 0
    fi

    if cmp "$SOURCE_PART" "$COMPARE_PART" >/dev/null 2>&1; then
        hr
        echo "✅  PARTITIONS ARE IDENTICAL"
        hr
        exit 0
    else
        DIFF_DESC=$(cmp "$SOURCE_PART" "$COMPARE_PART" 2>&1 | head -1)
        hr
        echo "❌  PARTITIONS DIFFER: ${DIFF_DESC}"
        hr
        exit 1
    fi
fi

# ==============================================================================
# BANNER
# ==============================================================================

hr
echo "🖧  PARTITION MIGRATION / CLONE SCRIPT  v3.0"
hr
echo "  Source      : ${SOURCE_PART}  (${SOURCE_DEVICE}, partition ${SOURCE_PARTNUM})"
echo "  Target      : ${DEVICE}  sectors ${START}–${END}"
echo "  Mode        : $( [ "$MOVE_MODE"    -eq 1 ] && echo "MOVE (source will be removed)" || echo "CLONE (source preserved)" )"
echo "  Method      : $( [ "$CLONE_MODE"   = "smart" ] && echo "Smart (filesystem-aware partclone)" || echo "DD (byte-to-byte partclone.dd)" )"
printf "  Alignment   : %d-byte (%d sectors)\n" "$ALIGN_BYTES" "$ALIGN_SECTORS"
echo "  Unmount     : $( [ "$UMOUNT_BEFORE" -eq 1 ] && echo "yes (before start)" || echo "no" )"
echo "  Mount after : $( [ "$MOUNT_AFTER"   -eq 1 ] && echo "$TARGET_MOUNT" || echo "no" )"
echo "  Step delay  : ${STEP_DELAY}s"
[ -n "$PARTCLONE_EXTRA" ] && echo "  Extra opts  : ${PARTCLONE_EXTRA}"
[ -n "$FORCE_FSTYPE" ]     && echo "  Force FS    : ${FORCE_FSTYPE}"
[ "$VERIFY_CLONE" -eq 1 ]  && echo "  Verify      : yes (partclone.chkimg after clone)"
if [ "$DRY_RUN" -eq 1 ]; then
    echo "  ⚠️  DRY-RUN  : NO data will be written — all invasive commands are simulated."
fi
hr

# ==============================================================================
# STEP 0 — VALIDATE AND AUTO-CORRECT SECTOR ALIGNMENT
# ==============================================================================

echo "🔎  [0/9] Validating sector alignment of requested range…"

if [ $(( START % ALIGN_SECTORS )) -ne 0 ]; then
    ALIGNED_START=$(align_up "$START" "$ALIGN_SECTORS")
    echo "⚠️   START ${START} is not ${ALIGN_BYTES}B-aligned → adjusted to ${ALIGNED_START}"
    START=$ALIGNED_START
else
    echo "     ✔ START ${START} is already aligned."
fi

ORIG_END="$END"
LENGTH=$(( END - START + 1 ))
REM=$(( LENGTH % ALIGN_SECTORS ))
if [ "$REM" -ne 0 ]; then
    _end_up=$(( END + ALIGN_SECTORS - REM ))
    # Try alignment upward first; align downward if it would exceed disk capacity
    # OR exceed the originally-requested END (= free-space boundary supplied by caller)
    _disk_sectors=''
    if [ -r "/sys/block/${DEVICE##*/}/size" ]; then
        _disk_sectors=$(cat "/sys/block/${DEVICE##*/}/size" 2>/dev/null)
    fi
    _exceeds_disk=0
    _exceeds_req=0
    if [ -n "$_disk_sectors" ] && [ "$_disk_sectors" -gt 0 ] && [ "$_end_up" -ge "$_disk_sectors" ]; then
        _exceeds_disk=1
    fi
    if [ "$_end_up" -gt "$ORIG_END" ]; then
        _exceeds_req=1
    fi
    if [ "$_exceeds_disk" -eq 1 ] || [ "$_exceeds_req" -eq 1 ]; then
        # Align downward: drop the remainder, then subtract one more unit if needed
        _end_down=$(( END - REM ))
        [ $(( (_end_down - START + 1) % ALIGN_SECTORS )) -ne 0 ] && \
            _end_down=$(( _end_down - ((_end_down - START + 1) % ALIGN_SECTORS) ))
        # If downward alignment shrinks the slot below the source partition size,
        # instead extend END upward past ORIG_END to fit the source.  The upstream
        # caller provides ORIG_END as a free-space hint, not a hard disk limit — the
        # real hard limit (DISK_SECTORS) is enforced in STEP 1.
        _src_size_now=$(parted -s -m "$SOURCE_DEVICE" unit s print \
            | awk -F: -v p="$SOURCE_PARTNUM" '$1 == p {gsub(/s/,"",$4); print $4}' 2>/dev/null)
        if [ -n "$_src_size_now" ] && [ $(( _end_down - START + 1 )) -lt "$_src_size_now" ] && [ "$_exceeds_disk" -eq 0 ]; then
            # Extend END to give exactly enough aligned space for the source
            _end_needed=$(( START + _src_size_now - 1 ))
            _rem2=$(( (_end_needed - START + 1) % ALIGN_SECTORS ))
            [ "$_rem2" -ne 0 ] && _end_needed=$(( _end_needed + ALIGN_SECTORS - _rem2 ))
            END=$_end_needed
            echo "⚠️   END extended to ${END} (downward alignment would shrink slot below source size)."
        else
            END=$_end_down
            if [ "$_exceeds_disk" -eq 1 ]; then
                echo "⚠️   END adjusted DOWN to ${END} (upward alignment would exceed disk bounds)."
            else
                echo "⚠️   END adjusted DOWN to ${END} (upward alignment would exceed requested range end ${ORIG_END})."
            fi
        fi
    else
        END=$_end_up
        echo "⚠️   END adjusted to ${END} so that length is a multiple of ${ALIGN_SECTORS} sectors."
    fi
else
    echo "     ✔ END ${END} yields an aligned length."
fi

echo "     Final range: sectors ${START} – ${END}  (length: $(( END - START + 1 )) sectors)"

# ==============================================================================
# STEP 1 — PRE-FLIGHT SIZE CHECKS
# ==============================================================================

step_pause
echo "📐  [1/9] Performing size checks…"

SRC_SIZE=$(parted -s -m "$SOURCE_DEVICE" unit s print \
    | awk -F: -v p="$SOURCE_PARTNUM" '$1 == p {gsub(/s/,"",$4); print $4}')
[ -z "$SRC_SIZE" ] && die "Cannot determine size of ${SOURCE_PART} from parted."

TARGET_SIZE=$(( END - START + 1 ))

echo "     Source partition size : ${SRC_SIZE} sectors"
echo "     Target slot size      : ${TARGET_SIZE} sectors"

[ "$TARGET_SIZE" -lt "$SRC_SIZE" ] && \
    die "Target slot (${TARGET_SIZE} s) is smaller than source (${SRC_SIZE} s)."
echo "     ✔ Target slot is large enough (surplus: $(( TARGET_SIZE - SRC_SIZE )) sectors)."

DISK_SECTORS=$(parted -s -m "$DEVICE" unit s print \
    | awk -F: 'NR==2 {gsub(/s/,"",$2); print $2}')
[ -z "$DISK_SECTORS" ] && die "Cannot determine capacity of ${DEVICE}."

[ "$END" -ge "$DISK_SECTORS" ] && \
    die "END sector ${END} exceeds disk capacity of ${DEVICE} (${DISK_SECTORS} sectors)."
echo "     ✔ END ${END} is within disk bounds (${DISK_SECTORS} sectors)."

# Detect partition table type here; reused in step 4
PTTYPE=$(parted -s -m "$DEVICE" unit s print | awk -F: 'NR==2 {print $6}')

# If the target has no partition table yet, initialize one so that the
# `parted mkpart` in step 4 does not fail with "unrecognised disk label".
# The new table type mirrors the SOURCE disk's table type when detectable,
# otherwise it defaults to msdos. (Only "unknown"/empty is auto-handled: a
# "loop" type means a filesystem sits directly on the device, which we do
# not silently destroy.)
if [ -z "$PTTYPE" ] || [ "$PTTYPE" = "unknown" ]; then
    _src_pttype=$(parted -s -m "$SOURCE_DEVICE" unit s print 2>/dev/null \
        | awk -F: 'NR==2 {print $6}')
    case "$_src_pttype" in
        gpt|msdos) _new_pttype="$_src_pttype" ;;
        *)         _new_pttype="msdos" ;;
    esac
    echo "     ℹ Target ${DEVICE} has no partition table — initializing ${_new_pttype}."
    run parted -s "$DEVICE" mklabel "$_new_pttype" \
        || die "Failed to initialize partition table on ${DEVICE}."
    run partprobe "$DEVICE" 2>/dev/null || true
    # Re-detect after mklabel (in dry-run this still reports unknown, which is
    # fine: step 4 is simulated too).
    PTTYPE=$(parted -s -m "$DEVICE" unit s print 2>/dev/null | awk -F: 'NR==2 {print $6}')
fi
# GPT requires ~34 sectors at the end of the disk for its backup header.
# If the requested END falls inside that reserved area, cap it silently so
# that 'parted mkpart' does not fail with an alignment/range error.
if [ "$PTTYPE" = "gpt" ] && [ -n "$DISK_SECTORS" ] && [ "$DISK_SECTORS" -gt 34 ]; then
    _gpt_safe_end=$(( DISK_SECTORS - 34 ))
    if [ "$END" -gt "$_gpt_safe_end" ]; then
        echo "⚠️   END adjusted from ${END} to ${_gpt_safe_end} (GPT backup header reservation)."
        END=$_gpt_safe_end
    fi
    unset _gpt_safe_end
fi
# Also detect extended partition range (MBR only) for use in step 4.
# EXT_START / EXT_END are set to the sector range of the first extended partition
# found; they remain empty on GPT or when no extended partition exists.
EXT_START=''
EXT_END=''
if [ "$PTTYPE" = "msdos" ]; then
    _ext=$(parted -s -m "$DEVICE" unit s print \
        | awk -F: 'NR>2 && ($5=="extended" || ($5=="" && index($7,"lba")>0)) {gsub(/s/,"",$2); gsub(/s/,"",$3); print $2" "$3; exit}')
    if [ -n "$_ext" ]; then
        EXT_START=$(echo "$_ext" | awk '{print $1}')
        EXT_END=$(  echo "$_ext" | awk '{print $2}')
    fi
fi

# Determine whether the target range falls inside the extended partition.
# If yes it must be created as a logical partition (not primary).
TGT_IS_LOGICAL=0
if [ -n "$EXT_START" ] && [ -n "$EXT_END" ]; then
    if [ "$START" -ge "$EXT_START" ] && [ "$END" -le "$EXT_END" ]; then
        TGT_IS_LOGICAL=1
    fi
fi

if [ "$PTTYPE" = "msdos" ]; then
    # On MBR disks only partition numbers 1-4 occupy primary/extended slots.
    # Logical partitions (numbers >= 5) live inside an extended partition and
    # do not consume a primary slot, so they must be excluded from the count.
    EXISTING_PARTS=$(parted -s -m "$DEVICE" unit s print \
        | awk -F: 'NR>2 && $1 ~ /^[0-9]+$/ && int($1)+0 <= 4 {c++} END {print c+0}')
    echo "     Partition table : MBR/msdos  (${EXISTING_PARTS} primary partition(s) present)"
    if [ "$TGT_IS_LOGICAL" -eq 1 ]; then
        echo "     ✔ Target range is inside extended partition — will create as logical (no primary slot used)."
    else
        [ "$EXISTING_PARTS" -ge 4 ] && \
            die "MBR disks support at most 4 primary partitions; ${DEVICE} already has ${EXISTING_PARTS}."
        echo "     ✔ Room for one more primary partition."
    fi
else
    echo "     Partition table : ${PTTYPE}"
fi

# ==============================================================================
# STEP 2 — UNMOUNT
# ==============================================================================

step_pause
if [ "$UMOUNT_BEFORE" -eq 1 ]; then
    echo "⏏️   [2/9] Unmounting source partition and target mountpoint…"
    run umount "$SOURCE_PART" 2>/dev/null \
        && echo "     ✔ Unmounted ${SOURCE_PART}." \
        || echo "     ℹ ${SOURCE_PART} was not mounted."
    if [ -n "$TARGET_MOUNT" ]; then
        run umount "$TARGET_MOUNT" 2>/dev/null \
            && echo "     ✔ Unmounted ${TARGET_MOUNT}." \
            || echo "     ℹ ${TARGET_MOUNT} was not mounted."
    fi
else
    echo "⏭️   [2/9] Unmount step skipped (-u not set)."
fi

# ==============================================================================
# STEP 3 — FILESYSTEM DETECTION & BACKEND SELECTION
# ==============================================================================

step_pause
echo "🔬  [3/9] Detecting filesystem on ${SOURCE_PART}…"

if [ -n "$FORCE_FSTYPE" ]; then
    FSTYPE=$(printf '%s' "$FORCE_FSTYPE" | tr '[:upper:]' '[:lower:]')
    echo "     Filesystem forced: ${FSTYPE} (-f override)"
else
    FSTYPE=$(detect_fs "$SOURCE_PART")
    if [ -z "$FSTYPE" ]; then
        if [ "$CLONE_MODE" = "smart" ]; then
            echo "     ⚠ No filesystem detected on ${SOURCE_PART} — falling back to sector-by-sector copy (partclone.dd)."
            CLONE_MODE="dd"
        else
            die "Could not detect filesystem type on ${SOURCE_PART} (tried blkid and lsblk)."
        fi
    fi
fi

echo "     Detected filesystem: ${FSTYPE:-<none, raw/unformatted>}"

if [ "$CLONE_MODE" = "smart" ]; then
    case "$FSTYPE" in
        ext2)                PARTCLONE_BIN="partclone.ext2"    ;;
        ext3)                PARTCLONE_BIN="partclone.ext3"    ;;
        ext4|ext4dev)        PARTCLONE_BIN="partclone.ext4"    ;;
        btrfs)               PARTCLONE_BIN="partclone.btrfs"   ;;
        xfs)                 PARTCLONE_BIN="partclone.xfs"     ;;
        ntfs)                PARTCLONE_BIN="partclone.ntfs"    ;;
        vfat)                PARTCLONE_BIN="partclone.vfat"    ;;
        fat|fat12|fat32)     PARTCLONE_BIN="partclone.fat"     ;;
        fat16)               PARTCLONE_BIN="partclone.fat16"   ;;
        exfat)               PARTCLONE_BIN="partclone.exfat"   ;;
        apfs)                PARTCLONE_BIN="partclone.apfs"    ;;
        hfs|hfs+|hfsp*)      PARTCLONE_BIN="partclone.hfsplus" ;;
        f2fs)                PARTCLONE_BIN="partclone.f2fs"    ;;
        minix|minix3)        PARTCLONE_BIN="partclone.minix"   ;;
        *) die "No smart partclone backend for '${FSTYPE}'. Use -c dd instead." ;;
    esac
    command -v "$PARTCLONE_BIN" >/dev/null 2>&1 || \
        die "Smart backend '${PARTCLONE_BIN}' not found in PATH. Use -c dd instead."
    echo "     ✔ Smart backend selected: ${PARTCLONE_BIN}"
else
    command -v partclone.dd >/dev/null 2>&1 || \
        die "partclone.dd not found in PATH."
    PARTCLONE_BIN="partclone.dd"
    echo "     ✔ Byte-to-byte backend: partclone.dd"
fi

# ==============================================================================
# STEP 4 — CREATE TARGET PARTITION
# ==============================================================================

step_pause
echo "🏗️   [4/9] Creating new partition on ${DEVICE} (sectors ${START}–${END})…"

# GPT partitions do not use role names; only MBR/msdos uses 'primary'/'logical'.
# On MBR, if the target sector range falls inside the extended partition it must
# be created as 'logical'; otherwise it is 'primary'.
if [ "$PTTYPE" = "msdos" ]; then
    if [ "$TGT_IS_LOGICAL" -eq 1 ]; then
        run parted -s "$DEVICE" unit s mkpart logical "${START}s" "${END}s" \
            || die "parted mkpart failed on ${DEVICE}."
    else
        run parted -s "$DEVICE" unit s mkpart primary "${START}s" "${END}s" \
            || die "parted mkpart failed on ${DEVICE}."
    fi
else
    run parted -s "$DEVICE" unit s mkpart "Linux" "${START}s" "${END}s" \
        || die "parted mkpart failed on ${DEVICE}."
fi

echo "     ✔ Partition entry created. Refreshing kernel partition table…"
run partprobe "$DEVICE" 2>/dev/null || sleep 2

# ==============================================================================
# STEP 5 — RESOLVE TARGET PARTITION DEVICE NODE
# ==============================================================================

step_pause
echo "🔍  [5/9] Resolving target partition device node…"

if [ "$DRY_RUN" -eq 1 ]; then
    EXISTING_COUNT=$(parted -s -m "$DEVICE" unit s print \
        | awk -F: 'NR>2 && $1 ~ /^[0-9]+$/ {c++} END {print c+0}')
    TARGET_PARTNUM=$(( EXISTING_COUNT + 1 ))
    TARGET_PART=$(partition_path "$DEVICE" "$TARGET_PARTNUM")
    echo "🔸  [DRY-RUN] Partition not yet created — simulated target: ${TARGET_PART}  (partition ${TARGET_PARTNUM})"
else
    TARGET_PARTNUM=""
    _retry=0
    while [ "$_retry" -lt 5 ]; do
        TARGET_PARTNUM=$(parted -s -m "$DEVICE" unit s print \
            | awk -F: -v s="${START}s" '$2 == s {print $1}')
        [ -n "$TARGET_PARTNUM" ] && break
        partprobe "$DEVICE" 2>/dev/null || true
        sleep 1
        _retry=$(( _retry + 1 ))
    done
    [ -n "$TARGET_PARTNUM" ] || \
        die "Cannot find a partition starting at sector ${START} on ${DEVICE} after 5 retries."
    TARGET_PART=$(partition_path "$DEVICE" "$TARGET_PARTNUM")
    echo "     ✔ Target partition resolved: ${TARGET_PART}  (partition ${TARGET_PARTNUM})"
fi

# Auto-unmount target if the OS mounted it automatically after partprobe
# (common on FritzBox: udev mounts new vfat/ext partitions immediately)
if [ "$DRY_RUN" -eq 0 ]; then
    _tgt_mount=$(grep -s "^${TARGET_PART}[[:space:]]" /proc/mounts | awk '{print $2}' | head -n 1)
    if [ -n "$_tgt_mount" ]; then
        echo "⚠️   Target ${TARGET_PART} was auto-mounted at ${_tgt_mount} — unmounting before clone…"
        run umount "$TARGET_PART" \
            || die "Cannot unmount auto-mounted target ${TARGET_PART} at ${_tgt_mount}. Aborting."
        echo "     ✔ Target unmounted."
    fi
fi

# Fix stale FAT BPB before partclone reads it (low-level TotSec32 patch)
case "$FSTYPE" in
    vfat|fat|fat12|fat16|fat32)
        [ "$DRY_RUN" -eq 0 ] && fat_fix_total_sectors "$SOURCE_PART"
        ;;
esac

# Pre-clone FAT repair: run dosfsck/fsck.fat (up to FAT_FSCK_PASSES times)
# on unmounted source.  Controlled by -F (default 2, 0 = skip).
_fat_fsck_cmd=""
case "$FSTYPE" in
    vfat|fat|fat12|fat16|fat32)
        if command -v dosfsck >/dev/null 2>&1; then
            _fat_fsck_cmd="dosfsck"
        elif command -v fsck.fat >/dev/null 2>&1; then
            _fat_fsck_cmd="fsck.fat"
        fi
        ;;
esac

if [ "$DRY_RUN" -eq 0 ] && [ -n "$_fat_fsck_cmd" ] && [ "${FAT_FSCK_PASSES:-2}" -gt 0 ] 2>/dev/null; then
    _src_mounted=0
    mount 2>/dev/null | grep -q "^${SOURCE_PART}[[:space:]]" && _src_mounted=1
    if [ "$_src_mounted" -eq 1 ]; then
        echo "     ℹ  Source ${SOURCE_PART} is mounted — skipping pre-clone FAT repair."
        echo "     ℹ  Use -u to unmount before cloning for a cleaner FAT state."
    else
        _max_pass="${FAT_FSCK_PASSES:-2}"
        _pass=1
        while [ "$_pass" -le "$_max_pass" ]; do
            echo "     → Pre-clone FAT repair pass ${_pass}/${_max_pass} ($_fat_fsck_cmd -a ${SOURCE_PART})…"
            _fsck_out=$("$_fat_fsck_cmd" -a "$SOURCE_PART" 2>&1)
            _fsck_rc=$?
            echo "$_fsck_out"
            # If no changes were made and no errors, no need for further passes
            if ! echo "$_fsck_out" | grep -qi "changed\|fix\|corrupt\|error\|dirty"; then
                echo "     ✔ FAT repair pass ${_pass}: no issues, stopping early."
                break
            fi
            echo "     ✔ FAT repair pass ${_pass} finished (rc=${_fsck_rc})."
            _pass=$(( _pass + 1 ))
        done
    fi
elif [ "${FAT_FSCK_PASSES:-2}" -eq 0 ] 2>/dev/null; then
    case "$FSTYPE" in
        vfat|fat|fat12|fat16|fat32)
            echo "     ℹ  Pre-clone FAT repair disabled (-F 0)."
            ;;
    esac
fi

# After FAT repair, re-apply BPB TotSec32 patch in case fsck rewrote it
case "$FSTYPE" in
    vfat|fat|fat12|fat16|fat32)
        [ "$DRY_RUN" -eq 0 ] && fat_fix_total_sectors "$SOURCE_PART"
        ;;
esac

# ==============================================================================
# STEP 6 — DATA CLONE
# ==============================================================================

step_pause
echo "💾  [6/9] Cloning data: ${SOURCE_PART} ──▶ ${TARGET_PART}…"
echo "     Backend : ${PARTCLONE_BIN}"
[ -n "$PARTCLONE_EXTRA" ] && echo "     Extra   : ${PARTCLONE_EXTRA}"

# shellcheck disable=SC2086
# Build partclone flags.
# partclone.dd (v0.3.x) does not accept --dev-to-dev; other backends do.
# IMPORTANT: --dev-to-dev (-b) performs a direct device-to-device copy that
# writes raw filesystem data to the target.  Do NOT use --clone (-c) here:
# --clone writes partclone's own image format (header + sparse blocks),
# which is NOT a mountable filesystem and causes "Bad magic number" /
# "wrong fs type" errors from tune2fs, e2fsck, and mount.
_pcdd_mode=0
[ "$PARTCLONE_BIN" = "partclone.dd" ] && _pcdd_mode=1
if [ "$DRY_RUN" -eq 0 ]; then
    if [ "$_pcdd_mode" -eq 1 ]; then
        set -- --overwrite --quiet --source "$SOURCE_PART" --output "$TARGET_PART"
    else
        set -- --dev-to-dev --overwrite --quiet --source "$SOURCE_PART" --output "$TARGET_PART"
    fi
    [ -n "$PARTCLONE_LOGFILE" ] && set -- "$@" --logfile "$PARTCLONE_LOGFILE"
    [ "$SKIP_WRITE_ERROR" = "1" ] && set -- "$@" --skip_write_error
    # partclone 0.3.x NON riapre un logfile già esistente ("open logfile ...
    # error", nessun dato scritto): rigeneriamolo pulito a ogni run.
    [ -n "$PARTCLONE_LOGFILE" ] && rm -f "$PARTCLONE_LOGFILE"
    # shellcheck disable=SC2086
    printf '\033[36m── cmd:\033[0m \033[1;33m%s\033[0m\n' "$PARTCLONE_BIN $* $PARTCLONE_EXTRA"
    "$PARTCLONE_BIN" "$@" $PARTCLONE_EXTRA
    _pclone_rc=$?
else
    if [ "$_pcdd_mode" -eq 1 ]; then
        set -- --overwrite --quiet --source "$SOURCE_PART" --output "$TARGET_PART"
    else
        set -- --dev-to-dev --overwrite --quiet --source "$SOURCE_PART" --output "$TARGET_PART"
    fi
    [ -n "$PARTCLONE_LOGFILE" ] && set -- "$@" --logfile "$PARTCLONE_LOGFILE"
    [ "$SKIP_WRITE_ERROR" = "1" ] && set -- "$@" --skip_write_error
    # shellcheck disable=SC2086
    run "$PARTCLONE_BIN" "$@" $PARTCLONE_EXTRA
    _pclone_rc=0
fi

# Check if partclone completed 100% despite a non-zero exit (e.g. fsync EIO).
# Returns 0 (treat as success) ONLY if:
#   - log shows 100.00% completed
#   - AND no write errors (write protected, critical target error) are present
# Returns 1 if writes actually failed (write protected, I/O errors during transfer).
_pclone_check_completed() {
    _rc="$1"
    [ "$_rc" -eq 0 ] && return 0
    [ -n "$PARTCLONE_LOGFILE" ] && [ -s "$PARTCLONE_LOGFILE" ] || return 1
    grep -q "100\.00% completed" "$PARTCLONE_LOGFILE" 2>/dev/null || return 1
    # If the log or dmesg indicates actual write failures (write protected, bad blocks
    # written), do NOT treat as success — data on target may be incomplete.
    if grep -qi "write.protect\|write error\|bad block\|critical.*error\|WRITE PROTECTED" \
            "$PARTCLONE_LOGFILE" 2>/dev/null; then
        echo "⚠️   partclone log shows 100% but also write errors — data on target may be incomplete."
        return 1
    fi
    # fsync-only failure: data was written, kernel flush reported EIO (e.g. USB glitch at sync)
    echo "⚠️   partclone exited with rc=${_rc} but log shows 100.00% completed."
    if grep -q "fsync error" "$PARTCLONE_LOGFILE" 2>/dev/null; then
        echo "     Cause: fsync error on target (errno=5/EIO — data written, kernel flush failed)."
        echo "     Data transfer is complete. Consider -W (--skip_write_error) to suppress next time."
    fi
    return 0
}

if [ "$_pclone_rc" -ne 0 ] && _pclone_check_completed "$_pclone_rc"; then
    _pclone_rc=0  # treat as success
fi

if [ "$_pclone_rc" -ne 0 ]; then
    echo "⚠️   partclone (${PARTCLONE_BIN}) failed (rc=${_pclone_rc})."
    if [ -n "$PARTCLONE_LOGFILE" ] && [ -s "$PARTCLONE_LOGFILE" ]; then
        echo "     ── partclone log (${PARTCLONE_LOGFILE}) ──"
        sed 's/^/     /' < "$PARTCLONE_LOGFILE"
        echo "     ── end log ──"
    fi
    die "partclone cloning failed (rc=${_pclone_rc}). Check source device and try again."
fi

echo "     ✔ Data clone completed."

# ==============================================================================
# STEP 6v — OPTIONAL PARTCLONE.CHKIMG VERIFY
# ==============================================================================

if [ "$VERIFY_CLONE" -eq 1 ]; then
    step_pause
    echo "🔬  [6v] Verifying clone integrity with partclone.chkimg on ${TARGET_PART}…"
    if command -v partclone.chkimg >/dev/null 2>&1; then
        run partclone.chkimg -s "$TARGET_PART" \
            || die "partclone.chkimg reported errors on ${TARGET_PART}. Clone may be corrupt."
        echo "     ✔ partclone.chkimg passed."
    else
        echo "     ⚠ partclone.chkimg not found — verify step skipped."
    fi
fi

# ==============================================================================
# STEP 7 — POST-CLONE INTEGRITY
# ==============================================================================

# Flush pending writes so filesystem tools see the data partclone just wrote.
# Write path: partclone → /dev/loop0pN block layer → loop driver → backing
# file page cache.  BLKFLSBUF on the partition node flushes dirty pages but
# does NOT always propagate cache invalidation through the loop → file layer
# stack; tune2fs and mount therefore sometimes read stale (pre-clone) data.
# Solution:
#  1. sync – commits all dirty pages to the backing file on disk.
#  2. blockdev --flushbufs – evict device buffers (best-effort, needs root).
#  3. echo 3 > drop_caches – full purge: pagecache + dentries + inodes.
#     echo 1 (clean pages only) is insufficient: dirty pages written by
#     partclone survive it and continue to look stale.
#
# IMPORTANT: Do NOT run partprobe here.  The partition table has not changed
# since step 4 — only data *within* the partition was written by partclone.
# Re-probing the partition table on MBR disks with logical partitions causes
# the kernel to re-walk the EBR chain and may assign different partition
# numbers, making TARGET_PART (/dev/loop0pN) point to wrong sectors.
# This manifests as "Bad magic number in super-block" from tune2fs/mount
# even though partclone completed successfully.
sync
blockdev --flushbufs "$DEVICE" 2>/dev/null || true
blockdev --flushbufs "$TARGET_PART" 2>/dev/null || true
# Loop devices need aggressive cache invalidation: the write path goes
# through the backing file's page cache, and subsequent reads may hit
# stale cached pages unless we drop them.
if echo "$DEVICE" | grep -qE '^/dev/loop[0-9]'; then
    # echo 3: drops pagecache + dentries + inodes (more thorough than echo 1).
    echo 3 > /proc/sys/vm/drop_caches 2>/dev/null || true
    sync
    blockdev --flushbufs "$DEVICE" 2>/dev/null || true
    blockdev --flushbufs "$TARGET_PART" 2>/dev/null || true
fi
sleep 3

step_pause
echo "🛠️   [7/9] Running filesystem integrity checks and UUID refresh on ${TARGET_PART}…"

case "$FSTYPE" in
    ext2|ext3|ext4|ext4dev)
        # e2fsck MUST run before tune2fs: tune2fs -U refuses to operate on a
        # filesystem that has not been freshly checked ("This operation
        # requires a freshly checked filesystem").
        echo "     → Running e2fsck filesystem check…"
        run e2fsck -fy "$TARGET_PART" \
            || die "e2fsck reported uncorrectable errors on ${TARGET_PART}."
        echo "     → Assigning new random UUID (tune2fs)…"
        if ! run tune2fs -U random "$TARGET_PART"; then
            if [ "$MOVE_MODE" -eq 1 ]; then
                echo "     ⚠ tune2fs failed — UUID not changed (non-fatal: source will be deleted)."
            else
                die "tune2fs -U random failed on ${TARGET_PART}."
            fi
        fi
        ;;
    vfat|fat|fat12|fat16|fat32)
        if command -v dosfsck >/dev/null 2>&1; then
            echo "     → Running dosfsck auto-repair…"
            run dosfsck -a "$TARGET_PART" \
                || die "dosfsck failed on ${TARGET_PART}."
        elif command -v fsck.fat >/dev/null 2>&1; then
            echo "     → Running fsck.fat auto-repair…"
            run fsck.fat -a "$TARGET_PART" \
                || die "fsck.fat failed on ${TARGET_PART}."
        else
            echo "     ℹ dosfsck/fsck.fat not found — FAT check skipped."
        fi
        ;;
    ntfs)
        echo "     → Running ntfsfix…"
        run ntfsfix "$TARGET_PART" \
            || die "ntfsfix failed on ${TARGET_PART}."
        ;;
    *)
        echo "     ℹ No specific post-clone check defined for '${FSTYPE}'. Skipping."
        ;;
esac

echo "     ✔ Integrity checks passed."

# Patch FAT BPB hidden_sectors to match new partition start.
# After clone/move the partition sits at a different LBA, so the original
# hidden_sectors value (copied verbatim by partclone) is stale.
case "$FSTYPE" in
    vfat|fat|fat12|fat16|fat32)
        if [ "$DRY_RUN" -eq 0 ]; then
            fat_fix_hidden_sectors "$TARGET_PART" "$START"
        else
            echo "🔸  [DRY-RUN] fat_fix_hidden_sectors ${TARGET_PART} ${START}"
        fi
        ;;
esac

# ==============================================================================
# STEP 8 — READ-ONLY VALIDATION MOUNT
# ==============================================================================

step_pause
echo "🧪  [8/9] Validating target partition with a read-only test mount…"

VALIDATE_DIR="/tmp/_partition_migration_verify_$$"

# Raw/unformatted partitions (FSTYPE empty) cannot be mounted — skip validation.
if [ -z "$FSTYPE" ]; then
    echo "     ℹ No filesystem on target (raw/unformatted) — skipping mount validation."
elif [ "$DRY_RUN" -eq 1 ]; then
    echo "🔸  [DRY-RUN] mkdir -p ${VALIDATE_DIR}"
    echo "🔸  [DRY-RUN] mount -t ${FSTYPE} -o ro ${TARGET_PART} ${VALIDATE_DIR}"
    echo "🔸  [DRY-RUN] umount ${VALIDATE_DIR}"
    echo "🔸  [DRY-RUN] rmdir  ${VALIDATE_DIR}"
    echo "     ✔ [DRY-RUN] Validation step simulated — no actual mount performed."
else
    mkdir -p "$VALIDATE_DIR" || die "Cannot create temporary validation directory."
    if mount -t "$FSTYPE" -o ro "$TARGET_PART" "$VALIDATE_DIR"; then
        echo "     ✔ Target mounted read-only successfully. Filesystem is accessible."
        umount "$VALIDATE_DIR" || die "Cannot unmount validation directory."
        rmdir  "$VALIDATE_DIR" 2>/dev/null
    else
        # On loop-backed devices the page cache may still be trailing; give it
        # one more flush cycle before giving up.
        _mount_ok=0
        if echo "$DEVICE" | grep -qE '^/dev/loop[0-9]'; then
            echo "     ℹ️  Initial mount failed on loop device — flushing and retrying in 4 s…"
            sync
            blockdev --flushbufs "$DEVICE"      2>/dev/null || true
            blockdev --flushbufs "$TARGET_PART" 2>/dev/null || true
            echo 3 > /proc/sys/vm/drop_caches   2>/dev/null || true
            sync
            sleep 4
            if mount -t "$FSTYPE" -o ro "$TARGET_PART" "$VALIDATE_DIR"; then
                echo "     ✔ Target mounted read-only on retry. Filesystem is accessible."
                umount "$VALIDATE_DIR" || die "Cannot unmount validation directory."
                rmdir  "$VALIDATE_DIR" 2>/dev/null
                _mount_ok=1
            fi
        fi
        if [ "$_mount_ok" -eq 0 ]; then
            rmdir  "$VALIDATE_DIR" 2>/dev/null
            die "Target ${TARGET_PART} is NOT mountable. Data may be corrupt. Source is untouched."
        fi
    fi
fi

# ==============================================================================
# STEP 9 — SOURCE REMOVAL (MOVE MODE ONLY)
# ==============================================================================

step_pause
if [ "$MOVE_MODE" -eq 1 ]; then
    echo "🧹  [9/9] MOVE MODE: deleting source partition ${SOURCE_PARTNUM} from ${SOURCE_DEVICE}…"
    run parted -s "$SOURCE_DEVICE" rm "$SOURCE_PARTNUM" \
        || die "Failed to delete source partition ${SOURCE_PARTNUM} on ${SOURCE_DEVICE}."
    run partprobe "$SOURCE_DEVICE" 2>/dev/null || sleep 2
    echo "     ✔ Source partition removed."
else
    echo "⏭️   [9/9] CLONE MODE: source partition ${SOURCE_PART} preserved."
fi

# ==============================================================================
# FINAL MOUNT
# ==============================================================================

step_pause
if [ "$MOUNT_AFTER" -eq 1 ]; then
    echo "📂  Mounting ${TARGET_PART} at ${TARGET_MOUNT}…"
    run mkdir -p "$TARGET_MOUNT" || die "Cannot create mount point ${TARGET_MOUNT}."
    run mount "$TARGET_PART" "$TARGET_MOUNT" \
        || die "Final mount of ${TARGET_PART} at ${TARGET_MOUNT} failed."
    echo "     ✔ Partition is now mounted at ${TARGET_MOUNT}."
else
    echo "⏭️   Final mount skipped (-o not set)."
fi

# ==============================================================================
# SUMMARY
# ==============================================================================

hr
if [ "$DRY_RUN" -eq 1 ]; then
    echo "🔸  DRY-RUN SIMULATION COMPLETED — NO DATA WAS WRITTEN"
else
    echo "✨  OPERATION COMPLETED SUCCESSFULLY"
fi
hr
echo "  Source      : ${SOURCE_PART}  →  $( [ "$MOVE_MODE" -eq 1 ] && echo "REMOVED" || echo "preserved" )$( [ "$DRY_RUN" -eq 1 ] && echo "  [simulated]" )"
echo "  Destination : ${TARGET_PART}  (${DEVICE}, partition ${TARGET_PARTNUM})$( [ "$DRY_RUN" -eq 1 ] && echo "  [simulated]" )"
echo "  Sectors     : ${START} – ${END}  ($(( END - START + 1 )) sectors, $(( (END - START + 1) / 2048 )) MiB approx.)"
echo "  Filesystem  : ${FSTYPE}"
echo "  Method      : ${PARTCLONE_BIN}"
echo "  Alignment   : ${ALIGN_BYTES}-byte"
echo "  Step delay  : ${STEP_DELAY}s"
echo "  Dry-run     : $( [ "$DRY_RUN" -eq 1 ] && echo "YES — simulation only" || echo "no" )"
[ "$MOUNT_AFTER" -eq 1 ] && \
    echo "  Mounted at  : $( [ "$DRY_RUN" -eq 1 ] && echo "${TARGET_MOUNT}  [simulated]" || echo "${TARGET_MOUNT}" )"
hr
