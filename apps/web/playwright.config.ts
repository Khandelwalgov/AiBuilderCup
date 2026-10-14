import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests',
  use: { baseURL: 'http://127.0.0.1:5174' },
  webServer: [
    {
      command:
        '../api/.venv/bin/uvicorn opportunity_platform.main:app --app-dir ../api/src --host 127.0.0.1 --port 8001',
      url: 'http://127.0.0.1:8001/health',
      env: { ENABLE_DEVELOPMENT_CATALOGUE: 'true' },
      reuseExistingServer: false,
    },
    {
      command: 'pnpm dev --port 5174 --strictPort',
      url: 'http://127.0.0.1:5174',
      env: { API_PROXY_TARGET: 'http://127.0.0.1:8001', VITE_API_BASE_URL: '' },
      reuseExistingServer: false,
    },
  ],
});
