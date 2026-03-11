#!/bin/sh

# Source CGI helper library
. /usr/lib/libmodcgi.sh

# ===========================================================================
# AJAX Handler
# ===========================================================================
AJAX_MODE=$(cgi_param ajax)

if [ "$AJAX_MODE" = "1" ]; then
	ACTION=$(cgi_param action)

	cat <<'EOF'
<style>
.ajax-json-box { display: none; }
</style>
<div class="ajax-json-box"><div class="ajax-json-content"><pre>Content-Type: application/json

EOF

	case "$ACTION" in
		check_directory)
			DIRPATH=$(cgi_param dirpath)
			# Security: allow only paths under /var/media or /tmp
			case "$DIRPATH" in
				/var/media/ftp/*|/var/media/ftp|/tmp/*)
					if [ -d "$DIRPATH" ]; then
						echo '{"exists": true}'
					else
						echo '{"exists": false}'
					fi
					;;
				*)
					echo '{"error": "Invalid path"}'
					;;
			esac
			;;
		get_status)
			# Determine elFinder access URL
			[ -r /mod/etc/conf/elfinder.cfg ] && . /mod/etc/conf/elfinder.cfg
			CONNECTOR_OK="false"
			ELFINDER_WWW=""
			if [ -d "/mod/external/usr/mww/elfinder" ]; then
				ELFINDER_WWW="/mod/external/usr/mww/elfinder"
			elif [ -d "/usr/mww/elfinder" ]; then
				ELFINDER_WWW="/usr/mww/elfinder"
			fi
			[ -f "$ELFINDER_WWW/php/connector.php" ] && CONNECTOR_OK="true"
			echo "{\"connector\": $CONNECTOR_OK, \"basedir\": \"${ELFINDER_BASEDIR:-}\", \"theme\": \"${ELFINDER_THEME:-}\"}"
			;;
		*)
			echo '{"error": "Unknown action"}'
			;;
	esac

	echo '</pre></div></div>'
	exit 0
fi

# ===========================================================================
# Load configuration
# ===========================================================================
[ -r /etc/options.cfg ] && . /etc/options.cfg
[ -r /mod/etc/conf/elfinder.cfg ] && . /mod/etc/conf/elfinder.cfg

# ===========================================================================
# Determine if connector.php is already generated
# ===========================================================================
ELFINDER_WWW=""
if [ -d "/mod/external/usr/mww/elfinder" ]; then
	ELFINDER_WWW="/mod/external/usr/mww/elfinder"
elif [ -d "/usr/mww/elfinder" ]; then
	ELFINDER_WWW="/usr/mww/elfinder"
fi
CONNECTOR_READY="no"
[ -f "$ELFINDER_WWW/php/connector.php" ] && CONNECTOR_READY="yes"

# ===========================================================================
# Section: Access link to elFinder
# ===========================================================================
sec_begin "$(lang de:"elFinder Dateimanager" en:"elFinder File Manager" it:"elFinder Gestione File")"
cat << EOF
<p>
$(lang \
	de:"Der elFinder-Webdateimanager ist erreichbar unter:" \
	en:"The elFinder web file manager is available at:" \
	it:"Il gestore file elFinder è disponibile all'indirizzo:")
&nbsp;
<b><a style='font-size:14px;' target='_blank' href='/elfinder/'>
$(lang de:"elFinder öffnen" en:"Open elFinder" it:"Apri elFinder")
</a></b>
</p>
EOF
if [ "$CONNECTOR_READY" = "no" ]; then
	cat << 'EOF'
<p style="color:#c00; font-weight:bold;">
<span>⚠</span>
EOF
	cat << EOF
$(lang \
	de:"Der PHP-Connector wurde noch nicht generiert.  Bitte Konfiguration speichern." \
	en:"The PHP connector has not been generated yet.  Please save the configuration." \
	it:"Il connettore PHP non è ancora stato generato.  Salvare la configurazione.")
</p>
EOF
fi
sec_end

# ===========================================================================
# Section: Base directory
# ===========================================================================
sec_begin "$(lang de:"Basisverzeichnis" en:"Base directory" it:"Directory di base")"
cat << EOF
<p>
<label for='basedir'>$(lang \
	de:"Stammverzeichnis für den Dateizugriff:" \
	en:"Root directory exposed to elFinder:" \
	it:"Directory radice esposta a elFinder:")</label>
<br>
<input type='text' id='basedir' name='basedir' size='55'
	value="$(html "${ELFINDER_BASEDIR:-/var/media/ftp}")"
	title="$(lang \
		de:"Stammverzeichnis für den Dateizugriff über elFinder (z.B. /var/media/ftp)." \
		en:"Root directory for file access via elFinder (e.g. /var/media/ftp)." \
		it:"Directory radice per l'accesso ai file tramite elFinder (es. /var/media/ftp).")">
<button type="button" style="padding:2px 8px;"
	onclick="checkDir(document.getElementById('basedir').value)">
$(lang de:"Prüfen" en:"Check" it:"Verifica")</button>
<span id='basedir_status' style='margin-left:8px; font-size:12px;'></span>
</p>
<p>
<label for='url'>$(lang \
	de:"URL-Pfad der Dateien (leer = automatisch):" \
	en:"URL path for the files (empty = auto-detect):" \
	it:"Percorso URL dei file (vuoto = rilevamento automatico):")</label>
<br>
<input type='text' id='url' name='url' size='40'
	value="$(html "${ELFINDER_URL:-}")"
	title="$(lang \
		de:"Optionaler URL-Pfad, unter dem das Basisverzeichnis erreichbar ist (z.B. /files)." \
		en:"Optional URL path under which the base directory is accessible (e.g. /files)." \
		it:"Percorso URL opzionale sotto cui è accessibile la directory base (es. /files).")">
</p>
EOF
sec_end

# ===========================================================================
# Section: Upload settings
# ===========================================================================
sec_begin "$(lang de:"Upload-Einstellungen" en:"Upload settings" it:"Impostazioni upload")"
cat << EOF
<p>
<label for='max_upload_size'>$(lang \
	de:"Maximale Upload-Größe pro Datei:" \
	en:"Maximum upload size per file:" \
	it:"Dimensione massima upload per file:")</label>
<input type='text' id='max_upload_size' name='max_upload_size' size='8' maxlength='10'
	value="$(html "${ELFINDER_MAX_UPLOAD_SIZE:-64M}")"
	title="$(lang \
		de:"Maximale Dateigröße beim Upload (PHP-Format, z.B. 32M, 64M, 128M, 1G)." \
		en:"Maximum file size for uploads (PHP format, e.g. 32M, 64M, 128M, 1G)." \
		it:"Dimensione massima del file da caricare (formato PHP, es. 32M, 64M, 128M, 1G).")">
<small>$(lang de:"(z.B. 32M, 64M, 1G)" en:"(e.g. 32M, 64M, 1G)" it:"(es. 32M, 64M, 1G)")</small>
</p>
<p>
<label for='upload_allow'>$(lang \
	de:"Erlaubte MIME-Typen beim Upload (kommagetrennt):" \
	en:"Allowed MIME types for upload (comma-separated):" \
	it:"Tipi MIME consentiti per l'upload (separati da virgola):")</label>
<br>
<input type='text' id='upload_allow' name='upload_allow' size='70'
	value="$(html "${ELFINDER_UPLOAD_ALLOW:-image/,audio/,video/,text/plain,application/pdf}")"
	title="$(lang \
		de:"Kommagetrennte Liste erlaubter MIME-Typen. Präfixe (z.B. image/) erlauben alle Untertypen." \
		en:"Comma-separated list of allowed MIME types. Prefixes (e.g. image/) allow all subtypes." \
		it:"Lista separata da virgola dei tipi MIME ammessi. I prefissi (es. image/) abilitano tutti i sottotipi.")">
</p>
EOF
sec_end

# ===========================================================================
# Section: Authentication
# ===========================================================================
check "$ELFINDER_AUTH_ENABLED" yes:auth_enabled
sec_begin "$(lang de:"Authentifizierung" en:"Authentication" it:"Autenticazione")"
cat << EOF
<p>
<label title="ELFINDER_AUTH_ENABLED">
<input type='hidden' name='auth_enabled' value='no'>
<input type='checkbox' id='auth_enabled' name='auth_enabled' value='yes'$auth_enabled_chk>
$(lang \
	de:"httpd-webcfg-Authentifizierung aktivieren" \
	en:"Enable httpd-webcfg authentication" \
	it:"Abilitare l'autenticazione di httpd-webcfg")
</label>
<small>$(lang \
	de:"(empfohlen – nutzt die bestehende FritzBox-Weboberflächen-Authentifizierung)" \
	en:"(recommended – uses the existing FritzBox web interface authentication)" \
	it:"(consigliato – utilizza l'autenticazione esistente dell'interfaccia web FritzBox)")</small>
</p>
EOF
sec_end

# ===========================================================================
# Section: Thumbnail cache
# ===========================================================================
sec_begin "$(lang de:"Vorschaubild-Cache" en:"Thumbnail cache" it:"Cache miniature")"
cat << EOF
<p>
<label for='thumbpath'>$(lang \
	de:"Verzeichnis für Thumbnail-Cache (leer = Standard: BASEDIR/.tmb):" \
	en:"Thumbnail cache directory (empty = default: BASEDIR/.tmb):" \
	it:"Directory cache miniature (vuoto = predefinita: BASEDIR/.tmb):")</label>
<br>
<input type='text' id='thumbpath' name='thumbpath' size='55'
	value="$(html "${ELFINDER_THUMBPATH:-}")"
	title="$(lang \
		de:"Verzeichnis für die Zwischenspeicherung von Vorschaubildern.  Leer lassen für den Standardpfad." \
		en:"Directory for caching thumbnails.  Leave empty for the default path." \
		it:"Directory per la memorizzazione nella cache delle miniature.  Lasciare vuoto per il percorso predefinito.")">
</p>
EOF
sec_end

# ===========================================================================
# Section: Archive tools
# ===========================================================================
sec_begin "$(lang de:"Archiv-Werkzeuge" en:"Archive tools" it:"Strumenti di archivio")"
cat << EOF
<p>
<small>$(lang \
	de:"Leer lassen für automatische Erkennung aus \$PATH." \
	en:"Leave empty for automatic detection from \$PATH." \
	it:"Lasciare vuoto per il rilevamento automatico da \$PATH.")</small>
</p>
<p>
<label for='unrar_path'>$(lang de:"Pfad zu unrar:" en:"Path to unrar:" it:"Percorso unrar:")
</label>
<input type='text' id='unrar_path' name='unrar_path' size='40'
	value="$(html "${ELFINDER_UNRAR_PATH:-}")"
	placeholder="$(lang de:"(automatisch)" en:"(auto-detect)" it:"(automatico)")">
</p>
<p>
<label for='sevenzip_path'>$(lang de:"Pfad zu 7za / 7z:" en:"Path to 7za / 7z:" it:"Percorso 7za / 7z:")
</label>
<input type='text' id='sevenzip_path' name='sevenzip_path' size='40'
	value="$(html "${ELFINDER_7Z_PATH:-}")"
	placeholder="$(lang de:"(automatisch)" en:"(auto-detect)" it:"(automatico)")">
</p>
<p>
<label for='convert_path'>$(lang de:"Pfad zu ImageMagick convert:" en:"Path to ImageMagick convert:" it:"Percorso ImageMagick convert:")
</label>
<input type='text' id='convert_path' name='convert_path' size='40'
	value="$(html "${ELFINDER_CONVERT_PATH:-}")"
	placeholder="$(lang de:"(automatisch)" en:"(auto-detect)" it:"(automatico)")">
</p>
EOF
sec_end

# ===========================================================================
# Section: MediaInfo (conditional on build option)
# ===========================================================================
if which mediainfo >/dev/null 2>&1 || [ -n "$ELFINDER_MEDIAINFO_PATH" ]; then
	sec_begin "$(lang de:"MediaInfo" en:"MediaInfo" it:"MediaInfo")"
	cat << EOF
<p>
<label for='mediainfo_path'>$(lang \
	de:"Pfad zu mediainfo (leer = automatisch):" \
	en:"Path to mediainfo (empty = auto-detect):" \
	it:"Percorso mediainfo (vuoto = automatico):")</label>
<input type='text' id='mediainfo_path' name='mediainfo_path' size='40'
	value="$(html "${ELFINDER_MEDIAINFO_PATH:-}")"
	placeholder="$(lang de:"(automatisch)" en:"(auto-detect)" it:"(automatico)")">
</p>
EOF
	sec_end
fi

# ===========================================================================
# Section: Visual Theme (only shown if at least one theme directory exists)
# ===========================================================================
THEMES_DIR=""
if [ -d "/mod/external/usr/mww/elfinder/css/themes" ]; then
    THEMES_DIR="/mod/external/usr/mww/elfinder/css/themes"
elif [ -d "/usr/mww/elfinder/css/themes" ]; then
    THEMES_DIR="/usr/mww/elfinder/css/themes"
fi

if [ -n "$THEMES_DIR" ] && [ "$(ls -A "$THEMES_DIR" 2>/dev/null)" ]; then
    sec_begin "$(lang de:"Visuelles Thema" en:"Visual Theme" it:"Tema visivo")"
    cat << EOF
<p>
<label for='theme'>$(lang \
    de:"Aktives Thema (leer = Standard-elfinder-Thema):" \
    en:"Active theme (empty = default elfinder theme):" \
    it:"Tema attivo (vuoto = tema elfinder predefinito):")</label>
<br>
<select id='theme' name='theme'>
<option value=''>$(lang de:"Standard (eingebaut)" en:"Default (built-in)" it:"Predefinito (integrato)")</option>
EOF
    for d in "$THEMES_DIR"/*/; do
        tname="${d%/}"
        tname="${tname##*/}"
        if [ -f "$d/css/theme.css" ]; then
            selected=""
            [ "$tname" = "${ELFINDER_THEME:-}" ] && selected=" selected"
            echo "<option value='$(html "$tname")'$selected>$(html "$tname")</option>"
        fi
    done
    cat << 'EOF'
</select>
</p>
EOF
    sec_end
fi
		.then(function(r) { return r.text(); })
		.then(function(text) {
			var marker = 'Content-Type: application/json';
			var pos = text.indexOf(marker);
			if (pos === -1) throw new Error('bad response');
			var first = text.indexOf('{', pos + marker.length);
			var depth = 0, end = -1;
			for (var i = first; i < text.length; i++) {
				if (text[i] === '{') depth++;
				else if (text[i] === '}') { depth--; if (depth === 0) { end = i + 1; break; } }
			}
			var data = JSON.parse(text.substring(first, end));
			if (data.exists) {
				status.style.color = 'green';
				status.textContent = '✓';
			} else {
				status.style.color = '#c00';
				status.textContent = '✗ not found';
			}
		})
		.catch(function() {
			status.style.color = '#c00';
			status.textContent = '?';
		});
}
</script>
ENDSCRIPT
