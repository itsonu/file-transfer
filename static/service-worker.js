self.addEventListener('install', function (event) {
    event.waitUntil(
        caches.open('your-app-cache').then(function (cache) {
            return cache.addAll([
                '/',
                '/static/style.css',
                '/static/android/android-launchericon-192-192.png',
                '/static/android/android-launchericon-512-512.png'
            ]);
        })
    );
});

self.addEventListener('fetch', function (event) {
    event.respondWith(
        caches.match(event.request).then(function (response) {
            return response || fetch(event.request);
        })
    );
});
