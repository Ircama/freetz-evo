skin_head() {
	local title=$1 id=$2
	local hname="$(hostname -s|html)"
	[ "$hname" != "fritz" ] && hname="&nbsp;&#64;${hname}" || hname=""
	cat << EOF
<title>$title&nbsp;&ndash; Freetz-EVO${hname}</title>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<link rel="manifest" href="/style/evo/manifest.json">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Freetz EVO">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="application-name" content="Freetz-EVO">
<meta name="msapplication-TileColor" content="#1e293b">
<meta name="msapplication-TileImage" content="/style/evo/icon-192.png">
<meta name="msapplication-config" content="none">
<meta name="color-scheme" content="dark light">
<meta name="format-detection" content="telephone=no, date=no, address=no, email=no">
<meta name="theme-color" content="#1e293b" media="(prefers-color-scheme: dark)">
<meta name="theme-color" content="#3b82f6" media="(prefers-color-scheme: light)">
<link rel="apple-touch-icon" sizes="180x180" href="/style/evo/icon-180.png">
<link rel="apple-touch-icon" sizes="152x152" href="/style/evo/icon-152.png">
<link rel="apple-touch-icon" sizes="120x120" href="/style/evo/icon-120.png">
<link rel="icon" type="image/svg+xml" href="/style/evo/icon.svg">
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
<h1><a href="https://ircama.github.io/freetz-evo/" target="_blank" class="logo">Freetz EVO</a>&nbsp;<a id="about" href="/cgi-bin/about.cgi" target="_blank">&ndash;</a>&nbsp;<span class="title">$title</span></h1>
<div id="header-right">
EOF
if [ -n "$_CGI_HELP" ]; then
        echo "<button class='evo-dark-toggle evo-help-btn' title='$(lang de:"Hilfe" en:"Help" it:"Aiuto" fr:"Aide" es:"Ayuda")' onclick=\"location.href='$(html "$_CGI_HELP")'\"><svg class='evo-help-icon' xmlns='http://www.w3.org/2000/svg' width='1em' height='1em' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round' aria-hidden='true'><circle cx='12' cy='12' r='10'/><path d='M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3'/><circle cx='12' cy='17' r='0.8' fill='currentColor' stroke='none'/></svg><span class='evo-help-text'>$(lang de:"Hilfe" en:"Help" it:"Aiuto" fr:"Aide" es:"Ayuda")</span></button>"
fi
if [ -n "$id" ]; then
	cat << 'EOF'
<button class="evo-dark-toggle evo-navmode-btn" id="evo-navmode-btn" title="Toggle tree menu" onclick="evoNavModeToggle()"><svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" viewBox="0 0 14 12" fill="currentColor" aria-hidden="true" style="vertical-align:middle"><rect x="0" y="0" width="14" height="2"/><rect x="3" y="5" width="11" height="2"/><rect x="3" y="10" width="11" height="2"/></svg></button>
<div id="evo-ham-wrap"><button class="evo-dark-toggle evo-ham-open-btn" id="evo-ham-open-btn" title="Open menu">&#9776;</button></div>
<button class="evo-dark-toggle evo-width-toggle" id="evo-width-btn" title="Page width" onclick="evoWidthToggle()">&#8646;</button>
EOF
fi
	cat << 'EOF'
<button class="evo-dark-toggle" id="evo-dark-btn" title="Dark / Light mode" onclick="evoDarkToggle()">&#9681;</button>
EOF
if [ -n "$id" ]; then
	cat << 'EOF'
<button class="evo-hamburger" id="evo-ham-btn" title="Menu" onclick="evoHamToggle()">&#9776;</button>
EOF
fi
	cat << EOF
<span class="version">$(html < /etc/.freetz-version)</span>
</div>
</div>
</div>
EOF
	[ -n "$id" ] && echo "<div class=\"evo-nav-overlay\" id=\"evo-overlay\" onclick=\"evoHamClose()\"></div>"
	echo "<div id='container'>"

	if [ -n "$id" ]; then
		_cgi_print_menu "$id"
		_cgi_print_submenu "$id"
	fi

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
<button class="evo-scroll-btn" id="evo-scroll-top" title="Top" onclick="window.scrollTo({top:0,behavior:'smooth'})" aria-label="Scroll to top">&#9650;</button>
<button class="evo-scroll-btn" id="evo-scroll-bot" title="Bottom" onclick="window.scrollTo({top:document.body.scrollHeight,behavior:'smooth'})" aria-label="Scroll to bottom">&#9660;</button>
<script>
function evoDarkToggle() {
  var h = document.documentElement;
  var b = document.body;
  var hasDarkClass  = h.classList.contains('dark-mode');
  var hasLightClass = h.classList.contains('light-mode');
  var osDark = !!(window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches);
  // Determine current visual state:
  // 1. Explicit class on <html> (set by anti-FOUC or prior toggle)
  // 2. OS media query (via matchMedia)
  // 3. Fallback: read the computed --evo-bg CSS variable (reliable even when matchMedia
  //    reports wrong value on embedded browsers like FritzBox WebKit)
  var currentlyDark;
  if (hasDarkClass)       currentlyDark = true;
  else if (hasLightClass) currentlyDark = false;
  else if (osDark)        currentlyDark = true;
  else {
    try {
      var bg = getComputedStyle(b).getPropertyValue('--evo-bg').trim();
      currentlyDark = (bg === '#0f172a');
    } catch(e) { currentlyDark = false; }
  }
  if (currentlyDark) {
    // Switch to light: always add light-mode to suppress OS dark media query
    h.classList.remove('dark-mode');
    b.classList.remove('dark-mode');
    h.classList.add('light-mode');
    b.classList.add('light-mode');
    document.cookie = 'evo-dark=0; Path=/; Max-Age=' + (20*365*24*3600) + '; SameSite=Lax';
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
/* Helpers for frequency-sorted mobile nav bar */
function evoGetNavFreq() {
  try { return JSON.parse(localStorage.getItem('evo-nav-freq') || '{}'); } catch(e) { return {}; }
}
function evoItemFreq(li, freq) {
  var a = li.querySelector(':scope > a') || li.querySelector('a');
  if (!a) return 0;
  try { return freq[a.pathname] || 0; } catch(e) { return 0; }
}
/* Nav order: manual position overrides (localStorage['evo-nav-order'] = {path: 1-based-pos}) */
function evoGetNavOrder() {
  try { return JSON.parse(localStorage.getItem('evo-nav-order') || '{}'); } catch(e) { return {}; }
}
function evoSetNavOrder(path, pos) {
  try {
    var o = evoGetNavOrder();
    if (pos === null) delete o[path]; else o[path] = pos;
    localStorage.setItem('evo-nav-order', JSON.stringify(o));
  } catch(e) {}
}
function evoResetNavOrder() {
  try { localStorage.removeItem('evo-nav-order'); } catch(e) {}
}
function evoShowOrderPopup(li, maxSlots) {
  var a = li.querySelector(':scope > a') || li.querySelector('a');
  var path = a ? a.pathname : '';
  var label = a ? (a.textContent || '').trim() : '';
  var navOrder = evoGetNavOrder();
  var curPos = navOrder[path];
  var ex = document.getElementById('evo-nav-order-popup');
  if (ex) ex.remove();
  var ov = document.getElementById('evo-nav-order-overlay');
  if (ov) ov.remove();
  ov = document.createElement('div');
  ov.id = 'evo-nav-order-overlay';
  document.body.appendChild(ov);
  var popup = document.createElement('div');
  popup.id = 'evo-nav-order-popup';
  var html = '<div class="evo-nop-title">' + label + '</div>';
  html += '<div class="evo-nop-desc">$(lang de:"Position in der mobilen Navigation" en:"Position in mobile navigation")</div>';
  html += '<div class="evo-nop-opts">';
  html += '<button class="evo-nop-btn' + (curPos === undefined ? ' evo-nop-active' : '') + '" data-pos="auto">$(lang de:"Auto" en:"Auto")</button>';
  var _posLabels3 = ['$(lang de:"Links" en:"Left")', '$(lang de:"Mitte" en:"Center")', '$(lang de:"Rechts" en:"Right")'];
  for (var _bi = 1; _bi <= maxSlots; _bi++) {
    var _lbl = (maxSlots === 3) ? _posLabels3[_bi - 1] : String(_bi);
    html += '<button class="evo-nop-btn' + (curPos === _bi ? ' evo-nop-active' : '') + '" data-pos="' + _bi + '">' + _lbl + '</button>';
  }
  html += '</div>';
  html += '<button class="evo-nop-reset-btn">$(lang de:"Alle Positionen zur\xfccksetzen" en:"Reset all positions")</button>';
  popup.innerHTML = html;
  document.body.appendChild(popup);
  popup.querySelectorAll('.evo-nop-btn').forEach(function(btn) {
    btn.addEventListener('click', function() {
      var pos = btn.getAttribute('data-pos');
      if (pos === 'auto') evoSetNavOrder(path, null); else evoSetNavOrder(path, parseInt(pos));
      ov.remove(); popup.remove();
      evoSetupMobileMenu();
    });
  });
  popup.querySelector('.evo-nop-reset-btn').addEventListener('click', function() {
    evoResetNavOrder();
    ov.remove(); popup.remove();
    evoSetupMobileMenu();
  });
  ov.addEventListener('click', function() { ov.remove(); popup.remove(); });
}
function evoSetupDesktopLogout(mainMenu) {
  /* Find logout li by href */
  var logoutLi = null;
  for (var i = 0; i < mainMenu.children.length; i++) {
    var li = mainMenu.children[i];
    if (li.tagName === 'HR') continue;
    var a = li.querySelector('a');
    if (a && a.href && a.href.indexOf('logout') !== -1) { logoutLi = li; break; }
  }
  if (!logoutLi) return;
  /* Already set up */
  if (logoutLi.classList.contains('evo-logout-dots')) return;
  var srcA = logoutLi.querySelector('a');
  if (!srcA) return;
  /* Save original <a> so mobile mode can still find it */
  logoutLi._ldotsOrigA = srcA;
  /* Build dots button (⋮) */
  var btn = document.createElement('button');
  btn.className = 'evo-ldots-btn';
  btn.setAttribute('aria-label', 'Account');
  btn.setAttribute('aria-expanded', 'false');
  btn.textContent = '\u22EE';
  /* Build dropdown */
  var drop = document.createElement('ul');
  drop.className = 'evo-ldots-drop';
  var dropLi = document.createElement('li');
  var dropA = document.createElement('a');
  dropA.href = srcA.href;
  dropA.textContent = (srcA.textContent || '').trim() || 'Logout';
  if (srcA.getAttribute('onclick')) dropA.setAttribute('onclick', srcA.getAttribute('onclick'));
  dropLi.appendChild(dropA);
  drop.appendChild(dropLi);
  /* Replace li content */
  logoutLi.innerHTML = '';
  logoutLi.classList.add('evo-logout-dots');
  logoutLi.appendChild(btn);
  logoutLi.appendChild(drop);
  /* Toggle on click */
  btn.addEventListener('click', function(e) {
    e.stopPropagation();
    var open = logoutLi.classList.toggle('evo-ldots-open');
    btn.setAttribute('aria-expanded', open ? 'true' : 'false');
  });
  /* Close on outside click */
  document.addEventListener('click', function() {
    logoutLi.classList.remove('evo-ldots-open');
    btn.setAttribute('aria-expanded', 'false');
  });
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
      li.style.order = '';
    });
    body.classList.remove('evo-menu-open');
    var old = document.getElementById('evo-mobile-drawer');
    if (old) old.remove();
    evoSetupDesktopLogout(mainMenu);
    return;
  }

  if (mobileActive) {
    mainMenu.classList.add('evo-mobile-limited');
    var maxVisible = isLand ? 5 : 3;
    /* Create hamburger immediately so bar is usable before freq sort */
    var moreEl = mainMenu.querySelector('li.evo-mobile-more');
    if (!moreEl) {
      moreEl = document.createElement('li');
      moreEl.className = 'evo-mobile-more';
      moreEl.innerHTML = '<a href="#" title="Menu">\u2630</a>';
      mainMenu.appendChild(moreEl);
      moreEl.querySelector('a').addEventListener('click', function(ev){
        ev.preventDefault();
        evoHamToggle();
      });
    }
    moreEl.style.order = maxVisible + 1;
    /* Bar + hamburger ready — show immediately */
    mainMenu.classList.add('evo-mobile-ready');
    /* Separate logout from freq-sorted items */
    var logoutLi = null;
    var items = Array.prototype.filter.call(mainMenu.children, function(li){
      if (li.classList.contains('evo-mobile-more')) return false;
      if (li.tagName === 'HR') return false;
      var a = li.querySelector(':scope > a') || li.querySelector('a');
      if (a && a.href && a.href.indexOf('logout') !== -1) {
        li.classList.add('evo-mobile-logout');
        logoutLi = li;
        return false;
      }
      return true;
    });
    var freq = evoGetNavFreq();
    var navOrder = evoGetNavOrder();
    var freqSlots = maxVisible;
    /* always keep the currently active item visible */
    var activeLi = null;
    items.forEach(function(li){
      var a = li.querySelector(':scope > a') || li.querySelector('a');
      if (a && (a.classList.contains('active') || li.classList.contains('open'))) activeLi = li;
    });
    /* rank items: manual position overrides frequency ranking */
    var manualItems = [], autoItems = [];
    items.forEach(function(li) {
      var a = li.querySelector(':scope > a') || li.querySelector('a');
      var pos = a ? navOrder[a.pathname] : undefined;
      if (pos !== undefined && pos >= 1 && pos <= freqSlots) manualItems.push([pos, li]);
      else autoItems.push(li);
    });
    manualItems.sort(function(a, b) { return a[0] - b[0]; });
    autoItems.sort(function(a, b) { return evoItemFreq(b, freq) - evoItemFreq(a, freq); });
    /* fill slots: manual first, then auto by frequency */
    var visible = new Array(freqSlots).fill(null);
    manualItems.forEach(function(pair) { var s = pair[0] - 1; if (s < freqSlots) visible[s] = pair[1]; });
    var _ai = 0;
    for (var _si = 0; _si < freqSlots; _si++) {
      if (visible[_si] === null) {
        while (_ai < autoItems.length && visible.indexOf(autoItems[_ai]) !== -1) _ai++;
        if (_ai < autoItems.length) visible[_si] = autoItems[_ai++];
      }
    }
    /* always keep active item visible (replace last non-manual slot) */
    if (activeLi && visible.indexOf(activeLi) === -1) {
      var lastAuto = -1;
      for (var _s2 = freqSlots - 1; _s2 >= 0; _s2--) {
        var _la = visible[_s2] ? (visible[_s2].querySelector(':scope > a') || visible[_s2].querySelector('a')) : null;
        if (_la && navOrder[_la.pathname] === undefined) { lastAuto = _s2; break; }
      }
      if (lastAuto >= 0) visible[lastAuto] = activeLi; else visible[freqSlots - 1] = activeLi;
    }
    /* apply visibility + CSS order (index 0 = leftmost) */
    items.forEach(function(li){
      var rank = visible.indexOf(li);
      li.classList.toggle('evo-mobile-hidden', rank === -1);
      li.style.order = rank >= 0 ? rank : '';
    });
    /* long-press on bar items opens order popup (600 ms threshold) */
    items.forEach(function(li) {
      if (li._evoLpAttached) return;
      li._evoLpAttached = true;
      var _lpt = null;
      function _lpCancel() { if (_lpt) { clearTimeout(_lpt); _lpt = null; } }
      li.addEventListener('touchstart', function(e) {
        _lpt = setTimeout(function() {
          _lpt = null; e.preventDefault();
          evoShowOrderPopup(li, maxVisible);
        }, 600);
      }, {passive: false});
      li.addEventListener('touchmove',   _lpCancel);
      li.addEventListener('touchend',    _lpCancel);
      li.addEventListener('touchcancel', _lpCancel);
      li.addEventListener('contextmenu', function(e) { e.preventDefault(); });
    });
    /* Logout hidden from bottom bar — appears only in drawer */
    if (logoutLi) {
      logoutLi.classList.add('evo-mobile-hidden');
    }
  } else {
    /* desktop ham mode: full menu in drawer, no bottom bar limitation */
    mainMenu.classList.remove('evo-mobile-limited');
    var oldMore = mainMenu.querySelector('li.evo-mobile-more');
    if (oldMore) oldMore.remove();
    Array.prototype.forEach.call(mainMenu.children, function(li){ li.style.order = ''; });
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

  function centerDrawerItem(li) {
    if (!drawer || !li) return;
    requestAnimationFrame(function() {
      var drawerRect = drawer.getBoundingClientRect();
      var itemRect = li.getBoundingClientRect();
      var delta = (itemRect.top + itemRect.height / 2) - (drawerRect.top + drawerRect.height / 2);
      drawer.scrollTop += delta;
    });
  }

  var ul = document.createElement('ul');
  var srcLogout = null;
  var srcItems = Array.prototype.filter.call(mainMenu.children, function(li){
    if (li.classList.contains('evo-mobile-more')) return false;
    if (li.tagName === 'HR') return false;
    var a = li.querySelector(':scope > a') || li.querySelector('a');
    if (a && a.href && a.href.indexOf('logout') !== -1) { srcLogout = li; return false; }
    return true;
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
          centerDrawerItem(li);
        }
      });
    } else {
      li.appendChild(a);
    }
    ul.appendChild(li);
  });
  drawer.appendChild(ul);
  var initiallyOpen = ul.querySelector('li.evo-drawer-open');
  if (initiallyOpen) centerDrawerItem(initiallyOpen);
  /* Logout pinned at bottom of drawer with separator */
  if (srcLogout) {
    var sep = document.createElement('div');
    sep.className = 'evo-drawer-sep';
    drawer.appendChild(sep);
    var logoutUl = document.createElement('ul');
    logoutUl.className = 'evo-drawer-logout-list';
    var logoutLiD = document.createElement('li');
    logoutLiD.className = 'evo-drawer-logout';
    var srcA = srcLogout.querySelector('a');
    var logoutA = document.createElement('a');
    logoutA.href = srcA.href;
    logoutA.textContent = srcA.textContent;
    logoutA.id = 'drawer-logout';
    if (srcA.getAttribute('onclick')) logoutA.setAttribute('onclick', srcA.getAttribute('onclick'));
    logoutLiD.appendChild(logoutA);
    logoutUl.appendChild(logoutLiD);
    drawer.appendChild(logoutUl);
  }
}
/* Track current page visits for dynamic mobile nav ordering */
(function(){
  try {
    var freq = JSON.parse(localStorage.getItem('evo-nav-freq') || '{}');
    var p = window.location.pathname;
    freq[p] = (freq[p] || 0) + 1;
    /* prune to top 60 entries to avoid unbounded growth */
    var keys = Object.keys(freq);
    if (keys.length > 60) {
      keys.sort(function(a,b){ return freq[a]-freq[b]; });
      keys.slice(0, keys.length - 60).forEach(function(k){ delete freq[k]; });
    }
    localStorage.setItem('evo-nav-freq', JSON.stringify(freq));
  } catch(e) {}
})();
// Right-edge dropdown flip: when a menu item is close to the right edge of
// #world the sub-menu would overflow and be clipped by overflow:hidden.
// Add .evo-drop-right so CSS right-aligns the dropdown instead.
function evoFixDropDir() {
  var world = document.getElementById('world');
  if (!world) return;
  var worldRight = world.getBoundingClientRect().right;
  var items = document.querySelectorAll('ul.menu.new > li');
  for (var i = 0; i < items.length; i++) {
    var li = items[i];
    if (!li.querySelector('ul')) continue;
    var liLeft = li.getBoundingClientRect().left;
    li.classList.toggle('evo-drop-right', liLeft + 200 > worldRight);
  }
}
document.addEventListener('DOMContentLoaded', function(){
  evoSetupMobileMenu();
  evoFixDropDir();
  window.addEventListener('resize', evoSetupMobileMenu);
  window.addEventListener('resize', evoFixDropDir);
});
// PWA: register service worker when available and on HTTPS / localhost
if ('serviceWorker' in navigator) {
  var _loc = window.location;
  if (_loc.protocol === 'https:' || _loc.hostname === 'localhost' || _loc.hostname === '127.0.0.1') {
    navigator.serviceWorker.register('/style/evo/sw.js')
      .catch(function(){}); // silently ignored on HTTP / scope mismatch
  }
}
// Scroll navigation buttons: show goto-top when scrolled down,
// show goto-bottom when there is more content below.
// Mobile (touch/coarse pointer): visible only during scroll, auto-hide after 1.5 s.
// Desktop: always visible when not at top / bottom.
(function(){
  var btnTop = document.getElementById('evo-scroll-top');
  var btnBot = document.getElementById('evo-scroll-bot');
  if (!btnTop || !btnBot) return;
  var _hideTimer = null;
  var _hasTouched = false;
  window.addEventListener('touchstart', function(){ _hasTouched = true; }, {once:true, passive:true});
  function isMobile() {
    return _hasTouched || !!(window.matchMedia && window.matchMedia('(hover:none) and (pointer:coarse)').matches);
  }
  function hideBtns() {
    btnTop.classList.remove('evo-scroll-visible');
    btnBot.classList.remove('evo-scroll-visible');
  }
  function evoUpdateScrollBtns() {
    var scrollY   = window.scrollY || window.pageYOffset || 0;
    var winH      = window.innerHeight || document.documentElement.clientHeight;
    var docH      = Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);
    var atTop     = scrollY <= 40;
    var atBottom  = scrollY + winH >= docH - 40;
    var pageShort = docH <= winH + 80;  /* page fits in viewport: hide both */
    btnTop.classList.toggle('evo-scroll-visible', !atTop  && !pageShort);
    btnBot.classList.toggle('evo-scroll-visible', !atBottom && !pageShort);
  }
  function evoOnScroll() {
    evoUpdateScrollBtns();
    if (isMobile()) {
      if (_hideTimer) clearTimeout(_hideTimer);
      _hideTimer = setTimeout(hideBtns, 1500);
    }
  }
  document.addEventListener('DOMContentLoaded', function(){
    if (!isMobile()) {
      evoUpdateScrollBtns();
      /* give dynamic content (menus, etc.) time to expand */
      setTimeout(evoUpdateScrollBtns, 350);
    }
    /* mobile: hidden on load, appear only on scroll */
  });
  window.addEventListener('scroll', evoOnScroll, {passive: true});
  window.addEventListener('resize', function(){
    if (_hideTimer) { clearTimeout(_hideTimer); _hideTimer = null; }
    if (isMobile()) hideBtns(); else evoUpdateScrollBtns();
  }, {passive: true});
})();
</script>
EOF
}

