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
LEGACY_TEST_CHANNELS="$(cgi_param test_channels)"
WAV_CHANNELS="$(cgi_param wav_channels)"
WAV_LOOPS="$(cgi_param wav_loops)"
SAMPLE_CHANNELS="$(cgi_param sample_channels)"
SAMPLE_LOOPS="$(cgi_param sample_loops)"
SINE_CHANNELS="$(cgi_param sine_channels)"
SINE_LOOPS="$(cgi_param sine_loops)"
SINE_FREQUENCY="$(cgi_param sine_frequency)"
SAMPLE_FILE="$(cgi_param sample_file)"
ACTION_TITLE=''
ACTION_COMMAND=''
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

normalize_uint() {
	local value="$1"
	local fallback="$2"
	local min="$3"
	local max="$4"

	value="$(sanitize_uint "$value")" || value=''
	if [ -z "$value" ] || [ "$value" -lt "$min" ] || [ "$value" -gt "$max" ]; then
		printf '%s' "$fallback"
	else
		printf '%s' "$value"
	fi
}

normalize_channels_or_all() {
	case "$1" in
		''|ALL|all|All) printf 'ALL' ;;
		*) normalize_uint "$1" ALL 1 32 ;;
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
WAV_CHANNELS="$(normalize_uint "${WAV_CHANNELS:-${LEGACY_TEST_CHANNELS:-${ALSA_UTILS_TEST_CHANNELS:-2}}}" 2 1 32)"
WAV_LOOPS="$(normalize_uint "${WAV_LOOPS:-4}" 4 1 64)"
SAMPLE_LOOPS="$(normalize_uint "${SAMPLE_LOOPS:-4}" 4 1 64)"
SAMPLE_CHANNELS="$(normalize_channels_or_all "${SAMPLE_CHANNELS:-ALL}")"
SINE_CHANNELS="$(normalize_uint "${SINE_CHANNELS:-${ALSA_UTILS_TEST_CHANNELS:-2}}" 2 1 32)"
SINE_LOOPS="$(normalize_uint "${SINE_LOOPS:-4}" 4 1 64)"
SINE_FREQUENCY="$(normalize_uint "${SINE_FREQUENCY:-440}" 440 20 20000)"
SAMPLE_FILE="$(sanitize_text "${SAMPLE_FILE:-${ALSA_UTILS_SAMPLE_FILE}}")"
[ -n "$PCM_DEVICE" ] || PCM_DEVICE=default
[ -n "$MIXER_DEVICE" ] || MIXER_DEVICE=default
[ -n "$SAMPLE_FILE" ] || SAMPLE_FILE="$(list_samples | sed -n '1p')"

case "$ACTION" in
	speaker_test) ACTION=speaker_test_wav ;;
	play_sample) ACTION=speaker_test_sample ;;
esac

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
		VOLUME_CONTROL_NOTE="$(lang de:"Regler '$REQUESTED_VOLUME_CONTROL' ist auf '$MIXER_DEVICE' nicht verfügbar." en:"Control '$REQUESTED_VOLUME_CONTROL' is not available on '$MIXER_DEVICE'.")"
	else
		VOLUME_CONTROL_NOTE="$(lang de:"Auf '$MIXER_DEVICE' wurden keine einfachen ALSA-Regler gefunden." en:"No simple ALSA controls were found on '$MIXER_DEVICE'.")"
	fi
fi

wav_test_preview() {
	printf 'speaker-test -t wav -c%s -l %s' "$WAV_CHANNELS" "$WAV_LOOPS"
}

sample_test_preview() {
	if [ "$SAMPLE_CHANNELS" = 'ALL' ]; then
		printf 'speaker-test -t wav -l %s -w %s' "$SAMPLE_LOOPS" "$SAMPLE_FILE"
	else
		printf 'speaker-test -t wav -c%s -l %s -w %s' "$SAMPLE_CHANNELS" "$SAMPLE_LOOPS" "$SAMPLE_FILE"
	fi
}

