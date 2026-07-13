#!/bin/sh
# Gerbera CGI web configuration interface

. /usr/lib/libmodcgi.sh

# ============================================================================
# AJAX Handler
# ============================================================================
AJAX_MODE=$(cgi_param ajax)

if [ "$AJAX_MODE" = "1" ]; then
	ACTION=$(cgi_param action)
	BASEDIR=$(cgi_param basedir)

	echo "$(date): AJAX - ACTION=$ACTION BASEDIR=$BASEDIR" >> /tmp/gerbera_ajax.log

	# JSON wrapper (styled)
	cat <<'EOF'
<style>
.ajax-json-box {
	margin: 20px auto;
	max-width: 900px;
	background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
	border-radius: 10px;
	padding: 3px;
	box-shadow: 0 8px 20px rgba(0,0,0,0.15);
}
.ajax-json-content {
	background: #1e1e1e;
	border-radius: 8px;
	padding: 20px;
	font-family: 'Courier New', Consolas, monospace;
	font-size: 13px;
	line-height: 1.6;
	color: #d4d4d4;
	overflow-x: auto;
}
.ajax-json-content pre {
	margin: 0;
	white-space: pre-wrap;
	word-wrap: break-word;
}
.ajax-json-content:empty, .ajax-json-content pre:empty { display: none; }
.ajax-json-box:has(.ajax-json-content:empty) { display: none; }
</style>
<div class="ajax-json-box"><div class="ajax-json-content"><pre>Content-Type: application/json

EOF

	case "$ACTION" in
		check_directory)
			if [ -d "$BASEDIR" ]; then
				echo '{"exists": true, "writable": true}'
			else
				echo '{"exists": false, "writable": false}'
			fi
			;;

		create_directory)
			if mkdir -p "$BASEDIR" 2>/dev/null; then
				echo '{"success": true, "message": "Directory created"}'
			else
				echo '{"success": false, "message": "Failed"}'
			fi
			;;

		check_config)
			if [ -f "$BASEDIR/config.xml" ]; then
				echo '{"exists": true}'
			else
				echo '{"exists": false}'
			fi
			;;

		create_config)
			CONFIG_FILE="$BASEDIR/config.xml"
			TEMPLATE="/mod/etc/default.gerbera/config.xml.template"
			if [ -f "$TEMPLATE" ]; then
				sed -e "s|__GERBERA_FRIENDLY_NAME__|Gerbera (Freetz)|g" \
				    -e "s|__GERBERA_BASEDIR__|$BASEDIR|g" \
				    -e "s|__GERBERA_PORT__|49152|g" \
				    -e "s|__GERBERA_WEBROOT__|/usr/share/gerbera/web|g" \
				    -e "s|__GERBERA_DB_ENGINE__|sqlite3|g" \
				    -e "s|__GERBERA_FOLLOW_SYMLINKS__|yes|g" \
				    -e "s|__GERBERA_TRANSCODING__|no|g" \
				    "$TEMPLATE" > "$CONFIG_FILE" 2>/dev/null && \
				echo '{"success": true}' || \
				echo '{"success": false, "message": "Failed to write config.xml"}'
			else
				# Fallback: create minimal config.xml
				cat > "$CONFIG_FILE" <<'CONFIGXML'
<?xml version="1.0" encoding="UTF-8"?>
<config version="2" xmlns="http://gerbera.io/config/2"
	xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
	xsi:schemaLocation="http://gerbera.io/config/2 http://gerbera.io/config/2.xsd">
	<server>
		<ui enabled="yes" show-tooltips="yes">
			<accounts enabled="no" session-timeout="30"/>
		</ui>
		<name>Gerbera (Freetz)</name>
		<udn/>
		<home>BASEDIR_PLACEHOLDER</home>
		<webroot>/usr/share/gerbera/web</webroot>
		<alive>180</alive>
		<storage>
			<sqlite3 enabled="yes">
				<database-file>BASEDIR_PLACEHOLDER/gerbera.db</database-file>
				<backup enabled="yes" interval="600"/>
			</sqlite3>
		</storage>
		<extended-runtime-options>
			<suppress-duplicate-entries>no</suppress-duplicate-entries>
		</extended-runtime-options>
		<pc-directory>BASEDIR_PLACEHOLDER</pc-directory>
	</server>
	<import hidden-files="no">
		<autoscan use-inotify="auto">
			<directory location="BASEDIR_PLACEHOLDER/media" mode="inotify" recursive="yes">
				<media-type>all</media-type>
			</directory>
		</autoscan>
		<scripting script-charset="UTF-8">
			<script-folder>
				<common>/usr/share/gerbera/js</common>
			</script-folder>
		</scripting>
		<settings>
			<follow-symlinks>yes</follow-symlinks>
			<metadata>
				<use-podcast>yes</use-podcast>
				<read-all-metadata>yes</read-all-metadata>
				<online-metadata><enabled>no</enabled></online-metadata>
			</metadata>
		</settings>
	</import>
	<transcoding><enabled>no</enabled></transcoding>
	<online-content><retrieve-metadata>no</retrieve-metadata></online-content>
</config>
CONFIGXML
				sed -i "s|BASEDIR_PLACEHOLDER|$BASEDIR|g" "$CONFIG_FILE"
				echo '{"success": true}'
			fi
			;;

		create_directories)
			if mkdir -p "$BASEDIR/media" "$BASEDIR/db" "$BASEDIR/log" "$BASEDIR/import" 2>/dev/null; then
				chmod 777 "$BASEDIR" "$BASEDIR/media" "$BASEDIR/db" "$BASEDIR/log" "$BASEDIR/import" 2>/dev/null
				echo '{"success": true}'
			else
				echo '{"success": false}'
			fi
			;;

		read_file)
			FILE_PATH=$(cgi_param file)

			# Expand basename shortcuts
			case "$FILE_PATH" in
				config.xml)
					[ -r /mod/etc/conf/gerbera.cfg ] && . /mod/etc/conf/gerbera.cfg
					BASEDIR="${GERBERA_BASEDIR%/}"
					[ -n "$BASEDIR" ] && FILE_PATH="$BASEDIR/config.xml" || {
						echo '{"error": "GERBERA_BASEDIR not configured"}'
						exit 0
					}
					;;
				config.xml.template|*.template)
					FILE_PATH="/mod/etc/default.gerbera/$FILE_PATH"
					;;
			esac

			# Security: directory traversal prevention
			case "$FILE_PATH" in
				*../*|*/../*|../*) echo '{"error": "Directory traversal not allowed"}'; exit 0 ;;
			esac

			# Whitelist
			ALLOWED=0
			case "$FILE_PATH" in
				/var/media/ftp/*/config.xml|\
				/var/media/ftp/*/*/config.xml|\
				/var/tmp/config.xml|\
				/tmp/config.xml|\
				/mod/etc/default.gerbera/config.xml.template|\
				/mod/etc/default.gerbera/*.template)
					ALLOWED=1
					;;
				*)
					[ -r /mod/etc/conf/gerbera.cfg ] && . /mod/etc/conf/gerbera.cfg
					BASEDIR_RC="${GERBERA_BASEDIR%/}/config.xml"
					[ "$FILE_PATH" = "$BASEDIR_RC" ] && ALLOWED=1
					;;
			esac

			[ "$ALLOWED" = "0" ] && {
				echo "{\"error\": \"Access denied: $FILE_PATH\"}"
				exit 0
			}

			if [ ! -f "$FILE_PATH" ]; then
				echo "{\"error\": \"File not found: $FILE_PATH\", \"content\": \"\"}"
			elif [ ! -r "$FILE_PATH" ]; then
				echo "{\"error\": \"Permission denied: cannot read $FILE_PATH\"}"
			else
				CONTENT=$(cat "$FILE_PATH")

				# Substitute __GERBERA_*__ placeholders when loading template
				case "$FILE_PATH" in
					*/config.xml.template|*/gerbera-config.xml.template)
						[ -r /mod/etc/conf/gerbera.cfg ] && . /mod/etc/conf/gerbera.cfg
						: "${GERBERA_FRIENDLY_NAME:=Gerbera (Freetz)}"
						: "${GERBERA_PORT:=49152}"
						: "${GERBERA_BASEDIR:=/tmp/flash/gerbera}"
						: "${GERBERA_WEBROOT:=/usr/share/gerbera/web}"
						: "${GERBERA_DB_ENGINE:=sqlite3}"
						: "${GERBERA_FOLLOW_SYMLINKS:=yes}"
						: "${GERBERA_TRANSCODING:=no}"

						CONTENT=$(echo "$CONTENT" | sed \
							-e "s|__GERBERA_FRIENDLY_NAME__|${GERBERA_FRIENDLY_NAME}|g" \
							-e "s|__GERBERA_PORT__|${GERBERA_PORT}|g" \
							-e "s|__GERBERA_BASEDIR__|${GERBERA_BASEDIR}|g" \
							-e "s|__GERBERA_WEBROOT__|${GERBERA_WEBROOT}|g" \
							-e "s|__GERBERA_DB_ENGINE__|${GERBERA_DB_ENGINE}|g" \
							-e "s|__GERBERA_FOLLOW_SYMLINKS__|${GERBERA_FOLLOW_SYMLINKS}|g" \
							-e "s|__GERBERA_TRANSCODING__|${GERBERA_TRANSCODING}|g")
						;;
				esac

				CONTENT=$(echo "$CONTENT" | sed 's/\\/\\\\/g; s/"/\\"/g; s/	/\\t/g' | awk '{printf "%s\\n", $0}' | sed '$ s/\\n$//')
				echo "{\"success\": true, \"file\": \"$FILE_PATH\", \"content\": \"$CONTENT\"}"
			fi
			;;

		write_file)
			FILE_PATH=$(cgi_param file)
			CONTENT=$(cgi_param content)

			# Expand basename shortcuts
			case "$FILE_PATH" in
				config.xml)
					[ -r /mod/etc/conf/gerbera.cfg ] && . /mod/etc/conf/gerbera.cfg
					BASEDIR="${GERBERA_BASEDIR%/}"
					[ -n "$BASEDIR" ] && FILE_PATH="$BASEDIR/config.xml" || {
						echo '{"error": "GERBERA_BASEDIR not configured"}'
						exit 0
					}
					;;
			esac

			case "$FILE_PATH" in
				*../*|*/../*|../*) echo '{"error": "Directory traversal not allowed"}'; exit 0 ;;
			esac

			ALLOWED=0
			case "$FILE_PATH" in
				/var/media/ftp/*/config.xml|\
				/var/media/ftp/*/*/config.xml|\
				/var/tmp/config.xml|\
				/tmp/config.xml)
					ALLOWED=1
					;;
				*)
					[ -r /mod/etc/conf/gerbera.cfg ] && . /mod/etc/conf/gerbera.cfg
					BASEDIR_RC="${GERBERA_BASEDIR%/}/config.xml"
					[ "$FILE_PATH" = "$BASEDIR_RC" ] && ALLOWED=1
					;;
			esac

			[ "$ALLOWED" = "0" ] && {
				echo "{\"error\": \"Access denied: $FILE_PATH\"}"
				exit 0
			}

			FILE_DIR=$(dirname "$FILE_PATH")
			[ ! -d "$FILE_DIR" ] && {
				echo "{\"error\": \"Directory does not exist: $FILE_DIR\"}"
				exit 0
			}

			# Backup existing file
			if [ -f "$FILE_PATH" ]; then
				TIMESTAMP=$(date +%Y-%m-%d-%H-%M-%S)
				BACKUP_FILE="${FILE_PATH}.${TIMESTAMP}"
				mv "$FILE_PATH" "$BACKUP_FILE" 2>/dev/null || {
					echo "{\"error\": \"Failed to create backup\"}"
					exit 0
				}
			fi

			if echo "$CONTENT" > "$FILE_PATH" 2>/dev/null; then
				chmod 666 "$FILE_PATH" 2>/dev/null
				echo "{\"success\": true, \"file\": \"$FILE_PATH\"}"
			else
				[ -n "$BACKUP_FILE" ] && [ -f "$BACKUP_FILE" ] && mv "$BACKUP_FILE" "$FILE_PATH" 2>/dev/null
				echo "{\"error\": \"Failed to write file: $FILE_PATH\"}"
			fi
			;;

		delete_config)
			CONFIG_FILE="$BASEDIR/config.xml"

			if [ -z "$BASEDIR" ]; then
				echo '{"success": false, "message": "No basedir specified"}'
			elif [ ! -f "$CONFIG_FILE" ]; then
				echo '{"success": false, "message": "File does not exist"}'
			else
				TIMESTAMP=$(date +%Y-%m-%d-%H-%M-%S)
				BACKUP_FILE="${CONFIG_FILE}.${TIMESTAMP}"
				if mv "$CONFIG_FILE" "$BACKUP_FILE" 2>/dev/null; then
					echo "{\"success\": true, \"message\": \"File archived to: ${BACKUP_FILE##*/}\"}"
				else
					echo '{"success": false, "message": "Failed to archive file"}'
				fi
			fi
			;;

		save_basedir_only)
			if [ -f /mod/etc/conf/gerbera.cfg ]; then
				sed -i "s|^export GERBERA_BASEDIR=.*|export GERBERA_BASEDIR='$BASEDIR'|" /mod/etc/conf/gerbera.cfg
				sed -i "s|^export GERBERA_ENABLED=.*|export GERBERA_ENABLED='no'|" /mod/etc/conf/gerbera.cfg
				grep -q "^export GERBERA_BASEDIR=" /mod/etc/conf/gerbera.cfg || echo "export GERBERA_BASEDIR='$BASEDIR'" >> /mod/etc/conf/gerbera.cfg
				grep -q "^export GERBERA_ENABLED=" /mod/etc/conf/gerbera.cfg || echo "export GERBERA_ENABLED='no'" >> /mod/etc/conf/gerbera.cfg
			else
				echo "export GERBERA_BASEDIR='$BASEDIR'" > /mod/etc/conf/gerbera.cfg
				echo "export GERBERA_ENABLED='no'" >> /mod/etc/conf/gerbera.cfg
			fi
			modsave flash >> /tmp/gerbera_ajax.log 2>&1
			echo '{"success": true}'
			;;

		start_service)
			if [ -f /mod/etc/conf/gerbera.cfg ]; then
				sed -i "s|^export GERBERA_BASEDIR=.*|export GERBERA_BASEDIR='$BASEDIR'|" /mod/etc/conf/gerbera.cfg
				sed -i "s|^export GERBERA_ENABLED=.*|export GERBERA_ENABLED='yes'|" /mod/etc/conf/gerbera.cfg
				grep -q "^export GERBERA_ENABLED=" /mod/etc/conf/gerbera.cfg || echo "export GERBERA_ENABLED='yes'" >> /mod/etc/conf/gerbera.cfg
			else
				echo "export GERBERA_BASEDIR='$BASEDIR'" > /mod/etc/conf/gerbera.cfg
				echo "export GERBERA_ENABLED='yes'" >> /mod/etc/conf/gerbera.cfg
			fi
			modsave flash >> /tmp/gerbera_ajax.log 2>&1
			if [ -x /mod/etc/init.d/rc.gerbera ]; then
				START_OUTPUT=$(/mod/etc/init.d/rc.gerbera start 2>&1)
			elif [ -x /etc/init.d/rc.gerbera ]; then
				START_OUTPUT=$(/etc/init.d/rc.gerbera start 2>&1)
			else
				START_OUTPUT=""
			fi
			START_EXIT=$?
			if [ $START_EXIT -eq 0 ]; then
				echo '{"success": true}'
			else
				ESCAPED_OUTPUT=$(echo "$START_OUTPUT" | sed 's/"/\\"/g' | tr '\n' ' ')
				echo "{\"success\": false, \"message\": \"Exit code $START_EXIT: $ESCAPED_OUTPUT\"}"
			fi
			;;

		get_port)
			CONFIG_FILE="$BASEDIR/config.xml"
			PORT="49152"
			if [ -f "$CONFIG_FILE" ]; then
				PORT=$(grep -oP '(?<=<port>)[^<]+' "$CONFIG_FILE" 2>/dev/null || echo "49152")
			fi
			echo "{\"port\": \"$PORT\"}"
			;;

		*)
			echo '{"error": "Unknown action"}'
			;;
	esac

	echo '</pre></div></div>'
	exit 0
