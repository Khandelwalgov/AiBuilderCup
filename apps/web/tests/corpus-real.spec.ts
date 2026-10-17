import { test, expect } from '@playwright/test';
import { productCapture } from './product-capture';

test('actual captured government pages and unverified Codex drafts remain separate from publication', async ({
  page,
}) => {
  test.skip(
    !process.env.PRODUCT_E2E_CORPUS_ROOT,
    'Requires the actual local captured corpus; no fake replacement',
  );
  await page.goto('/government-sources');
  await expect(
    page.getByRole('heading', { name: 'Government Sources', exact: true }),
  ).toBeVisible();
  await expect(page.getByRole('article')).toHaveCount(3);
  const team = page.getByRole('article').filter({ hasText: 'MSME TEAM Initiative' });
  await expect(team.getByRole('link', { name: 'Original government source' })).toHaveAttribute(
    'href',
    /ramp\.msme\.gov\.in/,
  );
  await team.getByRole('button', { name: 'Read captured text' }).click();
  const captured = page.getByRole('region', { name: 'Captured source text' });
  await captured.getByText('Page 12', { exact: true }).click();
  await expect(captured).toContainText('Udyam registered Micro and Small Enterprises');
  await productCapture(page, 'actual-government-library');
  await page.goto('/discover');
  await expect(page.getByRole('article')).toHaveCount(0); // source collection never publishes
  await page.goto('/tests/emulator-login.html');
  await page
    .getByRole('textbox', { name: 'Fictional email' })
    .fill('corpus-reviewer@example.invalid');
  await page.getByRole('button', { name: 'Sign in to emulator' }).click();
  await expect(page).toHaveURL(/\/$/);
  await page.goto('/admin');
  await page
    .getByRole('button', {
      name: /MSME Trade Enablement and Marketing Initiative \(MSME TEAM Initiative\)/,
    })
    .click();
  await expect(
    page.getByRole('heading', {
      name: 'MSME Trade Enablement and Marketing Initiative (MSME TEAM Initiative)',
      exact: true,
    }),
  ).toBeVisible();
  await expect(page.locator('.candidate-editor')).toContainText(
    'codex:interactive:prepared-corpus-v1',
  );
  await page.getByText('Processing and independent review findings', { exact: true }).click();
  await expect(page.locator('.candidate-editor')).toContainText('not_performed');
  await expect(page.locator('.candidate-editor')).toContainText('independent_review_failed');
  await productCapture(page, 'actual-codex-draft-review');
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/government-sources');
  await page.getByRole('combobox', { name: 'Interface language' }).first().selectOption('hi');
  await expect(page.getByRole('heading', { name: 'सरकारी स्रोत', exact: true })).toBeVisible();
  await expect(page.getByText('मानवीय समीक्षा बाकी · PDF', { exact: true }).first()).toBeVisible();
  await productCapture(page, 'actual-government-library-hi-mobile');
});
