import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

const apiTarget =
  (globalThis as unknown as { process?: { env?: Record<string, string> } })
    .process?.env?.VITE_API_TARGET || 'http://127.0.0.1:8000';

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    allowedHosts: true,
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.ts',
  },
});
