#!/bin/sh

DAEMON=php
DAEMON_LONG_NAME="PHP"
DAEMON_CFGFILE="/tmp/flash/$DAEMON/$DAEMON.ini"
. /etc/init.d/modlibrc


[ -r /etc/options.cfg ] && . /etc/options.cfg

[ -z "$PHP_BIN" ] && [ "$FREETZ_PACKAGE_PHP_cgi" == "y" ] && PHP_BIN="php-cgi"
[ -z "$PHP_BIN" ] && [ "$FREETZ_PACKAGE_PHP_cli" == "y" ] && PHP_BIN="php"


case $1 in
	""|load)
		modlib_defaults $DAEMON_CFGFILE

		#compat 2026/08: may be removed later
		if [ -e /tmp/flash/php.ini ]; then
			mv /tmp/flash/php /tmp/flash/php.d
			mkdir -p /tmp/flash/php
			mv /tmp/flash/php.d/ /tmp/flash/php/
			rm -f /tmp/flash/php/php.d/php.ini
			mv /tmp/flash/php.ini /tmp/flash/php/
		fi

		[ -n "$PHP_BIN" ] && \
		modreg status $DAEMON $DAEMON_LONG_NAME info
		modreg file $DAEMON config 'php.ini' 0 "php_config"
		modreg cgi $DAEMON $DAEMON_LONG_NAME
		modreg daemon --hide $DAEMON
		;;
	unload)
		modunreg daemon $DAEMON
		modunreg cgi $DAEMON
		modunreg file $DAEMON
		modunreg status $DAEMON
		;;
	*)
		echo "Usage: $0 [load|unload]" 1>&2
		exit 1
		;;
esac

exit 0
