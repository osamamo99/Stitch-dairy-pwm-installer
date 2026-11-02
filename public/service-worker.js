/**
 * Service Worker for Number Grid Stitch Diary
 * Provides complete offline support via Cache-First strategy.
 * Preserves all local storage data without any resets.
 */

const CACHE_NAME = 'stitch-diary-v1';

// Essential local application files to precache
const ESSENTIAL_ASSETS = [
  './',
  'index.html',
  'manifest.json',
  'icon-192.png',
  'icon-512.png',
  'icon-maskable-512.png',
  'apple-touch-icon.png',
  'favicon.ico',
  'icon.svg'
];

// Install Event - Precache all essential local resources
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[Service Worker] Precaching essential application files');
      return cache.addAll(ESSENTIAL_ASSETS);
    }).then(() => {
      return self.skipWaiting();
    })
  );
});

// Activate Event - Clean up any obsolete old caches and take control
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((name) => {
          if (name !== CACHE_NAME) {
            console.log('[Service Worker] Removing old cache:', name);
            return caches.delete(name);
          }
        })
      );
    }).then(() => {
      return self.clients.claim();
    })
  );
});

// Fetch Event - Cache-First Strategy for local assets with network fallback
self.addEventListener('fetch', (event) => {
  // Only handle GET requests
  if (event.request.method !== 'GET') {
    return;
  }

  const requestUrl = new URL(event.request.url);

  // Only handle requests from the same origin
  if (requestUrl.origin !== self.location.origin) {
    return;
  }

  event.respondWith(
    caches.match(event.request, { ignoreSearch: true }).then((cachedResponse) => {
      if (cachedResponse) {
        // Return cached asset immediately for speed and offline reliability
        // Fetch in background to update cache for next time
        fetch(event.request)
          .then((networkResponse) => {
            if (networkResponse && networkResponse.status === 200 && networkResponse.type === 'basic') {
              caches.open(CACHE_NAME).then((cache) => {
                cache.put(event.request, networkResponse.clone());
              });
            }
          })
          .catch(() => {
            // Offline - ignore background update error
          });

        return cachedResponse;
      }

      // If not in cache, fetch from network and cache for offline usage
      return fetch(event.request)
        .then((networkResponse) => {
          if (!networkResponse || networkResponse.status !== 200 || networkResponse.type !== 'basic') {
            return networkResponse;
          }

          const responseToCache = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseToCache);
          });

          return networkResponse;
        })
        .catch(() => {
          // If offline and request is a page navigation, return the cached application shell
          if (event.request.mode === 'navigate') {
            return caches.match('./').then((fallback) => {
              return fallback || caches.match('index.html');
            });
          }
        });
    })
  );
});
