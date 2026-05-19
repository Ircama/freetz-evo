#!/bin/sh

. /usr/lib/libmodcgi.sh

[ -r /mod/etc/conf/mpd.cfg ] && . /mod/etc/conf/mpd.cfg

: ${MPD_CONFIG_DIR:=/var/media/ftp/MediaServer/mpd}
: ${MPD_BIND_TO_ADDRESS:=0.0.0.0}
: ${MPD_PORT:=6600}
: ${MPD_MUSIC_DIR:=/var/media/ftp/MediaServer}

MPD_CONFIG_DIR="${MPD_CONFIG_DIR%/}"
CONFIG_FILE=/mod/etc/mpd.conf
LOG_FILE="${MPD_CONFIG_DIR}/mpd.log"
DB_FILE="${MPD_CONFIG_DIR}/database"
STATE_FILE="${MPD_CONFIG_DIR}/state"
PLAYLIST_DIR="${MPD_CONFIG_DIR}/playlists"
SOCKET_FILE=/var/run/mpd/socket
SERVICE_STATE=$(/mod/etc/init.d/rc.mpd status 2>/dev/null)
PID_VALUE=$(cat /var/run/mpd.pid 2>/dev/null)
REFRESH=$(cgi_param refresh)

case "$REFRESH" in
	''|*[!0-9]*) REFRESH=0 ;;
esac

if [ "$REFRESH" -gt 0 ] 2>/dev/null; then
	cat << EOF
<script type='text/javascript'>
window.setTimeout(function () { window.location.reload(); }, ${REFRESH}000);
</script>
EOF
fi

print_row() {
	local label="$1"
	local value="$2"
	[ -n "$value" ] || return 0
	echo "<tr><td style='width:220px'><b>$(html "$label")</b></td><td>$(html "$value")</td></tr>"
}

is_port_listening() {
	local port="$1"
	case "$port" in
		''|*[!0-9]*) return 1 ;;
	esac
	local hex_port
	hex_port=$(printf '%04X' "$port")
	awk -v hex_port="$hex_port" 'FNR > 1 { split($2, addr, ":"); if (addr[2] == hex_port && $4 == "0A") { found = 1; exit } } END { exit found ? 0 : 1 }' /proc/net/tcp /proc/net/tcp6 2>/dev/null
}

if [ -n "$MPD_BIND_TO_ADDRESS" ] && is_port_listening "$MPD_PORT"; then
	TCP_LISTENER_STATE='yes'
elif [ -n "$MPD_BIND_TO_ADDRESS" ]; then
	TCP_LISTENER_STATE='no'
else
	TCP_LISTENER_STATE='disabled'
fi

if [ -S "$SOCKET_FILE" ] 2>/dev/null; then
	SOCKET_STATE='yes'
elif [ -e "$SOCKET_FILE" ]; then
	SOCKET_STATE='present'
else
	SOCKET_STATE='no'
fi

case "$MPD_MUSIC_DIR" in
	'' ) MUSIC_DIR_STATE='not configured' ;;
	*://* ) MUSIC_DIR_STATE='remote storage URL' ;;
	* ) [ -d "$MPD_MUSIC_DIR" ] && MUSIC_DIR_STATE='accessible' || MUSIC_DIR_STATE='missing' ;;
esac

