#!/bin/sh

# ==============================================================================
# DISK MIGRATION / CLONE SCRIPT
# Version: 1.0 | POSIX ASH compliant
# ==============================================================================
#
# Clones or moves all partitions from a source disk to a target disk using
# the same partclone/parted toolchain as partition_migration.sh.
#
# Physical mode (-P): raw bit-for-bit copy with dd (MBR/GPT headers included).
# Logical mode  (default): partition-by-partition copy with partclone/parted.
#
# ==============================================================================
# DEFAULTS
# ==============================================================================

SOURCE_DEVICE=""      # -D  source disk device             (required)
TARGET_DEVICE=""      # -d  target disk device             (required)

MOVE_MODE=0           # -M  flag: delete source partitions after successful clone
PHYSICAL_MODE=0       # -P  flag: raw dd copy (includes MBR/GPT)
INCLUDE_TAIL=0        # -T  flag: (physical mode) include unallocated tail sectors
CLONE_MODE="smart"    # -c  smart | dd
ALIGN_BYTES=4096      # -a  512 | 4096 | 1048576
UMOUNT_BEFORE=0       # -u  flag: unmount all source/target partitions before starting
COPY_MBR=0            # -B  flag: (logical mode) copy MBR/GPT header from source to target
WIPE_TARGET=0         # -W  flag: (logical mode) wipe all partitions on target before copy
PARTCLONE_EXTRA=""    # -x  extra options passed to partclone verbatim
STEP_DELAY=1          # -w  seconds to wait between steps (0 = none)
VERIFY_CLONE=0        # -V  flag: run partclone.chkimg verify after each partition clone
FORCE_FSTYPE=""       # -f  force filesystem type (skip auto-detection; applied to ALL parts)
DRY_RUN=0             # -r  flag: simulate only, no writes
VERIFY_ONLY=0         # -Z  flag: verify mode – compare each source/target partition pair

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

hr()   { echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; }
die()  { echo "❌  FATAL: $*" >&2; exit 1; }

run() {
    if [ "$DRY_RUN" -eq 1 ]; then
        printf '\033[33m\U1F538  [DRY-RUN]\033[0m %s\n' "$*"
        return 0
    fi
    printf '\033[36m── cmd:\033[0m \033[1;33m%s\033[0m\n' "$*"
    "$@"
}

step_pause() {
    [ "${STEP_DELAY:-0}" -le 0 ] && return
    remaining=$STEP_DELAY
    printf "⏳  Continuing in "
    while [ "$remaining" -gt 0 ]; do
        printf "%d… " "$remaining"
        sleep 1
        remaining=$(( remaining - 1 ))
    done
    echo ""
}

align_up() {
    val=$1; mul=$2
    rem=$(( val % mul ))
    [ "$rem" -eq 0 ] && echo "$val" || echo $(( val - rem + mul ))
}

align_down() {
    val=$1; mul=$2
    echo $(( val - val % mul ))
}

partition_path() {
    _pdev="$1"; _pnum="$2"
    case "$_pdev" in
        *[0-9]) echo "${_pdev}p${_pnum}" ;;
        *)      echo "${_pdev}${_pnum}" ;;
    esac
    unset _pdev _pnum
}

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

disk_size_sectors() {
    parted -s -m "$1" unit s print 2>/dev/null \
        | awk -F: 'NR==2 {gsub(/s/,"",$2); print $2}'
}

# ==============================================================================
# USAGE / HELP
# ==============================================================================

usage() {
    cat <<'EOF'

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 DISK MIGRATION / CLONE SCRIPT  v1.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SYNOPSIS
    disk_migration.sh -D SDEV -d TDEV [OPTIONS]

DESCRIPTION
    Clones or moves all partitions from a source disk to a target disk.
    Two modes are available:

    Logical mode (default):
      Reads the source partition table with parted, recreates each partition
      on the target disk and clones the data using partclone (smart or dd).
      Each partition keeps its full source size; the target disk must fit the
      actually-used source sectors (checked up front, no shrinking).

    Physical mode (-P):
      Raw bit-for-bit copy of the entire source disk using dd.  Includes
      MBR/GPT headers, partition table, and all sectors.  Optionally includes
      unallocated tail sectors (-T).  Target must be >= source used capacity.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 REQUIRED OPTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  -D SDEV       Source disk device.    Example: -D /dev/sda
  -d TDEV       Target disk device.    Example: -d /dev/sdb

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 OPERATION MODE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  -M            Move mode: delete all source disk partitions after successful clone.
                Default: clone (source preserved).

  -P            Physical (raw) mode: byte-to-byte dd copy of the whole disk.
                Includes MBR/GPT. Target must fit the used sectors.
                Default: logical partition-by-partition copy.

  -Z            Verify-only mode: compare each source/target partition pair
                byte-by-byte using cmp(1). Read-only — no disk writes.
                Requires that target partitions already exist.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 LOGICAL MODE OPTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  -c MODE       Clone method: smart | dd    Default: smart
  -a BYTES      Alignment: 512 | 4096 | 1048576   Default: 4096
  -W            Wipe target partitions before cloning.
  -B            Copy MBR/GPT header from source to target (logical mode).
  -V            Verify each cloned partition with partclone.chkimg.
  -f FSTYPE     Force filesystem type for ALL partitions (overrides auto-detect).
  -x OPTS       Extra options appended verbatim to each partclone command.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PHYSICAL MODE OPTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  -T            Include unallocated tail sectors (full dd, not just used sectors).
                Default: stop dd at the end of the last partition + 1 MiB pad.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 COMMON OPTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  -u            Unmount all source and target partitions before starting.
  -w SECS       Step delay in seconds.  Default: 1
  -r            Dry-run: print all commands, execute none.
  -h            Print this help and exit.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 EXAMPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  # Logical clone /dev/sda → /dev/sdb, unmount first, verify:
  disk_migration.sh -D /dev/sda -d /dev/sdb -u -V

  # Physical raw copy /dev/sda → /dev/sdb (used sectors only):
  disk_migration.sh -D /dev/sda -d /dev/sdb -P -u

  # Physical copy including tail (full disk):
  disk_migration.sh -D /dev/sda -d /dev/sdb -P -T -u

  # Move (clone + wipe source) with dd method:
  disk_migration.sh -D /dev/sda -d /dev/sdb -M -c dd -u

  # Verify existing copy (no-write comparison):
  disk_migration.sh -D /dev/sda -d /dev/sdb -Z

  # Dry-run to check parameters without touching disks:
  disk_migration.sh -D /dev/sda -d /dev/sdb -u -V -r

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF
}

