#!/bin/sh

. /usr/lib/libmodcgi.sh

sec_begin "$(lang de:"Starttyp" en:"Start type")"
cgi_print_radiogroup_service_starttype "enabled" "$MPD_ENABLED" "" "" 0
sec_end

sec_begin "$(lang de:"Anzeigen" en:"Show")"
cat << EOF
<ul>
<li><a href="$(href status mpd)?refresh=5">$(lang de:"Status anzeigen" en:"Show status")</a></li>
</ul>
EOF
sec_end

sec_begin "$(lang de:"Verzeichnisse und Listener" en:"Directories and listeners")"
cgi_print_textline_p "config_dir" "$MPD_CONFIG_DIR" 40/128 \
	"$(lang de:"Arbeitsverzeichnis" en:"Working directory"): "
cgi_print_textline_p "music_dir" "$MPD_MUSIC_DIR" 40/255 \
	"$(lang de:"Musikverzeichnis" en:"Music directory"): "
cgi_print_textline_p "bind_to_address" "$MPD_BIND_TO_ADDRESS" 24/128 \
	"$(lang de:"Bind-Adresse (leer = nur Unix-Socket)" en:"Bind address (empty = Unix socket only)"): "
cgi_print_textline_p "port" "$MPD_PORT" 8/8 \
	"$(lang de:"TCP-Port" en:"TCP port"): "
sec_end

sec_begin "$(lang de:"ALSA-Ausgabe" en:"ALSA output")"
cgi_print_textline_p "alsa_output_name" "$MPD_ALSA_OUTPUT_NAME" 24/80 \
	"$(lang de:"Output-Name" en:"Output name"): "
cgi_print_textline_p "alsa_device" "$MPD_ALSA_DEVICE" 32/128 \
	"$(lang de:"ALSA-Geraet" en:"ALSA device"): "
cgi_print_radiogroup "mixer_type" "$MPD_MIXER_TYPE" "" "" \
	"hardware::Hardware" \
	"software::Software" \
	"none::None"
cgi_print_textline_p "mixer_device" "$MPD_MIXER_DEVICE" 24/128 \
	"$(lang de:"Mixer-Geraet (nur Hardware)" en:"Mixer device (hardware only)"): "
cgi_print_textline_p "mixer_control" "$MPD_MIXER_CONTROL" 24/128 \
	"$(lang de:"Mixer-Regler (nur Hardware)" en:"Mixer control (hardware only)"): "
cgi_print_textline_p "audio_format" "$MPD_AUDIO_FORMAT" 16/32 \
	"$(lang de:"Audioformat (optional, z.B. 44100:16:2)" en:"Audio format (optional, e.g. 44100:16:2)"): "
sec_end

sec_begin "$(lang de:"Laufzeitoptionen" en:"Runtime options")"
cgi_print_checkbox_p "auto_update" "$MPD_AUTO_UPDATE" \
	"$(lang de:"Musikdatenbank automatisch aktualisieren" en:"Automatically update music database")"
cgi_print_checkbox_p "restore_paused" "$MPD_RESTORE_PAUSED" \
	"$(lang de:"Nach Neustart pausiert bleiben" en:"Restore paused state on startup")"
cgi_print_radiogroup "log_level" "$MPD_LOG_LEVEL" "" "" \
	"error::Error" \
	"warning::Warning" \
	"notice::Notice" \
	"info::Info" \
	"verbose::Verbose"
sec_end

if [ -r /proc/asound/cards ]; then
	sec_begin "$(lang de:"Erkannte Soundkarten" en:"Detected sound cards")"
	echo '<pre class="log full">'
	cat /proc/asound/cards | html
	echo '</pre>'
	sec_end
fi