import createClient from 'openapi-fetch';
import type { paths } from './schema';
import { auth } from '../../app/auth';
export const api = createClient<paths>({ baseUrl: import.meta.env.VITE_API_BASE_URL || '' });
api.use({
  async onRequest({ request }) {
    if (
      auth?.currentUser &&
      (request.method !== 'GET' || !new URL(request.url).pathname.startsWith('/v1/opportunities'))
    )
      request.headers.set('Authorization', `Bearer ${await auth.currentUser.getIdToken()}`);
    return request;
  },
});
export function fail(error: unknown): never {
  throw new Error(
    error && typeof error === 'object' && 'error' in error
      ? String((error as { error: { message: string } }).error.message)
      : 'Unable to connect. Please try again.',
  );
}
