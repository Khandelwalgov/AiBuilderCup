import { expect, test } from '@playwright/test';
import { readFileSync } from 'node:fs';
const bundle = JSON.parse(readFileSync('../../data/research/catalogue-v1.json', 'utf8'));
const listing = bundle.listings[0];
const id = '11111111-2222-4333-8444-555555555555';
const card = {
  ...listing,
  id,
  source_url: listing.sources[0].source_url,
  source_count: listing.sources.length,
};

test.beforeEach(async ({ page }) => {
  await page.route('**/v1/research-opportunities**', async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith('/facets')) {
      await route.fulfill({
        json: {
          total: 98,
          categories: ['education', 'procurement'],
          jurisdictions: ['India'],
          availability: { unknown: 98 },
          application_status: { not_established: 98 },
          source_documents: 1,
        },
      });
    } else if (url.pathname.endsWith(id)) {
      await route.fulfill({ json: card });
    } else {
      const matches =
        !url.searchParams.get('category') || url.searchParams.get('category') === listing.category;
      await route.fulfill({
        json: { items: matches ? [card] : [], total: matches ? 98 : 0, next_cursor: null },
      });
    }
  });
});

test('guest Discover automatically loads research, filters, and opens actual captured evidence', async ({
  page,
}) => {
  const request = page.waitForRequest(
    (r) => new URL(r.url()).pathname === '/v1/research-opportunities',
  );
  await page.goto('/discover');
  expect(new URL((await request).url()).searchParams.get('q')).toBe('');
  const catalogue = page.getByRole('region', { name: 'Explore Government Opportunities' });
  await expect(catalogue.getByRole('heading', { name: listing.title })).toBeVisible();
  await expect(
    catalogue.getByText('Source-backed research · Eligibility not yet verified').first(),
  ).toBeVisible();
  await expect(catalogue.getByRole('link', { name: 'Original official source' })).toHaveAttribute(
    'href',
    listing.sources[0].source_url,
  );
  await catalogue
    .getByRole('combobox', { name: 'All research categories' })
    .selectOption('procurement');
  await expect(catalogue.getByText('No research listings match these filters.')).toBeVisible();
  await catalogue.getByRole('button', { name: 'Clear research filters' }).click();
  await catalogue.getByRole('link', { name: 'Read opportunity and evidence' }).click();
  await expect(page.getByRole('heading', { name: listing.title })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Source evidence' })).toBeVisible();
  await expect(page.locator('blockquote').first()).toContainText(listing.citations[0].passage);
});

test('research is readable on mobile with Hindi interface', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/discover');
  await page.getByRole('combobox', { name: 'Interface language' }).selectOption('hi');
  await expect(page.getByRole('heading', { name: 'सरकारी अवसर देखें' })).toBeVisible();
  await expect(
    page.getByText('आधिकारिक स्रोत पर आधारित शोध · पात्रता अभी सत्यापित नहीं').first(),
  ).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
