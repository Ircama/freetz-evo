#!/bin/sh

. /usr/lib/libmodcgi.sh

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
CMD_GDISK=''
CMD_CGDISK=''
CMD_SGDISK=''
CMD_FIXPARTS=''
CMD_HDPARM=''
CMD_SMARTCTL=''
CMD_LSBLK=''
CMD_BLKID=''
CMD_MKNTFS=''
CMD_NTFSFIX=''
CMD_NTFSINFO=''
CMD_NTFSLABEL=''
CMD_NTFSRESIZE=''
CMD_FATRESIZE=''
CMD_MOUNT=''
CMD_UMOUNT=''

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
	done
	return 1
}

resolve_tools() {
	[ -n "$CMD_PARTED" ] && return 0
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
	CMD_GDISK=$(find_cmd gdisk)
	CMD_CGDISK=$(find_cmd cgdisk)
	CMD_SGDISK=$(find_cmd sgdisk)
	CMD_FIXPARTS=$(find_cmd fixparts)
	CMD_HDPARM=$(find_cmd hdparm)
	CMD_SMARTCTL=$(find_cmd smartctl)
	CMD_LSBLK=$(find_cmd lsblk)
	CMD_BLKID=$(find_cmd blkid-util-linux blkid-ng blkid)
	CMD_MKNTFS=$(find_cmd mkntfs)
	CMD_NTFSFIX=$(find_cmd ntfsfix)
	CMD_NTFSINFO=$(find_cmd ntfsinfo)
	CMD_NTFSLABEL=$(find_cmd ntfslabel)
	CMD_NTFSRESIZE=$(find_cmd ntfsresize)
	CMD_FATRESIZE=$(find_cmd fatresize)
	CMD_MOUNT=$(find_cmd mount)
	CMD_UMOUNT=$(find_cmd umount)
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
		''|*[!0-9]*) return 1 ;;
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
	_msg=$(json_escape "$1")
	echo "{\"success\": false, \"message\": \"$_msg\"}"
}

emit_cmd_result() {
	_success="$1"
	_rc="$2"
	_msg=$(json_escape "$3")
	_out=$(json_escape "$4")
	echo "{\"success\": $_success, \"rc\": $_rc, \"message\": \"$_msg\", \"output\": \"$_out\"}"
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

run_partprobe() {
	if [ -n "$CMD_PARTPROBE" ]; then
		$CMD_PARTPROBE "$1" >/tmp/disk-mgmt-partprobe.log 2>&1
	fi
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
	add_item "gdisk" "$CMD_GDISK" "GPT interactive editor"
	add_item "cgdisk" "$CMD_CGDISK" "GPT curses editor"
	add_item "sgdisk" "$CMD_SGDISK" "GPT scriptable editor"
	add_item "fixparts" "$CMD_FIXPARTS" "MBR repair utility"
	add_item "hdparm" "$CMD_HDPARM" "Disk identify and tuning"
	add_item "smartctl" "$CMD_SMARTCTL" "SMART health check"
	add_item "lsblk" "$CMD_LSBLK" "Block device topology"
	add_item "blkid" "$CMD_BLKID" "Filesystem signatures"
	add_item "mkntfs" "$CMD_MKNTFS" "Create NTFS filesystem"
	add_item "ntfsfix" "$CMD_NTFSFIX" "Check and repair NTFS"
	add_item "ntfsinfo" "$CMD_NTFSINFO" "Read NTFS metadata"
	add_item "ntfslabel" "$CMD_NTFSLABEL" "Set NTFS label"
	add_item "ntfsresize" "$CMD_NTFSRESIZE" "Resize NTFS filesystem"
	add_item "fatresize" "$CMD_FATRESIZE" "Resize FAT filesystem"
	add_item "mount" "$CMD_MOUNT" "Mount filesystem"
	add_item "umount" "$CMD_UMOUNT" "Unmount filesystem"

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
				if [ -z "$_plabel" ] && [ -n "$CMD_BLKID" ]; then
					_plabel=$($CMD_BLKID -o value -s LABEL "$_ppath" 2>/dev/null | head -n 1)
				fi
				if [ "$_p_fs_size_bytes" -gt 0 ]; then
					_p_used_pct=$(safe_uint "$(awk -v u="$_p_fs_used_bytes" -v s="$_p_fs_size_bytes" 'BEGIN { if (s > 0) printf "%.0f", (u * 100) / s; else print 0 }')")
				fi
				_parts="$_parts{\"kind\":\"partition\",\"number\":$_pnum,\"start\":$_pstart,\"end\":$_pend,\"size\":$_psize,\"path\":\"$(json_escape "$_ppath")\",\"fs\":\"$(json_escape "$_pfs")\",\"name\":\"$(json_escape "$_pname")\",\"flags\":\"$(json_escape "$_pflags")\",\"label\":\"$(json_escape "$_plabel")\",\"mountpoint\":\"$(json_escape "$_mountpoint")\",\"fs_size_bytes\":$_p_fs_size_bytes,\"fs_used_bytes\":$_p_fs_used_bytes,\"fs_avail_bytes\":$_p_fs_avail_bytes,\"used_pct\":$_p_used_pct}"
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

	[ -n "$CMD_PARTED" ] || { emit_json_error "parted command not available"; return; }
	is_valid_device "$_device" || { emit_json_error "Invalid device"; return; }
	is_valid_sector "$_start_sector" || { emit_json_error "Invalid start sector"; return; }
	is_valid_sector "$_end_sector" || { emit_json_error "Invalid end sector"; return; }

	case "$_part_role" in
		primary|logical|extended|'') : ;;
		*) emit_json_error "Invalid partition role"; return ;;
	esac
	[ -z "$_part_role" ] && _part_role='primary'

	case "$_fs_hint" in
		''|ext2|ext3|ext4|fat16|fat32|linux-swap|ntfs|xfs) : ;;
		*) emit_json_error "Invalid fs hint"; return ;;
	esac

	if [ "$_start_sector" -ge "$_end_sector" ]; then
		emit_json_error "Start sector must be lower than end sector"
		return
	fi

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
		emit_dry_run_result "partition creation" "$_preview_cmd"
		return
	fi

	if [ -n "$_fs_hint" ]; then
		_out=$($CMD_PARTED -s "$_device" unit s mkpart "$_part_role" "$_fs_hint" "${_start_sector}s" "${_end_sector}s" 2>&1)
	else
		_out=$($CMD_PARTED -s "$_device" unit s mkpart "$_part_role" "${_start_sector}s" "${_end_sector}s" 2>&1)
	fi
	_rc=$?

	if [ "$_rc" -eq 0 ] && [ -n "$_part_name" ]; then
		if ! is_valid_label "$_part_name"; then
			_out="$_out\nWarning: Partition name contains unsupported characters and was skipped"
		else
			_new_part=$($CMD_PARTED -s -m "$_device" unit s print 2>/dev/null | awk -F: '/^[0-9]+:/ { n=$1 } END { print n }')
			if is_valid_partnum "$_new_part"; then
				$CMD_PARTED -s "$_device" name "$_new_part" "$_part_name" >/tmp/disk-mgmt-name.log 2>&1
			fi
		fi
	fi

	[ "$_rc" -eq 0 ] && run_partprobe "$_device"

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

	_out=$($CMD_PARTED -s "$_device" rm "$_partnum" 2>&1)
	_rc=$?
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

	_out=$($CMD_PARTED -s -f "$_device" unit s resizepart "$_partnum" "${_end_sector}s" 2>&1)
	_rc=$?

	# Some parted versions still require an explicit confirmation when shrinking.
	# Retry with scripted confirmation so queued operations do not stop on rc=134.
	if [ "$_rc" -ne 0 ]; then
		case "$_out" in
			*"Shrinking a partition can cause data loss"*|*"are you sure you want to continue"*)
				_retry_out=$(printf 'Yes\nIgnore\nIgnore\nIgnore\n' | $CMD_PARTED ---pretend-input-tty -f "$_device" unit s resizepart "$_partnum" "${_end_sector}s" yes 2>&1)
				_retry_rc=$?
				if [ "$_retry_rc" -eq 0 ]; then
					_out="$_out\n\nRetry with scripted confirmation rc=$_retry_rc:\n$_retry_out"
					_rc=0
				else
					_retry_out2=$($CMD_PARTED -s -f "$_device" unit s resizepart "$_partnum" "${_end_sector}s" yes 2>&1)
					_retry_rc2=$?
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
						_ck=$($CMD_E2FSCK -f -p "$_ppath" 2>&1)
						_ck_rc=$?
						_rs=$($CMD_RESIZE2FS "$_ppath" 2>&1)
						_rs_rc=$?
						_out="$_out\n\nFilesystem check rc=$_ck_rc:\n$_ck\n\nresize2fs rc=$_rs_rc:\n$_rs"
					else
						_out="$_out\n\nWarning: resize requested but e2fsprogs resize tools are not available"
					fi
					;;
				ntfs)
					if [ -n "$CMD_NTFSRESIZE" ]; then
						_rs=$($CMD_NTFSRESIZE -f "$_ppath" 2>&1)
						_rs_rc=$?
						_out="$_out\n\nntfsresize rc=$_rs_rc:\n$_rs"
					else
						_out="$_out\n\nWarning: NTFS resize requested but ntfsresize is not available"
					fi
					;;
				fat|fat12|fat16|fat32|vfat)
					if [ -n "$CMD_FATRESIZE" ]; then
						_rs=$($CMD_FATRESIZE -s max "$_ppath" 2>&1)
						_rs_rc=$?
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
emit_dry_run_result "filesystem resize" "resize2fs $_partition"
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
emit_dry_run_result "filesystem resize" "fatresize -s ${_target_bytes}B $_partition"
else
emit_dry_run_result "filesystem resize" "fatresize -s max $_partition"
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

_cmd_ck="$CMD_E2FSCK -f -p $_partition"
_ck=$($CMD_E2FSCK -f -p "$_partition" 2>&1)

