import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests',
  testMatch: [
    'product-real.spec.ts',
    'common-sense.spec.ts',
    'intelligence-real.spec.ts',
    'corpus-real.spec.ts',
  ],
  workers: 1,
  timeout: 60000,
  use: { baseURL: 'http://127.0.0.1:15210', acceptDownloads: true },
  webServer: [
    {
      command: '../api/.venv/bin/python ../../scripts/product_e2e_server.py',
      url: 'http://127.0.0.1:18210/health',
      gracefulShutdown: { signal: 'SIGTERM', timeout: 10000 },
      reuseExistingServer: false,
      env: {
        ENVIRONMENT: 'development',
        FIREBASE_PROJECT_ID: 'demo-opportunity-completion',
        FIREBASE_AUTH_EMULATOR_HOST: '127.0.0.1:19299',
        ENABLE_DEVELOPMENT_CATALOGUE: 'true',
        DOCUMENT_UPLOADS_ENABLED: 'true',
        AI_INGESTION_LIVE_ENABLED: 'false',
        AI_ASSISTANT_LIVE_ENABLED: 'false',
        OPENAI_API_KEY: '',
        GEMINI_API_KEY: '',
      },
    },
    {
      command: 'pnpm dev --port 15210 --strictPort',
      url: 'http://127.0.0.1:15210',
      reuseExistingServer: false,
      env: {
        API_PROXY_TARGET: 'http://127.0.0.1:18210',
        VITE_API_BASE_URL: '',
        VITE_FIREBASE_API_KEY: 'fictional-emulator-key',
        VITE_FIREBASE_AUTH_DOMAIN: 'demo-opportunity-completion.firebaseapp.com',
        VITE_FIREBASE_PROJECT_ID: 'demo-opportunity-completion',
        VITE_FIREBASE_APP_ID: 'fictional-emulator-app',
        VITE_FIREBASE_AUTH_EMULATOR_URL: 'http://127.0.0.1:19299',
      },
    },
  ],
});
