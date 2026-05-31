#! /bin/sh


. /usr/lib/libmodcgi.sh

. /mod/etc/conf/mod.cfg

cgi --id=firmware_update
cgi_begin "$(lang de:"external-Datei Update" en:"external-file update")"

cat << EOF
<script type=text/javascript>
function CheckUploadInput(form) {
	file_selector=form.elements[0];
	target_text=form.elements[1];
	delete_chk=form.elements[2];
	ex_start=form.elements[3];
	if (file_selector.value=="") {
		alert("$(lang de:"Keine external-Datei angegeben!" en:"No external-file provided!")");
		return false;
	}
	file_selector.name=target_text.value;
	if (delete_chk.checked) {
		file_selector.name += ":delete_oldfiles";
	}
	if (ex_start.checked) {
		file_selector.name += ":external_start";
	}
	return true;
}

function CheckUrlInput(form) {
	url_text=form.elements[0];
	if (url_text.value=="") {
		alert("$(lang de:"Keine URL angegeben!" en:"No URL provided!")");
		return false;
	}
	return true;
}
</script>

<h1>$(lang de:"external-Datei hochladen" en:"Upload external-file")</h1>

<p>
$(lang de:"Hier kann entweder eine external-Datei direkt hochgeladen oder von einer URL auf die Box gestreamt werden. Anschlie&szlig;end sollte die passende Firmware hochgeladen werden." en:"Here you can either upload an external-file directly or stream it to the box from a URL. Afterwards, the matching firmware should be uploaded.")
</p>

<p>
$(lang de:"Der Browser-Upload ist durch den verwendeten CGI-Upload-Handler auf etwa 250 MB begrenzt. F&uuml;r gr&ouml;&szlig;ere Dateien verwenden Sie bitte die URL-Methode weiter unten." en:"The browser upload path is limited to about 250 MB by the CGI upload handler. For larger files, please use the URL method below.")
</p>

<form action="do_external.cgi" method=POST enctype="multipart/form-data" onsubmit="return CheckUploadInput(document.forms[0]);">
	<p>$(lang de:"external-Datei" en:"External-file") <input type=file size=50 id="ex_file"></p>
	<p>$(lang de:"Zielverzeichnis" en:"Target directory") <input type="textfield" size=50 name="the_target" value="$MOD_EXTERNAL_DIRECTORY"></p>
	<p><input type="checkbox" name="delete" value="delete">$(lang de:"Alte External-Dateien l&ouml;schen" en:"Delete old external files")</p>
	<p><input type="checkbox" name="ex_start" value="ex_start">$(lang de:"External Dienste nach Update starten" en:"Start external services after update")</p>
	<input type=submit value="$(lang de:"Datei hochladen" en:"Upload file")" style="width:200px">
</form>

<hr>

<form action="do_external_url.cgi" method=GET onsubmit="return CheckUrlInput(document.forms[1]);">
	<p>URL <input type="text" size=60 name="url" value="http://"></p>
	<p>$(lang de:"Zielverzeichnis" en:"Target directory") <input type="textfield" size=50 name="target" value="$MOD_EXTERNAL_DIRECTORY"></p>
	<p><input type="checkbox" name="delete" value="delete">$(lang de:"Alte External-Dateien l&ouml;schen" en:"Delete old external files")</p>
	<p><input type="checkbox" name="ex_start" value="ex_start">$(lang de:"External Dienste nach Update starten" en:"Start external services after update")</p>
	<input type=submit value="$(lang de:"Von URL laden" en:"Download from URL")" style="width:200px">
</form>
EOF

cgi_end

