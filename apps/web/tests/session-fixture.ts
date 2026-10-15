import type { Page } from '@playwright/test';
export async function sessionFixture(page: Page, signedIn = true) {
  await page.addInitScript((signedIn) => {
    localStorage.setItem('fictional-session', signedIn ? 'fictional-one' : '');
  }, signedIn);
  await page.route('**/*', async (route) => {
    if (route.request().isNavigationRequest() && route.request().resourceType() === 'document') {
      const response = await route.fetch({
        url: new URL('/tests/shell.html', route.request().url()).href,
      });
      await route.fulfill({ response });
    } else await route.fallback();
  });
  await page.route('**/v1/me', (r) =>
    r.fulfill({ json: { uid: 'fictional-one', is_admin: false } }),
  );
  await page.route('**/v1/documents?*', (r) => r.fulfill({ json: [] }));
  await page.route('**/v1/documents/requirements?*', (r) => r.fulfill({ json: [] }));
  await page.route('**/v1/workspaces', (r) => r.fulfill({ json: [] }));
  await page.route('**/v1/dashboard', (r) =>
    r.fulfill({
      json: {
        profile_name: 'Fictional One',
        personal_pending_actions: 0,
        assessed_current_opportunities: 0,
        households: 0,
        businesses: 0,
        review_candidates: null,
      },
    }),
  );
  await page.route('**/v1/plan', (r) =>
    r.fulfill({
      json: {
        subject: { kind: 'person' },
        hypothetical: false,
        evaluations: [],
        actions: [],
        known_blockers: [],
      },
    }),
  );
}
