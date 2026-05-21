#!/bin/sh

. /usr/lib/libmodcgi.sh

[ -r /mod/etc/default.alsaequal/alsaequal.cfg ] && . /mod/etc/default.alsaequal/alsaequal.cfg
[ -r /mod/etc/conf/alsaequal.cfg ] && . /mod/etc/conf/alsaequal.cfg

: ${ALSAEQUAL_ENABLED:=no}
: ${ALSAEQUAL_SET_DEFAULT:=no}
: ${ALSAEQUAL_SLAVE_PCM:=plughw:0,0}
: ${ALSAEQUAL_CONTROL_FILE:=/tmp/flash/alsaequal/alsaequal.bin}
: ${ALSAEQUAL_LIBRARY:=caps.so}
: ${ALSAEQUAL_MODULE:=Eq10}
: ${ALSAEQUAL_CHANNELS:=2}

RUNTIME_CONFIG=/var/lib/alsa/conf.d/50-alsaequal.conf
ACTION="$(cgi_param action)"
ACTION_TITLE=''
ACTION_OUTPUT=''
ACTION_COMMAND=''
ACTION_RC=0

resolve_ladspa_library() {
	local library="$1"
	local search_path old_ifs dir candidate
	case "$library" in
		/*)
			[ -r "$library" ] && {
				printf '%s\n' "$library"
				return 0
			}
			case "$library" in
				*.so) ;;
				*)
					[ -r "${library}.so" ] && {
						printf '%s\n' "${library}.so"
						return 0
					}
					;;
			esac
			return 1
			;;
	esac
	search_path="${LADSPA_PATH:-/usr/lib/ladspa:/usr/lib/freetz/ladspa:/mod/usr/lib/ladspa:/mod/external/usr/lib/ladspa:/mod/lib/ladspa:/mod/external/lib/ladspa:/lib/ladspa:/usr/lib}"
	old_ifs="$IFS"
	IFS=':'
	for dir in $search_path; do
		[ -n "$dir" ] || continue
		for candidate in "$library" "${library}.so"; do
			if [ -r "$dir/$candidate" ]; then
				IFS="$old_ifs"
				printf '%s\n' "$dir/$candidate"
				return 0
			fi
		done
	done
	IFS="$old_ifs"
	return 1
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

control_label() {
	control_name "$1" | sed -e 's/ Playback Volume$//' -e 's/^[0-9][0-9]*[. ]*//' -e 's/^Left //'
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
			target=$(((min + max) / 2))
		fi
		line="$(apply_control_value "$numid" "$target")"
		output="${output}numid=${numid}: ${target}\n${line}\n"
	done
	printf '%b' "$output"
}

run_rc_alsaequal() {
	if [ -x /etc/init.d/rc.alsaequal ]; then
		/etc/init.d/rc.alsaequal "$@"
	elif [ -x /mod/etc/init.d/rc.alsaequal ]; then
		/mod/etc/init.d/rc.alsaequal "$@"
	elif [ -x /mod/external/etc/init.d/rc.alsaequal ]; then
		/mod/external/etc/init.d/rc.alsaequal "$@"
	else
		echo 'rc.alsaequal not found.'
		return 1
	fi
}

format_signed() {
	case "$1" in
		''|*[!0-9-]*) printf '%s' "$1" ;;
		-*) printf '%s dB' "$1" ;;
		0) printf '0 dB' ;;
		*) printf '+%s dB' "$1" ;;
	esac
}

print_row() {
	local label="$1"
	local value="$2"
	[ -n "$value" ] || return 0
	echo "<tr><td style='width:230px'><b>$(html "$label")</b></td><td>$(html "$value")</td></tr>"
}

