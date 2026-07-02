#!/bin/sh
# Pi-hole CGI web interface for freetz-ng

DAEMON=pi-hole
. /etc/init.d/modlibrc

# Check for AJAX mode
AJAX_MODE=$(cgi_param ajax)

if [ "$AJAX_MODE" = "1" ]; then
	# AJAX JSON response handler
	ACTION=$(cgi_param action)

	# Output JSON wrapper
	cat <<-EOF
	Content-Type: text/html; charset=UTF-8

	<style>
	.ajax-json-box { display: none; }
	</style>
	<div class="ajax-json-box"><div class="ajax-json-content"><pre>Content-Type: application/json

	EOF

	case "$ACTION" in
		status)
			# Return current blocking status and stats
			BLOCKLIST="/tmp/flash/dnsmasq/pi-hole.hosts"
			BLOCKING_FILE="/tmp/flash/pi-hole/.blocking"
			STATUS="disabled"
			DOMAINS=0

			if [ -f "$BLOCKING_FILE" ]; then
				STATUS="enabled"
			fi
			if [ -f "$BLOCKLIST" ]; then
				DOMAINS=$(($(wc -l < "$BLOCKLIST") - 2))
				[ "$DOMAINS" -lt 0 ] && DOMAINS=0
			fi

			echo "{"
			echo "  \"status\": \"${STATUS}\","
			echo "  \"blocked_domains\": ${DOMAINS},"
			echo "  \"dns_running\": $(pidof dnsmasq >/dev/null 2>&1 && echo 'true' || echo 'false')"
			echo "}"
			;;
		gravity)
			# Run gravity update and return result
			if [ -x /usr/share/pi-hole/gravity.sh ]; then
				RESULT=$(sh /usr/share/pi-hole/gravity.sh 2>/dev/null)
				echo "{\"success\": true, \"domains_added\": ${RESULT:-0}}"
			else
				echo '{"success": false, "error": "Gravity script not found"}'
			fi
			;;
		query)
			# Query if a domain is blocked
			DOMAIN=$(cgi_param domain)
			BLOCKLIST="/tmp/flash/dnsmasq/pi-hole.hosts"
			if [ -z "$DOMAIN" ]; then
				echo '{"error": "No domain specified"}'
			elif [ -f "$BLOCKLIST" ] && grep -qi "$DOMAIN" "$BLOCKLIST" 2>/dev/null; then
				echo "{\"domain\": \"${DOMAIN}\", \"blocked\": true}"
			else
				echo "{\"domain\": \"${DOMAIN}\", \"blocked\": false}"
			fi
			;;
		blocking)
			# Enable/disable blocking
			MODE=$(cgi_param mode)
			case "$MODE" in
				enable)
					mkdir -p /tmp/flash/pi-hole 2>/dev/null
					ln -sf /tmp/flash/dnsmasq/pi-hole.hosts /etc/dnsmasq.d/pi-hole.hosts 2>/dev/null || true
					echo enabled > /tmp/flash/pi-hole/.blocking
					killall -HUP dnsmasq 2>/dev/null || true
					echo '{"success": true, "blocking": "enabled"}'
					;;
				disable)
					rm -f /etc/dnsmasq.d/pi-hole.hosts 2>/dev/null
					rm -f /tmp/flash/pi-hole/.blocking 2>/dev/null
					killall -HUP dnsmasq 2>/dev/null || true
					echo '{"success": true, "blocking": "disabled"}'
					;;
				*)
					echo '{"error": "Invalid mode. Use enable or disable"}'
					;;
			esac
			;;
		toggle)
			# Toggle blocking
			BLOCKING_FILE="/tmp/flash/pi-hole/.blocking"
			if [ -f "$BLOCKING_FILE" ]; then
				rm -f /etc/dnsmasq.d/pi-hole.hosts 2>/dev/null
				rm -f "$BLOCKING_FILE" 2>/dev/null
				killall -HUP dnsmasq 2>/dev/null || true
				echo '{"success": true, "blocking": "disabled"}'
			else
				mkdir -p /tmp/flash/pi-hole 2>/dev/null
				ln -sf /tmp/flash/dnsmasq/pi-hole.hosts /etc/dnsmasq.d/pi-hole.hosts 2>/dev/null || true
				echo enabled > /tmp/flash/pi-hole/.blocking
				killall -HUP dnsmasq 2>/dev/null || true
				echo '{"success": true, "blocking": "enabled"}'
			fi
			;;
		*)
			echo '{"error": "Unknown action"}'
			;;
	esac

	# Close JSON wrapper
	echo '</pre></div></div>'
	exit 0
fi

# Regular HTML mode
cgi_begin "$(lang de:"Pi-hole DNS-Sinkhole" en:"Pi-hole DNS Sinkhole")"

# Source saved config
[ -r /mod/etc/conf/pi-hole.cfg ] && . /mod/etc/conf/pi-hole.cfg

# Main configuration form
cat <<-EOF
<script type="text/javascript">
// Pi-hole AJAX helpers
function piHoleStatus() {
	fetch('/cgi-bin/conf/pi-hole?ajax=1&action=status')
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
			const statusEl = document.getElementById('pihole-status');
			const domainEl = document.getElementById('pihole-domains');
			if (statusEl) statusEl.textContent = data.status === 'enabled' ? '🟢 Active' : '🔴 Inactive';
			if (domainEl) domainEl.textContent = data.blocked_domains + ' domains blocked';
		})
		.catch(err => console.error('Status error:', err));
}

