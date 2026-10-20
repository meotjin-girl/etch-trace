import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// /api는 오늘은 FastAPI(8000), Spring Boot 단계에서는 8080으로 target만 변경
export default defineConfig({
  plugins: [vue()],
  server: { proxy: { '/api': 'http://localhost:8000' } },
})
