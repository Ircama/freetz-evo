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
	printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' -e ':a;N;$!ba;s/\n/\\n/g' -e 's/\r/\\r/g'
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
	CMD_MKFS_EXFAT=$(find_cmd mkfs.exfat mkexfatfs)
	CMD_FSCK_EXFAT=$(find_cmd fsck.exfat exfatfsck)
	CMD_EXFATLABEL=$(find_cmd exfatlabel tune.exfat)
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
	CMD_MOUNT=$(find_cmd mount)
	CMD_UMOUNT=$(find_cmd umount)
}

run_exfat_label() {
	_partition="$1"
	_label="$2"

	[ -n "$CMD_EXFATLABEL" ] || return 127

	case "$(basename "$CMD_EXFATLABEL")" in
		tune.exfat)
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

			if [ "$_pid" = "free" ]; then
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
		if [ "$_resize_fs" = "yes" ]; then
			_preview_cmd="$_preview_cmd
# filesystem resize requested: backend auto-detects FS and runs ext/ntfs resize tools when available"
		fi
		emit_dry_run_result "partition resize" "$_preview_cmd"
		return
	fi

	_out=$($CMD_PARTED -s "$_device" unit s resizepart "$_partnum" "${_end_sector}s" 2>&1)
	_rc=$?

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
				*)
					_out="$_out\n\nWarning: filesystem resize supports ext2/3/4 and NTFS only (detected: ${_fstype:-unknown})"
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
				if [ -n "$_extra_opts" ]; then
					set -- $_extra_opts
					_out=$($CMD_E2FSCK -f -p "$@" "$_partition" 2>&1)
				else
					_out=$($CMD_E2FSCK -f -p "$_partition" 2>&1)
				fi
			else
				if [ -n "$_extra_opts" ]; then
					set -- $_extra_opts
					_out=$($CMD_E2FSCK -f -n "$@" "$_partition" 2>&1)
				else
					_out=$($CMD_E2FSCK -f -n "$_partition" 2>&1)
				fi
			fi
			_rc=$?
			if [ "$_rc" -eq 0 ] || [ "$_rc" -eq 1 ] || [ "$_rc" -eq 2 ]; then
				emit_cmd_result true "$_rc" "Filesystem check completed" "$_out"
			else
				emit_cmd_result false "$_rc" "Filesystem check reported errors" "$_out"
			fi
			;;
		fat|fat12|fat16|fat32|vfat)
			[ -n "$CMD_FSCK_FAT" ] || { emit_json_error "fsck.fat not available"; return; }
			if [ "$_repair" = "yes" ]; then
				if [ -n "$_extra_opts" ]; then
					set -- $_extra_opts
					_out=$($CMD_FSCK_FAT -a "$@" "$_partition" 2>&1)
				else
					_out=$($CMD_FSCK_FAT -a "$_partition" 2>&1)
				fi
			else
				if [ -n "$_extra_opts" ]; then
					set -- $_extra_opts
					_out=$($CMD_FSCK_FAT -n "$@" "$_partition" 2>&1)
				else
					_out=$($CMD_FSCK_FAT -n "$_partition" 2>&1)
				fi
			fi
			_rc=$?
			if [ "$_rc" -eq 0 ] || [ "$_rc" -eq 1 ]; then
				emit_cmd_result true "$_rc" "Filesystem check completed" "$_out"
			else
				emit_cmd_result false "$_rc" "Filesystem check reported errors" "$_out"
			fi
			;;
		exfat)
			[ -n "$CMD_FSCK_EXFAT" ] || { emit_json_error "fsck.exfat not available"; return; }
			if [ "$_repair" = "yes" ]; then
				if [ -n "$_extra_opts" ]; then
					set -- $_extra_opts
					_out=$($CMD_FSCK_EXFAT "$@" "$_partition" 2>&1)
				else
					_out=$($CMD_FSCK_EXFAT "$_partition" 2>&1)
				fi
			else
				if [ -n "$_extra_opts" ]; then
					set -- $_extra_opts
					_out=$($CMD_FSCK_EXFAT -n "$@" "$_partition" 2>&1)
				else
					_out=$($CMD_FSCK_EXFAT -n "$_partition" 2>&1)
				fi
			fi
			_rc=$?
			if [ "$_rc" -eq 0 ] || [ "$_rc" -eq 1 ] || [ "$_rc" -eq 2 ]; then
				emit_cmd_result true "$_rc" "exFAT check completed" "$_out"
			else
				emit_cmd_result false "$_rc" "exFAT check reported errors" "$_out"
			fi
			;;
		ntfs)
			if [ -n "$CMD_NTFSFIX" ]; then
				if [ "$_repair" = "yes" ]; then
					if [ -n "$_extra_opts" ]; then
						set -- $_extra_opts
						_out=$($CMD_NTFSFIX "$@" "$_partition" 2>&1)
					else
						_out=$($CMD_NTFSFIX "$_partition" 2>&1)
					fi
				else
					if [ -n "$_extra_opts" ]; then
						set -- $_extra_opts
						_out=$($CMD_NTFSFIX -n "$@" "$_partition" 2>&1)
					else
						_out=$($CMD_NTFSFIX -n "$_partition" 2>&1)
					fi
				fi
				_rc=$?
				emit_cmd_result true "$_rc" "NTFS check completed" "$_out"
			elif [ -n "$CMD_NTFSINFO" ]; then
				_out=$($CMD_NTFSINFO -m "$_partition" 2>&1)
				_rc=$?
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
		emit_dry_run_result "smart diagnostics" "smartctl -H -A $_device"
		return
	fi

	_out=$($CMD_SMARTCTL -H -A "$_device" 2>&1 | sed -n '1,220p')
	_rc=$?
	if [ -n "$_out" ]; then
		emit_cmd_result true "$_rc" "SMART report collected" "$_out"
	else
		emit_cmd_result false "$_rc" "SMART report failed" "$_out"
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

