import { test, expect, type Page, type Locator } from '@playwright/test';
import { productCapture } from './product-capture';
async function login(page: Page) {
  await page.goto('/tests/emulator-login.html');
  await page
    .getByRole('textbox', { name: 'Fictional email' })
    .fill(`research-${Date.now()}-${Math.random().toString(36).slice(2)}@example.invalid`);
  await page.getByRole('button', { name: 'Sign in to emulator' }).click();
  await expect(page).toHaveURL(/\/$/);
  await page.goto('/profile');
  await page.getByRole('textbox', { name: 'Profile name' }).fill('Fictional research graduate');
  await page.getByRole('button', { name: 'Continue', exact: true }).click();
  await page.getByRole('button', { name: 'Review your answers', exact: true }).click();
  await page.getByRole('button', { name: 'Finish setup', exact: true }).click();
}
async function profile(page: Page) {
  // Uses the actual typed client and official SDK's emulator session, never an auth override.
  return page.evaluate(async () => {
    const { api } = await import('/src/lib/api/client.ts');
    return (await api.GET('/v1/profile/me')).data;
  });
}
async function reachCard(page: Page, card: Locator) {
  // Source-backed mismatches remain reachable, but no longer lead recommendations.
  for (let attempt = 0; attempt < 20 && !(await card.count()); attempt++) {
    const more = page.getByRole('button', { name: 'More personalized results' });
    await expect(more).toBeEnabled();
    const priorTitle = await page.locator('.research-guide-card h3').first().textContent();
    await Promise.all([
      page.waitForResponse(
        (r) =>
          r.url().endsWith('/v1/research-opportunities/guidance') &&
          r.request().method() === 'POST',
      ),
      more.click(),
    ]);
    await expect(page.locator('.research-guide-card h3').first()).not.toHaveText(priorTitle || '');
  }
  await expect(card).toHaveCount(1);
  const group = card.locator(
    'xpath=ancestor::details[contains(@class,"research-relevance-group")][1]',
  );
  if ((await group.count()) && !(await group.evaluate((el) => (el as HTMLDetailsElement).open)))
    await group.locator(':scope > summary').click();
}
test('real-source automatic personal discovery, cited plan and nonpersistent enrollment scenario', async ({
  page,
}) => {
  await login(page);
  const status = await page.evaluate(async () => {
    const { api } = await import('/src/lib/api/client.ts');
    return (
      await api.PUT('/v1/profile/me', {
        body: {
          display_name: 'Fictional research graduate',
          facts: [
            { key: 'age', value: 22 },
            { key: 'domicile_state', value: 'Rajasthan' },
            { key: 'residence_state', value: 'Karnataka' },
            { key: 'highest_completed_education', value: 'undergraduate' },
            { key: 'student_status', value: false },
          ],
        },
      })
    ).response.status;
  });
  expect(status).toBe(200);
  await page.goto('/profile');
  await expect(page.locator('main')).toContainText('Undergraduate degree');
  const before = await profile(page);
  await page.goto('/discover');
  await expect(page.getByRole('textbox', { name: 'Search (optional)' })).toBeEmpty();
  const st = page.getByRole('article').filter({
    has: page.getByRole('heading', {
      name: 'Post-Matric Scholarship for Scheduled Tribe Students',
      exact: true,
    }),
  });
  await reachCard(page, st);
  await expect(st).toBeVisible();
  await st.getByText('Conditions, gaps and next steps', { exact: true }).click();
  await expect(st).toContainText('Known mismatch');
  await expect(st).toContainText('Condition met by supplied facts');
  await expect(st).toContainText('ST category recognized for the actual domicile state');
  await expect(
    st.getByRole('link', { name: 'Official evidence · Page 3' }).first(),
  ).toHaveAttribute('href', /government-sources.*page=3/);
  await productCapture(page, 'research-real-discover-cited');
  await st.getByRole('link', { name: 'Official evidence · Page 3' }).first().click();
  await expect(page.locator('#page-3')).toHaveAttribute('open', '');
  await expect(page.locator('#page-3')).toContainText('Conditions of eligibility');
  await page.goto('/discover');
  const firstTitle = await page.locator('.research-guide-card h3').first().innerText();
  await page.getByRole('button', { name: 'More personalized results' }).click();
  await expect(page.locator('.research-guide-card h3').first()).not.toHaveText(firstTitle);
  await page.goto('/plan');
  const tasks = page.getByRole('region', { name: 'Research readiness tasks' });
  await expect(tasks).toContainText('Record enrollment only after it occurs');
  await tasks.getByRole('button', { name: 'Mark my preparation task complete' }).first().click();
  await expect(tasks.getByRole('button', { name: 'Reopen task' }).first()).toBeVisible();
  await productCapture(page, 'research-real-unlock-task');
  expect(await profile(page)).toEqual(before);
  await page.goto('/scenarios');
  await page
    .getByRole('combobox', { name: 'Fact to change' })
    .first()
    .selectOption('student_status');
  await page.getByRole('button', { name: 'Add fact override', exact: true }).first().click();
  await page.getByRole('combobox', { name: 'Hypothetical value' }).selectOption('true');
  await page.getByRole('button', { name: 'Run scenario', exact: true }).click();
  const results = page.locator('[aria-label="Scenario results"]');
  await expect(results).toContainText('Known mismatch → Condition met by supplied facts');
  await expect(results).toContainText(
    'Unknown / confirmation needed → Unknown / confirmation needed',
  );
  expect(await profile(page)).toEqual(before);
  await productCapture(page, 'research-real-enrollment-scenario');
  await page.getByRole('button', { name: 'Reset / discard', exact: true }).click();
  await expect(results).toHaveCount(0);
  expect(await profile(page)).toEqual(before);
  await page.goto('/discover');
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole('combobox', { name: 'Interface language' }).selectOption('hi');
  await expect(page.getByRole('heading', { name: 'आपके लिए सरकारी अवसर' })).toBeVisible();
  await expect(page.locator('.research-guide-card').first()).toBeVisible();
  await productCapture(page, 'research-real-discover-mobile-hi');
});

