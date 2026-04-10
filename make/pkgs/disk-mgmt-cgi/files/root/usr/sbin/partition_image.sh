#!/bin/sh
# partition_image.sh — Export/Import/Network clone a partition via partclone
#
# USAGE (export):
#   partition_image.sh -e -p /dev/sda1 -o /path/to/image.img [-z gzip|bzip2|lz4|zstd] [-u] [-V] [-w N] [-r]
#
# USAGE (import/restore):
#   partition_image.sh -i -p /dev/sda1 -o /path/to/image.img [-z gzip|bzip2|lz4|zstd] [-u] [-V] [-w N] [-r]
#
# USAGE (network send):
#   partition_image.sh -N -p /dev/sda1 -H <ip> -P <port> [-z gzip|bzip2|lz4|zstd] [-u] [-w N] [-r]
#   or multicast: partition_image.sh -N -p /dev/sda1 -H 239.0.0.1 -P 9000 --multicast [-z]
#
# USAGE (network receive):
#   partition_image.sh -R -p /dev/sda1 -H <bind_ip> -P <port> [-z gzip|bzip2|lz4|zstd] [-u] [-V] [-w N] [-r]
#
# USAGE (ddrescue):
#   partition_image.sh -G -p /dev/sda1 -o /path/to/image.img [-l /path/logfile] [-r N] [-w N] [-u]
#
# USAGE (disk export / import via dd):
#   partition_image.sh -e -D /dev/sda -o /path/disk.img [-z ...] [-w N] [-r]
#   partition_image.sh -i -D /dev/sda -o /path/disk.img [-z ...] [-w N] [-r]
#
# OPTIONS:
#   -e          Export (partition/disk → image file)
#   -i          Import/restore (image file → partition/disk)
#   -N          Network send
#   -R          Network receive
#   -G          ddrescue clone to image
#   -p DEV      Source/target partition (e.g. /dev/sda1)
#   -D DEV      Source/target whole disk (e.g. /dev/sda)
#   -o PATH     Image file path (for export/import/ddrescue)
#   -z COMP     Compression: none, gzip, bzip2, lz4, zstd
#   -H IP       Remote host IP (network send) or bind IP (receive)
#   -P PORT     TCP port
#   -m          Multicast mode (use with -N)
#   -l PATH     ddrescue log file path
#   -r N        ddrescue: max retry passes (default 3)
#   -f FSTYPE   Force filesystem type (override auto-detect)
#   -u          Unmount partition before operation
#   -V          Verify image after export (partclone.chkimg)
#   -w N        Step delay in seconds (default 1)
#   -c dd       Use partclone.dd regardless of filesystem
#   -B N        Buffer size for dd (default 1M)
#   -x OPTS     Extra options passed to partclone
#   -v          Verbose output
#   -n          No-op / dry-run (print commands, do not execute)

set -e

# ── Defaults ──────────────────────────────────────────────────────────────────
MODE=''         # export | import | net_send | net_recv | ddrescue
PARTITION=''
DISK=''
IMAGE_PATH=''
COMPRESSION='none'
NET_HOST=''
NET_PORT='9000'
MULTICAST=0
DDRESCUE_LOG=''
DDRESCUE_RETRIES='3'
FORCE_FS=''
UNMOUNT=0
VERIFY=0
STEP_DELAY='1'
USE_DD=0
DD_BS='1M'
EXTRA_OPTS=''
VERBOSE=0
DRY_RUN=0

log() { printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }
err() { log "ERROR: $*" >&2; exit 1; }
warn() { log "WARN: $*" >&2; }
run() {
    if [ "$DRY_RUN" = "1" ]; then
        printf '  [dry-run] %s\n' "$*"
    else
        [ "$VERBOSE" = "1" ] && log "RUN: $*"
        eval "$@"
    fi
}

