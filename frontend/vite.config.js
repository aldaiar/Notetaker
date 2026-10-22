import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// В разработке запросы /api/* проксируются на бэкенд и префикс /api отбрасывается.
// Это же делает nginx в Docker (см. nginx.conf), поэтому CORS на бэкенде не нужен.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.API_URL || 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
