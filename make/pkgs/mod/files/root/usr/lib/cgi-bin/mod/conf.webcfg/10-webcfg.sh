[ -r /etc/options.cfg ] && . /etc/options.cfg

skins="$(ls /usr/share/skin)"
for skin in $skins; do
	check "$MOD_SKIN" $skin:${skin}
done


sec_begin "$(lang de:"Weboberfl&auml;che" en:"Web interface")"

cgi_print_radiogroup_service_starttype \
	"httpd" "$MOD_HTTPD" "$(lang de:"Starttyp der Weboberfl&auml;che" en:"Web interface start type")" "" 1

cgi_print_textline_p "httpd_port" "$MOD_HTTPD_PORT" 5 "$(lang de:"Port" en:"Port"): "

if [ "$MOD_HTTPD_NEWLOGIN" != yes ]; then
	cgi_print_textline "httpd_user" "$MOD_HTTPD_USER" 15 "$(lang de:"Benutzername" en:"Username"): "
	echo "<p>$(lang de:"Passwort" en:"Password"): <input type='button' value='$(lang de:"&auml;ndern" en:"change")' onclick='window.open(\"/cgi-bin/passwd.cgi\",\"_self\")'></p>"
else
	echo "<p>$(lang de:"Passwort" en:"Password"): <input type='button' value='$(lang de:"&auml;ndern" en:"change")' onclick='window.open(\"/cgi-bin/pwchange.cgi\",\"_self\")'></p>"
fi

sec_end
sec_begin "$(lang de:"Authentifizierung" en:"Authentification")"

cgi_print_checkbox "httpd_newlogin" "$MOD_HTTPD_NEWLOGIN" "$(lang de:"Neue Loginversion mit Session-ID" en:"Form-based login with session cookie (replaces browser Basic Auth dialog)")"
echo "<p>"
cgi_print_textline "httpd_sessiontimeout" "$MOD_HTTPD_SESSIONTIMEOUT" 7 "$(lang de:"Inaktivitäts-Timeout der Sitzung:" en:"Session inactivity timeout:") " " $(lang de:"Sekunden (danach wird erneut nach dem Passwort gefragt)" en:"seconds (after this idle period the login prompt reappears)")"
cat << EOF
<table style="margin-top:4px;margin-left:2px;font-size:0.85em;border-collapse:collapse">
<tr><th style="text-align:left;padding:1px 10px 1px 0">$(lang de:"Wert" en:"Value")</th><th style="text-align:left;padding:1px 0">$(lang de:"Inaktivitäts-Timeout" en:"Inactivity timeout")</th></tr>
<tr><td style="padding:1px 10px 1px 0">600</td><td>$(lang de:"10 Minuten (Standard)" en:"10 minutes (default)")</td></tr>
<tr><td style="padding:1px 10px 1px 0">3600</td><td>$(lang de:"1 Stunde" en:"1 hour")</td></tr>
<tr><td style="padding:1px 10px 1px 0">86400</td><td>$(lang de:"24 Stunden" en:"24 hours")</td></tr>
<tr><td style="padding:1px 10px 1px 0">864000</td><td>$(lang de:"100 Tage" en:"100 days")</td></tr>
<tr><td style="padding:1px 10px 1px 0">0</td><td>$(lang de:"nie (permanent, solange das Gerät läuft)" en:"never (permanent while device is running)")</td></tr>
</table>
EOF
echo "</p>"

if [ -n "${MOD_HTTPD_CUSTOM_LOGIN+x}" ]; then
cgi_print_checkbox "httpd_custom_login" "$MOD_HTTPD_CUSTOM_LOGIN" \
	"$(lang de:"Skin-angepasste Login-Seite (Passwort-Eingabe im Stil des aktiven Themes statt Browser-Dialog; erfordert Session-ID)" \
	       en:"Themed login page styled to match the active skin (password prompt in the web UI instead of browser dialog; requires form-based login)")"

cat << EOF
<script>
var elNewlogin  = document.getElementById('httpd_newlogin_yes');
var elCustom    = document.getElementById('httpd_custom_login_yes');
var elTimeout   = document.getElementById('httpd_sessiontimeout');
$([ "$MOD_HTTPD_NEWLOGIN" = yes ] || echo "elTimeout.disabled = true; elCustom.disabled = true;")
elCustom.onchange = function() {
  if (this.checked) { elNewlogin.checked = true; elTimeout.disabled = false; elCustom.disabled = false; }
};
elNewlogin.onchange = function() {
  elTimeout.disabled = !this.checked;
  elCustom.disabled  = !this.checked;
  if (!this.checked) elCustom.checked = false;
};
</script>
EOF

else

