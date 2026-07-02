#!/bin/sh
# Pi-hole status CGI for freetz-ng
# Provides real-time status information

. /usr/lib/libmodcgi.sh

sec_begin "$(lang de:"Pi-hole Status" en:"Pi-hole Status")"

# Source config
[ -r /mod/etc/conf/pi-hole.cfg ] && . /mod/etc/conf/pi-hole.cfg

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

cat <<-EOF
<table class="full">
<tr><td style="width:200px">$(lang de:"Blocking-Status" en:"Blocking status"):</td><td><b>${STATUS}</b></td></tr>
<tr><td>$(lang de:"Blockierte Domains" en:"Blocked domains"):</td><td>${DOMAINS}</td></tr>
<tr><td>$(lang de:"DNS-Server" en:"DNS server"):</td><td>$(pidof dnsmasq >/dev/null 2>&1 && echo "running" || echo "stopped")</td></tr>
<tr><td>$(lang de:"Datenverzeichnis" en:"Data directory"):</td><td>${PIHOLE_BASEDIR:-/tmp/flash/pi-hole}</td></tr>
<tr><td>$(lang de:"Upstream-DNS" en:"Upstream DNS"):</td><td>${PIHOLE_DNS_UPSTREAM:-none}</td></tr>
</table>
EOF

# Quick actions
cat <<-EOF
<div style="margin-top:15px;">
<button onclick="window.location.href='/cgi-bin/conf/pi-hole'">Back to config</button>
EOF

if [ "$STATUS" = "enabled" ]; then
	echo '<button onclick="fetch(\'/cgi-bin/conf/pi-hole?ajax=1&action=blocking&mode=disable\').then(() => location.reload())">Disable Blocking</button>'
else
	echo '<button onclick="fetch(\'/cgi-bin/conf/pi-hole?ajax=1&action=blocking&mode=enable\').then(() => location.reload())">Enable Blocking</button>'
fi

echo '<button onclick="fetch(\'/cgi-bin/conf/pi-hole?ajax=1&action=gravity\').then(() => location.reload())">Run Gravity</button>'
echo '</div>'

sec_end
