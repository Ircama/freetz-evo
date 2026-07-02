#!/bin/sh
# Gerbera CGI web interface for freetz-ng
# Minimal configuration interface

DAEMON=gerbera
. /etc/init.d/modlibrc

cgi_begin "$(lang de:"Gerbera Media Server" en:"Gerbera Media Server")"

[ -r /mod/etc/conf/gerbera.cfg ] && . /mod/etc/conf/gerbera.cfg

sec_begin "$(lang de:"Allgemein" en:"General")"
cgi_print_radiogroup_service_starttype "enabled" "$GERBERA_ENABLED" "" "" 0
cgi_print_textline_p "basedir" "$GERBERA_BASEDIR" 40/128 \
	"$(lang de:"Datenverzeichnis" en:"Data directory"): "
cgi_print_textline_p "port" "$GERBERA_PORT" 8/8 \
	"$(lang de:"Port" en:"Port"): "
cgi_print_textline_p "friendly_name" "$GERBERA_FRIENDLY_NAME" 40/128 \
	"$(lang de:"Server-Name" en:"Server name"): "
sec_end

cgi_end
