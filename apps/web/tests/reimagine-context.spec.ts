import { test, expect } from '@playwright/test';
import { sessionFixture } from './session-fixture';
const person = '11111111-1111-4111-8111-111111111111';
const household = '22222222-2222-4222-8222-222222222222';
const business = '33333333-3333-4333-8333-333333333333';
const workspaces = [
  {
    id: household,
    kind: 'household',
    name: 'Fictional family',
    role: 'owner',
    facts: [],
    members: [
      { id: person, name: 'Fictional dependent', managed: true, access: 'authorized' },
      { name: 'Private adult', access: 'not_shared', managed: false },
    ],
  },
  {
    id: business,
    kind: 'business',
    name: 'Fictional business',
    role: 'owner',
    facts: [],
    members: [],
  },
];
test('authorized subject is retained across navigation and plan requests; unknown identities stay hidden', async ({
  page,
}) => {
  await sessionFixture(page);
  await page.route('**/v1/workspaces', (r) => r.fulfill({ json: workspaces }));
  const subjects: unknown[] = [];
  await page.route('**/v1/plan', (r) => {
    const subject = r.request().postDataJSON().subject;
    subjects.push(subject);
    return r.fulfill({
      json: { subject, hypothetical: false, evaluations: [], actions: [], known_blockers: [] },
    });
  });
  await page.goto('/');
  const selector = page.locator('.shell-context select');
  await expect(selector.locator('option')).toHaveCount(4);
  await expect(selector).not.toContainText('Private adult');
  for (const [kind, id] of [
    ['person', person],
    ['household', household],
    ['business', business],
  ]) {
    await selector.selectOption(`${kind}:${id}`);
    await expect(page).toHaveURL(new RegExp(`kind=${kind}&id=${id}`));
    await page.getByRole('link', { name: 'Unlock plan', exact: true }).click();
    await expect
      .poll(() => subjects.some((s) => JSON.stringify(s) === JSON.stringify({ kind, id })))
      .toBe(true);
    await expect(selector).toHaveValue(`${kind}:${id}`);
    await page.getByRole('link', { name: 'Overview', exact: true }).click();
  }
  await page.goto('/plan?kind=person&id=44444444-4444-4444-8444-444444444444');
  await expect(page.getByRole('alert')).toContainText('This context is unavailable');
  await expect(page.locator('main')).not.toContainText('44444444');
});
test('profile edits survive background refetch and declined navigation; account change clears private draft', async ({
  page,
}) => {
  await sessionFixture(page);
  let reads = 0;
  await page.route('**/v1/profile/me', (r) => {
    reads++;
    return r.fulfill({ json: { id: person, display_name: 'Fictional original', facts: [] } });
  });
  await page.goto('/profile');
  await page.getByRole('button', { name: 'Edit about you', exact: true }).click();
  await page.getByRole('textbox', { name: 'Profile name' }).fill('Unsaved fictional change');
  await page
    .getByRole('button', { name: 'Refetch fictional profile', includeHidden: true })
    .evaluate((el: HTMLButtonElement) => el.click());
  await expect.poll(() => reads).toBeGreaterThan(1);
  await expect(page.getByRole('textbox', { name: 'Profile name' })).toHaveValue(
    'Unsaved fictional change',
  );
  page.once('dialog', (d) => d.dismiss());
  await page.getByRole('link', { name: 'Discover opportunities', exact: true }).click();
  await expect(page).toHaveURL(/\/profile$/);
  await page
    .getByRole('button', { name: 'Switch fictional account', includeHidden: true })
    .evaluate((el: HTMLButtonElement) => el.click());
  await page.getByRole('button', { name: 'Edit about you', exact: true }).click();
  await expect(page.getByRole('textbox', { name: 'Profile name' })).toHaveValue(
    'Fictional original',
  );
  await page.getByRole('button', { name: 'Account menu' }).click();
  await page.getByRole('menuitem', { name: 'Sign out', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Sign in');
});
test('ingestion is a reviewable confirmation and disabled operator permission makes no POST', async ({
  page,
}) => {
  await sessionFixture(page);
  await page.route('**/v1/me', (r) =>
    r.fulfill({ json: { uid: 'fictional-admin', is_admin: true } }),
  );
  let posts = 0;
  await page.route('**/v1/admin/**', (r) => {
    if (r.request().method() !== 'GET') {
      posts++;
      return r.abort();
    }
    const path = new URL(r.request().url()).pathname;
    const json = path.endsWith('ingestion-settings')
      ? {
          provider: 'gemini',
          model: 'configured-flash',
          live_enabled: false,
          test_budget_usd: 1,
          estimate_available: false,
        }
      : path.endsWith('sources')
        ? [
            {
              key: 'official-test',
              name: 'Fictional official source',
              url: 'https://example.gov.in/public',
              adapter: 'public',
              draft_count: 2,
            },
          ]
        : [];
    return r.fulfill({ json });
  });
  await page.goto('/admin');
  await page.getByText('Source operations and run history', { exact: true }).click();
  await page.getByRole('button', { name: 'Ingest source', exact: true }).click();
  const dialog = page.getByRole('dialog');
  await expect(dialog).toContainText('gemini / configured-flash');
  await expect(dialog).toContainText('durable spending limits');
  await expect(dialog.getByRole('button', { name: 'Confirm source ingestion' })).toBeDisabled();
  await dialog.getByRole('button', { name: 'Cancel' }).click();
  expect(posts).toBe(0);
});
test('candidate citation with absent page shows an evidence-location error, not page one', async ({
  page,
}) => {
  await sessionFixture(page);
  const { readFile } = await import('node:fs/promises');
  const fixture = JSON.parse(
    await readFile('../../data/fixtures/depwd-saved-candidates.json', 'utf8'),
  );
  const record = fixture.records[0];
  record.candidate.requirements[0].evidence.page = 999;
  const review = {
    id: record.original_id,
    opportunity_id: person,
    version: 1,
    title: record.candidate.title,
    publication_state: 'draft',
    candidate: record.candidate,
    pages: record.pages,
    candidate_hash: 'fictional-only',
    content_hash: record.hash,
    published: null,
    changes: [],
    history: [],
    extraction_provider: 'openai',
    extraction_model: 'preserved-copy',
    extractor_version: 'test-only',
    extraction_usage: null,
  };
  await page.route('**/v1/me', (r) =>
    r.fulfill({ json: { uid: 'fictional-admin', is_admin: true } }),
  );
  await page.route('**/v1/admin/**', (r) =>
    r.fulfill({
      json: new URL(r.request().url()).pathname.endsWith(`/reviews/${record.original_id}`)
        ? review
        : new URL(r.request().url()).pathname.endsWith('/reviews')
          ? [review]
          : [],
    }),
  );
  await page.goto(`/admin/reviews/${record.original_id}`);
  await page.getByRole('button', { name: 'Inspect captured page 999', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Cited source page not found' })).toBeVisible();
  await expect(page.locator('.capture-text')).toHaveCount(0);
  await page.getByRole('combobox', { name: 'Choose a captured page' }).selectOption('0');
  await expect(page.locator('.capture-text')).toBeVisible();
});
test('eligibility sends each authorized subject and fresh/renewal selection; unsupported response stays explicit', async ({
  page,
}) => {
  await sessionFixture(page);
  const { opportunity, id } = await import('./opportunity-fixture');
  await page.route('**/v1/workspaces', (r) => r.fulfill({ json: workspaces }));
  await page.route(`**/v1/opportunities/${id}?*`, (r) => r.fulfill({ json: opportunity }));
  const requests: { subject: { kind: string; id: string | null }; application_type: string }[] = [];
  await page.route(`**/v1/opportunities/${id}/evaluate`, (r) => {
    requests.push(r.request().postDataJSON());
    return r.fulfill({
      status: 422,
      json: {
        error: {
          code: 'unsupported_subject_context',
          message: 'This opportunity does not support this subject context.',
        },
      },
    });
  });
  await page.goto(`/opportunities/${id}`);
  for (const [kind, identifier] of [
    ['person', ''],
    ['person', person],
    ['household', household],
    ['business', business],
  ]) {
    await page.locator('.shell-context select').selectOption(`${kind}:${identifier}`);
    for (const application_type of ['fresh', 'renewal']) {
      await page
        .getByRole('combobox', { name: 'Application context for this opportunity' })
        .selectOption(application_type);
      await page.getByRole('button', { name: 'Check my eligibility', exact: true }).click();
      await expect(page.getByRole('alert')).toContainText('does not support this subject context');
      expect(requests.at(-1)).toEqual({
        subject: { kind, id: identifier || null },
        application_type,
        development: false,
      });
    }
  }
});
