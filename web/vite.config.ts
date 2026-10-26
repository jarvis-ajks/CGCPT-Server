import { defineConfig } from 'vite'
import { fileURLToPath, URL } from 'node:url'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'
import { crystvisBufferPlugin } from './scripts/crystvis-buffer-plugin'

const resolveFromRoot = (specifier: string) => fileURLToPath(new URL(`node_modules/${specifier}`, import.meta.url))

export default defineConfig({
  plugins: [crystvisBufferPlugin(), react(), svelte({ configFile: false, compilerOptions: { css: 'injected' } }), tailwindcss()],
  optimizeDeps: {
    rolldownOptions: { plugins: [crystvisBufferPlugin()] },
  },
  base: '/CGCPT/',
  define: {
    // @materialsproject/mp-react-components and its CommonJS deps expect the
    // Node-style `global` object; browsers only expose `globalThis`.
    global: 'globalThis',
  },
  resolve: {
    // MP ships its own nested React 16 copy. Force a single React instance,
    // otherwise the scene component throws React #321 (invalid hook call).
    dedupe: ['react', 'react-dom', 'react-is'],
    alias: [
      { find: /^react$/, replacement: resolveFromRoot('react') },
      { find: /^react\/jsx-runtime$/, replacement: resolveFromRoot('react/jsx-runtime') },
      { find: /^react\/jsx-dev-runtime$/, replacement: resolveFromRoot('react/jsx-dev-runtime') },
      { find: /^react-dom$/, replacement: resolveFromRoot('react-dom') },
      { find: /^react-dom\/client$/, replacement: resolveFromRoot('react-dom/client') },
    ],
  },
  server: {
    host: '0.0.0.0',
    allowedHosts: ['zsxw.asia', 'www.zsxw.asia', '118.31.164.41'],
    proxy: {
      // Crystal Toolkit scene service (upstream MP viewer payloads).
      '/CGCPT/api/structure/scene': {
        target: 'http://127.0.0.1:18108',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/CGCPT\/api\/structure\/scene/, '/scene'),
      },
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
          if (id.includes('recharts')) return 'vendor-recharts'
          if (id.includes('lucide-react')) return 'vendor-lucide'
          if (id.includes('react-dom') || id.includes('react-router')) return 'vendor-react'
          if (id.includes('/react/')) return 'vendor-react'
        },
      },
    },
  },
})
