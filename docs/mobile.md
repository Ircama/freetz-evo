# Freetz-EVO on Mobile Devices

## Using Freetz-EVO as a mobile app

The Freetz-EVO web interface is fully responsive and designed to work comfortably on smartphones and tablets. The navigation adapts to a fixed bottom bar with a slide-up drawer, dark mode is available, and the layout is touch-friendly throughout.

### Saving to the home screen (Android / iOS)

The simplest way to get an app-like experience is to save the Freetz-EVO page to your device's home screen directly from your browser:

- **Android (Chrome, Firefox, Samsung Internet)**: open the page, tap the browser menu (⋮), then *Add to Home Screen* / *Install app*
- **iOS (Safari)**: open the page, tap the share icon (□↑), then *Add to Home Screen*

The Freetz-EVO skin ships a `manifest.json`, themed icons (192×192 and larger), and the necessary `<meta>` tags (`mobile-web-app-capable`, `apple-mobile-web-app-capable`, `theme-color`) so the browser will present the full install prompt.

### Best experience: Samsung Internet Mobile Browser

Among Android browsers, **Samsung Internet** (available on Google Play for all Android devices, not only Samsung) delivers the closest experience to a native PWA:

- The address bar and navigation chrome fully hide when launched from the home screen icon
- The bottom navigation bar of Freetz-EVO integrates naturally with the gesture navigation of modern Android
- The status-bar color matches the Freetz-EVO theme (blue for light mode, dark for dark mode)

The result is indistinguishable from a natively installed Progressive Web App.

### Full PWA installation via HTTPS (freetz_proxy)

PWA installation (with service worker and offline support) requires HTTPS with a valid certificate. This can be achieved using **freetz_proxy** combined with the FritzBox's built-in HTTPS server:

1. Ensure the `freetz_proxy` package is installed and configured (see [docs/make/freetz-proxy.md](make/freetz-proxy.md)).
2. Access Freetz-EVO via the proxy URL:
   ```
   https://fritz.box/cgi-bin/freetz_proxy?service=freetz
   ```
   This is served over the FritzBox's own trusted HTTPS certificate.
3. From this HTTPS URL, Chrome/Samsung Internet will offer a full *Install app* prompt and register the service worker.
4. The same HTTPS URL is also reachable externally via **MyFRITZ!**, so the app works both at home and on mobile data without any port-forwarding or separate VPN setup.

> **Note**: without HTTPS (i.e. accessing `http://fritz.box:81/`) the browser can still add the page to the home screen, but the installation will not use a service worker — it behaves as a simple shortcut. The user experience is still good; the only difference is no offline fallback.

### Access from the internet

Because `freetz_proxy` runs inside the FritzBox HTTPS CGI infrastructure it is protected by FritzBox authentication and reachable via MyFRITZ! (`https://<boxid>.myfritz.net/cgi-bin/freetz_proxy`). No extra port-forwarding is needed.
