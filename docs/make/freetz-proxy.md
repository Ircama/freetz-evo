# freetz-proxy 0.1 - HTTPS multi-service reverse proxy CGI
  - Package: [master/make/pkgs/freetz-proxy/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/freetz-proxy/)
  - Maintainer: -


`freetz_proxy` is a static CGI binary that runs inside the FritzBox's built-in HTTPS server (port 443) and acts as a configurable reverse-proxy gateway for all Freetz services.

**Entry point:** `https://fritz.box/cgi-bin/freetz_proxy`

When called without parameters it renders an **index page** listing all configured services with their live links. When called with `?service=NAME` it proxies the request to the corresponding upstream HTTP port on `127.0.0.1`.

The key use-case is enabling **PWA (Progressive Web App) installation** and providing **secure remote access** to Freetz services via MyFRITZ! — without port-forwarding, VPN, or extra certificates. Because the proxy runs inside the FritzBox's native HTTPS entry-point, all AVM authentication and TLS termination are handled transparently before the CGI is invoked.

---

## How it works

```
Browser (HTTPS/443)
  └─→ AVM websrv CGI handler
       └─→ freetz_proxy (CGI binary)
            └─→ upstream HTTP service on 127.0.0.1:PORT
                 e.g. Freetz httpd on :81, ttyd on :7681, …
```

1. The browser opens `https://fritz.box/cgi-bin/freetz_proxy?service=freetz&path=/cgi-bin/conf/rtorrent`.
2. The binary connects to `127.0.0.1:81`, forwards the request, reads the response, rewrites all absolute URLs in the returned HTML/CSS/JS so that further requests go back through the proxy, then streams the rewritten body to the browser.
3. Static CDN resources (`script src="https://cdn..."`) are also proxied server-side so that AVM's Content-Security-Policy (`script-src 'self'`) is satisfied.

**Direct services** skip proxying entirely: the index page renders a plain `http://fritz.box:PORT/path` link, suitable for WebSocket apps (ttyd, ruTorrent) that cannot be proxied at the HTTP level.

---

## Configuration file

The proxy reads its configuration from the first readable file in the following order:

1. `/tmp/flash/mod/freetz-proxy.cfg` — NAND flash (persistent, edited via the Freetz web UI)
2. `/mod/etc/conf/freetz-proxy.cfg` — overlay filesystem

The active file is read at every CGI invocation; no daemon restart is needed after changes.

### Service entries

One service per line, format: **`name=port[:path[:direct]]`**

| Field | Description |
|-------|-------------|
| `name` | Service identifier (up to 63 chars). Used in the proxy URL: `?service=name`. |
| `port` | TCP port of the upstream service on `127.0.0.1`. Use `0` to auto-detect the Freetz HTTP port from `MOD_HTTPD_PORT` in `/mod/etc/conf/mod.cfg` (falls back to `81`). |
| `path` | Default upstream path (default: `/`). Used when `?path=` is not given in the request URL. |
| `direct` | Literal word `direct`. If present, the index page shows a plain `http://` link rather than routing the request through the proxy. |

Up to **32 services** can be registered.

The `freetz` service (Freetz admin UI) is **automatically added** at startup if not present in the config file, using the port from `MOD_HTTPD_PORT`.

#### Examples

```ini
# Basic: name=port
freetz=81

# With default path
rtorrent=81:/cgi-bin/conf/rtorrent

# Port 0 = auto-detect Freetz HTTP port
rtorrent=0:/cgi-bin/conf/rtorrent

# Direct HTTP link (no proxying through HTTPS)
rutorrent=81:/rutorrent/:direct
ariang=81:/ariang/:direct
ttyd=7681::direct

# Glob path pattern (fnmatch): covers /cgi-bin/conf/* without listing each CGI
freetz_cgi=81:/cgi-bin/conf/*:direct
```

#### Glob (wildcard) path patterns

Path rules support `fnmatch(3)` glob syntax (`*`, `?`, `[...]`).  
`*` does **not** cross `/` boundaries (standard shell glob behaviour).  
When multiple patterns match a URL path the one with the longest literal prefix wins.

---

### Security directives (`@key=value`)

Lines starting with `@` configure proxy security behaviour. They are not service entries. All are `yes`/`no` booleans unless noted.

#### `@disabled`

```ini
@disabled=no        # default
@disabled=yes
```

When `yes`, every request returns a static HTML notice page ("Freetz Proxy Disabled") with a link back to the Freetz settings. The proxy binary is still installed and invoked, but no upstream connections are made.

---

#### `@block_internet`

```ini
@block_internet=no  # default
@block_internet=yes
```

