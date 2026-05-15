#!/bin/sh

. /usr/lib/libmodcgi.sh

[ -r /mod/etc/conf/alsa-utils.cfg ] && . /mod/etc/conf/alsa-utils.cfg

ACTION="$(cgi_param action)"
PCM_DEVICE="$(cgi_param pcm_device)"
MIXER_DEVICE="$(cgi_param mixer_device)"
VOLUME_CONTROL="$(cgi_param volume_control)"
VOLUME_VALUE="$(cgi_param volume_value)"
VOLUME_SWITCH="$(cgi_param volume_switch)"
CONTROL_NAME="$(cgi_param control_name)"
CONTROL_VALUE="$(cgi_param control_value)"
TEST_CHANNELS="$(cgi_param test_channels)"
SAMPLE_FILE="$(cgi_param sample_file)"
ACTION_TITLE=''
ACTION_OUTPUT=''

sanitize_text() {
	printf '%s' "$1" | sed 's/[^A-Za-z0-9_.,:\/ +%=-]//g'
}

sanitize_uint() {
	case "$1" in
		''|*[!0-9]*) return 1 ;;
		*) printf '%s' "$1" ;;
	esac
}

list_simple_controls() {
	local device="$1"
	amixer -D "$device" scontrols 2>/dev/null | sed -n "s/Simple mixer control '\([^']*\)'.*/\1/p"
}

first_simple_control() {
	list_simple_controls "$1" | sed -n '1p'
}

has_simple_control() {
	local device="$1"
	local control="$2"
	[ -n "$control" ] || return 1
	list_simple_controls "$device" | grep -Fqx "$control"
}

PCM_DEVICE="$(sanitize_text "${PCM_DEVICE:-${ALSA_UTILS_PCM_DEVICE:-default}}")"
MIXER_DEVICE="$(sanitize_text "${MIXER_DEVICE:-${ALSA_UTILS_MIXER_DEVICE:-default}}")"
REQUESTED_VOLUME_CONTROL="$(sanitize_text "${VOLUME_CONTROL:-${ALSA_UTILS_VOLUME_CONTROL}}")"
VOLUME_CONTROL="$REQUESTED_VOLUME_CONTROL"
CONTROL_NAME="$(sanitize_text "$CONTROL_NAME")"
CONTROL_VALUE="$(sanitize_text "$CONTROL_VALUE")"
case "$VOLUME_SWITCH" in
	mute|unmute|toggle) ;;
	*) VOLUME_SWITCH=unmute ;;
esac
TEST_CHANNELS="$(sanitize_uint "${TEST_CHANNELS:-${ALSA_UTILS_TEST_CHANNELS:-2}}")"
[ -n "$TEST_CHANNELS" ] || TEST_CHANNELS=2
SAMPLE_FILE="$(sanitize_text "${SAMPLE_FILE:-${ALSA_UTILS_SAMPLE_FILE}}")"
[ -n "$PCM_DEVICE" ] || PCM_DEVICE=default
[ -n "$MIXER_DEVICE" ] || MIXER_DEVICE=default
[ -n "$SAMPLE_FILE" ] || SAMPLE_FILE="$(list_samples | sed -n '1p')"

DETECTED_VOLUME_CONTROL="$(first_simple_control "$MIXER_DEVICE")"
VOLUME_CONTROL_NOTE=''
if [ -n "$DETECTED_VOLUME_CONTROL" ]; then
	if ! has_simple_control "$MIXER_DEVICE" "$VOLUME_CONTROL"; then
		if [ -n "$VOLUME_CONTROL" ]; then
			VOLUME_CONTROL_NOTE="$(lang de:"Regler '$VOLUME_CONTROL' nicht gefunden; verwende '$DETECTED_VOLUME_CONTROL'." en:"Control '$VOLUME_CONTROL' not found; using '$DETECTED_VOLUME_CONTROL'.")"
		else
			VOLUME_CONTROL_NOTE="$(lang de:"Automatisch erkannter Regler '$DETECTED_VOLUME_CONTROL'." en:"Auto-detected control '$DETECTED_VOLUME_CONTROL'.")"
		fi
		VOLUME_CONTROL="$DETECTED_VOLUME_CONTROL"
	fi
else
	VOLUME_CONTROL=''
	if [ -n "$REQUESTED_VOLUME_CONTROL" ]; then
		VOLUME_CONTROL_NOTE="$(lang de:"Regler '$REQUESTED_VOLUME_CONTROL' ist auf '$MIXER_DEVICE' nicht verf\u00fcgbar." en:"Control '$REQUESTED_VOLUME_CONTROL' is not available on '$MIXER_DEVICE'.")"
	else
		VOLUME_CONTROL_NOTE="$(lang de:"Auf '$MIXER_DEVICE' wurden keine einfachen ALSA-Regler gefunden." en:"No simple ALSA controls were found on '$MIXER_DEVICE'.")"
	fi
fi