sine_test_preview() {
	printf 'speaker-test -t sine -f %s -c%s -l %s' "$SINE_FREQUENCY" "$SINE_CHANNELS" "$SINE_LOOPS"
}

print_sample_channel_options() {
	local selected="$1"
	local option
	for option in ALL; do
		if [ "$option" = "$selected" ]; then
			echo "<option value='$(html "$option")' selected>$(html "$option")</option>"
		else
			echo "<option value='$(html "$option")'>$(html "$option")</option>"
		fi
	done
	option=1
	while [ "$option" -le 32 ]; do
		if [ "$option" = "$selected" ]; then
			echo "<option value='$(html "$option")' selected>$(html "$option")</option>"
		else
			echo "<option value='$(html "$option")'>$(html "$option")</option>"
		fi
		option=$((option + 1))
	done
}

print_row() {
	local label="$1"
	local value="$2"
	[ -n "$value" ] || return 0
	echo "<tr><td style='width:240px'><b>$(html "$label")</b></td><td>$(html "$value")</td></tr>"
}

case "$ACTION" in
	speaker_test_wav)
		ACTION_TITLE="$(lang de:"WAV speaker-test Ausgabe" en:"WAV speaker-test output")"
		ACTION_COMMAND="$(wav_test_preview)"
		ACTION_OUTPUT="$(speaker-test -D "$PCM_DEVICE" -t wav -c "$WAV_CHANNELS" -l "$WAV_LOOPS" 2>&1 | tail -n 120)"
		;;
	speaker_test_sample)
		ACTION_TITLE="$(lang de:"WAV-Datei speaker-test Ausgabe" en:"WAV file speaker-test output")"
		if sample_exists "$SAMPLE_FILE"; then
			ACTION_COMMAND="$(sample_test_preview)"
			if [ "$SAMPLE_CHANNELS" = 'ALL' ]; then
				ACTION_OUTPUT="$(speaker-test -D "$PCM_DEVICE" -t wav -l "$SAMPLE_LOOPS" -w "/usr/share/sounds/alsa/$SAMPLE_FILE" 2>&1 | tail -n 120)"
			else
				ACTION_OUTPUT="$(speaker-test -D "$PCM_DEVICE" -t wav -c "$SAMPLE_CHANNELS" -l "$SAMPLE_LOOPS" -w "/usr/share/sounds/alsa/$SAMPLE_FILE" 2>&1 | tail -n 120)"
			fi
		else
			ACTION_OUTPUT="$(lang de:"Unbekannte Sample-Datei." en:"Unknown sample file.")"
		fi
		;;
	speaker_test_sine)
		ACTION_TITLE="$(lang de:"Sinus speaker-test Ausgabe" en:"Sine speaker-test output")"
		ACTION_COMMAND="$(sine_test_preview)"
		ACTION_OUTPUT="$(speaker-test -D "$PCM_DEVICE" -t sine -f "$SINE_FREQUENCY" -c "$SINE_CHANNELS" -l "$SINE_LOOPS" 2>&1 | tail -n 120)"
		;;
	set_volume)
		ACTION_TITLE="$(lang de:"Lautstärke gesetzt" en:"Volume control result")"
		VOLUME_VALUE="$(sanitize_uint "$VOLUME_VALUE")"
		[ -n "$VOLUME_VALUE" ] || VOLUME_VALUE=75
		if [ -n "$VOLUME_CONTROL" ]; then
			ACTION_COMMAND="amixer -D $MIXER_DEVICE sset $VOLUME_CONTROL ${VOLUME_VALUE}% $VOLUME_SWITCH"
			ACTION_OUTPUT="$(amixer -D "$MIXER_DEVICE" sset "$VOLUME_CONTROL" "${VOLUME_VALUE}%" "$VOLUME_SWITCH" 2>&1 | tail -n 80)"
		else
			ACTION_OUTPUT="$(lang de:"Kein einfacher Lautstärkeregler auf dem gewählten Mixer-Gerät gefunden." en:"No simple volume control found on the selected mixer device.")"
		fi
		;;
	set_control)
		ACTION_TITLE="$(lang de:"Mixer-Regler gesetzt" en:"Mixer control result")"
		if [ -n "$CONTROL_NAME" ] && [ -n "$CONTROL_VALUE" ]; then
			ACTION_COMMAND="amixer -D $MIXER_DEVICE sset $CONTROL_NAME $CONTROL_VALUE"
			ACTION_OUTPUT="$(amixer -D "$MIXER_DEVICE" sset "$CONTROL_NAME" "$CONTROL_VALUE" 2>&1 | tail -n 80)"
		else
			ACTION_OUTPUT="$(lang de:"Control-Name und Wert sind erforderlich." en:"Control name and value are required.")"
		fi
		;;
