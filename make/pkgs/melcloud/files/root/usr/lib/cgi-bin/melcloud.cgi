#!/bin/sh

. /usr/lib/libmodcgi.sh

[ -r /mod/etc/conf/melcloud.cfg ] && . /mod/etc/conf/melcloud.cfg

: ${MELCLOUD_ENABLED:=no}
: ${MELCLOUD_EMAIL:=}
: ${MELCLOUD_PASSWORD:=}
: ${MELCLOUD_CONTEXT_KEY:=}
: ${MELCLOUD_BASE_URL:=https://app.melcloud.com/Mitsubishi.Wifi.Client}
: ${MELCLOUD_APP_VERSION:=1.34.13.0}
: ${MELCLOUD_LANGUAGE:=0}
: ${MELCLOUD_POLL_SECONDS:=60}
: ${MELCLOUD_HOME_FILE:=/tmp/flash/melcloud/home.json}
: ${MELCLOUD_TEMPLATE_DIR:=/tmp/flash/melcloud/templates}

CLI=/usr/bin/melcloud-cli
RUNTIME_DIR=/tmp/flash/melcloud
SESSION_FILE=$RUNTIME_DIR/session.key
MELCLOUD_WEB_HTML=

resolve_web_html() {
	for p in \
		"/mod/external/usr/mww/melcloud/index.html" \
		"/usr/mww/melcloud/index.html" \
		"/mod/usr/mww/melcloud/index.html"
	do
		if [ -r "$p" ]; then
			MELCLOUD_WEB_HTML="$p"
			return 0
		fi
	done
	return 1
}

ensure_runtime() {
	mkdir -p "$RUNTIME_DIR" 2>/dev/null
	mkdir -p "$MELCLOUD_TEMPLATE_DIR" 2>/dev/null
	if [ ! -f "$MELCLOUD_HOME_FILE" ]; then
		echo '{"homeName":"My Home","devices":[]}' > "$MELCLOUD_HOME_FILE" 2>/dev/null
	fi
}

sanitize_template_name() {
	case "$1" in
		""|*[!A-Za-z0-9._-]*) return 1 ;;
		*) return 0 ;;
	esac
}

json_start() {
	cat << EOF
Content-Type: text/html; charset=UTF-8

<style>
.ajax-json-box { display: none; }
</style>
<div class="ajax-json-box"><div class="ajax-json-content"><pre>Content-Type: application/json

EOF
}

json_end() {
	echo '</pre></div></div>'
}

cli_exec() {
	cmd="$1"
	shift
	"$CLI" "$cmd" "$@" 2>&1
}

cli_common_auth() {
	CTX_OPT=
	if [ -n "$MELCLOUD_CONTEXT_KEY" ]; then
		CTX_OPT="--context $MELCLOUD_CONTEXT_KEY"
	elif [ -f "$SESSION_FILE" ]; then
		CTX_OPT="--session $SESSION_FILE"
	fi
}

AJAX_MODE="$(cgi_param ajax)"
DASHBOARD_MODE="$(cgi_param dashboard)"

if [ "$DASHBOARD_MODE" = "1" ]; then
	if resolve_web_html; then
		echo "Content-Type: text/html; charset=UTF-8"
		echo
		cat "$MELCLOUD_WEB_HTML"
	else
		echo "Content-Type: text/plain; charset=UTF-8"
		echo
		echo "MELCloud dashboard file not found. Expected one of:"
		echo "/mod/external/usr/mww/melcloud/index.html"
		echo "/usr/mww/melcloud/index.html"
		echo "/mod/usr/mww/melcloud/index.html"
	fi
	exit 0
fi

