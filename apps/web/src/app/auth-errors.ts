/** Only known codes select static messages; never display provider error text. */
export function authErrorKey(error: unknown) {
  const code = error && typeof error === 'object' && 'code' in error ? error.code : undefined;
  switch (code) {
    case 'auth/operation-not-allowed':
      return 'authProviderDisabled';
    case 'auth/unauthorized-domain':
      return 'authDomainBlocked';
    case 'auth/popup-blocked':
      return 'authPopupBlocked';
    case 'auth/popup-closed-by-user':
    case 'auth/cancelled-popup-request':
      return 'authPopupClosed';
    case 'auth/network-request-failed':
      return 'authNetworkFailed';
    default:
      return 'authFailed';
  }
}
