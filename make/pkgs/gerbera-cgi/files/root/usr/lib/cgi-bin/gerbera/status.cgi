#!/bin/sh
# Gerbera status CGI

. /usr/lib/libmodcgi.sh

sec_begin "$(lang de:"Gerbera Status" en:"Gerbera Status")"

[ -r /mod/etc/conf/gerbera.cfg ] && . /mod/etc/conf/gerbera.cfg

RUNNING="no"
pgrep -x gerbera >/dev/null 2>&1 && RUNNING="yes"

cat <<-EOF
<table class="full">
<tr><td>$(lang de:"Daemon-Status" en:"Daemon status"):</td><td><b>${RUNNING}</b></td></tr>
<tr><td>$(lang de:"Port" en:"Port"):</td><td>${GERBERA_PORT:-49152}</td></tr>
<tr><td>$(lang de:"Datenverzeichnis" en:"Data directory"):</td><td>${GERBERA_BASEDIR:-/tmp/flash/gerbera}</td></tr>
</table>
EOF

sec_end
