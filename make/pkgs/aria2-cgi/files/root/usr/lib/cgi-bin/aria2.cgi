#!/bin/sh

# Source CGI helper library
. /usr/lib/libmodcgi.sh

# ===========================================================================
# AJAX Handler
# ===========================================================================
AJAX_MODE=$(cgi_param ajax)

if [ "$AJAX_MODE" = "1" ]; then
	ACTION=$(cgi_param action)
	BASEDIR=$(cgi_param basedir)

	echo "$(date): AJAX - ACTION=$ACTION BASEDIR=$BASEDIR" >> /tmp/aria2_ajax.log

	cat <<'EOF'
<style>
.ajax-json-box { display: none; }
</style>
<div class="ajax-json-box"><div class="ajax-json-content"><pre>Content-Type: application/json

EOF

	case "$ACTION" in
		check_directory)
			if [ -d "$BASEDIR" ]; then
				echo '{"exists": true, "writable": true}'
			else
				echo '{"exists": false, "writable": false}'
			fi
			;;
		create_directory)
			if mkdir -p "$BASEDIR/downloads" 2>/dev/null; then
				chown bittorrent:users "$BASEDIR" "$BASEDIR/downloads" 2>/dev/null
				chmod 777 "$BASEDIR" "$BASEDIR/downloads" 2>/dev/null
				echo '{"success": true, "message": "Directory created"}'
			else
				echo '{"success": false, "message": "Failed to create directory"}'
			fi
			;;
		check_aria2_conf)
			if [ -f "$BASEDIR/aria2.conf" ]; then
				echo '{"exists": true}'
			else
				echo '{"exists": false}'
			fi
			;;
		check_connection)
			# Try the configured RPC port
			[ -r /mod/etc/conf/aria2.cfg ] && . /mod/etc/conf/aria2.cfg
			PORT="${ARIA2_RPC_PORT:-6800}"
			if pgrep -x aria2c >/dev/null 2>&1; then
				echo "{\"running\": true, \"port\": $PORT}"
			else
				echo "{\"running\": false, \"port\": $PORT}"
			fi
			;;
		get_status)
			IS_RUNNING="false"
			pgrep -x aria2c >/dev/null 2>&1 && IS_RUNNING="true"
			LOG_LINES=""
			if [ -f /tmp/rc.aria2.log ]; then
				LOG_LINES=$(tail -n 20 /tmp/rc.aria2.log | sed 's/\\/\\\\/g; s/"/\\"/g; s/$/\\n/g' | tr -d '\n')
			fi
			echo "{\"running\": $IS_RUNNING, \"log\": \"$LOG_LINES\"}"
			;;
		*)
			echo '{"error": "Unknown action"}'
			;;
	esac

	echo '</pre></div></div>'
	exit 0
fi

# ===========================================================================
# Load configuration
# ===========================================================================
[ -r /etc/options.cfg ] && . /etc/options.cfg
[ -r /mod/etc/conf/aria2.cfg ] && . /mod/etc/conf/aria2.cfg

# ===========================================================================
# Prepare select/check state variables for form widgets
# ===========================================================================
select "$ARIA2_LOGLEVEL" \
	error:logerror warn:logwarn notice:lognotice info:loginfo debug:logdebug "*":lognotice

check "$ARIA2_RPC_ENABLED"   yes:rpcenable
check "$ARIA2_RPC_LISTEN_ALL" yes:rpclistenall
check "$ARIA2_ASYNCDNS"      yes:asyncdns
check "$ARIA2_DHT_ENABLED"   yes:dht_enabled
check "$ARIA2_BT_ENABLED"    yes:bt_enabled
check "$ARIA2_BOOT_MONITOR"  yes:boot_monitor

# ===========================================================================
# HTML page output
# ===========================================================================

# Check running state for conditional sections below
IS_RUNNING="no"
pgrep -x aria2c >/dev/null 2>&1 && IS_RUNNING="yes"

# ===========================================================================
sec_begin "$(lang de:"Starttyp" en:"Start type")"
cgi_print_radiogroup_service_starttype "enabled" "$ARIA2_ENABLED" "" "" 0
sec_end

