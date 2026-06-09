import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    // The only chunk above the default 500 KB warning is vendor-hls — a
    // single, lazy-loaded library (hls.js) that can't be split further and
    // only downloads when the user opens the player.
    chunkSizeWarningLimit: 550,
    // Vendor chunk splitting (rolldown's codeSplitting — the Vite 8 equivalent
    // of rollup's manualChunks). Each group becomes a stable, separately-cached
    // chunk, so editing app code doesn't invalidate the heavy vendor downloads
    // in returning visitors' browser caches.
    //
    // Priorities: more specific groups win over the generic node_modules
    // catch-all. Regexes use [\\/] so they match both / and \ path separators.
    rolldownOptions: {
      output: {
        codeSplitting: {
          groups: [
            {
              // React core — changes only on framework upgrades.
              name: 'vendor-react',
              test: /node_modules[\\/](react|react-dom|scheduler)[\\/]/,
              priority: 50,
            },
            {
              // Router — separate from React core to keep each chunk under
              // the ~250 KB budget (react-dom alone is ~190 KB minified).
              name: 'vendor-router',
              test: /node_modules[\\/](react-router|react-router-dom)[\\/]/,
              priority: 40,
            },
            {
              // hls.js is ~500 KB minified and only needed by the /watch
              // player. Splitting it out keeps the Watch page chunk tiny and
              // lets the player vendor code stay cached across app deploys.
              name: 'vendor-hls',
              test: /node_modules[\\/]hls\.js[\\/]/,
              priority: 30,
            },
            {
              name: 'vendor-motion',
              test: /node_modules[\\/](framer-motion|motion-dom|motion-utils)[\\/]/,
              priority: 30,
            },
            {
              name: 'vendor-i18n',
              test: /node_modules[\\/](i18next|react-i18next|i18next-browser-languagedetector)[\\/]/,
              priority: 30,
            },
            {
              // Everything else from node_modules (axios, zustand, tanstack
              // query, lucide icons, ...) — one misc vendor chunk.
              name: 'vendor-misc',
              test: /node_modules[\\/]/,
              priority: 10,
            },
          ],
        },
      },
    },
  },
  server: {
    proxy: {
      // Proxy /v1/* to the FastAPI backend so we don't fight CORS in dev
      '/v1': 'http://localhost:8000',
      '/healthz': 'http://localhost:8000',
      '/readyz': 'http://localhost:8000',
    },
  },
})
