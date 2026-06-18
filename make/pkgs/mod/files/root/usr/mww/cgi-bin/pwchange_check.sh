#!/bin/sh

WRONGPW=0
ID_IP=$(cat /tmp/pwchangesid 2>/dev/null)
CHAL=${ID_IP%#*}
IP=${ID_IP#*#}
oldhash="$(echo "$QUERY_STRING" | sed -n "s%.*oldhash=\([^\?\&]*\).*%\1%p")"
newhash="$(echo "$QUERY_STRING" | sed -n "s%.*newhash=\([^\?\&]*\).*%\1%p")"
UPWHASH=$(cat /tmp/flash/mod/webmd5 | tr -d '\n' )
myhash="$(echo -n "$CHAL$UPWHASH" | md5sum | sed 's/[ ]*-.*//')"


if [ "$REMOTE_ADDR" = "$IP" -a  "$oldhash" = "$myhash" ]; then
	echo "$newhash" > /tmp/flash/mod/webmd5
	modsave flash > /dev/null 2>&1
	# Also update legacy MOD_HTTPD_PASSWD to keep both auth systems in sync
	pw="$(echo "$QUERY_STRING" | sed -n "s%.*pw=\([^\?\&]*\).*%\1%p" | sed 's/%20/ /g; s/+/ /g')"
	if [ -n "$pw" ] && [ -x /usr/sbin/httpd ]; then
		newhash_httpd="$(echo "$pw" | /usr/sbin/httpd -m 2>/dev/null)"
		if [ -n "$newhash_httpd" ]; then
			modconf set mod MOD_HTTPD_PASSWD "$newhash_httpd"
			modsave mod > /dev/null 2>&1
		fi
	fi
	QUERY_STRING=""
	. /usr/mww/cgi-bin/pwchange.cgi successful
else
	WRONGPW=1
	QUERY_STRING=""
	. /usr/mww/cgi-bin/pwchange.cgi && exit
fi

