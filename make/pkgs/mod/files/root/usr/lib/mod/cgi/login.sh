# validate login, renew "timer"
checklogin() {
SENDSID=""
SID="$(echo "$HTTP_COOKIE" | sed -n "s%.*SID=\([^\; ]*\).*%\1%p")"
# SIDs are 32 hex digits
[ "${#SID}" = 32 ] || SID=""
case $SID in *[!0123456789abcdef]*) SID="" ;; esac
local idfile="/tmp/.webcfg.${_CGI_CSRF_SCOPE:-default}.$SID.sid"
local timeout="${MOD_HTTPD_SESSIONTIMEOUT:-600}"
local mtime
case $timeout in ''|*[!0123456789]*) timeout=600 ;; esac
if [ -n "$SID" ] && [ -f "$idfile" ]; then
	mtime="$(date -r "$idfile" +%s 2>/dev/null)"
	if [ -n "$mtime" ] && { [ "$timeout" -eq 0 ] || [ "$(( $(date +%s) - mtime ))" -le "$timeout" ]; }; then
		if touch -c "$idfile"; then
			isauth=1
			return 0
		fi
	fi
	rm -f "$idfile"
fi
isauth=0
SENDSID="$(LC_ALL=C tr -dc 'a-f0-9' < /dev/urandom | head -c 32)"
return 1
}
