#!/bin/sh

. /usr/lib/libmodcgi.sh

PROXY_BIN=/usr/www/cgi-bin/freetz_proxy
CFG_FILE=/mod/etc/conf/freetz-proxy.cfg
DEFAULT_CFG=/mod/etc/default.freetz-proxy/freetz-proxy.cfg
EDIT_URL=/cgi-bin/file/freetz-proxy/cfg

# Read port from mod config (default 81)
FREETZ_PORT=81
[ -r /mod/etc/conf/mod.cfg ] && . /mod/etc/conf/mod.cfg
FREETZ_PORT="${MOD_HTTPD_PORT:-81}"

cgi_begin "$(lang de:"Freetz Proxy" en:"Freetz Proxy")"

# ── Status ────────────────────────────────────────────────────────────
echo '<h2>'
lang de:"Status" en:"Status"
echo '</h2>'

if [ -x "$PROXY_BIN" ]; then
	PROXY_SIZE=$(ls -lh "$PROXY_BIN" 2>/dev/null | awk '{print $5}')
	echo "<p>&#x2705; $(lang \
		de:"Proxy-Binary installiert: <code>$PROXY_BIN</code> ($PROXY_SIZE)" \
		en:"Proxy binary installed: <code>$PROXY_BIN</code> ($PROXY_SIZE)")</p>"
	echo "<p><a href=\"https://${HTTP_HOST}/cgi-bin/freetz_proxy\">"
	lang de:"&#x1F310; Freetz Proxy &#246;ffnen (HTTPS)" \
	     en:"&#x1F310; Open Freetz Proxy (HTTPS)"
	echo '</a></p>'
else
	print_warning "$(lang \
		de:"Proxy-Binary nicht gefunden: <code>$PROXY_BIN</code>" \
		en:"Proxy binary not found at <code>$PROXY_BIN</code>")"
fi

# ── Configuration ─────────────────────────────────────────────────────
echo '<h2>'
lang de:"Konfiguration" en:"Configuration"
echo '</h2>'

if [ -r "$CFG_FILE" ]; then
	ACTIVE_CFG="$CFG_FILE"
elif [ -r "$DEFAULT_CFG" ]; then
	ACTIVE_CFG="$DEFAULT_CFG"
	print_info "$(lang \
		de:"Keine gespeicherte Konfiguration gefunden — Standardwerte werden angezeigt." \
		en:"No saved configuration found — showing defaults.")"
else
	ACTIVE_CFG=""
fi

if [ -n "$ACTIVE_CFG" ]; then
	echo '<pre style="background:#f8f8f8;border:1px solid #ccc;padding:8px 12px;border-radius:4px;font-size:.9em">'
	html < "$ACTIVE_CFG"
	echo '</pre>'
fi

echo "<p><a href=\"$EDIT_URL\">"
lang de:"&#x270F; Konfiguration bearbeiten" \
     en:"&#x270F; Edit configuration"
echo '</a></p>'

# ── Format help ───────────────────────────────────────────────────────
echo '<h2>'
lang de:"Konfigurationsformat" en:"Configuration format"
echo '</h2>'
echo '<pre style="background:#f8f8f8;border:1px solid #ccc;padding:8px 12px;border-radius:4px;font-size:.85em">'
echo "$(lang \
  de:"# Format: name=port[:pfad[:direct]]
#   name   - Dienst-ID (wird in der URL verwendet: ?service=name)
#   port   - TCP-Port auf 127.0.0.1
#   pfad   - Standard-Upstream-Pfad (Standard: /)
#   direct - Das Wort \"direct\": Link &#246;ffnet direkt per HTTP statt &#252;ber den Proxy
#
# Bei \"direct\": Der Index zeigt einen HTTP-Link (fritz.box:port/pfad).
# Ohne \"direct\": Die Seite wird &#252;ber HTTPS durch den Proxy weitergeleitet.
#
# Beispiele:
freetz=${FREETZ_PORT}
rtorrent=${FREETZ_PORT}:/cgi-bin/conf/rtorrent
rutorrent=${FREETZ_PORT}:/rutorrent/:direct
ttyd=7681::direct" \
  en:"# Format: name=port[:path[:direct]]
#   name   - service identifier (used in URL: ?service=name)
#   port   - upstream TCP port on 127.0.0.1
#   path   - default upstream path (default: /)
#   direct - literal word \"direct\": opens as plain HTTP link instead of proxy
#
# With \"direct\": the index shows an HTTP link (fritz.box:port/path).
# Without \"direct\": the page is served through the HTTPS proxy.
#
# Examples:
freetz=${FREETZ_PORT}
rtorrent=${FREETZ_PORT}:/cgi-bin/conf/rtorrent
rutorrent=${FREETZ_PORT}:/rutorrent/:direct
ttyd=7681::direct")"
echo '</pre>'

cgi_end
