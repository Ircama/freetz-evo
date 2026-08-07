#!/bin/sh

. /usr/lib/libmodcgi.sh

# Load configuration
[ -r /etc/options.cfg ] && . /etc/options.cfg
[ -r /mod/etc/conf/hidws.cfg ] && . /mod/etc/conf/hidws.cfg

# Determine running state
IS_RUNNING="no"
pgrep -x hidws >/dev/null 2>&1 && IS_RUNNING="yes"

sec_begin "$(lang de:"Starttyp" en:"Start type")"
cgi_print_radiogroup_service_starttype "enabled" "$HIDWS_ENABLED" "" "" 0
sec_end

sec_begin "$(lang de:"Daemon" en:"Daemon")"
cgi_print_textline_p "port" "$HIDWS_PORT" 5/5 \
	"$(lang de:"WebSocket-Port" en:"WebSocket port"): "
cgi_print_textline_p "nice" "$HIDWS_NICE" 4/4 \
	"$(lang de:"Prozesspriorität (nice)" en:"Process priority (nice)"): "
cgi_print_checkbox_p "ssl" "${HIDWS_SSL:-yes}" \
	"$(lang de:"SSL/TLS aktivieren (wss:// zusätzlich zu ws://)" en:"Enable SSL/TLS (wss:// in addition to ws://)"): "
cgi_print_textline_p "cert" "${HIDWS_CERT:-/mod/etc/hidws/server.crt}" 40/160 \
	"$(lang de:"Zertifikatspfad" en:"Certificate path"): "
cgi_print_textline_p "key" "${HIDWS_KEY:-/mod/etc/hidws/server.key}" 40/160 \
	"$(lang de:"Schlüsselpfad" en:"Private key path"): "
cat << EOF
<p>
<strong>$(lang de:"Status" en:"Status"):</strong>
EOF
if [ "$IS_RUNNING" = "yes" ]; then
	echo "<span style='color:#28a745;font-weight:bold;'>&#x25CF; $(lang de:"läuft" en:"running")</span>"
else
	echo "<span style='color:#dc3545;font-weight:bold;'>&#x25CF; $(lang de:"gestoppt" en:"stopped")</span>"
fi
if [ "${HIDWS_SSL:-yes}" = "yes" ]; then
cat << EOF
&nbsp;&nbsp;<small>$(lang de:"Endpunkte" en:"Endpoints"): <code>ws://fritz.box:${HIDWS_PORT:-9001}</code> $(lang de:"und" en:"and") <code>wss://fritz.box:${HIDWS_PORT:-9001}</code></small>
</p>
<p><small>$(lang de:"Ein selbstsigniertes Zertifikat wird beim ersten Start automatisch erzeugt. Browser melden es als unsicher, die Verbindung funktioniert aber trotzdem." en:"A self-signed certificate is generated automatically on first start. Browsers flag it as untrusted, but the connection still works.")</small></p>
EOF
else
cat << EOF
&nbsp;&nbsp;<small>$(lang de:"WebSocket-Endpunkt" en:"WebSocket endpoint"): <code>ws://fritz.box:${HIDWS_PORT:-9001}</code></small>
</p>
EOF
fi
sec_end

sec_begin "$(lang de:"Web-Apps" en:"Web apps")"
cat << EOF
<p>$(lang de:"Diese Web-Apps verbinden sich über WebSocket mit hidws:" en:"These web apps connect to hidws over WebSocket:")</p>
<ul style="margin:4px 0 8px 0; padding-left:20px;">
<li><a href="https://ircama.github.io/fiiocontrol/" target="_blank" rel="noopener">fiiocontrol</a> — <small>$(lang de:"Offizielle FiiO-Control-Web-App (Equalizer / Custom)" en:"Official FiiO Control web app (equalizer / custom)")</small></li>
<li><a href="https://ircama.github.io/walkplay/" target="_blank" rel="noopener">walkplay</a> — <small>$(lang de:"Steuerung für Walk-Play-Geräte (z. B. Hi-MAX mit DAC-Chip CB1200AU)" en:"Control for Walk Play devices (e.g., Hi-MAX using the DAC chip CB1200AU)")</small></li>
<li><a href="https://ircama.github.io/kt02h20-control/" target="_blank" rel="noopener">kt02h20-control</a> — <small>$(lang de:"Steuerung für FiiO JA11 (KT02H20)" en:"Control for FiiO JA11 (KT02H20)")</small></li>
<li><a href="https://ircama.github.io/Audiocular-Aura/" target="_blank" rel="noopener">Audiocular-Aura (AuraPEQ)</a> — <small>$(lang de:"Parametrischer Equalizer für USB-DACs" en:"Parametric equalizer for USB DACs")</small></li>
<li><a href="https://ircama.github.io/fiiocontrol-oss/" target="_blank" rel="noopener">fiiocontrol-oss</a> — <small>$(lang de:"EQ-Steuerung für FiiO DACs" en:"EQ control for FiiO DACs")</small></li>
<li><a href="https://ircama.github.io/webhid-explorer/" target="_blank" rel="noopener">webhid-explorer</a> — <small>$(lang de:"HID-Explorer (Geräte, Report-Deskriptoren)" en:"HID explorer (devices, report descriptors)")</small></li>
</ul>
<p><small>$(lang de:"Hinweis: Auf HTTPS-Seiten (GitHub Pages) kann eine unsichere ws://-Verbindung blockiert werden. Dann wss:// verwenden oder die App lokal über http ausführen." en:"Note: on HTTPS pages (GitHub Pages) an insecure ws:// connection may be blocked; use wss:// or run the app locally over http.")</small></p>
EOF
sec_end

sec_begin "$(lang de:"Ausführungsprotokoll" en:"Execution log")"
cat << 'EOF'
<div style="background:#f8f9fa;border:1px solid #dee2e6;border-radius:4px;padding:12px;margin-bottom:10px;">
<p style="margin:0 0 8px 0;"><strong>&#128203; /tmp/rc.hidws.log</strong></p>
<pre style="background:#272822;color:#f8f8f2;padding:12px;border-radius:4px;overflow-x:auto;max-height:200px;overflow-y:auto;margin:0;font-family:'Courier New',monospace;font-size:12px;line-height:1.5;">
EOF
if [ -s "/tmp/rc.hidws.log" ]; then
	tail -n 100 /tmp/rc.hidws.log | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g'
else
	echo "$(lang de:"(kein Eintrag)" en:"(no entries)")"
fi
cat << 'EOF'
</pre>
</div>
<div style="background:#f8f9fa;border:1px solid #dee2e6;border-radius:4px;padding:12px;">
<p style="margin:0 0 8px 0;"><strong>&#128203; /tmp/hidws.log</strong></p>
<pre style="background:#272822;color:#f8f8f2;padding:12px;border-radius:4px;overflow-x:auto;max-height:300px;overflow-y:auto;margin:0;font-family:'Courier New',monospace;font-size:12px;line-height:1.5;">
EOF
if [ -s "/tmp/hidws.log" ]; then
	tail -n 100 /tmp/hidws.log | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g'
else
	echo "$(lang de:"(kein Eintrag)" en:"(no entries)")"
fi
cat << 'EOF'
</pre>
</div>
EOF
sec_end
