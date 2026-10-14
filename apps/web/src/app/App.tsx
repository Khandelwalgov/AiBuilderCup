import { createContext, useContext, useEffect, useRef, useState } from 'react';
import { Link, NavLink, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { Workspaces } from '../features/workspaces/Workspaces';
import { Plan } from '../features/workspaces/Plan';
import { Profile } from '../features/profiles/Profile';
import { Admin } from '../features/admin/Admin';
import { useQueryClient, useQuery } from '@tanstack/react-query';
import { onAuthStateChanged, type User } from 'firebase/auth';
import {
  ArrowDownLeft,
  ArrowRight,
  Blocks,
  BriefcaseBusiness,
  Compass,
  Globe2,
  House,
  Layers3,
  Leaf,
  Menu,
  Settings2,
  ShieldCheck,
  Sparkles,
  UserRound,
  UsersRound,
  X,
} from 'lucide-react';
import { strings, type Language } from '../i18n/strings';
import { auth, authConfigured, login, logout } from './auth';
import { authErrorKey } from './auth-errors';
import { api, fail } from '../lib/api/client';
import { Discover, Detail } from '../features/opportunities/Discover';
const Locale = createContext<Language>('en');
export function useLanguage() {
  return useContext(Locale);
}
export function useStrings() {
  return strings[useContext(Locale)];
}
const brand = import.meta.env.VITE_APP_NAME || 'Unclaimed';
export function useFacets(development = false) {
  return useQuery({
    queryKey: ['facets', development],
    queryFn: async () => {
      const { data, error } = await api.GET('/v1/opportunity-facets', {
        params: { query: { development } },
      });
      return data ?? fail(error);
    },
  });
}
export function App() {
  const cache = useQueryClient();
  const [language, setLanguage] = useState<Language>(() =>
    localStorage.getItem('language') === 'hi' ? 'hi' : 'en',
  );
  const [user, setUser] = useState<User | null>(null);
  const previousUid = useRef<string | null>(null);
  const [authError, setAuthError] = useState('');
  const [menu, setMenu] = useState(false);
  const location = useLocation();
  const t = strings[language];
  useEffect(() => {
    document.documentElement.lang = language;
    localStorage.setItem('language', language);
    document.title = `${brand} · Opportunity Intelligence`;
  }, [language]);
  useEffect(
    () =>
      auth
        ? onAuthStateChanged(auth, (next) => {
            const nextUid = next?.uid ?? null;
            // The initial signed-out callback must not cancel active public queries.
            // Actual account changes clear private cache and remount workspace state.
            if (previousUid.current !== nextUid) cache.clear();
            previousUid.current = nextUid;
            setUser(next);
          })
        : undefined,
    [cache],
  );
  const accountQuery = useQuery({
    queryKey: ['account', user?.uid],
    enabled: !!user,
    retry: false,
    queryFn: async () => {
      const { data, error } = await api.GET('/v1/me');
      return data ?? fail(error);
    },
  });
  useEffect(() => setMenu(false), [location.pathname]);
  useEffect(() => {
    const navigation = document.getElementById('primary-navigation');
    if (menu) navigation?.querySelector<HTMLAnchorElement>('a[href]')?.focus();
    const close = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && menu) {
        setMenu(false);
        document.querySelector<HTMLButtonElement>('.mobile-menu')?.focus();
      }
      if (event.key === 'Tab' && menu && window.innerWidth <= 800) {
        const items = Array.from(
          navigation?.querySelectorAll<HTMLElement>('a[href],button:not([disabled]),select') ?? [],
        ).filter((el) => el.offsetParent !== null);
        const first = items[0],
          last = items[items.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener('keydown', close);
    return () => document.removeEventListener('keydown', close);
  }, [menu]);
  async function signIn() {
    setAuthError('');
    try {
      await login();
    } catch (error) {
      setAuthError(t[authErrorKey(error)]);
    }
  }
  const navigation = [
    { to: '/dashboard', label: t.dashboard, icon: House },
    { to: '/discover', label: t.discover, icon: Compass },
    { to: '/profile', label: t.profile, icon: UserRound },
    { to: '/family', label: t.family, icon: UsersRound },
    { to: '/businesses', label: t.businesses, icon: BriefcaseBusiness },
    { to: '/plan', label: language === 'hi' ? 'मेरी कार्ययोजना' : 'Unlock plan', icon: Layers3 },
  ];
  if (accountQuery.data?.is_admin)
    navigation.push({ to: '/admin', label: t.adminReview, icon: ShieldCheck });
  return (
    <Locale.Provider value={language}>
      <a className="skip" href="#main">
        {t.accessibility}
      </a>
      <div className="layout">
        <aside id="primary-navigation" className={`sidebar ${menu ? 'open' : ''}`}>
          <Link to="/discover" className="brand">
            <span className="brand-icon">
              <ArrowDownLeft size={22} />
            </span>
            {brand}
            <span className="brand-dot">.</span>
          </Link>
          <button
            className="mobile-close icon-button"
            onClick={() => setMenu(false)}
            aria-label="Close navigation"
          >
            <X />
          </button>
          <p className="nav-caption">{t.discoverNav}</p>
          <nav aria-label="Main navigation">
            {navigation.map(({ to, label, icon: Icon }, i) => (
              <div key={to}>
                {i === 2 && <p className="nav-caption workspace-caption">{t.workspaceNav}</p>}
                <NavLink
                  to={to}
                  onClick={() => {
                    if (menu) {
                      setMenu(false);
                      document.getElementById('main')?.focus();
                    }
                  }}
                >
                  <Icon size={18} />
                  <span>{label}</span>
                  {to === '/discover' && <span className="nav-dot" />}
                </NavLink>
              </div>
            ))}
          </nav>
          <div className="sidebar-bottom">
            <div className="sidebar-note">
              <Leaf size={22} />
              <p>{t.footer}</p>
              <span>INDIA FIRST · EVIDENCE FIRST</span>
            </div>
            <NavLink className="settings-link" to="/settings">
              <Settings2 size={18} />
              {t.settings}
            </NavLink>
            <div className="guest">
              <span className="avatar">
                <UserRound size={18} />
              </span>
              <div>
                <strong>{user?.displayName || t.guest}</strong>
                <small>{t.foundation}</small>
              </div>
            </div>
          </div>
        </aside>
        <div className="workspace">
          <header className="topbar">
            <button
              className="mobile-menu icon-button"
              aria-label="Open navigation"
              aria-expanded={menu}
              aria-controls="primary-navigation"
              onClick={() => setMenu(!menu)}
            >
              <Menu />
            </button>
            <span className="breadcrumb">
              {brand} <span>/</span>{' '}
              {location.pathname.startsWith('/opportunities/')
                ? t.discover
                : navigation.find((n) => location.pathname.startsWith(n.to))?.label || t.settings}
            </span>
            <div className="top-actions">
              <label className="language">
                <Globe2 size={16} />
                <select
                  aria-label={t.language}
                  value={language}
                  onChange={(e) => setLanguage(e.target.value as Language)}
                >
                  <option value="en">English</option>
                  <option value="hi">हिन्दी</option>
                </select>
              </label>
              {user ? (
                <button className="button small" onClick={() => void logout()}>
                  {t.signOut}
                </button>
              ) : (
                <button
                  className="button small"
                  onClick={() =>
                    authConfigured ? void signIn() : window.location.assign('/settings')
                  }
                >
                  {t.signIn}
                  <ArrowRight size={14} />
                </button>
              )}
            </div>
          </header>
          {authError && (
            <div role="alert" className="notice">
              {authError}
            </div>
          )}
          <main key={user?.uid || 'public'} id="main" tabIndex={-1}>
            <Routes>
              <Route path="/" element={<Navigate to="/discover" replace />} />
              <Route path="/discover" element={<Discover />} />
              <Route path="/opportunities/:id" element={<Detail />} />
              <Route path="/dashboard" element={<Overview authenticated={!!user} />} />
              <Route path="/profile" element={<Profile />} />
              <Route path="/people/:personId/edit" element={<Profile />} />
              <Route path="/admin" element={<Admin />} />
              <Route path="/family" element={<Workspaces kind="household" />} />
              <Route path="/businesses" element={<Workspaces kind="business" />} />
              <Route path="/plan" element={<Plan />} />
              <Route path="/my-opportunities" element={<Navigate to="/plan" replace />} />
              <Route
                path="/settings"
                element={
                  <Settings
                    user={user}
                    language={language}
                    setLanguage={setLanguage}
                    signIn={signIn}
                  />
                }
              />
              <Route path="*" element={<Future />} />
            </Routes>
          </main>
          <footer className="page-footer">
            <span>
              {brand} · {t.foundation}
            </span>
            <span>
              <ShieldCheck size={13} /> {t.coverage}
            </span>
          </footer>
        </div>
      </div>
    </Locale.Provider>
  );
}
function Overview({ authenticated }: { authenticated: boolean }) {
  const t = useStrings();
  const f = useFacets();
  const overview = useQuery({
    queryKey: ['dashboard-summary'],
    enabled: authenticated,
    retry: false,
    queryFn: async () => {
      const { data, error } = await api.GET('/v1/dashboard');
      return data ?? fail(error);
    },
  });
  const hi = useLanguage() === 'hi';
  return (
    <div className="page">
      <div className="page-heading">
        <span className="eyebrow">{t.foundation}</span>
        <h1>
          {overview.data?.profile_name
            ? `${hi ? 'फिर स्वागत है' : 'Welcome back'}, ${overview.data.profile_name}.`
            : t.welcome}
        </h1>
        <p>{t.welcomeText}</p>
      </div>
      {overview.isError && <p role="alert">{overview.error.message}</p>}
      {overview.data && (
        <section className="personal-pulse panel">
          <div>
            <span className="eyebrow">{hi ? 'आपकी तैयारी' : 'YOUR READINESS'}</span>
            <h2>
              {overview.data.profile_name
                ? hi
                  ? 'अगला कदम सामने है'
                  : 'Your next steps, in one place'
                : hi
                  ? 'अपना न्यूनतम प्रोफ़ाइल बनाएं'
                  : 'Create your minimal profile'}
            </h2>
            <p>
              {overview.data.personal_pending_actions}{' '}
              {hi ? 'व्यक्तिगत कदम' : 'personal pending actions'} ·{' '}
              {overview.data.assessed_current_opportunities}{' '}
              {hi ? 'वर्तमान अवसर जाँचे गए' : 'current opportunities assessed'} ·{' '}
              {overview.data.households} {hi ? 'परिवार' : 'households'} · {overview.data.businesses}{' '}
              {hi ? 'व्यवसाय' : 'businesses'}
            </p>
          </div>
          {overview.data.review_candidates != null && (
            <Link className="button secondary" to="/admin">
              {overview.data.review_candidates} {hi ? 'मसौदे समीक्षा में' : 'drafts to review'}
              <ArrowRight size={16} />
            </Link>
          )}
        </section>
      )}
      <div className="dashboard-actions">
        <Link className="dashboard-primary" to="/plan">
          <span className="eyebrow">{hi ? 'अगला उपयोगी कदम' : 'YOUR NEXT USEFUL STEP'}</span>
          <h2>{hi ? 'अपनी तैयारी की योजना देखें' : 'Turn missing information into a plan'}</h2>
          <p>
            {hi
              ? 'समीक्षित अवसरों के लिए अपनी जानकारी जाँचें।'
              : 'Understand what is known, what is missing, and which steps can help across opportunities.'}
          </p>
          <span className="button">
            {hi ? 'मेरी योजना खोलें' : 'Open my unlock plan'} <ArrowRight size={16} />
          </span>
        </Link>
        <div className="dashboard-secondary">
          <Link className="panel" to="/profile">
            <UserRound />
            <h3>{hi ? 'आपके बारे में थोड़ा' : 'Start with what you know'}</h3>
            <p>
              {hi
                ? 'केवल आवश्यक जानकारी दें।'
                : 'Build a minimal profile. Leave uncertain answers unknown.'}
            </p>
            <ArrowRight size={16} />
          </Link>
          <Link className="panel" to="/family">
            <UsersRound />
            <h3>{hi ? 'परिवार के साथ तैयारी' : 'Bring your contexts together'}</h3>
            <p>
              {hi
                ? 'अधिकृत आश्रित और व्यवसाय जोड़ें।'
                : 'Manage authorized dependents and keep business facts separate.'}
            </p>
            <ArrowRight size={16} />
          </Link>
        </div>
      </div>
      <div className="stats">
        {[
          [t.publishedCount, f.data?.total],
          [t.verified, f.data?.verified],
          [t.sources, f.data?.official_sources],
        ].map(([label, value]) => (
          <div className="stat" key={label}>
            <strong>{value ?? '—'}</strong>
            <span>{label}</span>
          </div>
        ))}
      </div>
      <section className="panel">
        <Compass className="section-icon" />
        <h2>{t.coverage}</h2>
        <p>{t.coverageText}</p>
        <Link className="button" to="/discover">
          {t.browse}
          <ArrowRight size={16} />
        </Link>
      </section>
    </div>
  );
}
function Future() {
  const t = useStrings();
  return (
    <div className="page">
      <div className="empty-state future">
        <span className="empty-icon">
          <Blocks size={30} />
        </span>
        <span className="eyebrow">{t.foundation}</span>
        <h1>{t.future}</h1>
        <p>{t.futureText}</p>
        <Link className="button" to="/discover">
          {t.browse}
          <ArrowRight size={16} />
        </Link>
      </div>
    </div>
  );
}
function Settings({
  user,
  language,
  setLanguage,
  signIn,
}: {
  user: User | null;
  language: Language;
  setLanguage: (v: Language) => void;
  signIn: () => Promise<void>;
}) {
  const t = useStrings();
  const account = useQuery({
    queryKey: ['account', user?.uid],
    enabled: !!user,
    queryFn: async () => {
      const { data, error } = await api.GET('/v1/me');
      return data ?? fail(error);
    },
  });
  return (
    <div className="page narrow">
      <div className="page-heading">
        <span className="eyebrow">{t.settings}</span>
        <h1>{t.account}</h1>
      </div>
      <section className="panel">
        <ShieldCheck className="section-icon" />
        <h2>{user ? t.signedIn : t.signIn}</h2>
        {!authConfigured ? (
          <p>{t.firebaseMissing}</p>
        ) : user ? (
          <>
            <p>{user.displayName}</p>
            <p role="status">
              {account.isError ? account.error.message : account.data ? t.signedIn : t.loading}
            </p>
          </>
        ) : (
          <button className="button" onClick={() => void signIn()}>
            {t.signIn}
            <ArrowRight size={16} />
          </button>
        )}
      </section>
      <section className="panel">
        <Globe2 className="section-icon" />
        <h2>{t.language}</h2>
        <p>{t.languageNote}</p>
        <select
          aria-label={t.language}
          value={language}
          onChange={(e) => setLanguage(e.target.value as Language)}
        >
          <option value="en">English</option>
          <option value="hi">हिन्दी</option>
        </select>
      </section>
      <section className="panel">
        <Sparkles className="section-icon" />
        <h2>{t.coverage}</h2>
        <p>{t.coverageText}</p>
      </section>
    </div>
  );
}
