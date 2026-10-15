import { test, expect } from '@playwright/test';
import { sessionFixture } from './session-fixture';
import { captureContract } from './capture';
test('Opportunity OS public screen matrix (fictional session)', async ({ page }) => {
  test.setTimeout(90000);
  await sessionFixture(page, false);
  await page.goto('/');
  await expect(page.locator('h1')).toBeVisible();
  await captureContract(page, 'landing');
});

test('Overview, discovery and settings screen matrix (fictional session and public catalogue)', async ({
  page,
}) => {
  test.setTimeout(90000);
  await sessionFixture(page);
  for (const [route, name] of [
    ['/', 'overview'],
    ['/discover?development=true', 'discover'],
    ['/settings', 'settings'],
  ]) {
    await page.goto(route);
    await expect(page.locator('h1').first()).toBeVisible();
    await captureContract(page, name);
  }
});
