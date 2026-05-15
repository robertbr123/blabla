const CACHE = 'tecnico-pwa-v2'
const STATIC_CACHE = 'tecnico-pwa-static-v2'

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(['/'])))
  self.skipWaiting()
})

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.filter((k) => k !== CACHE && k !== STATIC_CACHE).map((k) => caches.delete(k))
      )
    )
  )
  self.clients.claim()
})

self.addEventListener('fetch', (e) => {
  const req = e.request
  if (req.method !== 'GET') return

  const url = new URL(req.url)

  // Never intercept API/auth requests
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/auth/')) return

  // _next/static chunks are content-hashed and immutable — cache-first is safe
  if (url.pathname.startsWith('/_next/static/')) {
    e.respondWith(
      caches.open(STATIC_CACHE).then((cache) =>
        cache.match(req).then((cached) => {
          if (cached) return cached
          return fetch(req).then((res) => {
            if (res.ok) cache.put(req, res.clone())
            return res
          })
        })
      )
    )
    return
  }

  // HTML navigation requests — always network-first to avoid stale chunk references
  if (req.mode === 'navigate' || req.headers.get('accept')?.includes('text/html')) {
    e.respondWith(
      fetch(req)
        .then((res) => {
          if (res.ok) {
            caches.open(CACHE).then((c) => c.put(req, res.clone()))
          }
          return res
        })
        .catch(() => caches.match(req))
    )
    return
  }

  // Everything else — network-first with cache fallback
  e.respondWith(
    fetch(req)
      .then((res) => {
        if (res.ok && res.type === 'basic') {
          caches.open(CACHE).then((c) => c.put(req, res.clone()))
        }
        return res
      })
      .catch(() => caches.match(req))
  )
})
