#!/bin/sh

. /usr/lib/libmodcgi.sh

[ -r /mod/etc/conf/mpd-mpc.cfg ] && . /mod/etc/conf/mpd-mpc.cfg

: ${MPD_MPC_ENABLED:=no}
: ${MPD_MPC_HOST:=/var/run/mpd/socket}
: ${MPD_MPC_PORT:=6600}
: ${MPD_MPC_PARTITION:=}
: ${MPD_MPC_PASSWORD:=}
: ${MPD_MPC_DB_URL:=https://jcorporation.github.io/webradiodb/db/index/webradiodb-combined.min.json}
: ${MPD_MPC_DB_CACHE_DIR:=/tmp/mpd-mpc}
: ${MPD_MPC_STARTUP_NAME:=}
: ${MPD_MPC_STARTUP_URI:=}
: ${MPD_MPC_STARTUP_IMAGE:=}
: ${MPD_MPC_STARTUP_HOMEPAGE:=}
: ${MPD_MPC_STARTUP_VOLUME:=}
: ${MPD_MPC_STARTUP_CLEAR:=yes}

: ${MPD_MPC_LOCAL_ROOT:=/var/media/ftp}
: ${MPD_MPC_PLAYLIST_DIR:=/var/media/ftp/playlists}
: ${MPD_MPC_MUSIC_DIR:=/var/media/ftp/mpd/music}
: ${MPD_MPC_CROSSFADE:=0}
: ${MPD_MPC_MIXRAMPDB:=0}
: ${MPD_MPC_MIXRAMPDELAY:=-1}
: ${MPD_MPC_REPLAYGAIN:=off}

# Escape function for JSON string values (must be before AJAX handler)
escape_json() {
	printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

DB_IMAGE_BASE='https://jcorporation.github.io/webradiodb/db/pics'
DB_CACHE_DIR="${MPD_MPC_DB_CACHE_DIR%/}"
DB_CACHE_FILE="${DB_CACHE_DIR}/webradiodb-combined.min.json"
LOCAL_MPD_SOCKET=/var/run/mpd/socket
LOG_FILE=/tmp/rc.mpd-mpc.log
LOCAL_ROOT="${MPD_MPC_LOCAL_ROOT:-/var/media/ftp}"
LOCAL_ROOT="${LOCAL_ROOT%/}"
[ -z "$LOCAL_ROOT" ] && LOCAL_ROOT="/var/media/ftp"
[ ! -d "$LOCAL_ROOT" ] && LOCAL_ROOT="/"
PLAYLIST_DIR="${MPD_MPC_PLAYLIST_DIR:-/var/media/ftp/playlists}"
PLAYLIST_DIR="${PLAYLIST_DIR%/}"
MUSIC_DIR="${MPD_MPC_MUSIC_DIR:-/var/media/ftp/mpd/music}"
MUSIC_DIR="${MUSIC_DIR%/}"
# Auto-detect music_directory from mpd.conf if available
if [ -z "$MPD_MPC_MUSIC_DIR" ] && [ -x /usr/bin/mpc ]; then
	CFG_DIR=$(mpc_cmd config 2>/dev/null | sed -n 's/^music_directory[[:space:]]*"\(.*\)".*/\1/p' | head -1)
	[ -n "$CFG_DIR" ] && [ -d "$CFG_DIR" ] && MUSIC_DIR="${CFG_DIR%/}" && MPD_MPC_MUSIC_DIR="$MUSIC_DIR"
fi
REFRESH="$(cgi_param refresh)"
AJAX_MODE="$(cgi_param ajax)"
ACTION="$(cgi_param action)"
STREAM_NAME="$(cgi_param stream_name)"
STREAM_URI="$(cgi_param stream_uri)"
STREAM_IMAGE="$(cgi_param stream_image)"
STREAM_HOMEPAGE="$(cgi_param stream_homepage)"
STREAM_NAME_B64="$(cgi_param stream_name_b64)"
STREAM_URI_B64="$(cgi_param stream_uri_b64)"
STREAM_IMAGE_B64="$(cgi_param stream_image_b64)"
STREAM_HOMEPAGE_B64="$(cgi_param stream_homepage_b64)"
VOLUME_VALUE="$(cgi_param volume_value)"
QUEUE_INDEX="$(cgi_param queue_index)"
FORCE_SYNC="$(cgi_param sync)"

bool_yes() {
	case "$1" in
		yes|true|1|on) return 0 ;;
		*) return 1 ;;
	esac
}

sanitize_uint() {
	case "$1" in
		''|*[!0-9]*) return 1 ;;
		*) printf '%s' "$1" ;;
	esac
}

normalize_uint() {
	value="$(sanitize_uint "$1")" || value="$2"
	if [ -n "$3" ] && [ "$value" -gt "$3" ] 2>/dev/null; then
		value="$3"
	fi
	if [ -n "$4" ] && [ "$value" -lt "$4" ] 2>/dev/null; then
		value="$4"
	fi
	printf '%s' "$value"
}

escape_sq() {
	printf '%s' "$1" | sed "s/'/'\"'\"'/g"
}

decode_base64_value() {
	encoded_value="$1"
	[ -n "$encoded_value" ] || return 1
	decoded_input="$(printf '%s' "$encoded_value" | tr '_-' '/+')"
	case $((${#decoded_input} % 4)) in
		0) ;;
		2) decoded_input="${decoded_input}==" ;;
		3) decoded_input="${decoded_input}=" ;;
		*) return 1 ;;
	esac
	if command -v base64 >/dev/null 2>&1; then
		printf '%s' "$decoded_input" | base64 -d 2>/dev/null
	elif command -v openssl >/dev/null 2>&1; then
		printf '%s' "$decoded_input" | openssl base64 -d -A 2>/dev/null
	else
		return 1
	fi
}

mpc_is_local_host() {
	case "$1" in
		''|127.0.0.1|localhost|::1|0.0.0.0|::) return 0 ;;
		*) return 1 ;;
	esac
}

mpc_default_host() {
	if [ -S "$LOCAL_MPD_SOCKET" ]; then
		printf '%s' "$LOCAL_MPD_SOCKET"
	else
		printf '%s' '127.0.0.1'
	fi
}

mpc_resolved_host() {
	case "$MPD_MPC_HOST" in
		/*|@*)
			printf '%s' "$MPD_MPC_HOST"
			;;
		*)
			if mpc_is_local_host "$MPD_MPC_HOST" && [ -S "$LOCAL_MPD_SOCKET" ]; then
				printf '%s' "$LOCAL_MPD_SOCKET"
			elif [ -n "$MPD_MPC_HOST" ]; then
				printf '%s' "$MPD_MPC_HOST"
			else
				mpc_default_host
			fi
			;;
	esac
}

mpc_host_value() {
	resolved_host="$(mpc_resolved_host)"
	case "$resolved_host" in
		/*|@*) printf '%s' "$resolved_host" ;;
		*)
			if [ -n "$MPD_MPC_PASSWORD" ]; then
				printf '%s@%s' "$MPD_MPC_PASSWORD" "$resolved_host"
			else
				printf '%s' "$resolved_host"
			fi
			;;
	esac
	}

mpc_uses_port() {
	case "$(mpc_resolved_host)" in
		/*|@*) return 1 ;;
		*) return 0 ;;
	esac
}

mpc_target_label() {
	resolved_host="$(mpc_resolved_host)"
	case "$resolved_host" in
		/*|@*) printf '%s' "$resolved_host" ;;
		*) printf '%s:%s' "$resolved_host" "$MPD_MPC_PORT" ;;
	esac
}

configured_mpc_target_label() {
	case "$MPD_MPC_HOST" in
		'') printf '%s' 'auto' ;;
		/*|@*) printf '%s' "$MPD_MPC_HOST" ;;
		*) printf '%s:%s' "$MPD_MPC_HOST" "$MPD_MPC_PORT" ;;
	esac
}

mpc_cmd() {
	host_value="$(mpc_host_value)"
	if mpc_uses_port; then
		if [ -n "$MPD_MPC_PARTITION" ]; then
			/usr/bin/mpc --host "$host_value" --port "$MPD_MPC_PORT" --partition "$MPD_MPC_PARTITION" "$@"
		else
			/usr/bin/mpc --host "$host_value" --port "$MPD_MPC_PORT" "$@"
		fi
	else
		if [ -n "$MPD_MPC_PARTITION" ]; then
			/usr/bin/mpc --host "$host_value" --partition "$MPD_MPC_PARTITION" "$@"
		else
			/usr/bin/mpc --host "$host_value" "$@"
		fi
	fi
}

ajax_json_begin() {
	cat << EOF
Content-Type: text/html; charset=UTF-8

<style>
.ajax-json-box { display: none; }
</style>
<div class="ajax-json-box"><div class="ajax-json-content"><pre>Content-Type: application/json

EOF
}

ajax_json_end() {
	echo '</pre></div></div>'
}

download_to_file() {
	url="$1"
	target="$2"
	if command -v wget >/dev/null 2>&1; then
		wget --no-check-certificate -q -O "$target" "$url" 2>/dev/null || wget -q -O "$target" "$url" 2>/dev/null
	elif command -v uclient-fetch >/dev/null 2>&1; then
		uclient-fetch -q -O "$target" "$url"
	elif command -v curl >/dev/null 2>&1; then
		curl -fsSL "$url" -o "$target"
	else
		return 1
	fi
}

refresh_db_cache() {
	tmp_file="/tmp/mpd-mpc-db.$$"
	mkdir -p "$DB_CACHE_DIR" 2>/dev/null || return 1
	if ! download_to_file "$MPD_MPC_DB_URL" "$tmp_file"; then
		rm -f "$tmp_file"
		return 1
	fi
	if ! grep -q '"webradios"' "$tmp_file" 2>/dev/null; then
		rm -f "$tmp_file"
		return 1
	fi
	mv "$tmp_file" "$DB_CACHE_FILE" 2>/dev/null || {
		rm -f "$tmp_file"
		return 1
	}
	return 0
}

resolve_image_url() {
	case "$1" in
		'') return 1 ;;
		http://*|https://*) printf '%s' "$1" ;;
		*) printf '%s/%s' "$DB_IMAGE_BASE" "${1#/}" ;;
	esac
}

binary_to_base64() {
	if command -v base64 >/dev/null 2>&1; then
		base64 | tr -d '\n'
	elif command -v openssl >/dev/null 2>&1; then
		openssl base64 -A
	else
		return 1
	fi
}

current_art_data_uri() {
	file_path="$1"
	[ -n "$file_path" ] || return 1
	for art_cmd in albumart readpicture; do
		art_b64="$(mpc_cmd "$art_cmd" "$file_path" 2>/dev/null | binary_to_base64)" || art_b64=''
		[ -n "$art_b64" ] || continue
		case "$art_b64" in
			iVBOR*) mime='image/png' ;;
			/9j/*|/9j*) mime='image/jpeg' ;;
			R0lGOD*) mime='image/gif' ;;
			UklGR*) mime='image/webp' ;;
			*) continue ;;
		esac
		printf 'data:%s;base64,%s' "$mime" "$art_b64"
		return 0
	done
	return 1
}

[ -n "$STREAM_NAME_B64" ] && STREAM_NAME="$(decode_base64_value "$STREAM_NAME_B64" 2>/dev/null || printf '%s' "$STREAM_NAME")"
[ -n "$STREAM_URI_B64" ] && STREAM_URI="$(decode_base64_value "$STREAM_URI_B64" 2>/dev/null || printf '%s' "$STREAM_URI")"
[ -n "$STREAM_IMAGE_B64" ] && STREAM_IMAGE="$(decode_base64_value "$STREAM_IMAGE_B64" 2>/dev/null || printf '%s' "$STREAM_IMAGE")"
[ -n "$STREAM_HOMEPAGE_B64" ] && STREAM_HOMEPAGE="$(decode_base64_value "$STREAM_HOMEPAGE_B64" 2>/dev/null || printf '%s' "$STREAM_HOMEPAGE")"

write_startup_config() {
	enabled_value="$1"
	name_value="$2"
	uri_value="$3"
	image_value="$4"
	homepage_value="$5"
	conf_file=/mod/etc/conf/mpd-mpc.cfg
	tmp_file="/tmp/mpd-mpc-conf.$$"
	mkdir -p /mod/etc/conf 2>/dev/null || return 1
	if [ -r "$conf_file" ]; then
		sed '/^export MPD_MPC_ENABLED=/d;/^export MPD_MPC_STARTUP_NAME=/d;/^export MPD_MPC_STARTUP_URI=/d;/^export MPD_MPC_STARTUP_IMAGE=/d;/^export MPD_MPC_STARTUP_HOMEPAGE=/d' "$conf_file" > "$tmp_file" || return 1
	else
		: > "$tmp_file" || return 1
	fi
	printf "export MPD_MPC_ENABLED='%s'\n" "$enabled_value" >> "$tmp_file"
	printf "export MPD_MPC_STARTUP_NAME='%s'\n" "$(escape_sq "$name_value")" >> "$tmp_file"
	printf "export MPD_MPC_STARTUP_URI='%s'\n" "$(escape_sq "$uri_value")" >> "$tmp_file"
	printf "export MPD_MPC_STARTUP_IMAGE='%s'\n" "$(escape_sq "$image_value")" >> "$tmp_file"
	printf "export MPD_MPC_STARTUP_HOMEPAGE='%s'\n" "$(escape_sq "$homepage_value")" >> "$tmp_file"
	mv "$tmp_file" "$conf_file" 2>/dev/null
}

print_row() {
	label="$1"
	value="$2"
	[ -n "$value" ] || return 0
	echo "<tr><td style='width:220px'><b>$(html "$label")</b></td><td>$(html "$value")</td></tr>"
}

print_link_row() {
	label="$1"
	url="$2"
	[ -n "$url" ] || return 0
	echo "<tr><td style='width:220px'><b>$(html "$label")</b></td><td><a href='$(html "$url")' target='_blank'>$(html "$url")</a></td></tr>"
}

format_size_human() {
	size_raw="$1"
	case "$size_raw" in
		''|*[!0-9]*) echo 'n/a' ; return 0 ;;
	esac
	if [ "$size_raw" -lt 1024 ] 2>/dev/null; then
		echo "${size_raw} B"
	elif [ "$size_raw" -lt 1048576 ] 2>/dev/null; then
		awk -v s="$size_raw" 'BEGIN { printf "%.1f KiB", s / 1024 }'
	else
		awk -v s="$size_raw" 'BEGIN { printf "%.1f MiB", s / 1048576 }'
	fi
}

normalize_queue_index() {
	queue_value="$(sanitize_uint "$1")" || return 1
	[ "$queue_value" -ge 1 ] 2>/dev/null || return 1
	printf '%s' "$queue_value"
}

meta_payload() {
	raw_value="$1"
	case "$raw_value" in
		*': '*)
			rest_value="${raw_value#*: }"
			case "$rest_value" in
				*'~'*)
					printf '%s' "$rest_value"
					return 0
					;;
			esac
			;;
	esac
	case "$raw_value" in
		*'~'*)
			printf '%s' "$raw_value"
			return 0
			;;
	esac
	return 1
}

meta_source() {
	raw_value="$1"
	case "$raw_value" in
		*': '*)
			rest_value="${raw_value#*: }"
			case "$rest_value" in
				*'~'*)
					printf '%s' "${raw_value%%: *}"
					return 0
					;;
			esac
			;;
	esac
	return 1
}

meta_field() {
	raw_value="$1"
	field_index="$2"
	payload_value="$(meta_payload "$raw_value")" || return 1
	printf '%s\n' "$payload_value" | awk -F'~' -v idx="$field_index" '{ if (idx <= NF) print $idx }'
}

meta_time_short() {
	short_value="$(printf '%s\n' "$1" | sed -n 's/.*T\([0-9][0-9]:[0-9][0-9]:[0-9][0-9]\).*/\1/p')"
	if [ -n "$short_value" ]; then
		printf '%s' "$short_value"
	else
		printf '%s' "$1"
	fi
}

