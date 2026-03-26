#!/bin/sh

. /usr/lib/libmodcgi.sh

# ── Paths ─────────────────────────────────────────────────────────────
for _b in \
/mod/external/usr/www/cgi-bin/freetz_proxy \
/usr/www/cgi-bin/freetz_proxy; do
[ -x "$_b" ] && { PROXY_BIN="$_b"; break; }
done
PROXY_BIN="${PROXY_BIN:-/usr/www/cgi-bin/freetz_proxy}"
FLASH_CFG=/tmp/flash/mod/freetz-proxy.cfg
CFG_FILE=/mod/etc/conf/freetz-proxy.cfg
DEFAULT_CFG=/mod/etc/default.freetz-proxy/freetz-proxy.cfg

# ── Read Freetz HTTP port ─────────────────────────────────────────────
FREETZ_PORT=81
[ -r /mod/etc/conf/mod.cfg ] && . /mod/etc/conf/mod.cfg
FREETZ_PORT="${MOD_HTTPD_PORT:-81}"

# ── Determine active config file ──────────────────────────────────────
if [ -r "$FLASH_CFG" ]; then
ACTIVE_CFG="$FLASH_CFG"
elif [ -r "$CFG_FILE" ]; then
ACTIVE_CFG="$CFG_FILE"
elif [ -r "$DEFAULT_CFG" ]; then
ACTIVE_CFG="$DEFAULT_CFG"
else
ACTIVE_CFG=""
fi

# ── Parse @directives from active config ──────────────────────────────
DISABLED=no
BLOCK_INTERNET=no
NO_INTERNET_COOKIE=yes
NO_COOKIE=no
INTERNET_DOMAINS=.myfritz.net
TRACE_FILE=
if [ -n "$ACTIVE_CFG" ]; then
while IFS= read -r cfgline; do
case "$cfgline" in
'@disabled=yes')           DISABLED=yes ;;
'@disabled=no')            DISABLED=no ;;
'@block_internet=yes')     BLOCK_INTERNET=yes ;;
'@block_internet=no')      BLOCK_INTERNET=no ;;
'@no_internet_cookie=yes') NO_INTERNET_COOKIE=yes ;;
'@no_internet_cookie=no')  NO_INTERNET_COOKIE=no ;;
'@no_cookie=yes')          NO_COOKIE=yes ;;
'@no_cookie=no')           NO_COOKIE=no ;;
@internet_domains=*)       INTERNET_DOMAINS="${cfgline#@internet_domains=}" ;;
@trace_file=*)             TRACE_FILE="${cfgline#@trace_file=}" ;;
esac
done < "$ACTIVE_CFG"
fi

# ── Handle save: GET ?action=save  (cgi_param reads QUERY_STRING) ─────
_action="$(cgi_param action)"
if [ "$_action" = "save" ]; then
_dis="$(cgi_param disabled)"
_bi="$(cgi_param block_internet)"
_nic="$(cgi_param no_internet_cookie)"
_nc="$(cgi_param no_cookie)"
_id="$(cgi_param internet_domains)"
_tf="$(cgi_param trace_file)"

# Sanitize free-text fields: strip shell metacharacters
_id="$(printf '%s' "$_id" | tr -d '\n\r;&`$|<>\\"'"'"'")"
_tf="$(printf '%s' "$_tf" | tr -d '\n\r;&`$|<>\\"'"'"'")"
# internet_domains must not be empty (restore default)
[ -z "$_id" ] && _id=".myfritz.net"

if [ -x "$PROXY_BIN" ]; then
"$PROXY_BIN" --set \
"@disabled=$([ "$_dis" = "on" ] && echo yes || echo no)" \
"@block_internet=$([ "$_bi" = "on" ] && echo yes || echo no)" \
"@no_internet_cookie=$([ "$_nic" = "on" ] && echo yes || echo no)" \
"@no_cookie=$([ "$_nc" = "on" ] && echo yes || echo no)" \
"@internet_domains=$_id" \
"@trace_file=$_tf"
modsave flash 2>/dev/null || true
fi
# PRG redirect (avoids re-submit on back/refresh)
echo "Location: /cgi-bin/file/mod/freetz_proxy"
echo ""
exit 0
fi

# ── HTML output ───────────────────────────────────────────────────────
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
if [ "$DISABLED" = "yes" ]; then
echo "<p>&#x26A0; $(lang \
de:"Freetz Proxy ist <strong>deaktiviert</strong>." \
en:"Freetz Proxy is <strong>disabled</strong>.")</p>"
else
echo "<p><a href=\"https://${HTTP_HOST}/cgi-bin/freetz_proxy\">"
lang de:"&#x1F310; Freetz Proxy &#246;ffnen (HTTPS)" \
     en:"&#x1F310; Open Freetz Proxy (HTTPS)"
echo '</a></p>'
fi
else
print_warning "$(lang \
de:"Proxy-Binary nicht gefunden: <code>$PROXY_BIN</code>" \
en:"Proxy binary not found at <code>$PROXY_BIN</code>")"
fi

# ── Proxy options form ────────────────────────────────────────────────
echo '<h2>'
lang de:"Einstellungen" en:"Proxy Options"
echo '</h2>'

echo '<form method="get" action="/cgi-bin/file/mod/freetz_proxy">'
echo '<input type="hidden" name="action" value="save">'
echo '<table style="border-collapse:collapse">'

