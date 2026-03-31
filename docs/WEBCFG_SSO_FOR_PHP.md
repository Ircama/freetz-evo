# WebCFG SSO for PHP Apps (elFinder, ruTorrent, AriaNg)

This document describes how to reuse Freetz-EVO WebCFG authentication in php-cgi web apps.

## Goal

- Respect `MOD_HTTPD_NEWLOGIN` mode (form login + SID session cookie).
- Keep compatibility with legacy Basic Authentication mode.
- Avoid auth loops and partial page loads.
- Return users to the app page after login.

## WebCFG Authentication Modes

WebCFG supports two modes from `mod.cfg`:

- `MOD_HTTPD_NEWLOGIN='yes'`: form-based login with SID cookie and `/tmp/<SID>.webcfg` session file.
- `MOD_HTTPD_NEWLOGIN!='yes'`: legacy Basic Auth.

### Authentication settings page

UI page: `/cgi-bin/conf/mod/webcfg`

Relevant checkboxes/fields:

- `Form-based login with session cookie`: enables NEWLOGIN (replaces Basic Auth dialog).
- `Session inactivity timeout`: number of idle seconds before session expires.
- `Themed login page`: skin-styled login form (depends on NEWLOGIN).
- `Do not persist session cookie`: cookie expires when browser closes.

## Shared PHP Helper

Helper file:

- `make/pkgs/mod/files/root/usr/lib/php/webcfg_auth.php`

What it does:

- Loads WebCFG config values from default and saved config paths.
- If NEWLOGIN is active:
  - validates `SID` cookie format;
  - validates `/tmp/<SID>.webcfg` presence and timeout;
  - refreshes session timestamp with `touch`.
- If NEWLOGIN is not active:
  - enforces legacy Basic Auth against `MOD_HTTPD_USER` and `MOD_HTTPD_PASSWD`.

Main function:

- `webcfg_require_auth(array $options)`

Options:

- `mode`: `redirect` or `json`.
- `subpage`: target app path (ex: `elfinder/`, `rutorrent/`).
- `login_url` (optional): explicit login redirect URL.

## Integration Pattern

1. Detect helper path:
   - `/usr/lib/php/webcfg_auth.php`
   - fallback `/mod/external/usr/lib/php/webcfg_auth.php`
2. `require_once` helper if present.
3. Call `webcfg_require_auth()` early in each app PHP entrypoint.
4. Use fixed app `subpage` and explicit `login_url` to prevent redirect loops.

Recommended values:

- elFinder:
  - `subpage = 'elfinder/'`
  - `login_url = '/cgi-bin/conf/elfinder?subpage=elfinder/'`
- ruTorrent:
  - `subpage = 'rutorrent/'`
  - `login_url = '/cgi-bin/conf/rtorrent?subpage=rutorrent/'`
- AriaNg:
  - `subpage = 'ariang/'`
  - `login_url = '/cgi-bin/conf/aria2?subpage=ariang/'`

## elFinder Strategy

### Backend gate

`php/connector.php` enforces auth with `mode='json'` and exposes `cmd=auth_ping`.

### Frontend guard

`index.html` performs preflight call to `auth_ping` before booting UI.

Rules:

- If `auth_ping` is not successful: save hash and redirect to login URL.
- Do not depend on reading SID from `document.cookie` (SID is HttpOnly).
- Keep bootstrap resilient: avoid optional CGI calls that can return login HTML instead of JSON in some browsers.

## ruTorrent Strategy

Auth helper is loaded in ruTorrent PHP entrypoints:

- `conf/freetz_config.php`
- `conf/freetz_config.php.template`
- `rtorrent_xmlrpc_proxy.php`
- `php-info.php`

All use fixed subpage/login_url values to avoid loops.

## AriaNg Strategy

AriaNg is a pure static SPA (no PHP backend), so the approach differs from
elFinder and ruTorrent. A dedicated PHP gateway file and a JS preflight block
injected into the minified `index.html` at build time are used instead.

### PHP gateway

`make/pkgs/ariang/files/root/usr/mww/ariang/ariang_auth.php` is copied to
`/usr/mww/ariang/ariang_auth.php` during the build.

- Always uses `mode='json'` so the JS XHR caller gets a status code instead of
  a Location redirect.
- When SSO is active and the session is missing, returns HTTP 403 + JSON:
  `{"error":"...","auth_required":true,"login_url":"/cgi-bin/conf/aria2?subpage=ariang/"}`.
- When SSO is disabled or session is valid, returns HTTP 200 + JSON:
  `{"success":true,"authenticated":true}`.
- When `webcfg_auth.php` is absent (no SSO configured), always returns 200 OK.

### JS preflight injection

`make/pkgs/ariang/files/ariang_sso_snippet.html` contains an inline `<script>`
block.  The build helper `make/pkgs/ariang/files/inject_sso.py` inserts it into
`index.html` immediately before the first `<script src="js/jquery-...">` tag so
that it executes synchronously before AngularJS bootstraps.

The script:

1. Restores the URL hash saved in localStorage before the last login redirect.
2. Makes a synchronous XHR to `/ariang/ariang_auth.php?auth_ping=1`.
3. If the response is 403/401 with `auth_required: true`:
   - saves the current hash to localStorage;
   - redirects to `login_url` from the JSON response (falls back to
     `/cgi-bin/conf/aria2?subpage=ariang/`).
4. On any other response (200, 404, network error) the page loads normally
   (SSO not enforced — covers non-Freetz-EVO environments).

### Build integration

`ariang.mk` `.compiled` step:

```makefile
cp $(ARIANG_MAKE_DIR)/files/root/usr/mww/ariang/ariang_auth.php \
    $(ARIANG_DEST_DIR)/usr/mww/ariang/ariang_auth.php
python3 $(ARIANG_MAKE_DIR)/files/inject_sso.py \
    $(ARIANG_MAKE_DIR)/files/ariang_sso_snippet.html \
    $(ARIANG_DEST_DIR)/usr/mww/ariang/index.html
```

## Common Pitfalls

1. Checking SID in JavaScript (`document.cookie`) fails with HttpOnly cookies.
2. Returning login URL based on connector request URI can redirect to raw JSON endpoint.
3. Optional CGI AJAX calls during bootstrap can return login HTML and break parsing.
4. Deploying app code without deploying helper file leaves backend unprotected.

## Deployment Notes

- `deploy-elfinder.sh` should deploy `webcfg_auth.php` to:
  - `/mod/external/usr/lib/php/webcfg_auth.php`
- For ruTorrent dev deployment, update files under:
  - `/mod/external/usr/mww/rutorrent/...`
- For AriaNg dev deployment, copy directly to:
  - `/mod/external/usr/mww/ariang/ariang_auth.php`
  - Re-run `inject_sso.py` on `/mod/external/usr/mww/ariang/index.html`

## Validation Checklist

Anonymous browser:

1. Open app URL.
2. Expect redirect/login form.
3. After login, app opens (and deep-link hash is restored when applicable).

Authenticated browser:

1. Refresh app page.
2. No auth popup/loop.
3. Core backend requests do not return 403.

Cookie/session checks:

1. SID cookie exists.
2. `/tmp/<SID>.webcfg` exists and mtime updates on requests.