_cmd_rs="$CMD_RESIZE2FS ${_opts_display}$_partition ${_target_kib}K"
if [ -n "$_extra_opts" ]; then
set -- $_extra_opts
_rs=$($CMD_RESIZE2FS "$@" "$_partition" "${_target_kib}K" 2>&1)
else
_rs=$($CMD_RESIZE2FS "$_partition" "${_target_kib}K" 2>&1)
fi
_rc=$?
_out="\$ $_cmd_ck
$_ck

\$ $_cmd_rs
$_rs"
else
_cmd_rs="$CMD_RESIZE2FS ${_opts_display}$_partition"
if [ -n "$_extra_opts" ]; then
set -- $_extra_opts
_rs=$($CMD_RESIZE2FS "$@" "$_partition" 2>&1)
else
_rs=$($CMD_RESIZE2FS "$_partition" 2>&1)
fi
_rc=$?
_out="\$ $_cmd_rs
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
_target_bytes=$(safe_uint "$_target_bytes")
[ "$_target_bytes" -gt 0 ] || { emit_json_error "Invalid target_bytes for shrink"; return; }
_cmd_rs="$CMD_NTFSRESIZE -f -s $_target_bytes ${_opts_display}$_partition"
if [ -n "$_extra_opts" ]; then
set -- $_extra_opts
_out=$($CMD_NTFSRESIZE -f -s "$_target_bytes" "$@" "$_partition" 2>&1)
else
_out=$($CMD_NTFSRESIZE -f -s "$_target_bytes" "$_partition" 2>&1)
fi
else
_cmd_rs="$CMD_NTFSRESIZE -f ${_opts_display}$_partition"
if [ -n "$_extra_opts" ]; then
set -- $_extra_opts
_out=$($CMD_NTFSRESIZE -f "$@" "$_partition" 2>&1)
else
_out=$($CMD_NTFSRESIZE -f "$_partition" 2>&1)
fi
fi
_rc=$?
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
if [ "$_direction" = "shrink" ]; then
_target_bytes=$(safe_uint "$_target_bytes")
[ "$_target_bytes" -gt 0 ] || { emit_json_error "Invalid target_bytes for shrink"; return; }
_cmd_rs="$CMD_FATRESIZE -s ${_target_bytes}B ${_opts_display}$_partition"
if [ -n "$_extra_opts" ]; then
set -- $_extra_opts
_out=$($CMD_FATRESIZE -s "${_target_bytes}B" "$@" "$_partition" 2>&1)
else
_out=$($CMD_FATRESIZE -s "${_target_bytes}B" "$_partition" 2>&1)
fi
else
_cmd_rs="$CMD_FATRESIZE -s max ${_opts_display}$_partition"
if [ -n "$_extra_opts" ]; then
set -- $_extra_opts
_out=$($CMD_FATRESIZE -s max "$@" "$_partition" 2>&1)
else
_out=$($CMD_FATRESIZE -s max "$_partition" 2>&1)
fi
fi
_rc=$?
_out="\$ $_cmd_rs
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
					_preview_cmd="mkntfs -F -L $_label ${_extra_opts:-} $_partition"
				else
					_preview_cmd="mkntfs -F ${_extra_opts:-} $_partition"
				fi
				;;
		esac
		emit_dry_run_result "filesystem creation" "$_preview_cmd"
		return
	fi

	case "$_fs_type" in
		ext2|ext3|ext4)
			[ -n "$CMD_MKE2FS" ] || { emit_json_error "mke2fs/e2fsprogs not available"; return; }
			if [ -n "$_extra_opts" ]; then
				set -- $_extra_opts
				_out=$($CMD_MKE2FS -F -t "$_fs_type" "$@" "$_partition" 2>&1)
			else
				_out=$($CMD_MKE2FS -F -t "$_fs_type" "$_partition" 2>&1)
			fi
			_rc=$?
			if [ "$_rc" -eq 0 ] && [ -n "$_label" ]; then
				if ! is_valid_label "$_label"; then
					_out="$_out\nWarning: label skipped (invalid chars)"
				elif [ -n "$CMD_E2LABEL" ]; then
					_lbl_out=$($CMD_E2LABEL "$_partition" "$_label" 2>&1)
					_out="$_out\n\nLabel:\n$_lbl_out"
				elif [ -n "$CMD_TUNE2FS" ]; then
					_lbl_out=$($CMD_TUNE2FS -L "$_label" "$_partition" 2>&1)
					_out="$_out\n\nLabel:\n$_lbl_out"
				fi
			fi
			;;
		fat16)
			[ -n "$CMD_MKFS_FAT" ] || { emit_json_error "mkfs.fat not available"; return; }
			if [ -n "$_extra_opts" ]; then
				set -- $_extra_opts
				_out=$($CMD_MKFS_FAT -F 16 "$@" "$_partition" 2>&1)
			else
				_out=$($CMD_MKFS_FAT -F 16 "$_partition" 2>&1)
			fi
			_rc=$?
			if [ "$_rc" -eq 0 ] && [ -n "$_label" ] && [ -n "$CMD_FATLABEL" ]; then
				_lbl_out=$($CMD_FATLABEL "$_partition" "$_label" 2>&1)
				_out="$_out\n\nLabel:\n$_lbl_out"
			fi
			;;
		fat32|vfat)
			[ -n "$CMD_MKFS_FAT" ] || { emit_json_error "mkfs.fat not available"; return; }
			if [ -n "$_extra_opts" ]; then
				set -- $_extra_opts
				_out=$($CMD_MKFS_FAT -F 32 "$@" "$_partition" 2>&1)
			else
				_out=$($CMD_MKFS_FAT -F 32 "$_partition" 2>&1)
			fi
			_rc=$?
			if [ "$_rc" -eq 0 ] && [ -n "$_label" ] && [ -n "$CMD_FATLABEL" ]; then
				_lbl_out=$($CMD_FATLABEL "$_partition" "$_label" 2>&1)
				_out="$_out\n\nLabel:\n$_lbl_out"
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
				set -- $_extra_opts
				if [ -n "$_label" ]; then
					_out=$($CMD_MKFS_EXFAT -n "$_label" "$@" "$_partition" 2>&1)
				else
					_out=$($CMD_MKFS_EXFAT "$@" "$_partition" 2>&1)
				fi
			else
				if [ -n "$_label" ]; then
					_out=$($CMD_MKFS_EXFAT -n "$_label" "$_partition" 2>&1)
				else
					_out=$($CMD_MKFS_EXFAT "$_partition" 2>&1)
				fi
			fi
			_rc=$?
			if [ "$_rc" -eq 0 ] && [ -n "$_label" ] && [ -n "$CMD_EXFATLABEL" ]; then
				_lbl_out=$(run_exfat_label "$_partition" "$_label")
				_lbl_rc=$?
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
			if [ -n "$_extra_opts" ]; then
				set -- $_extra_opts
				if [ -n "$_label" ]; then
					_out=$($CMD_MKNTFS -F -L "$_label" "$@" "$_partition" 2>&1)
				else
					_out=$($CMD_MKNTFS -F "$@" "$_partition" 2>&1)
				fi
			else
				if [ -n "$_label" ]; then
					_out=$($CMD_MKNTFS -F -L "$_label" "$_partition" 2>&1)
				else
					_out=$($CMD_MKNTFS -F "$_partition" 2>&1)
				fi
			fi
			_rc=$?
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

	case "$_fs_type" in
		ext2|ext3|ext4)
			[ -n "$CMD_E2FSCK" ] || { emit_json_error "e2fsck/e2fsprogs not available"; return; }
			if [ "$_repair" = "yes" ]; then
				_cmd_display="$CMD_E2FSCK -f -p ${_opts_display}$_partition"
				if [ -n "$_extra_opts" ]; then
					set -- $_extra_opts
					_out=$($CMD_E2FSCK -f -p "$@" "$_partition" 2>&1)
				else
					_out=$($CMD_E2FSCK -f -p "$_partition" 2>&1)
				fi
			else
				_cmd_display="$CMD_E2FSCK -f -n ${_opts_display}$_partition"
				if [ -n "$_extra_opts" ]; then
					set -- $_extra_opts
					_out=$($CMD_E2FSCK -f -n "$@" "$_partition" 2>&1)
				else
					_out=$($CMD_E2FSCK -f -n "$_partition" 2>&1)
				fi
			fi
			_rc=$?
			_out="\$ $_cmd_display
$_out"
			if [ "$_rc" -eq 0 ] || [ "$_rc" -eq 1 ] || [ "$_rc" -eq 2 ]; then
				emit_cmd_result true "$_rc" "Filesystem check completed" "$_out"
			else
				emit_cmd_result false "$_rc" "Filesystem check reported errors" "$_out"
			fi
			;;
		fat|fat12|fat16|fat32|vfat)
			[ -n "$CMD_FSCK_FAT" ] || { emit_json_error "fsck.fat not available"; return; }
			if [ "$_repair" = "yes" ]; then
				_cmd_display="$CMD_FSCK_FAT -a ${_opts_display}$_partition"
				if [ -n "$_extra_opts" ]; then
					set -- $_extra_opts
					_out=$($CMD_FSCK_FAT -a "$@" "$_partition" 2>&1)
				else
					_out=$($CMD_FSCK_FAT -a "$_partition" 2>&1)
				fi
			else
				_cmd_display="$CMD_FSCK_FAT -n ${_opts_display}$_partition"
				if [ -n "$_extra_opts" ]; then
					set -- $_extra_opts
					_out=$($CMD_FSCK_FAT -n "$@" "$_partition" 2>&1)
				else
					_out=$($CMD_FSCK_FAT -n "$_partition" 2>&1)
				fi
			fi
			_rc=$?
			_out="\$ $_cmd_display
