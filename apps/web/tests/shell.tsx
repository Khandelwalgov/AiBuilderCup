// Test-only composition with fictional session props. Never a Firebase override or production route.
import { useState, useEffect } from 'react';
import { createRoot } from 'react-dom/client';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ApplicationFrame } from '../src/app/App';
import type { SessionState } from '../src/app/session';
import '../src/styles/index.css';
const cache = new QueryClient({ defaultOptions: { queries: { retry: false } } });
function Fixture() {
  const [uid, setUid] = useState(localStorage.getItem('fictional-session') ?? 'fictional-one');
  const [ready, setReady] = useState(false);
  useEffect(() => {
    const timer = setTimeout(
      () => setReady(true),
      Number(localStorage.getItem('fictional-delay') ?? 50),
    );
    return () => clearTimeout(timer);
  }, []);
  const change = (next: string) => {
    cache.clear();
    localStorage.setItem('fictional-session', next);
    setUid(next);
  };
  const session: SessionState = {
    user: uid
      ? { uid, displayName: uid === 'fictional-one' ? 'Fictional One' : 'Fictional Two' }
      : null,
    ready,
    busy: false,
    errorKey: null,
    signIn: async () => change('fictional-one'),
    signOut: async () => change(''),
  };
  return (
    <>
      <div className="qa-session" hidden>
        <button onClick={() => change('fictional-two')}>Switch fictional account</button>
        <button onClick={() => void cache.invalidateQueries({ queryKey: ['personal-profile'] })}>
          Refetch fictional profile
        </button>
      </div>
      <ApplicationFrame session={session} />
    </>
  );
}
createRoot(document.getElementById('root')!).render(
  <QueryClientProvider client={cache}>
    <RouterProvider router={createBrowserRouter([{ path: '*', element: <Fixture /> }])} />
  </QueryClientProvider>,
);
