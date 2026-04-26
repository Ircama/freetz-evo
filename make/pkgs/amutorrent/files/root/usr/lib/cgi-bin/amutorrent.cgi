#!/bin/sh

PID_FILE=/var/run/amutorrent.pid
CONFIG_JSON=/mod/etc/amutorrent/data/config.json

[ -r /mod/etc/default.amutorrent/amutorrent.cfg ] && . /mod/etc/default.amutorrent/amutorrent.cfg
[ -r /mod/etc/conf/amutorrent.cfg ] && . /mod/etc/conf/amutorrent.cfg

HOST=${HTTP_HOST%%:*}
[ -z "$HOST" ] && HOST=${SERVER_NAME:-fritz.box}
PORT=${AMUTORRENT_PORT:-4000}

if [ -x /usr/bin/node ] && [ -r "$CONFIG_JSON" ]; then
	JSON_PORT=$(/usr/bin/node -e 'const fs=require("fs"); try { const cfg=JSON.parse(fs.readFileSync(process.argv[1], "utf8")); process.stdout.write(String(cfg?.server?.port || "")); } catch (_) {}' "$CONFIG_JSON" 2>/dev/null)
	[ -n "$JSON_PORT" ] && PORT=$JSON_PORT
fi

is_running() {
	if [ -f "$PID_FILE" ]; then
		pid=$(cat "$PID_FILE" 2>/dev/null)
		if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
			return 0
		fi
	fi
	pgrep -f "${AMUTORRENT_APPDIR:-/usr/lib/amutorrent}/server/server.js" >/dev/null 2>&1 && return 0
	return 1
}

if is_running; then
	echo 'Status: 302 Found'
	echo "Location: http://$HOST:$PORT/"
	echo
	exit 0
fi

cat <<EOF
Content-Type: text/html; charset=UTF-8

<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>aMUTorrent Offline</title>
  <style>
    body { font-family: sans-serif; margin: 2rem; color: #222; }
    code { background: #f4f4f4; padding: 0.15rem 0.3rem; }
  </style>
</head>
<body>
  <h1>aMUTorrent is not running</h1>
  <p>The backend service is stopped or failed to start.</p>
  <p>Expected service URL: <a href="http://$HOST:$PORT/">http://$HOST:$PORT/</a></p>
  <p>Start it manually with <code>/etc/init.d/rc.amutorrent start</code>.</p>
</body>
</html>
EOF