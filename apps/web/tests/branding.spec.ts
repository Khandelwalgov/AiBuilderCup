import { expect, test } from '@playwright/test';
import { sessionFixture } from './session-fixture';
for (const mobile of [false, true]) {
  test(`approved branding and navigation (${mobile ? 'mobile' : 'desktop'})`, async ({ page }) => {
    await sessionFixture(page);
    await page.setViewportSize(mobile ? { width: 390, height: 844 } : { width: 1440, height: 900 });
    await page.goto('/settings');
    if (mobile) await page.getByRole('button', { name: 'Open navigation' }).click();
    const logo = page.locator('.sidebar .brand-full-dark');
    await expect(logo).toBeVisible();
    expect(await logo.evaluate((img) => (img as HTMLImageElement).naturalWidth)).toBeGreaterThan(
      500,
    );
    await page.screenshot({
      path: `../../.live-validation/branding/${mobile ? 'mobile' : 'desktop'}.png`,
    });
    await page.locator('.sidebar .brand').click();
    await expect(page).toHaveURL(/\/$/);
    await expect(page.locator('.breadcrumb')).toContainText('Overview');
  });
}
test('light mobile logo and published metadata assets', async ({ page }) => {
  await sessionFixture(page, false);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await expect(page.locator('.topbar .brand-symbol')).toBeVisible();
  await expect(page.locator('.topbar .brand-full-light')).not.toBeVisible();
  await page.setViewportSize({ width: 1440, height: 900 });
  await expect(page.locator('.topbar .brand-full-light')).toBeVisible();
  for (const path of [
    '/favicon.ico',
    '/brand/logo-dark.png',
    '/brand/logo-light.png',
    '/brand/icon-180.png',
    '/brand/icon-192.png',
    '/brand/icon-512.png',
    '/brand/social-preview.png',
    '/site.webmanifest',
  ]) {
    expect((await page.request.get(path)).status()).toBe(200);
  }
  const html = await (await page.request.get('/index.html')).text();
  expect(html).toContain('property="og:image"');
  expect(html).toContain('/favicon.ico');
});