# ==============================================================================
# ARGUMENT PARSING
# ==============================================================================

while getopts ":D:d:c:a:x:w:f:MPTBWVZurh" OPT; do
    case "$OPT" in
        D)  SOURCE_DEVICE="$OPTARG"   ;;
        d)  TARGET_DEVICE="$OPTARG"   ;;
        M)  MOVE_MODE=1               ;;
        P)  PHYSICAL_MODE=1           ;;
        T)  INCLUDE_TAIL=1            ;;
        c)  CLONE_MODE="$OPTARG"      ;;
        a)  ALIGN_BYTES="$OPTARG"     ;;
        B)  COPY_MBR=1                ;;
        W)  WIPE_TARGET=1             ;;
        u)  UMOUNT_BEFORE=1           ;;
        x)  PARTCLONE_EXTRA="$OPTARG" ;;
        w)  STEP_DELAY="$OPTARG"      ;;
        V)  VERIFY_CLONE=1            ;;
        f)  FORCE_FSTYPE="$OPTARG"    ;;
        Z)  VERIFY_ONLY=1             ;;
        r)  DRY_RUN=1                 ;;
        h)  usage; exit 0             ;;
        :)  echo "❌  Option -${OPTARG} requires an argument." >&2; exit 1 ;;
        ?)  echo "❌  Unknown option: -${OPTARG}" >&2; exit 1 ;;
    esac
done

# ==============================================================================
# INPUT VALIDATION
# ==============================================================================

ERRORS=""
[ -z "$SOURCE_DEVICE" ] && ERRORS="${ERRORS}\n    -D  source disk device is required."
[ -z "$TARGET_DEVICE" ] && ERRORS="${ERRORS}\n    -d  target disk device is required."

case "$CLONE_MODE" in
    smart|dd) ;;
    *) ERRORS="${ERRORS}\n    -c  invalid value '${CLONE_MODE}'. Allowed: smart | dd" ;;
esac

case "$ALIGN_BYTES" in
    512|4096|1048576) ;;
    *) ERRORS="${ERRORS}\n    -a  invalid value '${ALIGN_BYTES}'. Allowed: 512 | 4096 | 1048576" ;;
esac

case "$STEP_DELAY" in
    ''|*[!0-9]*) ERRORS="${ERRORS}\n    -w  '${STEP_DELAY}' is not a valid non-negative integer." ;;
esac

if [ -n "$ERRORS" ]; then
    echo "❌  The following options are missing or invalid:" >&2
    printf "%b\n" "$ERRORS" >&2
    echo "    Run with -h for full help." >&2
    exit 1
fi

[ "$SOURCE_DEVICE" = "$TARGET_DEVICE" ] && die "Source and target device must be different."

ALIGN_SECTORS=$(( ALIGN_BYTES / 512 ))

# ==============================================================================
# BANNER
# ==============================================================================

hr
echo "💾  DISK MIGRATION / CLONE SCRIPT  v1.0"
hr
echo "  Source      : ${SOURCE_DEVICE}"
echo "  Target      : ${TARGET_DEVICE}"
echo "  Mode        : $( [ "$MOVE_MODE"      -eq 1 ] && echo "MOVE (source partitions will be removed)" || echo "CLONE (source preserved)" )"
echo "  Method      : $( [ "$PHYSICAL_MODE"  -eq 1 ] && echo "Physical (raw dd)" || echo "Logical (partition-by-partition)" )"
[ "$VERIFY_ONLY"  -eq 1 ] && echo "  Verify only : yes (no writes)"
[ "$PHYSICAL_MODE" -eq 1 ] && echo "  Include tail: $( [ "$INCLUDE_TAIL" -eq 1 ] && echo "yes" || echo "no (only used sectors)" )"
[ "$PHYSICAL_MODE" -eq 0 ] && {
    echo "  Clone method: $( [ "$CLONE_MODE" = "smart" ] && echo "Smart (filesystem-aware)" || echo "DD (byte-to-byte)" )"
    printf "  Alignment   : %d-byte (%d sectors)\n" "$ALIGN_BYTES" "$ALIGN_SECTORS"
    [ "$WIPE_TARGET" -eq 1 ] && echo "  Wipe target : yes"
    [ "$COPY_MBR"   -eq 1 ] && echo "  Copy MBR/GPT: yes"
    [ "$VERIFY_CLONE" -eq 1 ] && echo "  Verify      : yes (partclone.chkimg per partition)"
    [ -n "$FORCE_FSTYPE" ]   && echo "  Force FS    : ${FORCE_FSTYPE}"
    [ -n "$PARTCLONE_EXTRA" ] && echo "  Extra opts  : ${PARTCLONE_EXTRA}"
}
echo "  Unmount     : $( [ "$UMOUNT_BEFORE" -eq 1 ] && echo "yes" || echo "no" )"
echo "  Step delay  : ${STEP_DELAY}s"
[ "$DRY_RUN" -eq 1 ] && echo "  ⚠️  DRY-RUN  : NO data will be written — all invasive commands are simulated."
hr

# ==============================================================================
# STEP 1 — GATHER DISK INFORMATION
# ==============================================================================

echo "📐  [1] Reading partition tables…"

