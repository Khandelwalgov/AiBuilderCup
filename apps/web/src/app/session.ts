import { useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { onAuthStateChanged, type User } from 'firebase/auth';
import { auth, login, logout } from './auth';
import { authErrorKey } from './auth-errors';
export type SessionState = {
  user: Pick<User, 'uid' | 'displayName'> | null;
  ready: boolean;
  busy: boolean;
  errorKey: ReturnType<typeof authErrorKey> | null;
  signIn: () => Promise<void>;
  signOut: () => Promise<void>;
};
export function useFirebaseSession(): SessionState {
  const cache = useQueryClient();
  const previous = useRef<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(!auth);
  const [busy, setBusy] = useState(false);
  const [errorKey, setErrorKey] = useState<ReturnType<typeof authErrorKey> | null>(null);
  useEffect(
    () =>
      auth
        ? onAuthStateChanged(
            auth,
            (next) => {
              const uid = next?.uid ?? null;
              if (previous.current !== uid) cache.clear();
              previous.current = uid;
              setUser(next);
              setReady(true);
            },
            (error) => {
              cache.clear();
              setUser(null);
              setErrorKey(authErrorKey(error));
              setReady(true);
            },
          )
        : undefined,
    [cache],
  );
  const run = async (action: () => Promise<void>) => {
    setBusy(true);
    setErrorKey(null);
    try {
      await action();
    } catch (error) {
      setErrorKey(authErrorKey(error));
    } finally {
      setBusy(false);
    }
  };
  return { user, ready, busy, errorKey, signIn: () => run(login), signOut: () => run(logout) };
}
