#!/bin/sh

. /usr/lib/libmodcgi.sh

SERVER_CONFIG=/mod/etc/snapserver.conf
SERVER_PID_FILE=/var/run/snapserver.pid
CLIENT_PID_FILE=/var/run/snapclient.pid
SERVER_LOG=/var/log/snapserver.log
CLIENT_LOG=/var/log/snapclient.log

[ -r /mod/etc/default.snapcast/snapcast.cfg ] && . /mod/etc/default.snapcast/snapcast.cfg
[ -r /mod/etc/conf/snapcast.cfg ] && . /mod/etc/conf/snapcast.cfg

component_state() {
	local pidfile="$1"
	local pid
	[ -s "$pidfile" ] || {
		echo stopped
		return
	}
	pid="$(cat "$pidfile" 2>/dev/null)"
	if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
		echo "running (pid $pid)"
	else
		echo "stale pidfile"
	fi
}

print_row() {
	local label="$1"
	local value="$2"
	[ -n "$value" ] || return 0
	echo "<tr><td style='width:240px'><b>$(html "$label")</b></td><td>$(html "$value")</td></tr>"
}

sec_begin "$(lang de:"Snapcast-Status" en:"Snapcast status")"
echo "<table style='width:100%'>"
print_row "$(lang de:"Service" en:"Service")" "$(/mod/etc/init.d/rc.snapcast status 2>/dev/null | tr '\n' '; ' | sed 's/; $//')"
print_row "$(lang de:"Autostart" en:"Autostart")" "$SNAPCAST_ENABLED"
print_row "$(lang de:"Snapserver" en:"Snapserver")" "$(component_state "$SERVER_PID_FILE")"
print_row "$(lang de:"Lokaler snapclient" en:"Local snapclient")" "$(component_state "$CLIENT_PID_FILE")"
print_row "$(lang de:"Stream-Quelle" en:"Stream source")" "$SNAPCAST_STREAM_SOURCE"
print_row "$(lang de:"Client-Ziel" en:"Client target")" "${SNAPCAST_CLIENT_HOST}:${SNAPCAST_CLIENT_PORT}"
echo '</table>'
sec_end

if [ -r "$SERVER_CONFIG" ]; then
	sec_begin "$(lang de:"Generierte snapserver.conf" en:"Generated snapserver.conf")"
	echo '<pre class="log full">'
	cat "$SERVER_CONFIG" | html
	echo '</pre>'
	sec_end
fi

if [ -r "$SERVER_LOG" ]; then
	sec_begin "$(lang de:"Letzte Snapserver-Logzeilen" en:"Recent snapserver log lines")"
	echo '<pre class="log full">'
	tail -n 20 "$SERVER_LOG" | html
	echo '</pre>'
	sec_end
fi

if [ -r "$CLIENT_LOG" ]; then
	sec_begin "$(lang de:"Letzte Snapclient-Logzeilen" en:"Recent snapclient log lines")"
	echo '<pre class="log full">'
	tail -n 20 "$CLIENT_LOG" | html
	echo '</pre>'
	sec_end
fi

if ps 2>/dev/null | grep '[s]napserver\|[s]napclient' >/dev/null 2>&1; then
	sec_begin "$(lang de:"Prozessliste" en:"Process list")"
	echo '<pre class="log full">'
	ps 2>/dev/null | grep '[s]napserver\|[s]napclient' | html
	echo '</pre>'
	sec_end
fi

if [ -r /proc/asound/cards ]; then
	sec_begin "$(lang de:"Erkannte Soundkarten" en:"Detected sound cards")"
	echo '<pre class="log full">'
	cat /proc/asound/cards | html
	echo '</pre>'
	sec_end
fi

cat << EOF
<form class='btn' action='$(href status snapcast)' method='post' style='display:inline;'>
<input type='submit' value='$(lang de:"Aktualisieren" en:"Refresh")'>
</form>
&nbsp;&nbsp;
<form class='btn' action='$(href cgi snapcast)' method='get' style='display:inline;'>
<input type='submit' value='$(lang de:"Konfiguration" en:"Configuration")'>
</form>
EOF