meta_duration_human() {
	case "$1" in
		''|*[!0-9]*)
			printf '%s' "$1"
			return 0
			;;
	esac
	total_seconds="$1"
	hours=$((total_seconds / 3600))
	minutes=$(((total_seconds % 3600) / 60))
	seconds=$((total_seconds % 60))
	if [ "$hours" -gt 0 ]; then
		printf '%sh %sm %ss' "$hours" "$minutes" "$seconds"
	elif [ "$minutes" -gt 0 ]; then
		printf '%sm %ss' "$minutes" "$seconds"
	else
		printf '%ss' "$seconds"
	fi
}

format_current_metadata() {
	raw_value="$1"
	payload_value="$(meta_payload "$raw_value")" || {
		printf '%s' "$raw_value"
		return 0
	}
	title_value="$(meta_field "$raw_value" 1)"
	artist_value="$(meta_field "$raw_value" 2)"
	year_value="$(meta_field "$raw_value" 4)"
	duration_value="$(meta_field "$raw_value" 6)"
	start_value="$(meta_field "$raw_value" 7)"
	end_value="$(meta_field "$raw_value" 8)"
	station_value="$(meta_field "$raw_value" 9)"
	score_value="$(meta_field "$raw_value" 10)"
	id_value="$(meta_field "$raw_value" 11)"
	source_value="$(meta_source "$raw_value")"
	artist_year_line=''
	timing_line=''
	duration_label=''
	start_clock=''
	end_clock=''

	if [ -n "$title_value" ]; then
		printf '%s\n' "$title_value"
	else
		printf '%s\n' "$raw_value"
	fi

	if [ -n "$artist_value" ] && [ -n "$year_value" ]; then
		artist_year_line="${artist_value} | ${year_value}"
	elif [ -n "$artist_value" ]; then
		artist_year_line="$artist_value"
	elif [ -n "$year_value" ]; then
		artist_year_line="$year_value"
	fi
	[ -n "$artist_year_line" ] && printf '%s\n' "$artist_year_line"
	[ -n "$station_value" ] && printf '%s\n' "$station_value"

	[ -n "$duration_value" ] && duration_label="$(meta_duration_human "$duration_value")"
	[ -n "$start_value" ] && start_clock="$(meta_time_short "$start_value")"
	[ -n "$end_value" ] && end_clock="$(meta_time_short "$end_value")"
	if [ -n "$start_clock" ] && [ -n "$end_clock" ]; then
		timing_line="${start_clock}-${end_clock}"
	elif [ -n "$start_clock" ]; then
		timing_line="$start_clock"
	elif [ -n "$end_clock" ]; then
		timing_line="$end_clock"
	fi
	if [ -n "$duration_label" ]; then
		if [ -n "$timing_line" ]; then
			timing_line="${timing_line} | ${duration_label}"
		else
			timing_line="$duration_label"
		fi
	fi
	[ -n "$timing_line" ] && printf '%s\n' "$timing_line"
	[ -n "$score_value" ] && printf 'Score: %s\n' "$score_value"
	[ -n "$id_value" ] && printf 'ID: %s\n' "$id_value"
	[ -n "$source_value" ] && printf 'Source: %s\n' "$source_value"
}

case "$REFRESH" in
	''|*[!0-9]*) REFRESH=0 ;;
esac

