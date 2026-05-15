#!/bin/sh

. /usr/lib/libmodcgi.sh

[ -r /mod/etc/conf/alsaequal.cfg ] && . /mod/etc/conf/alsaequal.cfg

: ${ALSAEQUAL_ENABLED:=no}
: ${ALSAEQUAL_SET_DEFAULT:=no}
: ${ALSAEQUAL_SLAVE_PCM:=plughw:0,0}
: ${ALSAEQUAL_CONTROL_FILE:=/tmp/flash/alsaequal/alsaequal.bin}
: ${ALSAEQUAL_LIBRARY:=caps.so}
: ${ALSAEQUAL_MODULE:=Eq10}
: ${ALSAEQUAL_CHANNELS:=2}

RUNTIME_CONFIG=/etc/alsa/conf.d/50-alsaequal.conf
ACTION="$(cgi_param action)"
ACTION_TITLE=''
ACTION_OUTPUT=''

sanitize_text() {
	printf '%s' "$1" | sed 's/[^A-Za-z0-9_.,:\/ +%=-]//g'
}

sanitize_integer() {
	case "$1" in
		''|*[^0-9-]*) return 1 ;;
		-) return 1 ;;
		*) printf '%s' "$1" ;;
	esac
}

repeat_value() {
	local value="$1"
	local count="$2"
	local result="$value"
	while [ "$count" -gt 1 ] 2>/dev/null; do
		result="$result,$value"
		count=$((count - 1))
	done
	printf '%s' "$result"
}

equal_controls() {
	amixer -D equal controls 2>/dev/null | sed -n 's/numid=\([0-9][0-9]*\).*/\1/p'
}

equal_cget() {
	amixer -D equal cget numid="$1" 2>/dev/null
}

control_name() {
	equal_cget "$1" | sed -n "1 s/.*name='\([^']*\)'.*/\1/p"
}

control_channels() {
	equal_cget "$1" | sed -nr 's/.*values=([0-9][0-9]*),min=.*/\1/p' | head -n 1
}

control_min() {
	equal_cget "$1" | sed -nr 's/.*min=([-0-9]+),max=.*/\1/p' | head -n 1
}

control_max() {
	equal_cget "$1" | sed -nr 's/.*max=([-0-9]+),step=.*/\1/p' | head -n 1
}

control_step() {
	equal_cget "$1" | sed -nr 's/.*step=([-0-9]+).*/\1/p' | head -n 1
}

control_value() {
	equal_cget "$1" | sed -nr 's/.*: values=([-0-9]+)(,.*)?/\1/p' | tail -n 1
}

apply_control_value() {
	local numid="$1"
	local raw_value="$2"
	local value
	value="$(sanitize_integer "$raw_value")" || return 0
	local channels
	channels="$(control_channels "$numid")"
	[ -n "$channels" ] || channels=1
	amixer -D equal cset numid="$numid" "$(repeat_value "$value" "$channels")" 2>&1
}

set_flat_response() {
	local output=''
	local numid min max target line
	for numid in $(equal_controls); do
		min="$(control_min "$numid")"
		max="$(control_max "$numid")"
		case "$min:$max" in
			''*|*:*[!0-9-]*) continue ;;
		esac
		if [ "$min" -le 0 ] 2>/dev/null && [ 0 -le "$max" ] 2>/dev/null; then
			target=0
		else
			target=$(( (min + max) / 2 ))
		fi
		line="$(apply_control_value "$numid" "$target")"
		output="${output}numid=${numid}: ${target}\n${line}\n"
	done
	printf '%b' "$output"
}

print_row() {
	local label="$1"
	local value="$2"
	[ -n "$value" ] || return 0
	echo "<tr><td style='width:240px'><b>$(html "$label")</b></td><td>$(html "$value")</td></tr>"
}

case "$ACTION" in
	apply_controls)
		ACTION_TITLE="$(lang de:"Angewendete Reglerwerte" en:"Applied equalizer values")"
		if [ "$ALSAEQUAL_ENABLED" != 'yes' ]; then
			ACTION_OUTPUT="$(lang de:"alsaequal ist derzeit deaktiviert." en:"alsaequal is currently disabled.")"
		else
			for numid in $(equal_controls); do
				value="$(cgi_param "band_${numid}")"
				[ -n "$value" ] || continue
				line="$(apply_control_value "$numid" "$value")"
				ACTION_OUTPUT="${ACTION_OUTPUT}numid=${numid}\n${line}\n"
			done
			[ -n "$ACTION_OUTPUT" ] || ACTION_OUTPUT="$(lang de:"Keine Reglerwerte übermittelt." en:"No control values were submitted.")"
		fi
		;;
	flat)
		ACTION_TITLE="$(lang de:"Flache Frequenzkurve" en:"Flat response")"
		if [ "$ALSAEQUAL_ENABLED" != 'yes' ]; then
			ACTION_OUTPUT="$(lang de:"alsaequal ist derzeit deaktiviert." en:"alsaequal is currently disabled.")"
		else
			ACTION_OUTPUT="$(set_flat_response)"
			[ -n "$ACTION_OUTPUT" ] || ACTION_OUTPUT="$(lang de:"Keine Equalizer-Regler gefunden." en:"No equalizer controls found.")"
		fi
		;;
