#!/bin/sh

. /usr/lib/libmodcgi.sh

[ -r /mod/etc/conf/mympd.cfg ] && . /mod/etc/conf/mympd.cfg

: ${MYMPD_WORKDIR:=/var/media/ftp/MediaServer/mympd}
: ${MYMPD_CACHEDIR:=/var/media/ftp/MediaServer/mympd/cache}
: ${MYMPD_HTTP:=yes}
: ${MYMPD_HTTP_HOST:=0.0.0.0}
: ${MYMPD_HTTP_PORT:=8080}
: ${MYMPD_SSL:=no}
: ${MYMPD_SSL_PORT:=8443}

MYMPD_WORKDIR="${MYMPD_WORKDIR%/}"
MYMPD_CACHEDIR="${MYMPD_CACHEDIR%/}"
CONFIG_DIR="${MYMPD_WORKDIR}/config"
STATE_DIR="${MYMPD_WORKDIR}/state"
SSL_DIR="${MYMPD_WORKDIR}/ssl"
LOG_FILE="${MYMPD_WORKDIR}/mympd.log"

SERVICE_STATE=$(/mod/etc/init.d/rc.mympd status 2>/dev/null)
PID_VALUE=$(cat /var/run/mympd.pid 2>/dev/null)
REFRESH=$(cgi_param refresh)
REQUEST_HOST="${HTTP_HOST%%:*}"
[ -n "$REQUEST_HOST" ] || REQUEST_HOST='fritz.box'

bool_yes() {
	case "$1" in
		yes|true|1|on) return 0 ;;
		*) return 1 ;;
	esac
}

safe_host() {
	case "$1" in
		''|*[!A-Za-z0-9:._-]*) return 1 ;;
		*) return 0 ;;
	esac
}

resolve_host() {
	case "$1" in
		''|0.0.0.0|::) echo "$REQUEST_HOST" ;;
		*) echo "$1" ;;
	esac
}

print_row() {
	label="$1"
	value="$2"
	[ -n "$value" ] || return 0
	echo "<tr><td style='width:220px'><b>$(html "$label")</b></td><td>$(html "$value")</td></tr>"
}

print_link_row() {
	label="$1"
	url="$2"
	[ -n "$url" ] || return 0
	echo "<tr><td style='width:220px'><b>$(html "$label")</b></td><td><a href='$(html "$url")' target='_blank'>$(html "$url")</a></td></tr>"
}

is_port_listening() {
	port="$1"
	case "$port" in
		''|*[!0-9]*) return 1 ;;
	esac
	hex_port=$(printf '%04X' "$port")
	awk -v hex_port="$hex_port" 'FNR > 1 { split($2, addr, ":"); if (addr[2] == hex_port && $4 == "0A") { found = 1; exit } } END { exit found ? 0 : 1 }' /proc/net/tcp /proc/net/tcp6 2>/dev/null
}

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

HTTP_LINK_HOST="$(resolve_host "$MYMPD_HTTP_HOST")"
SSL_LINK_HOST="$HTTP_LINK_HOST"
HTTP_URL=''
HTTPS_URL=''

if bool_yes "$MYMPD_HTTP" && is_port_listening "$MYMPD_HTTP_PORT"; then
	HTTP_LISTENER_STATE='yes'
	if safe_host "$HTTP_LINK_HOST"; then
		HTTP_URL="http://${HTTP_LINK_HOST}:${MYMPD_HTTP_PORT}/"
	fi
elif bool_yes "$MYMPD_HTTP"; then
	HTTP_LISTENER_STATE='no'
else
	HTTP_LISTENER_STATE='disabled'
fi

if bool_yes "$MYMPD_SSL" && is_port_listening "$MYMPD_SSL_PORT"; then
	HTTPS_LISTENER_STATE='yes'
	if safe_host "$SSL_LINK_HOST"; then
		HTTPS_URL="https://${SSL_LINK_HOST}:${MYMPD_SSL_PORT}/"
	fi
elif bool_yes "$MYMPD_SSL"; then
	HTTPS_LISTENER_STATE='no'
else
	HTTPS_LISTENER_STATE='disabled'
fi

if [ -d "$MYMPD_WORKDIR" ]; then
	WORKDIR_STATE='accessible'
else
	WORKDIR_STATE='missing'
fi

if [ -d "$MYMPD_CACHEDIR" ]; then
	CACHEDIR_STATE='accessible'
