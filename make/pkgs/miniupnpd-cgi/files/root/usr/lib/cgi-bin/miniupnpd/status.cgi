#!/bin/sh
# MiniUPnPd status CGI

. /usr/lib/libmodcgi.sh

sec_begin "$(lang de:"MiniUPnPd Status" en:"MiniUPnPd Status")"

[ -r /mod/etc/conf/miniupnpd.cfg ] && . /mod/etc/conf/miniupnpd.cfg

RUNNING="no"
pgrep -x miniupnpd >/dev/null 2>&1 && RUNNING="yes"

cat <<-EOF
<table class="full">
<tr><td>$(lang de:"Daemon-Status" en:"Daemon status"):</td><td><b>${RUNNING}</b></td></tr>
<tr><td>$(lang de:"WAN-Schnittstelle" en:"WAN interface"):</td><td>${MINIUPNPD_WAN_IF:-eth1}</td></tr>
<tr><td>$(lang de:"LAN-Schnittstelle" en:"LAN interface"):</td><td>${MINIUPNPD_LAN_IF:-192.168.0.1/24}</td></tr>
</table>
EOF

sec_end