# ── Option parsing ─────────────────────────────────────────────────────────────
while [ $# -gt 0 ]; do
    case "$1" in
        -e) MODE='export' ;;
        -i) MODE='import' ;;
        -N) MODE='net_send' ;;
        -R) MODE='net_recv' ;;
        -G) MODE='ddrescue' ;;
        -p) PARTITION="$2"; shift ;;
        -D) DISK="$2"; shift ;;
        -o) IMAGE_PATH="$2"; shift ;;
        -z) COMPRESSION="$2"; shift ;;
        -H) NET_HOST="$2"; shift ;;
        -P) NET_PORT="$2"; shift ;;
        -m|--multicast) MULTICAST=1 ;;
        -l) DDRESCUE_LOG="$2"; shift ;;
        -r) DDRESCUE_RETRIES="$2"; shift ;;
        -f) FORCE_FS="$2"; shift ;;
        -u) UNMOUNT=1 ;;
        -V) VERIFY=1 ;;
        -w) STEP_DELAY="$2"; shift ;;
        -c) USE_DD=1 ;;  # -c dd
        -B) DD_BS="$2"; shift ;;
        -x) EXTRA_OPTS="$2"; shift ;;
        -v) VERBOSE=1 ;;
        -n) DRY_RUN=1 ;;
        *) warn "Unknown option: $1" ;;
    esac
    shift
done

# ── Determine target block device ──────────────────────────────────────────────
TARGET=''
if [ -n "$PARTITION" ]; then
    TARGET="$PARTITION"
elif [ -n "$DISK" ]; then
    TARGET="$DISK"
fi

[ -n "$MODE"   ] || err "No mode specified (-e, -i, -N, -R, -G)"
[ -n "$TARGET" ] || err "No partition (-p) or disk (-D) specified"
[ -b "$TARGET" ] || [ "$DRY_RUN" = "1" ] || err "Device not a block device: $TARGET"

# ── Step delay ────────────────────────────────────────────────────────────────
step_delay() {
    [ "$STEP_DELAY" -gt 0 ] 2>/dev/null && sleep "$STEP_DELAY"
    return 0
}

# ── Unmount ────────────────────────────────────────────────────────────────────
do_unmount() {
    [ "$UNMOUNT" = "1" ] || return 0
    log "Unmounting $TARGET ..."
    run "umount '$TARGET' 2>/dev/null || true"
    step_delay
}

# ── Detect filesystem type ─────────────────────────────────────────────────────
detect_fs() {
    [ -n "$FORCE_FS" ] && { echo "$FORCE_FS"; return; }
    _fs=''
    if command -v blkid >/dev/null 2>&1; then
        _fs=$(blkid -o value -s TYPE "$TARGET" 2>/dev/null | head -n 1)
    fi
    if [ -z "$_fs" ] && command -v lsblk >/dev/null 2>&1; then
        _fs=$(lsblk -dn -o FSTYPE "$TARGET" 2>/dev/null | head -n 1)
    fi
    echo "${_fs:-unknown}"
}

# ── Resolve partclone binary for fs type ──────────────────────────────────────
resolve_partclone() {
    _fs="$1"
    [ "$USE_DD" = "1" ] && { echo "partclone.dd"; return; }
    [ -n "$DISK" ]      && { echo "partclone.dd"; return; }  # whole disk → dd
    case "$_fs" in
        ext2)              echo "partclone.ext2" ;;
        ext3)              echo "partclone.ext3" ;;
        ext4|ext4dev)      echo "partclone.ext4" ;;
        btrfs)             echo "partclone.btrfs" ;;
        xfs)               echo "partclone.xfs" ;;
        f2fs)              echo "partclone.f2fs" ;;
        ntfs)              echo "partclone.ntfs" ;;
        fat|fat12|fat16|fat32|vfat)  echo "partclone.fat32" ;;
        exfat)             echo "partclone.exfat" ;;
        hfs|hfs+|hfsp|hfsplus) echo "partclone.hfsplus" ;;
        minix)             echo "partclone.minix" ;;
        apfs)              echo "partclone.apfs" ;;
        *)                 echo "partclone.dd" ;;
    esac
}

# ── Compression pipe helpers ───────────────────────────────────────────────────
compress_cmd() {
    case "$COMPRESSION" in
        gzip|gz)   echo "gzip -c" ;;
        bzip2|bz2) echo "bzip2 -c" ;;
        lz4)       echo "lz4 -c" ;;
        zstd)      echo "zstd -c" ;;
        *)         echo "cat" ;;
    esac
}

