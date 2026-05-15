#!/bin/sh

. /usr/lib/libmodcgi.sh

sec_begin "$(lang de:"Anzeigen" en:"Show")"
cat << EOF
<ul>
<li><a href="$(href status alsa-utils)">$(lang de:"Audio-Status und Tests anzeigen" en:"Show audio status and test tools")</a></li>
</ul>
EOF
sec_end

sec_begin "$(lang de:"Hinweis zu alsamixer" en:"About alsamixer")"
cat << EOF
<p>
$(lang de:"<code>alsamixer</code> fehlt hier absichtlich, weil das aktuelle Paket mit <code>--disable-alsamixer</code> gebaut wird, um die ncurses-Oberfl\u00e4chenabh\u00e4ngigkeit klein zu halten. Verwenden Sie stattdessen <code>amixer</code> oder diese Web-Oberfl\u00e4che." en:"<code>alsamixer</code> is intentionally absent here because the current package is built with <code>--disable-alsamixer</code> to avoid the ncurses UI dependency stack. Use <code>amixer</code> or this web UI instead.")
</p>
EOF
sec_end

if [ -r /proc/asound/cards ]; then
	sec_begin "$(lang de:"Erkannte Soundkarten" en:"Detected sound cards")"
	echo '<pre class="log full">'
	cat /proc/asound/cards | html
	echo '</pre>'
	sec_end
fi