#!/bin/sh

. /usr/lib/libmodcgi.sh

footer() {
	echo "<p>"
	back_button --title="$(lang de:"Zur&uuml;ck zum Update" en:"Back to update")" mod update
	echo "</p>"
	cgi_end
	touch /tmp/ex_update.done
}

pre_begin() {
	echo "<pre class='log'>"
	exec 3>&2 2>&1
}

pre_end() {
	exec 2>&3 3>&-
	echo "</pre>"
}

html_do() {
	local exit
	eval $({
		{ "$@"; echo exit=$? >&4; } | html
	} 4>&1 >&9)
	return $exit
} 9>&1

do_exit() {
	footer
	exit "$@"
}

status() {
	local status msg=$2
	case $1 in
		"done") status="$(lang de:"ERLEDIGT" en:"DONE")" ;;
		"failed") status="$(lang de:"FEHLGESCHLAGEN" en:"FAILED")" ;;
	esac
	echo -n "<p><span class='status'>$status</span>"
	[ -n "$msg" ] && echo -n " &ndash; $msg"
	echo "</p>"
}

url="$(cgi_param url)"
EXTERNAL_TARGET="$(cgi_param target)"
[ -z "$EXTERNAL_TARGET" ] && EXTERNAL_TARGET=/var/media/ftp

delete=false
[ "$(cgi_param delete)" = "delete" ] && delete=true

external_start=false
[ "$(cgi_param ex_start)" = "ex_start" ] && external_start=true

cgi_begin "$(lang de:"external-Update" en:"external-update")"

if [ -z "$url" ]; then
	echo "<h1>$(lang de:"Update vorbereiten" en:"Prepare update")</h1>"
	pre_begin
	echo "Missing URL parameter."
	pre_end
	status "failed"
	do_exit 1
fi

case "$url" in
	http://*|https://*) ;;
	*)
		echo "<h1>$(lang de:"Update vorbereiten" en:"Prepare update")</h1>"
		pre_begin
		echo "Unsupported URL scheme: $url"
		pre_end
		status "failed"
		do_exit 1
		;;
esac

echo "<p>$(lang de:"URL" en:"URL"): $(html "$url")</p>"
echo "<p>$(lang de:"Ziel-Verzeichnis" en:"Target directory"): $(html "$EXTERNAL_TARGET")</p>"

archive="/var/tmp/external-url-$$.external"

cleanup() {
	rm -f "$archive"
}

prepare() {
	echo "<h1>$(lang de:"Update vorbereiten" en:"Prepare update")</h1>"
	pre_begin
	echo -n "Stopping external services ... "
	if [ "$(/mod/etc/init.d/rc.external status 2>/dev/null)" = "running" ]; then
		/mod/etc/init.d/rc.external stop >/dev/null
		echo "done."
	else
		echo "not running."
	fi
	if $delete; then
		echo -n "Removing old stuff ... "
		if [ ! -e "$EXTERNAL_TARGET/.external" ]; then
			echo "$EXTERNAL_TARGET is not an external dir."
		else
			rm -rf "$EXTERNAL_TARGET"
			[ $? -ne 0 ] && echo "failed." || echo "done."
		fi
	else
		echo "Not deleting old external stuff."
	fi
	pre_end
	status "done"
}

[ -d "$EXTERNAL_TARGET" ] && prepare

echo "<h1>$(lang de:"Datei herunterladen" en:"Download file")</h1>"
pre_begin

download() {
	if command -v wget >/dev/null 2>&1; then
		wget -O "$archive" "$url"
	else
		curl -L -o "$archive" "$url"
	fi
}

html_do download
result=$?
pre_end
if [ $result -ne 0 ]; then
	status "failed"
	cleanup
	do_exit 1
fi

if [ "${archive##*.}" != "external" ] && [ "${url##*.}" != "external" ]; then
	echo "<h1>$(lang de:"Update vorbereiten" en:"Prepare update")</h1>"
	pre_begin
	echo "Downloaded file does not look like an .external archive."
	pre_end
	status "failed"
	cleanup
	do_exit 1
fi

status "done"

cat << EOF
<h1>$(lang de:"Dateien extrahieren" en:"Extract files")</h1>
EOF

pre_begin
untar() {
	if mkdir -p "$EXTERNAL_TARGET"; then
		tar -C "$EXTERNAL_TARGET" -xvf "$archive" 2>&1
	fi
}

html_do untar
result=$?
pre_end
cleanup
if [ $result -ne 0 ]; then
	status "failed"
	do_exit 1
fi

status "done"

if [ -e /mod/etc/init.d/rc.external ] && $external_start; then
	echo "<h1>$(lang de:"External-Dienste starten" en:"Starting external services")</h1>"
	pre_begin
	/mod/etc/init.d/rc.external start
	pre_end
fi

do_exit 0
