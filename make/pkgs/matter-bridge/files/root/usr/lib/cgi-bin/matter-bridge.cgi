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
<p>$(lang de:"Fabric- und Node-Speicher" en:"Fabric and node store"): <input type="text" id="store" name="store" size="40" maxlength="255" value="$(html "$MATTER_BRIDGE_STORE")"></p>
EOF
cgi_print_radiogroup_active "auto_local" "$MATTER_BRIDGE_AUTO_LOCAL" "" "$(lang de:"Automatische Inbetriebnahme des lokalen Geraets" en:"Automatic commissioning of the local device")"
sec_end

# Fabric und Noden muessen einen Neustart ueberleben. /tmp/flash ist ein
# RAM-Disk: sie landet nur dann im Box-Flash, wenn modsave laeuft (beim Stoppen
# des Dienstes und bei jedem Speichern ueber die Weboberflaeche). Deshalb werden
# hier die beschreibbaren Datentraeger angeboten, ein Klick uebernimmt den Pfad.
sec_begin "$(lang de:"Speicherort" en:"Store location")"
cat << EOF
<table style="width:100%; font-size:11px; border-collapse:collapse;">
<tr><th style="text-align:left;">$(lang de:"Geraet" en:"Device")</th><th style="text-align:left;">$(lang de:"Typ" en:"Type")</th><th style="text-align:right;">$(lang de:"Frei / Gesamt" en:"Free / total")</th></tr>
EOF

storage_row() {
	echo "<tr><td style='padding:2px 4px;'><code style='cursor:pointer;color:#0056b3;font-weight:bold;' onclick=\"document.getElementById('store').value='$1/matter-bridge';\">$1</code></td><td style='padding:2px 4px;color:#666;'>$2</td><td style='padding:2px 4px;text-align:right;'>$3</td></tr>"
}

DFOUT=$(df -hP 2>/dev/null)
mount | sed -rn '
	\#^/dev/(sd|mapper/)|^https?://|^.* on .* type (cifs|fuse|jffs|ubifs|yaffs|ext)|^.*:/.* on .* type nfs# {
		\# on /wrapper | on /var/flash #! {
			s/^([^ ]+) on (.*) type ([^ ]*) \(([^)]*)\)$/\3 \4 \1 \2/; p
		}
	}
' | while read -r fstyp mountopts device path; do
	case "$mountopts" in
		rw*)
			dfline=$(echo "$DFOUT" | grep " $path$" | head -1)
			if [ -n "$dfline" ]; then
				storage_row "$path" "$fstyp" "$(echo "$dfline" | awk '{print $4" / "$2}')"
			else
				storage_row "$path" "$fstyp" "-"
			fi
			;;
	esac
done

# Datentraeger unterhalb von /var/media/ftp, die selbst kein Mountpoint sind
if [ -d /var/media/ftp ]; then
	for subdir in /var/media/ftp/*/; do
		path="${subdir%/}"
		[ -d "$path" ] || continue
		mount | grep -q " on $path type " && continue
		dfline=$(echo "$DFOUT" | grep " $path$" | head -1)
		if [ -n "$dfline" ]; then
			storage_row "$path" "$(df -T "$path" 2>/dev/null | tail -1 | awk '{print $2}')" "$(echo "$dfline" | awk '{print $4" / "$2}')"
		else
			storage_row "$path" "$(lang de:"Verzeichnis" en:"directory")" "-"
		fi
	done
fi

cat << EOF
</table>
<p style="font-size:10px;color:#666;">$(lang de:"Klick auf einen Pfad uebernimmt ihn als Speicher. Beim Speichern wird der bisherige Inhalt (Fabric, Noden) automatisch mitgenommen, danach den Dienst neu starten." en:"Clicking a path uses it as store. On save the previous content (fabric, nodes) is moved along, then restart the service.")</p>
EOF

case "$MATTER_BRIDGE_STORE" in
	/tmp/flash/*)
		cat << EOF
<p style="font-size:10px;color:#a60;">$(lang de:"Hinweis: /tmp/flash ist ein RAM-Disk. Sie wird beim Stoppen des Dienstes und bei jedem Speichern ueber modsave in den Box-Flash geschrieben; bei einem Stromausfall geht die Fabric verloren - eine Platte ist sicherer." en:"Note: /tmp/flash is a ramdisk. It is written to the box flash by modsave when the service stops and on every save; a power cut loses the fabric - a disk is safer.")</p>
EOF
		;;
esac
sec_end

sec_begin "$(lang de:"Erweitert" en:"Advanced")"
cgi_print_radiogroup_active "verbose" "$MATTER_BRIDGE_VERBOSE" "" "$(lang de:"Debug-Protokoll (RUST_LOG=debug)" en:"Debug logging (RUST_LOG=debug)")"
cat << EOF
<p>$(lang de:"Warten auf das Programm im externen Speicher (Sekunden, 0 = sofort)" en:"Wait for the binary on external storage (seconds, 0 = immediately)"): <input type="text" name="config_wait" size="8" maxlength="5" value="$(html "$MATTER_BRIDGE_CONFIG_WAIT")"></p>
<p>$(lang de:"Zusaetzliche Kommandozeilenoptionen" en:"Additional command line options"): <input type="text" name="extra_args" size="60" maxlength="255" value="$(html "$MATTER_BRIDGE_EXTRA_ARGS")"></p>
EOF
sec_end
