import { expect, test } from '@playwright/test';
import { mkdir } from 'node:fs/promises';
const artifacts = '/Users/govind/Projects/AIBuildersCup/.live-validation/ui';
for (const width of [1440, 1024, 390, 320]) {
  test(`Nightfall real public and protected empty states: ${width}px EN/HI`, async ({ page }) => {
    await mkdir(artifacts, { recursive: true });
    await page.setViewportSize({ width, height: 960 });
    const errors: string[] = [];
    page.on('pageerror', (error) => errors.push(error.message));
    for (const language of ['en', 'hi']) {
      await page.addInitScript((language) => localStorage.setItem('language', language), language);
      for (const route of [
        'dashboard',
        'discover',
        'profile',
        'family',
        'businesses',
        'plan',
        'admin',
      ]) {
        await page.goto(`/${route}`);
        await expect(page.locator('h1').first()).toBeVisible();
        await page.waitForTimeout(180);
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
          true,
        );
        await page.screenshot({
          path: `${artifacts}/${route}-${language}-${width}.png`,
          fullPage: true,
        });
      }
    }
    expect(errors).toEqual([]);
  });
}
