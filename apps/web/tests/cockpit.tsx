// Component-only browser fixture. Not a production route, Firebase session or auth override.
import { useState } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Cockpit, Locale } from '../src/app/App';
import type { Language } from '../src/i18n/strings';
import '../src/styles.css';
import '../src/finale.css';
const cache = new QueryClient({ defaultOptions: { queries: { retry: false } } });
function Fixture() {
  const [language, setLanguage] = useState<Language>('en');
  return (
    <Locale.Provider value={language}>
      <header className="topbar">
        <strong>Fictional component contract · no Firebase acceptance</strong>
        <select
          aria-label="Interface language"
          value={language}
          onChange={(e) => {
            setLanguage(e.target.value as Language);
            document.documentElement.lang = e.target.value;
          }}
        >
          <option value="en">English</option>
          <option value="hi">हिन्दी</option>
        </select>
      </header>
      <main>
        <Cockpit />
      </main>
    </Locale.Provider>
  );
}
createRoot(document.getElementById('root')!).render(
  <QueryClientProvider client={cache}>
    <BrowserRouter>
      <Fixture />
    </BrowserRouter>
  </QueryClientProvider>,
);