fi

# ============================================================================
# Setup Wizard Actions (POST)
# ============================================================================
WIZARD_ACTION=$(cgi_param wizard_action)
if [ -n "$WIZARD_ACTION" ]; then
	BASEDIR=$(cgi_param basedir)
	case "$WIZARD_ACTION" in
		auto_setup)
			if [ ! -d "$BASEDIR" ]; then
				mkdir -p "$BASEDIR" 2>/dev/null
				chmod 777 "$BASEDIR" 2>/dev/null
			fi
			CONFIG_FILE="$BASEDIR/config.xml"
			if [ ! -f "$CONFIG_FILE" ]; then
				TEMPLATE="/mod/etc/default.gerbera/config.xml.template"
				if [ -f "$TEMPLATE" ]; then
					sed -e "s|__GERBERA_FRIENDLY_NAME__|Gerbera (Freetz)|g" \
					    -e "s|__GERBERA_BASEDIR__|$BASEDIR|g" \
					    -e "s|__GERBERA_PORT__|49152|g" \
					    -e "s|__GERBERA_WEBROOT__|/usr/share/gerbera/web|g" \
					    -e "s|__GERBERA_DB_ENGINE__|sqlite3|g" \
					    -e "s|__GERBERA_FOLLOW_SYMLINKS__|yes|g" \
					    -e "s|__GERBERA_TRANSCODING__|no|g" \
					    "$TEMPLATE" > "$CONFIG_FILE" 2>/dev/null
				fi
			fi
			mkdir -p "$BASEDIR/media" "$BASEDIR/db" "$BASEDIR/log" "$BASEDIR/import" 2>/dev/null
			chmod 777 "$BASEDIR" "$BASEDIR/media" "$BASEDIR/db" "$BASEDIR/log" "$BASEDIR/import" 2>/dev/null
			WIZARD_MSG="✓ Auto-setup complete!"
			;;
	esac
fi

# ============================================================================
# Load configuration
# ============================================================================
[ -r /etc/options.cfg ] && . /etc/options.cfg
[ -r /mod/etc/conf/gerbera.cfg ] && . /mod/etc/conf/gerbera.cfg

: "${GERBERA_ENABLED:=no}"
: "${GERBERA_BASEDIR:=/tmp/flash/gerbera}"
: "${GERBERA_PORT:=49152}"
: "${GERBERA_FRIENDLY_NAME:=Gerbera (Freetz)}"

# Check if config.xml exists
GERBERA_CONFIG_EXISTS="no"
if [ -n "$GERBERA_BASEDIR" ] && [ -f "${GERBERA_BASEDIR%/}/config.xml" ]; then
	GERBERA_CONFIG_EXISTS="yes"
fi

# Auto-detect storage
autodetect_storage_hint() {
	[ -r /mod/etc/conf/mod.cfg ] && . /mod/etc/conf/mod.cfg
	local stor_prefix="${MOD_STOR_PREFIX:-uStor}"
	if [ -d "/var/media/ftp/${stor_prefix}01" ]; then
		echo "/var/media/ftp/${stor_prefix}01/gerbera"
	elif ls -d /var/media/ftp/*/ >/dev/null 2>&1; then
		echo "$(ls -d /var/media/ftp/*/ 2>/dev/null | head -n1)gerbera"
	else
		echo "/tmp/flash/gerbera"
	fi
}
AUTO_STORAGE="$(autodetect_storage_hint)"

# Helper: read value from config.xml
get_config_value() {
	local config_file="$1"
	local xpath="$2"
	local default="$3"
	[ ! -f "$config_file" ] && echo "$default" && return
	local val
	val=$(grep -oP "(?<=<$xpath>)[^<]+" "$config_file" 2>/dev/null | head -1)
	echo "${val:-$default}"
}

# Read values from config.xml
CONFIG_FILE="${GERBERA_BASEDIR%/}/config.xml"
VAL_FRIENDLY_NAME=$(get_config_value "$CONFIG_FILE" "name" "$GERBERA_FRIENDLY_NAME")
VAL_PORT=$(get_config_value "$CONFIG_FILE" "port" "$GERBERA_PORT")
VAL_DB_ENGINE=$(get_config_value "$CONFIG_FILE" "engine" "sqlite3")
VAL_FOLLOW_SYMLINKS=$(get_config_value "$CONFIG_FILE" "follow-symlinks" "yes")
TRANSCODING_ENABLED=$(grep -ozP '<transcoding>\s*\n\s*<enabled>[^<]+</enabled>' "$CONFIG_FILE" 2>/dev/null | grep -oP '(?<=<enabled>)[^<]+' || echo "no")