esac

case "$ALSAEQUAL_LIBRARY" in
	/*)
		if [ -r "$ALSAEQUAL_LIBRARY" ]; then
			LIBRARY_STATE='present'
		else
			LIBRARY_STATE='missing'
		fi
		;;
	*)
		LIBRARY_STATE="search path (${ALSAEQUAL_LIBRARY})"
		;;
esac

CONTROL_IDS="$(equal_controls)"

sec_begin "$(lang de:"Equalizer-Status" en:"Equalizer status")"
echo "<table style='width:100%'>"
print_row "$(lang de:"Aktiviert" en:"Enabled")" "$ALSAEQUAL_ENABLED"
print_row "$(lang de:"Als Standard setzen" en:"Use as default")" "$ALSAEQUAL_SET_DEFAULT"
print_row "$(lang de:"Generierte Konfiguration" en:"Generated configuration")" "$RUNTIME_CONFIG"
print_row "$(lang de:"PCM-Slave" en:"Slave PCM")" "$ALSAEQUAL_SLAVE_PCM"
print_row "$(lang de:"Steuerdatei" en:"Control file")" "$ALSAEQUAL_CONTROL_FILE"
print_row "$(lang de:"LADSPA-Bibliothek" en:"LADSPA library")" "$ALSAEQUAL_LIBRARY"
print_row "$(lang de:"Bibliotheksstatus" en:"Library status")" "$LIBRARY_STATE"
print_row "$(lang de:"Plugin-Modul" en:"Plugin module")" "$ALSAEQUAL_MODULE"
print_row "$(lang de:"Kan\u00e4le" en:"Channels")" "$ALSAEQUAL_CHANNELS"
print_row "$(lang de:"Equalizer-Regler erreichbar" en:"Equalizer controls available")" "$( [ -n "$CONTROL_IDS" ] && echo yes || echo no )"
echo '</table>'
sec_end

if [ -n "$ACTION_OUTPUT" ]; then
	sec_begin "$ACTION_TITLE"
	echo '<pre class="log full">'
	printf '%s\n' "$ACTION_OUTPUT" | html
	echo '</pre>'
	sec_end
fi

if [ -n "$CONTROL_IDS" ]; then
	sec_begin "$(lang de:"Equalizer-Regler" en:"Equalizer controls")"
	cat << EOF
<form action="$(href status alsaequal)" method="post">
<input type="hidden" name="action" value="apply_controls">
<table style="width:100%">
<tr><th align="left">$(lang de:"Band" en:"Band")</th><th align="left">$(lang de:"Aktuell" en:"Current")</th><th align="left">$(lang de:"Bereich" en:"Range")</th><th align="left">$(lang de:"Neuer Wert" en:"New value")</th></tr>
EOF
	for numid in $CONTROL_IDS; do
		name="$(control_name "$numid")"
		current="$(control_value "$numid")"
		min="$(control_min "$numid")"
		max="$(control_max "$numid")"
		step="$(control_step "$numid")"
		[ -n "$step" ] || step=1
		echo "<tr><td>$(html "$name")</td><td>$(html "$current")</td><td>$(html "$min .. $max")</td><td><input type='number' name='band_${numid}' value='$(html "$current")' min='$(html "$min")' max='$(html "$max")' step='$(html "$step")'></td></tr>"
	done
	cat << EOF
</table>
<p>
<input type="submit" value="$(lang de:"Werte anwenden" en:"Apply values")">
</p>
</form>
<form class='btn' action="$(href status alsaequal)" method="post" style='display:inline;'>
<input type="hidden" name="action" value="flat">
<input type="submit" value="$(lang de:"Auf flach setzen" en:"Set flat")">
</form>
EOF
	sec_end
else
	sec_begin "$(lang de:"Equalizer-Regler" en:"Equalizer controls")"
	echo '<pre class="log full">'
	if [ "$ALSAEQUAL_ENABLED" != 'yes' ]; then
		echo "$(lang de:"alsaequal ist deaktiviert. Aktivieren Sie das Ger\u00e4t in der Konfiguration und speichern Sie die Seite." en:"alsaequal is disabled. Enable it in the configuration page and save it.")" | html
	else
		amixer -D equal controls 2>&1 | html
	fi
	echo '</pre>'
	sec_end
fi

if [ -r "$RUNTIME_CONFIG" ]; then
	sec_begin "$(lang de:"Generierte ALSA-Konfiguration" en:"Generated ALSA configuration")"
	echo '<pre class="log full">'
	cat "$RUNTIME_CONFIG" | html
	echo '</pre>'
	sec_end
fi

if [ -r /proc/asound/cards ]; then
	sec_begin "$(lang de:"Erkannte Soundkarten" en:"Detected sound cards")"
	echo '<pre class="log full">'
	cat /proc/asound/cards | html
	echo '</pre>'
	sec_end
fi

cat << EOF
<form class='btn' action='$(href cgi alsaequal)' method='get' style='display:inline;'>
<input type='submit' value='$(lang de:"Konfiguration" en:"Configuration")'>
</form>
&nbsp;&nbsp;
<form class='btn' action='$(href status alsaequal)' method='get' style='display:inline;'>
<input type='submit' value='$(lang de:"Aktualisieren" en:"Refresh")'>
</form>
EOF