SRC_TOTAL=$(disk_size_sectors "$SOURCE_DEVICE")
TGT_TOTAL=$(disk_size_sectors "$TARGET_DEVICE")

[ -z "$SRC_TOTAL" ] && die "Cannot read partition table of ${SOURCE_DEVICE} (parted)."
[ -z "$TGT_TOTAL" ] && die "Cannot read partition table of ${TARGET_DEVICE} (parted)."

echo "     Source disk : ${SOURCE_DEVICE}  (${SRC_TOTAL} sectors)"
echo "     Target disk : ${TARGET_DEVICE}  (${TGT_TOTAL} sectors)"

# Read source partition list: number start end size fstype name
# parted machine-readable output: num:start:end:size:fs:name:flags;
SRC_PARTS=$(parted -s -m "$SOURCE_DEVICE" unit s print 2>/dev/null \
    | awk -F: 'NR>2 && $1 ~ /^[0-9]+$/ {
        gsub(/s/,"",$2); gsub(/s/,"",$3); gsub(/s/,"",$4);
        print $1, $2, $3, $4, $5, $6
    }')

if [ -z "$SRC_PARTS" ]; then
    echo "     ℹ  No partitions found on source disk."
    SRC_PARTS=""
fi

# Find last used sector on source
SRC_LAST_USED_SECTOR=0
while IFS=' ' read -r _pnum _pstart _pend _psize _pfs _pname; do
    [ -z "$_pnum" ] && continue
    [ "$_pend" -gt "$SRC_LAST_USED_SECTOR" ] && SRC_LAST_USED_SECTOR="$_pend"
done <<EOF
$SRC_PARTS
EOF

echo "     Last used sector on source: ${SRC_LAST_USED_SECTOR}"

# Capacity check: target must fit at least the used sectors of the source
REQUIRED_SECTORS=$(( SRC_LAST_USED_SECTOR + 1 ))
if [ "$TGT_TOTAL" -lt "$REQUIRED_SECTORS" ]; then
    die "Target disk (${TGT_TOTAL} sectors) is too small for source used space (${REQUIRED_SECTORS} sectors needed)."
fi
echo "     ✔ Target disk is large enough (${TGT_TOTAL} sectors available, ${REQUIRED_SECTORS} needed)."

PART_COUNT=0
while IFS=' ' read -r _pnum _pstart _pend _psize _pfs _pname; do
    [ -z "$_pnum" ] && continue
    PART_COUNT=$(( PART_COUNT + 1 ))
done <<EOF
$SRC_PARTS
EOF
echo "     Source partition count: ${PART_COUNT}"

step_pause

# ==============================================================================
# STEP 2 — UNMOUNT
# ==============================================================================

if [ "$UMOUNT_BEFORE" -eq 1 ]; then
    echo "⏏️   [2] Unmounting all source and target partitions…"
    # Unmount all source partitions
    _pnum=1
    while [ "$_pnum" -le 16 ]; do
        _ppath=$(partition_path "$SOURCE_DEVICE" "$_pnum")
        [ -b "$_ppath" ] && run umount "$_ppath" 2>/dev/null && echo "     Unmounted ${_ppath}."
        _pnum=$(( _pnum + 1 ))
    done
    # Unmount all target partitions  
    _pnum=1
    while [ "$_pnum" -le 16 ]; do
        _ppath=$(partition_path "$TARGET_DEVICE" "$_pnum")
        [ -b "$_ppath" ] && run umount "$_ppath" 2>/dev/null && echo "     Unmounted ${_ppath}."
        _pnum=$(( _pnum + 1 ))
    done
    echo "     ✔ Unmount sweep complete."
    step_pause
else
    echo "⏭️   [2] Unmount step skipped (-u not set)."
fi

# ==============================================================================
# PHYSICAL MODE
# ==============================================================================

