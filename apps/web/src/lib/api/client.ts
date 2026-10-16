import createClient from 'openapi-fetch';
import type { paths } from './schema';
import { auth } from '../../app/auth';
export const api = createClient<paths>({
  baseUrl: import.meta.env.VITE_API_BASE_URL || '',
  fetch: (request) =>
    fetch(request, {
      signal: AbortSignal.any([
        request.signal,
        AbortSignal.timeout(new URL(request.url).pathname.endsWith('/ingest') ? 150_000 : 30_000),
      ]),
    }),
});
const requestUsers = new WeakMap<Request, string | null>();
api.use({
  async onRequest({ request }) {
    requestUsers.set(request, auth?.currentUser?.uid ?? null);
    if (
      auth?.currentUser &&
      (request.method !== 'GET' || !new URL(request.url).pathname.startsWith('/v1/opportunities'))
    )
      request.headers.set('Authorization', `Bearer ${await auth.currentUser.getIdToken()}`);
    return request;
  },
  onResponse({ request, response }) {
    if (
      requestUsers.has(request) &&
      requestUsers.get(request) !== (auth?.currentUser?.uid ?? null)
    ) {
      throw new RequestError(
        'session_changed',
        'Your account changed. Reload this page before continuing.',
      );
    }
    return response;
  },
});
export class RequestError extends Error {
  constructor(
    public code: string,
    message: string,
    public issues: Array<{ fields?: string[]; message?: string[] }> = [],
  ) {
    super(message);
    this.name = 'RequestError';
  }
}
export function fail(error: unknown): never {
  const envelope =
    error && typeof error === 'object' && 'error' in error
      ? (
          error as {
            error: {
              code: string;
              message: string;
              issues?: Array<{ fields?: string[]; message?: string[] }>;
            };
          }
        ).error
      : null;
  throw new RequestError(
    envelope?.code ?? 'connection_failed',
    envelope?.message ?? 'Unable to connect. Please try again.',
    envelope?.issues ?? [],
  );
}

// Binary document requests use the same authenticated transport as generated JSON calls.
export async function authorizedFetch(path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  const user = auth?.currentUser;
  if (user) headers.set('Authorization', `Bearer ${await user.getIdToken()}`);
  const response = await fetch((import.meta.env.VITE_API_BASE_URL || '') + path, {
    ...init,
    headers,
  });
  if ((auth?.currentUser?.uid ?? null) !== (user?.uid ?? null)) {
    void response.body?.cancel();
    throw new RequestError('session_changed', 'Your account changed. Reload before continuing.');
  }
  if (!response.ok) {
    let error: unknown;
    try {
      error = await response.json();
    } catch {
      error = null;
    }
    fail(error);
  }
  return response;
}
