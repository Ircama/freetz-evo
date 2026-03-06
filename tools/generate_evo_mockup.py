#!/usr/bin/env python3
"""
generate_evo_mockup.py — Freetz-EVO Web UI Mockup Generator
by Ircama, 2026

Crawls the live Freetz-EVO web interface on a device and produces a
fully self-contained single-file HTML mockup suitable for GitHub Pages
(or any static host) — no server required to view it.

Usage:
  tools/generate_evo_mockup.py --host 192.168.178.1 --password <pwd>
  tools/generate_evo_mockup.py --host 192.168.178.1 --password <pwd> \\
      --output docs/screenshots/evo-demo.html

  # With NEWLOGIN (session-cookie) auth instead of Basic Auth:
  tools/generate_evo_mockup.py --host 192.168.178.1 --newlogin --password <pwd>

  # Limit crawl depth (default: unlimited, bounded by --max-pages):
  tools/generate_evo_mockup.py --host 192.168.178.1 --password <pwd> --depth 3

  # Include only specific packages (plus core system pages):
  tools/generate_evo_mockup.py --host 192.168.178.1 --password <pwd> \
      --packages rtorrent nginx php

  # Include ONLY these packages (skip all other conf pages):
  tools/generate_evo_mockup.py --host 192.168.178.1 --password <pwd> \
      --packages rtorrent nginx --packages-only

Requirements:
  pip install requests beautifulsoup4 lxml

If you don't have python3 installed:
  make python3-host-precompiled
  tools/path/python3 tools/generate_evo_mockup.py ...
"""

import os
import sys
import re
import base64
import hashlib
import argparse
import time
import json
import urllib.parse
from pathlib import Path
from collections import OrderedDict

try:
    import requests
    from bs4 import BeautifulSoup, Comment
except ImportError:
    print("ERROR: Required packages missing. Run:")
    print("  pip install requests beautifulsoup4 lxml")
    sys.exit(1)

# ─── Constants ───────────────────────────────────────────────────────────────

VERSION = "1.0.0"
DEFAULT_HOST = "192.168.178.1"
DEFAULT_PORT = 81
DEFAULT_USER = "admin"
DEFAULT_OUTPUT = "docs/screenshots/evo-demo.html"
DEFAULT_TIMEOUT = 10
DEFAULT_MAX_PAGES = 60

# URL patterns derived from a package name.  Each pattern is tried in order;
# the first one that returns HTTP 200 is accepted.  The %s placeholder is
# replaced with the package name.
PKG_URL_CANDIDATES = [
    "/%s/",               # mww-alias path (e.g. /rtorrent/, /nginx/)
    "/cgi-bin/conf/%s",   # standard modconf CGI (most common)
    "/cgi-bin/%s.cgi",    # direct CGI binary
    "/cgi-bin/%s",        # bare CGI name (some packages)
    "/mww/%s/",           # mww static page directory
]

# Top-level path segments that are static-asset directories, NOT mww package
# aliases.  Used by _normalise() and _is_pkg_allowed() to avoid treating
# /css/, /js/, /ace/ etc. as crawlable package pages.
_STATIC_DIRS = frozenset([
    "js", "css", "style", "styles", "icons", "icon",
    "ace", "fonts", "font", "images", "img", "image",
    "static", "assets", "media", "vendor", "lib", "libs",
])

# Pages to always skip (too dynamic / destructive)
SKIP_URL_PATTERNS = [
    "/cgi-bin/reboot",
    "/cgi-bin/reset",
    "/cgi-bin/logout",
    "/cgi-bin/invalidate",
    "do_download",
    "do_update",
    "do_flash",
    "do_reboot",
    "do_restart",
    "passwd_save",
    "pwchange_check",
    "/cgi-bin/update",
    "?action=save",
    "?action=apply",
    "?action=restart",
    "?action=reboot",
]

# Static asset extensions to inline
ASSET_EXTENSIONS = {".css", ".js", ".svg", ".png", ".jpg", ".jpeg",
                    ".gif", ".ico", ".woff", ".woff2", ".ttf", ".eot"}

# CSS mime types
MIME_MAP = {
    ".css":   "text/css",
    ".js":    "application/javascript",
    ".svg":   "image/svg+xml",
    ".png":   "image/png",
    ".jpg":   "image/jpeg",
    ".jpeg":  "image/jpeg",
    ".gif":   "image/gif",
    ".ico":   "image/x-icon",
    ".woff":  "font/woff",
    ".woff2": "font/woff2",
    ".ttf":   "font/ttf",
    ".eot":   "application/vnd.ms-fontobject",
}

# ─── HTTP Session ─────────────────────────────────────────────────────────────

class FreetzSession:
    """Handles HTTP connection and authentication to a Freetz device."""

    def __init__(self, host, port, user, password, newlogin=False,
                 timeout=DEFAULT_TIMEOUT, verbose=False):
        self.base = f"http://{host}:{port}"
        self.user = user
        self.password = password
        self.newlogin = newlogin
        self.timeout = timeout
        self.verbose = verbose
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "FreetzEVO-MockupGenerator/" + VERSION})
        self._asset_cache: dict[str, bytes] = {}

    def connect(self) -> bool:
        """Authenticate and verify connectivity."""
        if self.newlogin:
            return self._auth_newlogin()
        else:
            self.session.auth = (self.user, self.password)
            return self._verify()

    def _verify(self) -> bool:
        try:
            r = self.session.get(self.base + "/", timeout=self.timeout)
            if r.status_code in (200, 302, 301):
                print(f"  ✓ Connected to {self.base} (HTTP {r.status_code})")
                return True
            print(f"  ✗ HTTP {r.status_code} — check credentials")
            return False
        except requests.ConnectionError as e:
            print(f"  ✗ Connection failed: {e}")
            return False

    def _auth_newlogin(self) -> bool:
        """Authenticate via Freetz NEWLOGIN (session-cookie) mechanism."""
        try:
            # Step 1: GET login page to obtain SID cookie
            r = self.session.get(self.base + "/cgi-bin/login.cgi", timeout=self.timeout)
            # Extract SID from Set-Cookie
            sid = self.session.cookies.get("SID", "")
            if not sid:
                # Try parsing from response
                match = re.search(r"SID=([a-f0-9]+)", r.text)
                if match:
                    sid = match.group(1)
            if not sid:
                print("  ✗ Could not obtain SID from login page")
                return False
            # Step 2: compute hash = MD5(SID + MD5(user + password))
            inner = hashlib.md5((self.user + self.password).encode()).hexdigest()
            outer = hashlib.md5((sid + inner).encode()).hexdigest()
            # Step 3: POST hash
            r2 = self.session.get(
                f"{self.base}/cgi-bin/login.cgi?hash={outer}",
                timeout=self.timeout
            )
            if r2.status_code == 200 and "Wrong password" not in r2.text:
                print(f"  ✓ NEWLOGIN authentication successful")
                return True
            print("  ✗ NEWLOGIN authentication failed — wrong password?")
            return False
        except requests.ConnectionError as e:
            print(f"  ✗ Connection failed: {e}")
            return False

    def get(self, url: str) -> requests.Response | None:
        """GET a URL, returning None on error."""
        full = url if url.startswith("http") else self.base + url
        try:
            r = self.session.get(full, timeout=self.timeout, allow_redirects=True)
            if self.verbose:
                print(f"    GET {url} → {r.status_code}")
            return r
        except Exception as e:
            if self.verbose:
                print(f"    GET {url} → ERROR: {e}")
            return None

    def fetch_asset(self, url: str) -> bytes | None:
        """Fetch a static asset, caching results."""
        if url in self._asset_cache:
            return self._asset_cache[url]
        r = self.get(url)
        if r and r.status_code == 200:
            self._asset_cache[url] = r.content
            return r.content
        return None


# ─── Asset Inliner ───────────────────────────────────────────────────────────

