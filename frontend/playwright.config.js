import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './e2e', timeout: 60000, expect: { timeout: 15000 }, fullyParallel: false, workers: 1,
  use: { baseURL: 'http://127.0.0.1:5173', viewport: { width: 1440, height: 1050 }, headless: true, screenshot: 'only-on-failure' },
  reporter: [['list']],
});
