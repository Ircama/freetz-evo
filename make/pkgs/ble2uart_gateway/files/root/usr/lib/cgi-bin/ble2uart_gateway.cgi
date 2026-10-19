#!/bin/sh

. /usr/lib/libmodcgi.sh

DAEMON_BIN=/usr/bin/ble2uart-gateway
[ -x "$DAEMON_BIN" ] || DAEMON_BIN=/mod/external/usr/bin/ble2uart-gateway
[ -r /mod/etc/default.ble2uart_gateway/ble2uart_gateway.cfg ] && . /mod/etc/default.ble2uart_gateway/ble2uart_gateway.cfg
[ -r /mod/etc/conf/ble2uart_gateway.cfg ] && . /mod/etc/conf/ble2uart_gateway.cfg
: "${BLE2UART_GATEWAY_STORE:=/tmp/flash/ble2uart_gateway}"
YAML="$BLE2UART_GATEWAY_STORE/ble2uart_gateway.yaml"

# ---------------------------------------------------------------------------
# AJAX actions: the configuration file is a structured YAML document owned by
# the daemon. The shell never parses or rewrites YAML: it reads and writes the
# file and lets `ble2uart-gateway --check-config` answer whether the content is valid
# (the daemon is the only implementation of the schema).
#
# The response is HTML-wrapped JSON, the format the freetz web interface parses.
# ---------------------------------------------------------------------------
if [ "$(cgi_param ajax)" = "1" ]; then
	ACTION=$(cgi_param action)

	cat << EOF
Content-Type: text/html; charset=UTF-8

<div class="ajax-json-box" style="display:none"><div class="ajax-json-content"><pre>Content-Type: application/json

EOF

	api_reply() {
		if [ "$REQUEST_METHOD" != POST ] && [ "$ACTION" != read ] && [ "$ACTION" != status ]; then
			echo '{"success":false,"error":"POST is required"}'
			return
		fi
		case "${HTTP_SEC_FETCH_SITE:-same-origin}" in
			cross-site) echo '{"success":false,"error":"cross-site request denied"}'; return ;;
		esac
		if [ -n "$HTTP_ORIGIN" ] && [ "$HTTP_ORIGIN" != "http://$HTTP_HOST" ] && [ "$HTTP_ORIGIN" != "https://$HTTP_HOST" ]; then
			echo '{"success":false,"error":"origin mismatch"}'
			return
		fi
		case "$ACTION" in
			read|backups) "$DAEMON_BIN" --config "$YAML" --web-config "$ACTION" ;;
			check|save|restore|inspect)
				case "$CONTENT_LENGTH" in ''|*[!0-9]*) echo '{"success":false,"error":"invalid request length"}'; return ;; esac
				if [ "$CONTENT_LENGTH" -gt 262144 ] || [ "$CONTENT_TYPE" != application/json ]; then
					echo '{"success":false,"error":"expected JSON, at most 256 KiB"}'
				else
					"$DAEMON_BIN" --config "$YAML" --web-config "$ACTION"
				fi
				;;
			status|discover-stop) "$DAEMON_BIN" --control "$ACTION" ;;
			command)
				case "$CONTENT_LENGTH" in ''|*[!0-9]*) echo '{"success":false,"error":"invalid request length"}'; return ;; esac
				if [ "$CONTENT_LENGTH" -gt 4096 ] || [ "$CONTENT_TYPE" != application/json ]; then
					echo '{"success":false,"error":"expected command JSON, at most 4096 bytes"}'
				else
					"$DAEMON_BIN" --command -
				fi
				;;
			discover-start)
				SECONDS=$(cgi_param seconds)
				case "$SECONDS" in ''|*[!0-9]*) echo '{"success":false,"error":"invalid duration"}' ;; *) "$DAEMON_BIN" --control discover-start "$SECONDS" ;; esac
				;;
			restart)
				SERVICE=/etc/init.d/rc.ble2uart_gateway
				[ -x "$SERVICE" ] || SERVICE=/mod/external/etc/init.d/rc.ble2uart_gateway
				if "$SERVICE" restart >>/tmp/rc.ble2uart_gateway.log 2>&1; then
					echo '{"success":true,"message":"service restarted"}'
				else
					echo '{"success":false,"error":"service restart failed; see service log"}'
				fi
				;;
			reload-logging)
				PID=$(cat /var/run/ble2uart_gateway.pid 2>/dev/null)
				case "$PID" in ''|*[!0-9]*) echo '{"success":false,"error":"gateway is not running"}' ;; *)
					if kill -HUP "$PID" 2>/dev/null; then echo '{"success":true,"message":"logging reload requested"}'; else echo '{"success":false,"error":"gateway is not running"}'; fi ;;
				esac
				;;
			*) echo '{"success":false,"error":"unknown action"}' ;;
		esac
	}
	api_reply | sed -e 's/\&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g'

	echo '</pre></div></div>'
	exit 0
fi

# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
echo '<details><summary>'"$(lang de:"Start und Speicher" en:"Startup and storage")"'</summary>'
sec_begin "$(lang de:"Starttyp" en:"Start type")"
cgi_print_radiogroup_service_starttype "enabled" "$BLE2UART_GATEWAY_ENABLED" "" "" 0
sec_end

sec_begin "$(lang de:"Serielle Schnittstelle" en:"Serial link")"
cat << EOF
<p>$(lang de:"Serielles Gerät bei Erstinstallation" en:"Initial serial device"): <input type="text" name="serial" size="24" maxlength="64" value="$(html "$BLE2UART_GATEWAY_SERIAL")"></p>
<p>$(lang de:"Baudrate bei Erstinstallation" en:"Initial baud rate"): <input type="text" name="baudrate" size="8" maxlength="8" value="$(html "$BLE2UART_GATEWAY_BAUDRATE")"></p>
<p>$(lang de:"Warten auf Programm/Gerät (Sekunden, 0 = sofort)" en:"Wait for the binary/device (seconds, 0 = immediately)"): <input type="text" name="config_wait" size="6" maxlength="5" value="$(html "$BLE2UART_GATEWAY_CONFIG_WAIT")"></p>
EOF
sec_end

