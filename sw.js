// Service worker: online, every request goes to the network first (so the pages
// always show the newest data) and the response is saved. Offline, the saved
// copy is served, so the site still opens and shows the last data it loaded.
const CACHE = "job-watcher-v1";
const SHELL = [
  "./", "index.html", "browse.html", "market.html",
  "assets/style.css", "assets/common.js", "assets/charts.js", "manifest.webmanifest",
  "icons/icon-192.png", "icons/icon-512.png",
  "data/status.json", "data/history.csv",
];

self.addEventListener("install", event => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    await Promise.all(SHELL.map(url =>
      fetch(url, { cache: "no-cache" }).then(res => res.ok && cache.put(url, res)).catch(() => {})));
    self.skipWaiting();
  })());
});

self.addEventListener("activate", event => {
  event.waitUntil((async () => {
    for (const key of await caches.keys()) if (key !== CACHE) await caches.delete(key);
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", event => {
  const req = event.request;
  if (req.method !== "GET") return;
  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    try {
      const res = await fetch(req);
      if (res.ok || res.type === "opaque") cache.put(req, res.clone());
      return res;
    } catch (err) {
      const hit = await cache.match(req, { ignoreSearch: true });
      if (hit) return hit;
      if (req.mode === "navigate") return cache.match("index.html");
      throw err;
    }
  })());
});
