import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'apple-touch-icon.png', 'masked-icon.svg'],
      manifest: {
        name: 'Krishi Bondhu - Smart Farming Assistant',
        short_name: 'KrishiBondhu',
        description: 'AI-powered agricultural assistant for farmers in Bangladesh',
        theme_color: '#2e7d32',
        background_color: '#ffffff',
        display: 'standalone',
        icons: [
          {
            src: 'pwa-192x192.png',
            sizes: '192x192',
            type: 'image/png'
          },
          {
            src: 'pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png'
          },
          {
            src: 'pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any maskable'
          }
        ]
      },
      workbox: {
        runtimeCaching: [
          {
            urlPattern: /\/api\/market\//,
            handler: 'NetworkFirst',
            options: { cacheName: 'market-api', expiration: { maxEntries: 50, maxAgeSeconds: 3600 } }
          },
          {
            urlPattern: /\/api\/alerts\//,
            handler: 'NetworkFirst',
            options: { cacheName: 'alerts-api', expiration: { maxEntries: 20, maxAgeSeconds: 1800 } }
          },
          {
            urlPattern: /\/api\//,
            handler: 'NetworkFirst',
            options: { cacheName: 'api-cache', expiration: { maxEntries: 100, maxAgeSeconds: 600 } }
          },
          {
            urlPattern: /\.(png|jpg|jpeg|svg|gif|webp)$/,
            handler: 'CacheFirst',
            options: { cacheName: 'image-cache', expiration: { maxEntries: 60, maxAgeSeconds: 86400 * 30 } }
          }
        ]
      },
      devOptions: {
        enabled: true
      }
    })
  ],
  server: {
    port: 5173,
    host: true
  },
  build: {
    assetsInlineLimit: 0
  }
})