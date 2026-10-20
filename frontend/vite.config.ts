import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { mockApi } from './mock/plugin'

// MOCK_API=1 (npm run dev:mock) serves /api from the in-memory mock instead of the backend.
const mock = Boolean(process.env.MOCK_API)

export default defineConfig({
  plugins: [vue(), ...(mock ? [mockApi()] : [])],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  // Dev only: reuse the compose web proxy so /api and SSE behave as in production.
  server: mock ? {} : {
    proxy: { '/api': `http://localhost:${process.env.WEB_PORT ?? 8080}` },
  },
  test: { environment: 'jsdom', include: ['tests/**/*.spec.ts'] },
})
