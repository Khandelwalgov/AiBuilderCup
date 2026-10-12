import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests',
  use: { baseURL: 'http://127.0.0.1:5173' },
  webServer: [
    {
      command:
        '../api/.venv/bin/uvicorn opportunity_platform.main:app --app-dir ../api/src --host 127.0.0.1 --port 8000',
      url: 'http://127.0.0.1:8000/health',
      reuseExistingServer: !process.env.CI,
    },
    { command: 'pnpm dev', url: 'http://127.0.0.1:5173', reuseExistingServer: !process.env.CI },
  ],
});
