/* Service worker : fait fonctionner l'appli hors-ligne. */
const V = "fa-v4";
const SHELL = ["/", "/signaler/", "/suivi/", "/urgences/", "/manifest.webmanifest",
  "/static/core/app.css", "/static/core/app.js", "/static/core/home.js", "/static/core/report.js",
  "/static/core/track.js", "/static/core/alert.js", "/static/core/urgences.js", "/static/core/icon-192.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(V).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== V).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", (e) => {
  const req = e.request, url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== location.origin) return;
  // Suivi de dossier, admin, fichiers privés : JAMAIS mis en cache (vie privée).
  if (url.pathname.startsWith("/api/reports/") || url.pathname.startsWith("/admin") || url.pathname.startsWith("/protected-media")) return;
  // Alertes et prix : réseau d'abord, copie en secours.
  if (url.pathname.startsWith("/api/")) {
    e.respondWith(fetch(req).then((r) => { const c = r.clone(); caches.open(V).then((x) => x.put(req, c)); return r; })
      .catch(() => caches.match(req)));
    return;
  }
  // Pages et fichiers de l'appli : copie d'abord, mise à jour en arrière-plan.
  e.respondWith(caches.match(req, { ignoreSearch: true }).then((hit) => {
    const net = fetch(req).then((r) => { if (r.ok) { const c = r.clone(); caches.open(V).then((x) => x.put(req, c)); } return r; }).catch(() => hit || caches.match("/"));
    return hit || net;
  }));
});
