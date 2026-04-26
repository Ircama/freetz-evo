#!/bin/sh

. /usr/lib/libmodcgi.sh
[ -r /etc/options.cfg ] && . /etc/options.cfg

case "$QUERY_STRING" in
	start*)
		ACTION_RESULT="started"
		;;
	stop*)
		ACTION_RESULT="stopped"
		;;
esac

select "$TRANSMISSION_LOGLEVEL" info:loginfo debug:logdebug "*":logerror
select "$TRANSMISSION_PEERENCRYPTIONMODE" \
	ENCRYPTION_REQUIRED:requireencryption \
	ENCRYPTION_PREFERRED:preferencryption \
	"*":noencryption
check "$TRANSMISSION_USEBLOCKLIST" yes:useblocklist
check "$TRANSMISSION_USEDHT" yes:usedht
check "$TRANSMISSION_USEUTP" yes:useutp

first_existing_webdir() {
	for candidate in "$@"; do
		if [ -d "$candidate" ] && [ -r "$candidate/index.html" ]; then
			printf '%s\n' "$candidate"
			return 0
		fi
	done
	return 1
}

render_detected_webui() {
	local url="$1"
	local label="$2"

	cat << EOF
<li><a href="${url}" target="_blank">${label}</a></li>
EOF
}


sec_begin "$(lang de:"Starttyp" en:"Start type")"
cgi_print_radiogroup_service_starttype "enabled" "$TRANSMISSION_ENABLED" "" "" 0
sec_end

sec_begin "$(lang de:"Installierte Web-Interfaces" en:"Installed Web Interfaces")"

WEBUI_FOUND="no"
TRANSMISSION_WEB_HOST="${HTTP_HOST%%:*}"
[ -n "$TRANSMISSION_WEB_HOST" ] || TRANSMISSION_WEB_HOST="${SERVER_NAME:-fritz.box}"
TRANSMISSION_RPCPORT_DISPLAY="${TRANSMISSION_RPCPORT:-9091}"
TRANSMISSION_BUILTIN_WEB_URL="http://${TRANSMISSION_WEB_HOST}:${TRANSMISSION_RPCPORT_DISPLAY}/"
TRANSMISSION_WEB_UI_URL="http://${TRANSMISSION_WEB_HOST}:${TRANSMISSION_RPCPORT_DISPLAY}/transmission/web/"
TRANSMISSION_FLOOD_URL="${TRANSMISSION_WEB_UI_URL}transmission-flood/index.html"
TRANSMISSION_TRGUING_URL="${TRANSMISSION_WEB_UI_URL}trguing/index.html"
TRANSMISSION_TRANSMISSIONIC_URL="${TRANSMISSION_WEB_UI_URL}transmissionic/index.html"
TRANSMISSION_WEB_CONTROL_URL="${TRANSMISSION_WEB_UI_URL}transmission-web-control/index.html"

TRANSMISSION_BUILTIN_WEBDIR="$(first_existing_webdir "/mod/external/usr/share/transmission-web-home" "/usr/share/transmission-web-home")"
TRANSMISSION_FLOOD_WEBDIR="$(first_existing_webdir "/usr/mww/transmission-flood" "/mod/external/usr/mww/transmission-flood")"
TRANSMISSION_TRGUING_WEBDIR="$(first_existing_webdir "/usr/mww/trguing" "/mod/external/usr/mww/trguing")"
TRANSMISSION_TRANSMISSIONIC_WEBDIR="$(first_existing_webdir "/usr/mww/transmissionic" "/mod/external/usr/mww/transmissionic")"
TRANSMISSION_WEB_CONTROL_WEBDIR="$(first_existing_webdir "/usr/mww/transmission-web-control" "/mod/external/usr/mww/transmission-web-control")"

cat << EOF
<ul>
EOF


if [ -n "$TRANSMISSION_BUILTIN_WEBDIR" ]; then
	WEBUI_FOUND="yes"
	render_detected_webui "$TRANSMISSION_WEB_UI_URL" "Transmission Web Interface"
fi

if [ -n "$TRANSMISSION_FLOOD_WEBDIR" ]; then
	WEBUI_FOUND="yes"
	render_detected_webui "$TRANSMISSION_FLOOD_URL" "flood-for-transmission"
fi

if [ -n "$TRANSMISSION_TRGUING_WEBDIR" ]; then
	WEBUI_FOUND="yes"
	render_detected_webui "$TRANSMISSION_TRGUING_URL" "TrguiNG web"
fi

if [ -n "$TRANSMISSION_TRANSMISSIONIC_WEBDIR" ]; then
	WEBUI_FOUND="yes"
	render_detected_webui "$TRANSMISSION_TRANSMISSIONIC_URL" "Transmissionic web UI"
fi

