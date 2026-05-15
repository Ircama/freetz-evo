#!/bin/sh

. /usr/lib/libmodcgi.sh

sec_begin "$(lang de:"Starttyp" en:"Start type")"
cgi_print_radiogroup_service_starttype "enabled" "$GO_LIBRESPOT_ENABLED" "" "" 0
sec_end

sec_begin "$(lang de:"Anzeigen" en:"Show")"
cat << EOF
<ul>
<li><a href="$(href status go-librespot)?refresh=5">$(lang de:"Status anzeigen" en:"Show status")</a></li>
</ul>
EOF
sec_end

sec_begin "$(lang de:"Spotify Connect" en:"Spotify Connect")"
cgi_print_textline_p "device_name" "$GO_LIBRESPOT_DEVICE_NAME" 32/80 \
	"$(lang de:"Geraetename" en:"Device name"): "
cgi_print_radiogroup "device_type" "$GO_LIBRESPOT_DEVICE_TYPE" "" "" \
	"speaker::Speaker" \
	"computer::Computer" \
	"avr::AV Receiver" \
	"cast_audio::Cast Audio" \
	"audio_dongle::Audio Dongle"
cgi_print_radiogroup "bitrate" "$GO_LIBRESPOT_BITRATE" "" "" \
	"96::96 kbps" \
	"160::160 kbps" \
	"320::320 kbps"
sec_end

sec_begin "$(lang de:"ALSA-Ausgabe" en:"ALSA output")"
cgi_print_textline_p "audio_device" "$GO_LIBRESPOT_AUDIO_DEVICE" 32/128 \
	"$(lang de:"Ausgabegeraet" en:"Output device"): "
cgi_print_textline_p "mixer_device" "$GO_LIBRESPOT_MIXER_DEVICE" 32/128 \
	"$(lang de:"Mixer-Geraet (optional)" en:"Mixer device (optional)"): "
cgi_print_textline_p "mixer_control_name" "$GO_LIBRESPOT_MIXER_CONTROL_NAME" 24/128 \
	"$(lang de:"Mixer-Regler (optional)" en:"Mixer control (optional)"): "
cgi_print_textline_p "audio_buffer_time" "$GO_LIBRESPOT_AUDIO_BUFFER_TIME" 12/16 \
	"$(lang de:"Buffer-Zeit in us (optional)" en:"Buffer time in us (optional)"): "
cgi_print_textline_p "audio_period_count" "$GO_LIBRESPOT_AUDIO_PERIOD_COUNT" 8/8 \
	"$(lang de:"Periodenanzahl (optional)" en:"Period count (optional)"): "
sec_end

sec_begin "$(lang de:"Persistenz und Netzwerk" en:"Persistence and networking")"
cgi_print_textline_p "config_dir" "$GO_LIBRESPOT_CONFIG_DIR" 40/128 \
	"$(lang de:"Konfigurationsverzeichnis" en:"Configuration directory"): "
cgi_print_textline_p "zeroconf_port" "$GO_LIBRESPOT_ZEROCONF_PORT" 8/8 \
	"$(lang de:"Zeroconf-Port (optional)" en:"Zeroconf port (optional)"): "
cgi_print_textline_p "zeroconf_interfaces" "$GO_LIBRESPOT_ZEROCONF_INTERFACES" 32/128 \
	"$(lang de:"Advertised Interfaces (leer = alle)" en:"Advertised interfaces (empty = all)"): "
cgi_print_checkbox_p "persist_credentials" "$GO_LIBRESPOT_PERSIST_CREDENTIALS" \
	"$(lang de:"Zeroconf-Zugangsdaten speichern" en:"Persist Zeroconf credentials")"
sec_end

sec_begin "$(lang de:"Wiedergabe und Logging" en:"Playback and logging")"
cgi_print_textline_p "volume_steps" "$GO_LIBRESPOT_VOLUME_STEPS" 8/8 \
	"$(lang de:"Lautstaerkestufen" en:"Volume steps"): "
cgi_print_textline_p "initial_volume" "$GO_LIBRESPOT_INITIAL_VOLUME" 8/8 \
	"$(lang de:"Initiale Lautstaerke" en:"Initial volume"): "
cgi_print_checkbox_p "disable_autoplay" "$GO_LIBRESPOT_DISABLE_AUTOPLAY" \
	"$(lang de:"Autoplay deaktivieren" en:"Disable autoplay")"
cgi_print_radiogroup "log_level" "$GO_LIBRESPOT_LOG_LEVEL" "" "" \
	"error::Error" \
	"warn::Warn" \
	"info::Info" \
	"debug::Debug" \
	"trace::Trace"
sec_end

if [ -r /proc/asound/cards ]; then
	sec_begin "$(lang de:"Erkannte Soundkarten" en:"Detected sound cards")"
	echo '<pre class="log full">'
	cat /proc/asound/cards | html
	echo '</pre>'
	sec_end
fi