esac

cat << EOF
<style>
.alsa-grid {
	display: flex;
	flex-wrap: wrap;
	gap: 16px;
}
.alsa-stage-grid {
	display: grid;
	grid-template-columns: minmax(360px, 2fr) minmax(280px, 1fr);
	gap: 16px;
	margin: 0 0 16px 0;
}
.alsa-card {
	flex: 1 1 320px;
	min-width: 320px;
	border: 1px solid #c8d3da;
	border-radius: 6px;
	background: #f7fafb;
	padding: 14px;
	box-sizing: border-box;
}
.alsa-card h3,
.alsa-stage-panel h3 {
	margin: 0 0 8px 0;
}
.alsa-stage-panel {
	border: 1px solid #c8d3da;
	border-radius: 6px;
	background: #f7fafb;
	padding: 14px;
	box-sizing: border-box;
}
.alsa-stage-panel-full {
	grid-column: 1 / -1;
}
.alsa-note {
	margin: 0 0 10px 0;
	color: #455a64;
	line-height: 1.45;
}
.alsa-section-label {
	display: block;
	margin: 0 0 6px 0;
	font-size: 12px;
	font-weight: bold;
	text-transform: uppercase;
	letter-spacing: 0.04em;
	color: #60727c;
}
.alsa-command-box {
	font-family: monospace;
	background: #eef4f7;
	border: 1px solid #d7e2e8;
	border-radius: 4px;
	padding: 8px 10px;
	margin: 0 0 12px 0;
	white-space: pre-wrap;
	word-break: break-word;
}
.alsa-device-table td,
.alsa-form-table td {
	padding: 4px 8px 4px 0;
	vertical-align: top;
}
.alsa-form-table {
	width: 100%;
}
.alsa-form-table td:first-child {
	width: 128px;
}
.alsa-form-table input[type='text'],
.alsa-form-table select {
	width: 100%;
	box-sizing: border-box;
}
.alsa-form-table input[type='number'] {
	width: 110px;
	box-sizing: border-box;
}
.alsa-submit {
	margin-top: 8px;
}
.alsa-output-box {
	max-height: 360px;
	overflow: auto;
}
@media (max-width: 900px) {
	.alsa-stage-grid {
		grid-template-columns: 1fr;
	}
}
</style>
EOF

sec_begin "$(lang de:"Aktuelle Ger\u00e4te" en:"Current devices")"
echo "<table class='alsa-device-table' style='width:100%'>"
print_row "$(lang de:"PCM-Ger\u00e4t" en:"PCM device")" "$PCM_DEVICE"
print_row "$(lang de:"Mixer-Ger\u00e4t" en:"Mixer device")" "$MIXER_DEVICE"
print_row "$(lang de:"Lautst\u00e4rkeregler" en:"Volume control")" "$VOLUME_CONTROL"
print_row "$(lang de:"Hinweis" en:"Note")" "$VOLUME_CONTROL_NOTE"
echo '</table>'
sec_end

