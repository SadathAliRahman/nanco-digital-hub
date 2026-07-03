const CACHE_NAME = 'nanco-pwa-cache-v6';
const ASSETS = [
  './',
  './index.html',
  './style.css',
  './assets/light-logo.png',
  './assets/dark-logo.png',
  './assets/logo.png'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(ASSETS);
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cache => {
          if (cache !== CACHE_NAME) {
            return caches.delete(cache);
          }
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  // Only handle GET requests for caching. Non-GET requests (POST, PUT, DELETE) 
  // cannot be cached and attempting to cache them throws errors.
  if (event.request.method !== 'GET') {
    return;
  }

  // Network-First Strategy: Always try fetching from the network first
  event.respondWith(
    fetch(event.request).then(networkResponse => {
      // 206 Partial Content is returned for range requests (streaming videos).
      // The Cache Storage API does not support caching partial responses.
      if (networkResponse.status === 206) {
        return networkResponse;
      }
      return caches.open(CACHE_NAME).then(cache => {
        // Only cache valid responses (not browser extensions or failed requests)
        if (event.request.url.startsWith('http') && networkResponse.ok) {
            cache.put(event.request, networkResponse.clone());
        }
        return networkResponse;
      });
    }).catch(() => {
      // Fallback to cache if offline
      return caches.match(event.request).then(cachedResponse => {
        if (cachedResponse) {
          return cachedResponse;
        }
        // Return a valid fallback Response to prevent "Failed to convert value to Response"
        return new Response('Offline and resource not cached.', {
          status: 503,
          statusText: 'Service Unavailable',
          headers: { 'Content-Type': 'text/plain' }
        });
      });
    })
  );
});
