#!/bin/sh

. /usr/lib/libmodcgi.sh

# Override cgi_param to fix suffix-collision bug in the built-in implementation.
# The upstream cgi_param uses  ${QUERY_STRING##*$key=}  (greedy ##), which matches
# any parameter whose NAME ends with $key.  For example,  cgi_param device  would
# return the value of  source_device  (or target_device) because the greedy ##
# strips the longest *device= prefix, landing on the LAST occurrence.
# Fix: prepend '&' to QUERY_STRING and use  ##*&$key=  so only a literal
# '&<key>=' boundary can match, preventing suffix collisions.
cgi_param() {
	local _key="$1"
	local _qs="&${QUERY_STRING}"
	case "$_qs" in
		*"&${_key}="*)
			local _val="${_qs##*&${_key}=}"
			_val="${_val%%&*}"
			httpd -d "$_val"
			;;
	esac
}

CMD_PARTED=''
CMD_PARTPROBE=''
CMD_MKFS_FAT=''
CMD_FSCK_FAT=''
CMD_FATLABEL=''
CMD_MKFS_EXFAT=''
CMD_FSCK_EXFAT=''
CMD_EXFATLABEL=''
CMD_MKE2FS=''
CMD_E2FSCK=''
CMD_RESIZE2FS=''
CMD_TUNE2FS=''
CMD_E2LABEL=''
CMD_DUMPE2FS=''
CMD_BADBLOCKS=''
CMD_GDISK=''
CMD_CGDISK=''
CMD_SGDISK=''
CMD_FIXPARTS=''
CMD_HDPARM=''
CMD_SMARTCTL=''
CMD_LSBLK=''
CMD_BLKID=''
CMD_BLOCKDEV=''
CMD_MKNTFS=''
CMD_NTFSFIX=''
CMD_NTFSINFO=''
CMD_NTFSLABEL=''
CMD_NTFSRESIZE=''
CMD_FATRESIZE=''
CMD_MOUNT=''
CMD_UMOUNT=''
CMD_DDRESCUE=''
CMD_DD=''
CMD_PARTCLONE_DD=''
CMD_PARTCLONE_INFO=''
CMD_PARTCLONE_CHKIMG=''
CMD_PARTITION_IMAGE=''
CMD_PARTITION_MIGRATION=''

# Streaming-mode globals (set by action_start_job; empty = non-streaming)
STREAM_LOG=''
STREAM_DONE=''
EXEC_OUT=''
EXEC_RC=0

BACKEND_LOG_FILE='/tmp/disk-mgmt-backend.log'
DRY_RUN='0'

# Capture all CGI stderr (fd2) to backend log.
exec 2>>"$BACKEND_LOG_FILE"

backend_log() {
	_ts=$(date '+%Y-%m-%d %H:%M:%S' 2>/dev/null)
	printf '[%s] %s\n' "${_ts:-unknown-time}" "$1" >> "$BACKEND_LOG_FILE"
}

dry_run_enabled() {
	[ "$DRY_RUN" = "1" ]
}

preview_or_default() {
	_preview=$(cgi_param command_preview)
	if [ -n "$_preview" ]; then
		printf '%s' "$_preview"
	else
		printf '%s' "$1"
	fi
}

emit_dry_run_result() {
	_label="$1"
	_preview=$(preview_or_default "$2")
	backend_log "DRY-RUN action=${ACTION:-unknown} preview=$_preview"
	emit_cmd_result true 0 "Dry-run: $_label skipped" "[dry-run]\n$_preview"
}

json_escape() {
	# Use awk for robust JSON string escaping.  Handles all control
	# characters (0x00-0x1f) including those BusyBox sed may not
	# reliably escape: newlines, carriage-returns, tabs, etc.
	printf '%s' "$1" | awk '
	BEGIN {
		ORS = ""
		for (_i = 0; _i < 32; _i++)
			_ctrl[sprintf("%c", _i)] = sprintf("\\u%04x", _i)
	}
	NR > 1 { printf "\\n" }
	{
		_n = length($0)
		for (_i = 1; _i <= _n; _i++) {
			_c = substr($0, _i, 1)
			if      (_c == "\\") printf "\\\\"
			else if (_c == "\"") printf "\\\""
			else if (_c == "\r") printf "\\r"
			else if (_c == "\t") printf "\\t"
			else if (_c in _ctrl) printf "%s", _ctrl[_c]
			else printf "%s", _c
		}
	}
	'
}

safe_uint() {
	case "$1" in
		''|*[!0-9]*) echo 0 ;;
		*) echo "$1" ;;
	esac
}

safe_bytes_uint() {
	_v=${1%[bB]}
	safe_uint "$_v"
}

# fat_fix_total_sectors <partition>
# Patches FAT32 BPB total_sectors_32 (offset 32, 4 bytes LE) and its backup
# when the BPB value exceeds the actual partition size. fatresize refuses with
# "The file system is bigger than its volume!" in that case.
# Outputs a description of what was done (empty if no fix needed).
fat_fix_total_sectors() {
	local _p="$1"
	local _psec512 _dev _bps _pfat_sec _bpb_sec _b0 _b1 _b2 _b3 _hex _bbsec
	# Partition size in 512-byte sectors via blockdev; fallback to sysfs
	_psec512=$(blockdev --getsz "$_p" 2>/dev/null)
	if [ -z "$_psec512" ] || [ "$_psec512" -le 0 ] 2>/dev/null; then
		_dev=$(basename "$_p")
		_psec512=$(cat /sys/class/block/"$_dev"/size 2>/dev/null)
	fi
	[ -z "$_psec512" ] || [ "$_psec512" -le 0 ] 2>/dev/null && return

	# bytes_per_sector from BPB offset 11 (2 bytes LE).
	# hexdump -v -e '/1 " %u"' prints each byte as decimal — BusyBox-portable.
	_bps=$(dd if="$_p" bs=1 skip=11 count=2 2>/dev/null |
		hexdump -v -e '/1 " %u"' 2>/dev/null |
		awk '{print ($1+0) + ($2+0)*256}')
	( [ -z "$_bps" ] || [ "$_bps" -le 0 ] ) 2>/dev/null && _bps=512

	# Partition size in FAT sectors
	_pfat_sec=$(awk -v p="$_psec512" -v b="$_bps" 'BEGIN { printf "%.0f", p * 512 / b }')

	# total_sectors_32 from BPB offset 32 (4 bytes LE)
	_bpb_sec=$(dd if="$_p" bs=1 skip=32 count=4 2>/dev/null |
		hexdump -v -e '/1 " %u"' 2>/dev/null |
		awk '{print ($1+0) + ($2+0)*256 + ($3+0)*65536 + ($4+0)*16777216}')
	[ -z "$_bpb_sec" ] && return

	if [ "$_bpb_sec" -gt "$_pfat_sec" ] 2>/dev/null; then
		# Build little-endian 4-byte representation using octal printf (POSIX / BusyBox-safe).
		_b0=$(( _pfat_sec        & 0xff ))
		_b1=$(((_pfat_sec >>  8) & 0xff ))
		_b2=$(((_pfat_sec >> 16) & 0xff ))
		_b3=$(((_pfat_sec >> 24) & 0xff ))
		_hex=$(printf "\\$(printf '%03o' "$_b0")\\$(printf '%03o' "$_b1")\\$(printf '%03o' "$_b2")\\$(printf '%03o' "$_b3")")
		# Patch main boot sector at offset 32
		printf '%s' "$_hex" | dd of="$_p" bs=1 seek=32 count=4 conv=notrunc 2>/dev/null
		# Locate backup boot sector: BPB offset 50 (2 bytes LE) × bytes_per_sector
		_bbsec=$(dd if="$_p" bs=1 skip=50 count=2 2>/dev/null |
			hexdump -v -e '/1 " %u"' 2>/dev/null |
			awk '{print ($1+0) + ($2+0)*256}')
		if [ -n "$_bbsec" ] && [ "$_bbsec" -gt 0 ] 2>/dev/null; then
			printf '%s' "$_hex" | dd of="$_p" bs=1 seek=$(( _bbsec * _bps + 32 )) count=4 conv=notrunc 2>/dev/null
		fi
		echo "BPB total_sectors_32 patched: $_bpb_sec -> $_pfat_sec (partition $_psec512 x 512 / $_bps)"
	fi
}

# fat_fix_hidden_sectors <partition>
# Patches FAT BPB hidden_sectors (offset 28, 4 bytes LE) when its value does
# NOT match the actual partition start sector.  fatresize uses libparted which
# identifies the partition entry by looking up hidden_sectors in the partition
# table; a stale value (e.g. from a cloned partition whose BPB was not updated)
# causes libparted to find the WRONG partition entry and fatresize then fails
# with "Unable to satisfy all constraints on the partition".
# Must be called BEFORE fatresize.  Outputs a message if patched (empty if OK).
fat_fix_hidden_sectors() {
	local _p="$1"
	local _dev _parent _sys_start _actual _cur _b0 _b1 _b2 _b3 _hex
	_dev=$(basename "$_p")
	# Strip trailing partition digits to get parent device (e.g. sdc2 → sdc, nvme0n1p2 → nvme0n1)
	_parent=$(printf '%s' "$_dev" | sed 's/p\?[0-9]\+$//')
	_sys_start="/sys/class/block/${_parent}/${_dev}/start"
	[ -f "$_sys_start" ] || return 0
	_actual=$(tr -cd '0-9' < "$_sys_start")
	[ -n "$_actual" ] || return 0
	[ "$_actual" -gt 0 ] 2>/dev/null || return 0
	# Read current hidden_sectors at BPB offset 28 (4 bytes LE)
	_cur=$(dd if="$_p" bs=1 skip=28 count=4 2>/dev/null |
		hexdump -v -e '/1 " %u"' 2>/dev/null |
		awk '{print ($1+0) + ($2+0)*256 + ($3+0)*65536 + ($4+0)*16777216}')
	[ -z "$_cur" ] && return 0
	if [ "$_cur" -ne "$_actual" ] 2>/dev/null; then
		_b0=$(( _actual        & 0xff ))
		_b1=$(((_actual >>  8) & 0xff ))
		_b2=$(((_actual >> 16) & 0xff ))
		_b3=$(((_actual >> 24) & 0xff ))
		_hex=$(printf "\\$(printf '%03o' "$_b0")\\$(printf '%03o' "$_b1")\\$(printf '%03o' "$_b2")\\$(printf '%03o' "$_b3")")
		printf '%s' "$_hex" | dd of="$_p" bs=1 seek=28 count=4 conv=notrunc 2>/dev/null
		echo "     ⚠️  FAT BPB patched: hidden_sectors ${_cur} → ${_actual} (libparted partition-lookup fix)"
	fi
}

normalize_mount_fs_type() {
	case "$1" in
		fat|fat12|fat16|fat32|vfat) echo "vfat" ;;
		*) echo "$1" ;;
	esac
}

human_bytes_sh() {
	_b=$(safe_uint "$1")
	awk -v b="$_b" 'BEGIN {
		u[0]="B"; u[1]="KiB"; u[2]="MiB"; u[3]="GiB"; u[4]="TiB";
		i=0;
		v=b+0;
		while (v >= 1024 && i < 4) { v = v / 1024; i++; }
		if (i == 0) {
			printf "%.0f %s", v, u[i];
		} else {
			printf "%.2f %s", v, u[i];
		}
	}'
}

find_cmd() {
	for _cmd in "$@"; do
		_cmd_path=$(command -v "$_cmd" 2>/dev/null)
		if [ -n "$_cmd_path" ]; then
			echo "$_cmd_path"
			return 0
		fi
		# Also search sbin directories that may not be in CGI PATH
		for _dir in /mod/usr/sbin /mod/external/usr/sbin /usr/sbin /sbin; do
			if [ -x "$_dir/$_cmd" ]; then
				echo "$_dir/$_cmd"
				return 0
			fi
		done
	done
	return 1
}

CMD_PARTED=$(find_cmd parted)
CMD_PARTPROBE=$(find_cmd partprobe)
CMD_MKFS_FAT=$(find_cmd mkfs.fat)
CMD_FSCK_FAT=$(find_cmd fsck.fat)
CMD_FATLABEL=$(find_cmd fatlabel)
CMD_MKFS_EXFAT=$(find_cmd mkfs.exfat-ng mkfs.exfat mkexfatfs)
CMD_FSCK_EXFAT=$(find_cmd fsck.exfat-ng fsck.exfat exfatfsck)
CMD_EXFATLABEL=$(find_cmd exfatlabel-ng exfatlabel tune.exfat-ng tune.exfat)
CMD_MKE2FS=$(find_cmd mke2fs-ng mke2fs)
CMD_E2FSCK=$(find_cmd e2fsck-ng e2fsck)
CMD_RESIZE2FS=$(find_cmd resize2fs-ng resize2fs)
CMD_TUNE2FS=$(find_cmd tune2fs-ng tune2fs)
CMD_E2LABEL=$(find_cmd e2label-ng e2label)
CMD_DUMPE2FS=$(find_cmd dumpe2fs-ng dumpe2fs)
CMD_BADBLOCKS=$(find_cmd badblocks-ng badblocks)
CMD_GDISK=$(find_cmd gdisk)
CMD_CGDISK=$(find_cmd cgdisk)
CMD_SGDISK=$(find_cmd sgdisk)
CMD_FIXPARTS=$(find_cmd fixparts)
CMD_HDPARM=$(find_cmd hdparm)
CMD_SMARTCTL=$(find_cmd smartctl)
CMD_LSBLK=$(find_cmd lsblk)
CMD_BLKID=$(find_cmd blkid-util-linux blkid-ng blkid)
CMD_BLOCKDEV=$(find_cmd blockdev-ng blockdev-util-linux blockdev)
CMD_MKNTFS=$(find_cmd mkntfs)
CMD_NTFSFIX=$(find_cmd ntfsfix)
CMD_NTFSINFO=$(find_cmd ntfsinfo)
CMD_NTFSLABEL=$(find_cmd ntfslabel)
CMD_NTFSRESIZE=$(find_cmd ntfsresize)
CMD_FATRESIZE=$(find_cmd fatresize)
CMD_MOUNT=$(find_cmd mount)
CMD_UMOUNT=$(find_cmd umount)
CMD_DDRESCUE=$(find_cmd ddrescue)
CMD_DD=$(find_cmd dd)
CMD_PARTCLONE_DD=$(find_cmd partclone.dd)
CMD_PARTCLONE_INFO=$(find_cmd partclone.info)
CMD_PARTCLONE_CHKIMG=$(find_cmd partclone.chkimg)
CMD_PARTITION_MIGRATION=$(find_cmd partition_migration.sh)
CMD_PARTITION_IMAGE=$(find_cmd partition_image.sh)

run_tune2fs() {
	[ -n "$CMD_TUNE2FS" ] || return 127
	case "$CMD_TUNE2FS" in
		*tune2fs-ng*)
			"$CMD_TUNE2FS" "$@"
			return
			;;
	esac
	"$CMD_TUNE2FS" "$@"
}

detect_partition_fs_type() {
	_partition="$1"
	_fs=''
	if [ -n "$CMD_BLKID" ]; then
		_fs=$($CMD_BLKID -o value -s TYPE "$_partition" 2>/dev/null | head -n 1)
	fi
	if [ -z "$_fs" ] && [ -n "$CMD_LSBLK" ]; then
		_fs=$($CMD_LSBLK -ln -o FSTYPE "$_partition" 2>/dev/null | head -n 1)
	fi
	printf '%s' "$_fs" | tr '[:upper:]' '[:lower:]'
}

partclone_bin_for_fs() {
	_fs=$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')
	case "$_fs" in
		ext2|ext3|ext4|ext4dev) find_cmd partclone.ext4 partclone.ext3 partclone.ext2 partclone.extfs ;;
		fat|fat12|fat16|fat32|vfat) find_cmd partclone.vfat partclone.fat ;;
		exfat) find_cmd partclone.exfat ;;
		ntfs) find_cmd partclone.ntfs ;;
		xfs) find_cmd partclone.xfs ;;
		btrfs) find_cmd partclone.btrfs ;;
		f2fs) find_cmd partclone.f2fs ;;
		minix|minix3) find_cmd partclone.minix ;;
		hfs|hfsplus|hfsp) find_cmd partclone.hfsplus partclone.hfsp ;;
		apfs) find_cmd partclone.apfs ;;
		*) return 1 ;;
	esac
}

clone_uuid_regen_cmd() {
	_partition="$1"
	_fs=$(printf '%s' "$2" | tr '[:upper:]' '[:lower:]')
	case "$_fs" in
		ext2|ext3|ext4|ext4dev)
			if [ -n "$CMD_TUNE2FS" ]; then
				printf '%s\n' "run_tune2fs -U random \"$_partition\""
				return 0
			fi
			return 1
			;;
		ntfs)
			if [ -n "$CMD_NTFSLABEL" ]; then
				printf '%s\n' "$CMD_NTFSLABEL --new-serial \"$_partition\""
				return 0
			fi
			return 1
			;;
		*)
			return 1
			;;
	esac
}

# Best-effort filesystem usage probe for unmounted partitions when lsblk does
# not provide FSSIZE/FSUSED/FSAVAIL. Prints: "size_bytes used_bytes avail_bytes".
get_unmounted_fs_usage() {
	_partition="$1"
	_fstype="$2"
	_mountpoint="$3"

	# Prefer lsblk/df values for mounted filesystems.
	[ -z "$_mountpoint" ] || return 1

	case "$_fstype" in
		ext2|ext3|ext4)
			[ -n "$CMD_TUNE2FS" ] || return 1
			_t2_out=$(run_tune2fs -l "$_partition" 2>/dev/null) || return 1
			printf '%s\n' "$_t2_out" | awk -F: '
				/^[[:space:]]*Block count[[:space:]]*:/ { bc=$2 }
				/^[[:space:]]*Free blocks[[:space:]]*:/ { fb=$2 }
				/^[[:space:]]*Reserved block count[[:space:]]*:/ { rb=$2 }
				/^[[:space:]]*Block size[[:space:]]*:/ { bs=$2 }
				END {
					gsub(/[^0-9]/, "", bc)
					gsub(/[^0-9]/, "", fb)
					gsub(/[^0-9]/, "", rb)
					gsub(/[^0-9]/, "", bs)
					if (bc == "" || bs == "") exit 1
					if (fb == "") fb = 0
					if (rb == "") rb = 0
					total = bc * bs
					freeb = fb * bs
					resv = rb * bs
					avail = freeb - resv
					if (avail < 0) avail = 0
					used = total - freeb
					if (used < 0) used = 0
					printf "%.0f %.0f %.0f", total, used, avail
				}
			' || return 1
			return 0
			;;
		ntfs)
			[ -n "$CMD_NTFSINFO" ] || return 1
			_ntfs_out=$($CMD_NTFSINFO -m "$_partition" 2>/dev/null) || return 1
			printf '%s\n' "$_ntfs_out" | awk -F: '
				/^[[:space:]]*Cluster Size[[:space:]]*:/ { cs=$2 }
				/^[[:space:]]*Volume Size in Clusters[[:space:]]*:/ { vc=$2 }
				/^[[:space:]]*Free Clusters[[:space:]]*:/ { fc=$2 }
				END {
					gsub(/[^0-9]/, "", cs)
					gsub(/[^0-9]/, "", vc)
					gsub(/[^0-9]/, "", fc)
					if (cs == "" || vc == "") exit 1
					if (fc == "") fc = 0
					total = vc * cs
					avail = fc * cs
					if (avail < 0) avail = 0
					if (avail > total) avail = total
					used = total - avail
					printf "%.0f %.0f %.0f", total, used, avail
				}
			' || return 1
			return 0
			;;
		fat|fat12|fat16|fat32|vfat)
			[ -n "$CMD_FSCK_FAT" ] || return 1
			_fat_out=$($CMD_FSCK_FAT -n -v "$_partition" 2>/dev/null)
			printf '%s\n' "$_fat_out" | awk '
				BEGIN { bpc=0; usedc=-1; totalc=-1 }
				/bytes per cluster/ {
					if (match($0, /[0-9]+/)) bpc = substr($0, RSTART, RLENGTH) + 0
				}
				{
					if (match($0, /([0-9]+)[[:space:]]*\/[[:space:]]*([0-9]+)[[:space:]]+clusters/)) {
						t = substr($0, RSTART, RLENGTH)
						gsub(/[^0-9\/]/, "", t)
						split(t, a, "/")
						if (a[1] ~ /^[0-9]+$/) usedc = a[1] + 0
						if (a[2] ~ /^[0-9]+$/) totalc = a[2] + 0
					}
				}
				END {
					if (bpc <= 0 || usedc < 0 || totalc < 0) exit 1
					if (usedc > totalc) usedc = totalc
					total = totalc * bpc
					used = usedc * bpc
					avail = total - used
					if (avail < 0) avail = 0
					printf "%.0f %.0f %.0f", total, used, avail
				}
			' || return 1
			return 0
			;;
	esac

	return 1
}

run_exfat_label() {
	_partition="$1"
	_label="$2"

	[ -n "$CMD_EXFATLABEL" ] || return 127

	case "$(basename "$CMD_EXFATLABEL")" in
		tune.exfat|tune.exfat-ng)
			_out=$($CMD_EXFATLABEL -L "$_label" "$_partition" 2>&1)
			_rc=$?
			if [ "$_rc" -ne 0 ]; then
				_out=$($CMD_EXFATLABEL -l "$_label" "$_partition" 2>&1)
				_rc=$?
			fi
			;;
		*)
			_out=$($CMD_EXFATLABEL "$_partition" "$_label" 2>&1)
			_rc=$?
			;;
	esac

	printf '%s' "$_out"
	return "$_rc"
}

is_valid_device() {
	case "$1" in
		/dev/*)
			[ -b "$1" ] && return 0
			return 1
			;;
		*)
			return 1
			;;
	esac
}

is_valid_partnum() {
	case "$1" in
		''|*[!0-9]*) return 1 ;;
		*) return 0 ;;
	esac
}

is_valid_sector() {
	case "$1" in
		''|*[!0-9%]*) return 1 ;;
		*) return 0 ;;
	esac
}

is_valid_label() {
	[ -n "$1" ] || return 1
	printf '%s' "$1" | grep -Eq '^[A-Za-z0-9._ -]+$'
}

is_valid_flag_name() {
	case "$1" in
		''|*[!a-zA-Z0-9_-]*) return 1 ;;
		*) return 0 ;;
	esac
}

is_valid_mountpoint() {
	case "$1" in
		/*)
			printf '%s' "$1" | grep -Eq '^/[A-Za-z0-9._/ -]+$'
			return $?
			;;
		*)
			return 1
			;;
	esac
}

is_disk_listed_in_proc() {
	_dev="$1"
	_base=$(basename "$_dev" 2>/dev/null)
	[ -n "$_base" ] || return 1
	[ -r /proc/partitions ] || return 0
	awk -v n="$_base" '$4 == n { found=1; exit } END { exit found ? 0 : 1 }' /proc/partitions
}

is_parted_scan_candidate() {
	_dev="$1"
	_base=$(basename "$_dev" 2>/dev/null)
	[ -n "$_base" ] || return 1
	case "$_base" in
		loop*|ram*|fd*|sr*|mtd*|mtdblock*|dm-*)
			return 1
			;;
	esac
	is_disk_listed_in_proc "$_dev"
}

is_valid_extra_opts() {
	[ -z "$1" ] && return 0
	printf '%s' "$1" | grep -Eq '^[A-Za-z0-9._/:=,+ -]+$'
}

require_ack() {
	dry_run_enabled && return 0
	_ack=$(cgi_param ack)
	[ "$_ack" = "YES_I_UNDERSTAND" ]
}

emit_json_error() {
	if [ -n "$STREAM_LOG" ]; then
		printf '\n── Error: %s ──\n' "$1" >> "$STREAM_LOG"
		printf 'false\n1\n%s\n\n' "$1" > "$STREAM_DONE"
		return 0
	fi
	_msg=$(json_escape "$1")
	echo "{\"success\": false, \"message\": \"$_msg\"}"
}

emit_cmd_result() {
	_success="$1"
	_rc="$2"
	_msg="$3"
	_detail="$4"
	if [ -n "$STREAM_LOG" ]; then
		printf '%s\n%s\n%s\n' "$_success" "$_rc" "$_msg" > "$STREAM_DONE"
		return 0
	fi
	_msg_json=$(json_escape "$_msg")
	_out_json=$(json_escape "$_detail")
	echo "{\"success\": $_success, \"rc\": $_rc, \"message\": \"$_msg_json\", \"output\": \"$_out_json\"}"
}

emit_cmd_result_with_target() {
	_success="$1"
	_rc="$2"
	_msg="$3"
	_detail="$4"
	if [ -n "$STREAM_LOG" ]; then
		_ecwt_extras="\"target_partnum\": \"$(json_escape "$5")\", \"target_partition\": \"$(json_escape "$6")\", \"target_device\": \"$(json_escape "$7")\", \"target_start_sector\": \"$(json_escape "$8")\", \"target_end_sector\": \"$(json_escape "$9")\""
		printf '%s\n%s\n%s\n%s\n' "$_success" "$_rc" "$_msg" "$_ecwt_extras" > "$STREAM_DONE"
		return 0
	fi
	_msg_json=$(json_escape "$_msg")
	_out_json=$(json_escape "$_detail")
	_target_partnum=$(json_escape "$5")
	_target_partition=$(json_escape "$6")
	_target_device=$(json_escape "$7")
	_target_start_sector=$(json_escape "$8")
	_target_end_sector=$(json_escape "$9")
	echo "{\"success\": $_success, \"rc\": $_rc, \"message\": \"$_msg_json\", \"output\": \"$_out_json\", \"target_partnum\": \"$_target_partnum\", \"target_partition\": \"$_target_partition\", \"target_device\": \"$_target_device\", \"target_start_sector\": \"$_target_start_sector\", \"target_end_sector\": \"$_target_end_sector\"}"
}

# exec_cmd: run command with direct streaming output to STREAM_LOG (no capture).
# Usage: exec_cmd LABEL DISPLAY_CMD actual_cmd [args...]
# In streaming mode: output goes directly to STREAM_LOG in real time; EXEC_OUT is empty.
# In normal mode: output captured to EXEC_OUT (like a normal subshell).
exec_cmd() {
	_ec_label="$1"; _ec_disp="$2"; shift 2
	if [ -n "$STREAM_LOG" ]; then
		printf '\n════════════════════════════════════════════════════════════════════════════\n\033[1;36m▶ %s\033[0m\n\033[36m── cmd:\033[0m \033[1;33m%s\033[0m\n' "$_ec_label" "$_ec_disp" >> "$STREAM_LOG"
		"$@" >> "$STREAM_LOG" 2>&1
		EXEC_RC=$?
		if [ "$EXEC_RC" -eq 0 ]; then
			printf '\033[1;32m── exit: %d (OK)\033[0m ────────────────────────────────────────────────────────────\n' "$EXEC_RC" >> "$STREAM_LOG"
		else
			printf '\033[1;31m── exit: %d (FAILED)\033[0m ────────────────────────────────────────────────────────\n' "$EXEC_RC" >> "$STREAM_LOG"
		fi
		EXEC_OUT=''
	else
		EXEC_OUT=$("$@" 2>&1)
		EXEC_RC=$?
	fi
	return $EXEC_RC
}

# exec_cmd_c: like exec_cmd but ALWAYS captures output (EXEC_OUT is populated).
# In streaming mode: output is also appended to STREAM_LOG after completion.
# Use for short commands where output may be needed for branching/retry logic.
exec_cmd_c() {
	_ec_label="$1"; _ec_disp="$2"; shift 2
	if [ -n "$STREAM_LOG" ]; then
		printf '\n════════════════════════════════════════════════════════════════════════════\n\033[1;36m▶ %s\033[0m\n\033[36m── cmd:\033[0m \033[1;33m%s\033[0m\n' "$_ec_label" "$_ec_disp" >> "$STREAM_LOG"
	fi
	EXEC_OUT=$("$@" 2>&1)
	EXEC_RC=$?
	if [ -n "$STREAM_LOG" ] && [ -n "$EXEC_OUT" ]; then
		printf '%s\n' "$EXEC_OUT" >> "$STREAM_LOG"
	fi
	if [ -n "$STREAM_LOG" ]; then
		if [ "$EXEC_RC" -eq 0 ]; then
			printf '\033[1;32m── exit: %d (OK)\033[0m ────────────────────────────────────────\n' "$EXEC_RC" >> "$STREAM_LOG"
		else
			printf '\033[1;31m── exit: %d (FAILED)\033[0m ────────────────────────────────────────\n' "$EXEC_RC" >> "$STREAM_LOG"
		fi
	fi
	return $EXEC_RC
}

partition_path() {
	_device="$1"
	_partnum="$2"
	case "$_device" in
		*[0-9]) _guess="${_device}p${_partnum}" ;;
		*) _guess="${_device}${_partnum}" ;;
	esac

	if [ -b "$_guess" ]; then
		echo "$_guess"
		return
	fi

	if [ -n "$CMD_LSBLK" ]; then
		_p=$($CMD_LSBLK -ln -o PATH,PARTN "$_device" 2>/dev/null | awk -v n="$_partnum" '$2 == n { print $1; exit }')
		if [ -n "$_p" ]; then
			echo "$_p"
			return
		fi
	fi

	echo "$_guess"
}

partition_number_by_range() {
    _device="$1"
    _start_sector="$2"
    _end_sector="$3"

    [ -n "$CMD_PARTED" ] || return 1
    $CMD_PARTED -s -m "$_device" unit s print 2>/dev/null | awk -F: -v s="$_start_sector" -v e="$_end_sector" '
        $1 ~ /^[0-9]+$/ {
            gsub(/s$/, "", $2)
            gsub(/s$/, "", $3)
            if ($2 == s && $3 == e) {
                print $1
                exit
            }
        }
    '
}

run_partprobe() {
	if [ -n "$CMD_PARTPROBE" ]; then
		$CMD_PARTPROBE "$1" >/tmp/disk-mgmt-partprobe.log 2>&1
		_rp_rc=$?
		if [ "$_rp_rc" -eq 139 ] && [ -n "$1" ]; then
			$CMD_PARTPROBE >>/tmp/disk-mgmt-partprobe.log 2>&1
			_rp_rc=$?
		fi
		if [ "$_rp_rc" -ne 0 ]; then
			if [ -n "$CMD_BLOCKDEV" ]; then
				"$CMD_BLOCKDEV" --rereadpt "$1" >>/tmp/disk-mgmt-partprobe.log 2>&1
			fi
		fi
	fi
}

wait_for_partition_path() {
	_device="$1"
	_partnum="$2"
	_max_wait="$3"
	[ -n "$_max_wait" ] || _max_wait=5

	_i=0
	while [ "$_i" -lt "$_max_wait" ]; do
		_p=$(partition_path "$_device" "$_partnum")
		if [ -b "$_p" ]; then
			printf '%s' "$_p"
			return 0
		fi
		sleep 1
		_i=$((_i + 1))
	done

	return 1
}

action_analyze_tools() {
	resolve_tools

	if echo "$CMD_MKE2FS $CMD_E2FSCK $CMD_RESIZE2FS" | grep -q -- '-ng'; then
		e2_mode='suffix-ng'
	else
		e2_mode='standard'
	fi

	items=''
	first=1
	add_item() {
		_name="$1"
		_path="$2"
		_role="$3"
		if [ -n "$_path" ]; then
			_avail=true
		else
			_avail=false
		fi
		if [ "$first" -eq 0 ]; then
			items="$items,"
		fi
		first=0
		items="$items{\"name\":\"$(json_escape "$_name")\",\"available\":$_avail,\"path\":\"$(json_escape "$_path")\",\"role\":\"$(json_escape "$_role")\"}"
	}

	add_item "parted" "$CMD_PARTED" "Partition table editor"
	add_item "partprobe" "$CMD_PARTPROBE" "Kernel partition table refresh"
	add_item "mkfs.fat" "$CMD_MKFS_FAT" "Create FAT filesystem"
	add_item "fsck.fat" "$CMD_FSCK_FAT" "Check FAT filesystem"
	add_item "fatlabel" "$CMD_FATLABEL" "Set FAT label"
	add_item "mkfs.exfat" "$CMD_MKFS_EXFAT" "Create exFAT filesystem"
	add_item "fsck.exfat" "$CMD_FSCK_EXFAT" "Check exFAT filesystem"
	add_item "exfatlabel" "$CMD_EXFATLABEL" "Set exFAT label"
	add_item "mke2fs/e2fsprogs" "$CMD_MKE2FS" "Create ext filesystem"
	add_item "e2fsck/e2fsprogs" "$CMD_E2FSCK" "Check ext filesystem"
	add_item "resize2fs/e2fsprogs" "$CMD_RESIZE2FS" "Resize ext filesystem"
	add_item "dumpe2fs/e2fsprogs" "$CMD_DUMPE2FS" "Ext2/3/4 superblock/block group dump"
	add_item "badblocks/e2fsprogs" "$CMD_BADBLOCKS" "Bad block scanner (ext2/3/4)"
	add_item "gdisk" "$CMD_GDISK" "GPT interactive editor"
	add_item "cgdisk" "$CMD_CGDISK" "GPT curses editor"
	add_item "sgdisk" "$CMD_SGDISK" "GPT scriptable editor"
	add_item "fixparts" "$CMD_FIXPARTS" "MBR repair utility"
	add_item "hdparm" "$CMD_HDPARM" "Disk identify and tuning"
	add_item "smartctl" "$CMD_SMARTCTL" "SMART health check"
	add_item "lsblk" "$CMD_LSBLK" "Block device topology"
	add_item "blkid" "$CMD_BLKID" "Filesystem signatures"
	add_item "blockdev" "$CMD_BLOCKDEV" "Low-level block-device ioctls"
	add_item "mkntfs" "$CMD_MKNTFS" "Create NTFS filesystem"
	add_item "ntfsfix" "$CMD_NTFSFIX" "Check and repair NTFS"
	add_item "ntfsinfo" "$CMD_NTFSINFO" "Read NTFS metadata"
	add_item "ntfslabel" "$CMD_NTFSLABEL" "Set NTFS label"
	add_item "ntfsresize" "$CMD_NTFSRESIZE" "Resize NTFS filesystem"
	add_item "fatresize" "$CMD_FATRESIZE" "Resize FAT filesystem"
	add_item "mount" "$CMD_MOUNT" "Mount filesystem"
	add_item "umount" "$CMD_UMOUNT" "Unmount filesystem"
	add_item "dd" "$CMD_DD" "Sector-by-sector copy"
	add_item "partclone.dd" "$CMD_PARTCLONE_DD" "Partclone raw copy engine"
	add_item "partclone.info" "$CMD_PARTCLONE_INFO" "Partclone information utility"
	add_item "partclone.chkimg" "$CMD_PARTCLONE_CHKIMG" "Partclone image verification utility"
	add_item "partition_migration.sh" "$CMD_PARTITION_MIGRATION" "Partition migration/clone script"
	add_item "ddrescue" "$CMD_DDRESCUE" "Safer block clone/copy"

	echo "{\"success\": true, \"e2fsprogs_mode\": \"$e2_mode\", \"tools\": [$items]}"
}

action_list_devices() {
	resolve_tools
	_usb_only=$(cgi_param usb_only)

	if [ -z "$CMD_PARTED" ]; then
		emit_json_error "parted command not available"
		return
	fi

	dev_json=''
	first_dev=1

	for _sys in /sys/block/*; do
		[ -e "$_sys" ] || continue
		_name=$(basename "$_sys")
		case "$_name" in
			loop*|ram*|fd*|sr*|mtd*|dm-*)
				continue
				;;
		esac

		_dev="/dev/$_name"
		[ -b "$_dev" ] || continue
		is_parted_scan_candidate "$_dev" || continue

		if [ "$_usb_only" = "1" ]; then
			_dev_path=$(readlink -f "$_sys/device" 2>/dev/null)
			case "$_dev_path" in
				*usb*) : ;;
				*) continue ;;
			esac
		fi

		_map=$($CMD_PARTED -s -m "$_dev" unit s print free 2>/dev/null)
		[ -n "$_map" ] || continue

		_header=$(printf '%s\n' "$_map" | sed -n '2p')
		[ -n "$_header" ] || continue

		_old_ifs=$IFS
		IFS=':'
		set -- $_header
		IFS=$_old_ifs

		_total_sectors=$(safe_uint "${2%s}")
		_logical_size=$(safe_uint "$4")
		_table_type="$6"
		_model="$7"
		if [ -z "$_model" ] && [ -r "$_sys/device/model" ]; then
			_model=$(cat "$_sys/device/model" 2>/dev/null)
		fi
		_vendor=''
		if [ -r "$_sys/device/vendor" ]; then
			_vendor=$(cat "$_sys/device/vendor" 2>/dev/null)
		fi
		_serial=''
		if [ -r "$_sys/device/serial" ]; then
			_serial=$(cat "$_sys/device/serial" 2>/dev/null)
		fi
		_removable='0'
		if [ -r "$_sys/removable" ]; then
			_removable=$(safe_uint "$(cat "$_sys/removable" 2>/dev/null)")
		fi
		_transport=''
		if [ -n "$CMD_LSBLK" ]; then
			_transport=$($CMD_LSBLK -dn -o TRAN "$_dev" 2>/dev/null | head -n 1)
		fi

		_parts=''
		first_part=1
		_part_lines=$(printf '%s\n' "$_map" | sed -n '3,$p')
		while IFS= read -r _line; do
			[ -n "$_line" ] || continue
			_line=${_line%;}

			_old_ifs=$IFS
			IFS=':'
			set -- $_line
			IFS=$_old_ifs

			_pid="$1"
			_pstart=$(safe_uint "${2%s}")
			_pend=$(safe_uint "${3%s}")
			_psize=$(safe_uint "${4%s}")
			_pfs="$5"
			_pname="$6"
			_pflags="$7"

			if [ "$first_part" -eq 0 ]; then
				_parts="$_parts,"
			fi
			first_part=0

			# Detect free space: older parted uses "free" in field 1; newer parted
			# uses a numeric slot index in field 1 but "free" in field 5 (_pfs).
			if [ "$_pid" = "free" ] || [ "$_pfs" = "free" ]; then
				_parts="$_parts{\"kind\":\"free\",\"start\":$_pstart,\"end\":$_pend,\"size\":$_psize}"
			else
				_pnum=$(safe_uint "$_pid")
				_ppath=$(partition_path "$_dev" "$_pnum")
				# For "loop"-type disks the filesystem sits directly on the
				# raw device; the synthetic partition node (e.g. /dev/sda1)
				# does not exist — fall back to the disk device itself.
				if [ "$_table_type" = "loop" ] && [ ! -b "$_ppath" ]; then
					_ppath="$_dev"
				fi
				_mountpoint=$(awk -v p="$_ppath" '$1 == p { print $2; exit }' /proc/mounts 2>/dev/null)
				_plabel=''
				_p_fs_size_bytes='0'
				_p_fs_used_bytes='0'
				_p_fs_avail_bytes='0'
				_p_used_pct='0'
				if [ -n "$CMD_LSBLK" ]; then
					_plabel=$($CMD_LSBLK -ln -o LABEL "$_ppath" 2>/dev/null | head -n 1)
					_p_fs_size_bytes=$(safe_uint "$($CMD_LSBLK -bn -o FSSIZE "$_ppath" 2>/dev/null | head -n 1)")
					_p_fs_used_bytes=$(safe_uint "$($CMD_LSBLK -bn -o FSUSED "$_ppath" 2>/dev/null | head -n 1)")
					_p_fs_avail_bytes=$(safe_uint "$($CMD_LSBLK -bn -o FSAVAIL "$_ppath" 2>/dev/null | head -n 1)")
				fi
				if [ -z "$_mountpoint" ] && { [ "$_p_fs_size_bytes" -eq 0 ] || { [ "$_p_fs_used_bytes" -eq 0 ] && [ "$_p_fs_avail_bytes" -eq 0 ]; }; }; then
					_fallback_usage=$(get_unmounted_fs_usage "$_ppath" "$_pfs" "$_mountpoint")
					if [ -n "$_fallback_usage" ]; then
						set -- $_fallback_usage
						_p_fs_size_bytes=$(safe_uint "$1")
						_p_fs_used_bytes=$(safe_uint "$2")
						_p_fs_avail_bytes=$(safe_uint "$3")
					fi
				fi
				if [ -z "$_plabel" ] && [ -n "$CMD_BLKID" ]; then
					_plabel=$($CMD_BLKID -o value -s LABEL "$_ppath" 2>/dev/null | head -n 1)
				fi
				# parted may not detect filesystem type (e.g. freshly-created NTFS);
				# fall back to blkid for a reliable reading.
				if [ -z "$_pfs" ] && [ -n "$CMD_BLKID" ]; then
					_pfs=$($CMD_BLKID -o value -s TYPE "$_ppath" 2>/dev/null | head -n 1)
				fi
				if [ "$_p_fs_used_bytes" -gt 0 ]; then
					# used_pct = fs_used / disk_total × 100 (disk-absolute coord, float).
					# JS converts to CSS% within the block by dividing by (p.size / total_sectors).
					# This keeps pixel-width fixed on the map regardless of partition resize.
					_disk_total_bytes=$(awk -v ts="$_total_sectors" -v ls="$_logical_size" 'BEGIN { printf "%.0f", ts * ls }')
					_p_used_pct=$(awk -v u="$_p_fs_used_bytes" -v d="$_disk_total_bytes" \
						'BEGIN { if (d > 0) printf "%.8f", (u * 100) / d; else print 0 }')
				fi
				# Determine partition role (primary/logical/extended) for MBR disks.
				# logical_sector numbers start at 5 for logical partitions on MBR.
				# For primary/extended (1-4), lsblk PARTTYPE may reveal 0x5/0xf (extended).
				_prole='primary'
				if [ "$_table_type" = "msdos" ]; then
					if [ "$_pnum" -ge 5 ]; then
						_prole='logical'
					elif [ -n "$CMD_LSBLK" ]; then
						_ptype_hex=$($CMD_LSBLK -dn -o PARTTYPE "$_ppath" 2>/dev/null | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]')
						case "$_ptype_hex" in
							0x5|0x0f|0xf|0x85) _prole='extended' ;;
						esac
					fi
				fi
				_parts="$_parts{\"kind\":\"partition\",\"number\":$_pnum,\"start\":$_pstart,\"end\":$_pend,\"size\":$_psize,\"path\":\"$(json_escape "$_ppath")\",\"fs\":\"$(json_escape "$_pfs")\",\"name\":\"$(json_escape "$_pname")\",\"flags\":\"$(json_escape "$_pflags")\",\"label\":\"$(json_escape "$_plabel")\",\"mountpoint\":\"$(json_escape "$_mountpoint")\",\"role\":\"$(json_escape "$_prole")\",\"fs_size_bytes\":$_p_fs_size_bytes,\"fs_used_bytes\":$_p_fs_used_bytes,\"fs_avail_bytes\":$_p_fs_avail_bytes,\"used_pct\":$_p_used_pct}"
			fi
		done <<EOF
$_part_lines
EOF

		if [ "$first_dev" -eq 0 ]; then
			dev_json="$dev_json,"
		fi
		first_dev=0
		dev_json="$dev_json{\"name\":\"$(json_escape "$_name")\",\"path\":\"$(json_escape "$_dev")\",\"model\":\"$(json_escape "$_model")\",\"vendor\":\"$(json_escape "$_vendor")\",\"serial\":\"$(json_escape "$_serial")\",\"transport\":\"$(json_escape "$_transport")\",\"removable\":$_removable,\"table\":\"$(json_escape "$_table_type")\",\"logical_sector_size\":$_logical_size,\"total_sectors\":$_total_sectors,\"partitions\":[$_parts]}"
	done

	echo "{\"success\": true, \"devices\": [$dev_json]}"
}

action_create_partition() {
	resolve_tools
	if ! require_ack; then
		emit_json_error "Dangerous operation blocked: type YES_I_UNDERSTAND first"
		return
	fi

	_device=$(cgi_param device)
	_start_sector=$(cgi_param start_sector)
	_end_sector=$(cgi_param end_sector)
	_part_role=$(cgi_param part_role)
	_fs_hint=$(cgi_param fs_hint)
	_part_name=$(cgi_param part_name)
	_part_label=$(cgi_param part_label)
	_mount_point=$(cgi_param mount_point)
	_create_fs=$(cgi_param create_fs)

	[ -n "$CMD_PARTED" ] || { emit_json_error "parted command not available"; return; }
	is_valid_device "$_device" || { emit_json_error "Invalid device"; return; }
	is_valid_sector "$_start_sector" || { emit_json_error "Invalid start sector"; return; }
	is_valid_sector "$_end_sector" || { emit_json_error "Invalid end sector"; return; }

	# Determine if start/end are percentage values; build parted position args accordingly.
	_s_arg="${_start_sector}s"; _e_arg="${_end_sector}s"
	_use_pct=0
	case "$_start_sector" in *%) _s_arg="$_start_sector"; _use_pct=1 ;; esac
	case "$_end_sector" in *%) _e_arg="$_end_sector"; _use_pct=1 ;; esac
	# When using percentages, omit unit s so parted interprets them correctly.
	_unit_arg='unit s'
	[ "$_use_pct" -eq 1 ] && _unit_arg=''

	case "$_part_role" in
		primary|logical|extended|'') : ;;
		*) emit_json_error "Invalid partition role"; return ;;
	esac
	[ -z "$_part_role" ] && _part_role='primary'

	case "$_fs_hint" in
		''|ext2|ext3|ext4|f2fs|fat16|fat32|linux-swap|ntfs|xfs) : ;;
		*) emit_json_error "Invalid fs hint"; return ;;
	esac

	# Numeric comparison only makes sense for pure-integer (non-%) values
	case "$_start_sector$_end_sector" in
		*%*) : ;;
		*) if [ "$_start_sector" -ge "$_end_sector" ]; then
				emit_json_error "Start sector must be lower than end sector"
				return
			fi ;;
	esac

	_dev_base=$(basename "$_device" 2>/dev/null)
	_logical_sector_size='512'
	if [ -n "$_dev_base" ] && [ -r "/sys/class/block/$_dev_base/queue/logical_block_size" ]; then
		_logical_sector_size=$(safe_uint "$(cat "/sys/class/block/$_dev_base/queue/logical_block_size" 2>/dev/null)")
	fi
	[ "$_logical_sector_size" -gt 0 ] || _logical_sector_size='512'
	_min_start_sector=$(( (1048576 + _logical_sector_size - 1) / _logical_sector_size ))
	case "$_start_sector" in
		*%) : ;; # skip numeric check for percentage values
		*) if [ "$_start_sector" -lt "$_min_start_sector" ]; then
				emit_json_error "Start sector too low. Use start sector >= $_min_start_sector to keep metadata/protective area and alignment."
				return
			fi ;;
	esac

	if dry_run_enabled; then
		if [ -n "$_fs_hint" ]; then
			_preview_cmd="parted -s $_device unit s mkpart $_part_role $_fs_hint ${_start_sector}s ${_end_sector}s"
		else
			_preview_cmd="parted -s $_device unit s mkpart $_part_role ${_start_sector}s ${_end_sector}s"
		fi
		if [ -n "$_part_name" ]; then
			_preview_cmd="$_preview_cmd
parted -s $_device name <new_partnum> $_part_name"
		fi
		_preview_cmd="$_preview_cmd
partprobe $_device"
		if [ "$_create_fs" = "1" ] && [ -n "$_fs_hint" ]; then
			case "$_fs_hint" in
				ext2|ext3|ext4) _preview_cmd="$_preview_cmd
mke2fs -F -t $_fs_hint ${_device}<new_partnum>" ;;
				fat16) _preview_cmd="$_preview_cmd
mkfs.fat -F 16 ${_device}<new_partnum>" ;;
				fat32) _preview_cmd="$_preview_cmd
mkfs.fat -F 32 ${_device}<new_partnum>" ;;
				exfat) _preview_cmd="$_preview_cmd
mkfs.exfat ${_device}<new_partnum>" ;;
				ntfs)  : ;; # parted mkpart with ntfs hint already creates the filesystem
			esac
		fi
		emit_dry_run_result "partition creation" "$_preview_cmd"
		return
	fi

	# Snapshot existing partition numbers before creation to identify the new one reliably
	_parts_before=$($CMD_PARTED -s -m "$_device" unit s print 2>/dev/null | awk -F: '/^[0-9]+:/ { print $1 }' | tr '\n' ' ')

	if [ -n "$_fs_hint" ]; then
		exec_cmd_c "Create partition on $_device" \
			"$CMD_PARTED -s $_device $_unit_arg mkpart $_part_role $_fs_hint $_s_arg $_e_arg" \
			"$CMD_PARTED" -s "$_device" $_unit_arg mkpart "$_part_role" "$_fs_hint" "$_s_arg" "$_e_arg"
	else
		exec_cmd_c "Create partition on $_device" \
			"$CMD_PARTED -s $_device $_unit_arg mkpart $_part_role $_s_arg $_e_arg" \
			"$CMD_PARTED" -s "$_device" $_unit_arg mkpart "$_part_role" "$_s_arg" "$_e_arg"
	fi
	_rc=$EXEC_RC; _out="$EXEC_OUT"

	# Determine new partition number by comparing before/after partition lists
	_new_part=''
	if [ "$_rc" -eq 0 ]; then
		_parts_after=$($CMD_PARTED -s -m "$_device" unit s print 2>/dev/null | awk -F: '/^[0-9]+:/ { print $1 }' | tr '\n' ' ')
		for _pnum in $_parts_after; do
			case " $_parts_before " in
				*" $_pnum "*) : ;;
				*) _new_part="$_pnum"; break ;;
			esac
		done
	fi

	if [ "$_rc" -eq 0 ] && [ -n "$_part_name" ]; then
		if ! is_valid_label "$_part_name"; then
			_out="$_out\nWarning: Partition name contains unsupported characters and was skipped"
		else
			if is_valid_partnum "$_new_part"; then
				exec_cmd_c "Set partition name on p$_new_part" \
					"$CMD_PARTED -s $_device name $_new_part $_part_name" \
					"$CMD_PARTED" -s "$_device" name "$_new_part" "$_part_name"
				_out="$_out\n$EXEC_OUT"
				if [ "$EXEC_RC" -ne 0 ]; then
					# msdos labels don't support partition names — treat as non-fatal warning
					case "$EXEC_OUT" in
						*"do not support partition name"*|*"msdos disk"*)
							_out="$_out\nWarning: Partition name skipped (not supported on msdos disk label)" ;;
						*)
							_rc=$EXEC_RC ;;
					esac
				fi
			fi
		fi
	fi

	[ "$_rc" -eq 0 ] && run_partprobe "$_device"

	# Optionally create filesystem on the new partition
	if [ "$_rc" -eq 0 ] && [ "$_create_fs" = "1" ] && [ -n "$_fs_hint" ] && is_valid_partnum "$_new_part"; then
		_new_part_dev=$(partition_path "$_device" "$_new_part")
		# Wait briefly for the kernel to register the new node
		_wait=0
		while [ ! -b "$_new_part_dev" ] && [ "$_wait" -lt 5 ]; do
			sleep 1; _wait=$((_wait+1))
		done
		if [ ! -b "$_new_part_dev" ]; then
			_out="$_out\nWarning: Partition device $_new_part_dev not yet available, skipping mkfs"
		else
			case "$_fs_hint" in
				ext2|ext3|ext4)
					if [ -n "$CMD_MKE2FS" ]; then
						_lbl_opt=''
						if [ -n "$_part_label" ] && is_valid_label "$_part_label"; then
							_lbl_opt="-L $_part_label"
						fi
						# shellcheck disable=SC2086
						exec_cmd_c "mke2fs create $_fs_hint on $_new_part_dev" \
							"$CMD_MKE2FS -v -F -t $_fs_hint ${_lbl_opt:+$_lbl_opt }$_new_part_dev" \
							"$CMD_MKE2FS" -v -F -t "$_fs_hint" ${_lbl_opt:+$_lbl_opt} "$_new_part_dev"
						_out="$_out\n$EXEC_OUT"
						[ "$EXEC_RC" -ne 0 ] && _out="$_out\nWarning: mkfs.$_fs_hint failed (rc=$EXEC_RC)"
					else
						_out="$_out\nWarning: mke2fs not available, skipping mkfs.$_fs_hint"
					fi
					;;
				fat16)
					if [ -n "$CMD_MKFS_FAT" ]; then
						_lbl_opt=''
						if [ -n "$_part_label" ] && is_valid_label "$_part_label"; then
							_lbl_opt="-n $_part_label"
						fi
						# shellcheck disable=SC2086
						exec_cmd_c "mkfs.fat fat16 on $_new_part_dev" \
							"$CMD_MKFS_FAT -v -F 16 ${_lbl_opt}$_new_part_dev" \
							"$CMD_MKFS_FAT" -v -F 16 ${_lbl_opt:+$_lbl_opt} "$_new_part_dev"
						_out="$_out\n$EXEC_OUT"
						[ "$EXEC_RC" -ne 0 ] && _out="$_out\nWarning: mkfs.fat fat16 failed (rc=$EXEC_RC)"
					else
						_out="$_out\nWarning: mkfs.fat not available, skipping mkfs.fat16"
					fi
					;;
				fat32)
					if [ -n "$CMD_MKFS_FAT" ]; then
						_lbl_opt=''
						if [ -n "$_part_label" ] && is_valid_label "$_part_label"; then
							_lbl_opt="-n $_part_label"
						fi
						# shellcheck disable=SC2086
						exec_cmd_c "mkfs.fat fat32 on $_new_part_dev" \
							"$CMD_MKFS_FAT -v -F 32 ${_lbl_opt}$_new_part_dev" \
							"$CMD_MKFS_FAT" -v -F 32 ${_lbl_opt:+$_lbl_opt} "$_new_part_dev"
						_out="$_out\n$EXEC_OUT"
						[ "$EXEC_RC" -ne 0 ] && _out="$_out\nWarning: mkfs.fat fat32 failed (rc=$EXEC_RC)"
					else
						_out="$_out\nWarning: mkfs.fat not available, skipping mkfs.fat32"
					fi
					;;
				exfat)
					if [ -n "$CMD_MKFS_EXFAT" ]; then
						_lbl_opt=''
						if [ -n "$_part_label" ] && is_valid_label "$_part_label"; then
							_lbl_opt="-n $_part_label"
						fi
						# shellcheck disable=SC2086
						exec_cmd_c "mkfs.exfat on $_new_part_dev" \
							"$CMD_MKFS_EXFAT ${_lbl_opt}$_new_part_dev" \
							"$CMD_MKFS_EXFAT" ${_lbl_opt:+$_lbl_opt} "$_new_part_dev"
						_out="$_out\n$EXEC_OUT"
						[ "$EXEC_RC" -ne 0 ] && _out="$_out\nWarning: mkfs.exfat failed (rc=$EXEC_RC)"
					else
						_out="$_out\nWarning: mkfs.exfat not available, skipping mkfs.exfat"
					fi
					;;
				ntfs)
					# parted mkpart with ntfs hint creates a basic NTFS without a volume label.
					# Re-run mkntfs to set the label (-Q = quick format, keeps existing data).
					if [ -n "$CMD_MKNTFS" ] && [ -n "$_part_label" ] && is_valid_label "$_part_label"; then
						exec_cmd_c "mkntfs set label on $_new_part_dev" \
							"$CMD_MKNTFS -Q -f -L $_part_label $_new_part_dev" \
							"$CMD_MKNTFS" -Q -f -L "$_part_label" "$_new_part_dev"
						_out="$_out\n$EXEC_OUT"
						[ "$EXEC_RC" -ne 0 ] && _out="$_out\nWarning: mkntfs failed (rc=$EXEC_RC), NTFS label not set"
					else
						_out="$_out\nNote: NTFS filesystem created by parted mkpart"
					fi
					;;
				*)
					_out="$_out\nWarning: mkfs for '$_fs_hint' not supported in create_partition, skipping"
					;;
			esac
			# Re-probe so kernel and parted detect the new filesystem type
			run_partprobe "$_device"
		fi
	fi

	# Optionally mount the new partition
	if [ "$_rc" -eq 0 ] && [ -n "$_mount_point" ] && [ -n "$_new_part" ] && is_valid_partnum "$_new_part"; then
		_new_part_dev=$(partition_path "$_device" "$_new_part")
		if is_valid_mountpoint "$_mount_point"; then
			mkdir -p "$_mount_point" 2>/dev/null
			if [ -d "$_mount_point" ] && [ -n "$CMD_MOUNT" ]; then
				exec_cmd_c "Mount $_new_part_dev on $_mount_point" \
					"$CMD_MOUNT $_new_part_dev $_mount_point" \
					"$CMD_MOUNT" "$_new_part_dev" "$_mount_point"
				_out="$_out\n$EXEC_OUT"
				[ "$EXEC_RC" -ne 0 ] && _out="$_out\nWarning: mount failed (rc=$EXEC_RC)"
			fi
		fi
	fi

	if [ "$_rc" -eq 0 ]; then
		emit_cmd_result true "$_rc" "Partition created" "$_out"
	else
		emit_cmd_result false "$_rc" "Partition creation failed" "$_out"
	fi
}

action_delete_partition() {
	resolve_tools
	if ! require_ack; then
		emit_json_error "Dangerous operation blocked: type YES_I_UNDERSTAND first"
		return
	fi

	_device=$(cgi_param device)
	_partnum=$(cgi_param partnum)

	[ -n "$CMD_PARTED" ] || { emit_json_error "parted command not available"; return; }
	is_valid_device "$_device" || { emit_json_error "Invalid device"; return; }
	is_valid_partnum "$_partnum" || { emit_json_error "Invalid partition number"; return; }

	if dry_run_enabled; then
		emit_dry_run_result "partition removal" "parted -s $_device rm $_partnum
partprobe $_device"
		return
	fi

	exec_cmd_c "Delete partition $_partnum on $_device" \
		"$CMD_PARTED -s $_device rm $_partnum" \
		"$CMD_PARTED" -s "$_device" rm "$_partnum"
	_rc=$EXEC_RC; _out="$EXEC_OUT"
	[ "$_rc" -eq 0 ] && run_partprobe "$_device"

	if [ "$_rc" -eq 0 ]; then
		emit_cmd_result true "$_rc" "Partition removed" "$_out"
	else
		emit_cmd_result false "$_rc" "Partition remove failed" "$_out"
	fi
}

action_resize_partition() {
	resolve_tools
	if ! require_ack; then
		emit_json_error "Dangerous operation blocked: type YES_I_UNDERSTAND first"
		return
	fi

	_device=$(cgi_param device)
	_partnum=$(cgi_param partnum)
	_end_sector=$(cgi_param end_sector)
	_resize_fs=$(cgi_param resize_fs)

	[ -n "$CMD_PARTED" ] || { emit_json_error "parted command not available"; return; }
	is_valid_device "$_device" || { emit_json_error "Invalid device"; return; }
	is_valid_partnum "$_partnum" || { emit_json_error "Invalid partition number"; return; }
	is_valid_sector "$_end_sector" || { emit_json_error "Invalid end sector"; return; }

	if dry_run_enabled; then
		_preview_cmd="parted -s $_device unit s resizepart $_partnum ${_end_sector}s
partprobe $_device"
		_preview_cmd="$_preview_cmd
# if shrink confirmation is requested, backend retries with scripted 'Yes'"
		if [ "$_resize_fs" = "yes" ]; then
			_preview_cmd="$_preview_cmd
# filesystem resize requested: backend auto-detects FS and runs ext/ntfs/fat resize tools when available"
		fi
		emit_dry_run_result "partition resize" "$_preview_cmd"
		return
	fi

	exec_cmd_c "Resize partition p$_partnum on $_device" \
		"$CMD_PARTED -s -f $_device unit s resizepart $_partnum ${_end_sector}s" \
		"$CMD_PARTED" -s -f "$_device" unit s resizepart "$_partnum" "${_end_sector}s"
	_rc=$EXEC_RC; _out="$EXEC_OUT"

	# Some parted versions still require an explicit confirmation when shrinking.
	# Retry with scripted confirmation so queued operations do not stop on rc=134.
	if [ "$_rc" -ne 0 ]; then
		case "$_out" in
			*"Shrinking a partition can cause data loss"*|*"are you sure you want to continue"*)
				exec_cmd_c "Resize partition (scripted-confirm retry)" \
					"printf 'Yes\\nIgnore\\nIgnore\\nIgnore\\n' | $CMD_PARTED ---pretend-input-tty -f $_device unit s resizepart $_partnum ${_end_sector}s yes" \
					/bin/sh -c "printf 'Yes\\nIgnore\\nIgnore\\nIgnore\\n' | $CMD_PARTED ---pretend-input-tty -f '$_device' unit s resizepart '$_partnum' '${_end_sector}s' yes 2>&1"
				_retry_rc=$EXEC_RC; _retry_out="$EXEC_OUT"
				if [ "$_retry_rc" -eq 0 ]; then
					_out="$_out\n\nRetry with scripted confirmation rc=$_retry_rc:\n$_retry_out"
					_rc=0
				else
					exec_cmd_c "Resize partition (trailing-yes retry)" \
						"$CMD_PARTED -s -f $_device unit s resizepart $_partnum ${_end_sector}s yes" \
						"$CMD_PARTED" -s -f "$_device" unit s resizepart "$_partnum" "${_end_sector}s" yes
					_retry_rc2=$EXEC_RC; _retry_out2="$EXEC_OUT"
					_out="$_out\n\nRetry with scripted confirmation rc=$_retry_rc:\n$_retry_out\n\nRetry with trailing yes rc=$_retry_rc2:\n$_retry_out2"
					_rc=$_retry_rc2
				fi
				;;
		esac
	fi

	if [ "$_rc" -eq 0 ]; then
		run_partprobe "$_device"
		if [ "$_resize_fs" = "yes" ]; then
			_ppath=$(partition_path "$_device" "$_partnum")
			_fstype=''
			if [ -n "$CMD_BLKID" ]; then
				_fstype=$($CMD_BLKID -o value -s TYPE "$_ppath" 2>/dev/null | head -n 1)
			fi

			case "$_fstype" in
				ext2|ext3|ext4)
					if [ -n "$CMD_E2FSCK" ] && [ -n "$CMD_RESIZE2FS" ]; then
						exec_cmd_c "e2fsck before FS resize" "$CMD_E2FSCK -v -f -p $_ppath" \
							"$CMD_E2FSCK" -v -f -p "$_ppath"
						_ck=$EXEC_OUT; _ck_rc=$EXEC_RC
						exec_cmd_c "resize2fs grow to partition size" "$CMD_RESIZE2FS -p $_ppath" \
							"$CMD_RESIZE2FS" -p "$_ppath"
						_rs=$EXEC_OUT; _rs_rc=$EXEC_RC
						_out="$_out\n\nFilesystem check rc=$_ck_rc:\n$_ck\n\nresize2fs rc=$_rs_rc:\n$_rs"
					else
						_out="$_out\n\nWarning: resize requested but e2fsprogs resize tools are not available"
					fi
					;;
				ntfs)
					if [ -n "$CMD_NTFSRESIZE" ]; then
						exec_cmd_c "ntfsresize grow" "$CMD_NTFSRESIZE -v -f $_ppath" \
							"$CMD_NTFSRESIZE" -v -f "$_ppath"
						_rs=$EXEC_OUT; _rs_rc=$EXEC_RC
						_out="$_out\n\nntfsresize rc=$_rs_rc:\n$_rs"
					else
						_out="$_out\n\nWarning: NTFS resize requested but ntfsresize is not available"
					fi
					;;
				fat|fat12|fat16|fat32|vfat)
					if [ -n "$CMD_FATRESIZE" ]; then
						if [ -n "$CMD_FSCK_FAT" ]; then
							exec_cmd_c "fsck.fat pre-repair" "$CMD_FSCK_FAT -v -a $_ppath" \
								"$CMD_FSCK_FAT" -v -a "$_ppath"
							_out="$_out\n\nfsck.fat pre-repair rc=$EXEC_RC:\n$EXEC_OUT"
						fi
						_fix_msg=$(fat_fix_total_sectors "$_ppath")
						[ -n "$_fix_msg" ] && _out="$_out\n\n$_fix_msg"
						[ -n "$STREAM_LOG" ] && printf '\033[1;33m\u26a0 WARNING: Disk write in progress \u2014 do NOT interrupt power or disconnect storage. This may take many minutes.\033[0m\n' >> "$STREAM_LOG"
						exec_cmd_c "fatresize grow" "$CMD_FATRESIZE -vps max $_ppath" \
							"$CMD_FATRESIZE" -vps max "$_ppath"
						_rs=$EXEC_OUT; _rs_rc=$EXEC_RC
						_out="$_out\n\nfatresize rc=$_rs_rc:\n$_rs"
					else
						_out="$_out\n\nWarning: FAT resize requested but fatresize is not available"
					fi
					;;
				*)
					_out="$_out\n\nWarning: filesystem resize supports ext2/3/4, NTFS and FAT only (detected: ${_fstype:-unknown})"
					;;
			esac
		fi
	fi

	if [ "$_rc" -eq 0 ]; then
		emit_cmd_result true "$_rc" "Partition resized" "$_out"
	else
		emit_cmd_result false "$_rc" "Partition resize failed" "$_out"
	fi
}

action_resize_filesystem() {
resolve_tools
if ! require_ack; then
emit_json_error "Dangerous operation blocked: type YES_I_UNDERSTAND first"
return
fi

_partition=$(cgi_param partition)
_fs_type=$(cgi_param fs_type)
_direction=$(cgi_param direction)
_target_kib=$(cgi_param target_kib)
_target_bytes=$(cgi_param target_bytes)
_extra_opts=$(cgi_param extra_opts)
_opts_display=''
[ -n "$_extra_opts" ] && _opts_display="$_extra_opts "

# Accept legacy byte payloads that may include a trailing B/b.
_target_bytes=$(safe_bytes_uint "$_target_bytes")

is_valid_device "$_partition" || { emit_json_error "Invalid partition path"; return; }
is_valid_extra_opts "$_extra_opts" || { emit_json_error "Invalid extra options"; return; }

case "$_direction" in
shrink|grow|'') : ;;
*) emit_json_error "Invalid resize direction"; return ;;
esac
[ -n "$_direction" ] || _direction='grow'

if [ -z "$_fs_type" ] || [ "$_fs_type" = "auto" ]; then
if [ -n "$CMD_BLKID" ]; then
_fs_type=$($CMD_BLKID -o value -s TYPE "$_partition" 2>/dev/null | head -n 1)
fi
fi

if dry_run_enabled; then
case "$_fs_type" in
ext2|ext3|ext4)
if [ "$_direction" = "shrink" ]; then
emit_dry_run_result "filesystem resize" "e2fsck -f -p $_partition
resize2fs $_partition ${_target_kib}K"
else
emit_dry_run_result "filesystem resize" "e2fsck -f -p $_partition
resize2fs $_partition"
fi
return
;;
ntfs)
if [ "$_direction" = "shrink" ]; then
emit_dry_run_result "filesystem resize" "ntfsresize -f -s ${_target_bytes} $_partition"
else
emit_dry_run_result "filesystem resize" "ntfsresize -f $_partition"
fi
return
;;
fat|fat12|fat16|fat32|vfat)
if [ "$_direction" = "shrink" ]; then
emit_dry_run_result "filesystem resize" "fatresize -vps ${_target_bytes} $_partition"
else
emit_dry_run_result "filesystem resize" "fatresize -vps max $_partition"
fi
return
;;
*)
emit_dry_run_result "filesystem resize" "# unsupported fs_type=${_fs_type:-unknown} for $_partition"
return
;;
esac
fi

case "$_fs_type" in
ext2|ext3|ext4)
[ -n "$CMD_E2FSCK" ] || { emit_json_error "e2fsck/e2fsprogs not available"; return; }
[ -n "$CMD_RESIZE2FS" ] || { emit_json_error "resize2fs/e2fsprogs not available"; return; }

if [ "$_direction" = "shrink" ]; then
_target_kib=$(safe_uint "$_target_kib")
[ "$_target_kib" -gt 0 ] || { emit_json_error "Invalid target_kib for shrink"; return; }

_cmd_ck="$CMD_E2FSCK -v -f -p $_partition"
exec_cmd_c "e2fsck before shrink" "$_cmd_ck" "$CMD_E2FSCK" -v -f -p "$_partition"
_ck="$EXEC_OUT"

_cmd_rs="$CMD_RESIZE2FS -p ${_opts_display}$_partition ${_target_kib}K"
if [ -n "$_extra_opts" ]; then
# shellcheck disable=SC2086
exec_cmd_c "resize2fs shrink" "$_cmd_rs" "$CMD_RESIZE2FS" -p $_extra_opts "$_partition" "${_target_kib}K"
else
exec_cmd_c "resize2fs shrink" "$_cmd_rs" "$CMD_RESIZE2FS" -p "$_partition" "${_target_kib}K"
fi
_rc=$EXEC_RC; _rs="$EXEC_OUT"
_out="\$ $_cmd_ck
$_ck

\$ $_cmd_rs
$_rs"
else
_cmd_ck="$CMD_E2FSCK -v -f -p $_partition"
exec_cmd_c "e2fsck before grow" "$_cmd_ck" "$CMD_E2FSCK" -v -f -p "$_partition"
_ck="$EXEC_OUT"
_cmd_rs="$CMD_RESIZE2FS -p ${_opts_display}$_partition"
if [ -n "$_extra_opts" ]; then
# shellcheck disable=SC2086
exec_cmd_c "resize2fs grow" "$_cmd_rs" "$CMD_RESIZE2FS" -p $_extra_opts "$_partition"
else
exec_cmd_c "resize2fs grow" "$_cmd_rs" "$CMD_RESIZE2FS" -p "$_partition"
fi
_rc=$EXEC_RC; _rs="$EXEC_OUT"
_out="\$ $_cmd_ck
$_ck

\$ $_cmd_rs
$_rs"
fi
if [ "$_rc" -eq 0 ]; then
emit_cmd_result true "$_rc" "Filesystem resized" "$_out"
else
emit_cmd_result false "$_rc" "Filesystem resize failed" "$_out"
fi
;;
ntfs)
[ -n "$CMD_NTFSRESIZE" ] || { emit_json_error "ntfsresize not available"; return; }
if [ "$_direction" = "shrink" ]; then
_target_bytes=$(safe_bytes_uint "$_target_bytes")
[ "$_target_bytes" -gt 0 ] || { emit_json_error "Invalid target_bytes for shrink"; return; }
_cmd_rs="$CMD_NTFSRESIZE -v -f -s $_target_bytes ${_opts_display}$_partition"
if [ -n "$_extra_opts" ]; then
# shellcheck disable=SC2086
exec_cmd_c "ntfsresize shrink" "$_cmd_rs" "$CMD_NTFSRESIZE" -v -f -s "$_target_bytes" $_extra_opts "$_partition"
else
exec_cmd_c "ntfsresize shrink" "$_cmd_rs" "$CMD_NTFSRESIZE" -v -f -s "$_target_bytes" "$_partition"
fi
else
_cmd_rs="$CMD_NTFSRESIZE -v -f ${_opts_display}$_partition"
if [ -n "$_extra_opts" ]; then
# shellcheck disable=SC2086
exec_cmd_c "ntfsresize grow" "$_cmd_rs" "$CMD_NTFSRESIZE" -v -f $_extra_opts "$_partition"
else
exec_cmd_c "ntfsresize grow" "$_cmd_rs" "$CMD_NTFSRESIZE" -v -f "$_partition"
fi
fi
_rc=$EXEC_RC; _out="$EXEC_OUT"
_out="\$ $_cmd_rs
$_out"
if [ "$_rc" -eq 0 ]; then
emit_cmd_result true "$_rc" "Filesystem resized" "$_out"
else
emit_cmd_result false "$_rc" "Filesystem resize failed" "$_out"
fi
;;
fat|fat12|fat16|fat32|vfat)
[ -n "$CMD_FATRESIZE" ] || { emit_json_error "fatresize not available"; return; }
_pre_out=''
# fatresize fails with "The file system is bigger than its volume!" when the FAT
# BPB sector count slightly exceeds the partition size.  Run fsck.fat -a first
# to correct the BPB; ignore the exit code (fsck.fat exits 1 even after fixing).
if [ -n "$CMD_FSCK_FAT" ]; then
_cmd_ck="$CMD_FSCK_FAT -v -a $_partition"
exec_cmd_c "fsck.fat pre-repair" "$_cmd_ck" "$CMD_FSCK_FAT" -v -a "$_partition"
_pre_out="\$ $_cmd_ck
$EXEC_OUT

"
fi
_fix_msg=$(fat_fix_total_sectors "$_partition")
[ -n "$_fix_msg" ] && _pre_out="${_pre_out}${_fix_msg}
"
_fix_msg=$(fat_fix_hidden_sectors "$_partition")
[ -n "$_fix_msg" ] && _pre_out="${_pre_out}${_fix_msg}
"
[ -n "$STREAM_LOG" ] && printf '\033[1;33m\u26a0 WARNING: Disk write in progress \u2014 do NOT interrupt power or disconnect storage. This may take many minutes.\033[0m\n' >> "$STREAM_LOG"
if [ "$_direction" = "shrink" ]; then
_target_bytes=$(safe_bytes_uint "$_target_bytes")
[ "$_target_bytes" -gt 0 ] || { emit_json_error "Invalid target_bytes for shrink"; return; }
_cmd_rs="$CMD_FATRESIZE -vps ${_target_bytes} ${_opts_display}$_partition"
if [ -n "$_extra_opts" ]; then
# shellcheck disable=SC2086
exec_cmd_c "fatresize shrink" "$_cmd_rs" "$CMD_FATRESIZE" -vps "${_target_bytes}" $_extra_opts "$_partition"
else
exec_cmd_c "fatresize shrink" "$_cmd_rs" "$CMD_FATRESIZE" -vps "${_target_bytes}" "$_partition"
fi
else
# Use explicit target_bytes for grow when available; fatresize 'max' can compute a
# location outside the device due to a bug with hidden_sectors double-counting.
_grow_target=''
if [ -n "$_target_bytes" ] && [ "$_target_bytes" -gt 0 ] 2>/dev/null; then
_grow_target=$(safe_bytes_uint "$_target_bytes")
fi
if [ -n "$_grow_target" ] && [ "$_grow_target" -gt 0 ]; then
_cmd_rs="$CMD_FATRESIZE -vps ${_grow_target} ${_opts_display}$_partition"
if [ -n "$_extra_opts" ]; then
# shellcheck disable=SC2086
exec_cmd_c "fatresize grow" "$_cmd_rs" "$CMD_FATRESIZE" -vps "${_grow_target}" $_extra_opts "$_partition"
else
exec_cmd_c "fatresize grow" "$_cmd_rs" "$CMD_FATRESIZE" -vps "${_grow_target}" "$_partition"
fi
else
_cmd_rs="$CMD_FATRESIZE -vps max ${_opts_display}$_partition"
if [ -n "$_extra_opts" ]; then
# shellcheck disable=SC2086
exec_cmd_c "fatresize grow" "$_cmd_rs" "$CMD_FATRESIZE" -vps max $_extra_opts "$_partition"
else
exec_cmd_c "fatresize grow" "$_cmd_rs" "$CMD_FATRESIZE" -vps max "$_partition"
fi
fi
fi
_rc=$EXEC_RC; _out="$EXEC_OUT"
_out="${_pre_out}\$ $_cmd_rs
$_out"
if [ "$_rc" -eq 0 ]; then
emit_cmd_result true "$_rc" "Filesystem resized" "$_out"
else
emit_cmd_result false "$_rc" "Filesystem resize failed" "$_out"
fi
;;
*)
emit_json_error "Unsupported or undetected filesystem type for resize"
;;
esac
}

action_create_filesystem() {
	resolve_tools
	if ! require_ack; then
		emit_json_error "Dangerous operation blocked: type YES_I_UNDERSTAND first"
		return
	fi

	_partition=$(cgi_param partition)
	_fs_type=$(cgi_param fs_type)
	_label=$(cgi_param label)
	_extra_opts=$(cgi_param extra_opts)
	_full_format=$(cgi_param full_format)

	is_valid_device "$_partition" || { emit_json_error "Invalid partition path"; return; }
	is_valid_extra_opts "$_extra_opts" || { emit_json_error "Invalid extra options"; return; }
	case "$_fs_type" in
		ext2|ext3|ext4|fat16|fat32|vfat|exfat|ntfs) : ;;
		*) emit_json_error "Unsupported filesystem type"; return ;;
	esac

	if dry_run_enabled; then
		case "$_fs_type" in
			ext2|ext3|ext4)
				_preview_cmd="mke2fs -F -t $_fs_type ${_extra_opts:-} $_partition"
				[ -n "$_label" ] && _preview_cmd="$_preview_cmd
e2label $_partition $_label"
				;;
			fat16)
				_preview_cmd="mkfs.fat -F 16 ${_extra_opts:-} $_partition"
				[ -n "$_label" ] && _preview_cmd="$_preview_cmd
fatlabel $_partition $_label"
				;;
			fat32|vfat)
				_preview_cmd="mkfs.fat -F 32 ${_extra_opts:-} $_partition"
				[ -n "$_label" ] && _preview_cmd="$_preview_cmd
fatlabel $_partition $_label"
				;;
			exfat)
				if [ -n "$_label" ]; then
					_preview_cmd="mkfs.exfat -n $_label ${_extra_opts:-} $_partition"
				else
					_preview_cmd="mkfs.exfat ${_extra_opts:-} $_partition"
				fi
				;;
			ntfs)
				if [ -n "$_label" ]; then
					_preview_cmd="mkntfs -f -v -L $_label ${_extra_opts:-} $_partition"
				else
					_preview_cmd="mkntfs -f -v ${_extra_opts:-} $_partition"
				fi
				;;
		esac
		emit_dry_run_result "filesystem creation" "$_preview_cmd"
		return
	fi

	case "$_fs_type" in
		ext2|ext3|ext4)
			[ -n "$CMD_MKE2FS" ] || { emit_json_error "mke2fs/e2fsprogs not available"; return; }
			_cmd_mk="$CMD_MKE2FS -v -F -t $_fs_type ${_extra_opts:+$_extra_opts }$_partition"
			if [ -n "$_extra_opts" ]; then
				# shellcheck disable=SC2086
				exec_cmd_c "mke2fs create $_fs_type" "$_cmd_mk" "$CMD_MKE2FS" -v -F -t "$_fs_type" $_extra_opts "$_partition"
			else
				exec_cmd_c "mke2fs create $_fs_type" "$_cmd_mk" "$CMD_MKE2FS" -v -F -t "$_fs_type" "$_partition"
			fi
			_rc=$EXEC_RC; _out="$EXEC_OUT"
			if [ "$_rc" -eq 0 ] && [ -n "$_label" ]; then
				if ! is_valid_label "$_label"; then
					_out="$_out\nWarning: label skipped (invalid chars)"
				elif [ -n "$CMD_E2LABEL" ]; then
					exec_cmd_c "e2label set" "$CMD_E2LABEL $_partition $_label" "$CMD_E2LABEL" "$_partition" "$_label"
					_out="$_out\n\nLabel:\n$EXEC_OUT"
				elif [ -n "$CMD_TUNE2FS" ]; then
					exec_cmd_c "tune2fs set label" "$CMD_TUNE2FS -L $_label $_partition" run_tune2fs -L "$_label" "$_partition"
					_lbl_rc=$EXEC_RC; _lbl_out="$EXEC_OUT"
					[ "$_lbl_rc" -eq 139 ] && _lbl_out="[tune2fs: Segmentation fault (SIGSEGV)]"
					_out="$_out\n\nLabel:\n$_lbl_out"
				fi
			fi
			;;
		fat16)
			[ -n "$CMD_MKFS_FAT" ] || { emit_json_error "mkfs.fat not available"; return; }
			_cmd_mk="$CMD_MKFS_FAT -v -F 16 ${_extra_opts:+$_extra_opts }$_partition"
			if [ -n "$_extra_opts" ]; then
				# shellcheck disable=SC2086
				exec_cmd_c "mkfs.fat fat16" "$_cmd_mk" "$CMD_MKFS_FAT" -v -F 16 $_extra_opts "$_partition"
			else
				exec_cmd_c "mkfs.fat fat16" "$_cmd_mk" "$CMD_MKFS_FAT" -v -F 16 "$_partition"
			fi
			_rc=$EXEC_RC; _out="$EXEC_OUT"
			if [ "$_rc" -eq 0 ] && [ -n "$_label" ] && [ -n "$CMD_FATLABEL" ]; then
				exec_cmd_c "fatlabel set" "$CMD_FATLABEL $_partition $_label" "$CMD_FATLABEL" "$_partition" "$_label"
				_out="$_out\n\nLabel:\n$EXEC_OUT"
			fi
			;;
		fat32|vfat)
			[ -n "$CMD_MKFS_FAT" ] || { emit_json_error "mkfs.fat not available"; return; }
			_cmd_mk="$CMD_MKFS_FAT -v -F 32 ${_extra_opts:+$_extra_opts }$_partition"
			if [ -n "$_extra_opts" ]; then
				# shellcheck disable=SC2086
				exec_cmd_c "mkfs.fat fat32" "$_cmd_mk" "$CMD_MKFS_FAT" -v -F 32 $_extra_opts "$_partition"
			else
				exec_cmd_c "mkfs.fat fat32" "$_cmd_mk" "$CMD_MKFS_FAT" -v -F 32 "$_partition"
			fi
			_rc=$EXEC_RC; _out="$EXEC_OUT"
			if [ "$_rc" -eq 0 ] && [ -n "$_label" ] && [ -n "$CMD_FATLABEL" ]; then
				exec_cmd_c "fatlabel set" "$CMD_FATLABEL $_partition $_label" "$CMD_FATLABEL" "$_partition" "$_label"
				_out="$_out\n\nLabel:\n$EXEC_OUT"
			fi
			;;
		exfat)
			[ -n "$CMD_MKFS_EXFAT" ] || { emit_json_error "mkfs.exfat not available"; return; }
			if [ -n "$_label" ]; then
				if ! is_valid_label "$_label"; then
					emit_json_error "Invalid exFAT label"
					return
				fi
			fi
			if [ -n "$_extra_opts" ]; then
				if [ -n "$_label" ]; then
					_cmd_mk="$CMD_MKFS_EXFAT -n $_label $_extra_opts $_partition"
					# shellcheck disable=SC2086
					exec_cmd_c "mkfs.exfat" "$_cmd_mk" "$CMD_MKFS_EXFAT" -n "$_label" $_extra_opts "$_partition"
				else
					_cmd_mk="$CMD_MKFS_EXFAT $_extra_opts $_partition"
					# shellcheck disable=SC2086
					exec_cmd_c "mkfs.exfat" "$_cmd_mk" "$CMD_MKFS_EXFAT" $_extra_opts "$_partition"
				fi
			else
				if [ -n "$_label" ]; then
					_cmd_mk="$CMD_MKFS_EXFAT -n $_label $_partition"
					exec_cmd_c "mkfs.exfat" "$_cmd_mk" "$CMD_MKFS_EXFAT" -n "$_label" "$_partition"
				else
					_cmd_mk="$CMD_MKFS_EXFAT $_partition"
					exec_cmd_c "mkfs.exfat" "$_cmd_mk" "$CMD_MKFS_EXFAT" "$_partition"
				fi
			fi
			_rc=$EXEC_RC; _out="$EXEC_OUT"
			if [ "$_rc" -eq 0 ] && [ -n "$_label" ] && [ -n "$CMD_EXFATLABEL" ]; then
				exec_cmd_c "exfatlabel set" "run_exfat_label $_partition $_label" run_exfat_label "$_partition" "$_label"
				_lbl_rc=$EXEC_RC; _lbl_out="$EXEC_OUT"
				if [ "$_lbl_rc" -eq 0 ]; then
					_out="$_out\n\nLabel:\n$_lbl_out"
				else
					_out="$_out\n\nWarning: exFAT label update failed\n$_lbl_out"
				fi
			fi
			;;
		ntfs)
			[ -n "$CMD_MKNTFS" ] || { emit_json_error "mkntfs not available"; return; }
			if [ -n "$_label" ]; then
				if ! is_valid_label "$_label"; then
					emit_json_error "Invalid NTFS label"
					return
				fi
			fi
			_ntfs_flag="-f"
			[ "$_full_format" = "1" ] && _ntfs_flag="-F"
			if [ -n "$_extra_opts" ]; then
				if [ -n "$_label" ]; then
					_cmd_mk="$CMD_MKNTFS $_ntfs_flag -v -L $_label $_extra_opts $_partition"
					# shellcheck disable=SC2086
					exec_cmd_c "mkntfs" "$_cmd_mk" "$CMD_MKNTFS" $_ntfs_flag -v -L "$_label" $_extra_opts "$_partition"
				else
					_cmd_mk="$CMD_MKNTFS $_ntfs_flag -v $_extra_opts $_partition"
					# shellcheck disable=SC2086
					exec_cmd_c "mkntfs" "$_cmd_mk" "$CMD_MKNTFS" $_ntfs_flag -v $_extra_opts "$_partition"
				fi
			else
				if [ -n "$_label" ]; then
					_cmd_mk="$CMD_MKNTFS $_ntfs_flag -v -L $_label $_partition"
					exec_cmd_c "mkntfs" "$_cmd_mk" "$CMD_MKNTFS" $_ntfs_flag -v -L "$_label" "$_partition"
				else
					_cmd_mk="$CMD_MKNTFS $_ntfs_flag -v $_partition"
					exec_cmd_c "mkntfs" "$_cmd_mk" "$CMD_MKNTFS" $_ntfs_flag -v "$_partition"
				fi
			fi
			_rc=$EXEC_RC; _out="$EXEC_OUT"
			;;
	esac

	if [ "$_rc" -eq 0 ]; then
		emit_cmd_result true "$_rc" "Filesystem created" "$_out"
	else
		emit_cmd_result false "$_rc" "Filesystem creation failed" "$_out"
	fi
}

action_check_filesystem() {
	resolve_tools
	_partition=$(cgi_param partition)
	_fs_type=$(cgi_param fs_type)
	_repair=$(cgi_param repair)
	_extra_opts=$(cgi_param extra_opts)
	_opts_display=''
	[ -n "$_extra_opts" ] && _opts_display="$_extra_opts "

	is_valid_device "$_partition" || { emit_json_error "Invalid partition path"; return; }
	is_valid_extra_opts "$_extra_opts" || { emit_json_error "Invalid extra options"; return; }
	if dry_run_enabled; then
		_preview_cmd="# fs_type=$_fs_type repair=$_repair
# backend auto-detects filesystem when fs_type=auto
# backend runs e2fsck/fsck.fat/fsck.exfat/ntfsfix depending on detected type
# if partition is mounted: umount → check/repair → remount
"
		emit_dry_run_result "filesystem check" "$_preview_cmd"
		return
	fi

	case "$_fs_type" in
		auto|'')
			if [ -n "$CMD_BLKID" ]; then
				_fs_type=$($CMD_BLKID -o value -s TYPE "$_partition" 2>/dev/null | head -n 1)
			fi
			;;
	esac

	# ── umount if currently mounted ──────────────────────────────────────────
	_was_mounted=''
	_orig_mountpoint=''
	_orig_mnt_fstype=''
	_orig_mnt_opts=''
	_mount_info=$(awk -v p="$_partition" '$1 == p { print $2, $3, $4; exit }' /proc/mounts 2>/dev/null)
	if [ -n "$_mount_info" ]; then
		_orig_mountpoint=$(printf '%s' "$_mount_info" | awk '{print $1}')
		_orig_mnt_fstype=$(printf '%s' "$_mount_info" | awk '{print $2}')
		_orig_mnt_opts=$(printf '%s'   "$_mount_info" | awk '{print $3}')
		[ -n "$CMD_UMOUNT" ] || { emit_json_error "umount not available; cannot unmount before check"; return; }
		exec_cmd_c "umount before check" "$CMD_UMOUNT $_partition" "$CMD_UMOUNT" "$_partition"
		if [ "$EXEC_RC" -ne 0 ]; then
			emit_cmd_result false "$EXEC_RC" "Unmount failed, check aborted" "$EXEC_OUT"
			return
		fi
		_was_mounted='yes'
	fi

	# ── run fsck (result stored, not emitted yet) ────────────────────────────
	_fsck_success='false'
	_fsck_rc=1
	_fsck_msg='Filesystem check failed'
	_fsck_out=''
	_fsck_done=''

	case "$_fs_type" in
		ext2|ext3|ext4)
			[ -n "$CMD_E2FSCK" ] || { emit_json_error "e2fsck/e2fsprogs not available"; return; }
			if [ "$_repair" = "yes" ]; then
				_cmd_display="$CMD_E2FSCK -v -f -p ${_opts_display}$_partition"
				if [ -n "$_extra_opts" ]; then
					# shellcheck disable=SC2086
					exec_cmd_c "e2fsck repair" "$_cmd_display" "$CMD_E2FSCK" -v -f -p $_extra_opts "$_partition"
				else
					exec_cmd_c "e2fsck repair" "$_cmd_display" "$CMD_E2FSCK" -v -f -p "$_partition"
				fi
			else
				_cmd_display="$CMD_E2FSCK -v -f -n ${_opts_display}$_partition"
				if [ -n "$_extra_opts" ]; then
					# shellcheck disable=SC2086
					exec_cmd_c "e2fsck check" "$_cmd_display" "$CMD_E2FSCK" -v -f -n $_extra_opts "$_partition"
				else
					exec_cmd_c "e2fsck check" "$_cmd_display" "$CMD_E2FSCK" -v -f -n "$_partition"
				fi
			fi
			_fsck_rc=$EXEC_RC
			_fsck_out="\$ $_cmd_display
$EXEC_OUT"
			if [ "$_fsck_rc" -eq 0 ] || [ "$_fsck_rc" -eq 1 ] || [ "$_fsck_rc" -eq 2 ]; then
				_fsck_success='true'; _fsck_msg='Filesystem check completed'
			else
				_fsck_success='false'; _fsck_msg='Filesystem check reported errors'
			fi
			_fsck_done='yes'
			;;
		fat|fat12|fat16|fat32|vfat)
			[ -n "$CMD_FSCK_FAT" ] || { emit_json_error "fsck.fat not available"; return; }
			if [ "$_repair" = "yes" ]; then
				_cmd_display="$CMD_FSCK_FAT -v -a ${_opts_display}$_partition"
				if [ -n "$_extra_opts" ]; then
					# shellcheck disable=SC2086
					exec_cmd_c "fsck.fat repair" "$_cmd_display" "$CMD_FSCK_FAT" -v -a $_extra_opts "$_partition"
				else
					exec_cmd_c "fsck.fat repair" "$_cmd_display" "$CMD_FSCK_FAT" -v -a "$_partition"
				fi
			else
				_cmd_display="$CMD_FSCK_FAT -v -n ${_opts_display}$_partition"
				if [ -n "$_extra_opts" ]; then
					# shellcheck disable=SC2086
					exec_cmd_c "fsck.fat check" "$_cmd_display" "$CMD_FSCK_FAT" -v -n $_extra_opts "$_partition"
				else
					exec_cmd_c "fsck.fat check" "$_cmd_display" "$CMD_FSCK_FAT" -v -n "$_partition"
				fi
			fi
			_fsck_rc=$EXEC_RC
			_fsck_out="\$ $_cmd_display
$EXEC_OUT"
			if [ "$_fsck_rc" -eq 0 ] || [ "$_fsck_rc" -eq 1 ]; then
				_fsck_success='true'; _fsck_msg='Filesystem check completed'
			else
				_fsck_success='false'; _fsck_msg='Filesystem check reported errors'
			fi
			_fsck_done='yes'
			;;
		exfat)
			[ -n "$CMD_FSCK_EXFAT" ] || { emit_json_error "fsck.exfat not available"; return; }
			if [ "$_repair" = "yes" ]; then
				_cmd_display="$CMD_FSCK_EXFAT ${_opts_display}$_partition"
				if [ -n "$_extra_opts" ]; then
					# shellcheck disable=SC2086
					exec_cmd_c "fsck.exfat repair" "$_cmd_display" "$CMD_FSCK_EXFAT" $_extra_opts "$_partition"
				else
					exec_cmd_c "fsck.exfat repair" "$_cmd_display" "$CMD_FSCK_EXFAT" "$_partition"
				fi
			else
				_cmd_display="$CMD_FSCK_EXFAT -n ${_opts_display}$_partition"
				if [ -n "$_extra_opts" ]; then
					# shellcheck disable=SC2086
					exec_cmd_c "fsck.exfat check" "$_cmd_display" "$CMD_FSCK_EXFAT" -n $_extra_opts "$_partition"
				else
					exec_cmd_c "fsck.exfat check" "$_cmd_display" "$CMD_FSCK_EXFAT" -n "$_partition"
				fi
			fi
			_fsck_rc=$EXEC_RC
			_fsck_out="\$ $_cmd_display
$EXEC_OUT"
			if [ "$_fsck_rc" -eq 0 ] || [ "$_fsck_rc" -eq 1 ] || [ "$_fsck_rc" -eq 2 ]; then
				_fsck_success='true'; _fsck_msg='exFAT check completed'
			else
				_fsck_success='false'; _fsck_msg='exFAT check reported errors'
			fi
			_fsck_done='yes'
			;;
		ntfs)
			if [ -n "$CMD_NTFSFIX" ]; then
				if [ "$_repair" = "yes" ]; then
					_cmd_display="$CMD_NTFSFIX ${_opts_display}$_partition"
					if [ -n "$_extra_opts" ]; then
						# shellcheck disable=SC2086
						exec_cmd_c "ntfsfix repair" "$_cmd_display" "$CMD_NTFSFIX" $_extra_opts "$_partition"
					else
						exec_cmd_c "ntfsfix repair" "$_cmd_display" "$CMD_NTFSFIX" "$_partition"
					fi
				else
					_cmd_display="$CMD_NTFSFIX -n ${_opts_display}$_partition"
					if [ -n "$_extra_opts" ]; then
						# shellcheck disable=SC2086
						exec_cmd_c "ntfsfix check" "$_cmd_display" "$CMD_NTFSFIX" -n $_extra_opts "$_partition"
					else
						exec_cmd_c "ntfsfix check" "$_cmd_display" "$CMD_NTFSFIX" -n "$_partition"
					fi
				fi
				_fsck_rc=$EXEC_RC
				_fsck_out="\$ $_cmd_display
$EXEC_OUT"
				_fsck_success='true'; _fsck_msg='NTFS check completed'
				_fsck_done='yes'
			elif [ -n "$CMD_NTFSINFO" ]; then
				_cmd_display="$CMD_NTFSINFO -m $_partition"
				exec_cmd_c "ntfsinfo" "$_cmd_display" "$CMD_NTFSINFO" -m "$_partition"
				_fsck_rc=$EXEC_RC
				_fsck_out="\$ $_cmd_display
$EXEC_OUT"
				_fsck_success='true'; _fsck_msg='NTFS metadata report collected (ntfsfix unavailable)'
				_fsck_done='yes'
			else
				emit_json_error "Neither ntfsfix nor ntfsinfo is available"
			fi
			;;
		*)
			emit_json_error "Unsupported or undetected filesystem type"
			;;
	esac

	[ "$_fsck_done" = 'yes' ] || return

	# ── remount if partition was mounted before ──────────────────────────────
	if [ "$_was_mounted" = 'yes' ] && [ -n "$CMD_MOUNT" ]; then
		mkdir -p "$_orig_mountpoint" 2>/dev/null
		if [ -n "$_orig_mnt_fstype" ] && [ "$_orig_mnt_fstype" != "auto" ]; then
			exec_cmd_c "remount after check" \
				"$CMD_MOUNT -t $_orig_mnt_fstype -o $_orig_mnt_opts $_partition $_orig_mountpoint" \
				"$CMD_MOUNT" -t "$_orig_mnt_fstype" -o "$_orig_mnt_opts" "$_partition" "$_orig_mountpoint"
		else
			exec_cmd_c "remount after check" \
				"$CMD_MOUNT $_partition $_orig_mountpoint" \
				"$CMD_MOUNT" "$_partition" "$_orig_mountpoint"
		fi
		if [ "$EXEC_RC" -ne 0 ]; then
			_fsck_msg="$_fsck_msg (remount failed: $EXEC_OUT)"
		else
			_fsck_msg="$_fsck_msg; remounted on $_orig_mountpoint"
		fi
	fi

	emit_cmd_result "$_fsck_success" "$_fsck_rc" "$_fsck_msg" "$_fsck_out"
}

action_set_label() {
	resolve_tools
	if ! require_ack; then
		emit_json_error "Dangerous operation blocked: type YES_I_UNDERSTAND first"
		return
	fi

	_partition=$(cgi_param partition)
	_fs_type=$(cgi_param fs_type)
	_label=$(cgi_param label)

	is_valid_device "$_partition" || { emit_json_error "Invalid partition path"; return; }
	is_valid_label "$_label" || { emit_json_error "Invalid label (allowed: letters, numbers, space, dot, dash, underscore)"; return; }

	if dry_run_enabled; then
		emit_dry_run_result "set filesystem label" "# fs_type=$_fs_type
# backend auto-detects filesystem when fs_type=auto
# ext: e2label/tune2fs, fat: fatlabel, exfat: exfatlabel/tune.exfat, ntfs: ntfslabel
"
		return
	fi

	case "$_fs_type" in
		auto|'')
			if [ -n "$CMD_BLKID" ]; then
				_fs_type=$($CMD_BLKID -o value -s TYPE "$_partition" 2>/dev/null | head -n 1)
			fi
			;;
	esac

	case "$_fs_type" in
		ext2|ext3|ext4)
			if [ -n "$CMD_E2LABEL" ]; then
				exec_cmd_c "e2label set" "$CMD_E2LABEL $_partition $_label" "$CMD_E2LABEL" "$_partition" "$_label"
				_rc=$EXEC_RC; _out="$EXEC_OUT"
			elif [ -n "$CMD_TUNE2FS" ]; then
				exec_cmd_c "tune2fs set label" "$CMD_TUNE2FS -L $_label $_partition" run_tune2fs -L "$_label" "$_partition"
				_rc=$EXEC_RC; _out="$EXEC_OUT"
				[ "$_rc" -eq 139 ] && _out="[tune2fs: Segmentation fault (SIGSEGV)]" && _rc=1
			else
				emit_json_error "Neither e2label nor tune2fs is available"
				return
			fi
			;;
		fat|fat12|fat16|fat32|vfat)
			[ -n "$CMD_FATLABEL" ] || { emit_json_error "fatlabel not available"; return; }
			exec_cmd_c "fatlabel set" "$CMD_FATLABEL $_partition $_label" "$CMD_FATLABEL" "$_partition" "$_label"
			_rc=$EXEC_RC; _out="$EXEC_OUT"
			;;
		exfat)
			[ -n "$CMD_EXFATLABEL" ] || { emit_json_error "exfatlabel/tune.exfat not available"; return; }
			exec_cmd_c "exfatlabel set" "run_exfat_label $_partition $_label" run_exfat_label "$_partition" "$_label"
			_rc=$EXEC_RC; _out="$EXEC_OUT"
			;;
		ntfs)
			[ -n "$CMD_NTFSLABEL" ] || { emit_json_error "ntfslabel not available"; return; }
			exec_cmd_c "ntfslabel set" "$CMD_NTFSLABEL $_partition $_label" "$CMD_NTFSLABEL" "$_partition" "$_label"
			_rc=$EXEC_RC; _out="$EXEC_OUT"
			;;
		*)
			emit_json_error "Unsupported or undetected filesystem type"
			return
			;;
	esac

	if [ "$_rc" -eq 0 ]; then
		emit_cmd_result true "$_rc" "Label updated" "$_out"
	else
		emit_cmd_result false "$_rc" "Label update failed" "$_out"
	fi
}

action_set_partition_name() {
	resolve_tools
	if ! require_ack; then
		emit_json_error "Dangerous operation blocked: type YES_I_UNDERSTAND first"
		return
	fi

	_device=$(cgi_param device)
	_partnum=$(cgi_param partnum)
	_part_name=$(cgi_param part_name)

	[ -n "$CMD_PARTED" ] || { emit_json_error "parted command not available"; return; }
	is_valid_device "$_device" || { emit_json_error "Invalid device"; return; }
	is_valid_partnum "$_partnum" || { emit_json_error "Invalid partition number"; return; }
	is_valid_label "$_part_name" || { emit_json_error "Invalid partition name"; return; }

	if dry_run_enabled; then
		emit_dry_run_result "set partition name" "parted -s $_device name $_partnum $_part_name"
		return
	fi

	exec_cmd_c "Set partition name to $_part_name" \
		"$CMD_PARTED -s $_device name $_partnum $_part_name" \
		"$CMD_PARTED" -s "$_device" name "$_partnum" "$_part_name"
	_rc=$EXEC_RC; _out="$EXEC_OUT"
	if [ "$_rc" -eq 0 ]; then
		emit_cmd_result true "$_rc" "Partition name updated" "$_out"
	else
		emit_cmd_result false "$_rc" "Partition name update failed" "$_out"
	fi
}

action_set_partition_flag() {
	resolve_tools
	if ! require_ack; then
		emit_json_error "Dangerous operation blocked: type YES_I_UNDERSTAND first"
		return
	fi

	_device=$(cgi_param device)
	_partnum=$(cgi_param partnum)
	_flag=$(cgi_param flag)
	_state=$(cgi_param state)

	[ -n "$CMD_PARTED" ] || { emit_json_error "parted command not available"; return; }
	is_valid_device "$_device" || { emit_json_error "Invalid device"; return; }
	is_valid_partnum "$_partnum" || { emit_json_error "Invalid partition number"; return; }
	is_valid_flag_name "$_flag" || { emit_json_error "Invalid flag name"; return; }
	case "$_state" in
		on|off) : ;;
		*) emit_json_error "Invalid flag state"; return ;;
	esac

	if dry_run_enabled; then
		emit_dry_run_result "set partition flag" "parted -s $_device set $_partnum $_flag $_state"
		return
	fi

	exec_cmd_c "Set partition flag $_flag=$_state on p$_partnum" \
		"$CMD_PARTED -s $_device set $_partnum $_flag $_state" \
		"$CMD_PARTED" -s "$_device" set "$_partnum" "$_flag" "$_state"
	_rc=$EXEC_RC; _out="$EXEC_OUT"
	if [ "$_rc" -eq 0 ]; then
		emit_cmd_result true "$_rc" "Partition flag updated" "$_out"
	else
		emit_cmd_result false "$_rc" "Partition flag update failed" "$_out"
	fi
}

action_convert_table_label() {
	resolve_tools
	if ! require_ack; then
		emit_json_error "Dangerous operation blocked: type YES_I_UNDERSTAND first"
		return
	fi

	_device=$(cgi_param device)
	_table_type=$(cgi_param table_type)

	[ -n "$CMD_PARTED" ] || { emit_json_error "parted command not available"; return; }
	is_valid_device "$_device" || { emit_json_error "Invalid device"; return; }
	case "$_table_type" in
		gpt|msdos|bsd|loop|atari|dvh|mac|pc98|sun) : ;;
		*) emit_json_error "Invalid table type (allowed: gpt msdos bsd loop atari dvh mac pc98 sun)"; return ;;
	esac

	if dry_run_enabled; then
		emit_dry_run_result "convert partition table" "parted -s $_device mklabel $_table_type"
		return
	fi

	exec_cmd_c "Create $_table_type partition table on $_device" \
		"$CMD_PARTED -s $_device mklabel $_table_type" \
		"$CMD_PARTED" -s "$_device" mklabel "$_table_type"
	_rc=$EXEC_RC; _out="$EXEC_OUT"
	if [ "$_rc" -eq 0 ]; then
		run_partprobe "$_device"
		emit_cmd_result true "$_rc" "Partition table converted to $_table_type" "$_out"
	else
		emit_cmd_result false "$_rc" "Partition table conversion failed" "$_out"
	fi
}

action_move_partition() {

	_device=$(cgi_param device)
	_source_device=$(cgi_param source_device)
	_source_partition=$(cgi_param source_partition)
	_source_partnum=$(cgi_param source_partnum)
	_start_sector=$(cgi_param start_sector)
	_end_sector=$(cgi_param end_sector)
	_clone_mode=$(cgi_param clone_mode)
	_target_mountpoint=$(cgi_param target_mountpoint)
	_align_bytes=$(cgi_param align_bytes)
	_unmount_before=$(cgi_param unmount_before)
	_force_fs=$(cgi_param force_fs)
	_partclone_extra=$(cgi_param partclone_extra)
	_step_delay=$(cgi_param step_delay)
	_partclone_verify=$(cgi_param partclone_verify)
	_fat_fsck_passes=$(cgi_param fat_fsck_passes)
	_dd_fallback=$(cgi_param dd_fallback)
	_skip_write_error=$(cgi_param skip_write_error)

	[ -n "$_source_device" ] || _source_device="$_device"

	is_valid_device "$_device" || { emit_json_error "Invalid target device"; return; }
	is_valid_device "$_source_device" || { emit_json_error "Invalid source device"; return; }
	is_valid_sector "$_start_sector" || { emit_json_error "Invalid start sector"; return; }
	is_valid_sector "$_end_sector" || { emit_json_error "Invalid end sector"; return; }

	if [ -n "$_source_partition" ]; then
		is_valid_device "$_source_partition" || { emit_json_error "Invalid source partition path"; return; }
		_source_path="$_source_partition"
		if [ -z "$_source_partnum" ]; then
			_source_partnum=$(printf '%s' "$_source_partition" | awk -v d="$_source_device" '
				index($0, d) == 1 {
					rest = substr($0, length(d) + 1)
					sub(/^p/, "", rest)
					if (rest ~ /^[0-9]+$/) print rest
				}')
		fi
	else
		is_valid_partnum "$_source_partnum" || { emit_json_error "Invalid source partition number"; return; }
		_source_path=$(partition_path "$_source_device" "$_source_partnum")
	fi

	is_valid_partnum "$_source_partnum" || { emit_json_error "Cannot determine source partition number"; return; }

	_clone_flag='smart'
	case "$_clone_mode" in
		sector|dd) _clone_flag='dd' ;;
	esac

	case "$_align_bytes" in
		512|4096|1048576) : ;;
		*) _align_bytes='1048576' ;;
	esac

	case "$_unmount_before" in
		no) _umount_flag='' ;;
		*) _umount_flag='-u' ;;
	esac

	case "$_step_delay" in
		''|*[!0-9]*) _step_delay='0' ;;
	esac

	case "$_partclone_verify" in
		yes|YES|true|1) _verify_flag='-V' ;;
		*) _verify_flag='' ;;
	esac

	_extra_safe=$(printf '%s' "$_partclone_extra" | tr -d '"'"'"'`$;|<>&(){}\\')
	_fs_safe=$(printf '%s' "$_force_fs" | tr -cd 'a-zA-Z0-9+._-')
	_fat_fsck_passes_safe=$(printf '%s' "$_fat_fsck_passes" | tr -cd '0-9')
	[ -z "$_fat_fsck_passes_safe" ] && _fat_fsck_passes_safe='2'
	case "$_dd_fallback" in 0) _dd_fallback='0' ;; *) _dd_fallback='1' ;; esac
	case "$_skip_write_error" in 1|yes|YES|true) _skip_write_flag='-W' ;; *) _skip_write_flag='' ;; esac

	_mount_args=''
	[ -n "$_target_mountpoint" ] && _mount_args="-o -t $_target_mountpoint"

	if dry_run_enabled; then
		_preview="$CMD_PARTITION_MIGRATION"
		_preview="$_preview -d $_device"
		_preview="$_preview -D $_source_device"
		_preview="$_preview -p $_source_path"
		_preview="$_preview -n $_source_partnum"
		_preview="$_preview -S $_start_sector"
		_preview="$_preview -E $_end_sector"
		_preview="$_preview -c $_clone_flag"
		_preview="$_preview -a $_align_bytes"
		_preview="$_preview -w $_step_delay"
		_preview="$_preview -M"
		[ -n "$_umount_flag" ] && _preview="$_preview -u"
		[ -n "$_verify_flag" ] && _preview="$_preview -V"
		[ -n "$_fs_safe" ] && _preview="$_preview -f $_fs_safe"
		[ -n "$_extra_safe" ] && _preview="$_preview -x '$_extra_safe'"
		[ -n "$_target_mountpoint" ] && _preview="$_preview -o -t $_target_mountpoint"
		_preview="$_preview -F $_fat_fsck_passes_safe -b $_dd_fallback"
		[ -n "$_skip_write_flag" ] && _preview="$_preview -W"
		_preview="$_preview -r"
		emit_dry_run_result "partition move" "$_preview"
		return
	fi

	# Validate target sector range against target disk capacity before invoking the script
	_target_disk_sectors=''
	if [ -r "/sys/block/${_device##*/}/size" ]; then
		_target_disk_sectors=$(cat "/sys/block/${_device##*/}/size" 2>/dev/null)
	elif [ -n "$CMD_BLOCKDEV" ]; then
		_target_disk_sectors=$($CMD_BLOCKDEV --getsz "$_device" 2>/dev/null)
	fi
	if [ -n "$_target_disk_sectors" ] && [ "$_target_disk_sectors" -gt 0 ] 2>/dev/null; then
		if [ "$_end_sector" -ge "$_target_disk_sectors" ] 2>/dev/null; then
			emit_json_error "Target sector range end (${_end_sector}) exceeds target disk ${_device} capacity (${_target_disk_sectors} sectors). Check that the correct target device is selected."
			return
		fi
	fi

	# shellcheck disable=SC2086
	exec_cmd "Move partition (partition_migration.sh)" \
		"$CMD_PARTITION_MIGRATION -d $_device -D $_source_device -p $_source_path -n $_source_partnum -S $_start_sector -E $_end_sector -c $_clone_flag -a $_align_bytes -w $_step_delay -M ${_umount_flag} ${_verify_flag} -F $_fat_fsck_passes_safe -b $_dd_fallback${_skip_write_flag:+ -W}" \
		"$CMD_PARTITION_MIGRATION" \
			-d "$_device" \
			-D "$_source_device" \
			-p "$_source_path" \
			-n "$_source_partnum" \
			-S "$_start_sector" \
			-E "$_end_sector" \
			-c "$_clone_flag" \
			-a "$_align_bytes" \
			-w "$_step_delay" \
			-M \
			${_umount_flag} \
			${_verify_flag} \
			-F "$_fat_fsck_passes_safe" \
			-b "$_dd_fallback" \
			${_skip_write_flag} \
			${_fs_safe:+"-f"} ${_fs_safe} \
			${_extra_safe:+"-x"} ${_extra_safe:+"$_extra_safe"} \
			$_mount_args
	_rc=$EXEC_RC
	_out="$EXEC_OUT"

	if [ "$_rc" -eq 0 ]; then
		emit_cmd_result true "$_rc" "Partition moved successfully" "$_out"
	else
		emit_cmd_result false "$_rc" "Partition move failed" "$_out"
	fi
}

action_clone_partition_dd() {
	resolve_tools
	if ! require_ack; then
		emit_json_error "Dangerous operation blocked: type YES_I_UNDERSTAND first"
		return
	fi

	[ -n "$CMD_PARTITION_MIGRATION" ] || { emit_json_error "partition_migration.sh not found in PATH"; return; }

	_device=$(cgi_param device)
	_source_partition=$(cgi_param source_partition)
	_source_device=$(cgi_param source_device)
	_source_partnum=$(cgi_param source_partnum)
	_target_device=$(cgi_param target_device)
	_target_start_sector=$(cgi_param target_start_sector)
	_target_end_sector=$(cgi_param target_end_sector)
	_clone_mode=$(cgi_param clone_mode)
	_target_mountpoint=$(cgi_param target_mountpoint)
	_align_bytes=$(cgi_param align_bytes)
	_unmount_before=$(cgi_param unmount_before)
	_force_fs=$(cgi_param force_fs)
	_partclone_extra=$(cgi_param partclone_extra)
	_step_delay=$(cgi_param step_delay)
	_partclone_verify=$(cgi_param partclone_verify)
	_fat_fsck_passes=$(cgi_param fat_fsck_passes)
	_dd_fallback=$(cgi_param dd_fallback)
	_skip_write_error=$(cgi_param skip_write_error)

	[ -n "$_source_device" ] || _source_device="$_device"
	[ -n "$_target_device" ] || _target_device="$_device"

	is_valid_device "$_source_device" || { emit_json_error "Invalid source device"; return; }
	is_valid_device "$_target_device" || { emit_json_error "Invalid target device"; return; }
	is_valid_sector "$_target_start_sector" || { emit_json_error "Invalid target start sector"; return; }
	is_valid_sector "$_target_end_sector" || { emit_json_error "Invalid target end sector"; return; }
	if [ "$_target_start_sector" -ge "$_target_end_sector" ]; then
		emit_json_error "Target start sector must be lower than target end sector"
		return
	fi

	if [ -n "$_source_partition" ]; then
		is_valid_device "$_source_partition" || { emit_json_error "Invalid source partition path"; return; }
		_source_path="$_source_partition"
		if [ -z "$_source_partnum" ]; then
			_source_partnum=$(printf '%s' "$_source_partition" | awk -v d="$_source_device" '
				index($0, d) == 1 {
					rest = substr($0, length(d) + 1)
					sub(/^p/, "", rest)
					if (rest ~ /^[0-9]+$/) print rest
				}')
		fi
	else
		is_valid_partnum "$_source_partnum" || { emit_json_error "Invalid source partition number"; return; }
		_source_path=$(partition_path "$_source_device" "$_source_partnum")
	fi

	is_valid_partnum "$_source_partnum" || { emit_json_error "Cannot determine source partition number"; return; }

	_clone_flag='smart'
	case "$_clone_mode" in
		sector|dd) _clone_flag='dd' ;;
	esac

	case "$_align_bytes" in
		512|4096|1048576) : ;;
		*) _align_bytes='1048576' ;;
	esac

	case "$_unmount_before" in
		no) _umount_flag='' ;;
		*) _umount_flag='-u' ;;
	esac

	case "$_step_delay" in
		''|*[!0-9]*) _step_delay='0' ;;
	esac

	case "$_partclone_verify" in
		yes|YES|true|1) _verify_flag='-V' ;;
		*) _verify_flag='' ;;
	esac

	_extra_safe=$(printf '%s' "$_partclone_extra" | tr -d '"'"'"'`$;|<>&(){}\\')
	_fs_safe=$(printf '%s' "$_force_fs" | tr -cd 'a-zA-Z0-9+._-')
	_fat_fsck_passes_safe=$(printf '%s' "$_fat_fsck_passes" | tr -cd '0-9')
	[ -z "$_fat_fsck_passes_safe" ] && _fat_fsck_passes_safe='2'
	case "$_dd_fallback" in 0) _dd_fallback='0' ;; *) _dd_fallback='1' ;; esac
	case "$_skip_write_error" in 1|yes|YES|true) _skip_write_flag='-W' ;; *) _skip_write_flag='' ;; esac

	_mount_args=''
	[ -n "$_target_mountpoint" ] && _mount_args="-o -t $_target_mountpoint"

	if dry_run_enabled; then
		_preview="$CMD_PARTITION_MIGRATION"
		_preview="$_preview -d $_target_device"
		_preview="$_preview -D $_source_device"
		_preview="$_preview -p $_source_path"
		_preview="$_preview -n $_source_partnum"
		_preview="$_preview -S $_target_start_sector"
		_preview="$_preview -E $_target_end_sector"
		_preview="$_preview -c $_clone_flag"
		_preview="$_preview -a $_align_bytes"
		_preview="$_preview -w $_step_delay"
		[ -n "$_umount_flag" ] && _preview="$_preview -u"
		[ -n "$_verify_flag" ] && _preview="$_preview -V"
		[ -n "$_fs_safe" ] && _preview="$_preview -f $_fs_safe"
		[ -n "$_extra_safe" ] && _preview="$_preview -x '$_extra_safe'"
		[ -n "$_target_mountpoint" ] && _preview="$_preview -o -t $_target_mountpoint"
		_preview="$_preview -F $_fat_fsck_passes_safe -b $_dd_fallback"
		[ -n "$_skip_write_flag" ] && _preview="$_preview -W"
		_preview="$_preview -r"
		emit_dry_run_result "partition clone ($_clone_flag)" "$_preview"
		return
	fi

	# shellcheck disable=SC2086
	exec_cmd "Clone partition (partition_migration.sh)" \
		"$CMD_PARTITION_MIGRATION -d $_target_device -D $_source_device -p $_source_path -n $_source_partnum -S $_target_start_sector -E $_target_end_sector -c $_clone_flag -a $_align_bytes -w $_step_delay ${_umount_flag} ${_verify_flag} -F $_fat_fsck_passes_safe -b $_dd_fallback${_skip_write_flag:+ -W}" \
		"$CMD_PARTITION_MIGRATION" \
			-d "$_target_device" \
			-D "$_source_device" \
			-p "$_source_path" \
			-n "$_source_partnum" \
			-S "$_target_start_sector" \
			-E "$_target_end_sector" \
			-c "$_clone_flag" \
			-a "$_align_bytes" \
			-w "$_step_delay" \
			${_umount_flag} \
			${_verify_flag} \
			-F "$_fat_fsck_passes_safe" \
			-b "$_dd_fallback" \
			${_skip_write_flag} \
			${_fs_safe:+"-f"} ${_fs_safe} \
			${_extra_safe:+"-x"} ${_extra_safe:+"$_extra_safe"} \
			$_mount_args
	_rc=$EXEC_RC
	_out="$EXEC_OUT"

	if [ "$_rc" -eq 0 ]; then
		emit_cmd_result true "$_rc" "Partition cloned successfully" "$_out"
	else
		emit_cmd_result false "$_rc" "Partition clone failed" "$_out"
	fi
}

action_verify_partition() {
	resolve_tools

	[ -n "$CMD_PARTITION_MIGRATION" ] || { emit_json_error "partition_migration.sh not found in PATH"; return; }

	_source_partition=$(cgi_param source_partition)
	_compare_partition=$(cgi_param compare_partition)
	_unmount_before=$(cgi_param unmount_before)
	_step_delay=$(cgi_param step_delay)

	is_valid_device "$_source_partition"  || { emit_json_error "Invalid source partition path"; return; }
	is_valid_device "$_compare_partition" || { emit_json_error "Invalid compare partition path"; return; }

	case "$_unmount_before" in
		no) _umount_flag='' ;;
		*)  _umount_flag='-u' ;;
	esac

	case "$_step_delay" in
		''|*[!0-9]*) _step_delay='0' ;;
	esac

	if dry_run_enabled; then
		_preview="$CMD_PARTITION_MIGRATION"
		_preview="$_preview -p $_source_partition"
		_preview="$_preview -Z $_compare_partition"
		[ -n "$_umount_flag" ] && _preview="$_preview -u"
		_preview="$_preview -w $_step_delay"
		_preview="$_preview -r"
		emit_dry_run_result "partition verify (compare)" "$_preview"
		return
	fi

	# shellcheck disable=SC2086
	exec_cmd "Verify partitions (partition_migration.sh -Z)" \
		"$CMD_PARTITION_MIGRATION -p $_source_partition -Z $_compare_partition ${_umount_flag} -w $_step_delay" \
		"$CMD_PARTITION_MIGRATION" \
			-p "$_source_partition" \
			-Z "$_compare_partition" \
			${_umount_flag} \
			-w "$_step_delay"
	_rc=$EXEC_RC
	_out="$EXEC_OUT"

	if [ "$_rc" -eq 0 ]; then
		emit_cmd_result true "$_rc" "Partitions are identical" "$_out"
	else
		emit_cmd_result false "$_rc" "Partitions differ or comparison failed" "$_out"
	fi
}

# ── Partclone image / network / ddrescue helpers ────────────────────────────────────────

# Common param validation and script path resolution for partition_image.sh calls
_action_partition_image_common() {
	resolve_tools
	CMD_PARTITION_IMAGE=$(find_cmd partition_image.sh)
	[ -n "$CMD_PARTITION_IMAGE" ] || { emit_json_error "partition_image.sh not found in PATH"; return 1; }
	return 0
}

action_partclone_export() {
	_action_partition_image_common || return
	_partition=$(cgi_param partition)
	_output=$(cgi_param output_file)
	_compress=$(cgi_param compression)
	_force_fs=$(cgi_param force_fs)
	_verify=$(cgi_param verify)
	_unmount=$(cgi_param unmount_before)
	_step_delay=$(cgi_param step_delay)
	_extra_opts=$(cgi_param extra_opts)
	_use_dd=$(cgi_param use_dd)
	_dry_run=$(cgi_param dry_run)

	is_valid_device "$_partition" || { emit_json_error "Invalid partition path"; return; }
	[ -n "$_output" ] || { emit_json_error "Output image file path required"; return; }
	case "$_compress" in
		none|gzip|gz|bzip2|bz2|lz4|zstd|'') ;;
		*) emit_json_error "Invalid compression '${_compress}'"; return ;;
	esac
	case "$_step_delay" in ''|*[!0-9]*) _step_delay='1' ;; esac

	_flags='-e'
	[ "$_unmount" = 'yes' ] && _flags="$_flags -u"
	[ "$_verify"  = 'yes' ] && _flags="$_flags -V"
	[ "$_use_dd"  = 'yes' ] && _flags="$_flags -c"

	if dry_run_enabled; then
		_preview="$CMD_PARTITION_IMAGE $_flags"
		_preview="$_preview -p $_partition"
		_preview="$_preview -o '$_output'"
		[ -n "$_compress" ] && [ "$_compress" != 'none' ] && _preview="$_preview -z $_compress"
		_preview="$_preview -w $_step_delay"
		[ -n "$_force_fs" ]   && _preview="$_preview -f $_force_fs"
		[ -n "$_extra_opts" ] && _preview="$_preview -x '$_extra_opts'"
		_preview="$_preview -n"
		emit_dry_run_result "partclone export" "$_preview"
		return
	fi

	# shellcheck disable=SC2086
	exec_cmd "Export partition (partition_image.sh)" \
		"$CMD_PARTITION_IMAGE $_flags -p $_partition -o '$_output' -w $_step_delay" \
		"$CMD_PARTITION_IMAGE" \
			$_flags \
			-p "$_partition" \
			-o "$_output" \
			${_compress:+-z "$_compress"} \
			-w "$_step_delay" \
			${_force_fs:+-f "$_force_fs"} \
			${_extra_opts:+-x "$_extra_opts"}
	_rc=$EXEC_RC
	_out="$EXEC_OUT"
	if [ "$_rc" -eq 0 ]; then
		emit_cmd_result true "$_rc" "Partition export completed successfully" "$_out"
	else
		emit_cmd_result false "$_rc" "Partition export failed" "$_out"
	fi
}

action_partclone_import() {
	_action_partition_image_common || return
	_partition=$(cgi_param partition)
	_input=$(cgi_param input_file)
	_compress=$(cgi_param compression)
	_verify=$(cgi_param verify)
	_unmount=$(cgi_param unmount_before)
	_step_delay=$(cgi_param step_delay)
	_extra_opts=$(cgi_param extra_opts)
	_dry_run=$(cgi_param dry_run)

	is_valid_device "$_partition" || { emit_json_error "Invalid partition path"; return; }
	[ -n "$_input" ] || { emit_json_error "Input image file path required"; return; }
	case "$_compress" in
		none|gzip|gz|bzip2|bz2|lz4|zstd|'') ;;
		*) emit_json_error "Invalid compression '${_compress}'"; return ;;
	esac
	case "$_step_delay" in ''|*[!0-9]*) _step_delay='1' ;; esac

	_flags='-i'
	[ "$_unmount" = 'yes' ] && _flags="$_flags -u"
	[ "$_verify"  = 'yes' ] && _flags="$_flags -V"

	if dry_run_enabled; then
		_preview="$CMD_PARTITION_IMAGE $_flags"
		_preview="$_preview -p $_partition"
		_preview="$_preview -o '$_input'"
		[ -n "$_compress" ] && [ "$_compress" != 'none' ] && _preview="$_preview -z $_compress"
		_preview="$_preview -w $_step_delay"
		[ -n "$_extra_opts" ] && _preview="$_preview -x '$_extra_opts'"
		_preview="$_preview -n"
		emit_dry_run_result "partclone import" "$_preview"
		return
	fi

	# shellcheck disable=SC2086
	exec_cmd "Import (restore) partition (partition_image.sh)" \
		"$CMD_PARTITION_IMAGE $_flags -p $_partition -o '$_input' -w $_step_delay" \
		"$CMD_PARTITION_IMAGE" \
			$_flags \
			-p "$_partition" \
			-o "$_input" \
			${_compress:+-z "$_compress"} \
			-w "$_step_delay" \
			${_extra_opts:+-x "$_extra_opts"}
	_rc=$EXEC_RC
	_out="$EXEC_OUT"
	if [ "$_rc" -eq 0 ]; then
		emit_cmd_result true "$_rc" "Partition restore completed successfully" "$_out"
	else
		emit_cmd_result false "$_rc" "Partition restore failed" "$_out"
	fi
}

action_partclone_net_send() {
	_action_partition_image_common || return
	_partition=$(cgi_param partition)
	_compress=$(cgi_param compression)
	_force_fs=$(cgi_param force_fs)
	_transport=$(cgi_param transport)
	_host=$(cgi_param net_host)
	_port=$(cgi_param net_port)
	_multicast=$(cgi_param multicast)
	_unmount=$(cgi_param unmount_before)
	_step_delay=$(cgi_param step_delay)
	_dry_run=$(cgi_param dry_run)

	is_valid_device "$_partition" || { emit_json_error "Invalid partition path"; return; }
	case "$_compress" in none|gzip|gz|bzip2|bz2|lz4|zstd|'') ;; *) emit_json_error "Invalid compression"; return ;; esac
	case "$_port" in ''|*[!0-9]*) _port='9000' ;; esac
	case "$_step_delay" in ''|*[!0-9]*) _step_delay='1' ;; esac

	_flags='-N'
	[ "$_unmount"   = 'yes' ] && _flags="$_flags -u"
	[ "$_multicast" = 'yes' ] && _flags="$_flags -m"

	if dry_run_enabled; then
		_preview="$CMD_PARTITION_IMAGE $_flags"
		_preview="$_preview -p $_partition"
		[ -n "$_host" ] && _preview="$_preview -H $_host"
		_preview="$_preview -P $_port"
		[ -n "$_compress" ] && [ "$_compress" != 'none' ] && _preview="$_preview -z $_compress"
		[ -n "$_force_fs" ]  && _preview="$_preview -f $_force_fs"
		_preview="$_preview -w $_step_delay -n"
		emit_dry_run_result "partclone network send" "$_preview"
		return
	fi

	# shellcheck disable=SC2086
	exec_cmd "Network send partition (partition_image.sh)" \
		"$CMD_PARTITION_IMAGE $_flags -p $_partition -P $_port -w $_step_delay" \
		"$CMD_PARTITION_IMAGE" \
			$_flags \
			-p "$_partition" \
			${_host:+-H "$_host"} \
			-P "$_port" \
			${_compress:+-z "$_compress"} \
			${_force_fs:+-f "$_force_fs"} \
			-w "$_step_delay"
	_rc=$EXEC_RC
	_out="$EXEC_OUT"
	if [ "$_rc" -eq 0 ]; then
		emit_cmd_result true "$_rc" "Network send completed" "$_out"
	else
		emit_cmd_result false "$_rc" "Network send failed" "$_out"
	fi
}

action_partclone_net_recv() {
	_action_partition_image_common || return
	_partition=$(cgi_param partition)
	_compress=$(cgi_param compression)
	_transport=$(cgi_param transport)
	_host=$(cgi_param net_host)
	_port=$(cgi_param net_port)
	_multicast=$(cgi_param multicast)
	_verify=$(cgi_param verify)
	_unmount=$(cgi_param unmount_before)
	_step_delay=$(cgi_param step_delay)
	_dry_run=$(cgi_param dry_run)

	is_valid_device "$_partition" || { emit_json_error "Invalid partition path"; return; }
	[ -n "$_host" ] || { emit_json_error "Source host IP required"; return; }
	case "$_compress" in none|gzip|gz|bzip2|bz2|lz4|zstd|'') ;; *) emit_json_error "Invalid compression"; return ;; esac
	case "$_port" in ''|*[!0-9]*) _port='9000' ;; esac
	case "$_step_delay" in ''|*[!0-9]*) _step_delay='1' ;; esac

	_flags='-R'
	[ "$_unmount"   = 'yes' ] && _flags="$_flags -u"
	[ "$_verify"    = 'yes' ] && _flags="$_flags -V"
	[ "$_multicast" = 'yes' ] && _flags="$_flags -m"

	if dry_run_enabled; then
		_preview="$CMD_PARTITION_IMAGE $_flags"
		_preview="$_preview -p $_partition"
		_preview="$_preview -H $_host"
		_preview="$_preview -P $_port"
		[ -n "$_compress" ] && [ "$_compress" != 'none' ] && _preview="$_preview -z $_compress"
		_preview="$_preview -w $_step_delay -n"
		emit_dry_run_result "partclone network receive" "$_preview"
		return
	fi

	# shellcheck disable=SC2086
	exec_cmd "Network receive partition (partition_image.sh)" \
		"$CMD_PARTITION_IMAGE $_flags -p $_partition -H $_host -P $_port -w $_step_delay" \
		"$CMD_PARTITION_IMAGE" \
			$_flags \
			-p "$_partition" \
			-H "$_host" \
			-P "$_port" \
			${_compress:+-z "$_compress"} \
			-w "$_step_delay"
	_rc=$EXEC_RC
	_out="$EXEC_OUT"
	if [ "$_rc" -eq 0 ]; then
		emit_cmd_result true "$_rc" "Network receive completed" "$_out"
	else
		emit_cmd_result false "$_rc" "Network receive failed" "$_out"
	fi
}

action_partclone_ddrescue() {
	_action_partition_image_common || return
	_partition=$(cgi_param partition)
	_output=$(cgi_param output_file)
	_log_file=$(cgi_param log_file)
	_retries=$(cgi_param retries)
	_unmount=$(cgi_param unmount_before)
	_step_delay=$(cgi_param step_delay)
	_extra_opts=$(cgi_param extra_opts)
	_dry_run=$(cgi_param dry_run)

	is_valid_device "$_partition" || { emit_json_error "Invalid partition path"; return; }
	[ -n "$_output" ] || { emit_json_error "Output image file path required"; return; }
	case "$_retries" in ''|*[!0-9]*) _retries='3' ;; esac
	case "$_step_delay" in ''|*[!0-9]*) _step_delay='1' ;; esac

	_flags='-G'
	[ "$_unmount" = 'yes' ] && _flags="$_flags -u"

	if dry_run_enabled; then
		_preview="$CMD_PARTITION_IMAGE $_flags"
		_preview="$_preview -p $_partition"
		_preview="$_preview -o '$_output'"
		[ -n "$_log_file" ] && _preview="$_preview -l '$_log_file'"
		_preview="$_preview -r $_retries -w $_step_delay"
		[ -n "$_extra_opts" ] && _preview="$_preview -x '$_extra_opts'"
		_preview="$_preview -n"
		emit_dry_run_result "ddrescue clone" "$_preview"
		return
	fi

	# shellcheck disable=SC2086
	exec_cmd "ddrescue clone (partition_image.sh -G)" \
		"$CMD_PARTITION_IMAGE $_flags -p $_partition -o '$_output' -r $_retries -w $_step_delay" \
		"$CMD_PARTITION_IMAGE" \
			$_flags \
			-p "$_partition" \
			-o "$_output" \
			${_log_file:+-l "$_log_file"} \
			-r "$_retries" \
			-w "$_step_delay" \
			${_extra_opts:+-x "$_extra_opts"}
	_rc=$EXEC_RC
	_out="$EXEC_OUT"
	if [ "$_rc" -eq 0 ]; then
		emit_cmd_result true "$_rc" "ddrescue completed successfully" "$_out"
	else
		emit_cmd_result false "$_rc" "ddrescue failed" "$_out"
	fi
}

action_disk_migration() {
	resolve_tools

	CMD_DISK_MIGRATION=$(find_cmd disk_migration.sh)
	[ -n "$CMD_DISK_MIGRATION" ] || { emit_json_error "disk_migration.sh not found in PATH"; return; }

	_source_device=$(cgi_param source_device)
	_target_device=$(cgi_param target_device)
	_move_mode=$(cgi_param move_mode)
	_physical_mode=$(cgi_param physical_mode)
	_include_tail=$(cgi_param include_tail)
	_clone_mode=$(cgi_param clone_mode)
	_align_bytes=$(cgi_param align_bytes)
	_copy_mbr=$(cgi_param copy_mbr)
	_wipe_target=$(cgi_param wipe_target)
	_unmount_before=$(cgi_param unmount_before)
	_verify_clone=$(cgi_param verify_clone)
	_extra_opts=$(cgi_param extra_opts)
	_step_delay=$(cgi_param step_delay)
	_force_fs=$(cgi_param force_fs)
	_dry_run=$(cgi_param dry_run)

	is_valid_device "$_source_device" || { emit_json_error "Invalid source device path"; return; }
	is_valid_device "$_target_device" || { emit_json_error "Invalid target device path"; return; }
	[ "$_source_device" = "$_target_device" ] && { emit_json_error "Source and target device must be different"; return; }

	case "$_align_bytes" in
		512|4096|1048576) ;;
		'') _align_bytes='1048576' ;;
		*) emit_json_error "Invalid alignment '${_align_bytes}'"; return ;;
	esac
	case "$_clone_mode" in
		smart|dd) ;;
		'') _clone_mode='smart' ;;
		*) emit_json_error "Invalid clone mode '${_clone_mode}'"; return ;;
	esac
	case "$_step_delay" in
		''|*[!0-9]*) _step_delay='1' ;;
	esac

	_flags=''
	[ "$_move_mode"      = 'yes' ] && _flags="$_flags -M"
	[ "$_physical_mode"  = 'yes' ] && _flags="$_flags -P"
	[ "$_include_tail"   = 'yes' ] && _flags="$_flags -T"
	[ "$_copy_mbr"       = 'yes' ] && _flags="$_flags -B"
	[ "$_wipe_target"    = 'yes' ] && _flags="$_flags -W"
	[ "$_unmount_before" = 'yes' ] && _flags="$_flags -u"
	[ "$_verify_clone"   = 'yes' ] && _flags="$_flags -V"
	[ "$_dry_run"        = 'yes' ] && _flags="$_flags -r"

	if dry_run_enabled; then
		_preview="$CMD_DISK_MIGRATION"
		_preview="$_preview -D $_source_device"
		_preview="$_preview -d $_target_device"
		[ "$_physical_mode" != 'yes' ] && {
			_preview="$_preview -c $_clone_mode"
			_preview="$_preview -a $_align_bytes"
		}
		_preview="$_preview -w $_step_delay"
		_preview="$_preview $_flags"
		[ -n "$_force_fs" ]   && _preview="$_preview -f $_force_fs"
		[ -n "$_extra_opts" ] && _preview="$_preview -x '$_extra_opts'"
		_preview="$_preview -r"
		emit_dry_run_result "disk migration" "$_preview"
		return
	fi

	# shellcheck disable=SC2086
	exec_cmd "Disk migration (disk_migration.sh)" \
		"$CMD_DISK_MIGRATION -D $_source_device -d $_target_device -c $_clone_mode -a $_align_bytes -w $_step_delay $_flags" \
		"$CMD_DISK_MIGRATION" \
			-D "$_source_device" \
			-d "$_target_device" \
			-c "$_clone_mode" \
			-a "$_align_bytes" \
			-w "$_step_delay" \
			${_flags} \
			${_force_fs:+-f "$_force_fs"} \
			${_extra_opts:+-x "$_extra_opts"}
	_rc=$EXEC_RC
	_out="$EXEC_OUT"

	if [ "$_rc" -eq 0 ]; then
		emit_cmd_result true "$_rc" "Disk migration completed successfully" "$_out"
	else
		emit_cmd_result false "$_rc" "Disk migration failed" "$_out"
	fi
}

action_mount_partition() {
	resolve_tools
	_partition=$(cgi_param partition)
	_device=$(cgi_param device)
	_target_partnum=$(cgi_param target_partnum)
	_target_start_sector=$(cgi_param target_start_sector)
	_target_end_sector=$(cgi_param target_end_sector)
	_mountpoint=$(cgi_param mountpoint)
	_fs_type=$(cgi_param fs_type)
	_mount_opts=$(cgi_param mount_opts)
	_fs_type=$(normalize_mount_fs_type "$_fs_type")

	[ -n "$CMD_MOUNT" ] || { emit_json_error "mount command not available"; return; }
	if [ -z "$_partition" ] && [ -n "$_device" ]; then
		is_valid_device "$_device" || { emit_json_error "Invalid target device"; return; }
		if [ -n "$_target_partnum" ]; then
			is_valid_partnum "$_target_partnum" || { emit_json_error "Invalid target partition number"; return; }
			_partition=$(partition_path "$_device" "$_target_partnum")
		elif [ -n "$_target_start_sector" ] && [ -n "$_target_end_sector" ]; then
			is_valid_sector "$_target_start_sector" || { emit_json_error "Invalid target start sector"; return; }
			is_valid_sector "$_target_end_sector" || { emit_json_error "Invalid target end sector"; return; }
			_target_partnum=$(partition_number_by_range "$_device" "$_target_start_sector" "$_target_end_sector")
			is_valid_partnum "$_target_partnum" || { emit_json_error "Target partition not found for mount"; return; }
			_partition=$(partition_path "$_device" "$_target_partnum")
		fi
	fi
	is_valid_device "$_partition" || { emit_json_error "Invalid partition path"; return; }
	is_valid_extra_opts "$_mount_opts" || { emit_json_error "Invalid mount options"; return; }

	if [ -z "$_mountpoint" ]; then
		_base=$(basename "$_partition")
		_mountpoint="/var/media/ftp/$_base"
	fi

	is_valid_mountpoint "$_mountpoint" || { emit_json_error "Invalid mountpoint"; return; }

	if dry_run_enabled; then
		if [ -n "$_fs_type" ] && [ "$_fs_type" != "auto" ]; then
			if [ -n "$_mount_opts" ]; then
				_preview_cmd="mount -t $_fs_type -o $_mount_opts $_partition $_mountpoint"
			else
				_preview_cmd="mount -t $_fs_type $_partition $_mountpoint"
			fi
		else
			if [ -n "$_mount_opts" ]; then
				_preview_cmd="mount -o $_mount_opts $_partition $_mountpoint"
			else
				_preview_cmd="mount $_partition $_mountpoint"
			fi
		fi
		emit_dry_run_result "mount partition" "mkdir -p $_mountpoint
$_preview_cmd"
		return
	fi

	_already=$(awk -v p="$_partition" '$1 == p { print $2; exit }' /proc/mounts 2>/dev/null)
	if [ -n "$_already" ]; then
		if [ "$_already" = "$_mountpoint" ]; then
			emit_cmd_result true 0 "Partition already mounted" "$_partition is already mounted on $_already"
			return
		fi
		# Mounted at wrong path (e.g. udev automount) — unmount then remount at requested path
		umount "$_already" 2>/dev/null
		sleep 1
		_still=$(awk -v p="$_partition" '$1 == p { print $2; exit }' /proc/mounts 2>/dev/null)
		if [ -n "$_still" ]; then
			emit_cmd_result true 0 "Partition already mounted" "$_partition is mounted on $_still (could not remount to $_mountpoint)"
			return
		fi
	fi

	mkdir -p "$_mountpoint" 2>/dev/null
	if [ ! -d "$_mountpoint" ]; then
		emit_json_error "Unable to create mountpoint"
		return
	fi

	if [ -n "$_fs_type" ] && [ "$_fs_type" != "auto" ]; then
		if [ -n "$_mount_opts" ]; then
			_cmd_disp="$CMD_MOUNT -t $_fs_type -o $_mount_opts $_partition $_mountpoint"
			exec_cmd_c "mount" "$_cmd_disp" "$CMD_MOUNT" -t "$_fs_type" -o "$_mount_opts" "$_partition" "$_mountpoint"
		else
			_cmd_disp="$CMD_MOUNT -t $_fs_type $_partition $_mountpoint"
			exec_cmd_c "mount" "$_cmd_disp" "$CMD_MOUNT" -t "$_fs_type" "$_partition" "$_mountpoint"
		fi
	else
		if [ -n "$_mount_opts" ]; then
			_cmd_disp="$CMD_MOUNT -o $_mount_opts $_partition $_mountpoint"
			exec_cmd_c "mount" "$_cmd_disp" "$CMD_MOUNT" -o "$_mount_opts" "$_partition" "$_mountpoint"
		else
			_cmd_disp="$CMD_MOUNT $_partition $_mountpoint"
			exec_cmd_c "mount" "$_cmd_disp" "$CMD_MOUNT" "$_partition" "$_mountpoint"
		fi
	fi
	_rc=$EXEC_RC; _out="$EXEC_OUT"

	if [ "$_rc" -eq 0 ]; then
		_now=$(awk -v p="$_partition" '$1 == p { print $2; exit }' /proc/mounts 2>/dev/null)
		emit_cmd_result true "$_rc" "Partition mounted" "$_out Mountpoint: ${_now:-$_mountpoint}"
	else
		emit_cmd_result false "$_rc" "Mount failed" "$_out"
	fi
}

action_unmount_partition() {
	resolve_tools
	if ! require_ack; then
		emit_json_error "Dangerous operation blocked: type YES_I_UNDERSTAND first"
		return
	fi

	_partition=$(cgi_param partition)
	_mountpoint=$(cgi_param mountpoint)

	[ -n "$CMD_UMOUNT" ] || { emit_json_error "umount command not available"; return; }

	if [ -n "$_partition" ]; then
		is_valid_device "$_partition" || { emit_json_error "Invalid partition path"; return; }
		_target="$_partition"
	elif [ -n "$_mountpoint" ]; then
		is_valid_mountpoint "$_mountpoint" || { emit_json_error "Invalid mountpoint"; return; }
		_target="$_mountpoint"
	else
		emit_json_error "partition or mountpoint is required"
		return
	fi

	if dry_run_enabled; then
		emit_dry_run_result "unmount" "umount $_target"
		return
	fi

	# Keep unmount idempotent so orchestrated queues can always start with this step.
	if [ -n "$_partition" ]; then
		_is_mounted=$(awk -v p="$_partition" '$1 == p { print 1; exit }' /proc/mounts 2>/dev/null)
		if [ "$_is_mounted" != "1" ]; then
			emit_cmd_result true 0 "Partition already unmounted" "$_partition is not mounted"
			return
		fi
	elif [ -n "$_mountpoint" ]; then
		_is_mounted=$(awk -v m="$_mountpoint" '$2 == m { print 1; exit }' /proc/mounts 2>/dev/null)
		if [ "$_is_mounted" != "1" ]; then
			emit_cmd_result true 0 "Mountpoint already unmounted" "$_mountpoint is not mounted"
			return
		fi
	fi

	exec_cmd_c "Unmount $_target" "$CMD_UMOUNT $_target" "$CMD_UMOUNT" "$_target"
	_rc=$EXEC_RC; _out="$EXEC_OUT"

	if [ "$_rc" -eq 0 ]; then
		emit_cmd_result true "$_rc" "Unmount completed" "$_out"
	else
		emit_cmd_result false "$_rc" "Unmount failed" "$_out"
	fi
}

action_partition_metadata() {
	resolve_tools
	_partition=$(cgi_param partition)
	_device=$(cgi_param device)
	_partnum=$(cgi_param partnum)

	is_valid_device "$_partition" || { emit_json_error "Invalid partition path"; return; }

	if [ -z "$_partnum" ] && [ -n "$CMD_LSBLK" ]; then
		_partnum=$($CMD_LSBLK -ln -o PARTN "$_partition" 2>/dev/null | head -n 1)
	fi
	if ! is_valid_partnum "$_partnum"; then
		_partnum=''
	fi

	if [ -z "$_device" ] && [ -n "$CMD_LSBLK" ]; then
		_parent=$($CMD_LSBLK -ln -o PKNAME "$_partition" 2>/dev/null | head -n 1)
		if [ -n "$_parent" ] && [ -b "/dev/$_parent" ]; then
			_device="/dev/$_parent"
		fi
	fi

	if [ -n "$_device" ]; then
		is_valid_device "$_device" || { emit_json_error "Invalid device path"; return; }
	fi

	_fstype=''
	if [ -n "$CMD_BLKID" ]; then
		_fstype=$($CMD_BLKID -o value -s TYPE "$_partition" 2>/dev/null | head -n 1)
	fi
	_label=''
	if [ -n "$CMD_LSBLK" ]; then
		_label=$($CMD_LSBLK -ln -o LABEL "$_partition" 2>/dev/null | head -n 1)
	fi
	if [ -z "$_label" ] && [ -n "$CMD_BLKID" ]; then
		_label=$($CMD_BLKID -o value -s LABEL "$_partition" 2>/dev/null | head -n 1)
	fi

	_mountpoint=$(awk -v p="$_partition" '$1 == p { print $2; exit }' /proc/mounts 2>/dev/null)
	_size_bytes='0'
	_fs_size_bytes='0'
	_fs_used_bytes='0'
	_fs_avail_bytes='0'
	_part_name=''
	_part_flags=''
	if [ -n "$CMD_LSBLK" ]; then
		_size_bytes=$(safe_uint "$($CMD_LSBLK -bn -o SIZE "$_partition" 2>/dev/null | head -n 1)")
		_fs_size_bytes=$(safe_uint "$($CMD_LSBLK -bn -o FSSIZE "$_partition" 2>/dev/null | head -n 1)")
		_fs_used_bytes=$(safe_uint "$($CMD_LSBLK -bn -o FSUSED "$_partition" 2>/dev/null | head -n 1)")
		_fs_avail_bytes=$(safe_uint "$($CMD_LSBLK -bn -o FSAVAIL "$_partition" 2>/dev/null | head -n 1)")
	fi
	if [ -z "$_mountpoint" ] && { [ "$_fs_size_bytes" -eq 0 ] || { [ "$_fs_used_bytes" -eq 0 ] && [ "$_fs_avail_bytes" -eq 0 ]; }; }; then
		_fallback_usage=$(get_unmounted_fs_usage "$_partition" "$_fstype" "$_mountpoint")
		if [ -n "$_fallback_usage" ]; then
			set -- $_fallback_usage
			_fs_size_bytes=$(safe_uint "$1")
			_fs_used_bytes=$(safe_uint "$2")
			_fs_avail_bytes=$(safe_uint "$3")
		fi
	fi

	_dev_path="$_device"
	_dev_name=''
	_dev_sys=''
	if [ -n "$_dev_path" ]; then
		_dev_name=$(basename "$_dev_path")
		_dev_sys="/sys/class/block/$_dev_name"
	fi

	_dev_model=''
	_dev_serial=''
	_dev_partition_table=''
	_dev_size_bytes='0'
	_dev_total_sectors='0'
	_dev_sector_size_bytes='0'
	_dev_heads='0'
	_dev_sectors_track='0'
	_dev_cylinders='0'

	if [ -n "$_dev_sys" ] && [ -r "$_dev_sys/device/model" ]; then
		_dev_model=$(cat "$_dev_sys/device/model" 2>/dev/null | tr -d '\r\n')
	fi
	if [ -n "$_dev_sys" ] && [ -r "$_dev_sys/device/serial" ]; then
		_dev_serial=$(cat "$_dev_sys/device/serial" 2>/dev/null | tr -d '\r\n')
	fi

	if [ -n "$CMD_LSBLK" ] && [ -n "$_dev_path" ]; then
		[ -n "$_dev_model" ] || _dev_model=$($CMD_LSBLK -dn -o MODEL "$_dev_path" 2>/dev/null | head -n 1)
		[ -n "$_dev_serial" ] || _dev_serial=$($CMD_LSBLK -dn -o SERIAL "$_dev_path" 2>/dev/null | head -n 1)
		_dev_size_bytes=$(safe_uint "$($CMD_LSBLK -bn -o SIZE "$_dev_path" 2>/dev/null | head -n 1)")
		[ -n "$_dev_partition_table" ] || _dev_partition_table=$($CMD_LSBLK -dn -o PTTYPE "$_dev_path" 2>/dev/null | head -n 1)
	fi

	if [ -n "$_dev_sys" ] && [ -r "$_dev_sys/size" ]; then
		_dev_total_sectors=$(safe_uint "$(cat "$_dev_sys/size" 2>/dev/null)")
	fi
	if [ -n "$_dev_sys" ] && [ -r "$_dev_sys/queue/logical_block_size" ]; then
		_dev_sector_size_bytes=$(safe_uint "$(cat "$_dev_sys/queue/logical_block_size" 2>/dev/null)")
	fi

	if [ -n "$CMD_PARTED" ] && [ -n "$_dev_path" ]; then
		_dev_map_meta=$($CMD_PARTED -s -m "$_dev_path" unit s print free 2>/dev/null)
		_dev_header=$(printf '%s\n' "$_dev_map_meta" | sed -n '2p')
		if [ -n "$_dev_header" ]; then
			_old_ifs=$IFS
			IFS=':'
			set -- $_dev_header
			IFS=$_old_ifs
			_tmp_total=$(safe_uint "${2%s}")
			_tmp_lsize=$(safe_uint "$4")
			[ -n "$_dev_partition_table" ] || _dev_partition_table="$6"
			[ "$_dev_total_sectors" -gt 0 ] || _dev_total_sectors="$_tmp_total"
			[ "$_dev_sector_size_bytes" -gt 0 ] || _dev_sector_size_bytes="$_tmp_lsize"
		fi
		if [ -n "$_partnum" ]; then
			_part_lines_meta=$(printf '%s\n' "$_dev_map_meta" | sed -n '3,$p')
			while IFS= read -r _pline; do
				[ -n "$_pline" ] || continue
				_pline=${_pline%;}
				_old_ifs=$IFS
				IFS=':'
				set -- $_pline
				IFS=$_old_ifs
				_pid="$1"
				if [ "$_pid" = "$_partnum" ]; then
					_part_name="$6"
					_part_flags="$7"
					break
				fi
			done <<EOF
$_part_lines_meta
EOF
		fi
	fi

	if [ -n "$_dev_sys" ] && [ -r "$_dev_sys/device/heads" ]; then
		_dev_heads=$(safe_uint "$(cat "$_dev_sys/device/heads" 2>/dev/null)")
	fi
	if [ -n "$_dev_sys" ] && [ -r "$_dev_sys/device/sectors" ]; then
		_dev_sectors_track=$(safe_uint "$(cat "$_dev_sys/device/sectors" 2>/dev/null)")
	fi
	if [ -n "$_dev_sys" ] && [ -r "$_dev_sys/device/cylinders" ]; then
		_dev_cylinders=$(safe_uint "$(cat "$_dev_sys/device/cylinders" 2>/dev/null)")
	fi

	if [ -n "$CMD_HDPARM" ] && [ -n "$_dev_path" ] && { [ "$_dev_heads" -eq 0 ] || [ "$_dev_sectors_track" -eq 0 ] || [ "$_dev_cylinders" -eq 0 ]; }; then
		_geom_line=$($CMD_HDPARM -g "$_dev_path" 2>/dev/null | sed -n 's/.*geometry[[:space:]]*=[[:space:]]*\([0-9][0-9]*\)\/\([0-9][0-9]*\)\/\([0-9][0-9]*\).*/\1 \2 \3/p' | head -n 1)
		if [ -n "$_geom_line" ]; then
			_g_cyl=$(safe_uint "$(printf '%s\n' "$_geom_line" | awk '{print $1}')")
			_g_heads=$(safe_uint "$(printf '%s\n' "$_geom_line" | awk '{print $2}')")
			_g_spt=$(safe_uint "$(printf '%s\n' "$_geom_line" | awk '{print $3}')")
			[ "$_dev_cylinders" -gt 0 ] || _dev_cylinders="$_g_cyl"
			[ "$_dev_heads" -gt 0 ] || _dev_heads="$_g_heads"
			[ "$_dev_sectors_track" -gt 0 ] || _dev_sectors_track="$_g_spt"
		fi
	fi

	if [ "$_dev_total_sectors" -eq 0 ] && [ "$_dev_size_bytes" -gt 0 ] && [ "$_dev_sector_size_bytes" -gt 0 ]; then
		_dev_total_sectors=$(safe_uint "$(awk -v b="$_dev_size_bytes" -v s="$_dev_sector_size_bytes" 'BEGIN { if (s > 0) printf "%.0f", b / s; else print 0 }')")
	fi
	if [ "$_dev_size_bytes" -eq 0 ] && [ "$_dev_total_sectors" -gt 0 ] && [ "$_dev_sector_size_bytes" -gt 0 ]; then
		_dev_size_bytes=$(safe_uint "$(awk -v t="$_dev_total_sectors" -v s="$_dev_sector_size_bytes" 'BEGIN { printf "%.0f", t * s }')")
	fi
	if [ "$_dev_cylinders" -eq 0 ] && [ "$_dev_heads" -gt 0 ] && [ "$_dev_sectors_track" -gt 0 ] && [ "$_dev_total_sectors" -gt 0 ]; then
		_dev_cylinders=$(safe_uint "$(awk -v t="$_dev_total_sectors" -v h="$_dev_heads" -v s="$_dev_sectors_track" 'BEGIN { printf "%.0f", t / (h * s) }')")
	fi

	_used_human=$(human_bytes_sh "$_fs_used_bytes")
	_unused_human=$(human_bytes_sh "$_fs_avail_bytes")

	_sources=''
	_first_src=1
	add_source() {
		_s_cmd="$1"
		_s_out="$2"
		if [ "$_first_src" -eq 0 ]; then
			_sources="$_sources,"
		fi
		_first_src=0
		_sources="$_sources{\"command\":\"$(json_escape "$_s_cmd")\",\"output\":\"$(json_escape "$_s_out")\"}"
	}

	if [ -n "$CMD_LSBLK" ]; then
		_lsblk_out=$($CMD_LSBLK -P -b -o NAME,KNAME,PKNAME,TYPE,PATH,FSTYPE,PARTTYPENAME,PARTLABEL,PARTUUID,UUID,LABEL,SIZE,FSSIZE,FSUSED,FSAVAIL,FSUSE%,MOUNTPOINT "$_partition" 2>&1)
		add_source "$CMD_LSBLK -P -b -o ... $_partition" "$_lsblk_out"
	fi

	if [ -n "$CMD_BLKID" ]; then
		_blkid_out=$($CMD_BLKID -p -o export "$_partition" 2>&1)
		add_source "$CMD_BLKID -p -o export $_partition" "$_blkid_out"
	fi

	if [ -n "$CMD_PARTED" ] && [ -n "$_device" ]; then
		_parted_out=$($CMD_PARTED -s -m "$_device" unit s print free 2>&1)
		add_source "$CMD_PARTED -s -m $_device unit s print free" "$_parted_out"
		if [ -n "$_partnum" ]; then
			_align_out=$($CMD_PARTED -s "$_device" align-check optimal "$_partnum" 2>&1)
			add_source "$CMD_PARTED -s $_device align-check optimal $_partnum" "$_align_out"
		fi
	fi

	case "$_fstype" in
		ext2|ext3|ext4)
			if [ -n "$CMD_TUNE2FS" ]; then
				_ext_out=$(run_tune2fs -l "$_partition" 2>&1)
				_t2_rc=$?
				[ "$_t2_rc" -eq 139 ] && _ext_out="[tune2fs: Segmentation fault (SIGSEGV) - binary crashed on this platform]"
				_ext_out=$(printf '%s' "$_ext_out" | head -n 260)
				add_source "$CMD_TUNE2FS -l $_partition" "$_ext_out"
			fi
			;;
		fat|fat12|fat16|fat32|vfat)
			if [ -n "$CMD_FSCK_FAT" ]; then
				_fat_out=$($CMD_FSCK_FAT -v -n "$_partition" 2>&1 | sed -n '1,260p')
				add_source "$CMD_FSCK_FAT -v -n $_partition" "$_fat_out"
			fi
			;;
		exfat)
			if [ -n "$CMD_FSCK_EXFAT" ]; then
				_exfat_out=$($CMD_FSCK_EXFAT -n "$_partition" 2>&1 | sed -n '1,260p')
				add_source "$CMD_FSCK_EXFAT -n $_partition" "$_exfat_out"
			fi
			;;
		ntfs)
			if [ -n "$CMD_NTFSINFO" ]; then
				_ntfs_out=$($CMD_NTFSINFO -m "$_partition" 2>&1 | sed -n '1,260p')
				add_source "$CMD_NTFSINFO -m $_partition" "$_ntfs_out"
			elif [ -n "$CMD_NTFSFIX" ]; then
				_ntfs_out=$($CMD_NTFSFIX -n "$_partition" 2>&1 | sed -n '1,260p')
				add_source "$CMD_NTFSFIX -n $_partition" "$_ntfs_out"
			fi
			;;
	esac

	echo "{\"success\": true, \"partition\": \"$(json_escape "$_partition")\", \"device\": \"$(json_escape "$_device")\", \"partnum\": \"$(json_escape "$_partnum")\", \"partition_name\": \"$(json_escape "$_part_name")\", \"flags\": \"$(json_escape "$_part_flags")\", \"label\": \"$(json_escape "$_label")\", \"fstype\": \"$(json_escape "$_fstype")\", \"filesystem_type\": \"$(json_escape "$_fstype")\", \"mountpoint\": \"$(json_escape "$_mountpoint")\", \"mount_point\": \"$(json_escape "$_mountpoint")\", \"size_bytes\": $_size_bytes, \"fs_size_bytes\": $_fs_size_bytes, \"fs_used_bytes\": $_fs_used_bytes, \"fs_avail_bytes\": $_fs_avail_bytes, \"used_human\": \"$(json_escape "$_used_human")\", \"unused_human\": \"$(json_escape "$_unused_human")\", \"device_info\": {\"path\": \"$(json_escape "$_dev_path")\", \"model\": \"$(json_escape "$_dev_model")\", \"serial\": \"$(json_escape "$_dev_serial")\", \"size_bytes\": $_dev_size_bytes, \"partition_table\": \"$(json_escape "$_dev_partition_table")\", \"heads\": $_dev_heads, \"sectors_per_track\": $_dev_sectors_track, \"cylinders\": $_dev_cylinders, \"total_sectors\": $_dev_total_sectors, \"sector_size_bytes\": $_dev_sector_size_bytes}, \"sources\": [$_sources]}"
}

action_reload_table() {
	resolve_tools
	_device=$(cgi_param device)
	is_valid_device "$_device" || { emit_json_error "Invalid device"; return; }

	if [ -z "$CMD_PARTPROBE" ]; then
		emit_json_error "partprobe command not available"
		return
	fi

	if dry_run_enabled; then
		emit_dry_run_result "reload partition table" "partprobe $_device"
		return
	fi

	exec_cmd_c "Reload partition table (partprobe)" "$CMD_PARTPROBE $_device" \
		"$CMD_PARTPROBE" "$_device"
	_rc=$EXEC_RC; _out="$EXEC_OUT"
	if [ "$_rc" -eq 139 ]; then
		# SIGSEGV with device arg: retry without argument
		exec_cmd_c "Reload partition table (partprobe, no-arg retry)" "$CMD_PARTPROBE" "$CMD_PARTPROBE"
		_rc2=$EXEC_RC; _out2="$EXEC_OUT"
		_out="$_out\n[retry without device] rc=$_rc2\n$_out2"
		[ "$_rc2" -eq 0 ] && _rc=0
	fi
	if [ "$_rc" -ne 0 ]; then
		# Last resort: blockdev --rereadpt
		if [ -n "$CMD_BLOCKDEV" ]; then
			exec_cmd_c "Reload partition table (blockdev --rereadpt)" "$CMD_BLOCKDEV --rereadpt $_device" \
				"$CMD_BLOCKDEV" --rereadpt "$_device"
			_rc3=$EXEC_RC; _out3="$EXEC_OUT"
			_out="$_out\n[blockdev --rereadpt] rc=$_rc3\n$_out3"
			[ "$_rc3" -eq 0 ] && _rc=0
		fi
	fi
	if [ "$_rc" -eq 0 ]; then
		emit_cmd_result true "$_rc" "Kernel partition table refreshed" "$_out"
	else
		emit_cmd_result false "$_rc" "partprobe failed" "$_out"
	fi
}

action_smart_info() {
	resolve_tools
	_device=$(cgi_param device)
	is_valid_device "$_device" || { emit_json_error "Invalid device"; return; }
	[ -n "$CMD_SMARTCTL" ] || { emit_json_error "smartctl not available"; return; }

	if dry_run_enabled; then
		emit_dry_run_result "smart diagnostics" "smartctl --xall $_device\n# fallback for USB/SAT bridges: smartctl -d sat,auto -T permissive -x $_device\n# info-only fallback: smartctl -d sat,auto -T permissive -i $_device"
		return
	fi

	_smart_has_info() {
		echo "$1" | grep -Eq 'START OF INFORMATION SECTION|Device Model:|Vendor:|Model Family:|User Capacity:|Serial Number:|SMART support is'
	}

	_smart_needs_fallback() {
		echo "$1" | grep -Eq 'INVALID ARGUMENT TO -l|VALID ARGUMENTS ARE:|Use smartctl -h|Smartctl open device: .* failed'
	}

	_smart_cmd_used="--xall"
	exec_cmd_c "SMART info (smartctl --xall)" "$CMD_SMARTCTL --xall $_device" \
		/bin/sh -c "$CMD_SMARTCTL --xall '$_device' 2>&1 | sed -n '1,220p'"
	_rc=$EXEC_RC; _out="$EXEC_OUT"

	if _smart_needs_fallback "$_out" || { [ "$_rc" -ne 0 ] && ! _smart_has_info "$_out"; }; then
		_smart_cmd_used='-d sat,auto -T permissive -x'
		exec_cmd_c "SMART info (smartctl -d sat,auto)" "$CMD_SMARTCTL -d sat,auto -T permissive -x $_device" \
			/bin/sh -c "$CMD_SMARTCTL -d sat,auto -T permissive -x '$_device' 2>&1 | sed -n '1,220p'"
		_rc=$EXEC_RC; _out="$EXEC_OUT"
	fi

	if [ "$_rc" -ne 0 ] && ! _smart_has_info "$_out"; then
		_smart_cmd_used='-d sat,auto -T permissive -i'
		exec_cmd_c "SMART info (smartctl -i)" "$CMD_SMARTCTL -d sat,auto -T permissive -i $_device" \
			/bin/sh -c "$CMD_SMARTCTL -d sat,auto -T permissive -i '$_device' 2>&1 | sed -n '1,220p'"
		_rc=$EXEC_RC; _out="$EXEC_OUT"
	fi

	if [ -n "$_out" ] && { _smart_has_info "$_out" || [ "$_rc" -eq 0 ]; }; then
		emit_cmd_result true "$_rc" "SMART report collected (smartctl $_smart_cmd_used $_device)" "$_out"
	else
		emit_cmd_result false "$_rc" "SMART report failed (smartctl $_smart_cmd_used $_device)" "$_out"
	fi
}

action_smart_selftest_short() {
	resolve_tools
	_device=$(cgi_param device)
	is_valid_device "$_device" || { emit_json_error "Invalid device"; return; }
	[ -n "$CMD_SMARTCTL" ] || { emit_json_error "smartctl not available"; return; }

	if dry_run_enabled; then
		emit_dry_run_result "SMART short self-test" "smartctl -t short $_device\n# wait for completion, then:\nsmartctl -l selftest $_device"
		return
	fi

	exec_cmd_c "SMART start short self-test" "$CMD_SMARTCTL -t short $_device" \
		"$CMD_SMARTCTL" -t short "$_device"
	_start_rc=$EXEC_RC
	_out="$EXEC_OUT"

	if [ "$_start_rc" -ne 0 ] && ! echo "$_out" | grep -qiE 'Self-test|self test'; then
		emit_cmd_result false "$_start_rc" "Failed to start SMART short self-test" "$_out"
		return
	fi

	# Extract estimated duration from smartctl output
	_wait_sec=120
	_min=$(echo "$_out" | grep -oE '[0-9]+ minute' | grep -oE '[0-9]+' | head -1)
	[ -n "$_min" ] && _wait_sec=$((_min * 60 + 15))
	[ "$_wait_sec" -gt 600 ] && _wait_sec=600

	# Poll until test completes or timeout
	_elapsed=0
	_interval=10
	_max_wait=$((_wait_sec + 60))
	while [ "$_elapsed" -lt "$_max_wait" ]; do
		sleep "$_interval"
		_elapsed=$((_elapsed + _interval))
		_poll=$("$CMD_SMARTCTL" -l selftest "$_device" 2>&1)
		if echo "$_poll" | grep -qE '#1.*Completed|#1.*Failed|#1.*Aborted|#1.*Interrupted'; then
			break
		fi
		echo "$_poll" | grep -qE 'progress|remaining' || break
	done

	exec_cmd_c "SMART self-test results" "$CMD_SMARTCTL -l selftest $_device" \
		"$CMD_SMARTCTL" -l selftest "$_device"
	_full_out="$_out\n$EXEC_OUT"

	if echo "$EXEC_OUT" | grep -qE 'Completed without error'; then
		emit_cmd_result true 0 "SMART short self-test: Completed without error" "$_full_out"
	elif echo "$EXEC_OUT" | grep -qE '#1.*Failed'; then
		emit_cmd_result false 1 "SMART short self-test: FAILED" "$_full_out"
	else
		emit_cmd_result true "$EXEC_RC" "SMART short self-test results" "$_full_out"
	fi
}

action_badblocks_scan() {
	resolve_tools
	_device=$(cgi_param device)
	is_valid_device "$_device" || { emit_json_error "Invalid device"; return; }
	[ -n "$CMD_BADBLOCKS" ] || { emit_json_error "badblocks not available"; return; }

	if dry_run_enabled; then
		emit_dry_run_result "badblocks read-only scan" "badblocks -sv '$_device'"
		return
	fi

	exec_cmd_c "badblocks read-only scan" "$CMD_BADBLOCKS -sv $_device" \
		"$CMD_BADBLOCKS" -sv "$_device"
	_rc=$EXEC_RC
	if [ "$_rc" -eq 0 ]; then
		emit_cmd_result true "$_rc" "Badblocks scan: no bad blocks found" "$EXEC_OUT"
	else
		emit_cmd_result false "$_rc" "Badblocks scan: bad blocks detected or error" "$EXEC_OUT"
	fi
}

action_hdparm_info() {
	resolve_tools
	_device=$(cgi_param device)
	is_valid_device "$_device" || { emit_json_error "Invalid device"; return; }
	[ -n "$CMD_HDPARM" ] || { emit_json_error "hdparm not available"; return; }

	if dry_run_enabled; then
		emit_dry_run_result "hdparm identify" "hdparm -I $_device"
		return
	fi

	exec_cmd_c "hdparm identify $_device" "$CMD_HDPARM -I $_device" \
		/bin/sh -c "$CMD_HDPARM -I '$_device' 2>&1 | sed -n '1,220p'"
	_rc=$EXEC_RC; _out="$EXEC_OUT"
	if [ -n "$_out" ]; then
		emit_cmd_result true "$_rc" "hdparm identify collected" "$_out"
	else
		emit_cmd_result false "$_rc" "hdparm identify failed" "$_out"
	fi
}

action_gpt_info() {
	resolve_tools
	_device=$(cgi_param device)
	is_valid_device "$_device" || { emit_json_error "Invalid device"; return; }

	if dry_run_enabled; then
		emit_dry_run_result "gpt diagnostics" "# backend uses sgdisk -p or gdisk -l depending on availability"
		return
	fi

	if [ -n "$CMD_SGDISK" ]; then
		exec_cmd_c "GPT info (sgdisk)" "$CMD_SGDISK -p $_device" \
			/bin/sh -c "$CMD_SGDISK -p '$_device' 2>&1 | sed -n '1,220p'"
		_rc=$EXEC_RC; _out="$EXEC_OUT"
		_msg='sgdisk GPT summary collected'
	elif [ -n "$CMD_GDISK" ]; then
		exec_cmd_c "GPT info (gdisk)" "$CMD_GDISK -l $_device" \
			/bin/sh -c "$CMD_GDISK -l '$_device' 2>&1 | sed -n '1,220p'"
		_rc=$EXEC_RC; _out="$EXEC_OUT"
		_msg='gdisk GPT summary collected'
	else
		emit_json_error "Neither sgdisk nor gdisk is available"
		return
	fi

	if [ -n "$_out" ]; then
		emit_cmd_result true "$_rc" "$_msg" "$_out"
	else
		emit_cmd_result false "$_rc" "GPT summary failed" "$_out"
	fi
}

# ── Streaming job management ──────────────────────────────────────────────────

# Remove stale job files older than 1 hour
_cleanup_stale_jobs() {
	for _stale in /tmp/disk-mgmt-job-*.done; do
		[ -f "$_stale" ] || continue
		_stale_base="${_stale%.done}"
		# Check age via find; remove if older than 60 min
		find "$_stale" -mmin +60 -exec rm -f "$_stale_base.log" "$_stale_base.done" "$_stale_base.pid" \; 2>/dev/null
	done
}

action_start_job() {
	_cleanup_stale_jobs
	_real_action=$(cgi_param job_cmd)
	[ -n "$_real_action" ] || { emit_json_error "job_cmd required"; return; }
	_token="$(date +%s 2>/dev/null || echo 0)$$"
	_token=$(printf '%s' "$_token" | tr -cd '0-9')
	[ -n "$_token" ] || _token="0$$"
	_slog="/tmp/disk-mgmt-job-${_token}.log"
	_sdone="/tmp/disk-mgmt-job-${_token}.done"
	_spid="/tmp/disk-mgmt-job-${_token}.pid"
	backend_log "JOB START: $_real_action token=$_token"
	: > "$_slog"
	(
		set +x
		STREAM_LOG="$_slog"
		STREAM_DONE="$_sdone"
		ACTION="$_real_action"
		case "$ACTION" in
			create_partition)    action_create_partition ;;
			delete_partition)    action_delete_partition ;;
			resize_partition)    action_resize_partition ;;
			resize_filesystem)   action_resize_filesystem ;;
			create_filesystem)   action_create_filesystem ;;
			check_filesystem)    action_check_filesystem ;;
			set_label)           action_set_label ;;
			set_partition_name)  action_set_partition_name ;;
			set_partition_flag)  action_set_partition_flag ;;
			convert_table_label) action_convert_table_label ;;
			move_partition)      action_move_partition ;;
			clone_partition_dd)  action_clone_partition_dd ;;
			verify_partition)    action_verify_partition ;;
			disk_migration)      action_disk_migration ;;
			partclone_export)    action_partclone_export ;;
			partclone_import)    action_partclone_import ;;
			partclone_net_send)  action_partclone_net_send ;;
			partclone_net_recv)  action_partclone_net_recv ;;
			partclone_ddrescue)  action_partclone_ddrescue ;;
			mount_partition)     action_mount_partition ;;
			unmount_partition)   action_unmount_partition ;;
			reload_table)        action_reload_table ;;
			smart_info)          action_smart_info ;;
			smart_selftest_short) action_smart_selftest_short ;;
			badblocks_scan)      action_badblocks_scan ;;
			hdparm_info)         action_hdparm_info ;;
			gpt_info)            action_gpt_info ;;
			*)
				printf 'Unknown job action: %s\n' "$ACTION" >> "$STREAM_LOG"
				printf 'false\n1\nUnknown job action: %s\n\n' "$ACTION" > "$STREAM_DONE"
				;;
		esac
		[ -f "$STREAM_DONE" ] || printf 'true\n0\nCompleted\n\n' > "$STREAM_DONE"
	) > /dev/null 2>&1 &
	printf '%s\n' "$!" > "$_spid"
	echo "{\"success\": true, \"token\": \"${_token}\"}"
}

action_poll_job() {
	_token=$(cgi_param job_token)
	[ -n "$_token" ] || { emit_json_error "job_token required"; return; }
	_token=$(printf '%s' "$_token" | tr -cd '0-9')
	[ -n "$_token" ] || { emit_json_error "invalid job_token"; return; }
	_slog="/tmp/disk-mgmt-job-${_token}.log"
	_sdone="/tmp/disk-mgmt-job-${_token}.done"
	_offset=$(cgi_param offset)
	case "$_offset" in ''|*[!0-9]*) _offset=0 ;; esac

	# Check done sentinel FIRST, before reading the log.
	# This prevents a race condition where a fast-completing command
	# writes its output + creates .done between our log read and done check,
	# causing the log content to be lost when files are deleted.
	# When .done exists, the log is guaranteed complete (emit_cmd_result
	# always writes STREAM_LOG before creating STREAM_DONE).
	_done=false; _success=true; _rc=0; _msg=''; _extras=''
	if [ -f "$_sdone" ]; then
		_success=$(sed -n '1p' "$_sdone" 2>/dev/null); case "$_success" in true|false) : ;; *) _success=true ;; esac
		_rc=$(sed -n '2p' "$_sdone" 2>/dev/null); case "$_rc" in ''|*[!0-9]*) _rc=0 ;; esac
		_msg=$(sed -n '3p' "$_sdone" 2>/dev/null)
		_extras=$(sed -n '4p' "$_sdone" 2>/dev/null)
		_done=true
	fi

	# Read log content AFTER done check (guaranteed complete if done=true)
	_size=0
	if [ -f "$_slog" ]; then
		_size=$(wc -c < "$_slog" 2>/dev/null | tr -d ' ')
		case "$_size" in ''|*[!0-9]*) _size=0 ;; esac
	fi
	_newtext=''
	if [ "$_size" -gt "$_offset" ]; then
		# Use printf x sentinel to preserve trailing newlines that $() would strip
		_rawtext=$(tail -c "+$((_offset + 1))" "$_slog" 2>/dev/null; printf x) || true
		_newtext="${_rawtext%x}"
	fi

	# Clean up AFTER reading final content
	if [ "$_done" = "true" ]; then
		rm -f "$_slog" "$_sdone" "/tmp/disk-mgmt-job-${_token}.pid" 2>/dev/null
	fi

	_te=$(json_escape "$_newtext")
	_me=$(json_escape "$_msg")
	if [ "$_done" = "true" ] && [ -n "$_extras" ]; then
		echo "{\"done\":true,\"success\":$_success,\"rc\":$_rc,\"message\":\"$_me\",\"text\":\"$_te\",\"offset\":$_size,$_extras}"
	else
		echo "{\"done\":$_done,\"success\":$_success,\"rc\":$_rc,\"message\":\"$_me\",\"text\":\"$_te\",\"offset\":$_size}"
	fi
}

AJAX_MODE=$(cgi_param ajax)

if [ "$AJAX_MODE" = "1" ]; then
	ACTION=$(cgi_param action)
	DRY_RUN=$(cgi_param dry_run)
	[ "$DRY_RUN" = "1" ] || DRY_RUN='0'

	backend_log "REQUEST action=$ACTION dry_run=$DRY_RUN remote=${REMOTE_ADDR:-unknown} query=${QUERY_STRING:-}"
	if [ -n "$(cgi_param command_preview)" ]; then
		backend_log "REQUEST command_preview=$(cgi_param command_preview)"
	fi
	PS4='+disk-mgmt:${ACTION}: '
	set -x

	cat <<'EOF'
<style>
.ajax-json-box { display: none; }
</style>
<div class="ajax-json-box"><div class="ajax-json-content"><pre>Content-Type: application/json

EOF

	case "$ACTION" in
		analyze_tools)
			action_analyze_tools
			;;
		list_devices)
			action_list_devices
			;;
		create_partition)
			action_create_partition
			;;
		delete_partition)
			action_delete_partition
			;;
		resize_partition)
			action_resize_partition
			;;
		resize_filesystem)
			action_resize_filesystem
			;;
		create_filesystem)
			action_create_filesystem
			;;
		check_filesystem)
			action_check_filesystem
			;;
		set_label)
			action_set_label
			;;
		set_partition_name)
			action_set_partition_name
			;;
		set_partition_flag)
			action_set_partition_flag
			;;
		move_partition)
			action_move_partition
			;;
		clone_partition_dd)
			action_clone_partition_dd
			;;
		verify_partition)
			action_verify_partition
			;;
		disk_migration)
			action_disk_migration
			;;
		partclone_export)
			action_partclone_export
			;;
		partclone_import)
			action_partclone_import
			;;
		partclone_net_send)
			action_partclone_net_send
			;;
		partclone_net_recv)
			action_partclone_net_recv
			;;
		partclone_ddrescue)
			action_partclone_ddrescue
			;;
		mount_partition)
			action_mount_partition
			;;
		unmount_partition)
			action_unmount_partition
			;;
		partition_metadata)
			action_partition_metadata
			;;
		reload_table)
			action_reload_table
			;;
		smart_info)
			action_smart_info
			;;
		smart_selftest_short)
			action_smart_selftest_short
			;;
		badblocks_scan)
			action_badblocks_scan
			;;
		hdparm_info)
			action_hdparm_info
			;;
		gpt_info)
			action_gpt_info
			;;
		start_job)
			action_start_job
			;;
		poll_job)
			action_poll_job
			;;
		*)
			emit_json_error "Unknown action"
			;;
	esac

	set +x
	backend_log "RESPONSE action=$ACTION completed"

	echo '</pre></div></div>'
	exit 0
fi

sec_begin "Safety and operation mode" "safetyModeSection"
cat <<'EOF'
<div class="pcgi-grid">
	<div class="pcgi-card pcgi-card-danger">
		<h3 id="i18nDangerTitle">Danger zone</h3>
		<p id="i18nDangerText">This interface executes real partitioning commands. Backup your data before applying any operation.</p>
		<p id="i18nDangerUnlock">To unlock mutating actions, type <strong>YES_I_UNDERSTAND</strong>:</p>
		<input id="ackToken" type="text" size="28" placeholder="YES_I_UNDERSTAND">
		<p id="i18nDangerReadonly" class="pcgi-small">Read-only actions (scan, map, diagnostics, filesystem check in read-only mode) do not require unlock.</p>
		<div id="toolSummaryBox" class="pcgi-tool-summary pcgi-tool-summary-unknown">
			<strong id="toolSummaryTitle">Toolchain status: checking...</strong>
			<div id="toolSummaryMeta" class="pcgi-small"></div>
			<div id="toolSummaryMissingWrap" class="pcgi-small" style="display:none;">
				<span id="i18nMissingCommandsLabel">Missing commands:</span> <span id="toolSummaryMissing"></span>
			</div>
			<div id="toolSummaryImpact" class="pcgi-small"></div>
		</div>
		<div class="pcgi-inline-form" style="margin-top:10px;">
			<div>
				<label id="i18nLanguageLabel" for="langSelect">Language</label>
				<select id="langSelect">
					<option value="en">English</option>
					<option value="fr">Francais</option>
					<option value="es">Espanol</option>
					<option value="it">Italiano</option>
					<option value="de">Deutsch</option>
				</select>
			</div>
			<div>
				<label id="i18nUsbOnlyLabel" for="usbOnlySelect">Device filter</label>
				<select id="usbOnlySelect">
					<option value="0">All block devices</option>
					<option value="1">USB devices only</option>
				</select>
			</div>
		</div>
	</div>
	<div class="pcgi-card">
		<h3 id="i18nWorkflowTitle">Disk management workflow</h3>
		<ol>
			<li id="i18nWorkflow1">Refresh devices and choose one disk.</li>
			<li id="i18nWorkflow2">Drag new partition into free space, drag partition edge to resize, drag partition into free area to move it.</li>
			<li id="i18nWorkflow3">Add operations, review, then apply in order.</li>
			<li id="i18nWorkflow4">Run metadata view, filesystem checks, mount operations and diagnostics.</li>
		</ol>
		<div class="pcgi-toolbar">
			<button type="button" id="helpBtn">Shortcuts and help</button>
		</div>
	</div>
</div>
EOF
sec_end

sec_begin "Device map (visual)"
cat <<'EOF'
<style>
.pcgi-grid {
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
	gap: 12px;
}
.pcgi-card {
	border: 1px solid var(--evo-border, #ccd5e0);
	background: var(--evo-surface, #f9fbfd);
	padding: 12px;
	border-radius: 6px;
}
.pcgi-card-danger {
	border-color: #d48a8a;
	background: #fff6f6;
}
.pcgi-small {
	font-size: 11px;
	color: #666;
}
.pcgi-tool-summary {
	margin-top: 10px;
	padding: 8px;
	border-radius: 4px;
	border: 1px solid #b9c3cf;
	background: #f5f8fb;
}
.pcgi-tool-summary-unknown {
	border-color: #aab5c0;
	background: #f4f6f8;
}
.pcgi-tool-summary-ok {
	border-color: #76b27a;
	background: #ecf8ed;
}
.pcgi-tool-summary-warn {
	border-color: #c8a14d;
	background: #fff7e8;
}
.pcgi-tool-summary-danger {
	border-color: #c66d6d;
	background: #fff0f0;
}
#toolSummaryMissing {
	font-family: monospace;
}
.pcgi-toolbar {
	display: flex;
	flex-wrap: wrap;
	gap: 8px;
	align-items: center;
	margin-top: 12px;
	margin-bottom: 10px;
}
.pcgi-device-strip {
	display: flex;
	gap: 8px;
	overflow-x: auto;
	padding: 2px 0 6px;
	margin: -2px 0 10px;
}
.pcgi-device-card {
	min-width: 180px;
	padding: 8px 10px;
	border: 1px solid #aebccb;
	border-radius: 6px;
	background: linear-gradient(180deg, #f8fbfe 0%, #eef3f8 100%);
	cursor: pointer;
	text-align: left;
	color: #152230;
	box-sizing: border-box;
}
.pcgi-device-card:hover {
	border-color: #6e95bb;
	background: linear-gradient(180deg, #f4f9ff 0%, #e8f0f8 100%);
}
.pcgi-device-card.selected {
	border-color: #1e88e5;
	box-shadow: inset 0 0 0 1px #1e88e5;
	background: linear-gradient(180deg, #e8f3ff 0%, #d7eaff 100%);
}
.pcgi-device-card-main {
	display: block;
	font-weight: 700;
	font-size: 12px;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}
.pcgi-device-card-meta {
	display: block;
	margin-top: 2px;
	font-size: 11px;
	color: #425464;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}
.pcgi-device-select-hidden {
	position: absolute;
	left: -9999px;
	width: 1px;
	height: 1px;
	overflow: hidden;
}
.pcgi-chip {
	display: inline-block;
	padding: 4px 8px;
	border-radius: 12px;
	background: #1e88e5;
	color: #fff;
	font-size: 11px;
	cursor: grab;
}
#pcgiToastWrap {
	position: fixed;
	top: 16px;
	right: 16px;
	display: flex;
	flex-direction: column;
	gap: 8px;
	z-index: 5000;
}
.pcgi-toast {
	min-width: 220px;
	max-width: 520px;
	padding: 10px 12px;
	border-radius: 6px;
	color: #fff;
	box-shadow: 0 6px 16px rgba(0, 0, 0, 0.25);
	font-size: 12px;
	line-height: 1.35;
	animation: pcgi-fade-in .15s ease-out;
}
.pcgi-toast-info { background: #1e88e5; }
.pcgi-toast-success { background: #2e7d32; }
.pcgi-toast-warn { background: #c77700; }
.pcgi-toast-error { background: #c62828; }
@keyframes pcgi-fade-in {
	from { transform: translateY(-6px); opacity: 0; }
	to { transform: translateY(0); opacity: 1; }
}
.pcgi-modal {
	position: fixed;
	inset: 0;
	background: rgba(0, 0, 0, 0.45);
	display: none;
	align-items: center;
	justify-content: center;
	z-index: 4500;
}
.pcgi-modal-box {
	background: #fff;
	border-radius: 8px;
	box-shadow: 0 12px 26px rgba(0, 0, 0, 0.35);
	padding: 14px;
	width: min(720px, calc(100vw - 40px));
	max-height: calc(100vh - 40px);
	overflow: auto;
}
.pcgi-modal-head {
	font-size: 16px;
	font-weight: 700;
	margin: 0 0 8px;
}
.pcgi-modal-actions {
	display: flex;
	gap: 8px;
	justify-content: flex-end;
	margin-top: 12px;
}
.pcgi-modal-subtle {
	font-size: 12px;
	color: #4f5b67;
	margin-bottom: 8px;
}
.pcgi-help-btn {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	width: 15px;
	height: 15px;
	border-radius: 50%;
	border: 1px solid #5b8dd9;
	background: #deeafb;
	color: #1a56b0;
	font-size: 9px;
	font-weight: 700;
	cursor: pointer;
	padding: 0;
	margin-left: 4px;
	vertical-align: middle;
	line-height: 1;
	flex-shrink: 0;
}
.pcgi-help-btn:hover {
	background: #1a56b0;
	color: #fff;
	border-color: #1a56b0;
}
#pcgiFieldHelpModal { z-index: 5500; }
#pcgiFieldHelpModal .pcgi-modal-box { max-width: 480px; }
#pcgiFieldHelpBody {
	font-size: 13px;
	line-height: 1.75;
	color: #222;
	margin-top: 6px;
}
#pcgiFieldHelpBody code {
	background: #eef2f7;
	border-radius: 3px;
	padding: 1px 4px;
	font-size: 12px;
}
.pcgi-editor-wrap {
	border: 1px solid #c7d1dc;
	border-radius: 6px;
	overflow: hidden;
	background: #f8fbff;
}
#pcgiCommandEditor {
	height: 140px;
}
#pcgiCommandEditorFallback {
	display: none;
	width: 100%;
	height: 140px;
	border: 0;
	font-family: monospace;
	font-size: 12px;
	padding: 10px;
	box-sizing: border-box;
	resize: vertical;
}
#pcgiParamsEditor {
	height: 180px;
}
#pcgiParamsEditorFallback {
	display: none;
	width: 100%;
	height: 180px;
	border: 0;
	font-family: monospace;
	font-size: 12px;
	padding: 10px;
	box-sizing: border-box;
	resize: vertical;
}
.pcgi-param-ranges-wrap {
	margin-top: 8px;
	border: 1px solid #d9e2ec;
	border-radius: 6px;
	padding: 8px;
	background: #fbfdff;
}
.pcgi-param-ranges {
	font-size: 11px;
	white-space: pre;
	overflow: auto;
	max-height: 170px;
}
.pcgi-queue-actions {
	display: flex;
	flex-direction: column;
	align-items: stretch;
	gap: 3px;
}
.pcgi-queue-arrows {
	display: flex;
	gap: 3px;
}
.pcgi-queue-actions button {
	display: block;
	width: 100%;
}
.pcgi-queue-arrow-btn {
	font-size: 10px;
	line-height: 1;
	padding: 1px 4px;
	min-width: 20px;
}
.pcgi-queue-arrows .pcgi-queue-arrow-btn {
	flex: 1 1 auto;
	width: auto;
}


.pcgi-context-menu {
	position: absolute;
	display: none;
	min-width: 220px;
	background: #fff;
	color: #111;
	border: 1px solid #bac5d2;
	border-radius: 6px;
	box-shadow: 0 8px 20px rgba(0, 0, 0, 0.2);
	z-index: 4000;
	overflow: hidden;
}
.pcgi-context-item {
	display: block;
	width: 100%;
	border: 0;
	background: #fff;
	color: #111;
	padding: 8px 10px;
	font-size: 12px;
	text-align: left;
	cursor: pointer;
}
.pcgi-context-item:hover {
	background: #b8d4f0;
	color: #000;
	font-weight: 700;
}
.pcgi-kv-grid {
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
	gap: 8px;
	margin-bottom: 10px;
}
.pcgi-kv-card {
	border: 1px solid #cfd8e3;
	border-radius: 6px;
	padding: 8px;
	background: #f8fbff;
}
.pcgi-kv-key {
	font-size: 11px;
	color: #58687a;
	margin-bottom: 3px;
}
.pcgi-kv-value {
	font-weight: 700;
	font-size: 13px;
	word-break: break-all;
}
.pcgi-progress-wrap {
	margin-top: 8px;
	border: 1px solid #c5d1df;
	height: 18px;
	border-radius: 10px;
	overflow: hidden;
	background: #eef2f7;
}
.pcgi-progress-used {
	height: 100%;
	background: linear-gradient(90deg, #43a047 0%, #2e7d32 100%);
}
.pcgi-help-list {
	font-size: 12px;
	line-height: 1.45;
	white-space: pre-line;
}
#partitionMap {
	position: relative;
	height: 110px;
	border: 1px solid #9ba8b6;
	background: linear-gradient(180deg, #f5f8fb 0%, #e8eef5 100%);
	overflow: hidden;
	border-radius: 4px;
}
.pcgi-map-loading {
	position: absolute;
	inset: 0;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 12px;
	font-weight: 700;
	color: #304658;
	background: repeating-linear-gradient(45deg, rgba(255, 255, 255, 0.55), rgba(255, 255, 255, 0.55) 8px, rgba(230, 238, 246, 0.55) 8px, rgba(230, 238, 246, 0.55) 16px);
}
.pcgi-disk-block {
	position: absolute;
	left: 0;
	right: 0;
	top: 4px;
	height: 16px;
	line-height: 16px;
	padding: 0 6px;
	font-size: 11px;
	font-weight: 700;
	box-sizing: border-box;
	border: 1px solid #4a5f74;
	border-radius: 3px;
	background: linear-gradient(180deg, #b0bec5 0%, #90a4ae 100%);
	color: #10212f;
	cursor: pointer;
	overflow: hidden;
	white-space: nowrap;
	text-overflow: ellipsis;
}
.pcgi-disk-block.selected {
	outline: 2px solid #ff8f00;
	z-index: 3;
}
.pcgi-block {
	position: absolute;
	top: 28px;
	height: 54px;
	border: 1px solid #5d7187;
	box-sizing: border-box;
	overflow: hidden;
	white-space: nowrap;
	text-overflow: ellipsis;
	font-size: 11px;
	line-height: 16px;
	padding: 2px 4px;
}
.pcgi-block.part {
	background: linear-gradient(180deg, #90caf9 0%, #64b5f6 100%);
	cursor: pointer;
	min-width: 6px;
}
.pcgi-block.part:hover {
	font-weight: 700;
	z-index: 2;
}
.pcgi-block.free {
	background: repeating-linear-gradient(45deg, #f5f5f5, #f5f5f5 6px, #e5e5e5 6px, #e5e5e5 12px);
	border-style: dashed;
	color: #444;
}
.pcgi-block.selected {
	outline: 2px solid #ff8f00;
	z-index: 3;
}
.pcgi-part-fsbar {
	position: absolute;
	left: 10px;
	right: 10px;
	bottom: 2px;
	height: 7px;
	border: 1px solid rgba(0, 0, 0, 0.22);
	border-radius: 4px;
	overflow: hidden;
	background: #d6e9f8;
}
.pcgi-part-fsbar-used {
	height: 100%;
	background: linear-gradient(90deg, #4caf50 0%, #2e7d32 100%);
	float: left;
}
.pcgi-part-fsbar-unused {
	height: 100%;
	background: #e9f5eb;
	float: left;
}
.pcgi-resize-handle {
	position: absolute;
	right: 0;
	top: 0;
	height: 100%;
	width: 8px;
	cursor: ew-resize;
	background: rgba(0, 0, 0, 0.18);
}
.pcgi-drag-landing {
	position: absolute;
	top: 2px;
	bottom: 2px;
	background: rgba(37, 99, 235, 0.45);
	border: 2px dashed #2563eb;
	border-radius: 3px;
	pointer-events: none;
	z-index: 5;
	transition: left 0.05s, width 0.05s;
}
/* Extended partition container band */
.pcgi-extended-band {
	position: absolute;
	top: 0;
	bottom: 0;
	background: rgba(234, 179, 8, 0.10);
	border: 2px solid rgba(161, 117, 7, 0.55);
	border-radius: 4px;
	z-index: 0;
	pointer-events: none;
	box-sizing: border-box;
}
.pcgi-extended-label {
	position: absolute;
	top: 1px;
	left: 3px;
	font-size: 9px;
	color: rgba(120, 80, 0, 0.8);
	font-weight: bold;
	white-space: nowrap;
	pointer-events: none;
	z-index: 6;
	user-select: none;
}
/* Logical partition blocks get a bottom stripe */
.pcgi-block.part.pcgi-logical::after {
	content: '';
	position: absolute;
	bottom: 0;
	left: 0;
	right: 0;
	height: 3px;
	background: rgba(161, 117, 7, 0.7);
	border-radius: 0 0 2px 2px;
	pointer-events: none;
}
/* Extended partition block itself */
.pcgi-block.part.pcgi-extended {
	background: repeating-linear-gradient(
		45deg,
		rgba(234, 179, 8, 0.18) 0px,
		rgba(234, 179, 8, 0.18) 4px,
		rgba(255, 248, 220, 0.4) 4px,
		rgba(255, 248, 220, 0.4) 8px
	);
	border-color: rgba(161, 117, 7, 0.7);
	color: #5a3e00;
}
.pcgi-resize-handle-left {
	left: 0;
	right: auto;
}
.pcgi-map-legend {
	font-size: 11px;
	margin-top: 6px;
	color: #4f5b67;
}
.pcgi-hover-tooltip {
	position: fixed;
	display: none;
	max-width: 360px;
	padding: 8px 10px;
	border: 1px solid #394a5a;
	border-radius: 6px;
	background: rgba(17, 24, 39, 0.95);
	color: #f3f7fb;
	font-size: 12px;
	line-height: 1.35;
	z-index: 5000;
	pointer-events: none;
	box-shadow: 0 10px 24px rgba(0, 0, 0, 0.35);
}
.pcgi-hover-tooltip-grid {
	display: grid;
	grid-template-columns: auto 1fr;
	column-gap: 8px;
	row-gap: 2px;
}
.pcgi-hover-tooltip-key {
	color: #9fb3c8;
	font-weight: 600;
	white-space: nowrap;
}
.pcgi-hover-tooltip-value {
	color: #ffffff;
	font-weight: 700;
	word-break: break-word;
}
.pcgi-inline-form {
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
	gap: 8px;
	margin-top: 10px;
}
.pcgi-log {
	background: #111827;
	color: #d1fae5;
	padding: 10px;
	border-radius: 6px;
	font-family: monospace;
	font-size: 11px;
	white-space: pre-wrap;
	max-height: 300px;
	overflow: auto;
}
.pcgi-ansi-log .ansi-bold      { font-weight: bold }
.pcgi-ansi-log .ansi-green     { color: #4ade80 }
.pcgi-ansi-log .ansi-red       { color: #f87171 }
.pcgi-ansi-log .ansi-yellow    { color: #fbbf24 }
.pcgi-ansi-log .ansi-blue      { color: #60a5fa }
.pcgi-ansi-log .ansi-cyan      { color: #22d3ee }
.pcgi-ansi-log .ansi-gray      { color: #9ca3af }
.pcgi-ansi-log .ansi-dim       { opacity: 0.7 }
.pcgi-log-fullscreen {
	position: fixed !important;
	inset: 0 !important;
	max-height: none !important;
	height: 100% !important;
	border-radius: 0 !important;
	z-index: 9999;
	font-size: 12px !important;
}
.pcgi-log-fsbody { overflow: hidden; }
.pcgi-table {
	width: 100%;
	border-collapse: collapse;
	font-size: 12px;
}
.pcgi-table th,
.pcgi-table td {
	border-bottom: 1px solid #d8dee6;
	padding: 6px;
	text-align: left;
}
.pcgi-mono {
	font-family: monospace;
}
/* Hide the framework Applica / Default (submit) buttons;
   disk-mgmt manages all actions via its own JavaScript flow. */
input[type="submit"], button[type="submit"] { display: none !important; }
details#advancedInfoDetails > summary.pcgi-sec-summary {
	cursor: pointer;
	user-select: none;
	padding: 4px 0;
	font-weight: bold;
}
.pcgi-rule {
	margin: 6px 0;
	border: none;
	border-top: 1px solid #d1d5db;
}
.pcgi-flag-hint {
	flex: 0 0 100%;
	font-size: 11px;
	color: #6b7280;
	margin-bottom: 2px;
}
.pace {
	pointer-events: none;
	user-select: none;
}
.pace.pace-inactive {
	display: none;
}
.pace .pace-progress {
	display: none;
}
.pace .pace-activity {
	position: fixed;
	top: 12px;
	right: 12px;
	width: 34px;
	height: 34px;
	border: 1px solid #c8d2de;
	border-radius: 6px;
	background: transparent;
	box-shadow: none;
	z-index: 12000;
}
.pace .pace-activity:before {
	content: '⌛';
	display: block;
	font-size: 20px;
	line-height: 34px;
	text-align: center;
	animation: pcgi-hourglass-pulse 1.1s ease-in-out infinite;
}
@keyframes pcgi-hourglass-pulse {
	0% { transform: scale(0.9); opacity: 0.7; }
	50% { transform: scale(1.05); opacity: 1; }
	100% { transform: scale(0.9); opacity: 0.7; }
}
</style>

<div class="pcgi-toolbar">
	<button type="button" onclick="refreshDevices()" id="refreshMapBtn">Refresh map</button>
	<span id="i18nDeviceStripLabel"><b>Devices:</b></span>
	<span id="mapStatus" class="pcgi-small"></span>
</div>

<div id="deviceStrip" class="pcgi-device-strip" aria-label="Devices"></div>
<select id="deviceSelect" class="pcgi-device-select-hidden" onchange="onDeviceChange()" aria-hidden="true" tabindex="-1"></select>

<div id="partitionMap"></div>
<div id="mapLegend" class="pcgi-map-legend"></div>
<div id="pcgiHoverTooltip" class="pcgi-hover-tooltip"></div>

<div id="partContextMenu" class="pcgi-context-menu"></div>

<div class="pcgi-inline-form" style="grid-template-columns:repeat(2,1fr)">
	<div>
		<label id="i18nSelPartPathLabel">Selected partition path</label>
		<input id="selectedPartPath" type="text" readonly>
	</div>
	<div>
		<label id="i18nSelPartNumLabel">Selected partition number</label>
		<input id="selectedPartNum" type="text" readonly>
	</div>
</div>
<div class="pcgi-inline-form" style="margin-top:4px">
	<div>
		<label id="i18nNewStartLabel">New start sector</label>
		<input id="newStartSector" type="text" placeholder="e.g. 2048">
	</div>
	<div>
		<label id="i18nNewStartHumanLabel">New start size</label>
		<input id="newStartHuman" type="text" placeholder="e.g. 1 MiB or 2048 KiB">
	</div>
</div>
<div class="pcgi-inline-form" style="margin-top:4px">
	<div>
		<label id="i18nNewEndLabel">New end sector</label>
		<input id="newEndSector" type="text" placeholder="e.g. 1023999">
	</div>
	<div>
		<label id="i18nNewEndHumanLabel">New end size</label>
		<input id="newEndHuman" type="text" placeholder="e.g. 488 MiB">
	</div>
</div>
<div class="pcgi-inline-form" style="margin-top:4px">
	<div>
		<label id="i18nRoleLabel">Role</label>
		<select id="newPartRole">
			<option value="primary">primary</option>
			<option value="logical">logical</option>
			<option value="extended">extended</option>
		</select>
	</div>
	<div>
		<label id="i18nFsHintLabel">Filesystem</label>
		<select id="newFsHint">
			<option value="">(none)</option>
			<option value="ext4">ext4</option>
			<option value="ext3">ext3</option>
			<option value="ext2">ext2</option>
			<option value="f2fs">f2fs</option>
			<option value="exfat">exfat</option>
			<option value="ntfs">ntfs</option>
			<option value="fat32">fat32</option>
			<option value="fat16">fat16</option>
		</select>
	</div>
</div>
<div class="pcgi-inline-form" style="margin-top:4px">
	<div>
		<label id="i18nPartNameLabel">Partition name</label>
		<input id="newPartName" type="text" placeholder="optional">
	</div>
	<div>
		<label id="i18nAlignLabel">Alignment <button type="button" class="pcgi-help-btn" onclick="showFieldHelp('map-align')" title="Help">?</button></label>
		<select id="newPartAlign">
			<option value="optimal" selected>optimal (1 MiB)</option>
			<option value="2048">2048 sectors (1 MiB)</option>
			<option value="4096">4096 sectors (2 MiB)</option>
			<option value="no">no alignment</option>
		</select>
	</div>
</div>

<div class="pcgi-toolbar">
	<span id="newPartChip" class="pcgi-chip" draggable="true" title="Drag on a free segment to create new partition">New partition</span>
	<span id="verifyPartChip" class="pcgi-chip" style="cursor:pointer" title="Compare two partitions byte-by-byte (read-only)">Verify partition</span>
	<span id="moveClonePartChip" class="pcgi-chip" draggable="true" title="Drag on a free segment to open move/clone configuration">Move or clone partition</span>
	<span id="i18nDragHint" class="pcgi-small">Drag <strong>New partition</strong> to a free segment for quick create. Drag <strong>New partition with filesystem</strong> to include Role, Filesystem and Partition name from the form above. Drag <strong>Move or clone partition</strong> to a free segment to open the move/clone form pre-filled with the selected partition. Click <strong>Verify partition</strong> to compare two partitions. Drag the left or right edge of a partition to resize. Drag a partition to free space for smart move.</span>
</div>

<div class="pcgi-toolbar" style="margin-top: 8px;">
	<button type="button" onclick="queueCreatePartition()" id="queueCreateBtn">Create partition</button>
	<button type="button" onclick="queueDeletePartition()" id="queueDeleteBtn">Delete selected partition</button>
</div>

<!-- New partition question modal -->
<div id="pcgiNewPartModal" class="pcgi-modal" aria-hidden="true">
	<div class="pcgi-modal-box" style="max-width:600px">
		<h3 id="pcgiNewPartTitle" class="pcgi-modal-head">New partition</h3>
		<!-- Partition table selector — shown only when disk has no partitions yet -->
		<div id="pnpTableRow" style="display:none;background:#fff3cd;border:1px solid #ffc107;border-radius:4px;padding:8px 10px;margin-bottom:10px">
			<p id="pnpTableMsg" style="margin:0 0 6px;font-size:.9em">⚠️ This disk has no partition table yet. Choose a type before creating the first partition.</p>
			<label id="i18nPnpTableLabel" style="font-weight:600">Partition table type</label>
			<select id="pnpTableType" style="margin-top:4px">
				<option value="gpt" selected>GPT – GUID Partition Table (recommended for &gt;2 TB, UEFI)</option>
				<option value="msdos">msdos – MBR (legacy, max 4 primary, up to 2 TB)</option>
				<option value="bsd">bsd – BSD disklabel</option>
				<option value="loop">loop – raw partition</option>
				<option value="atari">atari</option>
				<option value="dvh">dvh – SGI/IRIX</option>
				<option value="mac">mac – Apple partition map</option>
				<option value="sun">sun – Solaris</option>
			</select>
		</div>
		<!-- Validation warning -->
		<div id="pnpWarnRow" style="display:none;background:#f8d7da;border:1px solid #f5c2c7;border-radius:4px;padding:6px 10px;margin-bottom:8px;font-size:.9em" id="pnpWarnRow"></div>
		<div class="pcgi-inline-form" style="margin-top:8px;grid-template-columns:1fr 1.6em 1fr">
			<div>
				<label id="i18nPnpStartLabel">New start sector</label>
				<input id="pnpStartSector" type="text" placeholder="e.g. 2048">
			</div>
			<div style="display:flex;align-items:flex-end;justify-content:center;padding-bottom:5px;color:#888;font-size:1.1em;" title="Linked — sector ↔ size (editing one updates the other)">↔</div>
			<div>
				<label id="i18nPnpStartHLabel">New start size</label>
				<input id="pnpStartHuman" type="text" placeholder="e.g. 1 MiB">
			</div>
			<div>
				<label id="i18nPnpEndLabel">New end sector</label>
				<input id="pnpEndSector" type="text" placeholder="e.g. 1023999">
			</div>
			<div style="display:flex;align-items:flex-end;justify-content:center;padding-bottom:5px;color:#888;font-size:1.1em;" title="Linked — sector ↔ size (editing one updates the other)">↔</div>
			<div>
				<label id="i18nPnpEndHLabel">New end size</label>
				<input id="pnpEndHuman" type="text" placeholder="e.g. 488 MiB">
			</div>
			<div id="pnpRoleRow">
				<label id="i18nPnpRoleLabel">Role</label>
				<select id="pnpRole">
					<option value="primary">primary</option>
					<option value="logical">logical</option>
					<option value="extended">extended</option>
				</select>
			</div>
			<div></div><!-- spacer -->
			<div id="pnpFsHintRow">
				<label id="i18nPnpFsHintLabel">Filesystem</label>
				<select id="pnpFsHint">
					<option value="">(none)</option>
					<option value="ext4">ext4</option>
					<option value="ext3">ext3</option>
					<option value="ext2">ext2</option>
					<option value="f2fs">f2fs</option>
					<option value="exfat">exfat</option>
					<option value="ntfs">ntfs</option>
					<option value="fat32">fat32</option>
					<option value="fat16">fat16</option>
				</select>
			</div>
			<div style="grid-column:1/-1">
				<label id="i18nPnpPartNameLabel">Partition name (GPT only)</label>
				<input id="pnpPartName" type="text" placeholder="optional (stored in GPT entry)">
			</div>
			<div id="pnpFsLabelRow" style="grid-column:1/-1;display:none">
				<label id="i18nPnpFsLabelLabel">Filesystem label</label>
				<input id="pnpFsLabel" type="text" placeholder="optional (max 16 chars for ext4, 11 for FAT)">
			</div>
			<div id="pnpMountRow" style="grid-column:1/-1;display:none">
				<label id="i18nPnpMountLabel">Mount point (after creation)</label>
				<input id="pnpMountPoint" type="text" placeholder="e.g. /var/media/ftp/DATA">
			</div>
			<div style="grid-column:1/-1">
				<label id="i18nPnpAlignLabel">Alignment</label>
				<select id="pnpAlign">
					<option value="optimal" selected>optimal – 1 MiB / logical sector size (SD, USB, SSD, NVMe)</option>
					<option value="2048">2048 sectors – 1 MiB (512-byte drives)</option>
					<option value="4096">4096 sectors – 2 MiB (high-end NVMe)</option>
					<option value="no">no alignment</option>
				</select>
			</div>
		</div>
		<div class="pcgi-modal-actions" style="margin-top:12px">
			<button type="button" id="pcgiNewPartCancelBtn">Cancel</button>
			<button type="button" id="pcgiNewPartFsBtn">Create partition</button>
		</div>
	</div>
</div>

<!-- Convert partition table modal -->
<div id="pcgiConvertLabelModal" class="pcgi-modal" aria-hidden="true">
	<div class="pcgi-modal-box" style="max-width:480px">
		<h3 class="pcgi-modal-head">Convert partition table</h3>
		<p id="pcgiConvertLabelCurrent" style="margin:4px 0 8px;color:#888;font-size:.9em"></p>
		<p style="background:#fff3cd;border:1px solid #ffc107;padding:8px 10px;border-radius:4px;margin:0 0 10px;font-size:.9em">
			⚠️ This <strong>erases all partitions</strong> and their data on the disk.  Only the raw disk will remain.
		</p>
		<div class="pcgi-inline-form" style="margin-top:8px;grid-template-columns:1fr">
			<div>
				<label>New partition table type</label>
				<select id="pcgiConvertLabelType">
					<option value="gpt" selected>GPT – GUID Partition Table (recommended for &gt;2 TB, UEFI)</option>
					<option value="msdos">msdos – MBR (legacy, max 4 primary, up to 2 TB)</option>
					<option value="bsd">bsd – BSD disklabel</option>
					<option value="loop">loop – raw partition</option>
					<option value="atari">atari</option>
					<option value="dvh">dvh – SGI/IRIX</option>
					<option value="mac">mac – Apple partition map</option>
					<option value="sun">sun – Solaris</option>
				</select>
			</div>
		</div>
		<div class="pcgi-modal-actions" style="margin-top:12px">
			<button type="button" id="pcgiConvertLabelCancelBtn">Cancel</button>
			<button type="button" id="pcgiConvertLabelConfirmBtn" style="background:#dc3545;color:#fff">Convert (erase all partitions)</button>
		</div>
	</div>
</div>

<!-- Freetz EVO disk setup modal -->
<div id="pcgiFritzSetupModal" class="pcgi-modal" aria-hidden="true">
	<div class="pcgi-modal-box" style="max-width:680px">
		<h3 class="pcgi-modal-head" id="pcgiFritzSetupTitle">Freetz EVO disk setup</h3>
		<p id="pcgiFritzSetupDisk" style="margin:2px 0 6px;color:#888;font-size:.9em"></p>
		<p id="pcgiFritzSetupWarn" style="display:none;background:#fff3cd;border:1px solid #ffc107;padding:6px 10px;border-radius:4px;margin:0 0 8px;font-size:.85em"></p>
		<p style="background:#fff3cd;border:1px solid #ffc107;padding:8px 10px;border-radius:4px;margin:0 0 10px;font-size:.9em">
			⚠️ <strong>All existing partitions will be erased</strong> if "Delete existing partitions" is checked.
		</p>
		<!-- Global options -->
		<div class="pcgi-inline-form" style="grid-template-columns:1fr 1fr;margin-bottom:8px">
			<div>
				<label>Partition table <button type="button" class="pcgi-help-btn" onclick="showFieldHelp('fritz-table-type')" title="Help">?</button></label>
				<select id="fsSetupTableType">
					<option value="gpt">GPT (recommended)</option>
					<option value="msdos">msdos / MBR</option>
				</select>
			</div>
			<div>
				<label>Alignment <button type="button" class="pcgi-help-btn" onclick="showFieldHelp('fritz-align')" title="Help">?</button></label>
				<select id="fsSetupAlign">
					<option value="optimal" selected>optimal (1 MiB)</option>
					<option value="2048">2048 sectors (1 MiB)</option>
					<option value="4096">4096 sectors (2 MiB)</option>
					<option value="no">no alignment</option>
				</select>
			</div>
			<div style="grid-column:1/-1;display:flex;gap:20px;align-items:center;flex-wrap:wrap">
				<label style="display:flex;align-items:center;gap:6px;font-weight:normal">
					<input type="checkbox" id="fsSetupDeleteAll" checked> Delete existing partitions first <button type="button" class="pcgi-help-btn" onclick="showFieldHelp('fritz-delete-all')" title="Help">?</button>
				</label>
				<label style="display:flex;align-items:center;gap:6px;font-weight:normal">
					<input type="checkbox" id="fsSetupMountAll" checked> Mount all partitions after creation <button type="button" class="pcgi-help-btn" onclick="showFieldHelp('fritz-mount-all')" title="Help">?</button>
				</label>
			</div>
		</div>
		<!-- Partition list -->
		<div style="font-size:.85em;color:#555;margin-bottom:4px">Partitions to create (order = physical disk order):</div>
		<table id="fsSetupPartTable" style="width:100%;border-collapse:collapse;font-size:.9em">
			<thead>
				<tr style="background:#f5f5f5">
					<th style="padding:4px 6px;text-align:center;width:2em">✓</th>
					<th style="padding:4px 6px;text-align:left">Name / label</th>
					<th style="padding:4px 6px;text-align:left">Filesystem</th>
					<th style="padding:4px 6px;text-align:left">Size</th>
					<th style="padding:4px 6px;text-align:left;min-width:160px">Mount point</th>
					<th style="padding:4px 6px;width:2em"></th>
				</tr>
			</thead>
			<tbody id="fsSetupPartBody">
				<!-- rows populated by JS -->
			</tbody>
		</table>
		<div style="margin-top:6px">
			<button type="button" id="fsSetupAddPartBtn" style="font-size:.85em">+ Add partition</button>
		</div>
		<!-- Live disk layout preview -->
		<div style="margin:8px 0 2px;font-size:.8em;color:#666">Disk layout preview:</div>
		<div id="fsSetupPreviewBar" style="display:flex;height:24px;border-radius:3px;overflow:hidden;border:1px solid #ccc;margin-bottom:4px"></div>
		<div id="fsSetupPreviewLegend" style="display:flex;flex-wrap:wrap;gap:2px 10px;font-size:.78em;margin-bottom:8px"></div>
		<div class="pcgi-modal-actions" style="margin-top:12px">
			<button type="button" id="pcgiFritzSetupCancelBtn">Cancel</button>
			<button type="button" id="pcgiFritzSetupRunBtn" style="background:#28a745;color:#fff">Run setup</button>
		</div>
	</div>
</div>

<!-- Create filesystem modal -->
<div id="pcgiMkfsModal" class="pcgi-modal" aria-hidden="true">
	<div class="pcgi-modal-box" style="max-width:480px">
		<h3 id="pcgiMkfsTitle" class="pcgi-modal-head">Create filesystem</h3>
		<div class="pcgi-inline-form" style="margin-top:8px;grid-template-columns:repeat(2,1fr)">
			<div style="grid-column:1/-1">
				<label id="i18nMkfsPartPathLabel">Partition path</label>
				<input id="mkfsPartPath" type="text" placeholder="/dev/sda1">
			</div>
			<div style="grid-column:1/-1">
				<label id="i18nMkfsFsTypeLabel">Filesystem type</label>
				<select id="mkfsFsType">
					<option value="ext4">ext4</option>
					<option value="ext3">ext3</option>
					<option value="ext2">ext2</option>
					<option value="f2fs">f2fs</option>
					<option value="exfat">exfat</option>
					<option value="ntfs">ntfs</option>
					<option value="fat32">fat32</option>
					<option value="fat16">fat16</option>
					<option value="vfat">vfat</option>
				</select>
			</div>
			<div style="grid-column:1/-1">
				<label id="i18nMkfsLabelLabel">Label (optional)</label>
				<input id="mkfsLabel" type="text" placeholder="optional label">
			</div>
			<div style="grid-column:1/-1">
				<label id="i18nMkfsExtraOptsLabel">Advanced options</label>
				<input id="mkfsExtraOpts" type="text" placeholder="e.g. -E lazy_itable_init=0">
			</div>
			<div id="mkfsFullFormatRow" style="grid-column:1/-1;display:none">
				<label id="i18nMkfsFullFmtLabel">Full format (write zeros, NTFS only)</label>
				<input id="mkfsFullFormat" type="checkbox">
			</div>
		</div>
		<div class="pcgi-modal-actions" style="margin-top:12px">
			<button type="button" id="pcgiMkfsCancelBtn">Cancel</button>
			<button type="button" id="pcgiMkfsConfirmBtn">Create filesystem</button>
		</div>
	</div>
</div>

<!-- Verify partitions modal -->
<div id="pcgiVerifyModal" class="pcgi-modal" aria-hidden="true">
	<div class="pcgi-modal-box" style="max-width:500px">
		<h3 id="pcgiVerifyTitle" class="pcgi-modal-head">Verify partitions</h3>
		<div class="pcgi-inline-form" style="margin-top:8px">
			<div>
				<label id="i18nVerifySourceDevLabel">Source device (A)</label>
				<select id="verifySourceDev" onchange="populateVerifyPartDropdown('verifySourceDev','verifySourcePartNum')"></select>
			</div>
			<div>
				<label id="i18nVerifySourcePartLabel">Source partition (A)</label>
				<select id="verifySourcePartNum"></select>
			</div>
			<div>
				<label id="i18nVerifyTargetDevLabel">Compare device (B)</label>
				<select id="verifyTargetDev" onchange="populateVerifyPartDropdown('verifyTargetDev','verifyTargetPartNum')"></select>
			</div>
			<div>
				<label id="i18nVerifyTargetPartLabel">Compare partition (B)</label>
				<select id="verifyTargetPartNum"></select>
			</div>
			<div>
				<label id="i18nVerifyUnmountLabel">Unmount before (-u)</label>
				<select id="verifyUnmount">
					<option value="no">no</option>
					<option value="yes">yes</option>
				</select>
			</div>
		</div>
		<div class="pcgi-modal-actions">
			<button type="button" id="pcgiVerifyCancelBtn">Cancel</button>
			<button type="button" id="pcgiVerifyOkBtn">Verify</button>
		</div>
	</div>
</div>

<!-- Mount partition modal -->
<div id="pcgiMountModal" class="pcgi-modal" aria-hidden="true">
	<div class="pcgi-modal-box" style="max-width:480px">
		<h3 id="pcgiMountTitle" class="pcgi-modal-head">Mount partition</h3>
		<div class="pcgi-inline-form" style="margin-top:8px;grid-template-columns:1fr">
			<div>
				<label id="i18nMountModalPartLabel">Partition</label>
				<input id="mountModalPart" type="text" readonly style="background:#f5f5f5;font-family:monospace">
			</div>
			<div>
				<label id="i18nMountModalMpLabel">Mountpoint</label>
				<input id="mountModalMp" type="text" placeholder="/var/media/ftp/sda1">
			</div>
			<div>
				<label id="i18nMountModalFsLabel">Filesystem type</label>
				<select id="mountModalFs">
					<option value="auto">auto (kernel detect)</option>
					<option value="ext4">ext4</option>
					<option value="ext3">ext3</option>
					<option value="ext2">ext2</option>
					<option value="ntfs">ntfs</option>
					<option value="vfat">vfat</option>
					<option value="exfat">exfat</option>
					<option value="f2fs">f2fs</option>
				</select>
			</div>
			<div>
				<label id="i18nMountModalOptsLabel">Mount options (optional)</label>
				<input id="mountModalOpts" type="text" placeholder="rw,noatime">
			</div>
		</div>
		<div class="pcgi-modal-actions" style="margin-top:12px">
			<button type="button" id="pcgiMountCancelBtn">Cancel</button>
			<button type="button" id="pcgiMountOkBtn">Mount</button>
		</div>
	</div>
</div>

<!-- Move / Clone configuration modal -->
<div id="pcgiMoveCloneModal" class="pcgi-modal" aria-hidden="true">
	<div class="pcgi-modal-box" style="max-width:780px;width:96vw">
		<h3 id="pcgiMoveCloneTitle" class="pcgi-modal-head">Move or clone partition</h3>
		<div id="mcTargetInfo" class="pcgi-modal-subtle" style="margin-bottom:6px"></div>

		<!-- Source + Target devices/partitions — 2-column grid -->
		<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px 18px;margin-top:4px">
			<div>
				<label id="i18nMcModeLabel">Operation</label>
				<select id="mcMode" style="width:100%">
					<option value="clone">Clone (keep source)</option>
					<option value="move">Move (delete source)</option>
				</select>
			</div>
			<div><!-- spacer --></div>

			<div>
				<label id="i18nMcSourceDevLabel">Source device</label>
				<select id="mcSourceDevice" style="width:100%" onchange="populateMcPartDropdown(); updateMcSourceInfo()"></select>
			</div>
			<div>
				<label id="i18nMcTargetDevLabel">Target device</label>
				<select id="mcTargetDevice" style="width:100%" onchange="populateMcTargetPartDropdown()"></select>
			</div>

			<div>
				<label id="i18nMcSourcePartLabel">Source partition</label>
				<select id="mcSourcePartNum" style="width:100%" onchange="updateMcSourceInfo()"></select>
			</div>
			<div>
				<label id="i18nMcTargetPartLabel">Target partition (optional – or use sectors below)</label>
				<select id="mcTargetPartNum" style="width:100%">
					<option value="">— use sector range below —</option>
				</select>
			</div>
		</div>

		<!-- Source info strip -->
		<div id="mcSourceInfo" style="display:none;margin:6px 0;padding:6px 8px;background:#f0f6ff;border:1px solid #c8d8ef;border-radius:4px;font-size:11px;font-family:monospace;white-space:pre-wrap;line-height:1.6"></div>

		<!-- Target range: sector + unit selector -->
		<div style="margin:8px 0 4px;font-size:11px;font-weight:600;color:#4a6080" id="i18nMcTargetRangeHeading">Target range</div>
		<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px">
			<div>
				<label id="i18nMcTargetStartLabel">Start sector</label>
				<div style="display:flex;gap:4px;align-items:center">
					<input id="mcTargetStart" type="number" min="0" step="1" placeholder="sector" style="flex:1;min-width:0;font-family:monospace">
					<span style="color:#888;font-size:11px">=</span>
					<input id="mcTargetStartNum" type="number" min="0" step="0.01" placeholder="0" style="width:64px">
					<select id="mcTargetStartUnit" style="width:58px;padding:2px 2px">
						<option value="GiB">GiB</option>
						<option value="MiB">MiB</option>
						<option value="TiB">TiB</option>
						<option value="KiB">KiB</option>
					</select>
				</div>
			</div>
			<div>
				<label id="i18nMcTargetEndLabel">End sector (inclusive)</label>
				<div style="display:flex;gap:4px;align-items:center">
					<input id="mcTargetEnd" type="number" min="0" step="1" placeholder="sector" style="flex:1;min-width:0;font-family:monospace">
					<span style="color:#888;font-size:11px">=</span>
					<input id="mcTargetEndNum" type="number" min="0" step="0.01" placeholder="0" style="width:64px">
					<select id="mcTargetEndUnit" style="width:58px;padding:2px 2px">
						<option value="GiB">GiB</option>
						<option value="MiB">MiB</option>
						<option value="TiB">TiB</option>
						<option value="KiB">KiB</option>
					</select>
				</div>
			</div>
			<div>
				<label id="i18nMcTargetSizeLabel">Target range size</label>
				<input id="mcTargetSizeDisplay" type="text" readonly tabindex="-1" style="background:#f5f7fa;cursor:default;font-family:monospace;width:100%" placeholder="---">
			</div>
		</div>

		<!-- Options — 2-column layout -->
		<div style="margin:8px 0 4px;font-size:11px;font-weight:600;color:#4a6080" id="i18nMcOptionsHeading">Options</div>
		<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px 18px">
			<div>
				<label id="i18nMcCloneMethodLabel">Clone method</label>
				<select id="mcCloneMethod" style="width:100%">
					<option value="smart">Smart (filesystem-aware)</option>
					<option value="sector">Sector-by-sector (dd)</option>
				</select>
			</div>
			<div>
				<label id="i18nMcVerifyLabel">Verify after clone (-V)</label>
				<select id="mcVerify" style="width:100%">
					<option value="no">no</option>
					<option value="yes">yes (partclone.chkimg)</option>
				</select>
			</div>
			<div>
				<label id="i18nMcAlignmentLabel">Alignment (-a)</label>
				<select id="mcAlignment" style="width:100%">
					<option value="1048576" selected>1048576 (1 MiB – modern, recommended)</option>
					<option value="4096">4096 (4K – physical sector)</option>
					<option value="512">512 (legacy)</option>
				</select>
			</div>
			<div>
				<label id="i18nMcUnmountBeforeLabel">Unmount before (-u)</label>
				<select id="mcUnmountBefore" style="width:100%">
					<option value="yes" selected>yes</option>
					<option value="no">no</option>
				</select>
			</div>
			<div>
				<label id="i18nMcMountAfterLabel">Mount after (-o)</label>
				<select id="mcMountAfter" style="width:100%" onchange="document.getElementById('mcTargetMount').style.display=this.value==='yes'?'':'none'">
					<option value="no">no</option>
					<option value="yes">yes</option>
				</select>
			</div>
			<div>
				<label id="i18nMcTargetMountLabel">Target mountpoint (-t)</label>
				<input id="mcTargetMount" type="text" placeholder="/var/media/ftp/label" style="display:none;width:100%">
			</div>
			<div>
				<label id="i18nMcForceFsLabel">Force filesystem type (-f)</label>
				<input id="mcForceFs" type="text" placeholder="auto-detect if empty" style="width:100%">
			</div>
			<div>
				<label id="i18nMcExtraOptsLabel">Extra partclone options (-x)</label>
				<input id="mcPartcloneExtra" type="text" placeholder="e.g. --debug" style="width:100%">
			</div>
			<div>
				<label id="i18nMcFsckPassesLabel">FAT pre-clone fsck passes (-F)</label>
				<select id="mcFsckPasses" style="width:100%">
					<option value="2" selected>2 (recommended)</option>
					<option value="1">1</option>
					<option value="0">0 (disabled)</option>
				</select>
			</div>
			<div>
				<label id="i18nMcDdFallbackLabel">dd fallback on smart failure (-b)</label>
				<select id="mcDdFallback" style="width:100%">
					<option value="1" selected>yes (recommended)</option>
					<option value="0">no</option>
				</select>
			</div>
			<div>
				<label id="i18nMcSkipWriteErrLabel">Skip write errors (-W)</label>
				<select id="mcSkipWriteError" style="width:100%">
					<option value="0" selected>no (abort on errors)</option>
					<option value="1">yes (continue on write errors)</option>
				</select>
			</div>
			<div>
				<label id="i18nMcStepDelayLabel">Step delay seconds (-w)</label>
				<input id="mcStepDelay" type="number" min="0" step="1" value="1" placeholder="1" style="width:100%">
			</div>
			<div>
				<label id="i18nMcDdBsLabel">dd block size</label>
				<input id="mcDdBs" type="text" value="1M" placeholder="1M" style="width:100%">
			</div>
		</div>
		<div class="pcgi-modal-actions">
			<button type="button" id="pcgiMcCancelBtn">Cancel</button>
			<button type="button" id="pcgiMcOkBtn">Validate and queue</button>
		</div>
	</div>
</div>
<div id="pcgiDiskMoveCloneModal" class="pcgi-modal" aria-hidden="true">
	<div class="pcgi-modal-box" style="max-width:820px;width:96vw">
		<h3 id="pcgiDmTitle" class="pcgi-modal-head">Move or clone disk</h3>
		<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px 20px;padding:10px 0">
			<div>
				<label id="i18nDmSourceDevLabel">Source disk (-D)</label>
				<select id="dmSourceDevice" style="width:100%"></select>
			</div>
			<div>
				<label id="i18nDmTargetDevLabel">Target disk (-d)</label>
				<select id="dmTargetDevice" style="width:100%"></select>
			</div>
			<div>
				<label id="i18nDmModeLabel">Operation (-M)</label>
				<select id="dmMode" style="width:100%">
					<option value="clone">Clone (preserve source)</option>
					<option value="move">Move (wipe source after clone)</option>
				</select>
			</div>
			<div>
				<label id="i18nDmMethodLabel">Copy method (-P / -c)</label>
				<select id="dmMethod" style="width:100%" onchange="dmUpdateMethodFields()">
					<option value="smart">Logical – smart (filesystem-aware)</option>
					<option value="dd">Logical – dd (byte-to-byte)</option>
					<option value="physical">Physical (raw dd of whole disk)</option>
				</select>
			</div>
			<div id="dmLogicalFields" style="display:contents">
				<div>
					<label id="i18nDmAlignLabel">Alignment (-a)</label>
					<select id="dmAlign" style="width:100%">
						<option value="4096">4096 bytes – modern GPT / UEFI</option>
						<option value="512">512 bytes – legacy MBR</option>
					</select>
				</div>
				<div>
					<label id="i18nDmCopyMbrLabel">Copy MBR/GPT header (-B)</label>
					<select id="dmCopyMbr" style="width:100%">
						<option value="yes">yes</option>
						<option value="no">no</option>
					</select>
				</div>
				<div>
					<label id="i18nDmWipeTargetLabel">Wipe target partitions first (-W)</label>
					<select id="dmWipeTarget" style="width:100%">
						<option value="yes">yes</option>
						<option value="no">no</option>
					</select>
				</div>
				<div>
					<label id="i18nDmVerifyLabel">Verify each partition (-V)</label>
					<select id="dmVerify" style="width:100%">
						<option value="no">no</option>
						<option value="yes">yes</option>
					</select>
				</div>
				<div>
					<label id="i18nDmForceFsLabel">Force filesystem type (-f)</label>
					<input id="dmForceFs" type="text" placeholder="auto-detect if empty" style="width:100%">
				</div>
				<div>
					<label id="i18nDmExtraOptsLabel">Extra partclone options (-x)</label>
					<input id="dmExtraOpts" type="text" placeholder="e.g. --debug" style="width:100%">
				</div>
			</div>
			<div id="dmPhysicalFields" style="display:none;contents">
				<div>
					<label id="i18nDmIncludeTailLabel">Include unallocated tail (-T)</label>
					<select id="dmIncludeTail" style="width:100%">
						<option value="no">no (used sectors only)</option>
						<option value="yes">yes (full disk)</option>
					</select>
				</div>
			</div>
			<div>
				<label id="i18nDmUnmountLabel">Unmount partitions first (-u)</label>
				<select id="dmUnmount" style="width:100%">
					<option value="yes">yes</option>
					<option value="no">no</option>
				</select>
			</div>
			<div>
				<label id="i18nDmFsckPassesLabel">FAT pre-clone fsck passes (-F)</label>
				<select id="dmFsckPasses" style="width:100%">
					<option value="2" selected>2 (recommended)</option>
					<option value="1">1</option>
					<option value="0">0 (disabled)</option>
				</select>
			</div>
			<div>
				<label id="i18nDmDdFallbackLabel">dd fallback on smart failure (-b)</label>
				<select id="dmDdFallback" style="width:100%">
					<option value="1" selected>yes (recommended)</option>
					<option value="0">no</option>
				</select>
			</div>
			<div>
				<label id="i18nDmSkipWriteErrLabel">Skip write errors (-W)</label>
				<select id="dmSkipWriteError" style="width:100%">
					<option value="0" selected>no (abort on errors)</option>
					<option value="1">yes (continue on write errors)</option>
				</select>
			</div>
			<div>
				<label id="i18nDmStepDelayLabel">Step delay seconds (-w)</label>
				<input id="dmStepDelay" type="number" min="0" step="1" value="1" placeholder="1" style="width:100%">
			</div>
		</div>
		<div class="pcgi-modal-actions">
			<button type="button" id="pcgiDmCancelBtn">Cancel</button>
			<button type="button" id="pcgiDmOkBtn">Validate and queue</button>
		</div>
	</div>
</div>

<!-- ── Partclone Export Modal ─────────────────────────────────────────────── -->
<div id="pcgiPartcloneExportModal" class="pcgi-modal" aria-hidden="true">
	<div class="pcgi-modal-box" style="max-width:700px;width:96vw">
		<h3 id="pcgiPiExpTitle" class="pcgi-modal-head">Export partition/disk to image</h3>
		<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px 20px;padding:10px 0">
			<div>
				<label id="i18nPiExpSourceLabel">Source partition/disk</label>
				<input id="piExpSource" type="text" readonly style="width:100%;background:#f5f5f5">
			</div>
			<div>
				<label id="i18nPiExpOutputLabel">Output image file (-o)</label>
				<input id="piExpOutput" type="text" placeholder="/var/media/ftp/backup.img" style="width:100%">
			</div>
			<div>
				<label id="i18nPiExpCompressLabel">Compression (-z)</label>
				<select id="piExpCompress" style="width:100%">
					<option value="none">none (raw)</option>
					<option value="gzip">gzip (.gz)</option>
					<option value="bzip2">bzip2 (.bz2)</option>
					<option value="lz4">lz4 (.lz4)</option>
					<option value="zstd">zstd (.zst)</option>
				</select>
			</div>
			<div>
				<label id="i18nPiExpForceFsLabel">Force filesystem type (-f)</label>
				<input id="piExpForceFs" type="text" placeholder="auto-detect if empty" style="width:100%">
			</div>
			<div>
				<label id="i18nPiExpVerifyLabel">Verify image after export (-V)</label>
				<select id="piExpVerify" style="width:100%">
					<option value="no">no</option>
					<option value="yes">yes (partclone.chkimg)</option>
				</select>
			</div>
			<div>
				<label id="i18nPiExpUnmountLabel">Unmount before export (-u)</label>
				<select id="piExpUnmount" style="width:100%">
					<option value="yes">yes</option>
					<option value="no">no</option>
				</select>
			</div>
			<div>
				<label id="i18nPiExpUseDdLabel">Use partclone.dd regardless (-c)</label>
				<select id="piExpUseDd" style="width:100%">
					<option value="no">no (auto-detect fs)</option>
					<option value="yes">yes (raw dd mode)</option>
				</select>
			</div>
			<div>
				<label id="i18nPiExpStepDelayLabel">Step delay seconds (-w)</label>
				<input id="piExpStepDelay" type="number" min="0" step="1" value="1" style="width:100%">
			</div>
			<div style="grid-column:1/-1">
				<label id="i18nPiExpExtraOptsLabel">Extra options (-x)</label>
				<input id="piExpExtraOpts" type="text" placeholder="e.g. --debug" style="width:100%">
			</div>
		</div>
		<div class="pcgi-modal-actions">
			<button type="button" id="pcgiPiExpCancelBtn">Cancel</button>
			<button type="button" id="pcgiPiExpOkBtn">Run export</button>
		</div>
	</div>
</div>

<!-- ── Partclone Import Modal ─────────────────────────────────────────────── -->
<div id="pcgiPartcloneImportModal" class="pcgi-modal" aria-hidden="true">
	<div class="pcgi-modal-box" style="max-width:700px;width:96vw">
		<h3 id="pcgiPiImpTitle" class="pcgi-modal-head">Restore partition/disk from image</h3>
		<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px 20px;padding:10px 0">
			<div>
				<label id="i18nPiImpTargetLabel">Target partition/disk</label>
				<input id="piImpTarget" type="text" readonly style="width:100%;background:#f5f5f5">
			</div>
			<div>
				<label id="i18nPiImpInputLabel">Input image file (-o)</label>
				<input id="piImpInput" type="text" placeholder="/var/media/ftp/backup.img" style="width:100%">
			</div>
			<div>
				<label id="i18nPiImpCompressLabel">Compression (-z)</label>
				<select id="piImpCompress" style="width:100%">
					<option value="none">none (auto-detect from content)</option>
					<option value="gzip">gzip</option>
					<option value="bzip2">bzip2</option>
					<option value="lz4">lz4</option>
					<option value="zstd">zstd</option>
				</select>
			</div>
			<div>
				<label id="i18nPiImpVerifyLabel">Verify image before restore (-V)</label>
				<select id="piImpVerify" style="width:100%">
					<option value="no">no</option>
					<option value="yes">yes (partclone.chkimg)</option>
				</select>
			</div>
			<div>
				<label id="i18nPiImpUnmountLabel">Unmount before restore (-u)</label>
				<select id="piImpUnmount" style="width:100%">
					<option value="yes">yes</option>
					<option value="no">no</option>
				</select>
			</div>
			<div>
				<label id="i18nPiImpStepDelayLabel">Step delay seconds (-w)</label>
				<input id="piImpStepDelay" type="number" min="0" step="1" value="1" style="width:100%">
			</div>
			<div style="grid-column:1/-1">
				<label id="i18nPiImpExtraOptsLabel">Extra options (-x)</label>
				<input id="piImpExtraOpts" type="text" placeholder="e.g. --debug" style="width:100%">
			</div>
		</div>
		<div class="pcgi-modal-actions">
			<button type="button" id="pcgiPiImpCancelBtn">Cancel</button>
			<button type="button" id="pcgiPiImpOkBtn">Run restore</button>
		</div>
	</div>
</div>

<!-- ── Partclone Network Send Modal ──────────────────────────────────────── -->
<div id="pcgiPartcloneNetSendModal" class="pcgi-modal" aria-hidden="true">
	<div class="pcgi-modal-box" style="max-width:700px;width:96vw">
		<h3 id="pcgiPiNsTitle" class="pcgi-modal-head">Send partition over network</h3>
		<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px 20px;padding:10px 0">
			<div>
				<label id="i18nPiNsSourceLabel">Source partition</label>
				<input id="piNsSource" type="text" readonly style="width:100%;background:#f5f5f5">
			</div>
			<div>
				<label id="i18nPiNsTransportLabel">Mode</label>
				<select id="piNsTransport" style="width:100%" onchange="piNsUpdateHostField()">
					<option value="unicast">Unicast (netcat)</option>
					<option value="multicast">Multicast (udp-sender)</option>
				</select>
			</div>
			<div>
				<label id="i18nPiNsHostLabel">Target host IP / Multicast group</label>
				<input id="piNsHost" type="text" placeholder="e.g. 192.168.1.50 or 239.0.0.1" style="width:100%">
			</div>
			<div>
				<label id="i18nPiNsPortLabel">TCP/UDP port (-P)</label>
				<input id="piNsPort" type="number" min="1" max="65535" value="9000" style="width:100%">
			</div>
			<div>
				<label id="i18nPiNsCompressLabel">Compression (-z)</label>
				<select id="piNsCompress" style="width:100%">
					<option value="none">none</option>
					<option value="gzip">gzip</option>
					<option value="lz4">lz4 (fast)</option>
					<option value="zstd">zstd</option>
				</select>
			</div>
			<div>
				<label id="i18nPiNsForceFsLabel">Force filesystem type (-f)</label>
				<input id="piNsForceFs" type="text" placeholder="auto-detect if empty" style="width:100%">
			</div>
			<div>
				<label id="i18nPiNsUnmountLabel">Unmount before send (-u)</label>
				<select id="piNsUnmount" style="width:100%">
					<option value="yes">yes</option>
					<option value="no">no</option>
				</select>
			</div>
			<div>
				<label id="i18nPiNsStepDelayLabel">Step delay seconds (-w)</label>
				<input id="piNsStepDelay" type="number" min="0" step="1" value="1" style="width:100%">
			</div>
		</div>
		<div class="pcgi-modal-actions">
			<button type="button" id="pcgiPiNsCancelBtn">Cancel</button>
			<button type="button" id="pcgiPiNsOkBtn">Start send</button>
		</div>
	</div>
</div>

<!-- ── Partclone Network Receive Modal ───────────────────────────────────── -->
<div id="pcgiPartcloneNetRecvModal" class="pcgi-modal" aria-hidden="true">
	<div class="pcgi-modal-box" style="max-width:700px;width:96vw">
		<h3 id="pcgiPiNrTitle" class="pcgi-modal-head">Receive partition from network</h3>
		<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px 20px;padding:10px 0">
			<div>
				<label id="i18nPiNrTargetLabel">Target partition</label>
				<input id="piNrTarget" type="text" readonly style="width:100%;background:#f5f5f5">
			</div>
			<div>
				<label id="i18nPiNrTransportLabel">Mode</label>
				<select id="piNrTransport" style="width:100%">
					<option value="unicast">Unicast (netcat)</option>
					<option value="multicast">Multicast (udp-receiver)</option>
				</select>
			</div>
			<div>
				<label id="i18nPiNrHostLabel">Source host IP / Multicast group</label>
				<input id="piNrHost" type="text" placeholder="e.g. 192.168.1.10 or 239.0.0.1" style="width:100%">
			</div>
			<div>
				<label id="i18nPiNrPortLabel">TCP/UDP port (-P)</label>
				<input id="piNrPort" type="number" min="1" max="65535" value="9000" style="width:100%">
			</div>
			<div>
				<label id="i18nPiNrCompressLabel">Compression (-z)</label>
				<select id="piNrCompress" style="width:100%">
					<option value="none">none</option>
					<option value="gzip">gzip</option>
					<option value="lz4">lz4 (fast)</option>
					<option value="zstd">zstd</option>
				</select>
			</div>
			<div>
				<label id="i18nPiNrVerifyLabel">Verify after receive (-V)</label>
				<select id="piNrVerify" style="width:100%">
					<option value="no">no</option>
					<option value="yes">yes</option>
				</select>
			</div>
			<div>
				<label id="i18nPiNrUnmountLabel">Unmount before receive (-u)</label>
				<select id="piNrUnmount" style="width:100%">
					<option value="yes">yes</option>
					<option value="no">no</option>
				</select>
			</div>
			<div>
				<label id="i18nPiNrStepDelayLabel">Step delay seconds (-w)</label>
				<input id="piNrStepDelay" type="number" min="0" step="1" value="1" style="width:100%">
			</div>
		</div>
		<div class="pcgi-modal-actions">
			<button type="button" id="pcgiPiNrCancelBtn">Cancel</button>
			<button type="button" id="pcgiPiNrOkBtn">Start receive</button>
		</div>
	</div>
</div>

<!-- ── Ddrescue Modal ─────────────────────────────────────────────────────── -->
<div id="pcgiDdrescueModal" class="pcgi-modal" aria-hidden="true">
	<div class="pcgi-modal-box" style="max-width:700px;width:96vw">
		<h3 id="pcgiDrTitle" class="pcgi-modal-head">Clone with ddrescue (data recovery)</h3>
		<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px 20px;padding:10px 0">
			<div>
				<label id="i18nDrSourceLabel">Source partition/disk</label>
				<input id="drSource" type="text" readonly style="width:100%;background:#f5f5f5">
			</div>
			<div>
				<label id="i18nDrOutputLabel">Output image file (-o)</label>
				<input id="drOutput" type="text" placeholder="/var/media/ftp/rescue.img" style="width:100%">
			</div>
			<div>
				<label id="i18nDrLogLabel">ddrescue log file (-l)</label>
				<input id="drLogFile" type="text" placeholder="auto: output.log" style="width:100%">
			</div>
			<div>
				<label id="i18nDrRetriesLabel">Max retry passes (-r)</label>
				<input id="drRetries" type="number" min="0" step="1" value="3" style="width:100%">
			</div>
			<div>
				<label id="i18nDrUnmountLabel">Unmount before (-u)</label>
				<select id="drUnmount" style="width:100%">
					<option value="yes">yes</option>
					<option value="no">no</option>
				</select>
			</div>
			<div>
				<label id="i18nDrStepDelayLabel">Step delay seconds (-w)</label>
				<input id="drStepDelay" type="number" min="0" step="1" value="1" style="width:100%">
			</div>
			<div style="grid-column:1/-1">
				<label id="i18nDrExtraOptsLabel">Extra ddrescue options (-x)</label>
				<input id="drExtraOpts" type="text" placeholder="e.g. -d -r3" style="width:100%">
			</div>
		</div>
		<div class="pcgi-modal-actions">
			<button type="button" id="pcgiDrCancelBtn">Cancel</button>
			<button type="button" id="pcgiDrOkBtn">Run ddrescue</button>
		</div>
	</div>
</div>

<hr class="pcgi-rule">
<div class="pcgi-toolbar" style="margin-top: 4px;">
	<input id="renamePartInput" type="text" placeholder="new partition name">
	<button type="button" onclick="queueRenamePartition()" id="queueRenameBtn">Set partition name</button>
</div>
<hr class="pcgi-rule">
<div class="pcgi-toolbar" style="margin-top: 4px;">
	<span class="pcgi-flag-hint">Flags: boot, esp, lba, msftdata, swap, raid, hidden, diag, lvm, bios_grub, pmbr_boot</span>
	<select id="flagStateInput">
		<option value="on">on</option>
		<option value="off">off</option>
	</select>
	<input id="flagNameInput" type="text" placeholder="flag name">
	<button type="button" onclick="queueSetFlag()" id="queueFlagBtn">Set flag</button>
</div>
EOF
sec_end

sec_begin "Filesystem operations"
cat <<'EOF'
<div class="pcgi-inline-form">
	<div>
		<label id="i18nFsPartPathLabel">Partition path</label>
		<input id="fsPartitionPath" type="text" placeholder="/dev/sda1">
	</div>
	<div>
		<label id="i18nFsTypeLabel">Filesystem type</label>
		<select id="fsTypeSelect">
			<option value="ext4">ext4</option>
			<option value="ext3">ext3</option>
			<option value="ext2">ext2</option>
			<option value="f2fs">f2fs</option>
			<option value="exfat">exfat</option>
			<option value="ntfs">ntfs</option>
			<option value="fat32">fat32</option>
			<option value="fat16">fat16</option>
			<option value="vfat">vfat</option>
			<option value="auto">auto-detect</option>
		</select>
	</div>
	<div>
		<label id="i18nFsLabelLabel">Label</label>
		<input id="fsLabelInput" type="text" placeholder="optional label">
	</div>
	<div>
		<label id="i18nResizeEndLabel">Resize partition to sector</label>
		<input id="resizeEndSector" type="text" placeholder="new end sector">
	</div>
	<div>
		<label id="i18nResizeEndHumanLabel">Resize target size</label>
		<input id="resizeEndHuman" type="text" placeholder="e.g. 8 GiB">
	</div>
	<div>
		<label id="i18nResizeFsLabel">Resize filesystem too</label>
		<select id="resizeFsSelect">
			<option value="yes" selected>yes (ext2/3/4, ntfs, fat*)</option>
			<option value="no">no</option>
		</select>
	</div>
	<div>
		<label id="i18nExtraOptsLabel" for="extraOptsInput">Advanced options (safe subset)</label>
		<input id="extraOptsInput" type="text" placeholder="e.g. -E lazy_itable_init=0">
	</div>
	<div>
		<label id="i18nMountpointLabel" for="mountpointInput">Mountpoint</label>
		<input id="mountpointInput" type="text" placeholder="/var/media/ftp/sda1">
	</div>
	<div>
		<label id="i18nMountOptsLabel" for="mountOptsInput">Mount options</label>
		<input id="mountOptsInput" type="text" placeholder="rw,noatime">
	</div>
</div>

<div class="pcgi-toolbar" style="margin-top: 8px;">
	<button type="button" onclick="queueResizePartitionFromInputs()" id="queueResizeBtn">Resize partition</button>
	<button type="button" onclick="queueMkfs()" id="queueMkfsBtn">Create filesystem</button>
	<button type="button" onclick="queueSetLabel()" id="queueLabelBtn">Set label</button>
	<button type="button" onclick="queueMountPartition()" id="queueMountBtn">Mount</button>
	<button type="button" onclick="queueUnmountPartition()" id="queueUnmountBtn">Unmount</button>
</div>
<hr class="pcgi-rule">
<div class="pcgi-toolbar" style="margin-top: 4px;">
	<button type="button" onclick="runFsck(false)" id="checkReadonlyBtn">Check filesystem (read-only)</button>
	<button type="button" onclick="runFsck(true)" id="checkRepairBtn">Check/repair filesystem</button>
</div>
EOF
sec_end

sec_begin "Operation queue"
cat <<'EOF'
<p class="pcgi-small" style="margin:0 0 6px;">The <em>Command</em> column is a preview of the main shell command(s) that will run. The backend may add validation and cleanup steps. Operations run in sequence and stop on the first failure. Each step is executed in a separate CGI request, so shell variables are not shared across steps; required values must be passed in parameters or re-detected from disk state. Individual items can be edited or removed by using <strong>Edit</strong> and <strong>Remove</strong> in the Action column.</p>
<div style="overflow-x:auto">
<table class="pcgi-table" id="queueTable" style="table-layout:fixed;min-width:520px">
	<colgroup>
		<col style="width:2.6em">
		<col style="width:12em">
		<col style="width:28%">
		<col style="width:37%">
		<col style="width:7em">
	</colgroup>
	<thead>
		<tr>
			<th>#</th>
			<th>Operation</th>
			<th>Parameters</th>
			<th>Command</th>
			<th>Action</th>
		</tr>
	</thead>
	<tbody id="queueBody"></tbody>
</table>
</div>
<div class="pcgi-toolbar" style="margin-top:8px;">
	<button type="button" id="applyQueueBtn" onclick="applyQueue()">Apply pending operations</button>
	<button type="button" onclick="clearQueue()">Clear queue</button>
</div>
<div style="position:relative">
	<div id="cmdLogBtnBar" style="position:absolute;top:4px;right:18px;z-index:10;display:flex;gap:3px;opacity:0.75">
		<button type="button" onclick="toggleLogFullscreen()" id="fsLogBtn" title="Fullscreen" style="font-size:11px;padding:1px 6px;line-height:1.4;cursor:pointer;display:none">&#x26F6;</button>
		<button type="button" onclick="copyLogToClipboard()" id="copyLogBtn" title="Copy to clipboard" style="font-size:11px;padding:1px 6px;line-height:1.4;cursor:pointer;display:none">&#x2398;</button>
		<button type="button" onclick="clearLogOutput()" id="clearLogBtn" title="Clear log" style="font-size:11px;padding:1px 6px;line-height:1.4;cursor:pointer;display:none">&#x2715;</button>
	</div>
	<pre id="cmdOutput" class="pcgi-log pcgi-ansi-log"></pre>
</div>
EOF
sec_end

cat <<'EOF'
<details id="advancedInfoDetails">
<summary class="pcgi-sec-summary">Advanced information</summary>
EOF

sec_begin "Partition/filesystem metadata"
cat <<'EOF'
<div class="pcgi-toolbar">
	<button type="button" onclick="loadPartitionMetadata()" id="metaBtn" title="Load partition geometry and filesystem metadata for selected partition">Partition metadata</button>
	<span id="metaStatus" class="pcgi-small"></span>
</div>
<p id="i18nMetaExplain" class="pcgi-small">Shows partition geometry and filesystem metadata (size, used/free bytes, model/serial and table details) for the selected partition. Fetches live data from the device without modifying anything.</p>
<div id="metaGraph"></div>
<pre id="metaRawOutput" class="pcgi-log"></pre>
EOF
sec_end

sec_begin "Disk Diagnostics (hdparm, SMART, GPT)"
cat <<'EOF'
<div class="pcgi-toolbar">
	<button type="button" onclick="runDiagnostics('smart_info')">SMART information</button>
	<button type="button" onclick="runDiagnostics('smart_selftest_short')" title="Start SMART short self-test on selected disk, poll until completion (~2 min)">SMART self-test</button>
	<button type="button" onclick="runDiagnostics('badblocks_scan')" title="Read-only bad block scan on selected device (badblocks -sv). May take a long time on large disks.">Badblocks scan</button>
	<button type="button" onclick="runDiagnostics('hdparm_info')">hdparm identify</button>
	<button type="button" onclick="runDiagnostics('gpt_info')">GPT summary</button>
	<button type="button" onclick="runDiagnostics('reload_table')" id="partprobeBtn" title="Reload kernel partition table after partition changes (uses partprobe or blockdev --rereadpt)">Run partprobe</button>
</div>
<p id="i18nDiagExplain" class="pcgi-small">Runs hardware/partition diagnostics on the selected disk: SMART status, hdparm identify output, GPT layout summary, and kernel partition table refresh. Read-only diagnostics except for partprobe.</p>
<pre id="diagOutput" class="pcgi-log"></pre>
EOF
sec_end

sec_begin "Toolchain analysis" "toolchainSection"
cat <<'EOF'
<div class="pcgi-toolbar">
	<button type="button" onclick="analyzeTools()" id="analyzeBtn" title="Check required/optional disk-management commands on this system">Analyze toolchain</button>
</div>
<pre id="toolsOutput" class="pcgi-log"></pre>
EOF
sec_end

cat <<'EOF'
</details>
EOF

# Modals and toast container must live outside any collapsible section so that
# position:fixed overlays remain visible even when toolchainSection is hidden.
cat <<'EOF'
<div id="pcgiToastWrap"></div>

<div id="pcgiFieldHelpModal" class="pcgi-modal" aria-hidden="true">
	<div class="pcgi-modal-box">
		<h3 id="pcgiFieldHelpTitle" class="pcgi-modal-head"></h3>
		<div id="pcgiFieldHelpBody"></div>
		<div class="pcgi-modal-actions">
			<button type="button" id="pcgiFieldHelpCloseBtn">Close</button>
		</div>
	</div>
</div>

<div id="pcgiConfirmModal" class="pcgi-modal" aria-hidden="true">
	<div class="pcgi-modal-box">
		<h3 id="pcgiConfirmTitle" class="pcgi-modal-head">Confirm action</h3>
		<div id="pcgiConfirmText"></div>
		<div class="pcgi-modal-actions">
			<button type="button" id="pcgiConfirmCancelBtn">Cancel</button>
			<button type="button" id="pcgiConfirmOkBtn">Confirm</button>
		</div>
	</div>
</div>

<div id="pcgiHelpModal" class="pcgi-modal" aria-hidden="true">
	<div class="pcgi-modal-box">
		<h3 id="pcgiHelpTitle" class="pcgi-modal-head">Keyboard shortcuts and workflow</h3>
		<div id="pcgiHelpText" class="pcgi-help-list"></div>
		<div class="pcgi-modal-actions">
			<button type="button" id="pcgiHelpCloseBtn">Close</button>
		</div>
	</div>
</div>

<div id="pcgiCmdPreviewModal" class="pcgi-modal" aria-hidden="true">
	<div class="pcgi-modal-box">
		<h3 id="pcgiCmdPreviewTitle" class="pcgi-modal-head">Command preview</h3>
		<div id="pcgiCmdPreviewText" class="pcgi-modal-subtle">Review parameters first; command preview is regenerated automatically.</div>
<div id="pcgiParamsEditorLabel" class="pcgi-modal-subtle">Parameters (editable JSON). You can tune sectors, sizes and options before queueing.</div>
<div class="pcgi-editor-wrap">
<div id="pcgiParamsEditor"></div>
<textarea id="pcgiParamsEditorFallback"></textarea>
</div>
<div class="pcgi-modal-subtle">Command preview (auto-generated from Parameters).</div>
<div class="pcgi-editor-wrap">
<div id="pcgiCommandEditor"></div>
<textarea id="pcgiCommandEditorFallback" readonly></textarea>
</div>
<div id="pcgiParamRangesWrap" class="pcgi-param-ranges-wrap">
<div class="pcgi-modal-subtle" style="margin:0 0 4px;">Numeric ranges with normalized min/max (alignment-aware)</div>
<div id="pcgiParamRanges" class="pcgi-param-ranges pcgi-mono"></div>
</div>


		<div class="pcgi-modal-actions">
			<button type="button" id="pcgiCmdCancelBtn">Cancel</button>
			<button type="button" id="pcgiCmdValidateBtn">Validate and queue</button>
		</div>
	</div>
</div>
EOF

cat <<'EOF'
<script>
window.paceOptions = {
	startOnPageLoad: false,
	ajax: false,
	document: false,
	eventLag: false,
	elements: false,
	restartOnRequestAfter: false,
	restartOnPushState: false
};
</script>
<script src="/ace/ace.js"></script>
<script>
(function () {
	var API_URL = '/cgi-bin/conf/disk-mgmt';
	var translations = {
		en: {
			dangerTitle: 'Danger zone',
			dangerText: 'This interface executes real partitioning commands. Backup your data before applying any operation.',
			dangerUnlock: 'To unlock mutating actions, type YES_I_UNDERSTAND:',
			dangerReadonly: 'Read-only actions (scan, map, diagnostics, filesystem check in read-only mode) do not require unlock.',
			chipNewPartition: 'New partition',
			chipNewPartitionFs: 'New partition with filesystem',
			chipMovePartitionSmart: 'Move partition (smart)',
			chipMovePartitionSector: 'Move partition (sector-by-sector)',
			chipClonePartitionSmart: 'Clone partition (smart)',
			chipClonePartitionSector: 'Clone partition (sector-by-sector)',
			workflowTitle: 'Disk management workflow',
			workflow1: 'Select a disk or a partition and use the context menu (right-click) to choose the available operations.',
			workflow2: 'Drag \u201cMove or clone partition\u201d onto free space to pre-fill the form using the last selected partition as the source. Drag \u201cNew partition\u201d onto free space for quick creation with defaults. Drag the body of a partition onto free space for a smart move.',
			workflow3: 'Resize, move and clone may take several minutes \u2014 do not interrupt execution.',
			workflow4: 'Use metadata view, filesystem checks (fsck/repair), mount/unmount and diagnostics to inspect and maintain partitions.',
			dragHint: 'Right-click on a disk or partition for context menu operations. Drag \u201cMove or clone partition\u201d onto free space to pre-fill the form from the selected partition. Drag \u201cNew partition\u201d onto free space for quick create with defaults. Drag a partition body into free space for smart move. Drag left/right edge to resize.',
			missingCommandsLabel: 'Missing commands:',
			languageLabel: 'Language',
			usbOnlyLabel: 'Device filter',
			chipSourceDeviceLabel: 'Source device',
			chipSourcePartNumLabel: 'Source partition number',
			chipSourcePartPathLabel: 'Source partition path',
			chipTargetMountpointLabel: 'Target mountpoint',
			chipPartcloneVerifyLabel: 'Smart clone verify',
			chipDdBsLabel: 'dd block size',
			helperTitle: 'Keyboard shortcuts and workflow',
			helperText: 'Ctrl+R: refresh map\nCtrl+Shift+A: analyze toolchain\nCtrl+M: load partition metadata\nCtrl+Enter: apply operations\nDelete: delete selected partition\nF1 or ?: open this help\nRight click on partition: context menu actions\nDrag partition left/right edge: resize\nDrag partition to free area: smart move\nDrag smart/sector move/clone chips to free area: exact plan from source fields',
			cmdPreviewTitle: 'Command preview',
			cmdPreviewHint: 'Command preview is read-only and auto-generated from Parameters.',
			toolAllAvailable: 'Toolchain status: all detected commands are available.',
			toolRequiredMissing: 'Toolchain status: required command(s) missing.',
			toolOptionalMissing: 'Toolchain status: some optional commands are missing.',
			toolAnalysisFailed: 'Toolchain status: analysis failed.',
			confirmAction: 'Confirm action',
			confirmQueueApply: 'Apply pending operations?',
			confirmQueueApplyMsg: 'The operations will run real disk commands in sequence. Some operations may take a long time \u2014 be prepared to wait without interrupting execution. Continue?',
			confirmRepair: 'Confirm repair check',
			confirmRepairMsg: 'Repair mode can modify filesystem structures. Continue?',
			confirmDelete: 'Confirm partition deletion',
			confirmDeleteMsg: 'Delete the selected partition?',
			confirmCreate: 'Confirm partition creation',
			confirmCreateMsg: 'Create a partition with the selected geometry?',
			confirmMkfs: 'Confirm filesystem creation',
			confirmMkfsMsg: 'Create filesystem. Existing data will be lost when applied.',
			confirmMove: 'Confirm partition move',
			confirmMoveMsg: 'Move the selected partition to the target free region?',
			confirmClone: 'Confirm partition clone',
			confirmCloneMsg: 'Clone the selected source partition to the target free region?',
			confirmMount: 'Confirm mount request',
			confirmMountMsg: 'Mount the selected partition?',
			mountModalTitle: 'Mount partition',
			mountModalPartLabel: 'Partition',
			mountModalMpLabel: 'Mountpoint',
			mountModalFsLabel: 'Filesystem type',
			mountModalOptsLabel: 'Mount options (optional)',
			confirmUnmount: 'Confirm unmount request',
			confirmUnmountMsg: 'Unmount the selected partition or mountpoint?',
			tQueueEmpty: 'Operation queue is empty.',
			tNeedAck: 'Type YES_I_UNDERSTAND in the safety field first.',
			tNoDevice: 'Select a device first.',
			tNoPartition: 'Select a partition first.',
			tNeedPartPath: 'Partition path required.',
			tNeedResizeInput: 'Partition number and new end sector are required.',
			tNeedStartEnd: 'Start and end sectors are required.',
			tNeedLabel: 'Partition path and label are required.',
			tNeedMkfsType: 'Choose a concrete filesystem type for mkfs.',
			tNeedPartName: 'Select partition and provide a new name.',
			tNeedFlag: 'Select partition and provide flag name.',
			tNeedSourcePart: 'Set source partition path (or source device + number) first.',
			tDropQueuedQuick: 'New partition added from dropped free segment (quick mode).',
			tDropQueuedWithFs: 'New partition added from dropped free segment with Role, Filesystem and Partition name.',
			tDropQueuedMoveSmartChip: 'Smart move plan added from dropped Move partition chip.',
			tDropQueuedMoveSectorChip: 'Sector-by-sector move plan added from dropped Move partition chip.',
			tDropQueuedCloneSmartChip: 'Smart clone plan added from dropped Clone partition chip.',
			tDropQueuedCloneSectorChip: 'Sector-by-sector clone plan added from dropped Clone partition chip.',
			tQueued: 'Operation added.',
			tQueueApplied: 'All operations completed successfully.',
			tContextUnavailable: 'Action unavailable for this selection.',
			tMoveNoSpace: 'Not enough free space for move target.',
			tMoveSame: 'Source and target area overlap or are unchanged.',
			tMetaLoaded: 'Metadata loaded successfully.',
			tNoMetaData: 'No metadata available for this partition.',
			tMapLoaded: 'Map updated',
			tDevices: 'disks',
			tMapLoading: 'Loading device map...',
			tMapError: 'Map load error',
			deviceStripLabel: 'Devices:',
			btnConfirm: 'Confirm',
			btnCancel: 'Cancel',
			btnCreatePartition: 'Create partition',
			btnClose: 'Close',
			warnNoExtended: '\u26a0 No extended partition exists yet. Create one first (role: extended), then add logical partitions inside it.',
			warnPrimaryInExtended: '\u26a0 Cannot create a primary partition inside an extended partition. Use role \u201clogical\u201d instead.',
			pnpTableMsgText: '\u26a0\ufe0f This disk has no partition table yet. Choose a type before creating the first partition.',
			btnValidateQueue: 'Validate and add',
			tDone: 'Done',
			tError: 'Error',
			tQueueApplying: 'Applying {0} pending operation(s)...',
			tQueueAllDone: 'All {0} operation(s) applied successfully.',
			tQueueDiskWarning: 'WARNING: Disk operation is starting now. Do not interrupt power or disconnect storage. This may take several minutes.',
			tQueueStoppedAt: 'Stopped due to failure at step {0}.',
			tQueueErrorAt: 'Error at step {0}: {1}'
		},
		it: {
			dangerTitle: 'Zona pericolosa',
			dangerText: 'Questa interfaccia esegue comandi reali di partizionamento. Esegui un backup prima di applicare operazioni.',
			dangerUnlock: 'Per sbloccare le operazioni di modifica, digita YES_I_UNDERSTAND:',
			dangerReadonly: 'Le azioni in sola lettura (scan, mappa, diagnostica, check read-only) non richiedono sblocco.',
			chipNewPartition: 'Nuova partizione',
			chipNewPartitionFs: 'Nuova partizione con filesystem',
			chipMovePartitionSmart: 'Sposta partizione (smart)',
			chipMovePartitionSector: 'Sposta partizione (settore per settore)',
			chipClonePartitionSmart: 'Clona partizione (smart)',
			chipClonePartitionSector: 'Clona partizione (settore per settore)',
			workflowTitle: 'Workflow gestione dischi',
			workflow1: 'Seleziona un disco o una partizione e usa il menu contestuale (tasto destro) per scegliere le operazioni consentite.',
			workflow2: 'Trascina \u201cMove or clone partition\u201d su uno spazio libero per pre-compilare il form usando l\u2019ultima partizione selezionata come sorgente. Trascina \u201cNuova partizione\u201d sullo spazio libero per la creazione rapida con valori di default. Trascina il corpo di una partizione su spazio libero per lo spostamento smart.',
			workflow3: 'Resize, spostamento e clonazione possono richiedere diversi minuti \u2014 non interrompere l\u2019esecuzione.',
			workflow4: 'Usa vista metadati, controlli filesystem (fsck/riparazione), mount/unmount e diagnostica per ispezionare e manutenere le partizioni.',
			dragHint: 'Tasto destro su disco o partizione per il menu contestuale. Trascina \u201cMove or clone partition\u201d su spazio libero per pre-compilare il form dalla partizione selezionata. Trascina \u201cNuova partizione\u201d su spazio libero per la creazione rapida. Trascina il corpo di una partizione su spazio libero per lo spostamento smart. Trascina il bordo sinistro/destro per il resize.',
			missingCommandsLabel: 'Comandi mancanti:',
			languageLabel: 'Lingua',
			usbOnlyLabel: 'Filtro dispositivi',
			chipSourceDeviceLabel: 'Dispositivo sorgente',
			chipSourcePartNumLabel: 'Numero partizione sorgente',
			chipSourcePartPathLabel: 'Percorso partizione sorgente',
			chipTargetMountpointLabel: 'Mountpoint target',
			chipPartcloneVerifyLabel: 'Verifica clone smart',
			chipDdBsLabel: 'Dimensione blocco dd',
			helperTitle: 'Scorciatoie da tastiera e workflow',
			helperText: 'Ctrl+R: aggiorna mappa\nCtrl+Shift+A: analizza toolchain\nCtrl+M: carica metadati partizione\nCtrl+Invio: applica operazioni\nCanc: elimina partizione selezionata\nF1 o ?: apri aiuto\nClick destro sulla partizione: menu contestuale\nTrascina bordo sinistro/destro partizione: resize\nTrascina partizione su spazio libero: spostamento smart\nTrascina chip smart/settore move/clone su spazio libero: piano esatto dalla sorgente',
			cmdPreviewTitle: 'Anteprima comando',
			cmdPreviewHint: 'Anteprima comando in sola lettura, rigenerata automaticamente dai Parametri.',
			toolAllAvailable: 'Stato toolchain: tutti i comandi rilevati sono disponibili.',
			toolRequiredMissing: 'Stato toolchain: mancano comandi richiesti.',
			toolOptionalMissing: 'Stato toolchain: mancano alcuni comandi opzionali.',
			toolAnalysisFailed: 'Stato toolchain: analisi fallita.',
			confirmAction: 'Conferma azione',
			confirmQueueApply: 'Applicare le operazioni pendenti?',
			confirmQueueApplyMsg: 'Le operazioni eseguiranno comandi reali sul disco in sequenza. Alcune operazioni possono richiedere parecchio tempo \u2014 occorre essere preparati ad attendere senza interrompere l\u2019esecuzione. Continuare?',
			confirmRepair: 'Conferma controllo riparazione',
			confirmRepairMsg: 'La modalita riparazione puo modificare il filesystem. Continuare?',
			confirmDelete: 'Conferma eliminazione partizione',
			confirmDeleteMsg: 'Eliminare la partizione selezionata?',
			confirmCreate: 'Conferma creazione partizione',
			confirmCreateMsg: 'Creare una partizione con la geometria selezionata?',
			confirmMkfs: 'Conferma creazione filesystem',
			confirmMkfsMsg: 'Creare filesystem. I dati esistenti andranno persi quando applicata.',
			confirmMove: 'Conferma spostamento partizione',
			confirmMoveMsg: 'Spostare la partizione selezionata verso lo spazio libero target?',
			confirmClone: 'Conferma clonazione partizione',
			confirmCloneMsg: 'Clonare la partizione sorgente selezionata verso lo spazio libero target?',
			confirmMount: 'Conferma richiesta mount',
			confirmMountMsg: 'Montare la partizione selezionata?',
			mountModalTitle: 'Monta partizione',
			mountModalPartLabel: 'Partizione',
			mountModalMpLabel: 'Punto di mount',
			mountModalFsLabel: 'Tipo filesystem',
			mountModalOptsLabel: 'Opzioni mount (opzionale)',
			confirmUnmount: 'Conferma richiesta unmount',
			confirmUnmountMsg: 'Smontare la partizione o mountpoint selezionato?',
			tQueueEmpty: 'La coda operazioni e vuota.',
			tNeedAck: 'Digita YES_I_UNDERSTAND prima nel campo sicurezza.',
			tNoDevice: 'Seleziona prima un dispositivo.',
			tNoPartition: 'Seleziona prima una partizione.',
			tNeedPartPath: 'Percorso partizione richiesto.',
			tNeedResizeInput: 'Numero partizione e nuovo settore finale sono richiesti.',
			tNeedStartEnd: 'Settore iniziale e finale sono richiesti.',
			tNeedLabel: 'Percorso partizione ed etichetta sono richiesti.',
			tNeedMkfsType: 'Scegli un filesystem concreto per mkfs.',
			tNeedPartName: 'Seleziona una partizione e fornisci un nuovo nome.',
			tNeedFlag: 'Seleziona una partizione e fornisci il nome flag.',
			tNeedSourcePart: 'Imposta prima il percorso partizione sorgente (oppure dispositivo sorgente + numero).',
			tDropQueuedQuick: 'Nuova partizione aggiunta dal segmento libero (modalita rapida).',
			tDropQueuedWithFs: 'Nuova partizione aggiunta dal segmento libero con Role, Filesystem e Partition name.',
			tDropQueuedMoveSmartChip: 'Piano di spostamento smart aggiunto dal chip Sposta partizione.',
			tDropQueuedMoveSectorChip: 'Piano di spostamento settore per settore aggiunto dal chip Sposta partizione.',
			tDropQueuedCloneSmartChip: 'Piano di clonazione smart aggiunto dal chip Clona partizione.',
			tDropQueuedCloneSectorChip: 'Piano di clonazione settore per settore aggiunto dal chip Clona partizione.',
			tQueued: 'Operazione aggiunta.',
			tQueueApplied: 'Tutte le operazioni completate con successo.',
			tContextUnavailable: 'Azione non disponibile per questa selezione.',
			tMoveNoSpace: 'Spazio libero insufficiente per il target di move.',
			tMoveSame: 'Area sorgente e target sovrapposte o uguali.',
			tMetaLoaded: 'Metadati caricati con successo.',
			tNoMetaData: 'Nessun metadato disponibile per questa partizione.',
			tMapLoaded: 'Mappa aggiornata',
			tDevices: 'dischi',
			tMapLoading: 'Caricamento mappa dispositivi...',
			tMapError: 'Errore caricamento mappa',
			deviceStripLabel: 'Dischi:',
			btnConfirm: 'Conferma',
			btnCancel: 'Annulla',
			btnCreatePartition: 'Crea partizione',
			btnClose: 'Chiudi',
			warnNoExtended: '\u26a0 Nessuna partizione estesa presente. Creane prima una (ruolo: extended), poi aggiungi partizioni logiche al suo interno.',
			warnPrimaryInExtended: '\u26a0 Non \u00e8 possibile creare una partizione primaria all\u2019interno di una partizione estesa. Usa il ruolo \u201clogical\u201d.',
			pnpTableMsgText: '\u26a0\ufe0f Il disco non ha ancora una tabella delle partizioni. Scegli il tipo prima di creare la prima partizione.',
			btnValidateQueue: 'Valida e aggiungi',
			tDone: 'Fatto',
			tError: 'Errore',
			tQueueApplying: 'Applicazione di {0} operazione/i pendente/i...',
			tQueueAllDone: 'Tutte le {0} operazione/i applicate con successo.',
			tQueueDiskWarning: 'ATTENZIONE: Operazione disco in corso. Non interrompere alimentazione o staccare lo storage. Potrebbe richiedere alcuni minuti.',
			tQueueStoppedAt: 'Interrotto per errore al passo {0}.',
			tQueueErrorAt: 'Errore al passo {0}: {1}'
		},
		de: {
			dangerTitle: 'Gefahrenbereich',
			dangerText: 'Diese Oberflaeche fuehrt echte Partitionierungsbefehle aus. Vor dem Anwenden unbedingt sichern.',
			dangerUnlock: 'Zum Freigeben von Aenderungen YES_I_UNDERSTAND eingeben:',
			dangerReadonly: 'Nur-Lese-Aktionen (Scan, Karte, Diagnose, read-only Check) benoetigen keine Freigabe.',
			chipNewPartition: 'Neue Partition',
			chipNewPartitionFs: 'Neue Partition mit Dateisystem',
			chipMovePartitionSmart: 'Partition verschieben (smart)',
			chipMovePartitionSector: 'Partition verschieben (sektorweise)',
			chipClonePartitionSmart: 'Partition klonen (smart)',
			chipClonePartitionSector: 'Partition klonen (sektorweise)',
			workflowTitle: 'Datentraegerverwaltung',
			workflow1: 'Geraete aktualisieren und Datentraeger waehlen.',
			workflow2: 'Neue Partition fuer Schnellanlage mit Standardwerten ziehen. Neue Partition mit Dateisystem ziehen, um Role, Filesystem und Partition name aus dem Formular zu uebernehmen. Move or clone partition auf freien Bereich ziehen, um das vorausgefuellte Move/Clone-Formular zu oeffnen. Linken oder rechten Partitionsrand ziehen fuer Resize. Partition in freien Bereich ziehen fuer smarten Move.',
			workflow3: 'Operationen hinzufuegen, pruefen und dann anwenden.',
			workflow4: 'Metadatenansicht, Dateisystem-Pruefung, Mount und Diagnose verwenden.',
			dragHint: 'Neue Partition fuer Schnellanlage mit Standardwerten ziehen. Neue Partition mit Dateisystem ziehen, um Role, Filesystem und Partition name aus dem Formular zu uebernehmen. Move or clone partition auf freien Bereich ziehen, um das vorausgefuellte Move/Clone-Formular zu oeffnen. Linken oder rechten Rand einer Partition ziehen fuer Resize. Partition in freien Bereich ziehen fuer smarten Move.',
			missingCommandsLabel: 'Fehlende Befehle:',
			languageLabel: 'Sprache',
			usbOnlyLabel: 'Geraetefilter',
			chipSourceDeviceLabel: 'Quellgeraet',
			chipSourcePartNumLabel: 'Quell-Partitionsnummer',
			chipSourcePartPathLabel: 'Quell-Partitionspfad',
			chipTargetMountpointLabel: 'Ziel-Mountpoint',
			chipPartcloneVerifyLabel: 'Smart-Clone pruefen',
			chipDdBsLabel: 'dd-Blockgroesse',
			helperTitle: 'Tastenkuerzel und Ablauf',
			helperText: 'Ctrl+R: Karte aktualisieren\nCtrl+Shift+A: Toolchain analysieren\nCtrl+M: Partitions-Metadaten laden\nCtrl+Enter: Operationen anwenden\nEntf: Gewaehlte Partition loeschen\nF1 oder ?: Hilfe oeffnen\nRechtsklick auf Partition: Kontextmenue\nLinken/rechten Partitionsrand ziehen: Resize\nPartition auf freien Bereich ziehen: smarter Move\nSmart/Sektor Move/Clone-Chips auf freien Bereich ziehen: exakter Plan aus Quellfeldern',
			cmdPreviewTitle: 'Befehlsvorschau',
			cmdPreviewHint: 'Befehlsvorschau ist schreibgeschuetzt und wird automatisch aus den Parametern neu erzeugt.',
			toolAllAvailable: 'Toolchain-Status: alle erkannten Befehle sind verfuegbar.',
			toolRequiredMissing: 'Toolchain-Status: erforderliche Befehle fehlen.',
			toolOptionalMissing: 'Toolchain-Status: optionale Befehle fehlen.',
			toolAnalysisFailed: 'Toolchain-Status: Analyse fehlgeschlagen.',
			confirmAction: 'Aktion bestaetigen',
			confirmQueueApply: 'Anstehende Operationen anwenden?',
			confirmQueueApplyMsg: 'Die Operationen fuehren echte Datentraeger-Befehle der Reihe nach aus. Fortfahren?',
			confirmRepair: 'Reparaturpruefung bestaetigen',
			confirmRepairMsg: 'Reparaturmodus kann Dateisystemstrukturen aendern. Fortfahren?',
			confirmDelete: 'Partitionsloeschung bestaetigen',
			confirmDeleteMsg: 'Gewaehlte Partition loeschen?',
			confirmCreate: 'Partitionserstellung bestaetigen',
			confirmCreateMsg: 'Partition mit gewaehlter Geometrie erstellen?',
			confirmMkfs: 'Dateisystemerstellung bestaetigen',
			confirmMkfsMsg: 'Dateisystem erstellen. Vorhandene Daten gehen beim Anwenden verloren.',
			confirmMove: 'Partitionsverschiebung bestaetigen',
			confirmMoveMsg: 'Gewaehlte Partition in den Ziel-Freiraum verschieben?',
			confirmClone: 'Partitionsklon bestaetigen',
			confirmCloneMsg: 'Gewaehlte Quellpartition in den Ziel-Freiraum klonen?',
			confirmMount: 'Mount-Anfrage bestaetigen',
			confirmMountMsg: 'Gewaehlte Partition mounten?',
			mountModalTitle: 'Partition mounten',
			mountModalPartLabel: 'Partition',
			mountModalMpLabel: 'Einhängepunkt',
			mountModalFsLabel: 'Dateisystemtyp',
			mountModalOptsLabel: 'Mount-Optionen (optional)',
			confirmUnmount: 'Unmount-Anfrage bestaetigen',
			confirmUnmountMsg: 'Partition oder Mountpoint unmounten?',
			tQueueEmpty: 'Die Operationsliste ist leer.',
			tNeedAck: 'Bitte zuerst YES_I_UNDERSTAND in das Sicherheitsfeld eingeben.',
			tNoDevice: 'Bitte zuerst ein Geraet auswaehlen.',
			tNoPartition: 'Bitte zuerst eine Partition auswaehlen.',
			tNeedPartPath: 'Partitionspfad erforderlich.',
			tNeedResizeInput: 'Partitionsnummer und neuer Endsektor sind erforderlich.',
			tNeedStartEnd: 'Start- und Endsektor sind erforderlich.',
			tNeedLabel: 'Partitionspfad und Label sind erforderlich.',
			tNeedMkfsType: 'Fuer mkfs einen konkreten Dateisystemtyp waehlen.',
			tNeedPartName: 'Partition auswaehlen und neuen Namen angeben.',
			tNeedFlag: 'Partition auswaehlen und Flag-Namen angeben.',
			tNeedSourcePart: 'Zuerst Quell-Partitionspfad (oder Quellgeraet + Nummer) setzen.',
			tDropQueuedQuick: 'Neue Partition aus freiem Segment hinzugefuegt (Schnellmodus).',
			tDropQueuedWithFs: 'Neue Partition aus freiem Segment mit Role, Filesystem und Partition name hinzugefuegt.',
			tDropQueuedMoveSmartChip: 'Smarter Move-Plan aus gezogenem Partition-verschieben-Chip hinzugefuegt.',
			tDropQueuedMoveSectorChip: 'Sektorweiser Move-Plan aus gezogenem Partition-verschieben-Chip hinzugefuegt.',
			tDropQueuedCloneSmartChip: 'Smarter Clone-Plan aus gezogenem Partition-klonen-Chip hinzugefuegt.',
			tDropQueuedCloneSectorChip: 'Sektorweiser Clone-Plan aus gezogenem Partition-klonen-Chip hinzugefuegt.',
			tQueued: 'Operation hinzugefuegt.',
			tQueueApplied: 'Alle Operationen erfolgreich abgeschlossen.',
			tContextUnavailable: 'Aktion fuer diese Auswahl nicht verfuegbar.',
			tMoveNoSpace: 'Nicht genuegend freier Platz fuer das Move-Ziel.',
			tMoveSame: 'Quell- und Zielbereich ueberlappen oder sind unveraendert.',
			tMetaLoaded: 'Metadaten erfolgreich geladen.',
			tNoMetaData: 'Keine Metadaten fuer diese Partition verfuegbar.',
			tMapLoaded: 'Karte aktualisiert',
			tDevices: 'Datentraeger',
			tMapLoading: 'Geraetekarte wird geladen...',
			tMapError: 'Fehler beim Laden der Karte',
			deviceStripLabel: 'Datentraeger:',
			btnConfirm: 'Bestaetigen',
			btnCancel: 'Abbrechen',
			btnCreatePartition: 'Partition erstellen',
			btnClose: 'Schliessen',
			warnNoExtended: '\u26a0 Keine erweiterte Partition vorhanden. Zuerst eine anlegen (Rolle: extended), dann logische Partitionen darin erstellen.',
			warnPrimaryInExtended: '\u26a0 Innerhalb einer erweiterten Partition kann keine primaere Partition erstellt werden. Rolle \u201elogical\u201c verwenden.',
			pnpTableMsgText: '\u26a0\ufe0f Diese Disk hat noch keine Partitionstabelle. Bitte zuerst einen Typ auswaehlen.',
			btnValidateQueue: 'Bestaetigen und hinzufuegen',
			tDone: 'Fertig',
			tError: 'Fehler',
			tQueueApplying: '{0} anstehende Operation(en) werden angewendet...',
			tQueueAllDone: 'Alle {0} Operation(en) erfolgreich angewendet.',
			tQueueDiskWarning: 'WARNUNG: Festplattenoperation laeuft. Unterbrechung der Stromversorgung und Abtrennen des Speichers vermeiden. Dies kann einige Minuten dauern.',
			tQueueStoppedAt: 'Bei Schritt {0} wegen Fehler gestoppt.',
			tQueueErrorAt: 'Fehler bei Schritt {0}: {1}'
		}
	};

	translations.en = Object.assign({}, translations.en, {
		topButtonsExplain: "Run partprobe refreshes kernel partition table visibility, Analyze toolchain checks required/optional commands, Partition metadata loads partition geometry and filesystem metadata of the selected partition.",
		metaExplain: "Shows partition geometry and filesystem metadata (size, used/free bytes, model/serial and table details) for the selected partition. Read-only view.",
		diagExplain: "Runs hardware/partition diagnostics on the selected disk: SMART status, hdparm identify output and GPT layout summary. Read-only diagnostics.",
		btnRunPartprobe: "Run partprobe",
		btnAnalyzeToolchain: "Analyze toolchain",
		btnPartitionMetadata: "Partition metadata",
		btnLoadMetadataView: "Load metadata view",
		btnToolchainShow: "Show toolchain panel",
		btnToolchainHide: "Hide toolchain panel",
		partprobeHint: "Reload kernel partition table after partition changes",
		analyzeHint: "Check required/optional disk-management commands on this system",
		metadataHint: "Load partition geometry and filesystem metadata for selected partition",
		usbAllDevices: "All block devices",
		usbOnlyDevices: "USB devices only",
		chipMoveOrClone: "Move or clone partition",
		chipVerifyPartition: "Verify partition",
		mkfsModalTitle: "Create filesystem",
		mkfsBtnCreate: "Create filesystem",
		mkfsBtnCancel: "Cancel",
		mkfsFullFmtLabel: "Full format (write zeros, NTFS only)",
		newPartAskTitle: "New partition",
		newPartAskText: "Create a filesystem on the new partition?",
		mcTargetRangeHeading: "Target range",
		mcOptionsHeading: "Options",
		mcTargetStartLabel: "Start sector",
		mcTargetEndLabel: "End sector (inclusive)",
		mcTargetSizeLabel: "Target range size",
		mcModeLabel: "Operation",
		mcSourceDevLabel: "Source device",
		mcSourcePartLabel: "Source partition",
		mcTargetDevLabel: "Target device",
		mcTargetPartLabel: "Target partition (optional)",
		mcCloneMethodLabel: "Clone method",
		mcMountAfterLabel: "Mount after (-o)",
		mcTargetMountLabel: "Target mountpoint (-t)",
		mcVerifyLabel: "Verify after clone (-V)",
		mcAlignmentLabel: "Alignment (-a)  [4096=modern GPT, 512=legacy MBR]",
		mcUnmountBeforeLabel: "Unmount before (-u)",
		mcForceFsLabel: "Force filesystem type (-f)",
		mcExtraOptsLabel: "Extra partclone options (-x)",
		mcStepDelayLabel: "Step delay seconds (-w)",
		mcDdBsLabel: "dd block size",
		mcFsckPassesLabel: "FAT pre-clone fsck passes (-F)",
		mcDdFallbackLabel: "dd fallback on smart failure (-b)",
		mcSkipWriteErrLabel: "Skip write errors (-W)",
		dmFsckPassesLabel: "FAT pre-clone fsck passes (-F)",
		dmDdFallbackLabel: "dd fallback on smart failure (-b)",
		dmSkipWriteErrLabel: "Skip write errors (-W)",
		verifySourceDevLabel: "Source device (A)",
		verifySourcePartLabel: "Source partition (A)",
		verifyTargetDevLabel: "Compare device (B)",
		verifyTargetPartLabel: "Compare partition (B)",
		verifyUnmountLabel: "Unmount before",
		confirmVerify: "Confirm partition verify",
		confirmVerifyMsg: "Compare two partitions byte-by-byte (read-only)?",
		tVerifyQueued: "Verify operation added.",
		tDropQueuedMoveCloneChip: "Move or clone chip dropped – configure and add."
	});
	translations.en = Object.assign({}, translations.en, {
		ctxFreeCreate:     "Create partition",
		ctxFreeMoveClone:  "Move or clone partition here",
		ctxFreeRestore:    "Restore partition from image file",
		ctxFreeReceive:    "Receive partition from network",
		ctxDiskMoveClone: "Disk move or clone",
		dmTitle: "Move or clone disk",
		dmSourceDevLabel: "Source disk (-D)",
		dmTargetDevLabel: "Target disk (-d)",
		dmModeLabel: "Operation (-M)",
		dmMethodLabel: "Copy method (-P / -c)",
		dmAlignLabel: "Alignment (-a)  [4096=modern GPT, 512=legacy MBR]",
		dmCopyMbrLabel: "Copy MBR/GPT header (-B)",
		dmWipeTargetLabel: "Wipe target partitions first (-W)",
		dmVerifyLabel: "Verify each partition (-V)",
		dmForceFsLabel: "Force filesystem type (-f)",
		dmExtraOptsLabel: "Extra partclone options (-x)",
		dmIncludeTailLabel: "Include unallocated tail (-T)",
		dmUnmountLabel: "Unmount partitions first (-u)",
		dmStepDelayLabel: "Step delay seconds (-w)",
		confirmDiskClone: "Confirm disk clone/move",
		confirmDiskCloneMsg: "Clone all partitions from source disk to target disk?",
		tDiskMigrationQueued: "Disk migration operation added."
	});
	translations.it = Object.assign({}, translations.it, {
		topButtonsExplain: "Run partprobe aggiorna la tabella partizioni vista dal kernel, Analyze toolchain controlla i comandi richiesti/opzionali, Partition metadata carica geometria partizione e metadati filesystem della partizione selezionata.",
		metaExplain: "Mostra geometria partizione e metadati filesystem (dimensione, usato/libero, modello/seriale e dettagli tabella) per la partizione selezionata. Vista in sola lettura.",
		diagExplain: "Esegue diagnostica hardware/partizioni sul disco selezionato: stato SMART, output identify di hdparm e riepilogo layout GPT. Diagnostica in sola lettura.",
		btnRunPartprobe: "Esegui partprobe",
		btnAnalyzeToolchain: "Analizza toolchain",
		btnPartitionMetadata: "Metadati partizione",
		btnLoadMetadataView: "Carica vista metadati",
		btnToolchainShow: "Mostra pannello toolchain",
		btnToolchainHide: "Nascondi pannello toolchain",
		partprobeHint: "Ricarica la tabella partizioni nel kernel dopo modifiche alle partizioni",
		analyzeHint: "Controlla disponibilita dei comandi richiesti/opzionali per la gestione disco",
		metadataHint: "Carica geometria partizione e metadati filesystem per la partizione selezionata",
		usbAllDevices: "Tutti i dispositivi a blocchi",
		usbOnlyDevices: "Solo dispositivi USB",
		chipMoveOrClone: "Sposta o clona partizione",
		chipVerifyPartition: "Verifica partizione",
		mkfsModalTitle: "Crea filesystem",
		mkfsBtnCreate: "Crea filesystem",
		mkfsBtnCancel: "Annulla",
		mkfsFullFmtLabel: "Formato completo (scrivi zeri, solo NTFS)",
		newPartAskTitle: "Nuova partizione",
		newPartAskText: "Creare un filesystem sulla nuova partizione?",
		mcTargetRangeHeading: "Range target",
		mcOptionsHeading: "Opzioni",
		mcTargetStartLabel: "Settore iniziale",
		mcTargetEndLabel: "Settore finale (incluso)",
		mcTargetSizeLabel: "Dimensione range target",
		mcModeLabel: "Operazione",
		mcSourceDevLabel: "Dispositivo sorgente",
		mcSourcePartLabel: "Partizione sorgente",
		mcTargetDevLabel: "Dispositivo destinazione",
		mcTargetPartLabel: "Partizione destinazione (opzionale)",
		mcCloneMethodLabel: "Metodo di clonazione",
		mcMountAfterLabel: "Monta dopo (-o)",
		mcTargetMountLabel: "Mountpoint target (-t)",
		mcVerifyLabel: "Verifica dopo clone (-V)",
		mcAlignmentLabel: "Allineamento (-a)  [4096=GPT moderno, 512=MBR legacy]",
		mcUnmountBeforeLabel: "Smonta prima (-u)",
		mcForceFsLabel: "Forza tipo filesystem (-f)",
		mcExtraOptsLabel: "Opzioni partclone extra (-x)",
		mcStepDelayLabel: "Pausa tra passi in secondi (-w)",
		mcDdBsLabel: "Dimensione blocco dd",
		mcFsckPassesLabel: "Passate fsck FAT pre-clone (-F)",
		mcDdFallbackLabel: "Fallback dd su errore smart (-b)",
		mcSkipWriteErrLabel: "Ignora errori di scrittura (-W)",
		dmFsckPassesLabel: "Passate fsck FAT pre-clone (-F)",
		dmDdFallbackLabel: "Fallback dd su errore smart (-b)",
		dmSkipWriteErrLabel: "Ignora errori di scrittura (-W)",
		verifySourceDevLabel: "Dispositivo sorgente (A)",
		verifySourcePartLabel: "Partizione sorgente (A)",
		verifyTargetDevLabel: "Dispositivo da confrontare (B)",
		verifyTargetPartLabel: "Partizione da confrontare (B)",
		verifyUnmountLabel: "Smonta prima",
		confirmVerify: "Conferma verifica partizione",
		confirmVerifyMsg: "Confronto byte per byte tra due partizioni (sola lettura)?",
		tVerifyQueued: "Operazione di verifica aggiunta.",
		tDropQueuedMoveCloneChip: "Chip sposta/clona posizionato – configura e aggiungi."
	});
	translations.it = Object.assign({}, translations.it, {
		ctxFreeCreate:     "Crea partizione",
		ctxFreeMoveClone:  "Sposta o clona partizione qui",
		ctxFreeRestore:    "Ripristina partizione da immagine",
		ctxFreeReceive:    "Ricevi partizione dalla rete",
		ctxDiskMoveClone: "Sposta o clona disco",
		dmTitle: "Sposta o clona disco",
		dmSourceDevLabel: "Disco sorgente (-D)",
		dmTargetDevLabel: "Disco destinazione (-d)",
		dmModeLabel: "Operazione (-M)",
		dmMethodLabel: "Metodo di copia (-P / -c)",
		dmAlignLabel: "Allineamento (-a)  [4096=GPT moderno, 512=MBR legacy]",
		dmCopyMbrLabel: "Copia header MBR/GPT (-B)",
		dmWipeTargetLabel: "Cancella partizioni target prima (-W)",
		dmVerifyLabel: "Verifica ogni partizione (-V)",
		dmForceFsLabel: "Forza tipo filesystem (-f)",
		dmExtraOptsLabel: "Opzioni partclone extra (-x)",
		dmIncludeTailLabel: "Includi settori non allocati finali (-T)",
		dmUnmountLabel: "Smonta partizioni prima (-u)",
		dmStepDelayLabel: "Pausa tra passi in secondi (-w)",
		confirmDiskClone: "Conferma clone/spostamento disco",
		confirmDiskCloneMsg: "Clonare tutte le partizioni dal disco sorgente al disco destinazione?",
		tDiskMigrationQueued: "Operazione di migrazione disco aggiunta."
	});
	translations.de = Object.assign({}, translations.de, {
		topButtonsExplain: "Run partprobe aktualisiert die Kernel-Sicht auf die Partitionstabelle, Analyze toolchain prueft erforderliche/optionale Befehle, Partition metadata laedt Partitionsgeometrie und Dateisystem-Metadaten der gewaehlten Partition.",
		metaExplain: "Zeigt Partitionsgeometrie und Dateisystem-Metadaten (Groesse, belegt/frei, Modell/Seriennummer und Tabellendetails) fuer die gewaehlte Partition. Nur-Lese-Ansicht.",
		diagExplain: "Fuehrt Hardware-/Partitionsdiagnosen fuer den gewaehlten Datentraeger aus: SMART-Status, hdparm-Identify-Ausgabe und GPT-Layout-Zusammenfassung. Nur-Lese-Diagnose.",
		btnRunPartprobe: "Partprobe ausfuehren",
		btnAnalyzeToolchain: "Toolchain analysieren",
		btnPartitionMetadata: "Partitions-Metadaten",
		btnLoadMetadataView: "Metadatenansicht laden",
		btnToolchainShow: "Toolchain-Panel anzeigen",
		btnToolchainHide: "Toolchain-Panel ausblenden",
		partprobeHint: "Kernel-Partitionstabelle nach Partitionsaenderungen neu laden",
		analyzeHint: "Erforderliche/optionale Befehle fuer die Datentraegerverwaltung pruefen",
		metadataHint: "Partitionsgeometrie und Dateisystem-Metadaten fuer die gewaehlte Partition laden",
		usbAllDevices: "Alle Blockgeraete",
		usbOnlyDevices: "Nur USB-Geraete",
		chipMoveOrClone: "Partition verschieben oder klonen",
		chipVerifyPartition: "Partition pruefen",
		mkfsModalTitle: "Dateisystem erstellen",
		mkfsBtnCreate: "Dateisystem erstellen",
		mkfsBtnCancel: "Abbrechen",
		mkfsFullFmtLabel: "Vollformat (Nullen schreiben, nur NTFS)",
		newPartAskTitle: "Neue Partition",
		newPartAskText: "Dateisystem auf der neuen Partition erstellen?",
		mcTargetRangeHeading: "Zielbereich",
		mcOptionsHeading: "Optionen",
		mcTargetStartLabel: "Startsektor",
		mcTargetEndLabel: "Endsektor (einschliesslich)",
		mcTargetSizeLabel: "Groesse Zielbereich",
		mcModeLabel: "Vorgang",
		mcSourceDevLabel: "Quellgeraet",
		mcSourcePartLabel: "Quellpartition",
		mcTargetDevLabel: "Zielgeraet",
		mcTargetPartLabel: "Zielpartition (optional)",
		mcCloneMethodLabel: "Klonmethode",
		mcMountAfterLabel: "Einhaengen nach Abschluss (-o)",
		mcTargetMountLabel: "Ziel-Mountpoint (-t)",
		mcVerifyLabel: "Pruefen nach Klon (-V)",
		mcAlignmentLabel: "Ausrichtung (-a)  [4096=modernes GPT, 512=Legacy-MBR]",
		mcUnmountBeforeLabel: "Vorher aushaengen (-u)",
		mcForceFsLabel: "Dateisystemtyp erzwingen (-f)",
		mcExtraOptsLabel: "Zusaetzliche partclone-Optionen (-x)",
		mcStepDelayLabel: "Schritt-Pause in Sekunden (-w)",
		mcDdBsLabel: "dd-Blockgroesse",
		mcFsckPassesLabel: "FAT-Vorab-fsck-Durchgaenge (-F)",
		mcDdFallbackLabel: "dd-Fallback bei Smart-Fehler (-b)",
		mcSkipWriteErrLabel: "Schreibfehler ueberspringen (-W)",
		dmFsckPassesLabel: "FAT-Vorab-fsck-Durchgaenge (-F)",
		dmDdFallbackLabel: "dd-Fallback bei Smart-Fehler (-b)",
		dmSkipWriteErrLabel: "Schreibfehler ueberspringen (-W)",
		verifySourceDevLabel: "Quellgeraet (A)",
		verifySourcePartLabel: "Quellpartition (A)",
		verifyTargetDevLabel: "Vergleichsgeraet (B)",
		verifyTargetPartLabel: "Vergleichspartition (B)",
		verifyUnmountLabel: "Vorher aushaengen",
		confirmVerify: "Partitionspruefung bestaetigen",
		confirmVerifyMsg: "Zwei Partitionen byteweise vergleichen (nur lesend)?",
		tVerifyQueued: "Pruefungsoperation hinzugefuegt.",
		tDropQueuedMoveCloneChip: "Verschieben/Klonen-Chip abgelegt – konfigurieren und hinzufuegen."
	});
	translations.de = Object.assign({}, translations.de, {
		ctxFreeCreate:     "Partition erstellen",
		ctxFreeMoveClone:  "Partition hierher verschieben oder klonen",
		ctxFreeRestore:    "Partition aus Image wiederherstellen",
		ctxFreeReceive:    "Partition aus Netzwerk empfangen",
		ctxDiskMoveClone: "Datentrager verschieben oder klonen",
		dmTitle: "Datentrager verschieben oder klonen",
		dmSourceDevLabel: "Quelldatentrager (-D)",
		dmTargetDevLabel: "Zieldatentrager (-d)",
		dmModeLabel: "Vorgang (-M)",
		dmMethodLabel: "Kopiermethode (-P / -c)",
		dmAlignLabel: "Ausrichtung (-a)  [4096=modernes GPT, 512=Legacy-MBR]",
		dmCopyMbrLabel: "MBR/GPT-Header kopieren (-B)",
		dmWipeTargetLabel: "Zielpartitionen vorher loeschen (-W)",
		dmVerifyLabel: "Jede Partition pruefen (-V)",
		dmForceFsLabel: "Dateisystemtyp erzwingen (-f)",
		dmExtraOptsLabel: "Zusaetzliche partclone-Optionen (-x)",
		dmIncludeTailLabel: "Nicht allokierten Tail einschliessen (-T)",
		dmUnmountLabel: "Partitionen vorher aushaengen (-u)",
		dmStepDelayLabel: "Schritt-Pause in Sekunden (-w)",
		confirmDiskClone: "Datentragerklon/-verschiebung bestaetigen",
		confirmDiskCloneMsg: "Alle Partitionen vom Quelldatentrager auf den Zieldatentrager klonen?",
		tDiskMigrationQueued: "Disk-Migrationsoperation hinzugefuegt."
	});
	translations.en = Object.assign({}, translations.en, {
		piExpTitle: "Export partition/disk to image",
		piExpSourceLabel: "Source partition/disk",
		piExpOutputLabel: "Output image file (-o)",
		piExpCompressLabel: "Compression (-z)",
		piExpForceFsLabel: "Force filesystem type (-f)",
		piExpVerifyLabel: "Verify after export (-V)",
		piExpUnmountLabel: "Unmount before export (-u)",
		piExpUseDdLabel: "Use partclone.dd regardless (-c)",
		piExpStepDelayLabel: "Step delay seconds (-w)",
		piExpExtraOptsLabel: "Extra options (-x)",
		piImpTitle: "Restore partition/disk from image",
		piImpTargetLabel: "Target partition/disk",
		piImpInputLabel: "Input image file (-o)",
		piImpCompressLabel: "Compression (-z)",
		piImpVerifyLabel: "Verify before restore (-V)",
		piImpUnmountLabel: "Unmount before restore (-u)",
		piImpStepDelayLabel: "Step delay seconds (-w)",
		piImpExtraOptsLabel: "Extra options (-x)",
		piNsTitle: "Send partition over network",
		piNsSourceLabel: "Source partition",
		piNsTransportLabel: "Mode",
		piNsHostLabel: "Target host IP / Multicast group",
		piNsPortLabel: "TCP/UDP port (-P)",
		piNsCompressLabel: "Compression (-z)",
		piNsForceFsLabel: "Force filesystem type (-f)",
		piNsUnmountLabel: "Unmount before send (-u)",
		piNsStepDelayLabel: "Step delay seconds (-w)",
		piNrTitle: "Receive partition from network",
		piNrTargetLabel: "Target partition",
		piNrTransportLabel: "Mode",
		piNrHostLabel: "Source host IP / Multicast group",
		piNrPortLabel: "TCP/UDP port (-P)",
		piNrCompressLabel: "Compression (-z)",
		piNrVerifyLabel: "Verify after receive (-V)",
		piNrUnmountLabel: "Unmount before receive (-u)",
		piNrStepDelayLabel: "Step delay seconds (-w)",
		drTitle: "Clone with ddrescue (data recovery)",
		drSourceLabel: "Source partition/disk",
		drOutputLabel: "Output image file (-o)",
		drLogLabel: "ddrescue log file (-l)",
		drRetriesLabel: "Max retry passes (-r)",
		drUnmountLabel: "Unmount before (-u)",
		drStepDelayLabel: "Step delay seconds (-w)",
		drExtraOptsLabel: "Extra ddrescue options (-x)",
		confirmPiExp: "Confirm image export",
		confirmPiExpMsg: "Export partition/disk to image file? This is a read operation and safe.",
		confirmPiImp: "Confirm image restore",
		confirmPiImpMsg: "Restore partition/disk from image? ALL EXISTING DATA ON TARGET WILL BE OVERWRITTEN.",
		confirmNsSend: "Confirm network send",
		confirmNsSendMsg: "Send partition over network? Listening on specified port.",
		confirmNrRecv: "Confirm network receive",
		confirmNrRecvMsg: "Receive and restore partition from network? ALL EXISTING DATA ON TARGET WILL BE OVERWRITTEN.",
		confirmDr: "Confirm ddrescue",
		confirmDrMsg: "Run ddrescue clone to image file? The output file will be created/overwritten."
	});
	translations.it = Object.assign({}, translations.it, {
		piExpTitle: "Esporta partizione/disco su immagine",
		piExpSourceLabel: "Partizione/disco sorgente",
		piExpOutputLabel: "File immagine di output (-o)",
		piExpCompressLabel: "Compressione (-z)",
		piExpForceFsLabel: "Forza tipo filesystem (-f)",
		piExpVerifyLabel: "Verifica dopo export (-V)",
		piExpUnmountLabel: "Smonta prima dell'export (-u)",
		piExpUseDdLabel: "Usa partclone.dd comunque (-c)",
		piExpStepDelayLabel: "Pausa tra passi in secondi (-w)",
		piExpExtraOptsLabel: "Opzioni extra (-x)",
		piImpTitle: "Ripristina partizione/disco da immagine",
		piImpTargetLabel: "Partizione/disco destinazione",
		piImpInputLabel: "File immagine di input (-o)",
		piImpCompressLabel: "Compressione (-z)",
		piImpVerifyLabel: "Verifica prima del ripristino (-V)",
		piImpUnmountLabel: "Smonta prima del ripristino (-u)",
		piImpStepDelayLabel: "Pausa tra passi in secondi (-w)",
		piImpExtraOptsLabel: "Opzioni extra (-x)",
		piNsTitle: "Invia partizione tramite rete",
		piNsSourceLabel: "Partizione sorgente",
		piNsTransportLabel: "Modalita",
		piNsHostLabel: "IP host destinatario / Gruppo multicast",
		piNsPortLabel: "Porta TCP/UDP (-P)",
		piNsCompressLabel: "Compressione (-z)",
		piNsForceFsLabel: "Forza tipo filesystem (-f)",
		piNsUnmountLabel: "Smonta prima dell'invio (-u)",
		piNsStepDelayLabel: "Pausa tra passi in secondi (-w)",
		piNrTitle: "Ricevi partizione dalla rete",
		piNrTargetLabel: "Partizione destinazione",
		piNrTransportLabel: "Modalita",
		piNrHostLabel: "IP host sorgente / Gruppo multicast",
		piNrPortLabel: "Porta TCP/UDP (-P)",
		piNrCompressLabel: "Compressione (-z)",
		piNrVerifyLabel: "Verifica dopo ricezione (-V)",
		piNrUnmountLabel: "Smonta prima della ricezione (-u)",
		piNrStepDelayLabel: "Pausa tra passi in secondi (-w)",
		drTitle: "Clone con ddrescue (recupero dati)",
		drSourceLabel: "Partizione/disco sorgente",
		drOutputLabel: "File immagine di output (-o)",
		drLogLabel: "File log ddrescue (-l)",
		drRetriesLabel: "Tentativi massimi di retry (-r)",
		drUnmountLabel: "Smonta prima (-u)",
		drStepDelayLabel: "Pausa tra passi in secondi (-w)",
		drExtraOptsLabel: "Opzioni ddrescue extra (-x)",
		confirmPiExp: "Conferma export immagine",
		confirmPiExpMsg: "Esportare partizione/disco su file immagine? E un'operazione di lettura.",
		confirmPiImp: "Conferma ripristino immagine",
		confirmPiImpMsg: "Ripristinare partizione/disco dall'immagine? TUTTI I DATI SUL TARGET SARANNO SOVRASCRITTI.",
		confirmNsSend: "Conferma invio di rete",
		confirmNsSendMsg: "Inviare partizione tramite rete sulla porta specificata?",
		confirmNrRecv: "Conferma ricezione di rete",
		confirmNrRecvMsg: "Ricevere e ripristinare partizione dalla rete? TUTTI I DATI SUL TARGET SARANNO SOVRASCRITTI.",
		confirmDr: "Conferma ddrescue",
		confirmDrMsg: "Eseguire clone ddrescue su file immagine? Il file di output sara creato/sovrascritto."
	});
	translations.de = Object.assign({}, translations.de, {
		piExpTitle: "Partition/Datentraeger als Image exportieren",
		piExpSourceLabel: "Quellpartition/-datentraeger",
		piExpOutputLabel: "Image-Datei Ausgabe (-o)",
		piExpCompressLabel: "Komprimierung (-z)",
		piExpForceFsLabel: "Dateisystemtyp erzwingen (-f)",
		piExpVerifyLabel: "Nach Export pruefen (-V)",
		piExpUnmountLabel: "Vor Export aushaengen (-u)",
		piExpUseDdLabel: "partclone.dd immer verwenden (-c)",
		piExpStepDelayLabel: "Schritt-Pause in Sekunden (-w)",
		piExpExtraOptsLabel: "Zusaetzliche Optionen (-x)",
		piImpTitle: "Partition/Datentraeger aus Image wiederherstellen",
		piImpTargetLabel: "Zielpartition/-datentraeger",
		piImpInputLabel: "Image-Datei Eingabe (-o)",
		piImpCompressLabel: "Komprimierung (-z)",
		piImpVerifyLabel: "Vor Wiederherstellung pruefen (-V)",
		piImpUnmountLabel: "Vor Wiederherstellung aushaengen (-u)",
		piImpStepDelayLabel: "Schritt-Pause in Sekunden (-w)",
		piImpExtraOptsLabel: "Zusaetzliche Optionen (-x)",
		piNsTitle: "Partition ueber Netzwerk senden",
		piNsSourceLabel: "Quellpartition",
		piNsTransportLabel: "Modus",
		piNsHostLabel: "Ziel-IP / Multicast-Gruppe",
		piNsPortLabel: "TCP/UDP-Port (-P)",
		piNsCompressLabel: "Komprimierung (-z)",
		piNsForceFsLabel: "Dateisystemtyp erzwingen (-f)",
		piNsUnmountLabel: "Vor dem Senden aushaengen (-u)",
		piNsStepDelayLabel: "Schritt-Pause in Sekunden (-w)",
		piNrTitle: "Partition vom Netzwerk empfangen",
		piNrTargetLabel: "Zielpartition",
		piNrTransportLabel: "Modus",
		piNrHostLabel: "Quell-IP / Multicast-Gruppe",
		piNrPortLabel: "TCP/UDP-Port (-P)",
		piNrCompressLabel: "Komprimierung (-z)",
		piNrVerifyLabel: "Nach Empfang pruefen (-V)",
		piNrUnmountLabel: "Vor Empfang aushaengen (-u)",
		piNrStepDelayLabel: "Schritt-Pause in Sekunden (-w)",
		drTitle: "Klon mit ddrescue (Datenrettung)",
		drSourceLabel: "Quellpartition/-datentraeger",
		drOutputLabel: "Image-Datei Ausgabe (-o)",
		drLogLabel: "ddrescue-Protokolldatei (-l)",
		drRetriesLabel: "Max. Wiederholungsversuche (-r)",
		drUnmountLabel: "Vorher aushaengen (-u)",
		drStepDelayLabel: "Schritt-Pause in Sekunden (-w)",
		drExtraOptsLabel: "Zusaetzliche ddrescue-Optionen (-x)",
		confirmPiExp: "Image-Export bestaetigen",
		confirmPiExpMsg: "Partition/Datentraeger als Image-Datei exportieren? Nur-Lese-Vorgang.",
		confirmPiImp: "Image-Wiederherstellung bestaetigen",
		confirmPiImpMsg: "Partition/Datentraeger aus Image wiederherstellen? ALLE DATEN AUF DEM ZIEL WERDEN UEBERSCHRIEBEN.",
		confirmNsSend: "Netzwerksendung bestaetigen",
		confirmNsSendMsg: "Partition ueber Netzwerk auf dem angegebenen Port senden?",
		confirmNrRecv: "Netzwerkempfang bestaetigen",
		confirmNrRecvMsg: "Partition vom Netzwerk empfangen und wiederherstellen? ALLE DATEN AUF DEM ZIEL WERDEN UEBERSCHRIEBEN.",
		confirmDr: "ddrescue bestaetigen",
		confirmDrMsg: "ddrescue-Klon in Image-Datei erstellen? Die Ausgabedatei wird erstellt/ueberschrieben."
	});
	translations.fr = Object.assign({}, translations.en, {
		languageLabel: "Langue",
		usbOnlyLabel: "Filtre peripheriques",
		deviceStripLabel: "Peripheriques:",
		topButtonsExplain: "Run partprobe rafraichit la table de partitions du noyau, Analyze toolchain verifie les commandes requises/optionnelles, Partition metadata charge la geometrie et les metadonnees de la partition selectionnee.",
		metaExplain: "Affiche la geometrie de partition et les metadonnees du systeme de fichiers pour la partition selectionnee. Vue en lecture seule.",
		diagExplain: "Execute des diagnostics materiel/partition: SMART, hdparm identify et resume GPT. Lecture seule.",
		btnRunPartprobe: "Executer partprobe",
		btnAnalyzeToolchain: "Analyser la toolchain",
		btnPartitionMetadata: "Metadonnees partition",
		btnLoadMetadataView: "Charger vue metadonnees",
		btnToolchainShow: "Afficher panneau toolchain",
		btnToolchainHide: "Masquer panneau toolchain",
		partprobeHint: "Recharger la table de partitions du noyau apres modifications",
		analyzeHint: "Verifier les commandes requises/optionnelles de gestion disque",
		metadataHint: "Charger geometrie et metadonnees de la partition selectionnee",
		usbAllDevices: "Tous les peripheriques bloc",
		usbOnlyDevices: "Peripheriques USB uniquement",
		tDone: "Termine",
		tError: "Erreur",
		tQueueApplying: "Application de {0} operation(s) en attente...",
		tQueueAllDone: "Les {0} operation(s) appliquees avec succes.",
		tQueueDiskWarning: "ATTENTION: Operation disque en cours. Ne pas interrompre l'alimentation ni deconnecter le stockage. Cela peut prendre plusieurs minutes.",
		tQueueStoppedAt: "Arret a l'etape {0} suite a une erreur.",
		tQueueErrorAt: "Erreur a l'etape {0}: {1}"
	});
	translations.es = Object.assign({}, translations.en, {
		languageLabel: "Idioma",
		usbOnlyLabel: "Filtro de dispositivos",
		deviceStripLabel: "Dispositivos:",
		topButtonsExplain: "Run partprobe actualiza la tabla de particiones del kernel, Analyze toolchain verifica comandos requeridos/opcionales, Partition metadata carga geometria y metadatos de la particion seleccionada.",
		metaExplain: "Muestra la geometria de particion y metadatos del sistema de archivos para la particion seleccionada. Vista de solo lectura.",
		diagExplain: "Ejecuta diagnostico de hardware/particiones: SMART, hdparm identify y resumen GPT. Solo lectura.",
		btnRunPartprobe: "Ejecutar partprobe",
		btnAnalyzeToolchain: "Analizar toolchain",
		btnPartitionMetadata: "Metadatos de particion",
		btnLoadMetadataView: "Cargar vista de metadatos",
		btnToolchainShow: "Mostrar panel de toolchain",
		btnToolchainHide: "Ocultar panel de toolchain",
		partprobeHint: "Recargar la tabla de particiones del kernel tras cambios",
		analyzeHint: "Comprobar comandos requeridos/opcionales de gestion de discos",
		metadataHint: "Cargar geometria y metadatos de la particion seleccionada",
		usbAllDevices: "Todos los dispositivos de bloque",
		usbOnlyDevices: "Solo dispositivos USB",
		tDone: "Hecho",
		tError: "Error",
		tQueueApplying: "Aplicando {0} operacion(es) pendiente(s)...",
		tQueueAllDone: "Todas las {0} operacion(es) aplicadas con exito.",
		tQueueDiskWarning: "ADVERTENCIA: Operacion de disco en curso. No interrumpir la alimentacion ni desconectar el almacenamiento. Puede tardar varios minutos.",
		tQueueStoppedAt: "Detenido por error en el paso {0}.",
		tQueueErrorAt: "Error en el paso {0}: {1}"
	});

	var state = {
		devices: [],
		selectedDevice: '',
		selectedPartDevice: '',
		partSelectionByDisk: {},
		queue: [],
		queueResolvedTargets: {},
		selectedPart: null,
		selectedComponent: null,
		dragCtx: null,
		toolStatus: null,
		language: 'en',
		usbOnly: false,
		contextTarget: null,
		contextMenuHideTimer: null,
		dryRun: false,
		aceEditor: null,
		paramsAceEditor: null,
		paramsAceBound: false,
		paramEditorSyncTimer: null,
		previewEditContext: null,
		mapDragActive: false,
		partitionDragInfo: null,
		sectorSyncLock: false
	};

	function t(key) {
		var langMap = translations[state.language] || translations.en;
		if (langMap && Object.prototype.hasOwnProperty.call(langMap, key)) {
			return langMap[key];
		}
		return (translations.en && translations.en[key]) || key;
	}

	// Translate with positional placeholders: tf('key', arg0, arg1, ...)
	// Replaces {0}, {1}, ... in the translated string.
	function tf(key) {
		var s = t(key);
		for (var i = 1; i < arguments.length; i++) {
			s = s.replace('{' + (i - 1) + '}', String(arguments[i]));
		}
		return s;
	}

	function clampNumber(v, minV, maxV) {
		var n = Number(v);
		if (!isFinite(n)) n = minV;
		if (n < minV) n = minV;
		if (n > maxV) n = maxV;
		return n;
	}

	function computeMoveDropTargetStart(ev, freeSeg, moveSize, grabRatio) {
		var freeStart = Number(freeSeg && freeSeg.start || 0);
		var freeEnd = Number(freeSeg && freeSeg.end || 0);
		var size = Number(moveSize || 0);
		if (!isFinite(freeStart) || !isFinite(freeEnd) || !isFinite(size) || size <= 0 || freeEnd < freeStart) {
			return NaN;
		}

		var minStart = freeStart;
		var maxStart = freeEnd - size + 1;
		if (maxStart < minStart) return NaN;

		var ratio = clampNumber(grabRatio, 0, 1);
		var relRatio = 0;
		var tgt = ev && (ev.currentTarget || ev.target);
		if (tgt && tgt.getBoundingClientRect) {
			var rect = tgt.getBoundingClientRect();
			if (rect.width > 0) {
				var relX = (ev.clientX || 0) - rect.left;
				relX = clampNumber(relX, 0, rect.width);
				relRatio = relX / rect.width;
			}
		}

		var freeSpan = freeEnd - freeStart;
		var dropSector = freeStart + Math.round(relRatio * freeSpan);
		var grabOffset = Math.round(ratio * Math.max(0, size - 1));
		var targetStart = dropSector - grabOffset;
		targetStart = Math.floor(clampNumber(targetStart, minStart, maxStart));
		// Snap to 8-sector (4096-byte) alignment
		var aligned = Math.round(targetStart / 8) * 8;
		aligned = clampNumber(aligned, minStart, maxStart);
		return aligned;
	}

	function detectLanguage() {
		var browser = (navigator.language || 'en').toLowerCase();
		if (browser.indexOf('fr') === 0) return 'fr';
		if (browser.indexOf('es') === 0) return 'es';
		if (browser.indexOf('it') === 0) return 'it';
		if (browser.indexOf('de') === 0) return 'de';
		return 'en';
	}

	function applyTranslations() {
		var map = {
			i18nDangerTitle: 'dangerTitle',
			i18nDangerText: 'dangerText',
			i18nDangerUnlock: 'dangerUnlock',
			i18nDangerReadonly: 'dangerReadonly',
			i18nWorkflowTitle: 'workflowTitle',
			i18nWorkflow1: 'workflow1',
			i18nWorkflow2: 'workflow2',
			i18nWorkflow3: 'workflow3',
			i18nWorkflow4: 'workflow4',
			newPartChip: 'chipNewPartition',
			verifyPartChip: 'chipVerifyPartition',
			moveClonePartChip: 'chipMoveOrClone',
			i18nDragHint: 'dragHint',
			i18nTopButtonsExplain: 'topButtonsExplain',
			i18nMetaExplain: 'metaExplain',
			i18nDiagExplain: 'diagExplain',
			i18nDeviceStripLabel: 'deviceStripLabel',
			i18nMissingCommandsLabel: 'missingCommandsLabel',
			i18nLanguageLabel: 'languageLabel',
			i18nUsbOnlyLabel: 'usbOnlyLabel',
			i18nMcTargetRangeHeading: 'mcTargetRangeHeading',
			i18nMcOptionsHeading: 'mcOptionsHeading',
			i18nMcTargetStartLabel: 'mcTargetStartLabel',
			i18nMcTargetEndLabel: 'mcTargetEndLabel',
			i18nMcTargetSizeLabel: 'mcTargetSizeLabel',
			i18nMcModeLabel: 'mcModeLabel',
			i18nMcSourceDevLabel: 'mcSourceDevLabel',
			i18nMcSourcePartLabel: 'mcSourcePartLabel',
			i18nMcTargetDevLabel: 'mcTargetDevLabel',
			i18nMcTargetPartLabel: 'mcTargetPartLabel',
			i18nMcCloneMethodLabel: 'mcCloneMethodLabel',
			i18nMcMountAfterLabel: 'mcMountAfterLabel',
			i18nMcTargetMountLabel: 'mcTargetMountLabel',
			i18nMcVerifyLabel: 'mcVerifyLabel',
			i18nMcAlignmentLabel: 'mcAlignmentLabel',
			i18nMcUnmountBeforeLabel: 'mcUnmountBeforeLabel',
			i18nMcForceFsLabel: 'mcForceFsLabel',
			i18nMcExtraOptsLabel: 'mcExtraOptsLabel',
			i18nMcStepDelayLabel: 'mcStepDelayLabel',
			i18nMcDdBsLabel: 'mcDdBsLabel',
			i18nVerifySourceDevLabel: 'verifySourceDevLabel',
			i18nVerifySourcePartLabel: 'verifySourcePartLabel',
			i18nVerifyTargetDevLabel: 'verifyTargetDevLabel',
			i18nVerifyTargetPartLabel: 'verifyTargetPartLabel',
			i18nVerifyUnmountLabel: 'verifyUnmountLabel',
			i18nDmTitle: 'dmTitle',
			i18nDmSourceDevLabel: 'dmSourceDevLabel',
			i18nDmTargetDevLabel: 'dmTargetDevLabel',
			i18nDmModeLabel: 'dmModeLabel',
			i18nDmMethodLabel: 'dmMethodLabel',
			i18nDmAlignLabel: 'dmAlignLabel',
			i18nDmCopyMbrLabel: 'dmCopyMbrLabel',
			i18nDmWipeTargetLabel: 'dmWipeTargetLabel',
			i18nDmVerifyLabel: 'dmVerifyLabel',
			i18nDmForceFsLabel: 'dmForceFsLabel',
			i18nDmExtraOptsLabel: 'dmExtraOptsLabel',
			i18nDmIncludeTailLabel: 'dmIncludeTailLabel',
			i18nDmUnmountLabel: 'dmUnmountLabel',
			i18nDmStepDelayLabel: 'dmStepDelayLabel',
			i18nMountModalPartLabel: 'mountModalPartLabel',
			i18nMountModalMpLabel: 'mountModalMpLabel',
			i18nMountModalFsLabel: 'mountModalFsLabel',
			i18nMountModalOptsLabel: 'mountModalOptsLabel',
		};
		for (var id in map) {
			if (!Object.prototype.hasOwnProperty.call(map, id)) continue;
			var el = document.getElementById(id);
			if (!el) continue;
			// Preserve any injected help buttons (child <button> nodes) while
			// replacing the text content for the current language.
			var helpBtns = el.querySelectorAll('button.pcgi-help-btn');
			el.textContent = t(map[id]);
			for (var bi = 0; bi < helpBtns.length; bi++) {
				el.appendChild(helpBtns[bi]);
			}
		}
		var confirmBtn = document.getElementById('pcgiConfirmOkBtn');
		var cancelBtn = document.getElementById('pcgiConfirmCancelBtn');
		var closeBtn = document.getElementById('pcgiHelpCloseBtn');
		var cmdCancelBtn = document.getElementById('pcgiCmdCancelBtn');
		var cmdValidateBtn = document.getElementById('pcgiCmdValidateBtn');
		if (confirmBtn) confirmBtn.textContent = t('btnConfirm');
		if (cancelBtn) cancelBtn.textContent = t('btnCancel');
		if (closeBtn) closeBtn.textContent = t('btnClose');
		if (cmdCancelBtn) cmdCancelBtn.textContent = t('btnCancel');
		if (cmdValidateBtn) cmdValidateBtn.textContent = t('btnValidateQueue');
		var helpTitle = document.getElementById('pcgiHelpTitle');
		var helpText = document.getElementById('pcgiHelpText');
		if (helpTitle) helpTitle.textContent = t('helperTitle');
		if (helpText) helpText.textContent = t('helperText');
		var cmdTitle = document.getElementById('pcgiCmdPreviewTitle');
		var cmdText = document.getElementById('pcgiCmdPreviewText');
		if (cmdTitle) cmdTitle.textContent = t('cmdPreviewTitle');
		if (cmdText) cmdText.textContent = t('cmdPreviewHint');
		var partprobeBtn = document.getElementById('partprobeBtn');
		var analyzeBtn = document.getElementById('analyzeBtn');
		var metaBtn = document.getElementById('metaBtn');
		if (partprobeBtn) { partprobeBtn.textContent = t('btnRunPartprobe'); partprobeBtn.title = t('partprobeHint'); }
		if (analyzeBtn) { analyzeBtn.textContent = t('btnAnalyzeToolchain'); analyzeBtn.title = t('analyzeHint'); }
		if (metaBtn) { metaBtn.textContent = t('btnPartitionMetadata'); metaBtn.title = t('metadataHint'); }
		var usbSel = document.getElementById('usbOnlySelect');
		if (usbSel && usbSel.options.length >= 2) {
			usbSel.options[0].text = t('usbAllDevices');
			usbSel.options[1].text = t('usbOnlyDevices');
		}
		var mcCancelBtn   = document.getElementById('pcgiMcCancelBtn');
		var mcOkBtn       = document.getElementById('pcgiMcOkBtn');
		var verifyCancelBtn = document.getElementById('pcgiVerifyCancelBtn');
		var verifyOkBtn     = document.getElementById('pcgiVerifyOkBtn');
		var newPartCancelBtn = document.getElementById('pcgiNewPartCancelBtn');
		var newPartFsBtn     = document.getElementById('pcgiNewPartFsBtn');
		if (mcCancelBtn)     mcCancelBtn.textContent     = t('btnCancel');
		if (mcOkBtn)         mcOkBtn.textContent         = t('btnValidateQueue');
		if (verifyCancelBtn) verifyCancelBtn.textContent = t('btnCancel');
		if (verifyOkBtn)     verifyOkBtn.textContent     = t('confirmVerify') || 'Verify';
		if (newPartCancelBtn) newPartCancelBtn.textContent = t('btnCancel');
		if (newPartFsBtn)     newPartFsBtn.textContent     = t('btnCreatePartition') || 'Create partition';
		var dmCancelBtn = document.getElementById('pcgiDmCancelBtn');
		var dmOkBtn     = document.getElementById('pcgiDmOkBtn');
		if (dmCancelBtn) dmCancelBtn.textContent = t('btnCancel');
		if (dmOkBtn)     dmOkBtn.textContent     = t('btnValidateQueue');
		var dmTitleEl = document.getElementById('pcgiDmTitle');
		if (dmTitleEl) dmTitleEl.textContent = t('dmTitle');
		var mountCancelBtn = document.getElementById('pcgiMountCancelBtn');
		var mountOkBtn     = document.getElementById('pcgiMountOkBtn');
		var mountTitleEl   = document.getElementById('pcgiMountTitle');
		if (mountCancelBtn) mountCancelBtn.textContent = t('btnCancel');
		if (mountOkBtn)     mountOkBtn.textContent     = t('confirmMount') || 'Mount';
		if (mountTitleEl)   mountTitleEl.textContent   = t('mountModalTitle');
		updateToolchainToggleButton();
		renderDeviceStrip();
	}

	function hideLegacyFooterButtons() {
		var submitEls = document.querySelectorAll('input[type="submit"], button[type="submit"]');
		for (var i = 0; i < submitEls.length; i++) {
			var el = submitEls[i];
			var txt = String(el.value || el.textContent || '').toLowerCase().trim();
			if (!txt) continue;
			if (txt === 'apply' || txt === 'default' || txt === 'applica' || txt === 'predefinito' || txt === 'anwenden' || txt === 'standard') {
				el.style.display = 'none';
				if (el.parentNode && el.parentNode.className && String(el.parentNode.className).indexOf('btn') !== -1) {
					el.parentNode.style.display = 'none';
				}
			}
		}
	}

	function updateSafetySectionVisibility() {
		var safetySec = document.getElementById('safetyModeSection');
		var ackEl = document.getElementById('ackToken');
		if (!safetySec || !ackEl) return;
		if (ackEl.value.trim() === 'YES_I_UNDERSTAND') safetySec.style.display = 'none';
	}

	function updateToolchainToggleButton() {
		var sec = document.getElementById('toolchainSection');
		var btn = document.getElementById('toolchainToggleBtn');
		if (!btn || !sec) return;
		var isHidden = sec.style.display === 'none';
		btn.textContent = isHidden ? t('btnToolchainShow') : t('btnToolchainHide');
	}

	function toggleToolchainSection() {
		var sec = document.getElementById('toolchainSection');
		var btn = document.getElementById('toolchainToggleBtn');
		if (!sec) return;
		var isHidden = sec.style.display === 'none';
		sec.style.display = isHidden ? '' : 'none';
		if (btn) btn.textContent = isHidden ? t('btnToolchainHide') : t('btnToolchainShow');
	}

	function showToast(message, type, ttl) {
		var wrap = document.getElementById('pcgiToastWrap');
		if (!wrap) return;
		var toast = document.createElement('div');
		toast.className = 'pcgi-toast pcgi-toast-' + (type || 'info');
		toast.textContent = message;
		wrap.appendChild(toast);
		setTimeout(function () {
			if (toast.parentNode) toast.parentNode.removeChild(toast);
		}, ttl || 10000);
	}

	function showConfirmModal(title, message) {
		var modal = document.getElementById('pcgiConfirmModal');
		var titleEl = document.getElementById('pcgiConfirmTitle');
		var textEl = document.getElementById('pcgiConfirmText');
		var okBtn = document.getElementById('pcgiConfirmOkBtn');
		var cancelBtn = document.getElementById('pcgiConfirmCancelBtn');
		if (!modal || !titleEl || !textEl || !okBtn || !cancelBtn) {
			return Promise.resolve(false);
		}

		titleEl.textContent = title || t('confirmAction');
		textEl.textContent = message || '';
		modal.style.display = 'flex';
		modal.setAttribute('aria-hidden', 'false');

		return new Promise(function (resolve) {
			function cleanup(result) {
				modal.style.display = 'none';
				modal.setAttribute('aria-hidden', 'true');
				okBtn.onclick = null;
				cancelBtn.onclick = null;
				document.removeEventListener('keydown', onEsc);
				resolve(result);
			}
			function onEsc(ev) {
				if (ev.key === 'Escape') cleanup(false);
			}
			document.addEventListener('keydown', onEsc);
			okBtn.onclick = function () { cleanup(true); };
			cancelBtn.onclick = function () { cleanup(false); };
		});
	}

	function showHelpModal() {
		var modal = document.getElementById('pcgiHelpModal');
		if (!modal) return;
		modal.style.display = 'flex';
		modal.setAttribute('aria-hidden', 'false');
	}

	function hideHelpModal() {
		var modal = document.getElementById('pcgiHelpModal');
		if (!modal) return;
		modal.style.display = 'none';
		modal.setAttribute('aria-hidden', 'true');
	}

	// ── Field-level help system ───────────────────────────────────────────────
	var FIELD_HELP = {
		/* Verify modal */
		'verify-src-dev':  { title: 'Source device (A)',         body: 'The disk that contains the <strong>reference partition</strong> — the one considered correct. Typically the original disk you cloned or moved from.' },
		'verify-src-part': { title: 'Source partition (A)',      body: 'The partition on device A to compare. Its data will be read block-by-block and compared against partition B.' },
		'verify-tgt-dev':  { title: 'Compare device (B)',        body: 'The disk that contains the <strong>copy or clone</strong> to verify. May be the same device as A (on a different partition) or a different disk.' },
		'verify-tgt-part': { title: 'Compare partition (B)',     body: 'The partition on device B to compare against partition A. Verification reports any sector that differs.' },
		'verify-unmount':  { title: 'Unmount before (-u)',       body: '<b>yes</b> – unmounts both partitions before comparing. Required for live/mounted partitions to prevent inconsistent reads.<br><br><b>no</b> – skips unmount. Only safe if neither partition is being written to.' },
		/* Move/Clone partition modal */
		'mc-mode':         { title: 'Operation',                 body: '<b>Clone (keep source)</b> – copies the partition to the target and leaves the original untouched. Use for backups or duplication.<br><br><b>Move (delete source)</b> – copies the partition then removes the original. Irreversible relocation.' },
		'mc-src-dev':      { title: 'Source device',             body: 'The disk that contains the partition you want to copy or move. Its partitions are listed in the Source partition dropdown.' },
		'mc-tgt-dev':      { title: 'Target device',             body: 'The disk where data will be written. Can be the same disk (different position) or a different disk. Must have enough free space.' },
		'mc-src-part':     { title: 'Source partition',          body: 'The partition to clone or move. Its filesystem type is auto-detected to choose the right tool (partclone.ext4, partclone.ntfs, etc.).' },
		'mc-tgt-part':     { title: 'Target partition (optional)', body: 'Select an existing partition to write into its sector range, or leave blank to specify a custom range with the sector fields below.<br><br>The target must be at least as large as the used data on the source.' },
		'mc-tgt-start':    { title: 'Start sector',              body: 'The first 512-byte sector of the write range on the target. Enter the raw number or use the human-readable size fields on the right.<br><br><em>Tip:</em> selecting a target partition above auto-fills these values.' },
		'mc-tgt-end':      { title: 'End sector (inclusive)',    body: 'The last sector (inclusive) of the write range. Together with the start sector defines where data is placed on target. The range must fit all used blocks of the source.' },
		'mc-tgt-size':     { title: 'Target range size',         body: 'Auto-calculated size of the defined sector range (end − start + 1), shown in human-readable units. Read-only.' },
		'mc-method':       { title: 'Clone method',              body: '<b>Smart (filesystem-aware)</b> – partclone copies only used filesystem blocks. Much faster for partially-filled partitions. Supports ext2/3/4, NTFS, FAT, exFAT.<br><br><b>Sector-by-sector (dd)</b> – copies every sector regardless of content. Slower but works with any filesystem or raw data.' },
		'mc-verify':       { title: 'Verify after clone (-V)',   body: '<b>no</b> – skip verification. Faster but no integrity confirmation.<br><br><b>yes (partclone.chkimg)</b> – runs a bit-exact check after cloning. Recommended when the target will replace the source.' },
		'mc-align':        { title: 'Alignment (-a)',            body: '<b>4096 bytes (4K)</b> – aligns to 4096-byte boundaries. Use for SSDs, NVMe drives, modern 4K-native HDDs and UEFI/GPT setups.<br><br><b>512 bytes (legacy)</b> – only for old MBR disks with 512-byte physical sectors.<br><br><em>Tip:</em> modern USB3 flash drives, SD cards and NAS targets all benefit from at least 4096-byte alignment; misalignment causes a 2–4× write-amplification penalty on NAND storage.' },
		'mc-unmount':      { title: 'Unmount before (-u)',       body: '<b>yes</b> – unmounts source and target before starting. Strongly recommended to prevent data corruption.<br><br><b>no</b> – skips unmount. Only safe if the partitions are not in use.' },
		'mc-mount-after':  { title: 'Mount after (-o)',          body: '<b>no</b> – leave the target partition unmounted after the operation.<br><br><b>yes</b> – automatically mount the target partition when done. Fill in the mountpoint field that appears.' },
		'mc-tgt-mount':    { title: 'Target mountpoint (-t)',    body: 'Filesystem path where the target partition will be mounted. Example: <code>/var/media/ftp/backup</code>.<br><br>The directory must exist. Used only when Mount after = yes.' },
		'mc-force-fs':     { title: 'Force filesystem type (-f)', body: 'Override auto-detection of the filesystem type. Leave blank to use blkid/parted detection (recommended).<br><br>Use only when the detected type is wrong. Examples: <code>ext4</code>, <code>ntfs</code>, <code>fat32</code>, <code>exfat</code>.' },
		'mc-extra-opts':   { title: 'Extra partclone options (-x)', body: 'Additional flags passed directly to partclone. Leave empty unless needed.<br><br><code>--debug</code> – verbose output.<br><code>--rescue</code> – continue past read errors (damaged disks).<br><code>--check</code> – force filesystem check before cloning.' },
		'mc-step-delay':   { title: 'Step delay seconds (-w)',   body: 'Seconds to wait between major steps (unmount → clone → verify → mount). Allows the kernel to settle after partition table changes.<br><br><b>0</b> – no delay. <b>1</b> – default. <b>3–5</b> – use if you see "device busy" errors.' },
		'mc-dd-bs':        { title: 'dd block size',             body: 'I/O block size for the sector-by-sector method.<br><br><b>1M</b> – default, good balance of speed and memory.<br><b>4M</b> – faster on large high-throughput disks.<br><b>512</b> – sector-exact, slowest, maximum compatibility.' },
		/* Disk Move/Clone modal */
		'dm-src-dev':      { title: 'Source disk (-D)',          body: 'The entire disk to clone or move. All its partitions are processed in order. The disk should be unmounted for safety.' },
		'dm-tgt-dev':      { title: 'Target disk (-d)',          body: 'The destination disk. For logical clone: must fit all used data. For physical clone: must be at least as large as used sectors on source. Cannot be the same disk as source.' },
		'dm-mode':         { title: 'Operation (-M)',            body: '<b>Clone (preserve source)</b> – copies everything to target, source untouched. Use for backups or migrating while keeping the original.<br><br><b>Move (wipe source)</b> – clones the disk then wipes all source partitions. Irreversible.' },
		'dm-method':       { title: 'Copy method (-P / -c)',     body: '<b>Logical – smart</b> – partclone, only used blocks. Fastest. Supports ext2/3/4, NTFS, FAT, exFAT.<br><br><b>Logical – dd</b> – every sector of each partition. Works with any filesystem.<br><br><b>Physical</b> – raw dd of the whole disk including MBR/GPT. Target must be equal or larger in size.' },
		'dm-align':        { title: 'Alignment (-a)',            body: '<b>4096 bytes (4K)</b> – aligns every partition to a 4096-byte boundary on the target. Best for SSDs, NVMe drives, modern 4K-native HDDs, and GPT/UEFI targets.<br><br><b>512 bytes (legacy)</b> – only for old MBR disks with 512-byte physical sectors.<br><br><em>Tip:</em> even if the source uses 512-byte sectors, USB3 SSDs and SD cards use 4K internal pages — misaligned writes cross page boundaries and cut write speed significantly.' },
		'dm-copy-mbr':     { title: 'Copy MBR/GPT header (-B)', body: '<b>yes</b> – copies the partition table header from source to target, preserving disk UUID and metadata.<br><br><b>no</b> – creates a fresh partition table on target. Use when sizes differ or you want a clean table.' },
		'dm-wipe':         { title: 'Wipe target partitions first (-W)', body: '<b>yes</b> – deletes all existing partitions on target before starting. Ensures a clean state. Recommended if the target has leftover partitions.<br><br><b>no</b> – no wipe. Use only if the target is already empty.' },
		'dm-verify':       { title: 'Verify each partition (-V)', body: '<b>no</b> – skip verification. Faster.<br><br><b>yes</b> – after cloning each partition, runs partclone.chkimg to confirm bit-perfect copy. Strongly recommended for Move mode.' },
		'dm-force-fs':     { title: 'Force filesystem type (-f)', body: 'Override filesystem auto-detection for all partitions. Leave blank (recommended) to detect each partition individually.<br><br>Only useful if every partition has the same type and auto-detection fails.' },
		'dm-extra-opts':   { title: 'Extra partclone options (-x)', body: 'Additional flags passed to partclone for each partition.<br><br><code>--rescue</code> – ignore read errors.<br><code>--debug</code> – verbose output.<br><code>--check</code> – force filesystem check before cloning.' },
		'dm-include-tail': { title: 'Include unallocated tail (-T)', body: 'Physical mode only.<br><br><b>no (used sectors only)</b> – copies up to the last used sector + 2 MiB pad. Faster and allows cloning to a slightly smaller target.<br><br><b>yes (full disk)</b> – copies the entire disk including trailing unallocated space. Preserves hidden data, firmware areas or recovery partitions.' },
		'dm-unmount':      { title: 'Unmount partitions first (-u)', body: '<b>yes</b> – unmounts all partitions on both disks before starting. Prevents corruption. Strongly recommended.<br><br><b>no</b> – skips unmounting. Only use if no mounted filesystems exist on either disk.' },
		'dm-step-delay':   { title: 'Step delay seconds (-w)',   body: 'Pause between major steps.<br><br><b>0</b> – no delay. <b>1</b> – default. <b>3–5</b> – increase if you encounter "device or resource busy" errors.' },
		/* Filesystem operations */
		'fs-part-path':    { title: 'Partition path',            body: 'Block device path of the partition to operate on. Examples: <code>/dev/sda1</code>, <code>/dev/sdb3</code>.<br><br>Click a partition in the disk map above to auto-fill this field.' },
		'fs-type':         { title: 'Filesystem type',           body: '<b>ext4</b> – best for Linux: journaling, stable, large volumes.<br><b>ext3/ext2</b> – older ext variants; ext2 has no journaling.<br><b>exfat</b> – cross-platform (Windows/macOS/Linux), no journaling; good for USB drives shared across OS.<br><b>ntfs</b> – Windows native. Use for disks shared with Windows.<br><b>fat32/fat16/vfat</b> – max compatibility, 4 GB file-size limit. Use for bootloaders or embedded systems.<br><b>auto-detect</b> – keeps the current type for other operations.' },
		'fs-label':        { title: 'Label',                     body: 'Human-readable name shown in file managers and mount commands.<br><br>Limits: ext4 max 16 chars, FAT max 11 chars (uppercase), NTFS max 32 chars, exFAT max 15 chars. Leave blank for no label.' },
		'resize-end-sector': { title: 'Resize partition to sector', body: 'New last sector (inclusive) for the partition boundary (raw 512-byte sector number).<br><br><b>Shrink:</b> enter a smaller value. Requires the filesystem to be shrunk first, or enable "Resize filesystem too".<br><b>Grow:</b> enter a higher value up to the end of free space after the partition.' },
		'resize-end-human':{ title: 'Resize target size',        body: 'Human-readable target size, e.g. <code>8 GiB</code>, <code>500 MiB</code>. The raw sector field is auto-calculated from this — both fields are synchronized.<br><br>This is the total new partition size, not an offset from the current size.' },
		'resize-fs':       { title: 'Resize filesystem too',     body: '<b>yes</b> – after changing the partition table boundary, also resizes the filesystem. Supported for ext2/3/4 (resize2fs), NTFS (ntfsresize), FAT (fatresize).<br><br><b>no</b> – only changes the partition table. The filesystem stays at its original size.' },
		'fs-extra-opts':   { title: 'Advanced options (safe subset)', body: 'Extra options passed to mkfs when creating a filesystem. Leave blank for defaults.<br><br>ext4 examples:<br><code>-E lazy_itable_init=0</code> – init inode table immediately (no background).<br><code>-b 4096</code> – set block size.<br><code>-N 1000000</code> – set inode count.<br><br>Options that could override the device path are blocked for safety.' },
		'fs-mountpoint':   { title: 'Mountpoint',                body: 'Directory where the partition will be mounted. Example: <code>/var/media/ftp/usbdisk</code>.<br><br>On FritzBox, USB drives are normally under <code>/var/media/ftp/</code>. The directory must exist before mounting.' },
		'fs-mount-opts':   { title: 'Mount options',             body: 'Options passed to the <code>mount</code> command.<br><br><code>rw</code> – read-write (default). <code>ro</code> – read-only.<br><code>noatime</code> – skip access-time updates (reduces writes on flash/SD).<br><code>nofail</code> – do not fail boot if device is absent.<br><code>uid=1000,gid=1000</code> – set owner for FAT/exFAT/NTFS (Linux permission-less filesystems).<br><br>Leave blank for kernel defaults.' },
		/* Device map section */
		'map-sel-part-num':  { title: 'Selected partition number', body: 'The number of the partition currently selected in the disk map. Read-only — auto-updated when you click a partition in the visual map.<br><br>Used by operations (Delete, Resize, Set flag, Set label, Rename) to identify which partition to act on.' },
		'map-sel-part-path': { title: 'Selected partition path',   body: 'Full block device path of the selected partition, e.g. <code>/dev/sda1</code>. Read-only — auto-filled when you click a partition. Also auto-fills the Partition path field in the Filesystem operations section.' },
		'map-new-start':     { title: 'New start sector',          body: 'First 512-byte sector of the new partition to create. Must lie within a free (unallocated) region on the disk.<br><br>Use multiples of 2048 (= 1 MiB boundary) for modern disks. The drag-and-drop interface fills this automatically.<br><br>Linked to the "New start size" field — changing one updates the other.' },
		'map-new-start-h':   { title: 'New start size',            body: 'Human-readable offset of the partition start, e.g. <code>1 MiB</code>, <code>512 KiB</code>.<br><br>Synchronized with the raw sector field. Editing this updates the sector value automatically.' },
		'map-new-end':       { title: 'New end sector',            body: 'Last sector (inclusive) of the new partition. Must be within the same free region as the start sector, and after it.<br><br>Together with the start sector this defines the partition size. The drag-and-drop interface fills this automatically.' },
		'map-new-end-h':     { title: 'New end size',              body: 'Human-readable end position of the partition, e.g. <code>488 MiB</code>.<br><br>Synchronized with the raw sector field on the left. Editing this updates the sector value automatically.' },
		'map-role':          { title: 'Role',                      body: '<b>primary</b> – standard MBR partition. MBR supports max 4 primary partitions.<br><br><b>logical</b> – partition inside an extended container. Allows more than 4 partitions on MBR. Only valid if an extended partition exists.<br><br><b>extended</b> – container for logical partitions. Only one per MBR disk. Irrelevant on GPT (GPT supports up to 128 partitions, all treated as primary).' },
		'map-fs-hint':       { title: 'Filesystem',                body: 'Filesystem type hint stored in the partition table entry. Does <em>not</em> create a filesystem — only sets the partition type flag visible to tools like parted or fdisk.<br><br>To actually format the partition, use "Create filesystem" in the Filesystem operations section after creating the partition.' },
		'map-part-name':     { title: 'Partition name',            body: 'Label stored in the GPT partition entry. Visible in gdisk, parted and Windows Disk Management.<br><br>Ignored on MBR disks. Optional — leave blank for an unnamed partition.' },
		/* New partition modal */
		'pnp-start':     { title: 'New start sector',     body: 'First 512-byte sector of the new partition to create. Must lie within a free (unallocated) region on the disk.<br><br>Use multiples of 2048 (= 1 MiB boundary) for modern disks. The drag-and-drop interface fills this automatically.<br><br>Linked to the "New start size" field — changing one updates the other.' },
		'pnp-start-h':   { title: 'New start size',       body: 'Human-readable offset of the partition start, e.g. <code>1 MiB</code>, <code>512 KiB</code>.<br><br>Synchronized with the raw sector field. Editing this updates the sector value automatically.' },
		'pnp-end':       { title: 'New end sector',       body: 'Last sector (inclusive) of the new partition. Must be within the same free region as the start sector, and after it.<br><br>Together with the start sector this defines the partition size. The drag-and-drop interface fills this automatically.' },
		'pnp-end-h':     { title: 'New end size',         body: 'Human-readable end position of the partition, e.g. <code>488 MiB</code>.<br><br>Synchronized with the raw sector field on the left. Editing this updates the sector value automatically.' },
		'pnp-role':      { title: 'Role',                 body: '<b>primary</b> – standard MBR partition. MBR supports max 4 primary partitions.<br><br><b>logical</b> – partition inside an extended container. Allows more than 4 partitions on MBR. Only valid if an extended partition exists.<br><br><b>extended</b> – container for logical partitions. Only one per MBR disk. Irrelevant on GPT (GPT supports up to 128 partitions, all treated as primary).' },
		'pnp-fs-hint':   { title: 'Filesystem',           body: 'Filesystem type hint stored in the partition table entry. Does <em>not</em> create a filesystem — only sets the partition type flag visible to tools like parted or fdisk.<br><br>To actually format the partition, use "Create filesystem" in the Filesystem operations section after creating the partition.' },
		'pnp-part-name': { title: 'Partition name (GPT only)', body: 'Label stored in the GPT partition entry. Visible in gdisk, parted and Windows Disk Management.<br><br>Ignored on MBR disks. Optional — leave blank for an unnamed partition.' },
		'pnp-fs-label':  { title: 'Filesystem label',     body: 'Volume label embedded in the filesystem itself and shown by file managers and mount tools.<br><br>Limits: ext2/3/4 max 16 chars; FAT max 11 chars (uppercase); NTFS max 32 chars; exFAT max 15 chars.<br><br>Only used when creating the filesystem ("With filesystem" button). Leave blank for no label.' },
		'pnp-mount':     { title: 'Mount point',          body: 'Directory where the new partition will be automatically mounted after creation.<br><br>On FritzBox, USB drives are normally under <code>/var/media/ftp/</code>. The directory will be created if it does not exist.<br><br>Leave blank to skip automatic mounting.' },
		'pnp-align':     { title: 'Alignment',            body: '<b>optimal (1 MiB)</b> – automatically computes 1 MiB ÷ logical_sector_size: 2048 sectors on 512-byte drives, 256 sectors on 4K-native drives. Recommended for all modern media.<br><br><b>2048 sectors (1 MiB)</b> – fixed 1 MiB boundary. Ideal for SD cards (SD Association spec), USB2/USB3 flash drives, spinning HDDs, and legacy MSDOS/MBR disks. Compatible with virtually all operating systems.<br><br><b>4096 sectors (2 MiB)</b> – 2 MiB boundary for high-end NVMe SSDs and USB3 Gen2 SSDs with 2 MiB erase blocks.<br><br><b>no alignment</b> – no adjustment. Use only to match legacy disk geometries or to recover partitions. Avoid on flash/SSD storage as misaligned writes severely hurt write performance and longevity.<br><br><em>Recommendation by drive type:</em><br>• SD card / USB flash / spinning HDD → optimal or 2048 sectors<br>• USB3 SSD (SATA-in-USB) → optimal<br>• NVMe (via USB3 or internal) → optimal or 4096 sectors<br>• Legacy MSDOS/MBR (CHS geometry) → 2048 sectors' },
		/* Partclone export modal */
		'pi-exp-source':     { title: 'Source partition/disk',     body: 'The block device to export, e.g. <code>/dev/sda1</code> for a partition or <code>/dev/sda</code> for a whole disk.<br><br>Auto-filled from the context menu selection.' },
		'pi-exp-output':     { title: 'Output image file (-o)',     body: 'Full path for the output image file, e.g. <code>/var/media/ftp/USB_DISK/backup.img</code>.<br><br>If compression is selected the appropriate extension is appended automatically by the script (.gz, .bz2, .lz4, .zst).<br><br>Ensure the destination has sufficient free space (can be up to the partition size for non-sparse filesystems).' },
		'pi-exp-compress':   { title: 'Compression (-z)',           body: 'Compress the image stream on-the-fly to reduce file size.<br><br><b>none</b> – raw partclone image (fastest restore).<br><b>gzip</b> – good compression ratio, widely supported.<br><b>bzip2</b> – better compression, slower.<br><b>lz4</b> – very fast compression/decompression, lower ratio.<br><b>zstd</b> – modern, fast and strong compression (recommended if available).' },
		'pi-exp-force-fs':   { title: 'Force filesystem type (-f)',  body: 'Override auto-detection of the filesystem type. Usually leave empty — partclone will detect the filesystem via blkid/lsblk and choose the correct binary (partclone.ext4, partclone.ntfs, etc.).<br><br>Set only if detection fails or if you want to force raw dd mode (set to <code>dd</code>).' },
		'pi-exp-verify':     { title: 'Verify after export (-V)',    body: 'Run <code>partclone.chkimg</code> on the created image after export to validate its integrity.<br><br>Adds extra time proportional to image size. Highly recommended for important backups.' },
		'pi-exp-unmount':    { title: 'Unmount before export (-u)',  body: 'Automatically unmount the source partition before starting the export.<br><br>Recommended to ensure a consistent filesystem snapshot. If the partition is in use and cannot be unmounted, the export may capture an inconsistent state.' },
		'pi-exp-use-dd':     { title: 'Use partclone.dd always (-c)', body: 'Force use of <code>partclone.dd</code> regardless of the detected filesystem type.<br><br>This creates a raw sector-by-sector image (like <code>dd</code>) but with partclone metadata. Larger than a smart image but works for any filesystem including unknown or corrupted ones.' },
		'pi-exp-step-delay': { title: 'Step delay seconds (-w)',     body: 'Pause in seconds between internal steps. Useful to reduce I/O pressure on slow devices like USB sticks or when the system is under load.<br><br>Set to 0 for fastest execution.' },
		'pi-exp-extra-opts': { title: 'Extra options (-x)',          body: 'Additional flags passed directly to the partclone binary.<br><br>Example: <code>--debug</code> for verbose logging. Rarely needed. Consult <code>partclone --help</code> for available options.' },
		/* Partclone import modal */
		'pi-imp-target':     { title: 'Target partition/disk',      body: 'The block device to restore onto, e.g. <code>/dev/sda1</code>.<br><br>WARNING: all existing data on this partition will be overwritten. The target must be at least as large as the partition that was exported.' },
		'pi-imp-input':      { title: 'Input image file (-o)',       body: 'Full path to the partclone image to restore from, e.g. <code>/var/media/ftp/USB_DISK/backup.img.gz</code>.<br><br>Can be a raw image or a compressed one — select the matching Compression option.' },
		'pi-imp-compress':   { title: 'Compression (-z)',            body: 'Decompression to apply when reading the image.<br><br>Must match the compression used when the image was exported. Select <b>none</b> for uncompressed images.' },
		'pi-imp-verify':     { title: 'Verify before restore (-V)',  body: 'Run <code>partclone.chkimg</code> on the source image before starting the restore, to confirm it is not corrupted.<br><br>Adds extra time but prevents writing a broken image to the target.' },
		'pi-imp-unmount':    { title: 'Unmount before restore (-u)', body: 'Unmount the target partition before starting the restore. Required if the target is already mounted — writing to a mounted partition causes filesystem corruption.' },
		'pi-imp-step-delay': { title: 'Step delay seconds (-w)',     body: 'Pause in seconds between internal steps. Set to 0 for fastest execution.' },
		'pi-imp-extra-opts': { title: 'Extra options (-x)',          body: 'Additional flags passed directly to <code>partclone.restore</code>. Rarely needed.' },
		/* Network send modal */
		'pi-ns-source':      { title: 'Source partition',           body: 'The partition to stream over the network. Auto-filled from context menu selection.' },
		'pi-ns-transport':   { title: 'Network mode',               body: '<b>Unicast (netcat)</b>: streams the partition image to a single receiver. The receiver must be waiting with netcat on the same port before you start sending.<br><br><b>Multicast (udp-sender)</b>: streams to multiple receivers simultaneously using <code>udp-sender</code> (DRBL/Clonezilla style). Requires <code>udp-sender</code> on sender and <code>udp-receiver</code> on all receivers.<br><br>For unicast, the receiver command is:<br><code>nc -l -p PORT | partclone.restore -d -s - -o /dev/sdX1</code><br>(or with decompression piped in between).' },
		'pi-ns-host':        { title: 'Target host IP / Multicast group', body: 'For <b>unicast</b>: the IP or hostname of the receiving machine (netcat will connect to it).<br><br>For <b>multicast</b>: the multicast group address, e.g. <code>239.0.0.1</code>. All receivers that join this group will get the data.<br><br>Leave empty for unicast to make netcat listen on <em>this</em> machine instead of connecting outward.' },
		'pi-ns-port':        { title: 'TCP/UDP port (-P)',           body: 'Network port to use for the transfer. Default: 9000.<br><br>Must match on sender and all receivers. Choose an unused port above 1024 to avoid conflicts with system services.' },
		'pi-ns-compress':    { title: 'Compression (-z)',            body: 'Compress the data stream before sending over the network.<br><br><b>lz4</b> and <b>zstd</b> are recommended for network transfers — they are fast enough to not bottleneck even on fast LAN connections while reducing bandwidth usage.' },
		'pi-ns-force-fs':    { title: 'Force filesystem type (-f)',  body: 'Override auto-detection of the filesystem type. Usually leave empty.' },
		'pi-ns-unmount':     { title: 'Unmount before send (-u)',    body: 'Unmount the source partition before streaming. Recommended for consistent state.' },
		'pi-ns-step-delay':  { title: 'Step delay seconds (-w)',     body: 'Pause in seconds between preparation steps. Set to 0 for fastest execution.' },
		/* Network receive modal */
		'pi-nr-target':      { title: 'Target partition',           body: 'The local partition to restore the received image onto. WARNING: all existing data will be overwritten.' },
		'pi-nr-transport':   { title: 'Network mode',               body: 'Match the mode chosen on the sender side.<br><br><b>Unicast</b>: connect to or listen for the sender via netcat.<br><b>Multicast</b>: join a multicast group via udp-receiver.' },
		'pi-nr-host':        { title: 'Source host IP / Multicast group', body: 'For <b>unicast</b>: the IP or hostname of the sending machine.<br><br>For <b>multicast</b>: the multicast rendezvous IP used by the sender, e.g. <code>239.0.0.1</code>.' },
		'pi-nr-port':        { title: 'TCP/UDP port (-P)',           body: 'Must match the port configured on the sender. Default: 9000.' },
		'pi-nr-compress':    { title: 'Compression (-z)',            body: 'Must match the compression used by the sender.' },
		'pi-nr-verify':      { title: 'Verify after receive (-V)',   body: 'Run partition info check after restore to verify the received data is valid.' },
		'pi-nr-unmount':     { title: 'Unmount before receive (-u)', body: 'Unmount the target partition before starting the receive/restore. Required if mounted.' },
		'pi-nr-step-delay':  { title: 'Step delay seconds (-w)',     body: 'Pause in seconds between preparation steps.' },
		/* Ddrescue modal */
		'dr-source':         { title: 'Source partition/disk',       body: 'The damaged or source block device, e.g. <code>/dev/sda1</code> or <code>/dev/sda</code>.<br><br>ddrescue reads the source in multiple passes, skipping bad sectors and retrying them later, to maximise data recovery from failing drives.' },
		'dr-output':         { title: 'Output image file (-o)',       body: 'Path for the output image file. Can be on any writable filesystem with enough free space.<br><br>If the file already exists and a log file is specified, ddrescue will resume from where it left off — this allows interrupted rescues to be continued safely.' },
		'dr-log':            { title: 'ddrescue log file (-l)',        body: 'Path to the ddrescue domain log file. This file records which sectors have been read successfully and which have errors.<br><br>Strongly recommended: it allows you to resume an interrupted rescue operation. If empty, defaults to <code>&lt;output&gt;.log</code>.<br><br>Never delete the log file while a rescue is in progress or if you plan to continue later.' },
		'dr-retries':        { title: 'Max retry passes (-r)',         body: 'Maximum number of retry passes for failed sectors. Default: 3.<br><br>Each pass makes additional attempts to read unreadable sectors. More passes recover more data but take more time and may stress the drive further.<br><br>Set to 0 to disable retries (first pass only). Set to -1 for unlimited retries.' },
		'dr-unmount':        { title: 'Unmount before (-u)',           body: 'Unmount the source partition before running ddrescue. Recommended to avoid inconsistent reads on mounted filesystems.' },
		'dr-step-delay':     { title: 'Step delay seconds (-w)',       body: 'Pause in seconds between preparation steps.' },
		'dr-extra-opts':     { title: 'Extra ddrescue options (-x)',    body: 'Additional flags passed to <code>ddrescue</code>.<br><br>Examples:<br><code>-d</code> – use direct disc access (bypasses cache, slower but more reliable)<br><code>-r -1</code> – infinite retries<br><code>-S</code> – scrape mode (slower but recovers more from bad sectors)<br><code>-R</code> – reverse reading direction<br><br>Consult <code>man ddrescue</code> for the full list.' },
		/* Freetz EVO setup modal */
		'fritz-table-type':  { title: 'Partition table',   body: '<b>GPT</b> – GUID Partition Table. Supports disks larger than 2 TiB, up to 128 partitions, and is required for UEFI boot. Recommended for all modern disks.<br><br><b>msdos / MBR</b> – Master Boot Record. Legacy format with max 4 primary partitions and 2 TiB disk limit. Use only for old BIOS-boot setups or very small disks.' },
		'fritz-align':       { title: 'Alignment',         body: '<b>optimal (1 MiB)</b> – auto-computes 1 MiB alignment (2048 × 512-byte sectors, 256 × 4K-sector drives). Best for SD cards, USB3 drives and SSDs. Recommended.<br><br><b>2048 sectors (1 MiB)</b> – fixed 1 MiB boundary. Ideal for SD cards (SD Association spec), USB2/USB3 flash drives, spinning HDDs, and legacy MSDOS/MBR disks.<br><br><b>4096 sectors (2 MiB)</b> – 2 MiB boundary for NVMe SSDs and USB3 Gen2 SSD enclosures with 2 MiB erase blocks.<br><br><b>no alignment</b> – no adjustment. Only for legacy recovery. Avoid on flash/SSD storage.<br><br><em>Recommendation by drive type:</em><br>• SD card / USB flash / HDD → optimal or 2048 sectors<br>• USB3 SSD enclosure → optimal<br>• NVMe (via USB3 or internal) → optimal or 4096 sectors<br>• Old MSDOS/MBR with CHS geometry → 2048 sectors' },
		'fritz-delete-all':  { title: 'Delete existing partitions first', body: 'If checked, all existing partitions on the disk are removed before creating the new layout.<br><br>Each partition is deleted in reverse order (highest number first) via individual <em>delete_partition</em> operations. A fresh partition table of the chosen type is then written.<br><br>⚠ All data on the disk will be lost. Uncheck if you want to add partitions to an already-wiped disk.' },
		'fritz-mount-all':   { title: 'Mount all partitions after creation', body: 'If checked, each enabled partition with a non-empty mount point is automatically mounted after it is created and formatted.<br><br>The mount point directory is created if it does not already exist.<br><br>Uncheck if you want to mount partitions manually or do not need them mounted immediately.' },
		/* Device map alignment */
		'map-align':         { title: 'Alignment',         body: '<b>optimal (1 MiB)</b> – auto-computes partition boundary alignment as 1 MiB ÷ logical_sector_size: 2048 sectors on 512-byte drives, 256 sectors on 4K-native drives. The best default for all modern storage.<br><br><b>2048 sectors (1 MiB)</b> – fixed 1 MiB boundary. The SD Association specification and virtually every OS tool (fdisk, parted, gdisk) default to this. Ideal for SD cards, USB2/USB3 flash drives, spinning HDDs and legacy MBR disks.<br><br><b>4096 sectors (2 MiB)</b> – 2 MiB boundary for NVMe SSDs (both internal and USB3 enclosures) and enterprise SSDs with 2 MiB physical erase blocks. Overkill for SD/USB flash but harmless.<br><br><b>no alignment</b> – disables boundary rounding entirely. Use only to recover or precisely reproduce legacy partition layouts. Never use on flash-based or NAND storage: misaligned writes cause read-modify-write cycles that reduce write speed by 2–4× and shorten device lifetime.<br><br><em>Quick reference:</em><br>• SD card / USB2 flash → 2048 or optimal<br>• USB3 flash / USB3 HDD → optimal<br>• USB3 SSD enclosure (SATA drive) → optimal<br>• USB3 NVMe SSD → optimal or 4096<br>• Internal NVMe / PCIe SSD → optimal or 4096<br>• Old spinning HDD with MSDOS/MBR → 2048' }
	};

	function showFieldHelp(key) {
		var h = FIELD_HELP[key];
		if (!h) return;
		var modal   = document.getElementById('pcgiFieldHelpModal');
		var titleEl = document.getElementById('pcgiFieldHelpTitle');
		var bodyEl  = document.getElementById('pcgiFieldHelpBody');
		var closeBtn = document.getElementById('pcgiFieldHelpCloseBtn');
		if (!modal || !titleEl || !bodyEl) return;
		titleEl.textContent = h.title;
		bodyEl.innerHTML = h.body;
		modal.style.display = 'flex';
		modal.setAttribute('aria-hidden', 'false');
		function close() {
			modal.style.display = 'none';
			modal.setAttribute('aria-hidden', 'true');
			document.removeEventListener('keydown', onEsc);
		}
		function onEsc(ev) { if (ev.key === 'Escape') close(); }
		document.addEventListener('keydown', onEsc);
		if (closeBtn) closeBtn.onclick = close;
		modal.onclick = function(ev) { if (ev.target === modal) close(); };
	}

	function _injectHelpButtons() {
		var labelMap = {
			'i18nVerifySourceDevLabel'  : 'verify-src-dev',
			'i18nVerifySourcePartLabel' : 'verify-src-part',
			'i18nVerifyTargetDevLabel'  : 'verify-tgt-dev',
			'i18nVerifyTargetPartLabel' : 'verify-tgt-part',
			'i18nVerifyUnmountLabel'    : 'verify-unmount',
			'i18nMcModeLabel'           : 'mc-mode',
			'i18nMcSourceDevLabel'      : 'mc-src-dev',
			'i18nMcTargetDevLabel'      : 'mc-tgt-dev',
			'i18nMcSourcePartLabel'     : 'mc-src-part',
			'i18nMcTargetPartLabel'     : 'mc-tgt-part',
			'i18nMcTargetStartLabel'    : 'mc-tgt-start',
			'i18nMcTargetEndLabel'      : 'mc-tgt-end',
			'i18nMcTargetSizeLabel'     : 'mc-tgt-size',
			'i18nMcCloneMethodLabel'    : 'mc-method',
			'i18nMcVerifyLabel'         : 'mc-verify',
			'i18nMcAlignmentLabel'      : 'mc-align',
			'i18nMcUnmountBeforeLabel'  : 'mc-unmount',
			'i18nMcMountAfterLabel'     : 'mc-mount-after',
			'i18nMcTargetMountLabel'    : 'mc-tgt-mount',
			'i18nMcForceFsLabel'        : 'mc-force-fs',
			'i18nMcExtraOptsLabel'      : 'mc-extra-opts',
			'i18nMcStepDelayLabel'      : 'mc-step-delay',
			'i18nMcDdBsLabel'           : 'mc-dd-bs',
			'i18nDmSourceDevLabel'      : 'dm-src-dev',
			'i18nDmTargetDevLabel'      : 'dm-tgt-dev',
			'i18nDmModeLabel'           : 'dm-mode',
			'i18nDmMethodLabel'         : 'dm-method',
			'i18nDmAlignLabel'          : 'dm-align',
			'i18nDmCopyMbrLabel'        : 'dm-copy-mbr',
			'i18nDmWipeTargetLabel'     : 'dm-wipe',
			'i18nDmVerifyLabel'         : 'dm-verify',
			'i18nDmForceFsLabel'        : 'dm-force-fs',
			'i18nDmExtraOptsLabel'      : 'dm-extra-opts',
			'i18nDmIncludeTailLabel'    : 'dm-include-tail',
			'i18nDmUnmountLabel'        : 'dm-unmount',
			'i18nDmStepDelayLabel'      : 'dm-step-delay',
			'i18nMcFsckPassesLabel'     : 'mc-fsck-passes',
			'i18nMcDdFallbackLabel'     : 'mc-dd-fallback',
			'i18nMcSkipWriteErrLabel'   : 'mc-skip-write-err',
			'i18nDmFsckPassesLabel'     : 'dm-fsck-passes',
			'i18nDmDdFallbackLabel'     : 'dm-dd-fallback',
			'i18nDmSkipWriteErrLabel'   : 'dm-skip-write-err',
			'i18nFsPartPathLabel'       : 'fs-part-path',
			'i18nFsTypeLabel'           : 'fs-type',
			'i18nFsLabelLabel'          : 'fs-label',
			'i18nResizeEndLabel'        : 'resize-end-sector',
			'i18nResizeEndHumanLabel'   : 'resize-end-human',
			'i18nResizeFsLabel'         : 'resize-fs',
			'i18nExtraOptsLabel'        : 'fs-extra-opts',
			'i18nMountpointLabel'       : 'fs-mountpoint',
			'i18nMountOptsLabel'        : 'fs-mount-opts',
			/* Device map section */
			'i18nSelPartNumLabel'       : 'map-sel-part-num',
			'i18nSelPartPathLabel'      : 'map-sel-part-path',
			'i18nNewStartLabel'         : 'map-new-start',
			'i18nNewStartHumanLabel'    : 'map-new-start-h',
			'i18nNewEndLabel'           : 'map-new-end',
			'i18nNewEndHumanLabel'      : 'map-new-end-h',
			'i18nRoleLabel'             : 'map-role',
			'i18nFsHintLabel'           : 'map-fs-hint',
			'i18nPartNameLabel'         : 'map-part-name',
			/* New partition modal */
			'i18nPnpStartLabel'         : 'pnp-start',
			'i18nPnpStartHLabel'        : 'pnp-start-h',
			'i18nPnpEndLabel'           : 'pnp-end',
			'i18nPnpEndHLabel'          : 'pnp-end-h',
			'i18nPnpRoleLabel'          : 'pnp-role',
			'i18nPnpFsHintLabel'        : 'pnp-fs-hint',
			'i18nPnpPartNameLabel'      : 'pnp-part-name',
			'i18nPnpFsLabelLabel'       : 'pnp-fs-label',
			'i18nPnpMountLabel'         : 'pnp-mount',
			'i18nPnpAlignLabel'         : 'pnp-align',
			/* Partclone export modal */
			'i18nPiExpSourceLabel'      : 'pi-exp-source',
			'i18nPiExpOutputLabel'      : 'pi-exp-output',
			'i18nPiExpCompressLabel'    : 'pi-exp-compress',
			'i18nPiExpForceFsLabel'     : 'pi-exp-force-fs',
			'i18nPiExpVerifyLabel'      : 'pi-exp-verify',
			'i18nPiExpUnmountLabel'     : 'pi-exp-unmount',
			'i18nPiExpUseDdLabel'       : 'pi-exp-use-dd',
			'i18nPiExpStepDelayLabel'   : 'pi-exp-step-delay',
			'i18nPiExpExtraOptsLabel'   : 'pi-exp-extra-opts',
			/* Partclone import modal */
			'i18nPiImpTargetLabel'      : 'pi-imp-target',
			'i18nPiImpInputLabel'       : 'pi-imp-input',
			'i18nPiImpCompressLabel'    : 'pi-imp-compress',
			'i18nPiImpVerifyLabel'      : 'pi-imp-verify',
			'i18nPiImpUnmountLabel'     : 'pi-imp-unmount',
			'i18nPiImpStepDelayLabel'   : 'pi-imp-step-delay',
			'i18nPiImpExtraOptsLabel'   : 'pi-imp-extra-opts',
			/* Network send modal */
			'i18nPiNsSourceLabel'       : 'pi-ns-source',
			'i18nPiNsTransportLabel'    : 'pi-ns-transport',
			'i18nPiNsHostLabel'         : 'pi-ns-host',
			'i18nPiNsPortLabel'         : 'pi-ns-port',
			'i18nPiNsCompressLabel'     : 'pi-ns-compress',
			'i18nPiNsForceFsLabel'      : 'pi-ns-force-fs',
			'i18nPiNsUnmountLabel'      : 'pi-ns-unmount',
			'i18nPiNsStepDelayLabel'    : 'pi-ns-step-delay',
			/* Network receive modal */
			'i18nPiNrTargetLabel'       : 'pi-nr-target',
			'i18nPiNrTransportLabel'    : 'pi-nr-transport',
			'i18nPiNrHostLabel'         : 'pi-nr-host',
			'i18nPiNrPortLabel'         : 'pi-nr-port',
			'i18nPiNrCompressLabel'     : 'pi-nr-compress',
			'i18nPiNrVerifyLabel'       : 'pi-nr-verify',
			'i18nPiNrUnmountLabel'      : 'pi-nr-unmount',
			'i18nPiNrStepDelayLabel'    : 'pi-nr-step-delay',
			/* Ddrescue modal */
			'i18nDrSourceLabel'         : 'dr-source',
			'i18nDrOutputLabel'         : 'dr-output',
			'i18nDrLogLabel'            : 'dr-log',
			'i18nDrRetriesLabel'        : 'dr-retries',
			'i18nDrUnmountLabel'        : 'dr-unmount',
			'i18nDrStepDelayLabel'      : 'dr-step-delay',
			'i18nDrExtraOptsLabel'      : 'dr-extra-opts'
		};
		Object.keys(labelMap).forEach(function(labelId) {
			var el = document.getElementById(labelId);
			if (!el) return;
			var key = labelMap[labelId];
			var btn = document.createElement('button');
			btn.type = 'button';
			btn.className = 'pcgi-help-btn';
			btn.textContent = '?';
			btn.title = 'Field help';
			btn.addEventListener('click', function(ev) {
				ev.stopPropagation();
				showFieldHelp(key);
			});
			el.appendChild(btn);
		});
	}

	function parseAjaxJson(text) {
		var marker = 'Content-Type: application/json';
		var markerPos = text.indexOf(marker);
		if (markerPos === -1) {
			throw new Error('Invalid CGI response');
		}
		var firstBrace = text.indexOf('{', markerPos + marker.length);
		if (firstBrace === -1) {
			throw new Error('No JSON payload');
		}
		var braceCount = 0;
		var inString = false;
		var escaped = false;
		var endPos = -1;
		for (var i = firstBrace; i < text.length; i++) {
			var ch = text[i];
			if (inString) {
				if (escaped) {
					escaped = false;
				} else if (ch === '\\') {
					escaped = true;
				} else if (ch === '"') {
					inString = false;
				}
				continue;
			}
			if (ch === '"') {
				inString = true;
				continue;
			}
			if (ch === '{') {
				braceCount++;
			} else if (ch === '}') {
				braceCount--;
				if (braceCount === 0) {
					endPos = i + 1;
					break;
				}
			}
		}
		if (endPos === -1) {
			throw new Error('Broken JSON payload');
		}
		return JSON.parse(text.substring(firstBrace, endPos));
	}

	function callApi(action, params) {
		var qp = new URLSearchParams();
		qp.set('ajax', '1');
		qp.set('action', action);
		if (state.dryRun) {
			qp.set('dry_run', '1');
		}
		for (var k in params) {
			if (Object.prototype.hasOwnProperty.call(params, k) && params[k] !== undefined && params[k] !== null) {
				qp.set(k, String(params[k]));
			}
		}
		return fetch(API_URL + '?' + qp.toString())
			.then(function (r) { return r.text(); })
			.then(parseAjaxJson);
	}

	function appendTo(id, text) {
		var el = document.getElementById(id);
		if (!el) return;
		el.textContent += text;
		el.scrollTop = el.scrollHeight;
	}

	/* Convert ANSI colour codes to HTML spans and append to element */
	function appendAnsi(id, text) {
		var el = document.getElementById(id);
		if (!el) return;
		/* Escape HTML entities first */
		var safe = text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
		/* Map SGR codes -> CSS classes */
		var ANSI_MAP = {
			'0':  '',
			'1':  'ansi-bold',
			'2':  'ansi-dim',
			'31': 'ansi-red',   '1;31': 'ansi-bold ansi-red',
			'32': 'ansi-green', '1;32': 'ansi-bold ansi-green',
			'33': 'ansi-yellow','1;33': 'ansi-bold ansi-yellow',
			'34': 'ansi-blue',  '1;34': 'ansi-bold ansi-blue',
			'36': 'ansi-cyan',  '1;36': 'ansi-bold ansi-cyan',
			'90': 'ansi-gray',  '1;90': 'ansi-bold ansi-gray'
		};
		var html = '';
		var spanOpen = false;
		var parts = safe.split(/\x1b\[([0-9;]*)m/);
		for (var i = 0; i < parts.length; i++) {
			if (i % 2 === 0) {
				html += parts[i];
			} else {
				if (spanOpen) { html += '</span>'; spanOpen = false; }
				var cls = ANSI_MAP[parts[i]];
				if (cls === undefined) cls = '';
				if (cls) { html += '<span class="' + cls + '">'; spanOpen = true; }
			}
		}
		if (spanOpen) html += '</span>';
		el.insertAdjacentHTML('beforeend', html);
		el.scrollTop = el.scrollHeight;
	}

	function clearLogOutput() {
		var el = document.getElementById('cmdOutput');
		if (el) el.innerHTML = '';
		// hide buttons when log is cleared
		var cb = document.getElementById('copyLogBtn'), cl = document.getElementById('clearLogBtn'), fs = document.getElementById('fsLogBtn');
		if (cb) cb.style.display = 'none';
		if (cl) cl.style.display = 'none';
		if (fs) fs.style.display = 'none';
		// exit fullscreen if active
		if (el && el.classList.contains('pcgi-log-fullscreen')) {
			el.classList.remove('pcgi-log-fullscreen');
			document.body.classList.remove('pcgi-log-fsbody');
			if (fs) fs.title = 'Fullscreen';
			var bar = document.getElementById('cmdLogBtnBar');
			if (bar) { bar.style.position = 'absolute'; bar.style.zIndex = '10'; }
			if (window._fsLogEscHandler) {
				document.removeEventListener('keydown', window._fsLogEscHandler);
				window._fsLogEscHandler = null;
			}
		}
	}

	function toggleLogFullscreen() {
		var el = document.getElementById('cmdOutput');
		var btn = document.getElementById('fsLogBtn');
		var bar = document.getElementById('cmdLogBtnBar');
		if (!el) return;
		var isFs = el.classList.toggle('pcgi-log-fullscreen');
		document.body.classList.toggle('pcgi-log-fsbody', isFs);
		if (btn) btn.title = isFs ? 'Exit fullscreen' : 'Fullscreen';
		if (bar) {
			bar.style.position = isFs ? 'fixed' : 'absolute';
			bar.style.zIndex = isFs ? '10000' : '10';
		}
		if (isFs) {
			el.scrollTop = el.scrollHeight;
			if (!window._fsLogEscHandler) {
				window._fsLogEscHandler = function(e) {
					if (e.key === 'Escape') toggleLogFullscreen();
				};
				document.addEventListener('keydown', window._fsLogEscHandler);
			}
		} else {
			if (window._fsLogEscHandler) {
				document.removeEventListener('keydown', window._fsLogEscHandler);
				window._fsLogEscHandler = null;
			}
		}
	}

	function copyLogToClipboard() {
		var el = document.getElementById('cmdOutput');
		if (!el) return;
		var text = el.textContent || el.innerText || '';
		// navigator.clipboard requires HTTPS; FritzBox runs HTTP, so always use execCommand fallback.
		var ta = document.createElement('textarea');
		ta.value = text;
		ta.style.cssText = 'position:fixed;top:0;left:0;width:2em;height:2em;opacity:0;pointer-events:none';
		document.body.appendChild(ta);
		ta.focus();
		ta.select();
		try { document.execCommand('copy'); } catch (e) {
			if (navigator.clipboard && navigator.clipboard.writeText) {
				navigator.clipboard.writeText(text);
			}
		}
		document.body.removeChild(ta);
		// Brief 'Copied' feedback on the button
		var btn = document.getElementById('copyLogBtn');
		if (btn) {
			var origHTML = btn.innerHTML;
			btn.textContent = 'Copied';
			setTimeout(function () { btn.innerHTML = origHTML; }, 1000);
		}
	}

	// Show copy/clear/fullscreen log buttons as soon as the log has content
	(function () {
		var _logEl = document.getElementById('cmdOutput');
		if (!_logEl || typeof MutationObserver === 'undefined') return;
		var _obs = new MutationObserver(function () {
			var hasContent = !!(_logEl.textContent || _logEl.innerText || '').trim();
			var d = hasContent ? '' : 'none';
			var cb = document.getElementById('copyLogBtn'), cl = document.getElementById('clearLogBtn'), fs = document.getElementById('fsLogBtn');
			if (cb) cb.style.display = d;
			if (cl) cl.style.display = d;
			if (fs) fs.style.display = d;
		});
		_obs.observe(_logEl, { childList: true, subtree: true, characterData: true });
	}());

	function callApiStreaming(action, params, outputElId, stepIdx, totalSteps, stepLabel) {
		var _snow = new Date();
		var _sts = _snow.getFullYear() + '-' + String(_snow.getMonth()+1).padStart(2,'0') + '-' + String(_snow.getDate()).padStart(2,'0')
				+ ' ' + String(_snow.getHours()).padStart(2,'0') + ':' + String(_snow.getMinutes()).padStart(2,'0') + ':' + String(_snow.getSeconds()).padStart(2,'0');
		var sep = '\n' +
			'\x1b[1;90m\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\x1b[0m\n' +
			'\x1b[1;36m\u25ba Step ' + (stepIdx + 1) + '/' + totalSteps + ': ' + (stepLabel || action) + '\x1b[0m  \x1b[90m' + _sts + '\x1b[0m\n' +
			'\x1b[90m\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\x1b[0m\n';
		appendAnsi(outputElId, sep);
		paceHourglassStart();
		var jobParams = {};
		for (var k in params) {
			if (Object.prototype.hasOwnProperty.call(params, k)) jobParams[k] = params[k];
		}
		jobParams.job_cmd = action;
		return callApi('start_job', jobParams)
			.then(function (startRes) {
				if (!startRes.success) {
					paceHourglassStop();
					return { done: true, success: false, rc: 1, message: startRes.message || 'start_job failed', text: '' };
				}
				var token = startRes.token;
				var offset = 0;
				return new Promise(function (resolve) {
					function poll() {
						callApi('poll_job', { job_token: token, offset: String(offset) })
							.then(function (pr) {
								if (pr.text) appendAnsi(outputElId, pr.text);
								if (pr.offset !== undefined) offset = Number(pr.offset);
								if (pr.done) {
									paceHourglassStop();
									resolve(pr);
								} else {
									setTimeout(poll, 500);
								}
							})
							.catch(function (pollErr) {
								paceHourglassStop();
								resolve({ done: true, success: false, rc: 1, message: pollErr.message || String(pollErr), text: '' });
							});
					}
					poll();
				});
			})
			.catch(function (err) {
				paceHourglassStop();
				return { done: true, success: false, rc: 1, message: err.message || String(err), text: '' };
			});
	}

	function humanBytes(bytes) {
		if (!isFinite(bytes) || bytes <= 0) return '0 B';
		var units = ['B', 'KiB', 'MiB', 'GiB', 'TiB'];
		var i = 0;
		var v = bytes;
		while (v >= 1024 && i < units.length - 1) {
			v /= 1024;
			i++;
		}
		return v.toFixed(i === 0 ? 0 : 2) + ' ' + units[i];
	}

	function parseHumanBytes(text) {
		var raw = String(text || '').trim();
		if (!raw) return null;
		var m = raw.match(/^([0-9]+(?:[.,][0-9]+)?)\s*([kmgtp]?i?b?|b)?$/i);
		if (!m) return null;
		var num = Number(String(m[1]).replace(',', '.'));
		if (!isFinite(num) || num < 0) return null;
		var unit = String(m[2] || 'b').toLowerCase();
		if (unit === '' || unit === 'b') unit = 'b';
		var mul = 1;
		if (unit === 'k' || unit === 'kb' || unit === 'kib') mul = Math.pow(1024, 1);
		else if (unit === 'm' || unit === 'mb' || unit === 'mib') mul = Math.pow(1024, 2);
		else if (unit === 'g' || unit === 'gb' || unit === 'gib') mul = Math.pow(1024, 3);
		else if (unit === 't' || unit === 'tb' || unit === 'tib') mul = Math.pow(1024, 4);
		else if (unit === 'p' || unit === 'pb' || unit === 'pib') mul = Math.pow(1024, 5);
		else if (unit !== 'b') return null;
		var bytes = num * mul;
		if (!isFinite(bytes) || bytes < 0) return null;
		return bytes;
	}

	function updateHumanFieldFromSector(sectorId, humanId) {
		// humanId here is now the numeric-input half (e.g. mcTargetStartNum)
		// and there is a paired unit selector named humanId + 'Unit' → mcTargetStartNumUnit
		// Legacy text-only pairs (newStartHuman etc.) keep old behaviour.
		var s = document.getElementById(sectorId);
		var h = document.getElementById(humanId);
		if (!s || !h) return;
		var raw = String(s.value || '').trim();
		if (!/^\d+$/.test(raw)) { h.value = ''; return; }
		var sectors = Number(raw);
		if (!isFinite(sectors) || sectors < 0) { h.value = ''; return; }
		var bytes = sectors * getCurrentSectorSize();
		// If there is a paired unit selector, show the numeric value in the chosen unit
		var unitSelId = humanId + 'Unit';
		var unitSel = document.getElementById(unitSelId);
		if (unitSel) {
			var unit = unitSel.value || 'GiB';
			var mul = unitMul(unit);
			h.value = (mul > 0 ? (bytes / mul).toFixed(3) : '');
		} else {
			h.value = humanBytes(bytes);
		}
	}

	function unitMul(unit) {
		switch (unit) {
			case 'KiB': return Math.pow(1024, 1);
			case 'MiB': return Math.pow(1024, 2);
			case 'GiB': return Math.pow(1024, 3);
			case 'TiB': return Math.pow(1024, 4);
			default:    return Math.pow(1024, 3); // GiB
		}
	}

	function refreshSectorHumanFields() {
		if (state.sectorSyncLock) return;
		state.sectorSyncLock = true;
		updateHumanFieldFromSector('newStartSector', 'newStartHuman');
		updateHumanFieldFromSector('newEndSector', 'newEndHuman');
		updateHumanFieldFromSector('resizeEndSector', 'resizeEndHuman');
		updateHumanFieldFromSector('mcTargetStart', 'mcTargetStartNum');
		updateHumanFieldFromSector('mcTargetEnd', 'mcTargetEndNum');
		state.sectorSyncLock = false;
		updateMcTargetSize();
	}

	function updateMcTargetSize() {
		var startEl = document.getElementById('mcTargetStart');
		var endEl   = document.getElementById('mcTargetEnd');
		var sizeEl  = document.getElementById('mcTargetSizeDisplay');
		if (!sizeEl) return;
		var s = startEl ? String(startEl.value || '').trim() : '';
		var e = endEl   ? String(endEl.value   || '').trim() : '';
		if (!/^\d+$/.test(s) || !/^\d+$/.test(e)) { sizeEl.value = ''; return; }
		var sectors = Number(e) - Number(s) + 1;
		if (sectors <= 0) { sizeEl.value = ''; return; }
		var ss = getCurrentSectorSize();
		sizeEl.value = sectors + ' s  (' + humanBytes(sectors * ss) + ')';
	}

	function updateMcSourceInfo() {
		var infoEl = document.getElementById('mcSourceInfo');
		if (!infoEl) return;
		var devSel  = document.getElementById('mcSourceDevice');
		var partSel = document.getElementById('mcSourcePartNum');
		if (!devSel || !partSel) { infoEl.style.display = 'none'; return; }
		var devPath  = String(devSel.value  || '').trim();
		var partNum  = Number(partSel.value || 0);
		if (!devPath || !partNum) { infoEl.style.display = 'none'; return; }
		var found = findPartitionGlobalByDeviceNum(devPath, partNum);
		if (!found || !found.part) { infoEl.style.display = 'none'; return; }
		var p  = found.part;
		var ss = Number(found.device.logical_sector_size || 512);
		var sz = Number(p.size || 0);
		var lines = [];
		lines.push('Path:  ' + (p.path || devPath + partNum));
		lines.push('Start: ' + (p.start || 0) + ' s' +
		           (p.start ? ('  (' + humanBytes(Number(p.start) * ss) + ')') : ''));
		lines.push('End:   ' + (p.end || 0) + ' s' +
		           (p.end ? ('  (' + humanBytes(Number(p.end) * ss) + ')') : ''));
		lines.push('Size:  ' + sz + ' s  (' + humanBytes(sz * ss) + ')');
		if (p.fs)         lines.push('FS:    ' + p.fs);
		if (p.label)      lines.push('Label: ' + p.label);
		if (p.mountpoint) lines.push('Mount: ' + p.mountpoint);
		infoEl.textContent = lines.join('\n');
		infoEl.style.display = '';
	}

	function syncSectorFromHumanField(humanId, sectorId) {
		if (state.sectorSyncLock) return;
		var h = document.getElementById(humanId);
		var s = document.getElementById(sectorId);
		if (!h || !s) return;

		var txt = String(h.value || '').trim();
		if (!txt) {
			state.sectorSyncLock = true;
			s.value = '';
			state.sectorSyncLock = false;
			s.dispatchEvent(new Event('input', { bubbles: true }));
			return;
		}

		var num = Number(txt.replace(',', '.'));
		var secSize = getCurrentSectorSize();
		var bytes;

		// Check for a paired unit selector (mcTargetStartNumUnit etc.)
		var unitSelId = humanId + 'Unit';
		var unitSel = document.getElementById(unitSelId);
		if (unitSel) {
			// Numeric-with-unit input
			if (!isFinite(num) || num < 0) return;
			bytes = num * unitMul(unitSel.value || 'GiB');
		} else {
			// Legacy free-text input (e.g. "10 GiB")
			bytes = parseHumanBytes(txt);
			if (bytes === null) return;
		}

		var sectors = Math.floor(bytes / secSize);
		if (bytes > 0 && sectors === 0) sectors = 1;
		if (!isFinite(sectors) || sectors < 0) return;

		state.sectorSyncLock = true;
		s.value = String(sectors);
		// Don't reformat the numeric field — user is typing
		state.sectorSyncLock = false;
		s.dispatchEvent(new Event('input', { bubbles: true }));
	}

	function bindSectorHumanPair(sectorId, humanId) {
		var s = document.getElementById(sectorId);
		var h = document.getElementById(humanId);
		if (!s || !h) return;
		s.addEventListener('input', refreshSectorHumanFields);
		h.addEventListener('input', function () { syncSectorFromHumanField(humanId, sectorId); });
		h.addEventListener('change', function () { syncSectorFromHumanField(humanId, sectorId); });
	}

	function escapeHtml(v) {
		return String(v === undefined || v === null ? '' : v)
			.replace(/&/g, '&amp;')
			.replace(/</g, '&lt;')
			.replace(/>/g, '&gt;')
			.replace(/"/g, '&quot;')
			.replace(/'/g, '&#39;');
	}

	function tooltipKV(key, value) {
		return '<div class="pcgi-hover-tooltip-key">' + escapeHtml(key) + '</div><div class="pcgi-hover-tooltip-value">' + escapeHtml(value) + '</div>';
	}

	function getCurrentSectorSize() {
		var dev = getSelectedDeviceData();
		var ss = Number(dev && dev.logical_sector_size ? dev.logical_sector_size : 512);
		if (!isFinite(ss) || ss <= 0) ss = 512;
		return ss;
	}

	function bindSectorFieldTooltip(inputId, labelText) {
		var el = document.getElementById(inputId);
		if (!el) return;

		function buildHtml() {
			var raw = (el.value || '').trim();
			if (!/^\d+$/.test(raw)) {
				el.title = '';
				return '<div class="pcgi-hover-tooltip-grid">' +
					tooltipKV(labelText, 'Enter a numeric sector value') +
				'</div>';
			}
			var sectors = Number(raw);
			var secSize = getCurrentSectorSize();
			var bytes = sectors * secSize;
			el.title = sectors + ' sectors (~' + humanBytes(bytes) + ', ' + secSize + ' B/sector)';
			return '<div class="pcgi-hover-tooltip-grid">' +
				tooltipKV(labelText, sectors + ' sectors') +
				tooltipKV('Approx size', humanBytes(bytes)) +
				tooltipKV('Sector size', secSize + ' B') +
			'</div>';
		}

		el.addEventListener('mouseenter', function (ev) {
			showHoverTooltip(ev, buildHtml());
		});
		el.addEventListener('mousemove', moveHoverTooltip);
		el.addEventListener('mouseleave', hideHoverTooltip);
		el.addEventListener('input', buildHtml);
	}

	function buildPartitionTooltipHtml(p, logical, fsUsed, fsAvail) {
		var rows = '';
		rows += tooltipKV('Number', p.number || '-');
		rows += tooltipKV('Start', String(p.start || 0) + 's');
		rows += tooltipKV('End', String(p.end || 0) + 's');
		rows += tooltipKV('Size', humanBytes(Number(p.size || 0) * logical));
		rows += tooltipKV('File system', p.fs || '-');
		rows += tooltipKV('Name', p.name || '-');
		rows += tooltipKV('Flags', p.flags || '-');
		rows += tooltipKV('Label', p.label || '-');
		rows += tooltipKV('Path', p.path || '-');
		rows += tooltipKV('Used', humanBytes(fsUsed));
		rows += tooltipKV('Unused', humanBytes(fsAvail));
		if (p.mountpoint) rows += tooltipKV('Mounted at', p.mountpoint);
		return '<div class="pcgi-hover-tooltip-grid">' + rows + '</div>';
	}

	function buildDiskTooltipHtml(dev) {
		var total = Number(dev && dev.total_sectors ? dev.total_sectors : 0);
		var logical = Number(dev && dev.logical_sector_size ? dev.logical_sector_size : 512);
		var rows = '';
		rows += tooltipKV('Disk', (dev && dev.path) ? dev.path : '-');
		rows += tooltipKV('Name', (dev && dev.name) ? dev.name : '-');
		rows += tooltipKV('Model', (dev && dev.model) ? dev.model : '-');
		rows += tooltipKV('Vendor', (dev && dev.vendor) ? dev.vendor : '-');
		rows += tooltipKV('Serial', (dev && dev.serial) ? dev.serial : '-');
		rows += tooltipKV('Transport', (dev && dev.transport) ? dev.transport : '-');
		rows += tooltipKV('Partition table', (dev && dev.table) ? dev.table : '-');
		rows += tooltipKV('Sector size', logical + ' B');
		rows += tooltipKV('Total sectors', total > 0 ? String(total) : '-');
		rows += tooltipKV('Disk size', total > 0 ? humanBytes(total * logical) : '-');
		return '<div class="pcgi-hover-tooltip-grid">' + rows + '</div>';
	}

	function showHoverTooltip(ev, html) {
		if (state.dragCtx || state.mapDragActive || state.contextMenuVisible) {
			hideHoverTooltip();
			return;
		}
		var tip = document.getElementById('pcgiHoverTooltip');
		if (!tip) return;
		tip.innerHTML = html;
		tip.style.display = 'block';
		moveHoverTooltip(ev);
	}

	function moveHoverTooltip(ev) {
		if (state.dragCtx || state.mapDragActive || state.contextMenuVisible) {
			hideHoverTooltip();
			return;
		}
		var tip = document.getElementById('pcgiHoverTooltip');
		if (!tip || tip.style.display === 'none') return;
		var x = ev.clientX + 12;
		var y = ev.clientY + 12;
		var maxX = window.innerWidth - tip.offsetWidth - 8;
		var maxY = window.innerHeight - tip.offsetHeight - 8;
		if (x > maxX) x = Math.max(8, ev.clientX - tip.offsetWidth - 12);
		if (y > maxY) y = Math.max(8, ev.clientY - tip.offsetHeight - 12);
		tip.style.left = x + 'px';
		tip.style.top = y + 'px';
	}

	function hideHoverTooltip() {
		var tip = document.getElementById('pcgiHoverTooltip');
		if (!tip) return;
		tip.style.display = 'none';
		tip.innerHTML = '';
	}

	function logTo(id, msg, clear) {
		var el = document.getElementById(id);
		if (!el) return;
		if (clear) {
			el.textContent = msg;
		} else {
			if (el.textContent.length > 0) {
				el.textContent += '\n\n';
			}
			el.textContent += msg;
		}
		el.scrollTop = el.scrollHeight;
	}

	function paceHourglassStart() {
		var log = document.getElementById('cmdOutput');
		if (log) log.style.cursor = 'wait';
		if (!window.Pace) return;
		try { Pace.stop(); } catch (e) {}
		try { Pace.bar.render(); } catch (e) {}
	}

	function paceHourglassStop() {
		var log = document.getElementById('cmdOutput');
		if (log) log.style.cursor = '';
		if (!window.Pace) return;
		try {
			Pace.stop();
		} catch (e) {
			// Ignore Pace stop errors.
		}
	}

	function summarizeTools(res) {
		var tools = res.tools || [];
		var available = {};
		var missing = [];

		for (var i = 0; i < tools.length; i++) {
			available[tools[i].name] = !!tools[i].available;
			if (!tools[i].available) {
				missing.push(tools[i].name);
			}
		}

		var required = ['parted', 'partclone.dd'];
		var requiredMissing = [];
		for (var r = 0; r < required.length; r++) {
			if (!available[required[r]]) requiredMissing.push(required[r]);
		}

		var featureIssues = [];
		if (!available['partprobe']) featureIssues.push('kernel partition table refresh');
		if (!available['mkfs.fat']) featureIssues.push('FAT filesystem creation');
		if (!available['fsck.fat']) featureIssues.push('FAT filesystem checks');
		if (!available['fatlabel']) featureIssues.push('FAT label changes');
		if (!available['mkfs.exfat']) featureIssues.push('exFAT filesystem creation');
		if (!available['fsck.exfat']) featureIssues.push('exFAT filesystem checks');
		if (!available['exfatlabel']) featureIssues.push('exFAT label changes');
		if (!available['mke2fs/e2fsprogs']) featureIssues.push('ext filesystem creation');
		if (!available['e2fsck/e2fsprogs']) featureIssues.push('ext filesystem checks');
		if (!available['resize2fs/e2fsprogs']) featureIssues.push('ext filesystem resize');
		if (!available['fatresize']) featureIssues.push('FAT filesystem resize');
		if (!available['mkntfs']) featureIssues.push('NTFS filesystem creation');
		if (!available['ntfsfix']) featureIssues.push('NTFS check/repair');
		if (!available['ntfsinfo']) featureIssues.push('NTFS metadata inspection');
		if (!available['ntfslabel']) featureIssues.push('NTFS label updates');
		if (!available['ntfsresize']) featureIssues.push('NTFS filesystem resize');
		if (!available['mount']) featureIssues.push('mount operations');
		if (!available['umount']) featureIssues.push('unmount operations');
		if (!available['partclone.dd']) featureIssues.push('sector-by-sector clone/move (partclone.dd)');
		if (!available['partclone.chkimg']) featureIssues.push('optional smart clone verification');
		if (!available['partition_migration.sh']) featureIssues.push('full partition move/clone pipeline (partition_migration.sh)');
		if (!available['smartctl']) featureIssues.push('SMART diagnostics');
		if (!available['hdparm']) featureIssues.push('drive identify (hdparm)');
		if (!available['gdisk'] && !available['sgdisk']) featureIssues.push('GPT diagnostics');

		return {
			available: available,
			missing: missing,
			requiredMissing: requiredMissing,
			featureIssues: featureIssues,
			e2mode: res.e2fsprogs_mode || '-'
		};
	}

	function renderToolSummary(summary) {
		var box = document.getElementById('toolSummaryBox');
		var title = document.getElementById('toolSummaryTitle');
		var meta = document.getElementById('toolSummaryMeta');
		var missWrap = document.getElementById('toolSummaryMissingWrap');
		var miss = document.getElementById('toolSummaryMissing');
		var impact = document.getElementById('toolSummaryImpact');

		if (!box || !title || !meta || !missWrap || !miss || !impact) return;

		box.className = 'pcgi-tool-summary ';
		meta.textContent = 'e2fsprogs mode: ' + summary.e2mode;

		if (summary.missing.length === 0) {
			box.className += 'pcgi-tool-summary-ok';
			title.textContent = t('toolAllAvailable');
			missWrap.style.display = 'none';
			impact.textContent = '';
			return;
		}

		if (summary.requiredMissing.length > 0) {
			box.className += 'pcgi-tool-summary-danger';
			title.textContent = t('toolRequiredMissing');
		} else {
			box.className += 'pcgi-tool-summary-warn';
			title.textContent = t('toolOptionalMissing');
		}

		missWrap.style.display = '';
		miss.textContent = summary.missing.join(', ');

		if (summary.featureIssues.length > 0) {
			impact.textContent = 'Unavailable features: ' + summary.featureIssues.join(', ') + '.';
		} else {
			impact.textContent = '';
		}
	}

	function buildCommandPreview(action, params) {
		function v(x) { return String(x === undefined || x === null ? '' : x); }
		if (action === 'create_partition') {
			var role = v(params.part_role || 'primary');
			var fsHint = v(params.fs_hint || '');
			var base = fsHint ?
				('parted -s ' + v(params.device) + ' unit s mkpart ' + role + ' ' + fsHint + ' ' + v(params.start_sector) + 's ' + v(params.end_sector) + 's') :
				('parted -s ' + v(params.device) + ' unit s mkpart ' + role + ' ' + v(params.start_sector) + 's ' + v(params.end_sector) + 's');
			if (v(params.part_name)) {
				base += '\nNEW_PARTNUM="$(parted -s -m ' + v(params.device) + ' unit s print | awk -F: \'/^[0-9]+:/{n=$1} END{print n}\')"';
				base += '\nparted -s ' + v(params.device) + ' name "$NEW_PARTNUM" ' + v(params.part_name);
			}
			base += '\npartprobe ' + v(params.device);
			if (v(params.create_fs) === '1' && fsHint) {
				var lbl = v(params.part_label || '');
				var lblOpt = lbl ? (' -L ' + lbl) : '';
				var ext = /^ext[234]$/.test(fsHint);
				var fat = /^fat(16|32)$/.test(fsHint);
				var exfat = fsHint === 'exfat';
				var ntfs = fsHint === 'ntfs';
				var f2fs = fsHint === 'f2fs';
				var partDev = v(params.device) + '${NEW_PARTNUM:-N}';
				if (ext) base += '\nmke2fs -v -F -t ' + fsHint + (lbl ? ' -L ' + lbl : '') + ' ' + partDev;
				else if (fat) base += '\nmkfs.fat -v -F ' + fsHint.replace('fat','') + (lbl ? ' -n ' + lbl : '') + ' ' + partDev;
				else if (exfat) base += '\nmkfs.exfat' + (lbl ? ' -n ' + lbl : '') + ' ' + partDev;
				else if (ntfs) base += '\n# parted mkpart creates NTFS; optionally: mkntfs -Q -f' + (lbl ? ' -L ' + lbl : '') + ' ' + partDev;
				else if (f2fs) base += '\nmkfs.f2fs' + (lbl ? ' -l ' + lbl : '') + ' ' + partDev;
			}
			if (v(params.mount_point)) {
				base += '\nmkdir -p ' + v(params.mount_point);
				base += '\nmount ' + v(params.device) + '${NEW_PARTNUM:-N} ' + v(params.mount_point);
			}
			return base;
		}
		if (action === 'delete_partition') {
			return 'parted -s ' + v(params.device) + ' rm ' + v(params.partnum) + '\npartprobe ' + v(params.device);
		}
		if (action === 'resize_partition') {
			var txt = 'parted -s ' + v(params.device) + ' unit s resizepart ' + v(params.partnum) + ' ' + v(params.end_sector) + 's\npartprobe ' + v(params.device);
			if (v(params.resize_fs) === 'yes') {
				txt += '\n# backend will auto-detect filesystem and run ext/ntfs/fat resize tools when available';
			}
			return txt;
		}
		if (action === 'resize_filesystem') {
			var fstype = v(params.fs_type).toLowerCase();
			var direction = v(params.direction).toLowerCase() || 'grow';
			if (fstype === 'ext2' || fstype === 'ext3' || fstype === 'ext4') {
				if (direction === 'shrink') {
					return 'e2fsck -f -p ' + v(params.partition) + '\nresize2fs ' + v(params.partition) + ' ' + v(params.target_kib) + 'K';
				}
				return 'resize2fs ' + v(params.partition);
			}
			if (fstype === 'ntfs') {
				if (direction === 'shrink') {
					return 'ntfsresize -f -s ' + v(params.target_bytes) + ' ' + v(params.partition);
				}
				return 'ntfsresize -f ' + v(params.partition);
			}
			if (fstype === 'fat' || fstype === 'fat12' || fstype === 'fat16' || fstype === 'fat32' || fstype === 'vfat') {
				if (direction === 'shrink') {
					return 'fatresize -vps ' + v(params.target_bytes) + ' ' + v(params.partition);
				}
				return 'fatresize -vps max ' + v(params.partition);
			}
			return '# unsupported fs resize preview for fs_type=' + fstype + ' partition=' + v(params.partition);
		}
		if (action === 'create_filesystem') {
			var opts = v(params.extra_opts || '').trim();
			var pre = '';
			if (v(params.fs_type) === 'ext2' || v(params.fs_type) === 'ext3' || v(params.fs_type) === 'ext4') {
				pre = 'mke2fs -F -t ' + v(params.fs_type) + (opts ? (' ' + opts) : '') + ' ' + v(params.partition);
				if (v(params.label)) pre += '\ne2label ' + v(params.partition) + ' ' + v(params.label);
				return pre;
			}
			if (v(params.fs_type) === 'fat16') {
				pre = 'mkfs.fat -F 16' + (opts ? (' ' + opts) : '') + ' ' + v(params.partition);
				if (v(params.label)) pre += '\nfatlabel ' + v(params.partition) + ' ' + v(params.label);
				return pre;
			}
			if (v(params.fs_type) === 'fat32' || v(params.fs_type) === 'vfat') {
				pre = 'mkfs.fat -F 32' + (opts ? (' ' + opts) : '') + ' ' + v(params.partition);
				if (v(params.label)) pre += '\nfatlabel ' + v(params.partition) + ' ' + v(params.label);
				return pre;
			}
			if (v(params.fs_type) === 'exfat') {
				pre = 'mkfs.exfat' + (v(params.label) ? (' -n ' + v(params.label)) : '') + (opts ? (' ' + opts) : '') + ' ' + v(params.partition);
				if (v(params.label)) pre += '\n# backend may use exfatlabel/tune.exfat to ensure label';
				return pre;
			}
			if (v(params.fs_type) === 'ntfs') {
				pre = 'mkntfs -f -v' + (v(params.label) ? (' -L ' + v(params.label)) : '') + (opts ? (' ' + opts) : '') + ' ' + v(params.partition);
				return pre;
			}
		}
		if (action === 'set_label') {
			var lblFstype = v(params.fs_type).toLowerCase();
			var lblTarget = v(params.partition);
			var lblValue = v(params.label);
			if (lblFstype === 'ext2' || lblFstype === 'ext3' || lblFstype === 'ext4') {
				return 'e2label ' + lblTarget + ' ' + lblValue;
			}
			if (lblFstype === 'fat' || lblFstype === 'fat12' || lblFstype === 'fat16' || lblFstype === 'fat32' || lblFstype === 'vfat') {
				return 'fatlabel ' + lblTarget + ' ' + lblValue;
			}
			if (lblFstype === 'exfat') {
				return 'exfatlabel ' + lblTarget + ' ' + lblValue;
			}
			if (lblFstype === 'ntfs') {
				return 'ntfslabel ' + lblTarget + ' ' + lblValue;
			}
			return '# backend auto-detects FS for ' + lblTarget + '\n# ext: e2label, fat: fatlabel, exfat: exfatlabel, ntfs: ntfslabel\n# label=' + lblValue;
		}
		if (action === 'set_partition_name') {
			return 'parted -s ' + v(params.device) + ' name ' + v(params.partnum) + ' ' + v(params.part_name);
		}
		if (action === 'set_partition_flag') {
			return 'parted -s ' + v(params.device) + ' set ' + v(params.partnum) + ' ' + v(params.flag) + ' ' + v(params.state);
		}
		if (action === 'move_partition') {
			var moveMode = String(params.clone_mode || 'smart').toLowerCase();
			var moveSourceDev = v(params.source_device || params.device);
			var moveSourcePart = v(params.source_partition || '');
			var moveSourcePartnum = v(params.source_partnum || params.partnum || '');
			var moveTargetMount = String(params.target_mountpoint || '').trim();
			var moveAlign = String(params.align_bytes || '4096');
			var moveUnmount = String(params.unmount_before || 'yes').toLowerCase();
			var moveDelay = String(params.step_delay || '0');
			var moveVerify = String(params.partclone_verify || 'no').toLowerCase();
			var moveExtra = String(params.partclone_extra || '').trim();
			var moveForceFs = String(params.force_fs || '').trim();
			if (!moveSourcePart&&moveSourcePartnum){
				if (/[0-9]$/.test(moveSourceDev)) moveSourcePart = moveSourceDev + 'p' + moveSourcePartnum;
				else moveSourcePart = moveSourceDev + moveSourcePartnum;
			}
			var wf = 'partition_migration.sh';
			wf += ' \\\n  -d ' + JSON.stringify(v(params.device));
			wf += ' \\\n  -D ' + JSON.stringify(moveSourceDev);
			wf += ' \\\n  -p ' + JSON.stringify(moveSourcePart);
			wf += ' \\\n  -n ' + JSON.stringify(moveSourcePartnum);
			wf += ' \\\n  -S ' + v(params.start_sector);
			wf += ' \\\n  -E ' + v(params.end_sector);
			if (moveMode === 'sector') wf += ' \\\n  -c dd';
			wf += ' \\\n  -a ' + (moveAlign === '512' ? '512' : '4096');
			wf += ' \\\n  -w ' + (/^\d+$/.test(moveDelay) ? moveDelay : '0');
			wf += ' \\\n  -M';
			if (moveUnmount !== 'no') wf += ' -u';
			if (moveVerify === 'yes') wf += ' -V';
			if (moveForceFs) wf += ' \\\n  -f ' + JSON.stringify(moveForceFs);
			if (moveExtra) wf += ' \\\n  -x ' + JSON.stringify(moveExtra);
			if (moveTargetMount) wf += ' \\\n  -o -t ' + JSON.stringify(moveTargetMount);
			return wf;
		}
		if (action === 'clone_partition_dd') {
			var cloneMode = String(params.clone_mode || 'smart').toLowerCase();
			var cloneSourceDev = v(params.source_device || params.device);
			var cloneTargetDev = v(params.target_device || params.device);
			var cloneSrcPart = v(params.source_partition || '');
			var cloneSrcPartnum = v(params.source_partnum || '');
			var cloneTargetStart = v(params.target_start_sector || '');
			var cloneTargetEnd = v(params.target_end_sector || '');
			var cloneTargetMount = String(params.target_mountpoint || '').trim();
			var cloneAlign = String(params.align_bytes || '4096');
			var cloneUnmount = String(params.unmount_before || 'yes').toLowerCase();
			var cloneDelay = String(params.step_delay || '0');
			var cloneVerify = String(params.partclone_verify || 'no').toLowerCase();
			var cloneExtra = String(params.partclone_extra || '').trim();
			var cloneForceFs = String(params.force_fs || '').trim();
			if (!cloneSrcPart&&cloneSrcPartnum){
				if (/[0-9]$/.test(cloneSourceDev)) cloneSrcPart = cloneSourceDev + 'p' + cloneSrcPartnum;
				else cloneSrcPart = cloneSourceDev + cloneSrcPartnum;
			}
			var out = 'partition_migration.sh';
			out += ' \\\n  -d ' + JSON.stringify(cloneTargetDev);
			out += ' \\\n  -D ' + JSON.stringify(cloneSourceDev);
			out += ' \\\n  -p ' + JSON.stringify(cloneSrcPart);
			out += ' \\\n  -n ' + JSON.stringify(cloneSrcPartnum);
			out += ' \\\n  -S ' + cloneTargetStart;
			out += ' \\\n  -E ' + cloneTargetEnd;
			if (cloneMode === 'sector') out += ' \\\n  -c dd';
			out += ' \\\n  -a ' + (cloneAlign === '512' ? '512' : '4096');
			out += ' \\\n  -w ' + (/^\d+$/.test(cloneDelay) ? cloneDelay : '0');
			if (cloneUnmount !== 'no') out += ' -u';
			if (cloneVerify === 'yes') out += ' -V';
			if (cloneForceFs) out += ' \\\n  -f ' + JSON.stringify(cloneForceFs);
			if (cloneExtra) out += ' \\\n  -x ' + JSON.stringify(cloneExtra);
			if (cloneTargetMount) out += ' \\\n  -o -t ' + JSON.stringify(cloneTargetMount);
			return out;
		}
		if (action === 'mount_partition') {
			var mtarget = v(params.partition);
			var mtxt = '';
			if (!mtarget) {
				mtxt += 'TARGET_PARTNUM="' + v(params.target_partnum || '') + '"\n';
				mtxt += 'if [ -z "$TARGET_PARTNUM" ]; then TARGET_PARTNUM="$(parted -s -m ' + v(params.device) + ' unit s print | awk -F: -v s="' + v(params.target_start_sector) + '" -v e="' + v(params.target_end_sector) + '" \'$1 ~ /^[0-9]+$/ { gsub(/s$/, "", $2); gsub(/s$/, "", $3); if ($2 == s && $3 == e) { print $1; exit } }\')"; fi\n';
				mtxt += 'if echo "' + v(params.device) + '" | grep -Eq "[0-9]$"; then TARGET_PART="' + v(params.device) + 'p${TARGET_PARTNUM}"; else TARGET_PART="' + v(params.device) + '${TARGET_PARTNUM}"; fi\n';
				mtarget = '"$TARGET_PART"';
			}
			var mountpoint = v(params.mountpoint || '');
			if (!mountpoint) {
				mtxt += 'AUTO_MP="/var/media/ftp/$(basename ' + mtarget + ')"\n';
				mountpoint = '"$AUTO_MP"';
			}
			mtxt += 'mkdir -p ' + mountpoint + '\nmount';
			var mfs = v(params.fs_type).toLowerCase();
			if (mfs === 'fat' || mfs === 'fat12' || mfs === 'fat16' || mfs === 'fat32') mfs = 'vfat';
			if (mfs && mfs !== 'auto') mtxt += ' -t ' + mfs;
			if (v(params.mount_opts)) mtxt += ' -o ' + v(params.mount_opts);
			mtxt += ' ' + mtarget + ' ' + mountpoint;
			return mtxt;
		}
		if (action === 'unmount_partition') {
			return 'umount ' + v(params.partition || params.mountpoint);
		}
		if (action === 'check_filesystem') {
			var fs = v(params.fs_type).toLowerCase();
			var repair = v(params.repair) === 'yes';
			var target = v(params.partition);
			var extra = v(params.extra_opts).trim();
			if (!target) return '# fs check preview unavailable: missing partition path';

			if (!fs || fs === 'auto') {
				var autoTxt = '# backend auto-detects filesystem for ' + target + '\n';
				autoTxt += '# requested mode: ' + (repair ? 'repair' : 'read-only') + '\n';
				autoTxt += '# extra opts: ' + (extra || '(none)');
				return autoTxt;
			}

			if (fs === 'ext2' || fs === 'ext3' || fs === 'ext4') {
				return 'e2fsck -f ' + (repair ? '-p' : '-n') + (extra ? (' ' + extra) : '') + ' ' + target;
			}
			if (fs === 'fat' || fs === 'fat12' || fs === 'fat16' || fs === 'fat32' || fs === 'vfat') {
				return 'fsck.fat ' + (repair ? '-a' : '-n') + (extra ? (' ' + extra) : '') + ' ' + target;
			}
			if (fs === 'exfat') {
				return 'fsck.exfat' + (repair ? '' : ' -n') + (extra ? (' ' + extra) : '') + ' ' + target;
			}
			if (fs === 'ntfs') {
				return 'ntfsfix' + (repair ? '' : ' -n') + (extra ? (' ' + extra) : '') + ' ' + target + '\n# fallback: ntfsinfo -m ' + target;
			}

			return '# unsupported fs_type=' + fs + ' target=' + target;
		}
		if (action === 'smart_info') return 'smartctl --xall ' + v(params.device) + '\n# fallback: smartctl -d sat,auto -T permissive -x ' + v(params.device) + '\n# info-only fallback: smartctl -d sat,auto -T permissive -i ' + v(params.device);
		if (action === 'smart_selftest_short') return 'smartctl -t short ' + v(params.device) + '\n# wait for completion (~2 min), then:\nsmartctl -l selftest ' + v(params.device);
		if (action === 'badblocks_scan') return 'badblocks -sv ' + v(params.device) + '  # read-only scan, may take a long time on large disks';
		if (action === 'hdparm_info') return 'hdparm -I ' + v(params.device);
		if (action === 'gpt_info') return '# backend uses sgdisk -p or gdisk -l for ' + v(params.device);
		if (action === 'reload_table') return 'partprobe ' + v(params.device);
		if (action === 'verify_partition') {
			var vpA = v(params.source_partition);
			var vpB = v(params.compare_partition);
			var vpUnmount = String(params.unmount_before || 'no').toLowerCase();
			var vpDelay = String(params.step_delay || '0');
			var out = 'partition_migration.sh';
			out += ' \\\n  -p ' + JSON.stringify(vpA);
			out += ' \\\n  -Z ' + JSON.stringify(vpB);
			if (vpUnmount === 'yes') out += ' -u';
			out += ' \\\n  -w ' + (/^\d+$/.test(vpDelay) ? vpDelay : '0');
			return out;
		}
		if (action === 'disk_migration') {
			var dmSrc  = v(params.source_device);
			var dmTgt  = v(params.target_device);
			var dmMove = String(params.move_mode      || 'no').toLowerCase() === 'yes';
			var dmPhys = String(params.physical_mode  || 'no').toLowerCase() === 'yes';
			var dmIncT = String(params.include_tail   || 'no').toLowerCase() === 'yes';
			var dmMbr  = String(params.copy_mbr       || 'no').toLowerCase() === 'yes';
			var dmWipe = String(params.wipe_target    || 'no').toLowerCase() === 'yes';
			var dmUmnt = String(params.unmount_before || 'no').toLowerCase() === 'yes';
			var dmVer  = String(params.verify_clone   || 'no').toLowerCase() === 'yes';
			var dmMode = v(params.clone_mode  || 'smart');
			var dmAln  = v(params.align_bytes || '4096');
			var dmDly  = v(params.step_delay  || '1');
			var dmFs   = v(params.force_fs    || '');
			var dmXtra = v(params.extra_opts  || '');
			var out = 'disk_migration.sh';
			out += ' \\\n  -D ' + JSON.stringify(dmSrc);
			out += ' \\\n  -d ' + JSON.stringify(dmTgt);
			if (!dmPhys) {
				out += ' \\\n  -c ' + dmMode;
				out += ' \\\n  -a ' + dmAln;
			}
			out += ' \\\n  -w ' + (/^\d+$/.test(dmDly) ? dmDly : '1');
			if (dmPhys) out += ' -P';
			if (dmIncT) out += ' -T';
			if (dmMove) out += ' -M';
			if (dmMbr)  out += ' -B';
			if (dmWipe) out += ' -W';
			if (dmUmnt) out += ' -u';
			if (dmVer)  out += ' -V';
			if (dmFs)   out += ' \\\n  -f ' + JSON.stringify(dmFs);
			if (dmXtra) out += ' \\\n  -x ' + JSON.stringify(dmXtra);
			return out;
		}
		if (action === 'partclone_export') {
			var piSrc  = v(params.partition);
			var piOut  = v(params.output_file || '');
			var piComp = v(params.compression || 'none');
			var piFs   = v(params.force_fs || '');
			var piVer  = String(params.verify         || 'no') === 'yes';
			var piUmnt = String(params.unmount_before || 'yes') === 'yes';
			var piDd   = String(params.use_dd         || 'no') === 'yes';
			var piDly  = v(params.step_delay || '1');
			var piXtra = v(params.extra_opts || '');
			var out = 'partition_image.sh -e';
			if (piUmnt) out += ' -u';
			if (piVer)  out += ' -V';
			if (piDd)   out += ' -c';
			out += ' \\\n  -p ' + JSON.stringify(piSrc);
			out += ' \\\n  -o ' + JSON.stringify(piOut);
			if (piComp && piComp !== 'none') out += ' \\\n  -z ' + piComp;
			if (piFs)   out += ' \\\n  -f ' + JSON.stringify(piFs);
			out += ' \\\n  -w ' + (/^\d+$/.test(piDly) ? piDly : '1');
			if (piXtra) out += ' \\\n  -x ' + JSON.stringify(piXtra);
			return out;
		}
		if (action === 'partclone_import') {
			var piTgt  = v(params.partition);
			var piIn   = v(params.input_file || '');
			var piComp = v(params.compression || 'none');
			var piVer  = String(params.verify         || 'no') === 'yes';
			var piUmnt = String(params.unmount_before || 'yes') === 'yes';
			var piDly  = v(params.step_delay || '1');
			var piXtra = v(params.extra_opts || '');
			var out = 'partition_image.sh -i';
			if (piUmnt) out += ' -u';
			if (piVer)  out += ' -V';
			out += ' \\\n  -p ' + JSON.stringify(piTgt);
			out += ' \\\n  -o ' + JSON.stringify(piIn);
			if (piComp && piComp !== 'none') out += ' \\\n  -z ' + piComp;
			out += ' \\\n  -w ' + (/^\d+$/.test(piDly) ? piDly : '1');
			if (piXtra) out += ' \\\n  -x ' + JSON.stringify(piXtra);
			return out;
		}
		if (action === 'partclone_net_send') {
			var nsSrc  = v(params.partition);
			var nsHost = v(params.net_host || '');
			var nsPort = v(params.net_port || '9000');
			var nsComp = v(params.compression || 'none');
			var nsFs   = v(params.force_fs || '');
			var nsUmnt = String(params.unmount_before || 'yes') === 'yes';
			var nsMc   = String(params.multicast || 'no') === 'yes';
			var nsDly  = v(params.step_delay || '1');
			var out = 'partition_image.sh -N';
			if (nsUmnt) out += ' -u';
			if (nsMc)   out += ' -m';
			out += ' \\\n  -p ' + JSON.stringify(nsSrc);
			if (nsHost) out += ' \\\n  -H ' + JSON.stringify(nsHost);
			out += ' \\\n  -P ' + nsPort;
			if (nsComp && nsComp !== 'none') out += ' \\\n  -z ' + nsComp;
			if (nsFs)   out += ' \\\n  -f ' + JSON.stringify(nsFs);
			out += ' \\\n  -w ' + (/^\d+$/.test(nsDly) ? nsDly : '1');
			return out;
		}
		if (action === 'partclone_net_recv') {
			var nrTgt  = v(params.partition);
			var nrHost = v(params.net_host || '');
			var nrPort = v(params.net_port || '9000');
			var nrComp = v(params.compression || 'none');
			var nrVer  = String(params.verify         || 'no') === 'yes';
			var nrUmnt = String(params.unmount_before || 'yes') === 'yes';
			var nrMc   = String(params.multicast || 'no') === 'yes';
			var nrDly  = v(params.step_delay || '1');
			var out = 'partition_image.sh -R';
			if (nrUmnt) out += ' -u';
			if (nrVer)  out += ' -V';
			if (nrMc)   out += ' -m';
			out += ' \\\n  -p ' + JSON.stringify(nrTgt);
			if (nrHost) out += ' \\\n  -H ' + JSON.stringify(nrHost);
			out += ' \\\n  -P ' + nrPort;
			if (nrComp && nrComp !== 'none') out += ' \\\n  -z ' + nrComp;
			out += ' \\\n  -w ' + (/^\d+$/.test(nrDly) ? nrDly : '1');
			return out;
		}
		if (action === 'partclone_ddrescue') {
			var drSrc  = v(params.partition);
			var drOut  = v(params.output_file || '');
			var drLog  = v(params.log_file || '');
			var drRet  = v(params.retries || '3');
			var drUmnt = String(params.unmount_before || 'yes') === 'yes';
			var drDly  = v(params.step_delay || '1');
			var drXtra = v(params.extra_opts || '');
			var out = 'partition_image.sh -G';
			if (drUmnt) out += ' -u';
			out += ' \\\n  -p ' + JSON.stringify(drSrc);
			out += ' \\\n  -o ' + JSON.stringify(drOut);
			if (drLog)  out += ' \\\n  -l ' + JSON.stringify(drLog);
			out += ' \\\n  -r ' + (/^\d+$/.test(drRet) ? drRet : '3');
			out += ' \\\n  -w ' + (/^\d+$/.test(drDly) ? drDly : '1');
			if (drXtra) out += ' \\\n  -x ' + JSON.stringify(drXtra);
			return out;
		}
		return '# preview unavailable for action: ' + v(action);
	}

		function ensureAceEditor() {
		if (state.aceEditor || !window.ace) return;
		state.aceEditor = window.ace.edit('pcgiCommandEditor');
		state.aceEditor.setTheme('ace/theme/chrome');
		state.aceEditor.session.setMode('ace/mode/sh');
		state.aceEditor.session.setUseWorker(false);
		state.aceEditor.setOptions({ fontSize: '12px', showPrintMargin: false, useSoftTabs: true, tabSize: 2, readOnly: true, highlightActiveLine: false, highlightGutterLine: false });
	}

	function ensureParamsAceEditor() {
if (!state.paramsAceEditor&&window.ace){
state.paramsAceEditor = window.ace.edit('pcgiParamsEditor');
state.paramsAceEditor.setTheme('ace/theme/chrome');
state.paramsAceEditor.session.setMode('ace/mode/json');
state.paramsAceEditor.session.setUseWorker(false);
state.paramsAceEditor.setOptions({ fontSize: '12px', showPrintMargin: false, useSoftTabs: true, tabSize: 2 });
}
if (state.paramsAceEditor && !state.paramsAceBound){
state.paramsAceEditor.session.on('change', function () {
schedulePreviewFromParamEditorLive();
});
state.paramsAceBound = true;
}
}

function setPreviewEditorValue(text) {
		ensureAceEditor();
		var fallback = document.getElementById('pcgiCommandEditorFallback');
		var aceWrap = document.getElementById('pcgiCommandEditor');
		if (state.aceEditor) {
			if (fallback) fallback.style.display = 'none';
			if (aceWrap) aceWrap.style.display = '';
			state.aceEditor.setValue(String(text || ''), -1);
			state.aceEditor.clearSelection();
		} else {
			if (aceWrap) aceWrap.style.display = 'none';
			if (fallback) {
				fallback.style.display = 'block';
				fallback.value = String(text || '');
			}
		}
	}

	function getPreviewEditorValue() {
		var fallback = document.getElementById('pcgiCommandEditorFallback');
		if (state.aceEditor) return state.aceEditor.getValue();
		return fallback ? fallback.value : '';
	}

	function setParamEditorValue(text) {
		ensureParamsAceEditor();
		var fallback = document.getElementById('pcgiParamsEditorFallback');
		var aceWrap = document.getElementById('pcgiParamsEditor');
		if (state.paramsAceEditor) {
			if (fallback) fallback.style.display = 'none';
			if (aceWrap) aceWrap.style.display = '';
			state.paramsAceEditor.setValue(String(text || ''), -1);
			state.paramsAceEditor.clearSelection();
		} else {
			if (aceWrap) aceWrap.style.display = 'none';
			if (fallback) {
				fallback.style.display = 'block';
				fallback.value = String(text || '');
			}
		}
	}

	function getParamEditorValue() {
var fallback = document.getElementById('pcgiParamsEditorFallback');
if (state.paramsAceEditor) return state.paramsAceEditor.getValue();
return fallback ? fallback.value : '';
}

function refreshPreviewFromParamEditorLive() {
if (!state.previewEditContext||!state.previewEditContext.params)return;
var action = state.previewEditContext.action;
var params = state.previewEditContext.params;
var txt = String(getParamEditorValue() || '').trim();
if (!txt)return;

var parsed = null;
try {
parsed = JSON.parse(txt);
} catch (err) {
return;
}
if (!parsed||typeof parsed!=='object'||Array.isArray(parsed))return;

for (var k in params) {
if (Object.prototype.hasOwnProperty.call(params, k)) delete params[k];
}
for (var key in parsed) {
if (!Object.prototype.hasOwnProperty.call(parsed,key))continue;
params[key] = parsed[key];
}

setPreviewEditorValue(buildCommandPreview(action, params));
renderParamRanges(action, params);
}

function schedulePreviewFromParamEditorLive() {
if (!state.previewEditContext)return;
if (state.paramEditorSyncTimer) clearTimeout(state.paramEditorSyncTimer);
state.paramEditorSyncTimer = setTimeout(function () {
state.paramEditorSyncTimer = null;
refreshPreviewFromParamEditorLive();
}, 150);
}

function validateCommandPreviewSyntax(cmdText) {
		var txt = String(cmdText || '');
		if (!txt.trim()) return 'Command cannot be empty.';
		var inSingle = false;
		var inDouble = false;
		var inBacktick = false;
		var escaped = false;
		for (var i = 0; i < txt.length; i++) {
			var ch = txt.charAt(i);
			if (escaped) {
				escaped = false;
				continue;
			}
			if (!inSingle && ch === '\\') {
				escaped = true;
				continue;
			}
			if (!inDouble && !inBacktick && ch === "'") {
				inSingle = !inSingle;
				continue;
			}
			if (!inSingle && !inBacktick && ch === '"') {
				inDouble = !inDouble;
				continue;
			}
			if (!inSingle && !inDouble && ch === '`') inBacktick = !inBacktick;
		}
		if (inSingle) return 'Unclosed single quote in command preview.';
		if (inDouble) return 'Unclosed double quote in command preview.';
		if (inBacktick) return 'Unclosed backtick in command preview.';
		if (escaped) return 'Command preview ends with an unfinished escape (\\).';
		return '';
	}

	function getDeviceByPath(path) {
		var wanted = String(path || '');
		for (var i = 0; i < state.devices.length; i++) {
			if (String(state.devices[i].path || '') === wanted) return state.devices[i];
		}
		return null;
	}

	function getPreviewDeviceByPath(path) {
		var dev = getDeviceByPath(path);
		if (!dev) return null;
		return buildPreviewDevice(dev);
	}

	function alignUp(value, alignment) {
		var a = Math.max(1, Number(alignment) || 1);
		var v = Number(value);
		if (!isFinite(v)) return null;
		return Math.ceil(v / a) * a;
	}

	function alignDown(value, alignment) {
		var a = Math.max(1, Number(alignment) || 1);
		var v = Number(value);
		if (!isFinite(v)) return null;
		return Math.floor(v / a) * a;
	}

	function normalizeSectorBoundary(value, alignment, isEnd) {
		var v = Number(value);
		if (!isFinite(v)) return null;
		if (isEnd) return alignUp(v + 1, alignment) - 1;
		return alignUp(v, alignment);
	}

	function formatRangeCell(v, unit) {
		if (v === null || v === undefined || !isFinite(Number(v))) return '-';
		var n = String(Math.floor(Number(v)));
		if (unit) return n + ' ' + unit;
		return n;
	}

	function buildParamRangeRows(action, params) {
		var rows = [];
		if (!params) return rows;

		var devPath = String(params.device || state.selectedDevice || '');
		var previewDev = devPath ? getPreviewDeviceByPath(devPath) : null;
		var totalSectors = Number(previewDev && previewDev.total_sectors || 0);
		var logicalSectorSize = Number(previewDev && previewDev.logical_sector_size || 512);
		if (!isFinite(logicalSectorSize) || logicalSectorSize <= 0) logicalSectorSize = 512;
		var alignSectors = Math.max(1, Math.ceil((1024 * 1024) / logicalSectorSize));
		var tableType = String(previewDev && previewDev.table || '').toLowerCase();
		var reservedHead = alignSectors;
		var reservedTail = tableType === 'gpt' ? 33 : 0;
		var lastUsableSector = totalSectors > (reservedTail + 1) ? (totalSectors - 1 - reservedTail) : null;

		var part = null;
		var partnum = Number(params.partnum || 0);
		if (previewDev && partnum > 0) part = findPartitionInDeviceByNumber(previewDev, partnum);

		var keys = Object.keys(params);
		for (var i = 0; i < keys.length; i++) {
			var key = keys[i];
			if (key === 'ack' || key === 'dry_run' || key === 'command_preview') continue;

			var raw = String(params[key] === undefined || params[key] === null ? '' : params[key]).trim();
			if (!/^-?\d+$/.test(raw)) continue;

			var n = Number(raw);
			var min = 0;
			var max = null;
			var minNorm = null;
			var maxNorm = null;
			var unit = '';

			if (/(^|_)(start|end)_sector$/.test(key) || /(^|_)sector$/.test(key)) {
				var isEnd = /(^|_)end_sector$/.test(key);
				unit = 's';
				if (isEnd) {
					min = reservedHead + 1;
					if (String(action || '') === 'resize_partition' && part) min = Math.max(min, Number(part.start || 0) + 1);
					if (String(params.start_sector || '').match(/^\d+$/)) min = Math.max(min, Number(params.start_sector) + 1);
					if (String(params.target_start_sector || '').match(/^\d+$/)) min = Math.max(min, Number(params.target_start_sector) + 1);
					if (lastUsableSector !== null) max = Math.max(min, lastUsableSector);
					minNorm = normalizeSectorBoundary(min, alignSectors, true);
					if (max !== null) maxNorm = alignDown(max + 1, alignSectors) - 1;
				} else {
					min = reservedHead;
					if (lastUsableSector !== null) max = Math.max(min, lastUsableSector - 1);
					minNorm = normalizeSectorBoundary(min, alignSectors, false);
					if (max !== null) maxNorm = alignDown(max, alignSectors);
				}
			}
			if (key === 'target_kib') {
				min = 1;
				unit = 'KiB';
				max = lastUsableSector !== null ? Math.floor(((lastUsableSector + 1) * logicalSectorSize) / 1024) : null;
				minNorm = Math.max(1, Math.floor((alignSectors * logicalSectorSize) / 1024));
				if (max !== null) maxNorm = alignDown(max, Math.max(1, minNorm));
			}
			if (key === 'target_bytes') {
				min = logicalSectorSize;
				unit = 'B';
				max = lastUsableSector !== null ? (lastUsableSector + 1) * logicalSectorSize : null;
				minNorm = alignSectors * logicalSectorSize;
				if (max !== null) maxNorm = alignDown(max, minNorm);
			}
			if (key === 'partnum') {
				min = 1;
				max = previewDev ? (partitionCountOf(previewDev) + 1) : null;
				minNorm = 1;
				maxNorm = max;
			}

			if (max !== null && min > max) min = max;
			if (minNorm !== null && minNorm < min) minNorm = min;
			if (maxNorm !== null && max !== null && maxNorm > max) maxNorm = max;
			if (maxNorm !== null && minNorm !== null && maxNorm < minNorm) maxNorm = minNorm;

			rows.push({ key: key, cur: Math.floor(n), min: min, max: max, minNorm: minNorm, maxNorm: maxNorm, unit: unit });
		}
		return rows;
	}

	function renderParamRanges(action, params) {
var wrap = document.getElementById('pcgiParamRangesWrap');
var ranges = document.getElementById('pcgiParamRanges');
if (!wrap||!ranges)return;

var rows = buildParamRangeRows(action, params || {});
if (!rows.length){
wrap.style.display = 'none';
ranges.innerHTML = '';
return;
}

wrap.style.display = '';
ranges.innerHTML = '';

var table = document.createElement('table');
table.className = 'pcgi-table';
var thead = document.createElement('thead');
var hrow = document.createElement('tr');
['parameter', 'current', 'min', 'max', 'min normalized', 'max normalized'].forEach(function (h) {
var th = document.createElement('th');
th.textContent = h;
hrow.appendChild(th);
});
thead.appendChild(hrow);
table.appendChild(thead);

var tbody = document.createElement('tbody');
for (var i = 0; i < rows.length; i++) {
var row = rows[i];
var tr = document.createElement('tr');

var tdKey = document.createElement('td');
tdKey.className = 'pcgi-mono';
tdKey.textContent = row.key;
tr.appendChild(tdKey);

var tdCur = document.createElement('td');
tdCur.className = 'pcgi-mono';
tdCur.textContent = formatRangeCell(row.cur, row.unit);
tr.appendChild(tdCur);

var tdMin = document.createElement('td');
tdMin.className = 'pcgi-mono';
tdMin.textContent = formatRangeCell(row.min, row.unit);
tr.appendChild(tdMin);

var tdMax = document.createElement('td');
tdMax.className = 'pcgi-mono';
tdMax.textContent = formatRangeCell(row.max, row.unit);
tr.appendChild(tdMax);

var tdMinNorm = document.createElement('td');
tdMinNorm.className = 'pcgi-mono';
tdMinNorm.textContent = formatRangeCell(row.minNorm, row.unit);
tr.appendChild(tdMinNorm);

var tdMaxNorm = document.createElement('td');
tdMaxNorm.className = 'pcgi-mono';
tdMaxNorm.textContent = formatRangeCell(row.maxNorm, row.unit);
tr.appendChild(tdMaxNorm);

tbody.appendChild(tr);
}
table.appendChild(tbody);
ranges.appendChild(table);
}

function renderParamEditors(action, params) {
		setParamEditorValue(JSON.stringify(params || {}, null, 2));
		setPreviewEditorValue(buildCommandPreview(action, params || {}));
		renderParamRanges(action, params || {});
	}

	function applyParamEditors(params, action) {
var txt = String(getParamEditorValue() || '').trim();
if (!txt)return;

var parsed = null;
try {
parsed = JSON.parse(txt);
} catch (err) {
showToast('Invalid JSON in parameter editor: ' + err.message, 'error', 10000);
throw err;
}
if (!parsed||typeof parsed!=='object'||Array.isArray(parsed)){
showToast('Parameter editor must contain a JSON object.', 'error', 10000);
throw new Error('Invalid JSON object');
}

for (var k in params) {
if (Object.prototype.hasOwnProperty.call(params, k)) delete params[k];
}
for (var key in parsed) {
if (!Object.prototype.hasOwnProperty.call(parsed,key))continue;
params[key] = parsed[key];
}
setPreviewEditorValue(buildCommandPreview(action, params));
renderParamRanges(action, params);
}

function summarizeOperationLabel(label, action) {
		var ref = String(label || '').trim();
		if (!ref) ref = String(action || '').replace(/_/g, ' ');
		ref = ref.replace(/\s+on\s+\/dev\/\S+.*$/i, '');
		ref = ref.replace(/\s+on\s+[^\s].*$/i, '');
		return ref.trim() || String(action || '').replace(/_/g, ' ');
	}

function showCommandPreviewModal(action, params, label, confirmTitle, confirmMessage) {
		var modal = document.getElementById('pcgiCmdPreviewModal');
		var title = document.getElementById('pcgiCmdPreviewTitle');
		var text = document.getElementById('pcgiCmdPreviewText');
		var paramsLabel = document.getElementById('pcgiParamsEditorLabel');
		var btnCancel = document.getElementById('pcgiCmdCancelBtn');
		var btnValidate = document.getElementById('pcgiCmdValidateBtn');
		if (!modal || !title || !text || !btnCancel || !btnValidate || !paramsLabel) {
			return Promise.resolve(buildCommandPreview(action, params));
		}
		var previewText = buildCommandPreview(action, params);
		state.previewEditContext = { action: action, params: params };
		title.textContent = (confirmTitle || t('cmdPreviewTitle')) + ': ' + label;
		text.textContent = confirmMessage || t('cmdPreviewHint');
		var opRefLabel = summarizeOperationLabel(label, action);
		paramsLabel.textContent = 'Parameters for operation: ' + opRefLabel + ' (editable JSON). You can tune sectors, sizes and options before queueing.';
		setPreviewEditorValue(previewText);
		renderParamEditors(action, params);
		modal.style.display = 'flex';
		modal.setAttribute('aria-hidden', 'false');

		return new Promise(function (resolve) {
			function cleanup(result) {
				modal.style.display = 'none';
				modal.setAttribute('aria-hidden', 'true');
				btnCancel.onclick = null;
				btnValidate.onclick = null;
				document.removeEventListener('keydown', onEsc);
				if (state.paramEditorSyncTimer) {
					clearTimeout(state.paramEditorSyncTimer);
					state.paramEditorSyncTimer = null;
				}
				state.previewEditContext = null;
				resolve(result);
			}
			function onEsc(ev) {
				if (ev.key === 'Escape') cleanup(null);
			}
			document.addEventListener('keydown', onEsc);
			btnCancel.onclick = function () { cleanup(null); };
			btnValidate.onclick = function () {
				try {
					applyParamEditors(params, action);
				} catch (err) {
					return;
				}
				var previewValue = getPreviewEditorValue();
				var cmdErr = validateCommandPreviewSyntax(previewValue);
				if (cmdErr) {
					showToast(cmdErr, 'error', 10000);
					return;
				}
				cleanup(previewValue);
			};
		});
	}

	function editQueueOp(index) {
		var idx = Number(index);
		if (!isFinite(idx) || idx < 0 || idx >= state.queue.length) return;
		var op = state.queue[idx];
		var paramsCopy = {};
		for (var k in op.params) {
			if (Object.prototype.hasOwnProperty.call(op.params, k)) paramsCopy[k] = op.params[k];
		}
		showCommandPreviewModal(op.action, paramsCopy, op.label, 'Edit pending operation', 'Edit parameters and numeric values; command preview updates automatically.')
			.then(function (previewText) {
				if (previewText === null) return;
				op.params = paramsCopy;
				op.commandPreview = previewText;
				renderQueue();
				syncSelectionWithPreview();
				renderMap();
				showToast('Queued operation updated.', 'success', 10000);
			});
	}

	function moveQueueOp(index, direction) {
var idx = Number(index);
var dir = Number(direction);
if (!isFinite(idx)||!isFinite(dir)||idx<0||idx>=state.queue.length)return;
var dst = idx + dir;
if (dst < 0 || dst >= state.queue.length) return;
var item = state.queue.splice(idx, 1)[0];
state.queue.splice(dst, 0, item);
renderQueue();
syncSelectionWithPreview();
renderMap();
}

function queueOp(action, params, label, commandPreview, quiet) {

		state.queue.push({ action: action, params: params, label: label, commandPreview: commandPreview || '' });
		renderQueue();
		syncSelectionWithPreview();
		renderMap();
		if (!quiet) {
			showToast(t('tQueued') + ' ' + label, 'info', 10000);
		}
	}

	function queueOpWithConfirm(action, params, label, confirmTitle, confirmMessage) {
		showCommandPreviewModal(action, params, label, confirmTitle, confirmMessage)
			.then(function (previewText) {
				if (previewText === null) return;
				queueOp(action, params, label, previewText);
			});
	}

	function renderQueue() {
		var body = document.getElementById('queueBody');
		body.innerHTML = '';
		for (var i = 0; i < state.queue.length; i++) {
			var op = state.queue[i];
			var tr = document.createElement('tr');
			var tdIdx = document.createElement('td');
			tdIdx.textContent = String(i + 1);
			var tdLabel = document.createElement('td');
			tdLabel.textContent = op.label;
			var tdParams = document.createElement('td');
			tdParams.className = 'pcgi-mono';
			tdParams.style.cssText = 'white-space:pre-wrap;word-break:break-all;font-size:0.82em;vertical-align:top;';
			tdParams.textContent = JSON.stringify(op.params, null, 2);
			var tdCmd = document.createElement('td');
			tdCmd.className = 'pcgi-mono';
			tdCmd.style.cssText = 'white-space:pre-wrap;word-break:break-all;font-size:0.82em;vertical-align:top;';
			tdCmd.textContent = op.commandPreview || buildCommandPreview(op.action, op.params);
			var tdDel = document.createElement('td');
			var actionsWrap = document.createElement('div');
			actionsWrap.className = 'pcgi-queue-actions';

			var btnUp = document.createElement('button');
btnUp.type = 'button';
btnUp.textContent = '▲';
btnUp.title = 'Move up';
btnUp.className = 'pcgi-queue-arrow-btn';
btnUp.disabled = (i === 0);
btnUp.setAttribute('data-index', String(i));
btnUp.onclick = function () {
var idx = parseInt(this.getAttribute('data-index'), 10);
moveQueueOp(idx, -1);
};

var btnDown = document.createElement('button');
btnDown.type = 'button';
btnDown.textContent = '▼';
btnDown.title = 'Move down';
btnDown.className = 'pcgi-queue-arrow-btn';
btnDown.disabled = (i === state.queue.length - 1);
btnDown.setAttribute('data-index', String(i));
btnDown.onclick = function () {
var idx = parseInt(this.getAttribute('data-index'), 10);
moveQueueOp(idx, 1);
};

var btnEdit = document.createElement('button');
btnEdit.type = 'button';
btnEdit.textContent = 'Edit';
btnEdit.setAttribute('data-index', String(i));
btnEdit.onclick = function () {
var idx = parseInt(this.getAttribute('data-index'), 10);
editQueueOp(idx);
};

var btnRemove = document.createElement('button');
btnRemove.type = 'button';
btnRemove.textContent = 'Remove';
btnRemove.setAttribute('data-index', String(i));
btnRemove.onclick = function () {
var idx = parseInt(this.getAttribute('data-index'), 10);
state.queue.splice(idx, 1);
renderQueue();
syncSelectionWithPreview();
renderMap();
};

var arrowsWrap = document.createElement('div');
arrowsWrap.className = 'pcgi-queue-arrows';
arrowsWrap.appendChild(btnUp);
arrowsWrap.appendChild(btnDown);
actionsWrap.appendChild(arrowsWrap);
actionsWrap.appendChild(btnEdit);
actionsWrap.appendChild(btnRemove);

			tdDel.appendChild(actionsWrap);
			tr.appendChild(tdIdx);
			tr.appendChild(tdLabel);
			tr.appendChild(tdParams);
			tr.appendChild(tdCmd);
			tr.appendChild(tdDel);
			body.appendChild(tr);
		}
	}

	function getSelectedDeviceData() {

		for (var i = 0; i < state.devices.length; i++) {
			if (state.devices[i].path === state.selectedDevice) {
				return state.devices[i];
			}
		}
		return null;
	}

	function partitionCountOf(dev) {
		if (!dev || !dev.partitions) return 0;
		var n = 0;
		for (var i = 0; i < dev.partitions.length; i++) {
			if (dev.partitions[i].kind === 'partition') n++;
		}
		return n;
	}

	function renderDeviceStrip() {
		var strip = document.getElementById('deviceStrip');
		if (!strip) return;
		strip.innerHTML = '';
		for (var i = 0; i < state.devices.length; i++) {
			(function (dev) {
				var btn = document.createElement('button');
				btn.type = 'button';
				btn.className = 'pcgi-device-card' + (String(dev.path || '') === String(state.selectedDevice || '') ? ' selected' : '');
				btn.setAttribute('aria-pressed', String(String(dev.path || '') === String(state.selectedDevice || '')));

				var main = document.createElement('span');
				main.className = 'pcgi-device-card-main';
				var logical = Number(dev.logical_sector_size || 512);
				var total = Number(dev.total_sectors || 0);
				main.textContent = String(dev.path || '-') + ' | ' + (total > 0 ? humanBytes(total * logical) : '-');

				var meta = document.createElement('span');
				meta.className = 'pcgi-device-card-meta';
				var model = String(dev.model || '').trim();
				var pcount = partitionCountOf(dev);
				var info = String(dev.table || '-').toUpperCase() + ' | ' + pcount + 'p';
				if (model) info += ' | ' + model;
				meta.textContent = info;

				btn.title = String(dev.path || '-') + ' [' + String(dev.table || '-') + ']';
				btn.onclick = function () {
					var sel = document.getElementById('deviceSelect');
					if (sel) sel.value = String(dev.path || '');
					onDeviceChange();
				};

				btn.appendChild(main);
				btn.appendChild(meta);
				strip.appendChild(btn);
			})(state.devices[i]);
		}
	}

	function clearSelectedPartitionUi() {
		document.getElementById('selectedPartNum').value = '';
		document.getElementById('selectedPartPath').value = '';
		document.getElementById('fsPartitionPath').value = '';
		document.getElementById('newStartSector').value = '';
		document.getElementById('newEndSector').value = '';
		document.getElementById('resizeEndSector').value = '';
		document.getElementById('newPartName').value = '';
		document.getElementById('renamePartInput').value = '';
		document.getElementById('flagNameInput').value = '';
		document.getElementById('flagStateInput').value = 'off';
		document.getElementById('fsLabelInput').value = '';
		document.getElementById('mountpointInput').value = '';
		refreshSectorHumanFields();
	}

	function buildPartitionPath(devicePath, partNum) {
		var dev = String(devicePath || '');
		if (/(nvme\d+n\d+|mmcblk\d+|loop\d+)$/.test(dev)) {
			return dev + 'p' + String(partNum);
		}
		return dev + String(partNum);
	}

	function clonePartitionEntry(p) {
		var out = {};
		for (var k in p) {
			if (Object.prototype.hasOwnProperty.call(p, k)) out[k] = p[k];
		}
		out.kind = String(out.kind || 'partition');
		out.number = Number(out.number || 0);
		out.start = Number(out.start || 0);
		out.end = Number(out.end || 0);
		out.size = Number(out.size || 0);
		return out;
	}

	function getNextPartitionNumber(parts) {
		var used = {};
		for (var i = 0; i < parts.length; i++) {
			var n = Number(parts[i].number || 0);
			if (n > 0) used[n] = true;
		}
		for (var candidate = 1; candidate < 65535; candidate++) {
			if (!used[candidate]) return candidate;
		}
		return parts.length + 1;
	}

	function normalizePreviewPartitions(parts, totalSectors) {
		var out = [];
		var maxSector = Math.max(1, Number(totalSectors || 0) - 1);
		var ordered = parts.slice().sort(function (a, b) {
			if (Number(a.start || 0) === Number(b.start || 0)) {
				return Number(a.number || 0) - Number(b.number || 0);
			}
			return Number(a.start || 0) - Number(b.start || 0);
		});

		var cursor = 1;
		for (var i = 0; i < ordered.length; i++) {
			var p = clonePartitionEntry(ordered[i]);
			var start = Math.max(1, Math.floor(Number(p.start || 0)));
			var end = Math.max(start, Math.floor(Number(p.end || 0)));

			if (start > maxSector) continue;
			if (end > maxSector) end = maxSector;
			if (end < cursor) continue;
			if (start < cursor) start = cursor;

			if (start > cursor) {
				out.push({ kind: 'free', start: cursor, end: start - 1, size: start - cursor });
			}

			p.start = start;
			p.end = end;
			p.size = Math.max(1, (end - start + 1));
			out.push(p);
			cursor = end + 1;
		}

		if (cursor <= maxSector) {
			out.push({ kind: 'free', start: cursor, end: maxSector, size: maxSector - cursor + 1 });
		}

		return out;
	}

	function buildPreviewDevice(dev) {
		if (!dev) return null;

		var preview = {};
		for (var dk in dev) {
			if (Object.prototype.hasOwnProperty.call(dev, dk)) preview[dk] = dev[dk];
		}

		var partsOnly = [];
		for (var i = 0; i < (dev.partitions || []).length; i++) {
			var basePart = dev.partitions[i];
			if (basePart && basePart.kind === 'partition') {
				partsOnly.push(clonePartitionEntry(basePart));
			}
		}

		for (var q = 0; q < state.queue.length; q++) {
			var op = state.queue[q] || {};
			var action = String(op.action || '');
			var params = op.params || {};

			if (action === 'delete_partition' || action === 'resize_partition' || action === 'move_partition' || action === 'create_partition' || action === 'set_partition_name' || action === 'set_partition_flag') {
				if (String(params.device || '') !== String(dev.path || '')) continue;
			}

			if (action === 'delete_partition') {
				var delNum = Number(params.partnum || 0);
				partsOnly = partsOnly.filter(function (p) { return Number(p.number || 0) !== delNum; });
				continue;
			}

			if (action === 'create_partition') {
				var newStart = Number(params.start_sector || 0);
				var newEnd = Number(params.end_sector || 0);
				if (!isFinite(newStart) || !isFinite(newEnd) || newStart <= 0 || newEnd < newStart) continue;
				var newNum = getNextPartitionNumber(partsOnly);
				partsOnly.push({
					kind: 'partition',
					number: newNum,
					start: Math.floor(newStart),
					end: Math.floor(newEnd),
					size: Math.max(1, Math.floor(newEnd - newStart + 1)),
					path: buildPartitionPath(dev.path, newNum),
					fs: String(params.fs_hint || ''),
					name: String(params.part_name || ''),
					flags: '',
					label: '',
					mountpoint: '',
					fs_size_bytes: 0,
					fs_used_bytes: 0,
					fs_avail_bytes: 0,
					used_pct: 0
				});
				continue;
			}

			var targetNum = Number(params.partnum || 0);
			var targetPart = null;
			for (var pidx = 0; pidx < partsOnly.length; pidx++) {
				if (Number(partsOnly[pidx].number || 0) === targetNum) {
					targetPart = partsOnly[pidx];
					break;
				}
			}
			if (!targetPart) continue;

			if (action === 'resize_partition') {
				var newEndSector = Number(params.end_sector || 0);
				if (!isFinite(newEndSector) || newEndSector <= Number(targetPart.start || 0)) continue;
				targetPart.end = Math.floor(newEndSector);
				targetPart.size = Math.max(1, Number(targetPart.end) - Number(targetPart.start) + 1);
				continue;
			}

			if (action === 'move_partition') {
				var moveStart = Number(params.start_sector || 0);
				var moveEnd = Number(params.end_sector || 0);
				if (!isFinite(moveStart) || !isFinite(moveEnd) || moveStart <= 0 || moveEnd < moveStart) continue;
				targetPart.start = Math.floor(moveStart);
				targetPart.end = Math.floor(moveEnd);
				targetPart.size = Math.max(1, Number(targetPart.end) - Number(targetPart.start) + 1);
				continue;
			}

			if (action === 'set_partition_name') {
				targetPart.name = String(params.part_name || targetPart.name || '');
				continue;
			}

			if (action === 'set_partition_flag') {
				var flagName = String(params.flag || '').trim();
				if (!flagName) continue;
				var flags = String(targetPart.flags || '').split(/[ ,]+/).filter(function (s) { return s; });
				var stateOn = String(params.state || '').toLowerCase() === 'on';
				var present = false;
				for (var fi = 0; fi < flags.length; fi++) {
					if (flags[fi] === flagName) {
						present = true;
						break;
					}
				}
				if (stateOn && !present) flags.push(flagName);
				if (!stateOn && present) {
					flags = flags.filter(function (f) { return f !== flagName; });
				}
				targetPart.flags = flags.join(',');
			}
		}

		preview.partitions = normalizePreviewPartitions(partsOnly, Number(dev.total_sectors || 0));
		return preview;
	}

	function syncSelectionWithPreview() {
		if (!state.selectedComponent || state.selectedComponent.kind !== 'partition') return;
		var dev = getSelectedDeviceData();
		if (!dev) return;
		var preview = buildPreviewDevice(dev);
		if (!preview || !preview.partitions) return;

		var selectedPath = String(state.selectedComponent.path || '');
		var selectedNum = Number(state.selectedComponent.number || 0);
		var exists = false;

		for (var i = 0; i < preview.partitions.length; i++) {
			var p = preview.partitions[i];
			if (!p || p.kind !== 'partition') continue;
			if (selectedPath && String(p.path || '') === selectedPath) {
				exists = true;
				break;
			}
			if (!selectedPath && selectedNum > 0 && Number(p.number || 0) === selectedNum) {
				exists = true;
				break;
			}
		}

		if (!exists) {
			state.selectedPart = null;
			state.selectedComponent = null;
			clearSelectedPartitionUi();
			updateMapStatus('Selected partition is no longer available in pending preview.');
		}
	}

	function mapFsHintValue(fs) {
		var v = String(fs || '').toLowerCase();
		if (!v) return '';
		if (v === 'fat' || v === 'vfat') return 'fat32';
		if (v === 'ext2' || v === 'ext3' || v === 'ext4' || v === 'f2fs' || v === 'exfat' || v === 'fat16' || v === 'fat32' || v === 'ntfs') {
			return v;
		}
		return '';
	}

	function mapFsTypeSelectValue(fs) {
		var v = String(fs || '').toLowerCase();
		if (!v) return 'auto';
		if (v === 'fat' || v === 'fat12' || v === 'vfat') return 'fat32';
		if (v === 'fat16' || v === 'fat32' || v === 'ext2' || v === 'ext3' || v === 'ext4' || v === 'f2fs' || v === 'exfat' || v === 'ntfs') {
			return v;
		}
		return 'auto';
	}

	function firstFlagValue(flags) {
		var raw = String(flags || '').trim();
		if (!raw) return '';
		var parts = raw.split(/[ ,]+/);
		for (var i = 0; i < parts.length; i++) {
			if (parts[i]) return parts[i];
		}
		return '';
	}

	function updateMapStatus(txt) {
		document.getElementById('mapStatus').textContent = txt || '';
	}

	function renderMapLoading(msg) {
		var map = document.getElementById('partitionMap');
		if (!map) return;
		map.innerHTML = '';
		var box = document.createElement('div');
		box.className = 'pcgi-map-loading';
		box.textContent = msg || t('tMapLoading');
		map.appendChild(box);
	}

	function selectPartition(part) {
		state.selectedPart = part;
		state.selectedComponent = part ? {
			kind: 'partition',
			number: Number(part.number || 0),
			path: String(part.path || ''),
			start: Number(part.start || 0),
			end: Number(part.end || 0)
		} : null;
		document.getElementById('selectedPartNum').value = part ? String(part.number || '') : '';
		document.getElementById('selectedPartPath').value = part ? (part.path || '') : '';
		document.getElementById('fsPartitionPath').value = part ? (part.path || '') : '';
		document.getElementById('newStartSector').value = part ? String(part.start || '') : '';
		document.getElementById('newEndSector').value = part ? String(part.end || '') : '';
		document.getElementById('resizeEndSector').value = part ? String(part.end || '') : '';
		document.getElementById('newFsHint').value = part ? mapFsHintValue(part.fs) : '';
		document.getElementById('fsTypeSelect').value = part ? mapFsTypeSelectValue(part.fs) : 'auto';
		document.getElementById('newPartName').value = part ? (part.name || '') : '';
		document.getElementById('renamePartInput').value = part ? (part.name || '') : '';
		document.getElementById('flagNameInput').value = part ? firstFlagValue(part.flags) : '';
		document.getElementById('flagStateInput').value = part && part.flags ? 'on' : 'off';
		document.getElementById('fsLabelInput').value = part ? (part.label || '') : '';
		document.getElementById('mountpointInput').value = part && part.mountpoint ? part.mountpoint : '';
		if (part) fillChipSourceFromSelection(part, state.selectedDevice);
		/* Save selection to per-disk memory */
		state.selectedPartDevice = part ? state.selectedDevice : '';
		if (state.selectedDevice) {
			state.partSelectionByDisk[state.selectedDevice] = part
				? { part: part, component: state.selectedComponent }
				: null;
		}
		refreshSectorHumanFields();
		updateMapStatus(part ? ('Selected partition #' + part.number + ' [' + part.start + 's..' + part.end + 's].') : '');
		renderMap();
		/* Auto-set unmount selects based on current mount status */
		var _partMounted = !!(part && part.mountpoint && String(part.mountpoint).trim() && String(part.mountpoint).trim() !== '-');
		var _umVal = _partMounted ? 'yes' : 'no';
		['mcUnmountBefore','dmUnmount','piExpUnmount','piImpUnmount','piNsUnmount','piNrUnmount'].forEach(function(id) {
			var el = document.getElementById(id); if (el) el.value = _umVal;
		});
	}

	function selectDisk(dev) {
		state.selectedPart = null;
		state.selectedComponent = dev ? { kind: 'disk', path: String(dev.path || '') } : null;
		document.getElementById('selectedPartNum').value = '';
		document.getElementById('selectedPartPath').value = '';
		document.getElementById('fsPartitionPath').value = '';
		document.getElementById('newStartSector').value = '';
		document.getElementById('newEndSector').value = '';
		document.getElementById('resizeEndSector').value = '';
		refreshSectorHumanFields();
		if (dev && dev.path) {
			updateMapStatus('Selected disk ' + dev.path + '.');
		}
		renderMap();
	}

	function selectUnallocatedSegment(seg) {
		state.selectedPart = null;
		/* Clear this disk's saved partition selection since user chose free space */
		if (state.selectedDevice) {
			state.partSelectionByDisk[state.selectedDevice] = null;
		}
		state.selectedComponent = seg ? {
			kind: 'free',
			start: Number(seg.start || 0),
			end: Number(seg.end || 0)
		} : null;
		document.getElementById('selectedPartNum').value = '';
		document.getElementById('selectedPartPath').value = '';
		document.getElementById('fsPartitionPath').value = '';
		document.getElementById('mountpointInput').value = '';
		document.getElementById('fsLabelInput').value = '';
		document.getElementById('newFsHint').value = '';
		document.getElementById('fsTypeSelect').value = 'auto';
		document.getElementById('newPartName').value = '';
		document.getElementById('renamePartInput').value = '';
		document.getElementById('flagNameInput').value = '';
		document.getElementById('flagStateInput').value = 'off';
		document.getElementById('resizeEndSector').value = '';
		if (seg) {
			document.getElementById('newStartSector').value = String(seg.start || '');
			document.getElementById('newEndSector').value = String(seg.end || '');
			updateMapStatus('Selected unallocated segment [' + seg.start + 's..' + seg.end + 's].');
		}
		refreshSectorHumanFields();
		renderMap();
	}

	function hideContextMenu() {
		var menu = document.getElementById('partContextMenu');
		state.contextMenuVisible = false;
		if (state.contextMenuHideTimer) {
			clearTimeout(state.contextMenuHideTimer);
			state.contextMenuHideTimer = null;
		}
		if (!menu) return;
		menu.onmouseenter = null;
		menu.onmouseleave = null;
		menu.style.display = 'none';
	}

	function scheduleContextMenuAutoHide() {
		if (state.contextMenuHideTimer) clearTimeout(state.contextMenuHideTimer);
		state.contextMenuHideTimer = setTimeout(function () {
			hideContextMenu();
		}, 4000);
	}

	function showContextMenu(target, ev, menuType) {
		var menu = document.getElementById('partContextMenu');
		if (!menu || !target) return;
		hideHoverTooltip();
		state.contextMenuVisible = true;
		if (state.contextMenuHideTimer) {
			clearTimeout(state.contextMenuHideTimer);
			state.contextMenuHideTimer = null;
		}
		state.contextTarget = { type: menuType === 'disk' ? 'disk' : menuType === 'free' ? 'free' : 'partition', target: target };
		menu.innerHTML = '';

		var items = [];
		if (menuType === 'disk') {
			items = [
				{ id: 'select_disk',         label: 'Select disk' },
				{ id: 'delete_all_parts',    label: 'Delete all disk partitions' },
				{ id: 'disk_setup_fritzbox', label: '⚡ Freetz EVO disk setup' },
				{ id: 'disk_convert_label',  label: 'Convert partition table (MBR/GPT…)' },
				{ id: 'disk_move_clone',     label: 'Disk move or clone' },
				{ id: 'disk_img_export',     label: 'Export disk to image file' },
				{ id: 'disk_img_import',     label: 'Restore disk from image file' },
				{ id: 'disk_ddrescue',       label: 'Clone disk with ddrescue (data recovery)' },
				{ id: 'disk_smart',          label: 'SMART info (smartctl)' },
				{ id: 'disk_hdparm',         label: 'Disk info (hdparm)' },
				{ id: 'disk_gpt_info',       label: 'GPT info (sgdisk)' },
				{ id: 'disk_badblocks',      label: 'Badblocks scan' }
			];
		} else if (menuType === 'free') {
			items = [
				{ id: 'free_create',      label: t('ctxFreeCreate') },
				{ id: 'free_move_clone',  label: t('ctxFreeMoveClone') },
				{ id: 'free_img_import',  label: t('ctxFreeRestore') },
				{ id: 'free_net_recv',    label: t('ctxFreeReceive') }
			];
		} else {
			var part = target;
			var _ctxRole = String(part.role || (Number(part.number || 0) >= 5 ? 'logical' : 'primary'));
			if (_ctxRole === 'extended') {
				items = [
					{ id: 'select',      label: 'Select partition' },
					{ id: 'meta',        label: 'Load metadata' },
					{ id: 'new_logical', label: 'New logical partition inside…' },
					{ id: 'delete',      label: 'Delete partition' },
					{ id: 'rename',      label: 'Rename partition' },
					{ id: 'flag',        label: 'Set flag' }
				];
			} else {
				items = [
					{ id: 'select', label: 'Select partition' },
					{ id: 'meta', label: 'Load metadata' },
					{ id: 'delete', label: 'Delete partition' },
					{ id: 'rename', label: 'Rename partition' },
					{ id: 'flag', label: 'Set flag' },
					{ id: 'mkfs', label: 'Create filesystem' },
					{ id: 'mount', label: part.mountpoint ? 'Remount' : 'Mount' },
					{ id: 'umount', label: 'Unmount' },
					{ id: 'fsck_ro',    label: 'Filesystem check read-only' },
					{ id: 'fsck_fix',   label: 'Filesystem check/repair' },
					{ id: 'img_export', label: 'Export partition to image file' },
					{ id: 'img_import', label: 'Restore partition from image file' },
					{ id: 'net_send',   label: 'Send partition over network' },
					{ id: 'net_recv',   label: 'Receive partition from network' },
					{ id: 'ddrescue',   label: 'Clone with ddrescue (data recovery)' }
				];
			}
		}

		for (var i = 0; i < items.length; i++) {
			(function (item) {
				var btn = document.createElement('button');
				btn.type = 'button';
				btn.className = 'pcgi-context-item';
				btn.textContent = item.label;
				btn.onclick = function () {
					hideContextMenu();
					handleContextAction(item.id, target, menuType);
				};
				menu.appendChild(btn);
			})(items[i]);
		}

		menu.onmouseenter = function () {
			if (state.contextMenuHideTimer) {
				clearTimeout(state.contextMenuHideTimer);
				state.contextMenuHideTimer = null;
			}
		};
		menu.onmouseleave = scheduleContextMenuAutoHide;

		menu.style.display = 'block';
		var _mx = (ev.pageX != null ? ev.pageX : ev.clientX + (document.documentElement.scrollLeft || 0));
		var _my = (ev.pageY != null ? ev.pageY : ev.clientY + (document.documentElement.scrollTop  || 0));
		menu.style.position = 'absolute';
		menu.style.left = Math.max(0, Math.min(_mx, (document.documentElement.scrollWidth  || 9999) - 250)) + 'px';
		menu.style.top  = Math.max(0, Math.min(_my, (document.documentElement.scrollHeight || 9999) - 300)) + 'px';
	}

	function expandAdvancedInfo() {
		var det = document.getElementById('advancedInfoDetails');
		if (!det) return;
		if (!det.open) det.open = true;
		det.scrollIntoView({ behavior: 'smooth', block: 'start' });
	}

	function handleContextAction(action, target, menuType) {
		if (menuType === 'disk') {
			if (action === 'select_disk') { selectDisk(target); return; }
			if (action === 'delete_all_parts') { queueDeleteAllPartitions(target); return; }
			if (action === 'disk_setup_fritzbox') { showFritzSetupModal(target); return; }
			if (action === 'disk_convert_label')  { showConvertLabelModal(target); return; }
			if (action === 'disk_move_clone') { showDiskMoveCloneModal(target); return; }
			if (action === 'disk_img_export') { showPartcloneExportModal(target, 'disk'); return; }
			if (action === 'disk_img_import') { showPartcloneImportModal(target, 'disk'); return; }
			if (action === 'disk_ddrescue')   { showDdrescueModal(target, 'disk'); return; }
			if (action === 'disk_smart')     { selectDisk(target); expandAdvancedInfo(); runDiagnostics('smart_info');     return; }
			if (action === 'disk_hdparm')    { selectDisk(target); expandAdvancedInfo(); runDiagnostics('hdparm_info');    return; }
			if (action === 'disk_gpt_info')  { selectDisk(target); expandAdvancedInfo(); runDiagnostics('gpt_info');       return; }
			if (action === 'disk_badblocks') { selectDisk(target); expandAdvancedInfo(); runDiagnostics('badblocks_scan'); return; }
			showToast(t('tContextUnavailable'), 'warn');
			return;
		}
		if (menuType === 'free') {
			var freeSeg = target;
			if (action === 'free_create')     { showNewPartModal(freeSeg.start, freeSeg.end); return; }
			if (action === 'free_move_clone') {
				// Pass the currently selected partition as source (preserved — context menu no longer clears it)
				showMoveCloneModal(freeSeg.devPath, freeSeg.start, freeSeg.end, state.selectedPartDevice || freeSeg.devPath, state.selectedPart);
				return;
			}
			if (action === 'free_img_import') { showPartcloneImportModal({ path: freeSeg.devPath, mountpoint: '' }, 'disk'); return; }
			if (action === 'free_net_recv')   { showPartcloneNetRecvModal({ path: freeSeg.devPath, mountpoint: '' }); return; }
			showToast(t('tContextUnavailable'), 'warn');
			return;
		}
		var part = target;
		if (action === 'new_logical') {
			// Open new-partition modal inside the extended partition's range
			showNewPartModal(Number(part.start || 0) + 1, Number(part.end || 0) - 1);
			return;
		}
		selectPartition(part);
		if (action === 'select') return;
		if (action === 'meta') { loadPartitionMetadata(); return; }
		if (action === 'delete') { queueDeletePartition(); return; }
		if (action === 'rename') { queueRenamePartition(); return; }
		if (action === 'flag') { queueSetFlag(); return; }
		if (action === 'mkfs') { document.getElementById('fsTypeSelect').value = 'auto'; queueMkfs(); return; }
		if (action === 'mount') { showMountModal(); return; }
		if (action === 'umount') { queueUnmountPartition(); return; }
		if (action === 'fsck_ro') { runFsck(false); return; }
		if (action === 'fsck_fix') { runFsck(true); return; }
		if (action === 'img_export') { showPartcloneExportModal(part, 'partition'); return; }
		if (action === 'img_import') { showPartcloneImportModal(part, 'partition'); return; }
		if (action === 'net_send')   { showPartcloneNetSendModal(part); return; }
		if (action === 'net_recv')   { showPartcloneNetRecvModal(part); return; }
		if (action === 'ddrescue')   { showDdrescueModal(part, 'partition'); return; }
		showToast(t('tContextUnavailable'), 'warn');
	}

	function renderMap() {
		var baseDev = getSelectedDeviceData();
		var map = document.getElementById('partitionMap');
		var legend = document.getElementById('mapLegend');
		map.innerHTML = '';
		legend.textContent = '';
		if (!baseDev) {
			legend.textContent = 'No device selected.';
			return;
		}
		var dev = buildPreviewDevice(baseDev);
		if (!dev) {
			legend.textContent = 'No device selected.';
			return;
		}

		var total = Number(dev.total_sectors || 0);
		var logical = Number(dev.logical_sector_size || 512);
		var mapWidth = Math.max(1, Math.floor(map.clientWidth || map.getBoundingClientRect().width || 1));
		if (mapWidth <= 1) { requestAnimationFrame(renderMap); return; }
		// Width is strictly proportional; CSS min-width on .pcgi-block.part ensures click-target size.
		if (!total || total <= 0) {
			legend.textContent = 'Unable to render this device.';
			return;
		}

		var diskBlock = document.createElement('div');
		diskBlock.className = 'pcgi-disk-block';
		diskBlock.textContent = (dev.name || (dev.path || '').replace('/dev/', '')) + ' (disk)';
		if (state.selectedComponent && state.selectedComponent.kind === 'disk' && String(state.selectedComponent.path || '') === String(dev.path || '')) {
			diskBlock.className += ' selected';
		}
		diskBlock.onmouseenter = function (ev) {
			showHoverTooltip(ev, buildDiskTooltipHtml(dev));
		};
		diskBlock.onmousemove = moveHoverTooltip;
		diskBlock.onmouseleave = hideHoverTooltip;
		diskBlock.onclick = function (ev) {
			if (ev) {
				ev.preventDefault();
				ev.stopPropagation();
			}
			hideContextMenu();
			selectDisk(baseDev);
		};
		diskBlock.oncontextmenu = function (ev) {
			ev.preventDefault();
			ev.stopPropagation();
			showContextMenu(baseDev, ev, 'disk');
		};
		map.appendChild(diskBlock);

/* When a partition is selected, show its device info in the legend
                   even if the user is currently browsing a different disk. */
                var legendDev = dev;
                if (state.selectedPart && state.selectedPartDevice && state.selectedPartDevice !== String(dev.path || '')) {
                        for (var _li = 0; _li < state.devices.length; _li++) {
                                if (String(state.devices[_li].path || '') === state.selectedPartDevice) {
                                        legendDev = state.devices[_li];
                                        break;
                                }
                        }
                }
                var _lt = Number(legendDev.total_sectors || 0);
                var _ll = Number(legendDev.logical_sector_size || 512);
                legend.textContent = legendDev.path + ' | table=' + (legendDev.table || 'unknown') + ' | model=' + (legendDev.model || '-') + ' | size=' + humanBytes(_lt * _ll);
                if (legendDev.transport) legend.textContent += ' | transport=' + legendDev.transport;
                if (legendDev.vendor) legend.textContent += ' | vendor=' + legendDev.vendor;
                if (legendDev.serial) legend.textContent += ' | serial=' + legendDev.serial;

		// Pre-compute per-block layout geometry in a single forward pass so that:
		// (a) free-space segments get a 4 px minimum making small leading gaps
		//     (e.g. the pre-8064s area) visible instead of a 0-1 px sliver, and
		// (b) any block widened by the minimum pushes subsequent blocks rightward
		//     rather than overlapping them.
		var blockLayouts = [];
		var pixelCursor = 0;
		for (var bli = 0; bli < dev.partitions.length; bli++) {
			var blp      = dev.partitions[bli];
			var blStart  = Number(blp.start || 0);
			var blEnd    = Number(blp.end   || 0);
			var blSize   = Number(blp.size  || Math.max(1, blEnd - blStart + 1));
			if (state.dragCtx && blp.kind === 'partition') {
				var blDevPath  = String(state.dragCtx.dev && state.dragCtx.dev.path || '');
				var blPartPath = String(state.dragCtx.partPath || (state.dragCtx.part && state.dragCtx.part.path) || '');
				if (blDevPath === String(dev.path || '') && blPartPath && blPartPath === String(blp.path || '')) {
					if (state.dragCtx.edge === 'left') {
						blStart = Number(state.dragCtx.currentStart || blStart);
					} else {
						blEnd = Number(state.dragCtx.currentEnd || blEnd);
					}
					blSize = Math.max(1, blEnd - blStart + 1);
				}
			}
			var blNatLeft  = Math.round((blStart / total) * mapWidth);
			var blNatWidth = Math.max(1, Math.round((blSize  / total) * mapWidth));
			var blMinWidth = (blp.kind === 'partition') ? 30 : 4;
			var blWidth    = Math.max(blMinWidth, blNatWidth);
			var blLeft     = Math.max(pixelCursor, blNatLeft);
			if (blLeft < 0)         blLeft = 0;
			if (blLeft >= mapWidth) blLeft = mapWidth - 1;
			// Clamp right edge to mapWidth so the rightmost partition is never
			// clipped by the container's overflow:hidden when a leading free
			// segment minimum-width has shifted it right.
			if (blLeft + blWidth > mapWidth) {
				blWidth = Math.max(1, mapWidth - blLeft);
			}
			pixelCursor = blLeft + blWidth;
			blockLayouts.push({ leftPx: blLeft, widthPx: blWidth, drawStart: blStart, drawEnd: blEnd, drawSize: blSize });
		}

		// Identify extended partition (if any) and inject its band behind partition blocks.
		// The band is position:absolute with z-index:0; partition blocks sit on top.
		var _mapContainer = document.getElementById('partitionMap');
		for (var _ei = 0; _ei < dev.partitions.length; _ei++) {
			var _ep = dev.partitions[_ei];
			if (_ep.kind !== 'partition') continue;
			var _epRole = String(_ep.role || (_ep.number >= 5 ? 'logical' : 'primary'));
			if (_epRole !== 'extended') continue;
			var _eLay = blockLayouts[_ei];
			// Compute span: from leftmost logical partition to rightmost (may extend beyond visual block due to min-width clamping)
			var _eBandLeft  = _eLay.leftPx;
			var _eBandWidth = _eLay.widthPx;
			// Extend to cover all logical partitions within this extended range
			var _eStart = Number(_ep.start || 0), _eEnd = Number(_ep.end || 0);
			for (var _li2 = 0; _li2 < dev.partitions.length; _li2++) {
				var _lp = dev.partitions[_li2];
				if (_lp.kind !== 'partition') continue;
				var _lpNum = Number(_lp.number || 0);
				if (_lpNum < 5) continue;
				var _lpStart = Number(_lp.start || 0), _lpEnd = Number(_lp.end || 0);
				if (_lpStart >= _eStart && _lpEnd <= _eEnd) {
					var _lLay = blockLayouts[_li2];
					var _lRight = _lLay.leftPx + _lLay.widthPx;
					var _eRight = _eBandLeft + _eBandWidth;
					if (_lLay.leftPx < _eBandLeft) _eBandLeft = _lLay.leftPx;
					if (_lRight > _eRight) _eBandWidth = _lRight - _eBandLeft;
				}
			}
			var band = document.createElement('div');
			band.className = 'pcgi-extended-band';
			band.style.position = 'absolute';
			band.style.left  = _eBandLeft  + 'px';
			band.style.width = _eBandWidth + 'px';
			var bandLabel = document.createElement('span');
			bandLabel.className = 'pcgi-extended-label';
			bandLabel.textContent = 'extended';
			band.appendChild(bandLabel);
			// Allow click/contextmenu on the band label strip (above logical partitions)
			// to select/operate on the extended partition itself.
			(function(_bandEp) {
				band.onclick = function(ev) {
					ev.preventDefault(); ev.stopPropagation();
					hideContextMenu();
					selectPartition(_bandEp);
				};
				band.oncontextmenu = function(ev) {
					ev.preventDefault(); ev.stopPropagation();
					showContextMenu(_bandEp, ev, 'partition');
				};
				band.onmouseenter = function(ev) {
					showHoverTooltip(ev, buildPartitionTooltipHtml(_bandEp, logical, 0, 0));
				};
				band.onmousemove = moveHoverTooltip;
				band.onmouseleave = hideHoverTooltip;
			})(_ep);
			map.appendChild(band);
		}

		for (var i = 0; i < dev.partitions.length; i++) {
			(function (idx) {
				var p = dev.partitions[idx];
				var selectedDisk = !!(state.selectedComponent && state.selectedComponent.kind === 'disk' && String(state.selectedComponent.path || '') === String(dev.path || ''));
				// A partition is uniquely identified by its start sector (no two valid partitions
				// share the same start); path and number serve as optional secondary confirmation.
				var scPath  = String(state.selectedComponent ? (state.selectedComponent.path   || '') : '');
				var scNum   = state.selectedComponent ? Number(state.selectedComponent.number  || 0) : 0;
				var scStart = state.selectedComponent ? Number(state.selectedComponent.start   || 0) : 0;
				var pPath   = String(p.path   || '');
				var pNum    = Number(p.number || 0);
				var pStart  = Number(p.start  || 0);
				var selectedPart = !!(state.selectedComponent &&
					p.kind === 'partition' &&
					state.selectedComponent.kind === 'partition' &&
					scStart > 0 && pStart === scStart &&
					(
						(scPath && pPath === scPath) ||
						(scNum > 0 && pNum === scNum) ||
						(!scPath && !scNum)
					)
				);
				var selectedFree = !!(state.selectedComponent && p.kind === 'free' && state.selectedComponent.kind === 'free' && Number(p.start) === Number(state.selectedComponent.start) && Number(p.end) === Number(state.selectedComponent.end));
				// Use pre-computed geometry (correct min-widths + cursor shift applied).
				var draggingThis = false;
				var layout    = blockLayouts[idx];
				var drawStart = layout.drawStart;
				var drawEnd   = layout.drawEnd;
				var drawSize  = layout.drawSize;
				var leftPx    = layout.leftPx;
				var widthPx   = layout.widthPx;
				// Mark block as dragging if it is attached to the active handle.
				if (state.dragCtx && p.kind === 'partition' &&
						String(state.dragCtx.dev && state.dragCtx.dev.path || '') === String(dev.path || '')) {
					var dragPath = String(state.dragCtx.partPath || (state.dragCtx.part && state.dragCtx.part.path) || '');
					if (dragPath && dragPath === pPath) {
						draggingThis = true;
					}
				}
				// Extended partition: skip normal block rendering — the band pre-pass already drew it.
				if (p.kind === 'partition') {
					var _pRole = String(p.role || (Number(p.number || 0) >= 5 ? 'logical' : 'primary'));
					if (_pRole === 'extended') return;
				}
				var block = document.createElement('div');
				block.className = 'pcgi-block ' + (p.kind === 'free' ? 'free' : 'part');
				if (p.kind === 'partition') {
					var _pRole2 = String(p.role || (Number(p.number || 0) >= 5 ? 'logical' : 'primary'));
					if (_pRole2 === 'logical') block.className += ' pcgi-logical';
				}
				block.style.left = leftPx + 'px';
				block.style.width = widthPx + 'px';
				// Only highlight the individually selected partition/free segment.
				// Do NOT apply 'selected' class to all partitions when the disk is selected.
				if (selectedPart || draggingThis) {
					block.className += ' selected';
				}
				if (selectedFree) {
					block.className += ' selected';
				}

				if (p.kind === 'partition') {
					var fsUsed = Number(p.fs_used_bytes || 0);
					var fsAvail = Number(p.fs_avail_bytes || 0);
					// p.used_pct = fs_used/disk_total x 100 (disk-absolute coordinate, float).
					// CSS% inside block = used_pct / (p.size / dev.total_sectors) = fs_used/partition_size x 100.
					// Pixel width = (fs_used/disk_total) x map_px — stays fixed when partition is resized.
					var partSectors = Number(p.size || 1);
					var totalSectors = Number(dev.total_sectors || 1);
					var usedPct;
					if (draggingThis && drawSize > 0 && fsUsed > 0) {
						// During drag recompute from bytes so bar stays pixel-fixed.
						var drawBytesD = drawSize * logical;
						usedPct = drawBytesD > 0 ? Math.min(100, (fsUsed / drawBytesD) * 100) : 100;
					} else {
						// Static: disk-relative used_pct / partition_fraction = block-relative CSS%.
						var partFrac = partSectors / totalSectors;
						usedPct = partFrac > 0 ? Number(p.used_pct || 0) / partFrac : 0;
					}
					block.title = '';
					block.textContent = (p.name || p.label || p.fs || 'partition');
					block.onmouseenter = function (ev) {
						showHoverTooltip(ev, buildPartitionTooltipHtml(p, logical, fsUsed, fsAvail));
					};
					block.onmousemove = moveHoverTooltip;
					block.onmouseleave = hideHoverTooltip;
					block.onclick = function (ev) {
						if (ev) {
							ev.preventDefault();
							ev.stopPropagation();
						}
						hideContextMenu();
						selectPartition(p);
					};
					block.oncontextmenu = function (ev) {
						ev.preventDefault();
						ev.stopPropagation();
						showContextMenu(p, ev, 'partition');
					};
					if (Number(p.fs_size_bytes || 0) > 0) {
						var fsBar = document.createElement('div');
						fsBar.className = 'pcgi-part-fsbar';
						var fsUsedBar = document.createElement('div');
						fsUsedBar.className = 'pcgi-part-fsbar-used';
						fsUsedBar.style.width = Math.max(0, Math.min(100, usedPct)) + '%';
						var fsUnusedBar = document.createElement('div');
						fsUnusedBar.className = 'pcgi-part-fsbar-unused';
						// Unused bar: denominator = partition_size_bytes (disk-absolute).
						// (fs_size - fs_used) / partition_size x 100 keeps pixel footprint fixed on disk map.
						var partSizeBytes = partSectors * logical; // partSectors declared above
						var fsSizeBytes = Number(p.fs_size_bytes || 0);
						var fsUnusedPct;
						if (draggingThis && drawSize > 0) {
							var drawBytesD2 = drawSize * logical;
							var fsUnusedBytes = Math.max(0, fsSizeBytes - fsUsed);
							fsUnusedPct = drawBytesD2 > 0 ? Math.min(100 - Math.max(0, Math.min(100, usedPct)), (fsUnusedBytes / drawBytesD2) * 100) : 0;
						} else {
							var fsUnusedBytes2 = Math.max(0, fsSizeBytes - fsUsed);
							fsUnusedPct = partSizeBytes > 0 ? Math.min(100 - Math.max(0, Math.min(100, usedPct)), (fsUnusedBytes2 / partSizeBytes) * 100) : 0;
						}
						fsUnusedBar.style.width = Math.max(0, fsUnusedPct) + '%';
						fsBar.appendChild(fsUsedBar);
						fsBar.appendChild(fsUnusedBar);
						block.appendChild(fsBar);
					}
					block.draggable = true;
                    block.ondragstart = function (ev) {
                        state.mapDragActive = true;
                        var blockRect = block.getBoundingClientRect();
                        var grabPx = (ev.clientX || 0) - blockRect.left;
                        grabPx = clampNumber(grabPx, 0, Math.max(1, blockRect.width));
                        state.partitionDragInfo = {
                            devPath: String(dev.path || ''),
                            partnum: Number(p.number || 0),
                            partPath: String(p.path || ''),
                            size: Number(p.size || 0),
                            grabRatio: blockRect.width > 0 ? (grabPx / blockRect.width) : 0
                        };
                        hideHoverTooltip();
                        ev.dataTransfer.setData('text/plain', 'partition:' + p.number);
                        ev.dataTransfer.setData('part-size', String(p.size || 0));
                    };
                    block.ondragend = function () {
                        state.mapDragActive = false;
                        state.partitionDragInfo = null;
                        hideHoverTooltip();
                    };

					var leftHandle = document.createElement('div');
					leftHandle.className = 'pcgi-resize-handle pcgi-resize-handle-left';
					leftHandle.title = 'Drag left edge to move/resize';
					leftHandle.onmousedown = function (ev) {
						ev.stopPropagation();
						startResize(ev, dev, idx, 'left');
					};
					block.appendChild(leftHandle);
					var handle = document.createElement('div');
					handle.className = 'pcgi-resize-handle';
					handle.title = 'Drag to resize';
					handle.onmousedown = function (ev) {
						ev.stopPropagation();
						startResize(ev, dev, idx, 'right');
					};
					block.appendChild(handle);
				} else {
					block.title = '';
					block.textContent = 'unallocated';
					block.onmouseenter = function (ev) {
						showHoverTooltip(ev, '<div class="pcgi-hover-tooltip-grid">' +
							tooltipKV('Segment', 'Unallocated') +
							tooltipKV('Start', String(p.start || 0) + 's') +
							tooltipKV('End', String(p.end || 0) + 's') +
							tooltipKV('Size', humanBytes(Number(p.size || 0) * logical)) +
						'</div>');
					};
					block.onmousemove = moveHoverTooltip;
					block.onmouseleave = hideHoverTooltip;
					block.onclick = function (ev) {
						if (ev) {
							ev.preventDefault();
							ev.stopPropagation();
						}
						hideContextMenu();
						selectUnallocatedSegment(p);
					};
					block.oncontextmenu = function (ev) {
						ev.preventDefault();
						ev.stopPropagation();
						// Do NOT call selectUnallocatedSegment here — it would clear state.selectedPart
						showContextMenu({ kind: 'free', start: p.start, end: p.end, devPath: String(dev.path || '') }, ev, 'free');
					};
					block.ondragover = function (ev) {
						ev.preventDefault();
						var dragInfo = state.partitionDragInfo;
						if (!dragInfo) return;
						var moveSize = Number(dragInfo.size || 0);
						var targetStart = computeMoveDropTargetStart(ev, p, moveSize, Number(dragInfo.grabRatio || 0));
						if (!isFinite(targetStart)) return;
						var freeSpan = Number(p.end || 0) - Number(p.start || 0) + 1;
						if (freeSpan <= 0) return;
						var blockW = block.clientWidth;
						var landLeft = Math.max(0, (targetStart - Number(p.start || 0)) / freeSpan * blockW);
						var landW = Math.max(2, moveSize / freeSpan * blockW);
						var preview = block._dragPreview;
						if (!preview) {
							preview = document.createElement('div');
							preview.className = 'pcgi-drag-landing';
							block.style.position = 'relative';
							block.appendChild(preview);
							block._dragPreview = preview;
						}
						preview.style.left = landLeft + 'px';
						preview.style.width = landW + 'px';
					};
					block.ondragleave = function () {
						if (block._dragPreview) {
							block.removeChild(block._dragPreview);
							block._dragPreview = null;
						}
					};
					block.ondrop = function (ev) {
						ev.preventDefault();
						if (block._dragPreview) {
							block.removeChild(block._dragPreview);
							block._dragPreview = null;
						}
						state.mapDragActive = false;
						hideHoverTooltip();
						var data = ev.dataTransfer.getData('text/plain');
						if (data === 'new-partition') {
							showNewPartModal(p.start, p.end);
						} else if (data === 'chip-move-or-clone') {
							updateMapStatus(t('tDropQueuedMoveCloneChip'));
							showToast(t('tDropQueuedMoveCloneChip'), 'info', 10000);
							/* Use source captured at dragstart; fall back to current state */
							var preselSrcDev = ev.dataTransfer.getData('text/x-src-dev') || state.selectedDevice || '';
							var preselSrcPartNum = ev.dataTransfer.getData('text/x-src-part-num') || '';
							var preselSrcPart = null;
							if (preselSrcDev && preselSrcPartNum) {
								for (var _sd = 0; _sd < state.devices.length; _sd++) {
									if (String(state.devices[_sd].path || '') === preselSrcDev) {
										var _sparts = state.devices[_sd].partitions || [];
										for (var _sp = 0; _sp < _sparts.length; _sp++) {
											if (_sparts[_sp].kind === 'partition' && String(_sparts[_sp].number || '') === preselSrcPartNum) {
												preselSrcPart = _sparts[_sp]; break;
											}
										}
										break;
									}
								}
							} else {
								preselSrcPart = state.selectedPart || null;
							}
							showMoveCloneModal(dev.path, p.start, p.end, preselSrcDev, preselSrcPart);
						} else if (data.indexOf('partition:') === 0) {
							var pnum = data.split(':')[1];
							var dragInfo = state.partitionDragInfo;
							// Determine the TRUE source device from dragInfo (may differ from drop target)
							var srcDevicePath = dragInfo ? String(dragInfo.devPath || dev.path) : String(dev.path);
							// Find source device object
							var srcDeviceObj = dev; // default: same disk as target
							if (srcDevicePath !== String(dev.path || '')) {
								for (var sd = 0; sd < state.devices.length; sd++) {
									if (String(state.devices[sd].path || '') === srcDevicePath) {
										srcDeviceObj = state.devices[sd];
										break;
									}
								}
							}
							// Search the SOURCE device's partitions (not the target disk)
							var moveSource = null;
							var srcParts = srcDeviceObj.partitions || [];
							for (var m = 0; m < srcParts.length; m++) {
								if (srcParts[m].kind === 'partition' && String(srcParts[m].number) === String(pnum)) {
									moveSource = srcParts[m];
									break;
								}
							}
							if (!moveSource) {
                                state.partitionDragInfo = null;
                                showToast(t('tContextUnavailable'), 'warn');
                                return;
                            }
                            var moveSize = Number(moveSource.size || 0);
                            var grabRatio = 0;
                            if (dragInfo &&
                                (
                                    (String(dragInfo.partPath || '') && String(dragInfo.partPath || '') === String(moveSource.path || '')) ||
                                    (Number(dragInfo.partnum || 0) > 0 && Number(dragInfo.partnum || 0) === Number(moveSource.number || 0))
                                )
                            ) {
                                grabRatio = Number(dragInfo.grabRatio || 0);
                            }
                            var targetStart = computeMoveDropTargetStart(ev, p, moveSize, grabRatio);
                            if (!isFinite(targetStart)) {
                                state.partitionDragInfo = null;
                                showToast(t('tMoveNoSpace'), 'error');
                                return;
                            }
                            var targetEnd = targetStart + moveSize - 1;
                            if (targetEnd > Number(p.end || 0)) {
                                state.partitionDragInfo = null;
                                showToast(t('tMoveNoSpace'), 'error');
                                return;
                            }
                            if (srcDevicePath === String(dev.path || '') &&
                                Number(moveSource.start) === targetStart && Number(moveSource.end) === targetEnd) {
                                state.partitionDragInfo = null;
                                showToast(t('tMoveSame'), 'warn');
                                return;
                            }
                            state.partitionDragInfo = null;
							queueMovePartitionWithConfirm(
								dev.path,
								moveSource,
								targetStart,
								targetEnd,
								'Move p' + moveSource.number + ' on ' + srcDevicePath + ' to [' + targetStart + 's..' + targetEnd + 's]',
								srcDevicePath,
								'',
								'smart'
							);
						}
					};
				}
				map.appendChild(block);
			})(i);
		}
	}

	function startResize(ev, dev, partIndex, edge) {
		ev.preventDefault();
		var part = dev.partitions[partIndex];
		if (!part||part.kind!=='partition')return;

		// Select the partition immediately so all form fields are populated
		// even when the user starts dragging without a prior click.
		selectPartition(part);

		var map = document.getElementById('partitionMap');
		var rect = map.getBoundingClientRect();
		var total = Number(dev.total_sectors || 0);
		if (!total)return;

		var logical = Number(dev.logical_sector_size || 512);
		var prevSeg = partIndex > 0 ? dev.partitions[partIndex - 1] : null;
		var nextSeg = partIndex < dev.partitions.length - 1 ? dev.partitions[partIndex + 1] : null;
		var minStart = 1;
		var maxEnd = total - 1;
		if (prevSeg) minStart = prevSeg.kind === 'free' ? Number(prevSeg.start) : Number(prevSeg.end) + 1;
		if (nextSeg) maxEnd = nextSeg.kind === 'free' ? Number(nextSeg.end) : Number(nextSeg.start) - 1;
		// The right edge must not move below the used filesystem area (data loss).
		// 2048-sector alignment floor is always kept even with no filesystem.
		var fsUsedBytes = Number(part.fs_used_bytes || 0);
		var fsUsedMinSectors = (fsUsedBytes > 0 && logical > 0) ? Math.ceil(fsUsedBytes / logical) + 1 : 0;
		var minEnd = Number(part.start) + Math.max(2048, fsUsedMinSectors);
		if (minEnd > maxEnd) minEnd = Number(part.start);
		var maxStart = Number(part.end) - 2048;
		if (maxStart < minStart) maxStart = minStart;

		state.dragCtx = {
			dev: dev,
			part: part,
			partPath: String(part.path || ''),
			edge: edge || 'right',
			mapRect: rect,
			total: total,
			logical: logical,
			minStart: minStart,
			maxStart: maxStart,
			currentStart: Number(part.start),
			minEnd: minEnd,
			maxEnd: maxEnd,
			currentEnd: Number(part.end)
		};

		hideHoverTooltip();
		hideContextMenu();
		renderMap();
		document.addEventListener('mousemove', onResizeMove);
		document.addEventListener('mouseup', onResizeUp);
	}
	function onResizeMove(ev) {
		if (!state.dragCtx) return;
		var d = state.dragCtx;
		var relX = ev.clientX - d.mapRect.left;
		if (relX < 0) relX = 0;
		if (relX > d.mapRect.width) relX = d.mapRect.width;
		var sec = Math.floor((relX / d.mapRect.width) * d.total);
		if (d.edge === 'left') {
			if (sec < d.minStart) sec = d.minStart;
			if (sec > d.maxStart) sec = d.maxStart;
			d.currentStart = sec;
			document.getElementById('newStartSector').value = String(sec);
			refreshSectorHumanFields();
			updateMapStatus('Resize preview: #' + d.part.number + ' start -> ' + sec + 's');
		} else {
			if (sec < d.minEnd) sec = d.minEnd;
			if (sec > d.maxEnd) sec = d.maxEnd;
			d.currentEnd = sec;
			document.getElementById('resizeEndSector').value = String(sec);
			document.getElementById('newEndSector').value = String(sec);
			refreshSectorHumanFields();
			updateMapStatus('Resize preview: #' + d.part.number + ' end -> ' + sec + 's');
		}
		renderMap();
	}

	function onResizeUp() {
		if (!state.dragCtx)return;
		var d = state.dragCtx;
		// Remove listeners first to stop tracking mouse movement.
		document.removeEventListener('mousemove', onResizeMove);
		document.removeEventListener('mouseup', onResizeUp);
		// Keep state.dragCtx alive during the confirm modal so the map
		// continues to show the dragged position.  Clear only after the
		// Promise settles (confirmed, cancelled, or early error return).
		updateMapStatus('');

		function finishResize() {
			state.dragCtx = null;
			renderMap();
		}

		if (d.edge === 'left') {
			if (Number(d.currentStart) !== Number(d.part.start)) {
				var p = queueMoveResizePlan(d.dev, d.part, Number(d.currentStart), document.getElementById('resizeFsSelect').value);
				document.getElementById('newStartSector').value = String(d.currentStart);
				refreshSectorHumanFields();
				if (p && typeof p.then === 'function') {
					p.then(finishResize, finishResize);
				} else {
					finishResize();
				}
			} else {
				finishResize();
			}
		} else if (Number(d.currentEnd) !== Number(d.part.end)) {
			var p2 = queueResizePlan(d.dev, d.part, Number(d.currentEnd), document.getElementById('resizeFsSelect').value);
			document.getElementById('resizeEndSector').value = String(d.currentEnd);
			document.getElementById('newEndSector').value = String(d.currentEnd);
			refreshSectorHumanFields();
			if (p2 && typeof p2.then === 'function') {
				p2.then(finishResize, finishResize);
			} else {
				finishResize();
			}
		} else {
			finishResize();
		}
	}
	function normalizeFsTypeForResize(fsType) {
		var v = String(fsType || '').toLowerCase();
		if (!v || v === 'auto') return '';
		if (v === 'fat' || v === 'fat12' || v === 'fat16' || v === 'fat32' || v === 'vfat') return 'fat';
		if (v.indexOf('ext') === 0) return v;
		if (v === 'ntfs') return 'ntfs';
		return '';
	}


	function getToolAvailability(name) {
		if (!state.toolStatus || !state.toolStatus.available) return null;
		return !!state.toolStatus.available[name];
	}

	function getFsResizeCapability(fsType, direction) {
		var normalized = normalizeFsTypeForResize(fsType);
		if (!normalized) {
			return { supported: false, hasTool: false, canResize: false, fsType: '', toolHint: '' };
		}

		if (normalized.indexOf('ext') === 0) {
			var hasResize2fs = getToolAvailability('resize2fs/e2fsprogs');
			var hasE2fsck = getToolAvailability('e2fsck/e2fsprogs');
			var hasToolExt = direction === 'shrink' ? ((hasResize2fs !== false) && (hasE2fsck !== false)) : (hasResize2fs !== false);
			if (hasResize2fs === false || (direction === 'shrink' && hasE2fsck === false)) hasToolExt = false;
			return {
				supported: true,
				hasTool: hasToolExt,
				canResize: hasToolExt,
				fsType: normalized,
				toolHint: direction === 'shrink' ? 'e2fsck + resize2fs' : 'resize2fs'
			};
		}

		if (normalized === 'ntfs') {
			var hasNtfsresize = getToolAvailability('ntfsresize');
			var canNtfs = (hasNtfsresize !== false);
			if (hasNtfsresize === false) canNtfs = false;
			return {
				supported: true,
				hasTool: canNtfs,
				canResize: canNtfs,
				fsType: 'ntfs',
				toolHint: 'ntfsresize'
			};
		}

		if (normalized === 'fat') {
			var hasFatresize = getToolAvailability('fatresize');
			var canFat = (hasFatresize !== false);
			if (hasFatresize === false) canFat = false;
			return {
				supported: true,
				hasTool: canFat,
				canResize: canFat,
				fsType: 'fat',
				toolHint: 'fatresize'
			};
		}

		return { supported: false, hasTool: false, canResize: false, fsType: '', toolHint: '' };
	}
	function findPartitionInDeviceByNumber(dev, partnum) {
		if (!dev || !dev.partitions) return null;
		var n = Number(partnum || 0);
		for (var i = 0; i < dev.partitions.length; i++) {
			var p = dev.partitions[i];
			if (p && p.kind === 'partition' && Number(p.number || 0) === n) return p;
		}
		return null;
	}

	function queueResizePlan(dev, part, newEnd, resizeFs) {
		if (!dev || !part) {
			showToast(t('tContextUnavailable'), 'warn');
			return;
		}

		var start = Number(part.start || 0);
		var oldEnd = Number(part.end || 0);
		var targetEnd = Number(newEnd || 0);
		if (!isFinite(targetEnd) || targetEnd <= start) {
			showToast('Invalid end sector for resize.', 'warn');
			return;
		}
		if (targetEnd === oldEnd) {
			showToast(t('tMoveSame'), 'warn');
			return;
		}

		var isShrink = targetEnd < oldEnd;
		var queueFs = String(resizeFs || 'no') === 'yes';
		var rawFsType = String(part.fs || '').toLowerCase().trim();
		var hasFilesystem = !!(rawFsType && rawFsType !== 'unknown' && rawFsType !== '-');
		var fsCap = hasFilesystem ? getFsResizeCapability(rawFsType, isShrink ? 'shrink' : 'grow') : { supported: true, hasTool: true, canResize: true, fsType: '', toolHint: '' };
		var fsType = fsCap.fsType || normalizeFsTypeForResize(rawFsType);

		if (isShrink && hasFilesystem) {
			if (!fsCap.supported) {
				showToast('Cannot shrink partition #' + part.number + ': filesystem ' + rawFsType + ' is not supported for resize.', 'error', 10000);
				return;
			}
			if (fsCap.hasTool === false) {
				showToast('Cannot shrink partition #' + part.number + ': missing resize tool (' + fsCap.toolHint + ').', 'error', 10000);
				return;
			}
			if (!queueFs) {
				queueFs = true;
				showToast('Filesystem resize enabled automatically for shrink operation.', 'warn', 10000);
			}
		}

		if (!isShrink && hasFilesystem) {
			if (!fsCap.supported) {
				showToast('Warning: growing partition with filesystem ' + rawFsType + ' has no supported resize. Filesystem resize will be skipped.', 'warn', 10000);
				queueFs = false;
			} else if (fsCap.hasTool === false) {
				showToast('Warning: missing tool ' + fsCap.toolHint + '. Partition growth will be added without filesystem resize.', 'warn', 10000);
				queueFs = false;
			}
		}

		if (queueFs && !hasFilesystem) queueFs = false;
		if (queueFs && !fsType) queueFs = false;

		var logical = Number(dev.logical_sector_size || 512);
		var targetBytes = Math.max(1, (targetEnd - start + 1) * logical);
		var targetKib = Math.max(1, Math.floor(targetBytes / 1024));
		var isMounted = !!(part.mountpoint && String(part.mountpoint).trim() && String(part.mountpoint).trim() !== '-');
		var mountpoint = isMounted ? String(part.mountpoint).trim() : '';
		var partitionPath = String(part.path || '');

		return showConfirmModal(
			t('confirmAction'),
			'Resize partition #' + part.number + ' on ' + dev.path + '?'
		).then(function (ok) {
			if (!ok) return;

			var umParams = { partition: partitionPath };
			queueOp(
				'unmount_partition',
				umParams,
				'Unmount ' + partitionPath,
				buildCommandPreview('unmount_partition', umParams),
				true
			);

			if (hasFilesystem && fsType) {
				var ckParams = { partition: partitionPath, fs_type: fsType, repair: 'no', extra_opts: '' };
				queueOp(
					'check_filesystem',
					ckParams,
					'Check filesystem (read-only) on ' + partitionPath + ' before resize',
					buildCommandPreview('check_filesystem', ckParams),
					true
				);
			}

			if (queueFs && isShrink) {
				var fsBeforeParams = {
					partition: partitionPath,
					fs_type: fsType,
					direction: 'shrink',
					target_kib: String(targetKib),
					target_bytes: String(targetBytes)
				};
				queueOp(
					'resize_filesystem',
					fsBeforeParams,
					'Resize filesystem (shrink) on ' + partitionPath,
					buildCommandPreview('resize_filesystem', fsBeforeParams),
					true
				);
			}

			var rpParams = {
				device: dev.path,
				partnum: part.number,
				end_sector: String(targetEnd),
				resize_fs: 'no'
			};
			queueOp(
				'resize_partition',
				rpParams,
				'Resize partition #' + part.number + ' on ' + dev.path + ' to end=' + targetEnd + 's',
				buildCommandPreview('resize_partition', rpParams),
				true
			);

			if (queueFs && !isShrink) {
				// e2fsck is mandatory before resize2fs grow; prepend a check step for ext fs.
				if (fsType && fsType.indexOf('ext') === 0) {
					var ck2Params = { partition: partitionPath, fs_type: fsType, repair: 'no', extra_opts: '' };
					queueOp(
						'check_filesystem',
						ck2Params,
						'Check filesystem (read-only) on ' + partitionPath + ' before grow',
						buildCommandPreview('check_filesystem', ck2Params),
						true
					);
				}
				var fsAfterParams = {
					partition: partitionPath,
					fs_type: fsType,
					direction: 'grow',
					target_kib: String(targetKib),
					target_bytes: String(targetBytes)
				};
				queueOp(
					'resize_filesystem',
					fsAfterParams,
					'Resize filesystem (grow) on ' + partitionPath,
					buildCommandPreview('resize_filesystem', fsAfterParams),
					true
				);
			}

			if (isMounted && mountpoint) {
				var mParams = {
					partition: partitionPath,
					mountpoint: mountpoint,
					fs_type: mapFsTypeSelectValue(part.fs),
					mount_opts: ''
				};
				queueOp(
					'mount_partition',
					mParams,
					'Remount ' + partitionPath + ' on ' + mountpoint,
					buildCommandPreview('mount_partition', mParams),
					true
				);
			}

			showToast('Resize plan added (' + (isShrink ? 'shrink' : 'grow') + ').', 'success', 10000);
		});
	}


        function queueMoveResizePlan(dev, part, newStart, resizeFs) {
                if (!dev || !part) {
                        showToast(t('tContextUnavailable'), 'warn');
                        return Promise.resolve(false);
                }

                var oldStart = Number(part.start || 0);
                var end = Number(part.end || 0);
                var targetStart = Number(newStart || 0);
                if (!isFinite(targetStart) || targetStart <= 0 || targetStart >= end) {
                        showToast('Invalid start sector for resize.', 'warn');
                        return Promise.resolve(false);
                }
                if (targetStart === oldStart) {
                        showToast(t('tMoveSame'), 'warn');
                        return Promise.resolve(false);
                }

                return queueMovePartitionWithConfirm(
                        dev.path,
                        part,
                        targetStart,
                        end,
                        'Relocate partition #' + part.number + ' on ' + dev.path + ' to [' + targetStart + 's..' + end + 's] (create + dd + delete)'
                );
        }

function partitionMountInfo(part, devPath) {
var mountpoint = (part && part.mountpoint != null) ? String(part.mountpoint).trim() : '';
var isMounted = !!(mountpoint && mountpoint !== '-');
var partitionPath = '';
if (part && part.path) {
partitionPath = String(part.path).trim();
}
if (!partitionPath && devPath && part && part.number) {
partitionPath = buildPartitionPath(devPath, part.number);
}
return { isMounted: isMounted, mountpoint: mountpoint, partitionPath: partitionPath };
}

function moveRangesIntersect(startA, endA, startB, endB) {
var a0 = Number(startA || 0);
var a1 = Number(endA || 0);
var b0 = Number(startB || 0);
var b1 = Number(endB || 0);
if (!isFinite(a0) || !isFinite(a1) || !isFinite(b0) || !isFinite(b1)) return false;
if (a1 < a0 || b1 < b0) return false;
return (a0 <= b1) && (b0 <= a1);
}

function ensureMoveTargetDoesNotIntersectSource(part, targetStart, targetEnd, sourceDevPath, targetDevPath) {
if (String(sourceDevPath || '') !== String(targetDevPath || '')) return true;
var srcStart = Number(part && part.start || 0);
var srcEnd = Number(part && part.end || 0);
var tgtStart = Number(targetStart || 0);
var tgtEnd = Number(targetEnd || 0);
if (moveRangesIntersect(srcStart, srcEnd, tgtStart, tgtEnd)) {
showToast('Move blocked: target range intersects source partition range.', 'error', 10000);
return false;
}
return true;
}

function inferPartnumFromPath(devicePath, partitionPath) {
var dev = String(devicePath || '');
var p = String(partitionPath || '');
if (!dev || !p || p.indexOf(dev) !== 0) return '';
var suffix = p.substring(dev.length);
if (!suffix) return '';
if (suffix.charAt(0) === 'p') suffix = suffix.substring(1);
if (!/^[0-9]+$/.test(suffix)) return '';
return suffix;
}

function findPartitionGlobalByPath(path) {
var target = String(path || '').trim();
if (!target) return null;
for (var i = 0; i < state.devices.length; i++) {
var dev = state.devices[i];
for (var j = 0; j < (dev.partitions || []).length; j++) {
var p = dev.partitions[j];
if (!p || p.kind !== 'partition') continue;
if (String(p.path || '') === target) {
return { device: dev, part: p };
}
}
}
return null;
}

function findPartitionGlobalByDeviceNum(devicePath, partnum) {
var devPath = String(devicePath || '').trim();
var num = Number(partnum || 0);
if (!devPath || !isFinite(num) || num <= 0) return null;
for (var i = 0; i < state.devices.length; i++) {
var dev = state.devices[i];
if (String(dev.path || '') !== devPath) continue;
for (var j = 0; j < (dev.partitions || []).length; j++) {
var p = dev.partitions[j];
if (!p || p.kind !== 'partition') continue;
if (Number(p.number || 0) === num) {
return { device: dev, part: p };
}
}
}
return null;
}

function fillChipSourceFromSelection(part, devPath) {
	// No-op: source selection is handled by the mc modal dropdowns
}

function getChipSourceSelection(silent) {
	// Try selected partition from UI state
	if (state.selectedPart && state.selectedDevice) {
		return {
			sourceDevice: String(state.selectedDevice || ''),
			sourcePart: state.selectedPart,
			sourcePartnum: String(state.selectedPart.number || ''),
			sourcePath: String(state.selectedPart.path || '')
		};
	}
	if (!silent) showToast(t('tNeedSourcePart'), 'warn', 10000);
	return null;
}

function getCloneChipOptions() {
	// Read from mc modal fields if present, otherwise return defaults
	function v(id, def) {
		var el = document.getElementById(id);
		return el ? String(el.value || def).trim() : String(def);
	}
	var ddBs = v('mcDdBs', '1M'); if (!ddBs) ddBs = '1M';
	var targetMountpoint = v('mcTargetMount', '');
	var partcloneVerify = v('mcVerify', 'no').toLowerCase();
	if (partcloneVerify !== 'yes') partcloneVerify = 'no';
	var alignBytes = v('mcAlignment', '4096');
	if (alignBytes !== '512') alignBytes = '4096';
	var unmountBefore = v('mcUnmountBefore', 'yes').toLowerCase();
	if (unmountBefore !== 'no') unmountBefore = 'yes';
	var forceFs = v('mcForceFs', '');
	var partcloneExtra = v('mcPartcloneExtra', '');
	var stepDelay = v('mcStepDelay', '0');
	if (!/^\d+$/.test(stepDelay)) stepDelay = '0';
	var fsckPasses2 = v('mcFsckPasses', '2');
	var ddFallback2 = v('mcDdFallback', '1');
	var skipWriteErr2 = v('mcSkipWriteError', '0');
	return {
		dd_bs: ddBs,
		target_mountpoint: targetMountpoint,
		partclone_verify: partcloneVerify,
		align_bytes: alignBytes,
		unmount_before: unmountBefore,
		force_fs: forceFs,
		partclone_extra: partcloneExtra,
		step_delay: stepDelay,
		fat_fsck_passes: fsckPasses2,
		dd_fallback: ddFallback2,
		skip_write_error: skipWriteErr2
	};
}

function buildRoValidationMountpoint(targetMountpoint, targetDevPath, targetStart, targetEnd) {
var base = String(targetMountpoint || '').trim();
if (base) {
base = base.replace(/\/+$/, '');
return base + '.pcgi-ro-check';
}
var devToken = String(targetDevPath || 'dev').replace(/[^A-Za-z0-9._-]+/g, '_');
return '/tmp/pcgi-ro-check-' + devToken + '-' + String(targetStart) + '-' + String(targetEnd);
}

function queueMountTargetByRange(targetDevPath, targetStart, targetEnd, mountpoint, fsType, mountOpts, quiet) {
var mParams = {
partition: '',
device: targetDevPath,
target_start_sector: String(targetStart),
target_end_sector: String(targetEnd),
target_partnum: '',
mountpoint: mountpoint,
fs_type: mapFsTypeSelectValue(fsType),
mount_opts: mountOpts || ''
};
queueOp(
'mount_partition',
mParams,
'Mount target partition on ' + targetDevPath + ' [' + targetStart + 's..' + targetEnd + 's]' + (mountpoint ? (' at ' + mountpoint) : ''),
buildCommandPreview('mount_partition', mParams),
!!quiet
);
}

// ── Device/partition dropdown helpers for the modal dialogs ──────────────────

function populateDevDropdown(selId, preselectPath) {
	var sel = document.getElementById(selId);
	if (!sel) return;
	var prev = String(preselectPath || sel.value || '');
	sel.innerHTML = '';
	for (var i = 0; i < state.devices.length; i++) {
		var dev = state.devices[i];
		var opt = document.createElement('option');
		opt.value = String(dev.path || '');
		opt.textContent = String(dev.path || '') + (dev.model ? '  (' + dev.model + ')' : '');
		sel.appendChild(opt);
	}
	if (prev) sel.value = prev;
}

function populatePartDropdown(devSelId, partSelId, preselectNum) {
	var devSel  = document.getElementById(devSelId);
	var partSel = document.getElementById(partSelId);
	if (!devSel || !partSel) return;
	var devPath = String(devSel.value || '').trim();
	var prev    = String(preselectNum !== undefined ? preselectNum : (partSel.value || ''));
	partSel.innerHTML = '';
	var dev = null;
	for (var i = 0; i < state.devices.length; i++) {
		if (String(state.devices[i].path || '') === devPath) { dev = state.devices[i]; break; }
	}
	if (!dev) return;
	var ss = Number(dev.logical_sector_size || 512);
	for (var j = 0; j < (dev.partitions || []).length; j++) {
		var p = dev.partitions[j];
		if (!p || p.kind !== 'partition') continue;
		var sz = Number(p.size || 0);
		var opt = document.createElement('option');
		opt.value = String(p.number || '');
		opt.textContent = 'p' + p.number + '  ' + (p.path || '') + '  ' + humanBytes(sz * ss) +
		                  (p.fs ? '  [' + p.fs + ']' : '') + (p.label ? '  "' + p.label + '"' : '');
		partSel.appendChild(opt);
	}
	if (prev) partSel.value = prev;
}

function populateMcPartDropdown(preselectNum) {
	populatePartDropdown('mcSourceDevice', 'mcSourcePartNum', preselectNum);
}

function populateMcTargetPartDropdown(preselectNum) {
	var devSel  = document.getElementById('mcTargetDevice');
	var partSel = document.getElementById('mcTargetPartNum');
	if (!devSel || !partSel) return;
	var devPath = String(devSel.value || '').trim();
	// Keep blank option first
	partSel.innerHTML = '<option value="">\u2014 use sector range below \u2014</option>';
	if (!devPath) return;
	var dev = null;
	for (var i = 0; i < state.devices.length; i++) {
		if (state.devices[i].path === devPath) { dev = state.devices[i]; break; }
	}
	if (!dev) return;
	var parts = dev.partitions || [];
	for (var j = 0; j < parts.length; j++) {
		var p = parts[j];
		if (p.kind !== 'partition') continue;
		var opt = document.createElement('option');
		opt.value = String(p.number || '');
		var label = p.path || (devPath + p.number);
		if (p.size) label += '  ' + humanBytes(Number(p.size) * Number(dev.logical_sector_size || 512));
		if (p.fs) label += '  ' + p.fs;
		if (p.label) label += '  [' + p.label + ']';
		opt.textContent = label;
		if (String(p.number) === String(preselectNum || '')) opt.selected = true;
		partSel.appendChild(opt);
	}
}

function populateVerifyPartDropdown(devSelId, partSelId) {
	populatePartDropdown(devSelId, partSelId);
}

// ── New partition modal ───────────────────────────────────────────────────────

function showNewPartModal(dropStart, dropEnd) {
	var modal    = document.getElementById('pcgiNewPartModal');
	var titleEl  = document.getElementById('pcgiNewPartTitle');
	var cancelBtn = document.getElementById('pcgiNewPartCancelBtn');
	var fsBtn     = document.getElementById('pcgiNewPartFsBtn');
	if (!modal) return;

	/* Populate modal sector fields and human-readable peers */
	document.getElementById('pnpStartSector').value = String(dropStart);
	document.getElementById('pnpEndSector').value   = String(dropEnd);
	updateHumanFieldFromSector('pnpStartSector', 'pnpStartHuman');
	updateHumanFieldFromSector('pnpEndSector',   'pnpEndHuman');

	/* Gather device/partition context */
	var devPath = state.selectedDevice || '';
	var devObj  = devPath ? getPreviewDeviceByPath(devPath) : null;
	var tableType = String((devObj && devObj.table) || '').toLowerCase();
	var allParts  = (devObj && devObj.partitions) ? devObj.partitions.filter(function(q){return q.kind==='partition';}) : [];
	var isFirstPartition = (allParts.length === 0);
	var isGPT   = (tableType === 'gpt');
	var isMBR   = (tableType === 'msdos');

	/* Find existing extended partition on MBR */
	var extPart = null;
	if (isMBR) {
		for (var _xi = 0; _xi < allParts.length; _xi++) {
			var _xp = allParts[_xi];
			var _xRole = String(_xp.role || (Number(_xp.number||0) >= 5 ? 'logical' : 'primary'));
			if (_xRole === 'extended') { extPart = _xp; break; }
		}
	}

	/* Is the drop range inside an existing extended partition? */
	var insideExtended = false;
	if (extPart) {
		var _extStart = Number(extPart.start || 0);
		var _extEnd   = Number(extPart.end   || 0);
		if (Number(dropStart) >= _extStart && Number(dropEnd) <= _extEnd) insideExtended = true;
	}

	/* --- Role selector visibility --- */
	var roleRow = document.getElementById('pnpRoleRow');
	var roleEl  = document.getElementById('pnpRole');
	var _pnpRoleSpacerEl = roleRow ? roleRow.nextElementSibling : null; // spacer <div> after roleRow
	var _pnpFsHintRowEl  = document.getElementById('pnpFsHintRow');
	if (isGPT) {
		// GPT: only primary, hide role row entirely; expand filesystem field to full width
		if (roleRow)        roleRow.style.display      = 'none';
		if (_pnpRoleSpacerEl)  _pnpRoleSpacerEl.style.display = 'none';
		if (_pnpFsHintRowEl)   _pnpFsHintRowEl.style.gridColumn = '1 / -1';
		if (roleEl) { roleEl.innerHTML = '<option value="primary">primary</option>'; roleEl.value = 'primary'; }
	} else if (isMBR) {
		if (roleRow)        roleRow.style.display      = '';
		if (_pnpRoleSpacerEl)  _pnpRoleSpacerEl.style.display = '';
		if (_pnpFsHintRowEl)   _pnpFsHintRowEl.style.gridColumn = '';
		if (roleEl) {
			// Rebuild options based on context
			var opts = '<option value="primary">primary</option>';
			// Show "logical" only if extended exists or we're inside extended range
			if (extPart || insideExtended) opts += '<option value="logical">logical</option>';
			// Show "extended" only if no extended yet and not inside extended range
			if (!extPart && !insideExtended) opts += '<option value="extended">extended</option>';
			roleEl.innerHTML = opts;
			// Auto-select: if inside extended → logical; else primary
			roleEl.value = insideExtended ? 'logical' : 'primary';
		}
	} else {
		// Unknown/other table → show all options; restore layout from GPT overrides
		if (roleRow)        roleRow.style.display      = '';
		if (_pnpRoleSpacerEl)  _pnpRoleSpacerEl.style.display = '';
		if (_pnpFsHintRowEl)   _pnpFsHintRowEl.style.gridColumn = '';
		if (roleEl) {
			roleEl.innerHTML = '<option value="primary">primary</option><option value="logical">logical</option><option value="extended">extended</option>';
			roleEl.value = (document.getElementById('newPartRole') || {}).value || 'primary';
		}
	}

	/* Pre-fill fs/name from main form */
	var fsEl   = document.getElementById('pnpFsHint');
	var nameEl = document.getElementById('pnpPartName');
	if (fsEl)   fsEl.value    = (document.getElementById('newFsHint')   || {}).value || '';
	if (nameEl) nameEl.value  = (document.getElementById('newPartName') || {}).value || '';

	/* --- Partition table row visibility (first partition) --- */
	var tableRow = document.getElementById('pnpTableRow');
	var tableMsg = document.getElementById('pnpTableMsg');
	var tableTypeEl = document.getElementById('pnpTableType');
	var needsTable = isFirstPartition && (!tableType || tableType === 'unknown' || tableType === 'loop' || tableType === '');
	if (tableRow) tableRow.style.display = needsTable ? '' : 'none';
	if (needsTable && tableMsg) tableMsg.textContent = t('pnpTableMsgText') || '⚠️ This disk has no partition table yet. Choose a type before creating the first partition.';

	/* --- Warning row --- */
	var warnRow = document.getElementById('pnpWarnRow');
	function _pnpSetWarn(msg) {
		if (!warnRow) return;
		if (msg) { warnRow.textContent = msg; warnRow.style.display = ''; }
		else     { warnRow.textContent = ''; warnRow.style.display = 'none'; }
	}
	_pnpSetWarn('');

	/* --- Filesystem field: disabled for extended, enabled otherwise --- */
	var fsHintRow = document.getElementById('pnpFsHintRow');
	function _pnpToggleFsAndRole() {
		var roleVal = roleEl ? roleEl.value : 'primary';
		var fsVal   = fsEl  ? fsEl.value   : '';
		// Extended partition: no filesystem
		if (roleVal === 'extended') {
			if (fsEl) { fsEl.value = ''; fsEl.disabled = true; }
			if (fsHintRow) fsHintRow.style.opacity = '0.4';
		} else {
			if (fsEl) { fsEl.disabled = false; }
			if (fsHintRow) fsHintRow.style.opacity = '';
		}
		// Filesystem-dependent fields
		fsVal = fsEl ? fsEl.value : '';
		var show = (fsVal !== '' && roleVal !== 'extended');
		var lblRow = document.getElementById('pnpFsLabelRow');
		var mntRow = document.getElementById('pnpMountRow');
		if (lblRow) lblRow.style.display = show ? 'block' : 'none';
		if (mntRow) mntRow.style.display = show ? 'block' : 'none';
		// Validate logical without extended
		if (roleVal === 'logical' && !extPart && !insideExtended) {
			_pnpSetWarn(t('warnNoExtended') || '⚠ No extended partition exists yet. Create an extended partition first, then add logical partitions inside it.');
		} else if (roleVal === 'primary' && insideExtended) {
			_pnpSetWarn(t('warnPrimaryInExtended') || '⚠ Cannot create a primary partition inside an extended partition. Use role "logical" instead.');
		} else {
			_pnpSetWarn('');
		}
	}
	if (roleEl) {
		roleEl.removeEventListener('change', _pnpToggleFsAndRole);
		roleEl.addEventListener('change', _pnpToggleFsAndRole);
	}
	if (fsEl) {
		fsEl.removeEventListener('change', _pnpToggleFsAndRole);
		fsEl.addEventListener('change', _pnpToggleFsAndRole);
	}
	_pnpToggleFsAndRole();

	/* Sync main form so queueCreatePartition* helpers can read from it */
	document.getElementById('newStartSector').value = String(dropStart);
	document.getElementById('newEndSector').value   = String(dropEnd);
	refreshSectorHumanFields();

	if (titleEl) titleEl.textContent = t('newPartAskTitle') || 'New partition';

	modal.style.display = 'flex';
	modal.setAttribute('aria-hidden', 'false');

	function syncMainFormFromModal() {
		document.getElementById('newStartSector').value = document.getElementById('pnpStartSector').value.trim();
		document.getElementById('newEndSector').value   = document.getElementById('pnpEndSector').value.trim();
		document.getElementById('newPartRole').value    = document.getElementById('pnpRole').value;
		document.getElementById('newFsHint').value      = (roleEl && roleEl.value === 'extended') ? '' : document.getElementById('pnpFsHint').value;
		document.getElementById('newPartName').value    = document.getElementById('pnpPartName').value.trim();
		var _pnpAlignEl = document.getElementById('pnpAlign');
		var _mainAlignEl = document.getElementById('newPartAlign');
		if (_pnpAlignEl && _mainAlignEl) _mainAlignEl.value = _pnpAlignEl.value;
		// Store extra pnp params on state for use by queueCreatePartition
		state._pnpFsLabel   = (document.getElementById('pnpFsLabel')   || {value: ''}).value.trim();
		state._pnpMountPoint = (document.getElementById('pnpMountPoint') || {value: ''}).value.trim();
		// Store chosen table type if we need to create it first
		state._pnpNeedsTable = needsTable ? (tableTypeEl ? tableTypeEl.value : 'gpt') : null;
		refreshSectorHumanFields();
	}

	function cleanup() {
		modal.style.display = 'none';
		modal.setAttribute('aria-hidden', 'true');
		cancelBtn.onclick = fsBtn.onclick = null;
		document.removeEventListener('keydown', onEsc);
	}
	function onEsc(ev) { if (ev.key === 'Escape') cleanup(); }
	document.addEventListener('keydown', onEsc);
	cancelBtn.onclick = cleanup;
	fsBtn.onclick = function () {
		// Validate before accepting
		var _role = roleEl ? roleEl.value : 'primary';
		if (_role === 'logical' && !extPart && !insideExtended) {
			showToast(t('warnNoExtended') || 'Create an extended partition first.', 'warn', 5000);
			return;
		}
		if (_role === 'primary' && insideExtended) {
			showToast(t('warnPrimaryInExtended') || 'Cannot create primary inside extended.', 'warn', 5000);
			return;
		}
		cleanup();
		syncMainFormFromModal();
		updateMapStatus(t('tDropQueuedWithFs'));
		queueCreatePartition();
	};
}

// ── Convert partition table modal ──────────────────────────────────────────

function showConvertLabelModal(diskTarget) {
	var modal      = document.getElementById('pcgiConvertLabelModal');
	var cancelBtn  = document.getElementById('pcgiConvertLabelCancelBtn');
	var confirmBtn = document.getElementById('pcgiConvertLabelConfirmBtn');
	var typeEl     = document.getElementById('pcgiConvertLabelType');
	var curEl      = document.getElementById('pcgiConvertLabelCurrent');
	if (!modal) return;

	var devPath = String(diskTarget && (diskTarget.path || diskTarget) || '');
	var curTable = String((diskTarget && diskTarget.table) || 'unknown');
	if (curEl) curEl.textContent = 'Device: ' + (devPath || '?') + '  —  Current table: ' + curTable;

	// Pre-select current type if in list
	if (typeEl && curTable && curTable !== 'unknown') typeEl.value = curTable;

	modal.style.display = 'flex';
	modal.setAttribute('aria-hidden', 'false');

	function cleanup() {
		modal.style.display = 'none';
		modal.setAttribute('aria-hidden', 'true');
		cancelBtn.onclick = confirmBtn.onclick = null;
		document.removeEventListener('keydown', onEsc);
	}
	function onEsc(ev) { if (ev.key === 'Escape') cleanup(); }
	document.addEventListener('keydown', onEsc);
	cancelBtn.onclick = cleanup;
	confirmBtn.onclick = function () {
		var newType = typeEl ? typeEl.value : 'gpt';
		cleanup();
		queueOpWithConfirm(
			'convert_table_label',
			{ device: devPath, table_type: newType },
			'Convert partition table on ' + devPath + ' to ' + newType + ' — DESTROYS ALL PARTITIONS',
			'Confirm partition table conversion',
			'ALL PARTITIONS on ' + devPath + ' will be deleted. This cannot be undone. Continue?'
		);
	};
}

// ── Freetz EVO disk setup modal ────────────────────────────────────────────

function showFritzSetupModal(diskTarget) {
	var modal     = document.getElementById('pcgiFritzSetupModal');
	var cancelBtn = document.getElementById('pcgiFritzSetupCancelBtn');
	var runBtn    = document.getElementById('pcgiFritzSetupRunBtn');
	var tbody     = document.getElementById('fsSetupPartBody');
	var addBtn    = document.getElementById('fsSetupAddPartBtn');
	var diskEl    = document.getElementById('pcgiFritzSetupDisk');
	if (!modal) return;

	var devPath = String(diskTarget && (diskTarget.path || diskTarget) || '');
	var totalSec = Number(diskTarget && diskTarget.total_sectors || 0);
	var lss = Number(diskTarget && diskTarget.logical_sector_size || 512);
	if (lss <= 0 || !isFinite(lss)) lss = 512;
	if (diskEl) diskEl.textContent = 'Device: ' + (devPath || '?') +
		(totalSec ? '  —  ' + humanBytes(totalSec * lss) : '');

	// Default partitions: NTFS_Data ~50%, MediaServer ~50%, FRITZBOX 2 GiB
	var ALIGN = Math.max(1, Math.ceil(1048576 / lss));
	var fritzSec = Math.ceil(2 * 1024 * 1024 * 1024 / lss / ALIGN) * ALIGN;
	// Available after GPT head (2048s min) + GPT tail (33s)
	var avail = Math.max(0, totalSec - 2048 - 33 - fritzSec);
	var ntfsSec  = Math.floor(avail * 0.50 / ALIGN) * ALIGN;
	var msSec    = Math.max(ALIGN, Math.floor((avail - ntfsSec) / ALIGN) * ALIGN);

	function secToHuman(s) {
		return humanBytes(s * lss);
	}

	var defaultRows = [
		{ enabled: true, name: 'NTFS_Data',  fs: 'ntfs',  sizeSec: ntfsSec,  mount: '/var/media/ftp/NTFS_Data',  desc: 'Data exchange with Windows' },
		{ enabled: true, name: 'MediaServer', fs: 'ext4', sizeSec: msSec,    mount: '/var/media/ftp/MediaServer', desc: 'rtorrent / Transmission / aria2' },
		{ enabled: true, name: 'FRITZBOX',   fs: 'ext4',  sizeSec: fritzSec, mount: '/var/media/ftp/FRITZBOX',   desc: 'Freetz EVO external storage' }
	];

	function buildRow(row) {
		var tr = document.createElement('tr');
		tr.style.borderBottom = '1px solid #eee';
		function cell(content, style) {
			var td = document.createElement('td');
			td.style.padding = '4px 6px';
			if (style) td.setAttribute('style', td.getAttribute('style') + style);
			td.appendChild(typeof content === 'string' ? document.createTextNode(content) : content);
			return td;
		}
		var chk = document.createElement('input');
		chk.type = 'checkbox';
		chk.checked = row.enabled;
		chk.style.margin = '0';
		chk.setAttribute('data-field', 'enabled');

		var nameInp = document.createElement('input');
		nameInp.type = 'text';
		nameInp.value = row.name;
		nameInp.style.cssText = 'width:100%;box-sizing:border-box;';
		nameInp.setAttribute('data-field', 'name');

		var fsSel = document.createElement('select');
		fsSel.style.cssText = 'width:100%;';
		fsSel.setAttribute('data-field', 'fs');
		['ext4','ext3','ext2','fat32','ntfs','exfat'].forEach(function(f) {
			var o = document.createElement('option');
			o.value = f; o.textContent = f;
			if (f === row.fs) o.selected = true;
			fsSel.appendChild(o);
		});

		var sizeInp = document.createElement('input');
		sizeInp.type = 'text';
		sizeInp.value = row.sizeSec > 0 ? secToHuman(row.sizeSec) : '';
		sizeInp.title = row.sizeSec + ' sectors';
		sizeInp.style.cssText = 'width:100%;box-sizing:border-box;';
		sizeInp.setAttribute('data-field', 'size');
		sizeInp.setAttribute('data-sectors', String(row.sizeSec));

		var mountInp = document.createElement('input');
		mountInp.type = 'text';
		mountInp.value = row.mount || '';
		mountInp.style.cssText = 'width:100%;box-sizing:border-box;';
		mountInp.setAttribute('data-field', 'mount');

		var delBtn = document.createElement('button');
		delBtn.type = 'button';
		delBtn.textContent = '×';
		delBtn.style.cssText = 'padding:2px 6px;font-size:1em;cursor:pointer;background:#dc3545;color:#fff;border:none;border-radius:3px;';
		delBtn.onclick = function() { tr.parentNode && tr.parentNode.removeChild(tr); drawSetupPreview(); };

		tr.appendChild(cell(chk, 'text-align:center'));
		tr.appendChild(cell(nameInp));
		tr.appendChild(cell(fsSel));
		tr.appendChild(cell(sizeInp));
		tr.appendChild(cell(mountInp));
		tr.appendChild(cell(delBtn, 'text-align:center'));
		return tr;
	}

	if (tbody) {
		tbody.innerHTML = '';
		defaultRows.forEach(function(r) { tbody.appendChild(buildRow(r)); });
	}

	// Warn immediately if default partition names clash with already-mounted filesystems.
	(function() {
		var warnEl = document.getElementById('pcgiFritzSetupWarn');
		if (!warnEl) return;
		var _existing = {};
		var _devs = state.devices || [];
		for (var _di = 0; _di < _devs.length; _di++) {
			var _dparts = _devs[_di].partitions || [];
			for (var _dpi = 0; _dpi < _dparts.length; _dpi++) {
				var _pn = (_dparts[_dpi].part_name || _dparts[_dpi].name || '').trim();
				var _mp = (_dparts[_dpi].mountpoint || '').trim();
				if (_pn) _existing[_pn] = true;
				if (_mp && _mp !== '-') _existing[_mp] = true;
			}
		}
		var _clashing = [];
		defaultRows.forEach(function(r) {
			if (_existing[r.name] || _existing[r.mount]) _clashing.push(r.name);
		});
		if (_clashing.length) {
			warnEl.innerHTML = '⚠ Name(s) already present on another disk: <strong>' + _clashing.join(', ') + '</strong>.<br>' +
				'Consider renaming both the partition name and the filesystem label (e.g. add a <code>_new</code> suffix) ' +
				'to avoid conflicts with existing mount points.';
			warnEl.style.display = '';
		} else {
			warnEl.style.display = 'none';
		}
	})();

	if (addBtn) addBtn.onclick = function() {
		if (tbody) tbody.appendChild(buildRow({ enabled: true, name: '', fs: 'ext4', sizeSec: 0, mount: '', desc: '' }));
		drawSetupPreview();
	};

	modal.style.display = 'flex';
	modal.setAttribute('aria-hidden', 'false');

	// Live preview bar: shows proportional disk layout from current rows
	var _FS_COLORS = { ext4:'#4caf50', ext3:'#8bc34a', ext2:'#cddc39', ntfs:'#2196f3', fat32:'#ff9800', fat16:'#ffb74d', exfat:'#9c27b0', vfat:'#ce93d8' };
	function drawSetupPreview() {
		var previewEl  = document.getElementById('fsSetupPreviewBar');
		var legendEl   = document.getElementById('fsSetupPreviewLegend');
		if (!previewEl) return;
		var ALIGNN2 = Math.max(1, Math.ceil(1048576 / lss));
		var rows2 = collectRows().filter(function(r) { return r.enabled && r.name; });
		var usedSec = 0;
		rows2.forEach(function(r) { usedSec += Math.max(ALIGNN2, r.sizeSec); });
		var totalDisplay = totalSec > 0 ? totalSec : usedSec;
		if (totalDisplay <= 0) { previewEl.innerHTML = ''; if (legendEl) legendEl.innerHTML = ''; return; }
		var html = '', legendHtml = '';
		rows2.forEach(function(r, i) {
			var pct = Math.max(1, Math.round(Math.max(ALIGNN2, r.sizeSec) / totalDisplay * 1000) / 10);
			var col = _FS_COLORS[r.fs] || '#607d8b';
			var tip = r.name + ' (' + r.fs + ') ' + humanBytes(Math.max(ALIGNN2, r.sizeSec) * lss);
			html += '<div style="width:' + pct + '%;background:' + col + ';display:flex;align-items:center;justify-content:center;overflow:hidden;color:#fff;font-size:10px;font-weight:600;white-space:nowrap;min-width:4px" title="' + tip + '">' + (pct > 5 ? r.name : '') + '</div>';
			legendHtml += '<span style="display:inline-flex;align-items:center;gap:3px"><span style="display:inline-block;width:10px;height:10px;background:' + col + ';border-radius:2px"></span>' + r.name + ' (' + humanBytes(Math.max(ALIGNN2, r.sizeSec) * lss) + ')</span>';
		});
		if (totalSec > 0 && usedSec < totalSec) {
			var freePct = Math.max(1, Math.round((totalSec - usedSec) / totalSec * 1000) / 10);
			html += '<div style="flex:1;background:#e0e0e0;min-width:4px" title="Unallocated ' + humanBytes((totalSec - usedSec) * lss) + '"></div>';
			legendHtml += '<span style="display:inline-flex;align-items:center;gap:3px"><span style="display:inline-block;width:10px;height:10px;background:#e0e0e0;border-radius:2px"></span>Free (' + humanBytes((totalSec - usedSec) * lss) + ')</span>';
		}
		previewEl.innerHTML = html;
		if (legendEl) legendEl.innerHTML = legendHtml;
	}

	// Redraw preview on any size/name/fs/enabled change in the table
	if (tbody) {
		tbody.addEventListener('change', drawSetupPreview);
		tbody.addEventListener('input', drawSetupPreview);
	}

	drawSetupPreview();

	function collectRows() {
		var rows = [];
		if (!tbody) return rows;
		var trs = tbody.querySelectorAll('tr');
		for (var i = 0; i < trs.length; i++) {
			var tr = trs[i];
			var chkEl  = tr.querySelector('[data-field="enabled"]');
			var nameEl = tr.querySelector('[data-field="name"]');
			var fsEl   = tr.querySelector('[data-field="fs"]');
			var sizeEl = tr.querySelector('[data-field="size"]');
			var mntEl  = tr.querySelector('[data-field="mount"]');
			rows.push({
				enabled: chkEl  ? chkEl.checked : true,
				name:    nameEl ? nameEl.value.trim() : '',
				fs:      fsEl   ? fsEl.value : 'ext4',
				sizeSec: sizeEl ? (sizeEl.value.trim() ? Math.floor(parseHumanBytes(sizeEl.value) / lss) || parseInt(sizeEl.getAttribute('data-sectors'), 10) || 0 : parseInt(sizeEl.getAttribute('data-sectors'), 10) || 0) : 0,
				mount:   mntEl  ? mntEl.value.trim() : ''
			});
		}
		return rows;
	}

	function execSetup() {
		var rows = collectRows().filter(function(r) { return r.enabled && r.name; });
		if (!rows.length) { showToast('No partitions configured', 'warn'); return; }

		var doDelete = document.getElementById('fsSetupDeleteAll') && document.getElementById('fsSetupDeleteAll').checked;
		var doMount  = document.getElementById('fsSetupMountAll') && document.getElementById('fsSetupMountAll').checked;
		var tableType = (document.getElementById('fsSetupTableType') || {value: 'gpt'}).value;
		var alignSel  = (document.getElementById('fsSetupAlign') || {value: 'optimal'}).value;

		// Warn if any configured mount point is already in use
		var _warnMounts = [];
		var _devs = state.devices || [];
		for (var _di = 0; _di < _devs.length; _di++) {
			var _dparts = _devs[_di].partitions || [];
			for (var _dpi = 0; _dpi < _dparts.length; _dpi++) {
				var _mp = (_dparts[_dpi].mountpoint || '').trim();
				if (_mp && _mp !== '-') {
					for (var _ri = 0; _ri < rows.length; _ri++) {
						if (rows[_ri].mount && rows[_ri].mount === _mp)
							_warnMounts.push(_mp);
					}
				}
			}
		}
		if (_warnMounts.length)
			showToast('⚠ Mount point(s) already in use: ' + _warnMounts.join(', '), 'warn', 8000);

		var ops = [];

		// Step 1: delete existing + create partition table
		if (doDelete) {
			// Enumerate existing partitions and queue individual delete ops (in reverse order)
			// so each goes to the backend as action_delete_partition — no unknown action used.
			var _previewDev = buildPreviewDevice(diskTarget);
			var _existParts = [];
			for (var _pi = 0; _pi < (_previewDev.partitions || []).length; _pi++) {
				var _pp = _previewDev.partitions[_pi];
				if (_pp && _pp.kind === 'partition' && Number(_pp.number || 0) > 0)
					_existParts.push(_pp);
			}
			_existParts.sort(function(a, b) { return Number(b.number || 0) - Number(a.number || 0); });
			// First unmount any mounted partitions (in reverse order too)
			for (var _pu = 0; _pu < _existParts.length; _pu++) {
				var _pup = _existParts[_pu];
				var _pumpInfo = partitionMountInfo(_pup, devPath);
				if (_pumpInfo.isMounted && _pumpInfo.partitionPath) {
					ops.push({
						action: 'unmount_partition',
						partition: _pumpInfo.partitionPath,
						label: 'Unmount ' + _pumpInfo.partitionPath
					});
				}
			}
			for (var _pi2 = 0; _pi2 < _existParts.length; _pi2++) {
				ops.push({
					action: 'delete_partition',
					device: devPath,
					partnum: _existParts[_pi2].number,
					label: 'Delete partition p' + _existParts[_pi2].number + ' on ' + devPath
				});
			}
			ops.push({ action: 'convert_table_label',  device: devPath, table_type: tableType, label: 'Create ' + tableType + ' partition table' });
		}
		var ALIGNN = Math.max(1, Math.ceil(1048576 / lss));
		if (alignSel === '2048') ALIGNN = 2048;
		else if (alignSel === '4096') ALIGNN = 4096;
		else if (alignSel === 'no') ALIGNN = 1;

		// Last usable sector: GPT reserves 33 sectors at tail, MBR has no reserved tail.
		var _lastUsable = totalSec > 0
			? (tableType === 'gpt' ? totalSec - 1 - 33 : totalSec - 1)
			: 0;

		// Partition numbers start at 1 after a fresh table.
		// Helper: compute the block device node for partition number N.
		function _fritzPartPath(dev, n) {
			return /\d$/.test(dev) ? dev + 'p' + n : dev + n;
		}
		var _partIdx = 1;

		var curSec = ALIGNN;
		for (var ri = 0; ri < rows.length; ri++) {
			var r = rows[ri];
			// Skip partitions that start beyond the last usable sector (disk full)
			if (_lastUsable > 0 && curSec > _lastUsable) {
				showToast('⚠ Partition "' + r.name + '" does not fit on disk (out of space). Skipped.', 'warn', 8000);
				_partIdx++;
				continue;
			}
			var endSec = curSec + Math.max(ALIGNN, r.sizeSec) - 1;
			endSec = Math.floor((endSec + 1) / ALIGNN) * ALIGNN - 1;
			// Clamp to last usable sector — critical for the last partition and
			// avoids "location outside device" errors from parted.
			if (_lastUsable > 0 && endSec > _lastUsable) {
				endSec = Math.floor((_lastUsable + 1) / ALIGNN) * ALIGNN - 1;
				if (endSec > _lastUsable) endSec = _lastUsable;
			}
			ops.push({
				action: 'create_partition',
				device: devPath,
				start_sector: String(curSec),
				end_sector:   String(endSec),
				part_role:    'primary',
				fs_hint:      r.fs,
				part_name:    r.name,
				part_label:   r.name,
				create_fs:    '1',
				label: 'Create ' + r.name + ' (' + r.fs + ') ' + curSec + 's..' + endSec + 's'
			});
			if (doMount && r.mount) {
				var _partNode = _fritzPartPath(devPath, _partIdx);
				ops.push({
					action: 'mount_partition',
					partition: _partNode,
					mountpoint: r.mount,
					fs_type: 'auto',
					label: 'Mount ' + r.name + ' (' + _partNode + ') → ' + r.mount
				});
			}
			_partIdx++;
			curSec = endSec + 2;  // small gap before alignment
			curSec = Math.ceil(curSec / ALIGNN) * ALIGNN;
		}

		cleanup();

		// Queue all ops — user already confirmed via the modal
		ops.forEach(function(op) {
			var a = op.action;
			var p = Object.assign({}, op);
			delete p.action; delete p.label;
			queueOp(a, p, op.label || a, '', true /* quiet */);
		});
		showToast('Freetz EVO setup: ' + ops.length + ' operations queued', 'info');
	}

	function cleanup() {
		modal.style.display = 'none';
		modal.setAttribute('aria-hidden', 'true');
		if (cancelBtn) cancelBtn.onclick = null;
		if (runBtn)    runBtn.onclick    = null;
		document.removeEventListener('keydown', onEsc);
	}
	function onEsc(ev) { if (ev.key === 'Escape') cleanup(); }
	document.addEventListener('keydown', onEsc);
	if (cancelBtn) cancelBtn.onclick = cleanup;
	if (runBtn)    runBtn.onclick    = function() { execSetup(); };
}

// ── Create filesystem modal ──────────────────────────────────────────────────

function showMkfsModal() {
	var modal      = document.getElementById('pcgiMkfsModal');
	var cancelBtn  = document.getElementById('pcgiMkfsCancelBtn');
	var confirmBtn = document.getElementById('pcgiMkfsConfirmBtn');
	var titleEl    = document.getElementById('pcgiMkfsTitle');
	if (!modal) return;

	/* Pre-fill from the inline form */
	var partEl   = document.getElementById('mkfsPartPath');
	var fsEl     = document.getElementById('mkfsFsType');
	var lblEl    = document.getElementById('mkfsLabel');
	var extEl    = document.getElementById('mkfsExtraOpts');
	var fmtEl    = document.getElementById('mkfsFullFormat');
	var fmtRow   = document.getElementById('mkfsFullFormatRow');
	if (partEl) partEl.value = document.getElementById('fsPartitionPath').value.trim();
	if (fsEl)   { fsEl.value = document.getElementById('fsTypeSelect').value; if (fsEl.value === 'auto') fsEl.value = 'ext4'; }
	if (lblEl)  lblEl.value  = document.getElementById('fsLabelInput').value.trim();
	if (extEl)  extEl.value  = document.getElementById('extraOptsInput').value.trim();
	if (fmtEl)  fmtEl.checked = false;

	function updateFullFormatVisibility() {
		if (fmtRow) fmtRow.style.display = (fsEl && fsEl.value === 'ntfs') ? '' : 'none';
	}
	if (fsEl) fsEl.addEventListener('change', updateFullFormatVisibility);
	updateFullFormatVisibility();

	if (titleEl) titleEl.textContent = t('mkfsModalTitle') || 'Create filesystem';
	if (confirmBtn) confirmBtn.textContent = t('mkfsBtnCreate') || 'Create filesystem';
	if (cancelBtn)  cancelBtn.textContent  = t('mkfsBtnCancel') || 'Cancel';

	modal.style.display = 'flex';
	modal.setAttribute('aria-hidden', 'false');

	function cleanup() {
		modal.style.display = 'none';
		modal.setAttribute('aria-hidden', 'true');
		cancelBtn.onclick = confirmBtn.onclick = null;
		if (fsEl) fsEl.removeEventListener('change', updateFullFormatVisibility);
		document.removeEventListener('keydown', onEsc);
	}
	function onEsc(ev) { if (ev.key === 'Escape') cleanup(); }
	document.addEventListener('keydown', onEsc);
	cancelBtn.onclick = cleanup;
	confirmBtn.onclick = function () {
		var part = (partEl ? partEl.value.trim() : '') || document.getElementById('fsPartitionPath').value.trim();
		var fsType = fsEl ? fsEl.value : document.getElementById('fsTypeSelect').value;
		var label  = lblEl ? lblEl.value.trim() : document.getElementById('fsLabelInput').value.trim();
		var extra  = extEl ? extEl.value.trim()  : document.getElementById('extraOptsInput').value.trim();
		var fullFmt = (fmtEl && fmtEl.checked && fsType === 'ntfs') ? '1' : '0';
		if (!part) { showToast(t('tNeedPartPath'), 'warn'); return; }
		if (!fsType || fsType === 'auto') { showToast(t('tNeedMkfsType'), 'warn'); return; }
		/* Sync back to inline form */
		document.getElementById('fsPartitionPath').value = part;
		document.getElementById('fsTypeSelect').value    = fsType;
		document.getElementById('fsLabelInput').value    = label;
		document.getElementById('extraOptsInput').value  = extra;
		cleanup();
		queueOpWithConfirm(
			'create_filesystem',
			{ partition: part, fs_type: fsType, label: label, extra_opts: extra, full_format: fullFmt },
			'Make filesystem ' + fsType + ' on ' + part,
			t('confirmMkfs'),
			t('confirmMkfsMsg')
		);
	};
}

// ── Verify partitions modal ───────────────────────────────────────────────────

function showVerifyModal() {
	var modal = document.getElementById('pcgiVerifyModal');
	if (!modal) return;

	populateDevDropdown('verifySourceDev');
	populateDevDropdown('verifyTargetDev');
	populatePartDropdown('verifySourceDev', 'verifySourcePartNum');
	populatePartDropdown('verifyTargetDev', 'verifyTargetPartNum');

	/* Auto-set verify unmount based on currently selected partition */
	var _vumEl = document.getElementById('verifyUnmount');
	if (_vumEl) {
		var _vp = state.selectedPart;
		var _vmounted = !!((_vp) && _vp.mountpoint && String(_vp.mountpoint).trim() && String(_vp.mountpoint).trim() !== '-');
		_vumEl.value = _vmounted ? 'yes' : 'no';
	}

	var cancelBtn = document.getElementById('pcgiVerifyCancelBtn');
	var okBtn     = document.getElementById('pcgiVerifyOkBtn');

	modal.style.display = 'flex';
	modal.setAttribute('aria-hidden', 'false');

	function cleanup() {
		modal.style.display = 'none';
		modal.setAttribute('aria-hidden', 'true');
		cancelBtn.onclick = okBtn.onclick = null;
		document.removeEventListener('keydown', onEsc);
	}
	function onEsc(ev) { if (ev.key === 'Escape') cleanup(); }
	document.addEventListener('keydown', onEsc);
	cancelBtn.onclick = cleanup;
	okBtn.onclick = function () {
		var srcDev  = document.getElementById('verifySourceDev');
		var srcNum  = document.getElementById('verifySourcePartNum');
		var cmpDev  = document.getElementById('verifyTargetDev');
		var cmpNum  = document.getElementById('verifyTargetPartNum');
		var umSel   = document.getElementById('verifyUnmount');
		if (!srcDev || !srcNum || !cmpDev || !cmpNum) { cleanup(); return; }
		var srcPath = srcDev.value.replace(/\/*$/, '') +
		              (/[0-9]$/.test(srcDev.value) ? 'p' : '') + srcNum.value;
		var cmpPath = cmpDev.value.replace(/\/*$/, '') +
		              (/[0-9]$/.test(cmpDev.value) ? 'p' : '') + cmpNum.value;
		var unmount = umSel ? umSel.value : 'no';
		var vParams = {
			source_partition:  srcPath,
			compare_partition: cmpPath,
			unmount_before:    unmount,
			step_delay:        '0'
		};
		var vLabel = 'Verify ' + srcPath + ' == ' + cmpPath;
		cleanup();
		showCommandPreviewModal('verify_partition', vParams, vLabel, t('confirmVerify'), t('confirmVerifyMsg'))
		.then(function (previewText) {
			if (previewText === null) return;
			queueOp('verify_partition', vParams, vLabel, previewText, false);
			showToast(t('tVerifyQueued'), 'info', 10000);
		});
	};
}

// ── Move / Clone modal ────────────────────────────────────────────────────────

function showMoveCloneModal(targetDevPath, targetStart, targetEnd, preselectSourceDev, preselectSourcePart) {
	var modal    = document.getElementById('pcgiMoveCloneModal');
	var infoEl   = document.getElementById('mcTargetInfo');
	if (!modal) return;

	// Populate source device/partition
	populateDevDropdown('mcSourceDevice', preselectSourceDev || state.selectedDevice || '');
	populateMcPartDropdown(preselectSourcePart ? String(preselectSourcePart.number || '') : '');

	// Populate target device/partition
	populateDevDropdown('mcTargetDevice', targetDevPath || state.selectedDevice || '');
	populateMcTargetPartDropdown('');

	// Pre-fill target sector range
	var startEl = document.getElementById('mcTargetStart');
	var endEl   = document.getElementById('mcTargetEnd');
	if (startEl) startEl.value = String(targetStart);
	if (endEl)   endEl.value   = String(targetEnd);
	refreshSectorHumanFields();

	// Info strip
	if (infoEl) {
		var ss = getCurrentSectorSize();
		var sz = Number(targetEnd) - Number(targetStart) + 1;
		infoEl.textContent = (targetDevPath || '') + '  [' + targetStart + 's \u2013 ' + targetEnd + 's]  (' + humanBytes(sz * ss) + ')';
	}

	// Ensure mount field visibility matches selector
	var mountAfterSel = document.getElementById('mcMountAfter');
	var mountInput    = document.getElementById('mcTargetMount');
	if (mountAfterSel && mountInput) {
		mountInput.style.display = mountAfterSel.value === 'yes' ? '' : 'none';
	}

	updateMcSourceInfo();

	var cancelBtn = document.getElementById('pcgiMcCancelBtn');
	var okBtn     = document.getElementById('pcgiMcOkBtn');
	modal.style.display = 'flex';
	modal.setAttribute('aria-hidden', 'false');

	function cleanup() {
		modal.style.display = 'none';
		modal.setAttribute('aria-hidden', 'true');
		cancelBtn.onclick = okBtn.onclick = null;
		document.removeEventListener('keydown', onEsc);
	}
	function onEsc(ev) { if (ev.key === 'Escape') cleanup(); }
	document.addEventListener('keydown', onEsc);
	cancelBtn.onclick = cleanup;

	okBtn.onclick = function () {
		var srcDevSel   = document.getElementById('mcSourceDevice');
		var srcPartSel  = document.getElementById('mcSourcePartNum');
		var tgtDevSel   = document.getElementById('mcTargetDevice');
		var tgtPartSel  = document.getElementById('mcTargetPartNum');
		var modeSel     = document.getElementById('mcMode');
		var methodSel   = document.getElementById('mcCloneMethod');
		var startEl2    = document.getElementById('mcTargetStart');
		var endEl2      = document.getElementById('mcTargetEnd');
		var mountAfterEl= document.getElementById('mcMountAfter');
		var mountEl     = document.getElementById('mcTargetMount');
		var verifyEl    = document.getElementById('mcVerify');
		var alignEl     = document.getElementById('mcAlignment');
		var umountEl    = document.getElementById('mcUnmountBefore');
		var forceFsEl   = document.getElementById('mcForceFs');
		var extraEl     = document.getElementById('mcPartcloneExtra');
		var delayEl     = document.getElementById('mcStepDelay');
		var ddBsEl      = document.getElementById('mcDdBs');

		var srcDevPath  = srcDevSel  ? String(srcDevSel.value  || '').trim() : '';
		var srcPartNum  = srcPartSel ? String(srcPartSel.value || '').trim() : '';

		// Target device: use selector value; fall back to the drop-zone device
		var tgtDevPath  = tgtDevSel  ? String(tgtDevSel.value  || '').trim() : targetDevPath;
		if (!tgtDevPath) tgtDevPath = targetDevPath;

		// Target sector range: prefer explicit partition selection, else sector fields
		var tgtPartNum  = tgtPartSel ? String(tgtPartSel.value || '').trim() : '';
		var tStart, tEnd;
		if (tgtPartNum) {
			// Resolve start/end from selected target partition
			var tFound = findPartitionGlobalByDeviceNum(tgtDevPath, Number(tgtPartNum));
			if (tFound && tFound.part) {
				tStart = String(tFound.part.start);
				tEnd   = String(tFound.part.end);
			}
		}
		if (!tStart || !tEnd) {
			tStart = startEl2 ? String(startEl2.value || '').trim() : String(targetStart);
			tEnd   = endEl2   ? String(endEl2.value   || '').trim() : String(targetEnd);
		}

		var opMode      = modeSel      ? String(modeSel.value      || 'clone')  : 'clone';
		var cloneMethod = methodSel    ? String(methodSel.value    || 'smart')  : 'smart';
		var mountAfter  = mountAfterEl ? String(mountAfterEl.value || 'no')     : 'no';
		var tMount      = mountEl      ? String(mountEl.value      || '').trim(): '';
		var verify      = verifyEl     ? String(verifyEl.value     || 'no')     : 'no';
		var align       = alignEl      ? String(alignEl.value      || '1048576')   : '1048576';
		var unmount     = umountEl     ? String(umountEl.value     || 'yes')    : 'yes';
		var forceFs     = forceFsEl    ? String(forceFsEl.value    || '').trim(): '';
		var extra       = extraEl      ? String(extraEl.value      || '').trim(): '';
		var delay       = delayEl      ? String(delayEl.value      || '1').trim(): '1';
		var ddBs        = ddBsEl       ? String(ddBsEl.value       || '1M').trim(): '1M';
		var fsckPasses  = String((document.getElementById('mcFsckPasses')  || {value:'2'}).value || '2');
		var ddFallback  = String((document.getElementById('mcDdFallback')  || {value:'1'}).value || '1');
		var skipWriteErr = String((document.getElementById('mcSkipWriteError') || {value:'0'}).value || '0');

		if (!srcDevPath || !srcPartNum) {
			showToast(t('tNeedSourcePart'), 'warn', 10000);
			return;
		}
		if (!tStart || !tEnd || !/^\d+$/.test(tStart) || !/^\d+$/.test(tEnd)) {
			showToast(t('tNeedStartEnd'), 'warn', 10000);
			return;
		}

		var srcFound = findPartitionGlobalByDeviceNum(srcDevPath, Number(srcPartNum));
		var srcPart  = srcFound ? srcFound.part : null;

		cleanup();

		var isMove  = (opMode === 'move');
		var tStartN = Number(tStart);
		var tEndN   = Number(tEnd);
		var extraOpts = {
			clone_mode:       cloneMethod,
			dd_bs:            ddBs,
			partclone_verify: verify,
			align_bytes:      align,
			unmount_before:   unmount,
			mount_after:      mountAfter,
			target_mountpoint: tMount,
			force_fs:         forceFs,
			partclone_extra:  extra,
			step_delay:       /^\d+$/.test(delay) ? delay : '1',
			fat_fsck_passes:  fsckPasses,
			dd_fallback:      ddFallback,
			skip_write_error: skipWriteErr
		};

		if (!srcPart) {
			showToast(t('tNeedSourcePart'), 'warn', 10000);
			return;
		}

		if (isMove) {
			if (!ensureMoveTargetDoesNotIntersectSource(srcPart, tStartN, tEndN, srcDevPath, tgtDevPath)) return;
			var moveParams = {
				device:            tgtDevPath,
				source_device:     srcDevPath,
				source_partition:  String(srcPart.path || ''),
				source_partnum:    srcPartNum,
				start_sector:      String(tStartN),
				end_sector:        String(tEndN),
				clone_mode:        cloneMethod,
				dd_bs:             ddBs,
				partclone_verify:  verify,
				target_mountpoint: mountAfter === 'yes' ? tMount : '',
				align_bytes:       align,
				unmount_before:    unmount,
				force_fs:          forceFs,
				partclone_extra:   extra,
				step_delay:        extraOpts.step_delay,
				fat_fsck_passes:   fsckPasses,
				dd_fallback:       ddFallback,
				skip_write_error:  skipWriteErr
			};
			var moveLabel = 'Move partition (' + cloneMethod + ') #' + srcPartNum + ' from ' + srcDevPath + ' to ' + tgtDevPath + ' [' + tStart + 's..' + tEnd + 's]';
			showCommandPreviewModal('move_partition', moveParams, moveLabel, t('confirmMove'), t('confirmMoveMsg'))
			.then(function (previewText) {
				if (previewText === null) return;
				queueOp('move_partition', moveParams, moveLabel, previewText, false);
				showToast(t('tQueued') + ' ' + moveLabel, 'info', 10000);
			});
		} else {
			var cloneParams = {
				device:              tgtDevPath,
				target_device:       tgtDevPath,
				source_device:       srcDevPath,
				source_partition:    String(srcPart.path || ''),
				source_partnum:      srcPartNum,
				target_start_sector: String(tStartN),
				target_end_sector:   String(tEndN),
				clone_mode:          cloneMethod,
				dd_bs:               ddBs,
				partclone_verify:    verify,
				target_mountpoint:   mountAfter === 'yes' ? tMount : '',
				align_bytes:         align,
				unmount_before:      unmount,
				force_fs:            forceFs,
				partclone_extra:     extra,
				step_delay:          extraOpts.step_delay,
				fat_fsck_passes:     fsckPasses,
				dd_fallback:         ddFallback,
				skip_write_error:    skipWriteErr
			};
			var cloneLabel = 'Clone partition (' + cloneMethod + ') #' + srcPartNum + ' from ' + srcDevPath + ' to ' + tgtDevPath + ' [' + tStart + 's..' + tEnd + 's]';
			showCommandPreviewModal('clone_partition_dd', cloneParams, cloneLabel, t('confirmClone'), t('confirmCloneMsg'))
			.then(function (previewText) {
				if (previewText === null) return;
				queueOp('clone_partition_dd', cloneParams, cloneLabel, previewText, false);
				showToast(t('tQueued') + ' ' + cloneLabel, 'info', 10000);
			});
		}
	};
}

function enqueueCloneLikeOps(targetDevPath, sourceDevPath, part, targetStart, targetEnd, includeDeleteSource, quiet, mountpointOverride, cloneMode, extraOpts) {
	if (includeDeleteSource && !ensureMoveTargetDoesNotIntersectSource(part, targetStart, targetEnd, sourceDevPath, targetDevPath)) {
		return false;
	}
	var opts = extraOpts || {};
	var cloneOpts = getCloneChipOptions();
	var mode = String(cloneMode || opts.clone_mode || 'smart').toLowerCase() === 'sector' ? 'sector' : 'smart';
	var requestedMountpoint = String(mountpointOverride !== undefined ? mountpointOverride : (opts.target_mountpoint || cloneOpts.target_mountpoint || '')).trim();
	var mountAfter   = opts.mount_after      !== undefined ? String(opts.mount_after)      : 'no';
	var ddBs         = opts.dd_bs            || cloneOpts.dd_bs;
	var verify       = opts.partclone_verify || (mode === 'smart' ? cloneOpts.partclone_verify : 'no');
	var alignBytes   = opts.align_bytes      || cloneOpts.align_bytes;
	var unmountBef   = opts.unmount_before   !== undefined ? String(opts.unmount_before) : cloneOpts.unmount_before;
	var forceFs      = opts.force_fs         !== undefined ? opts.force_fs         : cloneOpts.force_fs;
	var extraPartcl  = opts.partclone_extra  !== undefined ? opts.partclone_extra  : cloneOpts.partclone_extra;
	var stepDelay    = opts.step_delay       !== undefined ? opts.step_delay       : cloneOpts.step_delay;
	var srcPartPath  = String(part.path || '');
	var srcPartNum   = String(part.number || '');

	if (includeDeleteSource) {
		// MOVE: single call to partition_migration.sh with -M flag
		var moveParams = {
			device:            targetDevPath,
			source_device:     sourceDevPath,
			source_partition:  srcPartPath,
			source_partnum:    srcPartNum,
			start_sector:      String(targetStart),
			end_sector:        String(targetEnd),
			clone_mode:        mode,
			dd_bs:             ddBs,
			partclone_verify:  verify,
			target_mountpoint: mountAfter === 'yes' ? requestedMountpoint : '',
			align_bytes:       alignBytes,
			unmount_before:    unmountBef,
			force_fs:          forceFs,
			partclone_extra:   extraPartcl,
			step_delay:        stepDelay
		};
		var moveLabel = 'Move partition (' + mode + ') #' + srcPartNum + ' from ' + sourceDevPath + ' to ' + targetDevPath + ' [' + targetStart + 's..' + targetEnd + 's]';
		queueOp('move_partition', moveParams, moveLabel, buildCommandPreview('move_partition', moveParams), !!quiet);
	} else {
		// CLONE: single call to partition_migration.sh (no -M)
		var cloneParams = {
			device:            targetDevPath,
			target_device:     targetDevPath,
			source_device:     sourceDevPath,
			source_partition:  srcPartPath,
			source_partnum:    srcPartNum,
			target_start_sector: String(targetStart),
			target_end_sector:   String(targetEnd),
			clone_mode:        mode,
			dd_bs:             ddBs,
			partclone_verify:  verify,
			target_mountpoint: mountAfter === 'yes' ? requestedMountpoint : '',
			align_bytes:       alignBytes,
			unmount_before:    unmountBef,
			force_fs:          forceFs,
			partclone_extra:   extraPartcl,
			step_delay:        stepDelay
		};
		var cloneLabel = 'Clone partition (' + mode + ') #' + srcPartNum + ' from ' + sourceDevPath + ' to ' + targetDevPath + ' [' + targetStart + 's..' + targetEnd + 's]';
		queueOp('clone_partition_dd', cloneParams, cloneLabel, buildCommandPreview('clone_partition_dd', cloneParams), !!quiet);
	}

	if (!quiet) {
		var kind = includeDeleteSource ? 'move' : 'clone';
		showToast('Queued ' + kind + ' (' + mode + ') for source partition #' + srcPartNum + '.', 'info', 10000);
	}
	return true;
}

function queueClonePartitionWithConfirm(targetDevPath, sourceDevPath, part, targetStart, targetEnd, label, mountpointOverride, cloneMode) {
var cloneOpts = getCloneChipOptions();
var mode = String(cloneMode || 'smart').toLowerCase() === 'sector' ? 'sector' : 'smart';
var cloneParams = {
source_partition: String(part.path || ''),
source_device: sourceDevPath,
source_partnum: String(part.number || ''),
target_device: targetDevPath,
target_start_sector: String(targetStart),
target_end_sector: String(targetEnd),
clone_mode: mode,
dd_bs: cloneOpts.dd_bs,
partclone_verify: mode === 'smart' ? cloneOpts.partclone_verify : 'no',
target_mountpoint: String(mountpointOverride || cloneOpts.target_mountpoint || ''),
align_bytes: cloneOpts.align_bytes,
unmount_before: cloneOpts.unmount_before,
force_fs: cloneOpts.force_fs,
partclone_extra: cloneOpts.partclone_extra,
step_delay: cloneOpts.step_delay
};
var cloneLabel = label || ('Clone partition (' + mode + ') #' + part.number + ' from ' + sourceDevPath + ' to ' + targetDevPath + ' [' + targetStart + 's..' + targetEnd + 's]');
return showCommandPreviewModal('clone_partition_dd', cloneParams, cloneLabel, t('confirmClone'), t('confirmCloneMsg'))
.then(function (previewText) {
if (previewText === null) return;
var enqueued = enqueueCloneLikeOps(targetDevPath, sourceDevPath, part, targetStart, targetEnd, false, true, mountpointOverride, mode);
if (enqueued === false) return;
showToast(t('tQueued') + ' ' + cloneLabel, 'info', 10000);
});
}

function enqueueMovePartitionOps(targetDevPath, sourceDevPath, part, targetStart, targetEnd, movePreview, quiet, mountpointOverride, cloneMode) {
if (!ensureMoveTargetDoesNotIntersectSource(part, targetStart, targetEnd, sourceDevPath, targetDevPath)) {
return false;
}
var enqueued = enqueueCloneLikeOps(targetDevPath, sourceDevPath, part, targetStart, targetEnd, true, true, mountpointOverride, cloneMode);
if (enqueued === false) return false;
if (!quiet) {
showToast('Relocate partition #' + part.number + ' added.', 'info', 10000);
}
return true;
}

function queueMovePartitionWithConfirm(targetDevPath, part, targetStart, targetEnd, label, sourceDevPath, mountpointOverride, cloneMode) {
var sourceDev = String(sourceDevPath || targetDevPath || '');
var mode = String(cloneMode || 'smart').toLowerCase() === 'sector' ? 'sector' : 'smart';
var cloneOpts = getCloneChipOptions();
if (!ensureMoveTargetDoesNotIntersectSource(part, targetStart, targetEnd, sourceDev, targetDevPath)) {
return Promise.resolve(false);
}
var moveParams = {
	device: targetDevPath,
	partnum: part.number,
	start_sector: targetStart,
	end_sector: targetEnd,
	source_device: sourceDev,
	source_partnum: String(part.number || ''),
	source_partition: String(part.path || ''),
	clone_mode: mode,
	dd_bs: cloneOpts.dd_bs,
	partclone_verify: mode === 'smart' ? cloneOpts.partclone_verify : 'no',
	target_mountpoint: String(mountpointOverride || cloneOpts.target_mountpoint || ''),
	align_bytes: cloneOpts.align_bytes,
	unmount_before: cloneOpts.unmount_before,
	force_fs: cloneOpts.force_fs,
	partclone_extra: cloneOpts.partclone_extra,
	step_delay: cloneOpts.step_delay
};
var moveLabel = label || ('Relocate partition (' + mode + ') #' + part.number + ' from ' + sourceDev + ' to ' + targetDevPath + ' [' + targetStart + 's..' + targetEnd + 's] (create + clone + delete)');
return showCommandPreviewModal('move_partition', moveParams, moveLabel, t('confirmMove'), t('confirmMoveMsg'))
.then(function (previewText) {
if (previewText === null) return;
if (!ensureMoveTargetDoesNotIntersectSource(part, targetStart, targetEnd, sourceDev, targetDevPath)) return;
var enqueued = enqueueMovePartitionOps(targetDevPath, sourceDev, part, targetStart, targetEnd, previewText, true, mountpointOverride, mode);
if (enqueued === false) return;
showToast(t('tQueued') + ' ' + moveLabel, 'info', 10000);
});
}

function enqueueDeletePartitionOps(devPath, part, deletePreview, quiet) {
var deleteParams = { device: devPath, partnum: part.number };
var deleteLabel = 'Delete partition p' + part.number + ' on ' + devPath;
var mountInfo = partitionMountInfo(part, devPath);

if (mountInfo.isMounted && mountInfo.partitionPath) {
var umParams = { partition: mountInfo.partitionPath };
queueOp(
'unmount_partition',
umParams,
'Unmount ' + mountInfo.partitionPath,
buildCommandPreview('unmount_partition', umParams),
true
);
}

queueOp('delete_partition', deleteParams, deleteLabel, deletePreview || buildCommandPreview('delete_partition', deleteParams), quiet);
}

function queueDeletePartitionWithConfirm(devPath, part) {
var deleteParams = { device: devPath, partnum: part.number };
var deleteLabel = 'Delete partition p' + part.number + ' on ' + devPath;
showCommandPreviewModal('delete_partition', deleteParams, deleteLabel, t('confirmDelete'), t('confirmDeleteMsg'))
.then(function (previewText) {
if (previewText === null) return;
enqueueDeletePartitionOps(devPath, part, previewText, true);
showToast(t('tQueued') + ' ' + deleteLabel, 'info', 10000);
});
}

	function queueMoveSelectedByDirection(direction) {
		if (!state.selectedPart || !state.selectedPart.number) {
			showToast(t('tNoPartition'), 'warn');
			return;
		}
		var dev = getSelectedDeviceData();
		if (!dev) {
			showToast(t('tNoDevice'), 'warn');
			return;
		}

		var idx = -1;
		for (var i = 0; i < dev.partitions.length; i++) {
			var part = dev.partitions[i];
			if (part.kind === 'partition' && String(part.path || '') === String(state.selectedPart.path || '')) {
				idx = i;
				break;
			}
		}
		if (idx < 0) {
			showToast(t('tContextUnavailable'), 'warn');
			return;
		}

		var source = dev.partitions[idx];
		var target = null;
		var size = Number(source.size || 0);
		var targetStart = Number(source.start || 0);
		var targetEnd = Number(source.end || 0);

		if (direction === 'left') {
			target = idx > 0 ? dev.partitions[idx - 1] : null;
			if (!target || target.kind !== 'free') {
				showToast('No free segment on the left of selected partition.', 'warn');
				return;
			}
			targetStart = Number(target.start || 0);
			targetEnd = targetStart + size - 1;
		} else {
			target = idx < dev.partitions.length - 1 ? dev.partitions[idx + 1] : null;
			if (!target || target.kind !== 'free') {
				showToast('No free segment on the right of selected partition.', 'warn');
				return;
			}
			targetEnd = Number(target.end || 0);
			targetStart = targetEnd - size + 1;
			if (targetStart < Number(target.start || 0)) {
				showToast(t('tMoveNoSpace'), 'warn');
				return;
			}
		}

		if (targetStart === Number(source.start || 0) && targetEnd === Number(source.end || 0)) {
			showToast(t('tMoveSame'), 'warn');
			return;
		}

		queueMovePartitionWithConfirm(
			dev.path,
			source,
			targetStart,
			targetEnd,
			'Move partition #' + source.number + ' on ' + dev.path + ' to [' + targetStart + 's..' + targetEnd + 's]'
		);
	}

	function navigateSelectedPartition(direction) {
		var dev = getSelectedDeviceData();
		if (!dev || !dev.partitions || !dev.partitions.length) return;
		var parts = [];
		for (var i = 0; i < dev.partitions.length; i++) {
			if (dev.partitions[i].kind === 'partition') parts.push(dev.partitions[i]);
		}
		if (!parts.length) return;

		var cur = -1;
		if (state.selectedPart) {
			// Match by start sector (unique per partition, same key used in renderMap).
			var spStart = Number(state.selectedPart.start || 0);
			for (var j = 0; j < parts.length; j++) {
				if (spStart > 0 && Number(parts[j].start || 0) === spStart) {
					cur = j;
					break;
				}
			}
		}

		if (direction === 'left') {
			cur = cur <= 0 ? parts.length - 1 : cur - 1;
		} else {
			cur = cur < 0 || cur >= parts.length - 1 ? 0 : cur + 1;
		}
		selectPartition(parts[cur]);
	}

	function onDeviceChange() {
		var sel = document.getElementById('deviceSelect');
		state.selectedDevice = sel ? sel.value : '';
		/* Changing the viewed disk does not affect the current partition selection.
		 * The global selectedPart/selectedPartDevice remain as-is; renderMap() will
		 * highlight the selected partition on whichever disk it belongs to. */
		renderDeviceStrip();
		renderMap();
	}

	function refreshDevices() {
		renderMapLoading(t('tMapLoading'));
		updateMapStatus(t('tMapLoading'));
		return callApi('list_devices', { usb_only: state.usbOnly ? '1' : '0' })
			.then(function (data) {
				if (!data.success) throw new Error(data.message || 'Map load failed');
				state.devices = data.devices || [];
				var sel = document.getElementById('deviceSelect');
				sel.innerHTML = '';
				for (var i = 0; i < state.devices.length; i++) {
					var dev = state.devices[i];
					var opt = document.createElement('option');
					opt.value = dev.path;
					opt.textContent = dev.path + ' [' + (dev.table || '-') + ']';
					sel.appendChild(opt);
				}
				if (state.devices.length > 0) {
					if (!state.selectedDevice) {
						state.selectedDevice = state.devices[0].path;
					}
					sel.value = state.selectedDevice;
					if (sel.value !== state.selectedDevice) {
						state.selectedDevice = sel.value;
					}
				} else {
					state.selectedDevice = '';
				}
				renderDeviceStrip();
				renderMap();
				var _dl = state.devices.map(function(d){return d.path+' ['+(d.table||'-')+']';}).join(', ');
					var _dm = state.devices.length === 1 ? t('tMapLoaded') + ': ' + _dl
						: t('tMapLoaded') + ' - ' + state.devices.length + ' ' + t('tDevices') + ': ' + _dl;
					updateMapStatus(_dm);
			})
			.catch(function (err) {
				renderMapLoading(t('tMapError'));
				updateMapStatus(t('tMapError') + ': ' + err.message);
				logTo('cmdOutput', t('tMapError') + ': ' + err.message, false);
				showToast(t('tMapError') + ': ' + err.message, 'error', 10000);
			});
	}

	function alignSectors(start, end, alignEl) {
		var s = parseInt(start, 10);
		var e = parseInt(end, 10);
		var align = alignEl ? alignEl.value : 'optimal';
		if (align === 'no' || isNaN(s) || isNaN(e)) return { start: start, end: end };
		var ALIGN;
		if (align === 'optimal' || align === 'yes') {
			// Derive alignment from device logical sector size (same formula as buildParamRangeRows)
			var devPath = state.selectedDevice;
			var dev = devPath ? getPreviewDeviceByPath(devPath) : null;
			var lss = Number(dev && dev.logical_sector_size || 512);
			if (!isFinite(lss) || lss <= 0) lss = 512;
			ALIGN = Math.max(1, Math.ceil(1048576 / lss));
		} else {
			ALIGN = Math.max(1, parseInt(align, 10) || 2048);
		}
		s = Math.ceil(s / ALIGN) * ALIGN;
		e = Math.floor((e + 1) / ALIGN) * ALIGN - 1;
		if (e < s) e = s + ALIGN - 1;
		return { start: String(s), end: String(e) };
	}

	function queueCreatePartition() {
		var dev = state.selectedDevice;
		if (dev === null || dev === '') {
			showToast(t('tNoDevice'), 'warn');
			return;
		}
		var start = document.getElementById('newStartSector').value.trim();
		var end = document.getElementById('newEndSector').value.trim();
		if (start === '' || end === '') {
			showToast(t('tNeedStartEnd'), 'warn');
			return;
		}
		// Clamp end to the device's last usable sector before alignment
		var _previewDev = dev ? getPreviewDeviceByPath(dev) : null;
		var _totalSec = Number(_previewDev && _previewDev.total_sectors || 0);
		var _tableType = String(_previewDev && _previewDev.table || '').toLowerCase();
		var _resTail = _tableType === 'gpt' ? 33 : 0;
		var _lastUsable = _totalSec > (_resTail + 1) ? (_totalSec - 1 - _resTail) : (_totalSec > 0 ? _totalSec - 1 : 0);
		if (_lastUsable > 0 && /^\d+$/.test(end) && parseInt(end, 10) > _lastUsable) end = String(_lastUsable);
		var aligned = alignSectors(start, end, document.getElementById('newPartAlign'));
		start = aligned.start; end = aligned.end;
		var role = document.getElementById('newPartRole').value;
		var fsHint = document.getElementById('newFsHint').value;
		var partName = document.getElementById('newPartName').value.trim();
		var partLabel = (state._pnpFsLabel || '').trim();
		var mountPoint = (state._pnpMountPoint || '').trim();
		var params = { device: dev, start_sector: start, end_sector: end, part_role: role, fs_hint: role === 'extended' ? '' : fsHint, part_name: partName, create_fs: (fsHint && role !== 'extended') ? '1' : '0' };
		if (partLabel) params.part_label = partLabel;
		if (mountPoint) params.mount_point = mountPoint;
		// If the disk had no partition table, prepend a convert_label op
		if (state._pnpNeedsTable) {
			var tableParams = { device: dev, table_type: state._pnpNeedsTable };
			var tableLabel = 'Create ' + state._pnpNeedsTable.toUpperCase() + ' partition table on ' + dev;
			// Recalculate lastUsable using the chosen table type (GPT needs 33 sector tail)
			if (state._pnpNeedsTable === 'gpt') {
				var _gptTail = 33;
				var _gptLast = _totalSec > (_gptTail + 1) ? (_totalSec - 1 - _gptTail) : (_totalSec > 0 ? _totalSec - 1 : 0);
				if (_gptLast > 0 && /^\d+$/.test(end) && parseInt(end, 10) > _gptLast) {
					end = String(_gptLast);
					params.end_sector = end;
				}
			}
			var _savedTableType = state._pnpNeedsTable;
			state._pnpNeedsTable = null;
			// Show preview modal for the table creation; on confirm, also queue the partition
			showCommandPreviewModal('convert_label', tableParams, tableLabel, t('confirmCreate'), t('confirmCreateMsg'))
				.then(function (tablePreview) {
					if (tablePreview === null) return;
					queueOp('convert_label', tableParams, tableLabel, tablePreview);
					// Queue the partition creation silently after confirming the table
					var partPreview = buildCommandPreview('create_partition', params);
					queueOp('create_partition', params, 'Create partition on ' + dev + ' [' + start + 's..' + end + 's]', partPreview);
					showToast(t('tQueued') + ' ×2 (' + _savedTableType.toUpperCase() + ' table + partition)', 'info', 6000);
				});
			return;
		}
		queueOpWithConfirm(
			'create_partition',
			params,
			'Create partition on ' + dev + ' [' + start + 's..' + end + 's] (with form Role/Filesystem/Name)',
			t('confirmCreate'),
			t('confirmCreateMsg')
		);
	}

	function queueCreatePartitionBasic() {
		var dev = state.selectedDevice;
		if (dev === null || dev === '') {
			showToast(t('tNoDevice'), 'warn');
			return;
		}
		var start = document.getElementById('newStartSector').value.trim();
		var end = document.getElementById('newEndSector').value.trim();
		if (start === '' || end === '') {
			showToast(t('tNeedStartEnd'), 'warn');
			return;
		}
		var aligned = alignSectors(start, end, document.getElementById('pnpAlign') || document.getElementById('newPartAlign'));
		start = aligned.start; end = aligned.end;
		queueOpWithConfirm(
			'create_partition',
			{ device: dev, start_sector: start, end_sector: end, part_role: 'primary', fs_hint: '', part_name: '' },
			'Create partition on ' + dev + ' [' + start + 's..' + end + 's] (quick mode)',
			t('confirmCreate'),
			t('confirmCreateMsg')
		);
	}

	function queueDeletePartition() {
		if (!state.selectedPart||!state.selectedPart.number){
			showToast(t('tNoPartition'), 'warn');
			return;
		}
		queueDeletePartitionWithConfirm(state.selectedDevice, state.selectedPart);
	}

	function dmUpdateMethodFields() {
		var method = document.getElementById('dmMethod');
		var logDiv  = document.getElementById('dmLogicalFields');
		var physDiv = document.getElementById('dmPhysicalFields');
		if (!method || !logDiv || !physDiv) return;
		var isPhys = method.value === 'physical';
		logDiv.style.display  = isPhys ? 'none' : 'contents';
		physDiv.style.display = isPhys ? 'contents' : 'none';
	}

	function populateDiskTargetDropdown(srcDevPath) {
		var sel = document.getElementById('dmTargetDevice');
		if (!sel) return;
		sel.innerHTML = '';
		var srcDev = null;
		var srcUsed = 0;
		for (var di = 0; di < (state.devices || []).length; di++) {
			var dv = state.devices[di];
			if (dv && dv.path === srcDevPath) {
				srcDev = dv;
				for (var pi = 0; pi < (dv.partitions || []).length; pi++) {
					var pp = dv.partitions[pi];
					if (pp && pp.kind === 'partition' && Number(pp.end || 0) > srcUsed) {
						srcUsed = Number(pp.end || 0);
					}
				}
				break;
			}
		}
		var added = 0;
		for (var di2 = 0; di2 < (state.devices || []).length; di2++) {
			var dv2 = state.devices[di2];
			if (!dv2 || !dv2.path || dv2.path === srcDevPath) continue;
			var totalSectors = Number(dv2.sectors || dv2.size || 0);
			if (srcUsed > 0 && totalSectors > 0 && totalSectors < srcUsed) continue;
			var opt = document.createElement('option');
			opt.value = dv2.path;
			var sizeStr = dv2.humanSize || (totalSectors ? (Math.round(totalSectors * 512 / 1073741824) + ' GiB') : '');
			opt.textContent = dv2.path + (sizeStr ? '  (' + sizeStr + ')' : '') + (dv2.model ? '  ' + dv2.model : '');
			sel.appendChild(opt);
			added++;
		}
		if (added === 0) {
			var none = document.createElement('option');
			none.value = '';
			none.textContent = '— no suitable target disk found —';
			sel.appendChild(none);
		}
	}

	function showDiskMoveCloneModal(srcDevArg) {
		var srcDev = srcDevArg || state.selectedDevice;
		if (!srcDev || !srcDev.path) { showToast(t('tNoDevice'), 'warn'); return; }

		var modal  = document.getElementById('pcgiDiskMoveCloneModal');
		if (!modal) { showToast('Disk move/clone modal not found', 'error'); return; }

		// Populate source dropdown
		var srcSel = document.getElementById('dmSourceDevice');
		if (srcSel) {
			srcSel.innerHTML = '';
			for (var di = 0; di < (state.devices || []).length; di++) {
				var dv = state.devices[di];
				if (!dv || !dv.path) continue;
				var opt = document.createElement('option');
				opt.value = dv.path;
				var sizeStr = dv.humanSize || '';
				opt.textContent = dv.path + (sizeStr ? '  (' + sizeStr + ')' : '') + (dv.model ? '  ' + dv.model : '');
				if (dv.path === srcDev.path) opt.selected = true;
				srcSel.appendChild(opt);
			}
			srcSel.onchange = function () { populateDiskTargetDropdown(srcSel.value); };
		}

		populateDiskTargetDropdown(srcDev.path);
		dmUpdateMethodFields();

		// Reset some fields
		var delayEl = document.getElementById('dmStepDelay');
		if (delayEl && !delayEl.value) delayEl.value = '1';

		// Wire cancel
		var cancelBtn = document.getElementById('pcgiDmCancelBtn');
		if (cancelBtn) cancelBtn.onclick = function () { modal.style.display = 'none'; };

		// Wire OK
		var okBtn = document.getElementById('pcgiDmOkBtn');
		if (okBtn) okBtn.onclick = function () {
			var src    = (document.getElementById('dmSourceDevice') || {}).value || '';
			var tgt    = (document.getElementById('dmTargetDevice') || {}).value || '';
			var method = (document.getElementById('dmMethod')       || {}).value || 'smart';
			var mode   = (document.getElementById('dmMode')         || {}).value || 'clone';
			var align  = (document.getElementById('dmAlign')        || {}).value || '1048576';
			var copyMbr  = (document.getElementById('dmCopyMbr')    || {}).value || 'yes';
			var wipe     = (document.getElementById('dmWipeTarget') || {}).value || 'yes';
			var verify   = (document.getElementById('dmVerify')     || {}).value || 'no';
			var forceFs  = (document.getElementById('dmForceFs')    || {}).value || '';
			var xtra     = (document.getElementById('dmExtraOpts')  || {}).value || '';
			var incTail  = (document.getElementById('dmIncludeTail')|| {}).value || 'no';
			var unmount  = (document.getElementById('dmUnmount')    || {}).value || 'yes';
			var delay    = (document.getElementById('dmStepDelay')  || {}).value || '1';

			if (!src || !tgt) { showToast(t('tNoDevice'), 'warn'); return; }
			if (src === tgt)  { showToast('Source and target disk must be different.', 'warn'); return; }

			var isPhys   = method === 'physical';
			var isMove   = mode   === 'move';
			var params = {
				source_device:  src,
				target_device:  tgt,
				move_mode:      isMove  ? 'yes' : 'no',
				physical_mode:  isPhys  ? 'yes' : 'no',
				include_tail:   isPhys  ? incTail : 'no',
				clone_mode:     isPhys  ? 'smart' : method,
				align_bytes:    isPhys  ? '4096'  : align,
				copy_mbr:       isPhys  ? 'no'    : copyMbr,
				wipe_target:    isPhys  ? 'no'    : wipe,
				unmount_before: unmount,
				verify_clone:   isPhys  ? 'no'    : verify,
				force_fs:       isPhys  ? ''      : forceFs,
				extra_opts:     isPhys  ? ''      : xtra,
				step_delay:     delay
			};

			var op = isMove ? 'move' : 'clone';
			var label = op + ' disk ' + src + ' → ' + tgt;
			modal.style.display = 'none';

			showCommandPreviewModal(
				'disk_migration',
				params,
				label,
				t('confirmDiskClone') || 'Confirm disk clone/move',
				t('confirmDiskCloneMsg') || 'Clone all partitions from source disk to target disk?'
			).then(function (previewText) {
				if (previewText === null) return;
				queueOp('disk_migration', params, label, previewText, false);
				showToast(t('tDiskMigrationQueued') || 'Disk migration added.', 'success');
			});
		};

		modal.style.display = 'flex';
	}

	// ── Helpers for partclone / ddrescue modals ────────────────────────────────

	function _piGetPartitionPath(partOrDevice, modeType) {
		if (!partOrDevice) return '';
		if (modeType === 'disk') {
			return String(partOrDevice.path || '');
		}
		return String(partOrDevice.path || '');
	}

	function _piSetupModal(modalId, titleKey, titleDefault, sourceLabelId, sourceValue, cancelBtnId, okBtnId, onOk) {
		var modal = document.getElementById(modalId);
		if (!modal) return;
		var titleEl = modal.querySelector('.pcgi-modal-head');
		if (titleEl) titleEl.textContent = t(titleKey) || titleDefault;
		var srcEl = document.getElementById(sourceLabelId);
		if (srcEl) srcEl.value = sourceValue;
		var cancelBtn = document.getElementById(cancelBtnId);
		var okBtn = document.getElementById(okBtnId);
		function close() { modal.style.display = 'none'; document.removeEventListener('keydown', onEsc); }
		function onEsc(ev) { if (ev.key === 'Escape') close(); }
		if (cancelBtn) cancelBtn.onclick = close;
		modal.onclick = function(ev) { if (ev.target === modal) close(); };
		document.addEventListener('keydown', onEsc);
		if (okBtn) okBtn.onclick = function() { close(); onOk(); };
		modal.style.display = 'flex';
		// Sync i18n labels
		modal.querySelectorAll('[id^="i18nPi"], [id^="i18nDr"]').forEach(function(el) {
			var key = el.id.replace(/^i18n/, '').replace(/Label$/, '');
			key = key.charAt(0).toLowerCase() + key.slice(1) + 'Label';
			var translated = t(key);
			if (translated && translated !== key) {
				// preserve help buttons
				var btn = el.querySelector('.pcgi-help-btn');
				el.childNodes.forEach(function(n) { if (n.nodeType === 3) n.textContent = ''; });
				if (!btn) { el.textContent = translated; } else {
					el.textContent = translated;
					el.appendChild(btn);
				}
			}
		});
	}

	function showPartcloneExportModal(partOrDevice, modeType) {
		var devPath = _piGetPartitionPath(partOrDevice, modeType);
		if (!devPath) { showToast(t('tNoPartition'), 'warn'); return; }
		var modal = document.getElementById('pcgiPartcloneExportModal');
		if (!modal) return;
		var titleEl = modal.querySelector('.pcgi-modal-head');
		if (titleEl) titleEl.textContent = t('piExpTitle') || 'Export partition/disk to image';
		document.getElementById('piExpSource').value = devPath;
		document.getElementById('piExpOutput').value = '';
		document.getElementById('piExpCompress').value = 'none';
		document.getElementById('piExpForceFs').value = '';
		document.getElementById('piExpVerify').value = 'no';
		document.getElementById('piExpUnmount').value = (partOrDevice && partOrDevice.mountpoint && String(partOrDevice.mountpoint).trim() && String(partOrDevice.mountpoint).trim() !== '-') ? 'yes' : 'no';
		document.getElementById('piExpUseDd').value = 'no';
		document.getElementById('piExpStepDelay').value = '1';
		document.getElementById('piExpExtraOpts').value = '';

		var cancelBtn = document.getElementById('pcgiPiExpCancelBtn');
		var okBtn = document.getElementById('pcgiPiExpOkBtn');
		function close() { modal.style.display = 'none'; document.removeEventListener('keydown', onEsc); }
		function onEsc(ev) { if (ev.key === 'Escape') close(); }
		document.addEventListener('keydown', onEsc);
		if (cancelBtn) cancelBtn.onclick = close;
		modal.onclick = function(ev) { if (ev.target === modal) close(); };

		if (okBtn) okBtn.onclick = function() {
			var output = document.getElementById('piExpOutput').value.trim();
			if (!output) { showToast('Output image file path required.', 'warn'); return; }
			close();
			var params = {
				partition: devPath,
				output_file: output,
				compression: document.getElementById('piExpCompress').value,
				force_fs: document.getElementById('piExpForceFs').value.trim(),
				verify: document.getElementById('piExpVerify').value,
				unmount_before: document.getElementById('piExpUnmount').value,
				use_dd: document.getElementById('piExpUseDd').value,
				step_delay: document.getElementById('piExpStepDelay').value
			};
			var xtra = document.getElementById('piExpExtraOpts').value.trim();
			if (xtra) params.extra_opts = xtra;
			var label = 'export ' + devPath + ' → ' + output;
			showCommandPreviewModal('partclone_export', params, label,
				t('confirmPiExp') || 'Confirm image export',
				t('confirmPiExpMsg') || 'Export partition to image file?'
			).then(function(previewText) {
				if (previewText === null) return;
				dispatchAjaxAction('partclone_export', params, label);
			});
		};

		modal.style.display = 'flex';
	}

	function showPartcloneImportModal(partOrDevice, modeType) {
		var devPath = _piGetPartitionPath(partOrDevice, modeType);
		if (!devPath) { showToast(t('tNoPartition'), 'warn'); return; }
		var modal = document.getElementById('pcgiPartcloneImportModal');
		if (!modal) return;
		var titleEl = modal.querySelector('.pcgi-modal-head');
		if (titleEl) titleEl.textContent = t('piImpTitle') || 'Restore partition/disk from image';
		document.getElementById('piImpTarget').value = devPath;
		document.getElementById('piImpInput').value = '';
		document.getElementById('piImpCompress').value = 'none';
		document.getElementById('piImpVerify').value = 'no';
		document.getElementById('piImpUnmount').value = (partOrDevice && partOrDevice.mountpoint && String(partOrDevice.mountpoint).trim() && String(partOrDevice.mountpoint).trim() !== '-') ? 'yes' : 'no';
		document.getElementById('piImpStepDelay').value = '1';
		document.getElementById('piImpExtraOpts').value = '';

		var cancelBtn = document.getElementById('pcgiPiImpCancelBtn');
		var okBtn = document.getElementById('pcgiPiImpOkBtn');
		function close() { modal.style.display = 'none'; document.removeEventListener('keydown', onEsc); }
		function onEsc(ev) { if (ev.key === 'Escape') close(); }
		document.addEventListener('keydown', onEsc);
		if (cancelBtn) cancelBtn.onclick = close;
		modal.onclick = function(ev) { if (ev.target === modal) close(); };

		if (okBtn) okBtn.onclick = function() {
			var input = document.getElementById('piImpInput').value.trim();
			if (!input) { showToast('Input image file path required.', 'warn'); return; }
			close();
			var params = {
				partition: devPath,
				input_file: input,
				compression: document.getElementById('piImpCompress').value,
				verify: document.getElementById('piImpVerify').value,
				unmount_before: document.getElementById('piImpUnmount').value,
				step_delay: document.getElementById('piImpStepDelay').value
			};
			var xtra = document.getElementById('piImpExtraOpts').value.trim();
			if (xtra) params.extra_opts = xtra;
			var label = 'restore ' + input + ' → ' + devPath;
			showCommandPreviewModal('partclone_import', params, label,
				t('confirmPiImp') || 'Confirm image restore',
				t('confirmPiImpMsg') || 'Restore partition from image? DATA WILL BE OVERWRITTEN.'
			).then(function(previewText) {
				if (previewText === null) return;
				dispatchAjaxAction('partclone_import', params, label);
			});
		};

		modal.style.display = 'flex';
	}

	function showPartcloneNetSendModal(part) {
		var devPath = part ? String(part.path || '') : '';
		if (!devPath) { showToast(t('tNoPartition'), 'warn'); return; }
		var modal = document.getElementById('pcgiPartcloneNetSendModal');
		if (!modal) return;
		var titleEl = modal.querySelector('.pcgi-modal-head');
		if (titleEl) titleEl.textContent = t('piNsTitle') || 'Send partition over network';
		document.getElementById('piNsSource').value = devPath;
		document.getElementById('piNsTransport').value = 'unicast';
		document.getElementById('piNsHost').value = '';
		document.getElementById('piNsPort').value = '9000';
		document.getElementById('piNsCompress').value = 'none';
		document.getElementById('piNsForceFs').value = '';
			document.getElementById('piNsUnmount').value = (part && part.mountpoint && String(part.mountpoint).trim() && String(part.mountpoint).trim() !== '-') ? 'yes' : 'no';

		var cancelBtn = document.getElementById('pcgiPiNsCancelBtn');
		var okBtn = document.getElementById('pcgiPiNsOkBtn');
		function close() { modal.style.display = 'none'; document.removeEventListener('keydown', onEsc); }
		function onEsc(ev) { if (ev.key === 'Escape') close(); }
		document.addEventListener('keydown', onEsc);
		if (cancelBtn) cancelBtn.onclick = close;
		modal.onclick = function(ev) { if (ev.target === modal) close(); };

		if (okBtn) okBtn.onclick = function() {
			close();
			var params = {
				partition: devPath,
				transport: document.getElementById('piNsTransport').value,
				net_host: document.getElementById('piNsHost').value.trim(),
				net_port: document.getElementById('piNsPort').value || '9000',
				compression: document.getElementById('piNsCompress').value,
				force_fs: document.getElementById('piNsForceFs').value.trim(),
				unmount_before: document.getElementById('piNsUnmount').value,
				multicast: document.getElementById('piNsTransport').value === 'multicast' ? 'yes' : 'no',
				step_delay: document.getElementById('piNsStepDelay').value
			};
			var label = 'net-send ' + devPath + ' → :' + params.net_port;
			showCommandPreviewModal('partclone_net_send', params, label,
				t('confirmNsSend') || 'Confirm network send',
				t('confirmNsSendMsg') || 'Send partition over network?'
			).then(function(previewText) {
				if (previewText === null) return;
				dispatchAjaxAction('partclone_net_send', params, label);
			});
		};

		modal.style.display = 'flex';
	}

	function showPartcloneNetRecvModal(part) {
		var devPath = part ? String(part.path || '') : '';
		if (!devPath) { showToast(t('tNoPartition'), 'warn'); return; }
		var modal = document.getElementById('pcgiPartcloneNetRecvModal');
		if (!modal) return;
		var titleEl = modal.querySelector('.pcgi-modal-head');
		if (titleEl) titleEl.textContent = t('piNrTitle') || 'Receive partition from network';
		document.getElementById('piNrTarget').value = devPath;
		document.getElementById('piNrTransport').value = 'unicast';
		document.getElementById('piNrHost').value = '';
		document.getElementById('piNrPort').value = '9000';
		document.getElementById('piNrCompress').value = 'none';
		document.getElementById('piNrVerify').value = 'no';
			document.getElementById('piNrUnmount').value = (part && part.mountpoint && String(part.mountpoint).trim() && String(part.mountpoint).trim() !== '-') ? 'yes' : 'no';

		var cancelBtn = document.getElementById('pcgiPiNrCancelBtn');
		var okBtn = document.getElementById('pcgiPiNrOkBtn');
		function close() { modal.style.display = 'none'; document.removeEventListener('keydown', onEsc); }
		function onEsc(ev) { if (ev.key === 'Escape') close(); }
		document.addEventListener('keydown', onEsc);
		if (cancelBtn) cancelBtn.onclick = close;
		modal.onclick = function(ev) { if (ev.target === modal) close(); };

		if (okBtn) okBtn.onclick = function() {
			var host = document.getElementById('piNrHost').value.trim();
			if (!host) { showToast('Source host IP required.', 'warn'); return; }
			close();
			var params = {
				partition: devPath,
				transport: document.getElementById('piNrTransport').value,
				net_host: host,
				net_port: document.getElementById('piNrPort').value || '9000',
				compression: document.getElementById('piNrCompress').value,
				verify: document.getElementById('piNrVerify').value,
				unmount_before: document.getElementById('piNrUnmount').value,
				multicast: document.getElementById('piNrTransport').value === 'multicast' ? 'yes' : 'no',
				step_delay: document.getElementById('piNrStepDelay').value
			};
			var label = 'net-recv ' + host + ':' + params.net_port + ' → ' + devPath;
			showCommandPreviewModal('partclone_net_recv', params, label,
				t('confirmNrRecv') || 'Confirm network receive',
				t('confirmNrRecvMsg') || 'Receive and restore partition from network? DATA OVERWRITTEN.'
			).then(function(previewText) {
				if (previewText === null) return;
				dispatchAjaxAction('partclone_net_recv', params, label);
			});
		};

		modal.style.display = 'flex';
	}

	function showDdrescueModal(partOrDevice, modeType) {
		var devPath = _piGetPartitionPath(partOrDevice, modeType);
		if (!devPath) { showToast(t('tNoPartition'), 'warn'); return; }
		var modal = document.getElementById('pcgiDdrescueModal');
		if (!modal) return;
		var titleEl = modal.querySelector('.pcgi-modal-head');
		if (titleEl) titleEl.textContent = t('drTitle') || 'Clone with ddrescue (data recovery)';
		document.getElementById('drSource').value = devPath;
		document.getElementById('drOutput').value = '';
		document.getElementById('drLogFile').value = '';
		document.getElementById('drRetries').value = '3';
		document.getElementById('drUnmount').value = 'yes';
		document.getElementById('drStepDelay').value = '1';
		document.getElementById('drExtraOpts').value = '';

		var cancelBtn = document.getElementById('pcgiDrCancelBtn');
		var okBtn = document.getElementById('pcgiDrOkBtn');
		function close() { modal.style.display = 'none'; document.removeEventListener('keydown', onEsc); }
		function onEsc(ev) { if (ev.key === 'Escape') close(); }
		document.addEventListener('keydown', onEsc);
		if (cancelBtn) cancelBtn.onclick = close;
		modal.onclick = function(ev) { if (ev.target === modal) close(); };

		if (okBtn) okBtn.onclick = function() {
			var output = document.getElementById('drOutput').value.trim();
			if (!output) { showToast('Output image file path required.', 'warn'); return; }
			close();
			var params = {
				partition: devPath,
				output_file: output,
				log_file: document.getElementById('drLogFile').value.trim(),
				retries: document.getElementById('drRetries').value || '3',
				unmount_before: document.getElementById('drUnmount').value,
				step_delay: document.getElementById('drStepDelay').value
			};
			var xtra = document.getElementById('drExtraOpts').value.trim();
			if (xtra) params.extra_opts = xtra;
			var label = 'ddrescue ' + devPath + ' → ' + output;
			showCommandPreviewModal('partclone_ddrescue', params, label,
				t('confirmDr') || 'Confirm ddrescue',
				t('confirmDrMsg') || 'Run ddrescue clone to image file?'
			).then(function(previewText) {
				if (previewText === null) return;
				dispatchAjaxAction('partclone_ddrescue', params, label);
			});
		};

		modal.style.display = 'flex';
	}

	// piNsUpdateHostField: show/hide host label based on multicast mode
	function piNsUpdateHostField() {
		// unicast: show host (target IP), multicast: show multicast group
		// Both use the same field, just update its placeholder via title bar
	}

	function dispatchAjaxAction(action, params, label) {
		var ack = document.getElementById('ackToken').value.trim();
		if (!state.dryRun && ack !== 'YES_I_UNDERSTAND') {
			showToast(t('tNeedAck'), 'warn');
			return;
		}
		params.ack = ack;
		appendAnsi('cmdOutput', '\n\x1b[1;34m\u25b6 Running: ' + label + ' ...\x1b[0m\n');
		callApiStreaming(action, params, 'cmdOutput', 0, 1, label)
			.then(function (res) {
				var msg = (res && res.message) ? res.message : JSON.stringify(res);
				if (res && res.success) {
					appendAnsi('cmdOutput', '\x1b[1;32m\u2714 ' + msg + '\x1b[0m\n');
					showToast(t('tDone') + ': ' + label, 'success', 10000);
				} else {
					appendAnsi('cmdOutput', '\x1b[1;31m\u2718 ' + msg + '\x1b[0m\n');
					showToast(t('tError') + ': ' + msg, 'error', 10000);
				}
				refreshDevices();
			})
			.catch(function (err) {
				appendTo('cmdOutput', '\u2718 Network error: ' + err.message + '\n');
				showToast('Network error: ' + err.message, 'error');
			});
	}

	function queueDeleteAllPartitions(devArg) {
		var baseDev = devArg || getSelectedDeviceData();
		if (!baseDev || !baseDev.path) {
			showToast(t('tNoDevice'), 'warn');
			return;
		}

		var previewDev = buildPreviewDevice(baseDev);
		var parts = [];
		for (var i = 0; i < (previewDev.partitions || []).length; i++) {
			var p = previewDev.partitions[i];
			if (p && p.kind === 'partition' && Number(p.number || 0) > 0) {
				parts.push(p);
			}
		}

		if (!parts.length) {
			showToast('No partitions to delete on ' + baseDev.path + '.', 'warn');
			return;
		}

		showConfirmModal(t('confirmDelete'), 'Delete ALL partitions on ' + baseDev.path + '?')
			.then(function (ok) {
				if (!ok) return;
				parts.sort(function (a, b) {
					return Number(b.number || 0) - Number(a.number || 0);
				});

				for (var j = 0; j < parts.length; j++) {
					var params = { device: baseDev.path, partnum: parts[j].number };
					enqueueDeletePartitionOps(baseDev.path, parts[j], buildCommandPreview('delete_partition', params), true);
				}
				showToast('Queued delete-all partitions on ' + baseDev.path + '.', 'warn', 10000);
			});
	}

	function queueResizePartitionFromInputs() {
		var partnum = document.getElementById('selectedPartNum').value.trim();
		var endSector = document.getElementById('resizeEndSector').value.trim();
		if (!partnum || !endSector) {
			showToast(t('tNeedResizeInput'), 'warn');
			return;
		}

		var dev = getSelectedDeviceData();
		if (!dev) {
			showToast(t('tNoDevice'), 'warn');
			return;
		}
		var part = findPartitionInDeviceByNumber(dev, partnum);
		if (!part) {
			showToast(t('tNoPartition'), 'warn');
			return;
		}

		queueResizePlan(dev, part, Number(endSector), document.getElementById('resizeFsSelect').value);
	}

	function queueMkfs() {
		showMkfsModal();
	}

	function queueSetLabel() {
		var part = document.getElementById('fsPartitionPath').value.trim();
		var label = document.getElementById('fsLabelInput').value.trim();
		if (!part || !label) {
			showToast(t('tNeedLabel'), 'warn');
			return;
		}
		queueOpWithConfirm(
			'set_label',
			{ partition: part, fs_type: document.getElementById('fsTypeSelect').value, label: label },
			'Set filesystem label on ' + part,
			t('confirmAction'),
			'Filesystem label update will be added.'
		);
	}

	function queueRenamePartition() {
		var name = document.getElementById('renamePartInput').value.trim();
		var partnum = document.getElementById('selectedPartNum').value.trim();
		if (!partnum || !name) {
			showToast(t('tNeedPartName'), 'warn');
			return;
		}
		queueOpWithConfirm(
			'set_partition_name',
			{ device: state.selectedDevice, partnum: partnum, part_name: name },
			'Set partition name p' + partnum + ' on ' + state.selectedDevice,
			t('confirmAction'),
			'Partition name update will be added.'
		);
	}

	function queueSetFlag() {
		var partnum = document.getElementById('selectedPartNum').value.trim();
		var flagName = document.getElementById('flagNameInput').value.trim();
		if (!partnum || !flagName) {
			showToast(t('tNeedFlag'), 'warn');
			return;
		}
		queueOpWithConfirm(
			'set_partition_flag',
			{
				device: state.selectedDevice,
				partnum: partnum,
				flag: flagName,
				state: document.getElementById('flagStateInput').value
			},
			'Set partition flag ' + flagName + ' on p' + partnum,
			t('confirmAction'),
			'Partition flag update will be added.'
		);
	}

	function showMountModal() {
		var part = state.selectedPart;
		var partPath = part ? String(part.path || '') : document.getElementById('fsPartitionPath').value.trim();
		if (!partPath) {
			showToast(t('tNeedPartPath'), 'warn');
			return;
		}

		// Pre-compute default mountpoint: prefer label, then partition name, then basename
		var defLabel = part ? (part.label || part.name || '') : '';
		defLabel = defLabel.replace(/[^a-zA-Z0-9_\-.]/g, '_');
		if (!defLabel) defLabel = partPath.replace(/.*\//, '');
		var defMp = '/var/media/ftp/' + defLabel;

		// Pre-fill fs type from partition info
		var defFs = part ? (String(part.fs || '').toLowerCase().trim() || 'auto') : 'auto';
		// Normalise to option values in the select
		if (defFs === 'fat' || defFs === 'fat32' || defFs === 'fat16' || defFs === 'fat12') defFs = 'vfat';

		var modal     = document.getElementById('pcgiMountModal');
		var partEl    = document.getElementById('mountModalPart');
		var mpEl      = document.getElementById('mountModalMp');
		var fsEl      = document.getElementById('mountModalFs');
		var optsEl    = document.getElementById('mountModalOpts');
		var cancelBtn = document.getElementById('pcgiMountCancelBtn');
		var okBtn     = document.getElementById('pcgiMountOkBtn');
		if (!modal) { queueMountPartition(); return; }

		partEl.value  = partPath;
		mpEl.value    = defMp;
		optsEl.value  = '';
		// Select matching fs option, fallback to auto
		var matched = false;
		for (var oi = 0; oi < fsEl.options.length; oi++) {
			if (fsEl.options[oi].value === defFs) { fsEl.selectedIndex = oi; matched = true; break; }
		}
		if (!matched) fsEl.value = 'auto';

		modal.style.display = 'flex';
		modal.setAttribute('aria-hidden', 'false');

		function cleanup() {
			modal.style.display = 'none';
			modal.setAttribute('aria-hidden', 'true');
			cancelBtn.onclick = okBtn.onclick = null;
			document.removeEventListener('keydown', onEsc);
		}
		function onEsc(ev) { if (ev.key === 'Escape') cleanup(); }
		document.addEventListener('keydown', onEsc);
		cancelBtn.onclick = cleanup;

		okBtn.onclick = function () {
			var pth  = partEl.value.trim();
			var mp   = mpEl.value.trim();
			var fs   = fsEl.value;
			var opts = optsEl.value.trim();
			cleanup();
			if (!pth) { showToast(t('tNeedPartPath'), 'warn'); return; }
			queueOpWithConfirm(
				'mount_partition',
				{ partition: pth, mountpoint: mp, fs_type: fs, mount_opts: opts },
				'Mount ' + pth + (mp ? (' \u2192 ' + mp) : ''),
				t('confirmMount'),
				t('confirmMountMsg')
			);
		};
	}

	function queueMountPartition() {
		var part = document.getElementById('fsPartitionPath').value.trim();
		if (!part) {
			showToast(t('tNeedPartPath'), 'warn');
			return;
		}
		var mountpoint = document.getElementById('mountpointInput').value.trim();
		var opts = document.getElementById('mountOptsInput').value.trim();
		queueOpWithConfirm(
			'mount_partition',
			{ partition: part, mountpoint: mountpoint, fs_type: document.getElementById('fsTypeSelect').value, mount_opts: opts },
			'Mount ' + part + (mountpoint ? (' on ' + mountpoint) : ''),
			t('confirmMount'),
			t('confirmMountMsg')
		);
	}

	function queueUnmountPartition() {
		var part = document.getElementById('fsPartitionPath').value.trim();
		var mountpoint = document.getElementById('mountpointInput').value.trim();
		if (!part && !mountpoint) {
			showToast(t('tNeedPartPath'), 'warn');
			return;
		}
		queueOpWithConfirm(
			'unmount_partition',
			{ partition: part, mountpoint: mountpoint },
			'Unmount ' + (part || mountpoint),
			t('confirmUnmount'),
			t('confirmUnmountMsg')
		);
	}

	function resolveFsTypeForCheck(partitionPath, requestedType) {
		var req = String(requestedType || '').toLowerCase();
		if (req && req !== 'auto') return req;

		if (state.selectedPart && String(state.selectedPart.path || '') === String(partitionPath || '') && state.selectedPart.fs) {
			return String(state.selectedPart.fs).toLowerCase();
		}

		var dev = getSelectedDeviceData();
		if (dev && dev.partitions) {
			for (var i = 0; i < dev.partitions.length; i++) {
				var p = dev.partitions[i];
				if (p && p.kind === 'partition' && String(p.path || '') === String(partitionPath || '') && p.fs) {
					return String(p.fs).toLowerCase();
				}
			}
		}

		return req || 'auto';
	}

	function runFsck(repair) {
		var part = document.getElementById('fsPartitionPath').value.trim();
		if (!part) {
			showToast(t('tNeedPartPath'), 'warn');
			return;
		}

		var reqFs = document.getElementById('fsTypeSelect').value;
		var resolvedFs = resolveFsTypeForCheck(part, reqFs);
		var extra = document.getElementById('extraOptsInput').value.trim();
		var mode = repair ? 'yes' : 'no';

		queueOpWithConfirm(
			'check_filesystem',
			{ partition: part, fs_type: resolvedFs, repair: mode, extra_opts: extra },
			(repair ? 'Check/repair' : 'Check (read-only)') + ' filesystem on ' + part + ' [' + resolvedFs + ']',
			repair ? t('confirmRepair') : t('confirmAction'),
			repair ? t('confirmRepairMsg') : 'Filesystem check will be added.'
		);
	}

	function clearQueue() {
		state.queue = [];
		state.queueResolvedTargets = {};
		renderQueue();
		syncSelectionWithPreview();
		renderMap();
	}

	function queueTargetKey(device, startSector, endSector) {
		var d = String(device || '').trim();
		var s = String(startSector || '').trim();
		var e = String(endSector || '').trim();
		if (!d || !s || !e) return '';
		return d + '|' + s + '|' + e;
	}

	function queueRememberResolvedTarget(opParams, res) {
		if (!res) return;
		var dev = String(res.target_device || opParams.target_device || opParams.device || '').trim();
		var start = String(res.target_start_sector || opParams.target_start_sector || opParams.start_sector || '').trim();
		var end = String(res.target_end_sector || opParams.target_end_sector || opParams.end_sector || '').trim();
		var key = queueTargetKey(dev, start, end);
		if (!key) return;

		var partnum = String(res.target_partnum || '').trim();
		var partition = String(res.target_partition || '').trim();
		if (!partnum && !partition) return;

		var cur = state.queueResolvedTargets[key] || {};
		if (partnum) cur.target_partnum = partnum;
		if (partition) cur.target_partition = partition;
		state.queueResolvedTargets[key] = cur;
	}

	function queueInjectResolvedTarget(params) {
		if (!params) return;
		var dev = String(params.target_device || params.device || '').trim();
		var start = String(params.target_start_sector || params.start_sector || '').trim();
		var end = String(params.target_end_sector || params.end_sector || '').trim();
		var key = queueTargetKey(dev, start, end);
		if (!key) return;
		var cur = state.queueResolvedTargets[key];
		if (!cur) return;

		if ((params.target_partnum === undefined || params.target_partnum === null || String(params.target_partnum).trim() === '') && cur.target_partnum) {
			params.target_partnum = cur.target_partnum;
		}
		if ((params.partition === undefined || params.partition === null || String(params.partition).trim() === '') && cur.target_partition) {
			params.partition = cur.target_partition;
		}
	}

	function applyQueue() {
		if (!state.queue.length) {
			showToast(t('tQueueEmpty'), 'warn');
			return;
		}
		if (state.toolStatus && state.toolStatus.requiredMissing && state.toolStatus.requiredMissing.length > 0) {
			showToast('Cannot apply queue. Required command(s) missing: ' + state.toolStatus.requiredMissing.join(', '), 'error', 4200);
			return;
		}
		var ack = document.getElementById('ackToken').value.trim();
		if (!state.dryRun && ack !== 'YES_I_UNDERSTAND') {
			showToast(t('tNeedAck'), 'warn');
			return;
		}

		showConfirmModal(t('confirmQueueApply'), t('confirmQueueApplyMsg')).then(function (ok) {
			if (!ok) return;
			state.queueResolvedTargets = {};
			document.getElementById('applyQueueBtn').disabled = true;
			var totalOps = state.queue.length;
			var _now = new Date();
			var _ts = _now.getFullYear() + '-' + String(_now.getMonth()+1).padStart(2,'0') + '-' + String(_now.getDate()).padStart(2,'0')
					+ ' ' + String(_now.getHours()).padStart(2,'0') + ':' + String(_now.getMinutes()).padStart(2,'0') + ':' + String(_now.getSeconds()).padStart(2,'0');
			var _header = '\x1b[1;34m' + _ts + '\x1b[0m  ';
			appendAnsi('cmdOutput', _header + '\x1b[1m' + tf('tQueueApplying', totalOps) + '\x1b[0m\n');

			var i = 0;
			function runNext() {
				if (i >= state.queue.length) {
					appendAnsi('cmdOutput', '\n\x1b[1;32m\u2714 ' + tf('tQueueAllDone', totalOps) + '\x1b[0m\n');
					showToast(t('tQueueApplied'), 'success', 10000);
					state.queue = [];
					renderQueue();
					document.getElementById('applyQueueBtn').disabled = false;
					refreshDevices();
					return;
				}
				var op = state.queue[i];
				var params = {};
				for (var k in op.params) {
					if (Object.prototype.hasOwnProperty.call(op.params, k)) params[k] = op.params[k];
				}
				queueInjectResolvedTarget(params);
				params.ack = ack;
				if (op.commandPreview) {
					params.command_preview = op.commandPreview;
				}
				if (op.action === "resize_partition" || op.action === "resize_filesystem" || op.action === "move_partition" || op.action === "clone_partition_dd") {
					appendAnsi('cmdOutput', '\x1b[1;33m\u26a0 ' + t('tQueueDiskWarning') + '\x1b[0m\n');
				}

				callApiStreaming(op.action, params, 'cmdOutput', i, state.queue.length, op.label || op.action)
					.then(function (res) {
						var stepSuccess = !!res.success;
						if (!stepSuccess && op.action === 'check_filesystem' && Number(res.rc) === 1) {
							stepSuccess = true;
							if (!res.message || res.message === 'Filesystem check reported errors') {
								res.message = 'Filesystem check completed';
							}
						}
						appendAnsi('cmdOutput', '\n' + (stepSuccess ? '\x1b[1;32m\u2500\u2500 \u2714 ' : '\x1b[1;31m\u2500\u2500 \u2718 ') + (res.message || op.action) + ' (rc=' + (res.rc || 0) + ')\x1b[0m\n');
						if (!stepSuccess) {
							appendAnsi('cmdOutput', '\x1b[1;31m\u2718 ' + tf('tQueueStoppedAt', i + 1) + '\x1b[0m\n');
							showToast(tf('tQueueStoppedAt', i + 1), 'error', 10000);
							document.getElementById('applyQueueBtn').disabled = false;
							return;
						}
						queueRememberResolvedTarget(params, res);
						i++;
						runNext();
					})
					.catch(function (err) {
						appendAnsi('cmdOutput', '\x1b[1;31m\u2718 ' + tf('tQueueErrorAt', i + 1, err.message) + '\x1b[0m\n');
						showToast(tf('tQueueErrorAt', i + 1, err.message), 'error', 10000);
						document.getElementById('applyQueueBtn').disabled = false;
					});
			}

			runNext();
		});
	}

	function runDiagnostics(action) {
		var dev = state.selectedDevice;
		if (! dev) {
			showToast(t('tNoDevice'), 'warn');
			return;
		}
		var diagEl = document.getElementById('diagOutput');
		if (diagEl) {
			diagEl.textContent = '\u2026';
			diagEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
		}
		paceHourglassStart();
		callApi(action, { device: dev })
			.then(function (res) {
				var msg = '[' + action + '] ' + (res.message || '') +
				          '\nrc=' + (res.rc || 0) + '\n' + (res.output || '');
				logTo('diagOutput', msg, true);
				paceHourglassStop();
				if (diagEl) diagEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
			})
			.catch(function (err) {
				logTo('diagOutput', 'Diagnostics error: ' + err.message, true);
				showToast('Diagnostics error: ' + err.message, 'error', 10000);
				paceHourglassStop();
				if (diagEl) diagEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
			});
	}
	function renderMetadata(data) {
		var graph = document.getElementById('metaGraph');
		var raw = document.getElementById('metaRawOutput');
		if (!graph || !raw) return;

		if (!data || !data.success) {
			graph.innerHTML = '';
			raw.textContent = t('tNoMetaData');
			return;
		}

		var fsSize = Number(data.fs_size_bytes || 0);
		var fsUsed = Number(data.fs_used_bytes || 0);
		var fsAvail = Number(data.fs_avail_bytes || 0);
		var usagePct = fsSize > 0 ? Math.max(0, Math.min(100, Math.round((fsUsed / fsSize) * 100))) : 0;
		var dev = data.device_info || {};
		var devPath = dev.path || data.device || '-';
		var devModel = dev.model || '-';
		var devSerial = dev.serial || '-';
		var devTable = dev.partition_table || '-';
		var devSizeBytes = Number(dev.size_bytes || 0);
		var devSectorSizeBytes = Number(dev.sector_size_bytes || 0);
		var devSizeHuman = devSizeBytes > 0 ? humanBytes(devSizeBytes) : '-';
		var devSectorSizeHuman = devSectorSizeBytes > 0 ? humanBytes(devSectorSizeBytes) : '-';
		var devTotalSectors = Number(dev.total_sectors || 0);
		var devHeads = Number(dev.heads || 0);
		var devSpt = Number(dev.sectors_per_track || 0);
		var devCylinders = Number(dev.cylinders || 0);
		var fsType = data.filesystem_type || data.fstype || '-';
		var partName = data.partition_name || '-';
		var partFlags = data.flags || '-';
		var fsLabel = data.label || '-';
		var mountPoint = data.mount_point || data.mountpoint || '(not mounted)';
		var usedHuman = data.used_human || humanBytes(fsUsed);
		var unusedHuman = data.unused_human || humanBytes(fsAvail);

		var html = '';
		html += '<div class="pcgi-kv-grid">';
		html += '<div class="pcgi-kv-card"><div class="pcgi-kv-key">Partition</div><div class="pcgi-kv-value">' + (data.partition || '-') + '</div></div>';
		html += '<div class="pcgi-kv-card"><div class="pcgi-kv-key">Partition name</div><div class="pcgi-kv-value">' + partName + '</div></div>';
		html += '<div class="pcgi-kv-card"><div class="pcgi-kv-key">Flags</div><div class="pcgi-kv-value">' + partFlags + '</div></div>';
		html += '<div class="pcgi-kv-card"><div class="pcgi-kv-key">Path</div><div class="pcgi-kv-value">' + devPath + '</div></div>';
		html += '<div class="pcgi-kv-card"><div class="pcgi-kv-key">Model</div><div class="pcgi-kv-value">' + devModel + '</div></div>';
		html += '<div class="pcgi-kv-card"><div class="pcgi-kv-key">Serial</div><div class="pcgi-kv-value">' + devSerial + '</div></div>';
		html += '<div class="pcgi-kv-card"><div class="pcgi-kv-key">Size</div><div class="pcgi-kv-value">' + devSizeHuman + '</div></div>';
		html += '<div class="pcgi-kv-card"><div class="pcgi-kv-key">Partition table</div><div class="pcgi-kv-value">' + devTable + '</div></div>';
		html += '<div class="pcgi-kv-card"><div class="pcgi-kv-key">Heads</div><div class="pcgi-kv-value">' + (devHeads > 0 ? String(devHeads) : '-') + '</div></div>';
		html += '<div class="pcgi-kv-card"><div class="pcgi-kv-key">Sectors/Track</div><div class="pcgi-kv-value">' + (devSpt > 0 ? String(devSpt) : '-') + '</div></div>';
		html += '<div class="pcgi-kv-card"><div class="pcgi-kv-key">Cylinders</div><div class="pcgi-kv-value">' + (devCylinders > 0 ? String(devCylinders) : '-') + '</div></div>';
		html += '<div class="pcgi-kv-card"><div class="pcgi-kv-key">Total sectors</div><div class="pcgi-kv-value">' + (devTotalSectors > 0 ? String(devTotalSectors) : '-') + '</div></div>';
		html += '<div class="pcgi-kv-card"><div class="pcgi-kv-key">Sector size</div><div class="pcgi-kv-value">' + devSectorSizeHuman + '</div></div>';
		html += '<div class="pcgi-kv-card"><div class="pcgi-kv-key">File system Type</div><div class="pcgi-kv-value">' + fsType + '</div></div>';
		html += '<div class="pcgi-kv-card"><div class="pcgi-kv-key">Label</div><div class="pcgi-kv-value">' + fsLabel + '</div></div>';
		html += '<div class="pcgi-kv-card"><div class="pcgi-kv-key">Mount point</div><div class="pcgi-kv-value">' + mountPoint + '</div></div>';
		html += '<div class="pcgi-kv-card"><div class="pcgi-kv-key">Partition size</div><div class="pcgi-kv-value">' + humanBytes(Number(data.size_bytes || 0)) + '</div></div>';
		html += '<div class="pcgi-kv-card"><div class="pcgi-kv-key">Filesystem used</div><div class="pcgi-kv-value">' + usedHuman + '</div></div>';
		html += '<div class="pcgi-kv-card"><div class="pcgi-kv-key">Filesystem unused</div><div class="pcgi-kv-value">' + unusedHuman + '</div></div>';
		html += '</div>';

		if (fsSize > 0) {
			html += '<div class="pcgi-kv-card">';
			html += '<div class="pcgi-kv-key">Filesystem usage graph</div>';
			html += '<div class="pcgi-kv-value">' + usagePct + '% used</div>';
			html += '<div class="pcgi-progress-wrap"><div class="pcgi-progress-used" style="width:' + usagePct + '%"></div></div>';
			html += '</div>';
		}

		graph.innerHTML = html;

		var src = data.sources || [];
		var lines = [];
		for (var i = 0; i < src.length; i++) {
			lines.push('$ ' + (src[i].command || 'command'));
			lines.push(src[i].output || '');
			lines.push('');
		}
		raw.textContent = lines.join('\n');
	}

	function loadPartitionMetadata() {
		var part = document.getElementById('fsPartitionPath').value.trim();
		if (!part && state.selectedPart && state.selectedPart.path) {
			part = state.selectedPart.path;
			document.getElementById('fsPartitionPath').value = part;
		}
		if (!part) {
			showToast(t('tNeedPartPath'), 'warn');
			return;
		}
		document.getElementById('metaStatus').textContent = 'Loading metadata...';
		callApi('partition_metadata', {
			partition: part,
			device: state.selectedDevice,
			partnum: document.getElementById('selectedPartNum').value.trim()
		}).then(function (res) {
			if (!res.success) throw new Error(res.message || 'Metadata load failed');
			renderMetadata(res);
			document.getElementById('metaStatus').textContent = t('tMetaLoaded');
			showToast(t('tMetaLoaded'), 'success', 10000);
		}).catch(function (err) {
			document.getElementById('metaStatus').textContent = 'Error: ' + err.message;
			renderMetadata(null);
			logTo('cmdOutput', 'Metadata error: ' + err.message, false);
			showToast('Metadata error: ' + err.message, 'error', 10000);
		});
	}

	function analyzeTools() {
		callApi('analyze_tools', {})
			.then(function (res) {
				if (!res.success) {
					throw new Error(res.message || 'Tool analysis failed');
				}
				var summary = summarizeTools(res);
				state.toolStatus = summary;
				renderToolSummary(summary);
				var lines = [];
				lines.push('e2fsprogs mode: ' + (res.e2fsprogs_mode || '-'));
				lines.push('missing commands: ' + (summary.missing.length ? summary.missing.join(', ') : '(none)'));
				lines.push('');
				for (var i = 0; i < (res.tools || []).length; i++) {
					var t = res.tools[i];
					lines.push((t.available ? '[ok] ' : '[missing] ') + t.name + ' -> ' + (t.path || '-') + ' | ' + (t.role || ''));
				}
				logTo('toolsOutput', lines.join('\n'), true);
			})
			.catch(function (err) {
				state.toolStatus = null;
				var box = document.getElementById('toolSummaryBox');
				var title = document.getElementById('toolSummaryTitle');
				var meta = document.getElementById('toolSummaryMeta');
				var missWrap = document.getElementById('toolSummaryMissingWrap');
				var impact = document.getElementById('toolSummaryImpact');
				if (box) box.className = 'pcgi-tool-summary pcgi-tool-summary-danger';
				if (title) title.textContent = t('toolAnalysisFailed');
				if (meta) meta.textContent = '';
				if (missWrap) missWrap.style.display = 'none';
				if (impact) impact.textContent = err.message;
				logTo('toolsOutput', 'Analysis error: ' + err.message, true);
				showToast('Tool analysis error: ' + err.message, 'error', 10000);
			});
	}

	function onKeyboardShortcuts(ev) {
		var tag = (ev.target && ev.target.tagName) ? ev.target.tagName.toLowerCase() : '';
		// Suppress shortcuts in text fields; for <select> allow ArrowLeft/Right.
		if (!ev.ctrlKey && ev.key !== 'F1') {
			if (tag === 'input' || tag === 'textarea') return;
			if (tag === 'select' && ev.key !== 'ArrowLeft' && ev.key !== 'ArrowRight') return;
		}

		if (ev.key === 'F1' || ev.key === '?') {
			ev.preventDefault();
			showHelpModal();
			return;
		}
		if (ev.ctrlKey && !ev.shiftKey && (ev.key === 'r' || ev.key === 'R')) {
			ev.preventDefault();
			refreshDevices();
			return;
		}
		if (ev.ctrlKey && ev.shiftKey && (ev.key === 'a' || ev.key === 'A')) {
			ev.preventDefault();
			analyzeTools();
			return;
		}
		if (ev.ctrlKey && !ev.shiftKey && (ev.key === 'm' || ev.key === 'M')) {
			ev.preventDefault();
			loadPartitionMetadata();
			return;
		}
		if (ev.ctrlKey && !ev.shiftKey && ev.key === 'Enter') {
			ev.preventDefault();
			applyQueue();
			return;
		}
		if (ev.key === 'ArrowLeft') {
			// Let browser handle Ctrl+Left (word navigation) inside text fields
			if (ev.ctrlKey && (tag === 'input' || tag === 'textarea')) return;
			ev.preventDefault();
			if (ev.altKey) {
				queueMoveSelectedByDirection('left');
			} else {
				navigateSelectedPartition('left');
			}
			return;
		}
		if (ev.key === 'ArrowRight') {
			// Let browser handle Ctrl+Right (word navigation) inside text fields
			if (ev.ctrlKey && (tag === 'input' || tag === 'textarea')) return;
			ev.preventDefault();
			if (ev.altKey) {
				queueMoveSelectedByDirection('right');
			} else {
				navigateSelectedPartition('right');
			}
			return;
		}
		if (ev.key === 'Delete') {
			ev.preventDefault();
			queueDeletePartition();
		}
	}

	document.getElementById('newPartChip').ondragstart = function (ev) {
		state.mapDragActive = true;
		hideHoverTooltip();
		ev.dataTransfer.setData('text/plain', 'new-partition');
	};
	document.getElementById('newPartChip').ondragend = function () {
		state.mapDragActive = false;
		hideHoverTooltip();
	};
	var moveCloneChipEl = document.getElementById('moveClonePartChip');
	if (moveCloneChipEl) {
		moveCloneChipEl.ondragstart = function (ev) {
			state.mapDragActive = true;
			hideHoverTooltip();
			ev.dataTransfer.setData('text/plain', 'chip-move-or-clone');
			if (state.selectedPart) {
				ev.dataTransfer.setData('part-size', String(state.selectedPart.size || 0));
			}
			/* Capture source context at drag time (user may switch device before drop).
			 * Use selectedPartDevice (device of last selected partition), not selectedDevice
			 * (which may have changed when user navigated to the target disk). */
			ev.dataTransfer.setData('text/x-src-dev', state.selectedPartDevice || state.selectedDevice || '');
			ev.dataTransfer.setData('text/x-src-part-num',
				state.selectedPart ? String(state.selectedPart.number || '') : '');
		};
		moveCloneChipEl.ondragend = function () {
			state.mapDragActive = false;
			hideHoverTooltip();
		};
	}
	var verifyChipEl = document.getElementById('verifyPartChip');
	if (verifyChipEl) {
		verifyChipEl.onclick = showVerifyModal;
	}
	document.getElementById('helpBtn').onclick = showHelpModal;
	document.getElementById('pcgiHelpCloseBtn').onclick = hideHelpModal;
	document.getElementById('langSelect').onchange = function () {
		state.language = this.value;
		applyTranslations();
		analyzeTools();
	};
	document.getElementById('usbOnlySelect').onchange = function () {
		state.usbOnly = this.value === '1';
		refreshDevices();
	};
	document.getElementById('ackToken').addEventListener('change', updateSafetySectionVisibility);
	document.getElementById('ackToken').addEventListener('keyup', function () {
		if (this.value.trim() === 'YES_I_UNDERSTAND') updateSafetySectionVisibility();
	});
	var paramsFallbackEditor = document.getElementById('pcgiParamsEditorFallback');
	if (paramsFallbackEditor) {
		paramsFallbackEditor.addEventListener('input', function () {
			schedulePreviewFromParamEditorLive();
		});
	}
	document.addEventListener('click', function (ev) {
		var menu = document.getElementById('partContextMenu');
		if (!menu) return;
		if (menu.style.display === 'none') return;
		if (!menu.contains(ev.target)) hideContextMenu();
	});
	document.addEventListener('scroll', hideHoverTooltip, true);
	document.addEventListener('dragend', function () {
		state.mapDragActive = false;
		hideHoverTooltip();
	}, true);
	document.addEventListener('keydown', function (ev) {
		if (ev.key === 'Escape') {
			hideContextMenu();
			hideHelpModal();
			hideHoverTooltip();
		}
	});
	document.addEventListener('keydown', onKeyboardShortcuts);
	window.addEventListener('resize', renderMap);

	window.refreshDevices = refreshDevices;
	window.onDeviceChange = onDeviceChange;
	window.queueCreatePartition = queueCreatePartition;
	window.showMoveCloneModal = showMoveCloneModal;
	window.showVerifyModal = showVerifyModal;
	window.showDiskMoveCloneModal = showDiskMoveCloneModal;
	window.showPartcloneExportModal = showPartcloneExportModal;
	window.showPartcloneImportModal = showPartcloneImportModal;
	window.showPartcloneNetSendModal = showPartcloneNetSendModal;
	window.showPartcloneNetRecvModal = showPartcloneNetRecvModal;
	window.showDdrescueModal = showDdrescueModal;
	window.queueDeletePartition = queueDeletePartition;
	window.queueResizePartitionFromInputs = queueResizePartitionFromInputs;
	window.queueMkfs = queueMkfs;
	window.queueSetLabel = queueSetLabel;
	window.queueRenamePartition = queueRenamePartition;
	window.queueSetFlag = queueSetFlag;
	window.queueMountPartition = queueMountPartition;
	window.showMountModal = showMountModal;
	window.queueUnmountPartition = queueUnmountPartition;
	window.runFsck = runFsck;
	window.clearQueue = clearQueue;
	window.applyQueue = applyQueue;
	window.showFieldHelp = showFieldHelp;
	window.clearLogOutput = clearLogOutput;
	window.copyLogToClipboard = copyLogToClipboard;
	window.toggleLogFullscreen = toggleLogFullscreen;
	window.runDiagnostics = runDiagnostics;
	window.analyzeTools = analyzeTools;
	window.loadPartitionMetadata = loadPartitionMetadata;
	window.toggleToolchainSection = toggleToolchainSection;

	state.language = detectLanguage();
	document.getElementById('langSelect').value = state.language;
	state.dryRun = false;
	applyTranslations();
	hideLegacyFooterButtons();
	setTimeout(hideLegacyFooterButtons, 0);
	updateSafetySectionVisibility();
	renderMapLoading(t('tMapLoading'));
	bindSectorFieldTooltip('newStartSector', 'New start sector');
	bindSectorFieldTooltip('newEndSector', 'New end sector');
	bindSectorFieldTooltip('resizeEndSector', 'Resize end sector');
	bindSectorHumanPair('newStartSector', 'newStartHuman');
	bindSectorHumanPair('newEndSector', 'newEndHuman');
	bindSectorHumanPair('resizeEndSector', 'resizeEndHuman');
	bindSectorHumanPair('mcTargetStart', 'mcTargetStartNum');
	bindSectorHumanPair('mcTargetEnd', 'mcTargetEndNum');
	bindSectorHumanPair('pnpStartSector', 'pnpStartHuman');
	bindSectorHumanPair('pnpEndSector',   'pnpEndHuman');
	// Unit-selector changes should re-sync the numeric display from current sector value
	(function () {
		['mcTargetStartNum', 'mcTargetEndNum'].forEach(function (numId) {
			var unitSel = document.getElementById(numId + 'Unit');
			if (unitSel) unitSel.addEventListener('change', function () {
				// Re-derive the numeric display from the current sector value
				var sectorId = numId === 'mcTargetStartNum' ? 'mcTargetStart' : 'mcTargetEnd';
				updateHumanFieldFromSector(sectorId, numId);
			});
		});
		var mcStart = document.getElementById('mcTargetStart');
		var mcEnd   = document.getElementById('mcTargetEnd');
		if (mcStart) mcStart.addEventListener('input', updateMcTargetSize);
		if (mcEnd)   mcEnd.addEventListener('input', updateMcTargetSize);
	}());
	refreshSectorHumanFields();
	_injectHelpButtons();
	refreshDevices();
	analyzeTools();
})();
</script>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/pace-js@1.2.4/themes/blue/pace-theme-center-radar.css">
<script src="https://cdn.jsdelivr.net/npm/pace-js@1.2.4/pace.min.js"></script>
EOF