$_out"
			if [ "$_rc" -eq 0 ] || [ "$_rc" -eq 1 ]; then
				emit_cmd_result true "$_rc" "Filesystem check completed" "$_out"
			else
				emit_cmd_result false "$_rc" "Filesystem check reported errors" "$_out"
			fi
			;;
		exfat)
			[ -n "$CMD_FSCK_EXFAT" ] || { emit_json_error "fsck.exfat not available"; return; }
			if [ "$_repair" = "yes" ]; then
				_cmd_display="$CMD_FSCK_EXFAT ${_opts_display}$_partition"
				if [ -n "$_extra_opts" ]; then
					set -- $_extra_opts
					_out=$($CMD_FSCK_EXFAT "$@" "$_partition" 2>&1)
				else
					_out=$($CMD_FSCK_EXFAT "$_partition" 2>&1)
				fi
			else
				_cmd_display="$CMD_FSCK_EXFAT -n ${_opts_display}$_partition"
				if [ -n "$_extra_opts" ]; then
					set -- $_extra_opts
					_out=$($CMD_FSCK_EXFAT -n "$@" "$_partition" 2>&1)
				else
					_out=$($CMD_FSCK_EXFAT -n "$_partition" 2>&1)
				fi
			fi
			_rc=$?
			_out="\$ $_cmd_display
$_out"
			if [ "$_rc" -eq 0 ] || [ "$_rc" -eq 1 ] || [ "$_rc" -eq 2 ]; then
				emit_cmd_result true "$_rc" "exFAT check completed" "$_out"
			else
				emit_cmd_result false "$_rc" "exFAT check reported errors" "$_out"
			fi
			;;
		ntfs)
			if [ -n "$CMD_NTFSFIX" ]; then
				if [ "$_repair" = "yes" ]; then
					_cmd_display="$CMD_NTFSFIX ${_opts_display}$_partition"
					if [ -n "$_extra_opts" ]; then
						set -- $_extra_opts
						_out=$($CMD_NTFSFIX "$@" "$_partition" 2>&1)
					else
						_out=$($CMD_NTFSFIX "$_partition" 2>&1)
					fi
				else
					_cmd_display="$CMD_NTFSFIX -n ${_opts_display}$_partition"
					if [ -n "$_extra_opts" ]; then
						set -- $_extra_opts
						_out=$($CMD_NTFSFIX -n "$@" "$_partition" 2>&1)
					else
						_out=$($CMD_NTFSFIX -n "$_partition" 2>&1)
					fi
				fi
				_rc=$?
				_out="\$ $_cmd_display
$_out"
				emit_cmd_result true "$_rc" "NTFS check completed" "$_out"
			elif [ -n "$CMD_NTFSINFO" ]; then
				_cmd_display="$CMD_NTFSINFO -m $_partition"
				_out=$($CMD_NTFSINFO -m "$_partition" 2>&1)
				_rc=$?
				_out="\$ $_cmd_display
$_out"
				emit_cmd_result true "$_rc" "NTFS metadata report collected (ntfsfix unavailable)" "$_out"
			else
				emit_json_error "Neither ntfsfix nor ntfsinfo is available"
			fi
			;;
		*)
			emit_json_error "Unsupported or undetected filesystem type"
			;;
	esac
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
				_out=$($CMD_E2LABEL "$_partition" "$_label" 2>&1)
				_rc=$?
			elif [ -n "$CMD_TUNE2FS" ]; then
				_out=$($CMD_TUNE2FS -L "$_label" "$_partition" 2>&1)
				_rc=$?
			else
				emit_json_error "Neither e2label nor tune2fs is available"
				return
			fi
			;;
		fat|fat12|fat16|fat32|vfat)
			[ -n "$CMD_FATLABEL" ] || { emit_json_error "fatlabel not available"; return; }
			_out=$($CMD_FATLABEL "$_partition" "$_label" 2>&1)
			_rc=$?
			;;
		exfat)
			[ -n "$CMD_EXFATLABEL" ] || { emit_json_error "exfatlabel/tune.exfat not available"; return; }
			_out=$(run_exfat_label "$_partition" "$_label")
			_rc=$?
			;;
		ntfs)
			[ -n "$CMD_NTFSLABEL" ] || { emit_json_error "ntfslabel not available"; return; }
			_out=$($CMD_NTFSLABEL "$_partition" "$_label" 2>&1)
			_rc=$?
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

	_out=$($CMD_PARTED -s "$_device" name "$_partnum" "$_part_name" 2>&1)
	_rc=$?
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

	_out=$($CMD_PARTED -s "$_device" set "$_partnum" "$_flag" "$_state" 2>&1)
	_rc=$?
	if [ "$_rc" -eq 0 ]; then
		emit_cmd_result true "$_rc" "Partition flag updated" "$_out"
	else
		emit_cmd_result false "$_rc" "Partition flag update failed" "$_out"
	fi
}

action_move_partition() {
	resolve_tools
	if ! require_ack; then
		emit_json_error "Dangerous operation blocked: type YES_I_UNDERSTAND first"
		return
	fi

	_device=$(cgi_param device)
	_partnum=$(cgi_param partnum)
	_start_sector=$(cgi_param start_sector)
	_end_sector=$(cgi_param end_sector)

	[ -n "$CMD_PARTED" ] || { emit_json_error "parted command not available"; return; }
	is_valid_device "$_device" || { emit_json_error "Invalid device"; return; }
	is_valid_partnum "$_partnum" || { emit_json_error "Invalid partition number"; return; }
	is_valid_sector "$_start_sector" || { emit_json_error "Invalid start sector"; return; }
	is_valid_sector "$_end_sector" || { emit_json_error "Invalid end sector"; return; }

	if [ "$_start_sector" -ge "$_end_sector" ]; then
		emit_json_error "Start sector must be lower than end sector"
		return
	fi

	if dry_run_enabled; then
		emit_dry_run_result "partition move" "parted -s $_device unit s move $_partnum ${_start_sector}s ${_end_sector}s
partprobe $_device"
		return
	fi

	_out=$($CMD_PARTED -s "$_device" unit s move "$_partnum" "${_start_sector}s" "${_end_sector}s" 2>&1)
	_rc=$?
	[ "$_rc" -eq 0 ] && run_partprobe "$_device"

	if [ "$_rc" -eq 0 ]; then
		emit_cmd_result true "$_rc" "Partition moved" "$_out"
	else
		emit_cmd_result false "$_rc" "Partition move failed" "$_out"
	fi
}

action_mount_partition() {
	resolve_tools
	if ! require_ack; then
		emit_json_error "Dangerous operation blocked: type YES_I_UNDERSTAND first"
		return
	fi

	_partition=$(cgi_param partition)
	_mountpoint=$(cgi_param mountpoint)
	_fs_type=$(cgi_param fs_type)
	_mount_opts=$(cgi_param mount_opts)

	[ -n "$CMD_MOUNT" ] || { emit_json_error "mount command not available"; return; }
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
		emit_cmd_result true 0 "Partition already mounted" "$_partition is already mounted on $_already"
		return
	fi

	mkdir -p "$_mountpoint" 2>/dev/null
	if [ ! -d "$_mountpoint" ]; then
		emit_json_error "Unable to create mountpoint"
		return
	fi

	if [ -n "$_fs_type" ] && [ "$_fs_type" != "auto" ]; then
		if [ -n "$_mount_opts" ]; then
			_out=$($CMD_MOUNT -t "$_fs_type" -o "$_mount_opts" "$_partition" "$_mountpoint" 2>&1)
		else
			_out=$($CMD_MOUNT -t "$_fs_type" "$_partition" "$_mountpoint" 2>&1)
		fi
	else
		if [ -n "$_mount_opts" ]; then
			_out=$($CMD_MOUNT -o "$_mount_opts" "$_partition" "$_mountpoint" 2>&1)
		else
			_out=$($CMD_MOUNT "$_partition" "$_mountpoint" 2>&1)
		fi
	fi
	_rc=$?

	if [ "$_rc" -eq 0 ]; then
		_now=$(awk -v p="$_partition" '$1 == p { print $2; exit }' /proc/mounts 2>/dev/null)
		emit_cmd_result true "$_rc" "Partition mounted" "$_out\nMountpoint: ${_now:-$_mountpoint}"
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

	_out=$($CMD_UMOUNT "$_target" 2>&1)
	_rc=$?

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
				_ext_out=$($CMD_TUNE2FS -l "$_partition" 2>&1 | sed -n '1,260p')
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

	_out=$($CMD_PARTPROBE "$_device" 2>&1)
	_rc=$?
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
	_out=$($CMD_SMARTCTL --xall "$_device" 2>&1 | sed -n '1,220p')
	_rc=$?

	if _smart_needs_fallback "$_out" || { [ "$_rc" -ne 0 ] && ! _smart_has_info "$_out"; }; then
		_smart_cmd_used='-d sat,auto -T permissive -x'
		_out=$($CMD_SMARTCTL -d sat,auto -T permissive -x "$_device" 2>&1 | sed -n '1,220p')
		_rc=$?
	fi

	if [ "$_rc" -ne 0 ] && ! _smart_has_info "$_out"; then
		_smart_cmd_used='-d sat,auto -T permissive -i'
		_out=$($CMD_SMARTCTL -d sat,auto -T permissive -i "$_device" 2>&1 | sed -n '1,220p')
		_rc=$?
	fi

	if [ -n "$_out" ] && { _smart_has_info "$_out" || [ "$_rc" -eq 0 ]; }; then
		emit_cmd_result true "$_rc" "SMART report collected (smartctl $_smart_cmd_used $_device)" "$_out"
	else
		emit_cmd_result false "$_rc" "SMART report failed (smartctl $_smart_cmd_used $_device)" "$_out"
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

	_out=$($CMD_HDPARM -I "$_device" 2>&1 | sed -n '1,220p')
	_rc=$?
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
		_out=$($CMD_SGDISK -p "$_device" 2>&1 | sed -n '1,220p')
		_rc=$?
		_msg='sgdisk GPT summary collected'
	elif [ -n "$CMD_GDISK" ]; then
		_out=$($CMD_GDISK -l "$_device" 2>&1 | sed -n '1,220p')
		_rc=$?
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

AJAX_MODE=$(cgi_param ajax)

if [ "$AJAX_MODE" = "1" ]; then
	ACTION=$(cgi_param action)
	DRY_RUN=$(cgi_param dry_run)
	[ "$DRY_RUN" = "1" ] || DRY_RUN='0'

	exec 2>>"$BACKEND_LOG_FILE"
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
		hdparm_info)
			action_hdparm_info
			;;
		gpt_info)
			action_gpt_info
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
			<li id="i18nWorkflow3">Queue operations, review, then apply in order.</li>
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
.pcgi-editor-wrap {
	border: 1px solid #c7d1dc;
	border-radius: 6px;
	overflow: hidden;
	background: #f8fbff;
}
#pcgiCommandEditor {
	height: 280px;
}
#pcgiCommandEditorFallback {
	display: none;
	width: 100%;
	height: 280px;
	border: 0;
	font-family: monospace;
	font-size: 12px;
	padding: 10px;
	box-sizing: border-box;
	resize: vertical;
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
	background: #eef4fb;
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
</style>

