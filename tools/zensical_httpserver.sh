#! /usr/bin/env bash
SCRIPT="$(readlink -f $0)"
PARENT="$(dirname ${SCRIPT%/*})"
ZENDIR="$PARENT/docs"
# NOTE: the virtual environment must stay OUTSIDE $ZENDIR. When zensical runs
# from a venv located inside the docs directory (seen with 0.0.69) it silently
# omits assets/ (plus 404.html and sitemap.xml) from the build output, so the
# preview has no CSS at all: no Material layout, no right-hand "On this page"
# column.
ENVDIR="$PARENT/.venv-build"


detect_linux() {
	NAME="$(sed -rn 's/^NAME=//p' /etc/os-release 2>/dev/null)"
	NAME="$(echo $NAME | sed 's/"//g;s/ *Linux *//;s/ .*//;s/\..*//')"
	VERSION="$(sed -rn 's/^VERSION=//p' /etc/os-release 2>/dev/null)"
	VERSION="$(echo $VERSION | sed 's/"//g;s/ .*//;s/\..*//')"
	echo "$NAME$VERSION"
}

install_python() {
	local SUDO DOY="$1"
	local OSV="$(detect_linux)"
	[ -z "$OSV" ] && echo 'Can not detect your Linux version, failed.' && exit 1
	[ -x "$(command -v sudo)" ] && SUDO="sudo" || SUDO=""
	[ -x "$(command -v apt)"  ] && APT="apt"   || APT="apt-get"

	case "${OSV##*/}" in
		Fedora*)                                    $SUDO dnf --refresh  install $DOY python3 python3-pip python3-virtualenv || exit 1 ;;
		Debian*|Devuan*|LMDE*) $SUDO $APT update && $SUDO $APT           install $DOY python3 python3-pip python3-venv       || exit 1 ;;
		Ubuntu*|Mint*)         $SUDO $APT update && $SUDO $APT           install $DOY python3 python3-pip python3-venv       || exit 1 ;;
		*)                     echo 'You Linux distribution is not yet supported'                                            && exit 1 ;;
	esac
}

setup_virtenv() {
	[ -d "$ZENDIR/.venv" ] && \
	  echo "Note: $ZENDIR/.venv is no longer used, run '$0 cleanup' to remove it."

	[ -x "$(command -v python3)" ] || \
	  python3 -m venv -h >/dev/null 2>&1 || \
	  [ -x "$(command -v pip3)" ] || \
	  install_python || exit 1

	python3 -m venv "$ENVDIR"                                   || exit 1
	source "$ENVDIR/bin/activate"                               || exit 1
	pip3 install --upgrade pip                                  || exit 1
	pip3 install "zensical"                                     || exit 1
}

run_httpserver() {
	local PORT="$1"
	local BIND="0.0.0.0"
	[ "$PORT" -gt 0 ] 2>/dev/null || PORT="8000"
	local LOG="${TMPDIR:-/tmp}/zensical_httpserver_${PORT}.log"

	echo "########################################################################"
	echo "     Building the docs site, then serving it on http://$BIND:$PORT (CTRL+C to quit)."
	echo "########################################################################"

	# Do not use "zensical serve" for this preview: zensical 0.0.69 deletes the
	# theme bundles from $ZENDIR/site and does not serve them, so every
	# /assets/... request returns 404 and the pages are rendered without any
	# CSS (no Material layout, no right-hand "On this page" index column).
	# Build the site first (this writes the bundles) and serve the output.
	build_site || exit 1

	echo "###################################################"
	echo "     Serving $ZENDIR/site on http://$BIND:$PORT"
	echo "     Open http://localhost:$PORT/ (the site root, not /freetz-evo/)"
	echo "     Request log: $LOG"
	echo "###################################################"

	source "$ENVDIR/bin/activate"
	cd "$ZENDIR/site" || exit 1
	# python's http.server logs every single request to stderr: keep the log in
	# a file instead of flooding the terminal.
	python3 -m http.server "$PORT" --bind "$BIND" 2>"$LOG"
}

build_site() {
	[ -d "$ENVDIR" ] || setup_virtenv || exit 1

	source "$ENVDIR/bin/activate"
	zensical build --config-file "$ZENDIR/zensical.toml"  # --clean

	# Guard against a build without the theme bundles (see ENVDIR above): such
	# a site is unusable, so fail loudly instead of serving a broken preview.
	if [ ! -d "$ZENDIR/site/assets" ]; then
		echo "" >&2
		echo "ERROR: $ZENDIR/site/assets is missing, the site was built without CSS." >&2
		echo "       Make sure zensical does not run from a venv inside $ZENDIR." >&2
		echo "       Current environment: $ENVDIR" >&2
		exit 1
	fi

	echo "###################################################"
	echo "     Site content can be found in ./docs/site/"
	echo "###################################################"
}

cleanup_virtenv() {
	rm -rf "$ENVDIR"
	rm -rf "$ZENDIR/.venv/"
	rm -rf "$ZENDIR/.cache/"
	rm -rf "$ZENDIR/site/"
	echo "Done."
}

show_usage() {
	cat << EOF

	Zensical http server

	Usage: $0 [ install [-y] | setup | run [port] | build | cleanup ]

	 - install [-y]
	   Installs packages by package-manager, python3, pip3 and venv.
	   You will be asked for sudo password if you have no sufficent permissions.
	   If sudo is not installed you need to have permissions to install packages.
	   To install instantly and without question use the '-y' parameter.
	   Executed by "setup" if not yet done.

	 - setup
	   Sets up virtual Python environemnt for Zensical.
	   Executed by "run" if not yet done.

	 - run [port]
	   Builds the documentation and serves the built site on all ips.
	   Default Port: 8000/tcp

	 - build
	   Build website locally only.

	 - cleanup
	   Removes caches and virtual environment directories, needs setup again.

EOF
	exit 1
}


ARG="$1"
shift
[ "$1" == '-y' ] && shift && DOY="-y" || DOY=""
PORT="$1"

case "$ARG" in
	i|install)	install_python "$DOY" ;;
	s|setup)	setup_virtenv ;;
	r|run)		run_httpserver "$PORT" ;;
	b|build)	build_site ;;
	c|cleanup)	cleanup_virtenv ;;
	*)		show_usage ;;
esac

exit 0