if [ -n "$TRANSMISSION_WEB_CONTROL_WEBDIR" ]; then
	WEBUI_FOUND="yes"
	render_detected_webui "$TRANSMISSION_WEB_CONTROL_URL" "transmission-web-control"
fi

if [ "$WEBUI_FOUND" = "no" ]; then
	cat << EOF
<li><em>$(lang de:"Kein Transmission-Web-Interface installiert" en:"No transmission web interface installed")</em></li>
EOF
fi

cat << EOF
</ul>
EOF

sec_end

sec_begin "$(lang de:"Priorit&auml;t" en:"Priority")"

cat << EOF
<p>
<label for='nice'>Nice-Level: </label>
<input type='text' id='nice' name='nice' size='3' maxlength='3' value="$(html "$TRANSMISSION_NICE")">
</p>

EOF

sec_end

sec_begin "$(lang de:"Logging" en:"Logging")"

cat << EOF
<p>
<label for='loglevel'>Log-Level: </label>
<select name='loglevel' id='loglevel'>
<option value='error'$logerror_sel>ERROR</option>
<option value='info'$loginfo_sel>INFO</option>
<option value='debug'$logdebug_sel>DEBUG</option>
</select>
</p>

EOF

sec_end

sec_begin "$(lang de:"Arbeitsverzeichnisse" en:"Working Directories")"

cat << EOF
<p>
<label for='basedir'>$(lang de:"Basisverzeichnis" en:"Base-Directory"): </label>
<input type='text' id='basedir' name='basedir' size='50' maxlength='255' value="$(html "$TRANSMISSION_BASEDIR")">
</p>

<p>
<label for='configdir'>$(lang de:"Konfigurationsverzeichnis" en:"Configuration-Directory"): </label>
<input type='text' id='configdir' name='configdir' size='40' maxlength='255' value="$(html "$TRANSMISSION_CONFIGDIR")">
</p>

<p>
<label for='downloaddir'>$(lang de:"Download-Verzeichnis" en:"Download-Directory"): </label>
<input type='text' id='downloaddir' name='downloaddir' size='40' maxlength='255' value="$(html "$TRANSMISSION_DOWNLOADDIR")"><br />
</p>

<p>
<small>$(lang
de:"Alle folgenden Verzeichnisse sind optional"
en:"Following directories can be empty"
)</small>
</p>

<p>
<small>$(lang
de:"Starte Torrents in diesem Verzeichnis automatisch:"
en:"Directory to watch for new torrents and to automatically start them:"
)</small>
</p>

<p>
<label for='watchdir'>$(lang de:"Autostart-Verzeichnis" en:"Watch-Directory"): </label>
<input type='text' id='watchdir' name='watchdir' size='40' maxlength='255' value="$(html "$TRANSMISSION_WATCHDIR")">
</p>

<p>
<small>$(lang
de:"Noch nicht fertig geladene Dateien werden in diesem Verzeichnis abgelegt:"
en:"Directory to store new torrents until they're complete:"
)</small>
</p>

<p>
<label for='incompletedir'>$(lang de:"Incomplete-Verzeichnis" en:"Incomplete-Directory"): </label>
<input type='text' id='incompletedir' name='incompletedir' size='40' maxlength='255' value="$(html "$TRANSMISSION_INCOMPLETEDIR")"><br />
</p>
EOF

if [ "$FREETZ_PACKAGE_TRANSMISSION_WITH_FINISHDIR" == "y" ]; then
cat << EOF
<p>
<small>$(lang
de:"Verschiebe komplett fertige Dateien (gedownloaded und geseedet) in folgendes Verzeichnis:"
en:"Completely seeded downloads will be moved to the following directory:"
)</small>
</p>

<p>
<label for='finishdir'>$(lang de:"End-Verzeichnis" en:"Finish-Directory"): </label>
<input type='text' id='finishdir' name='finishdir' size='40' maxlength='255' value="$(html "$TRANSMISSION_FINISHDIR")"><br />
</p>
EOF
fi

cat << EOF
<p>
<small>$(lang
de:"Au&szlig;er beim Basisverzeichnis d&uuml;rfen auch relative Pfade angegeben werden. Die relativen Pfade werden dabei als relativ zum Basisverzeichnis verstanden."
en:"Both absolute and relative paths are allowed for directories except for the base-directory. The relative ones will be interpreted as being relative to the base-directory."
)</small>
</p>
EOF

sec_end


sec_begin "$(lang de:"Peer-Einstellungen" en:"Peer-Settings")"

cat << EOF
<small>$(lang
de:"Dieser Port muss selbst freigegeben werden."
en:"Don't forget to open this port."
)</small>
<p>
<label for='peerport'>Peer-Port: </label>
<input type='text' id='peerport' name='peerport' value="$(html "$TRANSMISSION_PEERPORT")">
</p>
EOF

