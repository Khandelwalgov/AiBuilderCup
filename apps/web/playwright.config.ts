import { defineConfig } from '@playwright/test';
const webPort = Number(process.env.E2E_WEB_PORT || 5174);
const apiPort = Number(process.env.E2E_API_PORT || 8001);
export default defineConfig({
  testDir: './tests',
  testIgnore: ['product-real.spec.ts', 'common-sense.spec.ts'],
  use: { baseURL: `http://127.0.0.1:${webPort}` },
  webServer: [
    {
      command: `../api/.venv/bin/uvicorn opportunity_platform.main:app --app-dir ../api/src --host 127.0.0.1 --port ${apiPort}`,
      url: `http://127.0.0.1:${apiPort}/health`,
      env: { ENABLE_DEVELOPMENT_CATALOGUE: 'true' },
      reuseExistingServer: false,
    },
    {
      command: `pnpm dev --port ${webPort} --strictPort`,
      url: `http://127.0.0.1:${webPort}`,
      env: { API_PROXY_TARGET: `http://127.0.0.1:${apiPort}`, VITE_API_BASE_URL: '' },
      reuseExistingServer: false,
    },
  ],
});
