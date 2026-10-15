import { initializeApp } from 'firebase/app';
import {
  getAuth,
  GoogleAuthProvider,
  signInWithPopup,
  signOut,
  connectAuthEmulator,
} from 'firebase/auth';
const env = import.meta.env;
export const authConfigured = Boolean(
  env.VITE_FIREBASE_API_KEY &&
  env.VITE_FIREBASE_AUTH_DOMAIN &&
  env.VITE_FIREBASE_PROJECT_ID &&
  env.VITE_FIREBASE_APP_ID,
);
export const auth = authConfigured
  ? getAuth(
      initializeApp({
        apiKey: env.VITE_FIREBASE_API_KEY,
        authDomain: env.VITE_FIREBASE_AUTH_DOMAIN,
        projectId: env.VITE_FIREBASE_PROJECT_ID,
        appId: env.VITE_FIREBASE_APP_ID,
      }),
    )
  : null;
export const usingAuthEmulator = Boolean(
  import.meta.env.DEV && env.VITE_FIREBASE_AUTH_EMULATOR_URL,
);
if (auth && usingAuthEmulator) {
  const url = new URL(env.VITE_FIREBASE_AUTH_EMULATOR_URL);
  if (!['127.0.0.1', 'localhost'].includes(url.hostname) || url.protocol !== 'http:')
    throw new Error('The development auth emulator must use loopback HTTP.');
  connectAuthEmulator(auth, url.origin, { disableWarnings: true });
}
export async function login() {
  if (auth) await signInWithPopup(auth, new GoogleAuthProvider());
}
export async function logout() {
  if (auth) await signOut(auth);
}