test('real-source business requirements, grouped components and hypothetical Udyam status', async ({
  page,
}) => {
  await login(page);
  await page.goto('/businesses');
  await page
    .getByRole('textbox', { name: 'Business name', exact: true })
    .fill('Fictional source-backed enterprise');
  await page.getByRole('button', { name: 'Continue', exact: true }).click();
  await page
    .getByRole('button', { name: 'Add location or registration details if useful' })
    .click();
  await page.getByRole('combobox', { name: 'Udyam registered', exact: true }).selectOption('false');
  await page
    .getByRole('combobox', { name: 'Udyam classification', exact: true })
    .selectOption('small');
  await page
    .getByRole('combobox', { name: 'Business sector', exact: true })
    .selectOption('services');
  await page.getByRole('button', { name: 'Create business', exact: true }).click();
  await page.goto('/discover?mode=business');
  await page
    .getByRole('combobox', { name: 'Selected profile' })
    .selectOption({ label: 'Business · Fictional source-backed enterprise' });
  const team = page
    .getByRole('article')
    .filter({ has: page.getByRole('heading', { name: 'MSME TEAM', exact: true }) });
  await reachCard(page, team);
  await expect(team).toBeVisible();
  await team.getByText('Conditions, gaps and next steps', { exact: true }).click();
  await expect(team).toContainText('Known mismatch');
  await expect(team).toContainText('Programme components (5)');
  await expect(page.locator('.research-guide-card')).not.toContainText(['Scholarship']);
  await page.getByRole('link', { name: 'Scenario Studio', exact: true }).click();
  await page
    .getByRole('combobox', { name: 'Fact to change' })
    .first()
    .selectOption('business_udyam_registered');
  await page.getByRole('button', { name: 'Add fact override', exact: true }).first().click();
  await page.getByRole('combobox', { name: 'Hypothetical value' }).selectOption('true');
  await page.getByRole('button', { name: 'Run scenario', exact: true }).click();
  await expect(page.locator('[aria-label="Scenario results"]')).toContainText(
    'Known mismatch → Condition met by supplied facts',
  );
  await productCapture(page, 'research-real-business-scenario');
  await page.getByRole('link', { name: 'Discover opportunities', exact: true }).click();
  await page.getByRole('combobox', { name: 'Search context' }).selectOption('me');
  await expect(page.locator('.shell-context select')).toHaveValue('person:');
  const nextPlan = page.waitForRequest(
    (r) => new URL(r.url()).pathname === '/v1/plan' && r.method() === 'POST',
  );
  await page.getByRole('link', { name: 'Unlock plan', exact: true }).click();
  expect((await nextPlan).postDataJSON().subject).toEqual({ kind: 'person', id: null });
});

