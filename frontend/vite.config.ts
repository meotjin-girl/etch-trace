import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  // Dev only: reuse the compose web proxy so /api and SSE behave as in production.
  server: {
    proxy: { '/api': `http://localhost:${process.env.WEB_PORT ?? 8080}` },
  },
  test: { environment: 'jsdom', include: ['tests/**/*.spec.ts'] },
})