class AssetInliner:
    """Converts remote URLs to inline data URIs or inline text."""

    def __init__(self, session: FreetzSession, base_url: str):
        self.session = session
        self.base_url = base_url

    def _abs(self, href: str, current_page: str = "") -> str:
        if href.startswith("data:") or href.startswith("http"):
            return href
        if href.startswith("//"):
            return "http:" + href
        if href.startswith("/"):
            return self.base_url + href
        # relative
        base = current_page.rsplit("/", 1)[0] if "/" in current_page else current_page
        return self.base_url + "/" + base.lstrip("/") + "/" + href

    def to_data_uri(self, url: str) -> str:
        """Fetch binary asset → base64 data URI."""
        if url.startswith("data:"):
            return url
        ext = Path(url.split("?")[0]).suffix.lower()
        mime = MIME_MAP.get(ext, "application/octet-stream")
        data = self.session.fetch_asset(url)
        if data:
            b64 = base64.b64encode(data).decode()
            return f"data:{mime};base64,{b64}"
        return url

    def inline_css_text(self, css_text: str, css_url: str = "") -> str:
        """Inline url() references inside CSS text."""
        def replace_url(m):
            raw = m.group(1).strip("'\"")
            if raw.startswith("data:"):
                return m.group(0)
            abs_url = self._abs(raw, css_url)
            ext = Path(abs_url.split("?")[0]).suffix.lower()
            if ext in {".css"}:
                # Recurse for @import
                sub_css = self.session.fetch_asset(abs_url)
                if sub_css:
                    return self.inline_css_text(sub_css.decode("utf-8", errors="replace"), abs_url)
                return ""
            return f"url('{self.to_data_uri(abs_url)}')"

        return re.sub(r"url\(([^)]+)\)", replace_url, css_text)

    def fetch_and_inline_css(self, href: str, current_page: str = "") -> str:
        """Fetch a CSS file and inline all its url() references."""
        abs_href = self._abs(href, current_page)
        data = self.session.fetch_asset(abs_href)
        if not data:
            return ""
        css_text = data.decode("utf-8", errors="replace")
        return self.inline_css_text(css_text, abs_href)


# ─── Page Processor ──────────────────────────────────────────────────────────

