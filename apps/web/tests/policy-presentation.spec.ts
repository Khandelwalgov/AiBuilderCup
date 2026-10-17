import { expect, test } from '@playwright/test';
import { sessionFixture } from './session-fixture';

const person = '11111111-1111-4111-8111-111111111111';

test('empty unpublished catalogue explains review coverage in English and Hindi (mocked)', async ({
  page,
}) => {
  await sessionFixture(page, false);
  await page.route('**/v1/opportunity-facets*', (route) =>
    route.fulfill({
      json: {
        total: 0,
        verified: 0,
        synthetic: 0,
        official_sources: 0,
        categories: [],
        states: [],
        districts: [],
      },
    }),
  );
  await page.route('**/v1/opportunities?**', (route) =>
    route.fulfill({
      json: { items: [], total: 0, next_cursor: null },
    }),
  );
  await page.goto('/discover?mode=explore&q=TEAM');
  await expect(
    page.getByRole('heading', { name: 'No reviewed opportunities published yet' }),
  ).toBeVisible();
  const empty = page.locator('.empty-state');
  await expect(empty).toContainText('not a finding that you are ineligible');
  await expect(empty).not.toContainText('Try another keyword');
  await expect(empty.getByRole('link', { name: 'Browse government documents' })).toHaveAttribute(
    'href',
    /\/government-sources/,
  );
  await expect(empty.getByRole('button', { name: 'Clear filters' })).toHaveCount(0);
  await page.getByRole('combobox', { name: 'Interface language' }).selectOption('hi');
  await expect(
    page.getByRole('heading', { name: 'अभी कोई समीक्षित अवसर प्रकाशित नहीं हुआ है' }),
  ).toBeVisible();
  await expect(empty).toContainText('आपकी अपात्रता का निर्णय नहीं');
});

test('clearing catalogue filters retains authenticated Explore All (mocked)', async ({ page }) => {
  await sessionFixture(page);
  await page.route('**/v1/profile/me', (route) =>
    route.fulfill({
      json: {
        id: person,
        display_name: 'Fictional One',
        facts: [],
      },
    }),
  );
  await page.route('**/v1/opportunity-facets*', (route) =>
    route.fulfill({
      json: {
        total: 1,
        verified: 1,
        synthetic: 0,
        official_sources: 1,
        categories: ['education'],
        states: ['Rajasthan'],
        districts: [],
      },
    }),
  );
  await page.route('**/v1/opportunities?**', (route) =>
    route.fulfill({
      json: { items: [], total: 0, next_cursor: null },
    }),
  );
  await page.goto('/discover?mode=explore&q=unmatched&state=Rajasthan&national=false');
  await expect(page.getByRole('heading', { name: 'No opportunities found' })).toBeVisible();
  await page.locator('.empty-state').getByRole('button', { name: 'Clear filters' }).click();
  await expect(page).toHaveURL(/\/discover\?mode=explore$/);
  await expect(page.getByRole('combobox', { name: 'Search context' })).toHaveValue('explore');
});

test('Unlock Plan has no stray bilingual Scenario Studio content (mocked)', async ({ page }) => {
  await sessionFixture(page);
  await page.route('**/v1/profile/me', (route) =>
    route.fulfill({
      json: {
        id: person,
        display_name: 'Fictional One',
        facts: [],
      },
    }),
  );
  await page.goto('/plan');
  await expect(
    page.getByRole('heading', { name: 'From missing pieces to next steps' }),
  ).toBeVisible();
  await expect(page.locator('main')).not.toContainText('Scenario Studio · परिदृश्य स्टूडियो');
  await expect(page.getByRole('link', { name: 'Scenario Studio', exact: true })).toHaveCount(1);
});

test('automatic Discover explains a published catalogue with no applicable subject pairs (mocked)', async ({
  page,
}) => {
  await sessionFixture(page);
  await page.route('**/v1/profile/me', (route) =>
    route.fulfill({ json: { id: person, display_name: 'Fictional One', facts: [] } }),
  );
  let requestBody: Record<string, unknown> | undefined;
  await page.route('**/v1/search', (route) => {
    requestBody = route.request().postDataJSON();
    return route.fulfill({
      json: {
        items: [],
        subjects: [{ key: `person:${person}`, kind: 'person', id: person, name: 'Fictional One' }],
        catalogue_count: 2,
        eligible_pair_count: 0,
        assessed_pair_count: 0,
        truncated: false,
        neural_status: 'disabled',
        timings_ms: {},
        subject_coverage: {},
        category_coverage: {},
      },
    });
  });
  await page.goto('/discover');
  await expect(
    page.getByText('Published opportunities are available, but none could be assessed', {
      exact: false,
    }),
  ).toBeVisible();
  expect(requestBody).toMatchObject({ mode: 'me', q: '' });
  await expect(
    page.getByRole('textbox', { name: 'Search opportunities, interests, or keywords' }),
  ).toBeEmpty();
  await expect(page.getByText('This is a coverage gap', { exact: false })).toHaveCount(0);
});

test('excluding national opportunities does not imply the published catalogue is empty (mocked)', async ({
  page,
}) => {
  await sessionFixture(page, false);
  await page.route('**/v1/opportunity-facets*', (route) =>
    route.fulfill({
      json: {
        total: 1,
        verified: 1,
        synthetic: 0,
        official_sources: 1,
        categories: [],
        states: [],
        districts: [],
      },
    }),
  );
  await page.route('**/v1/opportunities?**', (route) =>
    route.fulfill({ json: { items: [], total: 0, next_cursor: null } }),
  );
  await page.goto('/discover?mode=explore&national=false');
  await expect(page.getByRole('heading', { name: 'No opportunities found' })).toBeVisible();
  await expect(
    page.getByRole('heading', { name: 'No reviewed opportunities published yet' }),
  ).toHaveCount(0);
});
