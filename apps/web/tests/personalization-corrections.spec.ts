import { expect, test } from '@playwright/test';
import { sessionFixture } from './session-fixture';
const reviewed = {
  items: [],
  subjects: [{ key: 'person:fictional', kind: 'person', name: 'Fictional learner', id: null }],
  catalogue_count: 0,
  eligible_pair_count: 0,
  assessed_pair_count: 0,
  truncated: false,
  neural_status: 'not_requested',
  timings_ms: {},
  subject_coverage: {},
  category_coverage: {},
};
const plan = {
  subject: { kind: 'person' },
  hypothetical: true,
  actions: [],
  evaluations: [],
  known_blockers: [],
};
function item(title: string, group: string, outcome: string) {
  return {
    subject_id: title,
    subject_name: 'Fictional learner',
    subject_kind: 'person',
    parent_key: title,
    relevance_group: group,
    reason: 'National geographic scope; other requirements need checking.',
    components: [],
    listing: {
      id: title,
      title,
      jurisdiction: 'India',
      benefit: 'Source-described financial assistance.',
      summary: 'Detailed source summary stays on the detail page.',
      documents: [],
      source_url: 'https://example.gov.in/',
      application_status: 'not_established',
    },
    conditions: [
      {
        title: 'Source-backed age condition',
        result: { outcome, reason: 'Comparison with supplied age.', missing: [], facts: [] },
        baseline: { outcome },
        changed: false,
        gap_kind: 'information_gap',
        rule: { op: 'condition', condition: { fact: 'age', op: 'gte', value: 60 } },
        exceptions: [],
        unresolved_conditions: [],
        passage: '',
        snapshot_id: 'fictional-source',
        page: 1,
      },
    ],
  };
}
test('compact previews keep known mismatches collapsed and source evidence expandable (mocked)', async ({
  page,
}) => {
  await sessionFixture(page);
  await page.route('**/v1/research-opportunities/guidance', (r) =>
    r.fulfill({
      json: {
        items: [
          item('Fictional scholarship', 'promising', 'satisfied'),
          item('Fictional pension', 'known_mismatch', 'unsatisfied'),
        ],
        actions: [],
        candidate_count: 2,
        hypothetical: false,
        reviewed,
        relevance_counts: { promising: 1, information_gaps: 0, known_mismatch: 1 },
      },
    }),
  );
  await page.goto('/discover');
  await expect(
    page.getByRole('heading', { name: 'Fictional scholarship', exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole('heading', { name: 'Fictional pension', exact: true }),
  ).not.toBeVisible();
  await page.getByText('Known condition mismatches (1)', { exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Fictional pension', exact: true })).toBeVisible();
  const pension = page.locator('.research-guide-card').filter({ hasText: 'Fictional pension' });
  await pension.getByText('Conditions, gaps and next steps', { exact: true }).click();
  await expect(pension.getByText('Read the cited original passage')).toHaveCount(0);
  await expect(pension.getByRole('link', { name: 'Official evidence · Page 1' })).toBeVisible();
  await expect(pension.getByText('Detailed source summary stays on the detail page.')).toHaveCount(
    0,
  );
  await expect(pension.getByRole('link', { name: 'Official evidence and details' })).toBeVisible();
  await page.screenshot({
    path: '../../.live-validation/personalization/discover.png',
    fullPage: true,
  });
});

test('provisional condition counters remain separate from empty reviewed-policy assessments (mocked)', async ({
  page,
}) => {
  await sessionFixture(page);
  await page.route('**/v1/search', (r) => r.fulfill({ json: reviewed }));
  await page.route('**/v1/scenarios/evaluate', (r) =>
    r.fulfill({
      json: {
        actual: reviewed,
        hypothetical: reviewed,
        plan,
        changes: [],
        graph: [],
        persistence: 'none',
      },
    }),
  );
  await page.route('**/v1/research-opportunities/guidance', (r) => {
    const scenario = r.request().postDataJSON().scenario;
    return r.fulfill({
      json: {
        items: [],
        actions: [],
        candidate_count: 0,
        hypothetical: scenario,
        reviewed,
        research_changes: {
          total_conditions: 12,
          changed_conditions: 6,
          unchanged_conditions: 6,
          improved_conditions: 6,
          worsened_conditions: 0,
          unknown_conditions: 4,
          changed_programme_subject_pairs: 3,
        },
      },
    });
  });
  await page.goto('/scenarios');
  await page.getByRole('button', { name: 'Add fact override', exact: true }).first().click();
  await page.getByRole('spinbutton', { name: 'Hypothetical value' }).fill('22');
  await page.getByRole('button', { name: 'Run scenario', exact: true }).click();
  const summary = page.getByRole('region', { name: 'Provisional research changes' });
  await expect(
    summary
      .locator('div')
      .filter({ has: page.locator('dt', { hasText: /^Changed conditions$/ }) })
      .locator('dd'),
  ).toHaveText('6');
  await expect(
    page.getByText('No reviewed-policy assessments to compare', { exact: false }),
  ).toBeVisible();
  await expect(page.getByText('Changed assessments (0)', { exact: true })).toHaveCount(0);
  await expect(page.getByLabel('Graph zoom')).toHaveCount(0);
  await expect(page.getByRole('region', { name: 'Graph; use arrow keys to pan' })).toHaveCount(0);
  await expect(page.getByText('100%', { exact: true })).toHaveCount(0);
});

for (const width of [320, 1440])
  test(`Government Sources responsive primary/advanced filters and reset at ${width}px (mocked)`, async ({
    page,
  }) => {
    await sessionFixture(page);
    await page.setViewportSize({ width, height: 900 });
    await page.route('**/v1/government-sources?*', (r) =>
      r.fulfill({
        json: {
          items: [],
          total: 0,
          all_capture_records: 0,
          all_unique_document_hashes: 0,
          public_research_listings: 0,
          unpublished_eligibility_versions: 0,
          published_eligibility_policies: 0,
        },
      }),
    );
    await page.goto('/government-sources');
    const search = page.getByRole('textbox', { name: 'Search source text' });
    await expect(search).toBeVisible();
    const input = await search.boundingBox();
    const form = await page.locator('.source-filters').boundingBox();
    expect(input!.width).toBeGreaterThan(form!.width * 0.85);
    await expect(page.getByRole('combobox', { name: 'Review state' })).toBeVisible();
    await expect(page.getByRole('textbox', { name: 'Department', exact: true })).not.toBeVisible();
    await page.getByText('Advanced filters', { exact: true }).click();
    await page.screenshot({
      path: `../../.live-validation/personalization/source-filters-${width}.png`,
      fullPage: true,
    });
    await page.getByRole('textbox', { name: 'Department', exact: true }).fill('MSME');
    await expect(page).toHaveURL(/department=MSME/);
    await page.getByRole('button', { name: 'Clear filters', exact: true }).click();
    await expect(page.getByRole('textbox', { name: 'Department', exact: true })).toHaveValue('');
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
  });