function toggleBlocking() {
	fetch('/cgi-bin/conf/pi-hole?ajax=1&action=toggle')
		.then(r => r.text())
		.then(text => {
			piHoleStatus();
			showStatus('Toggled', 'info');
		})
		.catch(err => showStatus('Error: ' + err.message, 'error'));
}

function runGravity() {
	document.getElementById('gravity-status').textContent = 'Updating...';
	fetch('/cgi-bin/conf/pi-hole?ajax=1&action=gravity')
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
			if (data.success) {
				document.getElementById('gravity-status').textContent = 'Updated: ' + data.domains_added + ' domains added';
				piHoleStatus();
			} else {
				document.getElementById('gravity-status').textContent = 'Error: ' + (data.error || 'Unknown');
			}
		})
		.catch(err => { document.getElementById('gravity-status').textContent = 'Error: ' + err.message; });
}

function showStatus(msg, type) {
	const el = document.getElementById('action-status');
	if (!el) return;
	el.textContent = msg;
	el.style.background = type === 'error' ? '#dc3545' : '#28a745';
	el.style.display = 'block';
	setTimeout(() => { el.style.display = 'none'; }, 3000);
}

// Auto-refresh status
setInterval(piHoleStatus, 10000);
window.addEventListener('load', piHoleStatus);
</script>

<div id="action-status" style="display:none; padding:10px; margin:10px 0; border-radius:4px; color:#fff;"></div>

<div style="display:flex; gap:10px; margin:10px 0; flex-wrap:wrap;">
	<div style="flex:1; min-width:200px; padding:15px; border:1px solid #ccc; border-radius:4px; text-align:center;">
		<div style="font-size:24px; font-weight:bold;" id="pihole-status">Loading...</div>
		<div style="font-size:14px; color:#666;" id="pihole-domains"></div>
	</div>
	<div style="flex:1; min-width:200px; padding:15px; border:1px solid #ccc; border-radius:4px; text-align:center;">
		<button onclick="toggleBlocking()" style="padding:10px 20px; font-size:16px;">Toggle Blocking</button>
		<br><br>
		<button onclick="runGravity()" style="padding:10px 20px; font-size:16px;">Update Gravity</button>
		<div id="gravity-status" style="margin-top:8px; font-size:12px; color:#666;"></div>
	</div>
</div>
EOF

# Configuration form
sec_begin "$(lang de:"Allgemein" en:"General")"
cgi_print_radiogroup_service_starttype "enabled" "$PIHOLE_ENABLED" "" "" 0
cgi_print_textline_p "basedir" "$PIHOLE_BASEDIR" 40/128 \
	"$(lang de:"Datenverzeichnis" en:"Data directory"): "
sec_end

sec_begin "$(lang de:"DNS-Einstellungen" en:"DNS Settings")"
cgi_print_textline_p "dns_upstream" "$PIHOLE_DNS_UPSTREAM" 64/256 \
	"$(lang de:"Upstream-DNS" en:"Upstream DNS"): "
cgi_print_textline_p "dns_port" "$PIHOLE_DNS_PORT" 8/8 \
	"$(lang de:"DNS-Port" en:"DNS port"): "
cgi_print_textline_p "rate_limit" "$PIHOLE_RATE_LIMIT" 8/8 \
	"$(lang de:"Rate-Limit" en:"Rate limit"): "
cgi_print_radiogroup "log_level" "$PIHOLE_LOG_LEVEL" "" "" \
	"0::$(lang de:"Aus" en:"Off")" \
	"1::$(lang de:"Nur Abfragen" en:"Queries only")" \
	"2::$(lang de:"Alles" en:"Everything")"
sec_end

sec_begin "$(lang de:"Blocklist-URLs" en:"Blocklist URLs")"
cgi_print_textarea_p "blocklist_urls" "$PIHOLE_BLOCKLIST_URLS" 80/4 \
	"$(lang de:"Blocklisten-URLs (eine pro Zeile)" en:"Blocklist URLs (one per line)"): "
sec_end

sec_begin "$(lang de:"DHCP (experimentell)" en:"DHCP (experimental)")"
cgi_print_checkbox_p "dhcp_active" "$PIHOLE_DHCP_ACTIVE" \
	"$(lang de:"DHCP-Server aktivieren" en:"Enable DHCP server")"
cgi_print_textline_p "dhcp_start" "$PIHOLE_DHCP_START" 20/64 \
	"$(lang de:"DHCP-Start-IP" en:"DHCP start IP"): "
cgi_print_textline_p "dhcp_end" "$PIHOLE_DHCP_END" 20/64 \
	"$(lang de:"DHCP-End-IP" en:"DHCP end IP"): "
cgi_print_textline_p "dhcp_leasetime" "$PIHOLE_DHCP_LEASETIME" 12/32 \
	"$(lang de:"Lease-Zeit" en:"Lease time"): "
sec_end

# Status section
sec_begin "$(lang de:"Status" en:"Status")"
cat <<-EOF
<ul>
<li><a href="$(href status pi-hole)?refresh=5">$(lang de:"Status anzeigen" en:"Show status")</a></li>
<li><a href="javascript:void(0)" onclick="runGravity()">$(lang de:"Gravity-Update ausführen" en:"Run gravity update")</a></li>
</ul>
EOF
sec_end

cgi_end
