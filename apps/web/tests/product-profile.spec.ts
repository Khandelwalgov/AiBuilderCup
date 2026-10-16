import { productCapture } from './product-capture';
import { test, expect } from '@playwright/test';
import { sessionFixture } from './session-fixture';
test('first-time learner gets a short conditional flow, saved summary and individual editing', async ({
  page,
}) => {
  await sessionFixture(page);
  let profile: Record<string, unknown> | null = null;
  let writes = 0;
  await page.route('**/v1/profile/me', (r) => {
    if (r.request().method() === 'PUT') {
      writes++;
      const p = r.request().postDataJSON();
      profile = {
        id: '11111111-1111-4111-8111-111111111111',
        display_name: p.display_name,
        revision: 'a'.repeat(64),
        facts: p.facts.map((f: Record<string, unknown>) => ({
          ...f,
          id: crypto.randomUUID(),
          origin: f.value == null ? 'unknown' : 'user_supplied',
          verification: 'unverified',
          context: {},
        })),
      };
      return r.fulfill({ json: profile });
    }
    return profile
      ? r.fulfill({ json: profile })
      : r.fulfill({
          status: 404,
          json: { error: { code: 'profile_not_found', message: 'Create a profile' } },
        });
  });
  await page.goto('/profile');
  await page.getByRole('textbox', { name: 'Profile name' }).fill('Fictional learner');
  await page.getByRole('button', { name: 'Education', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Education', exact: true })).toHaveAttribute(
    'aria-pressed',
    'true',
  );
  await productCapture(page, 'product-profile-new-en');
  await page.getByRole('button', { name: 'Continue', exact: true }).click();
  await expect(
    page.getByRole('combobox', { name: 'Are you studying anywhere right now?' }),
  ).toBeVisible();
  await expect(page.getByRole('combobox', { name: 'How are you studying now?' })).toHaveCount(0);
  await page
    .getByRole('combobox', { name: 'Are you studying anywhere right now?' })
    .selectOption('true');
  await page
    .getByRole('combobox', { name: 'What are you currently studying?' })
    .selectOption('undergraduate');
  await expect(page.getByRole('combobox', { name: /your school government/ })).toHaveCount(0);
  await expect(page.getByText('annual income', { exact: false })).toHaveCount(0);
  await expect(page.getByRole('combobox', { name: /work situation/ })).toHaveCount(0);
  await page.getByRole('combobox', { name: 'How are you studying now?' }).selectOption('full_time');
  page.once('dialog', (d) => d.dismiss());
  await page
    .getByRole('combobox', { name: 'Are you studying anywhere right now?' })
    .selectOption('false');
  await expect(
    page.getByRole('combobox', { name: 'Are you studying anywhere right now?' }),
  ).toHaveValue('true');
  page.once('dialog', (d) => d.accept());
  await page
    .getByRole('combobox', { name: 'Are you studying anywhere right now?' })
    .selectOption('false');
  await expect(page.getByRole('combobox', { name: 'How are you studying now?' })).toHaveCount(0);
  await productCapture(page, 'product-profile-incomplete-en');
  await page.getByRole('button', { name: 'Review your answers', exact: true }).click();
  await expect(page.locator('.profile-review')).not.toContainText('Not sure');
  await page.getByRole('button', { name: 'Finish setup', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Saved and up to date');
  await expect(page.getByRole('button', { name: /Finish setup|Save changes/ })).toHaveCount(0);
  expect(writes).toBe(1);
  await page.reload();
  await expect(page.locator('.profile-summary')).toContainText('Fictional learner');
  await page.getByRole('button', { name: 'Edit about you' }).click();
  await expect(page.getByRole('button', { name: 'Save changes', exact: true })).toBeDisabled();
  await page.getByRole('textbox', { name: 'Profile name' }).fill('Fictional revised');
  await expect(page.getByRole('status')).toContainText('Unsaved changes');
  await productCapture(page, 'product-profile-edited-en');
  await page.getByRole('button', { name: 'Save changes', exact: true }).click();
  await expect(page.locator('.profile-summary')).toContainText('Fictional revised');
  expect(writes).toBe(2);
  await productCapture(page, 'product-profile-summary-en');
  await page.setViewportSize({ width: 390, height: 900 });
  await page.getByRole('combobox', { name: 'Interface language' }).first().selectOption('hi');
  await productCapture(page, 'product-profile-summary-hi-mobile');
});
