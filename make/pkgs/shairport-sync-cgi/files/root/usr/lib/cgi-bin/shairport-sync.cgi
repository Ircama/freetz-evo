#!/bin/sh

. /usr/lib/libmodcgi.sh

sec_begin "$(lang de:"Starttyp" en:"Start type")"
cgi_print_radiogroup_service_starttype "enabled" "$SHAIRPORT_SYNC_ENABLED" "" "" 0
sec_end

sec_begin "$(lang de:"Anzeigen" en:"Show")"
cat << EOF
<ul>
<li><a href="$(href status shairport-sync)">$(lang de:"Status anzeigen" en:"Show status")</a></li>
</ul>
EOF
sec_end

sec_begin "$(lang de:"AirPlay Empfaenger" en:"AirPlay receiver")"
cgi_print_textline_p "name" "$SHAIRPORT_SYNC_NAME" 40/50 \
	"$(lang de:"Dienstname" en:"Service name"): "
cgi_print_password_p "password" "$SHAIRPORT_SYNC_PASSWORD" 24/128 \
	"$(lang de:"Passwort (optional)" en:"Password (optional)"): "
cgi_print_textline_p "interface" "$SHAIRPORT_SYNC_INTERFACE" 16/32 \
	"$(lang de:"Netzwerk-Interface (leer = alle)" en:"Network interface (empty = all)"): "
sec_end

sec_begin "$(lang de:"ALSA-Ausgabe" en:"ALSA output")"
cgi_print_textline_p "output_device" "$SHAIRPORT_SYNC_OUTPUT_DEVICE" 32/128 \
	"$(lang de:"Ausgabegeraet (z.B. plughw:0,0, hw:0,0 oder default)" en:"Output device (e.g. plughw:0,0, hw:0,0 or default)"): "
cgi_print_textline_p "output_format" "$SHAIRPORT_SYNC_OUTPUT_FORMAT" 16/32 \
	"$(lang de:"Ausgabeformat (optional, z.B. S16)" en:"Output format (optional, e.g. S16)"): "
cgi_print_textline_p "output_rate" "$SHAIRPORT_SYNC_OUTPUT_RATE" 8/16 \
	"$(lang de:"Ausgaberate (optional, z.B. 44100 oder auto)" en:"Output rate (optional, e.g. 44100 or auto)"): "
cgi_print_textline_p "mixer_control_name" "$SHAIRPORT_SYNC_MIXER_CONTROL_NAME" 24/128 \
	"$(lang de:"Mixer-Regler (optional)" en:"Mixer control (optional)"): "
cgi_print_textline_p "mixer_device" "$SHAIRPORT_SYNC_MIXER_DEVICE" 32/128 \
	"$(lang de:"Mixer-Geraet (optional)" en:"Mixer device (optional)"): "
sec_end

sec_begin "$(lang de:"Start- und Diagnoseoptionen" en:"Startup and diagnostics")"
cgi_print_radiogroup "interpolation" "$SHAIRPORT_SYNC_INTERPOLATION" "" "" \
	"auto::Auto" \
	"vernier::Vernier" \
	"basic::Basic"
cgi_print_checkbox_p "ignore_volume_control" "$SHAIRPORT_SYNC_IGNORE_VOLUME_CONTROL" \
	"$(lang de:"Quell-Lautstaerke ignorieren" en:"Ignore source volume")"
cgi_print_checkbox_p "statistics" "$SHAIRPORT_SYNC_STATISTICS" \
	"$(lang de:"Statistiken ins Log schreiben" en:"Write statistics to log")"
cgi_print_textline_p "log_verbosity" "$SHAIRPORT_SYNC_LOG_VERBOSITY" 1 \
	"$(lang de:"Log-Verbosity (0-3)" en:"Log verbosity (0-3)"): "
sec_end

if [ -r /proc/asound/cards ]; then
	sec_begin "$(lang de:"Erkannte Soundkarten" en:"Detected sound cards")"
	echo '<pre class="log full">'
	cat /proc/asound/cards | html
	echo '</pre>'
	sec_end
fi