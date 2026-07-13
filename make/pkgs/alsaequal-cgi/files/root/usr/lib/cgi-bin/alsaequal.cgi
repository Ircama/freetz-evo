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

sec_begin "$(lang de:"Aktivierung" en:"Activation")"
cgi_print_checkbox_p "enabled" "$ALSAEQUAL_ENABLED" \
	"$(lang de:"Equalizer-Ger\u00e4t aktivieren" en:"Enable equalizer device")"
cgi_print_checkbox_p "set_default" "$ALSAEQUAL_SET_DEFAULT" \
	"$(lang de:"Als Standard-PCM/-Mixer verwenden" en:"Route default PCM/control through equalizer")"
sec_end

sec_begin "$(lang de:"ALSA-Konfiguration" en:"ALSA configuration")"
cgi_print_textline_p "slave_pcm" "$ALSAEQUAL_SLAVE_PCM" 32/128 \
	"$(lang de:"Slave-PCM (z.B. plughw:0,0)" en:"Slave PCM (e.g. plughw:0,0)"): "
cgi_print_textline_p "control_file" "$ALSAEQUAL_CONTROL_FILE" 40/160 \
	"$(lang de:"Steuerdatei" en:"Control file"): "
cgi_print_textline_p "library" "$ALSAEQUAL_LIBRARY" 32/160 \
	"$(lang de:"LADSPA-Bibliothek" en:"LADSPA library"): "
cgi_print_textline_p "module" "$ALSAEQUAL_MODULE" 20/64 \
	"$(lang de:"Plugin-Modul" en:"Plugin module"): "
cgi_print_textline_p "channels" "$ALSAEQUAL_CHANNELS" 4/8 \
	"$(lang de:"Kan\u00e4le" en:"Channels"): "
	cat << EOF
<p>
$(lang de:"Die exportierten ALSA-Ger\u00e4tenamen sind fest auf <code>equal</code> und <code>plugequal</code> gesetzt." en:"The exported ALSA device names are fixed to <code>equal</code> and <code>plugequal</code>.")
</p>
<p>
$(lang de:"Der Standardwert <code>caps.so</code> passt zur mit Freetz-EVO verfuegbaren CAPS/Eq10-LADSPA-Bibliothek. Du kannst hier aber weiterhin eine andere kompatible LADSPA-Bibliothek oder einen absoluten Pfad eintragen." en:"The default <code>caps.so</code> value matches the CAPS/Eq10 LADSPA library available with Freetz-EVO. You can still override it with another compatible LADSPA library or an absolute path.")
</p>
EOF
sec_end

sec_begin "$(lang de:"Anzeigen" en:"Show")"
cat << EOF
<ul>
<li><a href="$(href status alsaequal)">$(lang de:"Runtime-Steuerung und Status anzeigen" en:"Show runtime control and status")</a></li>
</ul>
EOF
sec_end

if [ -r /proc/asound/cards ]; then
	sec_begin "$(lang de:"Erkannte Soundkarten" en:"Detected sound cards")"
	echo '<pre class="log full">'
	cat /proc/asound/cards | html
	echo '</pre>'
	sec_end
fi