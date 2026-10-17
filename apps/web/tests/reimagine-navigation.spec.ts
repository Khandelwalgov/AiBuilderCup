import { expect, test } from '@playwright/test';
import { sessionFixture } from './session-fixture';
for (const signedIn of [true, false])
  test(`canonical logo and Overview navigation, history and refresh (fictional session ${signedIn})`, async ({
    page,
  }) => {
    await sessionFixture(page, signedIn);
    await page.goto('/settings');
    await page.locator('.brand').click();
    await expect(page).toHaveURL(/\/$/);
    await expect(page.locator('.breadcrumb')).toContainText(signedIn ? 'Overview' : 'Home');
    await expect(page.locator('nav a[href="/"]')).toHaveClass(/active/);
    await expect(page.locator('.breadcrumb')).not.toContainText('Settings');
    await page.getByRole('link', { name: 'Discover opportunities', exact: true }).click();
    await page.getByRole('link', { name: signedIn ? 'Overview' : 'Home', exact: true }).click();
    await expect(page).toHaveURL(/\/$/);
    await page.goBack();
    await expect(page).toHaveURL(/\/discover$/);
    await page.goForward();
    await expect(page).toHaveURL(/\/$/);
    await page.reload();
    await expect(page.locator('.breadcrumb')).toContainText(signedIn ? 'Overview' : 'Home');
    await page.goto('/dashboard');
    await expect(page).toHaveURL(/\/$/);
    await page.goto('/not-a-real-page');
    await expect(page.getByRole('heading', { name: 'Page not found' })).toBeVisible();
    await page.goto('/settings');
    await page.setViewportSize({ width: 390, height: 900 });
    await page.getByRole('combobox', { name: 'Interface language' }).first().selectOption('hi');
    await page.getByRole('button', { name: 'Open navigation' }).click();
    await page.locator('.brand').click();
    await expect(page.locator('.breadcrumb')).toContainText(signedIn ? 'अवलोकन' : 'होम');
  });
test('auth-ready boundary never renders the guest landing while a session resolves (fictional session)', async ({
  page,
}) => {
  await sessionFixture(page);
  await page.addInitScript(() => localStorage.setItem('fictional-delay', '800'));
  await page.goto('/');
  await expect(page.getByRole('status')).toContainText('Restoring your secure session');
  await expect(
    page.getByRole('heading', { name: 'Possibility, with a path forward.' }),
  ).toHaveCount(0);
  await expect(page.getByRole('heading', { name: /Welcome back/ })).toBeVisible();
});

test('public initial HTML and rendered browser title keep the Unclaimed name', async ({ page }) => {
  const html = await page.request.get('/');
  expect(await html.text()).toContain('<title>Unclaimed</title>');
  await page.goto('/discover');
  await expect(page).toHaveTitle(/Unclaimed/);
});
