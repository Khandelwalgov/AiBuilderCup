import { DirtyFormsProvider, useDiscardGuard } from './dirty-forms';
import { ContextLink as Link } from './subject-context';
import { ContextNavLink as NavLink, SubjectProvider, useSubject } from './subject-context';
import { Landing } from '../components/Atlas';
import { createContext, useContext, useEffect, useState } from 'react';
import { Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { Workspaces } from '../features/workspaces/Workspaces';
import { Plan } from '../features/workspaces/Plan';
import { Profile } from '../features/profiles/Profile';
import { Documents } from '../features/documents/Documents';
import { Admin } from '../features/admin/Admin';
import { useQuery } from '@tanstack/react-query';
import { metadataFor, routeMetadata, routeTitle } from './routes';
import { useFirebaseSession, type SessionState } from './session';
import {
  ArrowDownLeft,
  ArrowRight,
  Blocks,
  Compass,
  Globe2,
  Leaf,
  Menu,
  Settings2,
  ShieldCheck,
  UserRound,
  UsersRound,
  X,
} from 'lucide-react';
import { strings, type Language } from '../i18n/strings';
import { authConfigured, usingAuthEmulator } from './auth';
import { api, fail } from '../lib/api/client';
import { Discover, Detail } from '../features/opportunities/Discover';
export const Locale = createContext<Language>('en');
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
  const session = useFirebaseSession();
  return <ApplicationFrame session={session} />;
}
export function ApplicationFrame({ session }: { session: SessionState }) {
  const navigate = useNavigate();
  const { user, ready, busy, errorKey, signIn, signOut } = session;
  const [language, setLanguage] = useState<Language>(() =>
    localStorage.getItem('language') === 'hi' ? 'hi' : 'en',
  );
  const [menu, setMenu] = useState(false);
  const location = useLocation();
  const t = strings[language];
  useEffect(() => {
    document.documentElement.lang = language;
    localStorage.setItem('language', language);
    document.title = `${brand} · Opportunity Intelligence`;
  }, [language]);
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
  const meta = metadataFor(location.pathname);
  const hi = language === 'hi';
  const navigation = routeMetadata
    .filter(
      (r) =>
        'icon' in r && r.id !== 'settings' && (r.access !== 'admin' || accountQuery.data?.is_admin),
    )
    .map((r) => ({
      to: r.path,
      label: routeTitle(r, t, hi, !!user),
      icon: 'icon' in r ? r.icon : Compass,
      id: r.id,
    }));
  useEffect(() => {
    document.title = `${routeTitle(meta, t, hi, !!user)} · ${brand}`;
  }, [meta, t, hi, user]);
  if (!ready)
    return (
      <Locale.Provider value={language}>
        <div className="auth-loading" role="status">
          <span className="loading-ring" />
          {hi ? 'सुरक्षित सत्र जाँचा जा रहा है…' : 'Restoring your secure session…'}
        </div>
      </Locale.Provider>
    );
  return (
    <Locale.Provider value={language}>
      <DirtyFormsProvider key={user?.uid ?? 'guest'} hi={hi}>
        <SubjectProvider key={user?.uid ?? 'guest'} enabled={!!user} hi={hi}>
          <a className="skip" href="#main">
            {t.accessibility}
          </a>
          <div
            className={`layout ${user ? 'app-site' : 'public-site'} ${meta?.access === 'admin' ? 'admin-console' : ''} ${menu ? 'menu-open' : ''}`}
          >
            {(user || menu) && (
              <aside id="primary-navigation" className={`sidebar ${menu ? 'open' : ''}`}>
                <Logo />
                <button
                  className="mobile-close icon-button"
                  onClick={() => setMenu(false)}
                  aria-label="Close navigation"
                >
                  <X />
                </button>
                <p className="nav-caption">{t.discoverNav}</p>
                <nav aria-label="Main navigation">
                  {navigation.map(({ to, label, icon: Icon, id }, i) => (
                    <div key={to}>
                      {i === 2 && <p className="nav-caption workspace-caption">{t.workspaceNav}</p>}
                      <NavLink
                        to={to}
                        end={to === '/'}
                        className={meta?.nav === id ? 'active' : ''}
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
                      <strong>
                        {user
                          ? user.displayName || (language === 'hi' ? 'आपका खाता' : 'Your account')
                          : t.guest}
                      </strong>
                      <small>{t.foundation}</small>
                    </div>
                  </div>
                </div>
              </aside>
            )}
            <div className="workspace">
              <header className="topbar">
                {!user && !menu && <Logo />}
                {!user && (
                  <nav
                    className="public-links"
                    aria-label={hi ? 'सार्वजनिक नेविगेशन' : 'Public navigation'}
                  >
                    <NavLink to="/" end>
                      {hi ? 'होम' : 'Home'}
                    </NavLink>
                    <NavLink to="/discover">{t.discover}</NavLink>
                    <Link to="/#how-it-works">{hi ? 'कैसे काम करता है' : 'How it works'}</Link>
                  </nav>
                )}
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
                  {'parent' in (meta ?? {}) ? (
                    <>
                      <Link
                        to={
                          routeMetadata.find(
                            (r) => r.id === ('parent' in meta! ? meta!.parent : ''),
                          )?.path ?? '/'
                        }
                      >
                        {routeTitle(
                          routeMetadata.find(
                            (r) => r.id === ('parent' in meta! ? meta!.parent : ''),
                          ),
                          t,
                          hi,
                          !!user,
                        )}
                      </Link>
                      <span>/</span>
                    </>
                  ) : null}
                  <strong>{routeTitle(meta, t, hi, !!user)}</strong>
                </span>
                <div className="top-actions">
                  {user && <SubjectSwitcher />}
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
                    <AccountMenu user={user} busy={busy} signOut={signOut} />
                  ) : (
                    <button
                      className="button small"
                      disabled={busy}
                      onClick={() => (authConfigured ? void signIn() : navigate('/settings'))}
                    >
                      {t.signIn}
                      <ArrowRight size={14} />
                    </button>
                  )}
                </div>
              </header>
              {errorKey && (
                <div role="alert" className="notice">
                  {t[errorKey]}
                </div>
              )}
              {usingAuthEmulator && (
                <p className="notice" role="status">
                  {hi
                    ? 'काल्पनिक खातों के लिए स्थानीय प्रमाणीकरण एमुलेटर'
                    : 'Local Firebase Auth emulator — fictional accounts only'}
                </p>
              )}
              <main key={user?.uid || 'public'} id="main" tabIndex={-1}>
                <Routes>
                  {routeMetadata.map((route) => (
                    <Route
                      key={route.id}
                      path={route.path}
                      element={
                        <RouteAccess
                          access={route.access}
                          title={routeTitle(route, t, hi, !!user)}
                          signedIn={!!user}
                        >
                          {
                            {
                              home: user ? <Cockpit /> : <Landing />,
                              discover: <Discover />,
                              detail: <Detail />,
                              profile: <Profile />,
                              documents: <Documents />,
                              dependent: <Profile />,
                              family: <Workspaces kind="household" />,
                              businesses: <Workspaces kind="business" />,
                              plan: <Plan />,
                              admin: <Admin />,
                              candidate: <Admin />,
                              settings: (
                                <Settings
                                  user={user}
                                  language={language}
                                  setLanguage={setLanguage}
                                  signIn={signIn}
                                />
                              ),
                            }[route.id]
                          }
                        </RouteAccess>
                      }
                    />
                  ))}
                  <Route
                    path="/dashboard"
                    element={<Navigate to={`/${location.search}`} replace />}
                  />
                  <Route
                    path="/my-opportunities"
                    element={<Navigate to={`/plan${location.search}`} replace />}
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
        </SubjectProvider>
      </DirtyFormsProvider>
    </Locale.Provider>
  );
}
export function Cockpit() {
  const context = useSubject();
  const authenticated = true;
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
  const plan = useQuery({
    queryKey: ['plan', context.subject],
    enabled: !!overview.data?.profile_name && context.available && !context.pending,
    retry: false,
    refetchOnWindowFocus: false,
    queryFn: async () => {
      const { data, error } = await api.POST('/v1/plan', {
        body: { subject: context.subject, development: false },
      });
      return data ?? fail(error);
    },
  });
  const nextAction = plan.data?.actions[0];
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
            {(overview.data.personal_pending_actions > 0 ||
              overview.data.assessed_current_opportunities > 0 ||
              overview.data.households > 0 ||
              overview.data.businesses > 0) && (
              <p>
                {overview.data.personal_pending_actions}{' '}
                {hi ? 'व्यक्तिगत कदम' : 'personal pending actions'} ·{' '}
                {overview.data.assessed_current_opportunities}{' '}
                {hi ? 'वर्तमान अवसर जाँचे गए' : 'current opportunities assessed'} ·{' '}
                {overview.data.households} {hi ? 'परिवार' : 'households'} ·{' '}
                {overview.data.businesses} {hi ? 'व्यवसाय' : 'businesses'}
              </p>
            )}
          </div>
          {overview.data.review_candidates != null && (
            <Link className="button secondary" to="/admin">
              {overview.data.review_candidates} {hi ? 'मसौदे समीक्षा में' : 'drafts to review'}
              <ArrowRight size={16} />
            </Link>
          )}
        </section>
      )}
      {plan.isError && <p role="alert">{plan.error.message}</p>}
      <div className="dashboard-actions">
        <Link className="dashboard-primary" to={overview.data?.profile_name ? '/plan' : '/profile'}>
          <span className="eyebrow">
            {context.label} · {hi ? 'अगला उपयोगी कदम' : 'YOUR NEXT USEFUL STEP'}
          </span>
          <h2>
            {nextAction?.title ??
              (overview.data?.profile_name
                ? hi
                  ? 'अपनी तैयारी की योजना देखें'
                  : 'Turn missing information into a plan'
                : hi
                  ? 'आपसे शुरू होता है रास्ता'
                  : 'The path starts with you')}
          </h2>
          <p>
            {hi
              ? 'समीक्षित अवसरों के लिए अपनी जानकारी जाँचें।'
              : 'Understand what is known, what is missing, and which steps can help across opportunities.'}
          </p>
          {nextAction && (
            <span className="action-impact">
              {new Set(nextAction.opportunities.map((o) => o.id)).size}{' '}
              {hi ? 'अवसरों से जुड़ा यह एक कदम' : 'opportunities connected to this one step'}
            </span>
          )}
          <span className="button">
            {overview.data?.profile_name
              ? hi
                ? 'मेरी योजना खोलें'
                : 'Open my unlock plan'
              : hi
                ? 'प्रोफ़ाइल बनाएँ'
                : 'Create your profile'}{' '}
            <ArrowRight size={16} />
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
      {(f.data?.total ?? 0) > 0 && (
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
      )}
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
        <h1>{useLanguage() === 'hi' ? 'पृष्ठ नहीं मिला' : 'Page not found'}</h1>
        <p>
          {useLanguage() === 'hi'
            ? 'यह पता उपलब्ध नहीं है।'
            : 'This address does not exist. Return home or explore published opportunities.'}
        </p>
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
  user: SessionState['user'];
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
        <h2>{user ? t.account : t.signIn}</h2>
        {!authConfigured ? (
          <p>{t.firebaseMissing}</p>
        ) : user ? (
          <>
            <p>{user.displayName}</p>
            <p role="status">
              {account.isError
                ? account.error.message
                : account.data
                  ? language === 'hi'
                    ? 'बैकएंड ने आपकी पहचान की पुष्टि की है।'
                    : 'Your identity is confirmed by the backend.'
                  : t.loading}
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
        <ShieldCheck className="section-icon" />
        <h2>{language === 'hi' ? 'आपके डेटा का नियंत्रण' : 'Your data, your control'}</h2>
        <p>
          {language === 'hi'
            ? 'इस प्रोटोटाइप में केवल काल्पनिक जानकारी प्रयोग करें। वयस्कों का निमंत्रण, दस्तावेज़ सत्यापन और खाता हटाने की सुविधा अभी उपलब्ध नहीं है।'
            : 'Use fictional information in this prototype. Adult invitations, document verification and account deletion are not yet available.'}
        </p>
        {user && (
          <Link className="button secondary" to="/documents">
            {language === 'hi'
              ? 'अपने निजी दस्तावेज़ देखें या हटाएँ'
              : 'View or remove your private documents'}
          </Link>
        )}
        <p>
          {language === 'hi'
            ? 'दस्तावेज़ हटाने पर उसकी पहुँच तुरंत बंद होती है। फ़ाइल हटाने में समस्या हो तो दोबारा कोशिश करें। सीमित इतिहास बना रहता है।'
            : 'Removing a document immediately ends access. If file removal fails, retry it in My Documents. A minimal history record remains.'}
        </p>
      </section>
    </div>
  );
}

