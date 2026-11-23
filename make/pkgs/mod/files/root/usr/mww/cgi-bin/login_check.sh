#!/bin/sh

# Ensure standard system directories are in PATH (busybox applets like md5sum,
# tr, head etc. live under /usr/bin which may not be in PATH during early CGI
# execution if /var/env.mod.daemon hasn't been loaded yet)
export PATH="${PATH:-/bin:/sbin:/usr/bin:/usr/sbin}"

WRONGPW=0

SID="$(echo "$HTTP_COOKIE" | sed -n "s%.*SID=\([^\; ]*\).*%\1%p")"
[ "${#SID}" != "32" ] && SID=""
case $SID in *[!0123456789abcdef]*) SID="" ;; esac

sidfile="/tmp/.webcfg.${_CGI_CSRF_SCOPE:-default}.$SID"
ID_IP=$(cat "$sidfile.tmp" 2>/dev/null)
IP=${ID_IP#*#}
eval "$(modcgi hash:subpage login)"
mkdir -p /tmp/flash/mod 2>/dev/null
[ -f /tmp/flash/mod/webmd5 ] || echo "465d0ff27bb239292778dc3a0c2f28d9" > /tmp/flash/mod/webmd5
UPWHASH="$(cat /tmp/flash/mod/webmd5)"
myhash="$(echo -n "$SID$UPWHASH" | md5sum | sed 's/ .*//')"

lastacc="$(date -r "$sidfile.tmp" +%s 2>/dev/null)"
[ -n "$lastacc" ] && lastacc=$(( $(date +%s) - lastacc ))

if [ -n "$SID" ] && [ -n "$UPWHASH" ] && [ -n "$lastacc" ] && [ "$lastacc" -ge 0 ] && [ "$lastacc" -lt 600 ] && [ "$REMOTE_ADDR" = "$IP" ] && [ "$LOGIN_HASH" = "$myhash" ]; then
	{
		echo -n "TICK=" ; date +%s
		echo -n "DATE=" ; date '+%Y-%m-%dT%H:%M:%S%z'
		echo "HOST=$REMOTE_ADDR"
		echo "USER=$HTTP_USER_AGENT"
	} > "$sidfile.sid"
	rm -f "$sidfile.tmp"
else
	SENDSID=""
	QUERY_STRING=""
	WRONGPW=1
	. /usr/mww/cgi-bin/login_page.sh
	exit
fi
# still default-PW "freetz"? Change
if [ "$UPWHASH" == "465d0ff27bb239292778dc3a0c2f28d9" ]; then
	. /usr/lib/libmodredir.sh
	redirect_302 /cgi-bin/pwchange.cgi
	exit
fi
#. $PWD/index.cgi

subpage="$(echo "$LOGIN_SUBPAGE" | sed 's/^\/*//;s/&.*//;s/[^-_a-zA-Z0-9\.\/]//g;s/\.\.//g')"
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

