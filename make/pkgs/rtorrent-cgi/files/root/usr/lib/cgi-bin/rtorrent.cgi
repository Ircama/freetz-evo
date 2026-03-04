#!/bin/sh

# Source libmodcgi.sh
. /usr/lib/libmodcgi.sh

# ============================================================================
# AJAX Handler - Check query string for AJAX requests
# ============================================================================
AJAX_MODE=$(cgi_param ajax)

if [ "$AJAX_MODE" = "1" ]; then
	# AJAX request - output JSON and exit
	ACTION=$(cgi_param action)
	BASEDIR=$(cgi_param basedir)
	
	echo "$(date): AJAX - ACTION=$ACTION BASEDIR=$BASEDIR" >> /tmp/rtorrent_ajax.log
	
	# Output JSON with styled box (CSS only, no extra text)
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
/* Hide box if pre is empty */
.ajax-json-content:empty, .ajax-json-content pre:empty {
	display: none;
}
.ajax-json-box:has(.ajax-json-content:empty) {
	display: none;
}
</style>
<div class="ajax-json-box"><div class="ajax-json-content"><pre>Content-Type: application/json

EOF
	
	case "$ACTION" in
		check_directory)
			echo "$(date): Checking directory: $BASEDIR" >> /tmp/rtorrent_ajax.log
			if [ -d "$BASEDIR" ]; then
				echo '{"exists": true, "writable": true}'
				echo "$(date): Directory exists" >> /tmp/rtorrent_ajax.log
			else
				echo '{"exists": false, "writable": false}'
				echo "$(date): Directory does not exist" >> /tmp/rtorrent_ajax.log
			fi
			;;
		create_directory)
			if mkdir -p "$BASEDIR" 2>/dev/null; then
				chown bittorrent:users "$BASEDIR" 2>/dev/null
				echo '{"success": true, "message": "Directory created"}'
			else
				echo '{"success": false, "message": "Failed"}'
			fi
			;;
		check_rtorrent_rc)
			if [ -f "$BASEDIR/.rtorrent.rc" ]; then
				echo '{"exists": true}'
			else
				echo '{"exists": false}'
			fi
			;;
		create_rtorrent_rc)
			RC_FILE="$BASEDIR/.rtorrent.rc"
			TEMPLATE="/mod/etc/default.rtorrent/rtorrent.rc.template"
			
			if [ -f "$TEMPLATE" ]; then
				# Use official template and replace base directory
				if sed "s|/var/media/ftp/.*rtorrent|$BASEDIR|g" "$TEMPLATE" > "$RC_FILE" 2>/dev/null; then
					chown bittorrent:users "$RC_FILE" 2>/dev/null
					echo '{"success": true}'
				else
					echo '{"success": false, "message": "Failed to write file"}'
				fi
			else
				# Fallback: create minimal inline template
				cat > "$RC_FILE" <<'RTORRENT_RC_EOF'
# rTorrent configuration file
method.insert = cfg.basedir,  private|const|string, (cat,"BASEDIR_PLACEHOLDER")
method.insert = cfg.download, private|const|string, (cat,(cfg.basedir),"/downloads/")
method.insert = cfg.session,  private|const|string, (cat,(cfg.basedir),"/session/")
method.insert = cfg.watch,    private|const|string, (cat,(cfg.basedir),"/watch/")
directory.default.set = (cat,(cfg.download))
session.path.set = (cfg.session)
schedule2 = watch_load, 10, 10, ((load.verbose, (cat, (cfg.watch), "load/*.torrent")))
schedule2 = watch_start, 11, 10, ((load.start_verbose, (cat, (cfg.watch), "start/*.torrent")))
network.port_range.set = 6881-6889
network.port_random.set = yes
network.scgi.open_port = 127.0.0.1:16891
dht.mode.set = auto
protocol.pex.set = yes
RTORRENT_RC_EOF
				sed -i "s|BASEDIR_PLACEHOLDER|$BASEDIR|g" "$RC_FILE"
				chown bittorrent:users "$RC_FILE" 2>/dev/null
				chmod 666 "$RC_FILE" 2>/dev/null
				echo '{"success": true}'
			fi
			;;
		check_directory_config)
			RC_FILE="$BASEDIR/.rtorrent.rc"
			if [ ! -f "$RC_FILE" ]; then
				echo '{"has_config": false}'
			elif grep -q "directory\.default\.set" "$RC_FILE" && grep -q "session\.path\.set" "$RC_FILE"; then
				echo '{"has_config": true}'
			else
				echo '{"has_config": false}'
			fi
			;;
		create_directories)
			if mkdir -p "$BASEDIR/downloads" "$BASEDIR/session" "$BASEDIR/watch/load" "$BASEDIR/watch/start" "$BASEDIR/log" 2>/dev/null; then
				chown -R bittorrent:users "$BASEDIR" 2>/dev/null
				# Set directory permissions to allow both daemon and web user to write
				chmod 777 "$BASEDIR" "$BASEDIR/downloads" "$BASEDIR/session" "$BASEDIR/watch" "$BASEDIR/watch/load" "$BASEDIR/watch/start" "$BASEDIR/log" 2>/dev/null
				echo '{"success": true}'
			else
				echo '{"success": false}'
			fi
			;;
		get_port)
			RC_FILE="$BASEDIR/.rtorrent.rc"
			if [ -f "$RC_FILE" ]; then
				# Try to extract port from network.port_range.set
				PORT=$(grep -E "^\s*network\.port_range\.set\s*=" "$RC_FILE" | sed -E 's/^[^=]*=\s*//' | sed 's/[^0-9-]//g' | cut -d'-' -f1)
				[ -z "$PORT" ] && PORT="6881"
				echo "{\"port\": \"$PORT\"}"
			else
				echo '{"port": "6881"}'
			fi
			;;
		save_basedir_only)
			echo "$(date): SAVE_BASEDIR_ONLY action called with BASEDIR=$BASEDIR" >> /tmp/rtorrent_ajax.log
			
			# Save BASEDIR and explicitly set ENABLED=no (user chose not to start)
			if [ -f /mod/etc/conf/rtorrent.cfg ]; then
				echo "$(date): Updating rtorrent.cfg - setting ENABLED=no" >> /tmp/rtorrent_ajax.log
				sed -i "s|^export RTORRENT_BASEDIR=.*|export RTORRENT_BASEDIR='$BASEDIR'|" /mod/etc/conf/rtorrent.cfg
				sed -i "s|^export RTORRENT_ENABLED=.*|export RTORRENT_ENABLED='no'|" /mod/etc/conf/rtorrent.cfg
				# Add BASEDIR and ENABLED if not exist
				grep -q "^export RTORRENT_BASEDIR=" /mod/etc/conf/rtorrent.cfg || echo "export RTORRENT_BASEDIR='$BASEDIR'" >> /mod/etc/conf/rtorrent.cfg
				grep -q "^export RTORRENT_ENABLED=" /mod/etc/conf/rtorrent.cfg || echo "export RTORRENT_ENABLED='no'" >> /mod/etc/conf/rtorrent.cfg
			else
				echo "$(date): Creating new rtorrent.cfg with ENABLED=no" >> /tmp/rtorrent_ajax.log
				echo "export RTORRENT_BASEDIR='$BASEDIR'" > /mod/etc/conf/rtorrent.cfg
				echo "export RTORRENT_ENABLED='no'" >> /mod/etc/conf/rtorrent.cfg
			fi
			
			echo "$(date): Saving to flash with modsave" >> /tmp/rtorrent_ajax.log
			modsave flash >> /tmp/rtorrent_ajax.log 2>&1
			
			echo "$(date): BASEDIR saved, ENABLED set to 'no'" >> /tmp/rtorrent_ajax.log
			echo '{"success": true}'
			;;
		start_service)
			echo "$(date): START_SERVICE action called with BASEDIR=$BASEDIR" >> /tmp/rtorrent_ajax.log
			
			# First, save RTORRENT_BASEDIR and RTORRENT_ENABLED to configuration
			echo "$(date): Saving RTORRENT_BASEDIR=$BASEDIR and RTORRENT_ENABLED=yes" >> /tmp/rtorrent_ajax.log
			
			# Update configuration file
			if [ -f /mod/etc/conf/rtorrent.cfg ]; then
				echo "$(date): Updating existing rtorrent.cfg" >> /tmp/rtorrent_ajax.log
				sed -i "s|^export RTORRENT_BASEDIR=.*|export RTORRENT_BASEDIR='$BASEDIR'|" /mod/etc/conf/rtorrent.cfg
				sed -i "s|^export RTORRENT_ENABLED=.*|export RTORRENT_ENABLED='yes'|" /mod/etc/conf/rtorrent.cfg
				# Add if not exists
				grep -q "^export RTORRENT_ENABLED=" /mod/etc/conf/rtorrent.cfg || echo "export RTORRENT_ENABLED='yes'" >> /mod/etc/conf/rtorrent.cfg
			else
				echo "$(date): Creating new rtorrent.cfg" >> /tmp/rtorrent_ajax.log
				echo "export RTORRENT_BASEDIR='$BASEDIR'" > /mod/etc/conf/rtorrent.cfg
				echo "export RTORRENT_ENABLED='yes'" >> /mod/etc/conf/rtorrent.cfg
			fi
			
			echo "$(date): Current rtorrent.cfg content:" >> /tmp/rtorrent_ajax.log
			cat /mod/etc/conf/rtorrent.cfg >> /tmp/rtorrent_ajax.log
			
			# Save to flash
			echo "$(date): Saving to flash with modsave" >> /tmp/rtorrent_ajax.log
			modsave flash >> /tmp/rtorrent_ajax.log 2>&1
			
			# Now start the service with correct path and argument
			echo "$(date): Executing: /mod/etc/init.d/rc.rtorrent start" >> /tmp/rtorrent_ajax.log
			START_OUTPUT=$(/mod/etc/init.d/rc.rtorrent start 2>&1)
			START_EXIT=$?
			echo "$(date): Start exit code: $START_EXIT" >> /tmp/rtorrent_ajax.log
			echo "$(date): Start output: $START_OUTPUT" >> /tmp/rtorrent_ajax.log
			
			if [ $START_EXIT -eq 0 ]; then
				echo "$(date): Service started successfully" >> /tmp/rtorrent_ajax.log
				echo '{"success": true}'
			else
				echo "$(date): Service failed to start with exit code $START_EXIT" >> /tmp/rtorrent_ajax.log
				# Escape quotes in output for JSON
				ESCAPED_OUTPUT=$(echo "$START_OUTPUT" | sed 's/"/\\"/g' | tr '\n' ' ')
				echo "{\"success\": false, \"message\": \"Exit code $START_EXIT: $ESCAPED_OUTPUT\"}"
			fi
			;;
		read_file)
			# Read file content for editor
			FILE_PATH=$(cgi_param file)
			
			# Expand relative .rtorrent.rc path
			if [ "$FILE_PATH" = ".rtorrent.rc" ] || [ "$FILE_PATH" = "rtorrent.rc" ]; then
				[ -r /mod/etc/conf/rtorrent.cfg ] && . /mod/etc/conf/rtorrent.cfg
				BASEDIR="${RTORRENT_BASEDIR%/}"
				if [ -n "$BASEDIR" ]; then
					FILE_PATH="$BASEDIR/.rtorrent.rc"
				else
					echo '{"error": "RTORRENT_BASEDIR not configured"}'
					exit 0
				fi
			fi
			
			# Expand ruTorrent config basename to full path
			case "$FILE_PATH" in
				config.php|freetz_config.php|plugins.ini|access.ini|\
				config.php.template|freetz_config.php.template|plugins.ini.template|access.ini.template)
					# Detect ruTorrent path (externalized or standard)
					if [ -d "/mod/external/usr/mww/rutorrent" ]; then
						FILE_PATH="/mod/external/usr/mww/rutorrent/conf/$FILE_PATH"
					elif [ -d "/usr/mww/rutorrent" ]; then
						FILE_PATH="/usr/mww/rutorrent/conf/$FILE_PATH"
					else
						echo '{"error": "ruTorrent directory not found"}'
						exit 0
					fi
					;;
			esac
			
			# Security checks
			case "$FILE_PATH" in
				*../*|*/../*|../*)
					echo '{"error": "Invalid file path: directory traversal not allowed"}'
					exit 0
					;;
			esac
			
			# Check if file path is allowed
			ALLOWED=0
			case "$FILE_PATH" in
				/var/media/ftp/*/.rtorrent.rc|\
				/var/media/ftp/*/*/.rtorrent.rc|\
				/var/media/ftp/*/*/*/.rtorrent.rc|\
				/var/tmp/.rtorrent.rc|\
				/tmp/.rtorrent.rc|\
				/mod/etc/default.rtorrent/rtorrent.rc.template)
					ALLOWED=1
					;;
				*)
					# Check ruTorrent config files
					case "$FILE_PATH" in
						/usr/mww/rutorrent/conf/*|\
						/mod/external/usr/mww/rutorrent/conf/*)
							# Check extension
							case "$FILE_PATH" in
								*.php|*.ini|*.template) ALLOWED=1 ;;
							esac
							;;
					esac
					
					# If not allowed yet, check if it's in RTORRENT_BASEDIR
					if [ "$ALLOWED" = "0" ]; then
						[ -r /mod/etc/conf/rtorrent.cfg ] && . /mod/etc/conf/rtorrent.cfg
						BASEDIR_RC="${RTORRENT_BASEDIR%/}/.rtorrent.rc"
						if [ "$FILE_PATH" = "$BASEDIR_RC" ]; then
							ALLOWED=1
						fi
					fi
					;;
			esac
			
			if [ "$ALLOWED" = "0" ]; then
				echo "{\"error\": \"Access denied: $FILE_PATH is not an allowed file\"}"
				exit 0
			fi
			
			# Check if file exists and is readable
			if [ ! -f "$FILE_PATH" ]; then
				echo "{\"error\": \"File not found: $FILE_PATH\", \"content\": \"\"}"
			elif [ ! -r "$FILE_PATH" ]; then
				echo "{\"error\": \"Permission denied: cannot read $FILE_PATH\"}"
			else
				# Read file content
				CONTENT=$(cat "$FILE_PATH")
				
				# Preprocess template placeholders if loading rtorrent.rc.template
				case "$FILE_PATH" in
					*/rtorrent.rc.template)
						# Load configuration values
						[ -r /mod/etc/conf/rtorrent.cfg ] && . /mod/etc/conf/rtorrent.cfg
						
						# Substitute placeholders with actual values (defaults match rtorrent.cfg)
						CONTENT=$(echo "$CONTENT" | sed \
							-e "s|__RTORRENT_DHT__|${RTORRENT_DHT:-auto}|g" \
							-e "s|__RTORRENT_DHTPORT__|${RTORRENT_DHTPORT:-6881}|g" \
							-e "s|__RTORRENT_UPLOADSLOTS__|${RTORRENT_UPLOADSLOTS:-30}|g" \
							-e "s|__RTORRENT_PEERLIMIT__|${RTORRENT_PEERLIMIT:-30}|g" \
							-e "s|__RTORRENT_MIN_PEERS__|${RTORRENT_MIN_PEERS:-20}|g" \
							-e "s|__RTORRENT_MAX_PEERS__|${RTORRENT_MAX_PEERS:-40}|g" \
							-e "s|__RTORRENT_MIN_PEERS_SEED__|${RTORRENT_MIN_PEERS_SEED:-30}|g" \
							-e "s|__RTORRENT_MAX_PEERS_SEED__|${RTORRENT_MAX_PEERS_SEED:-50}|g" \
							-e "s|__RTORRENT_DOWNLOADRATE__|${RTORRENT_DOWNLOADRATE:-300}|g" \
							-e "s|__RTORRENT_UPLOADRATE__|${RTORRENT_UPLOADRATE:-50}|g")
						;;
				esac
				
				# Escape content for JSON
				CONTENT=$(echo "$CONTENT" | sed 's/\\/\\\\/g; s/"/\\"/g; s/	/\\t/g' | awk '{printf "%s\\n", $0}' | sed '$ s/\\n$//')
				echo "{\"success\": true, \"file\": \"$FILE_PATH\", \"content\": \"$CONTENT\"}"
			fi
			;;
		write_file)
			# Write file content from editor
			FILE_PATH=$(cgi_param file)
			CONTENT=$(cgi_param content)
			
			# Expand relative .rtorrent.rc path
			if [ "$FILE_PATH" = ".rtorrent.rc" ] || [ "$FILE_PATH" = "rtorrent.rc" ]; then
				[ -r /mod/etc/conf/rtorrent.cfg ] && . /mod/etc/conf/rtorrent.cfg
				BASEDIR="${RTORRENT_BASEDIR%/}"
				if [ -n "$BASEDIR" ]; then
					FILE_PATH="$BASEDIR/.rtorrent.rc"
				else
					echo '{"error": "RTORRENT_BASEDIR not configured"}'
					exit 0
				fi
			fi
			
			# Expand ruTorrent config basename to full path
			case "$FILE_PATH" in
				config.php|freetz_config.php|plugins.ini|access.ini)
					# Detect ruTorrent path (externalized or standard)
					if [ -d "/mod/external/usr/mww/rutorrent" ]; then
						FILE_PATH="/mod/external/usr/mww/rutorrent/conf/$FILE_PATH"
					elif [ -d "/usr/mww/rutorrent" ]; then
						FILE_PATH="/usr/mww/rutorrent/conf/$FILE_PATH"
					else
						echo '{"error": "ruTorrent directory not found"}'
						exit 0
					fi
					;;
			esac
			
			# Security checks
			case "$FILE_PATH" in
				*../*|*/../*|../*)
					echo '{"error": "Invalid file path: directory traversal not allowed"}'
					exit 0
					;;
			esac
			
			# Check if file path is allowed
			ALLOWED=0
			case "$FILE_PATH" in
				/var/media/ftp/*/.rtorrent.rc|\
				/var/media/ftp/*/*/.rtorrent.rc|\
				/var/media/ftp/*/*/*/.rtorrent.rc|\
				/var/tmp/.rtorrent.rc|\
				/tmp/.rtorrent.rc|\
				/mod/etc/default.rtorrent/rtorrent.rc.template)
					ALLOWED=1
					;;
				*)
					# Check ruTorrent config files
					case "$FILE_PATH" in
						/usr/mww/rutorrent/conf/*|\
						/mod/external/usr/mww/rutorrent/conf/*)
							# Check extension
							case "$FILE_PATH" in
								*.php|*.ini|*.template) ALLOWED=1 ;;
							esac
							;;
					esac
					
					# If not allowed yet, check if it's in RTORRENT_BASEDIR
					if [ "$ALLOWED" = "0" ]; then
						[ -r /mod/etc/conf/rtorrent.cfg ] && . /mod/etc/conf/rtorrent.cfg
						BASEDIR_RC="${RTORRENT_BASEDIR%/}/.rtorrent.rc"
						if [ "$FILE_PATH" = "$BASEDIR_RC" ]; then
							ALLOWED=1
						fi
					fi
					;;
			esac
			
			if [ "$ALLOWED" = "0" ]; then
				echo "{\"error\": \"Access denied: $FILE_PATH is not an allowed file\"}"
				exit 0
			fi
			
			# Check if directory exists
			FILE_DIR=$(dirname "$FILE_PATH")
			if [ ! -d "$FILE_DIR" ]; then
				echo "{\"error\": \"Directory does not exist: $FILE_DIR\"}"
				exit 0
			fi
			
			# Create backup of existing file with timestamp
			if [ -f "$FILE_PATH" ]; then
				TIMESTAMP=$(date +%Y-%m-%d-%H-%M-%S)
				BACKUP_FILE="${FILE_PATH}.${TIMESTAMP}"
				if ! mv "$FILE_PATH" "$BACKUP_FILE" 2>/dev/null; then
					echo "{\"error\": \"Failed to create backup: $BACKUP_FILE\"}"
					exit 0
				fi
			fi
			
			# Write content to file (content comes URL-decoded from cgi_param)
			if echo "$CONTENT" > "$FILE_PATH" 2>/dev/null; then
				# Ensure file is readable and writable by all users (daemon runs as bittorrent, CGI as web user)
				chmod 666 "$FILE_PATH" 2>/dev/null
				echo "{\"success\": true, \"file\": \"$FILE_PATH\"}"
			else
				# Restore backup if write failed
				if [ -n "$BACKUP_FILE" ] && [ -f "$BACKUP_FILE" ]; then
					mv "$BACKUP_FILE" "$FILE_PATH" 2>/dev/null
				fi
				echo "{\"error\": \"Failed to write file: $FILE_PATH\"}"
			fi
			;;
		delete_rtorrent_rc)
			# Archive .rtorrent.rc file with timestamp backup
			BASEDIR=$(cgi_param basedir)
			RC_FILE="$BASEDIR/.rtorrent.rc"
			
			# Security check
			if [ -z "$BASEDIR" ]; then
				echo '{"success": false, "message": "No basedir specified"}'
			# Check if file exists
			elif [ ! -f "$RC_FILE" ]; then
				echo '{"success": false, "message": "File does not exist"}'
			else
				# Rename file with timestamp instead of deleting
				TIMESTAMP=$(date +%Y-%m-%d-%H-%M-%S)
				BACKUP_FILE="${RC_FILE}.${TIMESTAMP}"
				if mv "$RC_FILE" "$BACKUP_FILE" 2>/dev/null; then
					echo "{\"success\": true, \"message\": \"File archived to: ${BACKUP_FILE##*/}\"}"
				else
					echo '{"success": false, "message": "Failed to archive file"}'
				fi
			fi
			;;
		*)
			echo '{"error": "Unknown action"}'
			;;
	esac
	
	# Close styled JSON box
	echo '</pre></div></div>'
	
	echo "$(date): JSON sent, exiting" >> /tmp/rtorrent_ajax.log
	exit 0
