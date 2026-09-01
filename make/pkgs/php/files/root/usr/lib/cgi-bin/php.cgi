#!/bin/sh

. /usr/lib/libmodcgi.sh
[ -r /etc/options.cfg ] && . /etc/options.cfg


[ -z "$PHP_BIN" ] && [ "$FREETZ_PACKAGE_PHP_cgi" == "y" ] && PHP_BIN="php-cgi"
[ -z "$PHP_BIN" ] && [ "$FREETZ_PACKAGE_PHP_cli" == "y" ] && PHP_BIN="php"

# php-cgi enters "serve a script" mode when *any* CGI environment variable is
# present (REQUEST_METHOD, SERVER_*, HTTP_*, PATH_INFO, ...), printing
# "Security Alert" or "No input file specified" instead of version/module
# info. Run it with a clean environment; PATH is passed explicitly because
# the binary lives in /usr/bin (or /mod/external/usr/bin via symlink).
PHP_INFO_CALL="env -i PATH=$PATH \
$PHP_BIN -d zlib.output_compression=Off -d cgi.force_redirect=0"

# This page is purely informational (version + modules); nothing to save.
# Hide the framework form buttons (Apply/Default), same pattern as ncdu.cgi.
cat << 'EOF'
<style>
input[type="submit"],
input[type="reset"],
button[type="submit"] { display: none !important; }
</style>
EOF


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
$PHP_INFO_CALL -v | html
else
strings /usr/lib/apache2/libphp*.so | grep -E '^(Zend Engine|PHP/)' | sort | html
fi
echo '</FONT></pre>'
sec_end


if [ -n "$PHP_BIN" ]; then
sec_begin "$(lang de:"Module" en:"Modules")"

echo -n '<pre><FONT SIZE=-1>'
$PHP_INFO_CALL -m | html
echo '</FONT></pre>'

sec_end
fi