When `yes`, any request whose `SERVER_NAME` matches one of the patterns in `@internet_domains` is rejected with **HTTP 403 Forbidden**. Useful when you want the proxy accessible only on the LAN.

---

#### `@no_internet_cookie`

```ini
@no_internet_cookie=yes   # default
@no_internet_cookie=no
```

When `yes` (the default), `Max-Age=` and `Expires=` attributes are stripped from every `Set-Cookie` response header when the request originates from the internet (matching `@internet_domains`). Cookies become session-only and are deleted when the browser closes, reducing exposure of long-lived session tokens over external connections.

---

#### `@no_cookie`

```ini
@no_cookie=no       # default
@no_cookie=yes
```

When `yes`, `Max-Age=` and `Expires=` are stripped from **all** `Set-Cookie` headers regardless of origin (LAN or internet). Supersedes `@no_internet_cookie`.

---

#### `@internet_domains`

```ini
@internet_domains=.myfritz.net          # default
@internet_domains=.myfritz.net,.dyndns.org,.example.com
```

Comma-separated list of hostname substrings. A request is considered to come from the internet if `SERVER_NAME` contains any of these strings. Used by `@block_internet` and `@no_internet_cookie`. Up to 16 patterns, each up to 127 characters.

---

#### `@trace_file`

```ini
@trace_file=                            # default (disabled)
@trace_file=/tmp/freetz_proxy.log
```

When set to a non-empty path, every CGI invocation appends timestamped request/response trace lines to that file. Each trace line is prefixed with the Unix timestamp of the request. Logging is completely silent when the value is empty.

Enable and follow live:

```sh
# via CLI (see below)
freetz_proxy --set @trace_file=/tmp/freetz_proxy.log

# follow
tail -f /tmp/freetz_proxy.log

# disable
freetz_proxy --set @trace_file=
```

---

### Complete annotated example

```ini
# freetz-proxy.cfg
#
# ── Security ───────────────────────────────────────────────
@disabled=no
@block_internet=no
@no_internet_cookie=yes
@no_cookie=no
@internet_domains=.myfritz.net
@trace_file=

# ── Services ───────────────────────────────────────────────

# Freetz admin UI — proxied HTTPS (auto-detect port)
freetz=0

# rTorrent config CGI — proxied HTTPS
rtorrent=0:/cgi-bin/conf/rtorrent

# rTorrent config HTML editor — direct HTTP (ACE editor)
rtorrent_cfg=0:/rtorrent/rtorrent_config_editor.html:direct

# ruTorrent web UI — direct HTTP (WebSocket, heavy JS)
rutorrent=0:/rutorrent/:direct

# AriaNg web UI — direct HTTP (single-page app, heavy JS)
ariang=0:/ariang/:direct

# ttyd web terminal — direct HTTP (WebSocket required)
ttyd=7681::direct
```

---

## Command-line interface

The binary supports one command-line mode:

### `--set @key=value ...`

```sh
freetz_proxy --set @key1=value1 [@key2=value2 ...]
```

Updates one or more `@`-directive values in the active config file. Each argument must be in the form `@key=value`. Existing directives are replaced in-place; directives not yet present are appended.

The config is written to (first writable path):

1. `/tmp/flash/mod/freetz-proxy.cfg`
2. `/mod/etc/conf/freetz-proxy.cfg`

After `--set`, call `modsave flash` to persist changes to NAND.

#### Examples

```sh
# Disable the proxy temporarily
freetz_proxy --set @disabled=yes

# Re-enable
freetz_proxy --set @disabled=no

# Block access from the internet
freetz_proxy --set @block_internet=yes

# Enable debug tracing
freetz_proxy --set @trace_file=/tmp/fp.log

# Disable debug tracing
freetz_proxy --set @trace_file=

# Restrict internet-domain detection to a custom domain
freetz_proxy --set @internet_domains=.myfritz.net,.example.com

# Multiple directives in a single call
freetz_proxy --set @disabled=no @block_internet=yes @trace_file=/tmp/fp.log
```

Outside of `--set` the binary is a pure CGI and must be invoked by a web server (it reads `REQUEST_METHOD`, `QUERY_STRING`, etc. from the environment).

---

## Proxy URL scheme

| URL | Effect |
|-----|--------|
| `https://fritz.box/cgi-bin/freetz_proxy` | Renders the service index page |
| `https://fritz.box/cgi-bin/freetz_proxy?service=NAME` | Proxies to the service's default path |
| `https://fritz.box/cgi-bin/freetz_proxy?service=NAME&path=/some/path` | Proxies to the specified path |
| `https://fritz.box/cgi-bin/freetz_proxy?service=cdn&url=https%3A%2F%2F…` | Fetches an external HTTPS URL and streams it back (CDN proxy) |

