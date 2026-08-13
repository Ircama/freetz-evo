#!/bin/sh

. /usr/lib/libmodcgi.sh
[ -r /etc/options.cfg ] && . /etc/options.cfg


[ -z "$PHP_BIN" ] && [ "$FREETZ_PACKAGE_PHP_cgi" == "y" ] && PHP_BIN="php-cgi"
[ -z "$PHP_BIN" ] && [ "$FREETZ_PACKAGE_PHP_cli" == "y" ] && PHP_BIN="php"


if [ -n "$PHP_BIN" ]; then
sec_begin "$(lang de:"Anzeigen" en:"Extra")"

cat << EOF
<ul>
<li><a href="$(href status php info)">$(lang de:"PHP-Info" en:"PHP info")</a></li>
</ul>
EOF

sec_end
fi


sec_begin "$(lang de:"Version" en:"Version")"
echo -n '<pre><FONT SIZE=-1>'
if [ -n "$PHP_BIN" ]; then
$PHP_BIN -d zlib.output_compression=Off -v | html
else
strings /usr/lib/apache2/libphp*.so | grep -E '^(Zend Engine|PHP/)' | sort | html
fi
echo '</FONT></pre>'
sec_end


if [ -n "$PHP_BIN" ]; then
sec_begin "$(lang de:"Module" en:"Modules")"

echo -n '<pre><FONT SIZE=-1>'
$PHP_BIN -d zlib.output_compression=Off -m | html
echo '</FONT></pre>'

sec_end
fi


