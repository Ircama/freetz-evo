#!/bin/sh

. /usr/lib/libmodcgi.sh

# The freetz image build replaces every $(lang de:"..." en:"...") with the
# configured language (modlangsubst). When this CGI is hot-patched instead, or
# the image was built without FREETZ_LANG_XX, the stock /bin/lang helper only
# prints "*** error: language not set ***". Shadow it with an equivalent that
# follows the browser language, then MOD_LANG (modconf), then English.
BB_CGI_LANG=$(printf '%s' "${HTTP_ACCEPT_LANGUAGE:-}" | sed -n 's/^\([a-zA-Z]\{2\}\).*/\1/p' | tr 'A-Z' 'a-z')
[ -n "$BB_CGI_LANG" ] || BB_CGI_LANG=$(modconf value MOD_LANG mod 2>/dev/null)
lang() {
	for bb_lng in ${BB_CGI_LANG:-en} it en de; do
		for bb_par in "$@"; do
			bb_ret=$(printf '%s' "$bb_par" | sed -n "s/^$bb_lng://p")
			[ -n "$bb_ret" ] && printf '%s' "$bb_ret" && return 0
		done
	done
	return 0
}

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
		if [ "$REQUEST_METHOD" != POST ] && [ "$ACTION" != read ] && [ "$ACTION" != status ] && [ "$ACTION" != attributes ] && [ "$ACTION" != history-presets ] && [ "$ACTION" != availability-presets ] && [ "$ACTION" != availability-status ]; then
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
			read|backups|attributes|history-presets|availability-presets|availability-status) "$DAEMON_BIN" --config "$YAML" --web-config "$ACTION" ;;
			check|save|restore|inspect|availability-test|log)
				case "$CONTENT_LENGTH" in ''|*[!0-9]*) echo '{"success":false,"error":"invalid request length"}'; return ;; esac
				if [ "$CONTENT_LENGTH" -gt 262144 ] || [ "$CONTENT_TYPE" != application/json ]; then
					echo '{"success":false,"error":"expected JSON, at most 256 KiB"}'
				else
					"$DAEMON_BIN" --config "$YAML" --web-config "$ACTION"
				fi
				;;
			persist)
				case "$BLE2UART_GATEWAY_STORE" in
					/tmp/flash/*)
						if /usr/bin/modsave flash >/dev/null 2>&1; then
							echo '{"success":true,"message":"configuration archived to flash"}'
						else
							echo '{"success":false,"error":"modsave flash failed; YAML is saved in RAM but not confirmed persistent"}'
						fi
						;;
					*) echo '{"success":true,"message":"configuration saved at the selected storage path"}' ;;
				esac
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
echo '<details id="bbStartup" open><summary>'"$(lang de:"Start und Speicher" en:"Startup and storage")"'</summary>'
echo '<p><strong>'"$(lang de:"Konfigurationsdatei" en:"Configuration file" it:"File di configurazione")"':</strong> <code>'"$(html "$YAML")"'</code></p>'
sec_begin "$(lang de:"Starttyp" en:"Start type")"
cgi_print_radiogroup_service_starttype "enabled" "$BLE2UART_GATEWAY_ENABLED" "" "" 0
sec_end

sec_begin "$(lang de:"Serielle Schnittstelle" en:"Serial link")"
cat << EOF
<p>$(lang de:"Serielles Gerät bei Erstinstallation" en:"Initial serial device"): <input type="text" name="serial" size="24" maxlength="64" value="$(html "$BLE2UART_GATEWAY_SERIAL")"></p>
<p><label for="bbInitialBaudrate">$(lang de:"Baudrate bei Erstinstallation" en:"Initial baud rate"):</label> <select name="baudrate" id="bbInitialBaudrate">
EOF
BB_BAUDRATE_FOUND=
for BB_BAUDRATE in 9600 19200 38400 57600 115200 230400 460800 921600 1000000 2000000; do
	BB_SELECTED=
	if [ "$BLE2UART_GATEWAY_BAUDRATE" = "$BB_BAUDRATE" ]; then
		BB_SELECTED=' selected'
		BB_BAUDRATE_FOUND=yes
	fi
	printf '<option value="%s"%s>%s</option>\n' "$BB_BAUDRATE" "$BB_SELECTED" "$BB_BAUDRATE"
done
if [ -z "$BB_BAUDRATE_FOUND" ]; then
	printf '<option value="%s" selected>%s</option>\n' "$(html "$BLE2UART_GATEWAY_BAUDRATE")" "$(html "$BLE2UART_GATEWAY_BAUDRATE")"
fi
cat << EOF
</select></p>
<p>$(lang de:"Diese Werte gelten nur für eine neue YAML-Konfiguration. Bestehende Verbindungen unter Settings → Serial ändern; danach speichern und neu starten." en:"These values initialize a new YAML configuration only. Change an existing connection under Settings → Serial, then save and restart.")</p>
<p>$(lang de:"Warten auf Programm/Gerät (Sekunden, 0 = sofort)" en:"Wait for the binary/device (seconds, 0 = immediately)"): <input type="text" name="config_wait" size="6" maxlength="5" value="$(html "$BLE2UART_GATEWAY_CONFIG_WAIT")"></p>
EOF
sec_end

# Storage chooser: same pattern as the other freetz packages; the bind keys are
# secrets, so the store should live on a disk and never in a world readable
# place.
sec_begin "$(lang de:"Speicherort" en:"Store location" it:"Percorso di configurazione")"
cat << EOF
<style>
#bbStoreBlock .bbStoreLabel {display:block;font-weight:bold;margin-bottom:3px;}
#bbStoreBlock #store {width:100%;max-width:34em;}
#bbStoreBlock .bbStoreHint {display:block;font-size:11px;line-height:1.55;color:#555;margin:4px 0 8px;max-width:70em;}
#bbStoreBlock #bbStoreDisks {margin:10px 0 4px;}
#bbStoreBlock #bbStoreDisks > summary {cursor:pointer;font-size:12px;}
#bbStoreBlock table {width:100%;font-size:11px;border-collapse:collapse;}
#bbStoreBlock table th {text-align:left;}
#bbStoreBlock table td {padding:2px 4px;}
#bbStoreBlock table td.bbStoreType {color:#666;}
#bbStoreBlock table td.bbStoreFree {text-align:right;white-space:nowrap;}
#bbStoreBlock code.bbStorePick {cursor:pointer;color:#0056b3;font-weight:bold;}
#bbStoreBlock code.bbStorePick:hover {text-decoration:underline;}
#bbStartupActions {display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:14px 0 4px;padding-top:12px;border-top:1px solid #c9ced1;}
#bbApp + #bbStartupHint, #bbStartupHint {display:block;font-size:11px;line-height:1.55;color:#555;margin:0 0 10px;max-width:70em;}
</style>
<div id="bbStoreBlock">
<p><label class="bbStoreLabel" for="store">$(lang de:"Verzeichnis der Konfiguration" en:"Configuration directory" it:"Percorso della configurazione")</label>
<input type="text" id="store" name="store" size="40" maxlength="255" value="$(html "$BLE2UART_GATEWAY_STORE")">
<span class="bbStoreHint">$(lang de:"Enthält die Gateway-YAML (Geräte, Bindkeys, Verfügbarkeitsregeln), die Zustandsdatei der Regeln und – falls hier abgelegt – den Matter-Store." en:"Holds the gateway YAML (devices, bind keys, availability rules), the availability state file and, if you keep it here, the Matter fabric store." it:"Contiene lo YAML del gateway (dispositivi, bind key, regole di disponibilità), il file di stato delle regole e, se decidi di tenerlo qui, lo store delle identità Matter.")</span>
<span class="bbStoreHint">$(lang de:"Muss ein persistenter Ort sein: der Dienst liest sie nach jedem Neustart erneut. Beim Ändern des Pfads werden vorhandene Dateien kopiert, nie gelöscht." en:"Use a persistent location: the service reads it again after every reboot. Changing the path copies the existing files, it never deletes them." it:"Deve essere una posizione persistente: il servizio la rilegge dopo ogni riavvio. Cambiando percorso i file esistenti vengono copiati, mai cancellati.")</span></p>
<details id="bbStoreDisks"><summary>$(lang de:"Gemountete Datenträger anzeigen (zum Öffnen klicken)" en:"Show mounted disks (click to open)" it:"Mostra i dischi montati (clic per aprire)")</summary>
<table>
<tr><th>$(lang de:"Gerät" en:"Device" it:"Dispositivo")</th><th>$(lang de:"Typ" en:"Type" it:"Tipo")</th><th style="text-align:right;">$(lang de:"Frei / Gesamt" en:"Free / total" it:"Libero / totale")</th></tr>
EOF
storage_row() {
	echo "<tr><td><code class='bbStorePick' onclick=\"document.getElementById('store').value='$1/ble2uart_gateway';\">$1</code></td><td class='bbStoreType'>$2</td><td class='bbStoreFree'>$3</td></tr>"
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
</details>
<div id="bbStartupActions"></div>
<p id="bbStartupHint">$(lang de:"Diese Schaltfläche speichert nur die Freetz-Starteinstellungen (Starttyp, initiales serielles Gerät, Konfigurationsverzeichnis) in /mod/etc/conf und startet einen laufenden Dienst neu. „Save configuration“ oben speichert dagegen den Gateway-Entwurf (YAML: Geräte, Regeln, Frontends) und startet nichts neu." en:"This button saves only the Freetz startup options (start type, initial serial device, configuration directory) into /mod/etc/conf and restarts the service when it is running. “Save configuration” above saves the gateway draft (YAML: devices, rules, frontends) and never restarts anything." it:"Questo pulsante salva solo le impostazioni di avvio di Freetz (tipo di avvio, seriale iniziale, percorso della configurazione) in /mod/etc/conf e riavvia il servizio se è attivo. «Save configuration» in alto salva invece la bozza del gateway (YAML: dispositivi, regole, frontend) e non riavvia nulla.")</p>
</div>
EOF
case "$BLE2UART_GATEWAY_STORE" in
	/tmp/flash/*)
		cat << EOF
<p class="bbStoreHint" style="display:block;font-size:11px;line-height:1.55;color:#555;margin:4px 0 8px;max-width:70em;">$(lang de:"/tmp/flash ist kein flüchtiger Speicher: Freetz archiviert es beim Speichern mit modsave im Flash und stellt es beim Booten wieder her, die Konfiguration übersteht also einen Neustart. Es ist klein und liegt im Router-Flash: hier nur YAML und Bindkeys ablegen, aktive SQLite-Datenbanken und Matter-Store gehören auf externen Speicher." en:"/tmp/flash is not volatile memory: Freetz archives it into flash with modsave when you save and restores it at boot, so the configuration survives a reboot. It is small and lives in the router flash: keep only the YAML and the bind keys here; live SQLite databases and the Matter store belong on external storage." it:"/tmp/flash non è memoria volatile: Freetz la archivia in flash con modsave al salvataggio e la ripristina al boot, quindi la configurazione sopravvive al riavvio. È però piccola e risiede nella flash del router: qui vanno bene solo lo YAML e i bind key; database SQLite attivi e store Matter vanno su memoria esterna.")</p>
EOF
		;;
esac
sec_end

echo '</details>'
sec_begin "$(lang de:"Gateway-Konfiguration" en:"Gateway configuration")"
printf '<span id="bbLocale" data-language="%s" hidden></span>\n' "$(lang de:"de" en:"en" it:"it" fr:"fr" es:"es")"
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
#bbApp #bbFrontends > [data-frontend] {border:1px solid var(--bb-line);border-left:4px solid var(--bb-accent);border-radius:6px;padding:10px 14px 12px;margin:16px 0;min-width:0;background:color-mix(in srgb,var(--bb-accent) 5%,transparent);}
#bbApp #bbFrontends > [data-frontend] > legend {color:var(--bb-accent);padding:0 8px;}
#bbApp #bbFrontends > [data-frontend] > .bbGrid > .bbField:first-child {grid-column:1 / -1;border-bottom:1px solid var(--bb-line);padding-bottom:10px;}
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
#bbApp .bbOutput {height:280px;min-height:160px;max-height:65vh;width:100%;border:1px solid var(--bb-line);margin:12px 0;}
#bbApp #bbRadio {height:180px;}
#bbApp #bbCommandRequest,#bbApp #bbConfirmRequest,#bbApp #bbCmd_patch {height:220px;}
#bbApp .bbOutput:not(.ace_editor) {white-space:pre-wrap;overflow:auto;font:12px/1.5 monospace;}
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
#bbApp .bbFieldName {display:flex;align-items:center;gap:8px;}
#bbApp .bbParameterHelp {padding:0;width:24px;min-height:24px;flex:0 0 24px;border:1px solid var(--bb-line);border-radius:50%;background:transparent;color:var(--bb-accent);font-weight:bold;}
#bbApp .bbLink {display:inline-flex;align-items:center;min-height:30px;padding:4px 10px;border:1px solid var(--bb-line);border-radius:4px;text-decoration:none;color:inherit;}
#bbApp .bbLink:hover {border-color:var(--bb-accent);color:var(--bb-accent);}
#bbApp .bbFilterBar {border-top:1px solid var(--bb-line);padding-top:12px;margin-top:20px;}
#bbApp .bbFilterBar input {flex:1;min-width:160px;}
#bbApp .bbToggled {transition:background .15s,border-color .15s;}
#bbApp fieldset.bbToggled,#bbApp details.bbToggled {border:1px solid var(--bb-line);border-left:4px solid var(--bb-accent);border-radius:6px;padding:10px 14px 12px;margin:14px 0;min-width:0;}
#bbApp details.bbToggled {margin:16px 0 12px;padding:8px 12px 10px;}
#bbApp .bbToggled.bbOn {background:color-mix(in srgb,var(--bb-accent) 7%,transparent)!important;border-left-color:var(--bb-accent);}
#bbApp .bbToggled.bbOff {background:color-mix(in srgb,var(--bb-line) 28%,transparent)!important;border-left-color:var(--bb-line);}
#bbApp .bbToggled.bbOff > legend,#bbApp .bbToggled.bbOff > summary {color:var(--muted);}
#bbApp .bbBtnPrimary {background:var(--bb-accent);border:1px solid var(--bb-accent);color:#fff;font-weight:bold;}
#bbApp .bbBtnPrimary:hover {filter:brightness(.93);}
#bbApp .bbBtnSecondary {background:transparent;border:1px solid var(--bb-line);color:inherit;}
#bbApp .bbBtnSecondary:hover {background:color-mix(in srgb,var(--bb-line) 35%,transparent);}
#bbApp .bbDialogFooter {display:flex;flex-direction:column;gap:8px;margin-top:14px;padding:10px 0 4px;border-top:1px solid var(--bb-line);position:sticky;bottom:0;background:var(--evo-surface,#fff);box-shadow:0 -8px 12px -10px rgba(0,0,0,.35);}
#bbApp .bbDialogFooter .bbHint {flex:1 1 auto;min-width:0;font-size:11.5px;color:var(--muted);}
#bbApp .bbFooterButtons {display:flex;gap:8px;justify-content:flex-end;margin-left:auto;}
#bbApp #bbDeviceFields {padding-bottom:8px;}
#bbApp #bbAvailabilityRules > .bbBar button,#bbApp .bbAvailabilityRule > .bbBar:first-child button,#bbApp .bbPolicies .bbBar button {border:1px dashed var(--bb-accent);background:transparent;color:var(--bb-accent);font-size:12px;min-height:26px;padding:2px 8px;}
#bbApp #bbAvailabilityRules > .bbBar button:hover,#bbApp .bbAvailabilityRule > .bbBar:first-child button:hover,#bbApp .bbPolicies .bbBar button:hover {background:color-mix(in srgb,var(--bb-accent) 10%,transparent);}
#bbApp .bbHistoryPolicy {border:1px solid var(--bb-line);border-left:4px solid var(--bb-accent);border-radius:6px;padding:10px 12px;margin:12px 0;min-width:0;background:color-mix(in srgb,var(--bb-accent) 4%,transparent);}
#bbApp .bbHistoryPolicy > .bbPolicyHead {margin:0 0 4px;gap:8px;}
#bbApp .bbPolicyPresets {display:flex;flex-wrap:wrap;gap:6px;margin-right:auto;}
#bbApp .bbLocalActions {border-top:1px dashed var(--bb-line);padding-top:10px;margin-top:12px;}
#bbApp #bbYamlHint {margin:0 0 8px;}
#bbApp #bbTheengs {margin:14px 0 0;padding-top:10px;border-top:1px dashed var(--bb-line);}
#bbApp #bbTheengsJson,#bbApp #bbTheengsResult {height:190px;min-height:120px;}
#bbApp .bbInactive {border-left-color:var(--bb-line)!important;}
#bbApp .bbTier {display:grid;grid-template-columns:repeat(2,minmax(185px,1fr)) 32px;gap:12px;align-items:end;margin:12px 0;}
#bbApp .bbDuration {display:flex;gap:4px;min-width:0;}
#bbApp .bbDuration input {width:110px;min-width:100px;flex:1 1 110px;}
#bbApp .bbDuration select {width:90px;min-width:76px;flex:0 0 90px;}
#bbApp .bbTier > button {width:30px;padding:4px;}
#bbApp #bbHistoryMaintenance {container-type:inline-size;}
#bbApp #bbHistoryMaintenance > summary {cursor:pointer;font-weight:bold;padding:8px 0;}
#bbApp #bbHistoryMaintenance input[type=number] {min-height:36px;}
#bbApp .bbAvailabilityRule {border:1px solid var(--bb-line);border-left:4px solid var(--bb-accent);border-radius:6px;padding:10px 12px;margin:14px 0;min-width:0;background:color-mix(in srgb,var(--bb-accent) 5%,transparent);}
#bbApp .bbAvailabilityRule > .bbBar:first-child {margin-bottom:6px;}
#bbApp .bbAvailabilityWebhook {margin:8px 0 0 6px;padding-left:12px;border-left:3px solid var(--bb-line);background:transparent;}
#bbApp .bbAvailabilityWebhook > summary {cursor:pointer;font-weight:bold;padding:8px 0;}
@container(max-width:470px) {#bbApp .bbTier {grid-template-columns:minmax(0,1fr) 32px;}#bbApp .bbTier > .bbField {grid-column:1;}#bbApp .bbTier > button {grid-column:2;grid-row:1 / 3;align-self:center;}}
</style>
<div id="bbApp">
<div class="bbBar">
<button type="button" id="bbReload">Reload</button>
<button type="button" id="bbCheck">Validate</button>
<button type="button" id="bbSave">Save configuration</button>
<button type="button" id="bbLogging">Reload logging</button>
<button type="button" id="bbLogOpen">Service log</button>
<a class="bbLink" id="bbPortal" href="/cgi-bin/extra/ble2uart_gateway/portal" target="_blank" rel="noopener">Sensor graphs</a>
<span id="bbDirty"></span>
</div>
<div id="bbMsg" class="bbStatus" role="status" aria-live="polite">Loading configuration...</div>
<div class="bbBar bbTabs" role="tablist" aria-label="Gateway views">
<button type="button" role="tab" data-tab="devices" aria-selected="true">Devices</button>
<button type="button" role="tab" data-tab="discovery" aria-selected="false">Discovery</button>
<button type="button" role="tab" data-tab="commands" id="bbCommandsTab" aria-selected="false">Commands</button>
<button type="button" role="tab" data-tab="settings" aria-selected="false">Settings</button>
<button type="button" role="tab" data-tab="log" aria-selected="false">Log</button>
<button type="button" role="tab" data-tab="yaml" aria-selected="false">YAML</button>
</div>
<section data-panel="devices" role="tabpanel">
<div class="bbBar"><button type="button" id="bbDiscoverDevices">Discover devices</button><button type="button" id="bbAdd">Add manually</button></div>
<div class="bbBar bbFilterBar"><label for="bbDeviceSearch" id="bbDeviceFilterLabel">Filter configured devices</label><input id="bbDeviceSearch" type="search" placeholder="MAC, name, manufacturer or model"></div>
<div class="bbScroll"><table><thead><tr><th>Enabled</th><th>MAC</th><th>Name / manufacturer / model</th><th>Format</th><th>Exposed attributes</th><th>Actions</th></tr></thead><tbody id="bbDevices"></tbody></table></div>
</section>
<section data-panel="discovery" role="tabpanel" hidden>
<div class="bbBar"><label>Duration (s) <input type="number" id="bbDuration" min="1" max="300" value="30" style="width:80px"></label><button type="button" id="bbStart">Start discovery</button><button type="button" id="bbStop" disabled>Stop</button><span id="bbDiscoveryStatus" role="status"></span></div>
<div class="bbBar"><input type="search" id="bbSearch" placeholder="MAC, name or format" aria-label="Search discovery"><select id="bbVendor" aria-label="Filter by OUI vendor"><option value="">All OUI vendors</option></select><select id="bbSort" aria-label="Sort discovery"><option value="rssi">Strongest signal</option><option value="mac">MAC</option><option value="name">Name</option><option value="vendor">OUI vendor</option><option value="format">Wire format</option><option value="count">Most reports</option><option value="last_seen">Last seen</option></select><label><input type="checkbox" id="bbNewOnly"> Unconfigured only</label><button type="button" id="bbExport">Export observations</button></div>
<div class="bbBar"><span id="bbDiscoveryFilterNote" class="bbHint"></span><button type="button" id="bbOpenFilters"></button></div>
<div class="bbScroll"><table><thead><tr><th>MAC / name</th><th>OUI vendor</th><th>Wire format</th><th>RSSI</th><th>PHY</th><th>Reports / last seen</th><th>Actions</th></tr></thead><tbody id="bbFound"></tbody></table></div>
<details id="bbPacketDetails"><summary>Selected advertisement</summary><p id="bbPacketHint" class="bbHint"></p><details id="bbPacketHelp" class="bbHelp"><summary id="bbPacketHelpTitle"></summary><dl id="bbPacketFields"></dl></details><p id="bbPacketNotice" class="bbHint" role="status" hidden></p><div id="bbPacketError" role="alert" class="bbError" hidden></div><div id="bbPacket" aria-label="Selected advertisement JSON" aria-describedby="bbPacketHint"></div><details id="bbTheengs" class="bbHelp"><summary id="bbTheengsTitle"></summary><div id="bbTheengsJson" class="bbOutput" aria-label="Theengs decoder input"></div><p id="bbTheengsStatus" class="bbHint" role="status"></p><div class="bbBar"><button type="button" class="bbBtnPrimary" id="bbTheengsDecode"></button><button type="button" id="bbTheengsCopy"></button><a class="bbLink" id="bbTheengsOpen" href="https://decoder.theengs.io/parser.html" target="_blank" rel="noopener noreferrer"></a></div><p class="bbHint" id="bbTheengsResultLabel"></p><div id="bbTheengsResult" class="bbOutput" aria-labelledby="bbTheengsResultLabel"></div></details></details>
</section>
<section data-panel="settings" role="tabpanel" hidden><div id="bbSettings"></div></section>
<section data-panel="commands" role="tabpanel" hidden>
<p id="bbCommandNote"></p>
<div class="bbBar"><label><span id="bbCommandTypeLabel"></span> <select id="bbCommandType"></select></label><button type="button" id="bbCommandSend"></button><button type="button" id="bbRadioRefresh"></button></div>
<div id="bbCommandFields" class="bbGrid"></div>
<div id="bbCommandPatch" hidden><p id="bbCommandPatchLabel"></p><div id="bbCmd_patch" class="bbOutput" aria-labelledby="bbCommandPatchLabel" aria-describedby="bbCommandPatchError"></div><p id="bbCommandPatchError" class="bbError" role="alert" hidden></p></div>
<p id="bbGattHelp" class="bbHint"></p>
<div class="bbBar"><button type="button" id="bbAtcRead"></button><button type="button" id="bbAtcPatch"></button></div>
<details id="bbCommandRequestDetails" class="bbHelp"><summary id="bbCommandRequestLabel"></summary><div id="bbCommandRequest" class="bbOutput">{}</div></details>
<div id="bbRadio" class="bbOutput"></div>
<div id="bbCommandResult" class="bbOutput"></div>
</section>
<section data-panel="log" role="tabpanel" hidden>
<div class="bbBar"><label>Lines <select id="bbLogLines"><option value="100">100</option><option value="300" selected>300</option><option value="1000">1000</option><option value="2000">2000</option></select></label><button type="button" id="bbLogRefresh">Refresh</button><label><input type="checkbox" id="bbLogAuto" checked> Auto-refresh every 5 s</label><button type="button" id="bbLogDownload">Download</button><span id="bbLogStatus" class="bbHint" role="status"></span></div>
<p class="bbHint" id="bbLogNote"></p>
<pre id="bbLog" class="bbOutput" aria-label="Service log" tabindex="0"></pre>
</section>
<section data-panel="yaml" role="tabpanel" hidden><p class="bbHint" id="bbYamlHint"></p><div class="bbBar"><button type="button" class="bbBtnPrimary" id="bbYamlSave">Save YAML</button><button type="button" id="bbYamlRevert">Discard changes</button><button type="button" id="bbDownload">Download YAML</button><label>Import YAML <input type="file" id="bbImport" accept=".yaml,.yml,text/plain"></label></div><div class="bbBar"><button type="button" id="bbHistory">List backups</button><select id="bbBackups" aria-label="Configuration backup"><option value="">Select backup</option></select><button type="button" id="bbRestore">Load backup</button></div><div id="bbYaml" aria-label="Complete gateway YAML configuration" aria-describedby="bbYamlHint"></div></section>
<datalist id="bbFormats"><option value="custom"><option value="custom_enc"><option value="atc1441"><option value="atc1441_enc"><option value="mi_like"><option value="bt_home"><option value="bt_home_enc"><option value="bt_home_v2"></datalist>
<datalist id="bbAttributes"><option value="temperature"><option value="humidity"><option value="battery_level"><option value="battery_v"><option value="switch"><option value="opened"><option value="boolean"><option value="humidity_trigger"><option value="temp_trigger"><option value="out_gpio_trg_flag"><option value="out_gpio_trg_value"><option value="input_gpio_value"></datalist>
<dialog id="bbDeviceDialog"><h3 id="bbDeviceTitle">Device</h3><div id="bbDeviceFields"></div><div class="bbBar"><button type="button" id="bbSuggestAttributes" hidden>Detect attributes</button></div><div id="bbDeviceError" role="alert" class="bbError"></div><div class="bbDialogFooter"><span class="bbFooterButtons"><button type="button" class="bbBtnSecondary" id="bbDeviceCancel">Cancel</button><button type="button" class="bbBtnPrimary" id="bbDeviceApply">Add to configuration draft</button></span></div></dialog>
<dialog id="bbParameterDialog"><h3 id="bbParameterTitle"></h3><p><code id="bbParameterPath"></code></p><p id="bbParameterText"></p><button type="button" id="bbParameterClose">Close</button></dialog>
<dialog id="bbConfirm"><h3>Confirm</h3><p id="bbConfirmText"></p><div id="bbConfirmRequest" class="bbOutput" hidden></div><div class="bbBar"><button type="button" id="bbConfirmOk">Continue</button><button type="button" id="bbConfirmCancel">Cancel</button></div></dialog>
<div id="bbFieldTooltip" role="tooltip" hidden><strong></strong><span></span></div>
</div>
<script>
(() => {
	const app = document.getElementById('bbApp');
	const element = id => document.getElementById(id);
	const copy = value => JSON.parse(JSON.stringify(value));
	const normalize = mac => String(mac).replace(/[:-]/g, '').toUpperCase();
	let config = null, revision = '', dirty = false, rawDirty = false, tab = 'devices';
	let observations = [], editIndex = -1, draft = null, editObservation = null, polling = false, busy = false;
	let yamlEditor=null, yamlText='', syncingYaml=false, inspectionSequence=0;
	let aceLoading=null, packetEditor=null, packetEditorLoading=null, packetText='';
	let jsonModeLoading=null, commandEditorsLoading=null;
	let availabilityStatusEditor=null;
	const commandEditors={};
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
	const helpLanguage=(element('bbLocale')?.dataset.language||navigator.language||document.documentElement.lang||'en').split('-')[0];
	const ht=helpTranslations[helpLanguage]||helpTranslations.en;
	function setYaml(text) {yamlText=text;buildYamlLines(text);if(yamlEditor){syncingYaml=true;yamlEditor.setValue(text,-1);syncingYaml=false;}}
	function getYaml() {return yamlEditor?yamlEditor.getValue():yamlText;}
	function loadScript(source) {return new Promise((resolve,reject)=>{const script=document.createElement('script');script.src=source;script.onload=resolve;script.onerror=()=>reject(new Error('Cannot load editor asset: '+source));document.head.append(script);});}
	function ensureAce() {
		if(window.ace)return Promise.resolve();
		if(!aceLoading)aceLoading=loadScript('/ace/ace.js').catch(error=>{aceLoading=null;throw error;});
		return aceLoading;
	}
	async function jsonEditor(id, readOnly = true) {
		await ensureAce();
		if(!jsonModeLoading){
			ace.config.setModuleUrl('ace/mode/json','/ace/mode-json.js');
			jsonModeLoading=loadScript('/ace/mode-json.js').catch(error=>{jsonModeLoading=null;throw error;});
		}
		await jsonModeLoading;
		const editor=ace.edit(id);editor.session.setUseWorker(false);editor.session.setMode('ace/mode/json');editor.setTheme('ace/theme/textmate');
		editor.setOptions({fontSize:'12px',showPrintMargin:false,wrap:true,tabSize:2,useSoftTabs:true,readOnly,highlightActiveLine:!readOnly,highlightGutterLine:!readOnly});
		return editor;
	}
	function ensureCommandEditors() {
		if(!commandEditorsLoading)commandEditorsLoading=(async()=>{
			for(const id of ['bbRadio','bbCommandRequest','bbCommandResult']){
				if(!commandEditors[id]){
					const text=element(id).textContent;
					commandEditors[id]=await jsonEditor(id);
					commandEditors[id].setValue(text,-1);
				}
				commandEditors[id].resize(true);
			}
		})().catch(error=>{commandEditorsLoading=null;throw error;});
		return commandEditorsLoading;
	}
	function setCommandOutput(id,value,mode='json') {
		const text=mode==='json'?JSON.stringify(value,null,2):value;
		const editor=commandEditors[id];
		if(editor){editor.session.setMode('ace/mode/'+mode);editor.setValue(text,-1);editor.resize(true);}
		else element(id).textContent=text;
	}
	async function ensureYamlEditor() {
		if(yamlEditor)return;
		await ensureAce();
		ace.config.setModuleUrl('ace/mode/yaml','/ble2uart_gateway/mode-yaml.js');
		await loadScript('/ble2uart_gateway/mode-yaml.js');
		yamlEditor=ace.edit('bbYaml');yamlEditor.session.setUseWorker(false);yamlEditor.session.setMode('ace/mode/yaml');yamlEditor.setTheme('ace/theme/textmate');
		yamlEditor.setOptions({fontSize:'12px',showPrintMargin:false,wrap:true,tabSize:2,useSoftTabs:true});
		setYaml(yamlText);yamlEditor.session.on('change',()=>{if(!syncingYaml){rawDirty=true;buildYamlLines(getYaml());changed();}});
		element('bbYaml').addEventListener('mousemove',yamlHover);element('bbYaml').addEventListener('mouseleave',hidePacketTooltip);
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
		setTheengs(value);
	}
	function hidePacketTooltip(){element('bbFieldTooltip').hidden=true;}
	/** Independent cross-check: rebuild the JSON object expected by the Theengs
	 *  Web Parser from the raw advertisement, so the same payload can be decoded
	 *  by an unrelated implementation. */
	const theengsUi=({en:{title:'Theengs decoder (decoder.theengs.io)',note:'Second opinion with an independent decoder: the advertisement above rendered as the JSON object expected by the Theengs Web Parser (servicedata or manufacturerdata in hex, plus the optional name and MAC). Press Decode above to run the same WebAssembly decoder inside this page; Copy and Open remain available as a fallback.',copy:'Copy JSON',copied:'JSON copied: paste it in the Theengs input field',copyManual:'JSON selected: press Ctrl+C, then paste it in the Theengs input field',open:'Open decoder.theengs.io',embed:'Show the parser here',embedNote:'The parser runs locally as WebAssembly inside your browser and sends nothing to a server, but the page itself is loaded from the Internet. Paste the JSON with Ctrl+V in its input field, then press Decode.',empty:'No service data or manufacturer data in this advertisement.'},it:{title:'Decodifica decoder.theengs.io',note:'Verifica incrociata con un decoder indipendente: l’advertisement qui sopra convertito nell’oggetto JSON atteso dal Web Parser Theengs (servicedata o manufacturerdata in esadecimale, più nome e MAC se disponibili). Premi Decodifica qui sopra per eseguire lo stesso decoder WebAssembly in questa pagina; Copia e Apri restano come alternativa.',copy:'Copia JSON',copied:'JSON copiato: incollalo nel campo di Theengs',copyManual:'JSON selezionato: premi Ctrl+C, poi incollalo nel campo di Theengs',open:'Apri decoder.theengs.io',embed:'Mostra il parser qui',embedNote:'Il parser gira in locale come WebAssembly dentro il browser e non invia nulla a un server, ma la pagina viene caricata da Internet. Incolla il JSON con Ctrl+V nel suo campo, poi premi Decode.',empty:'Nessun service data o manufacturer data in questo advertisement.'},de:{title:'Theengs-Decoder (decoder.theengs.io)',note:'Gegenprobe mit einem unabhängigen Decoder: die Advertisement oben als JSON-Objekt des Theengs Web Parsers (servicedata oder manufacturerdata als Hex, dazu Name und MAC, wenn vorhanden). Mit „Mit Theengs decodieren“ oben läuft derselbe WebAssembly-Decoder in dieser Seite; Kopieren und Öffnen bleiben als Alternative.',copy:'JSON kopieren',copied:'JSON kopiert: im Theengs-Eingabefeld einfügen',copyManual:'JSON ausgewählt: mit Ctrl+C kopieren und im Theengs-Eingabefeld einfügen',open:'decoder.theengs.io öffnen',embed:'Parser hier anzeigen',embedNote:'Der Parser läuft lokal als WebAssembly im Browser und sendet nichts an einen Server, die Seite selbst wird aber aus dem Internet geladen. JSON mit Ctrl+V einfügen, dann Decode drücken.',empty:'Keine Service- oder Manufacturer-Daten in dieser Advertisement.'},fr:{title:'Décodeur Theengs (decoder.theengs.io)',note:'Contre-vérification avec un décodeur indépendant : l’annonce ci-dessus convertie en objet JSON attendu par le Web Parser Theengs (servicedata ou manufacturerdata en hexadécimal, plus le nom et le MAC si disponibles). Appuyez sur Décoder ci-dessus pour exécuter le même décodeur WebAssembly dans cette page ; Copier et Ouvrir restent disponibles.',copy:'Copier le JSON',copied:'JSON copié : collez-le dans le champ Theengs',copyManual:'JSON sélectionné : appuyez sur Ctrl+C puis collez-le dans le champ Theengs',open:'Ouvrir decoder.theengs.io',embed:'Afficher le parser ici',embedNote:'Le parser s’exécute localement en WebAssembly dans le navigateur et n’envoie rien à un serveur, mais la page est chargée depuis Internet. Collez le JSON avec Ctrl+V puis appuyez sur Decode.',empty:'Aucune service data ni manufacturer data dans cette annonce.'},es:{title:'Decodificador Theengs (decoder.theengs.io)',note:'Comprobación con un decodificador independiente: el advertisement anterior convertido al objeto JSON que espera el Web Parser de Theengs (servicedata o manufacturerdata en hexadecimal, más nombre y MAC si existen). Pulsa Decodificar arriba para ejecutar el mismo decodificador WebAssembly en esta página; Copiar y Abrir siguen disponibles.',copy:'Copiar JSON',copied:'JSON copiado: pégalo en el campo de Theengs',copyManual:'JSON seleccionado: pulsa Ctrl+C y pégalo en el campo de Theengs',open:'Abrir decoder.theengs.io',embed:'Mostrar el parser aquí',embedNote:'El parser se ejecuta localmente como WebAssembly en el navegador y no envía nada a un servidor, pero la página se carga desde Internet. Pega el JSON con Ctrl+V y pulsa Decode.',empty:'Este advertisement no tiene service data ni manufacturer data.'}})[helpLanguage]||{title:'Theengs decoder (decoder.theengs.io)',note:'Second opinion with an independent decoder: the advertisement above rendered as the JSON object expected by the Theengs Web Parser.',copy:'Copy JSON',copied:'JSON copied: paste it in the Theengs input field',copyManual:'JSON selected: press Ctrl+C, then paste it in the Theengs input field',open:'Open decoder.theengs.io',embed:'Show the parser here',embedNote:'The parser runs locally as WebAssembly inside your browser and sends nothing to a server, but the page itself is loaded from the Internet.',empty:'No service data or manufacturer data in this advertisement.'};
	function theengsReverseHex(hex){let out='';for(let index=hex.length-2;index>=0;index-=2)out+=hex.slice(index,index+2);return out;}
	function theengsPayload(observation) {
		const payload={};
		const mac=String(observation.mac||'').replace(/[^0-9A-Fa-f]/g,'').toUpperCase();
		if(mac){payload.id=mac.replace(/(..)(?=.)/g,'$1:');payload.mac=payload.id;}
		if(observation.name)payload.name=String(observation.name);
		if(typeof observation.rssi==='number')payload.rssi=observation.rssi;
		const data=String(observation.data||'').replace(/[^0-9A-Fa-f]/g,'');
		let offset=0;
		while(offset+4<=data.length){
			const length=parseInt(data.substr(offset,2),16);
			if(!length||offset+2+length*2>data.length)break;
			const type=parseInt(data.substr(offset+2,2),16);
			const value=data.substr(offset+4,(length-1)*2);
			if(type===0x16&&value.length>4){payload.servicedata=value.slice(4).toLowerCase();payload.servicedatauuid='0x'+theengsReverseHex(value.slice(0,4)).toLowerCase();return payload;}
			if(type===0x20&&value.length>8){payload.servicedata=value.slice(8).toLowerCase();payload.servicedatauuid='0x'+theengsReverseHex(value.slice(0,8)).toLowerCase();return payload;}
			if(type===0x21&&value.length>32){payload.servicedata=value.slice(32).toLowerCase();payload.servicedatauuid=theengsReverseHex(value.slice(0,32)).toLowerCase();return payload;}
			if(type===0xFF&&value.length>4){payload.manufacturerdata=value.toLowerCase();return payload;}
			offset+=2+length*2;
		}
		return null;
	}
	let theengsInput=null, theengsResult=null, theengsDecoder=null, theengsText='', theengsNative='', theengsReady=false, theengsBusy=false;
	const theengsNativeUi=({en:'Decoded by the gateway (compiled-in Theengs library)',it:'Decodificato dal gateway (libreria Theengs compilata)',de:'Vom Gateway decodiert (eingebaute Theengs-Bibliothek)',fr:'Décodé par la passerelle (bibliothèque Theengs intégrée)',es:'Decodificado por la puerta de enlace (biblioteca Theengs integrada)'})[helpLanguage]||'Decoded by the gateway (compiled-in Theengs library)';
	const theengsDecodeUi=({en:{decode:'Decode with Theengs',loading:'Loading the Theengs decoder (about 0.7 MB from decoder.theengs.io)…',decoding:'Decoding…',decoded:'Decoded by Theengs',noDecoder:'Theengs has no decoder for this payload; the JSON itself is valid.',failed:'Theengs decode failed',invalid:'Invalid JSON',result:'Theengs result'},it:{decode:'Decodifica con Theengs',loading:'Carico il decoder Theengs (circa 0,7 MB da decoder.theengs.io)…',decoding:'Decodifica in corso…',decoded:'Decodificato da Theengs',noDecoder:'Theengs non ha un decoder per questo payload; il JSON resta valido.',failed:'Decodifica Theengs non riuscita',invalid:'JSON non valido',result:'Risultato Theengs'},de:{decode:'Mit Theengs decodieren',loading:'Theengs-Decoder wird geladen (etwa 0,7 MB von decoder.theengs.io)…',decoding:'Decodiere…',decoded:'Von Theengs decodiert',noDecoder:'Theengs hat keinen Decoder für diesen Payload; das JSON selbst ist gültig.',failed:'Theengs-Dekodierung fehlgeschlagen',invalid:'Ungültiges JSON',result:'Theengs-Ergebnis'},fr:{decode:'Décoder avec Theengs',loading:'Chargement du décodeur Theengs (environ 0,7 Mo depuis decoder.theengs.io)…',decoding:'Décodage…',decoded:'Décodé par Theengs',noDecoder:'Theengs n’a pas de décodeur pour ce payload ; le JSON reste valide.',failed:'Échec du décodage Theengs',invalid:'JSON invalide',result:'Résultat Theengs'},es:{decode:'Decodificar con Theengs',loading:'Cargando el decodificador Theengs (unos 0,7 MB desde decoder.theengs.io)…',decoding:'Decodificando…',decoded:'Decodificado por Theengs',noDecoder:'Theengs no tiene decodificador para este payload; el JSON sigue siendo válido.',failed:'Falló la decodificación de Theengs',invalid:'JSON no válido',result:'Resultado Theengs'}})[helpLanguage]||{decode:'Decode with Theengs (WebAssembly)',loading:'Loading the Theengs decoder…',decoding:'Decoding…',decoded:'Decoded by Theengs',noDecoder:'Theengs has no decoder for this payload; the JSON itself is valid.',failed:'Theengs decode failed',invalid:'Invalid JSON',result:'Theengs result'};
	function theengsStatus(text,error){const node=element('bbTheengsStatus');if(!node)return;node.textContent=text||'';node.classList.toggle('bbError',!!error);}
	async function ensureTheengsEditors() {
		if(theengsInput)return;
		theengsInput=await jsonEditor('bbTheengsJson',false);
		theengsResult=await jsonEditor('bbTheengsResult',true);
		if(theengsText)theengsInput.setValue(theengsText,-1);
		if(theengsNative)theengsResult.setValue(theengsNative,-1);
		theengsInput.resize(true);theengsResult.resize(true);
	}
	function setTheengs(observation) {
		const payload=observation?theengsPayload(observation):null;
		theengsReady=!!payload;
		theengsText=payload?JSON.stringify(payload,null,2):'';
		const native=observation&&observation.theengs&&typeof observation.theengs==='object'?observation.theengs:null;
		theengsNative=native?JSON.stringify(native,null,2):'';
		if(theengsInput)theengsInput.setValue(theengsText,-1);
		if(theengsResult)theengsResult.setValue(theengsNative,-1);
		const decode=element('bbTheengsDecode'),copy=element('bbTheengsCopy');
		if(decode)decode.disabled=!payload;
		if(copy)copy.disabled=!payload;
		theengsStatus(native?theengsNativeUi:(payload?'':theengsUi.empty),false);
	}
	async function decodeWithTheengs() {
		if(theengsBusy)return;
		theengsBusy=true;
		element('bbTheengsDecode').disabled=true;
		theengsStatus(theengsDecodeUi.decoding);
		try{
			await ensureTheengsEditors();
			if(!theengsDecoder){
				theengsStatus(theengsDecodeUi.loading);
				const loaded=await import('https://decoder.theengs.io/wasm/theengs_decoder_wasm.mjs');
				const factory=loaded.default||loaded.createTheengsDecoderModule;
				const wasm=await factory();
				theengsDecoder=new wasm.TheengsDecoder();
			}
			let parsed;
			try{parsed=JSON.parse(theengsInput.getValue());}catch(error){throw new Error(theengsDecodeUi.invalid+': '+error.message);}
			const raw=theengsDecoder.decodeBLE(JSON.stringify(parsed));
			if(!raw){theengsResult.setValue('',-1);theengsStatus(theengsDecodeUi.noDecoder);}
			else{theengsResult.setValue(JSON.stringify(JSON.parse(raw),null,2),-1);theengsResult.resize(true);theengsStatus(theengsDecodeUi.decoded);}
		}catch(error){theengsStatus(theengsDecodeUi.failed+': '+error.message,true);}
		finally{theengsBusy=false;element('bbTheengsDecode').disabled=!theengsReady;}
	}
	async function copyTheengs() {
		await ensureTheengsEditors();
		let copied=false;
		try{copied=document.execCommand('copy');}catch(error){copied=false;}
		if(!theengsInput||!copied){
			if(navigator.clipboard&&navigator.clipboard.writeText){
				try{await navigator.clipboard.writeText(theengsInput?theengsInput.getValue():theengsText);copied=true;}catch(error){copied=false;}
			}
		}
		theengsStatus(copied?theengsUi.copied:theengsUi.copyManual,!copied);
	}
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
			packetEditor=await jsonEditor('bbPacket');
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
	const workflowTranslations={
		en:{manual:'Add manually',discover:'Discover devices',filter:'Filter configured devices',add:'Add to configuration draft',update:'Update configuration draft',detected:'Configure discovered device',manualTitle:'Add device manually',edit:'Edit device',detect:'Detect attributes',close:'Close',help:'Help',enabled:'Enabled',disabled:'Disabled',rules:'Rules (not executed)',saved:'Saved',pending:'Device added to draft. Save configuration to write it to disk, then restart from Status to activate it.',detectionFailed:'Attributes could not be detected. Check the bindkey/format, then retry, or add attributes manually.',startup:'Save startup settings',startupConfirm:'Save the startup settings (start type, initial serial device, configuration directory)? Freetz restarts a running service. The gateway draft is not saved: use “Save configuration” for that.',unsaved:'Save or reload the gateway draft before changing startup/storage.',sqlite:'SQLite reads include committed WAL data. The .db file timestamp alone does not indicate freshness.'},
		it:{manual:'Aggiungi manualmente',discover:'Scopri dispositivi',filter:'Filtra dispositivi configurati',add:'Aggiungi alla bozza',update:'Aggiorna nella bozza',detected:'Configura dispositivo rilevato',manualTitle:'Aggiungi dispositivo manualmente',edit:'Modifica dispositivo',detect:'Rileva attributi',close:'Chiudi',help:'Aiuto',enabled:'Abilitato',disabled:'Disabilitato',rules:'Rules (non eseguite)',saved:'Salvato',pending:'Dispositivo nella bozza. Premi Save configuration per salvarlo su disco, poi riavvia dalla sezione Stato per attivarlo.',detectionFailed:'Impossibile rilevare gli attributi. Verifica bindkey/formato e riprova, oppure aggiungi gli attributi manualmente.',startup:'Salva impostazioni di avvio',startupConfirm:'Salvare le impostazioni di avvio (tipo di avvio, seriale iniziale, percorso della configurazione)? Freetz riavvia il servizio se è attivo. La bozza del gateway non viene salvata: per quella usa «Save configuration».',unsaved:'Salva o ricarica la bozza del gateway prima di modificare avvio/percorso.',sqlite:'Le letture SQLite includono i dati WAL confermati. La data del solo file .db non indica la freschezza dei dati.'},
		de:{manual:'Manuell hinzufügen',discover:'Geräte suchen',filter:'Konfigurierte Geräte filtern',add:'Zum Entwurf hinzufügen',update:'Im Entwurf aktualisieren',detected:'Gefundenes Gerät konfigurieren',manualTitle:'Gerät manuell hinzufügen',edit:'Gerät bearbeiten',detect:'Attribute erkennen',close:'Schließen',help:'Hilfe',enabled:'Aktiviert',disabled:'Deaktiviert',rules:'Regeln (nicht ausgeführt)',saved:'Gespeichert',pending:'Gerät im Entwurf. Save configuration schreibt auf Datenträger; danach unter Status neu starten.',detectionFailed:'Attribute nicht erkannt. Bindkey/Format prüfen oder manuell ergänzen.',startup:'Starteinstellungen speichern',startupConfirm:'Starteinstellungen (Starttyp, initiales serielles Gerät, Konfigurationsverzeichnis) speichern? Freetz startet einen laufenden Dienst neu. Der Gateway-Entwurf wird nicht gespeichert: dafür „Save configuration“ verwenden.',unsaved:'Gateway-Entwurf zuerst speichern oder neu laden.',sqlite:'SQLite liest auch bestätigte WAL-Daten. Der .db-Zeitstempel allein zeigt nicht die Aktualität.'},
		fr:{manual:'Ajouter manuellement',discover:'Découvrir les appareils',filter:'Filtrer les appareils configurés',add:'Ajouter au brouillon',update:'Modifier le brouillon',detected:'Configurer cet appareil',manualTitle:'Ajouter un appareil manuellement',edit:'Modifier cet appareil',detect:'Détecter les attributs',close:'Fermer',help:'Aide',enabled:'Activé',disabled:'Désactivé',rules:'Règles (non exécutées)',saved:'Enregistré',pending:'Appareil dans le brouillon. Save configuration écrit sur disque ; redémarrer ensuite depuis État.',detectionFailed:'Attributs non détectés. Vérifier bindkey/format ou les ajouter manuellement.',startup:'Enregistrer les réglages de démarrage',startupConfirm:'Enregistrer les réglages de démarrage (type, port série initial, répertoire de configuration) ? Freetz redémarre le service actif. Le brouillon du gateway n’est pas enregistré : utilisez « Save configuration ».',unsaved:'Enregistrer ou recharger le brouillon du gateway avant de continuer.',sqlite:'SQLite lit aussi les données WAL validées. La date du fichier .db seule ne prouve pas leur fraîcheur.'},
		es:{manual:'Añadir manualmente',discover:'Descubrir dispositivos',filter:'Filtrar dispositivos configurados',add:'Añadir al borrador',update:'Actualizar borrador',detected:'Configurar dispositivo detectado',manualTitle:'Añadir dispositivo manualmente',edit:'Editar dispositivo',detect:'Detectar atributos',close:'Cerrar',help:'Ayuda',enabled:'Activado',disabled:'Desactivado',rules:'Reglas (no ejecutadas)',saved:'Guardado',pending:'Dispositivo en el borrador. Save configuration guarda en disco; después reiniciar desde Estado.',detectionFailed:'No se detectaron atributos. Revisar bindkey/formato o añadirlos manualmente.',startup:'Guardar ajustes de inicio',startupConfirm:'¿Guardar los ajustes de inicio (tipo, puerto serie inicial, directorio de configuración)? Freetz reinicia el servicio activo. El borrador del gateway no se guarda: use « Save configuration ».',unsaved:'Guardar o recargar el borrador del gateway antes de continuar.',sqlite:'SQLite incluye los datos WAL confirmados. La fecha del archivo .db no indica por sí sola su actualidad.'}
	};
	const ui=workflowTranslations[helpLanguage]||workflowTranslations.en;
	const parameterHelp={
		enabled:['Enable this device or frontend after saving and explicitly restarting the service. Other frontends are independent.','Abilita questo dispositivo o frontend dopo il salvataggio e il riavvio esplicito. Gli altri frontend sono indipendenti.'],
		batch_size:['Maximum items per write: SQLite counts advertisement frames, InfluxDB counts measurement lines. Writes also happen when the flush interval expires, even with a smaller batch. Range 1-1024; must not exceed queue capacity.','Massimo per scrittura: SQLite conta i frame advertisement, InfluxDB le righe di misura. La scrittura avviene anche allo scadere del flush, senza attendere un batch pieno. Da 1 a 1024, non oltre la capacità della coda.'],
		queue_capacity:['Maximum waiting items in RAM: SQLite frames or InfluxDB measurement lines. Range 1-16384. A full queue drops new items and logs an error; it is not a persistent disk spool.','Massimo di elementi in attesa in RAM: frame SQLite o righe di misura InfluxDB. Da 1 a 16384. Se piena, scarta i nuovi elementi e segnala un errore nel log; non è una coda persistente su disco.'],
		flush_interval_ms:['Flush deadline in milliseconds (10-60000), not a sensor polling interval. A full batch writes earlier. Locks, slow storage and retries can increase latency.','Scadenza di scrittura in millisecondi (10-60000), non frequenza di interrogazione del sensore. Un batch pieno viene scritto prima. Lock, disco lento e tentativi successivi possono aumentare la latenza.'],
		busy_timeout_ms:['SQLite waits this many milliseconds for a write lock (1-5000). Failed batches are retained for retry. Long reader transactions can continue to see an older snapshot; finish the transaction before querying again.','SQLite attende un lock di scrittura per questi millisecondi (1-5000). I batch falliti restano in attesa di un nuovo tentativo. Una lunga transazione di lettura può vedere una vecchia istantanea: terminarla prima della nuova query.'],
		path:['Absolute database path on local persistent storage; its parent directory must already exist. SQLite uses WAL: committed rows are visible through SQLite before the .db file is checkpointed. Do not copy only the .db file while the service runs; use the SQLite backup API.','Percorso assoluto del DB su disco locale persistente; la directory deve già esistere. SQLite usa WAL: le righe confermate sono leggibili tramite SQLite prima del checkpoint del file .db. Non copiare solo il .db a servizio attivo: usare la API di backup SQLite.'],
		endpoint:['InfluxDB 3 HTTP(S) server URL, for example http://127.0.0.1:8181. Remote token authentication requires HTTPS. No credentials, query or fragment in the URL.','URL HTTP(S) di InfluxDB 3, ad esempio http://127.0.0.1:8181. Il token su server remoto richiede HTTPS. Niente credenziali, query o frammenti nella URL.'],
		database:['InfluxDB destination database name (1-128 bytes).','Nome del database di destinazione InfluxDB (1-128 byte).'],
		measurement:['InfluxDB measurement/table name (1-128 bytes). Each decoded value is a measurement line.','Nome della measurement/tabella InfluxDB (1-128 byte). Ogni valore decodificato produce una riga di misura.'],
		token:['InfluxDB bearer token. Leave empty if the server does not require authentication. Stored privately in YAML.','Token bearer InfluxDB. Lasciare vuoto se il server non richiede autenticazione. Memorizzato nel file YAML privato.'],
		timeout_ms:['InfluxDB HTTP request timeout in milliseconds (100-30000). Unavailable servers retry within the bounded RAM queue.','Timeout richiesta HTTP InfluxDB in millisecondi (100-30000). Se non disponibile, ritenta entro i limiti della coda RAM.'],
		bind:['Local listener IP address. Loopback restricts access to this router; 0.0.0.0 or :: exposes the listener on network interfaces, subject to firewall rules.','IP locale di ascolto. Loopback limita l’accesso al router; 0.0.0.0 o :: espone il listener sulle interfacce di rete, secondo le regole firewall.'],
		port:['Network port for this frontend (1-65535). Avoid conflicts with other running services.','Porta di rete del frontend (1-65535). Evitare conflitti con altri servizi attivi.'],
		node_id_base:['First MySensors node ID assigned in configured device order. Changing the base or reordering devices can change controller identities.','Primo ID nodo MySensors, assegnato secondo l’ordine dei dispositivi. Cambiare base o ordine può cambiare le identità nel controller.'],
		host:['MQTT broker host name or IP address. This is the broker to connect to, not a local listener.','Nome host o IP del broker MQTT a cui connettersi, non indirizzo locale di ascolto.'],
		local_broker:['Start a gateway-managed Mosquitto broker on loopback using the configured MQTT port. Requires Mosquitto and an available port.','Avvia un broker Mosquitto gestito dal gateway su loopback alla porta MQTT configurata. Richiede Mosquitto e una porta libera.'],
		domoticz_discovery:['Publish native MQTT Auto Discovery descriptions for compatible controllers such as Domoticz. This is not the legacy domoticz/in protocol.','Pubblica descrizioni MQTT Auto Discovery per controller compatibili come Domoticz. Non è il protocollo legacy domoticz/in.'],
		discovery_prefix:['MQTT Auto Discovery topic prefix; must match the controller subscription, typically homeassistant.','Prefisso dei topic MQTT Auto Discovery; deve corrispondere alla sottoscrizione del controller, tipicamente homeassistant.'],
		client_id:['Unique MQTT client identifier. Do not reuse it for a second client on the same broker.','Identificativo univoco del client MQTT. Non riutilizzarlo per un secondo client sullo stesso broker.'],
		base_topic:['MQTT topic prefix for gateway device states. Changing it changes the topics clients must subscribe to.','Prefisso dei topic MQTT per lo stato dei dispositivi. Cambiarlo modifica i topic da sottoscrivere nei client.'],
		username:['MQTT broker username; empty for anonymous access when permitted by the broker.','Nome utente del broker MQTT; vuoto per accesso anonimo se consentito dal broker.'],
		password:['MQTT broker password. Requires a username; saved privately in YAML.','Password del broker MQTT. Richiede un nome utente; salvata nel file YAML privato.'],
		retain:['Ask the MQTT broker to retain the latest published state for new subscribers. Retained state is not an event history.','Chiede al broker di conservare l’ultimo stato pubblicato per i nuovi sottoscrittori. Non è uno storico degli eventi.'],
		domoticz_port:['WebSocket port of a gateway-managed dedicated Matter controller for Domoticz. Set 0 to disable this extra controller; the Matter bridge is configured separately.','Porta WebSocket di un controller Matter dedicato gestito dal gateway per Domoticz. Con 0 lo disabilita; il bridge Matter è configurato separatamente.'],
		store:['Private persistent directory for Matter fabrics and endpoint identities. This is not the gateway YAML location. Keep it across restarts to preserve pairing.','Directory privata persistente per fabric Matter e identità degli endpoint. Non è il percorso del file YAML del gateway. Conservarla tra i riavvii per mantenere gli abbinamenti.'],
		advertise:['Announce the Matter bridge using DNS-SD/mDNS. Disabling announcements does not disable direct-IP Matter traffic.','Annuncia il bridge Matter tramite DNS-SD/mDNS. Disabilitare gli annunci non disabilita il traffico Matter via IP diretto.'],
		mdns_backend:['DNS-SD publisher: auto chooses an available compiled backend; builtin uses the internal responder. Other choices require the matching build feature.','Publisher DNS-SD: auto sceglie un backend disponibile nella build; builtin usa il responder interno. Gli altri richiedono la relativa funzionalità compilata.'],
		mdns_hostname:['Single DNS host label, up to 63 letters/digits/hyphens, without .local. Empty uses the build default.','Singola etichetta DNS: massimo 63 lettere/cifre/trattini, senza .local. Vuoto usa il valore predefinito della build.'],
		mdns_interface:['Network interface used for mDNS, for example lan. Empty selects automatically. This is not an IP address.','Interfaccia di rete per mDNS, ad esempio lan. Vuota: selezione automatica. Non è un indirizzo IP.'],
		baudrate:['Serial speed in bits per second. Match a USB/UART adapter to its firmware. Native ESP32-C3 USB Serial/JTAG ignores host baudrate.','Velocità seriale in bit al secondo. Un adattatore USB/UART deve corrispondere al firmware; USB Serial/JTAG nativo ESP32-C3 ignora il baudrate host.'],
		command_timeout_ms:['Maximum wait in milliseconds for a firmware command response. Too short can cause timeouts on a busy USB link.','Attesa massima in millisecondi della risposta a un comando firmware. Un valore troppo basso può causare timeout su USB occupata.'],
		reconnect_delay_ms:['Wait in milliseconds before retrying a failed serial connection.','Attesa in millisecondi prima di ritentare una connessione seriale fallita.'],
		reset_on_open:['Pulse DTR/RTS when opening the serial device. This can reset the ESP32; leave off unless required by your adapter.','Impulso DTR/RTS all’apertura della seriale: può resettare ESP32. Lasciare disattivo se non richiesto dall’adattatore.'],
		phy_1m:['Receive standard Bluetooth LE 1M advertisements. Independent of payload format.','Riceve advertisement Bluetooth LE 1M standard. Indipendente dal formato dei dati.'],
		phy_coded:['Receive long-range Coded PHY advertisements. Requires compatible adapter firmware and sensors; does not change sensor firmware.','Riceve advertisement Coded PHY long-range. Richiede firmware adattatore e sensori compatibili; non modifica il firmware del sensore.'],
		window_1m:['1M scan window in units of 0.625 milliseconds; 320 means 200 ms.','Finestra di scansione 1M in unità di 0,625 millisecondi: 320 equivale a 200 ms.'],
		window_coded:['Coded scan window in units of 0.625 milliseconds; 64 means 40 ms.','Finestra di scansione Coded in unità di 0,625 millisecondi: 64 equivale a 40 ms.'],
		active_scan:['Request scan responses from advertisers. This adds radio traffic; passive scanning only listens.','Richiede scan response ai dispositivi. Aumenta il traffico radio; la scansione passiva si limita all’ascolto.'],
		dup_filter:['Ask adapter firmware to suppress duplicate advertisements. This can reduce repeated values; it is not a database flush interval.','Chiede al firmware di sopprimere advertisement duplicati. Può ridurre i valori ripetuti; non è l’intervallo di scrittura del database.'],
		discard_random:['Discard BLE random addresses. Some legitimate sensors use random addresses; enabling this can hide them.','Scarta indirizzi BLE casuali. Alcuni sensori legittimi li usano: abilitarlo può nasconderli.'],
		discard_rpa:['Discard resolvable private BLE addresses, which may rotate over time.','Scarta indirizzi BLE privati risolvibili, che possono cambiare nel tempo.'],
		mac:['Bluetooth advertiser MAC: 12 hexadecimal digits, optionally separated by colons. Discovery fills the observed address automatically.','MAC del trasmettitore Bluetooth: 12 cifre esadecimali, con separatori opzionali. Discovery compila l’indirizzo osservato.'],
		label:['Friendly device name shared with frontends. Inside a rule this labels the proposed derived attribute.','Nome leggibile del dispositivo condiviso con i frontend. In una regola etichetta l’attributo derivato proposto.'],
		manufacturer:['Physical device manufacturer, if known. Leave empty rather than guessing from the address-block vendor.','Produttore fisico, se noto. Lasciare vuoto invece di dedurlo dal titolare del blocco MAC.'],
		model:['Physical device model, if known. It does not select the decoder.','Modello fisico, se noto. Non seleziona il decoder.'],
		firmware_version:['Known physical sensor firmware version, not the gateway or BLE protocol version.','Versione nota del firmware del sensore fisico, non del gateway o protocollo BLE.'],
		bindkey:['AES-128 key for encrypted advertisements: exactly 32 hexadecimal digits. Not needed for unencrypted packets. Never share exported YAML containing keys.','Chiave AES-128 per advertisement cifrati: esattamente 32 cifre esadecimali. Non serve per pacchetti in chiaro. Non condividere YAML esportati contenenti chiavi.'],
		format:['Empty detects the payload format automatically. Force a format only if you know the actual sensor protocol; it does not choose the radio PHY.','Vuoto rileva automaticamente il formato. Forzarlo solo conoscendo il protocollo effettivo; non seleziona la PHY radio.'],
		attribute:['Canonical decoded measurement name, for example temperature, humidity, battery_level or opened. An attribute must exist in received data to produce values.','Nome canonico della misura decodificata, ad esempio temperature, humidity, battery_level o opened. Deve esistere nei dati ricevuti per produrre valori.'],
		child:['Optional MySensors child ID, 0-255. Keep existing IDs stable to preserve controller device associations.','ID child MySensors opzionale, 0-255. Conservare gli ID esistenti per mantenere le associazioni nel controller.'],
		kind:['Optional MySensors type override. Empty uses the supported attribute mapping.','Override opzionale del tipo MySensors. Vuoto usa la mappatura prevista per l’attributo.'],
		name:['Name of the proposed derived attribute. Rules are stored and validated but are not executed in this daemon.','Nome dell’attributo derivato proposto. Le Rules sono salvate e validate ma non eseguite da questo daemon.'],
		source:['Decoded attribute watched by the proposed rule. Rules are not executed in this version.','Attributo decodificato osservato dalla regola proposta. Le Rules non sono eseguite in questa versione.'],
		equals:['Comparison value for the proposed rule; empty means any change. Definitions only, not an active automation.','Valore di confronto proposto; vuoto significa qualsiasi variazione. Solo definizione, non automazione attiva.'],
		after_s:['Proposed rule delay in seconds. A timer definition requires a positive value; rules are not executed.','Ritardo proposto in secondi. Un timer richiede valore positivo; le Rules non sono eseguite.'],
		mirror:['Proposed immediate comparison mode without a timer. Rules are not executed.','Modalità proposta di confronto immediato senza timer. Le Rules non sono eseguite.'],
		log_level:['Minimum logging detail: off, error, warn, info, debug or trace. Reload logging applies only logging/diagnostic settings, not scanner/devices/frontends.','Dettaglio log: off, error, warn, info, debug o trace. Reload logging applica solo log/diagnostica, non scanner/dispositivi/frontend.'],
		tx_hex:['Log raw serial transmissions. Diagnostic dumps can contain sensitive device data; enable only when needed.','Registra trasmissioni seriali grezze. I dump possono contenere dati sensibili: abilitare solo se necessario.'],
		rx_hex:['Log raw serial receive chunks, including noise and incomplete frames. Can produce large sensitive logs.','Registra blocchi seriali ricevuti, anche rumore e frame incompleti. Può produrre log voluminosi e sensibili.'],
		decode:['Log codec field decoding details. High volume; use for diagnosis, not normal operation.','Registra dettagli dei campi decodificati. Alto volume: usare per diagnosi, non funzionamento ordinario.'],
		phy:['Log reception PHY and decoding status for advertisements, including unconfigured devices.','Registra PHY di ricezione ed esito decodifica degli advertisement, anche di dispositivi non configurati.']
	};
	function fieldExplanation(key,scope) {
		if(scope==='device.rules[]'&&key==='enabled')return helpLanguage==='it'?'Abilita questa regola e il relativo webhook dopo il salvataggio e il riavvio del servizio.':'Enable this availability rule and its webhook after saving and restarting the service.';
		if(scope==='device.rules[].webhook'&&key==='token')return helpLanguage==='it'?'Token privato: Bearer per ntfy o chiave applicazione Gotify. Inviato solo negli header HTTPS, mai nella URL o nello stato.':'Private ntfy bearer or Gotify application token. Sent only in HTTPS headers, never in URLs or saved episode state.';
		if(scope==='device.rules[].webhook'&&key==='timeout_ms')return helpLanguage==='it'?'Timeout HTTPS in millisecondi (100-10000). Le richieste non bloccano la ricezione BLE.':'HTTPS timeout in milliseconds (100-10000). Requests do not block BLE reception.';
		if(scope==='frontends.sqlite.maintenance'&&key==='enabled')return historyUi.warning;
		if(scope==='frontends.sqlite.maintenance'&&key==='batch_size')return helpLanguage==='it'?'Massimo di frame trasferiti o campioni esaminati per blocco (1-1000). Non è il batch del ricevitore.':'Maximum frames archived or samples examined per chunk (1-1000). Independent of receiver batching.';
		if(key==='port'&&scope==='serial')return helpLanguage==='it'?'Percorso della seriale attiva, ad esempio /dev/ttyACM0. Richiede salvataggio e riavvio.':'Active serial device path, for example /dev/ttyACM0. Save and restart to apply.';
		if(key==='filter_known_devices')return ht.filterKnown+' '+ht.filterAll;
		if(['whitelist','blacklist'].includes(key))return ht.filterList;
		const text=parameterHelp[key];
		return text?text[helpLanguage==='it'?1:0]:title(key);
	}
	function fieldHelp(label,key,scope) {
		const text=fieldExplanation(key,scope);
		label.title=text;
		const heading=document.createElement('span');heading.className='bbFieldName';heading.append(title(key));
		const help=button('?',event=>{event.preventDefault();element('bbParameterTitle').textContent=title(key);element('bbParameterPath').textContent=(scope?scope+'.':'')+key;element('bbParameterText').textContent=text;element('bbParameterDialog').showModal();},text);
		help.className='bbParameterHelp';help.setAttribute('aria-label',ui.help+': '+title(key));heading.append(help);label.append(heading);
	}
	/** Cards that contain an "enabled" checkbox get a background that shows at
	 *  a glance whether the feature inside them is active. */
	function toggleGroup(group,value,scope) {
		group.classList.add('bbToggled');
		const sync=()=>{
			const on=!!value.enabled;
			group.classList.toggle('bbOn',on);
			group.classList.toggle('bbOff',!on);
			group.classList.toggle('bbInactive',!on);
			const badge=group.querySelector('[data-enabledBadge]');
			if(badge)badge.textContent=' · '+(on?ui.enabled:ui.disabled);
		};
		const control=group.querySelector('input[type=checkbox][data-parameter="'+scope+'.enabled"]');
		if(control)control.addEventListener('change',sync);
		sync();
	}
	/** Documentation for the YAML editor: keys that exist only in the file and
	 *  are not rendered as form fields inherit their text from parameterHelp. */
	const yamlHelp={
		version:['Schema version written by the daemon. Do not edit it by hand: a different value can invalidate the file.','Versione dello schema scritta dal daemon. Non modificarla a mano: un valore diverso può invalidare il file.'],
		serial:['Serial link to the BLE adapter: device path, baud rate and timeouts.','Collegamento seriale all’adattatore BLE: percorso, baud rate e timeout.'],
		scanner:['BLE advertisement reception: PHY, scan windows, duplicate filter and MAC allow/deny lists.','Ricezione degli advertisement BLE: PHY, finestre di scansione, filtro duplicati e liste MAC.'],
		devices:['Configured sensors. Each entry binds one MAC address to a wire format, a bind key and the exposed attributes.','Sensori configurati. Ogni voce associa un MAC a formato dati, bind key e attributi esposti.'],
		expose:['Attributes published for this device as MySensors/Matter endpoints. Other decoded values are stored anyway.','Attributi pubblicati per questo dispositivo come endpoint MySensors/Matter. Gli altri valori decodificati vengono salvati comunque.'],
		frontends:['Optional consumers of the decoded values: SQLite history, InfluxDB, MySensors, MQTT and Matter.','Consumatori opzionali dei valori decodificati: storico SQLite, InfluxDB, MySensors, MQTT e Matter.'],
		influx:['InfluxDB 3 HTTP writer: endpoint, database, measurement and batching.','Scrittura su InfluxDB 3 via HTTP: endpoint, database, measurement e batching.'],
		sqlite:['Local SQLite history: database path, batching and retention maintenance.','Storico SQLite locale: percorso del database, batching e manutenzione della conservazione.'],
		maintenance:['Background consolidation of old complete frames into per-series samples.','Consolidamento in background dei vecchi frame completi in campioni per serie.'],
		policies:['Retention overrides for one attribute or one MAC address.','Eccezioni di conservazione per un attributo o un MAC.'],
		tiers:['Age bands of a progressive policy: each band keeps one sample per interval, after the last band numeric samples expire.','Fasce di età di una politica progressiva: ogni fascia conserva un campione per intervallo, oltre l’ultima i campioni numerici scadono.'],
		mode:['keep_all keeps every sample, progressive applies the age bands, discard removes archived numeric samples.','keep_all conserva ogni campione, progressive applica le fasce di età, discard elimina i campioni numerici archiviati.'],
		mysensors:['MySensors/Domoticz gateway frontend on a serial or TCP socket.','Frontend gateway MySensors/Domoticz su seriale o socket TCP.'],
		mqtt:['MQTT publisher, optionally backed by a gateway-managed local broker.','Publisher MQTT, con broker locale opzionale gestito dal gateway.'],
		matter:['Matter bridge published over IPv6, with its own fabric store.','Bridge Matter pubblicato su IPv6, con il proprio store di fabric.'],
		diagnostics:['Diagnostic trace switches for the daemon log. High volume: enable only while debugging.','Interruttori di traccia diagnostica del log. Alto volume: attivare solo durante il debug.'],
		automation:['Legacy automation block kept for compatibility: it is validated but no longer executed.','Blocco di automazione legacy mantenuto per compatibilità: viene validato ma non più eseguito.'],
		availability_state_file:['Persistent JSON file with the last notified availability episode, so a restart does not send duplicate alerts.','File JSON persistente con l’ultimo episodio di disponibilità notificato, così un riavvio non invia allarmi duplicati.'],
		rules:['Availability rules of this device: attribute to watch, maximum silence and webhook to notify.','Regole di disponibilità del dispositivo: attributo osservato, silenzio massimo e webhook da notificare.'],
		webhook:['HTTPS notification destination of this rule (ntfy, Gotify or a generic REST call).','Destinazione HTTPS delle notifiche di questa regola (ntfy, Gotify o REST generico).'],
		state_file:['Legacy per-automation state file, superseded by availability_state_file.','File di stato legacy dell’automazione, sostituito da availability_state_file.'],
		id:['Stable rule identifier used to remember which alerts were already delivered. Keep it unique.','Identificatore stabile della regola, usato per ricordare quali allarmi sono già stati consegnati. Deve essere univoco.']
	};
	let yamlLines=[];
	function buildYamlLines(text) {
		const stack=[];yamlLines=[];
		String(text||'').split('\n').forEach(line=>{
			const match=/^(\s*)(?:-\s+)?([A-Za-z0-9_]+):(\s|$)/.exec(line);
			if(!match){yamlLines.push(null);return;}
			const indent=match[1].length,key=match[2];
			while(stack.length&&stack[stack.length-1].indent>=indent)stack.pop();
			const chain=stack.map(entry=>entry.key);
			const start=line.indexOf(key,match[1].length);
			yamlLines.push({key,chain,start,end:start+key.length});
			stack.push({indent,key});
		});
	}
	function yamlScope(chain) {
		const last=chain[chain.length-1]||'';
		if(chain.includes('webhook'))return 'device.rules[].webhook';
		if(chain.includes('rules'))return 'device.rules[]';
		if(chain.includes('maintenance')||chain.includes('policies')||chain.includes('tiers'))return 'frontends.sqlite.maintenance';
		if(chain.includes('scanner'))return 'scanner';
		if(chain.includes('serial')||last==='serial')return 'serial';
		if(chain.includes('frontends'))return 'frontends';
		return '';
	}
	function yamlExplanation(entry) {
		const own=yamlHelp[entry.key];
		if(own)return own[helpLanguage==='it'?1:0];
		return fieldExplanation(entry.key,yamlScope(entry.chain));
	}
	function yamlHover(event) {
		if(!yamlEditor)return;
		const position=yamlEditor.renderer.screenToTextCoordinates(event.clientX,event.clientY);
		const entry=yamlLines[position.row];
		if(!entry||position.column<entry.start||position.column>=entry.end){hidePacketTooltip();return;}
		const tooltip=element('bbFieldTooltip');
		tooltip.querySelector('strong').textContent=entry.key;
		tooltip.querySelector('span').textContent=yamlExplanation(entry);
		tooltip.hidden=false;
		const bounds=tooltip.getBoundingClientRect();
		tooltip.style.left=Math.max(8,Math.min(event.clientX+12,innerWidth-bounds.width-8))+'px';
		tooltip.style.top=Math.max(8,event.clientY+bounds.height+18<innerHeight?event.clientY+18:event.clientY-bounds.height-12)+'px';
	}
	const uiNotes=({en:{yamlHint:'Hover a key to read its documentation. Ctrl+S saves the draft; edits stay in memory until you press Save YAML.',yamlDiscard:'Discard the YAML edits and reload the current draft?',yamlReverted:'YAML reloaded from the current draft'},it:{yamlHint:'Passa il mouse su una chiave per leggerne la documentazione. Ctrl+S salva la bozza; le modifiche restano in memoria finché non premi Save YAML.',yamlDiscard:'Scartare le modifiche allo YAML e ricaricare la bozza corrente?',yamlReverted:'YAML ricaricato dalla bozza corrente'},de:{yamlHint:'Mit der Maus über einen Schlüssel fahren, um die Dokumentation zu lesen. Ctrl+S speichert den Entwurf; Änderungen bleiben bis Save YAML im Speicher.',yamlDiscard:'YAML-Änderungen verwerfen und den aktuellen Entwurf neu laden?',yamlReverted:'YAML aus dem aktuellen Entwurf neu geladen'},fr:{yamlHint:'Survolez une clé pour lire sa documentation. Ctrl+S enregistre le brouillon ; les modifications restent en mémoire jusqu’à Save YAML.',yamlDiscard:'Abandonner les modifications YAML et recharger le brouillon actuel ?',yamlReverted:'YAML rechargé depuis le brouillon actuel'},es:{yamlHint:'Pase el ratón sobre una clave para leer su documentación. Ctrl+S guarda el borrador; los cambios quedan en memoria hasta pulsar Save YAML.',yamlDiscard:'¿Descartar los cambios YAML y recargar el borrador actual?',yamlReverted:'YAML recargado desde el borrador actual'}})[helpLanguage]||{yamlHint:'Hover a key to read its documentation. Ctrl+S saves the draft; edits stay in memory until you press Save YAML.',yamlDiscard:'Discard the YAML edits and reload the current draft?',yamlReverted:'YAML reloaded from the current draft'};
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
	async function api(action, body, params = {}, keepalive = false) {
		const url = new URL('/cgi-bin/extra/ble2uart_gateway/api', location.href);
		url.search = new URLSearchParams({ajax:'1', action, ...params}).toString();
		const response = await fetch(url, {method: ['read','status','attributes','history-presets','availability-presets','availability-status'].includes(action) ? 'GET' : 'POST', credentials:'same-origin', cache:'no-store', keepalive, headers:body ? {'Content-Type':'application/json'} : {}, body:body ? JSON.stringify(body) : undefined});
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
		['bbSave','bbCheck','bbReload','bbLogging','bbYamlSave'].forEach(id => element(id).disabled = true);
		try {await action();} catch (error) {message(error.message, true);} finally {busy = false; ['bbSave','bbCheck','bbReload','bbLogging','bbYamlSave'].forEach(id => element(id).disabled = !config);}
	}
	async function confirmAction(text, request) {
		const preview=element('bbConfirmRequest');
		preview.hidden=request===undefined;
		if(request!==undefined){
			if(!commandEditors.bbConfirmRequest)commandEditors.bbConfirmRequest=await jsonEditor('bbConfirmRequest');
			setCommandOutput('bbConfirmRequest',request);
		}
		return new Promise(resolve => {
			const dialog = element('bbConfirm'); element('bbConfirmText').textContent = text;
			const finish = answer => {dialog.close(); resolve(answer);};
			element('bbConfirmOk').onclick = () => finish(true);
			element('bbConfirmCancel').onclick = () => finish(false);
			dialog.oncancel = event => {event.preventDefault(); finish(false);};
			dialog.showModal();
			if(request!==undefined)commandEditors.bbConfirmRequest.resize(true);
		});
	}
	const commandTranslations = {
		en: {tab:'Commands',type:'Command',send:'Send command',refresh:'Refresh radio status',note:'Temporary commands pause scanning and restore it afterwards, including on error. TXADV start leaves scanning OFF until explicitly restarted. Commands use the running daemon, not unsaved settings.',confirm:'Send this command to the device? Writes and pairing can change the device. TXADV start stops scanning until you explicitly restart it.',pending:'Command running; do not retry while awaiting its result.',done:'Command completed; inspect the confirmation level below.',diagnostic:'Firmware diagnostics',gatt:'BLE GATT transaction',start:'Start TXADV (leave scan OFF)',stop:'Stop TXADV (leave scan OFF)',scanStart:'Start configured scan (stop TXADV)',scanStop:'Stop scan',name:'Diagnostic',pin:'GPIO pin',mac:'Peer MAC',addr_type:'Address type (0 public, 1 random)',coded:'Connect on Coded PHY',operation:'GATT operation',handle:'ATT handle (decimal, reads/writes only)',value:'Write value (hex, at most 20 bytes)',timeout_ms:'Transaction timeout (100-30000 ms)',phy:'TX PHY (0 legacy 1M, 1 extended 1M, 2 coded)',interval_units:'TX interval (0.625 ms units, minimum 32)',data:'Advertisement data (hex, at most 31 bytes)'},
		de: {tab:'Befehle',type:'Befehl',send:'Befehl senden',refresh:'Funkstatus aktualisieren',note:'Temporäre Befehle pausieren den Scan und stellen ihn auch bei Fehlern wieder her. TXADV lässt den Scan bis zum manuellen Neustart AUS. Es gelten die laufenden Einstellungen.',confirm:'Befehl senden? Schreiben und Pairing können das Gerät ändern. TXADV stoppt den Scan bis zum manuellen Neustart.',pending:'Befehl läuft; nicht erneut senden.',done:'Befehl beendet; Bestätigungsstufe unten prüfen.',diagnostic:'Firmware-Diagnose',gatt:'BLE-GATT-Transaktion',start:'TXADV starten (Scan AUS)',stop:'TXADV stoppen (Scan bleibt AUS)',scanStart:'Scan starten (TXADV stoppen)',scanStop:'Scan stoppen',name:'Diagnose',pin:'GPIO-Pin',mac:'Geräte-MAC',addr_type:'Adresstyp (0 öffentlich, 1 zufällig)',coded:'Coded-PHY-Verbindung',operation:'GATT-Operation',handle:'ATT-Handle (dezimal, nur Lesen/Schreiben)',value:'Schreibwert (Hex, maximal 20 Bytes)',timeout_ms:'Zeitlimit (100-30000 ms)',phy:'TX-PHY (0 Legacy 1M, 1 Extended 1M, 2 Coded)',interval_units:'TX-Intervall (0,625 ms, mindestens 32)',data:'Advertisement-Daten (Hex, maximal 31 Bytes)'},
		it: {tab:'Comandi',type:'Comando',send:'Invia comando',refresh:'Aggiorna stato radio',note:'I comandi temporanei sospendono lo scan e lo ripristinano anche in caso di errore. TXADV lascia lo scan SPENTO fino a un riavvio esplicito. Si usano le impostazioni del daemon, non le modifiche non salvate.',confirm:'Inviare il comando? Scritture e pairing possono modificare il dispositivo. TXADV interrompe lo scan fino al riavvio esplicito.',pending:'Comando in corso; non reinviarlo in attesa del risultato.',done:'Comando terminato; verificare il livello di conferma qui sotto.',diagnostic:'Diagnostica firmware',gatt:'Transazione BLE GATT',start:'Avvia TXADV (scan SPENTO)',stop:'Ferma TXADV (scan resta SPENTO)',scanStart:'Avvia scan configurato (ferma TXADV)',scanStop:'Ferma scan',name:'Diagnostica',pin:'Pin GPIO',mac:'MAC destinatario',addr_type:'Tipo indirizzo (0 pubblico, 1 casuale)',coded:'Connessione su PHY Coded',operation:'Operazione GATT',handle:'Handle ATT (decimale, solo letture/scritture)',value:'Valore da scrivere (hex, massimo 20 byte)',timeout_ms:'Timeout transazione (100-30000 ms)',phy:'PHY TX (0 legacy 1M, 1 extended 1M, 2 coded)',interval_units:'Intervallo TX (unità 0,625 ms, minimo 32)',data:'Dati advertisement (hex, massimo 31 byte)'},
		fr: {tab:'Commandes',type:'Commande',send:'Envoyer la commande',refresh:'Actualiser la radio',note:'Les commandes temporaires suspendent puis rétablissent le scan, même en cas d’erreur. TXADV laisse le scan ARRÊTÉ jusqu’au redémarrage explicite. Les paramètres actifs du daemon sont utilisés.',confirm:'Envoyer cette commande ? Écriture et appairage peuvent modifier le périphérique. TXADV arrête le scan jusqu’au redémarrage explicite.',pending:'Commande en cours ; ne pas la renvoyer.',done:'Commande terminée ; vérifier le niveau de confirmation ci-dessous.',diagnostic:'Diagnostic firmware',gatt:'Transaction BLE GATT',start:'Démarrer TXADV (scan ARRÊTÉ)',stop:'Arrêter TXADV (scan reste ARRÊTÉ)',scanStart:'Démarrer le scan (arrêter TXADV)',scanStop:'Arrêter le scan',name:'Diagnostic',pin:'Broche GPIO',mac:'MAC du périphérique',addr_type:'Type d’adresse (0 publique, 1 aléatoire)',coded:'Connexion PHY Coded',operation:'Opération GATT',handle:'Handle ATT (décimal, lecture/écriture)',value:'Valeur (hex, 20 octets maximum)',timeout_ms:'Délai (100-30000 ms)',phy:'PHY TX (0 legacy 1M, 1 extended 1M, 2 coded)',interval_units:'Intervalle TX (0,625 ms, minimum 32)',data:'Données advertisement (hex, 31 octets maximum)'},
		es: {tab:'Comandos',type:'Comando',send:'Enviar comando',refresh:'Actualizar radio',note:'Los comandos temporales pausan el escaneo y lo restauran incluso si fallan. TXADV deja el escaneo APAGADO hasta reiniciarlo explícitamente. Se usan los ajustes activos del daemon.',confirm:'¿Enviar el comando? Escritura y emparejamiento pueden modificar el dispositivo. TXADV detiene el escaneo hasta reiniciarlo explícitamente.',pending:'Comando en curso; no volver a enviarlo.',done:'Comando terminado; comprobar el nivel de confirmación abajo.',diagnostic:'Diagnóstico del firmware',gatt:'Transacción BLE GATT',start:'Iniciar TXADV (escaneo APAGADO)',stop:'Detener TXADV (escaneo sigue APAGADO)',scanStart:'Iniciar escaneo (detener TXADV)',scanStop:'Detener escaneo',name:'Diagnóstico',pin:'Pin GPIO',mac:'MAC del dispositivo',addr_type:'Tipo de dirección (0 pública, 1 aleatoria)',coded:'Conexión PHY Coded',operation:'Operación GATT',handle:'Handle ATT (decimal, lectura/escritura)',value:'Valor (hex, máximo 20 bytes)',timeout_ms:'Tiempo límite (100-30000 ms)',phy:'PHY TX (0 legacy 1M, 1 extended 1M, 2 coded)',interval_units:'Intervalo TX (0,625 ms, mínimo 32)',data:'Datos advertisement (hex, máximo 31 bytes)'}
	};
	const gattTranslations = {
		en: {
			open:'Open BLE GATT session',sessionCommand:'GATT operation in open session',close:'Close GATT session',session:'Session token (returned by Open)',idle_timeout_ms:'Idle timeout (1000-300000 ms)',uuid:'Characteristic/descriptor UUID (leave handle 0)',handle:'ATT handle (decimal; 0 selects UUID)',value:'Write/request value (hex; 56 bytes, 58 without response)',prefix:'Notification prefix filter (hex; empty = any)',mode:'Subscription (0 disable, 1 notify, 2 indicate)',count:'Matching notifications to await (1-64)',codec:'Codec structure (empty = raw bytes)',offset:'Response bytes to skip before decoding',write_offset:'Decoded bytes to omit when writing (response-only fields)',write_prefix:'Write prefix (hex; empty = request value)',patch:'JSON patch (only existing fields)',invalidJson:'Enter a nonempty JSON object',
			atcRead:'Read ATC configuration (0x55)',atcPatch:'Apply ATC configuration patch (0x55)',request:'Request JSON',cancelled:'Command cancelled; nothing sent.',
			help:'Open a session to discover, subscribe, write and await notifications without reconnecting. Copy its token for CLI use and close it when finished. ATC buttons send the read or patch after confirmation, using the selected peer/session. Edit the patch in Ace; the initial ATC patch enables bt5phy and longrange. Verify the installed firmware and codec first. Coded PHY needs compatible ATC firmware (4.2+ for LYWSD03MMC); confirm it from received advertisements, not the connection PHY.',
			note:'Commands require the running daemon; the service stays active. GATT pauses scan and daemon-configured TXADV, then restores them on close or error. Discovery time is paused; other radio commands are blocked during an open session. TXADV start leaves scan OFF. No settings are saved and the service is not restarted.',closeFailed:'Page-exit GATT cleanup failed; the idle timeout remains active'
		},
		de: {
			open:'BLE-GATT-Sitzung öffnen',sessionCommand:'GATT-Operation in offener Sitzung',close:'GATT-Sitzung schließen',session:'Sitzungstoken (vom Öffnen)',idle_timeout_ms:'Inaktivitätslimit (1000-300000 ms)',uuid:'UUID von Merkmal/Deskriptor (Handle 0)',handle:'ATT-Handle (dezimal; 0 wählt UUID)',value:'Schreib-/Anfragewert (Hex; 56 Bytes, 58 ohne Antwort)',prefix:'Benachrichtigungspräfix (Hex; leer = alle)',mode:'Abonnement (0 aus, 1 Notify, 2 Indicate)',count:'Passende Benachrichtigungen (1-64)',codec:'Codec-Struktur (leer = Rohdaten)',offset:'Vor dem Dekodieren übersprungene Antwortbytes',write_offset:'Beim Schreiben ausgelassene dekodierte Antwortbytes',write_prefix:'Schreibpräfix (Hex; leer = Anfragewert)',patch:'JSON-Patch (nur vorhandene Felder)',invalidJson:'Ein nicht leeres JSON-Objekt eingeben',
			atcRead:'ATC-Konfiguration lesen (0x55)',atcPatch:'ATC-Konfigurationspatch anwenden (0x55)',request:'JSON-Anfrage',cancelled:'Befehl abgebrochen; nichts gesendet.',
			help:'Eine Sitzung öffnen, um ohne Neuverbindung zu suchen, abonnieren, schreiben und Benachrichtigungen abzuwarten. Token auch für CLI nutzbar; danach schließen. Die ATC-Tasten senden Lesen oder Patch nach Bestätigung an das gewählte Gerät bzw. die Sitzung. Patch in Ace bearbeiten; anfangs werden bt5phy und longrange aktiviert. Firmware und Codec vorher prüfen. Coded PHY erfordert passende ATC-Firmware (4.2+ bei LYWSD03MMC); empfangene Advertisements prüfen, nicht die Verbindungs-PHY.',
			note:'Befehle erfordern den laufenden Daemon; der Dienst bleibt aktiv. GATT pausiert Scan und vom Daemon konfiguriertes TXADV bis zum Schließen, auch bei Fehlern. Die Discovery-Zeit pausiert; andere Funkbefehle sind während der Sitzung gesperrt. TXADV-Start lässt den Scan AUS. Kein Speichern oder Dienstneustart.',closeFailed:'GATT-Bereinigung beim Seitenende fehlgeschlagen; Inaktivitätslimit bleibt aktiv'
		},
		it: {
			open:'Apri sessione BLE GATT',sessionCommand:'Operazione GATT nella sessione aperta',close:'Chiudi sessione GATT',session:'Token sessione (restituito da Apri)',idle_timeout_ms:'Timeout inattività (1000-300000 ms)',uuid:'UUID caratteristica/descrittore (lasciare handle 0)',handle:'Handle ATT (decimale; 0 seleziona UUID)',value:'Valore scrittura/richiesta (hex; 56 byte, 58 senza risposta)',prefix:'Prefisso notifiche (hex; vuoto = qualsiasi)',mode:'Sottoscrizione (0 disabilita, 1 notify, 2 indicate)',count:'Notifiche corrispondenti da attendere (1-64)',codec:'Struttura codec (vuota = byte grezzi)',offset:'Byte risposta da saltare prima della decodifica',write_offset:'Byte decodificati da omettere in scrittura (sola risposta)',write_prefix:'Prefisso scrittura (hex; vuoto = valore richiesta)',patch:'Patch JSON (solo campi esistenti)',invalidJson:'Inserire un oggetto JSON non vuoto',
			atcRead:'Leggi configurazione ATC (0x55)',atcPatch:'Applica patch configurazione ATC (0x55)',request:'Richiesta JSON',cancelled:'Comando annullato; nessun invio.',
			help:'Aprire una sessione per discovery, sottoscrizioni, scritture e attesa notifiche senza riconnettersi. Il token è utilizzabile dalla CLI; chiudere la sessione al termine. I pulsanti ATC inviano lettura o patch dopo conferma, usando il destinatario o la sessione selezionati. Modificare la patch in Ace; quella ATC iniziale abilita bt5phy e longrange. Verificare prima firmware installato e codec. Coded PHY richiede firmware ATC compatibile (4.2+ per LYWSD03MMC); verificarlo negli advertisement ricevuti, non nella PHY della connessione.',
			note:'I comandi richiedono il daemon in esecuzione; il servizio resta attivo. GATT sospende scan e TXADV configurato dal daemon e li ripristina alla chiusura o in caso di errore. Il tempo di Discovery è sospeso; altri comandi radio sono bloccati durante la sessione. Avviare TXADV lascia lo scan SPENTO. Nessun salvataggio o riavvio del servizio.',closeFailed:'Pulizia GATT in uscita dalla pagina fallita; resta attivo il timeout di inattività'
		},
		fr: {
			open:'Ouvrir une session BLE GATT',sessionCommand:'Opération GATT dans la session ouverte',close:'Fermer la session GATT',session:'Jeton de session (fourni à l’ouverture)',idle_timeout_ms:'Délai d’inactivité (1000-300000 ms)',uuid:'UUID caractéristique/descripteur (handle 0)',handle:'Handle ATT (décimal ; 0 sélectionne UUID)',value:'Valeur écrite/requête (hex ; 56 octets, 58 sans réponse)',prefix:'Préfixe des notifications (hex ; vide = toutes)',mode:'Abonnement (0 arrêt, 1 notify, 2 indicate)',count:'Notifications correspondantes attendues (1-64)',codec:'Structure codec (vide = octets bruts)',offset:'Octets de réponse à ignorer avant décodage',write_offset:'Octets décodés à omettre en écriture (réponse seule)',write_prefix:'Préfixe écrit (hex ; vide = requête)',patch:'Patch JSON (champs existants uniquement)',invalidJson:'Saisir un objet JSON non vide',
			atcRead:'Lire la configuration ATC (0x55)',atcPatch:'Appliquer le patch ATC (0x55)',request:'Requête JSON',cancelled:'Commande annulée ; aucun envoi.',
			help:'Ouvrir une session pour découvrir, s’abonner, écrire et attendre les notifications sans reconnexion. Le jeton fonctionne en CLI ; fermer ensuite. Les boutons ATC envoient lecture ou patch après confirmation vers le périphérique ou la session sélectionnés. Modifier le patch dans Ace ; le patch ATC initial active bt5phy et longrange. Vérifier firmware et codec. Coded PHY nécessite un firmware ATC compatible (4.2+ pour LYWSD03MMC) ; vérifier les advertisements reçus, pas la PHY de connexion.',
			note:'Les commandes nécessitent le daemon en cours ; le service reste actif. GATT suspend scan et TXADV configuré par le daemon, puis les rétablit à la fermeture ou sur erreur. Le temps Discovery est suspendu ; les autres commandes radio sont bloquées pendant la session. Démarrer TXADV laisse le scan ARRÊTÉ. Aucun enregistrement ni redémarrage du service.',closeFailed:'Échec du nettoyage GATT à la sortie ; le délai d’inactivité reste actif'
		},
		es: {
			open:'Abrir sesión BLE GATT',sessionCommand:'Operación GATT en sesión abierta',close:'Cerrar sesión GATT',session:'Token de sesión (devuelto al abrir)',idle_timeout_ms:'Tiempo de inactividad (1000-300000 ms)',uuid:'UUID de característica/descriptor (handle 0)',handle:'Handle ATT (decimal; 0 selecciona UUID)',value:'Valor escrito/solicitud (hex; 56 bytes, 58 sin respuesta)',prefix:'Prefijo de notificaciones (hex; vacío = todas)',mode:'Suscripción (0 desactivar, 1 notify, 2 indicate)',count:'Notificaciones coincidentes esperadas (1-64)',codec:'Estructura codec (vacía = bytes sin procesar)',offset:'Bytes de respuesta a omitir antes de decodificar',write_offset:'Bytes decodificados a omitir al escribir (solo respuesta)',write_prefix:'Prefijo escrito (hex; vacío = solicitud)',patch:'Parche JSON (solo campos existentes)',invalidJson:'Introducir un objeto JSON no vacío',
			atcRead:'Leer configuración ATC (0x55)',atcPatch:'Aplicar parche ATC (0x55)',request:'Solicitud JSON',cancelled:'Comando cancelado; no se ha enviado.',
			help:'Abrir una sesión para descubrir, suscribirse, escribir y esperar notificaciones sin reconectar. El token también sirve en CLI; cerrar al terminar. Los botones ATC envían lectura o parche tras confirmar, usando el dispositivo o la sesión seleccionados. Editar el parche en Ace; el inicial activa bt5phy y longrange. Verificar firmware y codec. Coded PHY necesita firmware ATC compatible (4.2+ para LYWSD03MMC); comprobar los advertisements recibidos, no la PHY de conexión.',
			note:'Los comandos necesitan el daemon en ejecución; el servicio sigue activo. GATT pausa escaneo y TXADV configurado por el daemon y los restaura al cerrar o fallar. Se pausa el tiempo de Discovery; otras órdenes de radio se bloquean durante la sesión. Iniciar TXADV deja el escaneo APAGADO. No se guarda ni reinicia el servicio.',closeFailed:'Falló la limpieza GATT al salir; sigue activo el tiempo de inactividad'
		}
	};
	const commandLanguage = (navigator.language || 'en').split('-')[0];
	const ct = {...(commandTranslations[commandLanguage] || commandTranslations.en),...(gattTranslations[commandLanguage] || gattTranslations.en)};
	let commandDraft, gattToken = '', commandRunning = false;
	let patchEditor=null, patchEditorLoading=null, patchText='{}', patchInitialized=false, syncingPatch=false;
	// Live command validation must not block the enclosing Freetz settings form.
	const commandForm=document.createElement('form');commandForm.id='bbCommandForm';commandForm.hidden=true;
	commandForm.onsubmit=event=>event.preventDefault();document.body.append(commandForm);
	const commandOptions = {
		name:['info','version','uart','rfsdk','vbat','gpio-events','gpio-status','gpio-read','analog-read','connection-status','txadv-status'],
		operation:['discover','read','write','write-without-response','read-descriptor','write-descriptor','mtu','unpair','subscribe','notifications','exchange','patch']
	};
	function validatePatch() {
		let result;
		try {
			const value=JSON.parse(patchEditor?patchEditor.getValue():patchText);
			result=value&&typeof value==='object'&&!Array.isArray(value)&&Object.keys(value).length?{value}:{error:ct.invalidJson};
		} catch(error) {
			if(!(error instanceof SyntaxError))throw error;
			result={error:ct.invalidJson+': '+error.message};
		}
		element('bbCommandPatchError').textContent=result.error||'';
		element('bbCommandPatchError').hidden=!result.error;
		if(patchEditor)patchEditor.session.setAnnotations(result.error?[{row:0,column:0,text:result.error,type:'error'}]:[]);
		return result;
	}
	function patchValue() {
		const result=validatePatch();
		if(result.error)throw new Error(result.error);
		return result.value;
	}
	function setPatch(value) {
		patchText=JSON.stringify(value,null,2);patchInitialized=true;
		if(patchEditor){syncingPatch=true;patchEditor.setValue(patchText,-1);syncingPatch=false;}
		commandDraft.patch=value;
		validatePatch();
	}
	function ensurePatchEditor() {
		if(!patchEditorLoading)patchEditorLoading=(async()=>{
			patchEditor=await jsonEditor('bbCmd_patch',false);patchEditor.setValue(patchText,-1);
			patchEditor.session.on('change',()=>{
				if(syncingPatch)return;
				patchText=patchEditor.getValue();patchInitialized=true;
				const result=validatePatch();
				if(!result.error&&commandDraft.operation==='patch')commandDraft.patch=result.value;
			});
			validatePatch();
		})().catch(error=>{patchEditorLoading=null;throw error;});
		return patchEditorLoading.then(()=>{patchEditor.setReadOnly(commandRunning);patchEditor.resize(true);});
	}
	function commandBusy(pending) {
		commandRunning=pending;
		for(const id of ['bbCommandSend','bbAtcRead','bbAtcPatch','bbCommandType','bbRadioRefresh'])element(id).disabled=pending;
		element('bbCommandFields').querySelectorAll('input,select').forEach(input=>input.disabled=pending);
		if(patchEditor)patchEditor.setReadOnly(pending);
	}
	function renderCommand(previous = {}) {
		const type = element('bbCommandType').value, command = type === 'gatt-session' ? 'gatt' : type;
		commandDraft = command === 'diagnostic' ? {command,name:'info',pin:0} : type === 'gatt-open' ? {command,mac:'',addr_type:0,coded:false,timeout_ms:10000,idle_timeout_ms:60000} : type === 'gatt-close' ? {command,session:gattToken} : type === 'txadv-start' ? {command,phy:0,interval_units:160,data:''} : {command};
		if(command === 'gatt') {
			const operation = previous.operation || 'discover';
			Object.assign(commandDraft,type === 'gatt-session' ? {session:gattToken} : {mac:'',addr_type:0,coded:false},{operation,timeout_ms:10000});
			if(!['discover','mtu','unpair'].includes(operation))Object.assign(commandDraft,{handle:0,uuid:''});
			if(['write','write-descriptor','write-without-response','exchange','patch'].includes(operation))commandDraft.value='';
			if(['subscribe','exchange','patch'].includes(operation))commandDraft.mode=1;
			if(['notifications','exchange','patch'].includes(operation))Object.assign(commandDraft,{prefix:'',count:1});
			if(['read','read-descriptor','notifications','exchange','patch'].includes(operation))Object.assign(commandDraft,{codec:'',offset:0});
			if(operation==='patch')Object.assign(commandDraft,{write_offset:0,write_prefix:'',patch:{}});
		}
		Object.keys(commandDraft).forEach(key=>{if(key!=='command'&&Object.hasOwn(previous,key))commandDraft[key]=previous[key];});
		const parent = element('bbCommandFields'); parent.replaceChildren();
		Object.entries(commandDraft).filter(([key])=>key!=='command'&&key!=='patch').forEach(([key,value])=>{
			const label=document.createElement('label');label.className='bbField';label.append(ct[key]);
			const input=document.createElement(commandOptions[key]?'select':'input');
			if(commandOptions[key])commandOptions[key].forEach(option=>input.add(new Option(option,option)));
			else input.type=typeof value==='boolean'?'checkbox':typeof value==='number'?'number':'text';
			input.id='bbCmd_'+key;input.title=ct[key];input.autocomplete='off';
			if(key==='mac'||key==='session')input.required=true;
			input.setAttribute('form',commandForm.id);
			if(input.type==='checkbox')input.checked=value;else input.value=value;
			if(input.type==='number'){input.min='0';input.step='1';}
			if(key==='timeout_ms'){input.min='100';input.max='30000';}
			if(key==='idle_timeout_ms'){input.min='1000';input.max='300000';}
			if(key==='interval_units'){input.min='32';input.max='65535';}
			if(key==='handle')input.max='65535';
			if(key==='addr_type')input.max='1';
			if(key==='phy')input.max='2';
			if(key==='mode')input.max='2';
			if(key==='count'){input.min='1';input.max='64';}
			if(['offset','write_offset'].includes(key))input.max='197';
			input.oninput=()=>{
				commandDraft[key]=input.type==='checkbox'?input.checked:input.type==='number'?Number(input.value):input.value;
				if(key==='operation')renderCommand(commandDraft);
			};
			label.append(input);parent.append(label);
		});
		element('bbCommandPatch').hidden=commandDraft.operation!=='patch';
		if(commandDraft.operation==='patch')ensurePatchEditor().catch(error=>{element('bbCommandPatchError').textContent=error.message;element('bbCommandPatchError').hidden=false;message(error.message,true);});
		commandBusy(commandRunning);
	}
	async function radioStatus() {
		const status=await api('status');setCommandOutput('bbRadio',{connected:status.connected,...status.radio});
		if(status.radio?.gatt===null&&gattToken){
			if(commandDraft?.session===gattToken){commandDraft.session='';const input=element('bbCmd_session');if(input)input.value='';}
			gattToken='';
		}
		await ensureCommandEditors();
		if(commandDraft.operation==='patch')await ensurePatchEditor();
	}
	element('bbCommandsTab').textContent=ct.tab;element('bbCommandTypeLabel').textContent=ct.type;element('bbCommandNote').textContent=ct.note;
	element('bbGattHelp').textContent=ct.help;
	element('bbCommandPatchLabel').textContent=ct.patch;element('bbCmd_patch').title=ct.patch;element('bbCmd_patch').setAttribute('aria-label',ct.patch);
	element('bbCommandRequestLabel').textContent=ct.request;
	for(const id of ['bbCommandRequest','bbConfirmRequest'])element(id).setAttribute('aria-label',ct.request);
	element('bbCommandRequestDetails').addEventListener('toggle',()=>commandEditors.bbCommandRequest?.resize(true));
	[['diagnostic','diagnostic'],['gatt','gatt'],['gatt-open','open'],['gatt-session','sessionCommand'],['gatt-close','close'],['txadv-start','start'],['txadv-stop','stop'],['scan-start','scanStart'],['scan-stop','scanStop']].forEach(([value,key])=>element('bbCommandType').add(new Option(ct[key],value)));
	element('bbCommandType').title=ct.type;element('bbCommandType').onchange=()=>renderCommand();
	function prepareAtc(operation) {
		const previous=commandDraft,type=element('bbCommandType').value;
		const sessionMode=['gatt-session','gatt-close'].includes(type)||(!['gatt','gatt-open'].includes(type)&&!!gattToken);
		const session=['gatt-session','gatt-close'].includes(type)?previous.session:['gatt','gatt-open'].includes(type)?'':gattToken;
		const patch=operation==='patch'?(patchInitialized?patchValue():{flg2:{bt5phy:true,longrange:true}}):null;
		element('bbCommandType').value=sessionMode?'gatt-session':'gatt';
		const draft={operation,uuid:'1F1F',handle:0,value:'55',prefix:'55',codec:'cfg',offset:1,write_offset:1};
		if(sessionMode)draft.session=session;
		else for(const key of ['mac','addr_type','coded','timeout_ms'])if(Object.hasOwn(previous,key))draft[key]=previous[key];
		renderCommand(draft);
		if(patch)setPatch(patch);
	}
	for(const [id,key,operation] of [['bbAtcRead','atcRead','exchange'],['bbAtcPatch','atcPatch','patch']]){
		element(id).textContent=ct[key];element(id).title=ct.help;element(id).onclick=()=>run(()=>sendCommand(operation));
	}
	element('bbCommandSend').textContent=ct.send;element('bbCommandSend').title=ct.send;
	element('bbRadioRefresh').textContent=ct.refresh;element('bbRadioRefresh').title=ct.refresh;
	element('bbRadio').setAttribute('aria-label',ct.refresh);element('bbCommandResult').setAttribute('aria-label',ct.done);
	element('bbRadioRefresh').onclick=()=>run(radioStatus);
	async function sendCommand(atcOperation) {
		let sent=false;
		try {
			if(atcOperation)prepareAtc(atcOperation);
			if(!Array.from(element('bbCommandFields').querySelectorAll('input,select')).every(input=>input.reportValidity()))return;
			commandBusy(true);
			await ensureCommandEditors();
			if(commandDraft.operation==='patch')await ensurePatchEditor();
			const payload=copy(commandDraft);
			if(payload.operation==='patch')payload.patch=patchValue();
			if(payload.write_prefix==='')delete payload.write_prefix;
			setCommandOutput('bbCommandRequest',payload);element('bbCommandRequestDetails').open=true;
			commandEditors.bbCommandRequest.resize(true);
			if(!await confirmAction(ct.confirm,payload)){message(ct.cancelled);setCommandOutput('bbCommandResult',ct.cancelled,'text');return;}
			message(ct.pending);setCommandOutput('bbCommandResult','','text');sent=true;
			const response=await api('command',payload);setCommandOutput('bbCommandResult',response);message(ct.done);
			if(response.result?.session){gattToken=response.result.session;element('bbCommandType').value='gatt-session';renderCommand();}
			if(response.result?.confirmation==='disconnected'){gattToken='';element('bbCommandType').value='gatt-open';renderCommand();}
		}
		catch(error){setCommandOutput('bbCommandResult',error.message,'text');throw error;}
		finally{
			commandBusy(false);
			if(sent)try{await radioStatus();}catch(error){setCommandOutput('bbRadio',error.message,'text');message(error.message,true);}
		}
	}
	element('bbCommandSend').onclick=()=>run(()=>sendCommand());
	renderCommand();
	window.addEventListener('pagehide',()=>{if(gattToken)api('command',{command:'gatt-close',session:gattToken},{},true).catch(error=>console.warn(ct.closeFailed,error.message));});
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
	const historyTranslations={
		en:{maintenance:'Retention policies',policies:'Per-measurement retention',policiesHint:'Overrides for one attribute or one MAC address. Explicit rules win over the settings above; measurements without a policy are never consolidated.',policy:'Policy',attribute:'Attribute',mac:'MAC (empty = all devices)',mode:'History mode',keep:'Keep every sample, forever',progressive:'Progressive resolution',age:'Until age',spacing:'Sample interval',all:'Every sample',add:'Add policy',band:'Add age band',remove:'Remove',temperature:'Temperature preset',battery:'Battery preset',warning:'Irreversible consolidation: back up the database before enabling. Older full frames are replaced by related measurement series; discarded samples cannot be recovered.',expiry:'After the last age band: delete numeric samples.',units:['s','min','h','days','weeks','months'],close:'Close'},
		it:{maintenance:'Politiche di conservazione (retention)',policies:'Conservazione per singola misura',policiesHint:'Eccezioni per un singolo attributo o un singolo MAC. Le regole esplicite prevalgono sulle impostazioni qui sopra; le misure senza politica non vengono mai consolidate.',policy:'Politica',attribute:'Attributo',mac:'MAC (vuoto = tutti i dispositivi)',mode:'Trattamento storico',keep:'Conserva tutti i campioni, per sempre',progressive:'Risoluzione progressiva',age:'Fino all’età',spacing:'Intervallo campioni',all:'Tutti i campioni',add:'Aggiungi politica',band:'Aggiungi fascia',remove:'Rimuovi',temperature:'Preset temperatura',battery:'Preset batteria',warning:'Consolidamento irreversibile: eseguire un backup del database prima di abilitare. I vecchi frame completi vengono sostituiti da serie di misure correlate; i campioni scartati non sono recuperabili.',expiry:'Oltre l’ultima fascia: elimina i campioni numerici.',units:['s','min','h','giorni','settimane','mesi'],close:'Chiudi'},
		de:{maintenance:'Aufbewahrungsrichtlinien (Retention)',policies:'Aufbewahrung je Messwert',policiesHint:'Ausnahmen für einen Messwert oder eine MAC. Explizite Regeln gelten vor den Einstellungen oben; Messwerte ohne Richtlinie werden nie verdichtet.',policy:'Richtlinie',attribute:'Attribut',mac:'MAC (leer = alle Geräte)',mode:'Verlaufsmodus',keep:'Alle Werte unbegrenzt behalten',progressive:'Abgestufte Auflösung',age:'Bis zum Alter',spacing:'Werteintervall',all:'Alle Werte',add:'Richtlinie hinzufügen',band:'Altersstufe hinzufügen',remove:'Entfernen',temperature:'Temperaturvorgabe',battery:'Batterievorgabe',warning:'Nicht umkehrbare Verdichtung: Datenbank vorher sichern. Alte vollständige Frames werden durch verknüpfte Messreihen ersetzt; entfernte Werte sind nicht wiederherstellbar.',expiry:'Nach der letzten Altersstufe: numerische Werte löschen.',units:['s','min','h','Tage','Wochen','Monate'],close:'Schließen'},
		fr:{maintenance:'Politiques de rétention',policies:'Rétention par mesure',policiesHint:'Exceptions pour un attribut ou une adresse MAC. Les règles explicites priment sur les réglages ci-dessus ; les mesures sans politique ne sont jamais consolidées.',policy:'Politique',attribute:'Attribut',mac:'MAC (vide = tous)',mode:'Mode historique',keep:'Conserver tous les échantillons',progressive:'Résolution progressive',age:'Jusqu’à cet âge',spacing:'Intervalle',all:'Tous les échantillons',add:'Ajouter une politique',band:'Ajouter une tranche',remove:'Supprimer',temperature:'Profil température',battery:'Profil batterie',warning:'Consolidation irréversible : sauvegarder la base avant activation. Les anciens paquets complets sont remplacés par des séries liées ; les échantillons supprimés sont irrécupérables.',expiry:'Après la dernière tranche : supprimer les échantillons numériques.',units:['s','min','h','jours','semaines','mois'],close:'Fermer'},
		es:{maintenance:'Políticas de retención',policies:'Retención por medida',policiesHint:'Excepciones para un atributo o una MAC. Las reglas explícitas prevalecen sobre los ajustes anteriores; las medidas sin política nunca se consolidan.',policy:'Política',attribute:'Atributo',mac:'MAC (vacío = todos)',mode:'Modo histórico',keep:'Conservar todas las muestras',progressive:'Resolución progresiva',age:'Hasta esta edad',spacing:'Intervalo',all:'Todas las muestras',add:'Añadir política',band:'Añadir tramo',remove:'Eliminar',temperature:'Perfil temperatura',battery:'Perfil batería',warning:'Consolidación irreversible: hacer una copia antes de activar. Los paquetes antiguos se sustituyen por series relacionadas; las muestras eliminadas no se recuperan.',expiry:'Tras el último tramo: eliminar muestras numéricas.',units:['s','min','h','días','semanas','meses'],close:'Cerrar'}
	};
	const historyUi=historyTranslations[helpLanguage]||historyTranslations.en;
	const availabilityTranslations={
		en:{title:'Availability monitoring',rule:'Rule',add:'Add rule',remove:'Remove rule',test:'Test webhook',status:'Device availability status',confirm:'Send one test notification using this rule’s webhook? Device changes will not be saved.',webhook:'Webhook configuration',timeout:'Notify if no reading received for more than (seconds)'},
		it:{title:'Monitoraggio disponibilità',rule:'Regola',add:'Aggiungi regola',remove:'Elimina regola',test:'Prova webhook',status:'Stato disponibilità dispositivo',confirm:'Inviare una sola notifica di prova usando il webhook di questa regola? Le modifiche al dispositivo non verranno salvate.',webhook:'Configurazione webhook',timeout:'Notifica se il dato non perviene da oltre (secondi)'},
		de:{title:'Verfügbarkeitsüberwachung',rule:'Regel',add:'Regel hinzufügen',remove:'Regel entfernen',test:'Webhook testen',status:'Geräteverfügbarkeit',confirm:'Eine Testnachricht mit dem Webhook dieser Regel senden, ohne Änderungen zu speichern?',webhook:'Webhook-Konfiguration',timeout:'Benachrichtigen nach fehlender Messung (Sekunden)'},
		fr:{title:'Surveillance de disponibilité',rule:'Règle',add:'Ajouter une règle',remove:'Supprimer la règle',test:'Tester le webhook',status:'Disponibilité de l’appareil',confirm:'Envoyer une notification avec le webhook de cette règle sans enregistrer les modifications ?',webhook:'Configuration du webhook',timeout:'Notifier sans mesure depuis plus de (secondes)'},
		es:{title:'Supervisión de disponibilidad',rule:'Regla',add:'Añadir regla',remove:'Eliminar regla',test:'Probar webhook',status:'Disponibilidad del dispositivo',confirm:'¿Enviar una notificación con el webhook de esta regla sin guardar los cambios?',webhook:'Configuración del webhook',timeout:'Notificar sin lectura durante más de (segundos)'}
	};
	const availabilityUi=availabilityTranslations[helpLanguage]||availabilityTranslations.en;
	const notificationLabels={
		en:{message:'Notification message (empty = automatic)',recovery_message:'Recovery message (empty = automatic)',tgs:'tgs (override webhook tags)'},
		it:{message:'Messaggio notifica (vuoto = automatico)',recovery_message:'Messaggio di ripristino (vuoto = automatico)',tgs:'tgs (sostituisce tags del webhook)'},
		de:{message:'Nachricht (leer = automatisch)',recovery_message:'Entwarnungstext (leer = automatisch)',tgs:'tgs (überschreibt Webhook-Tags)'},
		fr:{message:'Message (vide = automatique)',recovery_message:'Message de rétablissement (vide = automatique)',tgs:'tgs (remplace les tags du webhook)'},
		es:{message:'Mensaje (vacío = automático)',recovery_message:'Mensaje de restablecimiento (vacío = automático)',tgs:'tgs (sustituye los tags del webhook)'}
	};
	Object.assign(labels,notificationLabels[helpLanguage]||notificationLabels.en);
	Object.assign(labels,{method:'REST method',content_type:'REST content type',body:'REST body template',header:'REST extra header (Name: value)',rules:availabilityUi.title,webhook:availabilityUi.webhook,startup_grace_s:helpLanguage==='it'?'Tolleranza iniziale (secondi)':'Startup grace (seconds)',stale_after_s:availabilityUi.timeout,notify_recovery:helpLanguage==='it'?'Notifica ripristino':'Notify recovery',provider:helpLanguage==='it'?'Servizio webhook':'Webhook provider',url:'HTTPS URL',max_attempts:helpLanguage==='it'?'Tentativi massimi per evento':'Maximum attempts per event',retry_s:helpLanguage==='it'?'Attesa tra tentativi (secondi)':'Retry interval (seconds)',ca_file:helpLanguage==='it'?'File CA PEM (opzionale)':'PEM CA file (optional)'});
	Object.assign(parameterHelp,{
		message:['Optional message transmitted verbatim for this rule’s alert, recovery and explicit webhook test. Empty or whitespace-only uses the corresponding automatic message. Up to 4096 UTF-8 bytes; multiline text is supported.','Messaggio opzionale trasmesso così com’è per allarme, ripristino e prova webhook di questa regola. Vuoto o composto solo da spazi usa il corrispondente messaggio automatico. Massimo 4096 byte UTF-8; sono consentite più righe.'],
		recovery_message:['Optional message sent only when a notified outage ends, so recovery and alert can say different things. Empty or whitespace-only uses the automatic recovery text. Up to 4096 UTF-8 bytes; it is sent only if “Notify recovery” is enabled and the stale alert was delivered.','Messaggio opzionale inviato solo quando un disservizio già notificato rientra, così allarme e ripristino possono avere testi diversi. Vuoto o composto solo da spazi usa il testo automatico di ripristino. Massimo 4096 byte UTF-8; viene inviato solo se “Notifica ripristino” è attivo e l’allarme era stato consegnato.'],
		method:['REST only: HTTP method POST, PUT, PATCH or GET. GET sends no body; the other methods send the rendered body template.','Solo REST: metodo HTTP POST, PUT, PATCH o GET. GET non invia corpo; gli altri metodi inviano il corpo generato dal modello.'],
		content_type:['REST only: request Content-Type, for example application/json or text/plain.','Solo REST: Content-Type della richiesta, ad esempio application/json o text/plain.'],
		body:['REST only: body template. Placeholders {event} (stale, recovery, test), {message}, {title}, {device}, {attribute}, {value}, {unit} and {id} are replaced verbatim; quote them yourself when the JSON value is a string. Same placeholders work in the URL.','Solo REST: modello del corpo. I segnaposto {event} (stale, recovery, test), {message}, {title}, {device}, {attribute}, {value}, {unit} e {id} vengono sostituiti alla lettera; se il valore JSON è una stringa, aggiungi le virgolette. Gli stessi segnaposto valgono nella URL.'],
		header:['REST only: one additional request header written as Name: value, for example X-Api-Key: secret. A non-empty token is always sent as Authorization: Bearer.','Solo REST: un header aggiuntivo scritto come Nome: valore, ad esempio X-Api-Key: segreto. Se il token non è vuoto viene sempre inviato Authorization: Bearer.'],
		tgs:['Optional per-rule ntfy tag override. If nonempty, this replaces webhook.tags; otherwise webhook.tags is used. Comma-separated ASCII tags, at most 256 bytes. Not used by Gotify.','Override ntfy opzionale per questa regola. Se compilato, sostituisce webhook.tags; altrimenti viene usato webhook.tags. Tag ASCII separati da virgole, massimo 256 byte. Non usato da Gotify.'],
		ipv4_only:['Use IPv4 only for this HTTPS destination when the router cannot route its IPv6 address. TLS and hostname verification remain enabled.','Usa soltanto IPv4 per questa destinazione HTTPS quando il router non può raggiungere l’indirizzo IPv6. TLS e verifica del nome restano attivi.'],
		priority:['Notification priority, 1-5. ntfy sends it as Priority; Gotify includes it in the JSON message.','Priorità della notifica, 1-5. ntfy la invia come Priority; Gotify nel messaggio JSON.'],
		tags:['Optional ntfy tags, comma-separated ASCII names such as thermometer. Not used by Gotify.','Tag ntfy opzionali: nomi ASCII separati da virgole, ad esempio thermometer. Non usati da Gotify.'],
		startup_grace_s:['Suppress new stale alerts for this many seconds after startup (0-86400). A saved active alarm is not sent again; fresh readings can still recover it during the grace period.','Sopprime nuovi allarmi per questi secondi dopo l’avvio (0-86400). Un allarme attivo salvato non viene reinviato; nuove letture possono ripristinarlo anche durante la tolleranza.'],
		stale_after_s:['Age of the last valid reading of this attribute, not the last BLE packet or last value change. Default 600 seconds. Repeated equal temperatures refresh freshness; battery packets do not.','Età dell’ultima lettura valida di questo attributo, non dell’ultimo pacchetto BLE o cambiamento. Default 600 secondi. Temperature uguali rinnovano la freschezza, i pacchetti batteria no.'],
		notify_recovery:['Send one recovery only if the corresponding stale alert was successfully delivered. Undelivered stale alerts are cancelled when readings resume.','Invia un solo ripristino se l’allarme corrispondente è stato consegnato. Gli allarmi non consegnati vengono annullati al ritorno delle letture.'],
		provider:['ntfy uses a topic URL and optional bearer token; Gotify uses the /message endpoint and an application token; rest sends a custom HTTPS request configured below.','ntfy usa la URL del topic e un eventuale token bearer; Gotify usa /message e un token applicazione; rest invia una richiesta HTTPS personalizzata configurata qui sotto.'],
		url:['Complete HTTPS destination, for example https://ntfy.example/topic or https://gotify.example/message. Certificates are verified, redirects/proxies disabled. No credentials or token query parameters in the URL.','Destinazione HTTPS completa, ad esempio https://ntfy.example/topic o https://gotify.example/message. Certificati verificati, redirect/proxy disabilitati. Niente credenziali o token nei parametri URL.'],
		max_attempts:['Default 1 gives one delivery attempt per event, persisted before network I/O. Higher values explicitly enable retries, which can duplicate a message if a server received it but its response was lost.','Default 1: un tentativo per evento, registrato prima dell’invio. Valori maggiori abilitano tentativi successivi, che possono duplicare un messaggio se il server lo ha ricevuto ma la risposta è persa.'],
		retry_s:['Seconds between explicitly enabled delivery retries (1-86400). No repeated reminder messages are generated.','Secondi tra tentativi successivi esplicitamente abilitati (1-86400). Non vengono generati promemoria ripetuti.'],
		ca_file:['Optional absolute path to a trusted PEM CA for a private HTTPS server. Empty uses bundled public roots; certificate verification is never disabled.','Percorso assoluto opzionale di una CA PEM fidata per un server privato. Vuoto usa le CA pubbliche incluse; la verifica non viene mai disabilitata.'],
	});
	const counterUi=({en:{mode:'Default counter history',discard:'Exclude from consolidated history'},it:{mode:'Storico predefinito dei contatori',discard:'Escludi dallo storico consolidato'},de:{mode:'Standardverlauf für Zähler',discard:'Vom verdichteten Verlauf ausschließen'},fr:{mode:'Historique des compteurs par défaut',discard:'Exclure de l’historique consolidé'},es:{mode:'Histórico predeterminado de contadores',discard:'Excluir del histórico consolidado'}})[helpLanguage]||{mode:'Default counter history',discard:'Exclude from consolidated history'};
	labels.counter_mode=counterUi.mode;
	Object.assign(labels,{maintenance:historyUi.maintenance,policies:historyUi.policies,interval_s:helpLanguage==='it'?'Pausa tra passaggi (secondi)':'Pass interval (seconds)',max_work_ms:helpLanguage==='it'?'Budget per blocco (ms)':'Work budget per chunk (ms)',raw_retention_s:helpLanguage==='it'?'Frame completi recenti':'Recent complete frames',max_age_s:historyUi.age,sample_interval_s:historyUi.spacing});
	Object.assign(parameterHelp,{
		counter_mode:['Default treatment of codec counters: counter, packet_id, count_id, count_i/count_s/count_m/count_l and counter8/16/32. Discard removes archived numeric/unsigned readings; recent complete frames remain until the raw horizon. Explicit per-attribute or MAC policies override this default.','Trattamento predefinito dei contatori del codec: counter, packet_id, count_id, count_i/count_s/count_m/count_l e counter8/16/32. Scarta elimina le letture numeriche/unsigned archiviate; i frame completi recenti restano entro l’orizzonte grezzo. Le politiche esplicite per attributo o MAC prevalgono su questo default.'],
		interval_s:['Delay in seconds after a complete maintenance pass. Backlogs are processed in bounded chunks with pauses; no cron is used.','Pausa in secondi dopo un passaggio completo. Gli arretrati vengono elaborati a blocchi limitati, senza cron.'],
		max_work_ms:['SQLite execution budget per chunk, 10-1000 ms. Long statements are interrupted and rolled back; lower budgets reduce writer contention but may require smaller batches.','Budget SQLite per blocco, 10-1000 ms. Le istruzioni lunghe vengono interrotte e annullate; riduce la contesa ma può richiedere batch più piccoli.'],
		raw_retention_s:['Keep complete original frames for this duration, then atomically split their readings into related series. The effective full-resolution horizon cannot be shorter than this. Unconfigured and discrete measurements remain forever.','Conserva i frame originali completi per questa durata, poi ne trasferisce atomicamente le letture in serie correlate. La risoluzione piena non può essere più breve di questa durata. Misure senza politica e stati discreti restano per sempre.'],
		max_age_s:['Upper age of this band, measured from reception time. Bands must increase. After the last band numeric samples expire. A month is 365/12 days; 24 months are 730 days.','Età massima della fascia dalla ricezione. Le età devono crescere. Oltre l’ultima fascia i numerici scadono. Un mese vale 365/12 giorni: 24 mesi sono 730 giorni.'],
		sample_interval_s:['0 keeps every sample. Otherwise retain the latest real sample in each UTC-aligned interval. Intervals must not decrease in older bands. No averaging or min/max columns.','0 conserva ogni campione; altrimenti conserva l’ultimo campione reale di ogni intervallo allineato UTC. La granularità non può diminuire nelle fasce più vecchie. Nessuna media o colonna min/max.']
	});
	function durationField(parent,object,key,onChange,scope) {
		const label=document.createElement('label');label.className='bbField';fieldHelp(label,key,scope);
		const pair=document.createElement('span');pair.className='bbDuration';
		const input=document.createElement('input');input.type='number';input.min=key==='sample_interval_s'?'0':'1';input.step='any';input.setAttribute('aria-label',title(key));input.title=fieldExplanation(key,scope);input.dataset.parameter=scope+'.'+key;
		const select=document.createElement('select');select.setAttribute('aria-label',title(key)+' unit');select.title=input.title;
		const factors=[1,60,3600,86400,604800,2628000];factors.forEach((factor,index)=>select.add(new Option(historyUi.units[index],String(factor))));
		select.value=String([...factors].reverse().find(factor=>object[key]>0&&object[key]%factor===0)||1);input.value=String(object[key]/Number(select.value));
		input.oninput=()=>{object[key]=Number(input.value)*Number(select.value);onChange();};
		select.onchange=()=>{object[key]=Number(input.value)*Number(select.value);onChange();};
		pair.append(input,select);label.append(pair);parent.append(label);
	}
	function historyPolicies(parent,policies,onChange) {
		const section=document.createElement('div');section.className='bbPolicies';section.id='bbHistoryPolicies';
		const hint=document.createElement('p');hint.className='bbHint';hint.textContent=historyUi.policiesHint;parent.append(section);
		const render=()=>{
			section.replaceChildren(hint);
			policies.forEach((policy,index)=>{
				const item=document.createElement('div');item.className='bbHistoryPolicy';item.dataset.policy=String(index);
				const bar=document.createElement('div');bar.className='bbBar bbPolicyHead';const heading=document.createElement('strong');heading.textContent=historyUi.policy+' '+(index+1);
				const presets=document.createElement('span');presets.className='bbPolicyPresets';
				for(const kind of ['temperature','battery'])presets.append(button(historyUi[kind],()=>run(async()=>{const result=await api('history-presets');const preset=result.maintenance.policies.find(entry=>entry.attribute===(kind==='temperature'?'temperature':'battery_level'));policy.mode=preset.mode;policy.tiers=copy(preset.tiers);onChange();render();}),historyUi[kind]));
				bar.append(heading,presets,button(historyUi.remove,()=>{policies.splice(index,1);onChange();render();}));item.append(bar);
				const grid=document.createElement('div');grid.className='bbGrid';
				for(const key of ['attribute','mac']){const label=document.createElement('label');label.className='bbField';label.append(historyUi[key]);const input=document.createElement('input');input.type='text';input.value=policy[key];input.setAttribute('aria-label',historyUi[key]);input.title=key==='mac'?(helpLanguage==='it'?'Override per un singolo MAC; vuoto applica la politica a tutti i dispositivi.':'Override for one MAC; empty applies to all devices.'):fieldExplanation('attribute','history');if(key==='attribute')input.setAttribute('list','bbAttributes');input.oninput=()=>{policy[key]=input.value;onChange();};label.append(input);grid.append(label);}
				const modeLabel=document.createElement('label');modeLabel.className='bbField';modeLabel.append(historyUi.mode);const mode=document.createElement('select');mode.setAttribute('aria-label',historyUi.mode);mode.title=historyUi.warning;mode.add(new Option(historyUi.keep,'keep_all'));mode.add(new Option(historyUi.progressive,'progressive'));mode.add(new Option(counterUi.discard,'discard'));mode.value=policy.mode;mode.onchange=()=>{policy.mode=mode.value;onChange();render();};modeLabel.append(mode);grid.append(modeLabel);item.append(grid);
				if(policy.mode==='progressive'){
					policy.tiers.forEach((tier,tierIndex)=>{const row=document.createElement('div');row.className='bbTier';row.dataset.tier=String(tierIndex);for(const key of ['max_age_s','sample_interval_s'])durationField(row,tier,key,onChange,'frontends.sqlite.maintenance.policies[].tiers[]');row.append(button('×',()=>{policy.tiers.splice(tierIndex,1);onChange();render();},historyUi.remove));item.append(row);});
					item.append(button(historyUi.band,()=>{const last=policy.tiers.at(-1);policy.tiers.push({max_age_s:last?last.max_age_s*2:3600,sample_interval_s:last?last.sample_interval_s:60});onChange();render();}));
					const expiry=document.createElement('p');expiry.className='bbHint';expiry.textContent=historyUi.expiry;item.append(expiry);
				}
				section.append(item);
			});
			const tools=document.createElement('div');tools.className='bbBar bbLocalActions';
			tools.append(button(historyUi.add,()=>{policies.push({mac:'',attribute:'',mode:'keep_all',tiers:[]});onChange();render();}));section.append(tools);
		};render();
	}
	function availabilityRules(parent,rules,onChange) {
		const section=document.createElement('fieldset');section.id='bbAvailabilityRules';section.className='bbGroup';
		const legend=document.createElement('legend');legend.textContent=availabilityUi.title;section.append(legend);parent.append(section);
		const render=()=>{if(availabilityStatusEditor){availabilityStatusEditor.destroy();availabilityStatusEditor=null;}section.replaceChildren(legend);rules.forEach((rule,index)=>{
			const item=document.createElement('div');item.className='bbAvailabilityRule';item.dataset.availabilityRule=String(index);
			const bar=document.createElement('div');bar.className='bbBar';const name=document.createElement('strong');name.textContent=availabilityUi.rule+' '+(index+1);
			bar.append(name,button(availabilityUi.remove,()=>{rules.splice(index,1);onChange();render();}));
			bar.append(button(availabilityUi.test,()=>run(async()=>{if(await confirmAction(availabilityUi.confirm)){await api('availability-test',{rule});message('HTTPS webhook test delivered');}}),availabilityUi.confirm));item.append(bar);
			const editable=Object.fromEntries(Object.entries(rule).filter(([key])=>key!=='id'));
			fields(item,editable,()=>{Object.assign(rule,editable);onChange();},'device.rules[]');
			toggleGroup(item,rule,'device.rules[]');
			const webhookSummary=item.querySelector('.bbAvailabilityWebhook > summary');
			if(webhookSummary)webhookSummary.textContent=availabilityUi.webhook+' · '+availabilityUi.rule+' '+(index+1);
			section.append(item);
		});
		const tools=document.createElement('div');tools.className='bbBar';
		tools.append(button(availabilityUi.add,()=>run(async()=>{const preset=await api('availability-presets');const rule=copy(preset.rule);let suffix=rules.length+1;while(rules.some(existing=>existing.id==='availability_'+suffix))suffix++;rule.id='availability_'+suffix;rules.push(rule);onChange();render();})));
		const status=document.createElement('div');status.id='bbAvailabilityStatus';status.className='bbOutput';status.hidden=true;status.setAttribute('aria-label',availabilityUi.status);
		tools.append(button(availabilityUi.status,()=>run(async()=>{
			let result;try{result=await api('availability-status');if(result.watches)result.watches=result.watches.filter(watch=>normalize(watch.mac)===normalize(draft.mac));}catch(error){result={success:false,error:error.message};message(error.message,true);}
			if(!status.isConnected)return;status.hidden=false;const text=JSON.stringify(result,null,2);
			try{const editor=availabilityStatusEditor||await jsonEditor(status);if(!status.isConnected){editor.destroy();return;}availabilityStatusEditor=editor;editor.setValue(text,-1);editor.resize(true);}catch(error){status.textContent=text;message(error.message,true);}
		}),availabilityUi.status));section.append(tools,status);
		};render();
	}
	function fields(parent, object, onChange, scope='') {
		const grid = document.createElement('div'); grid.className = 'bbGrid'; parent.append(grid);
		const keys=Object.keys(object);
		if(keys.includes('enabled')){keys.splice(keys.indexOf('enabled'),1);keys.unshift('enabled');}
		keys.forEach(key => {
			const value = object[key];
			if(key==='rules'){
				if(scope==='device')availabilityRules(parent,value,onChange);
			} else if(scope==='frontends.sqlite.maintenance'&&key==='policies'){
				historyPolicies(parent,value,onChange);
			} else if(scope==='frontends.sqlite.maintenance'&&key==='raw_retention_s'){
				durationField(grid,object,key,onChange,scope);
			} else if (Array.isArray(value) && ['whitelist','blacklist'].includes(key)) {
				const label = document.createElement('label'); label.className = 'bbField'; fieldHelp(label,key,scope);
				const input = document.createElement('textarea'); input.rows = 3; input.value = value.join('\n'); input.title=ht.filterList;input.setAttribute('aria-label',title(key));input.id=key==='whitelist'?'bbWhitelist':'bbBlacklist';input.placeholder='A4:C1:38\nA4C1383406CE';input.setAttribute('aria-describedby','bbFilterCommon bbFilterState');input.oninput = () => {object[key] = input.value.split(/[\s,]+/).filter(Boolean); onChange();}; label.append(input);
				const lists=scope==='scanner'?parent.querySelector('#bbMacFilterLists'):null;
				if(lists){if(key==='whitelist')lists.prepend(label);else lists.append(label);}else grid.append(label);
			} else if (Array.isArray(value)) {
				const group = document.createElement('fieldset'); group.className = 'bbGroup'; const legend = document.createElement('legend'); legend.textContent = title(key); if(key==='expose'){legend.title=helpLanguage==='it'?'Attributi pubblicati come endpoint MySensors/Matter. MQTT e database conservano anche altri valori decodificati.':'Attributes published as MySensors/Matter endpoints. MQTT and databases also retain other decoded values.';legend.tabIndex=0;}group.append(legend); parent.append(group);
				const render = () => {
					group.replaceChildren(legend);
					value.forEach((item, index) => {
						const row = document.createElement('div'); row.className = 'bbItem';
						row.append(button('Remove ' + (index + 1), () => {value.splice(index,1); render(); onChange();}));
						fields(row, item, onChange,scope+'.'+key+'[]'); group.append(row);
					});
					group.append(button(key==='publish'?labels.publish_add||'Add field':'Add attribute', () => {value.push(key==='publish'?{source:'',attribute:'',unit:''}:{attribute:'', child:null, kind:null}); render(); onChange();}));
				}; render();
			} else if (value && typeof value === 'object') {
				const maintenance=scope==='frontends.sqlite'&&key==='maintenance',webhook=scope==='device.rules[]'&&key==='webhook';
				const group = document.createElement(maintenance||webhook?'details':'fieldset'); group.className = 'bbGroup'+(webhook?' bbAvailabilityWebhook':''); const legend = document.createElement(maintenance||webhook?'summary':'legend'); legend.textContent = title(key); group.append(legend);if(key==='scanner')scannerHelp(group);
				if(webhook)group.open=!String(value.url||'').trim();
				if(scope==='frontends.sqlite'&&key==='maintenance'){group.id='bbHistoryMaintenance';const warning=document.createElement('p');warning.className='bbHint bbError';warning.textContent=historyUi.warning;group.append(warning);}
				if(key==='frontends'){
					group.id='bbFrontends';
					const missing=['mysensors','mqtt','matter','influx','sqlite'].filter(name=>!Object.prototype.hasOwnProperty.call(value,name));
					if(missing.length){const warning=document.createElement('p');warning.id='bbFrontendNotice';warning.className='bbError';warning.setAttribute('role','alert');warning.textContent=ht.frontendMissing.replace('{frontends}',missing.map(title).join(', '));group.append(warning);}
				}
				if(scope==='frontends'){
					group.dataset.frontend=key;
					const status=document.createElement('span');status.dataset.enabledBadge='';status.dataset.frontendStatus='';status.textContent=' · '+(value.enabled?ui.enabled:ui.disabled);legend.append(status);
					if(key==='sqlite'){const note=document.createElement('p');note.className='bbHint';note.textContent=ui.sqlite;group.append(note);}
				}
				const childScope=scope?scope+'.'+key:key;
				fields(group, value, onChange,childScope); parent.append(group);
				if(typeof value.enabled==='boolean')toggleGroup(group,value,childScope);
			} else {
				const label = document.createElement('label'); label.className = 'bbField';fieldHelp(label,key,scope);
				const restOnly=scope==='device.rules[].webhook'&&['method','content_type','body','header'].includes(key);
				if(restOnly){label.dataset.restOnly='';label.hidden=String(object.provider||'ntfy')!=='rest';}
				let input;
				if(scope==='device.rules[]'&&(key==='message'||key==='recovery_message')){input=document.createElement('textarea');input.rows=3;input.maxLength=4096;input.value=value;}
				else if(scope==='device.rules[].webhook'&&key==='method'){input=document.createElement('select');['POST','PUT','PATCH','GET'].forEach(method=>input.add(new Option(method,method)));input.value=value||'POST';}
				else if(scope==='device.rules[].webhook'&&key==='body'){input=document.createElement('textarea');input.rows=4;input.maxLength=8192;input.value=value;input.setAttribute('spellcheck','false');}
				else if(scope==='device.rules[].webhook'&&key==='provider'){input=document.createElement('select');['ntfy','gotify','rest'].forEach(provider=>input.add(new Option(provider,provider)));input.value=value;}
				else if(scope==='frontends.sqlite.maintenance'&&key==='counter_mode'){input=document.createElement('select');input.add(new Option(counterUi.discard,'discard'));input.add(new Option(historyUi.keep,'keep_all'));input.value=value;}
				else if (key === 'log_level') {input = document.createElement('select'); ['off','error','warn','info','debug','trace'].forEach(level => input.add(new Option(level,level))); input.value = value;}
				else if (scope==='serial'&&key==='baudrate') {input=document.createElement('select');input.setAttribute('aria-label',title(key));const rates=[9600,19200,38400,57600,115200,230400,460800,921600,1000000,2000000];if(!rates.includes(value))rates.push(value);rates.forEach(rate=>input.add(new Option(String(rate),String(rate))));input.value=String(value);}
				else if (key === 'decoder') {input = document.createElement('select');['builtin','theengs','both'].forEach(mode => input.add(new Option(mode, mode)));input.value = value || 'builtin';}
				else if (key === 'mdns_backend') {input = document.createElement('select'); ['auto','builtin','avahi','resolved','zeroconf','astro','disabled'].forEach(backend => input.add(new Option(backend,backend))); input.value = value || 'auto';}
				else {input = document.createElement('input'); input.type = typeof value === 'boolean' ? 'checkbox' : typeof value === 'number' || key === 'child' ? 'number' : /^(bindkey|password|token)$/.test(key) ? 'password' : 'text'; if (input.type === 'checkbox') input.checked = value; else input.value = value == null ? '' : value;}
				input.autocomplete = 'off';
				input.setAttribute('aria-label',title(key));input.title=fieldExplanation(key,scope);input.dataset.parameter=(scope?scope+'.':'')+key;
				if (input.type === 'number') {input.min = '0'; input.step = '1'; if (key === 'child') input.max = '255'; if (key === 'port') {input.min='1';input.max='65535';}}
				if (key === 'format') input.setAttribute('list','bbFormats');
				if (key === 'attribute') input.setAttribute('list','bbAttributes');
				if (key === 'bindkey') {input.maxLength=32; input.pattern='[A-Fa-f0-9]{32}';input.setAttribute('aria-label',title(key));}
				if(scope==='scanner'&&key==='filter_known_devices'){input.title=ht.filterKnown+' '+ht.filterAll;input.setAttribute('aria-describedby','bbFilterCommon bbFilterState');}
				if(scope==='device.rules[].webhook'&&key==='provider')input.addEventListener('change',()=>{const owner=input.closest('details');if(owner)owner.querySelectorAll('[data-rest-only]').forEach(node=>{node.hidden=input.value!=='rest';});});
				input.oninput = () => {object[key] = input.type === 'checkbox' ? input.checked : input.type === 'number' ? (input.value === '' ? null : Number(input.value)) : scope==='serial'&&key==='baudrate' ? Number(input.value) : input.value;if(key==='enabled'&&parent.dataset.frontend){parent.classList.toggle('bbInactive',!input.checked);parent.querySelector('[data-frontend-status]').textContent=' · '+(input.checked?ui.enabled:ui.disabled);} onChange();};
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
		const editable = Object.fromEntries(Object.entries(config).filter(([key]) => !['devices','version','rules','automation','availability_state_file'].includes(key)));
		fields(parent, editable, () => {Object.assign(config,editable); changed();refreshFilterHelp();});refreshFilterHelp();
	}
	function renderDevices() {
		const body = element('bbDevices'); body.replaceChildren(); const query = element('bbDeviceSearch').value.toLowerCase();
		config.devices.forEach((device,index) => {
			if (![device.mac,device.label,device.manufacturer,device.model].join(' ').toLowerCase().includes(query)) return;
			const row = body.insertRow(); const enabled = document.createElement('input'); enabled.type='checkbox'; enabled.checked=device.enabled; enabled.setAttribute('aria-label','Enable '+device.mac); enabled.onchange=()=>{device.enabled=enabled.checked;changed();}; cell(row,'').append(enabled);
			cell(row,device.mac,'bbMac'); cell(row,[device.label,device.manufacturer,device.model].filter(Boolean).join(' / ')); cell(row,device.format || 'Automatic'); cell(row,device.expose.map(item=>item.attribute + (item.child == null ? '' : ' ['+item.child+']')).join(', '));
			actionsCell(row,button('Edit',()=>run(()=>editDevice(index))),button('Remove',()=>removeDevice(index)));
		});
		if (!body.rows.length) cell(body.insertRow(),'No matching configured devices').colSpan=6;
	}
	async function editDevice(index, found) {
		editIndex=index;
		editObservation=found||null;
		draft=index>=0 ? copy(config.devices[index]) : {mac:found ? found.mac : '',label:found ? found.name : '',manufacturer:'',model:'',firmware_version:'',bindkey:'',enabled:true,format:'',expose:[],rules:[]};
		element('bbDeviceTitle').textContent=index>=0?ui.edit:found?ui.detected:ui.manualTitle;element('bbDeviceApply').textContent=index>=0?ui.update:ui.add;
		element('bbDeviceFields').replaceChildren(); element('bbDeviceError').textContent='';element('bbSuggestAttributes').hidden=!found;
		if(found&&index<0){try{await detectAttributes();}catch(error){element('bbDeviceError').textContent=error.message;}}
		fields(element('bbDeviceFields'),draft,()=>{},'device'); element('bbDeviceDialog').showModal();
	}
	async function detectAttributes() {
		const [result,supported]=await Promise.all([api('inspect',{observation:editObservation,device:draft}),api('attributes')]);
		if(result.decode_status!=='ok')throw new Error(ui.detectionFailed+' '+(result.error||''));
		const preferred=['temperature','humidity','battery_level'];
		const names=Object.keys(result.measurements||{}).filter(name=>supported.attributes.includes(name));
		names.sort((first,second)=>{const priority=name=>preferred.includes(name)?preferred.indexOf(name):preferred.length;return priority(first)-priority(second)||first.localeCompare(second);});
		if(!names.length)throw new Error(ui.detectionFailed);
		const used=new Set(draft.expose.map(item=>item.child).filter(child=>child!==null));
		names.forEach(attribute=>{if(!draft.expose.some(item=>item.attribute===attribute)){let child=0;while(used.has(child))child++;draft.expose.push({attribute,child:child<=255?child:null,kind:null});used.add(child);}});
	}
	async function keepDevice() {
		const candidate=copy(config); if(editIndex>=0)candidate.devices[editIndex]=draft;else candidate.devices.push(draft);
		try {const data=await api('check',{config:candidate}); config=data.config; changed();renderDevices();renderFound();element('bbDeviceDialog').close();message(ui.pending);await switchTab('devices');element('bbSave').focus();} catch(error){element('bbDeviceError').textContent=error.message;}
	}
	function renderFound() {
		const vendor=element('bbVendor').value, query=element('bbSearch').value.toLowerCase(), sort=element('bbSort').value;
		const vendors=[...new Set(observations.map(device=>device.vendor))].sort(); element('bbVendor').replaceChildren(new Option('All OUI vendors',''),...vendors.map(name=>new Option(name,name))); element('bbVendor').value=vendor;
		const found=observations.filter(device=>(!vendor||device.vendor===vendor)&&[device.mac,device.name,device.format,device.vendor].join(' ').toLowerCase().includes(query)&&(!element('bbNewOnly').checked||!config.devices.some(known=>normalize(known.mac)===device.mac)));
		found.sort((first,second)=>['rssi','count'].includes(sort)?second[sort]-first[sort]:sort==='last_seen'?String(second[sort]).localeCompare(first[sort]):String(first[sort]).localeCompare(String(second[sort])));
		const body=element('bbFound');body.replaceChildren();
		found.forEach(device=>{const row=body.insertRow();cell(row,device.mac+(device.name?' / '+device.name:''),'bbMac');cell(row,device.vendor);cell(row,device.format||'Unrecognized');cell(row,device.rssi+' dBm');cell(row,device.phy.replace(/^phy_raw=\S+ /,''));cell(row,device.count+' / '+device.last_seen);const index=config.devices.findIndex(known=>normalize(known.mac)===device.mac);const actions=actionsCell(row,button(index>=0?'Edit':'Configure',()=>run(()=>editDevice(index,device))),button('Inspect',()=>inspectDevice(device)));if(index>=0)actions.append(button('Remove',()=>removeDevice(index)));});
		if(!body.rows.length)cell(body.insertRow(),'No matching observations').colSpan=7;
	}
	async function inspectDevice(device) {
		const sequence=++inspectionSequence;
		element('bbPacketDetails').open=true;element('bbPacketError').hidden=true;setPacket({...device,decode_status:'decoding'});
		ensurePacketEditor().catch(error=>{if(sequence===inspectionSequence){element('bbPacketError').textContent=error.message;element('bbPacketError').hidden=false;}});
		const configured=config.devices.find(known=>normalize(known.mac)===device.mac);
		try {
			const decoded=await api('inspect',{observation:device,device:configured});
			if(sequence===inspectionSequence)setPacket({...device,decode_status:decoded.decode_status,wire_format:decoded.wire_format,measurements:decoded.measurements,decoded:decoded.decoded,theengs:decoded.theengs,decode_error:decoded.error});
		} catch(error) {if(sequence===inspectionSequence)setPacket({...device,decode_status:'failed',decode_error:error.message});}
	}
	async function poll() {
		if(polling||!config)return; polling=true;
		try {const status=await api('status');observations=status.devices;element('bbStart').disabled=status.active||!status.connected;element('bbStop').disabled=!status.active;element('bbDiscoveryStatus').textContent=(status.active?'Scanning, '+status.remaining_s+' s remaining':status.connected?'Idle':'Serial unavailable')+' | '+observations.length+' devices | '+status.reports+' reports'+(status.overflow?' | table limit reached':'')+(status.error?' | '+status.error:'');renderFound();}
		catch(error){element('bbDiscoveryStatus').textContent=error.message;element('bbStop').disabled=true;}
		finally{polling=false;}
	}
	let logTimer=null;
	function setLogAuto(on) {if(logTimer){clearInterval(logTimer);logTimer=null;}if(on)logTimer=setInterval(()=>{if(!document.hidden)refreshLog();},5000);}
	async function refreshLog() {
		const box=element('bbLog'),status=element('bbLogStatus');
		if(!box)return;
		try {
			const data=await api('log',{lines:Number(element('bbLogLines').value)||300});
			const lines=data.lines||[];
			box.textContent=lines.length?lines.join('\n'):(data.missing?'Log file not created yet.':'Log is empty.');
			box.scrollTop=box.scrollHeight;
			status.textContent=(data.path||'')+' · '+lines.length+' lines · '+new Date().toLocaleTimeString();
		} catch(error) {status.textContent=error.message;}
	}
	async function switchTab(next) {
		if(!config||next===tab)return;
		hidePacketTooltip();
		if(tab==='yaml'&&rawDirty){const result=await api('check',{yaml:getYaml()});config=result.config;rawDirty=false;renderSettings();renderDevices();}
		if(next==='yaml'){const result=await api('check',{config});setYaml(result.yaml);rawDirty=false;await ensureYamlEditor();}
		tab=next;app.querySelectorAll('[data-panel]').forEach(panel=>panel.hidden=panel.dataset.panel!==tab);app.querySelectorAll('[data-tab]').forEach(control=>control.setAttribute('aria-selected',String(control.dataset.tab===tab)));if(tab==='discovery')poll();if(tab==='log'){refreshLog();setLogAuto(element('bbLogAuto').checked);}else setLogAuto(false);
		if(tab==='yaml')yamlEditor.resize(true);
		if(tab==='discovery'&&packetEditor)packetEditor.resize(true);
		if(tab==='commands'){Object.values(commandEditors).forEach(editor=>editor.resize(true));await radioStatus();}
	}
	function payload(){return {...(tab==='yaml'&&rawDirty?{yaml:getYaml()}:{config}),revision};}
	function download(name,content,type){const url=URL.createObjectURL(new Blob([content],{type}));const link=document.createElement('a');link.href=url;link.download=name;link.click();URL.revokeObjectURL(url);}
	async function load(){if(dirty&&!await confirmAction('Reload and discard unsaved changes?'))return;const data=await api('read');config=data.config;revision=data.revision;dirty=false;rawDirty=false;setYaml(data.yaml);element('bbDirty').textContent='';renderSettings();renderDevices();message('Configuration loaded');if(tab==='discovery')poll();}
	element('bbReload').onclick=()=>run(load);
	element('bbCheck').onclick=()=>run(async()=>{await api('check',payload());message('Configuration is valid');});
	const saveDraft=()=>run(async()=>{const data=await api('save',payload());config=data.config;revision=data.revision;rawDirty=false;setYaml(data.yaml);renderSettings();renderDevices();try{await api('persist');}catch(error){changed();throw new Error('YAML saved; persistence not confirmed: '+error.message);}dirty=false;element('bbDirty').textContent=ui.saved;message('Saved. Running settings are unchanged. Restart from Status to activate devices/frontends.');});
	element('bbSave').onclick=saveDraft;element('bbYamlSave').onclick=saveDraft;
	element('bbYamlHint').textContent=uiNotes.yamlHint;
	element('bbYamlRevert').onclick=()=>run(async()=>{if(rawDirty&&!await confirmAction(uiNotes.yamlDiscard))return;const result=await api('check',{config});setYaml(result.yaml);rawDirty=false;message(uiNotes.yamlReverted);});
	element('bbLogging').onclick=()=>run(async()=>{await api('reload-logging');message('Logging reload requested');});
	element('bbLogOpen').onclick=()=>run(async()=>{await switchTab('log');element('bbLog').scrollIntoView({block:'center'});});
	element('bbLogRefresh').onclick=()=>run(refreshLog);element('bbLogAuto').onchange=()=>setLogAuto(element('bbLogAuto').checked);element('bbLogLines').onchange=()=>run(refreshLog);element('bbLogDownload').onclick=()=>download('rc.ble2uart_gateway.log',element('bbLog').textContent,'text/plain');element('bbLogNote').textContent='Service log ('+(helpLanguage==='it'?'ultime righe, aggiornamento automatico':helpLanguage==='de'?'letzte Zeilen, automatisch aktualisiert':'last lines, auto-refreshed')+').';
	element('bbAdd').onclick=()=>{if(config)run(()=>editDevice(-1));};element('bbDeviceApply').onclick=keepDevice;element('bbDeviceCancel').onclick=()=>element('bbDeviceDialog').close();
	element('bbDeviceApply').title=ht.keep;element('bbDeviceCancel').title=ht.cancel;
	element('bbAdd').textContent=ui.manual;element('bbDiscoverDevices').textContent=ui.discover;element('bbDeviceFilterLabel').textContent=ui.filter;
	element('bbDiscoverDevices').onclick=()=>run(()=>switchTab('discovery'));
	element('bbSuggestAttributes').textContent=ui.detect;element('bbSuggestAttributes').onclick=async()=>{const control=element('bbSuggestAttributes');control.disabled=true;try{await detectAttributes();element('bbDeviceFields').replaceChildren();fields(element('bbDeviceFields'),draft,()=>{},'device');element('bbDeviceError').textContent='';}catch(error){element('bbDeviceError').textContent=error.message;}finally{control.disabled=false;}};
	element('bbParameterClose').textContent=ui.close;element('bbParameterClose').onclick=()=>element('bbParameterDialog').close();
	element('bbPacketHint').textContent=ht.hint;element('bbPacketHelpTitle').textContent=ht.guide;
	element('bbTheengsTitle').textContent=theengsUi.title;
	element('bbTheengsCopy').textContent=theengsUi.copy;element('bbTheengsOpen').textContent=theengsUi.open;element('bbTheengsDecode').textContent=theengsDecodeUi.decode;element('bbTheengsResultLabel').textContent=theengsDecodeUi.result;
	element('bbTheengsCopy').onclick=()=>copyTheengs();element('bbTheengsOpen').addEventListener('click',()=>copyTheengs());element('bbTheengsDecode').onclick=()=>decodeWithTheengs();
	element('bbTheengs').addEventListener('toggle',()=>{hidePacketTooltip();if(!element('bbTheengs').open)return;ensureTheengsEditors().then(()=>{if(theengsInput)theengsInput.resize(true);if(theengsResult)theengsResult.resize(true);}).catch(error=>theengsStatus(error.message,true));});
	setTheengs(null);
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
	window.addEventListener('keydown',event=>{if(event.key==='Escape')hidePacketTooltip();if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='s'){event.preventDefault();if(config&&!busy)saveDraft();}});
	window.addEventListener('scroll',hidePacketTooltip,true);window.addEventListener('resize',hidePacketTooltip);window.addEventListener('blur',hidePacketTooltip);
	window.addEventListener('beforeunload',event=>{if(dirty||gattToken){event.preventDefault();event.returnValue='';}});
	function startupControls() {
		const startup=element('bbStartup'),form=app.closest('form');if(!startup||!form)return;
		const advanced=element('bbStartupAdvanced');if(advanced)startup.append(advanced);
		startup.append(element('bbStartupActions'));
		const startupHint=element('bbStartupHint');if(startupHint)startup.append(startupHint);
		const submit=form.querySelector('input[type=submit]');
		if(submit){submit.value=ui.startup;submit.title=ui.startupConfirm;element('bbStartupActions').append(submit);}
		form.addEventListener('submit',async event=>{event.preventDefault();if(dirty){message(ui.unsaved,true);element('bbSave').focus();return;}if(await confirmAction(ui.startupConfirm))form.submit();});
		document.querySelectorAll('form').forEach(candidate=>{if(candidate.action===form.action+'?default')candidate.hidden=true;});
		const startupHelp={enabled:['Service startup mode; saving this section restarts a running service.','Modalità di avvio del servizio; salvare questa sezione riavvia il servizio se attivo.'],store:['Configuration directory. Select a mounted persistent disk. Existing store contents are copied, not deleted; save startup settings and restart to use the new path.','Directory di configurazione. Scegli un disco persistente montato. Il contenuto esistente viene copiato, non eliminato; salva avvio/percorso e riavvia per usare il nuovo percorso.'],serial:['Initial serial path, used only for a new YAML file.','Seriale iniziale, usata solo per un nuovo YAML.'],baudrate:parameterHelp.baudrate,config_wait:['Boot wait in seconds for external resources; 0 means no wait.','Attesa al boot in secondi delle risorse esterne; 0 significa nessuna attesa.'],verbose:['Initial debug logging override; runtime logging is also configurable in Settings.','Override debug iniziale; il log runtime è configurabile anche in Settings.'],extra_args:['Extra daemon CLI arguments. They can override YAML settings; leave empty unless required.','Argomenti CLI aggiuntivi: possono sovrascrivere le impostazioni YAML. Lasciare vuoto se non necessari.']};
		startup.querySelectorAll('input,select').forEach(control=>{const help=startupHelp[control.name];if(help)control.title=help[helpLanguage==='it'?1:0];});
	}
	if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',startupControls,{once:true});else startupControls();
	setInterval(()=>{if(tab==='discovery'&&!document.hidden)poll();},1200);
	run(load);
})();
</script>
EOF
sec_end

echo '<div id="bbStartupAdvanced">'
sec_begin "$(lang de:"Erweitert" en:"Advanced")"
cgi_print_radiogroup_active "verbose" "$BLE2UART_GATEWAY_VERBOSE" "" "$(lang de:"Debug-Protokoll" en:"Debug logging")"
cat << EOF
<p>$(lang de:"Zusaetzliche Kommandozeilenoptionen" en:"Additional command line options"): <input type="text" name="extra_args" size="60" maxlength="255" value="$(html "$BLE2UART_GATEWAY_EXTRA_ARGS")"></p>
<p style="font-size:11px;">$(lang de:"Protokoll: Status -> Logs -> rc.ble2uart_gateway" en:"Log: Status -> Logs -> rc.ble2uart_gateway"): <code>/tmp/rc.ble2uart_gateway.log</code></p>
EOF
sec_end
echo '</div>'