sec_begin "$(lang de:"Speaker-test Studio" en:"Speaker-test studio")"
cat << EOF
<p class="alsa-note">$(lang de:"Konfigurieren Sie die drei speaker-test Varianten direkt im Browser. Die generierten Befehle bleiben sichtbar und jede Ausführung sammelt ihren Konsolen-Output in der Konsole dieser Seite." en:"Configure the three speaker-test variants directly in the browser. The generated commands stay visible and each execution collects its console output in the console on this page.")</p>
<div class="alsa-stage-grid">
<div class="alsa-stage-panel alsa-stage-panel-full">
<h3>$(lang de:"Ausführungs-Konsole" en:"Execution console")</h3>
<p class="alsa-note">$(lang de:"Hier landen die letzten speaker-test oder amixer Aufrufe inklusive Kommandozeile und gesammelter Ausgabe." en:"The latest speaker-test or amixer runs land here with the command line and collected output.")</p>
<span class="alsa-section-label">$(lang de:"Letztes Kommando" en:"Last command")</span>
<div class="alsa-command-box">$(html "${ACTION_COMMAND:-$(lang de:"Führen Sie einen speaker-test oder Mixer-Befehl aus, um hier den aufgerufenen Befehl zu sehen." en:"Run a speaker-test or mixer command to see the executed command here.")}")</div>
<span class="alsa-section-label">$(html "${ACTION_TITLE:-$(lang de:"Noch kein Kommando ausgeführt" en:"No command executed yet")}")</span>
<pre class="log full alsa-output-box">
EOF
if [ -n "$ACTION_OUTPUT" ]; then
	printf '%s\n' "$ACTION_OUTPUT" | html
else
	echo "$(lang de:"Noch keine Ausgabe vorhanden. Starten Sie einen Test, um die Konsole hier zu sammeln." en:"No output collected yet. Run a test to collect console output here.")" | html
fi
cat << EOF
</pre>
</div>
</div>
<div class="alsa-grid">
<div class="alsa-card">
<h3>$(lang de:"WAV-Kanaltest" en:"WAV channel test")</h3>
<p class="alsa-note">$(lang de:"Entspricht dem klassischen WAV-basierten speaker-test mit konfigurierbaren Kanälen und Zyklen." en:"Classic WAV-based speaker-test with configurable channels and loops.")</p>
<span class="alsa-section-label">$(lang de:"Kommando-Vorschau" en:"Command preview")</span>
<div class="alsa-command-box" id="alsa-preview-wav">$(html "$(wav_test_preview)")</div>
<form action="$(href status alsa-utils)" method="get">
<input type="hidden" name="action" value="speaker_test_wav">
<table class="alsa-form-table">
<tr><td>$(lang de:"PCM-Gerät" en:"PCM device"):</td><td><input type="text" name="pcm_device" value="$(html "$PCM_DEVICE")" size="24"></td></tr>
<tr><td>$(lang de:"Kanäle" en:"Channels"):</td><td><input id="alsa-wav-channels" type="number" name="wav_channels" value="$(html "$WAV_CHANNELS")" min="1" max="32"></td></tr>
<tr><td>$(lang de:"Zyklen" en:"Loops"):</td><td><input id="alsa-wav-loops" type="number" name="wav_loops" value="$(html "$WAV_LOOPS")" min="1" max="64"></td></tr>
</table>
<input class="alsa-submit" type="submit" value="$(lang de:"WAV-Kanaltest starten" en:"Run WAV channel test")">
</form>
</div>

<div class="alsa-card">
<h3>$(lang de:"WAV-Datei testen" en:"Test a WAV file")</h3>
<p class="alsa-note">$(lang de:"Ersetzt die bisherige aplay-Wiedergabe durch speaker-test mit auswählbarer WAV-Datei." en:"Replaces the old aplay playback with speaker-test using a selectable WAV file.")</p>
<span class="alsa-section-label">$(lang de:"Kommando-Vorschau" en:"Command preview")</span>
<div class="alsa-command-box" id="alsa-preview-sample">$(html "$(sample_test_preview)")</div>
<form action="$(href status alsa-utils)" method="get">
<input type="hidden" name="action" value="speaker_test_sample">
<table class="alsa-form-table">
<tr><td>$(lang de:"PCM-Gerät" en:"PCM device"):</td><td><input type="text" name="pcm_device" value="$(html "$PCM_DEVICE")" size="24"></td></tr>
<tr><td>$(lang de:"WAV-Datei" en:"WAV file"):</td><td><select id="alsa-sample-file" name="sample_file">
EOF
for sample in $(list_samples); do
	selected=''
	[ "$sample" = "$SAMPLE_FILE" ] && selected=' selected'
	echo "<option value='$(html "$sample")'$selected>$(html "$sample")</option>"
