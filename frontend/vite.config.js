import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['pwa-192x192.png', 'pwa-512x512.png'],
      manifest: {
        name: 'কৃষি বন্ধু — Smart Farming Assistant',
        short_name: 'KrishiBondhu',
        description: 'AI-powered agricultural assistant for Bangladeshi farmers',
        theme_color: '#2D6A4F',
        background_color: '#F7F5F0',
        display: 'standalone',
        start_url: '/',
        icons: [
          { src: 'pwa-192x192.png', sizes: '192x192', type: 'image/png' },
          { src: 'pwa-512x512.png', sizes: '512x512', type: 'image/png' },
          { src: 'pwa-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'any maskable' },
        ],
      },
      workbox: {
        runtimeCaching: [
          {
            urlPattern: /\/api\/market\//,
            handler: 'NetworkFirst',
            options: { cacheName: 'market-api', expiration: { maxEntries: 50, maxAgeSeconds: 3600 } },
          },
          {
            urlPattern: /\/api\/alerts\//,
            handler: 'NetworkFirst',
            options: { cacheName: 'alerts-api', expiration: { maxEntries: 20, maxAgeSeconds: 1800 } },
          },
          {
            urlPattern: /\/api\//,
            handler: 'NetworkFirst',
            options: { cacheName: 'api-cache', expiration: { maxEntries: 100, maxAgeSeconds: 600 } },
          },
          {
            urlPattern: /\.(png|jpg|jpeg|svg|gif|webp)$/,
            handler: 'CacheFirst',
            options: { cacheName: 'image-cache', expiration: { maxEntries: 60, maxAgeSeconds: 86400 * 30 } },
          },
        ],
      },
      devOptions: { enabled: false },
    }),
  ],
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    assetsInlineLimit: 0,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          i18n: ['i18next', 'react-i18next'],
          charts: ['chart.js', 'react-chartjs-2'],
        },
      },
    },
  },
});