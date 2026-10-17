import { artifactRoot } from './artifacts';
import { sessionFixture } from './session-fixture';
import { captureContract } from './capture';
import { expect, test } from '@playwright/test';
import type { components } from '../src/lib/api/schema';

// Browser contract test only. Firebase and Gemini are NOT bypassed in application code.
// These fictional policy responses never enter the application database or public catalogue.
import { id, time, citation, rule, opportunity } from './opportunity-fixture';

test('profile → published opportunity → cited eligibility results (mocked auth/API contract)', async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 960 });
  let profile: components['schemas']['ProfileView'] | null = null;
  await sessionFixture(page);
  await page.route('**/v1/profile/me', async (route) => {
    if (route.request().method() === 'PUT') {
      const input = route.request().postDataJSON() as components['schemas']['ProfileWrite'];
      expect(input.display_name).toBe('Synthetic learner');
      expect(input.facts).toHaveLength(1);
      expect(input.facts[0]).toMatchObject({ key: 'age', value: 20 });
      profile = {
        id,
        display_name: input.display_name,
        facts: input.facts.map((f) => ({
          id,
          key: f.key,
          value: f.value,
          origin: 'user_supplied',
          verification: 'unverified',
        })),
      };
    }
    await route.fulfill(
      profile
        ? { json: profile }
        : {
            status: 404,
            json: { error: { code: 'profile_not_found', message: 'Create your profile first.' } },
          },
    );
  });
  await page.route(`**/v1/opportunities/${id}?*`, (route) => route.fulfill({ json: opportunity }));
  await page.route(`**/v1/opportunities/${id}/evaluate`, async (route) => {
    expect(profile?.facts[0].value).toBe(20);
    const response: components['schemas']['EvaluationView'] = {
      id,
      opportunity_id: id,
      version_id: id,
      version: 1,
      evaluated_at: time,
      status: 'possibly_eligible_missing_information',
      disclaimer: 'Synthetic test assessment. The issuing authority decides approval.',
      requirements: [
        {
          requirement_id: id,
          requirement: 'Synthetic minimum age',
          rule,
          result: {
            outcome: 'satisfied',
            reason: 'Supplied age meets the synthetic condition.',
            facts: profile!.facts,
            missing: [],
            blockers: [],
            kind: 'condition',
            children: [],
          },
          citations: [citation],
          next_steps: [],
        },
        {
          requirement_id: '22222222-2222-4222-8222-222222222222',
          requirement: 'Synthetic evidence requirement',
          rule: { op: 'condition', condition: { op: 'unknown' } },
          result: {
            outcome: 'unknown',
            reason: 'Documentary evidence is not verified.',
            facts: [],
            missing: ['has_income_certificate'],
            blockers: ['document:test'],
            kind: 'evidence_gap',
            children: [],
          },
          citations: [citation],
          next_steps: ['Provide verified evidence.'],
        },
      ],
    };
    await route.fulfill({ json: response });
  });
  await page.goto('/profile');
  await page.getByRole('textbox', { name: 'Profile name' }).fill('Synthetic learner');
  await page.getByRole('button', { name: 'Continue', exact: true }).click();
  await page.getByRole('spinbutton', { name: 'How old are you?', exact: true }).fill('20');
  await page.getByRole('button', { name: 'Review your answers' }).click();
  await page.getByRole('button', { name: 'Finish setup' }).click();
  await expect(page.locator('.profile-summary').getByRole('status')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Save changes', exact: true })).toHaveCount(0);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: `${artifactRoot}/ui/profile-populated-contract-1440.png`,
    fullPage: true,
  });
  await captureContract(page, 'profile');
  await page.goto(`/opportunities/${id}`);
  await page.getByRole('button', { name: 'Check my eligibility', exact: true }).click();
  await expect(page.locator('.requirement-result.satisfied')).toContainText(
    'Synthetic minimum age',
  );
  await expect(page.locator('.requirement-result.unknown')).toContainText(
    'Provide verified evidence.',
  );
  await expect(page.locator('.requirement-result a').first()).toHaveAttribute(
    'href',
    citation.source_url,
  );
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: `${artifactRoot}/ui/eligibility-populated-contract-1440.png`,
    fullPage: true,
  });
  await captureContract(page, 'detail');
  await page.route('**/v1/assistant/capabilities', (r) =>
    r.fulfill({ json: { gemini_intent_enabled: false } }),
  );
  await page.route('**/v1/assistant/explain', (r) =>
    r.fulfill({
      json: {
        mode: 'local',
        model: null,
        intent: 'why',
        answer: 'Fictional cited explanation',
        disclaimer: 'Test only',
        items: [
          {
            requirement_id: id,
            condition: 'Synthetic minimum age',
            outcome: 'satisfied',
            explanation: 'Supplied age',
            citations: [citation],
          },
        ],
      },
    }),
  );
  await page.getByRole('button', { name: 'Why is this condition unknown?' }).click();
  await page.getByRole('link', { name: 'Locate condition in assessment' }).click();
  await expect(page).toHaveURL(new RegExp(`#source-requirement-${id}$`));
  await expect(page.locator(`#source-requirement-${id}`)).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
});