done
cat << EOF
</select></td></tr>
<tr><td>$(lang de:"Kanäle" en:"Channels"):</td><td><select id="alsa-sample-channels" name="sample_channels">
EOF
print_sample_channel_options "$SAMPLE_CHANNELS"
cat << EOF
</select> <span class="alsa-note">$(lang de:"ALL = speaker-test Standard" en:"ALL = speaker-test default")</span></td></tr>
<tr><td>$(lang de:"Zyklen" en:"Loops"):</td><td><input id="alsa-sample-loops" type="number" name="sample_loops" value="$(html "$SAMPLE_LOOPS")" min="1" max="64"></td></tr>
</table>
<input class="alsa-submit" type="submit" value="$(lang de:"WAV-Datei-Test starten" en:"Run WAV file test")">
</form>
</div>

<div class="alsa-card">
<h3>$(lang de:"Sinuston-Test" en:"Sine tone test")</h3>
<p class="alsa-note">$(lang de:"Erzeugt einen Sinuston mit konfigurierbarer Frequenz, Kanalzahl und Zyklusanzahl." en:"Generates a sine tone with configurable frequency, channels and loop count.")</p>
<span class="alsa-section-label">$(lang de:"Kommando-Vorschau" en:"Command preview")</span>
<div class="alsa-command-box" id="alsa-preview-sine">$(html "$(sine_test_preview)")</div>
<form action="$(href status alsa-utils)" method="get">
<input type="hidden" name="action" value="speaker_test_sine">
<table class="alsa-form-table">
<tr><td>$(lang de:"PCM-Gerät" en:"PCM device"):</td><td><input type="text" name="pcm_device" value="$(html "$PCM_DEVICE")" size="24"></td></tr>
<tr><td>$(lang de:"Frequenz" en:"Frequency"):</td><td><input id="alsa-sine-frequency" type="number" name="sine_frequency" value="$(html "$SINE_FREQUENCY")" min="20" max="20000"> Hz</td></tr>
<tr><td>$(lang de:"Kanäle" en:"Channels"):</td><td><input id="alsa-sine-channels" type="number" name="sine_channels" value="$(html "$SINE_CHANNELS")" min="1" max="32"></td></tr>
<tr><td>$(lang de:"Zyklen" en:"Loops"):</td><td><input id="alsa-sine-loops" type="number" name="sine_loops" value="$(html "$SINE_LOOPS")" min="1" max="64"></td></tr>
</table>
<input class="alsa-submit" type="submit" value="$(lang de:"Sinuston-Test starten" en:"Run sine tone test")">
</form>
</div>
</div>
<script>
(function() {
	function byId(id) {
		return document.getElementById(id);
	}

	function readValue(id, fallback) {
		var element = byId(id);
		if (!element || !element.value) {
			return fallback;
		}
		return element.value;
	}

	function normalizePositive(value, fallback) {
		var parsed = parseInt(value, 10);
		if (isNaN(parsed) || parsed < 1) {
			return fallback;
		}
		return parsed;
	}

	function updateText(id, text) {
		var element = byId(id);
		if (element) {
			element.textContent = text;
		}
	}

	function bind(ids, callback) {
		var index;
		var element;
		for (index = 0; index < ids.length; index++) {
			element = byId(ids[index]);
			if (!element) {
				continue;
			}
			element.addEventListener('input', callback);
			element.addEventListener('change', callback);
		}
	}

	function updateWavPreview() {
		var channels = normalizePositive(readValue('alsa-wav-channels', '2'), 2);
		var loops = normalizePositive(readValue('alsa-wav-loops', '4'), 4);
		updateText('alsa-preview-wav', 'speaker-test -t wav -c' + channels + ' -l ' + loops);
	}

	function updateSamplePreview() {
		var channels = readValue('alsa-sample-channels', 'ALL');
		var loops = normalizePositive(readValue('alsa-sample-loops', '4'), 4);
		var file = readValue('alsa-sample-file', 'Rear_Left.wav');
		var command = 'speaker-test -t wav ';

		if (channels && channels !== 'ALL') {
			command += '-c' + normalizePositive(channels, 2) + ' ';
		}

		command += '-l ' + loops + ' -w ' + file;
		updateText('alsa-preview-sample', command);
	}

	function updateSinePreview() {
		var frequency = normalizePositive(readValue('alsa-sine-frequency', '440'), 440);
		var channels = normalizePositive(readValue('alsa-sine-channels', '2'), 2);
		var loops = normalizePositive(readValue('alsa-sine-loops', '4'), 4);
		updateText('alsa-preview-sine', 'speaker-test -t sine -f ' + frequency + ' -c' + channels + ' -l ' + loops);
	}

	bind(['alsa-wav-channels', 'alsa-wav-loops'], updateWavPreview);
	bind(['alsa-sample-file', 'alsa-sample-channels', 'alsa-sample-loops'], updateSamplePreview);
	bind(['alsa-sine-frequency', 'alsa-sine-channels', 'alsa-sine-loops'], updateSinePreview);

	updateWavPreview();
	updateSamplePreview();
	updateSinePreview();
})();
</script>
EOF
sec_end