if [ "$AJAX_MODE" = '1' ]; then
	ajax_json_begin
	case "$ACTION" in
		db_data)
			if [ "$FORCE_SYNC" = '1' ] || [ ! -s "$DB_CACHE_FILE" ]; then
				refresh_db_cache >/dev/null 2>&1
			fi
			if [ -s "$DB_CACHE_FILE" ]; then
				cat "$DB_CACHE_FILE"
			else
				echo '{"error":"Unable to load WebRadioDB cache","webradios":{}}'
			fi
			;;
		browse_dir)
			BROWSE_PATH="$(cgi_param path)"
			[ -z "$BROWSE_PATH" ] && BROWSE_PATH="$LOCAL_ROOT"
			[ -z "$BROWSE_PATH" ] && BROWSE_PATH="/var/media/ftp"
			[ ! -d "$BROWSE_PATH" ] && BROWSE_PATH="$LOCAL_ROOT"
			[ ! -d "$BROWSE_PATH" ] && BROWSE_PATH="/var/media/ftp"
			# Security: prevent traversal
			case "$BROWSE_PATH" in
				*..*) BROWSE_PATH="$LOCAL_ROOT" ;;
			esac
			# Strip trailing slash for consistent handling
			BROWSE_PATH="${BROWSE_PATH%/}"
			[ -z "$BROWSE_PATH" ] && BROWSE_PATH="/"
			
			echo "$(date): browse_dir BROWSE_PATH=$BROWSE_PATH LOCAL_ROOT=$LOCAL_ROOT" >> /tmp/mpd_ajax.log
			
			if [ ! -d "$BROWSE_PATH" ]; then
				echo "{\"path\":\"$(escape_json "$BROWSE_PATH")\",\"error\":\"Directory not found\",\"entries\":[]}"
			else
				printf '{"path":"%s","parent":"%s","entries":[' \
					"$(escape_json "$BROWSE_PATH")" \
					"$(escape_json "$(dirname "$BROWSE_PATH")")"
				first=1
				for entry in "$BROWSE_PATH"/*; do
					[ -e "$entry" ] || continue
					en=$(basename "$entry")
					[ "$en" = "." ] || [ "$en" = ".." ] && continue
					ep="$BROWSE_PATH/$en"
					[ $first -eq 0 ] && printf ','
					if [ -d "$entry" ]; then
						printf '{"type":"dir","name":"%s","path":"%s"}' \
							"$(escape_json "$en")" "$(escape_json "$ep")"
					elif [ -f "$entry" ]; then
						sz=$(stat -c%s "$entry" 2>/dev/null || echo 0)
						ext="${en##*.}"
						printf '{"type":"file","name":"%s","path":"%s","size":%s,"ext":"%s"}' \
							"$(escape_json "$en")" "$(escape_json "$ep")" "$sz" "$(escape_json "$ext")"
					fi
					first=0
				done
				echo ']}'
			fi
			;;
		playlist_list)
			mkdir -p "$PLAYLIST_DIR" 2>/dev/null
			echo '{'
			echo '  "files":['
			first=1
			if [ -d "$PLAYLIST_DIR" ]; then
				for f in "$PLAYLIST_DIR"/*.m3u; do
					[ -f "$f" ] || continue
					fn=$(basename "$f" .m3u)
					sz=$(stat -c%s "$f" 2>/dev/null || echo 0)
					[ $first -eq 0 ] && echo ','
					echo "    {\"name\":\"$(escape_json "$fn")\",\"path\":\"$(escape_json "$f")\",\"size\":$sz}"
					first=0
				done
			fi
			echo '  ]'
			echo '}'
			;;
		playlist_save)
			PL_NAME="$(cgi_param name)"
			[ -z "$PL_NAME" ] && { echo '{"error":"No playlist name"}'; ajax_json_end; exit 0; }
			# Sanitize name
			PL_NAME=$(echo "$PL_NAME" | sed 's/[^a-zA-Z0-9_ .-]//g')
			[ -z "$PL_NAME" ] && { echo '{"error":"Invalid playlist name"}'; ajax_json_end; exit 0; }
			mkdir -p "$PLAYLIST_DIR" 2>/dev/null
			PL_FILE="$PLAYLIST_DIR/$PL_NAME.m3u"
			if mpc_cmd playlist > "$PL_FILE" 2>/dev/null; then
				echo "{\"success\":true,\"name\":\"$(escape_json "$PL_NAME")\",\"path\":\"$(escape_json "$PL_FILE")\"}"
			else
				echo "{\"success\":false,\"error\":\"Failed to save playlist\"}"
			fi
			;;
		playlist_load)
			PL_NAME="$(cgi_param name)"
			[ -z "$PL_NAME" ] && { echo '{"error":"No playlist name"}'; ajax_json_end; exit 0; }
			PL_FILE="$PLAYLIST_DIR/$PL_NAME.m3u"
			if [ ! -f "$PL_FILE" ]; then
				echo "{\"success\":false,\"error\":\"Playlist not found\"}"
			else
				mpc_cmd stop 2>/dev/null
				mpc_cmd clear 2>/dev/null
				TMP_OUT=$(mpc_cmd load "$PL_FILE" 2>&1)
				RC=$?
				if [ $RC -eq 0 ]; then
					echo "{\"success\":true,\"name\":\"$(escape_json "$PL_NAME")\"}"
				else
					echo "{\"success\":false,\"error\":\"$(escape_json "$TMP_OUT")\"}"
				fi
			fi
			;;
		playlist_delete)
			PL_NAME="$(cgi_param name)"
			[ -z "$PL_NAME" ] && { echo '{"error":"No playlist name"}'; ajax_json_end; exit 0; }
			PL_FILE="$PLAYLIST_DIR/$PL_NAME.m3u"
			if [ -f "$PL_FILE" ] && rm -f "$PL_FILE" 2>/dev/null; then
				echo "{\"success\":true,\"name\":\"$(escape_json "$PL_NAME")\"}"
			else
				echo "{\"success\":false,\"error\":\"Failed to delete playlist\"}"
			fi
			;;
		player_crossfade)
			CF_VAL="$(cgi_param value)"
			if mpc_cmd crossfade "$CF_VAL" 2>/dev/null; then
				sed -i "s|^export MPD_MPC_CROSSFADE=.*||" /mod/etc/conf/mpd-mpc.cfg 2>/dev/null
				echo "export MPD_MPC_CROSSFADE='$CF_VAL'" >> /mod/etc/conf/mpd-mpc.cfg
				echo "{\"success\":true,\"crossfade\":\"$CF_VAL\"}"
			else
				echo "{\"success\":false,\"error\":\"Failed to set crossfade\"}"
			fi
			;;
		player_mixrampdb)
			MR_VAL="$(cgi_param value)"
			if mpc_cmd mixrampdb "$MR_VAL" 2>/dev/null; then
				sed -i "s|^export MPD_MPC_MIXRAMPDB=.*||" /mod/etc/conf/mpd-mpc.cfg 2>/dev/null
				echo "export MPD_MPC_MIXRAMPDB='$MR_VAL'" >> /mod/etc/conf/mpd-mpc.cfg
				echo "{\"success\":true,\"mixrampdb\":\"$MR_VAL\"}"
			else
				echo "{\"success\":false,\"error\":\"Failed to set mixrampdb\"}"
			fi
			;;
		player_mixrampdelay)
			MD_VAL="$(cgi_param value)"
			if mpc_cmd mixrampdelay "$MD_VAL" 2>/dev/null; then
				sed -i "s|^export MPD_MPC_MIXRAMPDELAY=.*||" /mod/etc/conf/mpd-mpc.cfg 2>/dev/null
				echo "export MPD_MPC_MIXRAMPDELAY='$MD_VAL'" >> /mod/etc/conf/mpd-mpc.cfg
				echo "{\"success\":true,\"mixrampdelay\":\"$MD_VAL\"}"
			else
				echo "{\"success\":false,\"error\":\"Failed to set mixrampdelay\"}"
			fi
			;;
		player_replaygain)
			RG_VAL="$(cgi_param value)"
			if mpc_cmd replaygain "$RG_VAL" 2>/dev/null; then
				sed -i "s|^export MPD_MPC_REPLAYGAIN=.*||" /mod/etc/conf/mpd-mpc.cfg 2>/dev/null
				echo "export MPD_MPC_REPLAYGAIN='$RG_VAL'" >> /mod/etc/conf/mpd-mpc.cfg
				echo "{\"success\":true,\"replaygain\":\"$RG_VAL\"}"
			else
				echo "{\"success\":false,\"error\":\"Failed to set replaygain\"}"
			fi
			;;
		local_add)
			LA_PATH="$(cgi_param path)"
			[ -z "$LA_PATH" ] && { echo '{"error":"No path"}'; ajax_json_end; exit 0; }
			# Quick check: is MPD running?
			if ! mpc_cmd status >/dev/null 2>&1; then
				echo '{"success":false,"error":"MPD is not running. Start it first."}'
				ajax_json_end; exit 0
			fi
			# Strip music directory prefix so MPD accepts the path
			MPD_PATH="$LA_PATH"
			[ -n "$MUSIC_DIR" ] && [ "$MUSIC_DIR" != "/" ] && MPD_PATH="${LA_PATH#"$MUSIC_DIR/"}"
			TMP_OUT=$(mpc_cmd add "$MPD_PATH" 2>&1)
			RC=$?
			if [ $RC -eq 0 ]; then
				echo "{\"success\":true,\"path\":\"$(escape_json "$LA_PATH")\"}"
			else
				echo "{\"success\":false,\"error\":\"$(escape_json "$TMP_OUT")\"}"
			fi
			;;
		local_add_dir)
			LD_PATH="$(cgi_param path)"
			[ -z "$LD_PATH" ] && { echo '{"error":"No path"}'; ajax_json_end; exit 0; }
			# Quick check: is MPD running?
			if ! mpc_cmd status >/dev/null 2>&1; then
				echo '{"success":false,"error":"MPD is not running. Start it first."}'
				ajax_json_end; exit 0
			fi
			# Recursively add all audio files from directory
			COUNT=0
			errors=""
			for f in "$LD_PATH"/*; do
				if [ -f "$f" ]; then
					ext="${f##*.}"
					case "$(echo "$ext" | tr '[:upper:]' '[:lower:]')" in
						mp3|flac|ogg|wav|m4a|aac|wma|opus|ape|wv|aiff|dsf|dff)
							MPD_PATH="$f"
							[ -n "$MUSIC_DIR" ] && [ "$MUSIC_DIR" != "/" ] && MPD_PATH="${f#"$MUSIC_DIR/"}"
							TMP_OUT=$(mpc_cmd add "$MPD_PATH" 2>&1) && COUNT=$((COUNT + 1)) || errors="${errors}$(basename "$f"): $TMP_OUT\n"
							;;
					esac
				fi
			done
			echo "{\"success\":true,\"added\":$COUNT,\"errors\":\"$(escape_json "$(echo -n "$errors" | head -20)")\"}"
			;;
		player_repeat)
			PV_VAL="$(cgi_param value)"
			if mpc_cmd repeat "$PV_VAL" 2>/dev/null; then
				echo "{\"success\":true,\"repeat\":\"$PV_VAL\"}"
			else
				echo "{\"success\":false,\"error\":\"Failed to set repeat\"}"
			fi
			;;
		player_random)
			PV_VAL="$(cgi_param value)"
			if mpc_cmd random "$PV_VAL" 2>/dev/null; then
				echo "{\"success\":true,\"random\":\"$PV_VAL\"}"
			else
				echo "{\"success\":false,\"error\":\"Failed to set random\"}"
			fi
			;;
		player_single)
			PV_VAL="$(cgi_param value)"
			if mpc_cmd single "$PV_VAL" 2>/dev/null; then
				echo "{\"success\":true,\"single\":\"$PV_VAL\"}"
			else
				echo "{\"success\":false,\"error\":\"Failed to set single\"}"
			fi
			;;
		player_consume)
			PV_VAL="$(cgi_param value)"
			if mpc_cmd consume "$PV_VAL" 2>/dev/null; then
				echo "{\"success\":true,\"consume\":\"$PV_VAL\"}"
			else
				echo "{\"success\":false,\"error\":\"Failed to set consume\"}"
			fi
			;;
		queue_list)
			Q_OFFSET="$(cgi_param offset)"
			Q_LIMIT="$(cgi_param limit)"
			case "$Q_OFFSET" in ''|*[!0-9]*) Q_OFFSET=0 ;; esac
			case "$Q_LIMIT" in ''|*[!0-9]*) Q_LIMIT=50 ;; esac
			[ "$Q_LIMIT" -gt 200 ] && Q_LIMIT=200
			Q_TOTAL=$(mpc_cmd playlist 2>/dev/null | wc -l | tr -d ' ')
			Q_START=$((Q_OFFSET + 1))
			Q_END=$((Q_OFFSET + Q_LIMIT))
			Q_POS=$(mpc_cmd status 2>/dev/null | sed -n '2{s/^.*#\([0-9]*\)\/.*$/\1/p;q}')
			echo -n "{\"total\":$Q_TOTAL,\"offset\":$Q_OFFSET,\"limit\":$Q_LIMIT,\"current\":\"$Q_POS\",\"items\":["
			n=0
			first=1
			mpc_cmd playlist 2>/dev/null | sed -n "${Q_START},${Q_END}p" | while IFS= read -r label; do
				n=$((n + 1))
				idx=$((Q_OFFSET + n))
				[ $first -eq 1 ] || printf ','
				first=0
				printf '{"n":%d,"label":"%s","cur":%s}' "$idx" "$(escape_json "$label")" "$([ "$idx" = "$Q_POS" ] && echo 'true' || echo 'false')"
			done
			echo ']}'
			;;
		*)
			echo '{"error":"Unsupported AJAX action","webradios":{}}'
			;;
	esac
	ajax_json_end
	exit 0
fi

ACTION_TITLE=''
ACTION_COMMAND=''
ACTION_OUTPUT=''
ACTION_RC=0
QUEUE_LENGTH_BEFORE="$(mpc_cmd playlist 2>/dev/null | wc -l | tr -d ' ')"

case "$QUEUE_LENGTH_BEFORE" in
	''|*[!0-9]*) QUEUE_LENGTH_BEFORE=0 ;;
esac

case "$ACTION" in
	db_sync)
		ACTION_TITLE='WebRadioDB sync'
		ACTION_COMMAND="fetch ${MPD_MPC_DB_URL}"
		if refresh_db_cache; then
			ACTION_OUTPUT="WebRadioDB cache updated: ${DB_CACHE_FILE}"
		else
			ACTION_OUTPUT='WebRadioDB refresh failed.'
			ACTION_RC=1
		fi
		;;
	queue_add)
		ACTION_TITLE='Queue station'
		ACTION_COMMAND="mpc add -- ${STREAM_URI}"
		if [ -n "$STREAM_URI" ]; then
			ACTION_OUTPUT="$(mpc_cmd add -- "$STREAM_URI" 2>&1)"
			ACTION_RC=$?
		else
			ACTION_OUTPUT='No stream URI provided.'
			ACTION_RC=1
		fi
		;;
	replace_play)
		ACTION_TITLE='Play station now'
		ACTION_COMMAND="mpc stop && mpc clear && mpc add -- ${STREAM_URI} && mpc play 1"
		if [ -n "$STREAM_URI" ]; then
			ACTION_OUTPUT="$({ mpc_cmd stop && mpc_cmd clear && mpc_cmd add -- "$STREAM_URI" && mpc_cmd play 1; } 2>&1)"
			ACTION_RC=$?
		else
			ACTION_OUTPUT='No stream URI provided.'
			ACTION_RC=1
		fi
		;;
	queue_play)
		ACTION_TITLE='Play queue entry'
		QUEUE_INDEX_VALUE="$(normalize_queue_index "$QUEUE_INDEX")" || QUEUE_INDEX_VALUE=''
		if [ -z "$QUEUE_INDEX_VALUE" ]; then
			ACTION_COMMAND='mpc play <queue_index>'
			ACTION_OUTPUT='Invalid queue index.'
			ACTION_RC=1
		elif [ "$QUEUE_INDEX_VALUE" -gt "$QUEUE_LENGTH_BEFORE" ] 2>/dev/null; then
			ACTION_COMMAND="mpc play ${QUEUE_INDEX_VALUE}"
			ACTION_OUTPUT='Queue index out of range.'
			ACTION_RC=1
		else
			ACTION_COMMAND="mpc play ${QUEUE_INDEX_VALUE}"
			ACTION_OUTPUT="$(mpc_cmd play "$QUEUE_INDEX_VALUE" 2>&1)"
			ACTION_RC=$?
		fi
		;;
	queue_remove)
		ACTION_TITLE='Remove queue entry'
		QUEUE_INDEX_VALUE="$(normalize_queue_index "$QUEUE_INDEX")" || QUEUE_INDEX_VALUE=''
		if [ -z "$QUEUE_INDEX_VALUE" ]; then
			ACTION_COMMAND='mpc del <queue_index>'
			ACTION_OUTPUT='Invalid queue index.'
			ACTION_RC=1
		elif [ "$QUEUE_INDEX_VALUE" -gt "$QUEUE_LENGTH_BEFORE" ] 2>/dev/null; then
			ACTION_COMMAND="mpc del ${QUEUE_INDEX_VALUE}"
			ACTION_OUTPUT='Queue index out of range.'
			ACTION_RC=1
		else
			ACTION_COMMAND="mpc del ${QUEUE_INDEX_VALUE}"
			ACTION_OUTPUT="$(mpc_cmd del "$QUEUE_INDEX_VALUE" 2>&1)"
			ACTION_RC=$?
		fi
		;;
	queue_move_up)
		ACTION_TITLE='Move queue entry up'
		QUEUE_INDEX_VALUE="$(normalize_queue_index "$QUEUE_INDEX")" || QUEUE_INDEX_VALUE=''
		if [ -z "$QUEUE_INDEX_VALUE" ]; then
			ACTION_COMMAND='mpc move <queue_index> <queue_index-1>'
			ACTION_OUTPUT='Invalid queue index.'
			ACTION_RC=1
		elif [ "$QUEUE_INDEX_VALUE" -gt "$QUEUE_LENGTH_BEFORE" ] 2>/dev/null; then
			ACTION_COMMAND="mpc move ${QUEUE_INDEX_VALUE} ?"
			ACTION_OUTPUT='Queue index out of range.'
			ACTION_RC=1
		elif [ "$QUEUE_INDEX_VALUE" -le 1 ] 2>/dev/null; then
			ACTION_COMMAND="mpc move ${QUEUE_INDEX_VALUE} ${QUEUE_INDEX_VALUE}"
			ACTION_OUTPUT='Queue entry is already first.'
		else
			QUEUE_TARGET_VALUE=$((QUEUE_INDEX_VALUE - 1))
			ACTION_COMMAND="mpc move ${QUEUE_INDEX_VALUE} ${QUEUE_TARGET_VALUE}"
			ACTION_OUTPUT="$(mpc_cmd move "$QUEUE_INDEX_VALUE" "$QUEUE_TARGET_VALUE" 2>&1)"
			ACTION_RC=$?
		fi
		;;
	queue_move_down)
		ACTION_TITLE='Move queue entry down'
		QUEUE_INDEX_VALUE="$(normalize_queue_index "$QUEUE_INDEX")" || QUEUE_INDEX_VALUE=''
		if [ -z "$QUEUE_INDEX_VALUE" ]; then
			ACTION_COMMAND='mpc move <queue_index> <queue_index+1>'
			ACTION_OUTPUT='Invalid queue index.'
			ACTION_RC=1
		elif [ "$QUEUE_INDEX_VALUE" -gt "$QUEUE_LENGTH_BEFORE" ] 2>/dev/null; then
			ACTION_COMMAND="mpc move ${QUEUE_INDEX_VALUE} ?"
			ACTION_OUTPUT='Queue index out of range.'
			ACTION_RC=1
		elif [ "$QUEUE_INDEX_VALUE" -ge "$QUEUE_LENGTH_BEFORE" ] 2>/dev/null; then
			ACTION_COMMAND="mpc move ${QUEUE_INDEX_VALUE} ${QUEUE_INDEX_VALUE}"
			ACTION_OUTPUT='Queue entry is already last.'
		else
			QUEUE_TARGET_VALUE=$((QUEUE_INDEX_VALUE + 1))
			ACTION_COMMAND="mpc move ${QUEUE_INDEX_VALUE} ${QUEUE_TARGET_VALUE}"
			ACTION_OUTPUT="$(mpc_cmd move "$QUEUE_INDEX_VALUE" "$QUEUE_TARGET_VALUE" 2>&1)"
			ACTION_RC=$?
		fi
		;;
	queue_shuffle)
		ACTION_TITLE='Shuffle queue'
		ACTION_COMMAND='mpc shuffle'
		ACTION_OUTPUT="$(mpc_cmd shuffle 2>&1)"
		ACTION_RC=$?
		;;
	player_prev)
		ACTION_TITLE='Previous'
		ACTION_COMMAND='mpc prev'
		ACTION_OUTPUT="$(mpc_cmd prev 2>&1)"
		ACTION_RC=$?
		;;
	player_next)
		ACTION_TITLE='Next'
		ACTION_COMMAND='mpc next'
		ACTION_OUTPUT="$(mpc_cmd next 2>&1)"
		ACTION_RC=$?
		;;
	player_seek_back)
		ACTION_TITLE='Seek backward'
		ACTION_COMMAND='mpc seek -00:00:10'
		ACTION_OUTPUT="$(mpc_cmd seek -00:00:10 2>&1)"
		ACTION_RC=$?
		;;
	player_seek_forward)
		ACTION_TITLE='Seek forward'
		ACTION_COMMAND='mpc seek +00:00:10'
		ACTION_OUTPUT="$(mpc_cmd seek +00:00:10 2>&1)"
		ACTION_RC=$?
		;;
	player_play)
		ACTION_TITLE='Play'
		ACTION_COMMAND='mpc play'
		ACTION_OUTPUT="$(mpc_cmd play 2>&1)"
		ACTION_RC=$?
		;;
	player_pause)
		ACTION_TITLE='Pause'
		ACTION_COMMAND='mpc pause'
		ACTION_OUTPUT="$(mpc_cmd pause 2>&1)"
		ACTION_RC=$?
		;;
	player_toggle)
		ACTION_TITLE='Toggle'
		ACTION_COMMAND='mpc toggle'
		ACTION_OUTPUT="$(mpc_cmd toggle 2>&1)"
		ACTION_RC=$?
		;;
	player_stop)
		ACTION_TITLE='Stop'
		ACTION_COMMAND='mpc stop'
		ACTION_OUTPUT="$(mpc_cmd stop 2>&1)"
		ACTION_RC=$?
		;;
	player_clear)
		ACTION_TITLE='Clear queue'
		ACTION_COMMAND='mpc clear'
		ACTION_OUTPUT="$(mpc_cmd clear 2>&1)"
		ACTION_RC=$?
		;;
	player_current)
		ACTION_TITLE='Current track'
		ACTION_COMMAND='mpc current'
		ACTION_OUTPUT="$(mpc_cmd current 2>&1)"
		ACTION_RC=$?
		;;
	player_status)
		ACTION_TITLE='Status'
		ACTION_COMMAND='mpc status'
		ACTION_OUTPUT="$(mpc_cmd status 2>&1)"
		ACTION_RC=$?
		;;
	volume_set)
		ACTION_TITLE='Volume'
		VOLUME_VALUE="$(normalize_uint "$VOLUME_VALUE" 50 100 0)"
		ACTION_COMMAND="mpc volume ${VOLUME_VALUE}"
		ACTION_OUTPUT="$(mpc_cmd volume "$VOLUME_VALUE" 2>&1)"
		ACTION_RC=$?
		;;
	save_startup)
		ACTION_TITLE='Save startup profile'
		ACTION_COMMAND='write saved startup config'
		if [ -n "$STREAM_URI" ]; then
			if write_startup_config yes "$STREAM_NAME" "$STREAM_URI" "$STREAM_IMAGE" "$STREAM_HOMEPAGE"; then
				MPD_MPC_ENABLED='yes'
				MPD_MPC_STARTUP_NAME="$STREAM_NAME"
				MPD_MPC_STARTUP_URI="$STREAM_URI"
				MPD_MPC_STARTUP_IMAGE="$STREAM_IMAGE"
				MPD_MPC_STARTUP_HOMEPAGE="$STREAM_HOMEPAGE"
				ACTION_OUTPUT='Startup profile saved and autoplay enabled.'
			else
				ACTION_OUTPUT='Failed to write startup profile.'
				ACTION_RC=1
			fi
		else
			ACTION_OUTPUT='No stream URI provided.'
			ACTION_RC=1
		fi
		;;
	disable_autoplay)
		ACTION_TITLE='Disable autoplay'
		ACTION_COMMAND='set MPD_MPC_ENABLED=no'
		if write_startup_config no "$MPD_MPC_STARTUP_NAME" "$MPD_MPC_STARTUP_URI" "$MPD_MPC_STARTUP_IMAGE" "$MPD_MPC_STARTUP_HOMEPAGE"; then
			MPD_MPC_ENABLED='no'
			ACTION_OUTPUT='Autoplay disabled.'
		else
			ACTION_OUTPUT='Failed to update saved configuration.'
			ACTION_RC=1
		fi
		;;
esac

# -----------------------------------------------------------------------
# MPD connectivity check — block UI if MPD isn't running
# -----------------------------------------------------------------------
if ! mpc_cmd status >/dev/null 2>&1; then
	cat << 'MPD_DOWN_HTML'
<!DOCTYPE html>
<html lang="en">
<head>
	<meta charset="UTF-8">
	<meta name="viewport" content="width=device-width, initial-scale=1.0">
	<title>MPD Status</title>
	<style>
		* { box-sizing: border-box; margin: 0; padding: 0; }
		body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #f5f0e8 0%, #e8dcc8 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; }
		.mpd-down-card { background: #fff; border-radius: 16px; padding: 40px; max-width: 520px; width: 90%; box-shadow: 0 4px 20px rgba(0,0,0,0.1); text-align: center; }
		.mpd-down-icon { font-size: 64px; margin-bottom: 20px; }
		.mpd-down-title { font-size: 22px; font-weight: bold; color: #333; margin-bottom: 12px; }
		.mpd-down-msg { font-size: 15px; color: #666; line-height: 1.6; margin-bottom: 24px; }
		.mpd-down-btn { display: inline-block; background: #667eea; color: #fff; padding: 12px 28px; border-radius: 8px; text-decoration: none; font-weight: bold; font-size: 15px; transition: background .2s; }
		.mpd-down-btn:hover { background: #5a6fd6; }
		.mpd-down-links { margin-top: 20px; font-size: 13px; color: #999; }
		.mpd-down-links a { color: #667eea; text-decoration: none; }
	</style>
</head>
<body>
<div class='mpd-down-card'>
	<div class='mpd-down-icon'>🎵</div>
	<div class='mpd-down-title'>MPD is not running</div>
	<div class='mpd-down-msg'>
		Start the MPD daemon to use this page.<br>
		Use the Freetz web interface or run:
		<br><code style='background:#f0f0f0;padding:4px 8px;border-radius:4px;'>/etc/init.d/rc.mpd start</code>
	</div>
	<a class='mpd-down-btn' href='javascript:window.location.reload()'>🔄 Refresh</a>
	<div class='mpd-down-links'>
		<a href='/cgi-bin/conf/mpd-mpc'>MPD-MPC Configuration</a>
	</div>
</div>
</body>
</html>
MPD_DOWN_HTML
	exit 0
fi
# -----------------------------------------------------------------------

if [ -n "$ACTION" ] && [ -z "$ACTION_OUTPUT" ]; then
	ACTION_OUTPUT='Command completed with no output.'
fi

if [ -n "$STREAM_NAME$STREAM_URI$STREAM_IMAGE$STREAM_HOMEPAGE" ]; then
	MANUAL_NAME="$STREAM_NAME"
	MANUAL_URI="$STREAM_URI"
	MANUAL_IMAGE="$STREAM_IMAGE"
	MANUAL_HOMEPAGE="$STREAM_HOMEPAGE"
else
	MANUAL_NAME="$MPD_MPC_STARTUP_NAME"
	MANUAL_URI="$MPD_MPC_STARTUP_URI"
	MANUAL_IMAGE="$MPD_MPC_STARTUP_IMAGE"
	MANUAL_HOMEPAGE="$MPD_MPC_STARTUP_HOMEPAGE"
fi

CURRENT_TITLE="$(mpc_cmd current 2>/dev/null | sed -n '1p')"
CURRENT_URI="$(mpc_cmd --format '%file%' current 2>/dev/null | sed -n '1p')"
CURRENT_STATUS_RAW="$(mpc_cmd status 2>&1)"
STATUS_RC=$?
CURRENT_VOLUME_LINE="$(printf '%s\n%s\n' "$CURRENT_STATUS_RAW" "$(mpc_cmd volume 2>/dev/null)" | sed -n '/volume:/p' | sed -n '1p')"
CURRENT_VOLUME="$(printf '%s\n' "$CURRENT_VOLUME_LINE" | sed -n 's/^.*volume:[[:space:]]*\([0-9][0-9]*\)%.*/\1/p')"
CURRENT_VOLUME_SAFE="$(normalize_uint "$CURRENT_VOLUME" 0 100 0)"
# MPD toggle states: repeat, random, single, consume
MPD_REPEAT_STATE="$(printf '%s\n' "$CURRENT_STATUS_RAW" | sed -n 's/.*repeat:[[:space:]]*\([^[:space:]]*\).*/\1/p' | head -1)"
MPD_RANDOM_STATE="$(printf '%s\n' "$CURRENT_STATUS_RAW" | sed -n 's/.*random:[[:space:]]*\([^[:space:]]*\).*/\1/p' | head -1)"
MPD_SINGLE_STATE="$(printf '%s\n' "$CURRENT_STATUS_RAW" | sed -n 's/.*single:[[:space:]]*\([^[:space:]]*\).*/\1/p' | head -1)"
MPD_CONSUME_STATE="$(printf '%s\n' "$CURRENT_STATUS_RAW" | sed -n 's/.*consume:[[:space:]]*\([^[:space:]]*\).*/\1/p' | head -1)"
[ "$MPD_REPEAT_STATE" = 'on' ] || [ "$MPD_REPEAT_STATE" = '1' ] || MPD_REPEAT_STATE='off'
[ "$MPD_RANDOM_STATE" = 'on' ] || [ "$MPD_RANDOM_STATE" = '1' ] || MPD_RANDOM_STATE='off'
[ "$MPD_SINGLE_STATE" = 'on' ] || [ "$MPD_SINGLE_STATE" = '1' ] || MPD_SINGLE_STATE='off'
[ "$MPD_CONSUME_STATE" = 'on' ] || [ "$MPD_CONSUME_STATE" = '1' ] || MPD_CONSUME_STATE='off'
PLAYLIST_FULL="$(mpc_cmd playlist 2>/dev/null)"
if [ -n "$PLAYLIST_FULL" ]; then
	QUEUE_LENGTH="$(printf '%s\n' "$PLAYLIST_FULL" | wc -l | tr -d ' ')"
	PLAYLIST_PREVIEW="$(printf '%s\n' "$PLAYLIST_FULL" | sed -n '1,8p')"
