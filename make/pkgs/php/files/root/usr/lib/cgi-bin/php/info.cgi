#!/bin/sh

. /usr/lib/libmodcgi.sh
[ -r /etc/options.cfg ] && . /etc/options.cfg


[ -z "$PHP_BIN" ] && [ "$FREETZ_PACKAGE_PHP_cgi" == "y" ] && PHP_BIN="php-cgi"
[ -z "$PHP_BIN" ] && [ "$FREETZ_PACKAGE_PHP_cli" == "y" ] && PHP_BIN="php"

echo "<h1>$(lang de:"PHP-Info" en:"PHP info")</h1>"
echo -n '<pre id="log" class="log full">'
[ -z "$PHP_BIN" ] || $PHP_BIN -d zlib.output_compression=Off -i | html
echo '</pre>'

