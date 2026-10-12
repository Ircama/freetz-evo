#!/bin/sh

. /usr/lib/libmodcgi.sh

sec_begin "$(lang de:"Starttyp" en:"Start type")"
cgi_print_radiogroup_service_starttype "enabled" "$DOMOTICZ_ENABLED" "" "" 0
sec_end

sec_begin "$(lang de:"Webinterface" en:"Web interface")"
cat << EOF
<p>$(lang de:"Webinterface-URL" en:"Web interface URL"): <a href="http://$(html "$DOMOTICZ_HOSTNAME"):$(html "$DOMOTICZ_WWW_PORT")/" target="_blank">http://&lt;$DOMOTICZ_HOSTNAME&gt;:$DOMOTICZ_WWW_PORT/</a></p>
<p>$(lang de:"HTTP-Port (1-49151, 0 = aus)" en:"HTTP port (1-49151, 0 = off)"): <input type="text" name="www_port" size="8" maxlength="5" value="$(html "$DOMOTICZ_WWW_PORT")"></p>
<p>$(lang de:"HTTPS-Port (1-49151, 0 = aus)" en:"HTTPS port (1-49151, 0 = off)"): <input type="text" name="ssl_port" size="8" maxlength="5" value="$(html "$DOMOTICZ_SSL_PORT")"></p>
EOF
sec_end

sec_begin "$(lang de:"Datenverzeichnis" en:"Data directory")"
cat << EOF
<p>$(lang de:"Datenbank, Logs und Zertifikat" en:"Database, logs and certificate"): <input type="text" name="userdata" size="50" maxlength="255" value="$(html "$DOMOTICZ_USERDATA")"></p>
<p>$(lang de:"Warten auf das Speichermedium (Sekunden, 0 = sofort)" en:"Wait for the storage device (seconds, 0 = immediately)"): <input type="text" name="config_wait" size="8" maxlength="5" value="$(html "$DOMOTICZ_CONFIG_WAIT")"></p>
EOF
sec_end

sec_begin "$(lang de:"Protokoll" en:"Logging")"
cat << EOF
<p>$(lang de:"Log-Level (leer = Standard)" en:"Log level (empty = default)"): <input type="text" name="loglevel" size="12" maxlength="20" value="$(html "$DOMOTICZ_LOGLEVEL")"></p>
<p>$(lang de:"Zusaetzliche Kommandozeilenoptionen" en:"Additional command line options"): <input type="text" name="extra_args" size="60" maxlength="255" value="$(html "$DOMOTICZ_EXTRA_ARGS")"></p>
EOF
sec_end

sec_begin "$(lang de:"Status" en:"Status")"
cat << EOF
<p>$(lang de:"Der Status wird nach dem Speichern und beim Start neu ermittelt." en:"The status is refreshed after saving and when the service is started.")</p>
EOF
sec_end
