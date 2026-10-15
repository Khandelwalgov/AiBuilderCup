import { sessionFixture } from './session-fixture';
import { test, expect } from '@playwright/test';

test('Atlas landing stays illustrative and links to genuine discovery', async ({ page }) => {
  await page.goto('/');
  await expect(
    page.getByRole('heading', { name: 'Good opportunities. Clear next steps.' }),
  ).toBeVisible();
  await expect(page.getByText('ILLUSTRATIVE · NOT A MATCH')).toBeVisible();
  await page.getByRole('link', { name: 'Explore opportunities', exact: true }).click();
  await expect(page).toHaveURL(/\/discover$/);
  await expect(
    page
      .getByText('Public coverage includes only reviewed published records.', { exact: false })
      .first(),
  ).toBeVisible();
});

test('missing-fact deep link adds only the supported question, without saving (fictional API)', async ({
  page,
}) => {
  await sessionFixture(page);
  let writes = 0;
  await page.route('**/v1/profile/me', (route) => {
    if (route.request().method() !== 'GET') writes++;
    return route.fulfill({
      json: {
        id: '11111111-1111-4111-8111-111111111111',
        display_name: 'Fictional follow-up',
        facts: [],
      },
    });
  });
  await page.goto('/profile?field=domicile_state');
  await expect(page.locator('#fact-domicile_state')).toBeVisible();
  await expect(page.locator('.fact-editor')).toHaveCount(1);
  await expect(page.getByRole('textbox', { name: 'Value 1' })).toHaveValue('');
  expect(writes).toBe(0);
  await page.setViewportSize({ width: 320, height: 900 });
  await page.getByRole('combobox', { name: 'Interface language' }).selectOption('hi');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test('administrator reads actual 68-page public capture copy without any write (mocked API)', async ({
  page,
}) => {
  const { readFile } = await import('node:fs/promises');
  const fixture = JSON.parse(
    await readFile('../../data/fixtures/depwd-saved-candidates.json', 'utf8'),
  );
  const record = fixture.records[0];
  const id = record.original_id;
  const review = {
    id,
    opportunity_id: '11111111-1111-4111-8111-111111111111',
    version: 1,
    title: record.candidate.title,
    publication_state: 'draft',
    extraction_provider: 'openai',
    extraction_model: 'gpt-5.6-terra',
    extractor_version: 'preserved-public-copy',
    extraction_usage: null,
    candidate: record.candidate,
    published: null,
    pages: record.pages,
    content_hash: record.hash,
    candidate_hash: 'test-only-no-writes',
    changes: [],
    history: [],
  };
  await sessionFixture(page);
  let writes = 0;
  await page.route('**/v1/me', (r) =>
    r.fulfill({ json: { uid: 'fictional-admin-contract', is_admin: true } }),
  );
  await page.route('**/v1/admin/**', (r) => {
    if (r.request().method() !== 'GET') {
      writes++;
      return r.abort();
    }
    const path = new URL(r.request().url()).pathname;
    return r.fulfill({
      json: path.endsWith(`/reviews/${id}`) ? review : path.endsWith('/reviews') ? [review] : [],
    });
  });
  await page.goto('/admin');
  await page.getByRole('button', { name: /Pre-Matric Scholarship/ }).click();
  await expect(
    page.getByRole('combobox', { name: 'Captured page', exact: true }).locator('option'),
  ).toHaveCount(68);
  await page.getByRole('textbox', { name: 'Search all captured pages' }).fill('renewal');
  await expect(page.locator('.source-search-results button').first()).toBeVisible();
  await page
    .getByRole('combobox', { name: 'Captured page', exact: true })
    .selectOption({ label: '2025 amendment · page 2' });
  await expect(page.locator('.capture-text')).toContainText('UDID');
  await page.setViewportSize({ width: 1440, height: 960 });
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: '/Users/govind/Projects/AIBuildersCup/.live-validation/reimagine-after/admin-public-capture-copy-1440.png',
    fullPage: true,
  });
  expect(writes).toBe(0);
});

test('populated cockpit centers the actual API next-action contract (fictional component fixture)', async ({
  page,
}) => {
  const { captureContract } = await import('./capture');
  await page.route('**/v1/dashboard', (r) =>
    r.fulfill({
      json: {
        profile_name: 'Fictional learner',
        personal_pending_actions: 1,
        assessed_current_opportunities: 2,
        households: 1,
        businesses: 1,
        review_candidates: null,
      },
    }),
  );
  await page.route('**/v1/opportunity-facets*', (r) =>
    r.fulfill({
      json: {
        total: 2,
        verified: 2,
        official_sources: 1,
        categories: [],
        states: [],
        districts: [],
        synthetic: 0,
      },
    }),
  );
  await page.route('**/v1/plan', (r) =>
    r.fulfill({
      json: {
        subject: { kind: 'person' },
        hypothetical: false,
        evaluations: [],
        known_blockers: [],
        actions: [
          {
            title: 'Fictional shared certificate action',
            kind: 'document',
            opportunities: [{ id: 'fictional-1' }, { id: 'fictional-2' }],
          },
        ],
      },
    }),
  );
  await page.goto('/tests/cockpit.html');
  await expect(
    page.getByRole('heading', { name: 'Fictional shared certificate action', exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText('Fictional component contract · no Firebase acceptance'),
  ).toBeVisible();
  await captureContract(page, 'cockpit');
});
