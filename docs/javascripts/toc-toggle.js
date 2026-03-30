/**
 * TOC sidebar toggle for zensical/mkdocs-material.
 *
 * Adds a hamburger-style button to the header bar that shows/hides
 * the right-hand "On this page" table-of-contents sidebar.
 * State is persisted in localStorage so the preference survives reloads.
 *
 * Default state: TOC hidden (secondary sidebar already hidden via CSS).
 */
(function () {
  "use strict";

  var STORAGE_KEY = "__toc_visible";
  var MOBILE_QUERY = "(max-width: 76.1875em)";
  var _eventsBound = false;
  var _tocPresenceObserver = null;
  var _scrollToActiveTocLink = null;
  var _tocSearchValue = "";

  /* ── SVG icons ─────────────────────────────────────────────── */
  // "list-tree" icon — represents a table of contents
  var ICON_TOC =
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" ' +
    'fill="none" stroke="currentColor" stroke-width="2" ' +
    'stroke-linecap="round" stroke-linejoin="round">' +
    '<path d="M21 12h-8"/><path d="M21 6h-8"/>' +
    '<path d="M21 18h-8"/><path d="M3 12h4"/>' +
    '<path d="M3 6h4"/><path d="M3 18h4"/></svg>';

  /* ── Wide-screen threshold (px) ────────────────────────────── */
  // On displays wider than this, TOC defaults to visible (unless
  // the user explicitly toggled it off).
  var WIDE_SCREEN_PX = 1600;

  /* ── Helpers ───────────────────────────────────────────────── */
  function isWideScreen() {
    return window.innerWidth >= WIDE_SCREEN_PX;
  }

  function isVisible() {
    try {
      var stored = localStorage.getItem(STORAGE_KEY);
      // If user never toggled: show TOC on desktop, hide on mobile.
      if (stored === null) return !isMobile();
      return stored === "1";
    } catch (e) {
      return !isMobile();
    }
  }

  function persist(visible) {
    try {
      localStorage.setItem(STORAGE_KEY, visible ? "1" : "0");
    } catch (e) {
      /* private browsing – ignore */
    }
  }

  function isMobile() {
    return window.matchMedia(MOBILE_QUERY).matches;
  }

  function getTocContainer() {
    return document.querySelector('.md-sidebar--secondary [data-md-component="toc"]');
  }

  function getTocNav() {
    return document.querySelector('.md-sidebar--secondary .md-nav--secondary');
  }

  function getTocSearchInput() {
    return document.querySelector('.md-sidebar--secondary .toc-search__input');
  }

  function getTopLevelTocItems(nav) {
    if (!nav) return [];

    var topLevel = [];
    var topLists = nav.querySelectorAll(':scope > .md-nav__list');
    topLists.forEach(function (list) {
      list.querySelectorAll(':scope > .md-nav__item').forEach(function (item) {
        topLevel.push(item);
      });
    });

    return topLevel;
  }

  function getChildTocItems(item) {
    if (!item) return [];

    var children = [];
    var childLists = item.querySelectorAll(':scope > .md-nav > .md-nav__list, :scope > .md-nav__list');
    childLists.forEach(function (list) {
      list.querySelectorAll(':scope > .md-nav__item').forEach(function (child) {
        children.push(child);
      });
    });

    return children;
  }

  function getDirectTocLink(item) {
    if (!item) return null;
    var link = item.querySelector(':scope > .md-nav__link');
    if (link) return link;

    // Fallback for theme variations that render clickable labels.
    return item.querySelector(':scope > label.md-nav__link');
  }

  function ensureTocSearch() {
    var nav = getTocNav();
    if (!nav) return null;

    var title = nav.querySelector('.md-nav__title');
    if (!title) return null;

    var wrapper = nav.querySelector('.toc-search');
    var input = wrapper && wrapper.querySelector('.toc-search__input');

    if (!wrapper || !input) {
      wrapper = document.createElement('div');
      wrapper.className = 'toc-search';

      input = document.createElement('input');
      input.type = 'search';
      input.className = 'toc-search__input';
      input.setAttribute('placeholder', 'Filter index');
      input.setAttribute('aria-label', 'Filter table of contents');
      input.setAttribute('autocomplete', 'off');
      input.setAttribute('spellcheck', 'false');

      input.addEventListener('input', function () {
        _tocSearchValue = input.value || '';
        filterTocEntries(_tocSearchValue);
      });

      input.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && input.value) {
          event.stopPropagation();
          input.value = '';
          _tocSearchValue = '';
          filterTocEntries('');
        }
      });

      wrapper.appendChild(input);
      title.insertAdjacentElement('afterend', wrapper);
    }

    if (input.value !== _tocSearchValue) {
      input.value = _tocSearchValue;
    }

    return input;
  }

  function resetTocFilter(nav) {
    if (!nav) return;

    document.body.classList.remove('toc-search-active');

    nav.querySelectorAll('.md-nav__item').forEach(function (item) {
      item.style.removeProperty('display');
    });

    nav.querySelectorAll('.md-nav__link.toc-search-hit').forEach(function (link) {
      link.classList.remove('toc-search-hit');
    });
  }

  function filterTocItem(item, query) {
    var link = getDirectTocLink(item);
    var ownMatch = false;

    if (link) {
      var label = (link.textContent || '').trim().toLowerCase();
      ownMatch = label.indexOf(query) !== -1;
    }

    var childMatch = false;
    getChildTocItems(item).forEach(function (child) {
      if (filterTocItem(child, query)) {
        childMatch = true;
      }
    });

    var visible = ownMatch || childMatch;
    item.style.display = visible ? '' : 'none';

    if (link) {
      link.classList.toggle('toc-search-hit', ownMatch && query.length > 0);
    }

    return visible;
  }

  function filterTocEntries(rawQuery) {
    var nav = getTocNav();
    if (!nav) return;

    var query = (rawQuery || '').trim().toLowerCase();
    if (!query) {
      resetTocFilter(nav);
      return;
    }

    document.body.classList.add('toc-search-active');

    getTopLevelTocItems(nav).forEach(function (item) {
      filterTocItem(item, query);
    });
  }

  function hasTocEntries() {
    var toc = getTocContainer();
    if (toc) {
      // Accept both local anchors (#...) and absolute URLs ending with #...
      return toc.querySelectorAll('a.md-nav__link[href*="#"]').length > 0;
    }

    // Fallback: some theme states may have secondary nav before the toc list node
    var secondaryNav = document.querySelector('.md-sidebar--secondary .md-nav--secondary');
    if (!secondaryNav) return false;

    return secondaryNav.querySelectorAll('a.md-nav__link[href*="#"]').length > 0;
  }

  function queueAvailabilityResync() {
    requestAnimationFrame(syncTocAvailability);
    setTimeout(syncTocAvailability, 120);
    setTimeout(syncTocAvailability, 420);
  }

  function watchTocPresence() {
    if (_tocPresenceObserver) {
      _tocPresenceObserver.disconnect();
      _tocPresenceObserver = null;
    }

    if (!document.body) return;

    _tocPresenceObserver = new MutationObserver(function () {
      syncTocAvailability();
    });

    _tocPresenceObserver.observe(document.body, {
      childList: true,
      subtree: true
    });
  }

  function ensureBackdrop() {
    var backdrop = document.querySelector('.toc-mobile-backdrop');
    if (backdrop) return backdrop;

    backdrop = document.createElement('div');
    backdrop.className = 'toc-mobile-backdrop';
    document.body.appendChild(backdrop);
    return backdrop;
  }

  function syncTocAvailability() {
    var hasToc = hasTocEntries();
    document.body.classList.toggle('toc-has-content', hasToc);

    var btn = document.querySelector('.toc-toggle-btn');
    if (btn) {
      btn.style.display = hasToc ? 'inline-flex' : 'none';
      btn.disabled = !hasToc;
    }

    var searchInput = getTocSearchInput();
    if (searchInput) {
      var searchContainer = searchInput.closest('.toc-search');
      if (searchContainer) {
        searchContainer.style.display = hasToc ? '' : 'none';
      }
    }

    if (!hasToc) {
      document.body.classList.remove('toc-visible');
      document.body.classList.remove('toc-mobile-open');
      _tocSearchValue = '';
      if (searchInput) searchInput.value = '';
      filterTocEntries('');
    } else {
      ensureTocSearch();
      filterTocEntries(_tocSearchValue);
    }

    return hasToc;
  }

  function applyState(visible) {
    var hasToc = syncTocAvailability();
    var effectiveVisible = !!visible && hasToc;

    if (effectiveVisible) {
      document.body.classList.add("toc-visible");
    } else {
      document.body.classList.remove("toc-visible");
    }

    document.body.classList.toggle('toc-mobile-open', effectiveVisible && isMobile());

    if (effectiveVisible && _scrollToActiveTocLink) {
      // Wait for class application and drawer transition before aligning scroll.
      requestAnimationFrame(function () {
        _scrollToActiveTocLink();
        setTimeout(_scrollToActiveTocLink, 210);
      });
    }

    var btn = document.querySelector(".toc-toggle-btn");
    if (btn) {
      if (effectiveVisible) {
        btn.classList.add("active");
        btn.setAttribute("title", "Hide table of contents");
        btn.setAttribute("aria-pressed", "true");
      } else {
        btn.classList.remove("active");
        btn.setAttribute("title", "Show table of contents");
        btn.setAttribute("aria-pressed", "false");
      }
    }
  }

  function closeToc() {
    persist(false);
    applyState(false);
  }

  /* ── Inject button ─────────────────────────────────────────── */
  function injectButton() {
    // Don't double-inject
    if (document.querySelector(".toc-toggle-btn")) return;

    // Only inject if the page has a secondary sidebar container.
    var toc = document.querySelector(".md-sidebar--secondary");
    if (!toc) return;

    var btn = document.createElement("button");
    btn.className = "md-header__button md-icon toc-toggle-btn";
    btn.setAttribute("aria-label", "Toggle table of contents");
    btn.innerHTML = ICON_TOC;

    btn.addEventListener("click", function () {
      var next = !document.body.classList.contains("toc-visible");
      persist(next);
      applyState(next);
    });

    // Insert before the source/repo link (rightmost area of header)
    var source = document.querySelector(".md-header__source");
    if (source) {
      source.parentNode.insertBefore(btn, source);
    } else {
      // Fallback: append to the header nav
      var nav = document.querySelector(".md-header__inner");
      if (nav) nav.appendChild(btn);
    }

    syncTocAvailability();
  }

  function bindGlobalEvents() {
    if (_eventsBound) return;
    _eventsBound = true;

    document.addEventListener('click', function (event) {
      if (event.target.closest('.toc-mobile-backdrop')) {
        closeToc();
        return;
      }

      var tocLink = event.target.closest('.md-sidebar--secondary a.md-nav__link');
      if (tocLink && isMobile()) {
        closeToc();
      }
    });

    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && document.body.classList.contains('toc-mobile-open')) {
        closeToc();
      }
    });

    window.addEventListener('resize', function () {
      if (!document.body.classList.contains('toc-visible')) return;
      applyState(true);
    }, { passive: true });
  }

  /* ── Active scroll tracking for the TOC sidebar ────────────── */
  // When user scrolls the content, the TOC sidebar auto-scrolls so
  // the currently-active link stays visible — mirroring the dynamic
  // scroll behaviour of markdown-viewer.html's Bootstrap ScrollSpy.

  function attachScrollTracking() {
    var tocList = document.querySelector(
      '.md-sidebar--secondary [data-md-component="toc"]'
    );
    if (!tocList) return;

    // The actual scrollable container is .md-sidebar__scrollwrap
    var scrollContainer = document.querySelector(
      '.md-sidebar--secondary .md-sidebar__scrollwrap'
    );
    if (!scrollContainer) scrollContainer = tocList;

    var currentActive = null;

    // Scroll the TOC container so the active link is in view
    function scrollTocToActive(link) {
      if (!link) return;
      var linkRect = link.getBoundingClientRect();
      var contRect = scrollContainer.getBoundingClientRect();
      var MARGIN = 60; // px context above/below

      if (linkRect.bottom > contRect.bottom - MARGIN) {
        scrollContainer.scrollTop += linkRect.bottom - contRect.bottom + MARGIN;
      } else if (linkRect.top < contRect.top + MARGIN) {
        scrollContainer.scrollTop -= contRect.top - linkRect.top + MARGIN;
      }
    }

    function scrollCurrentActiveIntoView() {
      var active = tocList.querySelector('.md-nav__link--active');
      if (!active) return;
      currentActive = active;
      scrollTocToActive(active);
    }

    _scrollToActiveTocLink = scrollCurrentActiveIntoView;

    // Use a MutationObserver on the TOC list to detect when
    // mkdocs-material's built-in JS adds/removes .md-nav__link--active
    var observer = new MutationObserver(function () {
      var active = tocList.querySelector('.md-nav__link--active');
      if (active && active !== currentActive) {
        currentActive = active;
        if (document.body.classList.contains('toc-visible')) {
          scrollTocToActive(active);
        }
      }
    });

    observer.observe(tocList, {
      attributes: true,
      attributeFilter: ['class'],
      subtree: true
    });

    // Align once on init so opening the mobile drawer starts at the active item.
    requestAnimationFrame(scrollCurrentActiveIntoView);

    // Return disconnect handle so we can clean up on page nav
    return function () {
      observer.disconnect();
      if (_scrollToActiveTocLink === scrollCurrentActiveIntoView) {
        _scrollToActiveTocLink = null;
      }
    };
  }

  var _footerAvoidanceCleanup = null;

  function attachFooterAvoidance() {
    if (isMobile()) return null;

    var sidebar = document.querySelector('.md-sidebar--secondary');
    var scrollwrap = sidebar && sidebar.querySelector('.md-sidebar__scrollwrap');
    var footer = document.querySelector('.md-footer');
    if (!scrollwrap || !footer) return null;

    function update() {
      if (isMobile()) {
        // On mobile, keep native drawer scroll and avoid any inline max-height clamp.
        scrollwrap.style.removeProperty('max-height');
        return;
      }

      var footerVisible = footer.getBoundingClientRect().top < window.innerHeight;
      if (footerVisible) {
        // Footer is in view: constrain sidebar so it doesn't overlap
        scrollwrap.style.setProperty('max-height', 'calc(100vh - 8rem)', 'important');
      } else {
        // Footer out of view: let CSS height:85vh take over
        scrollwrap.style.removeProperty('max-height');
      }
    }

    window.addEventListener('scroll', update, { passive: true });
    window.addEventListener('resize', update, { passive: true });
    requestAnimationFrame(update);

    return function () {
      window.removeEventListener('scroll', update);
      window.removeEventListener('resize', update);
      scrollwrap.style.removeProperty('max-height');
    };
  }
  // The .filename span (auto_title from pymdownx.highlight) is hidden
  // by default via CSS. We inject a small "show language" button into
  // each code block, positioned like the copy-to-clipboard button.
  function injectLangButtons() {
    var blocks = document.querySelectorAll('.highlight');
    blocks.forEach(function (block) {
      // Skip if already processed or no filename span
      if (block.querySelector('.lang-toggle-btn')) return;
      var filenameSpan = block.querySelector('.filename');
      if (!filenameSpan) return;

      var btn = document.createElement('button');
      btn.className = 'lang-toggle-btn';
      btn.setAttribute('title', 'Show language');
      btn.setAttribute('aria-label', 'Show language');
      // "code" / tag icon
      btn.innerHTML =
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">' +
        '<path d="M9.4 16.6 4.8 12l4.6-4.6L8 6l-6 6 6 6 1.4-1.4zm5.2 0 4.6-4.6-4.6-4.6L16 6l6 6-6 6-1.4-1.4z"/></svg>';

      btn.addEventListener('click', function (e) {
        e.stopPropagation();
        var isShown = filenameSpan.classList.toggle('filename--visible');
        btn.classList.toggle('active', isShown);
        btn.setAttribute('title', isShown ? 'Hide language' : 'Show language');
      });

      block.style.position = 'relative';
      block.appendChild(btn);
    });
  }

  /* ── Initialise ────────────────────────────────────────────── */
  var _disconnectScrollTracking = null;

  function init() {
    // Clean up previous listeners (for instant-nav page changes)
    if (_disconnectScrollTracking) {
      _disconnectScrollTracking();
      _disconnectScrollTracking = null;
    }
    if (_footerAvoidanceCleanup) {
      _footerAvoidanceCleanup();
      _footerAvoidanceCleanup = null;
    }
    injectButton();
    ensureTocSearch();
    ensureBackdrop();
    applyState(isVisible());
    queueAvailabilityResync();
    watchTocPresence();
    _disconnectScrollTracking = attachScrollTracking();
    _footerAvoidanceCleanup = attachFooterAvoidance();
    injectLangButtons();
    bindGlobalEvents();
  }

  // Run on DOMContentLoaded (first load)
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  // For mkdocs-material instant navigation (SPA-style page transitions)
  // the `document$` RxJS observable fires on each navigation.
  if (typeof document$ !== "undefined") {
    document$.subscribe(function () {
      init();
    });
  }

  // Also handle the location$ observable used by some material versions
  if (typeof location$ !== "undefined") {
    location$.subscribe(function () {
      init();
    });
  }
})();