decompress_cmd() {
    case "$COMPRESSION" in
        gzip|gz)   echo "gunzip -c" ;;
        bzip2|bz2) echo "bunzip2 -c" ;;
        lz4)       echo "lz4 -dc" ;;
        zstd)      echo "zstd -dc" ;;
        *)         echo "cat" ;;
    esac
}

img_ext() {
    case "$COMPRESSION" in
        gzip|gz)   echo ".gz" ;;
        bzip2|bz2) echo ".bz2" ;;
        lz4)       echo ".lz4" ;;
        zstd)      echo ".zst" ;;
        *)         echo "" ;;
    esac
}

# ─────────────────────────────────────────────────────────────────────────────
# MODE: EXPORT
# ─────────────────────────────────────────────────────────────────────────────
do_export() {
    [ -n "$IMAGE_PATH" ] || err "Image path (-o) required for export"

    _dest="${IMAGE_PATH}$(img_ext)"
    _parent=$(dirname "$_dest")
    [ -d "$_parent" ] || err "Output directory does not exist: $_parent"
    [ -f "$_dest"   ] && warn "Overwriting existing image: $_dest"

    do_unmount
    log "Exporting $TARGET → $_dest ..."

    _fs=$(detect_fs)
    log "Detected filesystem: $_fs"
    _pc=$(resolve_partclone "$_fs")
    command -v "$_pc" >/dev/null 2>&1 || { warn "$_pc not found, falling back to partclone.dd"; _pc="partclone.dd"; }

    _comp=$(compress_cmd)
    if [ "$_comp" = "cat" ]; then
        run "$_pc -d -c -s '$TARGET' $EXTRA_OPTS -o '$_dest'"
    else
        run "$_pc -d -c -s '$TARGET' $EXTRA_OPTS | $_comp > '$_dest'"
    fi

    log "Export complete: $_dest"
    step_delay

    if [ "$VERIFY" = "1" ]; then
        log "Verifying image ..."
        if [ "$_comp" = "cat" ]; then
            run "partclone.chkimg -d -s '$_dest'"
        else
            _dcomp=$(decompress_cmd)
            run "$_dcomp '$_dest' | partclone.chkimg -d -s -"
        fi
        log "Verification complete."
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# MODE: IMPORT (restore)
# ─────────────────────────────────────────────────────────────────────────────
do_import() {
    [ -n "$IMAGE_PATH" ] || err "Image path (-o) required for import"
    [ -f "$IMAGE_PATH" ] || [ "$DRY_RUN" = "1" ] || err "Image file not found: $IMAGE_PATH"

    do_unmount
    log "Restoring $IMAGE_PATH → $TARGET ..."

    _dcomp=$(decompress_cmd)
    if [ "$_dcomp" = "cat" ]; then
        run "partclone.restore -d -s '$IMAGE_PATH' $EXTRA_OPTS -o '$TARGET'"
    else
        run "$_dcomp '$IMAGE_PATH' | partclone.restore -d -s - $EXTRA_OPTS -o '$TARGET'"
    fi

    log "Restore complete."
    step_delay

    if [ "$VERIFY" = "1" ]; then
        log "Verifying restored partition ..."
        if [ "$_dcomp" = "cat" ]; then
            run "partclone.chkimg -d -s '$IMAGE_PATH'"
        else
            run "$_dcomp '$IMAGE_PATH' | partclone.chkimg -d -s -"
        fi
        log "Verification complete."
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# MODE: NETWORK SEND
# ─────────────────────────────────────────────────────────────────────────────
do_net_send() {
    [ -n "$NET_PORT" ] || err "Port (-P) required for network send"

    _fs=$(detect_fs)
    log "Detected filesystem: $_fs"
    _pc=$(resolve_partclone "$_fs")
    command -v "$_pc" >/dev/null 2>&1 || { warn "$_pc not found, falling back to partclone.dd"; _pc="partclone.dd"; }

    _comp=$(compress_cmd)

    do_unmount
    log "Sending $TARGET over network (port $NET_PORT) ..."

    if [ "$MULTICAST" = "1" ]; then
        # Multicast send via udp-sender (DRBL/clonezilla style) if available
        if command -v udp-sender >/dev/null 2>&1; then
            if [ "$_comp" = "cat" ]; then
                run "$_pc -d -c -s '$TARGET' $EXTRA_OPTS | udp-sender --mcast-rdv-addr ${NET_HOST:-239.0.0.1} --mcast-all-addr ${NET_HOST:-239.0.0.1} --portbase '$NET_PORT'"
            else
                run "$_pc -d -c -s '$TARGET' $EXTRA_OPTS | $(_comp) | udp-sender --mcast-rdv-addr ${NET_HOST:-239.0.0.1} --mcast-all-addr ${NET_HOST:-239.0.0.1} --portbase '$NET_PORT'"
            fi
        else
            err "udp-sender not found; multicast not available"
        fi
    else
        # Unicast via netcat (nc)
        command -v nc >/dev/null 2>&1 || err "nc (netcat) not found"
        if [ "$_comp" = "cat" ]; then
            run "$_pc -d -c -s '$TARGET' $EXTRA_OPTS | nc -l -p '$NET_PORT'"
        else
            run "$_pc -d -c -s '$TARGET' $EXTRA_OPTS | $(_comp) | nc -l -p '$NET_PORT'"
        fi
    fi

    log "Network send complete."
}

# ─────────────────────────────────────────────────────────────────────────────
# MODE: NETWORK RECEIVE
# ─────────────────────────────────────────────────────────────────────────────
do_net_recv() {
    [ -n "$NET_HOST" ] || err "Source host IP (-H) required for network receive"
    [ -n "$NET_PORT" ] || err "Port (-P) required for network receive"

    do_unmount
    log "Receiving from $NET_HOST:$NET_PORT → $TARGET ..."

    _dcomp=$(decompress_cmd)
    command -v nc >/dev/null 2>&1 || err "nc (netcat) not found"

    if [ "$MULTICAST" = "1" ] && command -v udp-receiver >/dev/null 2>&1; then
        if [ "$_dcomp" = "cat" ]; then
            run "udp-receiver --mcast-rdv-addr '$NET_HOST' --portbase '$NET_PORT' | partclone.restore -d -s - $EXTRA_OPTS -o '$TARGET'"
        else
            run "udp-receiver --mcast-rdv-addr '$NET_HOST' --portbase '$NET_PORT' | $_dcomp | partclone.restore -d -s - $EXTRA_OPTS -o '$TARGET'"
        fi
    else
        if [ "$_dcomp" = "cat" ]; then
            run "nc '$NET_HOST' '$NET_PORT' | partclone.restore -d -s - $EXTRA_OPTS -o '$TARGET'"
        else
            run "nc '$NET_HOST' '$NET_PORT' | $_dcomp | partclone.restore -d -s - $EXTRA_OPTS -o '$TARGET'"
        fi
    fi

    log "Receive complete."
    step_delay

    if [ "$VERIFY" = "1" ]; then
        log "Verifying restored partition info ..."
        run "partclone.info -s '$TARGET' 2>/dev/null || true"
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# MODE: DDRESCUE
# ─────────────────────────────────────────────────────────────────────────────
do_ddrescue() {
    [ -n "$IMAGE_PATH" ] || err "Image path (-o) required for ddrescue"
    command -v ddrescue >/dev/null 2>&1 || err "ddrescue not found"

    _parent=$(dirname "$IMAGE_PATH")
    [ -d "$_parent" ] || err "Output directory does not exist: $_parent"

    _log="${DDRESCUE_LOG:-${IMAGE_PATH}.log}"
    case "$DDRESCUE_RETRIES" in ''|*[!0-9]*) DDRESCUE_RETRIES=3 ;; esac

    do_unmount
    log "ddrescue $TARGET → $IMAGE_PATH (log: $_log, max retries: $DDRESCUE_RETRIES) ..."

    run "ddrescue -d -r '$DDRESCUE_RETRIES' $EXTRA_OPTS '$TARGET' '$IMAGE_PATH' '$_log'"
    log "ddrescue complete."
}

# ─────────────────────────────────────────────────────────────────────────────
# Dispatch
# ─────────────────────────────────────────────────────────────────────────────
case "$MODE" in
    export)   do_export ;;
    import)   do_import ;;
    net_send) do_net_send ;;
    net_recv) do_net_recv ;;
    ddrescue) do_ddrescue ;;
    *) err "Unknown mode: $MODE" ;;
esac

exit 0