case "$ACTION" in
	apply_controls)
		ACTION_TITLE="$(lang de:"Angewendete Reglerwerte" en:"Applied equalizer values")"
		ACTION_COMMAND='apply equalizer values'
		if [ "$ALSAEQUAL_ENABLED" != 'yes' ]; then
			ACTION_OUTPUT="$(lang de:"alsaequal ist derzeit deaktiviert." en:"alsaequal is currently disabled.")"
		elif [ ! -s "$RUNTIME_CONFIG" ]; then
			ACTION_OUTPUT="$(lang de:"Die generierte ALSA-Konfiguration fehlt. Erstellen Sie sie zuerst neu." en:"The generated ALSA configuration is missing. Regenerate it first.")"
			ACTION_RC=1
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
		ACTION_COMMAND='set equalizer flat'
		if [ "$ALSAEQUAL_ENABLED" != 'yes' ]; then
			ACTION_OUTPUT="$(lang de:"alsaequal ist derzeit deaktiviert." en:"alsaequal is currently disabled.")"
			ACTION_RC=1
		else
			ACTION_OUTPUT="$(set_flat_response)"
			[ -n "$ACTION_OUTPUT" ] || {
				ACTION_OUTPUT="$(lang de:"Keine Equalizer-Regler gefunden." en:"No equalizer controls found.")"
				ACTION_RC=1
			}
		fi
		;;
	generate_config)
		ACTION_TITLE="$(lang de:"ALSA-Konfiguration erzeugen" en:"Generate ALSA configuration")"
		ACTION_COMMAND='rc.alsaequal config'
		ACTION_OUTPUT="$(run_rc_alsaequal config 2>&1)"
		ACTION_RC=$?
		if [ "$ACTION_RC" -eq 0 ] && [ -s "$RUNTIME_CONFIG" ]; then
			if [ -n "$ACTION_OUTPUT" ]; then
				ACTION_OUTPUT="${ACTION_OUTPUT}\n$(lang de:"Generierte Datei:" en:"Generated file:") ${RUNTIME_CONFIG}"
			else
				ACTION_OUTPUT="$(lang de:"ALSA-Konfiguration erfolgreich erzeugt." en:"ALSA configuration generated successfully.")"
			fi
		elif [ "$ACTION_RC" -eq 0 ] && [ ! -s "$RUNTIME_CONFIG" ] && [ -z "$ACTION_OUTPUT" ]; then
			ACTION_OUTPUT="$(lang de:"Es wurde keine Konfigurationsdatei erzeugt. Prüfen Sie Bibliothek und Aktivierungsstatus." en:"No configuration file was generated. Check library availability and enablement.")"
			ACTION_RC=1
		fi
		;;
	reload_package)
		ACTION_TITLE="$(lang de:"Paket neu laden" en:"Reload package")"
		ACTION_COMMAND='rc.alsaequal unload && rc.alsaequal load'
		ACTION_OUTPUT="$({ run_rc_alsaequal unload 2>/dev/null || true; run_rc_alsaequal load; } 2>&1)"
		ACTION_RC=$?
		[ -n "$ACTION_OUTPUT" ] || ACTION_OUTPUT="$(lang de:"Paket neu geladen." en:"Package reloaded.")"
		;;
esac

if [ -n "$ACTION" ] && [ -z "$ACTION_OUTPUT" ]; then
	ACTION_OUTPUT='Command completed with no output.'
fi

if RESOLVED_LIBRARY="$(resolve_ladspa_library "$ALSAEQUAL_LIBRARY")"; then
	LIBRARY_STATE="present (${RESOLVED_LIBRARY})"
	LIBRARY_OK=yes
else
	LIBRARY_OK=no
	if [ "${ALSAEQUAL_LIBRARY#/}" != "$ALSAEQUAL_LIBRARY" ]; then
		LIBRARY_STATE="missing (${ALSAEQUAL_LIBRARY})"
	else
		LIBRARY_STATE="missing in search path (${ALSAEQUAL_LIBRARY})"
	fi
fi

CONTROL_IDS="$(equal_controls)"
CONTROL_COUNT="$(printf '%s\n' "$CONTROL_IDS" | sed '/^$/d' | wc -l | tr -d ' ')"
[ -n "$CONTROL_COUNT" ] || CONTROL_COUNT=0
RUNTIME_CONFIG_STATE=no
[ -s "$RUNTIME_CONFIG" ] && RUNTIME_CONFIG_STATE=yes
CONTROLS_STATE=no
[ -n "$CONTROL_IDS" ] && CONTROLS_STATE=yes

