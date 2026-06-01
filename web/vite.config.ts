import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: '/CGCPT/',
  server: {
    host: '0.0.0.0',
    proxy: {
      '/CGCPT/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/CGCPT\/api/, '/api'),
      },
    },
  },
  build: {
    target: 'es2020',
    cssCodeSplit: true,
    reportCompressedSize: false,
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return
          if (id.includes('three') || id.includes('@react-three')) return 'vendor-three'
          if (id.includes('recharts')) return 'vendor-recharts'
          if (id.includes('lucide-react')) return 'vendor-lucide'
          if (id.includes('react-dom') || id.includes('react-router')) return 'vendor-react'
          if (id.includes('/react/')) return 'vendor-react'
        },
      },
    },
  },
})
