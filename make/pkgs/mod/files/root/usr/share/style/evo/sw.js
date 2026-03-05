/* Freetz-EVO Service Worker — minimal, network-first strategy
 * Scope limited to /style/evo/ unless Service-Worker-Allowed: / header is set.
 * Caches static skin assets (CSS, SVG, JSON) for faster repeat loads.
 * All other requests (CGI pages) pass through to network unchanged.
 */
var CACHE = 'freetz-evo-v3';
var OFFLINE_URL = '/style/evo/offline.html';
var STATIC = [
  '/style/evo/base.css',
  '/style/evo/icon.svg',
  '/style/evo/icon-120.png',
  '/style/evo/icon-152.png',
  '/style/evo/icon-180.png',
  '/style/evo/icon-192.png',
  '/style/evo/icon-512.png',
  '/style/evo/manifest.json',
  OFFLINE_URL
];

/* Install: pre-cache static assets */
self.addEventListener('install', function (ev) {
  ev.waitUntil(
    caches.open(CACHE).then(function (c) {
      return c.addAll(STATIC);
    }).catch(function () { /* ignore fetch errors during install */ })
  );
  self.skipWaiting();
});

/* Activate: delete old caches */
self.addEventListener('activate', function (ev) {
  ev.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(
        keys.filter(function (k) { return k !== CACHE; })
            .map(function (k) { return caches.delete(k); })
      );
    })
  );
  self.clients.claim();
});

/* Fetch: cache-first for static assets, network-first for everything else */
self.addEventListener('fetch', function (ev) {
  var req = ev.request;
  /* Only handle GET requests */
  if (req.method !== 'GET') return;

  var url = req.url;
  /* Cache-first for known static skin files */
  var isStatic = STATIC.some(function (p) { return url.indexOf(p) !== -1; });
  if (isStatic) {
    ev.respondWith(
      caches.match(req).then(function (cached) {
        return cached || fetch(req).then(function (resp) {
          if (resp && resp.status === 200) {
            var clone = resp.clone();
            caches.open(CACHE).then(function (c) { c.put(req, clone); });
          }
          return resp;
        });
      })
    );
    return;
  }

  /* Network-first for all other requests (CGI pages are always dynamic) */
  ev.respondWith(
    fetch(req).catch(function () {
      return caches.match(req).then(function (cached) {
        if (cached) return cached;
        /* For navigation requests, serve the offline fallback page */
        if (req.mode === 'navigate') {
          return caches.match(OFFLINE_URL);
        }
      });
    })
  );
});
