import { test, expect } from '@playwright/test';
import { productCapture } from './product-capture';
test('real Firebase/API/PostgreSQL search and ephemeral future family', async ({ page }) => {
  await page.goto('/tests/emulator-login.html');
  await page
    .getByRole('textbox', { name: 'Fictional email' })
    .fill(`intelligence-${Date.now()}@example.invalid`);
  await page.getByRole('button', { name: 'Sign in to emulator' }).click();
  await expect(page).toHaveURL(/\/$/);
  await page.goto('/profile');
  await page.getByRole('textbox', { name: 'Profile name' }).fill('Fictional scenario learner');
  await page.getByRole('button', { name: 'Continue', exact: true }).click();
  await page.getByRole('button', { name: 'Review your answers', exact: true }).click();
  await page.getByRole('button', { name: 'Finish setup', exact: true }).click();
  await page.goto('/discover?development=true');
  await expect(page.getByRole('combobox', { name: 'Search context' })).toHaveValue('me');
  await expect(
    page.getByRole('textbox', { name: 'Search opportunities, interests, or keywords' }),
  ).toBeEmpty();
  await expect(page.getByText('Fictional scenario learner', { exact: true }).first()).toBeVisible();
  await expect(page.getByText('Missing information', { exact: true }).first()).toBeVisible();
  await expect(
    page.getByRole('heading', { name: 'FICTIONAL scholarship 1', exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole('link', { name: 'Official source', exact: true }).first(),
  ).toBeVisible();
  await page.getByText('Cited conditions', { exact: true }).first().click();
  await expect(
    page
      .getByText('FICTIONAL parental income certificate for the 2026 test period.', {
        exact: false,
      })
      .first(),
  ).toBeVisible();
  await productCapture(page, 'phase4-ranked-me');
  await page.goto('/scenarios?development=true');
  await page.getByRole('button', { name: 'Add fact override', exact: true }).first().click();
  await page.getByRole('spinbutton', { name: 'Hypothetical value' }).fill('18');
  await page.getByRole('button', { name: 'Add fictional person', exact: true }).click();
  await page.getByRole('textbox', { name: 'Name', exact: true }).fill('Fictional future child');
  await page.getByRole('button', { name: 'Run scenario', exact: true }).click();
  await expect(
    page.getByRole('heading', { name: 'Reviewed-policy assessment changes' }),
  ).toBeVisible();
  await expect(page.getByText('No scenario data was saved.', { exact: true })).toBeVisible();
  await expect(page.locator('[aria-label="Scenario results"]')).toContainText('scenario');
  await productCapture(page, 'phase4-scenario-family');
  await page.setViewportSize({ width: 390, height: 844 });
  await productCapture(page, 'phase4-scenario-mobile');
  await page.getByRole('button', { name: 'Reset / discard', exact: true }).click();
  await expect(
    page.getByRole('heading', { name: 'Reviewed-policy assessment changes' }),
  ).toHaveCount(0);
  await expect(page.getByRole('textbox', { name: 'Name', exact: true })).toHaveCount(0);
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto('/family');
  await page.getByRole('textbox', { name: 'Household name' }).fill('Fictional intelligence family');
  await page.getByRole('button', { name: 'Create household', exact: true }).click();
  await page
    .getByRole('textbox', { name: 'Dependent’s name or nickname' })
    .fill('Fictional present dependent');
  await page.getByRole('spinbutton', { name: 'Age (optional)' }).fill('12');
  await page.getByRole('checkbox', { name: /I am the legal guardian/ }).check();
  await page.getByRole('button', { name: 'Add dependent', exact: true }).click();
  await expect(
    page.locator('.member-row').filter({ hasText: 'Fictional present dependent' }),
  ).toBeVisible();
  await page.goto('/discover?development=true&mode=family');
  await page
    .getByRole('combobox', { name: 'Selected profile' })
    .selectOption({ label: 'Household · Fictional intelligence family' });
  await expect(
    page.getByRole('heading', { name: 'FICTIONAL household opportunity', exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole('heading', { name: 'Fictional present dependent', exact: true }).first(),
  ).toBeVisible();
  await productCapture(page, 'phase4-family-context');
  await page.getByRole('combobox', { name: 'Search context' }).selectOption('member');
  await page
    .getByRole('combobox', { name: 'Selected profile' })
    .selectOption({ label: 'Dependent · Fictional present dependent' });
  await expect(
    page.getByRole('heading', { name: 'Fictional present dependent', exact: true }).first(),
  ).toBeVisible();
  await page.getByRole('link', { name: 'Inspect conditions and evidence' }).first().click();
  await expect(page).toHaveURL(/kind=person.*id=/);
  await page.goto('/businesses');
  await page
    .getByRole('textbox', { name: 'Business name' })
    .fill('Fictional intelligence business');
  await page.getByRole('button', { name: 'Continue', exact: true }).click();
  await page.getByRole('button', { name: 'Create business', exact: true }).click();
  await expect(page.locator('.workspace-overview')).toContainText(
    'Fictional intelligence business',
  );
  await page.goto('/discover?development=true&mode=business');
  await page
    .getByRole('combobox', { name: 'Selected profile' })
    .selectOption({ label: 'Business · Fictional intelligence business' });
  await expect(
    page.getByRole('heading', { name: 'FICTIONAL business opportunity', exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole('heading', { name: 'Fictional intelligence business', exact: true }),
  ).toBeVisible();
  await page.getByRole('combobox', { name: 'Search context' }).selectOption('explore');
  await expect(
    page.getByRole('link', { name: 'FICTIONAL scholarship 1', exact: true }),
  ).toBeVisible();
  await page.goto('/scenarios?development=true');
  await page.getByRole('combobox', { name: 'Interface language' }).first().selectOption('hi');
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByRole('heading', { name: 'परिदृश्य स्टूडियो', exact: true })).toBeVisible();
  await productCapture(page, 'phase4-studio-hi-mobile');
});
