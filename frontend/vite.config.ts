import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(import.meta.dirname, './src'),
    },
  },
  server: {
    // En dev, /api se reenvía a FastAPI: el navegador ve un único origen (sin CORS y con cookies).
    proxy: {
      // 127.0.0.1 y no localhost: Node puede resolver localhost a IPv6 (::1) y uvicorn escucha en IPv4.
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