else
	QUEUE_LENGTH=0
	PLAYLIST_PREVIEW=''
fi
CURRENT_STATE="$(printf '%s\n' "$CURRENT_STATUS_RAW" | sed -n '2{s/^\[\([^]]*\)\].*/\1/p;q}')"
CURRENT_QUEUE_POS="$(printf '%s\n' "$CURRENT_STATUS_RAW" | sed -n '2{s/^.*#\([0-9][0-9]*\/[0-9][0-9]*\).*$/\1/p;q}')"
CURRENT_QUEUE_INDEX=''
case "$CURRENT_QUEUE_POS" in
	*/*) CURRENT_QUEUE_INDEX="${CURRENT_QUEUE_POS%%/*}" ;;
esac
CURRENT_TIMELINE="$(printf '%s\n' "$CURRENT_STATUS_RAW" | sed -n '2{s/^.* \([0-9][0-9:]*\/[0-9][0-9:]*\) (.*$/\1/p;q}')"
CURRENT_ELAPSED=''
CURRENT_TOTAL=''
CURRENT_PROGRESS_PERCENT="$(printf '%s\n' "$CURRENT_STATUS_RAW" | sed -n '2{s/^.*(\([0-9][0-9]*%\)).*$/\1/p;q}')"
CURRENT_HAS_TIMELINE=no
CURRENT_PLAYBACK_TIMELINE=''
case "$CURRENT_TIMELINE" in
	*/*)
		CURRENT_ELAPSED="${CURRENT_TIMELINE%%/*}"
		CURRENT_TOTAL="${CURRENT_TIMELINE#*/}"
		case "$CURRENT_TOTAL" in
			''|0:00|00:00|0:00:00|00:00:00) ;;
			*) CURRENT_HAS_TIMELINE=yes ;;
		esac
		;;
esac
if [ "$CURRENT_HAS_TIMELINE" = 'yes' ]; then
	CURRENT_PLAYBACK_TIMELINE="${CURRENT_ELAPSED} / ${CURRENT_TOTAL}"
	if [ -n "$CURRENT_PROGRESS_PERCENT" ]; then
		CURRENT_PLAYBACK_TIMELINE="${CURRENT_PLAYBACK_TIMELINE} (${CURRENT_PROGRESS_PERCENT})"
	fi
fi
CURRENT_META_TITLE=''
CURRENT_META_ARTIST=''
CURRENT_META_YEAR=''
CURRENT_META_DURATION=''
CURRENT_META_START=''
CURRENT_META_END=''
CURRENT_META_STATION=''
CURRENT_META_SCORE=''
CURRENT_META_ID=''
CURRENT_META_SOURCE=''
CURRENT_TITLE_DISPLAY="$CURRENT_TITLE"
CURRENT_META_ARTIST_YEAR=''
CURRENT_META_TIME_RANGE=''
CURRENT_META_DURATION_HUMAN=''
CURRENT_FORMATTED_TITLE="$CURRENT_TITLE"
CURRENT_CONTROL_HEADLINE=''
CURRENT_STATE_LABEL=''
CURRENT_VOLUME_LABEL=''
QUEUE_STATUS_BADGE=''

if meta_payload "$CURRENT_TITLE" >/dev/null 2>&1; then
	CURRENT_META_TITLE="$(meta_field "$CURRENT_TITLE" 1)"
	CURRENT_META_ARTIST="$(meta_field "$CURRENT_TITLE" 2)"
	CURRENT_META_YEAR="$(meta_field "$CURRENT_TITLE" 4)"
	CURRENT_META_DURATION="$(meta_field "$CURRENT_TITLE" 6)"
	CURRENT_META_START="$(meta_field "$CURRENT_TITLE" 7)"
	CURRENT_META_END="$(meta_field "$CURRENT_TITLE" 8)"
	CURRENT_META_STATION="$(meta_field "$CURRENT_TITLE" 9)"
	CURRENT_META_SCORE="$(meta_field "$CURRENT_TITLE" 10)"
	CURRENT_META_ID="$(meta_field "$CURRENT_TITLE" 11)"
	CURRENT_META_SOURCE="$(meta_source "$CURRENT_TITLE")"
	CURRENT_TITLE_DISPLAY="$CURRENT_META_TITLE"
	[ -n "$CURRENT_TITLE_DISPLAY" ] || CURRENT_TITLE_DISPLAY="$CURRENT_TITLE"
	if [ -n "$CURRENT_META_ARTIST" ] && [ -n "$CURRENT_META_YEAR" ]; then
		CURRENT_META_ARTIST_YEAR="${CURRENT_META_ARTIST} | ${CURRENT_META_YEAR}"
	elif [ -n "$CURRENT_META_ARTIST" ]; then
		CURRENT_META_ARTIST_YEAR="$CURRENT_META_ARTIST"
	elif [ -n "$CURRENT_META_YEAR" ]; then
		CURRENT_META_ARTIST_YEAR="$CURRENT_META_YEAR"
	fi
	[ -n "$CURRENT_META_DURATION" ] && CURRENT_META_DURATION_HUMAN="$(meta_duration_human "$CURRENT_META_DURATION")"
	if [ -n "$CURRENT_META_START" ] && [ -n "$CURRENT_META_END" ]; then
		CURRENT_META_TIME_RANGE="$(meta_time_short "$CURRENT_META_START")-$(meta_time_short "$CURRENT_META_END")"
	elif [ -n "$CURRENT_META_START" ]; then
		CURRENT_META_TIME_RANGE="$(meta_time_short "$CURRENT_META_START")"
	elif [ -n "$CURRENT_META_END" ]; then
		CURRENT_META_TIME_RANGE="$(meta_time_short "$CURRENT_META_END")"
	fi
	CURRENT_FORMATTED_TITLE="$(format_current_metadata "$CURRENT_TITLE")"
fi

CURRENT_CONTROL_HEADLINE="$CURRENT_TITLE_DISPLAY"
if [ -n "$CURRENT_META_STATION" ]; then
	if [ -n "$CURRENT_CONTROL_HEADLINE" ] && [ "$CURRENT_CONTROL_HEADLINE" != "$CURRENT_META_STATION" ]; then
		CURRENT_CONTROL_HEADLINE="${CURRENT_CONTROL_HEADLINE} | ${CURRENT_META_STATION}"
	elif [ -z "$CURRENT_CONTROL_HEADLINE" ]; then
		CURRENT_CONTROL_HEADLINE="$CURRENT_META_STATION"
	fi
fi
[ -n "$CURRENT_CONTROL_HEADLINE" ] || CURRENT_CONTROL_HEADLINE="$(lang de:"Keine aktive Wiedergabe." en:"No active playback.")"
CURRENT_STATE_LABEL="$CURRENT_STATE"
[ -n "$CURRENT_STATE_LABEL" ] || CURRENT_STATE_LABEL="$(lang de:"unbekannt" en:"unknown")"
if [ -n "$CURRENT_VOLUME" ]; then
	CURRENT_VOLUME_LABEL="${CURRENT_VOLUME}%"
else
	CURRENT_VOLUME_LABEL='n/a'
fi
QUEUE_STATUS_BADGE="$QUEUE_LENGTH"
[ -n "$CURRENT_QUEUE_POS" ] && QUEUE_STATUS_BADGE="$CURRENT_QUEUE_POS"

HOMEPAGE_FALLBACK=''
if [ -n "$CURRENT_URI" ] && [ "$CURRENT_URI" = "$STREAM_URI" ]; then
	HOMEPAGE_FALLBACK="$STREAM_HOMEPAGE"
elif [ -n "$CURRENT_URI" ] && [ "$CURRENT_URI" = "$MPD_MPC_STARTUP_URI" ]; then
	HOMEPAGE_FALLBACK="$MPD_MPC_STARTUP_HOMEPAGE"
fi
CURRENT_ART_DATA_URI="$(current_art_data_uri "$CURRENT_URI")"
CONFIGURED_MPD_TARGET="$(configured_mpc_target_label)"
RESOLVED_MPD_TARGET="$(mpc_target_label)"
MPD_TARGET_NOTE=''
if mpc_is_local_host "$MPD_MPC_HOST" && [ "$RESOLVED_MPD_TARGET" = "$LOCAL_MPD_SOCKET" ]; then
	MPD_TARGET_NOTE="$(lang de:"Lokaler Unix-Socket automatisch verwendet." en:"Using local Unix socket automatically.")"
fi
DASHBOARD_CLASS='mpc-dashboard'
[ -n "$CURRENT_ART_DATA_URI" ] || DASHBOARD_CLASS='mpc-dashboard mpc-dashboard-no-art'

if [ "$ACTION" = 'player_current' ] && [ "$ACTION_RC" -eq 0 ] && [ -n "$CURRENT_FORMATTED_TITLE" ]; then
	ACTION_OUTPUT="$CURRENT_FORMATTED_TITLE"
fi

if [ -z "$ACTION_TITLE" ]; then
	ACTION_TITLE='Current snapshot'
	ACTION_COMMAND='mpc current && mpc status'
	ACTION_OUTPUT="${CURRENT_FORMATTED_TITLE}

${CURRENT_STATUS_RAW}"
fi

DB_CACHE_STATE='missing'
DB_CACHE_SIZE='n/a'
if [ -e "$DB_CACHE_DIR" ] && [ ! -d "$DB_CACHE_DIR" ]; then
	DB_CACHE_STATE='invalid-dir'
elif [ -s "$DB_CACHE_FILE" ]; then
	DB_CACHE_STATE='cached'
	DB_CACHE_SIZE_RAW="$(wc -c < "$DB_CACHE_FILE" 2>/dev/null)"
	DB_CACHE_SIZE="$(format_size_human "$DB_CACHE_SIZE_RAW")"
elif [ -f "$DB_CACHE_FILE" ]; then
	DB_CACHE_STATE='empty'
	DB_CACHE_SIZE='0 B'
fi

if [ "$REFRESH" -gt 0 ] 2>/dev/null; then
	cat << EOF
<script type='text/javascript'>
window.setTimeout(function () { window.location.reload(); }, ${REFRESH}000);
</script>
EOF
fi

