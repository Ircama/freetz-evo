#!/bin/sh

. /usr/lib/libmodcgi.sh

[ -r /mod/etc/conf/mpd-mpc.cfg ] && . /mod/etc/conf/mpd-mpc.cfg

: ${MPD_MPC_ENABLED:=no}
: ${MPD_MPC_HOST:=/var/run/mpd/socket}
: ${MPD_MPC_PORT:=6600}
: ${MPD_MPC_PARTITION:=}
: ${MPD_MPC_PASSWORD:=}
: ${MPD_MPC_DB_URL:=https://jcorporation.github.io/webradiodb/db/index/webradiodb-combined.min.json}
: ${MPD_MPC_DB_CACHE_DIR:=/tmp/mpd-mpc}
: ${MPD_MPC_STARTUP_NAME:=}
: ${MPD_MPC_STARTUP_URI:=}
: ${MPD_MPC_STARTUP_IMAGE:=}
: ${MPD_MPC_STARTUP_HOMEPAGE:=}
: ${MPD_MPC_STARTUP_VOLUME:=}
: ${MPD_MPC_STARTUP_CLEAR:=yes}
: ${MPD_MPC_STARTUP_WAIT:=45}

prefill_or_saved() {
	value="$(cgi_param "$1")"
	if [ -n "$value" ]; then
		printf '%s' "$value"
	else
		printf '%s' "$2"
	fi
}

DISPLAY_STARTUP_NAME="$(prefill_or_saved startup_name "$MPD_MPC_STARTUP_NAME")"
DISPLAY_STARTUP_URI="$(prefill_or_saved startup_uri "$MPD_MPC_STARTUP_URI")"
DISPLAY_STARTUP_IMAGE="$(prefill_or_saved startup_image "$MPD_MPC_STARTUP_IMAGE")"
DISPLAY_STARTUP_HOMEPAGE="$(prefill_or_saved startup_homepage "$MPD_MPC_STARTUP_HOMEPAGE")"

sec_begin "$(lang de:"Autoplay beim Booten" en:"Autoplay on boot")"
cgi_print_checkbox_p "enabled" "$MPD_MPC_ENABLED" \
	"$(lang de:"Beim Laden die gespeicherte Station automatisch in MPD einreihen und starten" en:"Queue and start the saved station automatically when the package is loaded")"
cgi_print_textline_p "startup_name" "$DISPLAY_STARTUP_NAME" 32/160 \
	"$(lang de:"Stationsname (optional)" en:"Station name (optional)"): "
cgi_print_textline_p "startup_uri" "$DISPLAY_STARTUP_URI" 48/255 \
	"$(lang de:"Stream-URI" en:"Stream URI"): "
cgi_print_textline_p "startup_image" "$DISPLAY_STARTUP_IMAGE" 40/255 \
	"$(lang de:"Bild oder WebRadioDB-Image (optional)" en:"Image or WebRadioDB image (optional)"): "
cgi_print_textline_p "startup_homepage" "$DISPLAY_STARTUP_HOMEPAGE" 40/255 \
	"$(lang de:"Homepage (optional)" en:"Homepage (optional)"): "
cgi_print_textline_p "startup_volume" "$MPD_MPC_STARTUP_VOLUME" 8/8 \
	"$(lang de:"Lautstaerke beim Start (leer = unveraendert)" en:"Startup volume (empty = keep current)"): "
cgi_print_checkbox_p "startup_clear" "$MPD_MPC_STARTUP_CLEAR" \
	"$(lang de:"Queue vor dem Start leeren" en:"Clear queue before playback")"
cgi_print_textline_p "startup_wait" "$MPD_MPC_STARTUP_WAIT" 8/8 \
	"$(lang de:"Wartezeit fuer erreichbaren MPD in Sekunden" en:"Wait time for reachable MPD in seconds"): "
sec_end

sec_begin "$(lang de:"MPD-Verbindung" en:"MPD connection")"
cgi_print_textline_p "host" "$MPD_MPC_HOST" 24/128 \
	"$(lang de:"Host oder Socket" en:"Host or socket"): "
cgi_print_textline_p "port" "$MPD_MPC_PORT" 8/8 \
	"$(lang de:"Port" en:"Port"): "
cgi_print_textline_p "partition" "$MPD_MPC_PARTITION" 16/64 \
	"$(lang de:"Partition (optional)" en:"Partition (optional)"): "
cgi_print_textline_p "password" "$MPD_MPC_PASSWORD" 20/64 \
	"$(lang de:"Passwort (optional)" en:"Password (optional)"): "
cat << EOF
<p>
$(lang de:"Fuer lokale MPD-Instanzen ist <code>/var/run/mpd/socket</code> der robusteste Standard. Wenn stattdessen ein lokaler TCP-Host wie <code>127.0.0.1</code> eingetragen ist, verwendet die Status-Seite automatisch den Unix-Socket, sobald er verfuegbar ist." en:"For local MPD instances, <code>/var/run/mpd/socket</code> is the most reliable default. If a local TCP host such as <code>127.0.0.1</code> is configured instead, the status page automatically falls back to the Unix socket whenever it is available.")
</p>
EOF
sec_end

sec_begin "$(lang de:"WebRadioDB" en:"WebRadioDB")"
cgi_print_textline_p "db_url" "$MPD_MPC_DB_URL" 48/255 \
	"$(lang de:"JSON-Quelle" en:"JSON source"): "
cgi_print_textline_p "db_cache_dir" "$MPD_MPC_DB_CACHE_DIR" 40/160 \
	"$(lang de:"Cache-Verzeichnis" en:"Cache directory"): "
cat << EOF
<p>
$(lang de:"Die Live-Seite kann die WebRadioDB-Daten lokal cachen, in der Web-Oberflaeche filtern und Stationsdaten direkt als Startprofil speichern." en:"The live page can cache the WebRadioDB dataset locally, filter it in the browser and save a selected station directly as startup profile.")
</p>
EOF
sec_end

sec_begin "$(lang de:"Anzeigen" en:"Show")"
cat << EOF
<ul>
<li><a href="$(href status mpd-mpc)">$(lang de:"Live-Status, MPD-Steuerung und WebRadioDB anzeigen" en:"Show live status, MPD controls and WebRadioDB browser")</a></li>
</ul>
EOF
sec_end

sec_begin "$(lang de:"Hinweise" en:"Notes")"
cat << EOF
<p>
$(lang de:"Die Status-Seite kann eine Station sofort per <code>mpc clear</code>, <code>mpc add</code> und <code>mpc play</code> starten oder nur in die Queue einreihen. Das Speichern eines Startprofils setzt <code>MPD_MPC_ENABLED=yes</code> und schreibt Name, URI, Bild und Homepage in die persistente Konfiguration." en:"The status page can start a station immediately with <code>mpc clear</code>, <code>mpc add</code> and <code>mpc play</code>, or only queue it. Saving a startup profile sets <code>MPD_MPC_ENABLED=yes</code> and writes name, URI, image and homepage into the persistent configuration.")
</p>
EOF
sec_end
