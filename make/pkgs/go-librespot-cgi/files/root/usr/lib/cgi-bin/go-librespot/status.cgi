#!/bin/sh

. /usr/lib/libmodcgi.sh

[ -r /mod/etc/conf/go-librespot.cfg ] && . /mod/etc/conf/go-librespot.cfg

: ${GO_LIBRESPOT_CONFIG_DIR:=/tmp/flash/go-librespot}
GO_LIBRESPOT_CONFIG_DIR="${GO_LIBRESPOT_CONFIG_DIR%/}"
CONFIG_FILE="${GO_LIBRESPOT_CONFIG_DIR}/config.yml"
LOG_FILE="${GO_LIBRESPOT_CONFIG_DIR}/go-librespot.log"
STATE_FILE="${GO_LIBRESPOT_CONFIG_DIR}/state.json"
LOCK_FILE="${GO_LIBRESPOT_CONFIG_DIR}/lockfile"
SERVICE_STATE=$(/mod/etc/init.d/rc.go-librespot status 2>/dev/null)
PID_VALUE=$(cat /var/run/go-librespot.pid 2>/dev/null)
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

sec_begin "$(lang de:"Daemonstatus" en:"Daemon status")"
echo "<table style='width:100%'>"
print_row "$(lang de:"Daemon" en:"Daemon")" "$SERVICE_STATE"
print_row "$(lang de:"PID" en:"PID")" "$PID_VALUE"
print_row "$(lang de:"Geraetename" en:"Device name")" "$GO_LIBRESPOT_DEVICE_NAME"
print_row "$(lang de:"Geraetetyp" en:"Device type")" "$GO_LIBRESPOT_DEVICE_TYPE"
print_row "$(lang de:"Audio Device" en:"Audio device")" "$GO_LIBRESPOT_AUDIO_DEVICE"
print_row "$(lang de:"Konfigurationsverzeichnis" en:"Configuration directory")" "$GO_LIBRESPOT_CONFIG_DIR"
echo '</table>'
sec_end

sec_begin "$(lang de:"Dateistatus" en:"File status")"
echo "<table style='width:100%'>"
[ -f "$CONFIG_FILE" ] && print_row "$(lang de:"YAML-Konfiguration" en:"YAML configuration")" "$CONFIG_FILE"
[ -f "$STATE_FILE" ] && print_row "$(lang de:"Persistenter Status" en:"Persistent state")" "$STATE_FILE"
[ -f "$LOCK_FILE" ] && print_row "$(lang de:"Lock-Datei" en:"Lock file")" "$LOCK_FILE"
[ -f "$LOG_FILE" ] && print_row "$(lang de:"Logdatei" en:"Log file")" "$LOG_FILE"
echo '</table>'
sec_end

if [ -r "$CONFIG_FILE" ]; then
	sec_begin "$(lang de:"Generierte Konfiguration" en:"Generated configuration")"
	echo '<pre class="log full">'
	cat "$CONFIG_FILE" | html
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
<form class='btn' action='$(href status go-librespot)?refresh=5' method='post' style='display:inline;'>
<input type='submit' value='$(lang de:"Auto-Refresh 5s" en:"Auto refresh 5s")'>
</form>
&nbsp;&nbsp;
<form class='btn' action='$(href status go-librespot)' method='post' style='display:inline;'>
<input type='submit' value='$(lang de:"Einmal aktualisieren" en:"Refresh once")'>
</form>
&nbsp;&nbsp;
<form class='btn' action='$(href cgi go-librespot)' method='get' style='display:inline;'>
<input type='submit' value='$(lang de:"Konfiguration" en:"Configuration")'>
</form>
EOF