// Gegenereerd door build_web.py - NIET met de hand aanpassen.
// Legt de hele app in de kast zodat hij zonder bereik opent.
const CACHE = "grand-escape-2a7caa1e217d";
const ASSETS = ["./", "./index.html", "./manifest.webmanifest", "./icon-180.png", "./icon-192.png", "./icon-512.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys()
      .then(k => Promise.all(k.filter(n => n !== CACHE).map(n => caches.delete(n))))
      .then(() => self.clients.claim())
  );
});

// Eerst de kast, dan pas het netwerk. In de bergen is er geen netwerk, en
// wachten op een verbinding die er niet is duurt eindeloos.
self.addEventListener("fetch", e => {
  if (e.request.method !== "GET") return;
  e.respondWith(
    caches.match(e.request, { ignoreSearch: true }).then(hit => {
      if (hit) return hit;
      return fetch(e.request).catch(() => caches.match("./index.html"));
    })
  );
});