list_samples() {
	for sample in /usr/share/sounds/alsa/*.wav; do
		[ -f "$sample" ] || continue
		basename "$sample"
	done
}

sample_exists() {
	local wanted="$1"
	local sample
	for sample in $(list_samples); do
		[ "$sample" = "$wanted" ] && return 0
	done
	return 1
}

print_row() {
	local label="$1"
	local value="$2"
	[ -n "$value" ] || return 0
	echo "<tr><td style='width:240px'><b>$(html "$label")</b></td><td>$(html "$value")</td></tr>"
}

case "$ACTION" in
	speaker_test)
		ACTION_TITLE="$(lang de:"speaker-test Ausgabe" en:"speaker-test output")"
		ACTION_OUTPUT="$(speaker-test -D "$PCM_DEVICE" -t wav -c "$TEST_CHANNELS" -l 1 2>&1 | tail -n 80)"
		;;
	play_sample)
		ACTION_TITLE="$(lang de:"aplay Ausgabe" en:"aplay output")"
		if sample_exists "$SAMPLE_FILE"; then
			ACTION_OUTPUT="$(aplay -D "$PCM_DEVICE" "/usr/share/sounds/alsa/$SAMPLE_FILE" 2>&1 | tail -n 80)"
		else
			ACTION_OUTPUT="$(lang de:"Unbekannte Sample-Datei." en:"Unknown sample file.")"
		fi
		;;
	set_volume)
		ACTION_TITLE="$(lang de:"Lautst\u00e4rke gesetzt" en:"Volume control result")"
		VOLUME_VALUE="$(sanitize_uint "$VOLUME_VALUE")"
		[ -n "$VOLUME_VALUE" ] || VOLUME_VALUE=75
		if [ -n "$VOLUME_CONTROL" ]; then
			ACTION_OUTPUT="$(amixer -D "$MIXER_DEVICE" sset "$VOLUME_CONTROL" "${VOLUME_VALUE}%" "$VOLUME_SWITCH" 2>&1 | tail -n 80)"
		else
			ACTION_OUTPUT="$(lang de:"Kein einfacher Lautst\u00e4rkeregler auf dem gew\u00e4hlten Mixer-Ger\u00e4t gefunden." en:"No simple volume control found on the selected mixer device.")"
		fi
		;;
	set_control)
		ACTION_TITLE="$(lang de:"Mixer-Regler gesetzt" en:"Mixer control result")"
		if [ -n "$CONTROL_NAME" ] && [ -n "$CONTROL_VALUE" ]; then
			ACTION_OUTPUT="$(amixer -D "$MIXER_DEVICE" sset "$CONTROL_NAME" "$CONTROL_VALUE" 2>&1 | tail -n 80)"
		else
			ACTION_OUTPUT="$(lang de:"Control-Name und Wert sind erforderlich." en:"Control name and value are required.")"
		fi
		;;
esac

sec_begin "$(lang de:"Aktuelle Ger\u00e4te" en:"Current devices")"
echo "<table style='width:100%'>"
print_row "$(lang de:"PCM-Ger\u00e4t" en:"PCM device")" "$PCM_DEVICE"
print_row "$(lang de:"Mixer-Ger\u00e4t" en:"Mixer device")" "$MIXER_DEVICE"
print_row "$(lang de:"Lautst\u00e4rkeregler" en:"Volume control")" "$VOLUME_CONTROL"
print_row "$(lang de:"Hinweis" en:"Note")" "$VOLUME_CONTROL_NOTE"
echo '</table>'
sec_end

if [ -n "$ACTION_OUTPUT" ]; then
	sec_begin "$ACTION_TITLE"
	echo '<pre class="log full">'
	printf '%s\n' "$ACTION_OUTPUT" | html
	echo '</pre>'
	sec_end
fi

sec_begin "$(lang de:"Ger\u00e4tetest" en:"Device test")"
cat << EOF
<form action="$(href status alsa-utils)" method="post">
<input type="hidden" name="action" value="speaker_test">
<table>
<tr><td>$(lang de:"PCM-Ger\u00e4t" en:"PCM device"):</td><td><input type="text" name="pcm_device" value="$(html "$PCM_DEVICE")" size="24"></td></tr>
<tr><td>$(lang de:"Kan\u00e4le" en:"Channels"):</td><td><input type="number" name="test_channels" value="$(html "$TEST_CHANNELS")" min="1" max="8"></td></tr>
</table>
<input type="submit" value="$(lang de:"speaker-test -t wav -c2" en:"Run speaker-test -t wav -c2")">
</form>
EOF
sec_end

sec_begin "$(lang de:"Sample-Wiedergabe" en:"Sample playback")"
cat << EOF
<form action="$(href status alsa-utils)" method="post">
<input type="hidden" name="action" value="play_sample">
<table>
<tr><td>$(lang de:"PCM-Ger\u00e4t" en:"PCM device"):</td><td><input type="text" name="pcm_device" value="$(html "$PCM_DEVICE")" size="24"></td></tr>
<tr><td>$(lang de:"Sample-Datei" en:"Sample file"):</td><td><select name="sample_file">
EOF
for sample in $(list_samples); do
	selected=''
	[ "$sample" = "$SAMPLE_FILE" ] && selected=' selected'
	echo "<option value='$(html "$sample")'$selected>$(html "$sample")</option>"
done
cat << EOF
</select></td></tr>
</table>
<input type="submit" value="$(lang de:"Mit aplay abspielen" en:"Play with aplay")">
</form>
EOF
sec_end

sec_begin "$(lang de:"Lautst\u00e4rke" en:"Volume control")"
cat << EOF
<form action="$(href status alsa-utils)" method="post">
<input type="hidden" name="action" value="set_volume">
<table>
<tr><td>$(lang de:"Mixer-Ger\u00e4t" en:"Mixer device"):</td><td><input type="text" name="mixer_device" value="$(html "$MIXER_DEVICE")" size="24"></td></tr>
<tr><td>$(lang de:"Control" en:"Control"):</td><td><input type="text" name="volume_control" value="$(html "$VOLUME_CONTROL")" size="24"></td></tr>
<tr><td>$(lang de:"Wert" en:"Value"):</td><td><input type="number" name="volume_value" value="$(html "${VOLUME_VALUE:-75}")" min="0" max="100">%</td></tr>
<tr><td>$(lang de:"Schalter" en:"Switch"):</td><td><select name="volume_switch">
<option value="unmute">unmute</option>
<option value="mute">mute</option>
<option value="toggle">toggle</option>
</select></td></tr>
</table>
<input type="submit" value="$(lang de:"Lautst\u00e4rke setzen" en:"Set volume")">
</form>
<pre class="log full">
EOF
if [ -n "$VOLUME_CONTROL" ]; then
	amixer -D "$MIXER_DEVICE" sget "$VOLUME_CONTROL" 2>&1 | tail -n 40 | html
else
	echo "$(lang de:"Kein einfacher Lautst\u00e4rkeregler verf\u00fcgbar. Verf\u00fcgbare Regler:" en:"No simple volume control available. Available controls:")" | html
	list_simple_controls "$MIXER_DEVICE" | html
	if ! list_simple_controls "$MIXER_DEVICE" | grep -q .; then
		amixer -D "$MIXER_DEVICE" controls 2>&1 | tail -n 80 | html
	fi
fi
cat << EOF
</pre>
EOF
sec_end

sec_begin "$(lang de:"Mixer" en:"Mixer control")"
cat << EOF
<form action="$(href status alsa-utils)" method="post">
<input type="hidden" name="action" value="set_control">
<table>
<tr><td>$(lang de:"Mixer-Ger\u00e4t" en:"Mixer device"):</td><td><input type="text" name="mixer_device" value="$(html "$MIXER_DEVICE")" size="24"></td></tr>
<tr><td>$(lang de:"Control-Name" en:"Control name"):</td><td><input type="text" name="control_name" value="$(html "$CONTROL_NAME")" size="24"></td></tr>
<tr><td>$(lang de:"Wert" en:"Value"):</td><td><input type="text" name="control_value" value="$(html "$CONTROL_VALUE")" size="24"></td></tr>
</table>
<input type="submit" value="$(lang de:"Regler anwenden" en:"Apply control")">
</form>
<pre class="log full">
EOF
if list_simple_controls "$MIXER_DEVICE" | grep -q .; then
	amixer -D "$MIXER_DEVICE" scontrols 2>&1 | tail -n 80 | html
else
	echo "$(lang de:"Keine einfachen ALSA-Regler gefunden; zeige rohe Control-Liste." en:"No simple ALSA controls found; showing raw control list.")" | html
	amixer -D "$MIXER_DEVICE" controls 2>&1 | tail -n 80 | html
fi
cat << EOF
</pre>
EOF
sec_end

sec_begin "$(lang de:"Audio-F\u00e4higkeiten" en:"Audio capabilities")"
echo '<pre class="log full">'
echo '### /proc/asound/cards' | html
[ -r /proc/asound/cards ] && cat /proc/asound/cards | html
echo | html
echo '### /proc/asound/pcm' | html
[ -r /proc/asound/pcm ] && cat /proc/asound/pcm | html
echo | html
echo '### /proc/asound/modules' | html
[ -r /proc/asound/modules ] && cat /proc/asound/modules | html
echo | html
echo '### /proc/asound/devices' | html
[ -r /proc/asound/devices ] && cat /proc/asound/devices | html
echo | html
echo '### aplay -l' | html
aplay -l 2>&1 | head -n 120 | html
echo | html
echo '### aplay -L' | html
aplay -L 2>&1 | head -n 160 | html
if command -v lsusb >/dev/null 2>&1; then
	echo | html
	echo '### lsusb' | html
	lsusb 2>&1 | grep -Ei 'audio|sound|usb' | html
fi
echo '</pre>'
sec_end

cat << EOF
<form class='btn' action='$(href cgi alsa-utils)' method='get' style='display:inline;'>
<input type='submit' value='$(lang de:"Zurück zur Übersicht" en:"Back to overview")'>
</form>
&nbsp;&nbsp;
<form class='btn' action='$(href status alsa-utils)' method='get' style='display:inline;'>
<input type='submit' value='$(lang de:"Aktualisieren" en:"Refresh")'>
</form>
EOF