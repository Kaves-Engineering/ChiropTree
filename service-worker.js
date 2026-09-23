const CACHE = 'chiroptree-core-__RELEASE__';
const CORE = [
  './', './index.html', './marine.html', './birds.html', './dinosaurs.html', './manifest.webmanifest',
  './app-install.js', './icons/icon.svg', './icons/icon-192.png',
  './icons/icon-512.png', './icons/icon-maskable-512.png',
  './icons/icon-192.png?v=cladogram-1', './icons/icon-512.png?v=cladogram-1',
  './icons/icon-maskable-512.png?v=cladogram-1',
  './data/chiroptera_taxonomy.json',
  './data/call_measurements.json',
  './data/calls/exports/calls.json',
  './data/danish_names.json', './data/gbif_country_supplement.json',
  './data/world_map.json', './data/marine_mammal_taxonomy.json',
  './data/marine_mammal_danish_names.json',
  './data/marine_mammal_gbif_country_supplement.json', './data/marine_world_map.json',
  './data/bird_taxonomy.json', './data/bird_danish_names.json',
  './data/dinosaur_taxonomy.json', './data/dinosaur_images.json',
  './data/media-manifest.json', './data/release.json'
];

async function installCore(){
  const cache = await caches.open(CACHE);
  let next = 0, failed = false;
  try {
    // Keep the complete offline library, but avoid dozens of simultaneous
    // downloads/cache writes competing with the page on a low-memory phone.
    await Promise.all([0,1].map(async()=>{
      while(!failed && next < CORE.length){
        const url = CORE[next++];
        await cache.add(url);
      }
    }));
    await self.skipWaiting();
  } catch(error) {
    failed = true;
    await caches.delete(CACHE);
    throw error;
  }
}
self.addEventListener('install', event => event.waitUntil(installCore()));

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
