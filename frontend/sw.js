/* ============================================================
   PestPulse — Service Worker
   Caches app shell for offline-tolerant behavior
   ============================================================ */

const CACHE = 'pestpulse-v1';
const SHELL = [
    '/', '/farmer', '/result', '/officer',
    '/static/style.css', '/static/app.js',
    '/static/farmer.js', '/static/officer.js',
    '/static/manifest.json',
];

self.addEventListener('install', e => {
    e.waitUntil(
        caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', e => {
    e.waitUntil(
        caches.keys().then(keys =>
            Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
        ).then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', e => {
    const url = new URL(e.request.url);
    // API calls: network first, no cache
    if (url.pathname.startsWith('/api/')) {
        e.respondWith(fetch(e.request).catch(() => new Response(
            JSON.stringify({ error: 'offline', status: 'source_unavailable' }),
            { headers: { 'Content-Type': 'application/json' } }
        )));
        return;
    }
    // Shell: cache first
    e.respondWith(
        caches.match(e.request).then(cached => cached || fetch(e.request))
    );
});