# ===========================================================================
sec_begin "$(lang de:"Priorität" en:"Priority")"
cat << EOF
<p>
<label for='nice' title="ARIA2_NICE">$(lang de:"Nice-Level" en:"Nice level"): </label>
<input type='text' id='nice' name='nice' size='4' maxlength='4' value="$(html "${ARIA2_NICE:-10}")"
	title="$(lang de:"Prozesspriorität: -20 (höchste) bis 19 (niedrigste). Standardwert: 10." en:"Process priority: -20 (highest) to 19 (lowest). Default: 10.")">
<small>$(lang de:"(-20 bis 19, Standard: 10)" en:"(-20 to 19, default: 10)")</small>
</p>
EOF
sec_end

# ===========================================================================
sec_begin "$(lang de:"Basisverzeichnis" en:"Base Directory")"
cat << EOF
<p>
<label for='basedir' title="ARIA2_BASEDIR">$(lang de:"Basisverzeichnis" en:"Base directory"): </label>
<input type='text' id='basedir' name='basedir' size='50' value="$(html "$ARIA2_BASEDIR")"
	title="$(lang de:"Ordner für Downloads, Sitzungsdatei und aria2.conf (z.B. /var/media/ftp/aria2)." en:"Directory for downloads, session file and aria2.conf (e.g. /var/media/ftp/aria2).")">
</p>
<p>
<small>
$(lang de:"Download-Unterverzeichnis:" en:"Download subdirectory:")
<code>${ARIA2_BASEDIR:-...}/downloads</code>
&nbsp;&nbsp;
$(lang de:"Konfigurationsdatei:" en:"Configuration file:")
<code>${ARIA2_BASEDIR:-...}/aria2.conf</code>
</small>
</p>
<p>
<button type="button" onclick="checkBasedir()"
	style="padding: 4px 12px;">$(lang de:"Verzeichnis prüfen" en:"Check directory")</button>
<button type="button" onclick="createBasedir()"
	style="padding: 4px 12px; margin-left: 8px;">$(lang de:"Verzeichnis erstellen" en:"Create directory")</button>
<span id='basedir_status' style='margin-left:12px; font-size:12px;'></span>
</p>
EOF

if [ -n "$ARIA2_BASEDIR" ] && [ ! -d "$ARIA2_BASEDIR" ]; then
	cat << EOF
<p style="color: #f80; font-size: 12px; margin-top: 5px;">
	&#x26A0;&#xFE0F; $(lang de:"Verzeichnis existiert nicht" en:"Directory does not exist"): <code>$(html "$ARIA2_BASEDIR")</code>
</p>
EOF
fi

# List RW mount points
cat << EOF
<div style="margin-top: 10px; border: 1px solid var(--evo-border, #ddd); background-color: var(--evo-surface, #f9f9f9); padding: 8px; border-radius: 4px;">
<div style="font-weight: bold; margin-bottom: 5px; color: var(--evo-text, #333);">$(lang de:"Verfügbare Speichergeräte (RW)" en:"Available Storage Devices (RW)"):</div>
<div style="max-height: 150px; overflow-y: auto;">
<table style="width: 100%; font-size: 11px; border-collapse: collapse;">
EOF

DFOUT=$(df -hP)
mount | sed -rn '
	\#^/dev/(sd|mapper/)|^https?://|^.* on .* type (cifs|fuse|jffs|ubifs|yaffs|ext)|^.*:/.* on .* type nfs# {
		\# on /wrapper | on /var/flash #! {
			s/^([^ ]+) on (.*) type ([^ ]*) \(([^)]*)\)$/\3 \4 \1 \2/; p
		}
	}
' | while read -r fstyp mountopts device path; do
	case "$mountopts" in
		rw*)
			dfline=$(echo "$DFOUT" | grep " $path$")
			if [ -n "$dfline" ]; then
				avail=$(echo "$dfline" | awk '{print $4}')
				total=$(echo "$dfline" | awk '{print $2}')
				info="$avail / $total"
			else
				info="-"
			fi
			echo "<tr>"
			echo "<td style='padding: 3px 2px; border-bottom: 1px solid #eee;'><code style='cursor: pointer; color: #0056b3; font-weight: bold;' onclick=\"document.getElementById('basedir').value='$path/aria2';\">$path</code></td>"
			echo "<td style='padding: 3px 2px; border-bottom: 1px solid #eee; color: #666;'>$fstyp</td>"
			echo "<td style='padding: 3px 2px; border-bottom: 1px solid #eee; text-align: right;'>$info</td>"
			echo "</tr>"
			;;
	esac
