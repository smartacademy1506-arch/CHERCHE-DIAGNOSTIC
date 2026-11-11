// Service worker : met en cache la coquille de l'application pour un démarrage hors ligne.
// Les données (Supabase) ne passent pas par ce cache : elles sont gérées dans IndexedDB par l'application.
const VERSION = '__APP_VERSION__';
const CACHE = `cd-shell-${VERSION}`;
const SHELL = ['/', '/index.html', '/assets/app.js', '/assets/app.css', '/icon.svg', '/icon-192.png', '/icon-512.png', '/manifest.webmanifest'];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k.startsWith('cd-shell-') && k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  const url = new URL(req.url);
  if (req.method !== 'GET' || url.origin !== self.location.origin || url.pathname.startsWith('/api/')) return;
  // Réseau d'abord (pour recevoir les mises à jour), cache en secours.
  event.respondWith(
    fetch(req).then((res) => {
      if (res.ok) { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(req, copy)); }
      return res;
    }).catch(() => caches.match(req).then((hit) => hit || caches.match('/index.html'))),
  );
});
