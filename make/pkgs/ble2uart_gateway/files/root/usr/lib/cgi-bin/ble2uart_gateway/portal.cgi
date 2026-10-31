#!/bin/sh
# Read-only sensor dashboard for the ble2uart_gateway SQLite front-end.
#
# Sourcing libmodcgi.sh installs the standard freetz login guard: when the
# browser has no valid session the library prints the login page and exits, so
# this CGI is protected exactly like /cgi-bin/conf/* and the other packaged
# web interfaces.
#
# Everything else is done by the gateway binary in CGI mode: it reads
# QUERY_STRING, opens the database read-only (PRAGMA query_only) and prints the
# response. There is no state to keep: one process per request, no daemon.

. /usr/lib/libmodcgi.sh

DAEMON_BIN=/usr/bin/ble2uart-gateway
[ -x "$DAEMON_BIN" ] || DAEMON_BIN=/mod/external/usr/bin/ble2uart-gateway
[ -x "$DAEMON_BIN" ] || DAEMON_BIN=/mod/usr/bin/ble2uart-gateway

[ -r /mod/etc/default.ble2uart_gateway/ble2uart_gateway.cfg ] &&
	. /mod/etc/default.ble2uart_gateway/ble2uart_gateway.cfg
[ -r /mod/etc/conf/ble2uart_gateway.cfg ] &&
	. /mod/etc/conf/ble2uart_gateway.cfg
: "${BLE2UART_GATEWAY_STORE:=/tmp/flash/ble2uart_gateway}"
YAML="$BLE2UART_GATEWAY_STORE/ble2uart_gateway.yaml"

if [ ! -x "$DAEMON_BIN" ]; then
	printf 'Content-Type: text/plain; charset=UTF-8\r\n\r\nble2uart-gateway binary not found\n'
	exit 0
fi

exec "$DAEMON_BIN" --config "$YAML" --portal