cat << EOF
<script>
var elNewlogin = document.getElementById('httpd_newlogin_yes');
var elTimeout  = document.getElementById('httpd_sessiontimeout');
$([ "$MOD_HTTPD_NEWLOGIN" = yes ] || echo "elTimeout.disabled = true;")
elNewlogin.onchange = function() {
  elTimeout.disabled = !this.checked;
};
</script>
EOF

fi

sec_end
sec_begin "$(lang de:"Erweiterte Einstellungen" en:"Advanced settings")"

cat << EOF
<p>
$(lang de:"Eingeh&auml;ngte Partitionen auf" en:"Mounted partitions on"):
EOF

cgi_print_checkbox "mounted_sub" "$MOD_MOUNTED_SUB" "$(lang de:"Untermen&uuml;" en:"Submenu")"
cgi_print_checkbox "mounted_main" "$MOD_MOUNTED_MAIN" "$(lang de:"Hauptseite" en:"Mainpage")"
cgi_print_checkbox "mounted_umount" "$MOD_MOUNTED_UMOUNT" "$(lang de:"mit Kn&ouml;pfen" en:"with buttons")"

cat << EOF
</p>
<p>
$(lang de:"Zus&auml;tzliche Partitionen" en:"Additional partitions"):
EOF

cgi_print_checkbox "mounted_tffs" "$MOD_MOUNTED_TFFS" "$(lang de:"TFFS" en:"TFFS")"
[ -d "/nvram" ] && \
  cgi_print_checkbox "mounted_nvram" "$MOD_MOUNTED_NVRAM" "$(lang de:"NVRAM" en:"NVRAM")"
df /var/flash/ 2>/dev/null | grep -q ' /var/flash$' && \
  cgi_print_checkbox "mounted_conf" "$MOD_MOUNTED_CONF" "$(lang de:"Konfiguration" en:"Configuartion")"
cgi_print_checkbox "mounted_temp" "$MOD_MOUNTED_TEMP" "$(lang de:"Tempor&auml;r" en:"Temporary")"

cat << EOF
</p>
EOF
if [ -r "/usr/lib/cgi-bin/mod/box_info.cgi" -o -r "/usr/lib/cgi-bin/mod/flash_info.cgi" -o -r "/usr/lib/cgi-bin/mod/info.cgi" ]; then
	echo "<p> $(lang de:"Zus&auml;tzliche Status-Seiten" en:"Additional status pages"):"

	if [ -r "/usr/lib/cgi-bin/mod/box_info.cgi" ]; then
		cgi_print_checkbox "show_box_info" "$MOD_SHOW_BOX_INFO" "$(lang de:"Box-Info" en:"Box info")"
	fi
	if [ -r "/usr/lib/cgi-bin/mod/flash_info.cgi" ]; then
		cgi_print_checkbox "show_flash_info" "$MOD_SHOW_FLASH_INFO" "$(lang de:"Flash-Info" en:"Flash info")"
	fi
	if [ -r "/usr/lib/cgi-bin/mod/info.cgi" ]; then
		cgi_print_checkbox "show_freetz_info" "$MOD_SHOW_FREETZ_INFO" "$(lang de:"Freetz-Info" en:"Freetz info")"
	fi

	echo "</p>"
fi

[ "$FREETZ_LANG_XX" == "y" ] && cgi_print_radiogroup \
  "lang" "$MOD_LANG" "" "$(lang de:"Sprachauswahl" en:"Language selection"):" \
  "de::deutsch" \
  "en::english"

cat << EOF
<p>$(lang de:"Skinauswahl" en:"Skin selection"):
EOF
for skin in $skins; do
	skin_nice_name="$(echo -n "${skin:0:1}" | tr '[:lower:]' '[:upper:]')${skin:1}"
	echo "<input id=\""$skin"\" type=\"radio\" name=\"skin\" value=\""$skin"\" "$(eval echo \$${skin}_chk)"><label for=\""$skin"\"> "$skin_nice_name"</label>"
done
echo '</p>'

cgi_print_textline_p "cgi_width" "$MOD_CGI_WIDTH" 4 "$(lang de:"Breite des Hauptinhalts" en:"Width of the main content area"):"
cgi_print_checkbox_p "show_memory_usage" "$MOD_SHOW_MEMORY_USAGE" "$(lang de:"Zeige Speicherverbrauch" en:"Show memory usage")"
[ ! -x /usr/bin/bootmanager ] && [ "$FREETZ_AVM_PROP_INNER_FILESYSTEM_TYPE_CPIO" != "y" ] && [ -e /usr/mww/cgi-bin/system_lfs.cgi ] && \
  cgi_print_checkbox_p "update_lfs" "$MOD_UPDATE_LFS" "$(lang de:"Ermittle inaktive Firmwareversion beim Booten" en:"Identify inactive firmware version at boot")"

sec_end

