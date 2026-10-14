#!/bin/sh

. /usr/lib/libmodcgi.sh

sec_begin "$(lang de:"Starttyp" en:"Start type")"
cgi_print_radiogroup_service_starttype "enabled" "$MATTER_BRIDGE_ENABLED" "" "" 0
sec_end

sec_begin "$(lang de:"WebSocket-API (python-matter-server)" en:"WebSocket API (python-matter-server)")"
cat << EOF
<p>$(lang de:"Domoticz-Hardware 'Matter' verbindet sich mit dieser Adresse" en:"The Domoticz 'Matter' hardware connects to this address"): <code>ws://$MATTER_BRIDGE_BIND:$MATTER_BRIDGE_PORT/ws</code></p>
<p>$(lang de:"Port" en:"Port"): <input type="text" name="port" size="8" maxlength="5" value="$(html "$MATTER_BRIDGE_PORT")"></p>
<p>$(lang de:"Bind-Adresse (127.0.0.1 = nur lokal)" en:"Bind address (127.0.0.1 = local only)"): <input type="text" name="bind" size="20" maxlength="64" value="$(html "$MATTER_BRIDGE_BIND")"></p>
EOF
sec_end

sec_begin "$(lang de:"Matter-Controller" en:"Matter controller")"
cat << EOF
<p>$(lang de:"Adresse des Matter-Geraets (IPv6, Port 5540)" en:"Address of the Matter device (IPv6, port 5540)"): <input type="text" name="peer" size="30" maxlength="64" value="$(html "$MATTER_BRIDGE_PEER")"></p>
<p>$(lang de:"Fabric- und Node-Speicher" en:"Fabric and node store"): <input type="text" name="store" size="40" maxlength="255" value="$(html "$MATTER_BRIDGE_STORE")"></p>
EOF
cgi_print_radiogroup_active "auto_local" "$MATTER_BRIDGE_AUTO_LOCAL" "" "$(lang de:"Automatische Inbetriebnahme des lokalen Geraets" en:"Automatic commissioning of the local device")"
sec_end

sec_begin "$(lang de:"Erweitert" en:"Advanced")"
cgi_print_radiogroup_active "verbose" "$MATTER_BRIDGE_VERBOSE" "" "$(lang de:"Debug-Protokoll (RUST_LOG=debug)" en:"Debug logging (RUST_LOG=debug)")"
cat << EOF
<p>$(lang de:"Warten auf das Programm im externen Speicher (Sekunden, 0 = sofort)" en:"Wait for the binary on external storage (seconds, 0 = immediately)"): <input type="text" name="config_wait" size="8" maxlength="5" value="$(html "$MATTER_BRIDGE_CONFIG_WAIT")"></p>
<p>$(lang de:"Zusaetzliche Kommandozeilenoptionen" en:"Additional command line options"): <input type="text" name="extra_args" size="60" maxlength="255" value="$(html "$MATTER_BRIDGE_EXTRA_ARGS")"></p>
EOF
sec_end