function SubjectSwitcher() {
  const context = useSubject();
  const hi = useLanguage() === 'hi';
  return (
    <label className="shell-context">
      <span>{hi ? 'संदर्भ' : 'Context'}</span>
      <select
        aria-label={hi ? 'कार्य संदर्भ चुनें' : 'Switch subject context'}
        value={context.key}
        onChange={(e) => context.select(e.target.value)}
        disabled={context.pending}
      >
        {!context.available && <option value={context.key}>{context.label}</option>}
        {context.options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function AccountMenu({
  user,
  busy,
  signOut,
}: {
  user: NonNullable<SessionState['user']>;
  busy: boolean;
  signOut: () => Promise<void>;
}) {
  const guard = useDiscardGuard();
  const t = useStrings();
  const hi = useLanguage() === 'hi';
  const [open, setOpen] = useState(false);
  return (
    <div
      className="account-menu"
      onKeyDown={(e) => {
        if (e.key === 'Escape') {
          setOpen(false);
          e.currentTarget.querySelector('button')?.focus();
        }
      }}
    >
      <button
        className="account-trigger"
        aria-label={hi ? 'खाता मेनू' : 'Account menu'}
        aria-expanded={open}
        aria-haspopup="menu"
        onClick={() => setOpen((v) => !v)}
      >
        {user.displayName || (hi ? 'खाता' : 'Account')}
        <UserRound size={17} />
      </button>
      {open && (
        <div role="menu">
          <Link role="menuitem" to="/settings" onClick={() => setOpen(false)}>
            {t.account}
          </Link>
          <button
            role="menuitem"
            disabled={busy}
            onClick={() => {
              if (guard.confirmLeave()) void signOut();
            }}
          >
            {t.signOut}
          </button>
        </div>
      )}
    </div>
  );
}

function Logo() {
  return (
    <Link to="/" className="brand" aria-label={`${brand}.`}>
      <span className="brand-icon">
        <ArrowDownLeft size={22} />
      </span>
      <span className="brand-name">
        {brand}
        <span className="brand-dot">.</span>
      </span>
    </Link>
  );
}
function RouteAccess({
  access,
  title,
  signedIn,
  children,
}: {
  access: string;
  title: string;
  signedIn: boolean;
  children: React.ReactNode;
}) {
  const t = useStrings();
  const hi = useLanguage() === 'hi';
  if (!signedIn && (access === 'authenticated' || access === 'admin'))
    return (
      <div className="page auth-required">
        <span className="eyebrow">{hi ? 'आपका निजी कार्यक्षेत्र' : 'YOUR PRIVATE WORKSPACE'}</span>
        <h1>{title}</h1>
        <section className="auth-entry" role="alert">
          <ShieldCheck size={32} />
          <h2>{hi ? 'अपना सुरक्षित कार्यक्षेत्र खोलें' : 'Open your secure workspace'}</h2>
          <p>
            {hi
              ? 'व्यक्तिगत, परिवार और व्यवसाय की जानकारी आपके अधिकृत खाते में अलग रहती है।'
              : 'Your personal, family and business information stays separate and permission-controlled.'}
          </p>
          <Link className="button" to="/settings">
            {t.signIn}
            <ArrowRight size={17} />
          </Link>
        </section>
      </div>
    );
  return children;
}