STATUS_HEADLINE=''
STATUS_TEXT=''
STATUS_CLASS='alsaeq-hero'
if [ "$ALSAEQUAL_ENABLED" != 'yes' ]; then
	STATUS_HEADLINE="$(lang de:"Equalizer ist deaktiviert" en:"Equalizer is disabled")"
	STATUS_TEXT="$(lang de:"Aktivieren Sie alsaequal auf der Konfigurationsseite und speichern Sie die Einstellungen, bevor Sie die Regler verwenden." en:"Enable alsaequal on the configuration page and save the settings before using the controls.")"
	STATUS_CLASS='alsaeq-hero alsaeq-hero-warning'
elif [ "$LIBRARY_OK" != 'yes' ]; then
	STATUS_HEADLINE="$(lang de:"LADSPA-Bibliothek fehlt" en:"LADSPA library is missing")"
	STATUS_TEXT="$(lang de:"Die konfigurierte Bibliothek ist nicht lesbar. Installieren oder korrigieren Sie die Library und erzeugen Sie danach die ALSA-Konfiguration neu." en:"The configured library is not readable. Install or fix the library, then regenerate the ALSA configuration.")"
	STATUS_CLASS='alsaeq-hero alsaeq-hero-warning'
elif [ "$RUNTIME_CONFIG_STATE" != 'yes' ]; then
	STATUS_HEADLINE="$(lang de:"Generierte ALSA-Konfiguration fehlt" en:"Generated ALSA configuration is missing")"
	STATUS_TEXT="$(lang de:"Erzeugen Sie '/var/lib/alsa/conf.d/50-alsaequal.conf' neu oder laden Sie das Paket, damit das virtuelle PCM 'equal' angelegt wird." en:"Regenerate '/var/lib/alsa/conf.d/50-alsaequal.conf' or reload the package so the virtual PCM 'equal' becomes available.")"
	STATUS_CLASS='alsaeq-hero alsaeq-hero-warning'
elif [ "$CONTROLS_STATE" != 'yes' ]; then
	STATUS_HEADLINE="$(lang de:"Regler derzeit nicht erreichbar" en:"Controls are currently unavailable")"
	STATUS_TEXT="$(lang de:"Die Konfiguration existiert, aber amixer kann 'equal' noch nicht öffnen. Laden Sie das Paket neu oder prüfen Sie die ALSA-Kette." en:"The configuration exists, but amixer still cannot open 'equal'. Reload the package or inspect the ALSA chain.")"
	STATUS_CLASS='alsaeq-hero alsaeq-hero-warning'
else
	STATUS_HEADLINE="$(lang de:"Equalizer bereit" en:"Equalizer ready")"
	STATUS_TEXT="$(lang de:"Passen Sie die Bänder an, testen Sie Presets und übernehmen Sie die Werte direkt in die laufende ALSA-Session." en:"Adjust bands, try presets, and apply the values directly to the running ALSA session.")"
fi