sec_begin "$(lang de:"Lautst\u00e4rke" en:"Volume control")"
cat << EOF
<form action="$(href status alsa-utils)" method="get">
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
<form action="$(href status alsa-utils)" method="get">
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

cat << EOF
<script>
(function() {
	function byId(id) {
		return document.getElementById(id);
	}

	function readValue(id, fallback) {
		var element = byId(id);
		if (!element || !element.value) {
			return fallback;
		}
		return element.value;
	}

	function normalizePositive(value, fallback) {
		var parsed = parseInt(value, 10);
		if (isNaN(parsed) || parsed < 1) {
			return fallback;
		}
		return parsed;
	}

	function updateText(id, text) {
		var element = byId(id);
		if (element) {
			element.textContent = text;
		}
	}

	function bind(ids, callback) {
		var index;
		var element;
		for (index = 0; index < ids.length; index++) {
			element = byId(ids[index]);
			if (!element) {
				continue;
			}
			element.addEventListener('input', callback);
			element.addEventListener('change', callback);
		}
	}

	function updateWavPreview() {
		var channels = normalizePositive(readValue('alsa-wav-channels', '2'), 2);
		var loops = normalizePositive(readValue('alsa-wav-loops', '4'), 4);
		updateText('alsa-preview-wav', 'speaker-test -t wav -c' + channels + ' -l ' + loops);
	}

	function updateSamplePreview() {
		var channels = readValue('alsa-sample-channels', 'ALL');
		var loops = normalizePositive(readValue('alsa-sample-loops', '4'), 4);
		var file = readValue('alsa-sample-file', 'Rear_Left.wav');
		var command = 'speaker-test -t wav ';

		if (channels && channels !== 'ALL') {
			command += '-c' + normalizePositive(channels, 2) + ' ';
		}

		command += '-l ' + loops + ' -w ' + file;
		updateText('alsa-preview-sample', command);
	}

	function updateSinePreview() {
		var frequency = normalizePositive(readValue('alsa-sine-frequency', '440'), 440);
		var channels = normalizePositive(readValue('alsa-sine-channels', '2'), 2);
		var loops = normalizePositive(readValue('alsa-sine-loops', '4'), 4);
		updateText('alsa-preview-sine', 'speaker-test -t sine -f ' + frequency + ' -c' + channels + ' -l ' + loops);
	}

	bind(['alsa-wav-channels', 'alsa-wav-loops'], updateWavPreview);
	bind(['alsa-sample-file', 'alsa-sample-channels', 'alsa-sample-loops'], updateSamplePreview);
	bind(['alsa-sine-frequency', 'alsa-sine-channels', 'alsa-sine-loops'], updateSinePreview);

	updateWavPreview();
	updateSamplePreview();
	updateSinePreview();
})();
</script>
EOF

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