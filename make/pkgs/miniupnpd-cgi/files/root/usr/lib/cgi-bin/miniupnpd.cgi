#!/bin/sh
# MiniUPnPd CGI web interface for freetz-ng

DAEMON=miniupnpd
. /etc/init.d/modlibrc

AJAX_MODE=$(cgi_param ajax)

if [ "$AJAX_MODE" = "1" ]; then
	ACTION=$(cgi_param action)

	cat <<-EOF
	Content-Type: text/html; charset=UTF-8

	<style>
	.ajax-json-box { display: none; }
	</style>
	<div class="ajax-json-box"><div class="ajax-json-content"><pre>Content-Type: application/json

	EOF

	case "$ACTION" in
		status)
			RUNNING="false"
			pgrep -x miniupnpd >/dev/null 2>&1 && RUNNING="true"
			echo "{\"running\": ${RUNNING}}"
			;;
		*)
			echo '{"error": "Unknown action"}'
			;;
	esac

	echo '</pre></div></div>'
	exit 0
fi

cgi_begin "$(lang de:"MiniUPnPd" en:"MiniUPnPd")"

[ -r /mod/etc/conf/miniupnpd.cfg ] && . /mod/etc/conf/miniupnpd.cfg

cat <<-EOF
<script type="text/javascript">
function checkStatus() {
	fetch('/cgi-bin/conf/miniupnpd?ajax=1&action=status')
		.then(r => r.text())
		.then(text => {
			const marker = 'Content-Type: application/json';
			const markerPos = text.indexOf(marker);
			if (markerPos === -1) return;
			const firstBrace = text.indexOf('{', markerPos + marker.length);
			let braceCount = 0, jsonEnd = -1;
			for (let i = firstBrace; i < text.length; i++) {
				if (text[i] === '{') braceCount++;
				else if (text[i] === '}') {
					braceCount--;
					if (braceCount === 0) { jsonEnd = i + 1; break; }
				}
			}
			if (jsonEnd === -1) return;
			const data = JSON.parse(text.substring(firstBrace, jsonEnd));
			document.getElementById('miniupnpd-status').textContent =
				data.running ? '✅ Running' : '❌ Stopped';
		})
		.catch(err => console.error(err));
}
setInterval(checkStatus, 10000);
window.addEventListener('load', checkStatus);
</script>
<div id="miniupnpd-status" style="font-size:18px; font-weight:bold;">Loading...</div>
EOF

sec_begin "$(lang de:"Allgemein" en:"General")"
cgi_print_radiogroup_service_starttype "enabled" "$MINIUPNPD_ENABLED" "" "" 0
sec_end

sec_begin "$(lang de:"Netzwerk-Schnittstellen" en:"Network Interfaces")"
cgi_print_textline_p "wan_if" "$MINIUPNPD_WAN_IF" 20/64 \
	"$(lang de:"WAN-Schnittstelle" en:"WAN interface"): "
cgi_print_textline_p "lan_if" "$MINIUPNPD_LAN_IF" 20/64 \
	"$(lang de:"LAN-Schnittstelle" en:"LAN interface"): "
sec_end

sec_begin "$(lang de:"Optionen" en:"Options")"
cgi_print_checkbox_p "secure_mode" "$MINIUPNPD_SECURE_MODE" \
	"$(lang de:"Secure Mode" en:"Secure mode")"
cgi_print_checkbox_p "enable_upnp" "$MINIUPNPD_ENABLE_UPNP" \
	"$(lang de:"UPnP aktivieren" en:"Enable UPnP")"
cgi_print_checkbox_p "enable_pcp_pmp" "$MINIUPNPD_ENABLE_PCP_PMP" \
	"$(lang de:"NAT-PMP/PCP aktivieren" en:"Enable NAT-PMP/PCP")"
sec_end

sec_begin "$(lang de:"Intervalle" en:"Intervals")"
cgi_print_textline_p "notify_interval" "$MINIUPNPD_NOTIFY_INTERVAL" 8/8 \
	"$(lang de:"SSDP-Notify-Intervall (s)" en:"SSDP notify interval (s)"): "
cgi_print_textline_p "clean_interval" "$MINIUPNPD_CLEAN_INTERVAL" 8/8 \
	"$(lang de:"Bereinigungsintervall (s)" en:"Clean interval (s)"): "
sec_end

sec_begin "$(lang de:"Status" en:"Status")"
cat <<-EOF
<ul>
<li><a href="$(href status miniupnpd)?refresh=5">$(lang de:"Status anzeigen" en:"Show status")</a></li>
</ul>
EOF
sec_end

cgi_end
