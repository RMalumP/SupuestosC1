const VERSION = "v10";
const CACHE = "supuestos-c1-" + VERSION;
const PRECACHE = [
  "./",
  "index.html",
  "manifest.webmanifest",
  "tema-menu.css",
  "tema-resultados.css",
  "base-supuesto.css",
  "tema-supuesto.css",
  "prefs.js",
  "telemetria-config.js",
  "app-telemetria.js",
  "pwa.js",
  "app-menu.js",
  "app-supuesto.js",
  "supuestos-datos.js",
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
  "resultados/resultados.html",
  "supuestos/supuesto_0.html",
  "supuestos/supuesto_1.html",
  "supuestos/supuesto_1I.html",
  "supuestos/supuesto_2.html",
  "supuestos/supuesto_2I.html",
  "supuestos/supuesto_3.html",
  "supuestos/supuesto_EX03E.html",
  "supuestos/supuesto_T2.html",
  "supuestos/supuesto_T2I.html"
];

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