fi

echo "$(date): Normal page rendering" >> /tmp/rtorrent_ajax.log

# ============================================================================
# Setup Wizard Actions (via POST)
# ============================================================================
WIZARD_ACTION=$(cgi_param wizard_action)
if [ -n "$WIZARD_ACTION" ]; then
	BASEDIR=$(cgi_param basedir)
	
	case "$WIZARD_ACTION" in
		check_and_create_dir)
			if [ ! -d "$BASEDIR" ]; then
				mkdir -p "$BASEDIR" 2>/dev/null && chown bittorrent:users "$BASEDIR" 2>/dev/null
				WIZARD_MSG="Directory created: $BASEDIR"
			else
				WIZARD_MSG="Directory already exists: $BASEDIR"
			fi
			;;
		create_rtorrent_rc)
			RC_FILE="$BASEDIR/.rtorrent.rc"
			if [ ! -f "$RC_FILE" ]; then
				TEMPLATE="/mod/etc/default.rtorrent/rtorrent.rc.template"
				if [ -f "$TEMPLATE" ]; then
					sed "s|/var/media/ftp/MediaServer/rtorrent/|$BASEDIR/|g" "$TEMPLATE" > "$RC_FILE" 2>/dev/null
					chown bittorrent:users "$RC_FILE" 2>/dev/null
					WIZARD_MSG="Created .rtorrent.rc"
				else
					WIZARD_MSG="ERROR: Template not found"
				fi
			else
				WIZARD_MSG=".rtorrent.rc already exists"
			fi
			;;
		create_directories)
			mkdir -p "$BASEDIR/downloads" "$BASEDIR/session" "$BASEDIR/watch/load" "$BASEDIR/watch/start" "$BASEDIR/log" 2>/dev/null
			chown -R bittorrent:users "$BASEDIR" 2>/dev/null
			# Set directory permissions to allow both daemon and web user to write
			chmod 777 "$BASEDIR" "$BASEDIR/downloads" "$BASEDIR/session" "$BASEDIR/watch" "$BASEDIR/watch/load" "$BASEDIR/watch/start" "$BASEDIR/log" 2>/dev/null
			WIZARD_MSG="Created directory structure"
			;;
		auto_setup)
			# Execute all setup steps
			if [ ! -d "$BASEDIR" ]; then
				mkdir -p "$BASEDIR" 2>/dev/null
				chown bittorrent:users "$BASEDIR" 2>/dev/null
				chmod 777 "$BASEDIR" 2>/dev/null
			fi
			RC_FILE="$BASEDIR/.rtorrent.rc"
			if [ ! -f "$RC_FILE" ]; then
				TEMPLATE="/mod/etc/default.rtorrent/rtorrent.rc.template"
				if [ -f "$TEMPLATE" ]; then
					sed "s|/var/media/ftp/MediaServer/rtorrent/|$BASEDIR/|g" "$TEMPLATE" > "$RC_FILE" 2>/dev/null
					chown bittorrent:users "$RC_FILE" 2>/dev/null
				fi
			fi
			mkdir -p "$BASEDIR/downloads" "$BASEDIR/session" "$BASEDIR/watch/load" "$BASEDIR/watch/start" "$BASEDIR/log" 2>/dev/null
			chown -R bittorrent:users "$BASEDIR" 2>/dev/null
			# Set directory permissions to allow both daemon and web user to write
			chmod 777 "$BASEDIR" "$BASEDIR/downloads" "$BASEDIR/session" "$BASEDIR/watch" "$BASEDIR/watch/load" "$BASEDIR/watch/start" "$BASEDIR/log" 2>/dev/null
			WIZARD_MSG="✓ Auto-setup complete! Base directory and configuration created."
			;;
	esac
fi

# ============================================================================
# Normal Page Rendering
# ============================================================================

# Handle start/stop actions from URL query string
case "$QUERY_STRING" in
	start*)
		# Framework will handle the actual start, but we redirect to clean URL
		ACTION_RESULT="started"
		;;
	stop*)
		# Framework will handle the actual stop, but we redirect to clean URL
		ACTION_RESULT="stopped"
		;;
esac

[ -r /etc/options.cfg ] && . /etc/options.cfg
[ -r /mod/etc/conf/rtorrent.cfg ] && . /mod/etc/conf/rtorrent.cfg

# ============================================================================
# Helper Functions
# ============================================================================

