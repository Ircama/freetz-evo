#!/bin/sh

. /usr/lib/libmodcgi.sh

[ -r /mod/etc/conf/mympd.cfg ] && . /mod/etc/conf/mympd.cfg

: ${MYMPD_HTTP:=yes}
: ${MYMPD_HTTP_HOST:=0.0.0.0}
: ${MYMPD_HTTP_PORT:=8080}
: ${MYMPD_SSL:=no}
: ${MYMPD_SSL_PORT:=8443}

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

HTTP_LINK_HOST="$(resolve_host "$MYMPD_HTTP_HOST")"
SSL_LINK_HOST="$HTTP_LINK_HOST"

sec_begin "$(lang de:"Starttyp" en:"Start type")"
cgi_print_radiogroup_service_starttype "enabled" "$MYMPD_ENABLED" "" "" 0
sec_end

sec_begin "$(lang de:"Anzeigen" en:"Show")"
cat << EOF
<ul>
<li><a href="$(href status mympd)?refresh=5">$(lang de:"Status anzeigen" en:"Show status")</a></li>
EOF
if bool_yes "$MYMPD_HTTP" && safe_host "$HTTP_LINK_HOST"; then
	echo "<li><a href=\"http://${HTTP_LINK_HOST}:${MYMPD_HTTP_PORT}/\" target=\"_blank\">$(lang de:"myMPD per HTTP oeffnen" en:"Open myMPD over HTTP")</a></li>"
fi
if bool_yes "$MYMPD_SSL" && safe_host "$SSL_LINK_HOST"; then
	echo "<li><a href=\"https://${SSL_LINK_HOST}:${MYMPD_SSL_PORT}/\" target=\"_blank\">$(lang de:"myMPD per HTTPS oeffnen" en:"Open myMPD over HTTPS")</a></li>"
fi
cat << EOF
</ul>
EOF
sec_end

sec_begin "$(lang de:"Verzeichnisse" en:"Directories")"
cgi_print_textline_p "workdir" "$MYMPD_WORKDIR" 40/128 \
	"$(lang de:"Arbeitsverzeichnis" en:"Working directory"): "
cgi_print_textline_p "cachedir" "$MYMPD_CACHEDIR" 40/128 \
	"$(lang de:"Cache-Verzeichnis" en:"Cache directory"): "
sec_end

sec_begin "$(lang de:"Web-Oberflaeche" en:"Web interface")"
cgi_print_checkbox_p "http" "$MYMPD_HTTP" \
	"$(lang de:"HTTP aktivieren" en:"Enable HTTP")"
cgi_print_textline_p "http_host" "$MYMPD_HTTP_HOST" 24/128 \
	"$(lang de:"HTTP-Bind-Adresse" en:"HTTP bind address"): "
cgi_print_textline_p "http_port" "$MYMPD_HTTP_PORT" 8/8 \
	"$(lang de:"HTTP-Port" en:"HTTP port"): "
cgi_print_checkbox_p "ssl" "$MYMPD_SSL" \
	"$(lang de:"HTTPS aktivieren" en:"Enable HTTPS")"
cgi_print_textline_p "ssl_port" "$MYMPD_SSL_PORT" 8/8 \
	"$(lang de:"HTTPS-Port" en:"HTTPS port"): "
sec_end

sec_begin "$(lang de:"MPD-Backend" en:"MPD backend")"
cgi_print_textline_p "mpd_host" "$MYMPD_MPD_HOST" 32/255 \
	"$(lang de:"MPD-Host oder Socket (leer = Autodetect)" en:"MPD host or socket (empty = autodetect)"): "
cgi_print_textline_p "mpd_port" "$MYMPD_MPD_PORT" 8/8 \
	"$(lang de:"MPD-Port (leer = Standard)" en:"MPD port (empty = default)"): "
sec_end

sec_begin "$(lang de:"Hinweis" en:"Note")"
cat << EOF
<p>$(lang de:"Weitere myMPD-Anwendungseinstellungen werden nach dem ersten Start in der nativen myMPD-Weboberflaeche verwaltet." en:"Additional myMPD application settings are managed in the native myMPD web interface after the first start.")</p>
EOF
sec_end