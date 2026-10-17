import { artifactRoot } from './artifacts';
import { expect, test } from '@playwright/test';
import { mkdir } from 'node:fs/promises';
const artifacts = `${artifactRoot}/ui`;
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

test('keyboard skip link and mobile navigation return focus safely', async ({ page }) => {
  await page.goto('/discover');
  await expect(page.locator('h1').first()).toBeVisible();
  await page.keyboard.press('Tab');
  await expect(page.getByRole('link', { name: 'Skip to content' })).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.locator('#main')).toBeFocused();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole('button', { name: 'Open navigation' }).click();
  await expect(page.locator('.brand')).toBeFocused();
  await page.keyboard.press('Shift+Tab');
  await expect(page.locator('.settings-link')).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('button', { name: 'Open navigation' })).toBeFocused();
  await expect(page.locator('#primary-navigation')).not.toBeVisible();
});