cat << EOF
<style type='text/css'>
.alsaeq-stack { display:grid; gap:16px; margin:10px 0 16px; }
.alsaeq-hero { display:flex; justify-content:space-between; gap:16px; align-items:flex-start; padding:16px; background:linear-gradient(135deg, #f7ecd8 0%, #fffaf1 100%); border:1px solid #dcc5a0; border-radius:16px; }
.alsaeq-hero h3 { margin:0 0 8px; color:#3b2811; font-size:20px; }
.alsaeq-hero p { margin:0; color:#694d23; max-width:760px; }
.alsaeq-hero-warning { background:linear-gradient(135deg, #fff0d8 0%, #fff9ef 100%); border-color:#d7a45a; }
.alsaeq-badges { display:flex; flex-wrap:wrap; gap:8px; justify-content:flex-end; }
.alsaeq-badge { display:inline-block; background:#efe1c5; color:#5d4420; border-radius:999px; padding:5px 10px; font-size:12px; }
.alsaeq-grid { display:grid; grid-template-columns:1fr; gap:16px; }
.alsaeq-panel { background:#fffdf8; border:1px solid #e2d0b1; border-radius:14px; padding:14px; box-shadow:0 1px 0 rgba(0,0,0,0.04); }
.alsaeq-panel h3 { margin:0 0 10px; color:#3b2811; }
.alsaeq-panel p { margin:0 0 12px; color:#6b542e; }
.alsaeq-actions { display:flex; flex-wrap:wrap; gap:8px; }
.alsaeq-actions form { display:inline-flex; align-items:center; gap:6px; margin:0; }
.alsaeq-console { background:#1f1a15; color:#f7eedf; border-radius:14px; padding:14px; overflow:auto; }
.alsaeq-console .cmd { color:#ffd27a; margin-bottom:8px; }
.alsaeq-console pre { margin:0; white-space:pre-wrap; word-break:break-word; }
.alsaeq-eq-shell { background:#fffaf1; border:1px solid #e3d1b2; border-radius:16px; padding:16px; }
.alsaeq-toolbar { display:flex; flex-wrap:wrap; justify-content:space-between; gap:12px; align-items:center; margin-bottom:14px; }
.alsaeq-toolbar h3 { margin:0; color:#3b2811; }
.alsaeq-toolbar p { margin:4px 0 0; color:#6b542e; }
.alsaeq-band-grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(130px, 1fr)); gap:12px; }
.alsaeq-band-card { background:#fffdf8; border:1px solid #eadcc6; border-radius:14px; padding:12px; display:grid; gap:10px; }
.alsaeq-band-title { font-weight:700; color:#3b2811; min-height:36px; }
.alsaeq-band-value { display:inline-block; justify-self:start; background:#efe1c5; color:#5d4420; border-radius:999px; padding:4px 10px; font-size:12px; }
.alsaeq-band-range { width:100%; accent-color:#c08324; }
.alsaeq-band-meta { display:flex; justify-content:space-between; gap:8px; font-size:12px; color:#85673a; }
.alsaeq-band-number { width:100%; box-sizing:border-box; }
.alsaeq-presets { display:flex; flex-wrap:wrap; gap:8px; margin-top:14px; }
.alsaeq-empty { padding:18px; border:1px dashed #d7b684; border-radius:14px; background:#fff7ea; color:#6a522b; }
@media (max-width: 960px) {
	.alsaeq-hero { flex-direction:column; }
	.alsaeq-badges { justify-content:flex-start; }
	.alsaeq-grid { grid-template-columns:1fr; }
	.alsaeq-toolbar { align-items:flex-start; }
}
</style>
EOF

sec_begin "$(lang de:"Equalizer-Status" en:"Equalizer status")"
cat << EOF
<div class='alsaeq-stack'>
	<div class='$(html "$STATUS_CLASS")'>
		<div>
			<h3>$(html "$STATUS_HEADLINE")</h3>
			<p>$(html "$STATUS_TEXT")</p>
		</div>
		<div class='alsaeq-badges'>
			<span class='alsaeq-badge'>$(lang de:"Aktiviert" en:"Enabled"): $(html "$ALSAEQUAL_ENABLED")</span>
			<span class='alsaeq-badge'>$(lang de:"Konfigurationsdatei" en:"Config file"): $(html "$RUNTIME_CONFIG_STATE")</span>
			<span class='alsaeq-badge'>$(lang de:"Regler" en:"Controls"): $(html "$CONTROL_COUNT")</span>
			<span class='alsaeq-badge'>$(lang de:"Bibliothek" en:"Library"): $(html "$LIBRARY_OK")</span>
		</div>
	</div>
	<div class='alsaeq-grid'>
		<div class='alsaeq-panel'>
			<h3>$(lang de:"Runtime-Details" en:"Runtime details")</h3>
			<table style='width:100%'>
EOF
print_row "$(lang de:"Als Standard setzen" en:"Use as default")" "$ALSAEQUAL_SET_DEFAULT"
print_row "$(lang de:"Generierte Konfiguration" en:"Generated configuration")" "$RUNTIME_CONFIG"
print_row "$(lang de:"PCM-Slave" en:"Slave PCM")" "$ALSAEQUAL_SLAVE_PCM"
print_row "$(lang de:"Steuerdatei" en:"Control file")" "$ALSAEQUAL_CONTROL_FILE"
print_row "$(lang de:"LADSPA-Bibliothek" en:"LADSPA library")" "$ALSAEQUAL_LIBRARY"
print_row "$(lang de:"Bibliotheksstatus" en:"Library status")" "$LIBRARY_STATE"
print_row "$(lang de:"Plugin-Modul" en:"Plugin module")" "$ALSAEQUAL_MODULE"
print_row "$(lang de:"Kanaele" en:"Channels")" "$ALSAEQUAL_CHANNELS"
print_row "$(lang de:"Equalizer-Regler erreichbar" en:"Equalizer controls available")" "$CONTROLS_STATE"
cat << EOF
			</table>
		</div>
	</div>
</div>
EOF
sec_end

if [ -n "$ACTION_OUTPUT" ]; then
	sec_begin "$ACTION_TITLE"
	cat << EOF
<div class='alsaeq-console'>
	<div class='cmd'>$(lang de:"Aktion" en:"Action"): $(html "$ACTION_TITLE")</div>
EOF
	if [ -n "$ACTION_COMMAND" ]; then
		echo "<div class='cmd'>$(html "$ACTION_COMMAND")</div>"
	fi
	if [ "$ACTION_RC" -ne 0 ]; then
		echo "<div class='cmd'>$(lang de:"Rueckgabecode" en:"Exit code"): $(html "$ACTION_RC")</div>"
	fi
	printf '%b' "$ACTION_OUTPUT" | html | {
		echo '<pre>'
		cat
		echo '</pre>'
	}
	cat << EOF
</div>
EOF
	sec_end
fi

sec_begin "$(lang de:"Grafischer Equalizer" en:"Graphical equalizer")"
if [ "$CONTROLS_STATE" = 'yes' ]; then
	cat << EOF
<div class='alsaeq-eq-shell'>
	<form id='alsaeqForm' action='$(href status alsaequal)' method='get'>
		<input type='hidden' name='action' value='apply_controls'>
		<div class='alsaeq-toolbar'>
			<div>
				<h3>$(lang de:"Bandauswahl" en:"Band controls")</h3>
				<p>$(lang de:"Die Presets setzen nur die Regler im Formular. Erst 'Werte anwenden' schreibt sie ins laufende Device." en:"Presets only stage values in the form. Use 'Apply values' to write them to the live device.")</p>
			</div>
			<div class='alsaeq-actions'>
				<input type='submit' value='$(lang de:"Werte anwenden" en:"Apply values")'>
				<a class='btn' href='$(href status alsaequal)?action=flat'>$(lang de:"Flat direkt senden" en:"Send flat directly")</a>
			</div>
		</div>
		<div class='alsaeq-band-grid'>
EOF
	for numid in $CONTROL_IDS; do
		name="$(control_label "$numid")"
		current="$(control_value "$numid")"
		min="$(control_min "$numid")"
		max="$(control_max "$numid")"
		step="$(control_step "$numid")"
		[ -n "$current" ] || current=0
		[ -n "$step" ] || step=1
		echo "<div class='alsaeq-band-card'>"
		echo "<label class='alsaeq-band-title' for='band_${numid}'>$(html "$name")</label>"
		echo "<div class='alsaeq-band-value' id='band_value_${numid}'>$(html "$(format_signed "$current")")</div>"
		echo "<input class='alsaeq-band-range' type='range' id='band_${numid}' name='band_${numid}' value='$(html "$current")' min='$(html "$min")' max='$(html "$max")' step='$(html "$step")' data-output='band_value_${numid}' data-number='band_number_${numid}'>"
		echo "<div class='alsaeq-band-meta'><span>$(html "$min") .. $(html "$max")</span><span>step $(html "$step")</span></div>"
		echo "<input class='alsaeq-band-number' type='number' id='band_number_${numid}' value='$(html "$current")' min='$(html "$min")' max='$(html "$max")' step='$(html "$step")'>"
		echo '</div>'
	done
	cat << EOF
		</div>
		<div class='alsaeq-presets'>
			<button type='button' onclick="window.alsaeqPreset('flat')">$(lang de:"Flat" en:"Flat")</button>
			<button type='button' onclick="window.alsaeqPreset('bass')">$(lang de:"Bass" en:"Bass")</button>
			<button type='button' onclick="window.alsaeqPreset('vocal')">$(lang de:"Stimme" en:"Vocal")</button>
			<button type='button' onclick="window.alsaeqPreset('treble')">$(lang de:"Hoehen" en:"Treble")</button>
			<button type='button' onclick="window.alsaeqPreset('smile')">$(lang de:"Smile" en:"Smile")</button>
		</div>
	</form>
</div>
<script type='text/javascript'>
(function () {
	function formatDb(value) {
		var num = parseInt(value, 10);
		if (isNaN(num)) {
			return value;
		}
		if (num > 0) {
			return '+' + num + ' dB';
		}
		return num + ' dB';
	}

	function clamp(value, min, max) {
		if (value < min) {
			return min;
		}
		if (value > max) {
			return max;
		}
		return value;
	}

	var ranges = Array.prototype.slice.call(document.querySelectorAll('.alsaeq-band-range'));

	function syncRange(range, nextValue) {
		var value = nextValue;
		var output = document.getElementById(range.getAttribute('data-output'));
		var number = document.getElementById(range.getAttribute('data-number'));
		if (typeof value === 'undefined') {
			value = range.value;
		}
		range.value = value;
		if (number) {
			number.value = value;
		}
		if (output) {
			output.textContent = formatDb(value);
		}
	}

	ranges.forEach(function (range) {
		var number = document.getElementById(range.getAttribute('data-number'));
		syncRange(range);
		range.addEventListener('input', function () {
			syncRange(range);
		});
		if (number) {
			number.addEventListener('input', function () {
				var min = parseInt(range.min, 10);
				var max = parseInt(range.max, 10);
				var value = parseInt(number.value, 10);
				if (isNaN(value)) {
					return;
				}
				syncRange(range, clamp(value, min, max));
			});
		}
	});

	window.alsaeqPreset = function (name) {
		var presets = {
			flat:   [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
			bass:   [6, 5, 4, 2, 0, -1, -2, -2, -3, -3],
			vocal:  [-2, -1, 1, 3, 4, 4, 3, 1, -1, -2],
			treble: [-3, -3, -2, -1, 0, 2, 4, 5, 6, 6],
			smile:  [5, 4, 2, 0, -1, -1, 0, 2, 4, 5]
		};
		var preset = presets[name] || presets.flat;
		ranges.forEach(function (range, index) {
			var min = parseInt(range.min, 10);
			var max = parseInt(range.max, 10);
			var value = preset[Math.min(index, preset.length - 1)];
			syncRange(range, clamp(value, min, max));
		});
	};
})();
</script>
EOF
else
	cat << EOF
<div class='alsaeq-empty'>
	<strong>$(html "$STATUS_HEADLINE")</strong><br>
	$(html "$STATUS_TEXT")
</div>
EOF
	if [ "$ALSAEQUAL_ENABLED" = 'yes' ] && [ "$LIBRARY_OK" = 'yes' ] && [ "$RUNTIME_CONFIG_STATE" = 'yes' ]; then
		echo '<pre class="log full">'
		amixer -D equal controls 2>&1 | html
		echo '</pre>'
	fi
fi
sec_end

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