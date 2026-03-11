#!/bin/sh
. /usr/lib/libmodcgi.sh
cgi --id=uimods


# for x in $(ctlmgr_ctl u | sed '1,2d'); do echo; ctlmgr_ctl u $x; done | tee uimods.txt
uimods_listing() {
	. /etc/uimods.conf | sed 's/^[\t ]*//g' | grep -vE '^(;|#|$)'
}

uimods_request() {
	uimods_listing | while read -r a b; do
		modul="${a%%:*}"
		uikey="${a#$modul:}"
		[ "$uikey" == "${uikey//\//\ }" ] && uikey="settings/$uikey"
		echo -n "$modul $uikey "
	done
}

uimods_table() {
	local colit oldhr=""
	uimods_result="$(ctlmgr_ctl r -v $(uimods_request))"
	uimods_listing | sort -u | while read -r a defa vals desc; do
		modul="${a%%:*}"
		uikey="${a#$modul:}"
		[ "$uikey" == "${uikey//\//}" ] && uikey="settings/$uikey"
		[ "$oldhr" != "$modul" ] && table_head "$modul" "$oldhr" && oldhr="$modul"
		saved="$(echo "$uimods_result" | sed -n "s,^${modul}:${uikey} = ,,p")"
		[ "$defa" -gt 0 ] 2>/dev/null && [ "$(echo "$vals" | cut -f$defa -d'|')" != "$saved" ] && colit="red" || colit=''
		[ -z "$saved" ] && [ -n "$colit" ] && colit="yellow"
		table_line "$modul" "$uikey" "$saved" "$colit" "${vals#|}" "$desc"
	done
	table_end
}


table_begin() {
	local modul="$1"
	sec_begin "$modul"
	echo "<style>table.uimods-tbl{width:100%;border-collapse:collapse;table-layout:auto}table.uimods-tbl td{padding:4px 6px;word-break:break-word;vertical-align:middle}table.uimods-tbl td:first-child{min-width:120px;font-weight:bold}table.uimods-tbl input[type=text]{width:100%;max-width:280px;box-sizing:border-box}@media(max-width:600px){table.uimods-tbl,table.uimods-tbl tbody,table.uimods-tbl tr{display:block;width:100%}table.uimods-tbl tr{padding:4px 0}table.uimods-tbl tr.uimods-desc-row{border-bottom:1px solid #ccc;padding-top:0}table.uimods-tbl td{display:block;width:100%!important;box-sizing:border-box}table.uimods-tbl input[type=text]{max-width:100%}}</style>"
	echo "<table class='uimods-tbl'>"
}

table_head() {
	local modul="$1"
	local oldhr="$2"
	[ -n "$oldhr" ] && table_end
	table_begin "$modul"
}

table_line() {
	local modul="$1"
	local uikey="$2"
	local saved="$3"
	local style="${4:+border:3px solid $4;}"
#	local style="${4:+color:black;background-color:$4;}"
	local vals="$5"
	local desc="$6"
	local short="${uikey#*/}"
	local htmlid="uimod_${modul}__${short}"
	local listid="dlist_${modul}__${short}"
	local disabled=""
	[ "${uikey%%/*}" != "settings" ] && disabled="disabled"
	[ -n "$saved" -a -n "$vals" ] && items="$saved|$vals" || items="$saved$vals"

	echo "<tr>"
	echo "<form action='/cgi-bin/exec.cgi/uimods' method='post'>"

	echo "<td><b>$short</b></td>"

	echo "<td><input type='text' list='$listid' name='val' id='$htmlid' value='$saved' style='$style' /> <datalist id='$listid'>"
	for x in $(echo "$items" | sed 's/|/\n/g' | sort -u); do echo "<option value='$x'>"; done
	echo "</datalist></td>";

	echo "<input type='hidden' name='mod' value='$modul'>"
	echo "<input type='hidden' name='key' value='$short'>"

	echo "<td><center> <input type='submit' name='cmd' value='&nbsp;$(lang de:"&auml;ndern" en:"change")&nbsp;' $disabled> </center></td>"

	echo "</form>"
	echo "</tr>"

	echo "<tr class='uimods-desc-row'><td colspan='2'><font size=-2><i>${desc:+&num; $desc}</i></font></td></tr>"
}

table_end() {
	echo "</table>"
	sec_end
}

uimods_info() {
cat << EOX
<br>
$(lang \
  de:"Hier k&ouml;nnen interne Variablen ge&auml;ndert werden die im AVM Webinterface deaktiviert oder schwer zu finden sind." \
  en:"You could change here internal variables which are disabled or hidden on the AVM web interface." \
)
$(lang \
  de:"Das kann eine schlechte Idee sein! Vor dem Experimentieren sollte man unbedingt eine Konfigurationsicherung erstellen. Siehe auch" \
  en:"This could be a very bad idea! You should create a settings backup before you start. See also" \
)
<a href='https://freetz-ng.github.io/freetz-ng/wiki/60_Development/uimods' target='_blank'>$(lang de:"Wiki: UI-Module und ctlmgr_ctl" en:"Wiki: UI modules and ctlmgr_ctl")</a>,
$(lang \
	de:"insbesondere der Punkt <a href='https://freetz-ng.github.io/freetz-ng/wiki/60_Development/uimods#alle-variablen' target='_blank'>Alle Variablen</a>." \
	en:"especially <a href='https://freetz-ng.github.io/freetz-ng/wiki/60_Development/uimods#alle-variablen' target='_blank'>All variables</a> to find more variables." \
)
EOX
}


cgi_begin "$(lang de:"FOS UI-Module" en:"FOS UI-Modules")"
uimods_info
uimods_table
cgi_end