sec_begin "Safety and operation mode"
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
			<div>
				<label for="dryRunToggle"><input id="dryRunToggle" type="checkbox"> <span id="i18nDryRunLabel">Dry-run mode (log only, do not execute)</span></label>
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
	position: fixed;
	display: none;
	min-width: 220px;
	background: #fff;
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
	padding: 8px 10px;
	font-size: 12px;
	text-align: left;
	cursor: pointer;
}
.pcgi-context-item:hover {
	background: #eef4fb;
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
	height: 88px;
	border: 1px solid #9ba8b6;
	background: linear-gradient(180deg, #f5f8fb 0%, #e8eef5 100%);
	overflow: hidden;
	border-radius: 4px;
}
.pcgi-block {
	position: absolute;
	top: 8px;
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
	left: 2px;
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
.pcgi-map-legend {
	font-size: 11px;
	margin-top: 6px;
	color: #4f5b67;
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
</style>

<div class="pcgi-toolbar">
	<button type="button" onclick="refreshDevices()" id="refreshMapBtn">Refresh map</button>
	<label for="deviceSelect">Device:</label>
	<select id="deviceSelect" onchange="onDeviceChange()"></select>
	<button type="button" onclick="runDiagnostics('reload_table')" id="partprobeBtn">Run partprobe</button>
	<button type="button" onclick="analyzeTools()" id="analyzeBtn">Analyze toolchain</button>
	<button type="button" onclick="loadPartitionMetadata()" id="metaBtn">Partition metadata</button>
	<span id="mapStatus" class="pcgi-small"></span>
</div>

<div class="pcgi-toolbar">
	<span id="newPartChip" class="pcgi-chip" draggable="true" title="Drag on a free segment to prefill new partition range">New partition</span>
	<span id="i18nDragHint" class="pcgi-small">Drag this chip into a free region. Drag the right edge of a partition to queue resize. Drag partitions into free regions to queue move.</span>
</div>

<div id="partitionMap"></div>
<div id="mapLegend" class="pcgi-map-legend"></div>

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
		<label id="i18nNewEndLabel">New end sector</label>
		<input id="newEndSector" type="text" placeholder="e.g. 1023999">
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
		<label id="i18nFsHintLabel">FS hint</label>
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
		<label id="i18nResizeFsLabel">Resize filesystem too</label>
		<select id="resizeFsSelect">
			<option value="no">no</option>
			<option value="yes">yes (ext/ntfs)</option>
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
<div id="metaGraph"></div>
<pre id="metaRawOutput" class="pcgi-log"></pre>
EOF
sec_end

sec_begin "Diagnostics (hdparm, SMART, GPT)"
cat <<'EOF'
<div class="pcgi-toolbar">
	<button type="button" onclick="runDiagnostics('smart_info')">SMART health</button>
	<button type="button" onclick="runDiagnostics('hdparm_info')">hdparm identify</button>
	<button type="button" onclick="runDiagnostics('gpt_info')">GPT summary</button>
</div>
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

sec_begin "Toolchain analysis"
cat <<'EOF'
<pre id="toolsOutput" class="pcgi-log"></pre>

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
sec_end

cat <<'EOF'
<script src="/ace/ace.js"></script>
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
			dragHint: 'Drag this chip into a free region. Drag the right edge of a partition to queue resize. Drag partitions into free regions to queue move.',
			missingCommandsLabel: 'Missing commands:',
			languageLabel: 'Language',
			usbOnlyLabel: 'Device filter',
			dryRunLabel: 'Dry-run mode (log only, do not execute)',
			helperTitle: 'Keyboard shortcuts and workflow',
			helperText: 'Ctrl+R: refresh map\nCtrl+Shift+A: analyze toolchain\nCtrl+M: load partition metadata\nCtrl+Enter: apply operation queue\nDelete: queue delete selected partition\nF1 or ?: open this help\nRight click on partition: context menu actions\nDrag partition edge: queue resize\nDrag partition to free area: queue move',
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
			tMapLoading: 'Loading device map...',
			tMapError: 'Map load error',
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
			dragHint: 'Trascina questo chip su spazio libero. Trascina il bordo destro di una partizione per accodare resize. Trascina una partizione su spazio libero per accodare move.',
			missingCommandsLabel: 'Comandi mancanti:',
			languageLabel: 'Lingua',
			usbOnlyLabel: 'Filtro dispositivi',
			dryRunLabel: 'Modalita dry-run (solo log, nessuna esecuzione)',
			helperTitle: 'Scorciatoie da tastiera e workflow',
			helperText: 'Ctrl+R: aggiorna mappa\nCtrl+Shift+A: analizza toolchain\nCtrl+M: carica metadati partizione\nCtrl+Invio: applica coda operazioni\nCanc: accoda eliminazione partizione selezionata\nF1 o ?: apri aiuto\nClick destro sulla partizione: menu contestuale\nTrascina bordo partizione: accoda resize\nTrascina partizione su spazio libero: accoda move',
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
			tMapLoading: 'Caricamento mappa dispositivi...',
			tMapError: 'Errore caricamento mappa',
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
			dragHint: 'Chip in freien Bereich ziehen. Rechten Rand einer Partition ziehen fuer Resize. Partition in freien Bereich ziehen fuer Move.',
			missingCommandsLabel: 'Fehlende Befehle:',
			languageLabel: 'Sprache',
			usbOnlyLabel: 'Geraetefilter',
			dryRunLabel: 'Dry-run Modus (nur Log, keine Ausfuehrung)',
			helperTitle: 'Tastenkuerzel und Ablauf',
			helperText: 'Ctrl+R: Karte aktualisieren\nCtrl+Shift+A: Toolchain analysieren\nCtrl+M: Partitions-Metadaten laden\nCtrl+Enter: Queue anwenden\nEntf: Loeschen der gewaehlten Partition in Queue\nF1 oder ?: Hilfe oeffnen\nRechtsklick auf Partition: Kontextmenue\nPartitionsrand ziehen: Resize in Queue\nPartition auf freien Bereich ziehen: Move in Queue',
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
			tMapLoading: 'Geraetekarte wird geladen...',
			tMapError: 'Fehler beim Laden der Karte',
			btnConfirm: 'Bestaetigen',
			btnCancel: 'Abbrechen',
			btnClose: 'Schliessen',
			btnValidateQueue: 'Bestaetigen und queue'
		}
	};

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
		contextPart: null,
		dryRun: false,
		aceEditor: null
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
			i18nMissingCommandsLabel: 'missingCommandsLabel',
			i18nLanguageLabel: 'languageLabel',
			i18nUsbOnlyLabel: 'usbOnlyLabel',
			i18nDryRunLabel: 'dryRunLabel'
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
		var usbSel = document.getElementById('usbOnlySelect');
		if (usbSel && usbSel.options.length >= 2) {
			usbSel.options[0].text = state.language === 'it' ? 'Tutti i dispositivi a blocchi' : (state.language === 'de' ? 'Alle Blockgeraete' : 'All block devices');
			usbSel.options[1].text = state.language === 'it' ? 'Solo dispositivi USB' : (state.language === 'de' ? 'Nur USB-Geraete' : 'USB devices only');
		}
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
		var endPos = -1;
		for (var i = firstBrace; i < text.length; i++) {
			if (text[i] === '{') braceCount++;
			if (text[i] === '}') {
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
		if (!available['mkntfs']) featureIssues.push('NTFS filesystem creation');
		if (!available['ntfsfix']) featureIssues.push('NTFS check/repair');
		if (!available['ntfsinfo']) featureIssues.push('NTFS metadata inspection');
		if (!available['ntfslabel']) featureIssues.push('NTFS label updates');
		if (!available['mount']) featureIssues.push('mount operations');
		if (!available['umount']) featureIssues.push('unmount operations');
		if (!available['smartctl']) featureIssues.push('SMART diagnostics');
		if (!available['hdparm']) featureIssues.push('drive identify (hdparm)');
		if (!available['gdisk'] && !available['sgdisk']) featureIssues.push('GPT diagnostics');

		return {
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
				txt += '\n# backend will auto-detect filesystem and run ext/ntfs resize tools when available';
			}
			return txt;
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
			return '# fs check preview\n# fs_type=' + v(params.fs_type) + ' repair=' + v(params.repair) + ' target=' + v(params.partition);
		}
		if (action === 'smart_info') return 'smartctl -H -A ' + v(params.device);
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

	function queueOp(action, params, label, commandPreview) {
		state.queue.push({ action: action, params: params, label: label, commandPreview: commandPreview || '' });
		renderQueue();
		showToast(t('tQueued') + ' ' + label, 'info', 2400);
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

	function updateMapStatus(txt) {
		document.getElementById('mapStatus').textContent = txt || '';
	}

	function selectPartition(part) {
		state.selectedPart = part;
		state.selectedComponent = part ? { kind: 'partition', number: Number(part.number || 0) } : null;
		document.getElementById('selectedPartNum').value = part ? String(part.number || '') : '';
		document.getElementById('selectedPartPath').value = part ? (part.path || '') : '';
		document.getElementById('fsPartitionPath').value = part ? (part.path || '') : '';
		document.getElementById('mountpointInput').value = part && part.mountpoint ? part.mountpoint : '';
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
		if (seg) {
			document.getElementById('newStartSector').value = String(seg.start || '');
			document.getElementById('newEndSector').value = String(seg.end || '');
			updateMapStatus('Selected unallocated segment [' + seg.start + 's..' + seg.end + 's].');
		}
		renderMap();
	}

	function hideContextMenu() {
		var menu = document.getElementById('partContextMenu');
		if (menu) menu.style.display = 'none';
	}

	function showContextMenu(part, ev) {
		var menu = document.getElementById('partContextMenu');
		if (!menu || !part) return;
		state.contextPart = part;
		menu.innerHTML = '';

		var items = [
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

		for (var i = 0; i < items.length; i++) {
			(function (item) {
				var btn = document.createElement('button');
				btn.type = 'button';
				btn.className = 'pcgi-context-item';
				btn.textContent = item.label;
				btn.onclick = function () {
					hideContextMenu();
					handleContextAction(item.id, part);
				};
				menu.appendChild(btn);
			})(items[i]);
		}

		menu.style.display = 'block';
		menu.style.left = Math.min(ev.clientX, window.innerWidth - 240) + 'px';
		menu.style.top = Math.min(ev.clientY, window.innerHeight - 280) + 'px';
	}

	function handleContextAction(action, part) {
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
		var dev = getSelectedDeviceData();
		var map = document.getElementById('partitionMap');
		var legend = document.getElementById('mapLegend');
		map.innerHTML = '';
		legend.textContent = '';
		if (!dev) {
			legend.textContent = 'No device selected.';
			return;
		}

		var total = Number(dev.total_sectors || 0);
		var logical = Number(dev.logical_sector_size || 512);
		if (!total || total <= 0) {
			legend.textContent = 'Unable to render this device.';
			return;
		}

		legend.textContent = dev.path + ' | table=' + (dev.table || 'unknown') + ' | model=' + (dev.model || '-') + ' | size=' + humanBytes(total * logical);
		if (dev.transport) legend.textContent += ' | transport=' + dev.transport;
		if (dev.vendor) legend.textContent += ' | vendor=' + dev.vendor;
		if (dev.serial) legend.textContent += ' | serial=' + dev.serial;

		for (var i = 0; i < dev.partitions.length; i++) {
			(function (idx) {
				var p = dev.partitions[idx];
				var leftPct = (Number(p.start) / total) * 100;
				var widthPct = (Number(p.size) / total) * 100;
				if (widthPct < 0.4) widthPct = 0.4;
				var block = document.createElement('div');
				block.className = 'pcgi-block ' + (p.kind === 'free' ? 'free' : 'part');
				block.style.left = leftPct + '%';
				block.style.width = widthPct + '%';
				if (state.selectedComponent && p.kind === 'partition' && state.selectedComponent.kind === 'partition' && Number(p.number) === Number(state.selectedComponent.number)) {
					block.className += ' selected';
				}
				if (state.selectedComponent && p.kind === 'free' && state.selectedComponent.kind === 'free' && Number(p.start) === Number(state.selectedComponent.start) && Number(p.end) === Number(state.selectedComponent.end)) {
					block.className += ' selected';
				}

				if (p.kind === 'partition') {
					var fsUsed = Number(p.fs_used_bytes || 0);
					var fsAvail = Number(p.fs_avail_bytes || 0);
					var usedPct = Number(p.used_pct || 0);
					block.title = p.path + '\nfs=' + (p.fs || '-') + '\nname=' + (p.name || '-') + '\nlabel=' + (p.label || '-') + '\nflags=' + (p.flags || '-') + '\nused=' + humanBytes(fsUsed) + '\nunused=' + humanBytes(fsAvail) + (p.mountpoint ? ('\nmounted at ' + p.mountpoint) : '');
					block.textContent = 'p' + p.number + ' ' + (p.name || p.fs || '-');
					block.onclick = function () { selectPartition(p); };
					block.oncontextmenu = function (ev) {
						ev.preventDefault();
						showContextMenu(p, ev);
					};
					if (Number(p.fs_size_bytes || 0) > 0) {
						var fsBar = document.createElement('div');
						fsBar.className = 'pcgi-part-fsbar';
						var fsUsedBar = document.createElement('div');
						fsUsedBar.className = 'pcgi-part-fsbar-used';
						fsUsedBar.style.width = Math.max(0, Math.min(100, usedPct)) + '%';
						var fsUnusedBar = document.createElement('div');
						fsUnusedBar.className = 'pcgi-part-fsbar-unused';
						fsUnusedBar.style.width = (100 - Math.max(0, Math.min(100, usedPct))) + '%';
						fsBar.appendChild(fsUsedBar);
						fsBar.appendChild(fsUnusedBar);
						block.appendChild(fsBar);
					}
					block.draggable = true;
					block.ondragstart = function (ev) {
						ev.dataTransfer.setData('text/plain', 'partition:' + p.number);
						ev.dataTransfer.setData('part-size', String(p.size || 0));
					};
					var handle = document.createElement('div');
					handle.className = 'pcgi-resize-handle';
					handle.title = 'Drag to queue resize';
					handle.onmousedown = function (ev) { startResize(ev, dev, idx); };
					block.appendChild(handle);
				} else {
					block.title = 'Unallocated space: ' + humanBytes(Number(p.size) * logical) + '\nRange: [' + p.start + 's..' + p.end + 's]';
					block.textContent = 'unallocated';
					block.onclick = function () { selectUnallocatedSegment(p); };
					block.ondragover = function (ev) { ev.preventDefault(); };
					block.ondrop = function (ev) {
						ev.preventDefault();
						var data = ev.dataTransfer.getData('text/plain');
						if (data === 'new-partition') {
							document.getElementById('newStartSector').value = String(p.start);
							document.getElementById('newEndSector').value = String(p.end);
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

	function startResize(ev, dev, partIndex) {
		ev.preventDefault();
		var part = dev.partitions[partIndex];
		if (!part || part.kind !== 'partition') return;

		var map = document.getElementById('partitionMap');
		var rect = map.getBoundingClientRect();
		var total = Number(dev.total_sectors || 0);
		if (!total) return;

		var minEnd = Number(part.start) + 2048;
		var maxEnd = total - 1;
		for (var i = 0; i < dev.partitions.length; i++) {
			var c = dev.partitions[i];
			if (Number(c.start) > Number(part.end)) {
				maxEnd = Number(c.start) - 1;
				break;
			}
		}

		state.dragCtx = {
			dev: dev,
			part: part,
			mapRect: rect,
			total: total,
			minEnd: minEnd,
			maxEnd: maxEnd,
			currentEnd: Number(part.end)
		};

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
		if (sec < d.minEnd) sec = d.minEnd;
		if (sec > d.maxEnd) sec = d.maxEnd;
		d.currentEnd = sec;
		updateMapStatus('Resize preview: p' + d.part.number + ' end -> ' + sec + 's');
	}

	function onResizeUp() {
		if (!state.dragCtx) return;
		var d = state.dragCtx;
		document.removeEventListener('mousemove', onResizeMove);
		document.removeEventListener('mouseup', onResizeUp);
		state.dragCtx = null;
		updateMapStatus('');

		if (Number(d.currentEnd) !== Number(d.part.end)) {
			queueOpWithConfirm(
				'resize_partition',
				{
					device: d.dev.path,
					partnum: d.part.number,
					end_sector: d.currentEnd,
					resize_fs: 'no'
				},
				'Resize p' + d.part.number + ' on ' + d.dev.path + ' to end=' + d.currentEnd + 's',
				t('confirmAction'),
				'Resize operation will be queued.'
			);
			document.getElementById('resizeEndSector').value = String(d.currentEnd);
			selectPartition(d.part);
		}
	}

	function onDeviceChange() {
		var sel = document.getElementById('deviceSelect');
		state.selectedDevice = sel.value;
		state.selectedPart = null;
		state.selectedComponent = null;
		renderMap();
	}

	function refreshDevices() {
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
				renderMap();
				updateMapStatus(t('tMapLoaded') + ' (' + state.devices.length + ' device(s)).');
			})
			.catch(function (err) {
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

	function queueResizePartitionFromInputs() {
		var partnum = document.getElementById('selectedPartNum').value.trim();
		var endSector = document.getElementById('resizeEndSector').value.trim();
		if (!partnum || !endSector) {
			showToast(t('tNeedResizeInput'), 'warn');
			return;
		}
		queueOpWithConfirm(
			'resize_partition',
			{
				device: state.selectedDevice,
				partnum: partnum,
				end_sector: endSector,
				resize_fs: document.getElementById('resizeFsSelect').value
			},
			'Resize partition p' + partnum + ' on ' + state.selectedDevice + ' to end=' + endSector + 's',
			t('confirmAction'),
			'Resize operation will be queued.'
		);
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

	function runFsck(repair) {
		var part = document.getElementById('fsPartitionPath').value.trim();
		if (!part) {
			showToast(t('tNeedPartPath'), 'warn');
			return;
		}
		function doRun() {
			var previewParams = {
				partition: part,
				fs_type: document.getElementById('fsTypeSelect').value,
				repair: repair ? 'yes' : 'no',
				extra_opts: document.getElementById('extraOptsInput').value.trim()
			};
			showCommandPreviewModal('check_filesystem', previewParams, 'Filesystem check', t('confirmAction'), t('cmdPreviewHint')).then(function (previewText) {
				if (previewText === null) return;
			callApi('check_filesystem', {
				partition: part,
				fs_type: document.getElementById('fsTypeSelect').value,
				repair: repair ? 'yes' : 'no',
				extra_opts: document.getElementById('extraOptsInput').value.trim(),
				command_preview: previewText
			}).then(function (res) {
				logTo('cmdOutput', '[check_filesystem] ' + (res.message || '') + '\nrc=' + (res.rc || 0) + '\n' + (res.output || ''), false);
				showToast((res.success ? 'OK: ' : 'Warning: ') + (res.message || 'check done'), res.success ? 'success' : 'warn', 2800);
			}).catch(function (err) {
				logTo('cmdOutput', 'Filesystem check error: ' + err.message, false);
				showToast('Filesystem check error: ' + err.message, 'error', 3200);
			});
			});
		}

		if (repair) {
			showConfirmModal(t('confirmRepair'), t('confirmRepairMsg')).then(function (ok) {
				if (!ok) return;
				doRun();
			});
		} else {
			doRun();
		}
	}

	function clearQueue() {
		state.queue = [];
		renderQueue();
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
		if (!dev) {
			showToast(t('tNoDevice'), 'warn');
			return;
		}
		var diagParams = { device: dev };
		showCommandPreviewModal(action, diagParams, 'Diagnostics: ' + action, t('confirmAction'), t('cmdPreviewHint')).then(function (previewText) {
			if (previewText === null) return;
		callApi(action, { device: dev, command_preview: previewText })
			.then(function (res) {
				var msg = '[' + action + '] ' + (res.message || '') + '\nrc=' + (res.rc || 0) + '\n' + (res.output || '');
				logTo('diagOutput', msg, true);
			})
			.catch(function (err) {
				logTo('diagOutput', 'Diagnostics error: ' + err.message, true);
				showToast('Diagnostics error: ' + err.message, 'error', 3300);
			});
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
		if ((tag === 'input' || tag === 'textarea' || tag === 'select') && !ev.ctrlKey && ev.key !== 'F1') {
			return;
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
		if (ev.key === 'Delete') {
			ev.preventDefault();
			queueDeletePartition();
		}
	}

	document.getElementById('newPartChip').ondragstart = function (ev) {
		ev.dataTransfer.setData('text/plain', 'new-partition');
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
	document.getElementById('dryRunToggle').onchange = function () {
		state.dryRun = !!this.checked;
		showToast(state.dryRun ? 'Dry-run enabled: commands are logged but not executed.' : 'Dry-run disabled: operations will execute normally.', state.dryRun ? 'warn' : 'info', 2600);
	};
	document.addEventListener('click', function (ev) {
		var menu = document.getElementById('partContextMenu');
		if (!menu) return;
		if (menu.style.display === 'none') return;
		if (!menu.contains(ev.target)) hideContextMenu();
	});
	document.addEventListener('keydown', function (ev) {
		if (ev.key === 'Escape') {
			hideContextMenu();
			hideHelpModal();
		}
	});
	document.addEventListener('keydown', onKeyboardShortcuts);

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

	state.language = detectLanguage();
	document.getElementById('langSelect').value = state.language;
	document.getElementById('dryRunToggle').checked = false;
	state.dryRun = false;
	applyTranslations();
	refreshDevices();
	analyzeTools();
})();
</script>
EOF