if [ "$AJAX_MODE" = "1" ]; then
	ensure_runtime
	json_start

	ACTION="$(cgi_param action)"
	cli_common_auth

	if [ ! -x "$CLI" ]; then
		echo '{"success":false,"error":"melcloud-cli is not installed"}'
	elif [ "$ACTION" = "login" ]; then
		EMAIL="$(cgi_param email)"
		PASS="$(cgi_param password)"
		[ -z "$EMAIL" ] && EMAIL="$MELCLOUD_EMAIL"
		[ -z "$PASS" ] && PASS="$MELCLOUD_PASSWORD"
		if [ -n "$EMAIL" ] && [ -n "$PASS" ]; then
			cli_exec login2 --email "$EMAIL" --password "$PASS" --base-url "$MELCLOUD_BASE_URL" --app-version "$MELCLOUD_APP_VERSION" --session "$SESSION_FILE"
		else
			echo '{"success":false,"error":"Missing email/password"}'
		fi
	elif [ "$ACTION" = "login_legacy" ]; then
		EMAIL="$(cgi_param email)"
		PASS="$(cgi_param password)"
		[ -z "$EMAIL" ] && EMAIL="$MELCLOUD_EMAIL"
		[ -z "$PASS" ] && PASS="$MELCLOUD_PASSWORD"
		if [ -n "$EMAIL" ] && [ -n "$PASS" ]; then
			cli_exec login --email "$EMAIL" --password "$PASS" --base-url "$MELCLOUD_BASE_URL" --app-version "$MELCLOUD_APP_VERSION" --session "$SESSION_FILE"
		else
			echo '{"success":false,"error":"Missing email/password"}'
		fi
	elif [ "$ACTION" = "list_devices" ]; then
		if [ -n "$CTX_OPT" ]; then
			cli_exec list-devices $CTX_OPT --base-url "$MELCLOUD_BASE_URL"
		else
			echo '{"success":false,"error":"No context key configured"}'
		fi
	elif [ "$ACTION" = "get_user_details" ]; then
		if [ -n "$CTX_OPT" ]; then
			cli_exec get-user-details $CTX_OPT --base-url "$MELCLOUD_BASE_URL"
		else
			echo '{"success":false,"error":"No context key configured"}'
		fi
	elif [ "$ACTION" = "get_device" ]; then
		ID="$(cgi_param id)"
		BID="$(cgi_param building)"
		if [ -n "$CTX_OPT" ] && [ -n "$ID" ] && [ -n "$BID" ]; then
			cli_exec get-device --id "$ID" --building "$BID" $CTX_OPT --base-url "$MELCLOUD_BASE_URL"
		else
			echo '{"success":false,"error":"Missing id/building/context"}'
		fi
	elif [ "$ACTION" = "list_device_units" ]; then
		ID="$(cgi_param id)"
		if [ -n "$CTX_OPT" ] && [ -n "$ID" ]; then
			cli_exec list-device-units --id "$ID" $CTX_OPT --base-url "$MELCLOUD_BASE_URL"
		else
			echo '{"success":false,"error":"Missing id/context"}'
		fi
	elif [ "$ACTION" = "set_device" ]; then
		ID="$(cgi_param id)"
		BID="$(cgi_param building)"
		DTYPE="$(cgi_param dtype)"
		PAYLOAD="$(cgi_param payload)"
		if [ -n "$CTX_OPT" ] && [ -n "$ID" ] && [ -n "$BID" ] && [ -n "$DTYPE" ] && [ -n "$PAYLOAD" ]; then
			case "$DTYPE" in
				ata|atw|erv)
					cli_exec "set-$DTYPE" --id "$ID" --building "$BID" --json-text "$PAYLOAD" $CTX_OPT --base-url "$MELCLOUD_BASE_URL"
					;;
				*)
					echo '{"success":false,"error":"dtype must be ata|atw|erv"}'
					;;
			esac
		else
			echo '{"success":false,"error":"Missing id/building/dtype/payload/context"}'
		fi
	elif [ "$ACTION" = "energy_report" ]; then
		ID="$(cgi_param id)"
		FROM="$(cgi_param from)"
		TO="$(cgi_param to)"
		if [ -n "$CTX_OPT" ] && [ -n "$ID" ] && [ -n "$FROM" ] && [ -n "$TO" ]; then
			cli_exec energy-report --id "$ID" --from "$FROM" --to "$TO" $CTX_OPT --base-url "$MELCLOUD_BASE_URL"
		else
			echo '{"success":false,"error":"Missing id/from/to/context"}'
		fi
	elif [ "$ACTION" = "raw_get" ]; then
		ENDPOINT="$(cgi_param endpoint)"
		if [ -n "$CTX_OPT" ] && [ -n "$ENDPOINT" ]; then
			cli_exec raw-get --endpoint "$ENDPOINT" $CTX_OPT --base-url "$MELCLOUD_BASE_URL"
		else
			echo '{"success":false,"error":"Missing endpoint/context"}'
		fi
	elif [ "$ACTION" = "raw_post" ]; then
		ENDPOINT="$(cgi_param endpoint)"
		PAYLOAD="$(cgi_param payload)"
		if [ -n "$CTX_OPT" ] && [ -n "$ENDPOINT" ] && [ -n "$PAYLOAD" ]; then
			cli_exec raw-post --endpoint "$ENDPOINT" --json-text "$PAYLOAD" $CTX_OPT --base-url "$MELCLOUD_BASE_URL"
		else
			echo '{"success":false,"error":"Missing endpoint/payload/context"}'
		fi
	elif [ "$ACTION" = "set_options" ]; then
		ID="$(cgi_param id)"
		BID="$(cgi_param building)"
		PAYLOAD="$(cgi_param payload)"
		if [ -n "$CTX_OPT" ] && [ -n "$ID" ] && [ -n "$BID" ] && [ -n "$PAYLOAD" ]; then
			cli_exec set-options --id "$ID" --building "$BID" --json-text "$PAYLOAD" $CTX_OPT --base-url "$MELCLOUD_BASE_URL"
		else
			echo '{"success":false,"error":"Missing id/building/payload/context"}'
		fi
	elif [ "$ACTION" = "update_application_options" ]; then
		PAYLOAD="$(cgi_param payload)"
		if [ -n "$CTX_OPT" ] && [ -n "$PAYLOAD" ]; then
			cli_exec update-application-options --json-text "$PAYLOAD" $CTX_OPT --base-url "$MELCLOUD_BASE_URL"
		else
			echo '{"success":false,"error":"Missing payload/context"}'
		fi
	elif [ "$ACTION" = "template_list" ]; then
		cli_exec template-list --template-dir "$MELCLOUD_TEMPLATE_DIR"
	elif [ "$ACTION" = "template_get" ]; then
		NAME="$(cgi_param name)"
		if sanitize_template_name "$NAME"; then
			cli_exec template-show --name "$NAME" --template-dir "$MELCLOUD_TEMPLATE_DIR"
		else
			echo '{"success":false,"error":"Invalid template name"}'
		fi
	elif [ "$ACTION" = "template_save" ]; then
		NAME="$(cgi_param name)"
		PAYLOAD="$(cgi_param payload)"
		if sanitize_template_name "$NAME" && [ -n "$PAYLOAD" ]; then
			cli_exec template-save --name "$NAME" --json-text "$PAYLOAD" --template-dir "$MELCLOUD_TEMPLATE_DIR"
		else
			echo '{"success":false,"error":"Invalid template name or payload"}'
		fi
	elif [ "$ACTION" = "template_delete" ]; then
		NAME="$(cgi_param name)"
		if sanitize_template_name "$NAME"; then
			cli_exec template-delete --name "$NAME" --template-dir "$MELCLOUD_TEMPLATE_DIR"
		else
			echo '{"success":false,"error":"Invalid template name"}'
		fi
	elif [ "$ACTION" = "template_apply" ]; then
		NAME="$(cgi_param name)"
		DTYPE="$(cgi_param dtype)"
		ID="$(cgi_param id)"
		BID="$(cgi_param building)"
		if sanitize_template_name "$NAME" && [ -n "$CTX_OPT" ] && [ -n "$DTYPE" ] && [ -n "$ID" ] && [ -n "$BID" ]; then
			cli_exec template-apply --name "$NAME" --type "$DTYPE" --id "$ID" --building "$BID" --template-dir "$MELCLOUD_TEMPLATE_DIR" $CTX_OPT --base-url "$MELCLOUD_BASE_URL"
		else
			echo '{"success":false,"error":"Invalid params for template apply"}'
		fi
	elif [ "$ACTION" = "home_get" ]; then
		if [ -f "$MELCLOUD_HOME_FILE" ]; then
			cat "$MELCLOUD_HOME_FILE"
		else
			echo '{"homeName":"My Home","devices":[]}'
		fi
	elif [ "$ACTION" = "home_set" ]; then
		MAP_JSON="$(cgi_param map_json)"
		if [ -n "$MAP_JSON" ]; then
			echo "$MAP_JSON" > "$MELCLOUD_HOME_FILE" 2>/dev/null && echo '{"success":true}' || echo '{"success":false,"error":"Failed to save home map"}'
		else
			echo '{"success":false,"error":"map_json is required"}'
		fi
	else
		echo '{"success":false,"error":"Unknown action"}'
	fi

	json_end
	exit 0
