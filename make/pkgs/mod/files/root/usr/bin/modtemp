#!/bin/sh
CACHE=/tmp/.modtemp

SELECTED="${1:-$(cat $CACHE 2>/dev/null)}"

READER="bpcm chip thermal device avm ctlmgr"
get_temp() {
	local cpu_temp
	case "$1" in
		bpcm)     cpu_temp="$(sed 's/.*: //;s/ .*//' /sys/power/bpcm/cpu_temp 2>/dev/null | head -n1)" ;;
		chip)     cpu_temp="$(sed -rn 's!^Channel .: ([0-9.]*) .*!\1!p' /proc/chip_temperature 2>/dev/null | sort -r | head -n1)" ;;
		thermal)  cpu_temp="$(sed 's/...$/.&/' /sys/devices/virtual/thermal/thermal_zone0/temp 2>/dev/null)" ;;
		device)   cpu_temp="$(sed 's/ .*//g' /proc/avm/powermanagmentressourceinfo/powerdevice_temperature 2>/dev/null)" ;;
		avm)      cpu_temp="$(sed -rn 's!^(CPU|cpu-thermal) *: ([0-9.]*) .*!\2!p' /proc/avm/temp_sensors 2>/dev/null)" ;;
		ctlmgr)   cpu_temp="$(ctlmgr_ctl r power status/act_temperature 2>/dev/null)" ;;
	esac
	[ "${cpu_temp/./}" -gt 0 ] 2>/dev/null && echo "$cpu_temp" || return 1
}

save_cache() {
	echo -n "$1" > "$CACHE"
}


[ "$SELECTED" == "none" ] && exit 1

if [ -n "$SELECTED" ]; then
	get_temp "$SELECTED"
	exit $?
fi

for source in $READER; do
	get_temp "$source" || continue
	save_cache "$source"
	exit 0
done

save_cache "none"
exit 1

