import { productCapture } from './product-capture';
import { test, expect, type Page } from '@playwright/test';
import { readFile } from 'node:fs/promises';
async function login(page: Page, label: string) {
  await page.goto('/tests/emulator-login.html');
  await page
    .getByRole('textbox', { name: 'Fictional email' })
    .fill(`${label}-${Date.now()}@example.invalid`);
  await page.getByRole('button', { name: 'Sign in to emulator' }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(
    page.getByText('Local Firebase Auth emulator — fictional accounts only'),
  ).toBeVisible();
}
async function profile(page: Page, name: string) {
  await page.goto('/profile');
  await page.getByRole('textbox', { name: 'Profile name' }).fill(name);
  await page.getByRole('button', { name: 'Education', exact: true }).click();
  await page.getByRole('button', { name: 'Continue', exact: true }).click();
  await page
    .getByRole('combobox', { name: 'Are you studying anywhere right now?' })
    .selectOption('true');
  await page
    .getByRole('combobox', { name: 'What are you currently studying?' })
    .selectOption('undergraduate');
  await page.getByRole('button', { name: 'Review your answers', exact: true }).click();
  await page.getByRole('button', { name: 'Finish setup', exact: true }).click();
  await expect(page.locator('.profile-summary')).toContainText(name);
}
async function upload(page: Page, name: string, extension = 'pdf') {
  await page.getByRole('textbox', { name: 'Recognizable name' }).fill(name);
  await page
    .getByLabel('Choose a PDF, JPEG or PNG')
    .setInputFiles(
      extension === 'pdf'
        ? '../../data/fixtures/documents/fictional-income.pdf'
        : `../../data/fixtures/documents/fictional-certificate.${extension}`,
    );
  await page.getByRole('checkbox', { name: /I authorize using this file/ }).check();
  await page.getByRole('button', { name: 'Save private file', exact: true }).click();
  await expect(
    page.getByRole('status').filter({ hasText: 'Document saved privately' }),
  ).toBeVisible();
}
test('real emulator + API/PostgreSQL/private file journey, compatible reuse, download, replace and delete', async ({
  page,
}) => {
  const started = Date.now();
  await login(page, 'learner');
  await profile(page, 'Fictional real-flow learner');
  const onboardingMs = Date.now() - started;
  await page.goto('/discover?development=true&mode=explore');
  await page.getByRole('link', { name: 'FICTIONAL scholarship 1', exact: true }).click();
  await page.getByRole('button', { name: 'Check my eligibility', exact: true }).click();
  await expect(
    page
      .locator('.requirement-result.unknown')
      .filter({ hasText: 'FICTIONAL parental income certificate needed' }),
  ).toBeVisible();
  const opportunityUrl = page.url();
  await page
    .getByRole('link', { name: 'Provide missing information: Age (years)', exact: true })
    .click();
  await expect(page.getByRole('heading', { name: 'Why are we asking?' })).toBeVisible();
  await page.getByRole('spinbutton', { name: 'How old are you?' }).fill('20');
  await page.getByRole('button', { name: 'Save changes', exact: true }).click();
  await page.goto(opportunityUrl);
  await page.getByRole('button', { name: 'Check my eligibility', exact: true }).click();
  await expect(page.locator('.requirement-result.satisfied')).toContainText(
    'FICTIONAL minimum age is eighteen',
  );
  await page
    .locator('.requirement-result.unknown')
    .getByRole('link', { name: 'Add or manage document' })
    .click();
  await expect(page).toHaveURL(/\/documents\?/);
  await page.getByRole('checkbox', { name: 'Also use for: FICTIONAL scholarship 2' }).check();
  await productCapture(page, 'product-real-upload-en');
  await upload(page, 'Fictional shared income PDF');
  await page.reload();
  await expect(page.locator('.document-card')).toContainText('Fictional shared income PDF');
  await expect(page.locator('.document-card')).toContainText('Uploaded — not verified');
  await expect(page.locator('.document-card a')).toHaveCount(2);
  await page
    .locator('.document-card')
    .getByRole('button', { name: 'Preview', exact: true })
    .click();
  await expect(page.getByRole('region', { name: 'Private preview' })).toBeVisible();
  await expect(page.locator('.private-preview iframe')).toHaveAttribute('src', /^blob:/);
  await page.getByRole('button', { name: 'Close preview' }).click();
  const downloading = page.waitForEvent('download');
  await page
    .locator('.document-card')
    .getByRole('button', { name: 'Download', exact: true })
    .click();
  const download = await downloading;
  expect(await readFile((await download.path())!)).toEqual(
    await readFile('../../data/fixtures/documents/fictional-income.pdf'),
  );
  await page.goto('/plan?development=true');
  await page.locator('.atlas-node.action').first().click();
  await expect(page.locator('main')).toContainText('Uploaded — not verified');
  await expect(page.locator('.evidence-card')).toHaveCount(2);
  await expect(page.locator('main')).toContainText('Cannot yet determine');
  await productCapture(page, 'product-real-shared-graph-en');
  await page.goto('/documents?development=true');
  await page
    .locator('.document-card')
    .getByRole('button', { name: 'Replace', exact: true })
    .click();
  await upload(page, 'Fictional replacement JPEG', 'jpg');
  await expect(page.locator('.document-card')).toHaveCount(1);
  await expect(page.locator('.document-card')).toContainText('Fictional replacement JPEG');
  await page
    .locator('.document-card')
    .getByRole('button', { name: 'Preview', exact: true })
    .click();
  await expect(page.locator('.private-preview img')).toBeVisible();
  await productCapture(page, 'product-real-vault-preview-en');
  await page.setViewportSize({ width: 390, height: 900 });
  await page.getByRole('combobox', { name: 'Interface language' }).first().selectOption('hi');
  await productCapture(page, 'product-real-vault-hi-mobile');
  await page.getByRole('combobox', { name: 'इंटरफ़ेस की भाषा' }).first().selectOption('en');
  await page.locator('.document-card').getByRole('button', { name: 'Remove', exact: true }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Remove file', exact: true }).click();
  await expect(page.locator('.document-card')).toHaveCount(0);
  await expect(page.getByRole('heading', { name: 'No documents yet' })).toBeVisible();
  console.log(
    JSON.stringify({
      scenario: 'fictional learner initial setup including emulator login',
      automation_duration_ms: onboardingMs,
      profile_answers: 2,
      skipped_optional_questions: 3,
      real_persistence: true,
    }),
  );
});

async function statusAsSignedIn(page: Page, path: string) {
  return page.evaluate(async (path) => {
    const modulePath = '/src/app/auth.ts';
    const module = await import(modulePath);
    const token = await module.auth.currentUser.getIdToken();
    return (await fetch(path, { headers: { Authorization: `Bearer ${token}` } })).status;
  }, path);
}
test('real guardian/dependent and business ownership, revoked and unrelated account denial', async ({
  page,
  browser,
}) => {
  await login(page, 'guardian');
  await profile(page, 'Fictional guardian profile');
  await page.goto('/family');
  await expect(
    page.getByRole('heading', { name: 'Create your household', exact: true }),
  ).toBeVisible();
  await productCapture(page, 'product-real-family-empty-en');
  await page.getByRole('textbox', { name: 'Household name' }).fill('Fictional test household');
  await page.getByRole('button', { name: 'Create household', exact: true }).click();
  await expect(page.locator('.workspace-overview')).toContainText('Fictional test household');
  await page
    .getByRole('textbox', { name: 'Dependent’s name or nickname' })
    .fill('Fictional dependent');
  await page.getByRole('spinbutton', { name: 'Age (optional)' }).fill('12');
  await page.getByRole('checkbox', { name: /I am the legal guardian/ }).check();
  await page.getByRole('button', { name: 'Add dependent', exact: true }).click();
  await page
    .locator('.member-row')
    .filter({ hasText: 'Fictional dependent' })
    .getByRole('link', { name: 'Profile and questions', exact: true })
    .click();
  await expect(page.locator('.profile-summary')).toContainText('Fictional dependent');
  await page.getByRole('button', { name: 'Edit about you' }).click();
  await page.getByRole('spinbutton', { name: 'How old are you?' }).fill('13');
  await page.getByRole('button', { name: 'Save changes', exact: true }).click();
  await expect(page.locator('.profile-summary')).toContainText('13');
  await page.getByRole('link', { name: 'Open My Documents', exact: true }).click();
  await page.getByRole('button', { name: 'Upload a document', exact: true }).click();
  await page
    .getByRole('combobox', { name: 'Document type', exact: true })
    .selectOption('age_proof');
  await upload(page, 'Fictional dependent age evidence', 'png');
  const docId = (await page.locator('.document-card').getAttribute('data-document-id'))!;
  const dependentUrl = page.url();
  await expect(page.locator('.document-toolbar')).toContainText('Dependent · Fictional dependent');
  const other = await browser.newContext();
  const stranger = await other.newPage();
  await login(stranger, 'unrelated');
  await profile(stranger, 'Fictional unrelated account');
  expect(await statusAsSignedIn(stranger, `/v1/documents/${docId}`)).toBe(404);
  await stranger.goto('/documents');
  await expect(stranger.locator('.document-card')).toHaveCount(0);
  await other.close();
  await page.goto('/family');
  await productCapture(page, 'product-real-family-populated-en');
  page.once('dialog', (d) => d.accept());
  await page.getByRole('button', { name: 'Stop managing', exact: true }).click();
  await expect(page.getByRole('link', { name: 'Profile and questions' })).toHaveCount(0);
  expect(await statusAsSignedIn(page, `/v1/documents/${docId}`)).toBe(404);
  await page.goto(dependentUrl);
  await expect(page.getByRole('alert')).toContainText('This context is unavailable');
  await expect(page.locator('.document-card')).toHaveCount(0);
  await page.goto('/businesses');
  await expect(
    page.getByRole('heading', { name: 'Create your business', exact: true }),
  ).toBeVisible();
  await productCapture(page, 'product-real-business-empty-en');
  await page.getByRole('textbox', { name: 'Business name' }).fill('Fictional informal business');
  await expect(page.getByRole('spinbutton', { name: 'Annual turnover (₹)' })).toHaveCount(0);
  await page.getByRole('button', { name: 'Continue', exact: true }).click();
  await page
    .getByRole('button', { name: 'Add location or registration details if useful', exact: true })
    .click();
  await page.getByRole('combobox', { name: 'Is the business registered?' }).selectOption('false');
  await page.getByRole('textbox', { name: 'Operating state' }).fill('Rajasthan');
  await page.getByRole('textbox', { name: 'Operating district' }).fill('Dausa');
  await page.getByRole('button', { name: 'Create business', exact: true }).click();
  await expect(page.locator('.workspace-overview')).toContainText('Fictional informal business');
  await page.getByRole('button', { name: 'Edit details', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Save changes', exact: true })).toBeDisabled();
  await page.getByRole('textbox', { name: 'Business name' }).fill('Fictional business revised');
  await page.getByRole('button', { name: 'Save changes', exact: true }).click();
  await expect(page.locator('.workspace-overview')).toContainText('Fictional business revised');
  await expect(page.getByRole('button', { name: 'Save changes', exact: true })).toHaveCount(0);
  await productCapture(page, 'product-real-business-overview-en');
  await page.getByRole('link', { name: 'Business documents', exact: true }).click();
  await page.getByRole('button', { name: 'Upload a document', exact: true }).click();
  await upload(page, 'Fictional business address evidence', 'png');
  await expect(page.locator('.document-card')).toContainText(
    'Business · Fictional business revised',
  );
  await productCapture(page, 'product-real-business-document-en');
  await page.locator('.shell-context select').selectOption('person:');
  await expect(page.locator('.document-card')).toHaveCount(0);
  await expect(page.locator('main')).not.toContainText('Fictional business address evidence');
});

test('real storage recovers after transport interruption and refresh; failed profile save keeps edits', async ({
  page,
}) => {
  await login(page, 'recovery');
  await profile(page, 'Fictional recovery learner');
  await page.goto('/documents');
  await page.getByRole('button', { name: 'Upload a document', exact: true }).click();
  let intents = 0;
  page.on('request', (request) => {
    if (new URL(request.url()).pathname === '/v1/documents' && request.method() === 'POST')
      intents++;
  });
  await page.route('**/v1/documents/*/content', (r) => r.abort('failed'), { times: 1 });
  await page
    .getByRole('textbox', { name: 'Recognizable name' })
    .fill('Fictional interrupted upload');
  await page
    .getByLabel('Choose a PDF, JPEG or PNG')
    .setInputFiles('../../data/fixtures/documents/fictional-income.pdf');
  await page.getByRole('checkbox', { name: /I authorize using this file/ }).check();
  await page.getByRole('button', { name: 'Save private file', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Your file selection and details remain');
  await expect(page.getByRole('textbox', { name: 'Recognizable name' })).toHaveValue(
    'Fictional interrupted upload',
  );
  page.once('dialog', (d) => d.accept());
  await page.reload();
  await expect(page.locator('.document-card')).toContainText('Upload incomplete — retry');
  await page
    .locator('.document-card')
    .getByRole('button', { name: 'Retry upload', exact: true })
    .click();
  await page
    .getByLabel('Choose a PDF, JPEG or PNG')
    .setInputFiles('../../data/fixtures/documents/fictional-income.pdf');
  await page.getByRole('checkbox', { name: /I authorize using this file/ }).check();
  await page
    .locator('.document-upload')
    .getByRole('button', { name: 'Retry upload', exact: true })
    .click();
  await expect(page.locator('.document-card')).toContainText('Uploaded — not verified');
  expect(intents).toBe(1);
  await page.goto('/profile');
  await page.getByRole('button', { name: 'Edit about you' }).click();
  await page.getByRole('textbox', { name: 'Profile name' }).fill('Fictional unsaved recovery');
  await page.route(
    '**/v1/profile/me',
    (r) => (r.request().method() === 'PUT' ? r.abort('failed') : r.continue()),
    { times: 1 },
  );
  await page.getByRole('button', { name: 'Save changes', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Your answers are still here');
  await expect(page.getByRole('textbox', { name: 'Profile name' })).toHaveValue(
    'Fictional unsaved recovery',
  );
  page.once('dialog', (d) => d.dismiss());
  await page.getByRole('link', { name: 'Discover opportunities', exact: true }).click();
  await expect(page).toHaveURL(/\/profile$/);
  await page.getByRole('button', { name: 'Save changes', exact: true }).click();
  await expect(page.locator('.profile-summary')).toContainText('Fictional unsaved recovery');
  await page.reload();
  await expect(page.locator('.profile-summary')).toContainText('Fictional unsaved recovery');
});

test('real concurrent profile edits preserve the stale draft and reject duplicate pending saves', async ({
  page,
  context,
}) => {
  await login(page, 'concurrency');
  await profile(page, 'Fictional concurrent learner');
  await page.getByRole('button', { name: 'Edit about you' }).click();
  await page.getByRole('textbox', { name: 'Profile name' }).fill('Fictional stale local draft');
  const other = await context.newPage();
  await other.goto('/profile');
  await other.getByRole('button', { name: 'Edit about you' }).click();
  await other.getByRole('textbox', { name: 'Profile name' }).fill('Fictional winning saved edit');
  await other.getByRole('button', { name: 'Save changes', exact: true }).click();
  await expect(other.locator('.profile-summary')).toContainText('Fictional winning saved edit');
  await page.getByRole('button', { name: 'Save changes', exact: true }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Stale edit' })).toBeVisible();
  await expect(page.getByRole('textbox', { name: 'Profile name' })).toHaveValue(
    'Fictional stale local draft',
  );
  page.once('dialog', (d) => d.accept());
  await page.getByRole('button', { name: 'Reload saved version', exact: true }).click();
  await expect(page.locator('.profile-summary')).toContainText('Fictional winning saved edit');
  await page.getByRole('button', { name: 'Edit about you' }).click();
  await expect(page.getByRole('textbox', { name: 'Profile name' })).toHaveValue(
    'Fictional winning saved edit',
  );
  await page.getByRole('textbox', { name: 'Profile name' }).fill('Fictional final saved edit');
  let writes = 0;
  let release!: () => void;
  const pending = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route('**/v1/profile/me', async (route) => {
    if (route.request().method() === 'PUT') {
      writes++;
      await pending;
    }
    await route.continue();
  });
  await page.getByRole('button', { name: 'Save changes', exact: true }).click();
  await expect(page.getByRole('textbox', { name: 'Profile name' })).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Saving…', exact: true })).toBeDisabled();
  release();
  await expect(page.locator('.profile-summary')).toContainText('Fictional final saved edit');
  expect(writes).toBe(1);
  await other.close();
});
