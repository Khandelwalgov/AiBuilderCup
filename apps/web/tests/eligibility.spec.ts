import { expect, test } from '@playwright/test';
import type { components } from '../src/lib/api/schema';

// Browser contract test only. Firebase and Gemini are NOT bypassed in application code.
// These fictional policy responses never enter the application database or public catalogue.
const id = '11111111-1111-4111-8111-111111111111';
const time = '2026-10-12T00:00:00Z';
const citation = {
  source_url: 'https://example.invalid/synthetic-test-policy',
  passage: 'Synthetic test clause: applicants must be at least eighteen.',
  page: '1',
};
const rule = {
  op: 'condition' as const,
  condition: { op: 'gte' as const, fact: 'age' as const, value: 18 },
};
const opportunity: components['schemas']['OpportunityView'] = {
  id,
  version: 1,
  publication_state: 'published',
  is_synthetic: false,
  title: 'Synthetic browser test policy',
  summary: 'Fictional policy for testing the browser contract only.',
  category: 'education',
  issuer: 'Synthetic test authority',
  status: 'verified',
  country: 'India',
  state: null,
  district: null,
  applicability: [],
  benefits: null,
  restrictions: [],
  required_documents: [],
  opens_on: null,
  closes_on: null,
  apply_url: null,
  source_url: citation.source_url,
  first_seen_at: time,
  last_verified_at: time,
  source: {
    name: 'Synthetic test source',
    authority: 'Test only',
    url: citation.source_url,
    status: 'verified',
    last_checked_at: time,
    last_successful_check_at: time,
  },
  requirements: [
    {
      id,
      description: 'Synthetic minimum age',
      rule,
      subject_context: 'person',
      citations: [citation],
    },
  ],
  field_evidence: [],
  review_flags: [],
  missing_fields: [],
};

test('profile → published opportunity → cited eligibility results (mocked auth/API contract)', async ({
  page,
}) => {
  let profile: components['schemas']['ProfileView'] | null = null;
  await page.route('**/v1/profile/me', async (route) => {
    if (route.request().method() === 'PUT') {
      const input = route.request().postDataJSON() as components['schemas']['ProfileWrite'];
      expect(input.display_name).toBe('Synthetic learner');
      expect(input.facts).toEqual([{ key: 'age', value: 20 }]);
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
  await page.getByRole('button', { name: 'Add a relevant fact' }).click();
  await page.getByRole('spinbutton', { name: 'Value 1', exact: true }).fill('20');
  await page.getByRole('button', { name: 'Save profile' }).click();
  await expect(
    page.getByText('Profile saved. You can now check a published opportunity.'),
  ).toBeVisible();
  await page.screenshot({ path: '/tmp/opportunity-profile.png', fullPage: true });
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
  await page.screenshot({ path: '/tmp/opportunity-eligibility.png', fullPage: true });
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
  await expect(page.getByRole('heading', { name: 'No opportunities found' })).toBeVisible();
  await page.goto('/profile');
  await expect(page.getByRole('alert')).toContainText('Sign in');
  await expect(page.getByRole('button', { name: 'Save profile' })).toHaveCount(0);
});

test('admin inspects evidence and publishes through the review API (mocked contract)', async ({
  page,
}) => {
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
  await page.route('**/v1/admin/reviews', (route) =>
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
  await page.getByText('Page 1 ·', { exact: false }).click();
  await expect(page.locator('.review-columns pre').first()).toContainText(citation.passage);
  await page.getByRole('textbox', { name: 'Review note' }).fill('Checked synthetic test evidence.');
  const checkboxes = page.locator('.candidate-editor input[type=checkbox]');
  await checkboxes.nth(0).check();
  await checkboxes.nth(1).check();
  await page.screenshot({ path: '/tmp/opportunity-admin.png', fullPage: true });
  await page.getByRole('button', { name: 'Approve & publish', exact: true }).click();
  await expect(page.locator('.candidate-editor [role=status]')).toContainText('published');
});
