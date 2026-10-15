// Test-only official Firebase SDK login. No token/auth dependency override; excluded from dist.
import { createRoot } from 'react-dom/client';
import { useState } from 'react';
import { createUserWithEmailAndPassword, signInWithEmailAndPassword } from 'firebase/auth';
import { auth, usingAuthEmulator } from '../src/app/auth';
function Login() {
  const [email, setEmail] = useState(''),
    [error, setError] = useState('');
  return (
    <main>
      <h1>Firebase Auth emulator — fictional account</h1>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          if (!auth || !usingAuthEmulator) {
            setError('Local emulator required');
            return;
          }
          try {
            try {
              await createUserWithEmailAndPassword(auth, email, 'Fictional-Only-123');
            } catch {
              await signInWithEmailAndPassword(auth, email, 'Fictional-Only-123');
            }
            window.location.assign('/');
          } catch {
            setError('Fictional sign-in failed');
          }
        }}
      >
        <label>
          Fictional email
          <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <button>Sign in to emulator</button>
        {error && <p role="alert">{error}</p>}
      </form>
    </main>
  );
}
createRoot(document.getElementById('root')!).render(<Login />);