<div class="pcgi-toolbar">
	<button type="button" onclick="refreshDevices()" id="refreshMapBtn">Refresh map</button>
	<span id="i18nDeviceStripLabel">Devices:</span>
	<button type="button" onclick="runDiagnostics('reload_table')" id="partprobeBtn" title="Reload kernel partition table after partition changes">Run partprobe</button>
	<button type="button" onclick="analyzeTools()" id="analyzeBtn" title="Check required/optional disk-management commands on this system">Analyze toolchain</button>
	<button type="button" onclick="loadPartitionMetadata()" id="metaBtn" title="Load partition geometry and filesystem metadata for selected partition">Partition metadata</button>
	<button type="button" onclick="toggleToolchainSection()" id="toolchainToggleBtn">Show toolchain panel</button>
	<span id="mapStatus" class="pcgi-small"></span>
</div>
<div id="i18nTopButtonsExplain" class="pcgi-small" style="margin-top:-4px; margin-bottom:8px;">Run partprobe refreshes kernel partition table visibility, Analyze toolchain checks required/optional commands, Partition metadata loads partition geometry and filesystem metadata of the selected partition.</div>

<div id="deviceStrip" class="pcgi-device-strip" aria-label="Devices"></div>
<select id="deviceSelect" class="pcgi-device-select-hidden" onchange="onDeviceChange()" aria-hidden="true" tabindex="-1"></select>

<div class="pcgi-toolbar">
	<span id="newPartChip" class="pcgi-chip" draggable="true" title="Drag on a free segment to prefill new partition range">New partition</span>
	<span id="i18nDragHint" class="pcgi-small">Drag this chip into a free region. Drag the left or right edge of a partition to queue resize. Drag partitions into free regions to queue move.</span>
</div>

<div id="partitionMap"></div>
<div id="mapLegend" class="pcgi-map-legend"></div>
<div id="pcgiHoverTooltip" class="pcgi-hover-tooltip"></div>

<div id="partContextMenu" class="pcgi-context-menu"></div>

<div class="pcgi-inline-form">
	<div>
		<label id="i18nSelPartNumLabel">Selected partition number</label>
		<input id="selectedPartNum" type="text" readonly>
	</div>
	<div>
		<label id="i18nSelPartPathLabel">Selected partition path</label>
		<input id="selectedPartPath" type="text" readonly>
	</div>
	<div>
		<label id="i18nNewStartLabel">New start sector</label>
		<input id="newStartSector" type="text" placeholder="e.g. 2048">
	</div>
	<div>
		<label id="i18nNewStartHumanLabel">New start size</label>
		<input id="newStartHuman" type="text" placeholder="e.g. 1 MiB or 2048 KiB">
	</div>
	<div>
		<label id="i18nNewEndLabel">New end sector</label>
		<input id="newEndSector" type="text" placeholder="e.g. 1023999">
	</div>
	<div>
		<label id="i18nNewEndHumanLabel">New end size</label>
		<input id="newEndHuman" type="text" placeholder="e.g. 488 MiB">
	</div>
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
			<option value="ext2">ext2</option>
			<option value="ext3">ext3</option>
			<option value="ext4">ext4</option>
			<option value="fat16">fat16</option>
			<option value="fat32">fat32</option>
			<option value="ntfs">ntfs</option>
			<option value="linux-swap">linux-swap</option>
		</select>
	</div>
	<div>
		<label id="i18nPartNameLabel">Partition name</label>
		<input id="newPartName" type="text" placeholder="optional">
	</div>
</div>

<div class="pcgi-toolbar" style="margin-top: 8px;">
	<button type="button" onclick="queueCreatePartition()" id="queueCreateBtn">Queue create partition</button>
	<button type="button" onclick="queueDeletePartition()" id="queueDeleteBtn">Queue delete selected partition</button>
	<button type="button" onclick="queueRenamePartition()" id="queueRenameBtn">Queue set partition name</button>
	<input id="renamePartInput" type="text" placeholder="new partition name">
	<input id="flagNameInput" type="text" placeholder="flag (boot, esp, lba)">
	<select id="flagStateInput">
		<option value="on">on</option>
		<option value="off">off</option>
	</select>
	<button type="button" onclick="queueSetFlag()" id="queueFlagBtn">Queue set flag</button>
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
	<button type="button" onclick="queueResizePartitionFromInputs()" id="queueResizeBtn">Queue resize partition</button>
	<button type="button" onclick="queueMkfs()" id="queueMkfsBtn">Queue create filesystem</button>
	<button type="button" onclick="queueSetLabel()" id="queueLabelBtn">Queue set label</button>
	<button type="button" onclick="queueMountPartition()" id="queueMountBtn">Queue mount</button>
	<button type="button" onclick="queueUnmountPartition()" id="queueUnmountBtn">Queue unmount</button>
	<button type="button" onclick="runFsck(false)" id="checkReadonlyBtn">Check filesystem (read-only)</button>
	<button type="button" onclick="runFsck(true)" id="checkRepairBtn">Check/repair filesystem</button>
</div>
EOF
sec_end

sec_begin "Partition/filesystem metadata"
cat <<'EOF'
<div class="pcgi-toolbar">
	<button type="button" onclick="loadPartitionMetadata()" id="loadMetaBtn">Load metadata view</button>
	<span id="metaStatus" class="pcgi-small"></span>
</div>
<p id="i18nMetaExplain" class="pcgi-small">Shows partition geometry and filesystem metadata (size, used/free bytes, model/serial and table details) for the selected partition. Read-only view.</p>
<div id="metaGraph"></div>
<pre id="metaRawOutput" class="pcgi-log"></pre>
EOF
sec_end

sec_begin "Disk Diagnostics (hdparm, SMART, GPT)"
cat <<'EOF'
<div class="pcgi-toolbar">
	<button type="button" onclick="runDiagnostics('smart_info')">SMART information</button>
	<button type="button" onclick="runDiagnostics('hdparm_info')">hdparm identify</button>
	<button type="button" onclick="runDiagnostics('gpt_info')">GPT summary</button>
</div>
<p id="i18nDiagExplain" class="pcgi-small">Runs hardware/partition diagnostics on the selected disk: SMART status, hdparm identify output and GPT layout summary. Read-only diagnostics.</p>
<pre id="diagOutput" class="pcgi-log"></pre>
EOF
sec_end

sec_begin "Operation queue"
cat <<'EOF'
<table class="pcgi-table" id="queueTable">
	<thead>
		<tr>
			<th>#</th>
			<th>Operation</th>
			<th>Parameters</th>
			<th>Action</th>
		</tr>
	</thead>
	<tbody id="queueBody"></tbody>
</table>
<div class="pcgi-toolbar" style="margin-top:8px;">
	<button type="button" id="applyQueueBtn" onclick="applyQueue()">Apply queued operations</button>
	<button type="button" onclick="clearQueue()">Clear queue</button>
</div>
<pre id="cmdOutput" class="pcgi-log"></pre>
EOF
sec_end

sec_begin "Toolchain analysis" "toolchainSection"
cat <<'EOF'
<pre id="toolsOutput" class="pcgi-log"></pre>
EOF
sec_end