# Read peer port from .rtorrent.rc
get_peer_port_from_rc() {
	local rc_path="$1"
	local port="6881"
	
	if [ -f "$rc_path" ]; then
		# Try to extract port from network.port_range.set
		local port_range=$(grep -E "^\s*network\.port_range\.set\s*=" "$rc_path" | head -1 | sed -E 's/^[^=]*=\s*//' | tr -d ' ')
		if [ -n "$port_range" ]; then
			# Remove parentheses and extract first number
			port=$(echo "$port_range" | sed 's/[^0-9-]//g' | cut -d'-' -f1)
		fi
		# If still empty, use default
		[ -z "$port" ] && port="6881"
	fi
	
	echo "$port"
}

# Read value from .rtorrent.rc
get_rc_value() {
	local rc_file="$1"
	local key="$2"
	local default="$3"
	
	[ ! -f "$rc_file" ] && echo "$default" && return
	
	local value=""
	case "$key" in
		"throttle.global_up.max_rate.set_kb")
			value=$(grep -E "^\s*throttle\.global_up\.max_rate\.set_kb\s*=" "$rc_file" | sed -E 's/^[^=]*=\s*//' | tr -d ' ' | head -1)
			;;
		"throttle.global_down.max_rate.set_kb")
			value=$(grep -E "^\s*throttle\.global_down\.max_rate\.set_kb\s*=" "$rc_file" | sed -E 's/^[^=]*=\s*//' | tr -d ' ' | head -1)
			;;
		"throttle.max_peers.normal.set")
			value=$(grep -E "^\s*throttle\.max_peers\.normal\.set\s*=" "$rc_file" | sed -E 's/^[^=]*=\s*//' | tr -d ' ' | head -1)
			;;
		"throttle.max_peers.seed.set")
			value=$(grep -E "^\s*throttle\.max_peers\.seed\.set\s*=" "$rc_file" | sed -E 's/^[^=]*=\s*//' | tr -d ' ' | head -1)
			;;
		"throttle.min_peers.normal.set")
			value=$(grep -E "^\s*throttle\.min_peers\.normal\.set\s*=" "$rc_file" | sed -E 's/^[^=]*=\s*//' | tr -d ' ' | head -1)
			;;
		"throttle.min_peers.seed.set")
			value=$(grep -E "^\s*throttle\.min_peers\.seed\.set\s*=" "$rc_file" | sed -E 's/^[^=]*=\s*//' | tr -d ' ' | head -1)
			;;
		"throttle.max_uploads.global.set")
			value=$(grep -E "^\s*throttle\.max_uploads\.global\.set\s*=" "$rc_file" | sed -E 's/^[^=]*=\s*//' | tr -d ' ' | head -1)
			;;
		"throttle.max_uploads.set")
			value=$(grep -E "^\s*throttle\.max_uploads\.set\s*=" "$rc_file" | sed -E 's/^[^=]*=\s*//' | tr -d ' ' | head -1)
			;;
		"dht.mode.set")
			value=$(grep -E "^\s*dht\.mode\.set\s*=" "$rc_file" | sed -E 's/^[^=]*=\s*//' | tr -d ' ' | head -1)
			;;
		"dht.port.set")
			value=$(grep -E "^\s*dht\.port\.set\s*=" "$rc_file" | sed -E 's/^[^=]*=\s*//' | tr -d ' ' | head -1)
			;;
		"pieces.hash.on_completion.set")
			value=$(grep -E "^\s*pieces\.hash\.on_completion\.set\s*=" "$rc_file" | sed -E 's/^[^=]*=\s*//' | tr -d ' ' | head -1)
			;;
	esac
	
	[ -z "$value" ] && value="$default"
	echo "$value"
}

# ============================================================================
# Load .rtorrent.rc values
# ============================================================================

# Get .rtorrent.rc path
RTORRENT_RC_PATH=""
if [ -n "$RTORRENT_BASEDIR" ]; then
	RTORRENT_RC_PATH="${RTORRENT_BASEDIR%/}/.rtorrent.rc"
fi

# Check if .rtorrent.rc exists
RTORRENT_RC_EXISTS="no"
[ -n "$RTORRENT_RC_PATH" ] && [ -f "$RTORRENT_RC_PATH" ] && RTORRENT_RC_EXISTS="yes"

# Auto-detect default storage for suggestions
autodetect_storage_hint() {
	[ -r /mod/etc/conf/mod.cfg ] && . /mod/etc/conf/mod.cfg
	local stor_prefix="${MOD_STOR_PREFIX:-uStor}"
	if [ -d "/var/media/ftp/${stor_prefix}01" ]; then
		echo "/var/media/ftp/${stor_prefix}01/rtorrent"
	elif ls -d /var/media/ftp/*/ >/dev/null 2>&1; then
		echo "$(ls -d /var/media/ftp/*/ 2>/dev/null | head -n1)rtorrent"
	else
		echo "/var/tmp/rtorrent"
	fi
}
AUTO_STORAGE="$(autodetect_storage_hint)"

# Read values from .rtorrent.rc or use defaults
VAL_UP=$(get_rc_value "$RTORRENT_RC_PATH" "throttle.global_up.max_rate.set_kb" "0")
VAL_DOWN=$(get_rc_value "$RTORRENT_RC_PATH" "throttle.global_down.max_rate.set_kb" "0")
VAL_MAX_PEERS=$(get_rc_value "$RTORRENT_RC_PATH" "throttle.max_peers.normal.set" "100")
VAL_MAX_PEERS_SEED=$(get_rc_value "$RTORRENT_RC_PATH" "throttle.max_peers.seed.set" "50")
VAL_MIN_PEERS=$(get_rc_value "$RTORRENT_RC_PATH" "throttle.min_peers.normal.set" "40")
VAL_MIN_PEERS_SEED=$(get_rc_value "$RTORRENT_RC_PATH" "throttle.min_peers.seed.set" "10")
VAL_PEERLIMIT=$(get_rc_value "$RTORRENT_RC_PATH" "throttle.max_uploads.global.set" "200")
VAL_UPLOADSLOTS=$(get_rc_value "$RTORRENT_RC_PATH" "throttle.max_uploads.set" "15")
VAL_DHT=$(get_rc_value "$RTORRENT_RC_PATH" "dht.mode.set" "auto")
VAL_DHTPORT=$(get_rc_value "$RTORRENT_RC_PATH" "dht.port.set" "6881")
VAL_CHECKHASH=$(get_rc_value "$RTORRENT_RC_PATH" "pieces.hash.on_completion.set" "yes")
VAL_PIECES_MEMORY_MAX=$(get_rc_value "$RTORRENT_RC_PATH" "pieces.memory.max.set" "64M")

# Peer port
if [ -n "$RTORRENT_RC_PATH" ] && [ -f "$RTORRENT_RC_PATH" ]; then
	PEER_PORT=$(get_peer_port_from_rc "$RTORRENT_RC_PATH")
fi
[ -z "$PEER_PORT" ] && PEER_PORT="6881"

# ============================================================================
# Checkboxes and selects
# ============================================================================

check "$RUTORRENT_USES_HOME" yes:uses_home
check "$RTORRENT_BOOT_MONITOR" yes:boot_monitor

# DHT select
select "$VAL_DHT" auto:dht_auto on:dht_on off:dht_off

# Check hash select  
select "$VAL_CHECKHASH" yes:hash_yes no:hash_no "*":hash_yes

# ============================================================================
# Port Forwarding Status Check
# ============================================================================

AVM_RULES_INSTALLED="no"
[ -x /etc/init.d/rc.avm-rules ] && AVM_RULES_INSTALLED="yes"

# Load avm-rules configuration
[ -r /var/flash/avm-rules.cfg ] && . /var/flash/avm-rules.cfg
[ -r /mod/etc/conf/avm-rules.cfg ] && . /mod/etc/conf/avm-rules.cfg

AVM_TCP_CONFIGURED="no"
AVM_UDP_CONFIGURED="no"

# Check if port is configured (support both space-separated and single port)
case " $AVM_RULES_TCP " in
	*" $PEER_PORT "*) AVM_TCP_CONFIGURED="yes" ;;
esac
case " $AVM_RULES_UDP " in
	*" $PEER_PORT "*) AVM_UDP_CONFIGURED="yes" ;;
esac

# ============================================================================
# Page Output
# ============================================================================

# Check if ruTorrent is installed
RUTORRENT_INSTALLED="no"
if [ -d "/usr/mww/rutorrent" ] || [ -d "/mod/external/usr/mww/rutorrent" ]; then
	RUTORRENT_INSTALLED="yes"
	WEBUI_HOST="${HTTP_HOST:-${SERVER_NAME:-fritz.box}}"
	if [ -n "$HTTP_HOST" ] && echo "$HTTP_HOST" | grep -q ':'; then
		RUTORRENT_LINK="http://${WEBUI_HOST}/rutorrent/"
	else
		RUTORRENT_LINK="http://${WEBUI_HOST:-fritz.box}/rutorrent/"
	fi
fi

