const CACHE = 'chiroptree-core-__RELEASE__';
const CORE = [
  './', './index.html', './marine.html', './manifest.webmanifest',
  './data/chiroptera_taxonomy.json', './data/call-records.json',
  './data/danish_call_measurements.json',
  './data/danish_names.json', './data/gbif_country_supplement.json',
  './data/world_map.json', './data/marine_mammal_taxonomy.json',
  './data/marine_mammal_danish_names.json',
  './data/marine_mammal_gbif_country_supplement.json', './data/marine_world_map.json',
  './data/media-manifest.json', './data/release.json'
];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(CORE)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(
    keys.filter(key => key.startsWith('chiroptree-core-') && key !== CACHE).map(key => caches.delete(key))
  )).then(() => self.clients.claim()));
});

self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  const sameOrigin = new URL(event.request.url).origin === self.location.origin;
  event.respondWith(caches.match(event.request).then(cached => cached || fetch(event.request).then(response => {
    if (!sameOrigin) return response;
    const copy = response.clone();
    caches.open(CACHE).then(cache => cache.put(event.request, copy));
    return response;
  }).catch(() => event.request.mode === 'navigate' ? caches.match('./index.html') : Response.error())));
});
