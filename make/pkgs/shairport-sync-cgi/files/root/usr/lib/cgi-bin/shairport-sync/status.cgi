#!/bin/sh

. /usr/lib/libmodcgi.sh

STATUS_FILE=/tmp/shairport-sync/status.env
LOG_FILE=/var/log/shairport-sync.log
SERVICE_STATE=$(/mod/etc/init.d/rc.shairport-sync status 2>/dev/null)

SHAIRPORT_SYNC_STATUS_STATE=idle
SHAIRPORT_SYNC_STATUS_ACTIVE=no
SHAIRPORT_SYNC_STATUS_TITLE=''
SHAIRPORT_SYNC_STATUS_ARTIST=''
SHAIRPORT_SYNC_STATUS_ALBUM=''
SHAIRPORT_SYNC_STATUS_CLIENT_NAME=''
SHAIRPORT_SYNC_STATUS_CLIENT_IP=''
SHAIRPORT_SYNC_STATUS_VOLUME=''
SHAIRPORT_SYNC_STATUS_PROGRESS=''
SHAIRPORT_SYNC_STATUS_UPDATED=''

[ -r "$STATUS_FILE" ] && . "$STATUS_FILE"

print_row() {
	local label="$1"
	local value="$2"
	[ -n "$value" ] || return 0
	echo "<tr><td style='width:220px'><b>$(html "$label")</b></td><td>$(html "$value")</td></tr>"
}

sec_begin "$(lang de:"Empfaengerstatus" en:"Receiver status")"
echo "<table style='width:100%'>"
print_row "$(lang de:"Daemon" en:"Daemon")" "$SERVICE_STATE"
print_row "$(lang de:"Aktiv" en:"Active")" "$SHAIRPORT_SYNC_STATUS_ACTIVE"
print_row "$(lang de:"Wiedergabestatus" en:"Playback state")" "$SHAIRPORT_SYNC_STATUS_STATE"
print_row "$(lang de:"Zuletzt aktualisiert" en:"Last update")" "$SHAIRPORT_SYNC_STATUS_UPDATED"
echo '</table>'
sec_end

sec_begin "$(lang de:"Metadaten" en:"Metadata")"
echo "<table style='width:100%'>"
print_row "$(lang de:"Titel" en:"Title")" "$SHAIRPORT_SYNC_STATUS_TITLE"
print_row "$(lang de:"Interpret" en:"Artist")" "$SHAIRPORT_SYNC_STATUS_ARTIST"
print_row "$(lang de:"Album" en:"Album")" "$SHAIRPORT_SYNC_STATUS_ALBUM"
print_row "$(lang de:"Client" en:"Client")" "$SHAIRPORT_SYNC_STATUS_CLIENT_NAME"
print_row "$(lang de:"Client-IP" en:"Client IP")" "$SHAIRPORT_SYNC_STATUS_CLIENT_IP"
print_row "$(lang de:"Lautstaerke" en:"Volume")" "$SHAIRPORT_SYNC_STATUS_VOLUME"
print_row "$(lang de:"Fortschritt" en:"Progress")" "$SHAIRPORT_SYNC_STATUS_PROGRESS"
echo '</table>'
sec_end

if [ -r "$LOG_FILE" ]; then
	sec_begin "$(lang de:"Letzte Logzeilen" en:"Recent log lines")"
	echo '<pre class="log full">'
	tail -n 20 "$LOG_FILE" | html
	echo '</pre>'
	sec_end
fi

cat << EOF
<form class='btn' action='$(href status shairport-sync)' method='post' style='display:inline;'>
<input type='submit' value='$(lang de:"Aktualisieren" en:"Refresh")'>
</form>
&nbsp;&nbsp;
<form class='btn' action='$(href cgi shairport-sync)' method='get' style='display:inline;'>
<input type='submit' value='$(lang de:"Konfiguration" en:"Configuration")'>
</form>
EOF