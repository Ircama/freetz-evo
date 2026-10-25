#!/bin/sh

. /usr/lib/libmodcgi.sh
[ -r /etc/options.cfg ] && . /etc/options.cfg

sec_begin "$(lang de:"Starttyp" en:"Start type")"
cgi_print_radiogroup_service_starttype "enabled" "$SER2NET_ENABLED" "" "" 0
sec_end

sec_begin "$(lang de:"Konfiguration" en:"Configuration")"

if [ "$FREETZ_PACKAGE_SER2NET_ABANDON" == "y" ]; then
cat << EOF
<ul>
<li><a href="$(href file ser2net conf)">$(lang de:"ser2net.conf bearbeiten" en:"Edit ser2net.conf")</a></li>
</ul>
EOF
else
cat << EOF
<ul>
<li><a href="$(href file ser2net yaml)">$(lang de:"ser2net.yaml bearbeiten" en:"Edit ser2net.yaml")</a></li>
</ul>
EOF
fi

sec_end

