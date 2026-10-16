import { test, expect, type Page } from '@playwright/test';
import { productCapture } from './product-capture';
import { readFileSync } from 'node:fs';
const cases = JSON.parse(
  readFileSync(
    new URL('../../../data/fixtures/domain-semantic-cases.json', import.meta.url),
    'utf8',
  ),
);
async function login(page: Page, legacy = false) {
  await page.goto('/tests/emulator-login.html');
  await page
    .getByRole('textbox', { name: 'Fictional email' })
    .fill(legacy ? 'legacy-education@example.invalid' : `meaning-${Date.now()}@example.invalid`);
  await page.getByRole('button', { name: 'Sign in to emulator' }).click();
  await expect(page).toHaveURL(/\/$/);
  await page.goto('/profile');
}
async function minimal(page: Page) {
  await login(page);
  await page.getByRole('textbox', { name: 'Profile name' }).fill('Fictional meaning learner');
  await page.getByRole('button', { name: 'Continue', exact: true }).click();
  await page.getByRole('button', { name: 'Review your answers', exact: true }).click();
  await page.getByRole('button', { name: 'Finish setup', exact: true }).click();
  await page.getByRole('button', { name: 'Edit education', exact: true }).click();
}
const enrolled = 'Are you studying anywhere right now?';
const completed = "What is the highest level of education you've completed?";
const course = 'What are you currently studying?';
test('shared semantic cases agree in actual frontend and backend specification', async ({
  page,
}) => {
  await page.goto('/');
  const actual = await page.evaluate(async (cases) => {
    // Test-only import of the same production questionnaire module used by the UI.
    const { semanticIssues } = await import('/src/features/profiles/questions.ts');
    return cases.map((c) =>
      semanticIssues(c.facts, c.before, '2026-10-16').map(
        (i: { code: string; severity: string }) => `${i.code}:${i.severity}`,
      ),
    );
  }, cases);
  expect(actual).toEqual(cases.map((c) => c.expected));
});
test('legacy hidden answers are visible, preserve reasonable graduate answers and archive only by consent', async ({
  page,
}) => {
  await login(page, true);
  await page.getByRole('button', { name: 'Edit education', exact: true }).click();
  await expect(page.getByRole('combobox', { name: enrolled })).toHaveValue('false');
  await expect(page.locator('.semantic-issue')).toContainText([
    'Full time',
    'Yes',
    'Undergraduate degree',
  ]);
  await expect(page.getByRole('combobox', { name: 'How are you studying now?' })).toHaveCount(0);
  await productCapture(page, 'common-sense-legacy-clarification-visible');
  await page.getByRole('combobox', { name: completed }).selectOption('undergraduate');
  await page.getByRole('button', { name: 'Save changes', exact: true }).click();
  await expect(page.locator('.profile-summary')).toContainText('Undergraduate degree');
  await page.reload();
  await expect(page.locator('.profile-summary')).toContainText('Undergraduate degree');
  await page.getByRole('button', { name: 'Edit education', exact: true }).click();
  // Retained legacy values do not invisibly prevent an unrelated valid qualification save.
  for (const name of [
    'How are you studying now?',
    'Is your current school government-run or officially recognized?',
    'Earlier education answer (meaning unclear)',
  ]) {
    const control = page.getByRole('button', {
      name: `Keep previous answer as historical: ${name}`,
      exact: true,
    });
    page.once('dialog', (d) => d.accept());
    await control.click();
  }
  await page.getByRole('button', { name: 'Save changes', exact: true }).click();
  await expect(
    page.getByRole('heading', { name: 'Earlier answers and when they applied' }),
  ).toBeVisible();
  await productCapture(page, 'common-sense-graduate-saved-en');
  await page.getByRole('combobox', { name: 'Interface language' }).first().selectOption('hi');
  await expect(page.locator('main')).toContainText(
    'आपने शिक्षा का कौनसा उच्चतम स्तर पूरा किया है?',
  );
  await page.setViewportSize({ width: 390, height: 900 });
  await productCapture(page, 'common-sense-graduate-hi-mobile');
});
test('current enrollment and completed qualification change independently with visible historical preservation', async ({
  page,
}) => {
  await minimal(page);
  await page.getByRole('combobox', { name: completed }).selectOption('undergraduate');
  await page.getByRole('combobox', { name: enrolled }).selectOption('true');
  await page.getByRole('combobox', { name: course }).selectOption('postgraduate');
  await page.getByRole('combobox', { name: 'How are you studying now?' }).selectOption('part_time');
  await page.getByRole('button', { name: 'Save changes', exact: true }).click();
  await productCapture(page, 'common-sense-current-completed-independent');
  await page.getByRole('button', { name: 'Edit education', exact: true }).click();
  page.once('dialog', (d) => d.dismiss());
  await page.getByRole('combobox', { name: enrolled }).selectOption('false');
  await expect(page.getByRole('combobox', { name: enrolled })).toHaveValue('true');
  page.once('dialog', (d) => d.accept());
  await page.getByRole('combobox', { name: enrolled }).selectOption('false');
  await expect(page.getByRole('combobox', { name: completed })).toHaveValue('undergraduate');
  await page.getByRole('button', { name: 'Save changes', exact: true }).click();
  await page.reload();
  await expect(page.locator('.profile-summary')).toContainText('Undergraduate degree');
  await expect(
    page.getByRole('heading', { name: 'Earlier answers and when they applied' }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Edit education', exact: true }).click();
  await page.getByRole('combobox', { name: completed }).selectOption('postgraduate');
  await expect(page.getByRole('combobox', { name: enrolled })).toHaveValue('false');
  await page.getByRole('button', { name: 'Save changes', exact: true }).click();
  await expect(page.locator('.profile-summary')).toContainText('Postgraduate degree');
});
test('fictional current-course source maps to the exact enrollment/course question; historical course never satisfies it', async ({
  page,
}) => {
  await minimal(page);
  await page.getByRole('button', { name: 'Cancel', exact: true }).click();
  await page.goto('/discover?development=true');
  await page.getByRole('link', { name: 'FICTIONAL scholarship 3', exact: true }).click();
  const opportunity = page.url();
  await page.getByRole('button', { name: 'Check my eligibility', exact: true }).click();
  await page
    .getByRole('link', { name: 'Provide missing information: Currently a student', exact: true })
    .click();
  await expect(page.getByRole('heading', { name: 'Why are we asking?' })).toBeVisible();
  await page.getByRole('combobox', { name: enrolled }).selectOption('true');
  await page.getByRole('button', { name: 'Save changes', exact: true }).click();
  await page.goto(opportunity);
  await page.getByRole('button', { name: 'Check my eligibility', exact: true }).click();
  await page
    .getByRole('link', {
      name: 'Provide missing information: Current course or class',
      exact: true,
    })
    .click();
  await expect(page.getByRole('heading', { name: 'Why are we asking?' })).toBeVisible();
  await page.getByRole('combobox', { name: course }).selectOption('postgraduate');
  await page.getByRole('button', { name: 'Save changes', exact: true }).click();
  await page.goto(opportunity);
  await page.getByRole('button', { name: 'Check my eligibility', exact: true }).click();
  await expect(page.locator('.requirement-result.satisfied')).toContainText(
    'FICTIONAL currently studying',
  );
  await page.goto('/profile?section=education');
  page.once('dialog', (d) => d.accept());
  await page.getByRole('combobox', { name: enrolled }).selectOption('false');
  await page.getByRole('button', { name: 'Save changes', exact: true }).click();
  await page.goto(opportunity);
  await page.getByRole('button', { name: 'Check my eligibility', exact: true }).click();
  await expect(page.locator('.requirement-result.unsatisfied')).toContainText(
    'supplied enrollment answer is No',
  );
  await expect(page.locator('.requirement-result.satisfied')).toHaveCount(0);
});

test('registered business separates operation, registration, activity and personal facts', async ({
  page,
}) => {
  await minimal(page);
  await page.getByRole('button', { name: 'Cancel', exact: true }).click();
  await page.goto('/businesses');
  await page
    .getByRole('textbox', { name: 'Business name' })
    .fill('Fictional cross-state enterprise');
  await page
    .getByRole('combobox', { name: 'How is your business set up?' })
    .selectOption('company');
  await page.getByRole('button', { name: 'Continue', exact: true }).click();
  await page
    .getByRole('button', { name: 'Add location or registration details if useful', exact: true })
    .click();
  await page.getByRole('combobox', { name: 'Is the business registered?' }).selectOption('true');
  await page.getByRole('textbox', { name: 'Operating state', exact: true }).fill('Rajasthan');
  await page.getByRole('textbox', { name: 'Operating district', exact: true }).fill('Dausa');
  await page
    .getByRole('textbox', { name: 'Registration state (if applicable)' })
    .fill('Maharashtra');
  await page.getByRole('textbox', { name: 'Registration district (if applicable)' }).fill('Pune');
  await page
    .getByRole('combobox', { name: 'What is the business doing now?' })
    .selectOption('active');
  await expect(page.getByRole('spinbutton', { name: 'Annual turnover (₹)' })).toHaveCount(0);
  await page.getByRole('button', { name: 'Create business', exact: true }).click();
  await expect(page.locator('.workspace-overview')).toContainText('Maharashtra');
  await page.reload();
  await expect(page.locator('.workspace-overview')).toContainText('Rajasthan');
  await expect(page.locator('.workspace-overview')).toContainText('Maharashtra');
  await productCapture(page, 'common-sense-business-geography');
  await page.locator('.shell-context select').selectOption('person:');
  await page.goto('/profile');
  await expect(page.locator('.profile-summary')).not.toContainText('Maharashtra');
});