# ============================================================================
# Dark-mode CSS overrides (injected once, before any HTML output)
# ============================================================================
cat << 'RTORRENT_DARK_STYLE'
<style>
/* rtorrent CGI — semantic alert boxes */
.evo-rtor-warning  { color: #856404; background: #fff3cd; }
.evo-rtor-info     { color: #1565c0; background: #e7f3ff; border-left: 4px solid #2196F3; border-radius: 4px; padding: 12px; margin-top: 10px; }
.evo-rtor-note     { color: #0066cc; background: #f0f8ff; border-left: 3px solid #0066cc; border-radius: 3px; }
.evo-rtor-success  { background: #d4edda; border-left: 4px solid #28a745; border-radius: 4px; padding: 15px; margin: 15px 0; }
.evo-rtor-success-light { background: #e8f5e9; border-radius: 4px; padding: 15px; margin: 15px 0; }
.evo-rtor-warn2    { background: #fff3cd; border-left: 4px solid #ffc107; border-radius: 4px; padding: 15px; }
.evo-rtor-li       { padding: 8px; background: #f8f9fa; margin-bottom: 8px; border-radius: 4px; }
.evo-rtor-danger   { background: #f8d7da; border-radius: 4px; padding: 12px; margin-top: 10px; }
.evo-rtor-success-sm { background: #d4edda; border-radius: 4px; padding: 12px; margin-top: 10px; }
.evo-rtor-warn-sm  { background: #fff3cd; border-radius: 4px; padding: 12px; margin-top: 10px; }
/* Dark mode — manual toggle */
body.dark-mode .evo-rtor-warning,
html.dark-mode .evo-rtor-warning    { color: #fcd34d; background: #422006; }
body.dark-mode .evo-rtor-info,
html.dark-mode .evo-rtor-info       { color: #93c5fd; background: #0c1a2e; border-color: #1e40af; }
body.dark-mode .evo-rtor-note,
html.dark-mode .evo-rtor-note       { color: #7dd3fc; background: #0c1a2e; border-color: #1e40af; }
body.dark-mode .evo-rtor-success,
body.dark-mode .evo-rtor-success-light,
html.dark-mode .evo-rtor-success,
html.dark-mode .evo-rtor-success-light { background: #052e16; border-color: #15803d; color: #86efac; }
body.dark-mode .evo-rtor-warn2,
html.dark-mode .evo-rtor-warn2      { background: #422006; border-color: #b45309; color: #fcd34d; }
body.dark-mode .evo-rtor-li,
html.dark-mode .evo-rtor-li         { background: var(--evo-bg, #0f172a); color: var(--evo-text, #e2e8f0); }
body.dark-mode .evo-rtor-danger,
html.dark-mode .evo-rtor-danger     { background: #450a0a; color: #fca5a5; }
body.dark-mode .evo-rtor-success-sm,
html.dark-mode .evo-rtor-success-sm { background: #052e16; color: #86efac; }
body.dark-mode .evo-rtor-warn-sm,
html.dark-mode .evo-rtor-warn-sm    { background: #422006; color: #fcd34d; }
/* Dark mode — prefers-color-scheme */
@media (prefers-color-scheme: dark) {
  body:not(.light-mode) .evo-rtor-warning    { color: #fcd34d; background: #422006; }
  body:not(.light-mode) .evo-rtor-info       { color: #93c5fd; background: #0c1a2e; border-color: #1e40af; }
  body:not(.light-mode) .evo-rtor-note       { color: #7dd3fc; background: #0c1a2e; border-color: #1e40af; }
  body:not(.light-mode) .evo-rtor-success,
  body:not(.light-mode) .evo-rtor-success-light { background: #052e16; border-color: #15803d; color: #86efac; }
  body:not(.light-mode) .evo-rtor-warn2      { background: #422006; border-color: #b45309; color: #fcd34d; }
  body:not(.light-mode) .evo-rtor-li         { background: var(--evo-bg, #0f172a); color: var(--evo-text, #e2e8f0); }
  body:not(.light-mode) .evo-rtor-danger     { background: #450a0a; color: #fca5a5; }
  body:not(.light-mode) .evo-rtor-success-sm { background: #052e16; color: #86efac; }
  body:not(.light-mode) .evo-rtor-warn-sm    { background: #422006; color: #fcd34d; }
}
</style>
RTORRENT_DARK_STYLE

# ============================================================================
# Initial Setup Wizard OR Normal Form
# ============================================================================

if [ -z "$RTORRENT_BASEDIR" ] || [ "$RTORRENT_RC_EXISTS" = "no" ]; then
	# INITIAL SETUP WIZARD - Shown when no basedir configured OR .rtorrent.rc missing
	
	sec_begin "$(lang de:"Starttyp" en:"Start type")"
	cat << EOF
<p class="evo-rtor-warning" style="padding: 10px; border-radius: 4px;">
ℹ️ $(lang de:"Bitte führen Sie zuerst die Ersteinrichtung durch" en:"Please complete initial setup first")
</p>

<!-- Base directory field - always visible and editable -->
<p style="margin-top: 15px;">
	<label for='basedir_initial'><strong>$(lang de:"Basisverzeichnis" en:"Base Directory"):</strong></label><br>
	<input type='text' id='basedir_initial' name='basedir' size='50' maxlength='255' 
	       value="$(html "${RTORRENT_BASEDIR:-$AUTO_STORAGE}")" 
	       style="padding: 8px; font-size: 14px; width: 100%; max-width: 600px; box-sizing: border-box; border: 2px solid #ddd; border-radius: 4px;"
	       title="$(lang de:"Hauptverzeichnis für rTorrent. Wird beim Start des Assistenten als Standard verwendet." en:"Main directory for rTorrent. Will be used as default when starting the wizard.")">
</p>
EOF

# Show hint if basedir not set
if [ -z "$RTORRENT_BASEDIR" ]; then
	cat << EOF
<p style="color: #666; font-size: 12px; margin-top: 5px;">
	<strong>$(lang de:"Empfohlen" en:"Suggested"):</strong> <code>$AUTO_STORAGE</code>
</p>
EOF
elif [ ! -d "$RTORRENT_BASEDIR" ]; then
	cat << EOF
<p style="color: #f80; font-size: 12px; margin-top: 5px;">
	⚠️ $(lang de:"Verzeichnis existiert nicht" en:"Directory does not exist"): <code>$(html "$RTORRENT_BASEDIR")</code>
</p>
EOF
fi

# List RW mount points
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
			# Get usage info
			dfline=$(echo "$DFOUT" | grep " $path$")
			if [ -n "$dfline" ]; then
				avail=$(echo "$dfline" | awk '{print $4}')
				total=$(echo "$dfline" | awk '{print $2}')
				info="$avail / $total"
			else
				info="-"
			fi
			
			echo "<tr>"
			echo "<td style='padding: 3px 2px; border-bottom: 1px solid #eee;'><code style='cursor: pointer; color: #0056b3; font-weight: bold;' onclick=\"document.getElementById('basedir_initial').value='$path/rtorrent';\">$path</code></td>"
			echo "<td style='padding: 3px 2px; border-bottom: 1px solid #eee; color: #666;'>$fstyp</td>"
			echo "<td style='padding: 3px 2px; border-bottom: 1px solid #eee; text-align: right;'>$info</td>"
			echo "</tr>"
			;;
	esac
done

# Also list subdirectories in /var/media/ftp (for storage like uStor01 that are not mount points)
if [ -d "/var/media/ftp" ]; then
	for subdir in /var/media/ftp/*/; do
		if [ -d "$subdir" ]; then
			path="${subdir%/}"
			# Skip if already listed as mount point
			if ! mount | grep -q " on $path type "; then
				# Get usage info
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
				echo "<td style='padding: 3px 2px; border-bottom: 1px solid #eee;'><code style='cursor: pointer; color: #0056b3; font-weight: bold;' onclick=\"document.getElementById('basedir_initial').value='$path/rtorrent';\">$path</code></td>"
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
<div class="evo-rtor-note" style="font-size: 11px; margin-top: 8px; padding: 8px;">
<strong>$(lang de:"Hinweis" en:"Note"):</strong> $(lang de:"Ext4-Dateisystem wird empfohlen für beste Leistung und Zuverlässigkeit." en:"Ext4 filesystem is the most appropriate for best performance and reliability.")
</div>
</div>

<p style="text-align: center; margin-top: 15px;">
	<button type="button" onclick="openSetupWizard()" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 12px 30px; font-size: 15px; font-weight: bold; border-radius: 6px; cursor: pointer; box-shadow: 0 3px 5px rgba(0,0,0,0.2);">
		🚀 $(lang de:"Ersteinrichtungs-Assistent starten" en:"Start Initial Setup Wizard")
	</button>
</p>
EOF

cat << EOF

<!-- Toast Container -->
<div id="toastContainer" style="position: fixed; top: 20px; right: 20px; z-index: 9999; min-width: 300px; max-width: 400px;"></div>

<!-- Setup Wizard Modal -->
<div id="setupWizardModal" style="display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; overflow: auto; background-color: rgba(0,0,0,0.6);">
	<div id="wizardContainer" style="background-color: var(--evo-surface, #fff); margin: 3% auto; padding: 0; border-radius: 10px; width: 90%; max-width: 800px; box-shadow: 0 5px 15px rgba(0,0,0,0.3); color: var(--evo-text, #333);">
		<!-- Wizard Header -->
		<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px 10px 0 0;">
			<h2 style="margin: 0; color: white;">🚀 $(lang de:"rTorrent Ersteinrichtung" en:"rTorrent Initial Setup")</h2>
			<p style="margin: 10px 0 0 0; opacity: 0.9;" id="wizardSubtitle">$(lang de:"Schritt 1 von 5" en:"Step 1 of 5")</p>
		</div>
		
		<!-- Wizard Body -->
		<div style="padding: 30px;">
			<!-- Step 1: Base Directory -->
			<div class="wizard-step" id="step1">
				<h3 style="color: var(--evo-text, #495057); margin-top: 0;">
					<span style="background: #667eea; color: white; border-radius: 50%; padding: 5px 12px; margin-right: 10px;">1</span>
					$(lang de:"Basisverzeichnis" en:"Base Directory")
				</h3>
				<p>$(lang 
					de:"Wählen Sie ein Verzeichnis auf Ihrem USB-Speicher oder NAS, wo rTorrent Dateien speichern soll."
					en:"Choose a directory on your USB storage or NAS where rTorrent will store files."
				)</p>
				<p>
					<label for='setup_basedir'><strong>$(lang de:"Verzeichnispfad" en:"Directory path"):</strong></label><br>
					<input type='text' id='setup_basedir' name='setup_basedir' size='60' maxlength='255' 
					       value="$AUTO_STORAGE" style="padding: 10px; font-size: 14px; width: 100%; box-sizing: border-box; border: 2px solid #ddd; border-radius: 4px;">
				</p>
				<div id="dirCheckResult"></div>
				<div class="evo-rtor-info">
					<p style="margin: 0; color: #1976D2;"><strong>💡 $(lang de:"Empfehlung" en:"Recommendation"):</strong></p>
					<p style="margin: 5px 0 0 0; font-size: 13px; color: var(--evo-text-muted, #555);">
						$(lang de:"Beispiel" en:"Example"): <code>$AUTO_STORAGE</code><br>
						$(lang 
							de:"Das Verzeichnis muss auf persistentem Speicher liegen (USB, NAS). Verwenden Sie NICHT /var/tmp!"
							en:"The directory must be on persistent storage (USB, NAS). Do NOT use /var/tmp!"
						)
					</p>
				</div>
			</div>
			
			<!-- Step 2: .rtorrent.rc Check -->
			<div class="wizard-step" id="step2" style="display: none;">
				<h3 style="color: var(--evo-text, #495057); margin-top: 0;">
					<span style="background: #667eea; color: white; border-radius: 50%; padding: 5px 12px; margin-right: 10px;">2</span>
					$(lang de:"Konfigurationsdatei" en:"Configuration File")
				</h3>
				<div id="rcFileCheck">
					<p>$(lang de:"Überprüfe .rtorrent.rc..." en:"Checking .rtorrent.rc...")</p>
				</div>
			</div>
			
			<!-- Step 3: Directory Structure (conditional) -->
			<div class="wizard-step" id="step3" style="display: none;">
				<h3 style="color: var(--evo-text, #495057); margin-top: 0;">
					<span style="background: #667eea; color: white; border-radius: 50%; padding: 5px 12px; margin-right: 10px;">3</span>
					$(lang de:"Verzeichnisstruktur" en:"Directory Structure")
				</h3>
				<p>$(lang de:"Folgende Verzeichnisse werden erstellt" en:"The following directories will be created"):</p>
				<ul style="line-height: 2; list-style: none; padding: 0;">
					<li class="evo-rtor-li">📁 <strong>downloads/</strong> - $(lang de:"Heruntergeladene Dateien" en:"Downloaded files")</li>
					<li class="evo-rtor-li">📁 <strong>session/</strong> - $(lang de:"Torrent-Sitzungsdaten" en:"Torrent session data")</li>
					<li class="evo-rtor-li">📁 <strong>watch/load/</strong> - $(lang de:"Torrent-Dateien zum Laden" en:"Torrent files to load")</li>
					<li class="evo-rtor-li">📁 <strong>watch/start/</strong> - $(lang de:"Torrent-Dateien zum Auto-Start" en:"Torrent files to auto-start")</li>
					<li class="evo-rtor-li">📁 <strong>log/</strong> - $(lang de:"Protokolldateien" en:"Log files")</li>
				</ul>
			</div>
			
			<!-- Step 4: Port Forwarding -->
			<div class="wizard-step" id="step4" style="display: none;">
				<h3 style="color: var(--evo-text, #495057); margin-top: 0;">
					<span style="background: #667eea; color: white; border-radius: 50%; padding: 5px 12px; margin-right: 10px;">4</span>
					$(lang de:"Port-Weiterleitung" en:"Port Forwarding")
				</h3>
				<p>$(lang 
					de:"rTorrent benötigt offene Ports für eingehende Verbindungen:"
					en:"rTorrent requires open ports for incoming connections:"
				)</p>
				<div class="evo-rtor-success-light">
					<p style="margin: 0 0 10px 0;"><strong>$(lang de:"Erforderliche Ports" en:"Required ports"):</strong></p>
					<ul style="list-style: none; padding: 0; margin: 0;">
						<li style="padding: 5px 0;">🔌 <strong>TCP Port 51413</strong></li>
						<li style="padding: 5px 0;">🔌 <strong>UDP Port 51413</strong></li>
					</ul>
				</div>
				<div id="portForwardingStatus"></div>
			</div>
			
			<!-- Step 5: ruTorrent Status (completion) -->
			<div class="wizard-step" id="step5" style="display: none;">
				<h3 style="color: var(--evo-text, #495057); margin-top: 0;">
					<span style="background: #28a745; color: white; border-radius: 50%; padding: 5px 12px; margin-right: 10px;">✓</span>
					$(lang de:"Einrichtung abgeschlossen!" en:"Setup Complete!")
				</h3>
EOF

	if [ "$RUTORRENT_INSTALLED" = "yes" ]; then
		cat << EOF
				<div class="evo-rtor-success">
					<p style="margin: 0; color: #155724;">
						<strong>✓ ruTorrent $(lang de:"ist installiert" en:"is installed")</strong>
					</p>
					<p style="margin: 10px 0 0 0; color: #155724;">
						$(lang de:"Zugriff über" en:"Access via"): <a href="$RUTORRENT_LINK" target="_blank" style="color: #155724; font-weight: bold;">$RUTORRENT_LINK</a>
					</p>
				</div>
EOF
	else
		cat << EOF
				<div class="evo-rtor-warn2">
					<p style="margin: 0; color: #856404;">
						<strong>ℹ️ ruTorrent $(lang de:"ist nicht installiert" en:"is not installed")</strong>
					</p>
					<p style="margin: 10px 0 0 0; color: #856404;">
						$(lang 
							de:"Sie können es später über das Paket-Management installieren."
							en:"You can install it later through package management."
						)
					</p>
				</div>
EOF
	fi

	cat << EOF
				<div style="text-align: center; margin-top: 20px;">
					<button type="button" onclick="finishWizard()" style="background: #28a745; color: white; border: none; padding: 12px 30px; border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 15px;">
						✓ $(lang de:"Fertig" en:"Finish")
					</button>
				</div>
			</div>
		</div>
		
		<!-- Wizard Footer -->
		<div id="wizardFooter" style="background: var(--evo-bg, #f8f9fa); padding: 15px 30px; border-radius: 0 0 10px 10px; border-top: 1px solid var(--evo-border, #dee2e6);">
			<!-- Normal footer with navigation buttons -->
			<div id="wizardFooterNormal" style="display: flex; justify-content: space-between;">
				<button type="button" onclick="closeSetupWizard()" style="background: #6c757d; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer;">
					$(lang de:"Abbrechen" en:"Cancel")
				</button>
				<div>
					<button type="button" id="prevBtn" onclick="changeStep(-1)" style="display: none; background: #6c757d; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; margin-right: 10px;">
						← $(lang de:"Zurück" en:"Back")
					</button>
					<button type="button" id="nextBtn" onclick="changeStep(1)" style="background: #667eea; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer;">
						$(lang de:"Weiter" en:"Next") →
					</button>
				</div>
			</div>
			<!-- Confirmation message (hidden by default) -->
			<div id="wizardFooterConfirm" style="display: none; text-align: center;">
				<p style="margin: 0 0 15px 0; font-size: 15px; color: var(--evo-text, #333);">
					$(lang de:"Möchten Sie den Assistenten wirklich beenden?" en:"Do you really want to exit the wizard?")
				</p>
				<button type="button" onclick="cancelCloseWizard()" style="background: #95a5a6; color: white; border: none; padding: 10px 24px; border-radius: 4px; cursor: pointer; font-size: 14px; margin-right: 10px;">
					$(lang de:"Abbrechen" en:"Cancel")
				</button>
				<button type="button" onclick="confirmCloseWizard()" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 10px 24px; border-radius: 4px; cursor: pointer; font-size: 14px;">
					OK
				</button>
			</div>
		</div>
	</div>
</div>

<script>
// Toast notification system - persistent for errors only
function showToast(message, type, duration) {
	// Only show persistent toast for errors
	if (type !== 'error') return;
	
	var container = document.getElementById('toastContainer');
	var toast = document.createElement('div');
	
	var bgColor = '#f44336'; // error
	var icon = '✗';
	
	toast.style.cssText = 'background: ' + bgColor + '; color: white; padding: 16px 20px; margin-bottom: 10px; border-radius: 6px; box-shadow: 0 3px 10px rgba(0,0,0,0.3); display: flex; align-items: center; animation: slideIn 0.3s ease;';
	toast.innerHTML = '<span style="font-size: 20px; margin-right: 12px;">' + icon + '</span><span style="flex: 1;">' + message + '</span><button onclick="this.parentElement.remove()" style="background: rgba(255,255,255,0.2); border: none; color: white; padding: 4px 12px; border-radius: 4px; margin-left: 10px; cursor: pointer; font-weight: bold;">✕</button>';
	
	container.appendChild(toast);
}

// Add CSS animation
if (!document.getElementById('toastStyles')) {
	var style = document.createElement('style');
	style.id = 'toastStyles';
	style.textContent = '@keyframes slideIn { from { transform: translateX(400px); opacity: 0; } to { transform: translateX(0); opacity: 1; } }';
	document.head.appendChild(style);
}

var currentStep = 1;
var totalSteps = 5;  // Reduced from 6 to 5 (removed service start step)
var wizardData = {
	basedir: '${RTORRENT_BASEDIR:-$AUTO_STORAGE}',
	needsDirectories: false,
	portConfigured: false,
	rcExists: false
};

function openSetupWizard() {
	console.log('=== WIZARD OPENED ===');
	// Update wizard basedir from initial form field if present
	var initialBasedirField = document.getElementById('basedir_initial');
	if (initialBasedirField && initialBasedirField.value.trim()) {
		wizardData.basedir = initialBasedirField.value.trim();
		console.log('Using basedir from form:', wizardData.basedir);
	}
	// Update wizard field to match
	var setupBasedirField = document.getElementById('setup_basedir');
	if (setupBasedirField) {
		setupBasedirField.value = wizardData.basedir;
	}
	document.getElementById('setupWizardModal').style.display = 'block';
	showStep(1);
}

function closeSetupWizard() {
	console.log('=== WIZARD CLOSE REQUESTED ===');
	// Show confirmation in footer
	document.getElementById('wizardFooterNormal').style.display = 'none';
	document.getElementById('wizardFooterConfirm').style.display = 'block';
}

function cancelCloseWizard() {
	console.log('=== WIZARD CLOSE CANCELLED ===');
	// Hide confirmation, show normal footer
	document.getElementById('wizardFooterConfirm').style.display = 'none';
	document.getElementById('wizardFooterNormal').style.display = 'flex';
}

function confirmCloseWizard() {
	console.log('=== WIZARD CLOSED ===');
	// Actually close the wizard
	document.getElementById('setupWizardModal').style.display = 'none';
	// Reset footer state for next time
	document.getElementById('wizardFooterConfirm').style.display = 'none';
	document.getElementById('wizardFooterNormal').style.display = 'flex';
}

function finishWizard() {
	console.log('=== WIZARD FINISHED ===');
	// Close wizard and reload immediately
	document.getElementById('setupWizardModal').style.display = 'none';
	window.location.reload();
}

function showStep(step) {
	console.log('showStep called with step=' + step);
	var steps = document.getElementsByClassName('wizard-step');
	for (var i = 0; i < steps.length; i++) {
		steps[i].style.display = 'none';
	}
	document.getElementById('step' + step).style.display = 'block';
	currentStep = step;
	
	document.getElementById('wizardSubtitle').textContent = '$(lang de:"Schritt" en:"Step") ' + step + ' $(lang de:"von" en:"of") ' + totalSteps;
	
	document.getElementById('prevBtn').style.display = step === 1 ? 'none' : 'inline-block';
	document.getElementById('nextBtn').style.display = step === totalSteps ? 'none' : 'inline-block';
	
	// Auto-execute checks for certain steps
	if (step === 2) {
		setTimeout(checkRtorrentRc, 300);
	} else if (step === 4) {
		setTimeout(checkPortForwarding, 300);
	} else if (step === 5) {
		// Step 5 is now the final completion step
		setTimeout(checkRutorrent, 300);
	}
}

function changeStep(direction) {
	if (direction > 0) {
		// Moving forward - validate and execute actions for current step
		if (currentStep === 1) {
			validateAndCheckBasedir();
			return;
		} else if (currentStep === 2) {
			// Already checked in step 2 display
			if (wizardData.needsDirectories) {
				showStep(3);
			} else {
				showStep(4);
			}
			return;
		} else if (currentStep === 3) {
			// Create directories
			createDirectories();
			return;
		} else if (currentStep === 4) {
			// Port forwarding - move to final completion step
			console.log('changeStep: Moving from step 4 to step 5 (completion)');
			showStep(5);
			return;
		}
	} else {
		// Moving backward
		if (currentStep === 4 && !wizardData.needsDirectories) {
			showStep(2);
		} else if (currentStep === 3) {
			showStep(2);
		} else if (currentStep > 1) {
			showStep(currentStep - 1);
		}
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
				// Extract JSON from HTML wrapper
				var text = xhr.responseText;
				var jsonStart = text.indexOf('Content-Type: application/json');
				if (jsonStart === -1) {
					throw new Error('No JSON found');
				}
				// Find the actual JSON after the Content-Type line
				var jsonText = text.substring(jsonStart);
				var firstBrace = jsonText.indexOf('{');
				if (firstBrace === -1) {
					throw new Error('No JSON object found');
				}
				jsonText = jsonText.substring(firstBrace);
				// Find end of JSON (look for closing brace before next HTML tag)
				var endPos = jsonText.indexOf('\n<');
				if (endPos > 0) {
					jsonText = jsonText.substring(0, endPos).trim();
				}
				var response = JSON.parse(jsonText);
				callback(null, response);
			} catch(e) {
				console.error('Parse error for ' + action + ':', e.message);
				callback('Invalid JSON response', null);
			}
		} else {
			callback('Request failed: ' + xhr.status, null);
		}
	};
	xhr.onerror = function() {
		callback('Network error', null);
	};
	xhr.send();
}

function validateAndCheckBasedir() {
	var basedir = document.getElementById('setup_basedir').value.trim();
	if (!basedir) {
		return;
	}
	if (basedir.indexOf('/var/tmp') === 0) {
		if (!confirm('$(lang de:"Warnung: /var/tmp ist nicht persistent! Bei Neustart gehen Daten verloren. Fortfahren?" en:"Warning: /var/tmp is not persistent! Data will be lost on reboot. Continue?")')) {
			return;
		}
	}
	
	continueBasedirValidation(basedir);
}

function continueBasedirValidation(basedir) {
	wizardData.basedir = basedir;
	document.getElementById('dirCheckResult').innerHTML = '<p>$(lang de:"Prüfe Verzeichnis..." en:"Checking directory...")</p>';
	
	// Check if directory exists
	makeAjaxCall('check_directory', {basedir: basedir}, function(err, response) {
		if (err) {
			document.getElementById('dirCheckResult').innerHTML = 
				'<div class="evo-rtor-danger">' +
				'<p style="margin: 0; color: #721c24;">✗ $(lang de:"Fehler" en:"Error"): ' + err + '</p></div>';
			return;
		}
		
		if (response.exists) {
			// Directory exists - save BASEDIR to config
			document.getElementById('dirCheckResult').innerHTML = 
				'<div class="evo-rtor-success-sm">' +
				'<p style="margin: 0; color: #155724;">✓ $(lang de:"Verzeichnis existiert, speichere Konfiguration..." en:"Directory exists, saving configuration...")</p></div>';
			
			// Save BASEDIR to rtorrent.cfg
			makeAjaxCall('save_basedir_only', {basedir: basedir}, function(err, response) {
				if (err || !response.success) {
					document.getElementById('dirCheckResult').innerHTML = 
						'<div class="evo-rtor-danger">' +
						'<p style="margin: 0; color: #721c24;">✗ $(lang de:"Fehler beim Speichern" en:"Error saving configuration")</p></div>';
					showToast('$(lang de:"Fehler beim Speichern" en:"Error saving configuration")', 'error', 4000);
					return;
				}
				document.getElementById('dirCheckResult').innerHTML = 
					'<div class="evo-rtor-success-sm">' +
					'<p style="margin: 0; color: #155724;">✓ $(lang de:"Verzeichnis existiert und Konfiguration gespeichert" en:"Directory exists and configuration saved")</p></div>';
				setTimeout(function() { showStep(2); }, 800);
			});
		} else {
			document.getElementById('dirCheckResult').innerHTML = 
				'<div class="evo-rtor-warn-sm">' +
				'<p style="margin: 0; color: #856404;">ℹ $(lang de:"Verzeichnis existiert nicht" en:"Directory does not exist")</p>' +
				'<button onclick="createBasedir(\'' + basedir + '\')" style="margin-top: 10px; background: #28a745; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-weight: bold;">$(lang de:"Jetzt erstellen" en:"Create Now")</button></div>';
		}
	});
}

function createBasedir(basedir) {
	document.getElementById('dirCheckResult').innerHTML = '<p>$(lang de:"Erstelle Verzeichnis..." en:"Creating directory...")</p>';
	
	makeAjaxCall('create_directory', {basedir: basedir}, function(err, response) {
		if (err || !response.success) {
			document.getElementById('dirCheckResult').innerHTML = 
				'<div class="evo-rtor-danger">' +
				'<p style="margin: 0; color: #721c24;">✗ ' + (response ? response.message : '$(lang de:"Fehler beim Erstellen" en:"Error creating directory")') + '</p></div>';
			showToast('$(lang de:"Fehler beim Erstellen" en:"Error creating directory")', 'error', 4000);
			return;
		}
		
		// Directory created - now save BASEDIR to config
		document.getElementById('dirCheckResult').innerHTML = 
			'<div class="evo-rtor-success-sm">' +
			'<p style="margin: 0; color: #155724;">✓ $(lang de:"Verzeichnis erstellt, speichere Konfiguration..." en:"Directory created, saving configuration...")</p></div>';
		
		makeAjaxCall('save_basedir_only', {basedir: basedir}, function(err, response) {
			if (err || !response.success) {
				document.getElementById('dirCheckResult').innerHTML = 
					'<div class="evo-rtor-danger">' +
					'<p style="margin: 0; color: #721c24;">✗ $(lang de:"Fehler beim Speichern" en:"Error saving configuration")</p></div>';
				showToast('$(lang de:"Fehler beim Speichern" en:"Error saving configuration")', 'error', 4000);
				return;
			}
			document.getElementById('dirCheckResult').innerHTML = 
				'<div class="evo-rtor-success-sm">' +
				'<p style="margin: 0; color: #155724;">✓ $(lang de:"Verzeichnis erstellt und Konfiguration gespeichert" en:"Directory created and configuration saved")</p></div>';
			setTimeout(function() { showStep(2); }, 800);
		});
	});
}

function checkRtorrentRc() {
	document.getElementById('rcFileCheck').innerHTML = '<p>$(lang de:"Prüfe .rtorrent.rc..." en:"Checking .rtorrent.rc...")</p>';
	
	makeAjaxCall('check_rtorrent_rc', {basedir: wizardData.basedir}, function(err, response) {
		if (err) {
			document.getElementById('rcFileCheck').innerHTML = 
				'<div class="evo-rtor-danger">' +
				'<p style="margin: 0; color: #721c24;">✗ $(lang de:"Fehler bei der Prüfung" en:"Error checking .rtorrent.rc")</p></div>';
			return;
		}
		
		wizardData.rcExists = response.exists;
		
		if (response.exists) {
			document.getElementById('rcFileCheck').innerHTML = 
				'<div class="evo-rtor-success-sm">' +
				'<p style="margin: 0; color: #155724;">✓ <strong>.rtorrent.rc</strong> $(lang de:"gefunden" en:"found")</p></div>' +
				'<p style="margin-top: 15px;">$(lang de:"Prüfe Verzeichniskonfiguration..." en:"Checking directory configuration...")</p>';
			
			// Check if directory configuration exists in .rtorrent.rc
			checkDirectoryConfig();
		} else {
			document.getElementById('rcFileCheck').innerHTML = 
				'<div class="evo-rtor-warn-sm">' +
				'<p style="margin: 0; color: #856404;">⚠️ <strong>.rtorrent.rc</strong> $(lang de:"nicht gefunden" en:"not found")</p></div>' +
				'<p style="margin-top: 15px;">$(lang de:"Soll .rtorrent.rc aus dem Template erstellt werden?" en:"Create .rtorrent.rc from template?")</p>' +
				'<div style="text-align: center; margin-top: 15px;">' +
				'<button onclick="createRtorrentRc()" style="background: #28a745; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-weight: bold;">$(lang de:"Ja, erstellen" en:"Yes, create")</button> ' +
				'<button onclick="wizardData.needsDirectories = true; showStep(3);" style="background: #6c757d; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer;">$(lang de:"Überspringen" en:"Skip")</button>' +
				'</div>';
		}
	});
}

function createRtorrentRc() {
	document.getElementById('rcFileCheck').innerHTML = '<p>$(lang de:"Erstelle .rtorrent.rc..." en:"Creating .rtorrent.rc...")</p>';
	
	makeAjaxCall('create_rtorrent_rc', {basedir: wizardData.basedir}, function(err, response) {
		if (err || !response.success) {
			document.getElementById('rcFileCheck').innerHTML = 
				'<div class="evo-rtor-danger">' +
				'<p style="margin: 0; color: #721c24;">✗ ' + (response ? response.message : '$(lang de:"Fehler beim Erstellen" en:"Error creating .rtorrent.rc")') + '</p></div>';
			showToast('$(lang de:"Fehler beim Erstellen von .rtorrent.rc" en:"Error creating .rtorrent.rc")', 'error', 4000);
			return;
		}
		
		document.getElementById('rcFileCheck').innerHTML = 
			'<div class="evo-rtor-success-sm">' +
			'<p style="margin: 0; color: #155724;">✓ .rtorrent.rc $(lang de:"erfolgreich erstellt" en:"created successfully")</p></div>';
		wizardData.rcExists = true;
		
		// Check directory configuration
		setTimeout(checkDirectoryConfig, 800);
	});
}

function checkDirectoryConfig() {
	makeAjaxCall('check_directory_config', {basedir: wizardData.basedir}, function(err, response) {
		if (err) {
			wizardData.needsDirectories = true;
			return;
		}
		
		wizardData.needsDirectories = !response.has_config;
		
		var checkMsg = document.getElementById('rcFileCheck');
		if (response.has_config) {
			checkMsg.innerHTML += 
				'<div class="evo-rtor-success-sm">' +
				'<p style="margin: 0; color: #155724;">✓ $(lang de:"Verzeichniskonfiguration vorhanden" en:"Directory configuration exists")</p></div>';
		} else {
			checkMsg.innerHTML += 
				'<div class="evo-rtor-warn-sm">' +
				'<p style="margin: 0; color: #856404;">⚠️ $(lang de:"Verzeichnisstruktur muss erstellt werden" en:"Directory structure needs to be created")</p></div>';
		}
	});
}

function createDirectories() {
	if (!confirm('$(lang de:"Verzeichnisstruktur jetzt erstellen?" en:"Create directory structure now?")')) {
		return;
	}
	
	document.getElementById('step3').innerHTML = 
			'<h3 style="color: var(--evo-text, #495057); margin-top: 0;">' +
			'<span style="background: #667eea; color: white; border-radius: 50%; padding: 5px 12px; margin-right: 10px;">3</span>' +
			'$(lang de:"Verzeichnisstruktur" en:"Directory Structure")' +
			'</h3>' +
			'<p>$(lang de:"Erstelle Verzeichnisse..." en:"Creating directories...")</p>';
		
		makeAjaxCall('create_directories', {basedir: wizardData.basedir}, function(err, response) {
			if (err || !response.success) {
				document.getElementById('step3').innerHTML += 
					'<div class="evo-rtor-danger">' +
					'<p style="margin: 0; color: #721c24;">✗ ' + (response ? response.message : '$(lang de:"Fehler beim Erstellen" en:"Error creating directories")') + '</p></div>';
				return;
			}
			
		document.getElementById('step3').innerHTML += 
			'<div class="evo-rtor-success-sm">' +
			'<p style="margin: 0; color: #155724;">✓ $(lang de:"Verzeichnisse erfolgreich erstellt" en:"Directories created successfully")</p></div>';
		setTimeout(function() { showStep(4); }, 1000);
	});
}

function checkPortForwarding() {
	document.getElementById('portForwardingStatus').innerHTML = '<p>$(lang de:"Lese Port-Konfiguration..." en:"Reading port configuration...")</p>';
	
	// First, get the port from .rtorrent.rc
	makeAjaxCall('get_port', {basedir: wizardData.basedir}, function(err, response) {
		if (err || !response.port) {
			document.getElementById('portForwardingStatus').innerHTML = 
				'<div class="evo-rtor-danger">' +
				'<p style="margin: 0; color: #721c24;">✗ $(lang de:"Fehler beim Lesen der Port-Konfiguration" en:"Error reading port configuration")</p></div>';
			return;
		}
		
		var port = response.port;
		wizardData.port = port;
		
		// Update the display with the actual port
		var step4 = document.getElementById('step4');
		var portList = step4.querySelector('ul');
		portList.innerHTML = 
			'<li style="padding: 5px 0;">🔌 <strong>TCP Port ' + port + '</strong></li>' +
			'<li style="padding: 5px 0;">🔌 <strong>UDP Port ' + port + '</strong></li>';
		
		// Show port configuration status
		document.getElementById('portForwardingStatus').innerHTML = 
			'<div class="evo-rtor-success">' +
			'<p style="margin: 0 0 10px 0;"><strong>✓ $(lang de:"Port-Konfiguration" en:"Port Configuration"):</strong></p>' +
			'<p style="margin: 5px 0;">$(lang de:"Port" en:"Port") <strong>' + port + '</strong> $(lang de:"wurde in .rtorrent.rc konfiguriert" en:"has been configured in .rtorrent.rc")</p>' +
			'<p style="font-size: 13px; color: #2d5016; margin: 10px 0 0 0;">$(lang de:"✓ Die Ports sind bereits korrekt konfiguriert. Stellen Sie sicher, dass diese auch im Router weitergeleitet werden für optimale Konnektivität." en:"✓ The ports are already correctly configured.")</p>' +
			'</div>';
	});
}

function startService(shouldStart) {
	var basedir = wizardData.basedir;
	console.log('startService called with shouldStart=' + shouldStart + ', basedir=' + basedir);
	
	if (shouldStart) {
		document.getElementById('serviceStartResult').innerHTML = '<p>$(lang de:"Starte Dienst..." en:"Starting service...")</p>';
		console.log('Making AJAX call to start_service with basedir=' + basedir);
		
		makeAjaxCall('start_service', {basedir: basedir}, function(err, response) {
			if (err) {
				var errorMsg = typeof err === 'string' ? err : '$(lang de:"Netzwerkfehler" en:"Network error")';
				document.getElementById('serviceStartResult').innerHTML = 
					'<div class="evo-rtor-danger">' +
					'<p style="margin: 0; color: #721c24;">✗ ' + errorMsg + '</p></div>';
				showToast('$(lang de:"Fehler beim Starten" en:"Error starting service")', 'error', 4000);
				return;
			}
			
			if (!response || !response.success) {
				var msg = response && response.message ? response.message : '$(lang de:"Unbekannter Fehler" en:"Unknown error")';
				document.getElementById('serviceStartResult').innerHTML = 
					'<div class="evo-rtor-danger">' +
					'<p style="margin: 0; color: #721c24;">✗ ' + msg + '</p></div>';
				showToast('$(lang de:"Fehler beim Starten" en:"Error starting service")', 'error', 4000);
				return;
			}
			
			wizardData.serviceStarted = true;  // Mark that service was started
			document.getElementById('serviceStartResult').innerHTML = 
				'<div class="evo-rtor-success-sm">' +
				'<p style="margin: 0; color: #155724;">✓ $(lang de:"Dienst erfolgreich gestartet" en:"Service started successfully")</p></div>';
			setTimeout(function() { showStep(6); }, 1200);
		});
	} else {
		// User chose not to start - save basedir only without enabling service
		document.getElementById('serviceStartResult').innerHTML = '<p>$(lang de:"Speichere Konfiguration..." en:"Saving configuration...")</p>';
		console.log('Making AJAX call to save_basedir_only with basedir=' + basedir);
		
		makeAjaxCall('save_basedir_only', {basedir: basedir}, function(err, response) {
			wizardData.serviceStarted = false;  // Mark that service was NOT started
			if (err || !response || !response.success) {
				document.getElementById('serviceStartResult').innerHTML = 
					'<div class="evo-rtor-warn-sm">' +
					'<p style="margin: 0; color: #856404;">⚠ $(lang de:"Konfiguration gespeichert. Dienst nicht gestartet." en:"Configuration saved. Service not started.")</p></div>';
			} else {
				document.getElementById('serviceStartResult').innerHTML = 
					'<div class="evo-rtor-warn-sm">' +
					'<p style="margin: 0; color: #856404;">ℹ $(lang de:"Dienst nicht gestartet. Sie können ihn später manuell starten." en:"Service not started. You can start it manually later.")</p></div>';
			}
			setTimeout(function() { showStep(6); }, 800);
		});
	}
}

function checkRutorrent() {
	// ruTorrent status is already displayed in step 6 HTML from backend
}

// Keyboard shortcuts for wizard navigation
document.addEventListener('keydown', function(e) {
	var wizardVisible = document.getElementById('setupWizardModal').style.display === 'block';
	var confirmVisible = document.getElementById('wizardFooterConfirm').style.display === 'block';
	
	if (e.key === 'Escape' && wizardVisible) {
		if (confirmVisible) {
			// ESC on confirmation = cancel close
			cancelCloseWizard();
		} else {
			// ESC on wizard = show close confirmation
			closeSetupWizard();
		}
	} else if (e.key === 'Enter' && wizardVisible && confirmVisible) {
		// Enter on confirmation = confirm close
		confirmCloseWizard();
	} else if (wizardVisible && !confirmVisible) {
		// Arrow navigation (only when confirmation not shown)
		if (e.key === 'ArrowRight' && document.getElementById('nextBtn').style.display !== 'none') {
			changeStep(1);
		} else if (e.key === 'ArrowLeft' && document.getElementById('prevBtn').style.display !== 'none') {
			changeStep(-1);
		}
	}
});

// Close modal when clicking outside
window.onclick = function(event) {
	var modal = document.getElementById('setupWizardModal');
	if (event.target == modal) {
		closeSetupWizard();
	}
}
</script>
EOF
	sec_end

else
	# NORMAL FORM - Shown when basedir is configured
	
sec_begin "$(lang de:"Starttyp" en:"Start type")"
cgi_print_radiogroup_service_starttype "enabled" "$RTORRENT_ENABLED" "" "" 0
sec_end

sec_begin "$(lang de:"Basisverzeichnis" en:"Base Directory")"
cat << EOF
<p>
<label for='basedir' title="cfg.basedir">$(lang de:"Basisverzeichnis" en:"Base Directory"): </label>
<input type='text' id='basedir' name='basedir' size='50' maxlength='255' value="$(html "$RTORRENT_BASEDIR")" 
       title="$(lang de:"Hauptverzeichnis für rTorrent. Hier werden Downloads, Session-Daten und Konfigurationsdateien gespeichert. Muss auf persistentem Speicher (USB/NAS) liegen." en:"Main directory for rTorrent. Downloads, session data and configuration files are stored here. Must be on persistent storage (USB/NAS).")">
</p>
EOF

# Show warning if base directory not set or doesn't exist
if [ -z "$RTORRENT_BASEDIR" ]; then
	cat << EOF
<p style="color: #c60;">
<strong>$(lang de:"Hinweis" en:"Note"):</strong> $(lang de:"Basisverzeichnis nicht gesetzt. Empfohlen" en:"Base directory not set. Suggested"): <code>$AUTO_STORAGE</code>
</p>
EOF
elif [ ! -d "$RTORRENT_BASEDIR" ]; then
	cat << EOF
<p style="color: #c00;">
<strong>$(lang de:"Warnung" en:"Warning"):</strong> $(lang de:"Verzeichnis existiert nicht" en:"Directory does not exist"): <code>$(html "$RTORRENT_BASEDIR")</code>
</p>
EOF
fi

# Show warning if .rtorrent.rc doesn't exist
if [ "$RTORRENT_RC_EXISTS" = "no" ] && [ -n "$RTORRENT_RC_PATH" ]; then
	cat << EOF
<p style="color: #f80;">
<strong>$(lang de:"Warnung" en:"Warning"):</strong> $(lang de:"Die Datei .rtorrent.rc existiert nicht unter" en:"The file .rtorrent.rc does not exist at") <code>$RTORRENT_RC_PATH</code>
</p>
EOF
fi

# List RW mount points
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
			# Get usage info
			dfline=$(echo "$DFOUT" | grep " $path$")
			if [ -n "$dfline" ]; then
				avail=$(echo "$dfline" | awk '{print $4}')
				total=$(echo "$dfline" | awk '{print $2}')
				info="$avail / $total"
			else
				info="-"
			fi
			
			echo "<tr>"
			echo "<td style='padding: 3px 2px; border-bottom: 1px solid #eee;'><code style='cursor: pointer; color: #0056b3; font-weight: bold;' onclick=\"document.getElementById('basedir').value='$path/rtorrent';\">$path</code></td>"
			echo "<td style='padding: 3px 2px; border-bottom: 1px solid #eee; color: #666;'>$fstyp</td>"
			echo "<td style='padding: 3px 2px; border-bottom: 1px solid #eee; text-align: right;'>$info</td>"
			echo "</tr>"
			;;
	esac
done

# Also list subdirectories in /var/media/ftp (for storage like uStor01 that are not mount points)
if [ -d "/var/media/ftp" ]; then
	for subdir in /var/media/ftp/*/; do
		if [ -d "$subdir" ]; then
			path="${subdir%/}"
			# Skip if already listed as mount point
			if ! mount | grep -q " on $path type "; then
				# Get usage info
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
				echo "<td style='padding: 3px 2px; border-bottom: 1px solid #eee;'><code style='cursor: pointer; color: #0056b3; font-weight: bold;' onclick=\"document.getElementById('basedir').value='$path/rtorrent';\">$path</code></td>"
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
<div class="evo-rtor-note" style="font-size: 11px; margin-top: 8px; padding: 8px;">
<strong>$(lang de:"Hinweis" en:"Note"):</strong> $(lang de:"Ext4-Dateisystem wird empfohlen für beste Leistung und Zuverlässigkeit." en:"Ext4 filesystem is the most appropriate for best performance and reliability.")
</div>
</div>
EOF

sec_end

sec_begin "$(lang de:"Priorit&auml;t" en:"Priority")"
cat << EOF
<p>
<label for='nice' title="RTORRENT_NICE (system config, not .rtorrent.rc)">Nice-Level: </label>
<input type='text' id='nice' name='nice' size='3' maxlength='3' value="$(html "${RTORRENT_NICE:-5}")" 
       title="$(lang de:"Prozess-Priorität (0-19). Höhere Werte = niedrigere Priorität. Standard: 5. Verwenden Sie höhere Werte, um System-Ressourcen für andere Dienste zu reservieren." en:"Process priority (0-19). Higher values = lower priority. Default: 5. Use higher values to reserve system resources for other services.")">
</p>
EOF
sec_end

sec_begin "$(lang de:"Peer-Einstellungen" en:"Peer Settings")"
cat << EOF
<p>
<label for='uploadrate' title="throttle.global_up.max_rate.set_kb">$(lang de:"Upload-Rate (KB/s)" en:"Upload Rate (KB/s)"): </label>
<input type='text' id='uploadrate' name='uploadrate' size='10' value="$(html "$VAL_UP")" 
       title="$(lang de:"Maximale Upload-Geschwindigkeit in KB/s. 0 = unbegrenzt. Empfehlung: 80-90% Ihrer Upload-Bandbreite, um andere Dienste nicht zu beeinträchtigen." en:"Maximum upload speed in KB/s. 0 = unlimited. Recommendation: 80-90% of your upload bandwidth to avoid affecting other services.")">
<small>$(lang de:"(0 = unbegrenzt, Standard)" en:"(0 = unlimited, default)")</small>
</p>
<p>
<label for='downloadrate' title="throttle.global_down.max_rate.set_kb">$(lang de:"Download-Rate (KB/s)" en:"Download Rate (KB/s)"): </label>
<input type='text' id='downloadrate' name='downloadrate' size='10' value="$(html "$VAL_DOWN")" 
       title="$(lang de:"Maximale Download-Geschwindigkeit in KB/s. 0 = unbegrenzt. Setzen Sie ein Limit, wenn Sie Bandbreite für andere Dienste reservieren möchten." en:"Maximum download speed in KB/s. 0 = unlimited. Set a limit if you want to reserve bandwidth for other services.")">
<small>$(lang de:"(0 = unbegrenzt, Standard)" en:"(0 = unlimited, default)")</small>
</p>
<p>
<label for='max_peers' title="throttle.max_peers.normal.set">$(lang de:"Max. Peers" en:"Max Peers"): </label>
<input type='text' id='max_peers' name='max_peers' size='5' value="$(html "$VAL_MAX_PEERS")" 
       title="$(lang de:"Maximale Anzahl verbundener Peers pro aktivem Torrent (Download). Höhere Werte = bessere Geschwindigkeit, aber mehr Ressourcenverbrauch." en:"Maximum number of connected peers per active torrent (download). Higher values = better speed, but more resource usage.")">
<small>$(lang de:"(Standard: 100)" en:"(default: 100)")</small>
</p>
<p>
<label for='max_peers_seed' title="throttle.max_peers.seed.set">$(lang de:"Max. Peers (Seeding)" en:"Max Peers Seeding"): </label>
<input type='text' id='max_peers_seed' name='max_peers_seed' size='5' value="$(html "$VAL_MAX_PEERS_SEED")" 
       title="$(lang de:"Maximale Anzahl verbundener Peers pro Torrent im Seeding-Modus. Normalerweise niedriger als beim Download, da Upload-Bandbreite begrenzt ist." en:"Maximum number of connected peers per torrent in seeding mode. Usually lower than download, since upload bandwidth is limited.")">
<small>$(lang de:"(Standard: 50)" en:"(default: 50)")</small>
</p>
<p>
<label for='min_peers' title="throttle.min_peers.normal.set">$(lang de:"Min. Peers" en:"Min Peers"): </label>
<input type='text' id='min_peers' name='min_peers' size='5' value="$(html "$VAL_MIN_PEERS")" 
       title="$(lang de:"Minimale Anzahl Peers, die rTorrent versucht zu halten (Download). rTorrent sucht aktiv nach neuen Peers, wenn die Anzahl darunter fällt." en:"Minimum number of peers rTorrent tries to maintain (download). rTorrent actively searches for new peers if the count drops below this.")">
<small>$(lang de:"(Standard: 40)" en:"(default: 40)")</small>
</p>
<p>
<label for='min_peers_seed' title="throttle.min_peers.seed.set">$(lang de:"Min. Peers (Seeding)" en:"Min Peers Seeding"): </label>
<input type='text' id='min_peers_seed' name='min_peers_seed' size='5' value="$(html "$VAL_MIN_PEERS_SEED")" 
       title="$(lang de:"Minimale Anzahl Peers beim Seeding. Niedriger als beim Download, da Seeding weniger aktive Verbindungen erfordert." en:"Minimum number of peers when seeding. Lower than download, since seeding requires fewer active connections.")">
<small>$(lang de:"(Standard: 10)" en:"(default: 10)")</small>
</p>
<p>
<label for='peerlimit' title="throttle.max_uploads.global.set">$(lang de:"Peer-Limit" en:"Peer Limit"): </label>
<input type='text' id='peerlimit' name='peerlimit' size='5' value="$(html "$VAL_PEERLIMIT")" 
       title="$(lang de:"Globales Maximum aller gleichzeitigen Peer-Verbindungen über alle Torrents. Verhindert Überlastung bei vielen aktiven Torrents." en:"Global maximum of all simultaneous peer connections across all torrents. Prevents overload with many active torrents.")">
<small>$(lang de:"(Standard: 200)" en:"(default: 200)")</small>
</p>
<p>
<label for='uploadslots' title="throttle.max_uploads.set">$(lang de:"Upload-Slots" en:"Upload Slots"): </label>
<input type='text' id='uploadslots' name='uploadslots' size='5' value="$(html "$VAL_UPLOADSLOTS")" 
       title="$(lang de:"Maximale Anzahl gleichzeitiger Uploads pro Torrent. Begrenzt, wie viele Peers gleichzeitig Daten hochladen können." en:"Maximum number of simultaneous uploads per torrent. Limits how many peers can upload data simultaneously.")">
<small>$(lang de:"(Standard: 15)" en:"(default: 15)")</small>
</p>
EOF
sec_end

sec_begin "$(lang de:"DHT-Einstellungen" en:"DHT Settings")"
cat << EOF
<p>
<label for='dht' title="dht.mode.set">DHT: </label>
<select name='dht' id='dht' 
        title="$(lang de:"Distributed Hash Table - Ermöglicht Peer-Suche ohne Tracker. Auto = aktiviert bei öffentlichen Torrents. Empfohlen: Auto." en:"Distributed Hash Table - Enables peer discovery without tracker. Auto = enabled for public torrents. Recommended: Auto.")">
<option value='auto'$dht_auto_sel>$(lang de:"Auto (Standard)" en:"Auto (default)")</option>
<option value='on'$dht_on_sel>$(lang de:"Ein" en:"On")</option>
<option value='off'$dht_off_sel>$(lang de:"Aus" en:"Off")</option>
</select>
</p>
<p>
<label for='dhtport' title="dht.port.set">$(lang de:"DHT-Port" en:"DHT Port"): </label>
<input type='text' id='dhtport' name='dhtport' size='10' value="$(html "$VAL_DHTPORT")" 
       title="$(lang de:"UDP-Port für DHT-Kommunikation. Muss nicht weitergeleitet werden, verbessert aber die Peer-Suche. Standard: 6881." en:"UDP port for DHT communication. Does not need to be forwarded, but improves peer discovery. Default: 6881.")">
<small>$(lang de:"(Standard: 6881)" en:"(default: 6881)")</small>
</p>
EOF
sec_end

sec_begin "$(lang de:"Weitere Einstellungen" en:"Other Settings")"
cat << EOF
<p>
<label for='checkhash' title="pieces.hash.on_completion.set">$(lang de:"Hash beim Start prüfen" en:"Check Hash on Start"): </label>
<select name='checkhash' id='checkhash' 
        title="$(lang de:"Prüft heruntergeladene Dateien beim rTorrent-Start auf Integrität. Ja = sicherer, aber längerer Start bei vielen/großen Torrents." en:"Checks downloaded files for integrity on rTorrent start. Yes = safer, but longer startup with many/large torrents.")">
<option value='yes'$hash_yes_sel>$(lang de:"Ja (Standard)" en:"Yes (default)")</option>
<option value='no'$hash_no_sel>$(lang de:"Nein" en:"No")</option>
</select>
</p>
<p>
<label for='config_wait' title="RTORRENT_CONFIG_WAIT (system config, not .rtorrent.rc)">$(lang de:"Wartezeit beim Booten (sec)" en:"Boot Wait Time (sec)"): </label>
<input type='text' id='config_wait' name='config_wait' size='3' value="$(html "${RTORRENT_CONFIG_WAIT:-120}")" 
       title="$(lang de:"Wie lange beim Systemstart auf USB/Netzwerk warten, bevor rTorrent gestartet wird. 0 = sofortiger Start (synchron, nur für internen Speicher). >0 = Hintergrundstart mit Wartezeit (für USB/NAS)." en:"How long to wait at system boot for USB/network resources before starting rTorrent. 0 = immediate start (synchronous, for internal storage only). >0 = background start with wait time (for USB/NAS).")">
<small>$(lang de:"(Standard: 120, 0 = sofort)" en:"(default: 120, 0 = immediate)")</small>
</p>
<p>
<label for='scgi_port' title="network.scgi.open_port">$(lang de:"SCGI-Port" en:"SCGI Port"): </label>
<input type='text' id='scgi_port' name='scgi_port' size='6' value="$(html "${RTORRENT_SCGI_PORT:-16891}")" 
       title="$(lang de:"TCP-Port für SCGI-Kommunikation zwischen ruTorrent und rTorrent. Wird nur lokal (127.0.0.1) gebunden. Traditionelle Ports sind 5000 oder 5555, aber 16891 vermeidet Konflikte mit Flask, Docker, UPnP usw. Standard: 16891." en:"TCP port for SCGI communication between ruTorrent and rTorrent. Bound only locally (127.0.0.1). Traditional ports are 5000 or 5555, but 16891 avoids conflicts with Flask, Docker, UPnP, etc. Default: 16891.")">
<small>$(lang de:"(Standard: 16891, traditionell: 5000 oder 5555)" en:"(default: 16891, traditional: 5000 or 5555)")</small>
</p>
<p>
<label for='pieces_memory_max' title="pieces.memory.max.set">$(lang de:"Pieces Memory Max" en:"Pieces Memory Max"): </label>
<input type='text' id='pieces_memory_max' name='pieces_memory_max' size='6' value="$(html "${VAL_PIECES_MEMORY_MAX:-${RTORRENT_PIECES_MEMORY_MAX:-64M}}")" 
       title="$(lang de:"RAM für Torrent-Piece-Puffer. Kritisch bei wenig RAM: zu hoch = System-Crash (OOM), zu niedrig = langsamere Performance. FritzBox 64MB RAM: 32M, 128-256MB: 64M, 512MB+: 128M." en:"RAM for buffering torrent pieces. Critical on low-RAM devices: too high = system crash (OOM), too low = slower performance. FritzBox 64MB RAM: 32M, 128-256MB: 64M, 512MB+: 128M.")">
<small>$(lang de:"(Standard: 64M, Werte: 32M/64M/128M/256M)" en:"(default: 64M, values: 32M/64M/128M/256M)")</small>
</p>
EOF
sec_end

sec_begin "$(lang de:"Boot-Überwachung" en:"Boot Monitor")"
cat << EOF
<p>
<label for='boot_monitor' title="RTORRENT_BOOT_MONITOR (system config)">$(lang de:"Aktivieren" en:"Enable"): </label>
<input type="hidden" name="boot_monitor" value="no">
<input type='checkbox' id='boot_monitor' name='boot_monitor' value='yes'$boot_monitor_chk
	title="$(lang de:"Falls aktiviert, überwacht das Init-Skript nach dem Start beim Booten für eine begrenzte Zeit, ob rTorrent noch läuft, und startet es bei Bedarf neu." en:"If enabled, after boot start the init script monitors for a limited time whether rTorrent is still running and restarts it if needed.")">
<small>$(lang de:"(Standard: aus)" en:"(default: off)")</small>
</p>
<p>
<label for='boot_monitor_interval' title="RTORRENT_BOOT_MONITOR_INTERVAL (system config)">$(lang de:"Intervall (Sek.)" en:"Interval (sec)"): </label>
<input type='text' id='boot_monitor_interval' name='boot_monitor_interval' size='4' value="$(html "${RTORRENT_BOOT_MONITOR_INTERVAL:-10}")"
	title="$(lang de:"Wie oft geprüft wird, ob rTorrent läuft (Sekunden). Beispiel: 10." en:"How often to check whether rTorrent is running (seconds). Example: 10.")">
<small>$(lang de:"(Standard: 10)" en:"(default: 10)")</small>
</p>
<p>
<label for='boot_monitor_duration' title="RTORRENT_BOOT_MONITOR_DURATION (system config)">$(lang de:"Dauer (Sek.)" en:"Duration (sec)"): </label>
<input type='text' id='boot_monitor_duration' name='boot_monitor_duration' size='5' value="$(html "${RTORRENT_BOOT_MONITOR_DURATION:-300}")"
	title="$(lang de:"Wie lange die Überwachung nach dem Boot läuft (Sekunden). Beispiel: 300 = 5 Minuten." en:"How long to monitor after boot (seconds). Example: 300 = 5 minutes.")">
<small>$(lang de:"(Standard: 300 = 5 Min.)" en:"(default: 300 = 5 min)")</small>
</p>
EOF
sec_end

# Only show ruTorrent section if ruTorrent is installed
if [ -d "/mod/external/usr/mww/rutorrent" ] || [ -d "/usr/mww/rutorrent" ]; then
	sec_begin "$(lang de:"ruTorrent" en:"ruTorrent")"
	cat << EOF
<p>
<strong>$(lang de:"ruTorrent Web-Interface" en:"ruTorrent Web Interface"):</strong> <a href="/rutorrent/" target="_blank" style="color: #007bff; font-weight: bold;">/rutorrent/</a>
</p>
<p>
<strong>$(lang de:"XMLRPC Proxy" en:"XMLRPC Proxy"):</strong> <a href="/rutorrent/rtorrent_xmlrpc_proxy.php" target="_blank" style="color: #28a745;">/rutorrent/rtorrent_xmlrpc_proxy.php</a><br>
<small style="color: #666;">$(lang de:"Ermöglicht HTTP/XMLRPC-Zugriff auf rTorrent (übersetzt XMLRPC zu SCGI). Benötigt Benutzer und Passwort des konfigurierten Freetz-Benutzers." en:"Enables HTTP/XMLRPC access to rTorrent (translates XMLRPC to SCGI). Requires username and password of the configured Freetz user.")</small>
</p>
<p>
<label for='uses_home' title="RUTORRENT_USES_HOME (ruTorrent config, not .rtorrent.rc)">$(lang de:"Home-Verzeichnis für temporäre Dateien verwenden" en:"Use home directory for temporary files"): </label>
<input type="hidden" name="uses_home" value="no">
<input type='checkbox' id='uses_home' name='uses_home' value='yes'$uses_home_chk 
       title="$(lang de:"Falls aktiviert, nutzt ruTorrent das Basisverzeichnis (basedir) für temporäre Dateien statt /tmp (RAM). Empfohlen bei vielen gleichzeitigen Uploads oder begrenztem RAM. Standard: /tmp (schneller, aber RAM-begrenzt)." en:"If enabled, ruTorrent uses the base directory (basedir) for temporary files instead of /tmp (RAM). Recommended with many simultaneous uploads or limited RAM. Default: /tmp (faster, but RAM-limited).")">
<small>$(lang de:"(Standard: /tmp, empfohlen bei < 64MB RAM: basedir)" en:"(default: /tmp, recommended with < 64MB RAM: basedir)")</small>
</p>
EOF
	sec_end
fi

sec_begin "$(lang de:"Port-Weiterleitung" en:"Port Forwarding")"
cat << EOF
<p>
<strong>$(lang de:"Wichtig" en:"Important"):</strong> $(lang de:"rTorrent benötigt offene Ports für eingehende Verbindungen. Ohne Port-Weiterleitung funktioniert nur ausgehender Verkehr." en:"rTorrent requires open ports for incoming connections. Without port forwarding, only outgoing traffic will work.")
</p>
<p>
$(lang de:"Erforderliche Ports" en:"Required ports"): <strong>TCP $PEER_PORT</strong>, <strong>UDP $PEER_PORT</strong>
</p>
EOF

if [ "$AVM_RULES_INSTALLED" = "yes" ]; then
	if [ "$AVM_TCP_CONFIGURED" = "yes" ] && [ "$AVM_UDP_CONFIGURED" = "yes" ]; then
		cat << EOF
<p style="color: green;">
&#x2713; $(lang de:"Port-Weiterleitung ist in AVM-Rules konfiguriert" en:"Port forwarding is configured in AVM-Rules")
</p>
EOF
	else
		cat << EOF
<p style="color: #c00;">
&#x2717; $(lang de:"Port-Weiterleitung ist NICHT in AVM-Rules konfiguriert" en:"Port forwarding is NOT configured in AVM-Rules")
</p>
EOF
	fi
	cat << EOF
<p>
<button type="button" onclick="window.location.href='/cgi-bin/conf/avm-rules'" class="btn">$(lang de:"AVM-Rules öffnen" en:"Open AVM-Rules")</button>
</p>
EOF
else
	cat << EOF
<p style="color: #f80;">
$(lang de:"AVM-Rules ist nicht installiert." en:"AVM-Rules is not installed.")
</p>
EOF
fi
sec_end

sec_begin "$(lang de:"Konfigurationsdateien bearbeiten" en:"Edit Configuration Files")"
cat << EOF
<p><strong>rTorrent:</strong></p>
<p>
<button type="button" onclick="window.open('/rtorrent/rtorrent_config_editor.html', '_blank')" class="btn">
$(lang de:"rTorrent Konfiguration bearbeiten" en:"Edit rTorrent configuration") (.rtorrent.rc)
</button>
EOF

if [ -n "$RTORRENT_RC_PATH" ] && [ -f "$RTORRENT_RC_PATH" ]; then
	BASEDIR_ESCAPED=$(dirname "$RTORRENT_RC_PATH" | sed 's/\//\\\//g')
	cat << EOF
<button type="button" onclick="if(confirm('$(lang de:"Sind Sie sicher, dass Sie .rtorrent.rc löschen möchten?" en:"Are you sure you want to delete .rtorrent.rc?")')) { fetch('/cgi-bin/conf/rtorrent?ajax=1&action=delete_rtorrent_rc&basedir=$(dirname "$RTORRENT_RC_PATH")').then(r=>r.text()).then(text=>{ const marker='Content-Type: application/json'; const markerPos=text.indexOf(marker); if(markerPos===-1) throw new Error('Invalid response'); const firstBrace=text.indexOf('{',markerPos+marker.length); if(firstBrace===-1) throw new Error('No JSON found'); let braceCount=0,jsonEnd=-1; for(let i=firstBrace;i<text.length;i++){ if(text[i]==='{')braceCount++; else if(text[i]==='}'){braceCount--; if(braceCount===0){jsonEnd=i+1;break;}}} if(jsonEnd===-1) throw new Error('Incomplete JSON'); const d=JSON.parse(text.substring(firstBrace,jsonEnd)); if(d.success) { alert('$(lang de:"Gelöscht" en:"Deleted")'); location.reload(); } else { alert('$(lang de:"Fehler: " en:"Error: ")' + d.message); } }).catch(err=>{alert('Error: '+err.message);}); }" class="btn" style="margin-left: 10px; background: #dc3545; color: white;">
$(lang de:"Löschen" en:"Delete") (.rtorrent.rc)
</button>
</p>
EOF
	cat << EOF
<p style="margin-top: -5px;">
<small style="color: #666; font-size: 11px;">
$(lang de:"Aktueller Pfad" en:"Current path"): <code style="background: var(--evo-bg, #f5f5f5); padding: 2px 6px; border-radius: 3px;">$RTORRENT_RC_PATH</code>
</small>
</p>
EOF
else
	cat << EOF
<p style="margin-top: -5px;">
<small style="color: #c00; font-size: 11px;">
<em>$(lang de:".rtorrent.rc existiert noch nicht. Verwenden Sie den Setup-Wizard." en:".rtorrent.rc does not exist yet. Use the Setup Wizard.")</em>
</small>
</p>
EOF
fi

cat << EOF
<p><strong>ruTorrent:</strong></p>
EOF

if [ -d "/mod/external/usr/mww/rutorrent" ] || [ -d "/usr/mww/rutorrent" ]; then
	if [ -d "/mod/external/usr/mww/rutorrent" ]; then
		RUTORRENT_PATH="/mod/external/usr/mww/rutorrent"
	else
		RUTORRENT_PATH="/usr/mww/rutorrent"
	fi
	RUTORRENT_CONFIG_FILE="${RUTORRENT_PATH}/conf/config.php"
	cat << EOF
<p>
<button type="button" onclick="window.open('/rutorrent/', '_blank')" class="btn" style="background: #28a745; color: white;">
$(lang de:"ruTorrent Web Interface öffnen" en:"Open ruTorrent Web Interface")
</button>
<button type="button" onclick="window.open('/rtorrent/rutorrent_config_editor.html', '_blank')" class="btn" style="margin-left: 10px;">
$(lang de:"ruTorrent Konfiguration bearbeiten" en:"Edit ruTorrent configuration")
</button><br/>
<small style="color: #666; font-size: 11px;">
$(lang de:"Unterstützt: config.php, freetz_config.php, plugins.ini, access.ini" en:"Supports: config.php, freetz_config.php, plugins.ini, access.ini")
</small>
</p>
EOF
else
	cat << EOF
<p><em>$(lang de:"ruTorrent ist nicht installiert" en:"ruTorrent is not installed")</em></p>
EOF
fi

sec_end

fi  # End of if [ -z "$RTORRENT_BASEDIR" ] - wizard vs normal form

# ============================================================================
# Startup Log Display
# ============================================================================
if [ -f "/tmp/rc.rtorrent.log" ]; then
	sec_begin "$(lang de:"Startup-Protokoll" en:"Startup Log")"
	cat << 'EOF'
<div style="background: var(--evo-surface, #f8f9fa); border: 1px solid var(--evo-border, #dee2e6); border-radius: 4px; padding: 12px; margin-bottom: 10px;">
	<p style="margin: 0 0 10px 0;"><strong style="color: var(--evo-text, #495057);">📋 /tmp/rc.rtorrent.log</strong></p>
	<pre style="background: #272822; color: #f8f8f2; padding: 12px; border-radius: 4px; overflow-x: auto; max-height: 400px; overflow-y: auto; margin: 0; font-family: 'Courier New', monospace; font-size: 12px; line-height: 1.5;">
EOF
	# Display log content with HTML escaping
	if [ -s "/tmp/rc.rtorrent.log" ]; then
		tail -n 200 /tmp/rc.rtorrent.log | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g'
	else
		echo "$(lang de:"(Log-Datei ist leer)" en:"(Log file is empty)")"
	fi
	cat << 'EOF'
</pre>
	<p style="margin: 10px 0 0 0; font-size: 11px; color: #6c757d;"><em>
EOF
	echo "$(lang de:"Zeigt die letzten 200 Zeilen. Bei Boot-Problemen hier nach Fehlermeldungen suchen." en:"Shows last 200 lines. Check here for error messages if rTorrent fails to start.")"
	cat << 'EOF'
</em></p>
</div>
EOF
	sec_end
fi

# ============================================================================
# Action Result Handler - URL cleanup only (no notifications)
# ============================================================================
if [ -n "$ACTION_RESULT" ]; then
	cat << EOF
<script>
(function() {
	// Clean URL immediately using history.replaceState
	if (window.history && window.history.replaceState) {
		var cleanUrl = window.location.pathname;
		window.history.replaceState({}, document.title, cleanUrl);
	}
})();
</script>
EOF
fi