done

# Also list subdirectories under /var/media/ftp (e.g. uStor01) not already listed
if [ -d "/var/media/ftp" ]; then
	for subdir in /var/media/ftp/*/; do
		if [ -d "$subdir" ]; then
			path="${subdir%/}"
			if ! mount | grep -q " on $path type "; then
				dfline=$(echo "$DFOUT" | grep " $path$")
				if [ -n "$dfline" ]; then
					avail=$(echo "$dfline" | awk '{print $4}')
					total=$(echo "$dfline" | awk '{print $2}')
					info="$avail / $total"
					fstyp=$(df -T "$path" 2>/dev/null | tail -1 | awk '{print $2}')
				else
					info="-"
					fstyp="dir"
				fi
				echo "<tr>"
				echo "<td style='padding: 3px 2px; border-bottom: 1px solid #eee;'><code style='cursor: pointer; color: #0056b3; font-weight: bold;' onclick=\"document.getElementById('basedir').value='$path/aria2';\">$path</code></td>"
				echo "<td style='padding: 3px 2px; border-bottom: 1px solid #eee; color: #666;'>$fstyp</td>"
				echo "<td style='padding: 3px 2px; border-bottom: 1px solid #eee; text-align: right;'>$info</td>"
				echo "</tr>"
			fi
		fi
	done
fi

cat << EOF
</table>
</div>
<div style="font-size: 10px; color: #666; margin-top: 5px;">$(lang de:"Klicken um Pfad als Basisverzeichnis zu übernehmen" en:"Click to use path as base directory")</div>
<div style="font-size: 11px; margin-top: 8px; padding: 8px; background: #fff8e1; border-radius: 3px;">
<strong>$(lang de:"Hinweis" en:"Note"):</strong> $(lang de:"Ext4-Dateisystem wird empfohlen für beste Leistung und Zuverlässigkeit." en:"Ext4 filesystem recommended for best performance and reliability.")
</div>
</div>
EOF

cat << EOF
<p>$(lang de:"Wartezeit beim Booten:" en:"Boot wait time:")
<label for='config_wait' title="ARIA2_CONFIG_WAIT">
<input type='text' id='config_wait' name='config_wait' size='4' maxlength='6' value="$(html "${ARIA2_CONFIG_WAIT:-120}")"
	title="$(lang de:"Wartezeit in Sekunden beim Booten, bis das Basisverzeichnis verfügbar ist (0=sofort, >0=warten auf USB/NFS)." en:"Wait time in seconds at boot until the base directory is available (0=immediate, >0=wait for USB/NFS).")">
</label>
$(lang de:"Sekunden" en:"seconds")
<small>$(lang de:"(0=sofort, &gt;0=auf USB/NFS warten)" en:"(0=immediate, &gt;0=wait for USB/NAS)")</small>
</p>
EOF
sec_end

# ===========================================================================
sec_begin "$(lang de:"JSON-RPC-Schnittstelle" en:"JSON-RPC Interface")"
cat << EOF
<p>
<label title="ARIA2_RPC_ENABLED">
<input type='hidden' name='rpc_enabled' value='no'>
<input type='checkbox' id='rpc_enabled' name='rpc_enabled' value='yes'$rpcenable_chk>
$(lang de:"JSON-RPC aktivieren" en:"Enable JSON-RPC")
</label>
<small>$(lang de:"(Für AriaNg und externe Steuerung erforderlich)" en:"(Required for AriaNg and external control)")</small>
</p>
<p>
<label for='rpc_port' title="ARIA2_RPC_PORT">$(lang de:"RPC-Port" en:"RPC port"): </label>
<input type='text' id='rpc_port' name='rpc_port' size='6' maxlength='5' value="$(html "${ARIA2_RPC_PORT:-6800}")"
	title="$(lang de:"Port für den JSON-RPC-Server (Standard: 6800)." en:"Port for the JSON-RPC server (default: 6800).")">
<small>$(lang de:"(Standard: 6800)" en:"(default: 6800)")</small>
</p>
<p>
<label title="ARIA2_RPC_LISTEN_ALL">
<input type='hidden' name='rpc_listen_all' value='no'>
<input type='checkbox' id='rpc_listen_all' name='rpc_listen_all' value='yes'$rpclistenall_chk>
$(lang de:"Auf allen Netzwerkschnittstellen lauschen" en:"Listen on all network interfaces")
</label>
<small>$(lang de:"(deaktivieren = nur 127.0.0.1)" en:"(disabled = localhost only)")</small>
</p>
<p>
<label for='rpc_secret' title="ARIA2_RPC_SECRET">$(lang de:"RPC-Geheimnis (Token)" en:"RPC secret (token)"): </label>
<input type='text' id='rpc_secret' name='rpc_secret' size='30' value="$(html "$ARIA2_RPC_SECRET")"
	title="$(lang de:"Optionaler Sicherheitstoken. Leer lassen, um keine Authentifizierung zu verwenden." en:"Optional security token. Leave empty to disable authentication.")">
<small>$(lang de:"(leer = keine Authentifizierung)" en:"(empty = no authentication)")</small>
</p>
EOF

if [ "$IS_RUNNING" = "yes" ]; then
	RPC_PORT="${ARIA2_RPC_PORT:-6800}"
	cat << EOF
<p>
<strong>$(lang de:"Links" en:"Links"):</strong>
&nbsp;
<a href="http://fritz.box:${RPC_PORT}/jsonrpc" target="_blank" style="color: #007bff;">JSON-RPC</a>
EOF
	if [ -d "/mod/external/usr/mww/ariang" ] || [ -d "/usr/mww/ariang" ]; then
		cat << 'EOF'
&nbsp;|&nbsp;
<a href="/ariang/" target="_blank" style="color: #28a745; font-weight: bold;">AriaNg Web UI</a>
EOF
	fi
	echo "</p>"
fi
sec_end

# ===========================================================================
sec_begin "$(lang de:"Download-Einstellungen" en:"Download Settings")"
cat << EOF
<p>
<label for='max_concurrent' title="ARIA2_MAX_CONCURRENT">$(lang de:"Gleichzeitige Downloads" en:"Concurrent downloads"): </label>
<input type='text' id='max_concurrent' name='max_concurrent' size='4' maxlength='4' value="$(html "${ARIA2_MAX_CONCURRENT:-5}")"
	title="$(lang de:"Maximale Anzahl gleichzeitiger Downloads. Standard: 5." en:"Maximum number of simultaneous downloads. Default: 5.")">
<small>$(lang de:"(Standard: 5)" en:"(default: 5)")</small>
</p>
<p>
<label for='max_conn_server' title="ARIA2_MAX_CONN_SERVER">$(lang de:"Verbindungen pro Server" en:"Connections per server"): </label>
<input type='text' id='max_conn_server' name='max_conn_server' size='4' maxlength='4' value="$(html "${ARIA2_MAX_CONN_SERVER:-16}")"
	title="$(lang de:"Maximale Anzahl von Verbindungen pro Server pro Download. Standard: 16." en:"Maximum number of connections per server per download. Default: 16.")">
<small>$(lang de:"(Standard: 16)" en:"(default: 16)")</small>
</p>
<p>
<label for='split' title="ARIA2_SPLIT">$(lang de:"Splits pro Download" en:"Splits per download"): </label>
<input type='text' id='split' name='split' size='4' maxlength='4' value="$(html "${ARIA2_SPLIT:-5}")"
	title="$(lang de:"Anzahl der parallelen Teile pro Download. Standard: 5." en:"Number of parallel parts per download. Default: 5.")">
<small>$(lang de:"(Standard: 5)" en:"(default: 5)")</small>
</p>
<p>
<label for='min_split_size' title="ARIA2_MIN_SPLIT_SIZE">$(lang de:"Minimale Split-Größe" en:"Minimum split size"): </label>
<input type='text' id='min_split_size' name='min_split_size' size='6' maxlength='8' value="$(html "${ARIA2_MIN_SPLIT_SIZE:-20M}")"
	title="$(lang de:"Minimale Dateigröße für das Aufteilen (z.B. 20M, 1G). Standard: 20M." en:"Minimum size for splitting (e.g. 20M, 1G). Default: 20M.")">
<small>$(lang de:"(z.B. 20M, Standard: 20M)" en:"(e.g. 20M, default: 20M)")</small>
</p>
EOF
sec_end

# ===========================================================================
sec_begin "$(lang de:"Geschwindigkeitsbegrenzung" en:"Speed Limits")"
cat << EOF
<p>
<label for='max_dl_limit' title="ARIA2_MAX_DL_LIMIT">$(lang de:"Download-Limit (KB/s)" en:"Download limit (KB/s)"): </label>
<input type='text' id='max_dl_limit' name='max_dl_limit' size='8' value="$(html "${ARIA2_MAX_DL_LIMIT:-0}")"
	title="$(lang de:"Maximale Gesamt-Download-Rate in KB/s. 0 = unbegrenzt." en:"Maximum overall download rate in KB/s. 0 = unlimited.")">
<small>$(lang de:"(0 = unbegrenzt)" en:"(0 = unlimited)")</small>
</p>
<p>
<label for='max_ul_limit' title="ARIA2_MAX_UL_LIMIT">$(lang de:"Upload-Limit (KB/s)" en:"Upload limit (KB/s)"): </label>
<input type='text' id='max_ul_limit' name='max_ul_limit' size='8' value="$(html "${ARIA2_MAX_UL_LIMIT:-0}")"
	title="$(lang de:"Maximale Gesamt-Upload-Rate in KB/s. 0 = unbegrenzt." en:"Maximum overall upload rate in KB/s. 0 = unlimited.")">
<small>$(lang de:"(0 = unbegrenzt)" en:"(0 = unlimited)")</small>
</p>
EOF
sec_end

# ===========================================================================
sec_begin "$(lang de:"BitTorrent" en:"BitTorrent")"
cat << EOF
<p>
<label title="ARIA2_BT_ENABLED">
<input type='hidden' name='bt_enabled' value='no'>
<input type='checkbox' id='bt_enabled' name='bt_enabled' value='yes'$bt_enabled_chk>
$(lang de:"BitTorrent aktivieren (DHT, LPD)" en:"Enable BitTorrent (DHT, LPD)")
</label>
</p>
<p>
<label for='seed_ratio' title="ARIA2_SEED_RATIO">$(lang de:"Seed-Ratio" en:"Seed ratio"): </label>
<input type='text' id='seed_ratio' name='seed_ratio' size='6' value="$(html "${ARIA2_SEED_RATIO:-1.0}")"
	title="$(lang de:"Seed-Verhältnis bevor gestoppt wird (0.0 = immer seeden, negativ = unbegrenzt). Standard: 1.0." en:"Seed ratio before stopping (0.0 = always seed, negative = unlimited). Default: 1.0.")">
<small>$(lang de:"(0.0=immer, 1.0=Standard)" en:"(0.0=always, 1.0=default)")</small>
</p>
<p>
<label for='seed_time' title="ARIA2_SEED_TIME">$(lang de:"Seed-Zeit (Min.)" en:"Seed time (min)"): </label>
<input type='text' id='seed_time' name='seed_time' size='6' value="$(html "${ARIA2_SEED_TIME:-0}")"
	title="$(lang de:"Seed-Zeit in Minuten nach dem Download (0 = unbegrenzt). Standard: 0." en:"Seed time in minutes after download (0 = unlimited). Default: 0.")">
<small>$(lang de:"(0 = unbegrenzt)" en:"(0 = unlimited)")</small>
</p>
<p>
<label for='bt_max_peers' title="ARIA2_BT_MAX_PEERS">$(lang de:"Max. Peers" en:"Max. peers"): </label>
<input type='text' id='bt_max_peers' name='bt_max_peers' size='5' value="$(html "${ARIA2_BT_MAX_PEERS:-55}")"
	title="$(lang de:"Maximale Anzahl von Peers pro Torrent (0 = unbegrenzt). Standard: 55." en:"Maximum number of peers per torrent (0 = unlimited). Default: 55.")">
<small>$(lang de:"(0 = unbegrenzt, Standard: 55)" en:"(0 = unlimited, default: 55)")</small>
</p>
<p>
<label title="ARIA2_DHT_ENABLED">
<input type='hidden' name='dht_enabled' value='no'>
<input type='checkbox' id='dht_enabled' name='dht_enabled' value='yes'$dht_enabled_chk>
$(lang de:"DHT aktivieren" en:"Enable DHT")
</label>
</p>
<p>
<label for='dht_port' title="ARIA2_DHT_PORT">$(lang de:"DHT-Port" en:"DHT port"): </label>
<input type='text' id='dht_port' name='dht_port' size='6' maxlength='5' value="$(html "${ARIA2_DHT_PORT:-6881}")"
	title="$(lang de:"Port für DHT-Verbindungen. Standard: 6881." en:"Port for DHT connections. Default: 6881.")">
<small>$(lang de:"(Standard: 6881)" en:"(default: 6881)")</small>
</p>
EOF
sec_end

# ===========================================================================
sec_begin "$(lang de:"Logging" en:"Logging")"
cat << EOF
<p>
<label for='loglevel'>$(lang de:"Log-Level" en:"Log level"): </label>
<select name='loglevel' id='loglevel'>
<option value='error'$logerror_sel>error</option>
<option value='warn'$logwarn_sel>warn</option>
<option value='notice'$lognotice_sel>notice</option>
<option value='info'$loginfo_sel>info</option>
<option value='debug'$logdebug_sel>debug</option>
</select>
<small>$(lang de:"(Standard: notice)" en:"(default: notice)")</small>
</p>
<p>
<label title="ARIA2_ASYNCDNS">
<input type='hidden' name='asyncdns' value='no'>
<input type='checkbox' id='asyncdns' name='asyncdns' value='yes'$asyncdns_chk>
$(lang de:"Asynchrone DNS-Auflösung (libcares)" en:"Async DNS resolution (libcares)")
</label>
<small>$(lang de:"(deaktivieren, falls aria2 ohne --with-libcares gebaut wurde)" en:"(disable if aria2 was built without --with-libcares)")</small>
</p>
EOF
sec_end

# ===========================================================================
sec_begin "$(lang de:"Boot-Überwachung" en:"Boot Monitor")"
cat << EOF
<p>
<label title="ARIA2_BOOT_MONITOR">
<input type='hidden' name='boot_monitor' value='no'>
<input type='checkbox' id='boot_monitor' name='boot_monitor' value='yes'$boot_monitor_chk
	title="$(lang de:"Falls aktiviert, überwacht das Init-Skript nach dem Boot-Start für begrenzte Zeit, ob aria2c noch läuft, und startet es bei Bedarf neu." en:"If enabled, the init script monitors after boot start for a limited time whether aria2c is still running and restarts it if needed.")">
$(lang de:"Aktivieren" en:"Enable")
<small>$(lang de:"(Standard: ja)" en:"(default: yes)")</small>
</label>
</p>
<p>
<label for='boot_monitor_interval' title="ARIA2_BOOT_MONITOR_INTERVAL">$(lang de:"Intervall (Sek.)" en:"Interval (sec)"): </label>
<input type='text' id='boot_monitor_interval' name='boot_monitor_interval' size='4' value="$(html "${ARIA2_BOOT_MONITOR_INTERVAL:-10}")"
	title="$(lang de:"Wie oft geprüft wird, ob aria2c läuft (Sekunden)." en:"How often to check whether aria2c is running (seconds).")">
<small>$(lang de:"(Standard: 10)" en:"(default: 10)")</small>
</p>
<p>
<label for='boot_monitor_duration' title="ARIA2_BOOT_MONITOR_DURATION">$(lang de:"Dauer (Sek.)" en:"Duration (sec)"): </label>
<input type='text' id='boot_monitor_duration' name='boot_monitor_duration' size='5' value="$(html "${ARIA2_BOOT_MONITOR_DURATION:-300}")"
	title="$(lang de:"Wie lange nach dem Boot überwacht wird (Sekunden)." en:"How long to monitor after boot (seconds).")">
<small>$(lang de:"(Standard: 300 = 5 Min.)" en:"(default: 300 = 5 min)")</small>
</p>
EOF
sec_end

# ===========================================================================
# AriaNg link if installed
if [ -d "/mod/external/usr/mww/ariang" ] || [ -d "/usr/mww/ariang" ]; then
sec_begin "$(lang de:"AriaNg Web-Interface" en:"AriaNg Web Interface")"
cat << 'EOF'
<p>
<a href="/ariang/" target="_blank" style="color: #28a745; font-weight: bold; font-size: 14px;">
&#x1F310; $(lang de:"AriaNg öffnen" en:"Open AriaNg")
</a>
&nbsp;
<small>$(lang de:"(Modernes Web-UI für aria2 via JSON-RPC)" en:"(Modern web UI for aria2 via JSON-RPC)")</small>
</p>
EOF
sec_end
fi

# ===========================================================================
# Startup log
if [ -f "/tmp/rc.aria2.log" ]; then
sec_begin "$(lang de:"Startup-Protokoll" en:"Startup Log")"
cat << 'EOF'
<div style="background:#f8f9fa;border:1px solid #dee2e6;border-radius:4px;padding:12px;margin-bottom:10px;">
<p style="margin:0 0 8px 0;"><strong>📋 /tmp/rc.aria2.log</strong></p>
<pre style="background:#272822;color:#f8f8f2;padding:12px;border-radius:4px;overflow-x:auto;max-height:300px;overflow-y:auto;margin:0;font-family:'Courier New',monospace;font-size:12px;line-height:1.5;">
EOF
if [ -s "/tmp/rc.aria2.log" ]; then
	tail -n 100 /tmp/rc.aria2.log | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g'
else
	echo "$(lang de:"(Protokolldatei ist leer)" en:"(log file is empty)")"
fi
cat << 'EOF'
</pre>
</div>
EOF
sec_end
fi

# ===========================================================================
# JavaScript helpers for AJAX directory buttons
cat << 'EOF'
<script>
function parseAjaxJson(text) {
	var marker = 'Content-Type: application/json';
	var markerPos = text.indexOf(marker);
	if (markerPos === -1) throw new Error('Invalid response format');
	var firstBrace = text.indexOf('{', markerPos + marker.length);
	if (firstBrace === -1) throw new Error('No JSON in response');
	var braceCount = 0, jsonEnd = -1;
	for (var i = firstBrace; i < text.length; i++) {
		if (text[i] === '{') braceCount++;
		else if (text[i] === '}') {
			braceCount--;
			if (braceCount === 0) { jsonEnd = i + 1; break; }
		}
	}
	if (jsonEnd === -1) throw new Error('Incomplete JSON');
	return JSON.parse(text.substring(firstBrace, jsonEnd));
}

function getBasedir() {
	var el = document.getElementById('basedir');
	return el ? el.value.trim() : '';
}

function setBasedirStatus(msg, color) {
	var el = document.getElementById('basedir_status');
	if (el) { el.textContent = msg; el.style.color = color || ''; }
}

function checkBasedir() {
	var basedir = getBasedir();
	if (!basedir) { setBasedirStatus('Please enter a base directory.', 'red'); return; }
	setBasedirStatus('Checking...', '');
	fetch('/cgi-bin/conf/aria2?ajax=1&action=check_directory&basedir=' + encodeURIComponent(basedir))
		.then(function(r) { return r.text(); })
		.then(function(text) {
			var d = parseAjaxJson(text);
			if (d.exists) {
				setBasedirStatus('\u2713 Directory exists', 'green');
			} else {
				setBasedirStatus('\u2717 Directory does not exist', 'red');
			}
		})
		.catch(function(err) { setBasedirStatus('Error: ' + err.message, 'red'); });
}

function createBasedir() {
	var basedir = getBasedir();
	if (!basedir) { setBasedirStatus('Please enter a base directory.', 'red'); return; }
	setBasedirStatus('Creating...', '');
	fetch('/cgi-bin/conf/aria2?ajax=1&action=create_directory&basedir=' + encodeURIComponent(basedir))
		.then(function(r) { return r.text(); })
		.then(function(text) {
			var d = parseAjaxJson(text);
			if (d.success) {
				setBasedirStatus('\u2713 Directory created', 'green');
			} else {
				setBasedirStatus('\u2717 Failed: ' + (d.message || ''), 'red');
			}
		})
		.catch(function(err) { setBasedirStatus('Error: ' + err.message, 'red'); });
}
</script>
EOF