# Modals and toast container must live outside any collapsible section so that
# position:fixed overlays remain visible even when toolchainSection is hidden.
cat <<'EOF'
<div id="pcgiToastWrap"></div>

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
		<div id="pcgiCmdPreviewText" class="pcgi-modal-subtle">Review/edit the command preview, then validate to queue the operation.</div>
		<div class="pcgi-editor-wrap">
			<div id="pcgiCommandEditor"></div>
			<textarea id="pcgiCommandEditorFallback"></textarea>
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
(function () {
	var API_URL = '/cgi-bin/conf/disk-mgmt';
	var translations = {
		en: {
			dangerTitle: 'Danger zone',
			dangerText: 'This interface executes real partitioning commands. Backup your data before applying any operation.',
			dangerUnlock: 'To unlock mutating actions, type YES_I_UNDERSTAND:',
			dangerReadonly: 'Read-only actions (scan, map, diagnostics, filesystem check in read-only mode) do not require unlock.',
			workflowTitle: 'Disk management workflow',
			workflow1: 'Refresh devices and choose one disk.',
			workflow2: 'Drag new partition into free space, drag partition edge to resize, drag partition into free area to move it.',
			workflow3: 'Queue operations, review, then apply in order.',
			workflow4: 'Run metadata view, filesystem checks, mount operations and diagnostics.',
			dragHint: 'Drag this chip into a free region. Drag the left or right edge of a partition to queue resize. Drag partitions into free regions to queue move.',
			missingCommandsLabel: 'Missing commands:',
			languageLabel: 'Language',
			usbOnlyLabel: 'Device filter',
			helperTitle: 'Keyboard shortcuts and workflow',
			helperText: 'Ctrl+R: refresh map\nCtrl+Shift+A: analyze toolchain\nCtrl+M: load partition metadata\nCtrl+Enter: apply operation queue\nDelete: queue delete selected partition\nF1 or ?: open this help\nRight click on partition: context menu actions\nDrag partition left/right edge: queue resize\nDrag partition to free area: queue move',
			cmdPreviewTitle: 'Command preview',
			cmdPreviewHint: 'Review/edit the command preview, then validate to queue the operation.',
			toolAllAvailable: 'Toolchain status: all detected commands are available.',
			toolRequiredMissing: 'Toolchain status: required command(s) missing.',
			toolOptionalMissing: 'Toolchain status: some optional commands are missing.',
			toolAnalysisFailed: 'Toolchain status: analysis failed.',
			confirmAction: 'Confirm action',
			confirmQueueApply: 'Apply queued operations?',
			confirmQueueApplyMsg: 'The queue will execute real disk operations in order. Continue?',
			confirmRepair: 'Confirm repair check',
			confirmRepairMsg: 'Repair mode can modify filesystem structures. Continue?',
			confirmDelete: 'Confirm partition deletion',
			confirmDeleteMsg: 'Queue deletion of selected partition?',
			confirmCreate: 'Confirm partition creation',
			confirmCreateMsg: 'Queue partition creation with the selected geometry?',
			confirmMkfs: 'Confirm filesystem creation',
			confirmMkfsMsg: 'Queue filesystem creation. Existing data will be lost when applied.',
			confirmMove: 'Confirm partition move',
			confirmMoveMsg: 'Queue move of selected partition to target free region?',
			confirmMount: 'Confirm mount request',
			confirmMountMsg: 'Queue mount operation for selected partition?',
			confirmUnmount: 'Confirm unmount request',
			confirmUnmountMsg: 'Queue unmount operation for selected partition or mountpoint?',
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
			tQueued: 'Operation queued.',
			tQueueApplied: 'Queue completed successfully.',
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
			btnClose: 'Close',
			btnValidateQueue: 'Validate and queue'
		},
		it: {
			dangerTitle: 'Zona pericolosa',
			dangerText: 'Questa interfaccia esegue comandi reali di partizionamento. Esegui un backup prima di applicare operazioni.',
			dangerUnlock: 'Per sbloccare le operazioni di modifica, digita YES_I_UNDERSTAND:',
			dangerReadonly: 'Le azioni in sola lettura (scan, mappa, diagnostica, check read-only) non richiedono sblocco.',
			workflowTitle: 'Workflow gestione dischi',
			workflow1: 'Aggiorna i dispositivi e scegli un disco.',
			workflow2: 'Trascina una nuova partizione nello spazio libero, trascina il bordo destro per ridimensionare, trascina una partizione su spazio libero per spostarla.',
			workflow3: 'Metti in coda le operazioni, controlla, poi applica in ordine.',
			workflow4: 'Usa vista metadati, controlli filesystem, mount e diagnostica.',
			dragHint: 'Trascina questo chip su spazio libero. Trascina il bordo sinistro o destro di una partizione per accodare resize. Trascina una partizione su spazio libero per accodare move.',
			missingCommandsLabel: 'Comandi mancanti:',
			languageLabel: 'Lingua',
			usbOnlyLabel: 'Filtro dispositivi',
			helperTitle: 'Scorciatoie da tastiera e workflow',
			helperText: 'Ctrl+R: aggiorna mappa\nCtrl+Shift+A: analizza toolchain\nCtrl+M: carica metadati partizione\nCtrl+Invio: applica coda operazioni\nCanc: accoda eliminazione partizione selezionata\nF1 o ?: apri aiuto\nClick destro sulla partizione: menu contestuale\nTrascina bordo sinistro/destro partizione: accoda resize\nTrascina partizione su spazio libero: accoda move',
			cmdPreviewTitle: 'Anteprima comando',
			cmdPreviewHint: 'Controlla/modifica il comando in anteprima, poi valida per accodare l\'operazione.',
			toolAllAvailable: 'Stato toolchain: tutti i comandi rilevati sono disponibili.',
			toolRequiredMissing: 'Stato toolchain: mancano comandi richiesti.',
			toolOptionalMissing: 'Stato toolchain: mancano alcuni comandi opzionali.',
			toolAnalysisFailed: 'Stato toolchain: analisi fallita.',
			confirmAction: 'Conferma azione',
			confirmQueueApply: 'Applicare le operazioni in coda?',
			confirmQueueApplyMsg: 'La coda eseguira vere operazioni sul disco in sequenza. Continuare?',
			confirmRepair: 'Conferma controllo riparazione',
			confirmRepairMsg: 'La modalita riparazione puo modificare il filesystem. Continuare?',
			confirmDelete: 'Conferma eliminazione partizione',
			confirmDeleteMsg: 'Accodare eliminazione della partizione selezionata?',
			confirmCreate: 'Conferma creazione partizione',
			confirmCreateMsg: 'Accodare creazione partizione con la geometria selezionata?',
			confirmMkfs: 'Conferma creazione filesystem',
			confirmMkfsMsg: 'Accodare creazione filesystem. I dati esistenti andranno persi quando applicata.',
			confirmMove: 'Conferma spostamento partizione',
			confirmMoveMsg: 'Accodare spostamento della partizione selezionata verso lo spazio libero target?',
			confirmMount: 'Conferma richiesta mount',
			confirmMountMsg: 'Accodare operazione di mount per la partizione selezionata?',
			confirmUnmount: 'Conferma richiesta unmount',
			confirmUnmountMsg: 'Accodare operazione di unmount per partizione o mountpoint?',
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
			tQueued: 'Operazione accodata.',
			tQueueApplied: 'Coda completata con successo.',
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
			btnClose: 'Chiudi',
			btnValidateQueue: 'Valida e accoda'
		},
		de: {
			dangerTitle: 'Gefahrenbereich',
			dangerText: 'Diese Oberflaeche fuehrt echte Partitionierungsbefehle aus. Vor dem Anwenden unbedingt sichern.',
			dangerUnlock: 'Zum Freigeben von Aenderungen YES_I_UNDERSTAND eingeben:',
			dangerReadonly: 'Nur-Lese-Aktionen (Scan, Karte, Diagnose, read-only Check) benoetigen keine Freigabe.',
			workflowTitle: 'Datentraegerverwaltung',
			workflow1: 'Geraete aktualisieren und Datentraeger waehlen.',
			workflow2: 'Neue Partition in freien Bereich ziehen, rechten Partitionsrand zum Resize ziehen, Partition in freien Bereich ziehen zum Verschieben.',
			workflow3: 'Operationen in Queue sammeln, pruefen und dann anwenden.',
			workflow4: 'Metadatenansicht, Dateisystem-Pruefung, Mount und Diagnose verwenden.',
			dragHint: 'Chip in freien Bereich ziehen. Linken oder rechten Rand einer Partition ziehen fuer Resize. Partition in freien Bereich ziehen fuer Move.',
			missingCommandsLabel: 'Fehlende Befehle:',
			languageLabel: 'Sprache',
			usbOnlyLabel: 'Geraetefilter',
			helperTitle: 'Tastenkuerzel und Ablauf',
			helperText: 'Ctrl+R: Karte aktualisieren\nCtrl+Shift+A: Toolchain analysieren\nCtrl+M: Partitions-Metadaten laden\nCtrl+Enter: Queue anwenden\nEntf: Loeschen der gewaehlten Partition in Queue\nF1 oder ?: Hilfe oeffnen\nRechtsklick auf Partition: Kontextmenue\nLinken/rechten Partitionsrand ziehen: Resize in Queue\nPartition auf freien Bereich ziehen: Move in Queue',
			cmdPreviewTitle: 'Befehlsvorschau',
			cmdPreviewHint: 'Befehlsvorschau pruefen/bearbeiten und dann bestaetigen, um die Operation in die Queue aufzunehmen.',
			toolAllAvailable: 'Toolchain-Status: alle erkannten Befehle sind verfuegbar.',
			toolRequiredMissing: 'Toolchain-Status: erforderliche Befehle fehlen.',
			toolOptionalMissing: 'Toolchain-Status: optionale Befehle fehlen.',
			toolAnalysisFailed: 'Toolchain-Status: Analyse fehlgeschlagen.',
			confirmAction: 'Aktion bestaetigen',
			confirmQueueApply: 'Warteschlangen-Operationen anwenden?',
			confirmQueueApplyMsg: 'Die Queue fuehrt echte Datentraeger-Operationen der Reihe nach aus. Fortfahren?',
			confirmRepair: 'Reparaturpruefung bestaetigen',
			confirmRepairMsg: 'Reparaturmodus kann Dateisystemstrukturen aendern. Fortfahren?',
			confirmDelete: 'Partitionsloeschung bestaetigen',
			confirmDeleteMsg: 'Loeschen der gewaehlten Partition in die Queue aufnehmen?',
			confirmCreate: 'Partitionserstellung bestaetigen',
			confirmCreateMsg: 'Partitionserstellung mit gewaehlter Geometrie in Queue aufnehmen?',
			confirmMkfs: 'Dateisystemerstellung bestaetigen',
			confirmMkfsMsg: 'Dateisystemerstellung in Queue aufnehmen. Vorhandene Daten gehen beim Anwenden verloren.',
			confirmMove: 'Partitionsverschiebung bestaetigen',
			confirmMoveMsg: 'Verschiebung der gewaehlten Partition in Ziel-Freiraum in Queue aufnehmen?',
			confirmMount: 'Mount-Anfrage bestaetigen',
			confirmMountMsg: 'Mount-Operation fuer die gewaehlte Partition in Queue aufnehmen?',
			confirmUnmount: 'Unmount-Anfrage bestaetigen',
			confirmUnmountMsg: 'Unmount-Operation fuer Partition oder Mountpoint in Queue aufnehmen?',
			tQueueEmpty: 'Die Operations-Queue ist leer.',
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
			tQueued: 'Operation in Queue aufgenommen.',
			tQueueApplied: 'Queue erfolgreich abgeschlossen.',
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
			btnClose: 'Schliessen',
			btnValidateQueue: 'Bestaetigen und queue'
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
		usbOnlyDevices: "USB devices only"
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
		usbOnlyDevices: "Solo dispositivi USB"
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
		usbOnlyDevices: "Nur USB-Geraete"
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
		usbOnlyDevices: "Peripheriques USB uniquement"
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
		usbOnlyDevices: "Solo dispositivos USB"
	});

	var state = {
		devices: [],
		selectedDevice: '',
		queue: [],
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
		mapDragActive: false,
		sectorSyncLock: false
	};

	function t(key) {
		var langMap = translations[state.language] || translations.en;
		if (langMap && Object.prototype.hasOwnProperty.call(langMap, key)) {
			return langMap[key];
		}
		return (translations.en && translations.en[key]) || key;
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
			i18nDragHint: 'dragHint',
			i18nTopButtonsExplain: 'topButtonsExplain',
			i18nMetaExplain: 'metaExplain',
			i18nDiagExplain: 'diagExplain',
			i18nDeviceStripLabel: 'deviceStripLabel',
			i18nMissingCommandsLabel: 'missingCommandsLabel',
			i18nLanguageLabel: 'languageLabel',
			i18nUsbOnlyLabel: 'usbOnlyLabel',
		};
		for (var id in map) {
			if (!Object.prototype.hasOwnProperty.call(map, id)) continue;
			var el = document.getElementById(id);
			if (el) el.textContent = t(map[id]);
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
		var loadMetaBtn = document.getElementById('loadMetaBtn');
		if (partprobeBtn) { partprobeBtn.textContent = t('btnRunPartprobe'); partprobeBtn.title = t('partprobeHint'); }
		if (analyzeBtn) { analyzeBtn.textContent = t('btnAnalyzeToolchain'); analyzeBtn.title = t('analyzeHint'); }
		if (metaBtn) { metaBtn.textContent = t('btnPartitionMetadata'); metaBtn.title = t('metadataHint'); }
		if (loadMetaBtn) loadMetaBtn.textContent = t('btnLoadMetadataView');
		var usbSel = document.getElementById('usbOnlySelect');
		if (usbSel && usbSel.options.length >= 2) {
			usbSel.options[0].text = t('usbAllDevices');
			usbSel.options[1].text = t('usbOnlyDevices');
		}
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
		}, ttl || 2800);
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
		var s = document.getElementById(sectorId);
		var h = document.getElementById(humanId);
		if (!s || !h) return;
		var raw = String(s.value || '').trim();
		if (!/^\d+$/.test(raw)) {
			h.value = '';
			return;
		}
		var sectors = Number(raw);
		if (!isFinite(sectors) || sectors < 0) {
			h.value = '';
			return;
		}
		h.value = humanBytes(sectors * getCurrentSectorSize());
	}

	function refreshSectorHumanFields() {
		if (state.sectorSyncLock) return;
		state.sectorSyncLock = true;
		updateHumanFieldFromSector('newStartSector', 'newStartHuman');
		updateHumanFieldFromSector('newEndSector', 'newEndHuman');
		updateHumanFieldFromSector('resizeEndSector', 'resizeEndHuman');
		state.sectorSyncLock = false;
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

		var bytes = parseHumanBytes(txt);
		if (bytes === null) return;

		var secSize = getCurrentSectorSize();
		var sectors = Math.floor(bytes / secSize);
		if (bytes > 0 && sectors === 0) sectors = 1;
		if (!isFinite(sectors) || sectors < 0) return;

		state.sectorSyncLock = true;
		s.value = String(sectors);
		h.value = humanBytes(sectors * secSize);
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
		if (state.dragCtx || state.mapDragActive) {
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
		if (state.dragCtx || state.mapDragActive) {
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

		var required = ['parted'];
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
				base += '\nparted -s ' + v(params.device) + ' name <new_partnum> ' + v(params.part_name);
			}
			return base + '\npartprobe ' + v(params.device);
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
					return 'fatresize -s ' + v(params.target_bytes) + 'B ' + v(params.partition);
				}
				return 'fatresize -s max ' + v(params.partition);
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
				pre = 'mkntfs -F' + (v(params.label) ? (' -L ' + v(params.label)) : '') + (opts ? (' ' + opts) : '') + ' ' + v(params.partition);
				return pre;
			}
		}
		if (action === 'set_label') {
			return '# fs_type=' + v(params.fs_type) + '\n# backend auto-detects FS for auto and applies ext/fat/exfat/ntfs label command\n# target=' + v(params.partition) + ' label=' + v(params.label);
		}
		if (action === 'set_partition_name') {
			return 'parted -s ' + v(params.device) + ' name ' + v(params.partnum) + ' ' + v(params.part_name);
		}
		if (action === 'set_partition_flag') {
			return 'parted -s ' + v(params.device) + ' set ' + v(params.partnum) + ' ' + v(params.flag) + ' ' + v(params.state);
		}
		if (action === 'move_partition') {
			return 'parted -s ' + v(params.device) + ' unit s move ' + v(params.partnum) + ' ' + v(params.start_sector) + 's ' + v(params.end_sector) + 's\npartprobe ' + v(params.device);
		}
		if (action === 'mount_partition') {
			var mtxt = 'mkdir -p ' + v(params.mountpoint || '<auto>') + '\nmount';
			if (v(params.fs_type) && v(params.fs_type) !== 'auto') mtxt += ' -t ' + v(params.fs_type);
			if (v(params.mount_opts)) mtxt += ' -o ' + v(params.mount_opts);
			mtxt += ' ' + v(params.partition) + ' ' + v(params.mountpoint || '<auto>');
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
		if (action === 'hdparm_info') return 'hdparm -I ' + v(params.device);
		if (action === 'gpt_info') return '# backend uses sgdisk -p or gdisk -l for ' + v(params.device);
		if (action === 'reload_table') return 'partprobe ' + v(params.device);
		return '# preview unavailable for action: ' + v(action);
	}

	function ensureAceEditor() {
		if (state.aceEditor || !window.ace) return;
		state.aceEditor = window.ace.edit('pcgiCommandEditor');
		state.aceEditor.setTheme('ace/theme/chrome');
		state.aceEditor.session.setMode('ace/mode/sh');
		state.aceEditor.setOptions({ fontSize: '12px', showPrintMargin: false, useSoftTabs: true, tabSize: 2 });
	}

	function setPreviewEditorValue(text) {
		ensureAceEditor();
		var fallback = document.getElementById('pcgiCommandEditorFallback');
		var aceWrap = document.getElementById('pcgiCommandEditor');
		if (state.aceEditor) {
			if (fallback) fallback.style.display = 'none';
			if (aceWrap) aceWrap.style.display = '';
			state.aceEditor.setValue(text, -1);
			state.aceEditor.clearSelection();
		} else {
			if (aceWrap) aceWrap.style.display = 'none';
			if (fallback) {
				fallback.style.display = 'block';
				fallback.value = text;
			}
		}
	}

	function getPreviewEditorValue() {
		var fallback = document.getElementById('pcgiCommandEditorFallback');
		if (state.aceEditor) return state.aceEditor.getValue();
		return fallback ? fallback.value : '';
	}

	function showCommandPreviewModal(action, params, label, confirmTitle, confirmMessage) {
		var modal = document.getElementById('pcgiCmdPreviewModal');
		var title = document.getElementById('pcgiCmdPreviewTitle');
		var text = document.getElementById('pcgiCmdPreviewText');
		var btnCancel = document.getElementById('pcgiCmdCancelBtn');
		var btnValidate = document.getElementById('pcgiCmdValidateBtn');
		if (!modal || !title || !text || !btnCancel || !btnValidate) {
			return Promise.resolve(buildCommandPreview(action, params));
		}
		var previewText = buildCommandPreview(action, params);
		title.textContent = (confirmTitle || t('cmdPreviewTitle')) + ': ' + label;
		text.textContent = confirmMessage || t('cmdPreviewHint');
		setPreviewEditorValue(previewText);
		modal.style.display = 'flex';
		modal.setAttribute('aria-hidden', 'false');

		return new Promise(function (resolve) {
			function cleanup(result) {
				modal.style.display = 'none';
				modal.setAttribute('aria-hidden', 'true');
				btnCancel.onclick = null;
				btnValidate.onclick = null;
				document.removeEventListener('keydown', onEsc);
				resolve(result);
			}
			function onEsc(ev) {
				if (ev.key === 'Escape') cleanup(null);
			}
			document.addEventListener('keydown', onEsc);
			btnCancel.onclick = function () { cleanup(null); };
			btnValidate.onclick = function () { cleanup(getPreviewEditorValue()); };
		});
	}

	function queueOp(action, params, label, commandPreview, quiet) {
		state.queue.push({ action: action, params: params, label: label, commandPreview: commandPreview || '' });
		renderQueue();
		syncSelectionWithPreview();
		renderMap();
		if (!quiet) {
			showToast(t('tQueued') + ' ' + label, 'info', 2400);
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
			tdParams.textContent = JSON.stringify(op.params);
			var tdDel = document.createElement('td');
			var btn = document.createElement('button');
			btn.type = 'button';
			btn.textContent = 'Remove';
			btn.setAttribute('data-index', String(i));
			btn.onclick = function () {
				var idx = parseInt(this.getAttribute('data-index'), 10);
				state.queue.splice(idx, 1);
				renderQueue();
				syncSelectionWithPreview();
				renderMap();
			};
			tdDel.appendChild(btn);
			tr.appendChild(tdIdx);
			tr.appendChild(tdLabel);
			tr.appendChild(tdParams);
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
			updateMapStatus('Selected partition is no longer available in queued preview.');
		}
	}

	function mapFsHintValue(fs) {
		var v = String(fs || '').toLowerCase();
		if (!v) return '';
		if (v === 'fat' || v === 'vfat') return 'fat32';
		if (v === 'ext2' || v === 'ext3' || v === 'ext4' || v === 'fat16' || v === 'fat32' || v === 'ntfs' || v === 'linux-swap') {
			return v;
		}
		return '';
	}

	function mapFsTypeSelectValue(fs) {
		var v = String(fs || '').toLowerCase();
		if (!v) return 'auto';
		if (v === 'fat' || v === 'fat12' || v === 'fat16' || v === 'fat32' || v === 'vfat') return 'fat';
		if (v === 'vfat') return 'vfat';
		if (v === 'ext2' || v === 'ext3' || v === 'ext4' || v === 'exfat' || v === 'ntfs' || v === 'fat16' || v === 'fat32') {
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
		refreshSectorHumanFields();
		updateMapStatus(part ? ('Selected partition #' + part.number + ' [' + part.start + 's..' + part.end + 's].') : '');
		renderMap();
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
		if (state.contextMenuHideTimer) {
			clearTimeout(state.contextMenuHideTimer);
			state.contextMenuHideTimer = null;
		}
		state.contextTarget = { type: menuType === 'disk' ? 'disk' : 'partition', target: target };
		menu.innerHTML = '';

		var items = [];
		if (menuType === 'disk') {
			items = [
				{ id: 'select_disk', label: 'Select disk' },
				{ id: 'delete_all_parts', label: 'Queue delete all disk partitions' }
			];
		} else {
			var part = target;
			items = [
				{ id: 'select', label: 'Select partition' },
				{ id: 'meta', label: 'Load metadata' },
				{ id: 'delete', label: 'Queue delete partition' },
				{ id: 'rename', label: 'Queue rename partition' },
				{ id: 'flag', label: 'Queue set flag' },
				{ id: 'mkfs', label: 'Queue create filesystem' },
				{ id: 'mount', label: part.mountpoint ? 'Queue remount' : 'Queue mount' },
				{ id: 'umount', label: 'Queue unmount' },
				{ id: 'fsck_ro', label: 'Filesystem check read-only' },
				{ id: 'fsck_fix', label: 'Filesystem check/repair' }
			];
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

	function handleContextAction(action, target, menuType) {
		if (menuType === 'disk') {
			if (action === 'select_disk') {
				selectDisk(target);
				return;
			}
			if (action === 'delete_all_parts') {
				queueDeleteAllPartitions(target);
				return;
			}
			showToast(t('tContextUnavailable'), 'warn');
			return;
		}

		var part = target;
		selectPartition(part);
		if (action === 'select') return;
		if (action === 'meta') { loadPartitionMetadata(); return; }
		if (action === 'delete') { queueDeletePartition(); return; }
		if (action === 'rename') { queueRenamePartition(); return; }
		if (action === 'flag') { queueSetFlag(); return; }
		if (action === 'mkfs') { queueMkfs(); return; }
		if (action === 'mount') { queueMountPartition(); return; }
		if (action === 'umount') { queueUnmountPartition(); return; }
		if (action === 'fsck_ro') { runFsck(false); return; }
		if (action === 'fsck_fix') { runFsck(true); return; }
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

		legend.textContent = dev.path + ' | table=' + (dev.table || 'unknown') + ' | model=' + (dev.model || '-') + ' | size=' + humanBytes(total * logical);
		if (dev.transport) legend.textContent += ' | transport=' + dev.transport;
		if (dev.vendor) legend.textContent += ' | vendor=' + dev.vendor;
		if (dev.serial) legend.textContent += ' | serial=' + dev.serial;

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
				var block = document.createElement('div');
				block.className = 'pcgi-block ' + (p.kind === 'free' ? 'free' : 'part');
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
					var usedPct = Number(p.used_pct || 0);
					// During shrink drag recompute usedPct relative to the current draw size
					// so the filled bar stays at its real pixel width (incompressible) and
					// only the unused (light) area shrinks.
					if (draggingThis && drawSize > 0 && fsUsed > 0) {
						var drawBytesD = drawSize * logical;
						usedPct = drawBytesD > 0 ? Math.min(100, (fsUsed / drawBytesD) * 100) : 100;
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
						// Unused portion also computed from absolute bytes during drag.
						var fsUnusedPct;
						if (draggingThis && drawSize > 0) {
							var drawBytesD2 = drawSize * logical;
							var fsUnusedBytes = Math.max(0, Number(p.fs_size_bytes || 0) - fsUsed);
							fsUnusedPct = drawBytesD2 > 0 ? Math.min(100 - Math.max(0, Math.min(100, usedPct)), (fsUnusedBytes / drawBytesD2) * 100) : 0;
						} else {
							fsUnusedPct = 100 - Math.max(0, Math.min(100, usedPct));
						}
						fsUnusedBar.style.width = Math.max(0, fsUnusedPct) + '%';
						fsBar.appendChild(fsUsedBar);
						fsBar.appendChild(fsUnusedBar);
						block.appendChild(fsBar);
					}
					block.draggable = true;
					block.ondragstart = function (ev) {
						state.mapDragActive = true;
						hideHoverTooltip();
						ev.dataTransfer.setData('text/plain', 'partition:' + p.number);
						ev.dataTransfer.setData('part-size', String(p.size || 0));
					};
					block.ondragend = function () {
						state.mapDragActive = false;
						hideHoverTooltip();
					};
					var leftHandle = document.createElement('div');
					leftHandle.className = 'pcgi-resize-handle pcgi-resize-handle-left';
					leftHandle.title = 'Drag left edge to queue move/resize';
					leftHandle.onmousedown = function (ev) {
						ev.stopPropagation();
						startResize(ev, dev, idx, 'left');
					};
					block.appendChild(leftHandle);
					var handle = document.createElement('div');
					handle.className = 'pcgi-resize-handle';
					handle.title = 'Drag to queue resize';
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
					block.ondragover = function (ev) { ev.preventDefault(); };
					block.ondrop = function (ev) {
						ev.preventDefault();
						state.mapDragActive = false;
						hideHoverTooltip();
						var data = ev.dataTransfer.getData('text/plain');
						if (data === 'new-partition') {
							document.getElementById('newStartSector').value = String(p.start);
							document.getElementById('newEndSector').value = String(p.end);
							refreshSectorHumanFields();
							updateMapStatus('New partition range loaded from dropped free segment.');
							showToast('New partition range pre-filled from free segment.', 'info', 1800);
						} else if (data.indexOf('partition:') === 0) {
							var pnum = data.split(':')[1];
							var moveSource = null;
							for (var m = 0; m < dev.partitions.length; m++) {
								if (dev.partitions[m].kind === 'partition' && String(dev.partitions[m].number) === String(pnum)) {
									moveSource = dev.partitions[m];
									break;
								}
							}
							if (!moveSource) {
								showToast(t('tContextUnavailable'), 'warn');
								return;
							}
							var moveSize = Number(moveSource.size || 0);
							var targetStart = Number(p.start || 0);
							var targetEnd = targetStart + moveSize - 1;
							if (targetEnd > Number(p.end || 0)) {
								showToast(t('tMoveNoSpace'), 'error');
								return;
							}
							if (Number(moveSource.start) === targetStart && Number(moveSource.end) === targetEnd) {
								showToast(t('tMoveSame'), 'warn');
								return;
							}
							queueOpWithConfirm(
								'move_partition',
								{ device: dev.path, partnum: moveSource.number, start_sector: targetStart, end_sector: targetEnd },
								'Move p' + moveSource.number + ' on ' + dev.path + ' to [' + targetStart + 's..' + targetEnd + 's]',
								t('confirmMove'),
								t('confirmMoveMsg')
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
		if (prevSeg) minStart = Number(prevSeg.end) + 1;
		if (nextSeg) maxEnd = Number(nextSeg.start) - 1;
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
				showToast('Cannot shrink partition #' + part.number + ': filesystem ' + rawFsType + ' is not supported for resize.', 'error', 4200);
				return;
			}
			if (fsCap.hasTool === false) {
				showToast('Cannot shrink partition #' + part.number + ': missing resize tool (' + fsCap.toolHint + ').', 'error', 4200);
				return;
			}
			if (!queueFs) {
				queueFs = true;
				showToast('Filesystem resize enabled automatically for shrink operation.', 'warn', 3200);
			}
		}

		if (!isShrink && hasFilesystem) {
			if (!fsCap.supported) {
				showToast('Warning: growing partition with filesystem ' + rawFsType + ' has no supported resize. Filesystem resize will be skipped.', 'warn', 3800);
				queueFs = false;
			} else if (fsCap.hasTool === false) {
				showToast('Warning: missing tool ' + fsCap.toolHint + '. Partition growth will be queued without filesystem resize.', 'warn', 3800);
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
			'Queue resize plan for partition #' + part.number + ' on ' + dev.path + '?'
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

			showToast('Resize plan queued (' + (isShrink ? 'shrink' : 'grow') + ').', 'success', 2200);
		});
	}


        function queueMoveResizePlan(dev, part, newStart, resizeFs) {
                if (!dev || !part) {
                        showToast(t('tContextUnavailable'), 'warn');
                        return;
                }

                var oldStart = Number(part.start || 0);
                var end = Number(part.end || 0);
                var targetStart = Number(newStart || 0);
                if (!isFinite(targetStart) || targetStart <= 0 || targetStart >= end) {
                        showToast('Invalid start sector for resize.', 'warn');
                        return;
                }
                if (targetStart === oldStart) {
                        showToast(t('tMoveSame'), 'warn');
                        return;
                }

                var isShrink = targetStart > oldStart;
                var queueFs = String(resizeFs || 'no') === 'yes';
                var rawFsType = String(part.fs || '').toLowerCase().trim();
                var hasFilesystem = !!(rawFsType && rawFsType !== 'unknown' && rawFsType !== '-');
                var fsCap = hasFilesystem ? getFsResizeCapability(rawFsType, isShrink ? 'shrink' : 'grow') : { supported: true, hasTool: true, canResize: true, fsType: '', toolHint: '' };
                var fsType = fsCap.fsType || normalizeFsTypeForResize(rawFsType);

                if (isShrink && hasFilesystem) {
                        if (!fsCap.supported) {
                                showToast('Cannot shrink partition #' + part.number + ': filesystem ' + rawFsType + ' is not supported for resize.', 'error', 4200);
                                return;
                        }
                        if (fsCap.hasTool === false) {
                                showToast('Cannot shrink partition #' + part.number + ': missing resize tool (' + fsCap.toolHint + ').', 'error', 4200);
                                return;
                        }
                        if (!queueFs) {
                                queueFs = true;
                                showToast('Filesystem resize enabled automatically for shrink operation.', 'warn', 3200);
                        }
                }

                if (!isShrink && hasFilesystem) {
                        if (!fsCap.supported) {
                                showToast('Warning: growing partition with filesystem ' + rawFsType + ' has no supported resize. Filesystem resize will be skipped.', 'warn', 3800);
                                queueFs = false;
                        } else if (fsCap.hasTool === false) {
                                showToast('Warning: missing tool ' + fsCap.toolHint + '. Partition growth will be queued without filesystem resize.', 'warn', 3800);
                                queueFs = false;
                        }
                }

                if (queueFs && !hasFilesystem) queueFs = false;
                if (queueFs && !fsType) queueFs = false;

                var logical = Number(dev.logical_sector_size || 512);
                var targetBytes = Math.max(1, (end - targetStart + 1) * logical);
                var targetKib = Math.max(1, Math.floor(targetBytes / 1024));
                var isMounted = !!(part.mountpoint && String(part.mountpoint).trim() && String(part.mountpoint).trim() !== '-');
                var mountpoint = isMounted ? String(part.mountpoint).trim() : '';
                var partitionPath = String(part.path || '');

                return showConfirmModal(
                        t('confirmAction'),
                        'Queue resize plan for partition #' + part.number + ' on ' + dev.path + ' (left edge)?'
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

                        var mpParams = {
                                device: dev.path,
                                partnum: part.number,
                                start_sector: String(targetStart),
                                end_sector: String(end)
                        };
                        queueOp(
                                'move_partition',
                                mpParams,
                                'Move/resize partition #' + part.number + ' on ' + dev.path + ' to [' + targetStart + 's..' + end + 's]',
                                buildCommandPreview('move_partition', mpParams),
                                true
                        );

                        if (queueFs && !isShrink) {
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

                        showToast('Resize plan queued (' + (isShrink ? 'shrink' : 'grow') + ', left edge).', 'success', 2200);
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

		queueOpWithConfirm(
			'move_partition',
			{ device: dev.path, partnum: source.number, start_sector: targetStart, end_sector: targetEnd },
			'Move partition #' + source.number + ' on ' + dev.path + ' to [' + targetStart + 's..' + targetEnd + 's]',
			t('confirmMove'),
			t('confirmMoveMsg')
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
		state.selectedPart = null;
		state.selectedComponent = null;
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
				showToast(t('tMapError') + ': ' + err.message, 'error', 3500);
			});
	}

	function queueCreatePartition() {
		var dev = state.selectedDevice;
		if (!dev) {
			showToast(t('tNoDevice'), 'warn');
			return;
		}
		var start = document.getElementById('newStartSector').value.trim();
		var end = document.getElementById('newEndSector').value.trim();
		if (!start || !end) {
			showToast(t('tNeedStartEnd'), 'warn');
			return;
		}
		var role = document.getElementById('newPartRole').value;
		var fsHint = document.getElementById('newFsHint').value;
		var partName = document.getElementById('newPartName').value.trim();
		queueOpWithConfirm(
			'create_partition',
			{ device: dev, start_sector: start, end_sector: end, part_role: role, fs_hint: fsHint, part_name: partName },
			'Create partition on ' + dev + ' [' + start + 's..' + end + 's]',
			t('confirmCreate'),
			t('confirmCreateMsg')
		);
	}

	function queueDeletePartition() {
		if (!state.selectedPart || !state.selectedPart.number) {
			showToast(t('tNoPartition'), 'warn');
			return;
		}
		queueOpWithConfirm(
			'delete_partition',
			{ device: state.selectedDevice, partnum: state.selectedPart.number },
			'Delete partition p' + state.selectedPart.number + ' on ' + state.selectedDevice,
			t('confirmDelete'),
			t('confirmDeleteMsg')
		);
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

		showConfirmModal(t('confirmDelete'), 'Queue deletion of ALL partitions on ' + baseDev.path + '?')
			.then(function (ok) {
				if (!ok) return;
				parts.sort(function (a, b) {
					return Number(b.number || 0) - Number(a.number || 0);
				});

				for (var j = 0; j < parts.length; j++) {
					var params = { device: baseDev.path, partnum: parts[j].number };
					queueOp(
						'delete_partition',
						params,
						'Delete partition p' + parts[j].number + ' on ' + baseDev.path,
						buildCommandPreview('delete_partition', params),
						true
					);
				}
				showToast('Queued delete-all partitions on ' + baseDev.path + '.', 'warn', 2800);
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
		var part = document.getElementById('fsPartitionPath').value.trim();
		if (!part) {
			showToast(t('tNeedPartPath'), 'warn');
			return;
		}
		var fsType = document.getElementById('fsTypeSelect').value;
		if (fsType === 'auto') {
			showToast(t('tNeedMkfsType'), 'warn');
			return;
		}
		queueOpWithConfirm(
			'create_filesystem',
			{
				partition: part,
				fs_type: fsType,
				label: document.getElementById('fsLabelInput').value.trim(),
				extra_opts: document.getElementById('extraOptsInput').value.trim()
			},
			'Make filesystem ' + fsType + ' on ' + part,
			t('confirmMkfs'),
			t('confirmMkfsMsg')
		);
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
			'Filesystem label update will be queued.'
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
			'Partition name update will be queued.'
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
			'Partition flag update will be queued.'
		);
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
			repair ? t('confirmRepairMsg') : 'Filesystem check will be queued.'
		);
	}

	function clearQueue() {
		state.queue = [];
		renderQueue();
		syncSelectionWithPreview();
		renderMap();
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
			document.getElementById('applyQueueBtn').disabled = true;
			logTo('cmdOutput', 'Applying ' + state.queue.length + ' queued operation(s)...', false);

			var i = 0;
			function runNext() {
				if (i >= state.queue.length) {
					logTo('cmdOutput', t('tQueueApplied'), false);
					showToast(t('tQueueApplied'), 'success', 2600);
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
				params.ack = ack;
				if (op.commandPreview) {
					params.command_preview = op.commandPreview;
				}

				callApi(op.action, params)
					.then(function (res) {
						var hdr = '[' + op.action + '] ' + (res.message || '');
						logTo('cmdOutput', hdr + '\nrc=' + (res.rc || 0) + '\n' + (res.output || ''), false);
						if (!res.success) {
							logTo('cmdOutput', 'Queue stopped due to failure at step ' + (i + 1) + '.', false);
							showToast('Queue stopped at step ' + (i + 1), 'error', 3400);
							document.getElementById('applyQueueBtn').disabled = false;
							return;
						}
						i++;
						runNext();
					})
					.catch(function (err) {
						logTo('cmdOutput', 'Queue error at step ' + (i + 1) + ': ' + err.message, false);
						showToast('Queue error: ' + err.message, 'error', 3600);
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
		callApi(action, { device: dev })
			.then(function (res) {
				var msg = '[' + action + '] ' + (res.message || '') +
				          '\nrc=' + (res.rc || 0) + '\n' + (res.output || '');
				logTo('diagOutput', msg, true);
				if (diagEl) diagEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
			})
			.catch(function (err) {
				logTo('diagOutput', 'Diagnostics error: ' + err.message, true);
				showToast('Diagnostics error: ' + err.message, 'error', 3300);
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
			showToast(t('tMetaLoaded'), 'success', 2200);
		}).catch(function (err) {
			document.getElementById('metaStatus').textContent = 'Error: ' + err.message;
			renderMetadata(null);
			logTo('cmdOutput', 'Metadata error: ' + err.message, false);
			showToast('Metadata error: ' + err.message, 'error', 3200);
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
				showToast('Tool analysis error: ' + err.message, 'error', 3200);
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
			ev.preventDefault();
			if (ev.altKey) {
				queueMoveSelectedByDirection('left');
			} else {
				navigateSelectedPartition('left');
			}
			return;
		}
		if (ev.key === 'ArrowRight') {
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
	window.queueDeletePartition = queueDeletePartition;
	window.queueResizePartitionFromInputs = queueResizePartitionFromInputs;
	window.queueMkfs = queueMkfs;
	window.queueSetLabel = queueSetLabel;
	window.queueRenamePartition = queueRenamePartition;
	window.queueSetFlag = queueSetFlag;
	window.queueMountPartition = queueMountPartition;
	window.queueUnmountPartition = queueUnmountPartition;
	window.runFsck = runFsck;
	window.clearQueue = clearQueue;
	window.applyQueue = applyQueue;
	window.runDiagnostics = runDiagnostics;
	window.analyzeTools = analyzeTools;
	window.loadPartitionMetadata = loadPartitionMetadata;
	window.toggleToolchainSection = toggleToolchainSection;

	state.language = detectLanguage();
	document.getElementById('langSelect').value = state.language;
	state.dryRun = false;
	applyTranslations();
	var toolchainSection = document.getElementById('toolchainSection');
	if (toolchainSection) toolchainSection.style.display = 'none';
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
	refreshSectorHumanFields();
	refreshDevices();
	analyzeTools();
})();
</script>
EOF

