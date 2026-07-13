#!/bin/sh

. /usr/lib/libmodcgi.sh

sec_begin "$(lang de:"Starttyp" en:"Start type")"
cgi_print_radiogroup_service_starttype "enabled" "$SNAPCAST_ENABLED" "" "" 0
sec_end

sec_begin "$(lang de:"Anzeigen" en:"Show")"
cat << EOF
<ul>
<li><a href="$(href status snapcast)?refresh=5">$(lang de:"Status anzeigen" en:"Show status")</a></li>
</ul>
EOF
sec_end

sec_begin "$(lang de:"Komponenten" en:"Components")"
cgi_print_checkbox_p "server_enabled" "$SNAPCAST_SERVER_ENABLED" \
	"$(lang de:"Snapserver starten" en:"Start snapserver")"
cgi_print_checkbox_p "client_enabled" "$SNAPCAST_CLIENT_ENABLED" \
	"$(lang de:"Lokalen snapclient starten" en:"Start local snapclient")"
sec_end

sec_begin "$(lang de:"Snapserver" en:"Snapserver")"
cgi_print_textline_p "server_data_dir" "$SNAPCAST_SERVER_DATA_DIR" 40/128 \
	"$(lang de:"Datenverzeichnis" en:"Data directory"): "
cgi_print_checkbox_p "http_enabled" "$SNAPCAST_HTTP_ENABLED" \
	"$(lang de:"HTTP-Weboberflaeche aktivieren" en:"Enable HTTP web UI")"
cgi_print_textline_p "http_bind_to_address" "$SNAPCAST_HTTP_BIND_TO_ADDRESS" 20/64 \
	"$(lang de:"HTTP-Bind-Adresse" en:"HTTP bind address"): "
cgi_print_textline_p "http_port" "$SNAPCAST_HTTP_PORT" 8/8 \
	"$(lang de:"HTTP-Port" en:"HTTP port"): "
cgi_print_textline_p "tcp_control_bind_to_address" "$SNAPCAST_TCP_CONTROL_BIND_TO_ADDRESS" 20/64 \
	"$(lang de:"Control-Bind-Adresse" en:"Control bind address"): "
cgi_print_textline_p "tcp_control_port" "$SNAPCAST_TCP_CONTROL_PORT" 8/8 \
	"$(lang de:"Control-Port" en:"Control port"): "
cgi_print_textline_p "stream_bind_to_address" "$SNAPCAST_STREAM_BIND_TO_ADDRESS" 20/64 \
	"$(lang de:"Stream-Bind-Adresse" en:"Stream bind address"): "
cgi_print_textline_p "stream_port" "$SNAPCAST_STREAM_PORT" 8/8 \
	"$(lang de:"Stream-Port" en:"Stream port"): "
sec_end

sec_begin "$(lang de:"Stream-Quelle" en:"Stream source")"
cgi_print_textline_p "stream_source" "$SNAPCAST_STREAM_SOURCE" 72/255 \
	"$(lang de:"Source-URI" en:"Source URI"): "
cgi_print_textline_p "stream_default_source" "$SNAPCAST_STREAM_DEFAULT_SOURCE" 24/80 \
	"$(lang de:"Standard-Quelle (optional)" en:"Default source (optional)"): "
cgi_print_radiogroup "stream_codec" "$SNAPCAST_STREAM_CODEC" "" "" \
	"flac::FLAC" \
	"ogg::Ogg/Vorbis" \
	"pcm::PCM"
cgi_print_textline_p "stream_sampleformat" "$SNAPCAST_STREAM_SAMPLEFORMAT" 16/32 \
	"$(lang de:"Sampleformat" en:"Sample format"): "
cgi_print_textline_p "stream_chunk_ms" "$SNAPCAST_STREAM_CHUNK_MS" 8/8 \
	"$(lang de:"Chunk-Groesse in ms" en:"Chunk size in ms"): "
cgi_print_textline_p "stream_buffer" "$SNAPCAST_STREAM_BUFFER" 8/8 \
	"$(lang de:"Puffer in ms" en:"Buffer in ms"): "
cgi_print_textline_p "log_filter" "$SNAPCAST_LOG_FILTER" 24/128 \
	"$(lang de:"Server-Logfilter" en:"Server log filter"): "
sec_end

sec_begin "$(lang de:"Lokaler snapclient" en:"Local snapclient")"
cgi_print_textline_p "client_host" "$SNAPCAST_CLIENT_HOST" 24/64 \
	"$(lang de:"Server-Host" en:"Server host"): "
cgi_print_textline_p "client_port" "$SNAPCAST_CLIENT_PORT" 8/8 \
	"$(lang de:"Server-Port" en:"Server port"): "
cgi_print_textline_p "client_sound_card" "$SNAPCAST_CLIENT_SOUND_CARD" 32/128 \
	"$(lang de:"ALSA-Geraet" en:"ALSA device"): "
cgi_print_radiogroup "client_mixer" "$SNAPCAST_CLIENT_MIXER" "" "" \
	"software::Software" \
	"hardware::Hardware" \
	"none::None"
cgi_print_textline_p "client_latency" "$SNAPCAST_CLIENT_LATENCY" 8/8 \
	"$(lang de:"Latenz" en:"Latency"): "
cgi_print_textline_p "client_instance" "$SNAPCAST_CLIENT_INSTANCE" 4/8 \
	"$(lang de:"Instanz-ID" en:"Instance id"): "
cgi_print_textline_p "client_host_id" "$SNAPCAST_CLIENT_HOST_ID" 24/64 \
	"$(lang de:"Host-ID (optional)" en:"Host ID (optional)"): "
cgi_print_textline_p "client_log_filter" "$SNAPCAST_CLIENT_LOG_FILTER" 24/128 \
	"$(lang de:"Client-Logfilter" en:"Client log filter"): "
sec_end

if [ -r /proc/asound/cards ]; then
	sec_begin "$(lang de:"Erkannte Soundkarten" en:"Detected sound cards")"
	echo '<pre class="log full">'
	cat /proc/asound/cards | html
	echo '</pre>'
	sec_end
fi