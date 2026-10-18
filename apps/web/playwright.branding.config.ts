import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests',
  testMatch: ['branding.spec.ts', 'reimagine-navigation.spec.ts'],
  use: { baseURL: 'http://127.0.0.1:15314' },
  webServer: {
    command: 'pnpm dev --port 15314 --strictPort',
    url: 'http://127.0.0.1:15314',
    env: { VITE_API_BASE_URL: '' },
    reuseExistingServer: false,
  },
});