class PageProcessor:
    """Transforms a fetched CGI page HTML into a mockup-embeddable fragment."""

    def __init__(self, inliner: AssetInliner):
        self.inliner = inliner

    # ── AJAX file pre-loading helpers ────────────────────────────────────────

    def _find_ajax_file_keys(self, html: str) -> list[str]:
        """Scan HTML/JS for AJAX read_file calls and return file key values.

        Matches patterns such as:
          action=read_file&file=.rtorrent.rc
          file=config.php&...action=read_file
          fetch('/cgi-bin/pkg.cgi?ajax=1&action=read_file&file=xxx')
        Returns a deduplicated list of unquoted file key strings.
        """
        keys: list[str] = []

        def _add(key: str):
            key = urllib.parse.unquote(key.strip())
            if key and key not in keys and not key.startswith("{"):
                keys.append(key)

        # action=read_file ...file=VALUE  (order 1)
        for m in re.finditer(
                r"action=read_file[^'\"]*?[&?]file=([^'\"&\s<>]+)", html):
            _add(m.group(1))
        # file=VALUE ...action=read_file   (order 2)
        for m in re.finditer(
                r"[&?]file=([^'\"&\s<>]+)[^'\"]*?action=read_file", html):
            _add(m.group(1))
        # Standalone string literals like '&file=something.rc' or
        # "?file=config.php" (covers JS string concatenation)
        for m in re.finditer(r"['\"][^'\"]*?[&?]file=([^'\"&\s<>]+)", html):
            k = m.group(1)
            if len(k) > 1:
                _add(k)
        return keys

    def _fetch_ajax_file(self, cgi_path: str, file_key: str) -> str | None:
        """Fetch a file from the device via the CGI read_file AJAX endpoint.

        cgi_path is an absolute URL path like /cgi-bin/rtorrent.cgi.
        Returns the file content string, or None on failure.

        The response is HTML-wrapped JSON in freetz-ng format:
          <div class="ajax-json-box">...<pre>Content-Type: application/json
          {"success": true, "content": "..."}</pre>...</div>
        """
        req_url = (f"{cgi_path}?ajax=1&action=read_file"
                   f"&file={urllib.parse.quote(file_key, safe='')}")
        r = self.inliner.session.get(req_url)
        if not r or r.status_code != 200:
            return None
        text = r.text
        marker = "Content-Type: application/json"
        pos = text.find(marker)
        if pos == -1:
            return None
        first_brace = text.find("{", pos + len(marker))
        if first_brace == -1:
            return None
        depth, end = 0, -1
        for i in range(first_brace, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end == -1:
            return None
        try:
            data = json.loads(text[first_brace:end])
            if data.get("success") and "content" in data:
                return data["content"]
        except (json.JSONDecodeError, KeyError):
            pass
        return None

    def _find_cgi_endpoint(self, html: str, page_url: str) -> str | None:
        """Infer the CGI endpoint path used by AJAX calls on this page.

        Strategy (first match wins):
          1. If the page itself is a /cgi-bin/... URL, derive from it.
          2. Scan inline JS for explicit fetch('/cgi-bin/xxx.cgi') patterns.
          3. Derive /cgi-bin/<pkg>.cgi from a /<pkg>/ alias page URL.
        Returns an absolute path string or None.
        """
        path = page_url.split("?")[0]
        if "/cgi-bin/" in path:
            m = re.match(r"(/cgi-bin/[^/?]+(?:\.[a-z]+)?)", path)
            return m.group(1) if m else path

        # Scan JS for explicit endpoint references (e.g. in variables)
        for m in re.finditer(r"['\"](/[^'\"]*?/cgi-bin/[^'\"?]+\.cgi)['\"|?]", html):
            return m.group(1)
        # Also: plain string assignment const endpoint = '/cgi-bin/rtorrent.cgi'
        for m in re.finditer(r"=\s*['\"](/cgi-bin/[^'\"?]+\.cgi)['\"]", html):
            return m.group(1)

        # Derive from /<pkgname>/ alias path
        m_alias = re.match(r"^/([a-zA-Z][a-zA-Z0-9_-]*)/", path)
        if m_alias:
            pkg = m_alias.group(1)
            return f"/cgi-bin/{pkg}.cgi"

        return None

    def _build_fetch_interceptor(self, preloaded: dict[str, str]) -> str:
        """Return a <script> block that intercepts fetch() and XHR for
        read_file AJAX calls and returns the preloaded file content,
        matching the freetz-ng HTML-wrapped JSON response format.
        Write operations (write_file, save, delete) are silently rejected
        with a read-only error so the mockup stays intact.
        """
        files_json = json.dumps(preloaded, ensure_ascii=False)
        return f"""
<script>
/* --- Mockup AJAX interceptor: preloaded file content --- */
(function() {{
  window.__mockupFiles = {files_json};

  function _mockupResponse(content) {{
    var body = '<div class="ajax-json-box"><div class="ajax-json-content"><pre>' +
               'Content-Type: application/json\\n\\n' +
               JSON.stringify({{success: true, content: content}}) +
               '</pre></div></div>';
    return new Response(body, {{status: 200,
      headers: {{'Content-Type': 'text/html; charset=UTF-8'}}}});
  }}

  function _mockupReadOnly() {{
    var body = '<div class="ajax-json-box"><div class="ajax-json-content"><pre>' +
               'Content-Type: application/json\\n\\n' +
               JSON.stringify({{success: false, error: 'Mockup: read-only'}}) +
               '</pre></div></div>';
    return new Response(body, {{status: 200,
      headers: {{'Content-Type': 'text/html; charset=UTF-8'}}}});
  }}

  function _fileKeyFromUrl(url) {{
    var s = String(url);
    var m = s.match(/[?&]action=read_file[^]*?[?&]file=([^&]+)/) ||
            s.match(/[?&]file=([^&]+)[^]*?[?&]action=read_file/);
    return m ? decodeURIComponent(m[1]) : null;
  }}

  /* ── fetch() interceptor ────────────────────────────────────────────── */
  var _origFetch = window.fetch ? window.fetch.bind(window) : null;
  window.fetch = function(resource, init) {{
    var url = (resource && resource.url) ? resource.url : String(resource);
    var key = _fileKeyFromUrl(url);
    if (key !== null && Object.prototype.hasOwnProperty.call(window.__mockupFiles, key))
      return Promise.resolve(_mockupResponse(window.__mockupFiles[key]));
    if (/[?&]action=(write_file|save|delete)/.test(url))
      return Promise.resolve(_mockupReadOnly());
    return _origFetch ? _origFetch(resource, init)
                      : Promise.reject(new Error('Mockup: no fetch'));
  }};

  /* ── XMLHttpRequest interceptor (legacy callers) ────────────────────── */
  var _OrigXHR = window.XMLHttpRequest;
  function MockXHR() {{
    this._real = new _OrigXHR();
    this.readyState = 0; this.status = 0;
    this.responseText = ''; this.response = '';
    this.onreadystatechange = null; this.onload = null; this.onerror = null;
    var self = this;
    this._real.onreadystatechange = function() {{
      self.readyState = self._real.readyState;
      self.status = self._real.status;
      self.responseText = self._real.responseText;
      self.response = self._real.response;
      if (self.onreadystatechange) self.onreadystatechange();
      if (self._real.readyState === 4 && self.onload) self.onload();
    }};
  }}
  MockXHR.prototype.open = function(method, url) {{
    this._url = url;
    var key = _fileKeyFromUrl(url);
    if (key !== null && Object.prototype.hasOwnProperty.call(window.__mockupFiles, key)) {{
      this._interceptKey = key; return;
    }}
    this._real.open(method, url, true);
  }};
  MockXHR.prototype.send = function(body) {{
    if (this._interceptKey !== undefined) {{
      var content = window.__mockupFiles[this._interceptKey];
      this.readyState = 4; this.status = 200;
      this.responseText = '<div class="ajax-json-box"><div class="ajax-json-content"><pre>' +
        'Content-Type: application/json\\n\\n' +
        JSON.stringify({{success: true, content: content}}) +
        '</pre></div></div>';
      this.response = this.responseText;
      if (this.onreadystatechange) this.onreadystatechange();
      if (this.onload) this.onload();
      return;
    }}
    this._real.send(body);
  }};
  MockXHR.prototype.setRequestHeader = function(h, v) {{
    if (this._interceptKey === undefined) this._real.setRequestHeader(h, v);
  }};
  MockXHR.prototype.getAllResponseHeaders = function() {{
    return this._interceptKey !== undefined
      ? 'content-type: text/html\\r\\n'
      : this._real.getAllResponseHeaders();
  }};
  MockXHR.UNSENT = 0; MockXHR.OPENED = 1; MockXHR.HEADERS_RECEIVED = 2;
  MockXHR.LOADING = 3; MockXHR.DONE = 4;
  window.XMLHttpRequest = MockXHR;
}})();
</script>
"""
    def extract_content(self, html: str, url: str) -> dict:
        """
        Parse HTML and return:
          {"title": str, "body_html": str, "extra_styles": str, "extra_scripts": str}
        """
        soup = BeautifulSoup(html, "lxml")

        # Title
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else url.split("/")[-1]

        # Remove <head> tags we don't need embedded
        head = soup.find("head")
        extra_styles = ""
        extra_scripts = ""
        if head:
            for link in head.find_all("link", rel="stylesheet"):
                href = link.get("href", "")
                if href and "/style/evo/base.css" not in href:
                    css_content = self.inliner.fetch_and_inline_css(href, url)
                    if css_content:
                        extra_styles += f"\n/* --- {href} --- */\n{css_content}\n"
            for style in head.find_all("style"):
                extra_styles += "\n" + self.inliner.inline_css_text(style.get_text(), url) + "\n"
            # Embedded scripts (avoid service worker registration etc.)
            for script in head.find_all("script"):
                src = script.get("src", "")
                s_text = script.get_text()
                if src:
                    if "ace" in src or "sw.js" in src or "serviceWorker" in s_text:
                        continue
                    data = self.inliner.session.fetch_asset(
                        self.inliner._abs(src, url))
                    if data:
                        extra_scripts += f"\n// --- {src} ---\n{data.decode('utf-8', errors='replace')}\n"
                else:
                    if "serviceWorker" in s_text or "navigator.serviceWorker" in s_text:
                        continue
                    extra_scripts += "\n" + s_text + "\n"

        # --- Inline img src ---
        body = soup.find("body") or soup
        for img in body.find_all("img"):
            src = img.get("src", "")
            if src and not src.startswith("data:"):
                abs_src = self.inliner._abs(src, url)
                img["src"] = self.inliner.to_data_uri(abs_src)

        # --- Disable all form submissions ---
        for form in body.find_all("form"):
            form["onsubmit"] = "event.preventDefault(); return false;"
            form["data-mockup"] = "readonly"

        # --- Neutralize navigation links (will be handled by mockup JS) ---
        # Resolve relative URLs against the current page so that links like
        # "../net.cgi", "./conf/webcfg", or "webcfg" are all normalised to an
        # absolute /cgi-bin/... path before being wired to mockupNavigate().
        _dummy_base = "http://fritz.box" + (url.split("?")[0] if url.startswith("/") else "/")
        for a in body.find_all("a", href=True):
            href = a["href"].strip()
            if not href or href.startswith("#") or \
               href.startswith("javascript:") or href.startswith("mailto:"):
                continue
            try:
                resolved = urllib.parse.urljoin(_dummy_base, href)
                parsed_a = urllib.parse.urlparse(resolved)
                path_a = parsed_a.path
                qs_a = parsed_a.query
                if qs_a:
                    safe = {k: v for k, v in urllib.parse.parse_qsl(qs_a)
                            if k not in ("SID", "sid", "ts", "nonce", "_")}
                    qs_a = urllib.parse.urlencode(safe) if safe else ""
                path_with_qs = path_a + ("?" + qs_a if qs_a else "")
            except Exception:
                path_with_qs = href
            if path_with_qs.startswith("/cgi-bin/") or path_with_qs.startswith("/mww/") or \
               re.match(r"^/[a-zA-Z][a-zA-Z0-9_-]*/", path_with_qs):
                a["data-mockup-href"] = path_with_qs
                a["href"] = "#"
                a["onclick"] = f"mockupNavigate('{path_with_qs}'); return false;"

        # --- Inline background-image in style attributes ---
        for tag in body.find_all(style=True):
            orig = tag["style"]
            tag["style"] = self.inliner.inline_css_text(orig, url)

        # --- Pre-fetch AJAX read_file content and inject fetch interceptor ---
        # Identify the CGI endpoint that services AJAX calls for this page,
        # pre-fetch each referenced file from the live device, then embed a
        # fetch/XHR interceptor so the editor works offline in the mockup.
        cgi_path = self._find_cgi_endpoint(html, url)
        if cgi_path:
            file_keys = self._find_ajax_file_keys(html)
            preloaded: dict[str, str] = {}
            for key in file_keys:
                content = self._fetch_ajax_file(cgi_path, key)
                if content is not None:
                    preloaded[key] = content
            if preloaded:
                extra_scripts += self._build_fetch_interceptor(preloaded)

        # Extract the inner HTML of <body> (or full soup if no body)
        body_tag = soup.find("body")
        if body_tag:
            # Remove the very outer #world wrapper we want to keep for styling
            body_html = body_tag.decode_contents()
        else:
            body_html = str(soup)

        return {
            "title": title,
            "body_html": body_html,
            "extra_styles": extra_styles,
            "extra_scripts": extra_scripts,
        }


# ─── Crawler ─────────────────────────────────────────────────────────────────

class PageCrawler:
    """Discovers and fetches CGI pages from the Freetz web interface."""

    def __init__(self, session: FreetzSession, inliner: AssetInliner,
                 processor: PageProcessor, max_pages: int = DEFAULT_MAX_PAGES,
                 max_depth: int | None = None,
                 pkg_filter: list[str] | None = None,
                 packages_only: bool = False):
        self.session = session
        self.inliner = inliner
        self.processor = processor
        self.max_pages = max_pages
        self.max_depth = max_depth       # None = unlimited (bounded only by max_pages)
        # pkg_filter: list of package names; if set, package-conf URLs that are
        # NOT for a listed package are silently dropped.
        # packages_only: only meaningful when pkg_filter is set — if True, any
        # URL under /cgi-bin/conf/ or /mww/ that does not match a listed package
        # is rejected even if it was discovered via a link.
        self.pkg_filter: list[str] | None = pkg_filter
        self.packages_only: bool = packages_only and bool(pkg_filter)
        self.visited: set[str] = set()
        self.pages: OrderedDict[str, dict] = OrderedDict()
        self.menu_items: list[dict] = []

    def _should_skip(self, url: str) -> bool:
        for pattern in SKIP_URL_PATTERNS:
            if pattern in url:
                return True
        return False

    def _is_pkg_allowed(self, url: str) -> bool:
        """Return False if pkg_filter is active and url belongs to a package
        not in the filter list.

        Logic:
          - If packages_only=False (default): all URLs are allowed; package
            filter only drives which extra start_urls are added — no pages
            are excluded.
          - If packages_only=True: a URL that looks like a package-specific
            conf page (/cgi-bin/conf/<name> or /mww/<name>/) is allowed only
            when <name> is in pkg_filter.  Core system pages (overview, webcfg
            internals, etc.) are always allowed.

        URL patterns recognised as package-specific (first match wins):
          /cgi-bin/conf/<pkg>       → package = <pkg>
          /mww/<pkg>/               → package = <pkg>
          /cgi-bin/<pkg>.cgi        → package = <pkg>  (bare CGI top-level)
          /cgi-bin/<pkg>/<anything> → package = <pkg>  (sub-CGI of pkg, e.g.
                                      /cgi-bin/mod/webcfg.cgi)
          /<pkg>/...                → package = <pkg>  (mww-alias, e.g.
                                      /rtorrent/rtorrent_config_editor.html)
        """
        if not self.packages_only or not self.pkg_filter:
            return True
        path = urllib.parse.urlparse(url).path
        # /cgi-bin/conf/<pkg>[/...]
        m_conf   = re.match(r"^/cgi-bin/conf/([^/?]+)", path)
        # /mww/<pkg>[/...]
        m_mww    = re.match(r"^/mww/([^/?]+)", path)
        # /cgi-bin/<pkg>.cgi  (bare top-level CGI)
        m_cgi    = re.match(r"^/cgi-bin/([^/?]+)\.cgi$", path)
        # /cgi-bin/<pkg>/<subpage>[.cgi]  (package sub-directory CGIs,
        #   e.g. /cgi-bin/mod/webcfg.cgi, /cgi-bin/mod/logs.cgi)
        m_subcgi = re.match(r"^/cgi-bin/([^/?]+)/", path)
        # /<pkg>/...  (mww-alias, e.g. /rtorrent/rtorrent_config_editor.html)
        m_alias  = re.match(r"^/([a-zA-Z][a-zA-Z0-9_-]*)/", path)
        for m in (m_conf, m_mww, m_cgi, m_subcgi):
            if m:
                pkg_name = m.group(1).lower()
                return any(pkg_name == p.lower() for p in self.pkg_filter)
        if m_alias and m_alias.group(1).lower() not in _STATIC_DIRS:
            pkg_name = m_alias.group(1).lower()
            return any(pkg_name == p.lower() for p in self.pkg_filter)
        # Core system pages (/cgi-bin/overview.cgi, etc.) are always included.
        return True

    def _normalise(self, href: str) -> str | None:
        """Normalise href to a canonical path.  Returns None if should skip.

        Accepted path prefixes:
          /cgi-bin/...          standard Freetz CGI pages
          /mww/...              mww package static pages
          /<pkgname>/...        mww-alias path (e.g. /rtorrent/, /nginx/),
                                accepted only when <pkgname> is not a known
                                static-asset directory name (/css/, /js/ …).
        """
        parsed = urllib.parse.urlparse(href)
        path = parsed.path
        if not path.startswith("/cgi-bin/") and not path.startswith("/mww/"):
            # Accept /<pkgname>/... mww-alias paths, excluding static-asset dirs
            m_alias = re.match(r"^/([a-zA-Z][a-zA-Z0-9_-]*)/", path)
            if not m_alias or m_alias.group(1).lower() in _STATIC_DIRS:
                return None
        # Keep query string for pages that differ only in query
        qs = parsed.query
        norm = path
        if qs:
            # Only keep safe params for page identity (not session tokens)
            safe_params = {k: v for k, v in urllib.parse.parse_qsl(qs)
                           if k not in ("SID", "sid", "ts", "nonce")}
            if safe_params:
                norm += "?" + urllib.parse.urlencode(safe_params)
        return norm

    def _extract_links(self, html: str, page_url: str) -> list[str]:
        """Extract and normalise all crawlable links found in html.

        Sources scanned:
          - <a href="..."> tags
          - window.open('...', ...) calls in <script> blocks
          - window.location[.href] = '...' assignments in <script> blocks

        Relative URLs are resolved against page_url using urljoin.
        """
        soup = BeautifulSoup(html, "lxml")
        links: list[str] = []
        # Base for relative resolution: use page_url path, strip query
        base_path = page_url.split("?")[0] if page_url else "/"
        dummy_base = "http://fritz.box" + base_path

        def _add(href: str):
            href = href.strip()
            if not href or href.startswith("#") or \
               href.startswith("javascript:") or href.startswith("mailto:"):
                return
            try:
                resolved = urllib.parse.urljoin(dummy_base, href)
                parsed = urllib.parse.urlparse(resolved)
                path = parsed.path
                qs = parsed.query
                # Strip volatile params that would produce duplicate entries
                if qs:
                    safe = {k: v for k, v in urllib.parse.parse_qsl(qs)
                            if k not in ("SID", "sid", "ts", "nonce", "_")}
                    qs = urllib.parse.urlencode(safe) if safe else ""
                norm_path = path + ("?" + qs if qs else "")
                n = self._normalise(norm_path)
                if n and n not in links:
                    links.append(n)
            except Exception:
                pass

        # --- <a href> tags ---
        for a in soup.find_all("a", href=True):
            _add(a["href"])

        # --- window.open(...) and location.href assignments in <script> tags ---
        _JS_URL_RE = re.compile(
            r"window\.open\s*\(\s*['\"]([^'\"]+)['\"]"        # window.open('url'
            r"|window\.location(?:\.href)?\s*=\s*['\"]([^'\"]+)['\"]"  # window.location = 'url'
            r"|location\.href\s*=\s*['\"]([^'\"]+)['\"]"      # location.href = 'url'
        )
        for script in soup.find_all("script"):
            js_text = script.get_text() or ""
            for m_js in _JS_URL_RE.finditer(js_text):
                url_hit = m_js.group(1) or m_js.group(2) or m_js.group(3)
                if url_hit:
                    _add(url_hit)

        return links

    def _extract_menu_structure(self, html: str) -> list[dict]:
        """Extract nav menu from a page (sidebar / bottom bar)."""
        soup = BeautifulSoup(html, "lxml")
        items = []
        # Look for the freetz menu UL
        for ul in soup.find_all("ul", class_=re.compile(r"menu|nav")):
            for li in ul.find_all("li"):
                a = li.find("a", href=True)
                if not a:
                    continue
                href = a["href"]
                n = self._normalise(href)
                if not n:
                    continue
                label = a.get_text(strip=True) or n.split("/")[-1]
                sub_items = []
                sub_ul = li.find("ul")
                if sub_ul:
                    for sub_li in sub_ul.find_all("li"):
                        sub_a = sub_li.find("a", href=True)
                        if sub_a:
                            sn = self._normalise(sub_a["href"])
                            if sn:
                                sub_items.append({
                                    "label": sub_a.get_text(strip=True) or sn.split("/")[-1],
                                    "url": sn,
                                })
                items.append({"label": label, "url": n, "children": sub_items})
        return items

    def crawl(self, start_urls: list[str] | None = None):
        """Crawl the web interface starting from overview.

        Uses BFS with optional depth limiting (max_depth).  Each queue entry
        is a (url, depth) tuple.  Depth 0 = start URLs; depth N = N hops from
        a start URL.  When max_depth is None the crawl is depth-unlimited and
        is bounded only by max_pages.
        """
        if start_urls is None:
            start_urls = ["/", "/cgi-bin/overview.cgi"]

        depth_info = ""
        if self.max_depth is not None:
            depth_info = f", max depth {self.max_depth}"
        pkg_info = ""
        if self.pkg_filter:
            mode = " (packages-only)" if self.packages_only else ""
            pkg_info = f", packages: {', '.join(self.pkg_filter)}{mode}"
        print(f"\n  Crawling web interface (max {self.max_pages} pages{depth_info}{pkg_info})...")

        # Queue entries: (url, depth)
        queue: list[tuple[str, int]] = [(u, 0) for u in start_urls]
        in_queue: set[str] = {self._normalise(u) or u for u in start_urls}

        while queue and len(self.pages) < self.max_pages:
            url, depth = queue.pop(0)
            norm = self._normalise(url) or url
            if norm in self.visited:
                continue
            if self._should_skip(url):
                continue
            self.visited.add(norm)

            depth_tag = f" (d{depth})" if self.max_depth is not None else ""
            if not self._is_pkg_allowed(norm):
                if self.session.verbose:
                    print(f"  [--] Filtered by --packages-only: {norm}")
                continue
            print(f"  [{len(self.pages)+1:2d}] Fetching {norm}{depth_tag} ...", end=" ", flush=True)
            r = self.session.get(url)
            if not r or r.status_code != 200:
                print(f"SKIP ({r.status_code if r else 'ERR'})")
                continue

            # Only process HTML pages
            ct = r.headers.get("Content-Type", "")
            if "html" not in ct:
                print("skip (not HTML)")
                continue

            html = r.text
            # Extract menu on first page
            if not self.menu_items:
                self.menu_items = self._extract_menu_structure(html)

            # Process page content
            try:
                info = self.processor.extract_content(html, norm)
            except Exception as e:
                print(f"ERROR processing: {e}")
                continue

            info["url"] = norm
            self.pages[norm] = info
            print(f"  ✓  «{info['title']}»")

            # Enqueue discovered links (unless depth limit reached)
            if self.max_depth is None or depth < self.max_depth:
                new_links = self._extract_links(html, norm)
                for link in new_links:
                    if link not in self.visited and not self._should_skip(link) \
                            and link not in in_queue:
                        queue.append((link, depth + 1))
                        in_queue.add(link)

        print(f"\n  Done. Captured {len(self.pages)} pages.")


# ─── Mockup Builder ──────────────────────────────────────────────────────────

class MockupBuilder:
    """Assembles all captured pages into a single self-contained HTML file."""

    def __init__(self, session: FreetzSession, inliner: AssetInliner, output: str):
        self.session = session
        self.inliner = inliner
        self.output = output

    def _fetch_base_css(self) -> str:
        """Fetch and fully inline base.css."""
        print("  Inlining base.css ...", end=" ", flush=True)
        css = self.inliner.fetch_and_inline_css("/style/evo/base.css")
        print("done.")
        return css

    def _icon_b64(self) -> str:
        """Fetch favicon as base64 for the mockup's own <link rel=icon>."""
        data = self.session.fetch_asset("/style/evo/icon.svg")
        if data:
            return "data:image/svg+xml;base64," + base64.b64encode(data).decode()
        return ""

    def build(self, pages: OrderedDict[str, dict],
              menu_items: list[dict],
              frameless: bool = False) -> str:
        """Build and return the final HTML string.

        When *frameless* is True the output uses :data:`_FRAMELESS_TEMPLATE`
        instead of the default browser-chrome wrapper template.
        """

        base_css = self._fetch_base_css()
        favicon = self._icon_b64()

        # Collect all extra CSS/JS from pages (deduplicated)
        seen_keys: set[str] = set()
        all_extra_styles = ""
        all_extra_scripts = ""
        for page in pages.values():
            key = hashlib.md5(page.get("extra_styles", "").encode()).hexdigest()
            if key not in seen_keys and page.get("extra_styles"):
                all_extra_styles += page["extra_styles"]
                seen_keys.add(key)

        # Pages JSON index
        page_ids = list(pages.keys())
        first_id = page_ids[0] if page_ids else ""

        # Build page divs
        page_divs = ""
        for pid, page in pages.items():
            safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", pid)
            page_divs += (
                f'<div class="mockup-page" id="page_{safe_id}" '
                f'data-url="{pid}" style="display:none">\n'
                f'{page["body_html"]}\n'
                f'</div>\n'
            )

        # Build sidebar nav
        nav_html = ""
        if menu_items:
            nav_html = _build_nav_html(menu_items, page_ids)
        else:
            # Fallback: plain list
            for pid in page_ids:
                label = pages[pid]["title"]
                safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", pid)
                nav_html += (
                    f'<li><a href="#" onclick="mockupNavigate(\'{pid}\'); return false;" '
                    f'data-pid="{safe_id}">{label}</a></li>\n'
                )
            nav_html = f"<ul class='mockup-nav-list'>\n{nav_html}</ul>"

        # Build pages index JSON for JS
        pages_index = json.dumps(
            {pid: {"title": p["title"], "id": re.sub(r"[^a-zA-Z0-9_-]", "_", pid)}
             for pid, p in pages.items()},
            indent=2
        )

        template = _FRAMELESS_TEMPLATE if frameless else _TEMPLATE
        return template.format(
            version=VERSION,
            base_css=base_css,
            extra_styles=all_extra_styles,
            favicon=favicon,
            page_count=len(pages),
            timestamp=time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
            nav_html=nav_html,
            page_divs=page_divs,
            first_page_id=re.sub(r"[^a-zA-Z0-9_-]", "_", first_id),
            pages_index=pages_index,
        )

    def save(self, html: str):
        out = Path(self.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")
        size_kb = out.stat().st_size // 1024
        print(f"\n  ✓ Mockup saved: {self.output}  ({size_kb} KB)")


# ─── Nav builder helper ───────────────────────────────────────────────────────

def _build_nav_html(menu_items: list[dict], page_ids: list[str]) -> str:
    html = "<ul class='mockup-nav-list'>\n"
    for item in menu_items:
        pid = item["url"]
        safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", pid)
        in_index = pid in page_ids
        cls = " class='has-children'" if item.get("children") else ""
        html += f"<li{cls}>"
        if in_index:
            html += (f"<a href='#' onclick=\"mockupNavigate('{pid}'); return false;\" "
                     f"data-pid='{safe_id}'>{item['label']}</a>")
        else:
            html += f"<span class='mockup-nav-unavail'>{item['label']}</span>"
        if item.get("children"):
            html += "<ul>\n"
            for child in item["children"]:
                cpid = child["url"]
                csafe = re.sub(r"[^a-zA-Z0-9_-]", "_", cpid)
                in_idx = cpid in page_ids
                if in_idx:
                    html += (f"<li><a href='#' onclick=\"mockupNavigate('{cpid}'); return false;\" "
                             f"data-pid='{csafe}'>{child['label']}</a></li>\n")
                else:
                    html += f"<li><span class='mockup-nav-unavail'>{child['label']}</span></li>\n"
            html += "</ul>\n"
        html += "</li>\n"
    html += "</ul>"
    return html


# ─── HTML Template ────────────────────────────────────────────────────────────

_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Freetz-EVO — Interactive UI Mockup</title>
<link rel="icon" type="image/svg+xml" href="{favicon}">
<style>
/* ── Freetz-EVO base skin ────────────────────────────────────────── */
{base_css}

/* ── Extra page styles ───────────────────────────────────────────── */
{extra_styles}

/* ── Mockup shell ────────────────────────────────────────────────── */
:root {{
  --mk-chrome: #1a1f2e;
  --mk-chrome-border: #2e3a50;
  --mk-nav-w: 200px;
  --mk-nav-bg: #141929;
  --mk-header-h: 42px;
  --mk-status-h: 30px;
}}
*, *::before, *::after {{ box-sizing: border-box; }}

html, body {{
  margin: 0; padding: 0;
  background: #0d1117;
  font-family: system-ui, -apple-system, Arial, sans-serif;
  height: 100%;
}}

/* ── Outer wrapper: centered card ───── */
.mk-wrapper {{
  max-width: 1100px;
  margin: 0 auto;
  padding: 24px 12px 48px;
}}

/* ── Mockup title (above browser) ───── */
.mk-title {{
  text-align: center;
  margin: 0 0 18px;
  font-size: 1.1rem;
  color: #94a3b8;
  letter-spacing: 0.03em;
}}
.mk-title strong {{ color: #3b82f6; }}

/* ── Browser frame ───────────────────── */
.mk-browser {{
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 24px 64px rgba(0,0,0,0.7);
  border: 1px solid var(--mk-chrome-border);
}}

/* Chrome top bar */
.mk-chrome-bar {{
  background: var(--mk-chrome);
  height: var(--mk-header-h);
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 14px;
  user-select: none;
}}
.mk-dots {{ display: flex; gap: 6px; flex-shrink: 0; }}
.mk-dot {{
  width: 12px; height: 12px;
  border-radius: 50%;
}}
.mk-dot.red   {{ background: #ef4444; }}
.mk-dot.amber {{ background: #f59e0b; }}
.mk-dot.green {{ background: #22c55e; }}

.mk-url-bar {{
  flex: 1;
  background: #0f172a;
  border: 1px solid var(--mk-chrome-border);
  border-radius: 6px;
  padding: 4px 12px;
  font-size: 0.75rem;
  color: #64748b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}}
.mk-url-prefix {{ color: #22c55e; }}

.mk-chrome-btns {{ display: flex; gap: 6px; flex-shrink: 0; }}
.mk-chrome-btn {{
  background: #374151;
  border: none;
  border-radius: 5px;
  color: #94a3b8;
  font-size: 0.75rem;
  padding: 3px 10px;
  cursor: pointer;
  transition: background .15s;
}}
.mk-chrome-btn:hover {{ background: #4b5563; }}

/* Content area = nav sidebar + page viewport */
.mk-content {{
  display: flex;
  height: calc(100vh - 200px);
  min-height: 500px;
  max-height: 800px;
  background: var(--evo-bg, #0f172a);
}}

/* Sidebar nav */
.mk-sidebar {{
  width: var(--mk-nav-w);
  background: var(--mk-nav-bg);
  border-right: 1px solid var(--mk-chrome-border);
  overflow-y: auto;
  flex-shrink: 0;
  padding: 10px 0;
}}
.mk-sidebar-title {{
  font-size: 0.65rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: #475569;
  padding: 6px 14px 4px;
}}
.mockup-nav-list {{
  list-style: none;
  margin: 0; padding: 0;
}}
.mockup-nav-list li {{ position: relative; }}
.mockup-nav-list > li > a,
.mockup-nav-list > li > span {{
  display: block;
  padding: 7px 14px;
  font-size: 0.78rem;
  color: #94a3b8;
  text-decoration: none;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: background .12s, color .12s;
  cursor: pointer;
}}
.mockup-nav-list > li > a:hover {{ background: rgba(59,130,246,0.12); color: #e2e8f0; }}
.mockup-nav-list > li > a.active {{ background: rgba(59,130,246,0.2); color: #3b82f6; font-weight: 600; }}
.mockup-nav-list > li .mockup-nav-unavail {{ color: #334155; cursor: default; }}
/* Sub-menu */
.mockup-nav-list li ul {{
  list-style: none; margin: 0; padding: 0;
  border-left: 2px solid #1e293b;
  margin-left: 14px;
}}
.mockup-nav-list li ul li a {{
  display: block; padding: 5px 14px;
  font-size: 0.74rem; color: #64748b;
  text-decoration: none;
  transition: color .12s;
}}
.mockup-nav-list li ul li a:hover {{ color: #e2e8f0; }}
.mockup-nav-list li ul li a.active {{ color: #3b82f6; font-weight: 600; }}

/* Viewport */
.mk-viewport {{
  flex: 1;
  overflow-y: auto;
  background: var(--evo-bg, #0f172a);
  position: relative;
}}
.mockup-page {{ min-height: 100%; }}

/* Status bar */
.mk-status-bar {{
  background: var(--mk-chrome);
  border-top: 1px solid var(--mk-chrome-border);
  height: var(--mk-status-h);
  display: flex;
  align-items: center;
  padding: 0 14px;
  gap: 16px;
  font-size: 0.7rem;
  color: #475569;
}}
.mk-status-bar .mk-badge {{
  background: #1e3a5f;
  color: #3b82f6;
  border-radius: 4px;
  padding: 1px 7px;
  font-size: 0.65rem;
  font-weight: 600;
}}

/* Readonly overlay badge */
.mk-readonly-badge {{
  position: fixed;
  top: 80px; right: 20px;
  background: rgba(245,158,11,0.15);
  border: 1px solid #f59e0b;
  color: #f59e0b;
  border-radius: 6px;
  padding: 4px 12px;
  font-size: 0.7rem;
  pointer-events: none;
  z-index: 9999;
  opacity: 0;
  transition: opacity .3s;
}}
.mk-readonly-badge.visible {{ opacity: 1; }}

/* Caption below browser */
.mk-caption {{
  text-align: center;
  margin-top: 16px;
  font-size: 0.78rem;
  color: #475569;
}}
.mk-caption a {{ color: #3b82f6; text-decoration: none; }}
.mk-caption a:hover {{ text-decoration: underline; }}

/* "Not captured" fallback */
.mk-not-captured {{
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  height: 100%;
  color: #334155;
  font-size: 0.9rem;
  gap: 8px;
}}

@media (max-width: 600px) {{
  .mk-sidebar {{ display: none; }}
  .mk-content {{ height: calc(100vh - 160px); }}
  .mk-title {{ font-size: 0.9rem; }}
}}
</style>
</head>
<body>

<div class="mk-wrapper">
  <p class="mk-title">
    <strong>Freetz-EVO</strong> — Interactive Web Interface Preview
    &nbsp;·&nbsp; {page_count} pages captured &nbsp;·&nbsp; {timestamp}
  </p>

  <div class="mk-browser">
    <!-- Chrome bar -->
    <div class="mk-chrome-bar">
      <div class="mk-dots">
        <div class="mk-dot red"></div>
        <div class="mk-dot amber"></div>
        <div class="mk-dot green"></div>
      </div>
      <div class="mk-url-bar">
        <span class="mk-url-prefix">http://</span><!--
        --><span id="mk-url-host">fritz.box:81</span><!--
        --><span id="mk-url-path">/</span>
      </div>
      <div class="mk-chrome-btns">
        <button class="mk-chrome-btn" onclick="mockupPrev()" title="Previous page">&#8592;</button>
        <button class="mk-chrome-btn" onclick="mockupNext()" title="Next page">&#8594;</button>
      </div>
    </div>

    <!-- Content: sidebar + viewport -->
    <div class="mk-content">
      <nav class="mk-sidebar" id="mk-sidebar">
        <div class="mk-sidebar-title">Navigation</div>
        {nav_html}
      </nav>
      <div class="mk-viewport" id="mk-viewport">
        {page_divs}
        <div class="mk-not-captured" id="mk-not-found" style="display:none">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none"
               stroke="#334155" stroke-width="1.5" stroke-linecap="round">
            <circle cx="12" cy="12" r="10"/>
            <line x1="15" y1="9" x2="9" y2="15"/>
            <line x1="9" y1="9" x2="15" y2="15"/>
          </svg>
          Page not captured in mockup
        </div>
      </div>
    </div>

    <!-- Status bar -->
    <div class="mk-status-bar">
      <span class="mk-badge">MOCKUP</span>
      <span id="mk-status-label">Interactive preview — forms are disabled</span>
      <span style="margin-left:auto" id="mk-page-counter">1 / {page_count}</span>
    </div>
  </div>

  <div class="mk-readonly-badge" id="mk-readonly-badge">Read-only mockup</div>

  <p class="mk-caption">
    Live interface on <a href="http://fritz.box:81" target="_blank">fritz.box:81</a>
    &nbsp;·&nbsp; Generated by
    <a href="https://github.com/Ircama/freetz-evo" target="_blank">Freetz-EVO</a>
    mockup generator v{version}
  </p>
</div>

<script>
// ── Mockup navigation JS ─────────────────────────────────────────────────────
var PAGES_INDEX = {pages_index};
var pageIds = Object.keys(PAGES_INDEX);
var currentIdx = 0;

function _safeId(pid) {{
  return pid.replace(/[^a-zA-Z0-9_-]/g, '_');
}}

function _showPage(idx) {{
  if (idx < 0 || idx >= pageIds.length) return;
  // Hide all
  document.querySelectorAll('.mockup-page').forEach(function(el) {{
    el.style.display = 'none';
  }});
  document.getElementById('mk-not-found').style.display = 'none';

  var pid = pageIds[idx];
  var safe = _safeId(pid);
  var el = document.getElementById('page_' + safe);
  if (el) {{
    el.style.display = '';
    el.scrollTop = 0;
  }} else {{
    document.getElementById('mk-not-found').style.display = 'flex';
  }}

  currentIdx = idx;

  // Update URL bar
  document.getElementById('mk-url-path').textContent = pid;

  // Update nav active state
  document.querySelectorAll('.mockup-nav-list a').forEach(function(a) {{
    a.classList.remove('active');
  }});
  document.querySelectorAll('[data-pid="' + safe + '"]').forEach(function(a) {{
    a.classList.add('active');
  }});

  // Update counter
  document.getElementById('mk-page-counter').textContent =
    (idx + 1) + ' / ' + pageIds.length;

  // Update status
  var info = PAGES_INDEX[pid] || {{}};
  document.getElementById('mk-status-label').textContent =
    (info.title || pid) + '  —  read-only mockup';
}}

function mockupNavigate(url) {{
  var idx = pageIds.indexOf(url);
  if (idx >= 0) {{
    _showPage(idx);
  }} else {{
    // Show "not found"
    document.querySelectorAll('.mockup-page').forEach(function(el) {{
      el.style.display = 'none';
    }});
    document.getElementById('mk-not-found').style.display = 'flex';
    document.getElementById('mk-url-path').textContent = url + ' [not captured]';
  }}
  // Flash readonly badge
  var badge = document.getElementById('mk-readonly-badge');
  badge.classList.add('visible');
  clearTimeout(badge._t);
  badge._t = setTimeout(function() {{ badge.classList.remove('visible'); }}, 1500);
}}

function mockupPrev() {{
  _showPage(currentIdx - 1 < 0 ? pageIds.length - 1 : currentIdx - 1);
}}
function mockupNext() {{
  _showPage((currentIdx + 1) % pageIds.length);
}}

// Keyboard nav
document.addEventListener('keydown', function(e) {{
  if (e.key === 'ArrowRight' || e.key === 'ArrowDown') mockupNext();
  if (e.key === 'ArrowLeft'  || e.key === 'ArrowUp')   mockupPrev();
}});

// Init: show first page
_showPage(0);

// Prevent actual form submissions
document.addEventListener('submit', function(e) {{
  e.preventDefault();
  var badge = document.getElementById('mk-readonly-badge');
  badge.textContent = 'Mockup: forms are disabled';
  badge.classList.add('visible');
  clearTimeout(badge._t);
  badge._t = setTimeout(function() {{
    badge.textContent = 'Read-only mockup';
    badge.classList.remove('visible');
  }}, 2000);
}});
</script>

</body>
</html>
"""

# ─────────────────────────────────────────────────────────────────────────────
# Frameless template: no browser-chrome wrapper, just nav sidebar + viewport.
# Intended for embedding or opening as a full-screen standalone page.
# An "Exit Simulation" button is added at the top of the sidebar.
# ─────────────────────────────────────────────────────────────────────────────
_FRAMELESS_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Freetz-EVO — Interactive UI Preview</title>
<link rel="icon" type="image/svg+xml" href="{favicon}">
<style>
/* ── Freetz-EVO base skin ────────────────────────────────────────── */
{base_css}

/* ── Extra page styles ───────────────────────────────────────────── */
{extra_styles}

/* ── Frameless shell ─────────────────────────────────────────────── */
:root {{
  --mk-nav-w: 200px;
  --mk-nav-bg: #141929;
  --mk-chrome-border: #2e3a50;
}}
*, *::before, *::after {{ box-sizing: border-box; }}

html, body {{
  margin: 0; padding: 0;
  height: 100%; overflow: hidden;
  font-family: system-ui, -apple-system, Arial, sans-serif;
}}

.mk-content {{
  display: flex;
  height: 100vh;
  width: 100vw;
}}

/* ── Sidebar ─────────────────────────────────────────────────────── */
.mk-sidebar {{
  width: var(--mk-nav-w);
  background: var(--mk-nav-bg);
  border-right: 1px solid var(--mk-chrome-border);
  overflow-y: auto;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  padding-bottom: 8px;
}}

.mk-exit-btn {{
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(239,68,68,0.1);
  border: none;
  border-bottom: 1px solid var(--mk-chrome-border);
  color: #ef4444;
  font-size: 0.78rem;
  padding: 9px 14px;
  cursor: pointer;
  width: 100%;
  text-align: left;
  transition: background .15s;
  flex-shrink: 0;
}}
.mk-exit-btn:hover {{ background: rgba(239,68,68,0.22); color: #fca5a5; }}

.mk-sidebar-title {{
  font-size: 0.65rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: #475569;
  padding: 8px 14px 4px;
  flex-shrink: 0;
}}

.mockup-nav-list {{
  list-style: none; margin: 0; padding: 0; flex: 1;
}}
.mockup-nav-list li {{ position: relative; }}
.mockup-nav-list > li > a,
.mockup-nav-list > li > span {{
  display: block; padding: 7px 14px;
  font-size: 0.78rem; color: #94a3b8;
  text-decoration: none;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  transition: background .12s, color .12s; cursor: pointer;
}}
.mockup-nav-list > li > a:hover {{
  background: rgba(59,130,246,0.12); color: #e2e8f0;
}}
.mockup-nav-list > li > a.active {{
  background: rgba(59,130,246,0.2); color: #3b82f6; font-weight: 600;
}}
.mockup-nav-list > li .mockup-nav-unavail {{ color: #334155; cursor: default; }}
.mockup-nav-list li ul {{
  list-style: none; margin: 0; padding: 0;
  border-left: 2px solid #1e293b; margin-left: 14px;
}}
.mockup-nav-list li ul li a {{
  display: block; padding: 5px 14px;
  font-size: 0.74rem; color: #64748b;
  text-decoration: none; transition: color .12s;
}}
.mockup-nav-list li ul li a:hover {{ color: #e2e8f0; }}
.mockup-nav-list li ul li a.active {{ color: #3b82f6; font-weight: 600; }}

/* ── Viewport ────────────────────────────────────────────────────── */
.mk-viewport {{
  flex: 1;
  overflow-y: auto;
  background: var(--evo-bg, #0f172a);
  position: relative;
}}
.mockup-page {{ min-height: 100%; }}

.mk-not-captured {{
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  height: 100%; color: #334155;
  font-size: 0.9rem; gap: 8px;
}}

.mk-readonly-badge {{
  position: fixed; top: 16px; right: 16px;
  background: rgba(245,158,11,0.15);
  border: 1px solid #f59e0b; color: #f59e0b;
  border-radius: 6px; padding: 4px 12px;
  font-size: 0.7rem; pointer-events: none;
  z-index: 9999; opacity: 0; transition: opacity .3s;
}}
.mk-readonly-badge.visible {{ opacity: 1; }}

@media (max-width: 600px) {{
  .mk-sidebar {{ display: none; }}
}}
</style>
</head>
<body>

<div class="mk-content">
  <nav class="mk-sidebar" id="mk-sidebar">
    <button class="mk-exit-btn" id="mk-exit-btn"
            onclick="window.opener ? window.close() : window.history.back()"
            title="Exit mockup simulation">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
           stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
        <polyline points="15 18 9 12 15 6"/>
      </svg>
      Exit Simulation
    </button>

    <div class="mk-sidebar-title">Navigation</div>
    {nav_html}
  </nav>

  <div class="mk-viewport" id="mk-viewport">
    {page_divs}
    <div class="mk-not-captured" id="mk-not-found" style="display:none">
      <svg width="40" height="40" viewBox="0 0 24 24" fill="none"
           stroke="#334155" stroke-width="1.5" stroke-linecap="round">
        <circle cx="12" cy="12" r="10"/>
        <line x1="15" y1="9" x2="9" y2="15"/>
        <line x1="9" y1="9" x2="15" y2="15"/>
      </svg>
      Page not captured in mockup
    </div>
  </div>
</div>

<div class="mk-readonly-badge" id="mk-readonly-badge">Read-only mockup</div>

<script>
var PAGES_INDEX = {pages_index};
var pageIds = Object.keys(PAGES_INDEX);
var currentIdx = 0;

function _safeId(pid) {{
  return pid.replace(/[^a-zA-Z0-9_-]/g, '_');
}}

function _showPage(idx) {{
  if (idx < 0 || idx >= pageIds.length) return;
  document.querySelectorAll('.mockup-page').forEach(function(el) {{
    el.style.display = 'none';
  }});
  document.getElementById('mk-not-found').style.display = 'none';
  var pid = pageIds[idx];
  var safe = _safeId(pid);
  var el = document.getElementById('page_' + safe);
  if (el) {{
    el.style.display = '';
    if (el.scrollTop !== undefined) el.scrollTop = 0;
  }} else {{
    document.getElementById('mk-not-found').style.display = 'flex';
  }}
  currentIdx = idx;
  document.querySelectorAll('.mockup-nav-list a').forEach(function(a) {{
    a.classList.remove('active');
  }});
  document.querySelectorAll('[data-pid="' + safe + '"]').forEach(function(a) {{
    a.classList.add('active');
  }});
}}

function mockupNavigate(url) {{
  var idx = pageIds.indexOf(url);
  if (idx >= 0) {{
    _showPage(idx);
  }} else {{
    document.querySelectorAll('.mockup-page').forEach(function(el) {{
      el.style.display = 'none';
    }});
    document.getElementById('mk-not-found').style.display = 'flex';
  }}
  var badge = document.getElementById('mk-readonly-badge');
  badge.classList.add('visible');
  clearTimeout(badge._t);
  badge._t = setTimeout(function() {{ badge.classList.remove('visible'); }}, 1500);
}}

function mockupPrev() {{
  _showPage(currentIdx - 1 < 0 ? pageIds.length - 1 : currentIdx - 1);
}}
function mockupNext() {{
  _showPage((currentIdx + 1) % pageIds.length);
}}

document.addEventListener('keydown', function(e) {{
  if (e.key === 'ArrowRight' || e.key === 'ArrowDown') mockupNext();
  if (e.key === 'ArrowLeft'  || e.key === 'ArrowUp')   mockupPrev();
}});

document.addEventListener('submit', function(e) {{
  e.preventDefault();
  var badge = document.getElementById('mk-readonly-badge');
  badge.textContent = 'Mockup: forms are disabled';
  badge.classList.add('visible');
  clearTimeout(badge._t);
  badge._t = setTimeout(function() {{
    badge.textContent = 'Read-only mockup';
    badge.classList.remove('visible');
  }}, 2000);
}});

_showPage(0);
</script>

</body>
</html>
"""


# ─── CLI Entry Point ──────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(
        description="Freetz-EVO Web UI Mockup Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--host",     default=DEFAULT_HOST,
                   help=f"Router IP (default: {DEFAULT_HOST})")
    p.add_argument("--port",     type=int, default=DEFAULT_PORT,
                   help=f"HTTP port (default: {DEFAULT_PORT})")
    p.add_argument("--user",     default=DEFAULT_USER,
                   help=f"Username (default: {DEFAULT_USER})")
    p.add_argument("--password", default=os.getenv("ROUTER_PASSWORD", ""),
                   help="Password (or set ROUTER_PASSWORD env var)")
    p.add_argument("--newlogin", action="store_true",
                   help="Use NEWLOGIN cookie auth instead of Basic Auth")
    p.add_argument("--output",   default=DEFAULT_OUTPUT,
                   help=f"Output HTML file (default: {DEFAULT_OUTPUT})")
    p.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES,
                   help=f"Maximum pages to crawl (default: {DEFAULT_MAX_PAGES})")
    p.add_argument("--depth", type=int, default=None, metavar="N",
                   help="Max link-follow depth from start URLs (default: unlimited, "
                        "bounded by --max-pages). Use 2 for two levels, 3 for three, etc.")
    p.add_argument("--extra-urls", nargs="*", default=[],
                   help="Additional CGI URLs to include (e.g. /cgi-bin/foo.cgi)")
    p.add_argument("--packages", nargs="+", default=[], metavar="PKG",
                   help="Package names to include.  For each name the generator "
                        "probes %s candidate URL patterns (conf, cgi, mww) and "
                        "adds the ones that respond with HTTP 200 to the start "
                        "URL list, so they are guaranteed to appear in the output."
                        "  Example: --packages rtorrent nginx php" % len(PKG_URL_CANDIDATES))
    p.add_argument("--packages-only", action="store_true",
                   help="When --packages is set, skip all package-specific conf pages "
                        "that do NOT belong to the listed packages.  Core system pages "
                        "(overview, webcfg, etc.) are always included.")
    p.add_argument("--timeout",  type=int, default=DEFAULT_TIMEOUT,
                   help=f"HTTP request timeout seconds (default: {DEFAULT_TIMEOUT})")
    p.add_argument("--verbose",  action="store_true",
                   help="Verbose HTTP logging")
    p.add_argument("--frameless", action="store_true",
                   help="Generate without the browser-chrome frame: output contains "
                        "only the nav sidebar + page viewport at full viewport size.  "
                        "An 'Exit Simulation' button is added to the sidebar.  "
                        "Useful for embedding in an iframe or as a standalone page.")
    return p.parse_args()


def main():
    args = parse_args()

    if not args.password:
        import getpass
        args.password = getpass.getpass(f"Password for {args.user}@{args.host}:{args.port}: ")

    print(f"\nFreetz-EVO Mockup Generator v{VERSION}")
    print(f"  Target : http://{args.host}:{args.port}")
    print(f"  Auth   : {'NEWLOGIN' if args.newlogin else 'Basic Auth'} ({args.user})")
    print(f"  Output : {args.output}")
    if args.packages:
        mode = " (packages-only)" if args.packages_only else ""
        print(f"  Pkgs   : {', '.join(args.packages)}{mode}")

    # Connect
    session = FreetzSession(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        newlogin=args.newlogin,
        timeout=args.timeout,
        verbose=args.verbose,
    )
    print("\nConnecting...")
    if not session.connect():
        sys.exit(1)

    base_url = f"http://{args.host}:{args.port}"
    inliner = AssetInliner(session, base_url)
    processor = PageProcessor(inliner)

    # ── Resolve --packages to concrete start URLs ────────────────────────────
    # For each package:
    #  1. Probe PKG_URL_CANDIDATES to find accessible entry points.
    #  2. Fetch each entry-point page and extract ALL its internal links so
    #     that sub-tabs (e.g. /cgi-bin/mod/webcfg.cgi, /cgi-bin/mod/logs.cgi)
    #     are immediately added as depth-0 start URLs — even if they are not
    #     reachable via the general BFS from the overview page.
    pkg_start_urls: list[str] = []
    if args.packages:
        print("\nResolving package URLs...")
        # Lightweight helper crawler used only for link extraction
        _helper = PageCrawler(session, inliner, processor)

        for pkg in args.packages:
            found: list[str] = []
            all_added_subs: list[str] = []
            for pattern in PKG_URL_CANDIDATES:
                candidate = pattern % pkg
                r = session.get(candidate)
                if r and r.status_code == 200 and \
                        "html" in r.headers.get("Content-Type", ""):
                    if candidate not in pkg_start_urls:
                        pkg_start_urls.append(candidate)
                    found.append(candidate)
                    # ── Pre-fetch: expand all links on this page as depth-0 ──
                    sub_links = _helper._extract_links(r.text, candidate)
                    added_subs = []
                    for lnk in sub_links:
                        if not _helper._should_skip(lnk) \
                                and lnk not in pkg_start_urls:
                            pkg_start_urls.append(lnk)
                            added_subs.append(lnk)
                            all_added_subs.append(lnk)
                    if added_subs and args.verbose:
                        for sl in added_subs:
                            print(f"    + sub-link: {sl}")
            if found:
                sub_note = f" (+{len(all_added_subs)} sub-links)" if all_added_subs else ""
                print(f"  {pkg}: " + ", ".join(found) + sub_note)
            else:
                print(f"  {pkg}: (no accessible URL found — will still try /cgi-bin/conf/{pkg})")
                pkg_start_urls.append(f"/cgi-bin/conf/{pkg}")

    crawler = PageCrawler(session, inliner, processor,
                          max_pages=args.max_pages, max_depth=args.depth,
                          pkg_filter=args.packages or None,
                          packages_only=args.packages_only)

    # Start crawl
    start_urls = ["/", "/cgi-bin/overview.cgi"] + pkg_start_urls + args.extra_urls
    crawler.crawl(start_urls)

    if not crawler.pages:
        print("\nERROR: No pages captured. Check credentials and network access.")
        sys.exit(1)

    # Build mockup
    print("\nBuilding self-contained mockup...")
    builder = MockupBuilder(session, inliner, args.output)
    html = builder.build(crawler.pages, crawler.menu_items,
                         frameless=args.frameless)

    # Save
    builder.save(html)
    print(f"\n  Pages  : {len(crawler.pages)}")
    print(f"  Assets : {len(session._asset_cache)}")
    print()
    print("  To publish to GitHub Pages, commit the output file:")
    print(f"    git add {args.output}")
    print(f"    git commit -m 'Update EVO UI mockup'")
    print(f"    git push")
    print()


if __name__ == "__main__":
    main()
