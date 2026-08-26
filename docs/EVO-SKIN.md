# Freetz-EVO — Web Interface and UX

The Freetz-EVO web interface features a completely redesigned skin (the "EVO skin") that replaces the traditional Freetz layout with a fully responsive, mobile-first design. Beyond the visual overhaul, the authentication layer has been reworked with a hardened session-cookie mechanism, and a companion reverse-proxy tool (`freetz_proxy`) makes the interface accessible over HTTPS from the internet without port-forwarding.

An [interactive UI mockup](../screenshots/evo-demo.html) is available for previewing the EVO skin without a physical device.

---

## Responsive layout

The EVO skin adapts its layout to the viewport at runtime, without requiring separate mobile and desktop code paths.

**On mobile devices**, the navigation collapses to a fixed bottom bar. Sub-menus and sub-pages slide up from the bottom as a drawer, keeping the main content area unobscured and reachable with a thumb. The bottom-bar icons are large tap targets designed for one-handed use.

**On desktop and tablet**, the navigation appears as a horizontal top menu with hover dropdowns for sub-pages. An optional hamburger mode collapses the top bar into a right-side slide-in panel, useful on narrower desktop windows or when the user prefers a minimal chrome.

---

## Dark mode and per-device preferences

The EVO skin supports a **dark mode** toggle that switches the interface colour scheme without a page reload. A **page-width toggle** switches between a full-width layout (preferred on large screens) and a comfortable centred reading width.

Both the dark mode state and the page-width preference are persisted in cookies, scoped to the specific browser and device. Re-opening the browser or reloading the page restores the last-used preference automatically, so the user does not need to re-apply it after rebooting the FRITZ!Box or clearing the browser session.

---

## PWA and home-screen installation

The Freetz-EVO web interface supports being added to the home screen on Android and iOS for an app-like experience. On Android, [Samsung Internet](https://play.google.com/store/apps/details?id=com.sec.android.app.sbrowser) delivers a full Progressive Web App (PWA) installation: the interface launches in a standalone window without the browser chrome, with its own icon and splash screen.

Full PWA installation (including the browser's "Add to Home Screen with install prompt" flow) requires HTTPS. When `freetz_proxy` is configured with HTTPS (see below), the install prompt becomes available and the same HTTPS URL works via [MyFRITZ!](https://www.myfritz.net) from anywhere on the internet without port-forwarding. See [docs/mobile.md](mobile.md) for detailed setup instructions.

---

## Form-based session login

The standard Freetz authentication uses HTTP Basic Auth, which delegates credential handling to the browser's native dialog. Freetz-EVO adds a **form-based session login** mode. When the *New login with session id* option is enabled, the web interface presents a custom HTML login page instead of the browser dialog. After successful login, a session cookie is set and the browser is redirected to the requested page.

The session cookie has a configurable **inactivity timeout**: if the user closes the browser and re-opens it within the active session window, they are not forced to log in again. Once the inactivity period expires, the next page load redirects to the login form.

### Session cookie hardening

Freetz-EVO applies three security improvements to the session cookie:

**128-bit CSPRNG session ID.** The original Freetz session-cookie implementation generated the session ID by taking an MD5 hash of the login timestamp, which is predictable and trivially brute-forced. Freetz-EVO replaces this with 128 bits of randomness drawn from `/dev/urandom`, making the session ID cryptographically unpredictable.

**`HttpOnly` flag.** The cookie is issued with the `HttpOnly` attribute, which instructs the browser to withhold the cookie value from JavaScript. This prevents an XSS vulnerability from leaking the session ID even if malicious script is injected into a page.

**`SameSite=Strict` flag.** The cookie is issued with `SameSite=Strict`, which causes the browser to omit the cookie on all cross-site requests — including top-level navigations from external links, form posts from foreign origins, and cross-origin fetch/XMLHttpRequest calls. This is a complete defence against Cross-Site Request Forgery (CSRF) without requiring a separate CSRF token.

### `passwd_save.sh` bug fix

A bug in `passwd_save.sh` caused the stored password hash to include the username as a prefix (e.g., `admin$1$...` instead of `$1$...`). Any subsequent login attempt against the stored hash failed because the hash format was invalid. Freetz-EVO fixes the script so that only the bare hash is stored, making password changes work correctly.

---

## freetz_proxy — HTTPS reverse proxy

`freetz_proxy` is a lightweight CGI-based HTTPS↔HTTP reverse proxy and index gateway. It accepts HTTPS connections on a configurable port and forwards them to the Freetz HTTP interface, transparently rewriting HTML, CSS, and JavaScript URLs in the response so that all embedded resources load through the proxy rather than directly from the HTTP interface.

The proxy also handles **CDN proxying**: embedded resources that would ordinarily load from external CDN URLs are rewritten to load through the proxy, keeping everything within the FRITZ!Box domain and avoiding browser mixed-content warnings.

When `freetz_proxy` is installed, the Fritz logo and the AVM user menu in the FRITZ!Box UI gain direct links to the Freetz menus through the proxy — so the user can reach the Freetz interface from the standard AVM interface without manually constructing the URL.

The HTTPS URL exposed by `freetz_proxy` is accessible via **MyFRITZ!** (`*.myfritz.net`), giving remote access to the full Freetz interface from anywhere on the internet without configuring port-forwarding on the FRITZ!Box. Combined with PWA support, this means the Freetz interface can be installed as a home-screen app and used remotely over a secure connection.
