#!/bin/sh

. /usr/lib/libmodcgi.sh

sec_begin "$(lang de:"Starttyp" en:"Start type")"
cgi_print_radiogroup_service_starttype "enabled" "$FREETZ_MATTER_ENABLED" "" "" 0
sec_end

sec_begin "$(lang de:"Matter-Geraet" en:"Matter device")"
cat << EOF
<p>$(lang de:"Die FritzBox wird selbst als Matter-Geraet bereitgestellt. Jeder Matter-Controller kann sie in Betrieb nehmen." en:"The FRITZ!Box itself is exposed as a Matter device. Any Matter controller can commission it.")</p>
<p>$(lang de:"Matter-Port (UDP)" en:"Matter port (UDP)"): <input type="text" name="port" size="8" maxlength="5" value="$(html "$FREETZ_MATTER_PORT")"></p>
<p>$(lang de:"Fabric-Speicher" en:"Fabric store"): <input type="text" id="store" name="store" size="40" maxlength="255" value="$(html "$FREETZ_MATTER_STORE")"></p>
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

# Die Fabric muss einen Neustart ueberleben. /tmp/flash ist ein RAM-Disk: sie
# landet nur dann im Box-Flash, wenn modsave laeuft (beim Stoppen des Dienstes
# und bei jedem Speichern ueber die Weboberflaeche). Deshalb werden hier die
# beschreibbaren Datentraeger angeboten, ein Klick uebernimmt den Pfad.
sec_begin "$(lang de:"Speicherort" en:"Store location")"
cat << EOF
<table style="width:100%; font-size:11px; border-collapse:collapse;">
<tr><th style="text-align:left;">$(lang de:"Geraet" en:"Device")</th><th style="text-align:left;">$(lang de:"Typ" en:"Type")</th><th style="text-align:right;">$(lang de:"Frei / Gesamt" en:"Free / total")</th></tr>
EOF

storage_row() {
	echo "<tr><td style='padding:2px 4px;'><code style='cursor:pointer;color:#0056b3;font-weight:bold;' onclick=\"document.getElementById('store').value='$1/freetz-matter';\">$1</code></td><td style='padding:2px 4px;color:#666;'>$2</td><td style='padding:2px 4px;text-align:right;'>$3</td></tr>"
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
<p style="font-size:10px;color:#666;">$(lang de:"Klick auf einen Pfad uebernimmt ihn als Speicher. Beim Speichern wird der bisherige Inhalt (Fabric) automatisch mitgenommen, danach den Dienst neu starten." en:"Clicking a path uses it as store. On save the previous content (fabric) is moved along, then restart the service.")</p>
EOF

case "$FREETZ_MATTER_STORE" in
	/tmp/flash/*)
		cat << EOF
<p style="font-size:10px;color:#a60;">$(lang de:"Hinweis: /tmp/flash ist ein RAM-Disk. Sie wird beim Stoppen des Dienstes und bei jedem Speichern ueber modsave in den Box-Flash geschrieben; bei einem Stromausfall geht die Fabric verloren und das Geraet muss neu in Betrieb genommen werden - eine Platte ist sicherer." en:"Note: /tmp/flash is a ramdisk. It is written to the box flash by modsave when the service stops and on every save; a power cut loses the fabric and the device has to be commissioned again - a disk is safer.")</p>
EOF
		;;
esac
sec_end

sec_begin "$(lang de:"Erweitert" en:"Advanced")"
cgi_print_radiogroup_active "verbose" "$FREETZ_MATTER_VERBOSE" "" "$(lang de:"Debug-Protokoll" en:"Debug logging")"
cat << EOF
<p>$(lang de:"Warten auf das Programm im externen Speicher (Sekunden, 0 = sofort)" en:"Wait for the binary on external storage (seconds, 0 = immediately)"): <input type="text" name="config_wait" size="8" maxlength="5" value="$(html "$FREETZ_MATTER_CONFIG_WAIT")"></p>
<p>$(lang de:"Zusaetzliche Kommandozeilenoptionen" en:"Additional command line options"): <input type="text" name="extra_args" size="60" maxlength="255" value="$(html "$FREETZ_MATTER_EXTRA_ARGS")"></p>
EOF
sec_end