fi

sec_begin "$(lang de:"MELCloud Zugriff" en:"MELCloud access")"
cgi_print_checkbox_p "enabled" "$MELCLOUD_ENABLED" "$(lang de:"MELCloud aktivieren" en:"Enable MELCloud package")"
cgi_print_textline_p "email" "$MELCLOUD_EMAIL" 36/128 "$(lang de:"E-Mail" en:"Email"): "
cgi_print_password_p "password" "$MELCLOUD_PASSWORD" 20/128 "$(lang de:"Passwort" en:"Password"): "
cgi_print_textline_p "context_key" "$MELCLOUD_CONTEXT_KEY" 52/255 "$(lang de:"Context Key (optional)" en:"Context key (optional)"): "
cgi_print_textline_p "base_url" "$MELCLOUD_BASE_URL" 58/255 "$(lang de:"API Basis-URL" en:"API base URL"): "
cgi_print_textline_p "app_version" "$MELCLOUD_APP_VERSION" 16/32 "$(lang de:"App-Version" en:"App version"): "
cgi_print_textline_p "language" "$MELCLOUD_LANGUAGE" 4/4 "$(lang de:"Sprache (0=en)" en:"Language (0=en)"): "
sec_end

sec_begin "$(lang de:"GUI Runtime" en:"GUI runtime")"
cgi_print_textline_p "poll_seconds" "$MELCLOUD_POLL_SECONDS" 8/8 "$(lang de:"Polling Intervall (s)" en:"Polling interval (s)"): "
cgi_print_textline_p "home_file" "$MELCLOUD_HOME_FILE" 48/255 "$(lang de:"Home-Mapping Datei" en:"Home mapping file"): "
cgi_print_textline_p "template_dir" "$MELCLOUD_TEMPLATE_DIR" 48/255 "$(lang de:"Template Verzeichnis" en:"Template directory"): "
cat << EOF
<ul>
<li><a href="/cgi-bin/conf/melcloud?dashboard=1">$(lang de:"MELCloud Dashboard oeffnen" en:"Open MELCloud dashboard")</a></li>
<li><a href="/melcloud/index.html">$(lang de:"Direkte URL (nur wenn statische Webroot dies bereitstellt)" en:"Direct URL (only when static webroot provides it)")</a></li>
</ul>
EOF
sec_end

sec_begin "$(lang de:"Hinweis" en:"Note")"
cat << EOF
<p>
$(lang de:"MELCloud ist eine inoffizielle API-Integration. Veraenderungen auf der Herstellerseite koennen Anpassungen erforderlich machen. Verwenden Sie vernuenftige Polling-Intervalle (mindestens 60 Sekunden)." en:"MELCloud is an unofficial API integration. Vendor-side changes may require updates. Use reasonable polling intervals (at least 60 seconds).")
</p>
EOF
sec_end