test('normal catalogue keeps synthetic fixtures out and profile requires authentication', async ({
  page,
}) => {
  await page.goto('/discover');
  await expect(page.getByRole('article')).toHaveCount(0);
  await expect(
    page.getByRole('heading', { name: 'No reviewed opportunities published yet' }),
  ).toBeVisible();
  await page.goto('/profile');
  await expect(page.getByRole('alert')).toContainText('Sign in');
  await expect(page.getByRole('button', { name: 'Save profile' })).toHaveCount(0);
});

test('admin inspects evidence and publishes through the review API (mocked contract)', async ({
  page,
}) => {
  await sessionFixture(page);
  await page.setViewportSize({ width: 1440, height: 960 });
  const candidate: components['schemas']['CandidateData'] = {
    title: opportunity.title,
    summary: opportunity.summary,
    category: 'education',
    issuer: 'Synthetic test authority',
    country: 'India',
    requirements: [
      {
        description: 'Synthetic minimum age',
        rule,
        evidence: { ...citation, page: 1, language: 'English', basis: 'explicit' },
      },
    ],
    review_flags: ['Synthetic test only'],
    missing_fields: ['closes_on'],
  };
  let review: components['schemas']['ReviewView'] = {
    id,
    title: candidate.title,
    version: 1,
    publication_state: 'draft',
    source_url: citation.source_url,
    created_at: time,
    candidate,
    published: null,
    pages: [{ page: 1, source_url: citation.source_url, text: citation.passage }],
    extraction_provider: 'gemini',
    extraction_model: 'gemini-3.8-flash',
    extractor_version: 'synthetic-browser-test',
    extraction_usage: null,
    content_hash: 'a'.repeat(64),
    candidate_hash: 'b'.repeat(64),
    changes: ['requirements'],
    history: [],
  };
  await page.route('**/v1/me', (route) =>
    route.fulfill({ json: { uid: 'synthetic-admin', is_admin: true } }),
  );
  await page.route('**/v1/admin/sources', (route) => route.fulfill({ json: [] }));
  await page.route('**/v1/admin/ingestion-runs', (route) => route.fulfill({ json: [] }));
  await page.route('**/v1/admin/reviews?*', (route) =>
    route.fulfill({ json: review.publication_state === 'draft' ? [review] : [] }),
  );
  await page.route(`**/v1/admin/reviews/${id}`, async (route) => {
    if (route.request().method() === 'POST') {
      const body = route.request().postDataJSON() as components['schemas']['ReviewWrite'];
      expect(body.decision).toBe('approve');
      expect(body.expected_hash).toBe('b'.repeat(64));
      expect(body.source_completeness_confirmed).toBe(true);
      expect(body.acknowledge_flags).toBe(true);
      review = { ...review, publication_state: 'published' };
    }
    await route.fulfill({ json: review });
  });
  await page.goto('/admin');
  await page.getByRole('button', { name: /Synthetic browser test policy/ }).click();
  await page.getByRole('combobox', { name: 'Captured page', exact: true }).selectOption('0');
  await expect(page.locator('.capture-text')).toContainText(citation.passage);
  await page.getByRole('textbox', { name: 'Search all captured pages' }).fill('eighteen');
  await expect(page.locator('.source-search-results')).toContainText('1 matching pages');
  await page.getByRole('textbox', { name: 'Exact source passage' }).fill(citation.passage);
  await page.getByRole('textbox', { name: 'Review note' }).fill('Checked synthetic test evidence.');
  const checkboxes = page.locator('.candidate-editor input[type=checkbox]');
  await checkboxes.nth(0).check();
  await checkboxes.nth(1).check();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: `${artifactRoot}/ui/admin-populated-contract-1440.png`,
    fullPage: true,
  });
  await captureContract(page, 'admin');
  await page.getByRole('button', { name: 'Approve & publish', exact: true }).click();
  await page
    .getByRole('dialog')
    .getByRole('button', { name: 'Approve & publish', exact: true })
    .click();
  await expect(page.locator('.candidate-editor p[role=status]')).toContainText('published');
});