if [ "$PHYSICAL_MODE" -eq 1 ]; then

    if [ "$VERIFY_ONLY" -eq 1 ]; then
        echo "🔍  [3] PHYSICAL VERIFY: comparing ${SOURCE_DEVICE} vs ${TARGET_DEVICE} with cmp…"
        COPY_SECTORS=$(( SRC_LAST_USED_SECTOR + 2048 ))   # include some pad
        [ "$COPY_SECTORS" -gt "$SRC_TOTAL" ] && COPY_SECTORS="$SRC_TOTAL"
        COPY_BYTES=$(( COPY_SECTORS * 512 ))
        if [ "$DRY_RUN" -eq 1 ]; then
            echo "🔸  [DRY-RUN] cmp -n ${COPY_BYTES} '${SOURCE_DEVICE}' '${TARGET_DEVICE}'"
            echo "     ✔ [DRY-RUN] Physical verify simulated."
        else
            if cmp -n "$COPY_BYTES" "$SOURCE_DEVICE" "$TARGET_DEVICE" >/dev/null 2>&1; then
                hr; echo "✅  DISKS ARE IDENTICAL (first ${COPY_BYTES} bytes)"; hr
            else
                hr; echo "❌  DISKS DIFFER"; hr; exit 1
            fi
        fi
        exit 0
    fi

    echo "💽  [3] PHYSICAL COPY: ${SOURCE_DEVICE} → ${TARGET_DEVICE} via dd…"

    if [ "$INCLUDE_TAIL" -eq 1 ]; then
        COPY_COUNT="$SRC_TOTAL"
        echo "     Copy scope: full disk (${COPY_COUNT} sectors = $(( COPY_COUNT / 2048 )) MiB approx.)"
    else
        # Copy only up to last used sector + 2 MiB padding
        PADDING_SECTORS=4096   # 2 MiB at 512 B/sector
        COPY_COUNT=$(( SRC_LAST_USED_SECTOR + PADDING_SECTORS + 1 ))
        [ "$COPY_COUNT" -gt "$SRC_TOTAL" ] && COPY_COUNT="$SRC_TOTAL"
        echo "     Copy scope: used sectors only (${COPY_COUNT} sectors = $(( COPY_COUNT / 2048 )) MiB approx.)"
    fi

    if [ "$DRY_RUN" -eq 1 ]; then
        echo "🔸  [DRY-RUN] dd if='${SOURCE_DEVICE}' of='${TARGET_DEVICE}' bs=1M count=$(( COPY_COUNT / 2048 + 1 )) status=progress"
    else
        COPY_BYTES=$(( COPY_COUNT * 512 ))
        # Use bs=1M; calculate count by ceiling division
        DD_BS=1048576
        DD_COUNT=$(( (COPY_BYTES + DD_BS - 1) / DD_BS ))
        echo "     dd: src=${SOURCE_DEVICE} dst=${TARGET_DEVICE} bs=1M count=${DD_COUNT}"
        dd if="$SOURCE_DEVICE" of="$TARGET_DEVICE" bs=1M count="$DD_COUNT" conv=fsync status=progress \
            || die "dd failed during physical copy."
        # Update target partition table in kernel
        run partprobe "$TARGET_DEVICE" 2>/dev/null || true
    fi

    step_pause

    if [ "$MOVE_MODE" -eq 1 ]; then
        echo "🧹  [4] MOVE MODE: wiping source disk partition table…"
        if [ "$DRY_RUN" -eq 1 ]; then
            echo "🔸  [DRY-RUN] parted -s '${SOURCE_DEVICE}' mklabel gpt"
        else
            # Read source partition table type
            _pttype=$(parted -s -m "$SOURCE_DEVICE" unit s print 2>/dev/null \
                | awk -F: 'NR==2 {print $6}')
            [ -z "$_pttype" ] && _pttype="gpt"
            parted -s "$SOURCE_DEVICE" mklabel "$_pttype" \
                || echo "⚠️   Could not re-initialize source partition table (continuing)."
            run partprobe "$SOURCE_DEVICE" 2>/dev/null || true
        fi
        echo "     ✔ Source disk partition table cleared."
    fi

    hr
    [ "$DRY_RUN" -eq 1 ] && echo "🔸  DRY-RUN PHYSICAL COPY COMPLETED" || echo "✨  PHYSICAL COPY COMPLETED SUCCESSFULLY"
    hr
    exit 0
fi

# ==============================================================================
# LOGICAL MODE
# ==============================================================================

# ==============================================================================
# STEP 3 — VERIFY-ONLY MODE (logical)
# ==============================================================================

if [ "$VERIFY_ONLY" -eq 1 ]; then
    echo "🔍  [3] VERIFY-ONLY MODE: comparing source/target partition pairs…"
    _errors=0

    while IFS=' ' read -r _pnum _pstart _pend _psize _pfs _pname; do
        [ -z "$_pnum" ] && continue
        _src_part=$(partition_path "$SOURCE_DEVICE" "$_pnum")
        _tgt_part=$(partition_path "$TARGET_DEVICE" "$_pnum")

        echo "     Comparing p${_pnum}: ${_src_part}  vs  ${_tgt_part} …"
        if [ ! -b "$_src_part" ]; then
            echo "     ⚠️  Source ${_src_part} not found – skipped."
            continue
        fi
        if [ ! -b "$_tgt_part" ]; then
            echo "     ⚠️  Target ${_tgt_part} not found – skipped."
            continue
        fi

        _sz_src=''
        _sz_tgt=''
        if command -v blockdev >/dev/null 2>&1; then
            _sz_src=$(blockdev --getsize64 "$_src_part" 2>/dev/null)
            _sz_tgt=$(blockdev --getsize64 "$_tgt_part" 2>/dev/null)
        fi
        [ -z "$_sz_src" ] && _sz_src=$(wc -c < "$_src_part" 2>/dev/null)
        [ -z "$_sz_tgt" ] && _sz_tgt=$(wc -c < "$_tgt_part" 2>/dev/null)

        if [ -n "$_sz_src" ] && [ -n "$_sz_tgt" ] && [ "$_sz_src" != "$_sz_tgt" ]; then
            echo "     ⚠️  Sizes differ: src=${_sz_src} tgt=${_sz_tgt} – cmp stops at smaller."
        fi

        if [ "$DRY_RUN" -eq 1 ]; then
            echo "🔸  [DRY-RUN] cmp '${_src_part}' '${_tgt_part}'"
        elif cmp "$_src_part" "$_tgt_part" >/dev/null 2>&1; then
            echo "     ✔ p${_pnum}: IDENTICAL"
        else
            echo "     ❌ p${_pnum}: DIFFER"
            _errors=$(( _errors + 1 ))
        fi
        step_pause
    done <<EOF
$SRC_PARTS
EOF

    hr
    if [ "$DRY_RUN" -eq 1 ]; then
        echo "🔸  DRY-RUN VERIFY SIMULATION COMPLETED"
    elif [ "$_errors" -eq 0 ]; then
        echo "✅  ALL PARTITIONS ARE IDENTICAL"
    else
        echo "❌  ${_errors} PARTITION(S) DIFFER"
    fi
    hr
    [ "$_errors" -eq 0 ] && exit 0 || exit 1
fi

# ==============================================================================
# STEP 3 — WIPE TARGET (optional)
# ==============================================================================