# Storage chooser: same pattern as the other freetz packages; the bind keys are
# secrets, so the store should live on a disk and never in a world readable
# place.
sec_begin "$(lang de:"Speicherort" en:"Store location")"
cat << EOF
<p>$(lang de:"Verzeichnis der Konfiguration (Geräte, Bindkeys, Regeln)" en:"Configuration directory (devices, bind keys, rules)"): <input type="text" id="store" name="store" size="40" maxlength="255" value="$(html "$BLE2UART_GATEWAY_STORE")"></p>
<table style="width:100%; font-size:11px; border-collapse:collapse;">
<tr><th style="text-align:left;">$(lang de:"Gerät" en:"Device")</th><th style="text-align:left;">$(lang de:"Typ" en:"Type")</th><th style="text-align:right;">$(lang de:"Frei / Gesamt" en:"Free / total")</th></tr>
EOF
storage_row() {
	echo "<tr><td style='padding:2px 4px;'><code style='cursor:pointer;color:#0056b3;font-weight:bold;' onclick=\"document.getElementById('store').value='$1/ble2uart_gateway';\">$1</code></td><td style='padding:2px 4px;color:#666;'>$2</td><td style='padding:2px 4px;text-align:right;'>$3</td></tr>"
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
<p style="font-size:10px;color:#666;">$(lang de:"Klick übernimmt den Pfad. Der bisherige Speicher wird beim Speichern mitgenommen." en:"Clicking uses the path. The existing store is moved along when saving.")</p>
EOF
case "$BLE2UART_GATEWAY_STORE" in
	/tmp/flash/*)
		cat << EOF
<p style="font-size:10px;color:#a60;">$(lang de:"Hinweis: /tmp/flash ist ein RAM-Disk; sie wird beim Stoppen und Speichern per modsave archiviert. Für Bindkeys ist eine Platte sicherer." en:"Note: /tmp/flash is a ramdisk; it is archived by modsave on stop and on every save. A disk is safer for the bind keys.")</p>
EOF
		;;
esac
sec_end

echo '</details>'
sec_begin "$(lang de:"Gateway-Konfiguration" en:"Gateway configuration")"
cat << 'EOF'
<style>
#bbApp {--bb-line:var(--evo-border,#c9ced1);--bb-accent:var(--evo-accent,#087e83);color:inherit;font:inherit;min-width:0;}
#bbApp * {box-sizing:border-box;letter-spacing:0;}
#bbApp button,#bbApp select,#bbApp input {font:inherit;max-width:100%;}
#bbApp button {cursor:pointer;min-height:30px;padding:4px 10px;white-space:normal;}
#bbApp button:disabled {cursor:default;opacity:.55;}
#bbApp input:not([type=checkbox]),#bbApp select,#bbApp textarea {padding:6px;border:1px solid var(--bb-line);border-radius:3px;color:inherit;background:var(--evo-surface,#fff);}
#bbApp input[type=checkbox] {width:18px;height:18px;vertical-align:middle;}
#bbApp .bbBar {display:flex;align-items:center;flex-wrap:wrap;gap:8px;margin:10px 0;}
#bbApp .bbTabs {border-bottom:1px solid var(--bb-line);gap:0;}
#bbApp .bbTabs button {border:0;border-bottom:3px solid transparent;background:transparent;color:inherit;padding:10px 14px;}
#bbApp .bbTabs button[aria-selected=true] {border-bottom-color:var(--bb-accent);font-weight:bold;}
#bbApp .bbScroll {overflow:auto;max-height:480px;border-top:1px solid var(--bb-line);}
#bbApp table {width:100%;border-collapse:collapse;font-size:12px;}
#bbApp th {position:sticky;top:0;background:var(--evo-surface,#edf2f3);z-index:1;text-align:left;}
#bbApp th,#bbApp td {padding:8px;border-bottom:1px solid var(--bb-line);vertical-align:top;overflow-wrap:anywhere;min-width:65px;}
#bbApp td.bbMac {white-space:nowrap;font-family:monospace;min-width:155px;}
#bbApp .bbGrid {display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,235px),1fr));gap:12px 20px;}
#bbApp label.bbField {display:flex;flex-direction:column;gap:5px;min-width:0;}
#bbApp label.bbField input:not([type=checkbox]),#bbApp label.bbField select {width:100%;}
#bbApp .bbGroup {border:0;border-top:1px solid var(--bb-line);padding:14px 0;margin:12px 0;min-width:0;}
#bbApp .bbGroup legend {font-weight:bold;padding:0 8px 0 0;}
#bbApp .bbItem {border-left:2px solid var(--bb-line);padding:4px 0 12px 12px;margin:8px 0;}
#bbApp .bbStatus {min-height:24px;margin:8px 0;overflow-wrap:anywhere;}
#bbApp .bbError {color:#b73030;}
#bbApp dialog {color:inherit;background:var(--evo-surface,#fff);border:1px solid var(--bb-line);border-radius:6px;width:720px;max-width:calc(100vw - 24px);max-height:90vh;padding:20px;overflow:auto;}
#bbApp dialog::backdrop {background:rgba(0,0,0,.4);}
#bbApp textarea {width:100%;resize:vertical;font:12px/1.5 monospace;}
#bbApp pre {white-space:pre-wrap;overflow-wrap:anywhere;font:12px/1.5 monospace;max-height:340px;overflow:auto;}
#bbApp [hidden] {display:none!important;}
@media(max-width:600px) {#bbApp th,#bbApp td {padding:6px;}#bbApp .bbTabs button {padding:8px;}#bbApp dialog {padding:12px;}}
#bbApp .bbActions {display:flex;flex-wrap:wrap;gap:8px;align-items:flex-start;min-width:90px;}
#bbApp .bbSecret {display:flex;gap:8px;align-items:center;min-width:0;}
#bbApp .bbSecret input {flex:1;min-width:0;}
#bbApp .bbSecret button {flex:0 0 64px;}
#bbApp #bbYaml {height:480px;min-height:280px;max-height:65vh;width:100%;border:1px solid var(--bb-line);}
</style>
<div id="bbApp">
<div class="bbBar">
<button type="button" id="bbReload">Reload</button>
<button type="button" id="bbCheck">Validate</button>
<button type="button" id="bbSave">Save configuration</button>
<button type="button" id="bbRestart">Restart service</button>
<button type="button" id="bbLogging">Reload logging</button>
<span id="bbDirty"></span>
</div>
<div id="bbMsg" class="bbStatus" role="status" aria-live="polite">Loading configuration...</div>
<div class="bbBar bbTabs" role="tablist" aria-label="Gateway views">
<button type="button" role="tab" data-tab="devices" aria-selected="true">Devices</button>
<button type="button" role="tab" data-tab="discovery" aria-selected="false">Discovery</button>
<button type="button" role="tab" data-tab="commands" id="bbCommandsTab" aria-selected="false">Commands</button>
<button type="button" role="tab" data-tab="settings" aria-selected="false">Settings</button>
<button type="button" role="tab" data-tab="yaml" aria-selected="false">YAML</button>
</div>
<section data-panel="devices" role="tabpanel">
<div class="bbBar"><button type="button" id="bbAdd">Add device</button><input id="bbDeviceSearch" type="search" placeholder="MAC, name, manufacturer or model" aria-label="Filter configured devices"></div>
<div class="bbScroll"><table><thead><tr><th>Enabled</th><th>MAC</th><th>Name / manufacturer / model</th><th>Format</th><th>Exposed attributes</th><th>Actions</th></tr></thead><tbody id="bbDevices"></tbody></table></div>
</section>
<section data-panel="discovery" role="tabpanel" hidden>
<div class="bbBar"><label>Duration (s) <input type="number" id="bbDuration" min="1" max="300" value="30" style="width:80px"></label><button type="button" id="bbStart">Start discovery</button><button type="button" id="bbStop" disabled>Stop</button><span id="bbDiscoveryStatus" role="status"></span></div>
<div class="bbBar"><input type="search" id="bbSearch" placeholder="MAC, name or format" aria-label="Search discovery"><select id="bbVendor" aria-label="Filter by OUI vendor"><option value="">All OUI vendors</option></select><select id="bbSort" aria-label="Sort discovery"><option value="rssi">Strongest signal</option><option value="mac">MAC</option><option value="name">Name</option><option value="vendor">OUI vendor</option><option value="format">Wire format</option><option value="count">Most reports</option><option value="last_seen">Last seen</option></select><label><input type="checkbox" id="bbNewOnly"> Unconfigured only</label><button type="button" id="bbExport">Export observations</button></div>
<div class="bbScroll"><table><thead><tr><th>MAC / name</th><th>OUI vendor</th><th>Wire format</th><th>RSSI</th><th>PHY</th><th>Reports / last seen</th><th>Actions</th></tr></thead><tbody id="bbFound"></tbody></table></div>
<details><summary>Selected advertisement</summary><pre id="bbPacket"></pre></details>
</section>
<section data-panel="settings" role="tabpanel" hidden><div id="bbSettings"></div></section>
<section data-panel="commands" role="tabpanel" hidden>
<p id="bbCommandNote"></p>
<div class="bbBar"><label><span id="bbCommandTypeLabel"></span> <select id="bbCommandType"></select></label><button type="button" id="bbCommandSend"></button><button type="button" id="bbRadioRefresh"></button></div>
<div id="bbCommandFields" class="bbGrid"></div>
<pre id="bbRadio" role="status"></pre>
<pre id="bbCommandResult" role="status" aria-live="polite"></pre>
</section>
<section data-panel="yaml" role="tabpanel" hidden><div id="bbYaml" aria-label="Complete gateway YAML configuration"></div><div class="bbBar"><button type="button" id="bbDownload">Download YAML</button><label>Import YAML <input type="file" id="bbImport" accept=".yaml,.yml,text/plain"></label></div><div class="bbBar"><button type="button" id="bbHistory">List backups</button><select id="bbBackups" aria-label="Configuration backup"><option value="">Select backup</option></select><button type="button" id="bbRestore">Load backup</button></div></section>
<datalist id="bbFormats"><option value="custom"><option value="custom_enc"><option value="atc1441"><option value="atc1441_enc"><option value="mi_like"><option value="bt_home"><option value="bt_home_enc"><option value="bt_home_v2"></datalist>
<datalist id="bbAttributes"><option value="temperature"><option value="humidity"><option value="battery_level"><option value="battery_v"><option value="switch"><option value="opened"><option value="boolean"><option value="humidity_trigger"><option value="temp_trigger"><option value="out_gpio_trg_flag"><option value="out_gpio_trg_value"><option value="input_gpio_value"></datalist>
<dialog id="bbDeviceDialog"><h3 id="bbDeviceTitle">Device</h3><div id="bbDeviceFields"></div><div class="bbBar"><button type="button" id="bbDeviceApply">Keep changes</button><button type="button" id="bbDeviceCancel">Cancel</button></div><div id="bbDeviceError" role="alert" class="bbError"></div></dialog>
<dialog id="bbConfirm"><h3>Confirm</h3><p id="bbConfirmText"></p><div class="bbBar"><button type="button" id="bbConfirmOk">Continue</button><button type="button" id="bbConfirmCancel">Cancel</button></div></dialog>
</div>
<script>
(() => {
	const app = document.getElementById('bbApp');
	const element = id => document.getElementById(id);
	const copy = value => JSON.parse(JSON.stringify(value));
	const normalize = mac => String(mac).replace(/[:-]/g, '').toUpperCase();
	let config = null, revision = '', dirty = false, rawDirty = false, tab = 'devices';
	let observations = [], editIndex = -1, draft = null, polling = false, busy = false;
	let yamlEditor=null, yamlText='', syncingYaml=false, inspectionSequence=0;
	function setYaml(text) {yamlText=text;if(yamlEditor){syncingYaml=true;yamlEditor.setValue(text,-1);syncingYaml=false;}}
	function getYaml() {return yamlEditor?yamlEditor.getValue():yamlText;}
	function loadScript(source) {return new Promise((resolve,reject)=>{const script=document.createElement('script');script.src=source;script.onload=resolve;script.onerror=()=>reject(new Error('Cannot load editor asset: '+source));document.head.append(script);});}
	async function ensureYamlEditor() {
		if(yamlEditor)return;
		if(!window.ace)await loadScript('/ace/ace.js');
		ace.config.setModuleUrl('ace/mode/yaml','/ble2uart_gateway/mode-yaml.js');
		await loadScript('/ble2uart_gateway/mode-yaml.js');
		yamlEditor=ace.edit('bbYaml');yamlEditor.session.setUseWorker(false);yamlEditor.session.setMode('ace/mode/yaml');yamlEditor.setTheme('ace/theme/textmate');
		yamlEditor.setOptions({fontSize:'12px',showPrintMargin:false,wrap:true,tabSize:2,useSoftTabs:true});
		setYaml(yamlText);yamlEditor.session.on('change',()=>{if(!syncingYaml){rawDirty=true;changed();}});
	}
	const labels = {filter_known_devices:'Filter registered devices in ESP32', phy_1m:'1M PHY', phy_coded:'Coded PHY', dup_filter:'Duplicate filter', discard_random:'Discard random addresses', discard_rpa:'Discard resolvable private addresses', active_scan:'Active scan', window_1m:'1M window (0.625 ms units)', window_coded:'Coded window (0.625 ms units)', whitelist:'Whitelist MAC prefixes', blacklist:'Blacklist MAC prefixes', reset_on_open:'Reset ESP32 on open', command_timeout_ms:'Command timeout (ms)', reconnect_delay_ms:'Reconnect delay (ms)', bindkey:'Bindkey (32 hexadecimal digits)', format:'Forced wire format (empty = automatic)', expose:'Exposed attributes', child:'MySensors child ID', node_id_base:'First MySensors node ID', tx_hex:'Raw TX trace', rx_hex:'Raw RX trace', decode:'Codec decode trace', phy:'PHY reception / decode trace', after_s:'Delay (seconds)', kind:'Kind override', mysensors:'MySensors / Domoticz', mqtt:'MQTT', matter:'Matter', influx:'InfluxDB 3', advertise:'Advertise via DNS-SD', mdns_backend:'DNS-SD backend', mdns_hostname:'mDNS host name (empty = default)', mdns_interface:'mDNS interface (empty = automatic)', endpoint:'Endpoint URL', batch_size:'Batch size', queue_capacity:'Queue capacity', flush_interval_ms:'Flush interval (ms)', timeout_ms:'Timeout (ms)', diagnostics:'Diagnostics', rules:'Rules', serial:'Serial', scanner:'Scanner', log_level:'Log level', frontends:'Frontends', mac:'MAC', rssi:'RSSI'};
	Object.assign(labels, {manufacturer:'Manufacturer',model:'Device model',firmware_version:'Device firmware version',label:'Device name',sqlite:'SQLite',path:'Database file (absolute local path)',busy_timeout_ms:'SQLite busy timeout (ms)'});
	const title = key => labels[key] || key.replace(/_/g, ' ').replace(/^./, letter => letter.toUpperCase());
	const message = (text, error = false) => {element('bbMsg').textContent = text; element('bbMsg').classList.toggle('bbError', error);};
	const changed = () => {dirty = true; element('bbDirty').textContent = 'Unsaved changes';};
	const button = (text, action, tooltip) => {const node = document.createElement('button'); node.type = 'button'; node.textContent = text; node.onclick = action; if (tooltip) node.title = tooltip; return node;};
	const cell = (row, text, className) => {const node = row.insertCell(); node.textContent = text; if (className) node.className = className; return node;};
	const actionsCell = (row, ...controls) => {const group=document.createElement('div');group.className='bbActions';group.append(...controls);cell(row,'').append(group);return group;};
	async function removeDevice(index) {
		const device=config.devices[index];
		if(await confirmAction('Remove '+(device.label||device.mac)+' from this configuration?')) {
			config.devices.splice(index,1);changed();renderDevices();renderFound();
		}
	}
	async function api(action, body, params = {}) {
		const url = new URL('/cgi-bin/extra/ble2uart_gateway/api', location.href);
		url.search = new URLSearchParams({ajax:'1', action, ...params}).toString();
		const response = await fetch(url, {method: ['read','status'].includes(action) ? 'GET' : 'POST', credentials:'same-origin', cache:'no-store', headers:body ? {'Content-Type':'application/json'} : {}, body:body ? JSON.stringify(body) : undefined});
		const document = new DOMParser().parseFromString(await response.text(), 'text/html');
		const pre = document.querySelector('.ajax-json-content pre');
		if (!pre) throw new Error('Invalid response or session expired');
		const text = pre.textContent;
		const marker = 'Content-Type: application/json';
		const index = text.indexOf(marker);
		if (index < 0) throw new Error('Invalid API response');
		const data = JSON.parse(text.slice(index + marker.length).trim());
		if (!response.ok || !data.success) throw new Error(data.error || 'Request failed');
		return data;
	}
	async function run(action) {
		if (busy) return;
		busy = true;
		['bbSave','bbCheck','bbReload','bbRestart','bbLogging'].forEach(id => element(id).disabled = true);
		try {await action();} catch (error) {message(error.message, true);} finally {busy = false; ['bbSave','bbCheck','bbReload','bbRestart','bbLogging'].forEach(id => element(id).disabled = !config);}
	}
	function confirmAction(text) {
		return new Promise(resolve => {
			const dialog = element('bbConfirm'); element('bbConfirmText').textContent = text;
			const finish = answer => {dialog.close(); resolve(answer);};
			element('bbConfirmOk').onclick = () => finish(true);
			element('bbConfirmCancel').onclick = () => finish(false);
			dialog.oncancel = event => {event.preventDefault(); finish(false);};
			dialog.showModal();
		});
	}
	const commandTranslations = {
		en: {tab:'Commands',type:'Command',send:'Send command',refresh:'Refresh radio status',note:'Temporary commands pause scanning and restore it afterwards, including on error. TXADV start leaves scanning OFF until explicitly restarted. Commands use the running daemon, not unsaved settings.',confirm:'Send this command to the device? Writes and pairing can change the device. TXADV start stops scanning until you explicitly restart it.',pending:'Command running; do not retry while awaiting its result.',done:'Command completed; inspect the confirmation level below.',diagnostic:'Firmware diagnostics',gatt:'BLE GATT transaction',start:'Start TXADV (leave scan OFF)',stop:'Stop TXADV (leave scan OFF)',scanStart:'Start configured scan (stop TXADV)',scanStop:'Stop scan',name:'Diagnostic',pin:'GPIO pin',mac:'Peer MAC',addr_type:'Address type (0 public, 1 random)',coded:'Connect on Coded PHY',operation:'GATT operation',handle:'ATT handle (decimal, reads/writes only)',value:'Write value (hex, at most 20 bytes)',timeout_ms:'Transaction timeout (100-30000 ms)',phy:'TX PHY (0 legacy 1M, 1 extended 1M, 2 coded)',interval_units:'TX interval (0.625 ms units, minimum 32)',data:'Advertisement data (hex, at most 31 bytes)'},
		de: {tab:'Befehle',type:'Befehl',send:'Befehl senden',refresh:'Funkstatus aktualisieren',note:'Temporäre Befehle pausieren den Scan und stellen ihn auch bei Fehlern wieder her. TXADV lässt den Scan bis zum manuellen Neustart AUS. Es gelten die laufenden Einstellungen.',confirm:'Befehl senden? Schreiben und Pairing können das Gerät ändern. TXADV stoppt den Scan bis zum manuellen Neustart.',pending:'Befehl läuft; nicht erneut senden.',done:'Befehl beendet; Bestätigungsstufe unten prüfen.',diagnostic:'Firmware-Diagnose',gatt:'BLE-GATT-Transaktion',start:'TXADV starten (Scan AUS)',stop:'TXADV stoppen (Scan bleibt AUS)',scanStart:'Scan starten (TXADV stoppen)',scanStop:'Scan stoppen',name:'Diagnose',pin:'GPIO-Pin',mac:'Geräte-MAC',addr_type:'Adresstyp (0 öffentlich, 1 zufällig)',coded:'Coded-PHY-Verbindung',operation:'GATT-Operation',handle:'ATT-Handle (dezimal, nur Lesen/Schreiben)',value:'Schreibwert (Hex, maximal 20 Bytes)',timeout_ms:'Zeitlimit (100-30000 ms)',phy:'TX-PHY (0 Legacy 1M, 1 Extended 1M, 2 Coded)',interval_units:'TX-Intervall (0,625 ms, mindestens 32)',data:'Advertisement-Daten (Hex, maximal 31 Bytes)'},
		it: {tab:'Comandi',type:'Comando',send:'Invia comando',refresh:'Aggiorna stato radio',note:'I comandi temporanei sospendono lo scan e lo ripristinano anche in caso di errore. TXADV lascia lo scan SPENTO fino a un riavvio esplicito. Si usano le impostazioni del daemon, non le modifiche non salvate.',confirm:'Inviare il comando? Scritture e pairing possono modificare il dispositivo. TXADV interrompe lo scan fino al riavvio esplicito.',pending:'Comando in corso; non reinviarlo in attesa del risultato.',done:'Comando terminato; verificare il livello di conferma qui sotto.',diagnostic:'Diagnostica firmware',gatt:'Transazione BLE GATT',start:'Avvia TXADV (scan SPENTO)',stop:'Ferma TXADV (scan resta SPENTO)',scanStart:'Avvia scan configurato (ferma TXADV)',scanStop:'Ferma scan',name:'Diagnostica',pin:'Pin GPIO',mac:'MAC destinatario',addr_type:'Tipo indirizzo (0 pubblico, 1 casuale)',coded:'Connessione su PHY Coded',operation:'Operazione GATT',handle:'Handle ATT (decimale, solo letture/scritture)',value:'Valore da scrivere (hex, massimo 20 byte)',timeout_ms:'Timeout transazione (100-30000 ms)',phy:'PHY TX (0 legacy 1M, 1 extended 1M, 2 coded)',interval_units:'Intervallo TX (unità 0,625 ms, minimo 32)',data:'Dati advertisement (hex, massimo 31 byte)'},
		fr: {tab:'Commandes',type:'Commande',send:'Envoyer la commande',refresh:'Actualiser la radio',note:'Les commandes temporaires suspendent puis rétablissent le scan, même en cas d’erreur. TXADV laisse le scan ARRÊTÉ jusqu’au redémarrage explicite. Les paramètres actifs du daemon sont utilisés.',confirm:'Envoyer cette commande ? Écriture et appairage peuvent modifier le périphérique. TXADV arrête le scan jusqu’au redémarrage explicite.',pending:'Commande en cours ; ne pas la renvoyer.',done:'Commande terminée ; vérifier le niveau de confirmation ci-dessous.',diagnostic:'Diagnostic firmware',gatt:'Transaction BLE GATT',start:'Démarrer TXADV (scan ARRÊTÉ)',stop:'Arrêter TXADV (scan reste ARRÊTÉ)',scanStart:'Démarrer le scan (arrêter TXADV)',scanStop:'Arrêter le scan',name:'Diagnostic',pin:'Broche GPIO',mac:'MAC du périphérique',addr_type:'Type d’adresse (0 publique, 1 aléatoire)',coded:'Connexion PHY Coded',operation:'Opération GATT',handle:'Handle ATT (décimal, lecture/écriture)',value:'Valeur (hex, 20 octets maximum)',timeout_ms:'Délai (100-30000 ms)',phy:'PHY TX (0 legacy 1M, 1 extended 1M, 2 coded)',interval_units:'Intervalle TX (0,625 ms, minimum 32)',data:'Données advertisement (hex, 31 octets maximum)'},
		es: {tab:'Comandos',type:'Comando',send:'Enviar comando',refresh:'Actualizar radio',note:'Los comandos temporales pausan el escaneo y lo restauran incluso si fallan. TXADV deja el escaneo APAGADO hasta reiniciarlo explícitamente. Se usan los ajustes activos del daemon.',confirm:'¿Enviar el comando? Escritura y emparejamiento pueden modificar el dispositivo. TXADV detiene el escaneo hasta reiniciarlo explícitamente.',pending:'Comando en curso; no volver a enviarlo.',done:'Comando terminado; comprobar el nivel de confirmación abajo.',diagnostic:'Diagnóstico del firmware',gatt:'Transacción BLE GATT',start:'Iniciar TXADV (escaneo APAGADO)',stop:'Detener TXADV (escaneo sigue APAGADO)',scanStart:'Iniciar escaneo (detener TXADV)',scanStop:'Detener escaneo',name:'Diagnóstico',pin:'Pin GPIO',mac:'MAC del dispositivo',addr_type:'Tipo de dirección (0 pública, 1 aleatoria)',coded:'Conexión PHY Coded',operation:'Operación GATT',handle:'Handle ATT (decimal, lectura/escritura)',value:'Valor (hex, máximo 20 bytes)',timeout_ms:'Tiempo límite (100-30000 ms)',phy:'PHY TX (0 legacy 1M, 1 extended 1M, 2 coded)',interval_units:'Intervalo TX (0,625 ms, mínimo 32)',data:'Datos advertisement (hex, máximo 31 bytes)'}
	};
	const ct = commandTranslations[(navigator.language || 'en').split('-')[0]] || commandTranslations.en;
	let commandDraft;
	const commandOptions = {
		name:['info','version','uart','rfsdk','vbat','gpio-events','gpio-status','gpio-read','analog-read','connection-status','txadv-status'],
		operation:['discover','read','write','write-without-response','read-descriptor','write-descriptor','mtu','unpair']
	};
	function renderCommand() {
		const command = element('bbCommandType').value;
		commandDraft = command === 'diagnostic' ? {command,name:'info',pin:0} : command === 'gatt' ? {command,mac:'',addr_type:0,coded:false,operation:'discover',handle:0,value:'',timeout_ms:10000} : command === 'txadv-start' ? {command,phy:0,interval_units:160,data:''} : {command};
		const parent = element('bbCommandFields'); parent.replaceChildren();
		Object.entries(commandDraft).filter(([key])=>key!=='command').forEach(([key,value])=>{
			const label=document.createElement('label');label.className='bbField';label.append(ct[key]);
			const input=document.createElement(commandOptions[key]?'select':'input');
			if(commandOptions[key])commandOptions[key].forEach(option=>input.add(new Option(option,option)));
			else input.type=typeof value==='boolean'?'checkbox':typeof value==='number'?'number':'text';
			input.id='bbCmd_'+key;input.title=ct[key];input.autocomplete='off';
			if(input.type==='checkbox')input.checked=value;else input.value=value;
			if(input.type==='number'){input.min='0';input.step='1';}
			if(key==='timeout_ms'){input.min='100';input.max='30000';}
			if(key==='interval_units'){input.min='32';input.max='65535';}
			if(key==='handle')input.max='65535';
			if(key==='addr_type')input.max='1';
			if(key==='phy')input.max='2';
			input.oninput=()=>{commandDraft[key]=input.type==='checkbox'?input.checked:input.type==='number'?Number(input.value):input.value;};
			label.append(input);parent.append(label);
		});
	}
	async function radioStatus() {const status=await api('status');element('bbRadio').textContent=JSON.stringify({connected:status.connected,...status.radio},null,2);}
	element('bbCommandsTab').textContent=ct.tab;element('bbCommandTypeLabel').textContent=ct.type;element('bbCommandNote').textContent=ct.note;
	[['diagnostic','diagnostic'],['gatt','gatt'],['txadv-start','start'],['txadv-stop','stop'],['scan-start','scanStart'],['scan-stop','scanStop']].forEach(([value,key])=>element('bbCommandType').add(new Option(ct[key],value)));
	element('bbCommandType').title=ct.type;element('bbCommandType').onchange=renderCommand;
	element('bbCommandSend').textContent=ct.send;element('bbCommandSend').title=ct.send;
	element('bbRadioRefresh').textContent=ct.refresh;element('bbRadioRefresh').title=ct.refresh;
	element('bbRadioRefresh').onclick=()=>run(radioStatus);
	element('bbCommandSend').onclick=()=>run(async()=>{
		if(!Array.from(element('bbCommandFields').querySelectorAll('input')).every(input=>input.reportValidity()))return;
		if(!await confirmAction(ct.confirm))return;
		element('bbCommandSend').disabled=true;message(ct.pending);element('bbCommandResult').textContent='';
		try {const response=await api('command',commandDraft);element('bbCommandResult').textContent=JSON.stringify(response,null,2);message(ct.done);}
		catch(error){element('bbCommandResult').textContent=error.message;throw error;}
		finally{element('bbCommandSend').disabled=false;await radioStatus();}
	});
	renderCommand();
	function fields(parent, object, onChange) {
		const grid = document.createElement('div'); grid.className = 'bbGrid'; parent.append(grid);
		Object.keys(object).forEach(key => {
			const value = object[key];
			if (Array.isArray(value) && ['whitelist','blacklist'].includes(key)) {
				const label = document.createElement('label'); label.className = 'bbField'; label.append(title(key));
				const input = document.createElement('textarea'); input.rows = 3; input.value = value.join('\n'); input.oninput = () => {object[key] = input.value.split(/[\s,]+/).filter(Boolean); onChange();}; label.append(input); grid.append(label);
			} else if (Array.isArray(value)) {
				const group = document.createElement('fieldset'); group.className = 'bbGroup'; const legend = document.createElement('legend'); legend.textContent = title(key); group.append(legend); parent.append(group);
				const render = () => {
					group.replaceChildren(legend);
					value.forEach((item, index) => {
						const row = document.createElement('div'); row.className = 'bbItem';
						row.append(button('Remove ' + (index + 1), () => {value.splice(index,1); render(); onChange();}));
						fields(row, item, onChange); group.append(row);
					});
					group.append(button('Add ' + (key === 'expose' ? 'attribute' : 'rule'), () => {value.push(key === 'expose' ? {attribute:'', child:null, kind:null} : {name:'',label:'',source:'',equals:'',after_s:0,mirror:false}); render(); onChange();}));
				}; render();
			} else if (value && typeof value === 'object') {
				const group = document.createElement('fieldset'); group.className = 'bbGroup'; const legend = document.createElement('legend'); legend.textContent = title(key); group.append(legend); fields(group, value, onChange); parent.append(group);
			} else {
				const label = document.createElement('label'); label.className = 'bbField'; label.append(title(key));
				let input;
				if (key === 'log_level') {input = document.createElement('select'); ['off','error','warn','info','debug','trace'].forEach(level => input.add(new Option(level,level))); input.value = value;}
				else if (key === 'mdns_backend') {input = document.createElement('select'); ['auto','builtin','avahi','resolved','zeroconf','astro','disabled'].forEach(backend => input.add(new Option(backend,backend))); input.value = value || 'auto';}
				else {input = document.createElement('input'); input.type = typeof value === 'boolean' ? 'checkbox' : typeof value === 'number' || key === 'child' ? 'number' : /^(bindkey|password|token)$/.test(key) ? 'password' : 'text'; if (input.type === 'checkbox') input.checked = value; else input.value = value == null ? '' : value;}
				input.autocomplete = 'off';
				if (input.type === 'number') {input.min = '0'; input.step = '1'; if (key === 'child') input.max = '255'; if (key === 'port') {input.min='1';input.max='65535';}}
				if (key === 'format') input.setAttribute('list','bbFormats');
				if (key === 'attribute') input.setAttribute('list','bbAttributes');
				if (key === 'bindkey') {input.maxLength=32; input.pattern='[A-Fa-f0-9]{32}';input.setAttribute('aria-label',title(key));}
				input.oninput = () => {object[key] = input.type === 'checkbox' ? input.checked : input.type === 'number' ? (input.value === '' ? null : Number(input.value)) : input.value; onChange();};
				if(input.type==='password') {
					const secret=document.createElement('div');secret.className='bbSecret';const name=key==='bindkey'?'bindkey':title(key).toLowerCase();
					const reveal=button('Show',event=>{event.preventDefault();const visible=input.type==='password';input.type=visible?'text':'password';reveal.textContent=visible?'Hide':'Show';reveal.setAttribute('aria-pressed',String(visible));reveal.setAttribute('aria-label',(visible?'Hide ':'Show ')+name);},'Show or hide '+name);
					reveal.setAttribute('aria-pressed','false');reveal.setAttribute('aria-label','Show '+name);secret.append(input,reveal);label.append(secret);
				} else {label.append(input);}
				grid.append(label);
			}
		});
	}
	function renderSettings() {
		const parent = element('bbSettings'); parent.replaceChildren();
		const editable = Object.fromEntries(Object.entries(config).filter(([key]) => !['devices','version'].includes(key)));
		fields(parent, editable, () => {Object.assign(config,editable); changed();});
	}
	function renderDevices() {
		const body = element('bbDevices'); body.replaceChildren(); const query = element('bbDeviceSearch').value.toLowerCase();
		config.devices.forEach((device,index) => {
			if (![device.mac,device.label,device.manufacturer,device.model].join(' ').toLowerCase().includes(query)) return;
			const row = body.insertRow(); const enabled = document.createElement('input'); enabled.type='checkbox'; enabled.checked=device.enabled; enabled.setAttribute('aria-label','Enable '+device.mac); enabled.onchange=()=>{device.enabled=enabled.checked;changed();}; cell(row,'').append(enabled);
			cell(row,device.mac,'bbMac'); cell(row,[device.label,device.manufacturer,device.model].filter(Boolean).join(' / ')); cell(row,device.format || 'Automatic'); cell(row,device.expose.map(item=>item.attribute + (item.child == null ? '' : ' ['+item.child+']')).join(', '));
			actionsCell(row,button('Edit',()=>editDevice(index)),button('Remove',()=>removeDevice(index)));
		});
		if (!body.rows.length) cell(body.insertRow(),'No matching configured devices').colSpan=6;
	}
	function editDevice(index, found) {
		editIndex=index;
		draft=index>=0 ? copy(config.devices[index]) : {mac:found ? found.mac : '',label:found ? found.name : '',manufacturer:'',model:'',firmware_version:'',bindkey:'',enabled:true,format:'',expose:found && found.format ? [{attribute:'temperature',child:0,kind:null},{attribute:'humidity',child:1,kind:null},{attribute:'battery_level',child:2,kind:null}] : [],rules:[]};
		element('bbDeviceTitle').textContent=index>=0?'Edit device':'Add device'; element('bbDeviceFields').replaceChildren(); element('bbDeviceError').textContent='';
		fields(element('bbDeviceFields'),draft,()=>{}); element('bbDeviceDialog').showModal();
	}
	async function keepDevice() {
		const candidate=copy(config); if(editIndex>=0)candidate.devices[editIndex]=draft;else candidate.devices.push(draft);
		try {const data=await api('check',{config:candidate}); config=data.config; changed();renderDevices();renderFound();element('bbDeviceDialog').close();} catch(error){element('bbDeviceError').textContent=error.message;}
	}
	function renderFound() {
		const vendor=element('bbVendor').value, query=element('bbSearch').value.toLowerCase(), sort=element('bbSort').value;
		const vendors=[...new Set(observations.map(device=>device.vendor))].sort(); element('bbVendor').replaceChildren(new Option('All OUI vendors',''),...vendors.map(name=>new Option(name,name))); element('bbVendor').value=vendor;
		const found=observations.filter(device=>(!vendor||device.vendor===vendor)&&[device.mac,device.name,device.format,device.vendor].join(' ').toLowerCase().includes(query)&&(!element('bbNewOnly').checked||!config.devices.some(known=>normalize(known.mac)===device.mac)));
		found.sort((first,second)=>['rssi','count'].includes(sort)?second[sort]-first[sort]:sort==='last_seen'?String(second[sort]).localeCompare(first[sort]):String(first[sort]).localeCompare(String(second[sort])));
		const body=element('bbFound');body.replaceChildren();
		found.forEach(device=>{const row=body.insertRow();cell(row,device.mac+(device.name?' / '+device.name:''),'bbMac');cell(row,device.vendor);cell(row,device.format||'Unrecognized');cell(row,device.rssi+' dBm');cell(row,device.phy.replace(/^phy_raw=\S+ /,''));cell(row,device.count+' / '+device.last_seen);const index=config.devices.findIndex(known=>normalize(known.mac)===device.mac);const actions=actionsCell(row,button(index>=0?'Edit':'Configure',()=>editDevice(index,device)),button('Inspect',()=>inspectDevice(device)));if(index>=0)actions.append(button('Remove',()=>removeDevice(index)));});
		if(!body.rows.length)cell(body.insertRow(),'No matching observations').colSpan=7;
	}
	async function inspectDevice(device) {
		const sequence=++inspectionSequence;
		const packet=element('bbPacket');packet.parentElement.open=true;packet.textContent='Decoding...\n'+JSON.stringify(device,null,2);
		const configured=config.devices.find(known=>normalize(known.mac)===device.mac);
		try {
			const decoded=await api('inspect',{observation:device,device:configured});
			if(sequence===inspectionSequence)packet.textContent=JSON.stringify({...device,decode_status:decoded.decode_status,wire_format:decoded.wire_format,measurements:decoded.measurements,decoded:decoded.decoded,decode_error:decoded.error},null,2);
		} catch(error) {if(sequence===inspectionSequence)packet.textContent=JSON.stringify({...device,decode_status:'failed',decode_error:error.message},null,2);}
	}
	async function poll() {
		if(polling||!config)return; polling=true;
		try {const status=await api('status');observations=status.devices;element('bbStart').disabled=status.active||!status.connected;element('bbStop').disabled=!status.active;element('bbDiscoveryStatus').textContent=(status.active?'Scanning, '+status.remaining_s+' s remaining':status.connected?'Idle':'Serial unavailable')+' | '+observations.length+' devices | '+status.reports+' reports'+(status.overflow?' | table limit reached':'')+(status.error?' | '+status.error:'');renderFound();}
		catch(error){element('bbDiscoveryStatus').textContent=error.message;element('bbStop').disabled=true;}
		finally{polling=false;}
	}
	async function switchTab(next) {
		if(!config||next===tab)return;
		if(tab==='yaml'&&rawDirty){const result=await api('check',{yaml:getYaml()});config=result.config;rawDirty=false;renderSettings();renderDevices();}
		if(next==='yaml'){const result=await api('check',{config});setYaml(result.yaml);rawDirty=false;await ensureYamlEditor();}
		tab=next;app.querySelectorAll('[data-panel]').forEach(panel=>panel.hidden=panel.dataset.panel!==tab);app.querySelectorAll('[data-tab]').forEach(control=>control.setAttribute('aria-selected',String(control.dataset.tab===tab)));if(tab==='discovery')poll();
		if(tab==='yaml')yamlEditor.resize(true);
		if(tab==='commands')await radioStatus();
	}
	function payload(){return {...(tab==='yaml'&&rawDirty?{yaml:getYaml()}:{config}),revision};}
	function download(name,content,type){const url=URL.createObjectURL(new Blob([content],{type}));const link=document.createElement('a');link.href=url;link.download=name;link.click();URL.revokeObjectURL(url);}
	async function load(){if(dirty&&!await confirmAction('Reload and discard unsaved changes?'))return;const data=await api('read');config=data.config;revision=data.revision;dirty=false;rawDirty=false;setYaml(data.yaml);element('bbDirty').textContent='';renderSettings();renderDevices();message('Configuration loaded');if(tab==='discovery')poll();}
	element('bbReload').onclick=()=>run(load);
	element('bbCheck').onclick=()=>run(async()=>{await api('check',payload());message('Configuration is valid');});
	element('bbSave').onclick=()=>run(async()=>{const data=await api('save',payload());config=data.config;revision=data.revision;dirty=false;rawDirty=false;setYaml(data.yaml);element('bbDirty').textContent='Saved';renderSettings();renderDevices();message('Saved. Running settings are unchanged.');});
	element('bbRestart').onclick=()=>run(async()=>{if(await confirmAction('Restart the service using the saved configuration?')){await api('restart');message('Service restarted');poll();}});
	element('bbLogging').onclick=()=>run(async()=>{await api('reload-logging');message('Logging reload requested');});
	element('bbAdd').onclick=()=>{if(config)editDevice(-1);};element('bbDeviceApply').onclick=keepDevice;element('bbDeviceCancel').onclick=()=>element('bbDeviceDialog').close();
	element('bbDeviceSearch').oninput=()=>{if(config)renderDevices();};
	['bbSearch','bbVendor','bbSort','bbNewOnly'].forEach(id=>element(id).addEventListener('input',()=>{if(config)renderFound();}));
	element('bbStart').onclick=()=>run(async()=>{const seconds=Number(element('bbDuration').value);if(!Number.isInteger(seconds)||seconds<1||seconds>300)throw new Error('Duration must be 1-300 seconds');await api('discover-start',null,{seconds});message('Discovery started');await poll();});
	element('bbStop').onclick=()=>run(async()=>{await api('discover-stop');message('Discovery stopped; configured filters restored');await poll();});
	element('bbExport').onclick=()=>download('ble-observations.json',JSON.stringify(observations,null,2),'application/json');
	element('bbHistory').onclick=()=>run(async()=>{const data=await api('backups');element('bbBackups').replaceChildren(new Option('Select backup',''),...data.backups.map(name=>new Option(name,name)));message(data.backups.length+' backups available');});
	element('bbRestore').onclick=()=>run(async()=>{const backup=element('bbBackups').value;if(!backup)throw new Error('Select a backup');if(!await confirmAction('Load this backup, replacing unsaved changes?'))return;const data=await api('restore',{backup});config=data.config;revision=data.revision;setYaml(data.yaml);rawDirty=false;changed();renderSettings();renderDevices();message('Backup loaded; not saved');});
	element('bbDownload').onclick=()=>run(async()=>{const data=await api('check',payload());download('ble2uart_gateway.yaml',data.yaml,'application/yaml');});
	element('bbImport').onchange=()=>run(async()=>{const file=element('bbImport').files[0];if(!file)return;if(file.size>262144)throw new Error('Configuration exceeds 256 KiB');if(dirty&&!await confirmAction('Replace unsaved changes with the imported configuration?'))return;const data=await api('check',{yaml:await file.text()});config=data.config;setYaml(data.yaml);rawDirty=false;changed();renderSettings();renderDevices();message('Imported; not saved');});
	app.querySelectorAll('[data-tab]').forEach(control=>control.onclick=()=>run(()=>switchTab(control.dataset.tab)));
	app.addEventListener('keydown',event=>{if(event.key==='Enter'&&event.target.tagName==='INPUT')event.preventDefault();});
	window.addEventListener('beforeunload',event=>{if(dirty){event.preventDefault();event.returnValue='';}});
	setInterval(()=>{if(tab==='discovery'&&!document.hidden)poll();},1200);
	run(load);
})();
</script>
EOF
sec_end

sec_begin "$(lang de:"Erweitert" en:"Advanced")"
cgi_print_radiogroup_active "verbose" "$BLE2UART_GATEWAY_VERBOSE" "" "$(lang de:"Debug-Protokoll" en:"Debug logging")"
cat << EOF
<p>$(lang de:"Zusaetzliche Kommandozeilenoptionen" en:"Additional command line options"): <input type="text" name="extra_args" size="60" maxlength="255" value="$(html "$BLE2UART_GATEWAY_EXTRA_ARGS")"></p>
<p style="font-size:11px;">$(lang de:"Protokoll: Status -> Logs -> rc.ble2uart_gateway" en:"Log: Status -> Logs -> rc.ble2uart_gateway"): <code>/tmp/rc.ble2uart_gateway.log</code></p>
EOF
sec_end
