#!/bin/sh

. /usr/lib/libmodcgi.sh

sec_begin "$(lang de:"Starttyp" en:"Start type")"
cgi_print_radiogroup_service_starttype "enabled" "$FREETZ_MATTER_ENABLED" "" "" 0
sec_end

sec_begin "$(lang de:"Matter-Geraet" en:"Matter device")"
cat << EOF
<p>$(lang de:"Die FritzBox wird selbst als Matter-Geraet bereitgestellt. Jeder Matter-Controller kann sie in Betrieb nehmen." en:"The FRITZ!Box itself is exposed as a Matter device. Any Matter controller can commission it.")</p>
<p>$(lang de:"Matter-Port (UDP)" en:"Matter port (UDP)"): <input type="text" name="port" size="8" maxlength="5" value="$(html "$FREETZ_MATTER_PORT")"></p>
<p>$(lang de:"Fabric-Speicher" en:"Fabric store"): <input type="text" name="store" size="40" maxlength="255" value="$(html "$FREETZ_MATTER_STORE")"></p>
<p>$(lang de:"Der Speicher wird bei jedem Speichern und beim Start automatisch angelegt." en:"The store is created automatically on every save and on start.")</p>
EOF
sec_end

sec_begin "$(lang de:"Geraete-Endpunkte" en:"Device endpoints")"
cat << EOF
<p>$(lang de:"Temperatursensor" en:"Temperature sensor"): <code>1/1026/0</code></p>
<p>$(lang de:"Lautsprecher (Ein/Aus, Lautstaerke)" en:"Speaker (on/off, volume)"): <code>2/6/0</code>, <code>2/8/0</code></p>
<p>$(lang de:"Grundinformationen (Modell, Firmware, Seriennummer)" en:"Basic information (model, firmware, serial)"): <code>0/40/*</code></p>
EOF
sec_end

sec_begin "$(lang de:"Erweitert" en:"Advanced")"
cgi_print_radiogroup_active "verbose" "$FREETZ_MATTER_VERBOSE" "" "$(lang de:"Debug-Protokoll" en:"Debug logging")"
cat << EOF
<p>$(lang de:"Warten auf das Programm im externen Speicher (Sekunden, 0 = sofort)" en:"Wait for the binary on external storage (seconds, 0 = immediately)"): <input type="text" name="config_wait" size="8" maxlength="5" value="$(html "$FREETZ_MATTER_CONFIG_WAIT")"></p>
<p>$(lang de:"Zusaetzliche Kommandozeilenoptionen" en:"Additional command line options"): <input type="text" name="extra_args" size="60" maxlength="255" value="$(html "$FREETZ_MATTER_EXTRA_ARGS")"></p>
EOF
sec_end
