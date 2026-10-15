import { expect, type Page } from '@playwright/test';
export async function productCapture(page: Page, name: string) {
  await expect(page.locator('main h1').first()).toBeVisible();
  await page.evaluate(async () => {
    await document.fonts.ready;
    await Promise.all(
      Array.from(document.images).map((image) => image.decode().catch(() => undefined)),
    );
    (document.activeElement as HTMLElement | null)?.blur();
    window.scrollTo({ top: 0, left: 0, behavior: 'instant' });
  });
  await expect.poll(() => page.evaluate(() => scrollY)).toBe(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({
    path: `/Users/govind/Projects/AIBuildersCup/.live-validation/${name}.png`,
    fullPage: true,
  });
}
