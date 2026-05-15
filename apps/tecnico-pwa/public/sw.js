const CACHE = 'tecnico-pwa-v3'
const STATIC_CACHE = 'tecnico-pwa-static-v3'

self.addEventListener('install', (e) => {
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
            if (res.ok) {
              const clone = res.clone()  // clone synchronously before body is consumed
              cache.put(req, clone)
            }
            return res
          })
        })
      )
    )
    return
  }

  // HTML and everything else: network-first, cache only for offline fallback
  e.respondWith(
    fetch(req)
      .then((res) => {
        if (res.ok && res.type === 'basic') {
          const clone = res.clone()  // clone synchronously before body is consumed
          caches.open(CACHE).then((c) => c.put(req, clone))
        }
        return res
      })
      .catch(() => caches.match(req))
  )
})
