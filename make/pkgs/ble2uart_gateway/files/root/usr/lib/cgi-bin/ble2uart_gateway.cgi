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
#bbApp #bbYaml,#bbApp #bbPacket {height:480px;min-height:280px;max-height:65vh;width:100%;border:1px solid var(--bb-line);}
#bbApp #bbPacket:not(.ace_editor) {white-space:pre-wrap;overflow:auto;font:12px/1.5 monospace;}
#bbApp .bbHelp {margin:8px 0;line-height:1.5;}
#bbApp .bbHelp summary {cursor:pointer;}
#bbApp .bbHelp dl {margin:8px 0;}
#bbApp .bbHelp dt {font-family:monospace;font-weight:bold;margin-top:10px;overflow-wrap:anywhere;}
#bbApp .bbHelp dd {margin:4px 0 10px;overflow-wrap:anywhere;}
#bbApp .bbHint {font-size:12px;line-height:1.5;overflow-wrap:anywhere;}
#bbApp #bbFieldTooltip {position:fixed;z-index:10000;max-width:min(390px,calc(100vw - 16px));padding:10px 12px;border:1px solid var(--bb-line);border-radius:4px;background:var(--evo-surface,#fff);color:inherit;box-shadow:0 3px 12px #0003;font:12px/1.5 sans-serif;pointer-events:none;overflow-wrap:anywhere;}
#bbApp #bbFieldTooltip strong {display:block;font-family:monospace;margin-bottom:4px;}
#bbApp #bbMacFilters {scroll-margin-top:16px;}
#bbApp #bbRegisteredFilter {margin:12px 0;}
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
<div class="bbBar"><span id="bbDiscoveryFilterNote" class="bbHint"></span><button type="button" id="bbOpenFilters"></button></div>
<div class="bbScroll"><table><thead><tr><th>MAC / name</th><th>OUI vendor</th><th>Wire format</th><th>RSSI</th><th>PHY</th><th>Reports / last seen</th><th>Actions</th></tr></thead><tbody id="bbFound"></tbody></table></div>
<details id="bbPacketDetails"><summary>Selected advertisement</summary><p id="bbPacketHint" class="bbHint"></p><details id="bbPacketHelp" class="bbHelp"><summary id="bbPacketHelpTitle"></summary><dl id="bbPacketFields"></dl></details><p id="bbPacketNotice" class="bbHint" role="status" hidden></p><div id="bbPacketError" role="alert" class="bbError" hidden></div><div id="bbPacket" aria-label="Selected advertisement JSON" aria-describedby="bbPacketHint"></div></details>
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
<dialog id="bbDeviceDialog"><h3 id="bbDeviceTitle">Device</h3><div id="bbDeviceFields"></div><details id="bbDeviceHelp" class="bbHelp"><summary>Keep changes / Cancel</summary><p id="bbKeepHelp"></p><p id="bbCancelHelp"></p></details><div class="bbBar"><button type="button" id="bbDeviceApply">Keep changes</button><button type="button" id="bbDeviceCancel">Cancel</button></div><div id="bbDeviceError" role="alert" class="bbError"></div></dialog>
<dialog id="bbConfirm"><h3>Confirm</h3><p id="bbConfirmText"></p><div class="bbBar"><button type="button" id="bbConfirmOk">Continue</button><button type="button" id="bbConfirmCancel">Cancel</button></div></dialog>
<div id="bbFieldTooltip" role="tooltip" hidden><strong></strong><span></span></div>
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
	let aceLoading=null, packetEditor=null, packetEditorLoading=null, packetText='';
	let packetKeys=[];
	const helpTranslations = {
		en: {
			guide:'Advertisement field guide', hint:'Hover a JSON field name for help. Open the field guide for keyboard or touch access; the JSON stays read-only and can be copied.',
			fields:{
				addr_type:'BLE address type reported by the dongle: normally 0 = public, 1 = random (static or private). It matters for GATT connections and whether OUI lookup is meaningful; it does not select the payload format or PHY.',
				configured:'Whether this MAC is present in the active gateway configuration. False does not mean unsupported or unpaired. A configured but disabled entry still counts as configured; a rotating private address may appear as a new MAC.',
				count:'Number of reports received for this MAC during the current Discovery session. It is not the sensor packet counter, and does not necessarily mean different measurements. Starting Discovery clears the observations.',
				data:'Entire received advertisement in hexadecimal, including AD length/type, flags and any name or service/manufacturer data. It is not JSON. The decoder extracts supported Service Data from it; it is not all sensor measurement bytes.',
				format:'Format detected from supported Service Data UUID/length. An empty string means no supported format was detected, not that reception failed. Detection alone does not prove successful decoding.',
				last_seen:'Gateway timestamp of the most recent report for this MAC, in ISO 8601 (Z = UTC). This is reception time, not a timestamp supplied by the sensor.',
				mac:'Advertiser address, displayed as 12 hexadecimal digits. It comes from radio metadata and may differ from a MAC inside the payload. Random/private addresses must not be treated as a manufacturer OUI.',
				name:'Local name announced by the device in AD type 0x08/0x09, when available. Discovery retains the last received name if a later packet has none. It is not the configured device label or proof of identity.',
				phy:'Radio transport: raw firmware PHY byte, primary PHY and secondary PHY when present. 1M and Coded describe radio reception, not a payload protocol; a Coded packet can carry BTHome v2.',
				rssi:'Received Signal Strength Indicator in dBm. A less negative value usually means a stronger received signal. It is not a reliable distance measurement and can vary with walls, antennas and interference.',
				vendor:'Offline IEEE OUI (Organizationally Unique Identifier) lookup of the advertiser MAC prefix: the address-block assignee, not necessarily the product brand. addr_type != 0 or bit 0x02 in the first MAC byte skips lookup and shows "Random / local address"; a locally administered address is not a universally assigned manufacturer address. "Unknown OUI" means no matching public prefix. This is separate from decoded.mac_vendor.',
				decode_status:'Inspect result: ok = decoded; unsupported_format = no supported Service Data; failed = decoding or the inspection request failed. Check decode_error: an expired web session is not evidence of a bad BLE packet.',
				decode_error:'Diagnostic from the decoder or the CGI/API request. Missing/wrong bindkeys and malformed packets differ from HTTP/session errors. "Invalid response or session expired" means the web response was not the expected API envelope: check login/session and server logs, then retry Inspect.',
				wire_format:'Format actually selected for Inspect, possibly overridden by the configured Forced wire format. It can differ from the automatically detected format. It does not encode 1M/Coded PHY.',
				measurements:'Normalized values extracted from the decoded structure, represented as strings (for example boolean 1/0 and formatted numbers). Publishing still depends on the configured device and Exposed attributes.',
				decoded:'Typed structure produced by the selected codec, with nested objects, numbers, booleans and units. Fields depend on the protocol; this is different from the original raw advertisement and from the codec schema.'
			},
			nested:'Field defined by the selected codec. Its meaning depends on the containing object and protocol; related *_unit fields describe units. Consult the codec schema for protocol-specific fields.',
			macVendor:'Computed vendor from the payload MAC, using the codec\'s small prefix table. It does not use addr_type or the complete Discovery OUI table; the payload MAC can differ from the advertiser MAC.',
			devInfo:'BTHome v2 device-information bits: version, encryption, trigger/event mode and reserved bits. These describe the payload, not the radio PHY.',
			packetId:'Counter supplied by the sensor/protocol for a packet. It can wrap; it is independent of Discovery count.',
			battery:'Battery voltage in volts. A companion battery_v_unit may be present; battery percentage is a different field.',
			rules:'Definitions of derived attributes (condition, optional timer or mirror). This daemon currently stores and validates rules but does not execute them.',
			ruleWarning:'Rules are saved and validated, but the current daemon does not evaluate them or run automations.',
			ruleDetails:'Name identifies the derived attribute; source is the input attribute; equals is the value to compare (empty means any change). A timer definition needs after_s > 0; mirror is the declared no-timer mode. These are definitions only in this version.',
			addRule:'Add an empty rule to this editing draft. Fill name/source and a positive delay or mirror before validation. This does not save, restart, program the sensor or activate an automation.',
			keep:'Validate this device and keep its changes in the page draft. Nothing is written to the saved configuration and the service is not restarted. Use Save configuration, then Restart service to apply supported settings.',
			cancel:'Discard edits made in this device dialog since opening it. Other unsaved page changes and the saved configuration remain unchanged.',
			filterTitle:'Advertisement MAC filters', include:'Include MACs/prefixes (whitelist)', exclude:'Exclude MACs/prefixes (blacklist)',
			filterCommon:'Fill only ONE list: include accepts matching addresses; exclude rejects matching addresses. Use one MAC or 1-6-byte prefix per line, or separate with spaces/commas. Examples: A4:C1:38 or A4C1383406CE. Maximum 64 entries in the effective firmware list. Save configuration, then Restart service to apply. Start configured scan resumes the configuration already loaded by the daemon; it does not reload saved edits.',
			filterKnown:'Registered-device filtering is ON: only enabled configured devices are eligible. Include further restricts them; exclude removes matches. With no eligible devices the scanner remains stopped.',
			filterAll:'Registered-device filtering is OFF: an include list restricts radio reports, an exclude list drops matches, and two empty lists admit all addresses. Receiving a device does not configure it or automatically publish its measurements.',
			filterConflict:'Both lists are populated. The firmware supports inclusion OR exclusion, not both: clear one list before saving.',
			filterList:'One MAC/prefix per line. Prefixes start at the first byte in displayed MAC order; no wildcard is needed. Leave the other list empty.',
			filterLink:'Configure advertisement filters', discoveryFilters:'Search/vendor/Unconfigured only filter this table, not the radio. Active Discovery temporarily bypasses configured MAC/address/duplicate filters and enables both PHYs; Stop or timeout restores the configured scanner.',
			sessionError:'Inspect did not receive the expected API response. Check the web login/session or CGI/server errors, reload if needed and retry Inspect. This does not establish that the received BLE packet is invalid.',
			decodeFailure:'Inspect failed. Read decode_error and its field help to distinguish codec/bindkey problems from a failed web request.',
			frontendMissing:'The daemon does not expose these frontend settings: {frontends}. Update/rebuild the daemon binary together with the CGI, then reload this page. This backend cannot configure the missing sections.'
		},
		de: {
			guide:'Hilfe zu Advertisement-Feldern', hint:'JSON-Feldnamen zeigen beim Darüberfahren Hilfe. Die aufklappbare Feldhilfe ist auch per Tastatur und Touch erreichbar; JSON bleibt schreibgeschützt und kopierbar.',
			fields:{
				addr_type:'Vom Dongle gemeldeter BLE-Adresstyp: normalerweise 0 = öffentlich, 1 = zufällig (statisch oder privat). Wichtig für GATT und OUI-Zuordnung, nicht für Datenformat oder PHY.',
				configured:'Ob diese MAC in der aktiven Gateway-Konfiguration steht. False bedeutet nicht unbekanntes Protokoll oder fehlendes Pairing. Auch deaktivierte Einträge zählen; wechselnde private Adressen können als neue MAC erscheinen.',
				count:'Anzahl empfangener Berichte dieser MAC in der aktuellen Discovery-Sitzung, nicht der Paketzähler des Sensors oder die Zahl verschiedener Messwerte. Ein neuer Discovery-Lauf leert die Beobachtungen.',
				data:'Vollständiges empfangenes Advertisement als Hex, einschließlich AD-Länge/Typ, Flags und Name, Service- oder Herstellerdaten. Kein JSON. Der Decoder entnimmt daraus unterstützte Service Data.',
				format:'Anhand unterstützter Service-Data-UUID/Länge erkanntes Format. Leer bedeutet kein erkanntes unterstütztes Format, nicht fehlenden Empfang. Erkennung garantiert keine erfolgreiche Dekodierung.',
				last_seen:'ISO-8601-Zeit des Gateways für den letzten Empfang dieser MAC (Z = UTC), kein vom Sensor gelieferter Messzeitpunkt.',
				mac:'Senderadresse als zwölf Hex-Ziffern aus den Funkmetadaten. Sie kann von einer MAC im Nutzinhalt abweichen. Zufällige/private Adressen sind keine verlässlichen Hersteller-OUIs.',
				name:'Vom Gerät in AD 0x08/0x09 angekündigter Name. Fehlt er in einem späteren Paket, bleibt der letzte Name erhalten. Kein konfigurierter Gerätename oder Identitätsnachweis.',
				phy:'Funktransport: rohes Firmware-PHY-Byte, primäre und gegebenenfalls sekundäre PHY. 1M/Coded sind keine Nutzdatenprotokolle; Coded kann BTHome v2 transportieren.',
				rssi:'Empfangsfeldstärke in dBm. Weniger negative Werte bedeuten meist stärkeren Empfang, aber keine zuverlässige Entfernung; Wände, Antennen und Störungen beeinflussen den Wert.',
				vendor:'Offline-IEEE-OUI-Zuordnung (Organizationally Unique Identifier) des MAC-Präfixes zum Adressblock-Inhaber, nicht zwingend zur Produktmarke. Bei addr_type != 0 oder Bit 0x02 im ersten MAC-Byte entfällt die Suche: "Random / local address". Lokal verwaltet bedeutet nicht universell vom Hersteller zugewiesen. "Unknown OUI" bedeutet kein passendes öffentliches Präfix. Unabhängig von decoded.mac_vendor.',
				decode_status:'Inspect-Ergebnis: ok = dekodiert; unsupported_format = keine unterstützten Service Data; failed = Dekodierung oder Webanfrage fehlgeschlagen. decode_error prüfen; eine abgelaufene Sitzung beweist kein defektes BLE-Paket.',
				decode_error:'Diagnose vom Decoder oder CGI/API. Bindkey-/Paketfehler von HTTP-/Sitzungsfehlern unterscheiden. "Invalid response or session expired" bedeutet eine unerwartete API-Antwort: Anmeldung/Sitzung und Serverprotokoll prüfen, Inspect erneut versuchen.',
				wire_format:'Tatsächlich für Inspect gewähltes Format, eventuell durch Forced wire format überschrieben. Kann von format abweichen; enthält keine 1M/Coded-PHY-Angabe.',
				measurements:'Normalisierte dekodierte Werte als Zeichenketten, z. B. 1/0 für Boolesche Werte und formatierte Zahlen. Veröffentlichung hängt von Gerät und Exposed attributes ab.',
				decoded:'Typisierte Struktur des Codecs mit Objekten, Zahlen, Booleschen Werten und Einheiten. Protokollabhängig und weder Roh-Advertisement noch Codec-Schema.'
			},
			nested:'Feld des gewählten Codecs; Bedeutung hängt von Objekt und Protokoll ab. Zugehörige *_unit-Felder geben Einheiten an. Protokollspezifische Details stehen im Codec-Schema.',
			macVendor:'Berechneter Anbieter anhand der Nutzdaten-MAC und einer kleinen Codec-Präfixtabelle. Nutzt weder addr_type noch die vollständige OUI-Tabelle; die Sender-MAC kann abweichen.',
			devInfo:'BTHome-v2-Informationsbits: Version, Verschlüsselung, Trigger-/Ereignismodus und reservierte Bits. Beschreiben Nutzdaten, nicht die Funk-PHY.',
			packetId:'Protokoll-/Sensor-Paketzähler, der überlaufen kann; unabhängig von Discovery count.',
			battery:'Batteriespannung in Volt, gegebenenfalls mit battery_v_unit. Batterieprozente sind ein anderes Feld.',
			rules:'Definitionen abgeleiteter Attribute mit Bedingung, Timer oder Spiegelung. Der Daemon speichert und prüft Regeln derzeit nur; er führt sie nicht aus.',
			ruleWarning:'Regeln werden gespeichert und geprüft, aber vom aktuellen Daemon nicht ausgewertet; es laufen keine Automationen.',
			ruleDetails:'Name benennt das abgeleitete Attribut, source das Eingangsattribut, equals den Vergleichswert (leer: jede Änderung). Timer benötigen after_s > 0; mirror bezeichnet den Modus ohne Timer. In dieser Version sind dies nur Definitionen.',
			addRule:'Leere Regel im Entwurf hinzufügen. Name/source und positive Verzögerung oder mirror vor der Prüfung ausfüllen. Speichert nicht, startet nichts neu und aktiviert keine Automation.',
			keep:'Gerät prüfen und Änderungen im Seitenentwurf behalten. Schreibt keine gespeicherte Konfiguration und startet den Dienst nicht neu. Danach Save configuration und Restart service verwenden.',
			cancel:'Änderungen dieses Gerätedialogs seit dem Öffnen verwerfen. Andere ungespeicherte Seitenänderungen und die gespeicherte Konfiguration bleiben erhalten.',
			filterTitle:'Advertisement-MAC-Filter', include:'MACs/Präfixe einschließen (whitelist)', exclude:'MACs/Präfixe ausschließen (blacklist)',
			filterCommon:'Nur EINE Liste ausfüllen: Einschließen erlaubt passende Adressen, Ausschließen verwirft sie. Eine MAC oder ein 1-6-Byte-Präfix je Zeile, alternativ mit Leerzeichen/Komma trennen. Beispiele: A4:C1:38 oder A4C1383406CE. Maximal 64 effektive Firmware-Einträge. Save configuration, dann Restart service. Start configured scan verwendet die bereits vom Daemon geladene Konfiguration und lädt gespeicherte Änderungen nicht neu.',
			filterKnown:'Filter auf registrierte Geräte EIN: Nur aktivierte konfigurierte Geräte kommen infrage. Einschließen schränkt weiter ein, Ausschließen entfernt Treffer. Ohne passende Geräte bleibt der Scanner aus.',
			filterAll:'Filter auf registrierte Geräte AUS: Einschließen begrenzt Funkberichte, Ausschließen entfernt Treffer; zwei leere Listen erlauben alle Adressen. Empfang konfiguriert kein Gerät und veröffentlicht nicht automatisch Messwerte.',
			filterConflict:'Beide Listen sind gefüllt. Die Firmware unterstützt Einschließen ODER Ausschließen: vor dem Speichern eine Liste leeren.',
			filterList:'Eine MAC/ein Präfix je Zeile, ab dem ersten Byte der angezeigten MAC. Kein Platzhalter nötig. Andere Liste leer lassen.',
			filterLink:'Advertisement-Filter konfigurieren', discoveryFilters:'Suche/Anbieter/Unconfigured only filtern nur die Tabelle. Aktive Discovery umgeht vorübergehend MAC-, Adress- und Duplikatfilter und aktiviert beide PHYs. Stop/Zeitablauf stellt den konfigurierten Scanner wieder her.',
			sessionError:'Inspect hat keine erwartete API-Antwort erhalten. Anmeldung/Sitzung oder CGI-/Serverfehler prüfen, gegebenenfalls neu laden und Inspect wiederholen. Kein Beweis für ein ungültiges BLE-Paket.',
			decodeFailure:'Inspect fehlgeschlagen. decode_error und die Feldhilfe unterscheiden Codec-/Bindkey-Probleme von fehlgeschlagenen Webanfragen.',
			frontendMissing:'Der Daemon bietet diese Frontend-Einstellungen nicht an: {frontends}. Daemon-Binärdatei zusammen mit dem CGI aktualisieren/neu bauen und die Seite neu laden. Dieses Backend kann die fehlenden Abschnitte nicht konfigurieren.'
		},
		it: {
			guide:'Guida ai campi dell’advertisement', hint:'Passa sulle chiavi JSON per la spiegazione. La guida espandibile è accessibile anche da tastiera e telefono; il JSON resta in sola lettura e copiabile.',
			fields:{
				addr_type:'Tipo di indirizzo BLE riportato dal dongle: normalmente 0 = pubblico, 1 = random (statico o privato). Serve per GATT e per stabilire se il lookup OUI è attendibile; non seleziona il formato del payload o la PHY.',
				configured:'Indica se questo MAC è nella configurazione attiva del gateway. False non significa protocollo non supportato o dispositivo non abbinato. Anche una voce disabilitata risulta configurata; un indirizzo privato che cambia può apparire come nuovo MAC.',
				count:'Numero di report ricevuti per questo MAC nella sessione Discovery corrente. Non è il contatore del sensore e non indica necessariamente misure diverse. Avviare Discovery azzera le osservazioni.',
				data:'Advertisement completo ricevuto, in esadecimale: comprende lunghezza/tipo AD, flag ed eventuali nome, Service Data o dati del produttore. Non è JSON. Il decoder estrae da qui i Service Data supportati; non sono tutti byte di misura.',
				format:'Formato rilevato tramite UUID/lunghezza dei Service Data supportati. Stringa vuota significa nessun formato supportato riconosciuto, non ricezione fallita. Il riconoscimento non garantisce la decodifica.',
				last_seen:'Timestamp ISO 8601 del gateway relativo all’ultimo report di questo MAC (Z = UTC). È l’ora di ricezione, non un timestamp della misura fornito dal sensore.',
				mac:'Indirizzo del trasmettitore, visualizzato con 12 cifre esadecimali. Arriva dai metadati radio e può differire dal MAC nel payload. Gli indirizzi random/privati non identificano attendibilmente il produttore tramite OUI.',
				name:'Nome locale annunciato dal dispositivo nei campi AD 0x08/0x09. Se un report successivo non lo contiene, Discovery conserva l’ultimo nome ricevuto. Non è l’etichetta configurata né una prova d’identità.',
				phy:'Trasporto radio: byte PHY grezzo del firmware, PHY primaria ed eventuale secondaria. 1M/Coded non sono protocolli del payload: un pacchetto Coded può contenere BTHome v2.',
				rssi:'Potenza del segnale ricevuto in dBm. Un valore meno negativo indica in genere un segnale più forte, ma non misura attendibilmente la distanza; varia con ostacoli, antenne e interferenze.',
				vendor:'Lookup IEEE OUI (Organizationally Unique Identifier) offline del prefisso MAC: identifica l’assegnatario del blocco, non necessariamente il marchio. Con addr_type != 0 o bit 0x02 del primo byte MAC, il lookup viene saltato: "Random / local address". Localmente amministrato significa non assegnato universalmente dal produttore. "Unknown OUI" indica un prefisso pubblico non trovato. È distinto da decoded.mac_vendor.',
				decode_status:'Esito di Inspect: ok = decodificato; unsupported_format = nessun Service Data supportato; failed = errore del decoder oppure della richiesta web. Leggere decode_error: una sessione scaduta non prova che il pacchetto BLE sia errato.',
				decode_error:'Diagnostica del decoder o della richiesta CGI/API. Chiave mancante/errata e pacchetto malformato sono diversi da errori HTTP/sessione. "Invalid response or session expired" indica una risposta web diversa dall’API attesa: controllare accesso/sessione e log del server, poi riprovare Inspect.',
				wire_format:'Formato effettivamente scelto per Inspect, eventualmente imposto da Forced wire format nella configurazione del dispositivo. Può differire da format rilevato automaticamente. Non descrive la PHY 1M/Coded.',
				measurements:'Valori normalizzati estratti dalla struttura decodificata, rappresentati come stringhe (ad esempio booleani 1/0 e numeri formattati). La pubblicazione dipende comunque dal dispositivo configurato e da Exposed attributes.',
				decoded:'Struttura tipizzata prodotta dal codec scelto, con oggetti annidati, numeri, booleani e unità. I campi dipendono dal protocollo: non è né l’advertisement grezzo né lo schema del codec.'
			},
			nested:'Campo definito dal codec selezionato. Il significato dipende dall’oggetto che lo contiene e dal protocollo; i campi *_unit indicano le unità. Per i campi specifici consultare lo schema del codec.',
			macVendor:'Vendor calcolato dal MAC nel payload tramite la piccola tabella di prefissi del codec. Non usa addr_type o l’intera tabella OUI di Discovery; il MAC del trasmettitore può essere diverso.',
			devInfo:'Bit informativi BTHome v2: versione, cifratura, modalità trigger/evento e bit riservati. Descrivono il payload, non la PHY radio.',
			packetId:'Contatore di pacchetto fornito dal sensore/protocollo; può ripartire da zero ed è indipendente da count di Discovery.',
			battery:'Tensione della batteria in volt, eventualmente accompagnata da battery_v_unit. La percentuale della batteria è un campo diverso.',
			rules:'Definizioni di attributi derivati con condizione, eventuale timer o mirror. Il daemon attuale le salva e valida, ma non le esegue.',
			ruleWarning:'Le regole vengono salvate e validate, ma il daemon attuale non le valuta e non esegue automazioni.',
			ruleDetails:'Name identifica l’attributo derivato; source è l’attributo in ingresso; equals è il valore da confrontare (vuoto: ogni cambiamento). Un timer richiede after_s > 0; mirror dichiara la modalità senza timer. In questa versione sono solo definizioni.',
			addRule:'Aggiunge una regola vuota alla bozza. Compilare name/source e un ritardo positivo oppure mirror prima della validazione. Non salva, non riavvia, non programma il sensore e non attiva automazioni.',
			keep:'Valida il dispositivo e conserva le modifiche nella bozza della pagina. Non scrive la configurazione salvata e non riavvia il servizio. Usare poi Save configuration e Restart service per applicare le impostazioni supportate.',
			cancel:'Scarta le modifiche fatte in questa finestra dispositivo dalla sua apertura. Le altre modifiche non salvate nella pagina e la configurazione su disco restano invariate.',
			filterTitle:'Filtri MAC degli advertisements', include:'Includi MAC/prefissi (whitelist)', exclude:'Escludi MAC/prefissi (blacklist)',
			filterCommon:'Compilare UNA sola lista: inclusione accetta gli indirizzi corrispondenti, esclusione li scarta. Un MAC o prefisso di 1-6 byte per riga, oppure separati da spazi/virgole. Esempi: A4:C1:38 oppure A4C1383406CE. Massimo 64 voci nella lista effettiva del firmware. Salvare, poi riavviare il servizio. Start configured scan riprende la configurazione già caricata dal daemon: non rilegge le modifiche salvate.',
			filterKnown:'Filtro sui dispositivi registrati ATTIVO: sono ammessi solo quelli configurati e abilitati. Inclusione li restringe ulteriormente; esclusione rimuove le corrispondenze. Senza dispositivi ammessi lo scanner resta fermo.',
			filterAll:'Filtro sui dispositivi registrati DISATTIVO: inclusione limita i report radio, esclusione scarta le corrispondenze; entrambe le liste vuote ammettono tutti gli indirizzi. Ricevere un dispositivo non lo configura e non ne pubblica automaticamente le misure.',
			filterConflict:'Entrambe le liste sono compilate. Il firmware supporta inclusione OPPURE esclusione, non entrambe: svuotare una lista prima di salvare.',
			filterList:'Un MAC/prefisso per riga, a partire dal primo byte del MAC visualizzato; non serve alcun carattere jolly. Lasciare vuota l’altra lista.',
			filterLink:'Configura filtri advertisements', discoveryFilters:'Ricerca/vendor/Unconfigured only filtrano solo la tabella, non la radio. Discovery attivo bypassa temporaneamente filtri MAC, indirizzi e duplicati e abilita entrambe le PHY; Stop o scadenza ripristinano lo scanner configurato.',
			sessionError:'Inspect non ha ricevuto la risposta API attesa. Controllare accesso/sessione web o errori CGI/server, ricaricare se necessario e riprovare Inspect. Questo non dimostra che il pacchetto BLE ricevuto sia invalido.',
			decodeFailure:'Inspect non riuscito. Leggere decode_error e la relativa guida per distinguere problemi di codec/bindkey da una richiesta web fallita.',
			frontendMissing:'Il daemon non espone le configurazioni di questi frontend: {frontends}. Aggiorna/ricompila il binario del daemon insieme al CGI, poi ricarica la pagina. Questo backend non può configurare le sezioni mancanti.'
		},
		fr: {
			guide:'Guide des champs advertisement', hint:'Survolez une clé JSON pour son explication. Le guide déroulant reste accessible au clavier et au toucher ; le JSON est en lecture seule et copiable.',
			fields:{
				addr_type:'Type d’adresse BLE fourni par le dongle : normalement 0 = publique, 1 = aléatoire (statique ou privée). Utile pour GATT et la fiabilité du lookup OUI, pas pour choisir le protocole ou le PHY.',
				configured:'Indique si cette MAC figure dans la configuration active. False ne signifie ni protocole inconnu ni absence d’appairage. Une entrée désactivée compte aussi ; une adresse privée changeante peut apparaître comme nouvelle MAC.',
				count:'Nombre de rapports reçus pour cette MAC pendant la session Discovery actuelle, pas le compteur du capteur ni forcément des mesures distinctes. Un nouveau Discovery efface les observations.',
				data:'Advertisement reçu complet en hexadécimal, avec longueur/type AD, indicateurs, nom et éventuelles données de service/fabricant. Ce n’est pas du JSON. Le décodeur en extrait les Service Data supportées.',
				format:'Format détecté par UUID/longueur des Service Data supportées. Vide signifie aucun format supporté reconnu, pas un échec de réception. La détection ne garantit pas le décodage.',
				last_seen:'Heure ISO 8601 du dernier rapport reçue par la passerelle pour cette MAC (Z = UTC), et non l’heure de mesure fournie par le capteur.',
				mac:'Adresse de l’émetteur sur 12 chiffres hexadécimaux, issue des métadonnées radio. Peut différer de la MAC du payload. Les adresses privées/aléatoires ne permettent pas une identification OUI fiable.',
				name:'Nom local annoncé dans les champs AD 0x08/0x09. Le dernier nom reste affiché si un paquet suivant n’en contient pas. Ce n’est ni le nom configuré ni une preuve d’identité.',
				phy:'Transport radio : octet PHY brut, PHY primaire et secondaire éventuel. 1M/Coded ne sont pas des protocoles de payload ; Coded peut transporter BTHome v2.',
				rssi:'Puissance reçue en dBm. Une valeur moins négative indique généralement un signal plus fort, pas une distance fiable ; obstacles, antennes et interférences modifient la mesure.',
				vendor:'Recherche IEEE OUI (Organizationally Unique Identifier) hors ligne du préfixe MAC : titulaire du bloc, pas forcément la marque. Si addr_type != 0 ou le bit 0x02 du premier octet MAC est actif, la recherche est ignorée : "Random / local address". Une adresse administrée localement n’est pas universellement attribuée par le fabricant. "Unknown OUI" signifie aucun préfixe public correspondant. Distinct de decoded.mac_vendor.',
				decode_status:'Résultat Inspect : ok = décodé ; unsupported_format = aucune Service Data supportée ; failed = échec du décodeur ou de la requête web. Lire decode_error ; une session expirée ne prouve pas un paquet BLE incorrect.',
				decode_error:'Diagnostic du décodeur ou de CGI/API. Distinguer bindkey/paquet incorrect d’un problème HTTP/session. "Invalid response or session expired" signifie une réponse API inattendue : vérifier connexion/session et journaux serveur, puis relancer Inspect.',
				wire_format:'Format réellement choisi pour Inspect, éventuellement imposé par Forced wire format. Peut différer du format détecté ; ne décrit pas le PHY 1M/Coded.',
				measurements:'Valeurs normalisées extraites du décodage sous forme de chaînes, par exemple 1/0 et nombres formatés. Leur publication dépend du périphérique configuré et de Exposed attributes.',
				decoded:'Structure typée du codec avec objets, nombres, booléens et unités. Les champs dépendent du protocole ; ce n’est ni le paquet brut ni le schéma du codec.'
			},
			nested:'Champ du codec choisi, dont le sens dépend de l’objet et du protocole. Les champs *_unit donnent les unités ; voir le schéma pour les détails spécifiques.',
			macVendor:'Fabricant calculé depuis la MAC du payload avec une petite table du codec. N’utilise ni addr_type ni la table OUI complète ; la MAC radio peut différer.',
			devInfo:'Bits BTHome v2 : version, chiffrement, mode événement/trigger et réserves. Décrivent le payload, pas le PHY radio.',
			packetId:'Compteur de paquet du capteur/protocole, pouvant reboucler ; indépendant de count de Discovery.',
			battery:'Tension de batterie en volts, éventuellement avec battery_v_unit. Le pourcentage est un autre champ.',
			rules:'Définitions d’attributs dérivés avec condition, temporisation ou miroir. Le daemon les enregistre et valide seulement ; il ne les exécute pas.',
			ruleWarning:'Les règles sont enregistrées et validées mais le daemon actuel ne les évalue pas et ne lance aucune automatisation.',
			ruleDetails:'Name nomme l’attribut dérivé, source l’entrée, equals la valeur comparée (vide : tout changement). Une temporisation exige after_s > 0 ; mirror déclare le mode sans délai. Seulement des définitions dans cette version.',
			addRule:'Ajouter une règle vide au brouillon. Renseigner name/source et un délai positif ou mirror avant validation. Ne sauvegarde pas, ne redémarre pas et n’active aucune automatisation.',
			keep:'Valider le périphérique et conserver ses changements dans le brouillon de la page. N’écrit pas la configuration sauvegardée et ne redémarre pas. Utiliser ensuite Save configuration puis Restart service.',
			cancel:'Abandonner les modifications de ce dialogue depuis son ouverture. Les autres changements de page et la configuration sauvegardée restent intacts.',
			filterTitle:'Filtres MAC des advertisements', include:'Inclure MAC/préfixes (whitelist)', exclude:'Exclure MAC/préfixes (blacklist)',
			filterCommon:'Remplir UNE seule liste : inclusion accepte les correspondances, exclusion les rejette. Une MAC ou un préfixe de 1-6 octets par ligne, ou séparés par espaces/virgules. Exemples : A4:C1:38 ou A4C1383406CE. Maximum 64 entrées effectives. Sauvegarder puis redémarrer le service. Start configured scan utilise la configuration déjà chargée par le daemon sans relire les modifications enregistrées.',
			filterKnown:'Filtrage des périphériques enregistrés ACTIF : seuls les périphériques configurés et activés sont admis. Inclusion restreint encore, exclusion retire les correspondances. Sans périphérique admissible, le scanner reste arrêté.',
			filterAll:'Filtrage des périphériques enregistrés INACTIF : inclusion limite les rapports, exclusion rejette les correspondances ; deux listes vides acceptent toutes les adresses. Recevoir un périphérique ne le configure ni ne publie ses mesures.',
			filterConflict:'Les deux listes sont remplies. Le firmware permet inclusion OU exclusion : vider une liste avant sauvegarde.',
			filterList:'Une MAC/un préfixe par ligne, depuis le premier octet de la MAC affichée ; aucun joker nécessaire. Laisser l’autre liste vide.',
			filterLink:'Configurer les filtres advertisements', discoveryFilters:'Recherche/fabricant/Unconfigured only filtrent uniquement le tableau. Discovery contourne temporairement les filtres MAC/adresses/doublons et active les deux PHY ; Stop ou expiration restaure le scanner configuré.',
			sessionError:'Inspect n’a pas reçu la réponse API attendue. Vérifier connexion/session ou erreurs CGI/serveur, recharger si nécessaire et réessayer. Cela ne prouve pas un paquet BLE invalide.',
			decodeFailure:'Échec Inspect. Lire decode_error et son aide pour distinguer codec/bindkey d’une requête web échouée.',
			frontendMissing:'Le daemon n’expose pas les paramètres de ces frontends : {frontends}. Mettre à jour/recompiler le binaire du daemon avec le CGI, puis recharger la page. Ce backend ne peut pas configurer les sections manquantes.'
		},
		es: {
			guide:'Guía de campos del advertisement', hint:'Pase sobre una clave JSON para ver su explicación. La guía desplegable funciona con teclado y pantalla táctil; el JSON sigue siendo de solo lectura y se puede copiar.',
			fields:{
				addr_type:'Tipo de dirección BLE recibido del dongle: normalmente 0 = pública, 1 = aleatoria (estática o privada). Importa para GATT y la fiabilidad del OUI, no para elegir protocolo o PHY.',
				configured:'Indica si esta MAC figura en la configuración activa. False no significa protocolo no compatible ni ausencia de emparejamiento. Una entrada desactivada también cuenta; una dirección privada cambiante puede aparecer como nueva MAC.',
				count:'Número de informes de esta MAC en la sesión Discovery actual, no el contador del sensor ni necesariamente medidas distintas. Iniciar Discovery borra las observaciones.',
				data:'Advertisement recibido completo en hexadecimal, con longitud/tipo AD, indicadores, nombre y posibles datos de servicio/fabricante. No es JSON. El decoder extrae los Service Data compatibles.',
				format:'Formato detectado mediante UUID/longitud de los Service Data compatibles. Vacío significa ningún formato compatible reconocido, no fallo de recepción. Detectar no garantiza decodificar.',
				last_seen:'Hora ISO 8601 del gateway para el último informe de esta MAC (Z = UTC), no una hora de medida enviada por el sensor.',
				mac:'Dirección del anunciante en 12 dígitos hexadecimales, procedente de metadatos radio. Puede diferir de la MAC del payload. Las direcciones privadas/aleatorias no identifican fiablemente al fabricante mediante OUI.',
				name:'Nombre local anunciado en AD 0x08/0x09. Discovery conserva el último nombre si otro paquete no lo contiene. No es la etiqueta configurada ni una prueba de identidad.',
				phy:'Transporte radio: byte PHY bruto, PHY primaria y secundaria si existe. 1M/Coded no son protocolos del payload; Coded puede transportar BTHome v2.',
				rssi:'Potencia recibida en dBm. Menos negativo suele indicar mayor señal, pero no una distancia fiable; obstáculos, antenas e interferencias afectan al valor.',
				vendor:'Consulta IEEE OUI (Organizationally Unique Identifier) sin conexión del prefijo MAC: titular del bloque, no necesariamente la marca. Con addr_type != 0 o bit 0x02 en el primer byte MAC se omite la consulta: "Random / local address". Una dirección administrada localmente no está asignada universalmente por el fabricante. "Unknown OUI" significa ningún prefijo público coincidente. Distinto de decoded.mac_vendor.',
				decode_status:'Resultado Inspect: ok = decodificado; unsupported_format = ningún Service Data compatible; failed = fallo del decoder o de la petición web. Leer decode_error; una sesión caducada no demuestra un paquete BLE erróneo.',
				decode_error:'Diagnóstico del decoder o CGI/API. Distinguir problemas de bindkey/paquete de errores HTTP/sesión. "Invalid response or session expired" indica una respuesta API inesperada: revisar acceso/sesión y registros del servidor, después repetir Inspect.',
				wire_format:'Formato realmente seleccionado para Inspect, quizá impuesto por Forced wire format. Puede diferir del formato detectado; no describe la PHY 1M/Coded.',
				measurements:'Valores normalizados extraídos del decoder como cadenas, por ejemplo booleanos 1/0 y números formateados. Publicar depende del dispositivo configurado y de Exposed attributes.',
				decoded:'Estructura tipada del codec con objetos, números, booleanos y unidades. Los campos dependen del protocolo; no es el advertisement bruto ni el esquema del codec.'
			},
			nested:'Campo del codec seleccionado; su significado depende del objeto y protocolo. Los campos *_unit indican unidades; consultar el esquema para detalles específicos.',
			macVendor:'Fabricante calculado desde la MAC del payload con la pequeña tabla del codec. No usa addr_type ni la tabla OUI completa; la MAC radio puede diferir.',
			devInfo:'Bits BTHome v2: versión, cifrado, modo trigger/evento y reservados. Describen el payload, no la PHY radio.',
			packetId:'Contador de paquete del sensor/protocolo, que puede volver a cero; independiente de count de Discovery.',
			battery:'Tensión de batería en voltios, quizá con battery_v_unit. El porcentaje es otro campo.',
			rules:'Definiciones de atributos derivados con condición, temporizador o espejo. El daemon actual solo las guarda y valida; no las ejecuta.',
			ruleWarning:'Las reglas se guardan y validan, pero el daemon actual no las evalúa ni ejecuta automatizaciones.',
			ruleDetails:'Name identifica el atributo derivado, source la entrada y equals el valor comparado (vacío: cualquier cambio). Un temporizador requiere after_s > 0; mirror declara el modo sin temporizador. Solo son definiciones en esta versión.',
			addRule:'Añadir una regla vacía al borrador. Completar name/source y un retardo positivo o mirror antes de validar. No guarda, reinicia, programa el sensor ni activa automatizaciones.',
			keep:'Validar el dispositivo y conservar los cambios en el borrador de la página. No escribe la configuración guardada ni reinicia el servicio. Usar después Save configuration y Restart service.',
			cancel:'Descartar los cambios de este diálogo desde su apertura. Los demás cambios de página y la configuración guardada no cambian.',
			filterTitle:'Filtros MAC de advertisements', include:'Incluir MAC/prefijos (whitelist)', exclude:'Excluir MAC/prefijos (blacklist)',
			filterCommon:'Rellenar UNA sola lista: inclusión acepta coincidencias, exclusión las descarta. Una MAC o prefijo de 1-6 bytes por línea, o separados por espacios/comas. Ejemplos: A4:C1:38 o A4C1383406CE. Máximo 64 entradas efectivas. Guardar y reiniciar el servicio. Start configured scan usa la configuración ya cargada por el daemon, sin releer los cambios guardados.',
			filterKnown:'Filtro de dispositivos registrados ACTIVO: solo se admiten los configurados y habilitados. Inclusión restringe más; exclusión elimina coincidencias. Sin dispositivos admitidos, el escáner permanece detenido.',
			filterAll:'Filtro de dispositivos registrados INACTIVO: inclusión limita informes, exclusión descarta coincidencias; ambas listas vacías admiten todas las direcciones. Recibir un dispositivo no lo configura ni publica sus medidas automáticamente.',
			filterConflict:'Ambas listas contienen datos. El firmware admite inclusión O exclusión: vaciar una antes de guardar.',
			filterList:'Una MAC/prefijo por línea, desde el primer byte de la MAC mostrada; no requiere comodines. Dejar vacía la otra lista.',
			filterLink:'Configurar filtros advertisements', discoveryFilters:'Búsqueda/fabricante/Unconfigured only solo filtran la tabla. Discovery omite temporalmente filtros MAC/direcciones/duplicados y activa ambas PHY; Stop o fin del tiempo restaura el escáner configurado.',
			sessionError:'Inspect no recibió la respuesta API esperada. Revisar acceso/sesión o errores CGI/servidor, recargar si hace falta y repetir. Esto no demuestra que el paquete BLE sea inválido.',
			decodeFailure:'Inspect falló. Leer decode_error y su ayuda para distinguir codec/bindkey de una petición web fallida.',
			frontendMissing:'El daemon no expone la configuración de estos frontends: {frontends}. Actualice/recompile el binario del daemon junto con el CGI y recargue la página. Este backend no puede configurar las secciones que faltan.'
		}
	};
	const helpLanguage=(navigator.language||'en').split('-')[0];
	const ht=helpTranslations[helpLanguage]||helpTranslations.en;
	function setYaml(text) {yamlText=text;if(yamlEditor){syncingYaml=true;yamlEditor.setValue(text,-1);syncingYaml=false;}}
	function getYaml() {return yamlEditor?yamlEditor.getValue():yamlText;}
	function loadScript(source) {return new Promise((resolve,reject)=>{const script=document.createElement('script');script.src=source;script.onload=resolve;script.onerror=()=>reject(new Error('Cannot load editor asset: '+source));document.head.append(script);});}
	function ensureAce() {
		if(window.ace)return Promise.resolve();
		if(!aceLoading)aceLoading=loadScript('/ace/ace.js').catch(error=>{aceLoading=null;throw error;});
		return aceLoading;
	}
	async function ensureYamlEditor() {
		if(yamlEditor)return;
		await ensureAce();
		ace.config.setModuleUrl('ace/mode/yaml','/ble2uart_gateway/mode-yaml.js');
		await loadScript('/ble2uart_gateway/mode-yaml.js');
		yamlEditor=ace.edit('bbYaml');yamlEditor.session.setUseWorker(false);yamlEditor.session.setMode('ace/mode/yaml');yamlEditor.setTheme('ace/theme/textmate');
		yamlEditor.setOptions({fontSize:'12px',showPrintMargin:false,wrap:true,tabSize:2,useSoftTabs:true});
		setYaml(yamlText);yamlEditor.session.on('change',()=>{if(!syncingYaml){rawDirty=true;changed();}});
	}
	function setPacket(value) {
		hidePacketTooltip();
		packetText=JSON.stringify(value,null,2);
		packetKeys=packetText.split('\n').map(line=>{
			const match=/^(\s*)"((?:\\.|[^"\\])*)"\s*:/.exec(line);
			if(!match)return null;
			const key=JSON.parse('"'+match[2]+'"');
			return {key,start:match[1].length,end:match[1].length+match[2].length+2,root:match[1].length===2};
		});
		const failed=value.decode_status==='failed';
		element('bbPacketNotice').hidden=!failed;
		element('bbPacketNotice').textContent=failed?(['Invalid response or session expired','Invalid API response'].includes(value.decode_error)?ht.sessionError:ht.decodeFailure):'';
		if(packetEditor){packetEditor.setValue(packetText,-1);packetEditor.resize(true);}
		else element('bbPacket').textContent=packetText;
	}
	function hidePacketTooltip(){element('bbFieldTooltip').hidden=true;}
	function packetExplanation(field) {
		if(field.root)return typeof ht.fields[field.key]==='string'?ht.fields[field.key]:ht.nested;
		if(['DevInfo','Encryption','Reserved1','Reserved2','Trigger','Version'].includes(field.key))return ht.devInfo;
		const explanation=({mac_vendor:ht.macVendor,packet_id:ht.packetId,battery_v:ht.battery})[field.key];
		return typeof explanation==='string'?explanation:ht.nested;
	}
	function packetHover(event) {
		if(!packetEditor){hidePacketTooltip();return;}
		const position=packetEditor.renderer.screenToTextCoordinates(event.clientX,event.clientY);
		const field=packetKeys[position.row];
		if(!field||position.column<field.start||position.column>=field.end){hidePacketTooltip();return;}
		const tooltip=element('bbFieldTooltip');
		tooltip.querySelector('strong').textContent=field.key;
		tooltip.querySelector('span').textContent=packetExplanation(field);
		tooltip.hidden=false;
		const bounds=tooltip.getBoundingClientRect();
		tooltip.style.left=Math.max(8,Math.min(event.clientX+12,innerWidth-bounds.width-8))+'px';
		tooltip.style.top=Math.max(8,event.clientY+bounds.height+18<innerHeight?event.clientY+18:event.clientY-bounds.height-12)+'px';
	}
	function ensurePacketEditor() {
		if(!packetEditorLoading)packetEditorLoading=(async()=>{
			await ensureAce();
			ace.config.setModuleUrl('ace/mode/json','/ace/mode-json.js');
			await loadScript('/ace/mode-json.js');
			packetEditor=ace.edit('bbPacket');packetEditor.session.setUseWorker(false);packetEditor.session.setMode('ace/mode/json');packetEditor.setTheme('ace/theme/textmate');
			packetEditor.setOptions({fontSize:'12px',showPrintMargin:false,wrap:true,tabSize:2,useSoftTabs:true,readOnly:true,highlightActiveLine:false,highlightGutterLine:false});
			packetEditor.setValue(packetText,-1);packetEditor.resize(true);
			element('bbPacket').addEventListener('mousemove',packetHover);
			element('bbPacket').addEventListener('mouseleave',hidePacketTooltip);
		})().catch(error=>{packetEditorLoading=null;throw error;});
		return packetEditorLoading;
	}
	element('bbPacketDetails').addEventListener('toggle',()=>{hidePacketTooltip();if(element('bbPacketDetails').open&&packetEditor)packetEditor.resize(true);});
	element('bbPacketHelp').addEventListener('toggle',hidePacketTooltip);
	const labels = {filter_known_devices:'Filter registered devices in ESP32', phy_1m:'1M PHY', phy_coded:'Coded PHY', dup_filter:'Duplicate filter', discard_random:'Discard random addresses', discard_rpa:'Discard resolvable private addresses', active_scan:'Active scan', window_1m:'1M window (0.625 ms units)', window_coded:'Coded window (0.625 ms units)', whitelist:'Whitelist MAC prefixes', blacklist:'Blacklist MAC prefixes', reset_on_open:'Reset ESP32 on open', command_timeout_ms:'Command timeout (ms)', reconnect_delay_ms:'Reconnect delay (ms)', bindkey:'Bindkey (32 hexadecimal digits)', format:'Forced wire format (empty = automatic)', expose:'Exposed attributes', child:'MySensors child ID', node_id_base:'First MySensors node ID', tx_hex:'Raw TX trace', rx_hex:'Raw RX trace', decode:'Codec decode trace', phy:'PHY reception / decode trace', after_s:'Delay (seconds)', kind:'Kind override', mysensors:'MySensors / Domoticz', mqtt:'MQTT', matter:'Matter', influx:'InfluxDB 3', advertise:'Advertise via DNS-SD', mdns_backend:'DNS-SD backend', mdns_hostname:'mDNS host name (empty = default)', mdns_interface:'mDNS interface (empty = automatic)', endpoint:'Endpoint URL', batch_size:'Batch size', queue_capacity:'Queue capacity', flush_interval_ms:'Flush interval (ms)', timeout_ms:'Timeout (ms)', diagnostics:'Diagnostics', rules:'Rules', serial:'Serial', scanner:'Scanner', log_level:'Log level', frontends:'Frontends', mac:'MAC', rssi:'RSSI'};
	Object.assign(labels, {manufacturer:'Manufacturer',model:'Device model',firmware_version:'Device firmware version',label:'Device name',sqlite:'SQLite',path:'Database file (absolute local path)',busy_timeout_ms:'SQLite busy timeout (ms)'});
	const title = key => key==='whitelist'?ht.include:key==='blacklist'?ht.exclude:labels[key] || key.replace(/_/g, ' ').replace(/^./, letter => letter.toUpperCase());
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
	function ruleHelp() {
		const fragment=document.createDocumentFragment();
		const warning=document.createElement('p');warning.className='bbHint';warning.textContent=ht.ruleWarning;
		const details=document.createElement('details');details.className='bbHelp';
		const summary=document.createElement('summary');summary.textContent='Rules — ?';
		const note=document.createElement('p');note.textContent=ht.ruleDetails;
		details.append(summary,note);fragment.append(warning,details);return fragment;
	}
	function scannerHelp(parent) {
		const section=document.createElement('div');section.id='bbMacFilters';section.tabIndex=-1;
		const heading=document.createElement('h4');heading.textContent=ht.filterTitle;
		const common=document.createElement('p');common.id='bbFilterCommon';common.className='bbHint';common.textContent=ht.filterCommon+' '+ht.filterList;
		const status=document.createElement('p');status.id='bbFilterState';status.className='bbHint';status.setAttribute('role','status');status.setAttribute('aria-live','polite');
		const registered=document.createElement('div');registered.id='bbRegisteredFilter';
		const lists=document.createElement('div');lists.id='bbMacFilterLists';lists.className='bbGrid';
		section.append(heading,common,status,registered,lists);parent.append(section);
	}
	function refreshFilterHelp() {
		const status=element('bbFilterState');if(!status||!config)return;
		const scanner=config.scanner, conflict=scanner.whitelist.length>0&&scanner.blacklist.length>0;
		status.classList.toggle('bbError',conflict);
		const text=conflict?ht.filterConflict:scanner.filter_known_devices?ht.filterKnown:ht.filterAll;
		if(status.textContent!==text)status.textContent=text;
	}
	function fields(parent, object, onChange, scope='') {
		const grid = document.createElement('div'); grid.className = 'bbGrid'; parent.append(grid);
		Object.keys(object).forEach(key => {
			const value = object[key];
			if (Array.isArray(value) && ['whitelist','blacklist'].includes(key)) {
				const label = document.createElement('label'); label.className = 'bbField'; label.append(title(key));
				const input = document.createElement('textarea'); input.rows = 3; input.value = value.join('\n'); input.title=ht.filterList;input.id=key==='whitelist'?'bbWhitelist':'bbBlacklist';input.placeholder='A4:C1:38\nA4C1383406CE';input.setAttribute('aria-describedby','bbFilterCommon bbFilterState');input.oninput = () => {object[key] = input.value.split(/[\s,]+/).filter(Boolean); onChange();}; label.append(input);
				const lists=scope==='scanner'?parent.querySelector('#bbMacFilterLists'):null;
				if(lists){if(key==='whitelist')lists.prepend(label);else lists.append(label);}else grid.append(label);
			} else if (Array.isArray(value)) {
				const group = document.createElement('fieldset'); group.className = 'bbGroup'; const legend = document.createElement('legend'); legend.textContent = title(key); if(key==='rules'){legend.title=ht.rules;legend.tabIndex=0;}group.append(legend); parent.append(group);
				const render = () => {
					group.replaceChildren(legend);
					if(key==='rules')group.append(ruleHelp());
					value.forEach((item, index) => {
						const row = document.createElement('div'); row.className = 'bbItem';
						row.append(button('Remove ' + (index + 1), () => {value.splice(index,1); render(); onChange();}));
						fields(row, item, onChange,scope+'.'+key+'[]'); group.append(row);
					});
					group.append(button('Add ' + (key === 'expose' ? 'attribute' : 'rule'), () => {value.push(key === 'expose' ? {attribute:'', child:null, kind:null} : {name:'',label:'',source:'',equals:'',after_s:0,mirror:false}); render(); onChange();},key==='rules'?ht.addRule:undefined));
				}; render();
			} else if (value && typeof value === 'object') {
				const group = document.createElement('fieldset'); group.className = 'bbGroup'; const legend = document.createElement('legend'); legend.textContent = title(key); group.append(legend);if(key==='scanner')scannerHelp(group);
				if(key==='frontends'){
					group.id='bbFrontends';
					const missing=['mysensors','mqtt','matter','influx','sqlite'].filter(name=>!Object.prototype.hasOwnProperty.call(value,name));
					if(missing.length){const warning=document.createElement('p');warning.id='bbFrontendNotice';warning.className='bbError';warning.setAttribute('role','alert');warning.textContent=ht.frontendMissing.replace('{frontends}',missing.map(title).join(', '));group.append(warning);}
				}
				if(scope==='frontends')group.dataset.frontend=key;
				fields(group, value, onChange,scope?scope+'.'+key:key); parent.append(group);
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
				if(scope==='scanner'&&key==='filter_known_devices'){input.title=ht.filterKnown+' '+ht.filterAll;input.setAttribute('aria-describedby','bbFilterCommon bbFilterState');}
				input.oninput = () => {object[key] = input.type === 'checkbox' ? input.checked : input.type === 'number' ? (input.value === '' ? null : Number(input.value)) : input.value; onChange();};
				if(input.type==='password') {
					const secret=document.createElement('div');secret.className='bbSecret';const name=key==='bindkey'?'bindkey':title(key).toLowerCase();
					const reveal=button('Show',event=>{event.preventDefault();const visible=input.type==='password';input.type=visible?'text':'password';reveal.textContent=visible?'Hide':'Show';reveal.setAttribute('aria-pressed',String(visible));reveal.setAttribute('aria-label',(visible?'Hide ':'Show ')+name);},'Show or hide '+name);
					reveal.setAttribute('aria-pressed','false');reveal.setAttribute('aria-label','Show '+name);secret.append(input,reveal);label.append(secret);
				} else {label.append(input);}
				if(scope==='scanner'&&key==='filter_known_devices')parent.querySelector('#bbRegisteredFilter').append(label);else grid.append(label);
			}
		});
	}
	function renderSettings() {
		const parent = element('bbSettings'); parent.replaceChildren();
		const editable = Object.fromEntries(Object.entries(config).filter(([key]) => !['devices','version'].includes(key)));
		fields(parent, editable, () => {Object.assign(config,editable); changed();refreshFilterHelp();});refreshFilterHelp();
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
		element('bbPacketDetails').open=true;element('bbPacketError').hidden=true;setPacket({...device,decode_status:'decoding'});
		ensurePacketEditor().catch(error=>{if(sequence===inspectionSequence){element('bbPacketError').textContent=error.message;element('bbPacketError').hidden=false;}});
		const configured=config.devices.find(known=>normalize(known.mac)===device.mac);
		try {
			const decoded=await api('inspect',{observation:device,device:configured});
			if(sequence===inspectionSequence)setPacket({...device,decode_status:decoded.decode_status,wire_format:decoded.wire_format,measurements:decoded.measurements,decoded:decoded.decoded,decode_error:decoded.error});
		} catch(error) {if(sequence===inspectionSequence)setPacket({...device,decode_status:'failed',decode_error:error.message});}
	}
	async function poll() {
		if(polling||!config)return; polling=true;
		try {const status=await api('status');observations=status.devices;element('bbStart').disabled=status.active||!status.connected;element('bbStop').disabled=!status.active;element('bbDiscoveryStatus').textContent=(status.active?'Scanning, '+status.remaining_s+' s remaining':status.connected?'Idle':'Serial unavailable')+' | '+observations.length+' devices | '+status.reports+' reports'+(status.overflow?' | table limit reached':'')+(status.error?' | '+status.error:'');renderFound();}
		catch(error){element('bbDiscoveryStatus').textContent=error.message;element('bbStop').disabled=true;}
		finally{polling=false;}
	}
	async function switchTab(next) {
		if(!config||next===tab)return;
		hidePacketTooltip();
		if(tab==='yaml'&&rawDirty){const result=await api('check',{yaml:getYaml()});config=result.config;rawDirty=false;renderSettings();renderDevices();}
		if(next==='yaml'){const result=await api('check',{config});setYaml(result.yaml);rawDirty=false;await ensureYamlEditor();}
		tab=next;app.querySelectorAll('[data-panel]').forEach(panel=>panel.hidden=panel.dataset.panel!==tab);app.querySelectorAll('[data-tab]').forEach(control=>control.setAttribute('aria-selected',String(control.dataset.tab===tab)));if(tab==='discovery')poll();
		if(tab==='yaml')yamlEditor.resize(true);
		if(tab==='discovery'&&packetEditor)packetEditor.resize(true);
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
	element('bbDeviceApply').title=ht.keep;element('bbDeviceCancel').title=ht.cancel;
	element('bbKeepHelp').textContent='Keep changes: '+ht.keep;element('bbCancelHelp').textContent='Cancel: '+ht.cancel;
	element('bbPacketHint').textContent=ht.hint;element('bbPacketHelpTitle').textContent=ht.guide;
	Object.entries(ht.fields).forEach(([key,text])=>{const term=document.createElement('dt');term.textContent=key;term.dataset.field=key;const description=document.createElement('dd');description.textContent=text;element('bbPacketFields').append(term,description);});
	element('bbDiscoveryFilterNote').textContent=ht.discoveryFilters;element('bbOpenFilters').textContent=ht.filterLink;
	element('bbOpenFilters').onclick=()=>run(async()=>{await switchTab('settings');const section=element('bbMacFilters');section.scrollIntoView({block:'start'});section.focus({preventScroll:true});});
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
	window.addEventListener('keydown',event=>{if(event.key==='Escape')hidePacketTooltip();});
	window.addEventListener('scroll',hidePacketTooltip,true);window.addEventListener('resize',hidePacketTooltip);window.addEventListener('blur',hidePacketTooltip);
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