if [ "$WIPE_TARGET" -eq 1 ]; then
    echo "🗑️   [3] Wiping all target partitions from ${TARGET_DEVICE}…"
    TGT_PTTYPE=$(parted -s -m "$TARGET_DEVICE" unit s print 2>/dev/null \
        | awk -F: 'NR==2 {print $6}')
    # Il target senza tabella riporta "unknown" (non stringa vuota): in quel
    # caso rispecchia il tipo della sorgente (come per un target vuoto).
    case "$TGT_PTTYPE" in
        ''|unknown)
            TGT_PTTYPE=$(parted -s -m "$SOURCE_DEVICE" unit s print 2>/dev/null \
                | awk -F: 'NR==2 {print $6}')
            ;;
    esac
    # Normalizza: valori accettati da `parted mklabel` (loop/altro → gpt).
    case "$TGT_PTTYPE" in
        gpt|msdos) : ;;
        *) TGT_PTTYPE="gpt" ;;
    esac

    if [ "$DRY_RUN" -eq 1 ]; then
        echo "🔸  [DRY-RUN] parted -s '${TARGET_DEVICE}' mklabel '${TGT_PTTYPE}'"
    else
        parted -s "$TARGET_DEVICE" mklabel "$TGT_PTTYPE" \
            || die "Failed to initialize partition table on ${TARGET_DEVICE}."
        run partprobe "$TARGET_DEVICE" 2>/dev/null || true
        echo "     ✔ Target partition table re-initialized (${TGT_PTTYPE})."
    fi
    step_pause
else
    echo "⏭️   [3] Target wipe skipped (-W not set)."
fi

# ==============================================================================
# STEP 4 — COPY MBR/GPT HEADER (optional)
# ==============================================================================

if [ "$COPY_MBR" -eq 1 ]; then
    echo "🗂️   [4] Copying MBR/GPT header from ${SOURCE_DEVICE} to ${TARGET_DEVICE}…"
    SRC_PTTYPE=$(parted -s -m "$SOURCE_DEVICE" unit s print 2>/dev/null \
        | awk -F: 'NR==2 {print $6}')

    if [ "$SRC_PTTYPE" = "gpt" ]; then
        # GPT: primary header in sector 0 (MBR) + sector 1 (GPT header) + sectors 2-33 (partition entries)
        HEADER_SECTORS=34
    else
        # MBR: just the first 512 bytes
        HEADER_SECTORS=1
    fi

    echo "     Partition table type: ${SRC_PTTYPE}  (copying first ${HEADER_SECTORS} sector(s))"
    if [ "$DRY_RUN" -eq 1 ]; then
        echo "🔸  [DRY-RUN] dd if='${SOURCE_DEVICE}' of='${TARGET_DEVICE}' bs=512 count=${HEADER_SECTORS} conv=notrunc"
    else
        dd if="$SOURCE_DEVICE" of="$TARGET_DEVICE" bs=512 count="$HEADER_SECTORS" conv=notrunc \
            || die "Failed to copy MBR/GPT header."
        run partprobe "$TARGET_DEVICE" 2>/dev/null || true
        echo "     ✔ MBR/GPT header copied."
    fi
    step_pause
else
    echo "⏭️   [4] MBR/GPT copy skipped (-B not set)."
fi

# ==============================================================================
# STEP 5 — CLONE PARTITIONS
# ==============================================================================

echo "🔄  [5] Cloning partitions (${PART_COUNT} partition(s))…"

# Ensure the target has a partition table (mirroring the source when the target
# is blank), otherwise the `parted mkpart` calls below fail with
# "unrecognised disk label".
_TGT_PTTYPE=$(parted -s -m "$TARGET_DEVICE" unit s print 2>/dev/null \
    | awk -F: 'NR==2 {print $6}')
if [ -z "$_TGT_PTTYPE" ] || [ "$_TGT_PTTYPE" = "unknown" ]; then
    _SRC_PTTYPE=$(parted -s -m "$SOURCE_DEVICE" unit s print 2>/dev/null \
        | awk -F: 'NR==2 {print $6}')
    case "$_SRC_PTTYPE" in
        gpt|msdos) _NEW_PTTYPE="$_SRC_PTTYPE" ;;
        *)         _NEW_PTTYPE="msdos" ;;
    esac
    echo "     ℹ Target has no partition table — initializing ${_NEW_PTTYPE}."
    if [ "$DRY_RUN" -eq 1 ]; then
        echo "🔸  [DRY-RUN] parted -s '${TARGET_DEVICE}' mklabel '${_NEW_PTTYPE}'"
    else
        parted -s "$TARGET_DEVICE" mklabel "$_NEW_PTTYPE" \
            || die "Failed to initialize partition table on ${TARGET_DEVICE}."
        run partprobe "$TARGET_DEVICE" 2>/dev/null || true
        echo "     ✔ Target partition table initialized (${_NEW_PTTYPE})."
    fi
    step_pause
fi

# Scaling factor: partitions are NEVER shrunk below their source size — each
# partition is copied in full and the capacity check above already guarantees
# the source's used sectors fit on the target (REQUIRED_SECTORS <= TGT_TOTAL).
# Scaling by the TOTAL disk sizes (TGT_TOTAL/SRC_TOTAL) was WRONG: e.g. cloning
# a 256M source (used data up to sector 309231) onto a 192M target (393216
# sectors, 309232 needed) applied a 393216/524288 factor, shrank every partition
# below its source size, SKIPPED all of them, and still reported success with
# 0/N cloned. The branch below is only a defensive guard (unreachable after the
# capacity check aborts the run when the used data does not fit).
if [ "$REQUIRED_SECTORS" -gt "$TGT_TOTAL" ]; then
    # Cannot happen here (the capacity check above would have aborted).
    SCALE_NUM="$TGT_TOTAL"
    SCALE_DEN="$REQUIRED_SECTORS"
    echo "     Target smaller than source used space: proportional scaling applied."
    echo "     Scale: ${SCALE_NUM} / ${SCALE_DEN}"
else
    SCALE_NUM=1
    SCALE_DEN=1
fi

CLONED=0
FAILED=0
_CLONED_PARTS=""

# Rileva il tipo di tabella della sorgente e, per MBR/msdos, il contenitore
# extended: serve per ricreare le partizioni con il ruolo corretto.
SRC_PTTYPE=$(parted -s -m "$SOURCE_DEVICE" unit s print 2>/dev/null \
    | awk -F: 'NR==2 {print $6}')