sec_begin "$(lang de:"Daemonstatus" en:"Daemon status")"
echo "<table style='width:100%'>"
print_row "$(lang de:"Daemon" en:"Daemon")" "$SERVICE_STATE"
print_row "$(lang de:"PID" en:"PID")" "$PID_VALUE"
print_row "$(lang de:"Arbeitsverzeichnis" en:"Working directory")" "$MPD_CONFIG_DIR"
print_row "$(lang de:"Musikverzeichnis" en:"Music directory")" "$MPD_MUSIC_DIR"
print_row "$(lang de:"Musikverzeichnis erreichbar" en:"Music directory status")" "$MUSIC_DIR_STATE"
print_row "$(lang de:"TCP-Listener" en:"TCP listener")" "$TCP_LISTENER_STATE"
print_row "$(lang de:"Unix-Socket" en:"Unix socket")" "$SOCKET_STATE"
print_row "$(lang de:"Bind-Adresse" en:"Bind address")" "$MPD_BIND_TO_ADDRESS"
print_row "$(lang de:"Port" en:"Port")" "$MPD_PORT"
print_row "$(lang de:"ALSA-Geraet" en:"ALSA device")" "$MPD_ALSA_DEVICE"
print_row "$(lang de:"Mixer-Typ" en:"Mixer type")" "$MPD_MIXER_TYPE"
echo '</table>'
sec_end

sec_begin "$(lang de:"Dateistatus" en:"File status")"
echo "<table style='width:100%'>"
[ -f "$CONFIG_FILE" ] && print_row "$(lang de:"Konfiguration" en:"Configuration")" "$CONFIG_FILE"
[ -f "$LOG_FILE" ] && print_row "$(lang de:"Logdatei" en:"Log file")" "$LOG_FILE"
[ -f "$DB_FILE" ] && print_row "$(lang de:"Datenbank" en:"Database")" "$DB_FILE"
[ -f "$STATE_FILE" ] && print_row "$(lang de:"Statusdatei" en:"State file")" "$STATE_FILE"
[ -d "$PLAYLIST_DIR" ] && print_row "$(lang de:"Playlist-Verzeichnis" en:"Playlist directory")" "$PLAYLIST_DIR"
[ -d "$DB_FILE" ] && print_row "$(lang de:"Datenbankpfad" en:"Database path")" "$(lang de:"FEHLER: ist Verzeichnis" en:"ERROR: is directory")"
[ -d "$STATE_FILE" ] && print_row "$(lang de:"Statusdateipfad" en:"State file path")" "$(lang de:"FEHLER: ist Verzeichnis" en:"ERROR: is directory")"
echo '</table>'
sec_end

if [ -r "$CONFIG_FILE" ]; then
	sec_begin "$(lang de:"Generierte Konfiguration" en:"Generated configuration")"
	echo '<pre class="log full">'
	cat "$CONFIG_FILE" | html
	echo '</pre>'
	sec_end
fi

alsa_params_found=0
for hw_params in /proc/asound/card*/pcm*p/sub*/hw_params; do
	[ -r "$hw_params" ] || continue
	if grep -qx 'closed' "$hw_params" 2>/dev/null; then
		continue
	fi
	if [ "$alsa_params_found" -eq 0 ]; then
		sec_begin "$(lang de:"Aktive ALSA-Parameter" en:"Active ALSA parameters")"
		echo '<pre class="log full">'
		alsa_params_found=1
	fi
	echo "### $hw_params" | html
	cat "$hw_params" | html
	echo
done
if [ "$alsa_params_found" -eq 1 ]; then
	echo '</pre>'
	sec_end
fi

if [ -r "$LOG_FILE" ]; then
	sec_begin "$(lang de:"Letzte Logzeilen" en:"Recent log lines")"
	echo '<pre class="log full">'
	tail -n 30 "$LOG_FILE" | html
	echo '</pre>'
	sec_end
fi

cat << EOF
<form class='btn' action='$(href status mpd)?refresh=5' method='post' style='display:inline;'>
<input type='submit' value='$(lang de:"Auto-Refresh 5s" en:"Auto refresh 5s")'>
</form>
&nbsp;&nbsp;
<form class='btn' action='$(href status mpd)' method='post' style='display:inline;'>
<input type='submit' value='$(lang de:"Einmal aktualisieren" en:"Refresh once")'>
</form>
&nbsp;&nbsp;
<form class='btn' action='$(href cgi mpd)' method='get' style='display:inline;'>
<input type='submit' value='$(lang de:"Konfiguration" en:"Configuration")'>
</form>
EOF