cat << EOF
<style type='text/css'>
.mpc-dashboard { display:grid; grid-template-columns: minmax(340px, 2fr) minmax(260px, 1fr); gap:16px; margin:10px 0 16px; }
.mpc-dashboard-no-art { grid-template-columns:minmax(340px, 1fr); }
.mpc-card { background:#f8f3e7; border:1px solid #dbcdae; border-radius:12px; padding:14px; box-shadow:0 1px 0 rgba(0,0,0,0.05); }
.mpc-card h3 { margin:0 0 10px; font-size:17px; color:#3d2b16; }
.mpc-meta { display:flex; flex-wrap:wrap; gap:8px; margin:8px 0 0; }
.mpc-badge { background:#efe3c7; color:#5f4520; border-radius:999px; padding:4px 10px; font-size:12px; }
.mpc-art { min-height:180px; display:flex; align-items:center; justify-content:center; padding:14px; background:linear-gradient(135deg, #f3e3c0 0%, #f9f6ee 100%); border:1px dashed #c2ad82; border-radius:12px; overflow:hidden; box-sizing:border-box; }
.mpc-art img { display:block; width:auto; height:auto; max-width:min(100%, 180px); max-height:180px; object-fit:contain; }
.mpc-actions { display:flex; flex-wrap:wrap; gap:8px; margin:10px 0; }
.mpc-actions form { display:inline-flex; align-items:center; gap:6px; margin:0; }
.mpc-actions input[type='text'] { width:72px; }
.mpc-control-summary { display:flex; justify-content:space-between; align-items:flex-start; gap:14px; padding:12px 14px; margin:0 0 14px; background:#fff8ea; border:1px solid #e5d4b1; border-radius:12px; }
.mpc-control-summary strong { display:block; color:#3d2b16; font-size:15px; }
.mpc-control-summary span { display:block; margin-top:4px; color:#6b5328; }
.mpc-control-summary .mpc-meta { margin:0; justify-content:flex-end; }
.mpc-control-layout { display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:12px; }
.mpc-control-card { background:#fffdf8; border:1px solid #e3d4b7; border-radius:12px; padding:14px; }
.mpc-control-card h4 { margin:0 0 6px; color:#352412; font-size:15px; }
.mpc-control-card p { margin:0 0 10px; color:#6b5328; font-size:13px; }
.mpc-control-actions { margin:0; }
.mpc-control-volume { display:grid; gap:10px; }
.mpc-control-volume-row { display:grid; grid-template-columns:minmax(0, 1fr) auto auto; gap:10px; align-items:center; }
.mpc-control-volume input[type='range'] { width:100%; accent-color:#b57f24; }
.mpc-control-volume-value { min-width:54px; text-align:center; font-weight:700; color:#5f4520; background:#efe3c7; border-radius:999px; padding:4px 8px; }
.mpc-control-presets { margin-top:10px; }
.mpc-console { background:#1f1a15; color:#f7eedf; border-radius:12px; padding:14px; overflow:auto; }
.mpc-console .cmd { color:#ffd27a; margin-bottom:8px; }
.mpc-console pre { margin:0; white-space:pre-wrap; word-break:break-word; }
.mpc-manual-grid { display:grid; grid-template-columns:repeat(2, minmax(180px, 1fr)); gap:10px 14px; }
.mpc-manual-grid label { display:block; font-weight:600; margin-bottom:4px; }
.mpc-manual-grid input[type='text'] { width:100%; box-sizing:border-box; }
.mpc-browser-tools { display:grid; grid-template-columns:2fr repeat(4, minmax(120px, 1fr)); gap:10px; margin:10px 0 14px; }
.mpc-browser-tools input,
.mpc-browser-tools select { width:100%; box-sizing:border-box; }
.mpc-browser-status { display:flex; justify-content:space-between; gap:12px; margin-bottom:10px; font-size:13px; color:#5d4a26; }
.mpc-station-grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(210px, 280px)); justify-content:start; gap:14px; }
.mpc-station-card { width:100%; max-width:280px; justify-self:start; background:#fffdf8; border:1px solid #e3d4b7; border-radius:14px; overflow:hidden; box-shadow:0 1px 0 rgba(0,0,0,0.04); }
.mpc-station-thumb { aspect-ratio:16 / 10; max-height:136px; padding:12px; box-sizing:border-box; background:linear-gradient(135deg, #d6a24a 0%, #f6e7c8 100%); display:flex; align-items:center; justify-content:center; color:#fff7e8; font-size:15px; letter-spacing:0.08em; }
.mpc-station-thumb img { width:auto; height:auto; max-width:100%; max-height:100%; object-fit:contain; display:block; border-radius:10px; background:#fffdf8; }
.mpc-station-body { padding:14px; }
.mpc-station-body h4 { margin:0 0 8px; color:#352412; font-size:16px; }
.mpc-station-body p { margin:0 0 10px; color:#5d4a26; min-height:38px; }
.mpc-tags { display:flex; flex-wrap:wrap; gap:6px; margin:0 0 12px; }
.mpc-tag { background:#f3ead8; border-radius:999px; color:#654d25; font-size:12px; padding:3px 8px; }
.mpc-station-buttons { display:flex; flex-wrap:wrap; gap:8px; }
.mpc-station-buttons form { margin:0; }
.mpc-queue-toolbar { display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin:0 0 12px; }
.mpc-queue-toolbar form { margin:0; }
.mpc-queue-info { font-size:13px; color:#666; white-space:nowrap; }
.mpc-table { width:100%; border-collapse:collapse; border-radius:8px; overflow:hidden; }
.mpc-table thead th { background:#667eea; color:#fff; padding:10px 12px; text-align:left; font-size:13px; font-weight:600; white-space:nowrap; cursor:pointer; user-select:none; }
.mpc-table thead th:hover { background:#5a6fd6; }
.mpc-table thead th.sorted:after { margin-left:4px; opacity:0.7; }
.mpc-table thead th.sorted.asc:after { content:' \u25b2'; }
.mpc-table thead th.sorted.desc:after { content:' \u25bc'; }
.mpc-table tbody td { padding:8px 12px; border-bottom:1px solid #eee; font-size:13px; vertical-align:middle; }
.mpc-table tbody tr:hover td { background:#f0f4ff; }
.mpc-table tbody tr.playing td { background:#fff6df; border-color:#e3d4b7; }
.mpc-table .col-index { width:50px; font-weight:700; color:#6a4c1e; text-align:center; }
.mpc-table .col-actions { white-space:nowrap; text-align:right; }
.mpc-table .col-actions button, .mpc-table .col-actions form { display:inline; margin:0 2px; }
.mpc-table .col-actions button { padding:4px 10px; border-radius:4px; cursor:pointer; font-size:11px; border:1px solid #ccc; background:#fff; color:#333; }
.mpc-table .col-actions button:hover { background:#667eea; color:#fff; border-color:#667eea; }
.mpc-table .playing-badge { display:inline-block; background:#e3d4b7; color:#5f4520; border-radius:999px; padding:2px 7px; font-size:11px; margin-right:6px; }
.mpc-pager { display:flex; align-items:center; justify-content:center; gap:8px; padding:12px; flex-wrap:wrap; }
.mpc-pager button { padding:6px 14px; border-radius:6px; cursor:pointer; border:1px solid #ccc; background:#fff; color:#333; font-size:13px; }
.mpc-pager button:hover:not(:disabled) { background:#667eea; color:#fff; border-color:#667eea; }
.mpc-pager button:disabled { opacity:0.4; cursor:default; }
.mpc-pager span { font-size:13px; color:#666; }
.mpc-pager select { padding:5px 6px; border-radius:6px; border:1px solid #ccc; font-size:13px; background:#fff; color:#333; }
.mpc-pager .mpc-pager-label { font-size:13px; color:#888; }
.mpc-pager .mpc-page-input { width:60px; padding:5px 8px; border-radius:6px; border:1px solid #ccc; font-size:13px; text-align:center; background:#fff; color:#333; }
.mpc-pager .mpc-page-input:focus { outline:none; border-color:#667eea; box-shadow:0 0 0 2px rgba(102,126,234,.25); }
.mpc-pager .mpc-page-total { font-size:13px; color:#999; }
.mpc-browser-toolbar { display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin-bottom:10px; }
.mpc-browser-path { display:flex; align-items:center; gap:6px; flex:1; min-width:0; }
.mpc-browser-path button { padding:6px 10px; border-radius:4px; cursor:pointer; border:1px solid #ccc; background:#333; color:#fff; font-size:13px; }
.mpc-browser-path button:hover { background:#fff; color:#333; }
.mpc-browser-path-text { flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-family:monospace; font-size:13px; }
.mpc-browser-actions { display:flex; gap:6px; }
.mpc-browser-actions button { padding:6px 12px; border-radius:4px; cursor:pointer; border:1px solid #ccc; background:#333; color:#fff; font-size:13px; }
.mpc-browser-actions button:hover { background:#fff; color:#333; }
.mpc-browser-actions .btn-primary { background:#28a745; color:#fff; border-color:#28a745; }
.mpc-browser-actions .btn-primary:hover { background:#218838; }
.mpc-browser-grid { max-height:400px; overflow-y:auto; border:1px solid #e0e0e0; border-radius:8px; }
.mpc-table .file-icon { font-size:18px; min-width:24px; text-align:center; }
.mpc-table .file-name { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.mpc-table .file-size { font-size:11px; color:#999; white-space:nowrap; }
.mpc-table .td-name { max-width:0; width:100%; }
@media (max-width:640px) {
	.mpc-table .col-actions button span { display:none; }
	.mpc-queue-toolbar { flex-direction:column; align-items:stretch; }
	.mpc-browser-toolbar { flex-direction:column; }
}
.mpc-queue-list { display:flex; flex-direction:column; gap:10px; }
.mpc-queue-row { display:grid; grid-template-columns:auto 1fr auto; gap:10px; align-items:center; padding:10px 12px; background:#fffdf8; border:1px solid #e3d4b7; border-radius:12px; }
.mpc-queue-row-current { border-color:#d6a24a; background:#fff6df; }
.mpc-queue-index { min-width:40px; font-weight:700; color:#6a4c1e; }
.mpc-queue-label { color:#352412; overflow-wrap:anywhere; }
.mpc-queue-actions { display:flex; flex-wrap:wrap; gap:6px; justify-content:flex-end; }
.mpc-queue-actions form { margin:0; }
.mpc-queue-state { display:inline-block; margin:0 8px 4px 0; background:#efe3c7; color:#5f4520; border-radius:999px; padding:3px 8px; font-size:12px; }
.mpc-empty { padding:18px; border:1px dashed #c8b089; border-radius:12px; background:#fffaf0; color:#6c552b; }
@media (max-width: 960px) {
	.mpc-dashboard { grid-template-columns:1fr; }
	.mpc-browser-tools { grid-template-columns:1fr 1fr; }
	.mpc-manual-grid { grid-template-columns:1fr; }
	.mpc-control-summary { flex-direction:column; }
	.mpc-control-summary .mpc-meta { justify-content:flex-start; }
	.mpc-control-volume-row { grid-template-columns:1fr auto; }
	.mpc-control-volume-row input[type='submit'] { grid-column:1 / -1; }
	.mpc-queue-row { grid-template-columns:1fr; }
	.mpc-queue-actions { justify-content:flex-start; }
}
.mpc-effects-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:16px; }
.mpc-card-title { font-weight:bold; font-size:14px; margin-bottom:12px; color:#333; }
.mpc-slider-row { display:flex; align-items:center; gap:4px; margin-bottom:8px; white-space:nowrap; }
.mpc-slider-row label { min-width:42px; font-size:13px; }
.mpc-slider-row input[type=range] { min-width:0; flex:1; }
.mpc-slider-val { min-width:36px; text-align:center; font-family:monospace; font-size:13px; }
.mpc-preset-row { display:flex; gap:6px; margin-top:10px; }
.mpc-preset-row button { padding:4px 12px; border-radius:4px; cursor:pointer; font-size:12px; background:#f0f0f0; border:1px solid #ccc; }
.mpc-preset-row button:hover { background:#667eea; color:#fff; }
.mpc-local-browser { }
.mpc-local-tools { display:flex; gap:10px; align-items:center; flex-wrap:wrap; }
.mpc-local-status { }
.mpc-local-grid { display:grid; grid-template-columns:1fr; gap:2px; max-height:380px; overflow-y:auto; border:1px solid #e0e0e0; border-radius:8px; background:#fafafa; }
.mpc-local-item { display:flex; align-items:center; gap:8px; padding:6px 10px; border-bottom:1px solid #eee; transition:background .15s; }
.mpc-local-item:hover { background:#f0f4ff; }
.mpc-local-dir { font-weight:bold; }
.mpc-playlist-grid { display:flex; flex-direction:column; gap:4px; max-height:300px; overflow-y:auto; }
.mpc-playlist-row { display:flex; align-items:center; gap:8px; padding:8px 12px; background:#fff; border:1px solid #eee; border-radius:8px; transition:background .15s; }
.mpc-playlist-row:hover { background:#f0f4ff; }
@media (max-width: 960px) {
	.mpc-effects-grid { grid-template-columns:1fr; }
	.mpc-local-tools { flex-direction:column; }
}
.mpc-toggle-row { display:flex; flex-wrap:wrap; gap:10px; margin-top:10px; }
.mpc-toggle-btn { padding:8px 14px; border-radius:6px; cursor:pointer; font-size:13px; font-weight:500; border:2px solid #ccc; background:#f5f5f5; color:#666; transition:all .2s; }
.mpc-toggle-btn.active { border-color:#28a745; background:#d4edda; color:#155724; }
</style>
EOF

sec_begin "$(lang de:"Live-Uebersicht" en:"Live overview")"
cat << EOF
<div class='$(html "$DASHBOARD_CLASS")'>
	<div class='mpc-card'>
		<h3>$(lang de:"Aktuelle Wiedergabe" en:"Current playback")</h3>
		<table style='width:100%'>
EOF
print_row "$(lang de:"Konfiguriertes MPD-Ziel" en:"Configured MPD target")" "$CONFIGURED_MPD_TARGET"
print_row "$(lang de:"Aktives MPD-Ziel" en:"Active MPD target")" "$RESOLVED_MPD_TARGET"
print_row "$(lang de:"Verbindungs-Hinweis" en:"Connection note")" "$MPD_TARGET_NOTE"
print_row "$(lang de:"Partition" en:"Partition")" "$MPD_MPC_PARTITION"
print_row "$(lang de:"Autoplay beim Booten" en:"Autoplay on boot")" "$MPD_MPC_ENABLED"
print_row "$(lang de:"Gespeicherte Station" en:"Saved startup station")" "$MPD_MPC_STARTUP_NAME"
print_row "$(lang de:"Aktueller Titel" en:"Current title")" "$CURRENT_TITLE_DISPLAY"
print_row "$(lang de:"Interpret / Jahr" en:"Artist / year")" "$CURRENT_META_ARTIST_YEAR"
print_row "$(lang de:"Station" en:"Station")" "$CURRENT_META_STATION"
print_row "$(lang de:"Sendezeit" en:"On air")" "$CURRENT_META_TIME_RANGE"
print_row "$(lang de:"Dauer" en:"Duration")" "$CURRENT_META_DURATION_HUMAN"
print_row "$(lang de:"Metadaten-Wert" en:"Metadata score")" "$CURRENT_META_SCORE"
print_row "$(lang de:"Metadaten-Quelle" en:"Metadata source")" "$CURRENT_META_SOURCE"
print_row "$(lang de:"Metadaten-ID" en:"Metadata ID")" "$CURRENT_META_ID"
print_row "$(lang de:"Aktuelle URI" en:"Current URI")" "$CURRENT_URI"
print_row "$(lang de:"Player-Status" en:"Player state")" "$CURRENT_STATE"
print_row "$(lang de:"Fortschritt" en:"Progress")" "$CURRENT_PLAYBACK_TIMELINE"
print_row "$(lang de:"Queue-Position" en:"Queue position")" "$CURRENT_QUEUE_POS"
print_row "$(lang de:"Queue-Laenge" en:"Queue length")" "$QUEUE_LENGTH"
print_row "$(lang de:"Lautstaerke" en:"Volume")" "$CURRENT_VOLUME"
print_link_row "$(lang de:"Stations-Homepage" en:"Station homepage")" "$HOMEPAGE_FALLBACK"
cat << EOF
		</table>
		<div class='mpc-meta'>
			<span class='mpc-badge'>$(lang de:"DB-Cache" en:"DB cache"): $(html "$DB_CACHE_STATE")</span>
			<span class='mpc-badge'>$(lang de:"Cache-Datei" en:"Cache file"): $(html "$DB_CACHE_FILE")</span>
			<span class='mpc-badge'>$(lang de:"Cache-Groesse" en:"Cache size"): $(html "$DB_CACHE_SIZE")</span>
		</div>
	</div>

EOF
if [ -n "$CURRENT_ART_DATA_URI" ]; then
	cat << EOF
	<div class='mpc-card'>
		<h3>$(lang de:"Artwork" en:"Artwork")</h3>
		<div class='mpc-art'>
EOF
	echo "<img src='$(html "$CURRENT_ART_DATA_URI")' alt='artwork'>"
	cat << EOF
		</div>
	</div>
EOF
	fi
	cat << EOF
</div>
EOF
sec_end

sec_begin "$(lang de:"MPD-Steuerung" en:"MPD controls")"
cat << EOF
<div class='mpc-control-summary'>
	<div>
		<strong>$(lang de:"Aktuelle Session" en:"Current session")</strong>
		<span>$(html "$CURRENT_CONTROL_HEADLINE")</span>
	</div>
	<div class='mpc-meta'>
		<span class='mpc-badge'>$(lang de:"Status" en:"State"): $(html "$CURRENT_STATE_LABEL")</span>
		<span class='mpc-badge'>$(lang de:"Queue" en:"Queue"): $(html "$QUEUE_STATUS_BADGE")</span>
		<span class='mpc-badge'>$(lang de:"Lautstaerke" en:"Volume"): $(html "$CURRENT_VOLUME_LABEL")</span>
	</div>
</div>
<div class='mpc-control-layout'>
	<div class='mpc-control-card'>
		<h4>$(lang de:"Wiedergabe" en:"Playback")</h4>
		<p>$(lang de:"Direkte Transportbefehle fuer den aktuellen Stream oder Queue-Eintrag." en:"Immediate transport commands for the active stream or queue entry.")</p>
		<div class='mpc-actions mpc-control-actions'>
			<form class='btn' action='$(href status mpd-mpc)' method='get'>
				<input type='hidden' name='action' value='player_play'>
				<input type='submit' value='▶ $(lang de:"Play" en:"Play")'>
			</form>
			<form class='btn' action='$(href status mpd-mpc)' method='get'>
				<input type='hidden' name='action' value='player_pause'>
				<input type='submit' value='⏸ $(lang de:"Pause" en:"Pause")'>
			</form>
			<form class='btn' action='$(href status mpd-mpc)' method='get'>
				<input type='hidden' name='action' value='player_toggle'>
				<input type='submit' value='⏯ $(lang de:"Toggle" en:"Toggle")'>
			</form>
			<form class='btn' action='$(href status mpd-mpc)' method='get'>
				<input type='hidden' name='action' value='player_stop'>
				<input type='submit' value='⏹ $(lang de:"Stop" en:"Stop")'>
			</form>
		</div>
EOF
if [ "$CURRENT_HAS_TIMELINE" = 'yes' ]; then
	cat << EOF
		<div class='mpc-meta'>
			<span class='mpc-badge'>$(lang de:"Clip-Fortschritt" en:"Clip progress"): $(html "$CURRENT_PLAYBACK_TIMELINE")</span>
		</div>
		<div class='mpc-actions mpc-control-actions'>
			<form class='btn' action='$(href status mpd-mpc)' method='get'>
				<input type='hidden' name='action' value='player_prev'>
				<input type='submit' value='⏮ $(lang de:"Prev" en:"Prev")'>
			</form>
			<form class='btn' action='$(href status mpd-mpc)' method='get'>
				<input type='hidden' name='action' value='player_seek_back'>
				<input type='submit' value='⏪ -10s'>
			</form>
			<form class='btn' action='$(href status mpd-mpc)' method='get'>
				<input type='hidden' name='action' value='player_seek_forward'>
				<input type='submit' value='⏩ +10s'>
			</form>
			<form class='btn' action='$(href status mpd-mpc)' method='get'>
				<input type='hidden' name='action' value='player_next'>
				<input type='submit' value='⏭ $(lang de:"Next" en:"Next")'>
			</form>
		</div>
EOF
fi
cat << EOF
	</div>
	<div class='mpc-control-card'>
		<h4>$(lang de:"Queue & Status" en:"Queue and status")</h4>
		<p>$(lang de:"Schneller Zugriff auf Current, Status und wichtige Queue-Befehle." en:"Quick access to current track, status output, and key queue actions.")</p>
		<div class='mpc-actions mpc-control-actions'>
			<form class='btn' action='$(href status mpd-mpc)' method='get'>
				<input type='hidden' name='action' value='player_current'>
				<input type='submit' value='$(lang de:"Current" en:"Current")'>
			</form>
			<form class='btn' action='$(href status mpd-mpc)' method='get'>
				<input type='hidden' name='action' value='player_status'>
				<input type='submit' value='$(lang de:"Status" en:"Status")'>
			</form>
			<form class='btn' action='$(href status mpd-mpc)' method='get'>
				<input type='hidden' name='action' value='queue_shuffle'>
				<input type='submit' value='$(lang de:"Queue mischen" en:"Shuffle queue")'>
			</form>
			<form class='btn' action='$(href status mpd-mpc)' method='get'>
				<input type='hidden' name='action' value='player_clear'>
				<input type='submit' value='$(lang de:"Queue leeren" en:"Clear queue")'>
			</form>
		</div>
	</div>
	<div class='mpc-control-card'>
		<h4>$(lang de:"Lautstaerke" en:"Volume")</h4>
		<p>$(lang de:"Ziehe den Regler fuer Feineinstellung oder nutze einen festen Preset-Wert." en:"Use the slider for fine adjustments or jump to a fixed preset value.")</p>
		<form class='mpc-control-volume' action='$(href status mpd-mpc)' method='get'>
			<input type='hidden' name='action' value='volume_set'>
			<div class='mpc-control-volume-row'>
				<input type='range' name='volume_value' min='0' max='100' step='1' value='$(html "$CURRENT_VOLUME_SAFE")' oninput="document.getElementById('mpcVolumeValue').textContent=this.value + '%'">
				<span id='mpcVolumeValue' class='mpc-control-volume-value'>$(html "$CURRENT_VOLUME_SAFE")%</span>
				<input type='submit' value='$(lang de:"Anwenden" en:"Apply")'>
			</div>
		</form>
		<div class='mpc-actions mpc-control-actions mpc-control-presets'>
			<form class='btn' action='$(href status mpd-mpc)' method='get'>
				<input type='hidden' name='action' value='volume_set'>
				<input type='hidden' name='volume_value' value='0'>
				<input type='submit' value='0%'>
			</form>
			<form class='btn' action='$(href status mpd-mpc)' method='get'>
				<input type='hidden' name='action' value='volume_set'>
				<input type='hidden' name='volume_value' value='25'>
				<input type='submit' value='25%'>
			</form>
			<form class='btn' action='$(href status mpd-mpc)' method='get'>
				<input type='hidden' name='action' value='volume_set'>
				<input type='hidden' name='volume_value' value='50'>
				<input type='submit' value='50%'>
			</form>
			<form class='btn' action='$(href status mpd-mpc)' method='get'>
				<input type='hidden' name='action' value='volume_set'>
				<input type='hidden' name='volume_value' value='75'>
				<input type='submit' value='75%'>
			</form>
			<form class='btn' action='$(href status mpd-mpc)' method='get'>
				<input type='hidden' name='action' value='volume_set'>
				<input type='hidden' name='volume_value' value='100'>
				<input type='submit' value='100%'>
			</form>
		</div>
	</div>
	<div class='mpc-control-card'>
		<h4>$(lang de:"Aktualisieren & Setup" en:"Refresh and setup")</h4>
		<p>$(lang de:"Aktualisiere die Ansicht, synchronisiere die Radio-Datenbank oder springe in die Konfiguration." en:"Refresh the page, sync the radio database, or jump into configuration.")</p>
		<div class='mpc-actions mpc-control-actions'>
			<form class='btn' action='$(href status mpd-mpc)?refresh=5' method='get'>
				<input type='submit' value='$(lang de:"Auto-Refresh 5s" en:"Auto refresh 5s")'>
			</form>
			<form class='btn' action='$(href status mpd-mpc)' method='get'>
				<input type='submit' value='$(lang de:"Jetzt aktualisieren" en:"Refresh now")'>
			</form>
			<form class='btn' action='$(href status mpd-mpc)' method='get'>
				<input type='hidden' name='action' value='db_sync'>
				<input type='submit' value='$(lang de:"WebRadioDB sync" en:"Sync WebRadioDB")'>
			</form>
			<form class='btn' action='$(href status mpd-mpc)' method='get'>
				<input type='hidden' name='action' value='disable_autoplay'>
				<input type='submit' value='$(lang de:"Autoplay aus" en:"Disable autoplay")'>
			</form>
			<form class='btn' action='$(href cgi mpd-mpc)' method='get'>
				<input type='submit' value='$(lang de:"Konfiguration" en:"Configuration")'>
			</form>
		</div>
	</div>
</div>
EOF
sec_end

sec_begin "$(lang de:"\u00dcberg\u00e4nge & Effekte" en:"Transitions & Effects")"
cat << EOF
<div class='mpc-effects-grid'>
	<div class='mpc-card'>
		<div class='mpc-card-title'>$(lang de:"Crossfade" en:"Crossfade")</div>
		<div class='mpc-slider-row'>
			<input type='range' id='crossfadeSlider' min='0' max='30' value='${MPD_MPC_CROSSFADE:-0}' oninput="document.getElementById('crossfadeVal').textContent=this.value+'s'; updateCrossfade(this.value)"
				style='flex:1; accent-color:#667eea;'>
			<span id='crossfadeVal' class='mpc-slider-val'>${MPD_MPC_CROSSFADE:-0}s</span>
		</div>
		<div class='mpc-preset-row'>
			<button type='button' onclick="setCrossfade(0);document.getElementById('crossfadeSlider').value=0;document.getElementById('crossfadeVal').textContent='0s';">0s</button>
			<button type='button' onclick="setCrossfade(2);document.getElementById('crossfadeSlider').value=2;document.getElementById('crossfadeVal').textContent='2s';">2s</button>
			<button type='button' onclick="setCrossfade(5);document.getElementById('crossfadeSlider').value=5;document.getElementById('crossfadeVal').textContent='5s';">5s</button>
			<button type='button' onclick="setCrossfade(10);document.getElementById('crossfadeSlider').value=10;document.getElementById('crossfadeVal').textContent='10s';">10s</button>
		</div>
	</div>
	<div class='mpc-card'>
		<div class='mpc-card-title'>$(lang de:"MixRamp" en:"MixRamp")</div>
		<div class='mpc-slider-row'>
			<label>$(lang de:"dB" en:"dB"):</label>
			<input type='range' id='mixrampdbSlider' min='-30' max='0' step='0.5' value='${MPD_MPC_MIXRAMPDB:-0}' oninput="document.getElementById('mixrampdbVal').textContent=this.value; updateMixrampDb(this.value)"
				style='flex:1; accent-color:#e67e22;'>
			<span id='mixrampdbVal' class='mpc-slider-val'>${MPD_MPC_MIXRAMPDB:-0}</span>
		</div>
		<div class='mpc-slider-row'>
			<label>$(lang de:"Delay" en:"Delay"):</label>
			<input type='range' id='mixrampdelaySlider' min='-1' max='10' value='${MPD_MPC_MIXRAMPDELAY:--1}' oninput="var v=this.value;document.getElementById('mixrampdelayVal').textContent=v==-1?'off':v+'s'; updateMixrampDelay(v)"
				style='flex:1; accent-color:#e67e22;'>
			<span id='mixrampdelayVal' class='mpc-slider-val'>$([ "${MPD_MPC_MIXRAMPDELAY:-0}" -eq -1 ] && echo 'off' || echo "${MPD_MPC_MIXRAMPDELAY}s")</span>
		</div>
	</div>
	<div class='mpc-card'>
		<div class='mpc-card-title'>$(lang de:"ReplayGain" en:"ReplayGain")</div>
		<select id='replaygainSel' onchange="updateReplayGain(this.value)" style='width:100%;padding:8px;border-radius:6px;'>
			<option value='off' $([ "${MPD_MPC_REPLAYGAIN:-off}" = 'off' ] && echo 'selected')>$(lang de:"Aus" en:"Off")</option>
			<option value='track' $([ "$MPD_MPC_REPLAYGAIN" = 'track' ] && echo 'selected')>Track</option>
			<option value='album' $([ "$MPD_MPC_REPLAYGAIN" = 'album' ] && echo 'selected')>Album</option>
			<option value='auto' $([ "$MPD_MPC_REPLAYGAIN" = 'auto' ] && echo 'selected')>Auto</option>
		</select>
	</div>
	<div class='mpc-card'>
		<div class='mpc-card-title'>$(lang de:"Wiedergabemodi" en:"Playback Mode")</div>
		<div class='mpc-toggle-row'>
			<button id='btnRepeat' class='mpc-toggle-btn$([ "$MPD_REPEAT_STATE" = 'on' ] && echo ' active')' onclick="toggleMPD('repeat')">$(lang de:"Wiederholen" en:"Repeat")</button>
			<button id='btnRandom' class='mpc-toggle-btn$([ "$MPD_RANDOM_STATE" = 'on' ] && echo ' active')' onclick="toggleMPD('random')">$(lang de:"Zufall" en:"Random")</button>
			<button id='btnSingle' class='mpc-toggle-btn$([ "$MPD_SINGLE_STATE" = 'on' ] && echo ' active')' onclick="toggleMPD('single')">$(lang de:"Einzeln" en:"Single")</button>
			<button id='btnConsume' class='mpc-toggle-btn$([ "$MPD_CONSUME_STATE" = 'on' ] && echo ' active')' onclick="toggleMPD('consume')">$(lang de:"Verbrauchen" en:"Consume")</button>
		</div>
	</div>
</div>
<script>
function ajaxGet(action, params, callback) {
	var q = '?ajax=1&action=' + encodeURIComponent(action);
	if (params) for (var k in params) q += '&' + k + '=' + encodeURIComponent(params[k]);
	var x = new XMLHttpRequest();
	x.open('GET', window.location.pathname + q, true);
	x.onload = function() {
		try {
			var t = x.responseText;
			var s = t.indexOf('Content-Type: application/json');
			if (s === -1) { callback('No JSON', null); return; }
			t = t.substring(s);
			var b = t.indexOf('{');
			if (b === -1) { callback('No brace', null); return; }
			var d = 0, e = -1;
			for (var i = b; i < t.length; i++) { if (t[i]==='{') d++; else if (t[i]==='}') { d--; if (d===0) { e=i+1; break; } } }
			var r = JSON.parse(t.substring(b, e));
			callback(null, r);
		} catch(ex) { callback(ex.message, null); }
	};
	x.send();
}
function setCrossfade(v) { ajaxGet('player_crossfade', {value:v}, function(){}); }
function updateCrossfade(v) { ajaxGet('player_crossfade', {value:v}, function(){}); }
function updateMixrampDb(v) { ajaxGet('player_mixrampdb', {value:v}, function(){}); }
function updateMixrampDelay(v) { ajaxGet('player_mixrampdelay', {value:v}, function(){}); }
function updateReplayGain(v) { ajaxGet('player_replaygain', {value:v}, function(){}); }
function toggleMPD(mode) {
	var btn = document.getElementById('btn'+mode.charAt(0).toUpperCase()+mode.slice(1));
	var isActive = btn.classList.contains('active');
	var newVal = isActive ? 'off' : 'on';
	ajaxGet('player_'+mode, {value:newVal}, function(err, r) {
		if (!err && r && r.success) {
			if (newVal === 'on') btn.classList.add('active');
			else btn.classList.remove('active');
		}
	});
}
</script>
EOF
sec_end

sec_begin "$(lang de:"Queue-Verwaltung" en:"Queue management")"
cat << EOF
<div class='mpc-queue-toolbar'>
	<div style='display:flex;align-items:center;gap:8px;flex-wrap:wrap;'>
		<input type='text' id='queueSearch' placeholder='$(lang de:"Filter..." en:"Filter...")' oninput='queueReload()'
			style='padding:6px 10px;border-radius:6px;border:1px solid #ccc;min-width:120px;font-size:13px;'>
		<span id='queueInfo' class='mpc-queue-info'></span>
	</div>
	<div style='display:flex;gap:6px;flex-wrap:wrap;'>
		<form class='btn' action='$(href status mpd-mpc)' method='get'>
			<input type='hidden' name='action' value='queue_shuffle'>
			<input type='submit' value='$(lang de:"Mischen" en:"Shuffle")'>
		</form>
		<form class='btn' action='$(href status mpd-mpc)' method='get'>
			<input type='hidden' name='action' value='player_clear'>
			<input type='submit' value='$(lang de:"Leeren" en:"Clear")' onclick="return confirm('$(lang de:"Queue wirklich leeren?" en:"Really clear queue?")')">
		</form>
		<form class='btn' action='$(href status mpd-mpc)' method='get'>
			<input type='submit' value='$(lang de:"Aktualisieren" en:"Refresh")'>
		</form>
	</div>
</div>
<div class='mpc-queue-table-wrap'>
	<table id='queueTable' class='mpc-table'>
		<thead><tr><th class='col-index' onclick='queueSort("#")'>#</th><th onclick='queueSort("label")'>$(lang de:"Titel" en:"Track")</th><th class='col-actions'>$(lang de:"Aktionen" en:"Actions")</th></tr></thead>
		<tbody id='queueTbody'><tr><td colspan='3' style='text-align:center;padding:30px;color:#999;'>$(lang de:"Lade..." en:"Loading...")</td></tr></tbody>
	</table>
</div>
<div id='queuePager' class='mpc-pager'>
	<button id='queuePrevBtn' onclick='queuePage(-1)' disabled>&#9664; $(lang de:"Zurueck" en:"Prev")</button>
	<span class='mpc-pager-label'>$(lang de:"Seite" en:"Page")</span>
	<input id='queuePageInput' class='mpc-page-input' type='number' min='1' value='1' onkeydown='if(event.key==="Enter")queueGoPage()' title='$(lang de:"Seitenzahl eingeben, Enter zum Springen" en:"Enter page number, press Enter to jump")'>
	<span id='queuePageTotal' class='mpc-page-total'></span>
	<button onclick='queueGoPage()' title='$(lang de:"Zu Seite springen" en:"Jump to page")'>$(lang de:"Gehe" en:"Go")</button>
	<select id='queuePageSize' onchange='queueChangePageSize()' title='$(lang de:"Eintraege pro Seite" en:"entries per page")'>
		<option value='20'>20</option>
		<option value='50' selected>50</option>
		<option value='100'>100</option>
		<option value='200'>200</option>
	</select>
	<button id='queueNextBtn' onclick='queuePage(1)'>$(lang de:"Weiter" en:"Next") &#9654;</button>
</div>
<script>
var qTotal=0,qOffset=0,qLimit=50,qCur='$CURRENT_QUEUE_INDEX',qData=[],qSortCol='',qSortDir='asc';
function queueLoad(append) {
	var el=document.getElementById('queueTbody');
	var f=document.getElementById('queueSearch');
	var filter=f?f.value:'';
	if(!append){qOffset=0;qData=[];el.innerHTML='<tr><td colspan="3" style="text-align:center;padding:30px;color:#999;">$(lang de:"Lade..." en:"Loading...")</td></tr>';}
	document.getElementById('queueInfo').textContent='';
	if(filter!==''){queueFilterAll(filter);return;}
	ajaxGet('queue_list',{offset:qOffset,limit:qLimit},function(err,data){
		if(err){el.innerHTML='<tr><td colspan="3" class="mpc-empty">Error: '+err+'</td></tr>';return;}
		qTotal=data.total;qCur=data.current||qCur;var items=data.items||[];
		for(var i=0;i<items.length;i++)qData.push(items[i]);
		if(!append)queueRender(items);else queueRender(items);
		queueUpdateInfo();
	});
}
function queueFilterAll(f) {
	f=f.toLowerCase();qData=[];qOffset=0;
	(function fb(o){ajaxGet('queue_list',{offset:o,limit:200},function(err,data){
		if(err)return;qTotal=data.total;var items=data.items||[];
		for(var i=0;i<items.length;i++){if(items[i].label.toLowerCase().indexOf(f)!==-1)qData.push(items[i]);}
		if(o+200<data.total){document.getElementById('queueTbody').innerHTML='<tr><td colspan="3" style="text-align:center;padding:20px;color:#888;">$(lang de:"Suche..." en:"Searching...") ('+Math.min(o+200,data.total)+'/'+data.total+')</td></tr>';setTimeout(function(){fb(o+200);},50);}
		else{document.getElementById('queueInfo').textContent=qData.length+' / '+qTotal+' $(lang de:"Treffer" en:"hits")';queueRender(qData);}
	});})(0);
}
function queueRender(items) {
	var el=document.getElementById('queueTbody');el.innerHTML='';
	if(items.length===0){el.innerHTML='<tr><td colspan="3" class="mpc-empty">$(lang de:"Keine Eintraege" en:"No entries")</td></tr>';return;}
	var html='';
	for(var i=0;i<items.length;i++){
		var it=items[i];
		var isCur=(String(it.n)===String(qCur))||it.cur;
		var rowCls=isCur?' playing':'';
		var badge=isCur?'<span class="playing-badge">$(lang de:"Laeuft" en:"Playing")</span>':'';
		html+='<tr class="'+rowCls+'">'+
			'<td class="col-index">#'+it.n+'</td>'+
			'<td>'+badge+queueEsc(it.label)+'</td>'+
			'<td class="col-actions">'+
				'<form action="'+(window.location.pathname)+'" method="get" style="display:inline">'+
					'<input type="hidden" name="action" value="queue_play"><input type="hidden" name="queue_index" value="'+it.n+'">'+
					'<button type="submit"><span>$(lang de:"Play" en:"Play")</span></button></form>'+
				'<form action="'+(window.location.pathname)+'" method="get" style="display:inline">'+
					'<input type="hidden" name="action" value="queue_move_up"><input type="hidden" name="queue_index" value="'+it.n+'">'+
					'<button type="submit"><span>$(lang de:"Hoch" en:"Up")</span></button></form>'+
				'<form action="'+(window.location.pathname)+'" method="get" style="display:inline">'+
					'<input type="hidden" name="action" value="queue_move_down"><input type="hidden" name="queue_index" value="'+it.n+'">'+
					'<button type="submit"><span>$(lang de:"Runter" en:"Down")</span></button></form>'+
				'<form action="'+(window.location.pathname)+'" method="get" style="display:inline">'+
					'<input type="hidden" name="action" value="queue_remove"><input type="hidden" name="queue_index" value="'+it.n+'">'+
					'<button type="submit"><span>$(lang de:"Entf." en:"Del")</span></button></form>'+
			'</td></tr>';
	}
	el.innerHTML=html;
	queueUpdatePager();
}
function queueReload(){queueLoad(false);}
function queuePage(dir){
	if(dir<0&&qOffset<=0)return;
	var newOff=qOffset+dir*qLimit;
	if(newOff<0)newOff=0;
	if(newOff>=qTotal&&dir>0)return;
	qOffset=newOff;qData=[];queueLoad(false);
}
function queueUpdateInfo(){
	document.getElementById('queueInfo').textContent=qData.length+' / '+qTotal+' $(lang de:"Eintraege" en:"items")';
}
function queueUpdatePager(){
	var prev=document.getElementById('queuePrevBtn');
	var next=document.getElementById('queueNextBtn');
	if(prev)prev.disabled=(qOffset<=0);
	if(next)next.disabled=(qOffset+qLimit>=qTotal);
	var pg=Math.floor(qOffset/qLimit)+1;
	var totalPg=Math.max(1,Math.ceil(qTotal/qLimit));
	var inp=document.getElementById('queuePageInput');
	if(inp)inp.value=pg;
	var tot=document.getElementById('queuePageTotal');
	if(tot)tot.textContent='/ '+totalPg;
}
function queueChangePageSize(){
	var sel=document.getElementById('queuePageSize');
	if(!sel)return;
	qLimit=parseInt(sel.value);
	queueReload();
}
function queueGoPage(){
	var inp=document.getElementById('queuePageInput');
	if(!inp)return;
	var totalPg=Math.max(1,Math.ceil(qTotal/qLimit));
	var pg=Math.min(totalPg,Math.max(1,parseInt(inp.value,10)||1));
	if(String(inp.value)!==String(pg))inp.value=pg;
	var newOff=(pg-1)*qLimit;
	if(newOff===qOffset)return;
	qOffset=newOff;qData=[];queueLoad(false);
}
function queueEsc(s){var d=document.createElement('div');d.textContent=s;return d.innerHTML;}
queueLoad(false);
</script>
EOF
sec_end

sec_begin "$(lang de:"Lokaler Dateibrowser" en:"Local File Browser")"
cat << LOCALBROWSE_HTML
<div class='mpc-browser-toolbar'>
	<div class='mpc-browser-path'>
		<button type='button' onclick='browseUp()' title='$(lang de:"Elternverzeichnis" en:"Parent directory")'>&#x25B2;</button>
		<span id='localPathDisp' class='mpc-browser-path-text'>$(lang de:"Lade..." en:"Loading...")</span>
	</div>
	<div class='mpc-browser-actions'>
		<button type='button' onclick='browseRoot()'>$(lang de:"Root" en:"Root")</button>
		<button type='button' onclick='addCurrentDir()' class='btn-primary'>$(lang de:"+ Dir" en:"+ Dir")</button>
	</div>
</div>
<div id='localDirStatus' style='padding:4px 0 8px;font-size:12px;color:#888;'></div>
<div class='mpc-browser-grid'>
	<table id='browserTable' class='mpc-table'>
		<thead><tr><th onclick='brSort("name")' class='sorted asc'>$(lang de:"Name" en:"Name")</th><th onclick='brSort("size")' style='width:90px;'>$(lang de:"Groesse" en:"Size")</th><th style='width:50px;'>$(lang de:"Aktion" en:"Action")</th></tr></thead>
		<tbody id='browserTbody'><tr><td colspan='3' style='text-align:center;padding:30px;color:#999;'>$(lang de:"Lade..." en:"Loading...")</td></tr></tbody>
	</table>
</div>
<div id='brPager' class='mpc-pager'>
	<button id='brPrevBtn' onclick='brPage(-1)' disabled>&#9664; $(lang de:"Zurueck" en:"Prev")</button>
	<span class='mpc-pager-label'>$(lang de:"Seite" en:"Page")</span>
	<input id='brPageInput' class='mpc-page-input' type='number' min='1' value='1' onkeydown='if(event.key==="Enter")brGoPage()' title='$(lang de:"Seitenzahl eingeben, Enter zum Springen" en:"Enter page number, press Enter to jump")'>
	<span id='brPageTotal' class='mpc-page-total'></span>
	<button onclick='brGoPage()' title='$(lang de:"Zu Seite springen" en:"Jump to page")'>$(lang de:"Gehe" en:"Go")</button>
	<select id='brPageSize' onchange='brChangePageSize()' title='$(lang de:"Eintraege pro Seite" en:"entries per page")'>
		<option value='20' selected>20</option>
		<option value='50'>50</option>
		<option value='100'>100</option>
		<option value='200'>200</option>
	</select>
	<button id='brNextBtn' onclick='brPage(1)'>$(lang de:"Weiter" en:"Next") &#9654;</button>
</div>
<script>
var brRoot='$(html "${LOCAL_ROOT:-/var/media/ftp}")';
var brPath=brRoot;
var brData=[];
var brSortCol='name';
var brSortDir=1;
var brPageNum=0;
var brPageSize=20;

function browseLocal(path){
	brPath=path||brRoot;
	document.getElementById('localPathDisp').textContent=brPath;
	document.getElementById('localDirStatus').textContent='$(lang de:"Lade..." en:"Loading...")';
	document.getElementById('browserTbody').innerHTML='<tr><td colspan="3" style="text-align:center;padding:20px;color:#999;">$(lang de:"Lade..." en:"Loading...")</td></tr>';
	ajaxGet('browse_dir',{path:brPath},function(err,data){
		if(err){document.getElementById('localDirStatus').textContent='Error: '+err;return;}
		document.getElementById('localPathDisp').textContent=data.path;
		brData=[];
		var entries=data.entries||[];
		if(brPath!==brRoot&&data.parent){brData.push({name:'..',path:data.parent,type:'dir',size:0});}
		for(var i=0;i<entries.length;i++)brData.push(entries[i]);
		document.getElementById('localDirStatus').textContent=entries.length+' $(lang de:"Eintraege" en:"entries")';
		brPageNum=0;
		brPageSize=parseInt(document.getElementById('brPageSize').value);
		brRender();
	});
}
function brRender(){
	var data=brData.slice();
	if(brSortCol==='name'){data.sort(function(a,b){var x=a.name.toLowerCase(),y=b.name.toLowerCase();return x<y?-1:x>y?1:0;});}
	else if(brSortCol==='size'){data.sort(function(a,b){return(a.size||0)-(b.size||0);});}
	if(brSortDir===-1)data.reverse();
	var total=data.length;
	var totalPages=Math.ceil(total/brPageSize)||1;
	if(brPageNum>=totalPages)brPageNum=totalPages-1;
	if(brPageNum<0)brPageNum=0;
	var start=brPageNum*brPageSize;
	var pageData=data.slice(start,start+brPageSize);
	var html='';
	for(var i=0;i<pageData.length;i++){
		var e=pageData[i];
		if(e.name==='..'){
			html+='<tr onclick="browseLocal(\''+brEsc(e.path)+'\')" style="cursor:pointer">'+
				'<td><span class="file-icon">&#x2190;</span> <em>$(lang de:"Oberverzeichnis" en:"Parent")</em></td><td class="file-size"></td><td></td></tr>';
			continue;
		}
		var icon='\ud83c\udfb5',labelCls='';
		if(e.type==='dir'){icon='\ud83d\udcc1';}
		else{
			if(/\.(mp3|flac|ogg|wav|m4a|aac|wma|opus|ape|wv|aiff|dsf|dff)$/i.test(e.name)){icon='\ud83c\udfb5';labelCls='style="color:#28a745;font-weight:bold"';}
			else if(/\.(jpg|jpeg|png|gif|bmp|webp)$/i.test(e.name)){icon='\ud83d\uddbc';}
			else if(/\.(txt|nfo|log|md)$/i.test(e.name)){icon='\ud83d\udcc4';}
		}
		var size=e.size>1048576?(e.size/1048576).toFixed(1)+' MB':(e.size>1024?(e.size/1024).toFixed(1)+' KB':(e.size||0)+' B');
		if(e.type==='dir'){
			html+='<tr onclick="browseLocal(\''+brEsc(e.path)+'\')" style="cursor:pointer">'+
				'<td><span class="file-icon">'+icon+'</span> <span class="file-name" '+labelCls+'>'+brEsc(e.name)+'/</span></td>'+
				'<td class="file-size"></td><td></td></tr>';
		}else{
			html+='<tr>'+
				'<td><span class="file-icon">'+icon+'</span> <span class="file-name" '+labelCls+' title="'+brEsc(e.name)+'">'+brEsc(e.name)+'</span></td>'+
				'<td class="file-size">'+size+'</td>'+
				'<td><button onclick="brAddFile(\''+brEsc(e.path)+'\')" style="padding:4px 10px;border-radius:4px;cursor:pointer;font-size:12px;border:1px solid #28a745;background:#d4edda;color:#155724;">+</button></td></tr>';
		}
	}
	document.getElementById('browserTbody').innerHTML=html||'<tr><td colspan="3" class="mpc-empty">$(lang de:"Leeres Verzeichnis" en:"Empty directory")</td></tr>';
	brUpdatePager(total,totalPages);
}
function brPage(dir){
	brPageNum+=dir;
	brRender();
}
function brChangePageSize(){
	brPageSize=parseInt(document.getElementById('brPageSize').value);
	brPageNum=0;
	brRender();
}
function brUpdatePager(total,totalPages){
	var prev=document.getElementById('brPrevBtn');
	var next=document.getElementById('brNextBtn');
	if(prev)prev.disabled=(brPageNum<=0);
	if(next)next.disabled=(brPageNum>=totalPages-1||totalPages<=1);
	var pg=Math.min(totalPages,Math.max(1,brPageNum+1));
	var inp=document.getElementById('brPageInput');
	if(inp)inp.value=pg;
	var tot=document.getElementById('brPageTotal');
	if(tot)tot.textContent='/ '+totalPages;
}
function brGoPage(){
	var inp=document.getElementById('brPageInput');
	if(!inp)return;
	var totalPages=Math.max(1,Math.ceil(brData.length/brPageSize));
	var pg=Math.min(totalPages,Math.max(1,parseInt(inp.value,10)||1));
	if(String(inp.value)!==String(pg))inp.value=pg;
	brPageNum=pg-1;
	brRender();
}
function brSort(col){
	if(brSortCol===col)brSortDir*=-1;else{brSortCol=col;brSortDir=1;}
	var ths=document.querySelectorAll('#browserTable thead th');
	for(var i=0;i<ths.length;i++)ths[i].classList.remove('sorted','asc','desc');
	var idx=(col==='name'?0:1);
	ths[idx].classList.add('sorted',brSortDir===1?'asc':'desc');
	brPageNum=0;
	brRender();
}
function browseUp(){
	if(brPath&&brPath!==brRoot&&brPath!=='/'){var p=brPath.substring(0,brPath.lastIndexOf('/'))||brRoot;browseLocal(p);}
}
function browseRoot(){browseLocal(brRoot);}
function brAddFile(p){
	document.getElementById('localDirStatus').textContent='$(lang de:"Fuege hinzu..." en:"Adding...") '+p.split('/').pop();
	ajaxGet('local_add',{path:p},function(err,data){
		if(err||!data||!data.success){alert('$(lang de:"Fehler" en:"Error")'+(data?': '+data.error:err));document.getElementById('localDirStatus').textContent='$(lang de:"Fehler" en:"Error")';}
		else{document.getElementById('localDirStatus').textContent='$(lang de:"Hinzugefuegt!" en:"Added!")';}
	});
}
function addCurrentDir(){
	if(!brPath)return;
	document.getElementById('localDirStatus').textContent='$(lang de:"Fuege Verzeichnis hinzu..." en:"Adding directory...")';
	ajaxGet('local_add_dir',{path:brPath},function(err,data){
		if(err||!data||!data.success){alert('$(lang de:"Fehler" en:"Error")'+(data?': '+data.error:err));document.getElementById('localDirStatus').textContent='$(lang de:"Fehler" en:"Error")';}
		else{document.getElementById('localDirStatus').textContent='$(lang de:"Hinzugefuegt" en:"Added") '+data.added+' $(lang de:"Dateien" en:"files")';if(data.errors)alert('$(lang de:"Fehler" en:"Errors")' + ':\n' + data.errors);}
	});
}
function brEsc(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
browseLocal(brRoot);
</script>
LOCALBROWSE_HTML
sec_end

sec_begin "$(lang de:"Lokale Playlisten" en:"Local Playlists")"
cat << 'PLAYLISTS_HTML'
<div class='mpc-playlist-manager'>
	<div class='mpc-local-tools'>
		<input type='text' id='newPlaylistName' placeholder='Playlist name...' style='flex:1;padding:10px;border-radius:6px;border:1px solid #ddd;min-width:0;'>
		<button type='button' onclick='savePlaylist()' style='padding:10px 20px;border-radius:6px;cursor:pointer;background:#667eea;color:#fff;'>Save Queue</button>
		<button type='button' onclick='refreshPlaylists()' style='padding:10px 20px;border-radius:6px;cursor:pointer;'>Refresh</button>
	</div>
	<div id='playlistStatus' style='padding:6px 0;font-size:12px;color:#888;'></div>
	<div id='playlistList' class='mpc-playlist-grid'></div>
</div>
<script>
function refreshPlaylists() {
	document.getElementById('playlistStatus').textContent = 'Loading...';
	ajaxGet('playlist_list', null, function(err, data) {
		if (err) { document.getElementById('playlistStatus').textContent = 'Error: ' + err; return; }
		var files = data.files || [];
		var html = '';
		for (var i = 0; i < files.length; i++) {
			var f = files[i];
			html += '<div class="mpc-playlist-row">' +
				'<span style="font-size:18px;min-width:24px;">\ud83c\udfb6</span>' +
				'<span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:bold;">'+escapeHtml(f.name)+'</span>' +
				'<span style="font-size:11px;color:#999;min-width:50px;text-align:right;">'+(f.size > 1024 ? (f.size/1024).toFixed(1)+' KB' : f.size+' B')+'</span>' +
				'<button type="button" onclick="loadPlaylist(\''+escapeHtml(f.name)+'\')" style="padding:6px 12px;border-radius:4px;cursor:pointer;font-size:12px;background:#667eea;color:#fff;">Load</button>' +
				'<button type="button" onclick="deletePlaylist(\''+escapeHtml(f.name)+'\')" style="padding:6px 12px;border-radius:4px;cursor:pointer;font-size:12px;background:#dc3545;color:#fff;">Del</button>' +
				'</div>';
		}
		document.getElementById('playlistList').innerHTML = html || '<div class="mpc-empty">No saved playlists</div>';
		document.getElementById('playlistStatus').textContent = files.length + ' playlist(s)';
	});
}
function savePlaylist() {
	var name = document.getElementById('newPlaylistName').value.trim();
	if (!name) { alert('Enter a playlist name'); return; }
	document.getElementById('playlistStatus').textContent = 'Saving...';
	ajaxGet('playlist_save', {name: name}, function(err, data) {
		if (err || !data || !data.success) {
			alert('Failed to save: ' + (data ? data.error : err));
			document.getElementById('playlistStatus').textContent = 'Error';
		} else {
			document.getElementById('newPlaylistName').value = '';
			document.getElementById('playlistStatus').textContent = 'Saved: ' + data.name;
			refreshPlaylists();
		}
	});
}
function loadPlaylist(name) {
	if (!confirm('Load playlist "' + name + '"? Current queue will be replaced.')) return;
	document.getElementById('playlistStatus').textContent = 'Loading...';
	ajaxGet('playlist_load', {name: name}, function(err, data) {
		if (err || !data || !data.success) {
			alert('Failed to load: ' + (data ? data.error : err));
			document.getElementById('playlistStatus').textContent = 'Error';
		} else {
			document.getElementById('playlistStatus').textContent = 'Loaded: ' + data.name;
			window.location.reload();
		}
	});
}
function deletePlaylist(name) {
	if (!confirm('Delete playlist "' + name + '"?')) return;
	ajaxGet('playlist_delete', {name: name}, function(err, data) {
		if (err || !data || !data.success) {
			alert('Failed to delete: ' + (data ? data.error : err));
		} else {
			refreshPlaylists();
		}
	});
}
refreshPlaylists();
</script>
PLAYLISTS_HTML
sec_end

sec_begin "$(lang de:"Kommando-Ausgabe" en:"Command output")"
cat << EOF
<div class='mpc-console'>
	<div class='cmd'>$(lang de:"Letztes Kommando" en:"Last command"): $(html "$ACTION_TITLE")</div>
EOF
if [ -n "$ACTION_COMMAND" ]; then
	echo "<div class='cmd'>$(html "$ACTION_COMMAND")</div>"
fi
if [ "$ACTION_RC" -ne 0 ]; then
	echo "<div class='cmd'>$(lang de:"Rueckgabecode" en:"Exit code"): $(html "$ACTION_RC")</div>"
fi
printf '%s\n' "$ACTION_OUTPUT" | sed -n '1,120p' | html | {
	echo '<pre>'
	cat
	echo '</pre>'
}
cat << EOF
</div>
EOF
sec_end

sec_begin "$(lang de:"Manuelle Station" en:"Manual station")"
cat << EOF
<form action='$(href status mpd-mpc)' method='get'>
	<div class='mpc-manual-grid'>
		<div>
			<label for='stream_name'>$(lang de:"Name" en:"Name")</label>
			<input id='stream_name' type='text' name='stream_name' value='$(html "$MANUAL_NAME")'>
		</div>
		<div>
			<label for='stream_uri'>$(lang de:"Stream-URI" en:"Stream URI")</label>
			<input id='stream_uri' type='text' name='stream_uri' value='$(html "$MANUAL_URI")'>
		</div>
		<div>
			<label for='stream_image'>$(lang de:"Bild oder Dateiname" en:"Image or filename")</label>
			<input id='stream_image' type='text' name='stream_image' value='$(html "$MANUAL_IMAGE")'>
		</div>
		<div>
			<label for='stream_homepage'>$(lang de:"Homepage" en:"Homepage")</label>
			<input id='stream_homepage' type='text' name='stream_homepage' value='$(html "$MANUAL_HOMEPAGE")'>
		</div>
	</div>
	<div class='mpc-actions'>
		<button type='submit' name='action' value='queue_add'>$(lang de:"In Queue" en:"Queue")</button>
		<button type='submit' name='action' value='replace_play'>$(lang de:"Jetzt spielen" en:"Play now")</button>
		<button type='submit' name='action' value='save_startup'>$(lang de:"Als Start speichern" en:"Save startup")</button>
	</div>
</form>
<p>
$(lang de:"Speichert eine manuelle Station direkt in der persistenten Konfiguration oder startet sie sofort in MPD." en:"Save a manual station directly into the persistent configuration or start it immediately in MPD.")
</p>
EOF
sec_end

sec_begin "$(lang de:"WebRadioDB Browser" en:"WebRadioDB browser")"
cat << EOF
<div class='mpc-browser-tools'>
	<input type='text' id='dbQuery' placeholder='$(lang de:"Suchen nach Name, Genre, Land" en:"Search by name, genre, country")'>
	<select id='dbCountry'><option value=''>$(lang de:"Alle Laender" en:"All countries")</option></select>
	<select id='dbLanguage'><option value=''>$(lang de:"Alle Sprachen" en:"All languages")</option></select>
	<select id='dbGenre'><option value=''>$(lang de:"Alle Genres" en:"All genres")</option></select>
	<select id='dbCodec'><option value=''>$(lang de:"Alle Codecs" en:"All codecs")</option></select>
</div>
<div class='mpc-browser-status'>
	<div id='dbStatus'>$(lang de:"Lade WebRadioDB ..." en:"Loading WebRadioDB ...")</div>
	<div id='dbResultCount'></div>
</div>
<div id='dbResults' class='mpc-station-grid'></div>
<noscript><div class='mpc-empty'>$(lang de:"JavaScript wird fuer die Suche in WebRadioDB benoetigt." en:"JavaScript is required for WebRadioDB filtering.")</div></noscript>
EOF
sec_end

sec_begin "$(lang de:"Rohdaten" en:"Raw MPD output")"
echo '<pre class="log full">'
if [ "$STATUS_RC" -eq 0 ]; then
	printf '%s\n\n' "$CURRENT_STATUS_RAW" | html
else
	printf '%s\n\n' "$CURRENT_STATUS_RAW" | html
fi
printf '%s\n' "$PLAYLIST_PREVIEW" | html
echo '</pre>'
sec_end

if [ -r "$LOG_FILE" ]; then
	sec_begin "$(lang de:"Autoplay-Log" en:"Autoplay log")"
	echo '<pre class="log full">'
	tail -n 30 "$LOG_FILE" | html
	echo '</pre>'
	sec_end
fi

cat << EOF
<script type='text/javascript'>
(function () {
	var endpoint = '$(href status mpd-mpc)?ajax=1&action=db_data';
	var imageBase = '$(html "$DB_IMAGE_BASE")';
	var stations = [];
	var resultLimit = 60;
	var queryEl = document.getElementById('dbQuery');
	var countryEl = document.getElementById('dbCountry');
	var languageEl = document.getElementById('dbLanguage');
	var genreEl = document.getElementById('dbGenre');
	var codecEl = document.getElementById('dbCodec');
	var statusEl = document.getElementById('dbStatus');
	var countEl = document.getElementById('dbResultCount');
	var resultsEl = document.getElementById('dbResults');

	function htmlEscape(value) {
		return String(value || '').replace(/[&<>"']/g, function (char) {
			return {
				'&': '&amp;',
				'<': '&lt;',
				'>': '&gt;',
				'"': '&quot;',
				"'": '&#39;'
			}[char];
		});
	}

	function parseWrappedJson(text) {
		var marker = 'Content-Type: application/json';
		var markerPos = text.indexOf(marker);
		if (markerPos === -1) {
			throw new Error('Invalid AJAX wrapper');
		}
		var firstBrace = text.indexOf('{', markerPos + marker.length);
		if (firstBrace === -1) {
			throw new Error('JSON payload missing');
		}
		var depth = 0;
		for (var i = firstBrace; i < text.length; i += 1) {
			if (text[i] === '{') {
				depth += 1;
			} else if (text[i] === '}') {
				depth -= 1;
				if (depth === 0) {
					return JSON.parse(text.substring(firstBrace, i + 1));
				}
			}
		}
		throw new Error('JSON payload incomplete');
	}

	function splitValues(value) {
		if (!value) {
			return [];
		}
		if (Array.isArray(value)) {
			return value;
		}
		return String(value)
			.split(/[;,|]/)
			.map(function (part) { return part.trim(); })
			.filter(Boolean);
	}

	function uniqueValues(items) {
		var seen = Object.create(null);
		return items.filter(function (item) {
			if (!item || seen[item]) {
				return false;
			}
			seen[item] = true;
			return true;
		}).sort(function (left, right) {
			return left.localeCompare(right);
		});
	}

	function resolveImage(imageValue) {
		if (!imageValue) {
			return '';
		}
		if (/^https?:\/\//.test(imageValue)) {
			return imageValue;
		}
		return imageBase + '/' + String(imageValue).replace(/^\/+/, '');
	}

	function populateSelect(selectEl, values, label) {
		selectEl.innerHTML = '';
		var first = document.createElement('option');
		first.value = '';
		first.textContent = label;
		selectEl.appendChild(first);
		values.forEach(function (value) {
			var option = document.createElement('option');
			option.value = value;
			option.textContent = value;
			selectEl.appendChild(option);
		});
	}

	function collectValues(field) {
		var values = [];
		stations.forEach(function (station) {
			if (field === 'Country' || field === 'Region' || field === 'Codec') {
				if (station[field]) {
					values.push(String(station[field]));
				}
				return;
			}
			splitValues(station[field]).forEach(function (value) { values.push(value); });
		});
		return uniqueValues(values);
	}

	function matchesFilter(station, query, country, language, genre, codec) {
		var haystack = [
			station.Name,
			station.Description,
			station.Country,
			station.Region,
			station.Genre,
			station.Languages,
			station.Codec,
			station.Homepage
		].join(' ').toLowerCase();
		if (query && haystack.indexOf(query) === -1) {
			return false;
		}
		if (country && String(station.Country || '') !== country) {
			return false;
		}
		if (codec && String(station.Codec || '') !== codec) {
			return false;
		}
		if (language && splitValues(station.Languages).indexOf(language) === -1) {
			return false;
		}
		if (genre && splitValues(station.Genre).indexOf(genre) === -1) {
			return false;
		}
		return true;
	}

		function renderStationActionForm(action, label, station) {
			return '' +
				'<form action="$(href status mpd-mpc)" method="get">' +
					'<input type="hidden" name="action" value="' + htmlEscape(action) + '">' +
					'<input type="hidden" name="stream_name_b64" value="' + htmlEscape(toBase64Url(station.Name || '')) + '">' +
					'<input type="hidden" name="stream_uri_b64" value="' + htmlEscape(toBase64Url(station.StreamUri || '')) + '">' +
					'<input type="hidden" name="stream_image_b64" value="' + htmlEscape(toBase64Url(station.Image || '')) + '">' +
					'<input type="hidden" name="stream_homepage_b64" value="' + htmlEscape(toBase64Url(station.Homepage || '')) + '">' +
					'<button type="submit">' + htmlEscape(label) + '</button>' +
				'</form>';
		}

		function toBase64Url(value) {
			var encoded = window.btoa(unescape(encodeURIComponent(String(value || ''))));
			return encoded.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
		}

	function renderCard(station) {
		var image = resolveImage(station.Image || '');
		var description = station.Description || station.Homepage || '';
		var tags = uniqueValues([
			station.Country || '',
			station.Region || '',
			station.Codec || '',
			station.Bitrate ? String(station.Bitrate) + ' kbps' : ''
		].concat(splitValues(station.Languages)).concat(splitValues(station.Genre))).slice(0, 7);
		var tagHtml = tags.map(function (tag) {
			return '<span class="mpc-tag">' + htmlEscape(tag) + '</span>';
		}).join('');
		var altCount = station.alternativeStreams ? Object.keys(station.alternativeStreams).length : 0;
		var thumbHtml = image ? '<img src="' + htmlEscape(image) + '" alt="station">' : htmlEscape((station.Name || 'RADIO').slice(0, 5).toUpperCase());
		return '' +
			'<article class="mpc-station-card">' +
				'<div class="mpc-station-thumb">' + thumbHtml + '</div>' +
				'<div class="mpc-station-body">' +
					'<h4>' + htmlEscape(station.Name || 'Unnamed station') + '</h4>' +
					'<p>' + htmlEscape(description) + '</p>' +
					'<div class="mpc-tags">' + tagHtml + '</div>' +
					'<div class="mpc-station-buttons">' +
						renderStationActionForm('queue_add', 'Queue', station) +
						renderStationActionForm('replace_play', 'Play now', station) +
						renderStationActionForm('save_startup', 'Save startup', station) +
					'</div>' +
					(altCount ? '<p style="margin-top:10px;">Alt streams: ' + altCount + '</p>' : '') +
				'</div>' +
			'</article>';
	}

	function renderResults() {
		var query = String(queryEl.value || '').trim().toLowerCase();
		var country = countryEl.value;
		var language = languageEl.value;
		var genre = genreEl.value;
		var codec = codecEl.value;
		var filtered = stations.filter(function (station) {
			return matchesFilter(station, query, country, language, genre, codec);
		});
		countEl.textContent = filtered.length + ' / ' + stations.length;
		if (!filtered.length) {
			resultsEl.innerHTML = '<div class="mpc-empty">$(lang de:"Keine Station passt zu den aktuellen Filtern." en:"No station matches the current filters.")</div>';
			return;
		}
		if (filtered.length > resultLimit) {
			statusEl.textContent = '$(lang de:"Zeige erste" en:"Showing first") ' + resultLimit + ' $(lang de:"von" en:"of") ' + filtered.length + ' $(lang de:"Stationen" en:"stations")';
		} else {
			statusEl.textContent = '$(lang de:"Gefundene Stationen" en:"Matching stations")';
		}
		resultsEl.innerHTML = filtered.slice(0, resultLimit).map(renderCard).join('');
	}

	function normalizeStations(payload) {
		var radios = payload.webradios || {};
		stations = Object.keys(radios).map(function (key, index) {
			var station = radios[key] || {};
			station._index = index;
			if (!station.Name) {
				station.Name = key;
			}
			return station;
		}).sort(function (left, right) {
			return String(left.Name || '').localeCompare(String(right.Name || ''));
		});
		stations.forEach(function (station, index) {
			station._index = index;
		});
	}

	// Keep search reactive while typing, but avoid blur-triggered rerender on submit clicks.
	queryEl.addEventListener('input', renderResults);
	[countryEl, languageEl, genreEl, codecEl].forEach(function (element) {
		element.addEventListener('change', renderResults);
	});

	fetch(endpoint)
		.then(function (response) { return response.text(); })
		.then(parseWrappedJson)
		.then(function (payload) {
			if (payload.error) {
				throw new Error(payload.error);
			}
			normalizeStations(payload);
			populateSelect(countryEl, collectValues('Country'), '$(lang de:"Alle Laender" en:"All countries")');
			populateSelect(languageEl, collectValues('Languages'), '$(lang de:"Alle Sprachen" en:"All languages")');
			populateSelect(genreEl, collectValues('Genre'), '$(lang de:"Alle Genres" en:"All genres")');
			populateSelect(codecEl, collectValues('Codec'), '$(lang de:"Alle Codecs" en:"All codecs")');
			statusEl.textContent = '$(lang de:"WebRadioDB bereit" en:"WebRadioDB ready")';
			renderResults();
		})
		.catch(function (error) {
			statusEl.textContent = error.message;
			resultsEl.innerHTML = '<div class="mpc-empty">' + htmlEscape(error.message) + '</div>';
		});
}());
</script>
EOF
