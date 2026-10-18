#!/bin/sh

. /usr/lib/libmodcgi.sh

sec_begin "$(lang de:"Starttyp" en:"Start type")"
cgi_print_radiogroup_service_starttype "enabled" "$INFLUXDB3_ENABLED" "" "" 0
sec_end

sec_begin "$(lang de:"Datenbank und HTTP" en:"Database and HTTP")"
cgi_print_textline_p "node_id" "$INFLUXDB3_NODE_ID" 32/64 "$(lang de:"Knoten-ID" en:"Node ID"): "
cgi_print_textline_p "data_dir" "$INFLUXDB3_DATA_DIR" 60/1024 "$(lang de:"Datenverzeichnis (muss existieren)" en:"Data directory (must already exist)"): "
cgi_print_textline_p "bind" "$INFLUXDB3_BIND" 40/45 "$(lang de:"IP-Adresse (IPv6 ohne Klammern)" en:"IP address (IPv6 without brackets)"): "
cgi_print_textline_p "port" "$INFLUXDB3_PORT" 6/5 "$(lang de:"HTTP-Port" en:"HTTP port"): "
cgi_print_checkbox "without_auth" "$INFLUXDB3_WITHOUT_AUTH" "$(lang de:"Authentifizierung deaktivieren (nur vertrauensw&uuml;rdige Netze)" en:"Disable authentication (trusted networks only)")"
sec_end

sec_begin "$(lang de:"Start und Speicherung" en:"Startup and storage")"
cgi_print_textline_p "config_wait" "$INFLUXDB3_CONFIG_WAIT" 5/3 "$(lang de:"Wartezeit beim Booten (Sekunden, 0 = synchron)" en:"Boot resource wait (seconds, 0 = synchronous)"): "
cgi_print_textline_p "startup_wait" "$INFLUXDB3_STARTUP_WAIT" 5/3 "$(lang de:"HTTP-Startzeitlimit (Sekunden)" en:"HTTP startup timeout (seconds)"): "
cat << EOF
<p>$(lang de:"Lokalen externen Speicher mit geeignetem Dateisystem (z.B. ext4) verwenden. Daten werden nicht durch modsave gesichert. Speichern startet den Dienst nicht neu." en:"Use local external storage with a suitable filesystem (e.g. ext4). Database files are not backed up by modsave. Saving does not restart the service.")</p>
<p>$(lang de:"Standard: nur Loopback, mit Authentifizierung. Ohne Authentifizierung kann jeder erreichbare Client die Datenbank verwenden." en:"Default: loopback only, authentication enabled. With authentication disabled, every client that can reach the listener can access the database.")</p>
EOF
sec_end