skin_sec_begin() {
	echo "<div class='section'><h1>$1</h1>"
}

skin_sec_end() {
	echo "</div>"
}

skin_login_form() {
	local sid="$1" subpage="$2" wrongpw="$3"
	local errmsg=""
	[ "$wrongpw" = "1" ] && errmsg="<p class='evo-lgerr'>$(lang de:"Passwort falsch!" en:"Wrong password!" it:"Password errata!" fr:"Mot de passe erron&eacute;!" es:"&iexcl;Contrase&ntilde;a incorrecta!")</p>"
	cat << EOF
<div class="evo-lgwrap">
<div class="evo-lgcard">
<div class="evo-lglogo">Freetz-EVO</div>
<div class="evo-lghost">$(hostname -s | html)</div>
<label class="evo-lglabel">$(lang de:"Benutzername" en:"Username" it:"Utente" fr:"Utilisateur" es:"Usuario")</label>
<input type="text" class="evo-lginput" value="$MOD_HTTPD_USER" readonly>
<label class="evo-lglabel">$(lang de:"Passwort" en:"Password" it:"Password" fr:"Mot de passe" es:"Contrase&ntilde;a")</label>
<div class="evo-lgpwwrap">
<input type="password" id="inp_pw" class="evo-lginput evo-lgpwinput" maxlength="45" autofocus autocomplete="current-password" onkeydown="if(event.key==='Enter')document.getElementById('id_go').click()">
<button type="button" class="evo-lgpweye" title="$(lang de:"Passwort anzeigen" en:"Show password" it:"Mostra password" fr:"Afficher le mot de passe" es:"Mostrar contrase&ntilde;a")" onclick="var f=document.getElementById('inp_pw');var s=this.querySelector('.evo-eye-show');var h=this.querySelector('.evo-eye-hide');if(f.type==='password'){f.type='text';s.style.display='none';h.style.display='block';this.title='$(lang de:"Passwort verbergen" en:"Hide password" it:"Nascondi password" fr:"Masquer le mot de passe" es:"Ocultar contrase&ntilde;a")';}else{f.type='password';s.style.display='block';h.style.display='none';this.title='$(lang de:"Passwort anzeigen" en:"Show password" it:"Mostra password" fr:"Afficher le mot de passe" es:"Mostrar contrase&ntilde;a")';}f.focus();"><svg class="evo-eye-show" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg><svg class="evo-eye-hide" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:none"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg></button>
</div>
<button id="id_go" class="evo-lgbtn" onclick="var f=document.getElementById('inp_pw');f.type='password';location.href='/cgi-bin/login.cgi?subpage=$subpage&amp;hash='+makemd5(f.value,'$sid')">
$(lang de:"Anmelden" en:"Sign in" it:"Accedi" fr:"Connexion" es:"Entrar")
</button>
$errmsg
</div>
</div>
<style>
.evo-lgwrap{display:flex;align-items:center;justify-content:center;min-height:50vh;padding:2rem 1rem}
.evo-lgcard{background:var(--evo-surface);border:1px solid var(--evo-border);border-radius:var(--evo-radius-lg);padding:2rem 2.5rem;width:100%;max-width:360px;box-shadow:var(--evo-shadow-lg)}
.evo-lglogo{font-size:1.6rem;font-weight:700;color:var(--evo-accent);margin-bottom:.25rem;letter-spacing:-.5px}
.evo-lghost{font-size:.85rem;color:var(--evo-text-muted);margin-bottom:1.5rem}
.evo-lglabel{display:block;font-size:.75rem;color:var(--evo-text-muted);margin-bottom:.3rem;text-transform:uppercase;letter-spacing:.5px}
.evo-lginput{display:block;width:100%;box-sizing:border-box;padding:.55rem .75rem;margin-bottom:1rem;background:var(--evo-bg);border:1px solid var(--evo-border);border-radius:var(--evo-radius);color:var(--evo-text);font-size:.95rem;transition:border-color var(--evo-transition)}
.evo-lginput:focus{outline:none;border-color:var(--evo-accent);box-shadow:var(--evo-focus-ring)}
.evo-lginput[readonly]{opacity:.55;cursor:default}
.evo-lgbtn{width:100%;padding:.65rem;background:var(--evo-accent);color:#fff;border:none;border-radius:var(--evo-radius);font-size:1rem;font-weight:600;cursor:pointer;margin-top:.25rem;transition:opacity var(--evo-transition)}
.evo-lgbtn:hover{opacity:.85}
.evo-lgerr{color:#f87171;font-size:.875rem;margin-top:.75rem;text-align:center}
.evo-lgpwwrap{position:relative;margin-bottom:1rem}
.evo-lgpwwrap .evo-lgpwinput{margin-bottom:0;padding-right:2.5rem}
.evo-lgpweye{position:absolute;font-family: 'Courier New', monospace !important;right:.5rem;top:50%;transform:translateY(-50%);background:none;border:none;padding:.25rem;cursor:pointer;color:var(--evo-text-muted);display:flex;align-items:center;line-height:1}
</style>
EOF
}