test('real family research compares each dependent and revocation removes their assessment', async ({
  page,
}) => {
  await login(page);
  await page.goto('/family');
  await page
    .getByRole('textbox', { name: 'Household name', exact: true })
    .fill('Fictional research family');
  await page.getByRole('button', { name: 'Create household', exact: true }).click();
  for (const [name, age] of [
    ['Fictional daughter IX', '14'],
    ['Fictional daughter XII', '17'],
  ]) {
    await page.getByRole('textbox', { name: 'Dependent’s name or nickname' }).fill(name);
    await page.getByRole('spinbutton', { name: 'Age (optional)' }).fill(age);
    await page.getByRole('checkbox', { name: /I am the legal guardian/ }).check();
    await page.getByRole('button', { name: 'Add dependent', exact: true }).click();
    await expect(page.locator('.member-row').filter({ hasText: name })).toBeVisible();
  }
  const ids = await page.evaluate(async () => {
    const { api } = await import('/src/lib/api/client.ts');
    const workspaces = (await api.GET('/v1/workspaces')).data!;
    const household = workspaces.find((w) => w.name === 'Fictional research family')!;
    const children = household.members.filter((m) => m.managed);
    for (const child of children) {
      const response = await api.PUT('/v1/people/{identifier}', {
        params: { path: { identifier: String(child.id) } },
        body: {
          display_name: String(child.name),
          facts: [
            { key: 'student_status', value: true },
            {
              key: 'current_education_level',
              value: String(child.name).endsWith('IX') ? 'IX' : 'XII',
            },
            { key: 'enrollment_mode', value: 'full_time' },
          ],
        },
      });
      if (response.response.status !== 200) throw new Error('Fictional dependent setup failed');
    }
    return { household: household.id, children: children.map((c) => String(c.id)) };
  });
  await page.goto(`/discover?mode=family&kind=household&id=${ids.household}`);
  await page.getByRole('textbox', { name: 'Search (optional)' }).fill('YASASVI');
  const first = page
    .locator('.research-guide-card')
    .filter({ hasText: 'Fictional daughter IX' })
    .filter({ hasText: 'PM-YASASVI — Pre-Matric Scholarship' });
  const second = page
    .locator('.research-guide-card')
    .filter({ hasText: 'Fictional daughter XII' })
    .filter({ hasText: 'PM-YASASVI — Pre-Matric Scholarship' });
  await expect(first).toBeVisible();
  await first.getByText('Conditions, gaps and next steps', { exact: true }).click();
  await expect(first).toContainText('Condition met by supplied facts');
  // Expanded programme coverage is paginated; later known mismatches remain reachable.
  await reachCard(page, second);
  await expect(second).toBeVisible();
  await second.getByText('Conditions, gaps and next steps', { exact: true }).click();
  await expect(second).toContainText('Known mismatch');
  await productCapture(page, 'research-real-family-separate-conditions');
  const status = await page.evaluate(async (id) => {
    const { api } = await import('/src/lib/api/client.ts');
    return (
      await api.POST('/v1/people/{identifier}/guardian-access/revoke', {
        body: { confirm_revocation: true },
        params: { path: { identifier: id } },
      })
    ).response.status;
  }, ids.children[0]);
  expect(status).toBe(200);
  await page.reload();
  await expect(
    page.locator('.research-guide-card').filter({ hasText: 'Fictional daughter IX' }),
  ).toHaveCount(0);
  await page.getByRole('button', { name: 'Account menu' }).click();
  await page.getByRole('menuitem', { name: 'Sign out', exact: true }).click();
  await expect(page.locator('.research-guidance')).toHaveCount(0);
});
