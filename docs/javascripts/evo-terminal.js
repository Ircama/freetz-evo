/**
 * Expand/collapse toggle for the home-page hero terminal card.
 *
 * The card lives in the narrow right-hand hero column, so the longest build
 * command cannot fit on a single line. The card therefore keeps one command
 * per line (the overflow scrolls horizontally) and the top-right button opens
 * the same card as a centered overlay, where the whole command list is visible
 * without scrolling.
 *
 * Behaviour:
 *   - click the button to expand/collapse
 *   - Escape or a click outside the card closes the overlay
 *   - page scrolling is locked while the overlay is open
 *   - focus returns to the button when the overlay closes
 *
 * The toggle is wired through document-level delegated listeners so it keeps
 * working with mkdocs-material/zensical instant navigation.
 */
(function () {
  "use strict";

  var CARD_SELECTOR = "[data-evo-terminal]";
  var TOGGLE_SELECTOR = "[data-evo-terminal-toggle]";
  var LINES_SELECTOR = ".evo-terminal-card__lines";
  var EXPANDED_CLASS = "evo-terminal-card--expanded";
  var BODY_CLASS = "evo-terminal-open";

  var LABEL_EXPAND = "Expand command list";
  var LABEL_COLLAPSE = "Collapse command list";

  // lucide "maximize-2" / "minimize-2"
  var ICON_EXPAND =
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" ' +
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" ' +
    'stroke-linejoin="round" aria-hidden="true">' +
    '<polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/>' +
    '<line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/>' +
    "</svg>";

  var ICON_COLLAPSE =
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" ' +
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" ' +
    'stroke-linejoin="round" aria-hidden="true">' +
    '<polyline points="4 14 10 14 10 20"/><polyline points="20 10 14 10 14 4"/>' +
    '<line x1="14" y1="10" x2="21" y2="3"/><line x1="3" y1="21" x2="10" y2="14"/>' +
    "</svg>";

  var _bound = false;
  var _expandedCard = null;
  var _lastToggle = null;

  /* ── Helpers ───────────────────────────────────────────────── */
  function cardOf(el) {
    return el && typeof el.closest === "function" ? el.closest(CARD_SELECTOR) : null;
  }

  function isInsideCard(card, event) {
    var rect = card.getBoundingClientRect();
    return (
      event.clientX >= rect.left &&
      event.clientX <= rect.right &&
      event.clientY >= rect.top &&
      event.clientY <= rect.bottom
    );
  }

  function render(btn, expanded) {
    if (!btn) return;
    btn.innerHTML = expanded ? ICON_COLLAPSE : ICON_EXPAND;
    btn.setAttribute("aria-expanded", expanded ? "true" : "false");
    btn.setAttribute("aria-label", expanded ? LABEL_COLLAPSE : LABEL_EXPAND);
    btn.setAttribute("title", expanded ? LABEL_COLLAPSE : LABEL_EXPAND);
  }

  function expand(btn) {
    var card = cardOf(btn);
    if (!card) return;
    if (_expandedCard && _expandedCard !== card) collapse(false);
    _expandedCard = card;
    _lastToggle = btn;
    card.classList.add(EXPANDED_CLASS);
    render(btn, true);
    document.body.classList.add(BODY_CLASS);
  }

  function collapse(refocus) {
    var card = _expandedCard;
    _expandedCard = null;
    document.body.classList.remove(BODY_CLASS);

    if (card) {
      card.classList.remove(EXPANDED_CLASS);
      // Reopen the compact card at the first command
      var lines = card.querySelector(LINES_SELECTOR);
      if (lines) lines.scrollLeft = 0;
      render(card.querySelector(TOGGLE_SELECTOR), false);
    }

    if (refocus && _lastToggle && document.contains(_lastToggle)) {
      _lastToggle.focus();
    }
    _lastToggle = null;
  }

  /* ── Events (delegated, bound once) ────────────────────────── */
  function onClick(event) {
    var target = event.target;
    if (!target || typeof target.closest !== "function") return;

    var btn = target.closest(TOGGLE_SELECTOR);
    if (btn) {
      event.preventDefault();
      if (cardOf(btn) === _expandedCard) {
        collapse(false);
      } else {
        expand(btn);
      }
      return;
    }

    // Click on the backdrop (anywhere outside the expanded card). The
    // backdrop is drawn with ::before, so hit-testing reports the card
    // itself: compare against its box instead of the event target.
    if (_expandedCard && !isInsideCard(_expandedCard, event)) {
      collapse(true);
    }
  }

  function onKeydown(event) {
    if (event.key !== "Escape" || !_expandedCard) return;
    event.preventDefault();
    collapse(true);
  }

  /* ── Initialise ────────────────────────────────────────────── */
  function init() {
    var card = document.querySelector(CARD_SELECTOR);

    // Left the home page (instant navigation): drop any lingering state
    if (!card) {
      collapse(false);
      return;
    }

    if (!_bound) {
      document.addEventListener("click", onClick);
      document.addEventListener("keydown", onKeydown);
      _bound = true;
    }

    // Keep the overlay state owned by this page instance
    if (_expandedCard && _expandedCard !== card) collapse(false);
    if (_expandedCard) document.body.classList.add(BODY_CLASS);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  // mkdocs-material / zensical instant navigation hooks
  if (typeof document$ !== "undefined") {
    document$.subscribe(function () {
      init();
    });
  }

  if (typeof location$ !== "undefined") {
    location$.subscribe(function () {
      init();
    });
  }
})();
