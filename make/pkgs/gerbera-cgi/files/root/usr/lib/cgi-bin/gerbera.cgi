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
			CONTENTDIR=$(cgi_param contentdir)
			ALIVE=$(cgi_param alive)
			FRIENDLY_NAME=$(cgi_param friendly_name)
			SCRIPTING=$(cgi_param scripting)
			: "${CONTENTDIR:=${BASEDIR}/media}"
			: "${ALIVE:=180}"
			: "${FRIENDLY_NAME:=Gerbera (Freetz)}"
			: "${SCRIPTING:=no}"

			if HOME="$BASEDIR" gerbera --create-advanced-config > "$CONFIG_FILE" 2>/dev/null; then
				sed -i \
				    -e "s|<name>Gerbera</name>|<name>${FRIENDLY_NAME}</name>|g" \
				    -e "s|<alive>180</alive>|<alive>${ALIVE}</alive>|g" \
				    -e "s|title=\"PC Directory\"|title=\"Fritz!BOX Filesystem\"|g" \
				    -e "s|<directory location=\"/media\" |<directory location=\"${CONTENTDIR}\" |g" \
				    -e "/<autoscan/,/<\\/autoscan>/ s|location=\"/media\"|location=\"${CONTENTDIR}\"|" \
				    -e "/<scripting>/,/<\\/scripting>/ s|<enabled>yes</enabled>|<enabled>${SCRIPTING}</enabled>|" \
				    -e "s|/etc/default\.gerbera/|${BASEDIR%/}/|g" \
				    "$CONFIG_FILE" && \
				echo '{"success": true}' || \
				echo '{"success": false, "message": "Failed to apply substitutions to config.xml"}'
			else
				echo '{"success": false, "message": "gerbera --create-advanced-config failed. Is gerbera installed?"}'
			fi
			;;

		create_directories)
			if mkdir -p "$BASEDIR/media" "$BASEDIR/db" "$BASEDIR/log" "$BASEDIR/import" "$BASEDIR/js" 2>/dev/null; then
				chmod 777 "$BASEDIR" "$BASEDIR/media" "$BASEDIR/db" "$BASEDIR/log" "$BASEDIR/import" "$BASEDIR/js" 2>/dev/null
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

			if [ ! -f "$FILE_PATH" ]; then
				echo "{\"error\": \"File not found: $FILE_PATH\", \"content\": \"\"}"
			elif [ ! -r "$FILE_PATH" ]; then
				echo "{\"error\": \"Permission denied: cannot read $FILE_PATH\"}"
			else
				CONTENT=$(cat "$FILE_PATH")
				CONTENT=$(echo "$CONTENT" | sed 's/\\/\\\\/g; s/"/\\"/g; s/	/\\t/g' | awk '{printf "%s\\n", $0}' | sed '$ s/\\n$//')
				echo "{\"success\": true, \"file\": \"$FILE_PATH\", \"content\": \"$CONTENT\"}"
			fi
			;;

		write_file)
			# write_file_chunk is the chunked replacement used by JS.
			# This legacy action is kept for compatibility but rarely triggered
			# since config.xml is too large for a single GET URL.
			FILE_PATH=$(cgi_param file)
			CONTENT=$(cgi_param content)

			case "$FILE_PATH" in
				config.xml)
					[ -r /mod/etc/conf/gerbera.cfg ] && . /mod/etc/conf/gerbera.cfg
					BASEDIR="${GERBERA_BASEDIR%/}"
					if [ -z "$BASEDIR" ]; then
						echo '{"error": "GERBERA_BASEDIR not configured"}'
						FILE_PATH=""
					else
						FILE_PATH="$BASEDIR/config.xml"
					fi
					;;
			esac

			[ -z "$FILE_PATH" ] && echo '{"error": "No file path"}' || {

			case "$FILE_PATH" in
				*../*|*/../*|../*) echo '{"error": "Directory traversal not allowed"}' ;;
				*)
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
							[ "$FILE_PATH" = "${GERBERA_BASEDIR%/}/config.xml" ] && ALLOWED=1
							;;
					esac
					if [ "$ALLOWED" = "0" ]; then
						echo "{\"error\": \"Access denied: $FILE_PATH\"}"
					elif [ -n "$CONTENT" ]; then
						if [ -f "$FILE_PATH" ]; then
							mv "$FILE_PATH" "${FILE_PATH}.$(date +%Y-%m-%d-%H-%M-%S)" 2>/dev/null
						fi
						echo "$CONTENT" > "$FILE_PATH" && \
							echo "{\"success\": true}" || \
							echo "{\"error\": \"Failed to write\"}"
					else
						echo '{"error": "No content provided"}'
					fi
					;;
			esac
			}
			;;

		write_file_chunk)
			# Chunked file upload: sends the file in small GET-safe pieces.
			# chunk_index=0 → create/truncate temp file
			# chunk_index>0 → append
			# is_last=1     → move temp file to destination (with backup)
			WRITE_ID=$(cgi_param write_id)
			CHUNK_INDEX=$(cgi_param chunk_index)
			CHUNK_DATA=$(cgi_param chunk_data)
			IS_LAST=$(cgi_param is_last)
			FILE_KEY=$(cgi_param file)

			# Validate write_id (alphanumeric + underscore only)
			case "$WRITE_ID" in
				*[!a-zA-Z0-9_]*|'')
					echo '{"error": "Invalid write_id"}'
					;;
				*)
					TMPFILE="/tmp/gerbera_chunk_${WRITE_ID}.tmp"

					if [ "$CHUNK_INDEX" = "0" ]; then
						printf '%s' "$CHUNK_DATA" > "$TMPFILE" 2>/dev/null
					else
						printf '%s' "$CHUNK_DATA" >> "$TMPFILE" 2>/dev/null
					fi

					if [ "$IS_LAST" = "1" ]; then
						# Resolve destination
						case "$FILE_KEY" in
							config.xml)
								[ -r /mod/etc/conf/gerbera.cfg ] && . /mod/etc/conf/gerbera.cfg
								FILE_PATH="${GERBERA_BASEDIR%/}/config.xml"
								;;
							*) FILE_PATH="$FILE_KEY" ;;
						esac

						# Security: whitelist check
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
								[ "$FILE_PATH" = "${GERBERA_BASEDIR%/}/config.xml" ] && ALLOWED=1
								;;
						esac

						if [ "$ALLOWED" = "0" ]; then
							rm -f "$TMPFILE"
							echo "{\"error\": \"Access denied\"}"
						elif [ ! -f "$TMPFILE" ]; then
							echo '{"error": "Temp file missing"}'
						else
							if [ -f "$FILE_PATH" ]; then
								TIMESTAMP=$(date +%Y-%m-%d-%H-%M-%S)
								mv "$FILE_PATH" "${FILE_PATH}.${TIMESTAMP}" 2>/dev/null
							fi
							if mv "$TMPFILE" "$FILE_PATH" 2>/dev/null; then
								chmod 664 "$FILE_PATH" 2>/dev/null
								echo "{\"success\": true, \"file\": \"$FILE_PATH\"}"
							else
								echo '{"error": "Failed to finalize file"}'
							fi
						fi
					else
						echo "{\"success\": true, \"chunk\": $CHUNK_INDEX}"
					fi
					;;
			esac
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
			ALIVE=$(cgi_param alive)
			SCRIPTING=$(cgi_param scripting)
			: "${ALIVE:=180}"
			: "${SCRIPTING:=no}"
			if [ -f /mod/etc/conf/gerbera.cfg ]; then
				sed -i "s|^export GERBERA_BASEDIR=.*|export GERBERA_BASEDIR='$BASEDIR'|" /mod/etc/conf/gerbera.cfg
				sed -i "s|^export GERBERA_ENABLED=.*|export GERBERA_ENABLED='no'|" /mod/etc/conf/gerbera.cfg
				sed -i "s|^export GERBERA_ALIVE=.*|export GERBERA_ALIVE='$ALIVE'|" /mod/etc/conf/gerbera.cfg
				sed -i "s|^export GERBERA_SCRIPTING=.*|export GERBERA_SCRIPTING='$SCRIPTING'|" /mod/etc/conf/gerbera.cfg
				grep -q "^export GERBERA_BASEDIR=" /mod/etc/conf/gerbera.cfg || echo "export GERBERA_BASEDIR='$BASEDIR'" >> /mod/etc/conf/gerbera.cfg
				grep -q "^export GERBERA_ENABLED=" /mod/etc/conf/gerbera.cfg || echo "export GERBERA_ENABLED='no'" >> /mod/etc/conf/gerbera.cfg
				grep -q "^export GERBERA_ALIVE=" /mod/etc/conf/gerbera.cfg || echo "export GERBERA_ALIVE='$ALIVE'" >> /mod/etc/conf/gerbera.cfg
				grep -q "^export GERBERA_SCRIPTING=" /mod/etc/conf/gerbera.cfg || echo "export GERBERA_SCRIPTING='$SCRIPTING'" >> /mod/etc/conf/gerbera.cfg
			else
				echo "export GERBERA_BASEDIR='$BASEDIR'" > /mod/etc/conf/gerbera.cfg
				echo "export GERBERA_ENABLED='no'" >> /mod/etc/conf/gerbera.cfg
				echo "export GERBERA_ALIVE='$ALIVE'" >> /mod/etc/conf/gerbera.cfg
				echo "export GERBERA_SCRIPTING='$SCRIPTING'" >> /mod/etc/conf/gerbera.cfg
			fi
			modsave flash >> /tmp/gerbera_ajax.log 2>&1
			echo '{"success": true}'
			;;

		start_service)
			ALIVE=$(cgi_param alive)
			SCRIPTING=$(cgi_param scripting)
			: "${ALIVE:=180}"
			: "${SCRIPTING:=no}"
			if [ -f /mod/etc/conf/gerbera.cfg ]; then
				sed -i "s|^export GERBERA_BASEDIR=.*|export GERBERA_BASEDIR='$BASEDIR'|" /mod/etc/conf/gerbera.cfg
				sed -i "s|^export GERBERA_ENABLED=.*|export GERBERA_ENABLED='yes'|" /mod/etc/conf/gerbera.cfg
				sed -i "s|^export GERBERA_ALIVE=.*|export GERBERA_ALIVE='$ALIVE'|" /mod/etc/conf/gerbera.cfg
				sed -i "s|^export GERBERA_SCRIPTING=.*|export GERBERA_SCRIPTING='$SCRIPTING'|" /mod/etc/conf/gerbera.cfg
				grep -q "^export GERBERA_ENABLED=" /mod/etc/conf/gerbera.cfg || echo "export GERBERA_ENABLED='yes'" >> /mod/etc/conf/gerbera.cfg
				grep -q "^export GERBERA_ALIVE=" /mod/etc/conf/gerbera.cfg || echo "export GERBERA_ALIVE='$ALIVE'" >> /mod/etc/conf/gerbera.cfg
				grep -q "^export GERBERA_SCRIPTING=" /mod/etc/conf/gerbera.cfg || echo "export GERBERA_SCRIPTING='$SCRIPTING'" >> /mod/etc/conf/gerbera.cfg
			else
				echo "export GERBERA_BASEDIR='$BASEDIR'" > /mod/etc/conf/gerbera.cfg
				echo "export GERBERA_ENABLED='yes'" >> /mod/etc/conf/gerbera.cfg
				echo "export GERBERA_ALIVE='$ALIVE'" >> /mod/etc/conf/gerbera.cfg
				echo "export GERBERA_SCRIPTING='$SCRIPTING'" >> /mod/etc/conf/gerbera.cfg
			fi
			modsave flash >> /tmp/gerbera_ajax.log 2>&1
			LOG_FILE="/tmp/rc.gerbera.log"
			echo "$(date): Starting Gerbera (via CGI start_service)..." >> "$LOG_FILE"
			if [ -x /mod/etc/init.d/rc.gerbera ]; then
				START_OUTPUT=$(/mod/etc/init.d/rc.gerbera start 2>&1)
			elif [ -x /etc/init.d/rc.gerbera ]; then
				START_OUTPUT=$(/etc/init.d/rc.gerbera start 2>&1)
			else
				START_OUTPUT=""
			fi
			START_EXIT=$?
			echo "$(date): rc.gerbera start exit=$START_EXIT: $START_OUTPUT" >> "$LOG_FILE"
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
				PORT=$(sed -n 's|.*<port>\([^<]*\)</port>.*|\1|p' "$CONFIG_FILE" 2>/dev/null | head -1)
				: "${PORT:=49152}"
			fi
			echo "{\"port\": \"$PORT\"}"
			;;

		reset_db)
			: "${BASEDIR:=/tmp/flash/gerbera}"
			CONFIG_FILE="$BASEDIR/config.xml"
			DB_FILE="${BASEDIR%/}/gerbera.db"
			OUTPUT=""

			if [ -x /mod/etc/init.d/rc.gerbera ]; then
				OUTPUT=$(/mod/etc/init.d/rc.gerbera stop 2>&1)
			elif [ -x /etc/init.d/rc.gerbera ]; then
				OUTPUT=$(/etc/init.d/rc.gerbera stop 2>&1)
			else
				OUTPUT="rc.gerbera not found"
			fi

			if [ -f "$DB_FILE" ]; then
				TIMESTAMP=$(date +%Y-%m-%d-%H-%M-%S)
				mv "$DB_FILE" "${DB_FILE}.${TIMESTAMP}" 2>/dev/null
				OUTPUT="${OUTPUT} | Backed up gerbera.db as gerbera.db.${TIMESTAMP}"
			fi
			rm -f "${BASEDIR%/}/gerbera.db-shm" "${BASEDIR%/}/gerbera.db-wal" 2>/dev/null

			if [ -x /mod/etc/init.d/rc.gerbera ]; then
				START_OUT=$(/mod/etc/init.d/rc.gerbera start 2>&1)
			elif [ -x /etc/init.d/rc.gerbera ]; then
				START_OUT=$(/etc/init.d/rc.gerbera start 2>&1)
			else
				START_OUT=""
			fi
			START_EXIT=$?

			ESCAPED_OUTPUT=$(echo "$OUTPUT | $START_OUT" | sed 's/"/\\"/g' | tr '\n' ' ')
			if [ $START_EXIT -eq 0 ]; then
				echo "{\"success\": true, \"message\": \"$ESCAPED_OUTPUT\"}"
			else
				echo "{\"success\": false, \"message\": \"Exit code $START_EXIT: $ESCAPED_OUTPUT\"}"
			fi
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
				CONTENTDIR=$(cgi_param contentdir)
				ALIVE=$(cgi_param alive)
				SCRIPTING=$(cgi_param scripting)
				: "${CONTENTDIR:=${BASEDIR}/media}"
				: "${ALIVE:=180}"
				: "${SCRIPTING:=no}"
				if HOME="$BASEDIR" gerbera --create-advanced-config > "$CONFIG_FILE" 2>/dev/null; then
					sed -i \
					    -e "s|<name>Gerbera</name>|<name>Gerbera (Freetz)</name>|g" \
					    -e "s|title=\"PC Directory\"|title=\"Fritz|BOX Filesystem\"|g" \
					    -e "s|<alive>180</alive>|<alive>${ALIVE}</alive>|g" \
					    -e "s|<directory location=\"/media\" |<directory location=\"${CONTENTDIR}\" |g" \
					    -e "/<autoscan/,/<\\/autoscan>/ s|location=\"/media\"|location=\"${CONTENTDIR}\"|" \
					    -e "/<scripting>/,/<\\/scripting>/ s|<enabled>yes</enabled>|<enabled>${SCRIPTING}</enabled>|" \
					    -e "s|/etc/default\.gerbera/|${BASEDIR%/}/|g" \
					    "$CONFIG_FILE"
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
: "${GERBERA_ALIVE:=180}"
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
	val=$(sed -n "s|.*<$xpath>\([^<]*\)</$xpath>.*|\1|p" "$config_file" 2>/dev/null | head -1)
	echo "${val:-$default}"
}

# Read values from config.xml
CONFIG_FILE="${GERBERA_BASEDIR%/}/config.xml"
VAL_FRIENDLY_NAME=$(get_config_value "$CONFIG_FILE" "name" "$GERBERA_FRIENDLY_NAME")
VAL_PORT=$(get_config_value "$CONFIG_FILE" "port" "$GERBERA_PORT")
VAL_DB_ENGINE=$(get_config_value "$CONFIG_FILE" "engine" "sqlite3")
VAL_FOLLOW_SYMLINKS=$(get_config_value "$CONFIG_FILE" "follow-symlinks" "yes")
VAL_ALIVE=$(get_config_value "$CONFIG_FILE" "alive" "$GERBERA_ALIVE")
TRANSCODING_ENABLED=$(sed -n '/<transcoding>/,/<\/transcoding>/p' "$CONFIG_FILE" 2>/dev/null | sed -n 's|.*<enabled>\([^<]*\)</enabled>.*|\1|p' | head -1 || echo "no")
VAL_SCRIPTING=$(sed -n '/<scripting>/,/<\/scripting>/p' "$CONFIG_FILE" 2>/dev/null | sed -n 's|.*<enabled>\([^<]*\)</enabled>.*|\1|p' | head -1 || echo "no")

# Get import directory (first <directory> inside <import>, excluding autoscan)
get_import_directory() {
	local config_file="$1"
	local default="$2"
	[ ! -f "$config_file" ] && echo "$default" && return
	local val
	val=$(sed -n '/<import>/,/<\/import>/p' "$config_file" 2>/dev/null | \
	      sed '/<autoscan>/,/<\/autoscan>/d' | \
	      sed -n 's|.*directory location="\([^"]*\)".*|\1|p' | head -1)
	echo "${val:-$default}"
}

# Get autoscan directory from config.xml
get_autoscan_directory() {
	local config_file="$1"
	local default="$2"
	[ ! -f "$config_file" ] && echo "$default" && return
	local val
	val=$(sed -n '/<autoscan/,/<\/autoscan>/p' "$config_file" 2>/dev/null | \
	      sed -n 's|.*directory location="\([^"]*\)".*|\1|p' | head -1)
	echo "${val:-$default}"
}

# Get magic-file path from config.xml
get_magic_file_value() {
	local config_file="$1"
	local default="$2"
	[ ! -f "$config_file" ] && echo "$default" && return
	local val
	val=$(sed -n 's|.*<magic-file>\([^<]*\)</magic-file>.*|\1|p' "$config_file" 2>/dev/null | head -1)
	echo "${val:-$default}"
}

VAL_IMPORT_DIR=$(get_import_directory "$CONFIG_FILE" "${GERBERA_BASEDIR%/}/media")
VAL_AUTOSCAN_DIR=$(get_autoscan_directory "$CONFIG_FILE" "${GERBERA_BASEDIR%/}/media")
VAL_MAGIC_FILE=$(get_magic_file_value "$CONFIG_FILE" "/usr/share/misc/magic")

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

		<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px 10px 0 0; position: relative;">
			<h2 style="margin: 0; color: white;">🚀 Gerbera Initial Setup</h2>
			<p style="margin: 10px 0 0 0; opacity: 0.9;" id="wizardSubtitle">Step 1 of 5</p>
			<button type="button" onclick="confirmCloseWizard()" style="position: absolute; top: 10px; right: 15px; background: transparent; border: none; color: white; font-size: 28px; cursor: pointer; opacity: 0.7;" title="Close wizard">&times;</button>
		</div>

		<div style="padding: 30px;">
			<!-- Step 1: Base Directory, Content Directory, Server Name & Alive Interval -->
			<div class="wizard-step" id="step1">
				<h3 style="color: var(--evo-text, #495057); margin-top: 0;">
					<span style="background: #667eea; color: white; border-radius: 50%; padding: 5px 12px; margin-right: 10px;">1</span>
					Base Directory &amp; Content
				</h3>
				<p>Choose the base directory for Gerbera and the directory where your media files are stored.</p>
				<p>
					<label for='setup_basedir'><strong>Base directory:</strong></label><br>
					<input type='text' id='setup_basedir' name='setup_basedir' size='60' maxlength='255'
					       value="__AUTO_STORAGE__" style="padding: 10px; font-size: 14px; width: 100%; box-sizing: border-box; border: 2px solid #ddd; border-radius: 4px;">
				</p>
				<div id="dirCheckResult"></div>
				<p>
					<label for='setup_contentdir'><strong>Content directory (media files):</strong></label><br>
					<input type='text' id='setup_contentdir' name='setup_contentdir' size='60' maxlength='255'
					       value="__AUTO_STORAGE__/media" style="padding: 10px; font-size: 14px; width: 100%; box-sizing: border-box; border: 2px solid #ddd; border-radius: 4px;">
				</p>
				<p>
					<label for='setup_friendly_name'><strong>Server name (UPnP friendly name):</strong></label><br>
					<input type='text' id='setup_friendly_name' name='setup_friendly_name' size='60' maxlength='128'
					       value="Gerbera (Freetz)" style="padding: 10px; font-size: 14px; width: 100%; box-sizing: border-box; border: 2px solid #ddd; border-radius: 4px;">
				</p>
				<p>
					<label for='setup_alive'><strong>Announcement interval (alive, seconds, min 62):</strong></label><br>
					<input type='number' id='setup_alive' name='setup_alive' min='62' value='180'
					       style="padding: 10px; font-size: 14px; width: 120px; box-sizing: border-box; border: 2px solid #ddd; border-radius: 4px;">
				</p>
				<p>
					<label for='setup_scripting'><strong>JavaScript scripting:</strong></label><br>
					<select id='setup_scripting' name='setup_scripting'
						style="padding: 10px; font-size: 14px; width: 140px; box-sizing: border-box; border: 2px solid #ddd; border-radius: 4px;">
						<option value="no" selected>Disabled</option>
						<option value="yes">Enabled</option>
					</select>
				</p>
				<div class="evo-gerbera-info">
					<p style="margin: 0; color: #1976D2;"><strong>💡 Recommendations:</strong></p>
					<p style="margin: 5px 0 0 0; font-size: 13px; color: var(--evo-text-muted, #555);">
						Base directory example: <code>__AUTO_STORAGE__</code><br>
						Content directory (default): <code>__AUTO_STORAGE__/media</code><br>
						The base directory should be on persistent storage (USB, NAS).
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
					<li class="evo-gerbera-li">📁 <strong>js/</strong> - Javascript</li>
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
	contentdir: '',
	friendly_name: 'Gerbera (Freetz)',
	alive: '180',
	scripting: 'no',
	needsConfig: false
};

function openSetupWizard() {
	var initialBasedirField = document.getElementById('basedir_initial');
	if (initialBasedirField && initialBasedirField.value.trim()) {
		wizardData.basedir = initialBasedirField.value.trim();
		wizardData.contentdir = wizardData.basedir + '/media';
	}
	var setupBasedirField = document.getElementById('setup_basedir');
	if (setupBasedirField) {
		setupBasedirField.value = wizardData.basedir;
	}
	var setupContentdirField = document.getElementById('setup_contentdir');
	if (setupContentdirField && !setupContentdirField.value.trim()) {
		setupContentdirField.value = wizardData.contentdir;
	}
	document.getElementById('setupWizardModal').style.display = 'block';
	showStep(1);
}

// Auto-fill content directory when base directory changes
document.addEventListener('input', function(e) {
	if (e.target && e.target.id === 'setup_basedir') {
		var contentdirField = document.getElementById('setup_contentdir');
		if (contentdirField) {
			var currentBasedir = e.target.value.replace(/\/+$/, '');
			var prevBasedir = wizardData.basedir ? wizardData.basedir.replace(/\/+$/, '') : '';
			if (contentdirField.value === prevBasedir + '/media' || contentdirField.value === '') {
				contentdirField.value = currentBasedir + '/media';
			}
		}
	}
});

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
	var contentdir = document.getElementById('setup_contentdir').value.trim();
	var friendly_name = document.getElementById('setup_friendly_name').value.trim();
	var alive = document.getElementById('setup_alive').value.trim();
	if (!basedir) return;
	if (!contentdir) contentdir = basedir + '/media';
	if (!friendly_name) friendly_name = 'Gerbera (Freetz)';
	if (!alive || parseInt(alive) < 62) alive = '180';
	wizardData.basedir = basedir;
	wizardData.contentdir = contentdir;
	wizardData.friendly_name = friendly_name;
	wizardData.alive = alive;
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
	var contentdir = document.getElementById('setup_contentdir').value.trim();
	var friendly_name = document.getElementById('setup_friendly_name').value.trim();
	var alive = document.getElementById('setup_alive').value.trim();
	if (!contentdir) contentdir = basedir + '/media';
	if (!friendly_name) friendly_name = 'Gerbera (Freetz)';
	if (!alive || parseInt(alive) < 62) alive = '180';
	wizardData.contentdir = contentdir;
	wizardData.friendly_name = friendly_name;
	wizardData.alive = alive;
	document.getElementById('dirCheckResult').innerHTML = '<p>Creating directory...</p>';
	makeAjaxCall('create_directory', {basedir: basedir}, function(err, response) {
		if (err || !response.success) {
			document.getElementById('dirCheckResult').innerHTML =
				'<div class="evo-gerbera-danger"><p style="margin: 0; color: #721c24;">✗ Error creating directory</p></div>';
			return;
		}
		document.getElementById('dirCheckResult').innerHTML =
			'<div class="evo-gerbera-success-sm"><p style="margin: 0; color: #155724;">✓ Directory created, saving configuration...</p></div>';
		makeAjaxCall('save_basedir_only', {basedir: basedir, alive: alive}, function(err2, resp2) {
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
				'<p style="margin-top: 15px;">Generate config.xml with gerbera --create-advanced-config?</p>' +
				'<div style="text-align: center; margin-top: 15px;">' +
				'<button onclick="createConfig()" style="background: #28a745; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-weight: bold;">Yes, generate</button> ' +
				'<button onclick="wizardData.needsConfig = true; showStep(3);" style="background: #6c757d; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer;">Skip</button>' +
				'</div></div>';
		}
	});
}

function createConfig() {
	document.getElementById('configFileCheck').innerHTML = '<p>Creating config.xml...</p>';
	makeAjaxCall('create_config', {
		basedir: wizardData.basedir,
		contentdir: wizardData.contentdir,
		friendly_name: wizardData.friendly_name,
		alive: wizardData.alive,
		scripting: wizardData.scripting
	}, function(err, response) {
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
<input type='text' id='port' name='port' size='8' maxlength='8' value="$(html "$VAL_PORT")"
       title="$(lang de:"Port fuer die Weboberflaeche" en:"Port for the web interface")">
</p>
<p>
<label for='friendly_name'>$(lang de:"Server-Name" en:"Server name"): </label>
<input type='text' id='friendly_name' name='friendly_name' size='50' maxlength='128' value="$(html "$VAL_FRIENDLY_NAME")"
       title="$(lang de:"Angezeigter Name im UPnP-Netzwerk" en:"Display name in the UPnP network")">
</p>
<p>
<label for='alive'>$(lang de:"Alive-Intervall" en:"Alive interval"): </label>
<input type='text' id='alive' name='alive' size='8' maxlength='8' value="$(html "$VAL_ALIVE")"
       title="$(lang de:"SSDP-Ankündigungsintervall in Sekunden (min 62)" en:"SSDP announcement interval in seconds (min 62)")">
</p>
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
       value="$(html "$VAL_AUTOSCAN_DIR")"
       title="$(lang de:"Verzeichnis, das automatisch auf neue Medien ueberwacht wird" en:"Directory that is automatically monitored for new media")">
</p>
<p>
<label for='scripting'>$(lang de:"JavaScript-Scripting" en:"JavaScript scripting"): </label>
<select id='scripting' name='scripting'>
	<option value="no" $(select "$VAL_SCRIPTING" no)>$(lang de:"Deaktiviert" en:"Disabled")</option>
	<option value="yes" $(select "$VAL_SCRIPTING" yes)>$(lang de:"Aktiviert" en:"Enabled")</option>
</select>
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
		<button type="button" id="confirmCancel" style="background: #95a5a6; color: white; border: none; padding: 10px 24px; border-radius: 4px; cursor: pointer; font-size: 14px; margin-right: 10px;">Cancel</button>
		<button type="button" id="confirmOk" style="background: #e74c3c; color: white; border: none; padding: 10px 24px; border-radius: 4px; cursor: pointer; font-size: 14px;">OK</button>
	</div>
</div>
CONFIRM_MODAL
	cat << EOF
<p>$(lang de:"Bearbeiten Sie die config.xml direkt im ACE-Editor." en:"Edit config.xml directly with the ACE editor.")</p>
<p style="font-size: 12px; color: #666; word-break: break-all;">
	<code>$(html "${GERBERA_BASEDIR%/}")/config.xml</code>
</p>
<p>
	<button type="button" onclick="loadConfigFile()" style="background: #667eea; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; margin-right: 5px;">📄 $(lang de:"Laden" en:"Load")</button>
	<button type="button" onclick="saveConfigFile()" style="background: #28a745; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; margin-right: 5px;">💾 $(lang de:"Speichern" en:"Save")</button>
	<button type="button" onclick="findInEditor()" style="background: #ff9800; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; margin-right: 5px;">🔍 $(lang de:"Suchen" en:"Find")</button>
	<button type="button" onclick="deleteConfig()" style="background: #dc3545; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;">🗑 $(lang de:"Loeschen" en:"Delete")</button>
</p>
<div id="editorStatus" style="padding: 8px; margin: 10px 0; border-radius: 4px; background: #e7f3ff; color: #1565c0;">$(lang de:"Bereit" en:"Ready")</div>
<div id="editorSearchBar" style="display: none; background: #2d2d2d; padding: 6px 8px; border: 1px solid #555; border-bottom: none; border-radius: 4px 4px 0 0; font-size: 12px;">
	<input type="text" id="editorSearchInput" placeholder="Find..." style="width: 160px; padding: 4px 6px; background: #1e1e1e; color: #d4d4d4; border: 1px solid #555; border-radius: 3px;">
	<button type="button" onclick="editorFindNext()" style="background: #444; color: #fff; border: 1px solid #555; padding: 4px 8px; margin: 0 2px; border-radius: 3px; cursor: pointer;" title="Find next (Enter)">&#9660;</button>
	<button type="button" onclick="editorFindPrev()" style="background: #444; color: #fff; border: 1px solid #555; padding: 4px 8px; margin: 0 2px; border-radius: 3px; cursor: pointer;" title="Find previous (Shift+Enter)">&#9650;</button>
	<input type="text" id="editorReplaceInput" placeholder="Replace..." style="width: 160px; padding: 4px 6px; background: #1e1e1e; color: #d4d4d4; border: 1px solid #555; border-radius: 3px; margin-left: 8px;">
	<button type="button" onclick="editorReplaceOne()" style="background: #444; color: #fff; border: 1px solid #555; padding: 4px 8px; margin: 0 2px; border-radius: 3px; cursor: pointer;">Rpl</button>
	<button type="button" onclick="editorReplaceAll()" style="background: #444; color: #fff; border: 1px solid #555; padding: 4px 8px; margin: 0 2px; border-radius: 3px; cursor: pointer;">Rpl All</button>
	<button type="button" onclick="document.getElementById('editorSearchBar').style.display='none'; editor.focus();" style="background: #444; color: #fff; border: 1px solid #555; padding: 4px 8px; margin: 0 2px; border-radius: 3px; cursor: pointer;">&#10005;</button>
	<span id="editorSearchStatus" style="color: #888; margin-left: 10px;"></span>
</div>
<div id="editor" style="height: 500px; border: 1px solid #ccc; border-radius: 0 0 4px 4px;"></div>

<script src="/ace/ace.js"></script>
EOF



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

// NOTE: The FritzBox web server does not invoke CGI for POST requests
// (neither XHR POST nor form POST — the modconf framework intercepts POST
// to /cgi-bin/conf/*). So we use chunked GET for file saving.

var editor = null;
var configFilePath = '';

function initEditor() {
	if (typeof ace !== 'undefined') {
		editor = ace.edit("editor");
		ace.config.set('basePath', '/ace/');
		// Set theme and mode - ACE will load them from the server
		editor.setTheme("ace/theme/monokai");
		editor.session.setMode("ace/mode/xml");
		editor.setOptions({
			fontSize: "14px",
			showPrintMargin: false,
			showGutter: true,
			wrap: true,
			indentedSoftWrap: false
		});
		// Override find command: ext-searchbox not available on server
		editor.commands.addCommand({
			name: "find",
			bindKey: {win: "Ctrl-F", mac: "Command-F"},
			exec: function() {
				findInEditor();
			}
		});
		editor.commands.addCommand({
			name: "replace",
			bindKey: {win: "Ctrl-H", mac: "Command-Option-F"},
			exec: function() {
				findInEditor();
			}
		});
		// Keyboard shortcuts for search bar
		document.addEventListener('keydown', function(e) {
			var searchBar = document.getElementById('editorSearchBar');
			if (searchBar.style.display !== 'block') return;
			if (e.target.id === 'editorSearchInput' || e.target.id === 'editorReplaceInput') {
				if (e.key === 'Enter' && !e.shiftKey) {
					e.preventDefault();
					if (e.target.id === 'editorReplaceInput') {
						editorReplaceOne();
					} else {
						editorFindNext();
					}
				} else if (e.key === 'Enter' && e.shiftKey) {
					e.preventDefault();
					editorFindPrev();
				} else if (e.key === 'Escape') {
					searchBar.style.display = 'none';
					editor.focus();
				} else if (e.key === 'Tab' && !e.shiftKey) {
					e.preventDefault();
					if (e.target.id === 'editorSearchInput') {
						document.getElementById('editorReplaceInput').focus();
						document.getElementById('editorReplaceInput').select();
					} else {
						document.getElementById('editorSearchInput').focus();
						document.getElementById('editorSearchInput').select();
					}
				}
			}
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

	// Chunked upload via GET (the only method the FritzBox web server supports
	// for invoking our CGI — both XHR POST and form POST are intercepted).
	var CHUNK = 1500;
	var chunks = [];
	for (var i = 0; i < content.length; i += CHUNK) {
		chunks.push(content.substring(i, i + CHUNK));
	}
	if (chunks.length === 0) chunks = [''];

	var writeId = 'w' + Date.now();
	var total = chunks.length;

	var sendChunk = function(idx) {
		status.textContent = 'Saving ' + (idx + 1) + '/' + total + '...';
		var isLast = (idx === total - 1) ? '1' : '0';
		makeAjaxCall('write_file_chunk', {
			write_id: writeId,
			chunk_index: String(idx),
			chunk_data: chunks[idx],
			is_last: isLast,
			file: 'config.xml'
		}, function(err, response) {
			if (err || !response.success) {
				status.textContent = 'Error: ' + (err || response.error || 'Save failed');
				status.style.background = '#f8d7da';
				status.style.color = '#721c24';
				return;
			}
			if (isLast === '1') {
				status.textContent = 'Saved successfully ✓';
				status.style.background = '#d4edda';
				status.style.color = '#155724';
				setTimeout(function() {
					status.textContent = 'Ready';
					status.style.background = '#e7f3ff';
					status.style.color = '#1565c0';
				}, 3000);
			} else {
				// Send next chunk sequentially
				sendChunk(idx + 1);
			}
		});
	};

	// Start sequential upload from chunk 0
	sendChunk(0);
}

function findInEditor() {
	if (!editor) return;
	var bar = document.getElementById('editorSearchBar');
	bar.style.display = 'block';
	var input = document.getElementById('editorSearchInput');
	input.focus();
	input.select();
	editorFindNext();
}

function editorFindNext() {
	if (!editor) return;
	var term = document.getElementById('editorSearchInput').value;
	if (term && term.length > 0) {
		var found = editor.find(term, {
			wrap: true,
			caseSensitive: false,
			wholeWord: false,
			regExp: false,
			backwards: false
		});
		document.getElementById('editorSearchStatus').textContent = found ? '' : 'Not found';
	}
}

function editorFindPrev() {
	if (!editor) return;
	var term = document.getElementById('editorSearchInput').value;
	if (term && term.length > 0) {
		var found = editor.find(term, {
			wrap: true,
			caseSensitive: false,
			wholeWord: false,
			regExp: false,
			backwards: true
		});
		document.getElementById('editorSearchStatus').textContent = found ? '' : 'Not found';
	}
}

function editorReplaceOne() {
	if (!editor) return;
	var term = document.getElementById('editorSearchInput').value;
	var replace = document.getElementById('editorReplaceInput').value;
	if (term && term.length > 0) {
		editor.find(term, {wrap: true, caseSensitive: false, backwards: false});
		editor.replace(replace);
		document.getElementById('editorSearchStatus').textContent = 'Replaced';
	}
}

function editorReplaceAll() {
	if (!editor) return;
	var term = document.getElementById('editorSearchInput').value;
	var replace = document.getElementById('editorReplaceInput').value;
	if (term && term.length > 0) {
		var occurrences = editor.findAll(term, {wrap: true, caseSensitive: false});
		var count = 0;
		while (editor.replace(replace)) {
			count++;
		}
		document.getElementById('editorSearchStatus').textContent = 'Replaced ' + count + ' occurrences';
	}
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

setTimeout(function() {
	initEditor();
	setTimeout(loadConfigFile, 800);
}, 500);
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
<p style="margin-bottom: 8px;">
	<button type="button" onclick="window.location.reload()" style="background: #6c757d; color: white; border: none; padding: 6px 16px; font-size: 12px; border-radius: 4px; cursor: pointer;">🔄 $(lang de:"Aktualisieren" en:"Refresh")</button>
</p>
<pre style="max-height: 200px; overflow-y: auto; background: #1e1e1e; color: #d4d4d4; padding: 10px; border-radius: 4px; font-size: 11px; white-space: pre-wrap;">
EOF
	if [ -f /tmp/rc.gerbera.log ]; then
		tail -100 /tmp/rc.gerbera.log
	elif [ -f "${GERBERA_BASEDIR%/}/log/gerbera.log" ]; then
		echo "=== gerbera daemon log ==="
		tail -100 "${GERBERA_BASEDIR%/}/log/gerbera.log"
	elif [ -f /tmp/gerbera_ajax.log ]; then
		echo "$(lang de:"Gerbera-Log nicht gefunden. AJAX-Log anzeigen:" en:"Gerbera log not found. Showing AJAX log:")"
		echo "---"
		tail -50 /tmp/gerbera_ajax.log
	else
		echo "$(lang de:"Kein Protokoll vorhanden - Dienst wurde noch nicht gestartet" en:"No log available - service has not been started yet")"
	fi
	cat << EOF
</pre>
EOF
	sec_end

	sec_begin "$(lang de:"Datenbank" en:"Database")"
	cat << EOF
<p>
	<button type="button" onclick="resetDatabase()" style="background: #dc3545; color: white; border: none; padding: 12px 30px; font-size: 14px; font-weight: bold; border-radius: 6px; cursor: pointer; box-shadow: 0 3px 5px rgba(0,0,0,0.2);">
		🗑️ $(lang de:"Datenbank zurücksetzen" en:"Reset Database")
	</button>
	<span id="dbStatus" style="margin-left: 15px; font-size: 13px; color: #666;"></span>
</p>
<p style="font-size: 12px; color: #856404; margin-top: 8px;">
	⚠️ $(lang de:"Stoppt Gerbera, sichert die alte Datenbank und startet neu. Die Mediensammlung wird neu aufgebaut." en:"Stops Gerbera, backs up the old database, and restarts. The media library will be rebuilt.")
</p>
<script>
function resetDatabase() {
	if (!confirm('$(lang de:"Datenbank wirklich zur\u00fccksetzen? Gerbera wird gestoppt, die alte Datenbank gesichert und dann neu gestartet." en:"Really reset the database? Gerbera will be stopped, the old database backed up, and then restarted.")')) return;
	var status = document.getElementById('dbStatus');
	status.textContent = '$(lang de:"Wird ausgef\u00fchrt..." en:"Running...")';
	status.style.color = '#666';
	makeAjaxCall('reset_db', {basedir: '$(html "$GERBERA_BASEDIR")'}, function(err, response) {
		if (err || !response.success) {
			status.textContent = '$(lang de:"Fehler" en:"Error"): ' + (response ? response.message : '$(lang de:"Verbindungsfehler" en:"Connection error")');
			status.style.color = '#dc3545';
			return;
		}
		status.textContent = '✓ $(lang de:"Datenbank zurückgesetzt" en:"Database reset")';
		status.style.color = '#28a745';
		setTimeout(function() { window.location.reload(); }, 1500);
	});
}
</script>
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

		<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px 10px 0 0; position: relative;">
			<h2 style="margin: 0; color: white;">🚀 Gerbera Initial Setup</h2>
			<p style="margin: 10px 0 0 0; opacity: 0.9;" id="wizardSubtitle">Step 1 of 5</p>
			<button type="button" onclick="confirmCloseWizard()" style="position: absolute; top: 10px; right: 15px; background: transparent; border: none; color: white; font-size: 28px; cursor: pointer; opacity: 0.7;" title="Close wizard">&times;</button>
		</div>

		<div style="padding: 30px;">
			<!-- Step 1: Base Directory, Content Directory, Server Name & Alive Interval -->
			<div class="wizard-step" id="step1">
				<h3 style="color: var(--evo-text, #495057); margin-top: 0;">
					<span style="background: #667eea; color: white; border-radius: 50%; padding: 5px 12px; margin-right: 10px;">1</span>
					Base Directory &amp; Content
				</h3>
				<p>Choose the base directory for Gerbera and the directory where your media files are stored.</p>
				<p>
					<label for='setup_basedir'><strong>Base directory:</strong></label><br>
					<input type='text' id='setup_basedir' name='setup_basedir' size='60' maxlength='255'
					       value="__AUTO_STORAGE__" style="padding: 10px; font-size: 14px; width: 100%; box-sizing: border-box; border: 2px solid #ddd; border-radius: 4px;">
				</p>
				<div id="dirCheckResult"></div>
				<p>
					<label for='setup_contentdir'><strong>Content directory (media files):</strong></label><br>
					<input type='text' id='setup_contentdir' name='setup_contentdir' size='60' maxlength='255'
					       value="__AUTO_STORAGE__/media" style="padding: 10px; font-size: 14px; width: 100%; box-sizing: border-box; border: 2px solid #ddd; border-radius: 4px;">
				</p>
				<p>
					<label for='setup_friendly_name'><strong>Server name (UPnP friendly name):</strong></label><br>
					<input type='text' id='setup_friendly_name' name='setup_friendly_name' size='60' maxlength='128'
					       value="Gerbera (Freetz)" style="padding: 10px; font-size: 14px; width: 100%; box-sizing: border-box; border: 2px solid #ddd; border-radius: 4px;">
				</p>
				<p>
					<label for='setup_alive'><strong>Announcement interval (alive, seconds, min 62):</strong></label><br>
					<input type='number' id='setup_alive' name='setup_alive' min='62' value='180'
					       style="padding: 10px; font-size: 14px; width: 120px; box-sizing: border-box; border: 2px solid #ddd; border-radius: 4px;">
				</p>
				<p>
					<label for='setup_scripting'><strong>JavaScript scripting:</strong></label><br>
					<select id='setup_scripting' name='setup_scripting'
						style="padding: 10px; font-size: 14px; width: 140px; box-sizing: border-box; border: 2px solid #ddd; border-radius: 4px;">
						<option value="no" selected>Disabled</option>
						<option value="yes">Enabled</option>
					</select>
				</p>
				<div class="evo-gerbera-info">
					<p style="margin: 0; color: #1976D2;"><strong>💡 Recommendations:</strong></p>
					<p style="margin: 5px 0 0 0; font-size: 13px; color: var(--evo-text-muted, #555);">
						Base directory example: <code>__AUTO_STORAGE__</code><br>
						Content directory (default): <code>__AUTO_STORAGE__/media</code><br>
						The base directory should be on persistent storage (USB, NAS).
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
	contentdir: '',
	friendly_name: 'Gerbera (Freetz)',
	alive: '180',
	scripting: 'no',
	needsConfig: false
};

function openSetupWizard() {
	var basedirField = document.getElementById('basedir');
	if (basedirField && basedirField.value.trim()) {
		wizardData.basedir = basedirField.value.trim();
		wizardData.contentdir = wizardData.basedir + '/media';
	}
	var friendlyNameField = document.getElementById('friendly_name');
	if (friendlyNameField && friendlyNameField.value.trim()) {
		wizardData.friendly_name = friendlyNameField.value.trim();
	}
	var setupBasedirField = document.getElementById('setup_basedir');
	if (setupBasedirField) {
		setupBasedirField.value = wizardData.basedir;
	}
	var setupContentdirField = document.getElementById('setup_contentdir');
	if (setupContentdirField && !setupContentdirField.value.trim()) {
		setupContentdirField.value = wizardData.contentdir;
	}
	var setupFriendlyNameField = document.getElementById('setup_friendly_name');
	if (setupFriendlyNameField) {
		setupFriendlyNameField.value = wizardData.friendly_name;
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
	var contentdir = document.getElementById('setup_contentdir').value.trim();
	var friendly_name = document.getElementById('setup_friendly_name').value.trim();
	var alive = document.getElementById('setup_alive').value.trim();
	if (!basedir) return;
	if (!contentdir) contentdir = basedir + '/media';
	if (!friendly_name) friendly_name = 'Gerbera (Freetz)';
	if (!alive || parseInt(alive) < 62) alive = '180';
	wizardData.basedir = basedir;
	wizardData.contentdir = contentdir;
	wizardData.friendly_name = friendly_name;
	wizardData.alive = alive;
	wizardData.scripting = document.getElementById('setup_scripting').value;
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
			makeAjaxCall('save_basedir_only', {basedir: basedir, alive: alive, scripting: wizardData.scripting}, function(err2, resp2) {
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
	var contentdir = document.getElementById('setup_contentdir').value.trim();
	var friendly_name = document.getElementById('setup_friendly_name').value.trim();
	var alive = document.getElementById('setup_alive').value.trim();
	if (!contentdir) contentdir = basedir + '/media';
	if (!friendly_name) friendly_name = 'Gerbera (Freetz)';
	if (!alive || parseInt(alive) < 62) alive = '180';
	wizardData.contentdir = contentdir;
	wizardData.friendly_name = friendly_name;
	wizardData.alive = alive;
	document.getElementById('dirCheckResult').innerHTML = '<p>Creating directory...</p>';
	makeAjaxCall('create_directory', {basedir: basedir}, function(err, response) {
		if (err || !response.success) {
			document.getElementById('dirCheckResult').innerHTML =
				'<div class="evo-gerbera-danger"><p style="margin: 0; color: #721c24;">✗ Error creating directory</p></div>';
			return;
		}
		document.getElementById('dirCheckResult').innerHTML =
			'<div class="evo-gerbera-success-sm"><p style="margin: 0; color: #155724;">✓ Directory created, saving configuration...</p></div>';
		makeAjaxCall('save_basedir_only', {basedir: basedir, alive: alive}, function(err2, resp2) {
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
				'<p style="margin-top: 15px;">Generate config.xml with gerbera --create-advanced-config?</p>' +
				'<div style="text-align: center; margin-top: 15px;">' +
				'<button onclick="createConfig()" style="background: #28a745; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-weight: bold;">Yes, generate</button> ' +
				'<button onclick="wizardData.needsConfig = true; showStep(3);" style="background: #6c757d; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer;">Skip</button>' +
				'</div></div>';
		}
	});
}

function createConfig() {
	document.getElementById('configFileCheck').innerHTML = '<p>Creating config.xml...</p>';
	makeAjaxCall('create_config', {
		basedir: wizardData.basedir,
		contentdir: wizardData.contentdir,
		friendly_name: wizardData.friendly_name,
		alive: wizardData.alive,
		scripting: wizardData.scripting
	}, function(err, response) {
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

</script>
WIZARD_JS

fi
