import { createContext, useContext, useEffect, useRef, useState } from 'react';
import { Link, NavLink, Navigate, Route, Routes, useLocation } from 'react-router-dom';
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
    const close = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setMenu(false);
    };
    document.addEventListener('keydown', close);
    return () => document.removeEventListener('keydown', close);
  }, []);
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
    { to: '/my-opportunities', label: t.saved, icon: Layers3 },
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
                <NavLink to={to}>
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
              <span>INDIA FIRST · PHASE 02</span>
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
              <Route path="/dashboard" element={<Overview />} />
              <Route path="/profile" element={<Profile />} />
              <Route path="/admin" element={<Admin />} />
              {['family', 'businesses', 'my-opportunities'].map((path) => (
                <Route key={path} path={`/${path}`} element={<Future />} />
              ))}
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
function Overview() {
  const t = useStrings();
  const f = useFacets();
  return (
    <div className="page">
      <div className="page-heading">
        <span className="eyebrow">{t.foundation}</span>
        <h1>{t.welcome}</h1>
        <p>{t.welcomeText}</p>
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
