import { expect, type Page } from '@playwright/test';
import { mkdir } from 'node:fs/promises';
export async function captureContract(page: Page, name: string) {
  const directory = '/Users/govind/Projects/AIBuildersCup/.live-validation/reimagine-after';
  await mkdir(directory, { recursive: true });
  for (const width of [1440, 1024, 390, 320]) {
    await page.setViewportSize({ width, height: 960 });
    for (const language of ['en', 'hi']) {
      await page
        .getByRole('combobox', { name: /Interface language|इंटरफ़ेस की भाषा/ })
        .first()
        .selectOption(language);
      await page.evaluate(() => window.scrollTo(0, 0));
      const overflow = await page.evaluate(() =>
        Array.from(document.querySelectorAll('body *'))
          .filter((el) => el.getBoundingClientRect().right > innerWidth + 1)
          .slice(0, 12)
          .map((el) => ({
            tag: el.tagName,
            cls: el.className,
            right: el.getBoundingClientRect().right,
            width: el.getBoundingClientRect().width,
          })),
      );
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
        JSON.stringify({ width, language, overflow }),
      ).toBe(true);
      await page.screenshot({
        path: `${directory}/${name}-fictional-${language}-${width}.png`,
        fullPage: true,
      });
    }
  }
  await page.setViewportSize({ width: 1440, height: 960 });
  await page
    .getByRole('combobox', { name: /Interface language|इंटरफ़ेस की भाषा/ })
    .first()
    .selectOption('en');
}
