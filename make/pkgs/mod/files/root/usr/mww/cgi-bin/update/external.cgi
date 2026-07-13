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
$(lang de:"Diese Seite dient zum Hochladen von external-Dateien f&uuml;r Freetz-Boxen, deren Pakete externalisiert sind. Eine external-Datei ist eine Datei mit der Endung *.external, die in der Firmware-Image-Region abgelegt ist und mit einem bestimmten Image-Dateinamen (*.image) verkn&uuml;pft ist. Sie enth&auml;lt alle zus&auml;tzlichen Pakete, die nicht im eigentlichen Firmware-Image enthalten sind. Die hier hochgeladene *.external-Datei muss immer diejenige sein, die zu der verwendeten *.image-Datei geh&ouml;rt. Nur wenn Image und external-Datei zusammengeh&ouml;ren, ist ein korrekter Systembetrieb gew&auml;hrleistet." en:"This page is used to upload external files for Freetz boxes whose packages are externalized. An external file is a file with the *.external extension stored in the firmware image region and associated with a specific image file name (*.image). It contains all additional packages that are not included in the actual firmware image. The uploaded *.external file must always be the one belonging to the *.image file being used. Correct system operation is only guaranteed when the image and the external file match.")
</p>

<p>
$(lang de:"F&uuml;r das Hochladen stehen zwei Methoden zur Verf&uuml;gung: Die erste Methode ist der direkte Upload einer Datei &uuml;ber den Browser, der vom integrierten CGI-Upload-Handler auf etwa 250 MB begrenzt ist. Sie ist die einfachere Methode und f&uuml;r die meisten F&auml;lle ausreichend. Die zweite Methode ist der Download von einer externen URL, die vom Ger&auml;t aus erreichbar sein muss. Sie ist dann erforderlich, wenn die hochzuladende Datei gr&ouml;&szlig;er als 250 MB ist und nicht mehr &uuml;ber den Browser hochgeladen werden kann. Dazu muss der Benutzer die external-Datei auf einem eigenen, vom Ger&auml;t aus erreichbaren Webserver ver&ouml;ffentlichen und die vollst&auml;ndige URL in das entsprechende Feld unten eingeben. Beide Methoden k&ouml;nnen je nach Bedarf verwendet werden." en:"Two methods are available for uploading: The first method is direct browser upload, which is limited to about 250 MB by the built-in upload handler. It is the simpler method and sufficient for most cases. The second method is downloading from an external URL that must be reachable from the device. This is required when the file to be uploaded is larger than 250 MB and can no longer be uploaded via the browser. To use this method, the user must publish the external file on their own web server accessible from the device and enter the complete URL in the corresponding field below. Both methods can be used as needed.")
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