---

## URL rewriting

When proxying an HTML/CSS or JavaScript response the proxy transparently rewrites:

| Original form | Rewritten to |
|---------------|--------------|
| `="https://cdn.example.com/..."` (attribute) | `="?service=cdn&url=<encoded>"` |
| `="https://..."` inside `onclick="..."` (JS string) | _left unchanged_ (navigates directly) |
| `="/absolute/path"` or `='/absolute/path'` | `="?service=NAME&path=<encoded>"` |
| `="?qs-suffix"` (query-relative) | `="?service=NAME&path=<base>%3F<qs>"` |
| `url(/path)` / `url('/path')` (CSS absolute) | `url(?service=NAME&path=<encoded>)` |
| `url(../relative.css)` (CSS relative) | resolved then rewritten as above |
| `<meta http-equiv="refresh" content="…;url=/…">` | URL portion rewritten |
| JavaScript `navigate('/')`, `location.href='/'`, etc. | path argument rewritten |
| JavaScript object literals `{ cgiUrl: '/cgi-bin/…' }` | value rewritten |
| `<link rel="manifest" …>` | **stripped** (AVM CSP blocks manifests) |
| ACE editor `basePath` / `modePath` / `themePath` / `workerPath` | `ace.config.set(…)` injected after `ace.js` `</script>` tag |

**Backtick template literals** (`` `…` ``) are intentionally **not** rewritten. Use backticks in JavaScript when a literal path must be preserved unchanged after the proxy.

---

## CDN proxying

When the browser requires a CDN resource (e.g. `<script src="https://cdn.jsdelivr.net/…/ace.js">`) the rewritten attribute becomes `src="?service=cdn&url=<encoded>"`. The proxy fetches the URL server-side using `curl` (with `--compressed`, max 30 s timeout) and streams the response back, satisfying AVM's `script-src 'self'` Content-Security-Policy without mixed-content warnings.

The `Content-Type` is inferred from the URL's file extension (`.js`, `.css`, `.html`, `.json`, `.svg`, `.png`, `.ico`, `.woff`, `.woff2`). CDN responses are cached in the browser for 24 h (`Cache-Control: public, max-age=86400`).

---

## POST / method tunnelling

AVM's `websrv` gateway rejects `POST` requests from internet (MyFRITZ!) connections. To work around this the proxy supports a GET-encoded tunnel: embed the real method and body as query parameters and the proxy decodes them before forwarding to the upstream.

| Query parameter | Description |
|-----------------|-------------|
| `_method=POST\|PUT\|PATCH\|DELETE` | Real HTTP method to use upstream |
| `_body=<url-encoded-body>` | Request body (max 4 KB decoded) |
| `_ctype=<content-type>` | `Content-Type` header (default: `application/x-www-form-urlencoded`) |

This mechanism is used transparently by the Freetz web UI JavaScript when it detects an internet origin.

---

## Internet access and AVM webif integration

Because `freetz_proxy` runs as a standard CGI inside the FritzBox's built-in HTTPS server (port 443), it is accessible via **MyFRITZ!** and from the internet through the FritzBox's built-in remote-access gateway — no port-forwarding or extra VPN required. Authentication is handled by the existing FritzBox session mechanism before the CGI is reached, so Freetz itself remains protected.

When `freetz_proxy` is included in the firmware, the build system also patches the AVM web-interface (`content.lua`) to improve discoverability:

- **Fritz logo link**: the AVM Fritz logo (top-left, with Freetz-EVO overlay) becomes a hyperlink to `https://fritz.box/cgi-bin/freetz_proxy`, giving one-click access to the proxy index from any page.
- **User menu entry**: a *Freetz* entry is appended to the AVM user menu (the ⊙ icon, top-right), providing a direct shortcut alongside the built-in FritzBox menu items.

Both additions are build-time patches to `content.lua` and require no additional packages or configuration.

---

## Debug mode

Enable trace logging by setting `@trace_file` in the config, either by editing the file directly or via the CLI:

```sh
# Enable
freetz_proxy --set @trace_file=/tmp/freetz_proxy.log

# Follow live
tail -f /tmp/freetz_proxy.log

# Disable
freetz_proxy --set @trace_file=
```

Each log entry is prefixed with a Unix timestamp. The log includes:
- Incoming request method, query string, `PATH_INFO`, `HTTP_HOST`
- All incoming `HTTP_*` headers
- Routing decision (service name, upstream port and path)
- CDN proxy requests (URL, bytes served, curl exit code)
- Redirect rewrites
- Method-tunnel decoding (`_method`, `_body` length, `_ctype`)