else
	CACHEDIR_STATE='missing'
fi

ACTIVE_MPD_HOST=$(cat "$STATE_DIR/mpd_host" 2>/dev/null)
ACTIVE_MPD_PORT=$(cat "$STATE_DIR/mpd_port" 2>/dev/null)

if [ -z "$MYMPD_MPD_HOST" ]; then
	CONFIGURED_MPD_HOST='autodetect'
else
	CONFIGURED_MPD_HOST="$MYMPD_MPD_HOST"
fi

if [ -z "$MYMPD_MPD_PORT" ]; then
	CONFIGURED_MPD_PORT='default'
else
	CONFIGURED_MPD_PORT="$MYMPD_MPD_PORT"
fi

sec_begin "$(lang de:"Daemonstatus" en:"Daemon status")"
echo "<table style='width:100%'>"
print_row "$(lang de:"Daemon" en:"Daemon")" "$SERVICE_STATE"
print_row "$(lang de:"PID" en:"PID")" "$PID_VALUE"
print_row "$(lang de:"Arbeitsverzeichnis" en:"Working directory")" "$MYMPD_WORKDIR"
print_row "$(lang de:"Arbeitsverzeichnis Status" en:"Working directory status")" "$WORKDIR_STATE"
print_row "$(lang de:"Cache-Verzeichnis" en:"Cache directory")" "$MYMPD_CACHEDIR"
print_row "$(lang de:"Cache-Verzeichnis Status" en:"Cache directory status")" "$CACHEDIR_STATE"
print_row "$(lang de:"HTTP-Listener" en:"HTTP listener")" "$HTTP_LISTENER_STATE"
print_row "$(lang de:"HTTPS-Listener" en:"HTTPS listener")" "$HTTPS_LISTENER_STATE"
print_link_row "$(lang de:"HTTP-URL" en:"HTTP URL")" "$HTTP_URL"
print_link_row "$(lang de:"HTTPS-URL" en:"HTTPS URL")" "$HTTPS_URL"
print_row "$(lang de:"Konfigurierter MPD-Host" en:"Configured MPD host")" "$CONFIGURED_MPD_HOST"
print_row "$(lang de:"Konfigurierter MPD-Port" en:"Configured MPD port")" "$CONFIGURED_MPD_PORT"
print_row "$(lang de:"Aktiver MPD-Host" en:"Active MPD host")" "$ACTIVE_MPD_HOST"
print_row "$(lang de:"Aktiver MPD-Port" en:"Active MPD port")" "$ACTIVE_MPD_PORT"
echo '</table>'
sec_end

sec_begin "$(lang de:"Bootstrap-Dateien" en:"Bootstrap files")"
echo "<table style='width:100%'>"
for name in http http_host http_port ssl ssl_port; do
	if [ -f "$CONFIG_DIR/$name" ]; then
		print_row "$name" "$(cat "$CONFIG_DIR/$name" 2>/dev/null)"
	fi
done
[ -d "$CONFIG_DIR" ] && print_row "$(lang de:"Konfigurationsverzeichnis" en:"Configuration directory")" "$CONFIG_DIR"
[ -d "$STATE_DIR" ] && print_row "$(lang de:"State-Verzeichnis" en:"State directory")" "$STATE_DIR"
[ -d "$SSL_DIR" ] && print_row "$(lang de:"SSL-Verzeichnis" en:"SSL directory")" "$SSL_DIR"
echo '</table>'
sec_end

if [ -r "$LOG_FILE" ]; then
	sec_begin "$(lang de:"Letzte Logzeilen" en:"Recent log lines")"
	echo '<pre class="log full">'
	tail -n 30 "$LOG_FILE" | html
	echo '</pre>'
	sec_end
fi

cat << EOF
<form class='btn' action='$(href status mympd)?refresh=5' method='post' style='display:inline;'>
<input type='submit' value='$(lang de:"Auto-Refresh 5s" en:"Auto refresh 5s")'>
</form>
&nbsp;&nbsp;
<form class='btn' action='$(href status mympd)' method='post' style='display:inline;'>
<input type='submit' value='$(lang de:"Einmal aktualisieren" en:"Refresh once")'>
</form>
&nbsp;&nbsp;
<form class='btn' action='$(href cgi mympd)' method='get' style='display:inline;'>
<input type='submit' value='$(lang de:"Konfiguration" en:"Configuration")'>
</form>
EOF