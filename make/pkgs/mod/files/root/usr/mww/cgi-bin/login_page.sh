#!/bin/sh

# Ensure standard system directories are in PATH (busybox applets like md5sum,
# tr, head etc. live under /usr/bin which may not be in PATH during early CGI
# execution if /var/env.mod.daemon hasn't been loaded yet)
export PATH="${PATH:-/bin:/sbin:/usr/bin:/usr/sbin}"

# keine Schleife, wenn wir schon libmodcgi.sh hatten ;-)
[ -z "$SENDSID" ] && . /usr/lib/libmodcgi.sh

# Load webcfg settings for cookie policy
[ -r /mod/etc/conf/mod.cfg ] && . /mod/etc/conf/mod.cfg

[ -n "$SENDSID" ] || SENDSID="$(LC_ALL=C tr -dc 'a-f0-9' < /dev/urandom | head -c 32)"
find /tmp/ -maxdepth 1 -type f -name ".webcfg.${_CGI_CSRF_SCOPE:-default}.*.tmp" -mmin +9 -exec rm -f {} \;
printf '%s#%s\n' "$SENDSID" "$REMOTE_ADDR" > "/tmp/.webcfg.${_CGI_CSRF_SCOPE:-default}.$SENDSID.tmp"

# Send session cookie — omit Max-Age when MOD_HTTPD_NO_COOKIE=yes so the
# cookie is a proper session cookie (expires when browser closes).
if [ "$MOD_HTTPD_NO_COOKIE" = yes ]; then
	printf "Set-Cookie: SID=$SENDSID;Path=/;HttpOnly;SameSite=Strict\r\n"
else
	printf "Set-Cookie: SID=$SENDSID;Path=/;Max-Age=86400;HttpOnly;SameSite=Strict\r\n"
fi
cgi_begin "$(lang de:"Anmelden" en:"Login")"

. /usr/mww/cgi-bin/md5hash.sh

subpage="$(echo "${REQUEST_URI}" | sed -n 's/.*\?subpage=//p' | sed 's/^\/*//;s/&.*//;s/[^-_a-zA-Z0-9\.\/]//g;s/\.\.//')"
[ -z "$subpage" ] && subpage="${REQUEST_URI%%\?*}" || subpage="/$subpage"

cat << LOGINEOF
<form id="login" action="/cgi-bin/login.cgi" method="POST" onsubmit="document.getElementById('login_hash').value=makemd5(document.getElementById('inp_pw').value,'$SENDSID')">
<input type="hidden" name="hash" id="login_hash">
<input type="hidden" name="subpage" value="$(html "$subpage")">
LOGINEOF

if type skin_login_form >/dev/null 2>&1 && [ "$MOD_HTTPD_CUSTOM_LOGIN" = yes ]; then
	skin_login_form "$SENDSID" "$subpage" "$WRONGPW"
else
	cat << LOGINEOF
<br><br>
$(lang de:"Passwort" en:"Password"):
<input type="password" id="inp_pw" maxlength="45" onkeydown="if (event.keyCode == 13) document.getElementById('id_go').click()">
<input type="button" value="$(lang de:"anzeigen" en:"show")" title="$(lang de:"Passwort anzeigen" en:"Show password")" style="padding:2px 6px;cursor:pointer;" onclick="var f=document.getElementById('inp_pw');var b=this;if(f.type==='password'){f.type='text';b.value='$(lang de:"verbergen" en:"hide")';b.title='$(lang de:"Passwort verbergen" en:"Hide password")';}else{f.type='password';b.value='$(lang de:"anzeigen" en:"show")';b.title='$(lang de:"Passwort anzeigen" en:"Show password")';}f.focus();">
&nbsp;
<input type="submit" name="go" id="id_go" value="$(lang de:"Anmelden" en:"Login")">
LOGINEOF
	echo '<br><br>'
	[ "$WRONGPW" = 1 ] && echo "<p><b><font color=red>$(lang de:"Passwort falsch!" en:"Wrong password!")</font></b></p>"
fi
echo '</form>'
[ "$WRONGPW" = 1 ] && echo "<p><a href='https://ircama.github.io/freetz-evo/make/mod/#resetting-the-password' target='_blank'>$(lang de:"Passwort vergessen?" en:"Forgot password?")</a></p>"

cgi_end
