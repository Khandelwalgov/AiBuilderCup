import { captureContract } from './capture';
import { expect, test } from '@playwright/test';
import type { components } from '../src/lib/api/schema';
const id = '11111111-1111-4111-8111-111111111111';
const second = '22222222-2222-4222-8222-222222222222';
const artifacts = '/Users/govind/Projects/AIBuildersCup/.live-validation/ui';
// All identities and policy data in these UI contracts are fictional. No auth bypass is shipped.
test('household and unregistered business creation controls (mocked API)', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 960 });
  let workspaces: components['schemas']['WorkspaceView'][] = [];
  await page.route('**/v1/workspaces', (route) => route.fulfill({ json: workspaces }));
  await page.route('**/v1/households', async (route) => {
    expect(route.request().postDataJSON()).toEqual({ name: 'Fictional household', primary: true });
    const household = {
      id,
      kind: 'household' as const,
      name: 'Fictional household',
      role: 'owner',
      members: [],
      facts: [],
    };
    workspaces = [household];
    await route.fulfill({ json: household });
  });
  await page.route(`**/v1/households/${id}`, async (route) => {
    expect(route.request().method()).toBe('PUT');
    expect(route.request().postDataJSON()).toEqual({
      name: 'Fictional household revised',
      primary: true,
    });
    workspaces[0].name = 'Fictional household revised';
    await route.fulfill({ json: workspaces[0] });
  });
  await page.route(`**/v1/households/${id}/dependents`, async (route) => {
    expect(route.request().postDataJSON().guardian_responsibility_confirmed).toBe(true);
    workspaces[0].members = [
      { id: second, name: 'Fictional dependent', access: 'authorized', managed: true },
    ];
    await route.fulfill({
      json: {
        id: second,
        kind: 'person',
        name: 'Fictional dependent',
        role: 'owner',
        facts: [],
        members: [],
      },
    });
  });
  await page.route(`**/v1/people/${second}/guardian-access/revoke`, async (route) => {
    expect(route.request().postDataJSON()).toEqual({ confirm_revocation: true });
    workspaces[0].members = [{ name: 'Adult authorization required', access: 'restricted' }];
    await route.fulfill({ json: { status: 'guardian_access_revoked' } });
  });
  await page.route('**/v1/businesses', async (route) => {
    const body = route.request().postDataJSON();
    expect(body.legal_status).toBe('unregistered');
    expect(body).not.toHaveProperty('gst');
    const business = {
      id: second,
      kind: 'business' as const,
      name: body.name,
      role: 'owner',
      legal_status: 'unregistered',
      facts: body.facts,
      members: [],
    };
    workspaces.push(business);
    await route.fulfill({ json: business });
  });
  await page.goto('/family');
  await page.getByRole('textbox', { name: 'Name', exact: true }).fill('Fictional household');
  await page.getByRole('button', { name: 'Save context', exact: true }).click();
  await expect(
    page.getByRole('heading', { name: 'Fictional household', exact: true }),
  ).toBeVisible();
  await page
    .getByRole('textbox', { name: 'Household name', exact: true })
    .fill('Fictional household revised');
  await page.getByRole('button', { name: 'Save and make primary household' }).click();
  await expect(
    page.getByRole('heading', { name: 'Fictional household revised', exact: true }),
  ).toBeVisible();
  await page.getByRole('textbox', { name: 'Profile name' }).fill('Fictional dependent');
  await page.getByRole('checkbox').check();
  await page.getByRole('button', { name: 'Add dependent', exact: true }).click();
  await expect(page.getByText('Fictional dependent', { exact: true })).toBeVisible();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: `${artifacts}/family-populated-contract-1440.png`,
    fullPage: true,
  });
  await captureContract(page, 'family');
  page.once('dialog', (dialog) => dialog.accept());
  await page.getByRole('button', { name: 'Stop managing', exact: true }).click();
  await expect(page.getByText('Adult authorization required')).toBeVisible();
  await expect(page.getByText('Fictional dependent', { exact: true })).toHaveCount(0);
  await page.goto('/businesses');
  await page.getByRole('textbox', { name: 'Name', exact: true }).fill('Fictional microbusiness');
  await page.getByRole('button', { name: 'Save context', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Edit business' })).toBeVisible();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: `${artifacts}/business-populated-contract-1440.png`,
    fullPage: true,
  });
  await captureContract(page, 'business');
});

