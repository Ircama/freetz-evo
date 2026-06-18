#!/bin/sh

# Ensure standard system directories are in PATH (busybox applets like md5sum,
# tr, head etc. live under /usr/bin which may not be in PATH during early CGI
# execution if /var/env.mod.daemon hasn't been loaded yet)
export PATH="${PATH:-/bin:/sbin:/usr/bin:/usr/sbin}"

WRONGPW=0
ID_IP=$(cat /tmp/loginsid 2>/dev/null)
SID=${ID_IP%#*}
IP=${ID_IP#*#}
hash=${QUERY_STRING##*hash=}
# Ensure /tmp/flash/mod/ exists before trying to create webmd5.
# This directory may not exist yet if modload was skipped because
# AVM's init already created /tmp/flash.
mkdir -p /tmp/flash/mod 2>/dev/null
[ -f /tmp/flash/mod/webmd5 ] || echo -n "465d0ff27bb239292778dc3a0c2f28d9" > /tmp/flash/mod/webmd5
UPWHASH=$(cat /tmp/flash/mod/webmd5 | tr -d '\n' )
myhash="$(echo -n "$SID$UPWHASH" | md5sum | sed 's/[ ]*-.*//')"

if [ "$REMOTE_ADDR" = "$IP" -a "$hash" = "$myhash" ]; then
	touch /tmp/$SID.webcfg
else
	SENDSID=""
	QUERY_STRING=""
	WRONGPW=1
	. /usr/mww/cgi-bin/login_page.sh
fi
# still default-PW "freetz"? Change
[ "$UPWHASH" = "465d0ff27bb239292778dc3a0c2f28d9" ] && . /usr/mww/cgi-bin/pwchange.cgi && exit
#. $PWD/index.cgi

subpage="$(echo "${QUERY_STRING}" | sed -n 's/.*\?subpage=//p' | sed 's/^\/*//;s/&.*//;s/[^-_a-zA-Z0-9\.\/]//g;s/\.\.//g')"
[ "$subpage" == "cgi-bin/login.cgi" -o "$subpage" == "cgi-bin/logout.cgi" ] && subpage=''
. /usr/lib/libmodredir.sh
# Re-assert cookie on the redirect response — honour MOD_HTTPD_NO_COOKIE policy
[ -r /mod/etc/conf/mod.cfg ] && . /mod/etc/conf/mod.cfg
if [ "$MOD_HTTPD_NO_COOKIE" = yes ]; then
	printf "Set-Cookie: SID=$SID;Path=/;HttpOnly;SameSite=Strict\r\n"
else
	printf "Set-Cookie: SID=$SID;Path=/;Max-Age=86400;HttpOnly;SameSite=Strict\r\n"
fi
redirect "/$subpage"