if [ "$FREETZ_PACKAGE_TRANSMISSION_WITH_FINISHDIR" == "y" ]; then
cat << EOF
<small>$(lang
de:"Beim Erreichen der Ratio werden Uploads automatisch gestoppt und in das End-Verzeichnis verschoben (falls angegeben)"
en:"Seeding torrents will be stopped when they reach this ratio and moved to the finish-directory (if not empty)"
)</small>
EOF
fi

cat << EOF
<p>
<label for='ratio'>$(lang de:"Ratio:" en:"Ratio:") </label>
<input type='text' id='ratio' name='ratio' value="$(html "$TRANSMISSION_RATIO")">
</p>

<p>
<label for='globalpeerlimit'>$(lang de:"Maximale Gesamtanzahl an Peers:" en:"Maximum overall number of peers:") </label>
<input type='text' id='globalpeerlimit' name='globalpeerlimit' value="$(html "$TRANSMISSION_GLOBALPEERLIMIT")">
</p>

<p>
<label for='torrentpeerlimit'>$(lang de:"Maximale Anzahl an Peers pro Torrent:" en:"Maximum number of peers per torrent:") </label>
<input type='text' id='torrentpeerlimit' name='torrentpeerlimit' value="$(html "$TRANSMISSION_TORRENTPEERLIMIT")">
</p>

<p>
<label for='peerencryptionmode'>$(lang de:"Verschl&uuml;sselungsmodus:" en:"Encryption mode:")</label>
<select name='peerencryptionmode' id='peerencryptionmode'>
<option value='NO_ENCRYPTION'$noencryption_sel>$(lang de:"Keine Verschl&uuml;sselung" en:"No encryption")</option>
<option value='ENCRYPTION_PREFERRED'$preferencryption_sel>$(lang de:"Verschl&uuml;sselte Peer-Verbindungen bevorzugen" en:"Prefer encrypted peer connections")</option>
<option value='ENCRYPTION_REQUIRED'$requireencryption_sel>$(lang de:"Alle Peer-Verbindungen verschl&uuml;sseln" en:"Encrypt all peer connections")</option>
</select>
</p>

<p>
<label for='useblocklist'>$(lang de:"Peer-Blockliste verwenden:" en:"Use peer-blocklist:") </label>
<input type="hidden" name="useblocklist" value="no">
<input type='checkbox' id='useblocklist' name='useblocklist' value='yes'$useblocklist_chk>
</p>

<p>
<label for='usedht'>$(lang de:"DHT verwenden:" en:"Use DHT:") </label>
<input type="hidden" name="usedht" value="no">
<input type='checkbox' id='usedht' name='usedht' value='yes'$usedht_chk>
</p>

<p>
<label for='useutp'>$(lang de:"&mu;TP verwenden:" en:"Use &mu;TP:") </label>
<input type="hidden" name="useutp" value="no">
<input type='checkbox' id='useutp' name='useutp' value='yes'$useutp_chk>
</p>
EOF

sec_end


sec_begin "$(lang de:"RPC- und Webinterface-Einstellungen" en:"RPC and Web Interface Settings")"

cat << EOF
<small>$(lang
de:"Ist kein Passwortschutz gew&uuml;nscht, so sollen Benutzername und Kennwort leer gelassen werden."
en:"Leave user name and password empty if no password protection required."
)</small>
<p>
<label for='rpcport'>$(lang de:"RPC- und Webinterface-Port" en:"RPC- and Web-Interface-Port"): </label>
<input type='text' id='rpcport' name='rpcport' value="$(html "$TRANSMISSION_RPCPORT")">
</p>

<p>
<label for='rpcusername'>$(lang de:"Benutzername" en:"User Name"): </label>
<input type='text' id='rpcusername' name='rpcusername' value="$(html "$TRANSMISSION_RPCUSERNAME")">
</p>

<p>
<label for='rpcpassword'>$(lang de:"Kennwort" en:"Password"): </label>
<input type='password' id='rpcpassword' name='rpcpassword' value="$(html "$TRANSMISSION_RPCPASSWORD")">
<p>

<p>
<label for='rpcwhitelist'>$(lang de:"Erlaubte IP-Adressen" en:"Allowed IP-Addresses"): </label>
<input type='text' id='rpcwhitelist' name='rpcwhitelist' size='40' maxlength='255' value="$(html "$TRANSMISSION_RPCWHITELIST")">
</p>

<p>
<input type='hidden' id='webdir' name='webdir' value="$(html "${TRANSMISSION_BUILTIN_WEBDIR:-/mod/external/usr/share/transmission-web-home}")">
EOF

sec_end

if [ -n "$ACTION_RESULT" ]; then
	cat << EOF
<script>
(function() {
	var cleanUrl = window.location.pathname;
	window.location.replace(cleanUrl);
})();
</script>
EOF
fi
