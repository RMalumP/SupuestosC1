const VERSION = "v2";
const CACHE = "supuestos-c1-" + VERSION;
const PRECACHE = [
  "./",
  "index.html",
  "manifest.webmanifest",
  "tema-menu.css",
  "tema-supuesto.css",
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
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(PRECACHE)).then(() => self.skipWaiting()));
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
