import { expect, test } from '@playwright/test';

test('public catalogue searches, filters, and opens database-backed detail', async ({ page }) => {
  await page.goto('/discover?development=true');
  await expect(page.getByRole('article')).toHaveCount(6);
  await expect(page.getByText('These fictional records help you explore')).toBeVisible();
  await page
    .getByRole('combobox', { name: 'All categories', exact: true })
    .selectOption('education');
  await expect(page.getByRole('article')).toHaveCount(1);
  await page.getByRole('link', { name: 'Learning support for students', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Learning support for students' })).toBeVisible();
  await expect(page.getByText('No official source has been attached')).toBeVisible();
  await expect(page.getByText('Not verified', { exact: true })).toBeVisible();
  await page.goto('/discover?development=true');
  await page
    .getByRole('textbox', { name: 'Search opportunities, interests, or keywords' })
    .fill('no-such-opportunity');
  await page.getByRole('button', { name: 'Search opportunities, interests, or keywords' }).click();
  await expect(page.getByRole('heading', { name: 'No opportunities found' })).toBeVisible();
  await page.getByRole('button', { name: 'Clear filters' }).first().click();
  await expect(page.getByRole('article')).toHaveCount(6);
  await page.getByRole('combobox', { name: 'All states / national' }).selectOption('Rajasthan');
  await page.getByRole('combobox', { name: 'All districts' }).selectOption('Dausa');
  await expect(page.getByRole('article')).toHaveCount(1);
  await expect(page.getByRole('article')).toContainText('Community skills fellowship');
});

test('mobile navigation, Hindi preference, and truthful coverage', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/discover?development=true');
  await expect(page.getByRole('article')).toHaveCount(6);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  await page.getByRole('button', { name: 'Open navigation' }).click();
  await page.getByRole('link', { name: 'Overview', exact: true }).click();
  await expect(page.getByText('Verified official sources', { exact: true })).toBeVisible();
  await page.getByRole('combobox', { name: 'Interface language' }).selectOption('hi');
  await expect(page.getByRole('heading', { name: 'संभावनाओं का स्पष्ट रास्ता।' })).toBeVisible();
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('lang', 'hi');
});

test('network failure gives a recoverable error state', async ({ page }) => {
  await page.route('**/v1/opportunities?**', (route) => route.abort());
  await page.goto('/discover?development=true');
  await expect(page.getByRole('heading', { name: 'We couldn’t load this page' })).toBeVisible();
  await page.unroute('**/v1/opportunities?**');
  await page.getByRole('button', { name: 'Try again', exact: true }).click();
  await expect(page.getByRole('article')).toHaveCount(6);
});