test('shared graph action, evidence panel and non-saving simulation (mocked API)', async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 960 });
  const citation = {
    source_url: 'https://example.invalid/fictional-policy',
    page: '1',
    passage: 'Fictional income evidence requirement for browser testing only.',
  };
  const evaluations = [id, second].map((identifier, i) => ({
    id: identifier,
    opportunity_id: identifier,
    version_id: identifier,
    version: 1,
    opportunity_title: `Fictional opportunity ${i + 1}`,
    evaluated_at: '2026-10-14T00:00:00Z',
    status: 'possibly_eligible_missing_information',
    requirements: [],
    disclaimer: 'Fictional assessment only.',
  }));
  const action = {
    id,
    title: 'Verify evidence: fictional income certificate',
    status: 'pending',
    identity: 'fictional-shared-evidence',
    kind: 'document',
    explanation: 'Fictional shared action for UI tests.',
    opportunities: [id, second].map((identifier) => ({
      id: identifier,
      version_id: identifier,
      requirement_id: identifier,
      requirement: 'Fictional cited evidence condition',
      citations: [citation],
    })),
  };
  const plan = {
    subject: { kind: 'person', id },
    hypothetical: false,
    evaluations,
    actions: [action],
    known_blockers: [],
  };
  await page.route('**/v1/workspaces', (route) => route.fulfill({ json: [] }));
  await page.route('**/v1/plan', (route) => route.fulfill({ json: plan }));
  await page.route(`**/v1/actions/${id}`, async (route) => {
    expect(route.request().postDataJSON()).toEqual({ status: 'in_progress' });
    action.status = 'in_progress';
    await route.fulfill({ json: { status: 'in_progress' } });
  });
  await page.route('**/v1/plan/simulate', async (route) => {
    expect(route.request().postDataJSON().facts).toEqual([{ key: 'age', value: 12 }]);
    await route.fulfill({
      json: {
        ...plan,
        hypothetical: true,
        evaluations: evaluations.map((ev) => ({ ...ev, status: 'not_eligible_on_known_facts' })),
        known_blockers: [{ requirement: 'Fictional known age restriction remains' }],
      },
    });
  });
  await page.goto('/plan');
  await page
    .locator('.atlas-node.action')
    .filter({ hasText: 'fictional income certificate' })
    .click();
  await expect(page.locator('.evidence-card')).toHaveCount(2);
  await expect(page.locator('.atlas-edges > path.illuminated')).toHaveCount(3);
  await page.getByRole('button', { name: 'Zoom out', exact: true }).click();
  await expect(page.getByLabel('Graph zoom')).toHaveText('85%');
  await page.getByRole('button', { name: 'Fit graph to view' }).click();
  await expect(page.getByLabel('Graph zoom')).toHaveText('100%');
  await expect(page.locator('.evidence-card blockquote').first()).toContainText(citation.passage);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: `${artifacts}/graph-populated-contract-1440.png`, fullPage: true });
  await captureContract(page, 'graph');
  await page.getByRole('button', { name: 'Mark in progress', exact: true }).click();
  await expect(
    page
      .getByRole('button', { name: 'Verify evidence: fictional income certificate', exact: false })
      .first(),
  ).toBeVisible();
  await page
    .locator('.atlas-node.action')
    .filter({ hasText: 'fictional income certificate' })
    .click();
  await expect(page.getByText('Task status: In progress')).toBeVisible();
  await page.getByRole('spinbutton', { name: 'Hypothetical age' }).fill('12');
  await page.getByRole('button', { name: 'Preview assessment', exact: true }).click();
  await expect(
    page.getByText('Hypothetical preview. No stored facts or evidence have changed.'),
  ).toBeVisible();
  await expect(page.getByText('Fictional known age restriction remains')).toBeVisible();
  await page.setViewportSize({ width: 320, height: 900 });
  await page.getByRole('combobox', { name: 'Interface language' }).selectOption('hi');
  await expect(page.getByRole('heading', { name: 'अंतर से अगले कदम तक' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: `${artifacts}/graph-populated-contract-hi-320.png`,
    fullPage: true,
  });
});
