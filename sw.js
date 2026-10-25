// La lista de supuestos se lee de supuestos-datos.js (el mismo archivo que pinta el menú):
// dar de alta un supuesto ahí basta para que funcione sin conexión. Si ese archivo cambia,
// el navegador detecta una versión nueva de este service worker por sí solo.
importScripts("datos/supuestos-datos.js");
const VERSION = "v26";
const CACHE = "supuestos-c1-" + VERSION;
const PRECACHE_BASE = [
  "./",
  "index.html",
  "manifest.webmanifest",
  "css/tema-menu.css",
  "css/tema-resultados.css",
  "css/base-supuesto.css",
  "css/tema-supuesto.css",
  "js/prefs.js",
  "config/telemetria-config.js",
  "js/app-telemetria.js",
  "js/app-uso.js",
  "js/app-subrayado.js",
  "css/subrayado.css",
  "js/app-estudio.js",
  "js/app-sync.js",
  "config/sync-config.js",
  "datos/normas-datos.js",
  "mi-estudio.html",
  "privacidad.html",
  "js/pwa.js",
  "js/app-menu.js",
  "js/app-supuesto.js",
  "datos/supuestos-datos.js",
  "fuentes/fuentes.css",
  "fuentes/caveat-normal-500-latin-ext.woff2",
  "fuentes/caveat-normal-500-latin.woff2",
  "fuentes/jetbrains-mono-normal-400-latin-ext.woff2",
  "fuentes/jetbrains-mono-normal-400-latin.woff2",
  "fuentes/playfair-display-italic-400-latin-ext.woff2",
  "fuentes/playfair-display-italic-400-latin.woff2",
  "fuentes/playfair-display-normal-400-latin-ext.woff2",
  "fuentes/playfair-display-normal-400-latin.woff2",
  "fuentes/source-serif-4-italic-300-latin-ext.woff2",
  "fuentes/source-serif-4-italic-300-latin.woff2",
  "fuentes/source-serif-4-normal-300-latin-ext.woff2",
  "fuentes/source-serif-4-normal-300-latin.woff2",
  "fuentes/public-sans-latin-1.woff2",
  "fuentes/public-sans-latin-3.woff2",
  "fuentes/public-sans-latin-ext-0.woff2",
  "fuentes/public-sans-latin-ext-2.woff2",
  "icons/icon-192.png",
  "icons/icon-512.png",
  "resultados/resultados.html"
];
const PRECACHE = PRECACHE_BASE.concat(
  (self.SUPUESTOS_DATOS && self.SUPUESTOS_DATOS.lista || []).map(it => "supuestos/" + it.archivo + ".html")
);

self.addEventListener("install", e => {
  // Primera instalación: se activa ya. Si había una versión anterior, espera a
  // que la persona pulse «Actualizar» (ver pwa.js) para no cambiar nada a mitad de un examen.
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(PRECACHE)).then(() => {
    if (!self.registration.active) self.skipWaiting();
  }));
});

self.addEventListener("message", e => {
  if (e.data === "SKIP_WAITING") self.skipWaiting();
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k.startsWith("supuestos-c1-") && k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

// Stale-while-revalidate: responde desde caché y actualiza en segundo plano.
self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET" || !req.url.startsWith("http")) return;
  // Datos en vivo de otros sitios (API de Google Drive, hoja de resultados…): siempre de la red,
  // nunca de la caché, para no servir copias antiguas. Solo se guardan las imágenes externas (logotipo).
  if (new URL(req.url).origin !== self.location.origin && req.destination !== "image") return;
  e.respondWith(
    caches.open(CACHE).then(cache =>
      cache.match(req, { ignoreSearch: true }).then(hit => {
        const net = fetch(req).then(res => {
          if (res && (res.ok || res.type === "opaque")) cache.put(req, res.clone());
          return res;
        }).catch(() => hit || (req.mode === "navigate" ? cache.match("index.html") : undefined));
        return hit || net;
      })
    )
  );
});
