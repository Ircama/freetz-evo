#!/bin/sh

. /usr/lib/libmodcgi.sh

[ -r /mod/etc/conf/alsa-utils.cfg ] && . /mod/etc/conf/alsa-utils.cfg

: ${ALSA_UTILS_PCM_DEVICE:=default}
: ${ALSA_UTILS_MIXER_DEVICE:=default}
: ${ALSA_UTILS_VOLUME_CONTROL:=}
: ${ALSA_UTILS_TEST_CHANNELS:=2}
: ${ALSA_UTILS_SAMPLE_FILE:=}

sec_begin "$(lang de:"Standardwerte" en:"Defaults")"
cgi_print_textline_p "pcm_device" "$ALSA_UTILS_PCM_DEVICE" 24/128 \
	"$(lang de:"Standard-PCM-Ger\u00e4t" en:"Default PCM device"): "
cgi_print_textline_p "mixer_device" "$ALSA_UTILS_MIXER_DEVICE" 24/128 \
	"$(lang de:"Standard-Mixer-Ger\u00e4t" en:"Default mixer device"): "
cgi_print_textline_p "volume_control" "$ALSA_UTILS_VOLUME_CONTROL" 24/128 \
	"$(lang de:"Standard-Lautst\u00e4rkeregler (leer = auto)" en:"Default volume control (empty = auto)"): "
cgi_print_textline_p "test_channels" "$ALSA_UTILS_TEST_CHANNELS" 4/8 \
	"$(lang de:"Standard-Kan\u00e4le f\u00fcr speaker-test" en:"Default speaker-test channels"): "
cgi_print_textline_p "sample_file" "$ALSA_UTILS_SAMPLE_FILE" 24/128 \
	"$(lang de:"Standard-Sample-Datei (optional)" en:"Default sample file (optional)"): "
sec_end

sec_begin "$(lang de:"Anzeigen" en:"Show")"
cat << EOF
<ul>
<li><a href="$(href status alsa-utils)">$(lang de:"Audio-Status und Tests anzeigen" en:"Show audio status and test tools")</a></li>
</ul>
EOF
sec_end

sec_begin "$(lang de:"Hinweis zu alsamixer" en:"About alsamixer")"
cat << EOF
<p>
$(lang de:"<code>alsamixer</code> fehlt hier absichtlich, weil das aktuelle Paket mit <code>--disable-alsamixer</code> gebaut wird, um die ncurses-Oberfl\u00e4chenabh\u00e4ngigkeit klein zu halten. Verwenden Sie stattdessen <code>amixer</code> oder diese Web-Oberfl\u00e4che." en:"<code>alsamixer</code> is intentionally absent here because the current package is built with <code>--disable-alsamixer</code> to avoid the ncurses UI dependency stack. Use <code>amixer</code> or this web UI instead.")
</p>
<p>
$(lang de:"Wenn kein Lautst\u00e4rkeregler eingetragen ist, versucht die Statusseite automatisch den ersten verf\u00fcgbaren einfachen ALSA-Regler des gew\u00e4hlten Mixer-Ger\u00e4ts zu verwenden." en:"If no volume control is configured, the status page automatically tries to use the first available simple ALSA control of the selected mixer device.")
</p>
EOF
sec_end

if [ -r /proc/asound/cards ]; then
	sec_begin "$(lang de:"Erkannte Soundkarten" en:"Detected sound cards")"
	echo '<pre class="log full">'
	cat /proc/asound/cards | html
	echo '</pre>'
	sec_end
fi