SRC_EXT_START=''
SRC_EXT_END=''
if [ "$SRC_PTTYPE" = "msdos" ]; then
    _first_logical=$(printf '%s\n' "$SRC_PARTS" | awk '$1 >= 5 {print; exit}')
    if [ -n "$_first_logical" ]; then
        SRC_EXT_START=$(printf '%s\n' "$SRC_PARTS" | awk -v l="$_first_logical" '
            BEGIN { split(l, a, " "); ls=a[2]; le=a[3] }
            $1 <= 4 && $2 <= ls && $3 >= le { print $2; exit }')
        SRC_EXT_END=$(printf '%s\n' "$SRC_PARTS" | awk -v l="$_first_logical" '
            BEGIN { split(l, a, " "); ls=a[2]; le=a[3] }
            $1 <= 4 && $2 <= ls && $3 >= le { print $3; exit }')
    fi
fi

while IFS=' ' read -r _pnum _pstart _pend _psize _pfs _pname; do
    [ -z "$_pnum" ] && continue

    hr
    echo "📦  Partition ${_pnum}: source sectors ${_pstart}–${_pend}  (${_psize} sectors)"
    [ -n "$_pname" ] && echo "     Name: ${_pname}"
    [ -n "$_pfs"   ] && echo "     FS:   ${_pfs}"

    _src_part=$(partition_path "$SOURCE_DEVICE" "$_pnum")

    # Ruolo per tabelle MBR/msdos (extended/logical/primary); su GPT nessun ruolo.
    _part_role='primary'
    if [ "$SRC_PTTYPE" = "msdos" ]; then
        if [ "$_pnum" -ge 5 ]; then
            _part_role='logical'
        elif [ -n "$SRC_EXT_START" ] && [ "$_pstart" -eq "$SRC_EXT_START" ] 2>/dev/null; then
            _part_role='extended'
        fi
    fi

    # Compute scaled target start (proportional when target < source)
    _tgt_start=$(( _pstart * SCALE_NUM / SCALE_DEN ))
    _tgt_start=$(align_up "$_tgt_start" "$ALIGN_SECTORS")

    # Size the range from the SOURCE partition size, NOT from aligned endpoints.
    # (Old code aligned _pend DOWN, silently losing up to ALIGN_SECTORS sectors,
    # so the size check below always skipped the last partition of a disk even
    # when the target was large enough.)
    _tgt_size=$(( _psize * SCALE_NUM / SCALE_DEN ))
    _tgt_end=$(( _tgt_start + _tgt_size - 1 ))

    # Make sure target range fits on disk
    if [ "$_tgt_end" -ge "$TGT_TOTAL" ]; then
        _tgt_end=$(( TGT_TOTAL - 1 ))
        _tgt_size=$(( _tgt_end - _tgt_start + 1 ))
    fi

    # If clamping trimmed the range below the source size, try to recover by
    # moving the start one alignment unit earlier (still alignment-aligned).
    if [ "$_tgt_size" -lt "$_psize" ] && [ "$_tgt_start" -ge "$ALIGN_SECTORS" ]; then
        _tgt_start=$(( _tgt_start - ALIGN_SECTORS ))
        _tgt_end=$(( _tgt_start + _tgt_size - 1 ))
        if [ "$_tgt_end" -ge "$TGT_TOTAL" ]; then
            _tgt_end=$(( TGT_TOTAL - 1 ))
        fi
        _tgt_size=$(( _tgt_end - _tgt_start + 1 ))
    fi

    if [ "$_tgt_size" -lt "$_psize" ]; then
        echo "     ❌  SKIPPED: scaled target range (${_tgt_size} sectors) is smaller than source partition (${_psize} sectors)."
        FAILED=$(( FAILED + 1 ))
        continue
    fi
    echo "     Target range: sectors ${_tgt_start}–${_tgt_end}  (${_tgt_size} sectors)"
    step_pause

    # Create target partition
    echo "🏗️   Creating target partition ${_pnum} on ${TARGET_DEVICE}…"
    _fstype_hint=""
    if [ -n "$_pfs" ] && [ "$_pfs" != "unknown" ]; then
        _fstype_hint="$_pfs"
    fi

    if [ "$DRY_RUN" -eq 1 ]; then
        if [ "$SRC_PTTYPE" = "msdos" ]; then
            echo "🔸  [DRY-RUN] parted -s '${TARGET_DEVICE}' unit s mkpart ${_part_role} ${_fstype_hint} ${_tgt_start}s ${_tgt_end}s"
        else
            echo "🔸  [DRY-RUN] parted -s '${TARGET_DEVICE}' unit s mkpart '' ${_tgt_start}s ${_tgt_end}s"
        fi
        [ -n "$_pname" ] && echo "🔸  [DRY-RUN] parted -s '${TARGET_DEVICE}' name ${_pnum} '${_pname}'"
        echo "🔸  [DRY-RUN] partprobe '${TARGET_DEVICE}'"
        _tgt_part=$(partition_path "$TARGET_DEVICE" "$_pnum")
        echo "     (Simulated target partition: ${_tgt_part})"
    else
        _mkpart_ok=1
        if [ "$SRC_PTTYPE" = "msdos" ]; then
            if [ -n "$_fstype_hint" ]; then
                parted -s "$TARGET_DEVICE" unit s mkpart "$_part_role" "$_fstype_hint" "${_tgt_start}s" "${_tgt_end}s" || _mkpart_ok=0
            else
                parted -s "$TARGET_DEVICE" unit s mkpart "$_part_role" "${_tgt_start}s" "${_tgt_end}s" || _mkpart_ok=0
            fi
        else
            parted -s "$TARGET_DEVICE" unit s mkpart "" "${_tgt_start}s" "${_tgt_end}s" || _mkpart_ok=0
        fi
        # Tollerante: se mkpart fallisce ma esiste già una partizione con lo
        # stesso start (es. tabella copiata con -B o run ripetuta), la riusa.
        if [ "$_mkpart_ok" = "0" ]; then
            _exists=$(parted -s -m "$TARGET_DEVICE" unit s print 2>/dev/null \
                | awk -F: -v s="${_tgt_start}" 'NR>2 && $1 ~ /^[0-9]+$/ {
                    gsub(/s/,"",$2); if ($2 == s) { print $1; exit } }')
            if [ -n "$_exists" ]; then
                echo "     ⚠️  Partition with start ${_tgt_start} already exists (${_exists}) — reusing it."
                _mkpart_ok=1
            else
                die "Failed to create partition ${_pnum} on ${TARGET_DEVICE}."
            fi
        fi
        [ -n "$_pname" ] && parted -s "$TARGET_DEVICE" name "$_pnum" "$_pname" 2>/dev/null || true
        partprobe "$TARGET_DEVICE" 2>/dev/null || true
        sleep 1

        # Resolve target partition node. On WSL2 loop devices the kernel can lag
        # behind parted's table writes (partprobe "unable to inform the kernel"),
        # so re-probe inside the retry loop. Never fall back to the SOURCE
        # partition number: for MBR logical partitions the target renumbers them
        # (5,6,7,… in creation order), so guessing with the source number clones
        # into the WRONG partition and corrupts data.
        _tgt_part=''
        _try=0
        while [ "$_try" -lt 10 ] && [ -z "$_tgt_part" ]; do
            partprobe "$TARGET_DEVICE" 2>/dev/null || true
            _candidate=$(parted -s -m "$TARGET_DEVICE" unit s print 2>/dev/null \
                | awk -F: -v s="${_tgt_start}" '$1 ~ /^[0-9]+$/ {
                    gsub(/s/,"",$2);
                    if ($2 == s) { print $1; exit }
                }')
            if [ -n "$_candidate" ]; then
                _tgt_part=$(partition_path "$TARGET_DEVICE" "$_candidate")
                [ -b "$_tgt_part" ] || _tgt_part=''
            fi
            [ -z "$_tgt_part" ] && sleep 1
            _try=$(( _try + 1 ))
        done
        if [ -z "$_tgt_part" ]; then
            echo "     ❌  Could not resolve target partition node for start ${_tgt_start}."
            echo "         Target table:"
            parted -s -m "$TARGET_DEVICE" unit s print 2>/dev/null | sed 's/^/           /'
            die "Could not resolve target partition node for source p${_pnum} (start ${_tgt_start}); aborting to avoid cloning into the wrong partition."
        fi
        echo "     ✔ Target partition created: ${_tgt_part}"
    fi

    step_pause

    # Il contenitore extended non contiene dati: viene solo creato (mkpart) e
    # le partizioni logiche al suo interno vengono clonate singolarmente.
    # Clonarlo con partclone.dd è inutile e su WSL2 corrompe la vista della
    # tabella per parted (quirk cache dei loop device: "wrong signature 0").
    if [ "$_part_role" = "extended" ]; then
        echo "     ⏭️  Extended container (${_pnum}): no data to clone — logical partitions are cloned individually."
        CLONED=$(( CLONED + 1 ))
        _CLONED_PARTS="${_CLONED_PARTS} ${_pnum}"
        step_pause
        continue
    fi

    # Clone data
    echo "💾  Cloning data: ${_src_part}  ──▶  ${_tgt_part}…"
    _fstype="${FORCE_FSTYPE:-}"
    [ -z "$_fstype" ] && _fstype=$(detect_fs "$_src_part")
    [ -z "$_fstype" ] && _fstype="$_pfs"
    [ -z "$_fstype" ] && _fstype="unknown"

    # Select partclone backend
    _partclone_bin=""
    if [ "$CLONE_MODE" = "smart" ]; then
        case "$_fstype" in
            ext2)                _partclone_bin="partclone.ext2"    ;;
            ext3)                _partclone_bin="partclone.ext3"    ;;
            ext4|ext4dev)        _partclone_bin="partclone.ext4"    ;;
            btrfs)               _partclone_bin="partclone.btrfs"   ;;
            xfs)                 _partclone_bin="partclone.xfs"     ;;
            ntfs)                _partclone_bin="partclone.ntfs"    ;;
            vfat)                _partclone_bin="partclone.vfat"    ;;
            fat|fat12|fat32)     _partclone_bin="partclone.fat"     ;;
            fat16)               _partclone_bin="partclone.fat16"   ;;
            exfat)               _partclone_bin="partclone.exfat"   ;;
            apfs)                _partclone_bin="partclone.apfs"    ;;
            hfs|hfs+|hfsp*)      _partclone_bin="partclone.hfsplus" ;;
            f2fs)                _partclone_bin="partclone.f2fs"    ;;
            minix|minix3)        _partclone_bin="partclone.minix"   ;;
            *)
                echo "     ⚠️  No smart backend for '${_fstype}' — falling back to partclone.dd."
                _partclone_bin="partclone.dd"
                ;;
        esac
    else
        _partclone_bin="partclone.dd"
    fi

    # partclone.dd (v0.3.x) NON accetta --dev-to-dev (-b): solo i backend
    # filesystem-aware lo supportano.
    _pcdd=0
    case "$_partclone_bin" in
        partclone.dd) _pcdd=1 ;;
    esac

    if [ "$DRY_RUN" -eq 1 ]; then
        if [ "$_pcdd" -eq 1 ]; then
            echo "🔸  [DRY-RUN] ${_partclone_bin} --overwrite --quiet --source '${_src_part}' --output '${_tgt_part}' ${PARTCLONE_EXTRA}"
        else
            echo "🔸  [DRY-RUN] ${_partclone_bin} --dev-to-dev --overwrite --quiet --source '${_src_part}' --output '${_tgt_part}' ${PARTCLONE_EXTRA}"
        fi
    else
        command -v "$_partclone_bin" >/dev/null 2>&1 \
            || die "${_partclone_bin} not found in PATH."
        # shellcheck disable=SC2086
        # --dev-to-dev (-b): sorgente e target sono ENTRAMBI device a blocchi →
        # copia dati grezzi. NON usare --clone (-c): scriverebbe il formato
        # immagine partclone (header + blocchi sparsi), non un filesystem
        # montabile ("Bad magic number" da e2fsck/tune2fs/mount).
        # --overwrite: la partizione target è appena stata creata e va
        # sovrascritta; senza, partclone >= 0.3.x rifiuta di scrivere su un
        # device che già esiste.
        if [ "$_pcdd" -eq 1 ]; then
            "$_partclone_bin" \
                --overwrite \
                --quiet \
                --source "$_src_part" \
                --output "$_tgt_part" \
                $PARTCLONE_EXTRA \
                || die "partclone failed on partition ${_pnum}."
        else
            "$_partclone_bin" \
                --dev-to-dev \
                --overwrite \
                --quiet \
                --source "$_src_part" \
                --output "$_tgt_part" \
                $PARTCLONE_EXTRA \
                || die "partclone failed on partition ${_pnum}."
        fi
        echo "     ✔ Data clone of partition ${_pnum} completed."
    fi

    step_pause

    # Verify (optional)
    if [ "$VERIFY_CLONE" -eq 1 ]; then
        echo "🔬  Verifying clone integrity on ${_tgt_part}…"
        if [ "$DRY_RUN" -eq 1 ]; then
            echo "🔸  [DRY-RUN] partclone.chkimg -s '${_tgt_part}'"
        elif command -v partclone.chkimg >/dev/null 2>&1; then
            partclone.chkimg -s "$_tgt_part" \
                || echo "     ⚠️  partclone.chkimg reported errors on partition ${_pnum}."
            echo "     ✔ partclone.chkimg passed for partition ${_pnum}."
        else
            echo "     ⚠️  partclone.chkimg not found — verify skipped for partition ${_pnum}."
        fi
        step_pause
    fi

    # Post-clone FS integrity
    if [ "$DRY_RUN" -eq 0 ]; then
        echo "🛠️   Post-clone integrity on ${_tgt_part} (${_fstype})…"
        case "$_fstype" in
            ext2|ext3|ext4|ext4dev)
                if command -v tune2fs >/dev/null 2>&1; then
                    tune2fs -U random "$_tgt_part" 2>/dev/null && echo "     → New UUID assigned."
                fi
                if command -v e2fsck >/dev/null 2>&1; then
                    e2fsck -p -f "$_tgt_part" 2>/dev/null && echo "     → e2fsck passed."
                fi
                ;;
            vfat|fat|fat12|fat16|fat32)
                if command -v dosfsck >/dev/null 2>&1; then
                    dosfsck -a "$_tgt_part" 2>/dev/null || true
                elif command -v fsck.fat >/dev/null 2>&1; then
                    fsck.fat -a "$_tgt_part" 2>/dev/null || true
                fi
                ;;
            ntfs)
                command -v ntfsfix >/dev/null 2>&1 && ntfsfix "$_tgt_part" 2>/dev/null || true
                ;;
        esac
        echo "     ✔ Post-clone checks done for partition ${_pnum}."
    fi

    CLONED=$(( CLONED + 1 ))
    _CLONED_PARTS="${_CLONED_PARTS} ${_pnum}"
    step_pause

