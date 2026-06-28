/* FALCON Service Worker — caché offline de la app, mosaicos del mapa y datos OSM.
   Estrategia:
   - Mosaicos (cartocdn) y datos (overpass): cache-first (sirven sin internet si ya se descargaron).
   - App + librerías: network-first con respaldo a caché (siempre fresco online, funciona offline). */
const APP_CACHE  = 'falcon-app-v1';
const TILE_CACHE = 'falcon-tiles-v1';
const DATA_CACHE = 'falcon-data-v1';
const APP_ASSETS = [
  './', './index.html', './holo-lib.js',
  'https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css',
  'https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js',
  'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js',
  'https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js',
  'https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js'
];

self.addEventListener('install', e=>{
  self.skipWaiting();
  e.waitUntil(caches.open(APP_CACHE).then(c=>Promise.all(APP_ASSETS.map(u=>c.add(u).catch(()=>{})))));
});
self.addEventListener('activate', e=>{ e.waitUntil(self.clients.claim()); });

self.addEventListener('fetch', e=>{
  if(e.request.method!=='GET') return;
  const url=e.request.url;
  // Mosaicos del mapa -> cache-first
  if(/basemaps\.cartocdn\.com/.test(url)){
    e.respondWith(caches.open(TILE_CACHE).then(c=>c.match(e.request).then(hit=>
      hit || fetch(e.request).then(r=>{ if(r&&r.ok) c.put(e.request,r.clone()); return r; }))));
    return;
  }
  // Datos OSM (líneas/torres) -> cache-first, con respaldo vacío si offline y no hay caché
  if(/overpass-api\.de/.test(url)){
    e.respondWith(caches.open(DATA_CACHE).then(c=>c.match(e.request).then(hit=>
      hit || fetch(e.request).then(r=>{ if(r&&r.ok) c.put(e.request,r.clone()); return r; })
        .catch(()=> hit || new Response('{"elements":[]}',{headers:{'Content-Type':'application/json'}})))));
    return;
  }
  // App + librerías -> network-first, respaldo a caché
  e.respondWith(
    fetch(e.request).then(r=>{ if(r&&r.ok){ const cc=r.clone(); caches.open(APP_CACHE).then(c=>c.put(e.request,cc)); } return r; })
      .catch(()=> caches.match(e.request).then(r=> r || (e.request.mode==='navigate' ? caches.match('./index.html') : undefined)))
  );
});
