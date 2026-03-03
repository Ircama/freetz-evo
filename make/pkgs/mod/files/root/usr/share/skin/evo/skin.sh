skin_head() {
	local title=$1 id=$2
	local hname="$(hostname -s|html)"
	[ "$hname" != "fritz" ] && hname="&nbsp;&#64;${hname}" || hname=""
	cat << EOF
<title>$title&nbsp;&ndash; Freetz-Evo${hname}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" type="text/css" href="/style/evo/base.css">
<link rel="stylesheet" type="text/css" href="/style/colorscheme.css">
EOF
	_cgi_print_extra_styles

	# There is padding in #container (2x24px), so make #world wider
	let _world_width=_cgi_width+48
	cat << EOF
<style type="text/css">
#world {
    max-width: ${_world_width}px;
}
</style>
<script>
(function(){
  try {
    var b = document.body || document.documentElement;
    if (localStorage.getItem('evo-dark') === '1')   b.className += ' dark-mode';
    if (localStorage.getItem('evo-nav')  === 'top') b.className += ' evo-topnav';
  } catch(e) {}
})();
</script>
EOF
}

skin_body_begin() {
	local title=$1 id=$2
	cat << EOF
<div id="world">
<div id="header">
<div id="header-inner">
<h1><a href="https://freetz-ng.github.io" target="_blank" class="logo">Freetz<span class="evo-brand">-Evo</span></a>&nbsp;<a id="about" href="/cgi-bin/about.cgi" target="_blank">&ndash;</a>&nbsp;<span class="title">$title</span></h1>
<div id="header-right">
EOF
if [ -n "$_CGI_HELP" ]; then
	echo "<a class='help' href='$(html "$_CGI_HELP")'>$(lang de:"Hilfe" en:"Help")</a>"
fi
	cat << 'EOF'
<button class="evo-dark-toggle" id="evo-dark-btn" title="Dark / Light mode" onclick="evoDarkToggle()">&#9681;</button>
<button class="evo-hamburger" id="evo-ham-btn" title="Menu" onclick="evoHamToggle()">&#9776;</button>
EOF
	cat << EOF
<span class="version">$(html < /etc/.freetz-version)</span>
</div>
</div>
</div>
<div class="evo-nav-overlay" id="evo-overlay" onclick="evoHamClose()"></div>
<div id="container">
EOF

	_cgi_print_menu "$id"
	_cgi_print_submenu "$id"

	echo "<div id='content'>"
}

skin_body_end() {
	cat << 'EOF'
</div>
</div>
<div id="footer">
<div id="footer-inner">
EOF
	cat << EOF
<span class="footer-left">
<span class="datetime" title="$(lang de:"Systemzeit des Routers" en:"Router's system time")">$(date +'$(lang de:"%d.%m.%Y" en:"%m/%d/%Y") %H:%M')</span>&nbsp;&ndash;
<span class="uptime" title="Uptime">$(uptime | sed -r 's/.*(up.*), *load.*/\1/')</span>
</span>
<span class="footer-right">Freetz-Evo</span>
</div>
</div>
</div>
<script>
function evoDarkToggle() {
  var b = document.body;
  b.classList.toggle('dark-mode');
  b.classList.remove('light-mode');
  try { localStorage.setItem('evo-dark', b.classList.contains('dark-mode') ? '1' : '0'); } catch(e) {}
}
function evoHamToggle() {
  document.body.classList.toggle('evo-menu-open');
}
function evoHamClose() {
  document.body.classList.remove('evo-menu-open');
}
</script>
EOF
}

skin_sec_begin() {
	echo "<div class='section'><h1>$1</h1>"
}

skin_sec_end() {
	echo "</div>"
}
