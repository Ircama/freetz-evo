skin_head() {
	local title=$1 id=$2
	local hname="$(hostname -s|html)"
	[ "$hname" != "fritz" ] && hname="&nbsp;&#64;${hname}" || hname=""
	cat << EOF
<title>$title&nbsp;&ndash; Freetz${hname}</title>
<link rel="stylesheet" type="text/css" href="/style/phoenix/base.css">
<link rel="stylesheet" type="text/css" href="/style/colorscheme.css">
EOF
	_cgi_print_extra_styles

	# There is padding in #container (2x30px), so make #world 60px bigger
	# than _cgi_width, so the application can use _cgi_width pixels (as
	# requested by the cgi via 'cgi --width=1234' or defined by the user)
	let _world_width=_cgi_width+60
	cat << EOF
<style type="text/css">
<!--
#world {
    max-width: ${_world_width}px;
}
-->
</style>
EOF
}

skin_body_begin() {
	local title=$1 id=$2
	cat << EOF
<div id="world">
<div id="header">
<h1><a href="https://ircama.github.io/freetz-evo/" target="_blank" class="logo">Freetz EVO</a>&nbsp;<a id="about" href="/cgi-bin/about.cgi" target="_blank">&ndash;</a>&nbsp;<span class="title">$title</span></h1>
EOF
if [ -n "$_CGI_HELP" ]; then
	echo "<a class='help' href='$(html "$_CGI_HELP")'>$(lang de:"Hilfe" en:"Help")</a>"
fi
	cat << EOF
</div>
<div id="container">
EOF

	_cgi_print_menu "$id"
	_cgi_print_submenu "$id"

	echo "<div id='content'>"
}

skin_body_end() {
	cat << EOF
</div>
</div>
<div id="footer">
<span class="datetime" title="$(lang de:"Systemzeit des Routers" en:"Router's system time")">$(date +'$(lang de:"%d.%m.%Y" en:"%m/%d/%Y") %H:%M')</span>&nbsp;&ndash;
<span class="uptime" title="Uptime">$(uptime | sed -r 's/.*(up.*), *load.*/\1/')</span>
<span class="version">$(html < /etc/.freetz-version)</span>
</div>
</div>
EOF
}

skin_sec_begin() {
	echo "<h1>$1</h1>"
}

skin_sec_end() {
	:
}

skin_login_form() {
	local sid="$1" subpage="$2" wrongpw="$3"
	local errmsg=""
	[ "$wrongpw" = "1" ] && errmsg="<tr><td></td><td><span style='color:red'>$(lang de:"Passwort falsch!" en:"Wrong password!")</span></td></tr>"
	cat << EOF
<br>
<table cellpadding="4" cellspacing="0">
<tr>
  <td>$(lang de:"Benutzername" en:"Username"):</td>
  <td><input type="text" value="$MOD_HTTPD_USER" readonly style="background:#f0f0f0;border:1px solid #ccc;padding:3px 6px"></td>
</tr>
<tr>
  <td>$(lang de:"Passwort" en:"Password"):</td>
  <td><input type="password" id="inp_pw" maxlength="45" style="border:1px solid #ccc;padding:3px 6px" onkeydown="if(event.key==='Enter')document.getElementById('id_go').click()"></td>
</tr>
$errmsg
<tr>
  <td></td>
  <td><input type="button" id="id_go" value="$(lang de:"Anmelden" en:"Login")" onclick="location.href='/cgi-bin/login.cgi?subpage=$subpage&amp;hash='+makemd5(document.getElementById('inp_pw').value,'$sid')"></td>
</tr>
</table>
<script>document.getElementById('inp_pw').focus();</script>
EOF
}
