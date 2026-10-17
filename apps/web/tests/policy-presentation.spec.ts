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
    page.getByRole('heading', { name: 'Personalized eligibility matching' }),
  ).toBeVisible();
  const empty = page
    .locator('section.notice')
    .filter({ has: page.getByRole('heading', { name: 'Personalized eligibility matching' }) });
  await expect(empty).toContainText('do not establish personal eligibility');
  await expect(empty).not.toContainText('Try another keyword');
  await expect(empty.getByRole('button', { name: 'Clear filters' })).toHaveCount(0);
  await page.getByRole('combobox', { name: 'Interface language' }).selectOption('hi');
  await expect(page.getByRole('heading', { name: 'व्यक्तिगत पात्रता मिलान' })).toBeVisible();
  await expect(
    page
      .locator('section.notice')
      .filter({ has: page.getByRole('heading', { name: 'व्यक्तिगत पात्रता मिलान' }) }),
  ).toContainText('पात्रता');
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
  await page.route('**/v1/research-opportunities/guidance', (route) => {
    requestBody = route.request().postDataJSON();
    return route.fulfill({
      json: {
        items: [],
        candidate_count: 0,
        eligible_count: 0,
        hypothetical: false,
        actions: [],
        reviewed: {
          items: [],
          subjects: [
            { key: `person:${person}`, kind: 'person', id: person, name: 'Fictional One' },
          ],
          catalogue_count: 2,
          eligible_pair_count: 0,
          assessed_pair_count: 0,
          truncated: false,
          neural_status: 'disabled',
          timings_ms: {},
          subject_coverage: {},
          category_coverage: {},
        },
      },
    });
  });
  await page.goto('/discover');
  await expect(
    page.getByText('Published opportunities are available, but none could be assessed', {
      exact: false,
    }),
  ).toBeVisible();
  expect(requestBody).toMatchObject({ subject: { kind: 'person', id: null }, q: '' });
  await expect(page.getByRole('textbox', { name: 'Search (optional)' })).toBeEmpty();
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
    page.getByRole('heading', { name: 'Personalized eligibility matching' }),
  ).toHaveCount(0);
});

test('saved age and its explanation remain visually separate on mobile (mocked)', async ({
  page,
}) => {
  await sessionFixture(page);
  await page.route('**/v1/profile/me', (route) =>
    route.fulfill({
      json: {
        id: person,
        display_name: 'Fictional One',
        facts: [
          {
            key: 'age',
            value: 22,
            origin: 'user_supplied',
            context: { recorded_at: '2026-10-17' },
          },
        ],
      },
    }),
  );
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/profile');
  const answer = page.locator('.profile-section dd').filter({ hasText: 'Age recorded on:' });
  await expect(answer).toContainText('22');
  await expect(answer.locator('small')).toBeVisible();
  const answerBox = await answer.boundingBox();
  const noteBox = await answer.locator('small').boundingBox();
  expect(answerBox).not.toBeNull();
  expect(noteBox).not.toBeNull();
  expect(noteBox!.y).toBeGreaterThan(answerBox!.y + 10);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