# Dark-mode CSS
cat << 'GERBERA_DARK_STYLE'
<style>
.evo-gerbera-warning  { color: #856404; background: #fff3cd; }
.evo-gerbera-info     { color: #1565c0; background: #e7f3ff; border-left: 4px solid #2196F3; border-radius: 4px; padding: 12px; margin-top: 10px; }
.evo-gerbera-note     { color: #0066cc; background: #f0f8ff; border-left: 3px solid #0066cc; border-radius: 3px; }
.evo-gerbera-success  { background: #d4edda; border-left: 4px solid #28a745; border-radius: 4px; padding: 15px; margin: 15px 0; }
.evo-gerbera-success-light { background: #e8f5e9; border-radius: 4px; padding: 15px; margin: 15px 0; }
.evo-gerbera-warn2    { background: #fff3cd; border-left: 4px solid #ffc107; border-radius: 4px; padding: 15px; }
.evo-gerbera-li       { padding: 8px; background: #f8f9fa; margin-bottom: 8px; border-radius: 4px; }
.evo-gerbera-danger   { background: #f8d7da; border-radius: 4px; padding: 12px; margin-top: 10px; }
.evo-gerbera-success-sm { background: #d4edda; border-radius: 4px; padding: 12px; margin-top: 10px; }
.evo-gerbera-warn-sm  { background: #fff3cd; border-radius: 4px; padding: 12px; margin-top: 10px; }
/* Dark mode */
body.dark-mode .evo-gerbera-warning,
html.dark-mode .evo-gerbera-warning    { color: #fcd34d; background: #422006; }
body.dark-mode .evo-gerbera-info,
html.dark-mode .evo-gerbera-info       { color: #93c5fd; background: #0c1a2e; border-color: #1e40af; }
body.dark-mode .evo-gerbera-note,
html.dark-mode .evo-gerbera-note       { color: #7dd3fc; background: #0c1a2e; border-color: #1e40af; }
body.dark-mode .evo-gerbera-success,
body.dark-mode .evo-gerbera-success-light,
html.dark-mode .evo-gerbera-success,
html.dark-mode .evo-gerbera-success-light { background: #052e16; border-color: #15803d; color: #86efac; }
body.dark-mode .evo-gerbera-warn2,
html.dark-mode .evo-gerbera-warn2      { background: #422006; border-color: #b45309; color: #fcd34d; }
body.dark-mode .evo-gerbera-li,
html.dark-mode .evo-gerbera-li         { background: var(--evo-bg, #0f172a); color: var(--evo-text, #e2e8f0); }
body.dark-mode .evo-gerbera-danger,
html.dark-mode .evo-gerbera-danger     { background: #450a0a; color: #fca5a5; }
body.dark-mode .evo-gerbera-success-sm,
html.dark-mode .evo-gerbera-success-sm { background: #052e16; color: #86efac; }
body.dark-mode .evo-gerbera-warn-sm,
html.dark-mode .evo-gerbera-warn-sm    { background: #422006; color: #fcd34d; }
@media (prefers-color-scheme: dark) {
  body:not(.light-mode) .evo-gerbera-warning    { color: #fcd34d; background: #422006; }
  body:not(.light-mode) .evo-gerbera-info       { color: #93c5fd; background: #0c1a2e; border-color: #1e40af; }
  body:not(.light-mode) .evo-gerbera-note       { color: #7dd3fc; background: #0c1a2e; border-color: #1e40af; }
  body:not(.light-mode) .evo-gerbera-success,
  body:not(.light-mode) .evo-gerbera-success-light { background: #052e16; border-color: #15803d; color: #86efac; }
  body:not(.light-mode) .evo-gerbera-warn2      { background: #422006; border-color: #b45309; color: #fcd34d; }
  body:not(.light-mode) .evo-gerbera-li         { background: var(--evo-bg, #0f172a); color: var(--evo-text, #e2e8f0); }
  body:not(.light-mode) .evo-gerbera-danger     { background: #450a0a; color: #fca5a5; }
  body:not(.light-mode) .evo-gerbera-success-sm { background: #052e16; color: #86efac; }
  body:not(.light-mode) .evo-gerbera-warn-sm    { background: #422006; color: #fcd34d; }
}
</style>
GERBERA_DARK_STYLE

# Page Output
if [ -z "$GERBERA_BASEDIR" ] || [ "$GERBERA_CONFIG_EXISTS" = "no" ]; then
	# SETUP WIZARD - shown when no basedir or no config.xml

	sec_begin "$(lang de:"Starttyp" en:"Start type")"
	cat << EOF
<p class="evo-gerbera-warning" style="padding: 10px; border-radius: 4px;">
ℹ️ $(lang de:"Bitte f\u00fchren Sie zuerst die Ersteinrichtung durch" en:"Please complete initial setup first")
</p>

<p style="margin-top: 15px;">
	<label for='basedir_initial'><strong>$(lang de:"Basisverzeichnis" en:"Base Directory"):</strong></label><br>
	<input type='text' id='basedir_initial' name='basedir' size='50' maxlength='255'
	       value="$(html "${GERBERA_BASEDIR:-$AUTO_STORAGE}")"
	       style="padding: 8px; font-size: 14px; width: 100%; max-width: 600px; box-sizing: border-box; border: 2px solid #ddd; border-radius: 4px;"
	       title="$(lang de:"Hauptverzeichnis f\u00fcr Gerbera. Medien, Datenbank und Konfiguration werden hier gespeichert." en:"Main directory for Gerbera. Media, database and configuration files are stored here.")">
</p>
EOF

if [ -z "$GERBERA_BASEDIR" ]; then
	cat << EOF
<p style="color: #666; font-size: 12px; margin-top: 5px;">
	<strong>$(lang de:"Empfohlen" en:"Suggested"):</strong> <code>$AUTO_STORAGE</code>
</p>
EOF
elif [ ! -d "$GERBERA_BASEDIR" ]; then
	cat << EOF
<p style="color: #f80; font-size: 12px; margin-top: 5px;">
	⚠️ $(lang de:"Verzeichnis existiert nicht" en:"Directory does not exist"): <code>$(html "$GERBERA_BASEDIR")</code>
</p>
EOF
fi

# Storage device list
cat << EOF
<div style="margin-top: 10px; border: 1px solid var(--evo-border, #ddd); background-color: var(--evo-surface, #f9f9f9); padding: 8px; border-radius: 4px;">
<div style="font-weight: bold; margin-bottom: 5px; color: var(--evo-text, #333);">$(lang de:"Verfügbare Speichergeräte (RW)" en:"Available Storage Devices (RW)"):</div>
<div style="max-height: 150px; overflow-y: auto;">
<table style="width: 100%; font-size: 11px; border-collapse: collapse;">
EOF

DFOUT=$(df -hP)
mount | sed -rn '
	\#^/dev/(sd|mapper/)|^https?://|^.* on .* type (cifs|fuse|jffs|ubifs|yaffs|ext)|^.*:/.* on .* type nfs# {
		\# on /wrapper | on /var/flash #! {
			s/^([^ ]+) on (.*) type ([^ ]*) \(([^)]*)\)$/\3 \4 \1 \2/; p
		}
	}
' | while read -r fstyp mountopts device path; do
	case "$mountopts" in
		rw*)
			dfline=$(echo "$DFOUT" | grep " $path$")
			if [ -n "$dfline" ]; then
				avail=$(echo "$dfline" | awk '{print $4}')
				total=$(echo "$dfline" | awk '{print $2}')
				info="$avail / $total"
			else
				info="-"
			fi
			echo "<tr>"
			echo "<td style='padding: 3px 2px; border-bottom: 1px solid #eee;'><code style='cursor: pointer; color: #0056b3; font-weight: bold;' onclick=\"document.getElementById('basedir_initial').value='$path/gerbera';\">$path</code></td>"
			echo "<td style='padding: 3px 2px; border-bottom: 1px solid #eee; color: #666;'>$fstyp</td>"
			echo "<td style='padding: 3px 2px; border-bottom: 1px solid #eee; text-align: right;'>$info</td>"
			echo "</tr>"
			;;
	esac
done

if [ -d "/var/media/ftp" ]; then
	for subdir in /var/media/ftp/*/; do
		if [ -d "$subdir" ]; then
			path="${subdir%/}"
			if ! mount | grep -q " on $path type "; then
				dfline=$(echo "$DFOUT" | grep " $path$")
				if [ -n "$dfline" ]; then
					avail=$(echo "$dfline" | awk '{print $4}')
					total=$(echo "$dfline" | awk '{print $2}')
					info="$avail / $total"
					fstyp=$(df -T "$path" 2>/dev/null | tail -1 | awk '{print $2}')
				else
					info="-"
					fstyp="dir"
				fi
				echo "<tr>"
				echo "<td style='padding: 3px 2px; border-bottom: 1px solid #eee;'><code style='cursor: pointer; color: #0056b3; font-weight: bold;' onclick=\"document.getElementById('basedir_initial').value='$path/gerbera';\">$path</code></td>"
				echo "<td style='padding: 3px 2px; border-bottom: 1px solid #eee; color: #666;'>$fstyp</td>"
				echo "<td style='padding: 3px 2px; border-bottom: 1px solid #eee; text-align: right;'>$info</td>"
				echo "</tr>"
			fi
		fi
	done
fi

cat << EOF
</table>
</div>
<div style="font-size: 10px; color: #666; margin-top: 5px;">$(lang de:"Klicken um Pfad als Basisverzeichnis zu übernehmen" en:"Click to use path as base directory")</div>
</div>

<p style="text-align: center; margin-top: 15px;">
	<button type="button" onclick="openSetupWizard()" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 12px 30px; font-size: 15px; font-weight: bold; border-radius: 6px; cursor: pointer; box-shadow: 0 3px 5px rgba(0,0,0,0.2);">
		🚀 $(lang de:"Ersteinrichtungs-Assistent starten" en:"Start Initial Setup Wizard")
	</button>
</p>
EOF

# Wizard Modal HTML
AUTO_STORAGE_ESC=$(html "$AUTO_STORAGE")
cat << 'WIZARD_HTML' | sed "s|__AUTO_STORAGE__|${AUTO_STORAGE_ESC}|g"
<!-- Toast Container -->
<div id="toastContainer" style="position: fixed; top: 20px; right: 20px; z-index: 9999; min-width: 300px; max-width: 400px;"></div>

<!-- Setup Wizard Modal -->
<div id="setupWizardModal" style="display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; overflow: auto; background-color: rgba(0,0,0,0.6);">
	<div id="wizardContainer" style="background-color: var(--evo-surface, #fff); margin: 3% auto; padding: 0; border-radius: 10px; width: 90%; max-width: 800px; box-shadow: 0 5px 15px rgba(0,0,0,0.3); color: var(--evo-text, #333);">

		<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px 10px 0 0;">
			<h2 style="margin: 0; color: white;">🚀 Gerbera Initial Setup</h2>
			<p style="margin: 10px 0 0 0; opacity: 0.9;" id="wizardSubtitle">Step 1 of 5</p>
		</div>

		<div style="padding: 30px;">
			<!-- Step 1: Base Directory -->
			<div class="wizard-step" id="step1">
				<h3 style="color: var(--evo-text, #495057); margin-top: 0;">
					<span style="background: #667eea; color: white; border-radius: 50%; padding: 5px 12px; margin-right: 10px;">1</span>
					Base Directory
				</h3>
				<p>Choose a directory on your USB storage or NAS where Gerbera stores its media database and configuration.</p>
				<p>
					<label for='setup_basedir'><strong>Directory path:</strong></label><br>
					<input type='text' id='setup_basedir' name='setup_basedir' size='60' maxlength='255'
					       value="__AUTO_STORAGE__" style="padding: 10px; font-size: 14px; width: 100%; box-sizing: border-box; border: 2px solid #ddd; border-radius: 4px;">
				</p>
				<div id="dirCheckResult"></div>
				<div class="evo-gerbera-info">
					<p style="margin: 0; color: #1976D2;"><strong>💡 Recommendation:</strong></p>
					<p style="margin: 5px 0 0 0; font-size: 13px; color: var(--evo-text-muted, #555);">
						Example: <code>__AUTO_STORAGE__</code><br>
						The directory should be on persistent storage (USB, NAS).
					</p>
				</div>
			</div>

			<!-- Step 2: config.xml Check -->
			<div class="wizard-step" id="step2" style="display: none;">
				<h3 style="color: var(--evo-text, #495057); margin-top: 0;">
					<span style="background: #667eea; color: white; border-radius: 50%; padding: 5px 12px; margin-right: 10px;">2</span>
					Configuration File
				</h3>
				<div id="configFileCheck">
					<p>Checking config.xml...</p>
				</div>
			</div>

			<!-- Step 3: Directory Structure -->
			<div class="wizard-step" id="step3" style="display: none;">
				<h3 style="color: var(--evo-text, #495057); margin-top: 0;">
					<span style="background: #667eea; color: white; border-radius: 50%; padding: 5px 12px; margin-right: 10px;">3</span>
					Directory Structure
				</h3>
				<p>The following directories will be created:</p>
				<ul style="line-height: 2; list-style: none; padding: 0;">
					<li class="evo-gerbera-li">📁 <strong>media/</strong> - Media files</li>
					<li class="evo-gerbera-li">📁 <strong>db/</strong> - Database backups</li>
					<li class="evo-gerbera-li">📁 <strong>log/</strong> - Log files</li>
					<li class="evo-gerbera-li">📁 <strong>import/</strong> - Import</li>
				</ul>
			</div>

			<!-- Step 4: Network -->
			<div class="wizard-step" id="step4" style="display: none;">
				<h3 style="color: var(--evo-text, #495057); margin-top: 0;">
					<span style="background: #667eea; color: white; border-radius: 50%; padding: 5px 12px; margin-right: 10px;">4</span>
					Network
				</h3>
				<p>Gerbera runs as a UPnP Media Server and communicates over the following ports:</p>
				<div class="evo-gerbera-success-light">
					<p style="margin: 0 0 10px 0;"><strong>Default ports:</strong></p>
					<ul style="list-style: none; padding: 0; margin: 0;">
						<li style="padding: 5px 0;">🌐 <strong>TCP Port 49152</strong> - Web interface</li>
						<li style="padding: 5px 0;">📡 <strong>UPnP</strong> - Automatic port selection</li>
					</ul>
				</div>
			</div>

			<!-- Step 5: Completion -->
			<div class="wizard-step" id="step5" style="display: none;">
				<h3 style="color: var(--evo-text, #495057); margin-top: 0;">
					<span style="background: #28a745; color: white; border-radius: 50%; padding: 5px 12px; margin-right: 10px;">✓</span>
					Setup Complete!
				</h3>
				<div class="evo-gerbera-success">
					<p style="margin: 0; color: #155724;">
						<strong>✓ Gerbera is ready for configuration</strong>
					</p>
				</div>
				<div style="text-align: center; margin-top: 20px;">
					<button type="button" onclick="finishWizard()" style="background: #28a745; color: white; border: none; padding: 12px 30px; border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 15px;">
						✓ Finish
					</button>
				</div>
			</div>
		</div>

		<!-- Wizard Footer -->
		<div id="wizardFooter" style="background: var(--evo-bg, #f8f9fa); padding: 15px 30px; border-radius: 0 0 10px 10px; border-top: 1px solid var(--evo-border, #dee2e6);">
			<div id="wizardFooterNormal" style="display: flex; justify-content: space-between;">
				<button type="button" onclick="closeSetupWizard()" style="background: #6c757d; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer;">
					Cancel
				</button>
				<div>
					<button type="button" id="prevBtn" onclick="changeStep(-1)" style="display: none; background: #6c757d; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; margin-right: 10px;">
						← Back
					</button>
					<button type="button" id="nextBtn" onclick="changeStep(1)" style="background: #667eea; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer;">
						Next →
					</button>
				</div>
			</div>
			<div id="wizardFooterConfirm" style="display: none; text-align: center;">
				<p style="margin: 0 0 15px 0; font-size: 15px; color: var(--evo-text, #333);">
					Do you really want to exit the wizard?
				</p>
				<button type="button" onclick="cancelCloseWizard()" style="background: #95a5a6; color: white; border: none; padding: 10px 24px; border-radius: 4px; cursor: pointer; font-size: 14px; margin-right: 10px;">
					Cancel
				</button>
				<button type="button" onclick="confirmCloseWizard()" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 10px 24px; border-radius: 4px; cursor: pointer; font-size: 14px;">
					OK
				</button>
			</div>
		</div>
	</div>
</div>
WIZARD_HTML

# Wizard JavaScript
cat << 'WIZARD_JS'
<script>
function showToast(message, type, duration) {
	if (type !== 'error') return;
	var container = document.getElementById('toastContainer');
	var toast = document.createElement('div');
	var bgColor = '#f44336';
	var icon = '✗';
	toast.style.cssText = 'background: ' + bgColor + '; color: white; padding: 16px 20px; margin-bottom: 10px; border-radius: 6px; box-shadow: 0 3px 10px rgba(0,0,0,0.3); display: flex; align-items: center; animation: slideIn 0.3s ease;';
	toast.innerHTML = '<span style="font-size: 20px; margin-right: 12px;">' + icon + '</span><span style="flex: 1;">' + message + '</span><button onclick="this.parentElement.remove()" style="background: rgba(255,255,255,0.2); border: none; color: white; padding: 4px 12px; border-radius: 4px; margin-left: 10px; cursor: pointer; font-weight: bold;">✕</button>';
	container.appendChild(toast);
}
if (!document.getElementById('toastStyles')) {
	var style = document.createElement('style');
	style.id = 'toastStyles';
	style.textContent = '@keyframes slideIn { from { transform: translateX(400px); opacity: 0; } to { transform: translateX(0); opacity: 1; } }';
	document.head.appendChild(style);
}

var currentStep = 1;
var totalSteps = 5;
var wizardData = {
	basedir: '',
	needsConfig: false
};

function openSetupWizard() {
	var initialBasedirField = document.getElementById('basedir_initial');
	if (initialBasedirField && initialBasedirField.value.trim()) {
		wizardData.basedir = initialBasedirField.value.trim();
	}
	var setupBasedirField = document.getElementById('setup_basedir');
	if (setupBasedirField) {
		setupBasedirField.value = wizardData.basedir;
	}
	document.getElementById('setupWizardModal').style.display = 'block';
	showStep(1);
}

function closeSetupWizard() {
	document.getElementById('wizardFooterNormal').style.display = 'none';
	document.getElementById('wizardFooterConfirm').style.display = 'block';
}

function cancelCloseWizard() {
	document.getElementById('wizardFooterConfirm').style.display = 'none';
	document.getElementById('wizardFooterNormal').style.display = 'flex';
}

function confirmCloseWizard() {
	document.getElementById('setupWizardModal').style.display = 'none';
	document.getElementById('wizardFooterConfirm').style.display = 'none';
	document.getElementById('wizardFooterNormal').style.display = 'flex';
}

function finishWizard() {
	document.getElementById('setupWizardModal').style.display = 'none';
	window.location.reload();
}

function showStep(step) {
	var steps = document.getElementsByClassName('wizard-step');
	for (var i = 0; i < steps.length; i++) {
		steps[i].style.display = 'none';
	}
	document.getElementById('step' + step).style.display = 'block';
	currentStep = step;
	document.getElementById('wizardSubtitle').textContent = 'Step ' + step + ' of ' + totalSteps;
	document.getElementById('prevBtn').style.display = step === 1 ? 'none' : 'inline-block';
	document.getElementById('nextBtn').style.display = step === totalSteps ? 'none' : 'inline-block';
	if (step === 2) setTimeout(checkConfig, 300);
}

function changeStep(direction) {
	if (direction > 0) {
		if (currentStep === 1) {
			validateAndCheckBasedir();
			return;
		} else if (currentStep === 2) {
			showStep(3);
			return;
		} else if (currentStep === 3) {
			createDirectories();
			return;
		} else if (currentStep === 4) {
			showStep(5);
			return;
		}
	} else {
		if (currentStep > 1) showStep(currentStep - 1);
	}
}

function makeAjaxCall(action, params, callback) {
	var url = window.location.pathname;
	var data = 'ajax=1&action=' + encodeURIComponent(action);
	for (var key in params) {
		data += '&' + key + '=' + encodeURIComponent(params[key]);
	}
	var xhr = new XMLHttpRequest();
	xhr.open('GET', url + '?' + data, true);
	xhr.onload = function() {
		if (xhr.status === 200) {
			try {
				var text = xhr.responseText;
				var jsonStart = text.indexOf('Content-Type: application/json');
				if (jsonStart === -1) throw new Error('No JSON found');
				var jsonText = text.substring(jsonStart);
				var firstBrace = jsonText.indexOf('{');
				if (firstBrace === -1) throw new Error('No JSON object found');
				jsonText = jsonText.substring(firstBrace);
				var endPos = jsonText.indexOf('\n<');
				if (endPos > 0) jsonText = jsonText.substring(0, endPos).trim();
				var response = JSON.parse(jsonText);
				callback(null, response);
			} catch(e) {
				console.error('Parse error:', e.message);
				callback('Invalid JSON response', null);
			}
		} else {
			callback('Request failed: ' + xhr.status, null);
		}
	};
	xhr.onerror = function() { callback('Network error', null); };
	xhr.send();
}

function validateAndCheckBasedir() {
	var basedir = document.getElementById('setup_basedir').value.trim();
	if (!basedir) return;
	wizardData.basedir = basedir;
	document.getElementById('dirCheckResult').innerHTML = '<p>Checking directory...</p>';

	makeAjaxCall('check_directory', {basedir: basedir}, function(err, response) {
		if (err) {
			document.getElementById('dirCheckResult').innerHTML =
				'<div class="evo-gerbera-danger"><p style="margin: 0; color: #721c24;">✗ Error: ' + err + '</p></div>';
			showToast('Error checking directory', 'error', 4000);
			return;
		}
		if (response.exists) {
			document.getElementById('dirCheckResult').innerHTML =
				'<div class="evo-gerbera-success-sm"><p style="margin: 0; color: #155724;">✓ Directory exists, saving configuration...</p></div>';
			makeAjaxCall('save_basedir_only', {basedir: basedir}, function(err2, resp2) {
				if (err2 || !resp2 || !resp2.success) {
					document.getElementById('dirCheckResult').innerHTML =
						'<div class="evo-gerbera-danger"><p style="margin: 0; color: #721c24;">✗ Error saving configuration</p></div>';
					return;
				}
				document.getElementById('dirCheckResult').innerHTML =
					'<div class="evo-gerbera-success-sm"><p style="margin: 0; color: #155724;">✓ Directory exists and configuration saved</p></div>';
				setTimeout(function() { showStep(2); }, 800);
			});
		} else {
			document.getElementById('dirCheckResult').innerHTML =
				'<div class="evo-gerbera-warn-sm"><p style="margin: 0; color: #856404;">ℹ Directory does not exist</p>' +
				'<button onclick="createBasedir(\'' + basedir + '\')" style="margin-top: 10px; background: #28a745; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-weight: bold;">Create Now</button></div>';
		}
	});
}

function createBasedir(basedir) {
	document.getElementById('dirCheckResult').innerHTML = '<p>Creating directory...</p>';
	makeAjaxCall('create_directory', {basedir: basedir}, function(err, response) {
		if (err || !response.success) {
			document.getElementById('dirCheckResult').innerHTML =
				'<div class="evo-gerbera-danger"><p style="margin: 0; color: #721c24;">✗ Error creating directory</p></div>';
			return;
		}
		document.getElementById('dirCheckResult').innerHTML =
			'<div class="evo-gerbera-success-sm"><p style="margin: 0; color: #155724;">✓ Directory created, saving configuration...</p></div>';
		makeAjaxCall('save_basedir_only', {basedir: basedir}, function(err2, resp2) {
			if (err2 || !resp2 || !resp2.success) {
				document.getElementById('dirCheckResult').innerHTML =
					'<div class="evo-gerbera-danger"><p style="margin: 0; color: #721c24;">✗ Error saving configuration</p></div>';
				return;
			}
			document.getElementById('dirCheckResult').innerHTML =
				'<div class="evo-gerbera-success-sm"><p style="margin: 0; color: #155724;">✓ Directory created and configuration saved</p></div>';
			setTimeout(function() { showStep(2); }, 800);
		});
	});
}

function checkConfig() {
	document.getElementById('configFileCheck').innerHTML = '<p>Checking config.xml...</p>';
	makeAjaxCall('check_config', {basedir: wizardData.basedir}, function(err, response) {
		if (err) {
			document.getElementById('configFileCheck').innerHTML =
				'<div class="evo-gerbera-danger"><p style="margin: 0; color: #721c24;">✗ Error checking config.xml</p></div>';
			return;
		}
		wizardData.needsConfig = !response.exists;
		if (response.exists) {
			document.getElementById('configFileCheck').innerHTML =
				'<div class="evo-gerbera-success-sm"><p style="margin: 0; color: #155724;">✓ <strong>config.xml</strong> found</p></div>';
			setTimeout(function() { showStep(3); }, 800);
		} else {
			document.getElementById('configFileCheck').innerHTML =
				'<div class="evo-gerbera-warn-sm"><p style="margin: 0; color: #856404;">⚠️ <strong>config.xml</strong> not found</p>' +
				'<p style="margin-top: 15px;">Create config.xml from template?</p>' +
				'<div style="text-align: center; margin-top: 15px;">' +
				'<button onclick="createConfig()" style="background: #28a745; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-weight: bold;">Yes, create</button> ' +
				'<button onclick="wizardData.needsConfig = true; showStep(3);" style="background: #6c757d; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer;">Skip</button>' +
				'</div></div>';
		}
	});
}

function createConfig() {
	document.getElementById('configFileCheck').innerHTML = '<p>Creating config.xml...</p>';
	makeAjaxCall('create_config', {basedir: wizardData.basedir}, function(err, response) {
		if (err || !response.success) {
			document.getElementById('configFileCheck').innerHTML =
				'<div class="evo-gerbera-danger"><p style="margin: 0; color: #721c24;">✗ Error creating config.xml</p></div>';
			return;
		}
		document.getElementById('configFileCheck').innerHTML =
			'<div class="evo-gerbera-success-sm"><p style="margin: 0; color: #155724;">✓ config.xml created successfully</p></div>';
		setTimeout(function() { showStep(3); }, 800);
	});
}

function createDirectories() {
	document.getElementById('step3').innerHTML =
		'<h3 style="color: var(--evo-text, #495057); margin-top: 0;">' +
		'<span style="background: #667eea; color: white; border-radius: 50%; padding: 5px 12px; margin-right: 10px;">3</span>' +
		'Directory Structure</h3><p>Creating directories...</p>';
	makeAjaxCall('create_directories', {basedir: wizardData.basedir}, function(err, response) {
		if (err || !response.success) {
			document.getElementById('step3').innerHTML +=
				'<div class="evo-gerbera-danger"><p style="margin: 0; color: #721c24;">✗ Error creating directories</p></div>';
			return;
		}
		document.getElementById('step3').innerHTML +=
			'<div class="evo-gerbera-success-sm"><p style="margin: 0; color: #155724;">✓ Directories created successfully</p></div>';
		setTimeout(function() { showStep(4); }, 1000);
	});
}

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
	var wizardVisible = document.getElementById('setupWizardModal').style.display === 'block';
	var confirmVisible = document.getElementById('wizardFooterConfirm').style.display === 'block';
	if (e.key === 'Escape' && wizardVisible) {
		if (confirmVisible) cancelCloseWizard();
		else closeSetupWizard();
	} else if (e.key === 'Enter' && wizardVisible && confirmVisible) {
		confirmCloseWizard();
	} else if (wizardVisible && !confirmVisible) {
		if (e.key === 'ArrowRight' && document.getElementById('nextBtn').style.display !== 'none') changeStep(1);
		else if (e.key === 'ArrowLeft' && document.getElementById('prevBtn').style.display !== 'none') changeStep(-1);
	}
});

window.onclick = function(event) {
	var modal = document.getElementById('setupWizardModal');
	if (event.target == modal) closeSetupWizard();
};
</script>
WIZARD_JS

	sec_end

else
	# NORMAL FORM - Shown when basedir and config.xml exist

	sec_begin "$(lang de:"Starttyp" en:"Start type")"
	cgi_print_radiogroup_service_starttype "enabled" "$GERBERA_ENABLED" "" "" 0
	sec_end

	sec_begin "$(lang de:"Basisverzeichnis" en:"Base Directory")"
	cat << EOF
<p>
<label for='basedir' title="cfg.basedir">$(lang de:"Basisverzeichnis" en:"Base Directory"): </label>
<input type='text' id='basedir' name='basedir' size='50' maxlength='255' value="$(html "$GERBERA_BASEDIR")"
       title="$(lang de:"Hauptverzeichnis fuer Gerbera. Medien, Datenbank und Konfiguration." en:"Main directory for Gerbera. Media, database and configuration.")">
</p>
EOF
	sec_end

	sec_begin "$(lang de:"Server-Einstellungen" en:"Server Settings")"
	cat << EOF
<p>
<label for='port'>$(lang de:"Port" en:"Port"): </label>
<input type='text' id='port' name='port' size='8' maxlength='8' value="$(html "$GERBERA_PORT")"
       title="$(lang de:"Port fuer die Weboberflaeche" en:"Port for the web interface")">
</p>
<p>
<label for='friendly_name'>$(lang de:"Server-Name" en:"Server name"): </label>
<input type='text' id='friendly_name' name='friendly_name' size='50' maxlength='128' value="$(html "$GERBERA_FRIENDLY_NAME")"
       title="$(lang de:"Angezeigter Name im UPnP-Netzwerk" en:"Display name in the UPnP network")">
</p>
EOF
	sec_end

	sec_begin "$(lang de:"Datenbank" en:"Database")"
	cat << EOF
<p>
<label for='db_engine'>$(lang de:"Datenbank-Engine" en:"Database engine"): </label>
<select id='db_engine' name='db_engine' title="$(lang de:"SQLite3 ist standardmaessig aktiviert und erfordert keine Konfiguration." en:"SQLite3 is enabled by default and requires no configuration.")">
	<option value="sqlite3" $(select "$VAL_DB_ENGINE" sqlite3)>SQLite3</option>
	<option value="mysql" $(select "$VAL_DB_ENGINE" mysql)>MySQL</option>
</select>
</p>
<div id="mysql_settings" style="display: $(test "$VAL_DB_ENGINE" = "mysql" && echo "block" || echo "none");">
<p><label for='db_host'>MySQL Host: </label><input type='text' id='db_host' name='db_host' size='30' maxlength='128' value="localhost"></p>
<p><label for='db_user'>MySQL User: </label><input type='text' id='db_user' name='db_user' size='20' maxlength='64' value="gerbera"></p>
<p><label for='db_pass'>MySQL Password: </label><input type='password' id='db_pass' name='db_pass' size='20' maxlength='64'></p>
<p><label for='db_name'>MySQL Database: </label><input type='text' id='db_name' name='db_name' size='20' maxlength='64' value="gerbera"></p>
</div>
<script>
document.getElementById('db_engine').addEventListener('change', function() {
	document.getElementById('mysql_settings').style.display = this.value === 'mysql' ? 'block' : 'none';
});
</script>
EOF
	sec_end

	sec_begin "$(lang de:"Import-Einstellungen" en:"Import Settings")"
	cat << EOF
<p>
<label for='follow_symlinks'>$(lang de:"Symlinks folgen" en:"Follow symlinks"): </label>
<select id='follow_symlinks' name='follow_symlinks'>
	<option value="yes" $(select "$VAL_FOLLOW_SYMLINKS" yes)>$(lang de:"Ja" en:"Yes")</option>
	<option value="no" $(select "$VAL_FOLLOW_SYMLINKS" no)>$(lang de:"Nein" en:"No")</option>
</select>
</p>
<p>
<label for='autoscan_dir'>$(lang de:"Autoscan-Verzeichnis" en:"Autoscan directory"): </label>
<input type='text' id='autoscan_dir' name='autoscan_dir' size='50' maxlength='255'
       value="$(html "${GERBERA_BASEDIR%/}/media")"
       title="$(lang de:"Verzeichnis, das automatisch auf neue Medien ueberwacht wird" en:"Directory that is automatically monitored for new media")">
</p>
<p>
<label for='magic_file'>$(lang de:"Magic-Datei" en:"Magic file"): </label>
<input type='text' id='magic_file' name='magic_file' size='50' maxlength='255' value="/usr/share/misc/magic"
       title="$(lang de:"Datei zur Typ-Erkennung (libmagic)" en:"File type detection database (libmagic)")">
</p>
EOF
	sec_end

	sec_begin "$(lang de:"Transcodierung" en:"Transcoding")"
	cat << EOF
<p>
<label for='transcoding'>$(lang de:"Transcodierung" en:"Transcoding"): </label>
<select id='transcoding' name='transcoding'>
	<option value="no" $(select "$TRANSCODING_ENABLED" no)>$(lang de:"Deaktiviert" en:"Disabled")</option>
	<option value="yes" $(select "$TRANSCODING_ENABLED" yes)>$(lang de:"Aktiviert" en:"Enabled")</option>
</select>
</p>
EOF
	sec_end

	sec_begin "$(lang de:"Web-Oberflaeche" en:"Web Interface")"
	cat << EOF
<p>
<label for='ui_accounts'>$(lang de:"Zugangskontrolle" en:"Access control"): </label>
<select id='ui_accounts' name='ui_accounts'>
	<option value="no" selected>$(lang de:"Deaktiviert" en:"Disabled")</option>
	<option value="yes">$(lang de:"Aktiviert" en:"Enabled")</option>
</select>
</p>
<div id="account_settings" style="display: none;">
<p><label for='ui_user'>$(lang de:"Benutzername" en:"Username"): </label><input type='text' id='ui_user' name='ui_user' size='20' maxlength='64' value="gerbera"></p>
<p><label for='ui_pass'>$(lang de:"Passwort" en:"Password"): </label><input type='password' id='ui_pass' name='ui_pass' size='20' maxlength='64'></p>
</div>
<script>
document.getElementById('ui_accounts').addEventListener('change', function() {
	document.getElementById('account_settings').style.display = this.value === 'yes' ? 'block' : 'none';
});
</script>
EOF
	sec_end

	sec_begin "$(lang de:"Konfigurationseditor" en:"Configuration Editor")"
	cat << 'CONFIRM_MODAL'
<div id="confirmOverlay" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 9999; align-items: center; justify-content: center;">
	<div style="background: var(--evo-surface, #fff); padding: 30px; border-radius: 10px; max-width: 400px; width: 90%; box-shadow: 0 5px 20px rgba(0,0,0,0.3); text-align: center;">
		<p id="confirmMessage" style="font-size: 16px; color: var(--evo-text, #333); margin: 0 0 20px 0;"></p>
		<button id="confirmCancel" style="background: #95a5a6; color: white; border: none; padding: 10px 24px; border-radius: 4px; cursor: pointer; font-size: 14px; margin-right: 10px;">Cancel</button>
		<button id="confirmOk" style="background: #e74c3c; color: white; border: none; padding: 10px 24px; border-radius: 4px; cursor: pointer; font-size: 14px;">OK</button>
	</div>
</div>
CONFIRM_MODAL
	cat << EOF
<p>$(lang de:"Bearbeiten Sie die config.xml direkt im ACE-Editor." en:"Edit config.xml directly with the ACE editor.")</p>
<p>
	<button type="button" onclick="loadConfigFile()" style="background: #667eea; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; margin-right: 5px;">📄 $(lang de:"Laden" en:"Load")</button>
	<button type="button" onclick="saveConfigFile()" style="background: #28a745; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; margin-right: 5px;">💾 $(lang de:"Speichern" en:"Save")</button>
	<button type="button" onclick="loadTemplate()" style="background: #ffc107; color: black; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; margin-right: 5px;">📋 $(lang de:"Template laden" en:"Load Template")</button>
	<button type="button" onclick="deleteConfig()" style="background: #dc3545; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;">🗑 $(lang de:"Loeschen" en:"Delete")</button>
</p>
<div id="editorStatus" style="padding: 8px; margin: 10px 0; border-radius: 4px; background: #e7f3ff; color: #1565c0;">$(lang de:"Bereit" en:"Ready")</div>
<div id="editor" style="height: 500px; border: 1px solid #ccc; border-radius: 4px;"></div>

<script src="/ace/ace.js"></script>
EOF

# Inline ACE XML mode + Monokai theme (ace-builds v1.23.4 src-min-noconflict)
# These are embedded inline because /usr/mww/ace/ is on read-only squashfs.
cat << 'ACE_MODE_XML_JS'
<script>
ace.define("ace/mode/xml_highlight_rules",["require","exports","module","ace/lib/oop","ace/mode/text_highlight_rules"],function(e,t,n){"use strict";var r=e("../lib/oop"),i=e("./text_highlight_rules").TextHighlightRules,s=function(e){var t="[_:a-zA-Z\u00c0-\uffff][-_:.a-zA-Z0-9\u00c0-\uffff]*";this.$rules={start:[{token:"string.cdata.xml",regex:"<\\!\\[CDATA\\[",next:"cdata"},{token:["punctuation.instruction.xml","keyword.instruction.xml"],regex:"(<\\?)("+t+")",next:"processing_instruction"},{token:"comment.start.xml",regex:"<\\!--",next:"comment"},{token:"xml-pe",regex:"<\\!(?:"+t+")",next:"doctype"},{token:["punctuation.tag.open.xml","entity.name.tag.xml"],regex:"(<)((?:"+t+":)?"+t+")",next:"tag"},{token:"punctuation.tag.close.xml",regex:"(</)((?:"+t+":)?"+t+">)",next:"tag"},{token:"text.end-tag-open.xml",regex:"</?"},{token:"entity.name.tag.xml",regex:t},{include:"reference"},{token:"text.xml",regex:"[^<&]+"},{token:"invalid.xml",regex:"<"}],processing_instruction:[{token:"punctuation.instruction.xml",regex:"\\?>",next:"start"},{token:"string.instruction.xml",regex:".+"}],doctype:[{token:"punctuation.xml",regex:">",next:"start"},{token:"xml-pe",regex:"[\\w:.-]+(?:(?!>)[^\"'>])+"},{token:"string",regex:'"[^"]*"'},{token:"string",regex:"'[^']*'"}],comment:[{token:"comment.end.xml",regex:"-->",next:"start"},{defaultToken:"comment.xml"}],cdata:[{token:"string.cdata.xml",regex:"\\]\\]>",next:"start"},{defaultToken:"string.cdata.xml"}],tag:[{token:["meta.tag.punctuation.xml","meta.tag.punctuation.xml"],regex:'(=)(")',next:"qqstring"},{token:["meta.tag.punctuation.xml","meta.tag.punctuation.xml"],regex:"(=)(')",next:"qstring"},{token:"punctuation.tag.xml",regex:"/?>",next:"start"},{token:"entity.other.attribute-name.xml",regex:t},{include:"reference"},{token:"text.tag-whitespace.xml",regex:"\\s+"},{token:"invalid.illegal.xml",regex:"[^\\s=>/<@]+"},{token:"invalid.illegal.bad-ampersand.xml",regex:"&"}],reference:[{token:"constant.character.entity.xml",regex:"(?:&#[0-9]+;)|(?:&#x[0-9a-fA-F]+;)|(?:&[a-zA-Z0-9_:\\.-]+;)"},{token:"invalid.illegal.bad-ampersand.xml",regex:"&"}],qqstring:[{token:"string.xml",regex:'"',next:"tag"},{include:"reference"},{defaultToken:"string.xml"}],qstring:[{token:"string.xml",regex:"'",next:"tag"},{include:"reference"},{defaultToken:"string.xml"}]};if(e)this.$rules=e;this.normalizeRules()};r.inherits(s,i);n.exports.XmlHighlightRules=s});ace.define("ace/mode/xml_fold_mode",["require","exports","module","ace/lib/oop","ace/mode/fold_mode","ace/range","ace/lib/xmlutil"],function(e,t,n){"use strict";var r=e("../lib/oop"),i=e("./fold_mode").FoldMode,s=e("../range").Range,o=e("../lib/xmlutil");t.XmlFoldMode=function(e){this.voidElements=e||{}};r.inherits(t.XmlFoldMode,i);(function(){this.getFoldWidget=function(e,t,n){var r=e.getLine(n);if(r.match(/<[A-Za-z\0-9]+(?:\s|>|$)/))return"start";if(r.match("<\/[A-Za-z\\0-9]+>"))return t=="markbeginend"?"end":"";else return""};this.getFoldWidgetRange=function(e,t,n){var r=this.voidElements||{};var i=e.getLine(n);if(/^<[!?]/.test(i)){var s=e.getTokens(n),a=0;for(var l=0;l<s.length;l++){var c=s[l];if(c.type.match("comment|string|processing_instruction"))a+=c.value.length;else a+=c.value.length}return this.getCommentFoldWidget(e,n,a-1)}var u=o.getParent(e,{row:n,column:i.length});if(u&&u.start&&u.end)return new s(u.start.row,u.start.column,u.end.row,u.end.column)}}).call(t.XmlFoldMode.prototype)});ace.define("ace/mode/xml",["require","exports","module","ace/lib/oop","ace/mode/text","ace/mode/xml_highlight_rules","ace/mode/xml_fold_mode","ace/lib/xmlutil"],function(e,t,n){"use strict";var r=e("../lib/oop"),i=e("./text").Mode,s=e("./xml_highlight_rules").XmlHighlightRules,o=e("./xml_fold_mode").XmlFoldMode;t.Mode=function(){this.HighlightRules=s;this.foldingRules=new o};r.inherits(t.Mode,i);(function(){this.$id="ace/mode/xml"}).call(t.Mode.prototype)});
(function() {
ace.require(["ace/mode/xml"], function(m) {
if (typeof module == "object" && typeof exports == "object" && module) {
module.exports = m;
}
});
})();
</script>
ACE_MODE_XML_JS

cat << 'ACE_THEME_MONOKAI_JS'
<script>
ace.define("ace/theme/monokai-css",["require","exports","module"],function(e,t,n){n.exports=".ace-monokai .ace_gutter {\n  background: #2F3129;\n  color: #8F908A\n}\n\n.ace-monokai .ace_print-margin {\n  width: 1px;\n  background: #555651\n}\n\n.ace-monokai {\n  background-color: #272822;\n  color: #F8F8F2\n}\n\n.ace-monokai .ace_cursor {\n  color: #F8F8F0\n}\n\n.ace-monokai .ace_marker-layer .ace_selection {\n  background: #49483E\n}\n\n.ace-monokai.ace_multiselect .ace_selection.ace_start {\n  box-shadow: 0 0 3px 0px #272822;\n}\n\n.ace-monokai .ace_marker-layer .ace_step {\n  background: rgb(102, 82, 0)\n}\n\n.ace-monokai .ace_marker-layer .ace_bracket {\n  margin: -1px 0 0 -1px;\n  border: 1px solid #49483E\n}\n\n.ace-monokai .ace_marker-layer .ace_active-line {\n  background: #202020\n}\n\n.ace-monokai .ace_gutter-active-line {\n  background-color: #272727\n}\n\n.ace-monokai .ace_marker-layer .ace_selected-word {\n  border: 1px solid #49483E\n}\n\n.ace-monokai .ace_invisible {\n  color: #52524d\n}\n\n.ace-monokai .ace_entity.ace_name.ace_tag,\n.ace-monokai .ace_keyword,\n.ace-monokai .ace_meta.ace_tag,\n.ace-monokai .ace_storage {\n  color: #F92672\n}\n\n.ace-monokai .ace_punctuation,\n.ace-monokai .ace_punctuation.ace_tag {\n  color: #fff\n}\n\n.ace-monokai .ace_constant.ace_character,\n.ace-monokai .ace_constant.ace_language,\n.ace-monokai .ace_constant.ace_numeric,\n.ace-monokai .ace_constant.ace_other {\n  color: #AE81FF\n}\n\n.ace-monokai .ace_invalid {\n  color: #F8F8F0;\n  background-color: #F92672\n}\n\n.ace-monokai .ace_invalid.ace_deprecated {\n  color: #F8F8F0;\n  background-color: #AE81FF\n}\n\n.ace-monokai .ace_support.ace_constant,\n.ace-monokai .ace_support.ace_function {\n  color: #66D9EF\n}\n\n.ace-monokai .ace_fold {\n  background-color: #A6E22E;\n  border-color: #F8F8F2\n}\n\n.ace-monokai .ace_storage.ace_type,\n.ace-monokai .ace_support.ace_class,\n.ace-monokai .ace_support.ace_type {\n  font-style: italic;\n  color: #66D9EF\n}\n\n.ace-monokai .ace_entity.ace_name.ace_function,\n.ace-monokai .ace_entity.ace_other,\n.ace-monokai .ace_entity.ace_other.ace_attribute-name,\n.ace-monokai .ace_variable {\n  color: #A6E22E\n}\n\n.ace-monokai .ace_variable.ace_parameter {\n  font-style: italic;\n  color: #FD971F\n}\n\n.ace-monokai .ace_string {\n  color: #E6DB74\n}\n\n.ace-monokai .ace_comment {\n  color: #75715E\n}\n\n.ace-monokai .ace_indent-guide {\n  background: url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAACCAYAAACZgbYnAAAAEklEQVQImWPQ0FD0ZXBzd/wPAAjVAoxeSgNeAAAAAElFTkSuQmCC) right repeat-y\n}\n\n.ace-monokai .ace_indent-guide-active {\n  background: url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAACCAYAAACZgbYnAAAAEklEQVQIW2PQ1dX9zzBz5sz/ABCcBFFentLlAAAAAElFTkSuQmCC) right repeat-y;\n}\n"}),ace.define("ace/theme/monokai",["require","exports","module","ace/theme/monokai-css","ace/lib/dom"],function(e,t,n){t.isDark=!0,t.cssClass="ace-monokai",t.cssText=e("./monokai-css");var r=e("../lib/dom");r.importCssString(t.cssText,t.cssClass,!1)});
       (function() {
                    ace.require(["ace/theme/monokai"], function(m) {
                        if (typeof module == "object" && typeof exports == "object" && module) {
                            module.exports = m;
                        }
                    });
                })();
</script>
ACE_THEME_MONOKAI_JS

	cat << EOF
<script>
// Shared AJAX helper (also defined in the wizard section above).
function makeAjaxCall(action, params, callback) {
	var url = window.location.pathname;
	var data = 'ajax=1&action=' + encodeURIComponent(action);
	for (var key in params) {
		if (params.hasOwnProperty(key))
			data += '&' + key + '=' + encodeURIComponent(params[key]);
	}
	var xhr = new XMLHttpRequest();
	xhr.open('GET', url + '?' + data, true);
	xhr.onload = function() {
		if (xhr.status === 200) {
			try {
				var text = xhr.responseText;
				var jsonStart = text.indexOf('Content-Type: application/json');
				if (jsonStart === -1) throw new Error('No JSON found');
				var jsonText = text.substring(jsonStart);
				var firstBrace = jsonText.indexOf('{');
				if (firstBrace === -1) throw new Error('No JSON object found');
				jsonText = jsonText.substring(firstBrace);
				var endPos = jsonText.indexOf('\n<');
				if (endPos > 0) jsonText = jsonText.substring(0, endPos).trim();
				var response = JSON.parse(jsonText);
				callback(null, response);
			} catch(e) {
				console.error('Parse error:', e.message);
				callback('Invalid JSON response', null);
			}
		} else {
			callback('Request failed: ' + xhr.status, null);
		}
	};
	xhr.onerror = function() { callback('Network error', null); };
	xhr.send();
}

var editor = null;
var configFilePath = '';

function initEditor() {
	if (typeof ace !== 'undefined') {
		editor = ace.edit("editor");
		ace.config.set('basePath', '/ace/');
		editor.setTheme("ace/theme/monokai");
		editor.session.setMode("ace/mode/xml");
		editor.setOptions({
			fontSize: "14px",
			showPrintMargin: false,
			enableBasicAutocompletion: true,
			enableLiveAutocompletion: true
		});
	}
}

function loadConfigFile() {
	var filePath = 'config.xml';
	var status = document.getElementById('editorStatus');
	status.textContent = 'Loading...';
	status.style.background = '#fff3cd';
	status.style.color = '#856404';

	makeAjaxCall('read_file', {file: filePath}, function(err, response) {
		if (err || !response.success) {
			status.textContent = 'Error: ' + (err || response.error || 'Failed to load');
			status.style.background = '#f8d7da';
			status.style.color = '#721c24';
			return;
		}
		configFilePath = response.file;
		if (editor) {
			editor.setValue(response.content || '', -1);
			editor.clearSelection();
		}
		status.textContent = 'Loaded: ' + configFilePath;
		status.style.background = '#d4edda';
		status.style.color = '#155724';
	});
}

function saveConfigFile() {
	if (!editor) return;
	var content = editor.getValue();
	var status = document.getElementById('editorStatus');
	status.textContent = 'Saving...';
	status.style.background = '#fff3cd';
	status.style.color = '#856404';

	makeAjaxCall('write_file', {file: 'config.xml', content: content}, function(err, response) {
		if (err || !response.success) {
			status.textContent = 'Error: ' + (err || response.error || 'Failed to save');
			status.style.background = '#f8d7da';
			status.style.color = '#721c24';
			return;
		}
		status.textContent = 'Saved successfully ✓';
		status.style.background = '#d4edda';
		status.style.color = '#155724';
		setTimeout(function() {
			status.textContent = 'Ready';
			status.style.background = '#e7f3ff';
			status.style.color = '#1565c0';
		}, 3000);
	});
}

function confirmModal(msg) {
	return new Promise(function(resolve) {
		var modal = document.getElementById('confirmOverlay');
		var msgEl = document.getElementById('confirmMessage');
		msgEl.textContent = msg;
		modal.style.display = 'flex';
		document.getElementById('confirmOk').onclick = function() {
			modal.style.display = 'none';
			resolve(true);
		};
		document.getElementById('confirmCancel').onclick = function() {
			modal.style.display = 'none';
			resolve(false);
		};
	});
}

async function loadTemplate() {
	var confirmed = await confirmModal('Load template? Current changes will be lost.');
	if (!confirmed) return;
	var status = document.getElementById('editorStatus');
	status.textContent = 'Loading template...';
	status.style.background = '#fff3cd';
	status.style.color = '#856404';

	makeAjaxCall('read_file', {file: 'config.xml.template'}, function(err, response) {
		if (err || !response.success) {
			status.textContent = 'Error: ' + (err || response.error || 'Failed to load template');
			status.style.background = '#f8d7da';
			status.style.color = '#721c24';
			return;
		}
		if (editor) {
			editor.setValue(response.content || '', -1);
			editor.clearSelection();
		}
		status.textContent = 'Template loaded';
		status.style.background = '#d4edda';
		status.style.color = '#155724';
	});
}

async function deleteConfig() {
	var confirmed = await confirmModal('Delete config.xml? A backup will be created.');
	if (!confirmed) return;
	var status = document.getElementById('editorStatus');
	makeAjaxCall('delete_config', {basedir: '$(html "$GERBERA_BASEDIR")'}, function(err, response) {
		if (err || !response.success) {
			status.textContent = 'Error: ' + (response ? response.message : 'Failed');
			status.style.background = '#f8d7da';
			status.style.color = '#721c24';
			return;
		}
		status.textContent = 'Archived: ' + response.message;
		status.style.background = '#d4edda';
		status.style.color = '#155724';
		if (editor) editor.setValue('', -1);
	});
}

setTimeout(initEditor, 500);
</script>
EOF
	sec_end

	sec_begin "$(lang de:"Setup-Assistent" en:"Setup Wizard")"
	cat << EOF
<p>
	<button type="button" onclick="openSetupWizard()" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 12px 30px; font-size: 15px; font-weight: bold; border-radius: 6px; cursor: pointer; box-shadow: 0 3px 5px rgba(0,0,0,0.2);">
		🚀 $(lang de:"Ersteinrichtungs-Assistent erneut starten" en:"Re-run Setup Wizard")
	</button>
</p>
EOF
	sec_end

	sec_begin "$(lang de:"Startprotokoll" en:"Startup Log")"
	cat << EOF
<pre style="max-height: 200px; overflow-y: auto; background: #1e1e1e; color: #d4d4d4; padding: 10px; border-radius: 4px; font-size: 11px; white-space: pre-wrap;">
EOF
	if [ -f /tmp/rc.gerbera.log ]; then
		tail -100 /tmp/rc.gerbera.log
	else
		echo "$(lang de:"Kein Protokoll vorhanden" en:"No log available")"
	fi
	cat << EOF
</pre>
EOF
	sec_end

# ============================================================================
# Shared: Wizard Modal HTML + JavaScript (available in both modes)
# ============================================================================
AUTO_STORAGE_ESC=$(html "$AUTO_STORAGE")
cat << 'WIZARD_HTML' | sed "s|__AUTO_STORAGE__|${AUTO_STORAGE_ESC}|g"
<!-- Toast Container -->
<div id="toastContainer" style="position: fixed; top: 20px; right: 20px; z-index: 9999; min-width: 300px; max-width: 400px;"></div>

<!-- Setup Wizard Modal -->
<div id="setupWizardModal" style="display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; overflow: auto; background-color: rgba(0,0,0,0.6);">
	<div id="wizardContainer" style="background-color: var(--evo-surface, #fff); margin: 3% auto; padding: 0; border-radius: 10px; width: 90%; max-width: 800px; box-shadow: 0 5px 15px rgba(0,0,0,0.3); color: var(--evo-text, #333);">

		<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px 10px 0 0;">
			<h2 style="margin: 0; color: white;">🚀 Gerbera Initial Setup</h2>
			<p style="margin: 10px 0 0 0; opacity: 0.9;" id="wizardSubtitle">Step 1 of 5</p>
		</div>

		<div style="padding: 30px;">
			<!-- Step 1: Base Directory -->
			<div class="wizard-step" id="step1">
				<h3 style="color: var(--evo-text, #495057); margin-top: 0;">
					<span style="background: #667eea; color: white; border-radius: 50%; padding: 5px 12px; margin-right: 10px;">1</span>
					Base Directory
				</h3>
				<p>Choose a directory on your USB storage or NAS where Gerbera stores its media database and configuration.</p>
				<p>
					<label for='setup_basedir'><strong>Directory path:</strong></label><br>
					<input type='text' id='setup_basedir' name='setup_basedir' size='60' maxlength='255'
					       value="__AUTO_STORAGE__" style="padding: 10px; font-size: 14px; width: 100%; box-sizing: border-box; border: 2px solid #ddd; border-radius: 4px;">
				</p>
				<div id="dirCheckResult"></div>
				<div class="evo-gerbera-info">
					<p style="margin: 0; color: #1976D2;"><strong>💡 Recommendation:</strong></p>
					<p style="margin: 5px 0 0 0; font-size: 13px; color: var(--evo-text-muted, #555);">
						Example: <code>__AUTO_STORAGE__</code><br>
						The directory should be on persistent storage (USB, NAS).
					</p>
				</div>
			</div>

			<!-- Step 2: config.xml Check -->
			<div class="wizard-step" id="step2" style="display: none;">
				<h3 style="color: var(--evo-text, #495057); margin-top: 0;">
					<span style="background: #667eea; color: white; border-radius: 50%; padding: 5px 12px; margin-right: 10px;">2</span>
					Configuration File
				</h3>
				<div id="configFileCheck">
					<p>Checking config.xml...</p>
				</div>
			</div>

			<!-- Step 3: Directory Structure -->
			<div class="wizard-step" id="step3" style="display: none;">
				<h3 style="color: var(--evo-text, #495057); margin-top: 0;">
					<span style="background: #667eea; color: white; border-radius: 50%; padding: 5px 12px; margin-right: 10px;">3</span>
					Directory Structure
				</h3>
				<p>The following directories will be created:</p>
				<ul style="line-height: 2; list-style: none; padding: 0;">
					<li class="evo-gerbera-li">📁 <strong>media/</strong> - Media files</li>
					<li class="evo-gerbera-li">📁 <strong>db/</strong> - Database backups</li>
					<li class="evo-gerbera-li">📁 <strong>log/</strong> - Log files</li>
					<li class="evo-gerbera-li">📁 <strong>import/</strong> - Import</li>
				</ul>
			</div>

			<!-- Step 4: Network -->
			<div class="wizard-step" id="step4" style="display: none;">
				<h3 style="color: var(--evo-text, #495057); margin-top: 0;">
					<span style="background: #667eea; color: white; border-radius: 50%; padding: 5px 12px; margin-right: 10px;">4</span>
					Network
				</h3>
				<p>Gerbera runs as a UPnP Media Server and communicates over the following ports:</p>
				<div class="evo-gerbera-success-light">
					<p style="margin: 0 0 10px 0;"><strong>Default ports:</strong></p>
					<ul style="list-style: none; padding: 0; margin: 0;">
						<li style="padding: 5px 0;">🌐 <strong>TCP Port 49152</strong> - Web interface</li>
						<li style="padding: 5px 0;">📡 <strong>UPnP</strong> - Automatic port selection</li>
					</ul>
				</div>
			</div>

			<!-- Step 5: Completion -->
			<div class="wizard-step" id="step5" style="display: none;">
				<h3 style="color: var(--evo-text, #495057); margin-top: 0;">
					<span style="background: #28a745; color: white; border-radius: 50%; padding: 5px 12px; margin-right: 10px;">✓</span>
					Setup Complete!
				</h3>
				<div class="evo-gerbera-success">
					<p style="margin: 0; color: #155724;">
						<strong>✓ Gerbera is ready for configuration</strong>
					</p>
				</div>
				<div style="text-align: center; margin-top: 20px;">
					<button type="button" onclick="finishWizard()" style="background: #28a745; color: white; border: none; padding: 12px 30px; border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 15px;">
						✓ Finish
					</button>
				</div>
			</div>
		</div>

		<!-- Wizard Footer -->
		<div id="wizardFooter" style="background: var(--evo-bg, #f8f9fa); padding: 15px 30px; border-radius: 0 0 10px 10px; border-top: 1px solid var(--evo-border, #dee2e6);">
			<div id="wizardFooterNormal" style="display: flex; justify-content: space-between;">
				<button type="button" onclick="closeSetupWizard()" style="background: #6c757d; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer;">
					Cancel
				</button>
				<div>
					<button type="button" id="prevBtn" onclick="changeStep(-1)" style="display: none; background: #6c757d; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; margin-right: 10px;">
						← Back
					</button>
					<button type="button" id="nextBtn" onclick="changeStep(1)" style="background: #667eea; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer;">
						Next →
					</button>
				</div>
			</div>
			<div id="wizardFooterConfirm" style="display: none; text-align: center;">
				<p style="margin: 0 0 15px 0; font-size: 15px; color: var(--evo-text, #333);">
					Do you really want to exit the wizard?
				</p>
				<button type="button" onclick="cancelCloseWizard()" style="background: #95a5a6; color: white; border: none; padding: 10px 24px; border-radius: 4px; cursor: pointer; font-size: 14px; margin-right: 10px;">
					Cancel
				</button>
				<button type="button" onclick="confirmCloseWizard()" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 10px 24px; border-radius: 4px; cursor: pointer; font-size: 14px;">
					OK
				</button>
			</div>
		</div>
	</div>
</div>
WIZARD_HTML

# Wizard JavaScript
cat << 'WIZARD_JS'
<script>
function showToast(message, type, duration) {
	if (type !== 'error') return;
	var container = document.getElementById('toastContainer');
	var toast = document.createElement('div');
	var bgColor = '#f44336';
	var icon = '✗';
	toast.style.cssText = 'background: ' + bgColor + '; color: white; padding: 16px 20px; margin-bottom: 10px; border-radius: 6px; box-shadow: 0 3px 10px rgba(0,0,0,0.3); display: flex; align-items: center; animation: slideIn 0.3s ease;';
	toast.innerHTML = '<span style="font-size: 20px; margin-right: 12px;">' + icon + '</span><span style="flex: 1;">' + message + '</span><button onclick="this.parentElement.remove()" style="background: rgba(255,255,255,0.2); border: none; color: white; padding: 4px 12px; border-radius: 4px; margin-left: 10px; cursor: pointer; font-weight: bold;">✕</button>';
	container.appendChild(toast);
}
if (!document.getElementById('toastStyles')) {
	var style = document.createElement('style');
	style.id = 'toastStyles';
	style.textContent = '@keyframes slideIn { from { transform: translateX(400px); opacity: 0; } to { transform: translateX(0); opacity: 1; } }';
	document.head.appendChild(style);
}

var currentStep = 1;
var totalSteps = 5;
var wizardData = {
	basedir: '',
	needsConfig: false
};

function openSetupWizard() {
	var basedirField = document.getElementById('basedir');
	if (basedirField && basedirField.value.trim()) {
		wizardData.basedir = basedirField.value.trim();
	}
	var setupBasedirField = document.getElementById('setup_basedir');
	if (setupBasedirField) {
		setupBasedirField.value = wizardData.basedir;
	}
	document.getElementById('setupWizardModal').style.display = 'block';
	showStep(1);
}

function closeSetupWizard() {
	document.getElementById('wizardFooterNormal').style.display = 'none';
	document.getElementById('wizardFooterConfirm').style.display = 'block';
}

function cancelCloseWizard() {
	document.getElementById('wizardFooterConfirm').style.display = 'none';
	document.getElementById('wizardFooterNormal').style.display = 'flex';
}

function confirmCloseWizard() {
	document.getElementById('setupWizardModal').style.display = 'none';
	document.getElementById('wizardFooterConfirm').style.display = 'none';
	document.getElementById('wizardFooterNormal').style.display = 'flex';
}

function finishWizard() {
	document.getElementById('setupWizardModal').style.display = 'none';
	window.location.reload();
}

function showStep(step) {
	var steps = document.getElementsByClassName('wizard-step');
	for (var i = 0; i < steps.length; i++) {
		steps[i].style.display = 'none';
	}
	document.getElementById('step' + step).style.display = 'block';
	currentStep = step;
	document.getElementById('wizardSubtitle').textContent = 'Step ' + step + ' of ' + totalSteps;
	document.getElementById('prevBtn').style.display = step === 1 ? 'none' : 'inline-block';
	document.getElementById('nextBtn').style.display = step === totalSteps ? 'none' : 'inline-block';
	if (step === 2) setTimeout(checkConfig, 300);
}

function changeStep(direction) {
	if (direction > 0) {
		if (currentStep === 1) {
			validateAndCheckBasedir();
			return;
		} else if (currentStep === 2) {
			showStep(3);
			return;
		} else if (currentStep === 3) {
			createDirectories();
			return;
		} else if (currentStep === 4) {
			showStep(5);
			return;
		}
	} else {
		if (currentStep > 1) showStep(currentStep - 1);
	}
}

function validateAndCheckBasedir() {
	var basedir = document.getElementById('setup_basedir').value.trim();
	if (!basedir) return;
	wizardData.basedir = basedir;
	document.getElementById('dirCheckResult').innerHTML = '<p>Checking directory...</p>';

	makeAjaxCall('check_directory', {basedir: basedir}, function(err, response) {
		if (err) {
			document.getElementById('dirCheckResult').innerHTML =
				'<div class="evo-gerbera-danger"><p style="margin: 0; color: #721c24;">✗ Error: ' + err + '</p></div>';
			showToast('Error checking directory', 'error', 4000);
			return;
		}
		if (response.exists) {
			document.getElementById('dirCheckResult').innerHTML =
				'<div class="evo-gerbera-success-sm"><p style="margin: 0; color: #155724;">✓ Directory exists, saving configuration...</p></div>';
			makeAjaxCall('save_basedir_only', {basedir: basedir}, function(err2, resp2) {
				if (err2 || !resp2 || !resp2.success) {
					document.getElementById('dirCheckResult').innerHTML =
						'<div class="evo-gerbera-danger"><p style="margin: 0; color: #721c24;">✗ Error saving configuration</p></div>';
					return;
				}
				document.getElementById('dirCheckResult').innerHTML =
					'<div class="evo-gerbera-success-sm"><p style="margin: 0; color: #155724;">✓ Directory exists and configuration saved</p></div>';
				setTimeout(function() { showStep(2); }, 800);
			});
		} else {
			document.getElementById('dirCheckResult').innerHTML =
				'<div class="evo-gerbera-warn-sm"><p style="margin: 0; color: #856404;">ℹ Directory does not exist</p>' +
				'<button onclick="createBasedir(\'' + basedir + '\')" style="margin-top: 10px; background: #28a745; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-weight: bold;">Create Now</button></div>';
		}
	});
}

function createBasedir(basedir) {
	document.getElementById('dirCheckResult').innerHTML = '<p>Creating directory...</p>';
	makeAjaxCall('create_directory', {basedir: basedir}, function(err, response) {
		if (err || !response.success) {
			document.getElementById('dirCheckResult').innerHTML =
				'<div class="evo-gerbera-danger"><p style="margin: 0; color: #721c24;">✗ Error creating directory</p></div>';
			return;
		}
		document.getElementById('dirCheckResult').innerHTML =
			'<div class="evo-gerbera-success-sm"><p style="margin: 0; color: #155724;">✓ Directory created, saving configuration...</p></div>';
		makeAjaxCall('save_basedir_only', {basedir: basedir}, function(err2, resp2) {
			if (err2 || !resp2 || !resp2.success) {
				document.getElementById('dirCheckResult').innerHTML =
					'<div class="evo-gerbera-danger"><p style="margin: 0; color: #721c24;">✗ Error saving configuration</p></div>';
				return;
			}
			document.getElementById('dirCheckResult').innerHTML =
				'<div class="evo-gerbera-success-sm"><p style="margin: 0; color: #155724;">✓ Directory created and configuration saved</p></div>';
			setTimeout(function() { showStep(2); }, 800);
		});
	});
}

function checkConfig() {
	document.getElementById('configFileCheck').innerHTML = '<p>Checking config.xml...</p>';
	makeAjaxCall('check_config', {basedir: wizardData.basedir}, function(err, response) {
		if (err) {
			document.getElementById('configFileCheck').innerHTML =
				'<div class="evo-gerbera-danger"><p style="margin: 0; color: #721c24;">✗ Error checking config.xml</p></div>';
			return;
		}
		wizardData.needsConfig = !response.exists;
		if (response.exists) {
			document.getElementById('configFileCheck').innerHTML =
				'<div class="evo-gerbera-success-sm"><p style="margin: 0; color: #155724;">✓ <strong>config.xml</strong> found</p></div>';
			setTimeout(function() { showStep(3); }, 800);
		} else {
			document.getElementById('configFileCheck').innerHTML =
				'<div class="evo-gerbera-warn-sm"><p style="margin: 0; color: #856404;">⚠️ <strong>config.xml</strong> not found</p>' +
				'<p style="margin-top: 15px;">Create config.xml from template?</p>' +
				'<div style="text-align: center; margin-top: 15px;">' +
				'<button onclick="createConfig()" style="background: #28a745; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-weight: bold;">Yes, create</button> ' +
				'<button onclick="wizardData.needsConfig = true; showStep(3);" style="background: #6c757d; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer;">Skip</button>' +
				'</div></div>';
		}
	});
}

function createConfig() {
	document.getElementById('configFileCheck').innerHTML = '<p>Creating config.xml...</p>';
	makeAjaxCall('create_config', {basedir: wizardData.basedir}, function(err, response) {
		if (err || !response.success) {
			document.getElementById('configFileCheck').innerHTML =
				'<div class="evo-gerbera-danger"><p style="margin: 0; color: #721c24;">✗ Error creating config.xml</p></div>';
			return;
		}
		document.getElementById('configFileCheck').innerHTML =
			'<div class="evo-gerbera-success-sm"><p style="margin: 0; color: #155724;">✓ config.xml created successfully</p></div>';
		setTimeout(function() { showStep(3); }, 800);
	});
}

function createDirectories() {
	document.getElementById('step3').innerHTML =
		'<h3 style="color: var(--evo-text, #495057); margin-top: 0;">' +
		'<span style="background: #667eea; color: white; border-radius: 50%; padding: 5px 12px; margin-right: 10px;">3</span>' +
		'Directory Structure</h3><p>Creating directories...</p>';
	makeAjaxCall('create_directories', {basedir: wizardData.basedir}, function(err, response) {
		if (err || !response.success) {
			document.getElementById('step3').innerHTML +=
				'<div class="evo-gerbera-danger"><p style="margin: 0; color: #721c24;">✗ Error creating directories</p></div>';
			return;
		}
		document.getElementById('step3').innerHTML +=
			'<div class="evo-gerbera-success-sm"><p style="margin: 0; color: #155724;">✓ Directories created successfully</p></div>';
		setTimeout(function() { showStep(4); }, 1000);
	});
}

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
	var wizardVisible = document.getElementById('setupWizardModal').style.display === 'block';
	var confirmVisible = document.getElementById('wizardFooterConfirm').style.display === 'block';
	if (e.key === 'Escape' && wizardVisible) {
		if (confirmVisible) cancelCloseWizard();
		else closeSetupWizard();
	} else if (e.key === 'Enter' && wizardVisible && confirmVisible) {
		confirmCloseWizard();
	} else if (wizardVisible && !confirmVisible) {
		if (e.key === 'ArrowRight' && document.getElementById('nextBtn').style.display !== 'none') changeStep(1);
		else if (e.key === 'ArrowLeft' && document.getElementById('prevBtn').style.display !== 'none') changeStep(-1);
	}
});

window.onclick = function(event) {
	var modal = document.getElementById('setupWizardModal');
	if (event.target == modal) closeSetupWizard();
};
</script>
WIZARD_JS

fi
