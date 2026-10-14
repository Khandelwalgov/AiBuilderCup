import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: (id) =>
          id.includes('/node_modules/') && (id.includes('/firebase') || id.includes('/@firebase/'))
            ? 'firebase'
            : undefined,
      },
    },
  },
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/v1': process.env.API_PROXY_TARGET || 'http://127.0.0.1:8000',
      '/health': process.env.API_PROXY_TARGET || 'http://127.0.0.1:8000',
    },
  },
});
