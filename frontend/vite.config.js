import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules')) {
            if (id.includes('/xlsx/')) return 'xlsx'
            if (id.includes('react-router')) return 'react-vendor'
            if (id.includes('/react-dom/') || id.includes('/react/')) return 'react-vendor'
            if (id.includes('@tanstack')) return 'query-vendor'
            if (
              id.includes('react-hook-form') ||
              id.includes('@hookform') ||
              id.includes('/zod/')
            ) {
              return 'form-vendor'
            }
          }
        },
      },
    },
  },
})
