# freetz-proxy 0.1 - HTTPS multi-service reverse proxy CGI
  - Package: [master/make/pkgs/freetz-proxy/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/freetz-proxy/)
  - Maintainer: -


`freetz_proxy` is a static CGI binary that runs inside the FritzBox's built-in HTTPS server and acts as a configurable reverse-proxy gateway for all Freetz services.

**Entry point:** `https://fritz.box/cgi-bin/freetz_proxy`

When called without parameters it renders an **index page** listing all configured services with their live links. When called with `?service=NAME` it proxies the request to the corresponding upstream HTTP port on `127.0.0.1`.

## Configuration

`/mod/etc/conf/freetz-proxy.cfg` (one service per line):

```
# name=port[:path[:direct]]
freetz=81
rtorrent=81:/cgi-bin/conf/rtorrent
rutorrent=81:/rutorrent/:direct
ttyd=7681::direct
```

Lines marked `direct` are shown as plain HTTP links on the index page (for WebSocket apps or UIs that cannot be proxied). Omitting the `freetz` entry causes the proxy to read the port from `/mod/etc/conf/mod.cfg` automatically.

## URL rewriting

When proxying an HTML/CSS/JS response the proxy transparently rewrites:

- Absolute HTTPS CDN URLs → `?service=cdn&url=<encoded>` (CDN proxy sub-service)
- HTML `src=` / `href=` absolute paths → `?service=NAME&path=<encoded>`
- CSS `url(…)` absolute and relative paths
- HTML `<meta http-equiv="refresh">` `content="…;url=/…"`
- JavaScript navigation assignments: `navigate('/')`, `location.href = '/'`
- JavaScript object-literal URL properties: `cgiUrl: '/cgi-bin/…'`
- ACE editor CDN module paths (basePath, modePath, themePath, workerPath) via injected `ace.config.set()` calls

Backtick template literals (`` ` ``) are intentionally **not** rewritten, so JS code that must preserve a literal path string should use backticks instead of single or double quotes.

## Wildcard path rules

Path rules in `freetz-proxy.cfg` support `fnmatch(3)` glob patterns (`*`, `?`, `[...]`). This allows a single service entry to cover multiple sub-paths without duplicating lines.

## CDN proxying

When the browser requests a CDN resource (e.g. an ACE editor worker script loaded from `cdn.jsdelivr.net`), the proxy fetches it server-side and streams it back to the browser, so all content is served over the same HTTPS origin without mixed-content warnings.

## Internet access and AVM webif integration

Because `freetz_proxy` runs as a standard CGI inside the FritzBox's own HTTPS server (port 443), it is accessible via **MyFRITZ!** and from the internet through the FritzBox's built-in remote-access gateway — no port-forwarding or extra VPN required.
Authentication is handled by the existing FritzBox session mechanism before the CGI is reached, so Freetz itself remains protected.

When `freetz_proxy` is included in the firmware, the build system also patches the AVM web-interface (`content.lua`) to improve discoverability:

- **Fritz logo link**: the AVM Fritz logo (top-left, with Freetz-EVO overlay) becomes a hyperlink to `https://fritz.box/cgi-bin/freetz_proxy`, giving one-click access to the proxy index from any page.
- **User menu entry**: a *Freetz* entry is appended to the AVM user menu (the ⊙ icon, top-right), providing a direct shortcut alongside the built-in FritzBox menu items.

Both additions are build-time patches to `content.lua` and require no additional packages or configuration.

## Debug mode

Create `/tmp/freetz_proxy_debug` on the device to enable request/response tracing to `/tmp/freetz_proxy.log`. Remove the file to silence it.

```sh
touch /tmp/freetz_proxy_debug          # enable
tail -f /tmp/freetz_proxy.log          # follow live
rm /tmp/freetz_proxy_debug             # disable
```
