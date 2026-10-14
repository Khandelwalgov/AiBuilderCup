import { expect, test } from '@playwright/test';
import { authErrorKey } from '../src/app/auth-errors';
import { strings } from '../src/i18n/strings';

test('sign-in failures select actionable localized messages without provider data', () => {
  for (const [code, key] of [
    ['auth/operation-not-allowed', 'authProviderDisabled'],
    ['auth/unauthorized-domain', 'authDomainBlocked'],
    ['auth/popup-blocked', 'authPopupBlocked'],
    ['auth/popup-closed-by-user', 'authPopupClosed'],
    ['auth/network-request-failed', 'authNetworkFailed'],
  ] as const) {
    const result = authErrorKey({ code, message: 'synthetic-private-provider-data' });
    expect(result).toBe(key);
    expect(strings.en[result]).not.toContain('synthetic-private-provider-data');
    expect(strings.hi[result]).toBeTruthy();
  }
  expect(authErrorKey({ code: 'unknown', message: 'synthetic-private-provider-data' })).toBe(
    'authFailed',
  );
  expect(authErrorKey(null)).toBe('authFailed');
});