for _row in \
"disabled|$DISABLED|$(lang \
de:"Proxy deaktivieren (liefert stattdessen eine Hinweisseite)" \
en:"Disable proxy (returns a notice page for all requests)")" \
"block_internet|$BLOCK_INTERNET|$(lang \
de:"Zugriff aus dem Internet sperren (*.myfritz.net \342\206\222 403)" \
en:"Block access from internet (*.myfritz.net \342\206\222 403)")" \
"no_internet_cookie|$NO_INTERNET_COOKIE|$(lang \
de:"Sitzungs-Cookie bei Internetzugriff (Max-Age/Expires entfernen)" \
en:"Session-only cookies from internet (strip Max-Age/Expires)")" \
"no_cookie|$NO_COOKIE|$(lang \
de:"Sitzungs-Cookie immer (Max-Age/Expires immer entfernen)" \
en:"Session-only cookies always (strip Max-Age/Expires always)")"; do
_key="${_row%%|*}"; _tmp="${_row#*|}"; _val="${_tmp%%|*}"; _desc="${_tmp#*|}"
[ "$_val" = "yes" ] && _checked='checked="checked"' || _checked=""
echo "<tr>"
echo "<td style=\"padding:4px 8px\"><input type=\"checkbox\" name=\"${_key}\" id=\"cb_${_key}\" value=\"on\" ${_checked}></td>"
echo "<td style=\"padding:4px 8px\"><label for=\"cb_${_key}\"><code>@${_key}</code></label></td>"
echo "<td style=\"padding:4px 8px;color:#555;font-size:.9em\">${_desc}</td>"
echo "</tr>"
done

# ── internet_domains text field ───────────────────────────────────────
echo "<tr>"
echo "<td style=\"padding:4px 8px\">&nbsp;</td>"
echo "<td style=\"padding:4px 8px\"><code>@internet_domains</code></td>"
echo "<td style=\"padding:4px 8px\">"
echo "<input type=\"text\" name=\"internet_domains\" value=\"$(html "$INTERNET_DOMAINS")\" style=\"width:100%;max-width:320px\">"
echo "<br><span style=\"font-size:.85em;color:#777\">$(lang \
de:"Kommagetrennte Teilstrings f&#252;r Internetzugriff-Erkennung (Standard: .myfritz.net)" \
en:"Comma-separated substrings indicating internet access (default: .myfritz.net)")</span>"
echo "</td></tr>"

# ── trace_file text field ─────────────────────────────────────────────
echo "<tr>"
echo "<td style=\"padding:4px 8px\">&nbsp;</td>"
echo "<td style=\"padding:4px 8px\"><code>@trace_file</code></td>"
echo "<td style=\"padding:4px 8px\">"
echo "<input type=\"text\" name=\"trace_file\" value=\"$(html "$TRACE_FILE")\" placeholder=\"$(lang de:"leer = kein Log" en:"empty = no log")\" style=\"width:100%;max-width:320px\">"
echo "<br><span style=\"font-size:.85em;color:#777\">$(lang \
de:"Pfad f&#252;r Trace-Log (leer = deaktiviert; Beispiel: /tmp/freetz_proxy.log)" \
en:"Trace log path (empty = disabled; example: /tmp/freetz_proxy.log)")</span>"
echo "</td></tr>"

echo '</table>'
echo "<p><input type=\"submit\" value=\"$(lang de:"&#x1F4BE; Speichern" en:"&#x1F4BE; Save")\"></p>"
echo '</form>'

# ── Raw config file ───────────────────────────────────────────────────
echo '<h2>'
lang de:"Konfigurationsdatei" en:"Configuration File"
echo '</h2>'

if [ -z "$ACTIVE_CFG" ]; then
print_info "$(lang \
de:"Keine Konfiguration gefunden \342\200\224 Standardwerte werden verwendet." \
en:"No saved configuration found \342\200\224 defaults are in effect.")"
else
echo '<pre style="background:#f8f8f8;border:1px solid #ccc;padding:8px 12px;border-radius:4px;font-size:.9em">'
html < "$ACTIVE_CFG"
echo '</pre>'
fi

echo "<p><a href=\"/cgi-bin/file/mod/freetz_proxy\">"
lang de:"&#x270F; Konfigurationsdatei direkt bearbeiten" \
     en:"&#x270F; Edit configuration file directly"
echo '</a></p>'

# ── Format help ───────────────────────────────────────────────────────
echo '<h2>'
lang de:"Konfigurationsformat" en:"Configuration format"
echo '</h2>'
echo '<pre style="background:#f8f8f8;border:1px solid #ccc;padding:8px 12px;border-radius:4px;font-size:.85em">'
echo "$(lang \
  de:"# Format: name=port[:pfad[:direct]]
#   name   - Dienst-ID (in der URL: ?service=name)
#   port   - TCP-Port auf 127.0.0.1 (0 = Freetz-Port aus mod.cfg)
#   pfad   - Upstream-Pfad (Standard: /)
#   direct - Wort \"direct\": Index zeigt HTTP-Link statt Proxy-Link
#
# Beispiel:
freetz=0
rtorrent=0:/cgi-bin/conf/rtorrent
rutorrent=0:/rutorrent/:direct
ariang=0:/ariang/:direct
ttyd=7681::direct" \
  en:"# Format: name=port[:path[:direct]]
#   name   - service identifier (in URL: ?service=name)
#   port   - upstream TCP port on 127.0.0.1 (0 = Freetz port from mod.cfg)
#   path   - default upstream path (default: /)
#   direct - literal word \"direct\": index shows HTTP link instead of proxy
#
# Example:
freetz=0
rtorrent=0:/cgi-bin/conf/rtorrent
rutorrent=0:/rutorrent/:direct
ariang=0:/ariang/:direct
ttyd=7681::direct")"
echo '</pre>'

cgi_end
