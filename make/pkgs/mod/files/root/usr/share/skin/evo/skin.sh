skin_head() {
	local title=$1 id=$2
	local hname="$(hostname -s|html)"
	[ "$hname" != "fritz" ] && hname="&nbsp;&#64;${hname}" || hname=""
	cat << EOF
<title>$title&nbsp;&ndash; Freetz-EVO${hname}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" type="text/css" href="/style/evo/base.css">
<link rel="stylesheet" type="text/css" href="/style/colorscheme.css">
EOF
	_cgi_print_extra_styles

	# There is padding in #container (2x24px), so make #world wider
	let _world_width=_cgi_width+48
	cat << EOF
<style type="text/css">
:root { --evo-cgi-width: ${_world_width}px; }
</style>
<script>
(function(){
  try {
    var ck = '; ' + document.cookie;
    var h  = document.documentElement;
    if (ck.indexOf('; evo-dark=1')       !== -1) h.classList.add('dark-mode');
    if (ck.indexOf('; evo-dark=0')       !== -1) h.classList.add('light-mode');
    if (ck.indexOf('; evo-nav=top')      !== -1) h.classList.add('evo-topnav');
    if (ck.indexOf('; evo-navmode=ham')  !== -1) h.classList.add('evo-hammode');
    // Sync html classes → body once DOM is ready (CSS targets body.dark-mode)
    document.addEventListener('DOMContentLoaded', function() {
      if (h.classList.contains('dark-mode'))   document.body.classList.add('dark-mode');
      if (h.classList.contains('light-mode'))  document.body.classList.add('light-mode');
      if (h.classList.contains('evo-topnav'))  document.body.classList.add('evo-topnav');
      if (h.classList.contains('evo-hammode')) document.body.classList.add('evo-hammode');
    });
    // Width override from cookie (e.g. evo-width=1100px)
    var wm = ck.match(/; evo-width=(\d+px)/);
    if (wm) h.style.setProperty('--evo-world-max', wm[1]);
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
<h1><a href="https://freetz-ng.github.io" target="_blank" class="logo">Freetz<span class="evo-brand">-EVO</span></a>&nbsp;<a id="about" href="/cgi-bin/about.cgi" target="_blank">&ndash;</a>&nbsp;<span class="title">$title</span></h1>
<div id="header-right">
EOF
if [ -n "$_CGI_HELP" ]; then
	echo "<button class='evo-dark-toggle evo-help-btn' onclick=\"location.href='$(html "$_CGI_HELP")'\">$(lang de:"Hilfe" en:"Help" it:"Aiuto" fr:"Aide" es:"Ayuda")</button>"
fi
	cat << 'EOF'
<button class="evo-dark-toggle evo-navmode-btn" id="evo-navmode-btn" title="Toggle tree menu" onclick="evoNavModeToggle()"><svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" viewBox="0 0 14 12" fill="currentColor" aria-hidden="true" style="vertical-align:middle"><rect x="0" y="0" width="14" height="2"/><rect x="3" y="5" width="11" height="2"/><rect x="3" y="10" width="11" height="2"/></svg></button>
<div id="evo-ham-wrap"><button class="evo-dark-toggle evo-ham-open-btn" id="evo-ham-open-btn" title="Open menu">&#9776;</button></div>
<button class="evo-dark-toggle evo-width-toggle" id="evo-width-btn" title="Page width" onclick="evoWidthToggle()">&#8646;</button>
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
<span class="footer-right">Freetz-EVO</span>
</div>
</div>
</div>
<script>
function evoDarkToggle() {
  var h = document.documentElement;
  var b = document.body;
  var hasDarkClass  = h.classList.contains('dark-mode');
  var hasLightClass = h.classList.contains('light-mode');
  var osDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  // Effective dark = explicit dark-mode class, OR OS dark preference not overridden by light-mode
  var currentlyDark = hasDarkClass || (osDark && !hasLightClass);
  if (currentlyDark) {
    // Switch to light
    h.classList.remove('dark-mode');
    b.classList.remove('dark-mode');
    if (osDark) {
      // Must add light-mode to suppress OS dark preference
      h.classList.add('light-mode');
      b.classList.add('light-mode');
    }
    var age = osDark ? 20*365*24*3600 : 0;
    document.cookie = 'evo-dark=0; Path=/; Max-Age=' + age + '; SameSite=Lax';
  } else {
    // Switch to dark
    h.classList.remove('light-mode');
    b.classList.remove('light-mode');
    h.classList.add('dark-mode');
    b.classList.add('dark-mode');
    document.cookie = 'evo-dark=1; Path=/; Max-Age=' + (20*365*24*3600) + '; SameSite=Lax';
  }
}
function evoWidthToggle() {
  var h = document.documentElement;
  var vals = ['900px', '1100px', '750px', '800px', '850px'];
  var cur = (getComputedStyle(h).getPropertyValue('--evo-world-max') || '').trim();
  var idx = vals.indexOf(cur);
  var next = vals[(idx + 1) % vals.length];
  h.style.setProperty('--evo-world-max', next);
  document.cookie = 'evo-width=' + next + '; Path=/; Max-Age=' + (20*365*24*3600) + '; SameSite=Lax';
}
function evoHamToggle() {
  document.body.classList.toggle('evo-menu-open');
}
function evoHamClose() {
  document.body.classList.remove('evo-menu-open');
}
function evoNavModeToggle() {
  if (window.matchMedia('(max-width: 600px), (max-height: 480px) and (orientation: landscape)').matches) return;
  var b = document.body;
  var h = document.documentElement;
  var isHam = b.classList.toggle('evo-hammode');
  h.classList[isHam ? 'add' : 'remove']('evo-hammode');
  document.cookie = 'evo-navmode=' + (isHam ? 'ham' : 'top') + '; Path=/; Max-Age=' + (20*365*24*3600) + '; SameSite=Lax';
  if (!isHam) { b.classList.remove('evo-menu-open'); }
  evoSetupMobileMenu();
}
function evoSetupMobileMenu() {
  var mqMobile  = window.matchMedia('(max-width: 600px), (max-height: 480px) and (orientation: landscape)');
  var mqLand    = window.matchMedia('(orientation: landscape) and (max-height: 480px)');
  var isMobile  = mqMobile.matches;
  var isLand    = mqLand.matches;
  var body      = document.body;
  var isHamMode = body.classList.contains('evo-hammode');
  var mainMenu  = document.querySelector('ul.menu.new:not(.sub)');
  if (!mainMenu) return;

  var mobileActive = isMobile && !body.classList.contains('evo-topnav');
  var needDrawer   = mobileActive || isHamMode;

  /* Relocate bar to body for reliable position:fixed on all mobile browsers */
  if (mainMenu._evoOrigParent === undefined) {
    mainMenu._evoOrigParent = mainMenu.parentNode || null;
    mainMenu._evoOrigNext   = mainMenu.nextSibling || null;
  }
  if (mobileActive && mainMenu.parentNode !== document.body) {
    document.body.appendChild(mainMenu);
  } else if (!mobileActive && mainMenu._evoOrigParent && mainMenu.parentNode === document.body) {
    var _op = mainMenu._evoOrigParent, _on = mainMenu._evoOrigNext;
    if (_on && _op.contains && _op.contains(_on)) { _op.insertBefore(mainMenu, _on); }
    else { _op.appendChild(mainMenu); }
  }

  if (!needDrawer) {
    mainMenu.classList.remove('evo-mobile-limited');
    mainMenu.classList.add('evo-mobile-ready');
    var oldMore = mainMenu.querySelector('li.evo-mobile-more');
    if (oldMore) oldMore.remove();
    Array.prototype.forEach.call(mainMenu.children, function(li){
      li.classList.remove('evo-mobile-hidden');
    });
    body.classList.remove('evo-menu-open');
    var old = document.getElementById('evo-mobile-drawer');
    if (old) old.remove();
    return;
  }

  if (mobileActive) {
    mainMenu.classList.add('evo-mobile-limited');
    var items = Array.prototype.filter.call(mainMenu.children, function(li){
      return !li.classList.contains('evo-mobile-more');
    });
    var maxVisible = isLand ? 5 : 3;
    items.forEach(function(li, i){
      li.classList.toggle('evo-mobile-hidden', i >= maxVisible);
    });
    if (!mainMenu.querySelector('li.evo-mobile-more')) {
      var more = document.createElement('li');
      more.className = 'evo-mobile-more';
      more.innerHTML = '<a href="#" title="More">\u2026</a>';
      mainMenu.appendChild(more);
      more.querySelector('a').addEventListener('click', function(ev){
        ev.preventDefault();
        evoHamToggle();
      });
    }
  } else {
    /* desktop ham mode: full menu in drawer, no bottom bar limitation */
    mainMenu.classList.remove('evo-mobile-limited');
    var oldMore = mainMenu.querySelector('li.evo-mobile-more');
    if (oldMore) oldMore.remove();
  }

  /* Build / rebuild the popup drawer */
  var drawer = document.getElementById('evo-mobile-drawer');
  var hamWrap = document.getElementById('evo-ham-wrap');
  var drawerTarget = (isHamMode && !mobileActive && hamWrap) ? hamWrap : document.body;
  if (!drawer) {
    drawer = document.createElement('div');
    drawer.id = 'evo-mobile-drawer';
    drawerTarget.appendChild(drawer);
  } else if (drawer.parentNode !== drawerTarget) {
    drawerTarget.appendChild(drawer);
  }
  drawer.innerHTML = '';
  var ul = document.createElement('ul');
  var srcItems = Array.prototype.filter.call(mainMenu.children, function(li){
    return !li.classList.contains('evo-mobile-more');
  });
  srcItems.forEach(function(srcLi){
    var li = document.createElement('li');
    var srcA = srcLi.querySelector(':scope > a') || srcLi.querySelector('a');
    if (!srcA) return;
    var a = document.createElement('a');
    a.href = srcA.href;
    a.textContent = srcA.textContent;
    if (srcLi.classList.contains('open')) li.classList.add('evo-drawer-active');
    var srcSub = srcLi.querySelector(':scope > ul') || srcLi.querySelector('ul');
    if (srcSub) {
      li.classList.add('evo-drawer-parent');
      var subUl = document.createElement('ul');
      Array.prototype.forEach.call(srcSub.children, function(srcSubLi){
        var subLi = document.createElement('li');
        var subA = srcSubLi.querySelector('a');
        if (!subA) return;
        var sa = document.createElement('a');
        sa.href = subA.href;
        sa.textContent = subA.textContent;
        if (subA.classList.contains('active')) sa.classList.add('active');
        subLi.appendChild(sa);
        subUl.appendChild(subLi);
      });
      li.appendChild(a);
      li.appendChild(subUl);
      if (srcLi.classList.contains('open')) li.classList.add('evo-drawer-open');
      a.addEventListener('click', function(ev){
        ev.preventDefault();
        var isOpen = li.classList.toggle('evo-drawer-open');
        if (isOpen) {
          Array.prototype.forEach.call(ul.children, function(o){
            if (o !== li) o.classList.remove('evo-drawer-open');
          });
        }
      });
    } else {
      li.appendChild(a);
    }
    ul.appendChild(li);
  });
  drawer.appendChild(ul);
  mainMenu.classList.add('evo-mobile-ready');
}
document.addEventListener('DOMContentLoaded', function(){
  evoSetupMobileMenu();
  window.addEventListener('resize', evoSetupMobileMenu);
});
</script>
EOF
}

skin_sec_begin() {
	echo "<div class='section'><h1>$1</h1>"
}

skin_sec_end() {
	echo "</div>"
}