done <<EOF
$SRC_PARTS
EOF

# ==============================================================================
# STEP 6 — MOVE: DELETE SOURCE PARTITIONS (optional)
# ==============================================================================

if [ "$MOVE_MODE" -eq 1 ]; then
    step_pause
    echo "🧹  [6] MOVE MODE: deleting source partitions from ${SOURCE_DEVICE}…"
    while IFS=' ' read -r _pnum _pstart _pend _psize _pfs _pname; do
        [ -z "$_pnum" ] && continue
        echo "     Deleting source partition ${_pnum}…"
        if [ "$DRY_RUN" -eq 1 ]; then
            echo "🔸  [DRY-RUN] parted -s '${SOURCE_DEVICE}' rm ${_pnum}"
        else
            parted -s "$SOURCE_DEVICE" rm "$_pnum" 2>/dev/null \
                || echo "     ⚠️  Failed to delete source partition ${_pnum} (continuing)."
        fi
    done <<EOF
$SRC_PARTS
EOF
    run partprobe "$SOURCE_DEVICE" 2>/dev/null || true
    echo "     ✔ Source partitions removed."
fi

# ==============================================================================
# FINAL SUMMARY
# ==============================================================================

hr
if [ "$DRY_RUN" -eq 1 ]; then
    echo "🔸  DRY-RUN SIMULATION COMPLETED — NO DATA WAS WRITTEN"
elif [ "$FAILED" -gt 0 ]; then
    echo "⚠️  DISK MIGRATION COMPLETED WITH ERRORS — ${FAILED}/${PART_COUNT} partition(s) NOT cloned"
else
    echo "✨  DISK MIGRATION COMPLETED SUCCESSFULLY"
fi
hr
echo "  Source : ${SOURCE_DEVICE}  →  $( [ "$MOVE_MODE" -eq 1 ] && echo "partition table cleared" || echo "preserved" )"
echo "  Target : ${TARGET_DEVICE}"
echo "  Cloned : ${CLONED}/${PART_COUNT} partition(s)"
[ "$FAILED" -gt 0 ] && echo "  Failed : ${FAILED} partition(s) (size mismatch)"
echo "  Method : $( [ "$CLONE_MODE" = "smart" ] && echo "Smart (filesystem-aware)" || echo "DD (byte-to-byte)" )"
hr
# A migration that skipped partitions must FAIL, otherwise the caller (CGI/queue)
# would report "completed successfully" while nothing (or only some) was cloned.
[ "$FAILED" -gt 0 ] && exit 1
exit 0
