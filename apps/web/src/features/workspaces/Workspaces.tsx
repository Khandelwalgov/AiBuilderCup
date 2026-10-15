import { displayLabel } from '../../i18n/format';
import { useDirtyForm } from '../../app/dirty-forms';
import { useSubject } from '../../app/subject-context';
import { ContextLink as Link } from '../../app/subject-context';
import { useEffect, useRef, useState } from 'react';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowRight, BriefcaseBusiness, UsersRound, Plus, ShieldCheck } from 'lucide-react';
import { api, fail } from '../../lib/api/client';
import type { components } from '../../lib/api/schema';
import { useStrings, useLanguage } from '../../app/App';
type Workspace = components['schemas']['WorkspaceView'];
type Fact = components['schemas']['FactInput'];
export function useWorkspaces() {
  return useQuery({
    queryKey: ['workspaces'],
    retry: false,
    queryFn: async () => {
      const { data, error } = await api.GET('/v1/workspaces');
      return data ?? fail(error);
    },
  });
}
export function Workspaces({ kind }: { kind: 'household' | 'business' }) {
  const context = useSubject();
  return <WorkspaceEditor key={context.key + kind} kind={kind} />;
}
function WorkspaceEditor({ kind }: { kind: 'household' | 'business' }) {
  const context = useSubject();
  const t = useStrings();
  const hi = useLanguage() === 'hi';
  const cache = useQueryClient();
  const query = useWorkspaces();
  const [selected, setSelected] = useState<string>(
    context.subject.kind === kind ? (context.subject.id ?? '') : '',
  );
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [legal, setLegal] =
    useState<components['schemas']['BusinessWrite']['legal_status']>('unregistered');
  const [registered, setRegistered] = useState('');
  const [state, setState] = useState('');
  const [district, setDistrict] = useState('');
  const [turnover, setTurnover] = useState('');
  const [dependent, setDependent] = useState('');
  const [age, setAge] = useState('');
  const [responsibility, setResponsibility] = useState(false);
  const signature = JSON.stringify({
    name,
    description,
    legal,
    registered,
    state,
    district,
    turnover,
    dependent,
    age,
    responsibility,
  });
  const baseline = useRef<string | null>(null);
  const submitted = useRef('');
  const dirty = baseline.current !== null && signature !== baseline.current;
  const guard = useDirtyForm(dirty);
  const list = query.data?.filter((w) => w.kind === kind) ?? [];
  const current = list.find((w) => w.id === selected);
  useEffect(() => {
    if (dirty) return;
    setName(current?.name ?? '');
    setDescription(current?.description ?? '');
    setLegal((current?.legal_status as typeof legal) ?? 'unregistered');
    const value = (key: string) => String(current?.facts.find((f) => f.key === key)?.value ?? '');
    setRegistered(value('business_registered'));
    setState(value('residence_state'));
    setDistrict(value('residence_district'));
    setTurnover(value('business_turnover'));
    baseline.current = JSON.stringify({
      name: current?.name ?? '',
      description: current?.description ?? '',
      legal: current?.legal_status ?? 'unregistered',
      registered: value('business_registered'),
      state: value('residence_state'),
      district: value('residence_district'),
      turnover: value('business_turnover'),
      dependent,
      age,
      responsibility,
    });
  }, [current, dirty, dependent, age, responsibility]);
  const save = useMutation({
    mutationFn: async () => {
      if (kind === 'household') {
        const response = selected
          ? await api.PUT('/v1/households/{identifier}', {
              params: { path: { identifier: selected } },
              body: { name, primary: true },
            })
          : await api.POST('/v1/households', { body: { name, primary: true } });
        return response.data ?? fail(response.error);
      }
      const facts: Fact[] = [
        { key: 'business_registered', value: registered === '' ? null : registered === 'true' },
        { key: 'residence_state', value: state || null },
        { key: 'residence_district', value: district || null },
        { key: 'business_turnover', value: turnover === '' ? null : Number(turnover) },
      ];
      const body = { name, description, legal_status: legal, facts };
      const response = selected
        ? await api.PUT('/v1/businesses/{identifier}', {
            params: { path: { identifier: selected } },
            body,
          })
        : await api.POST('/v1/businesses', { body });
      return response.data ?? fail(response.error);
    },
    onSuccess: async (data) => {
      baseline.current = submitted.current;
      await cache.invalidateQueries({ queryKey: ['workspaces'] });
      void cache.invalidateQueries({ queryKey: ['dashboard-summary'] });
      void cache.invalidateQueries({ queryKey: ['plan'] });
      setSelected(data.id);
    },
  });
  const add = useMutation({
    mutationFn: async () => {
      if (!responsibility) throw new Error('Guardian responsibility is required.');
      const { data, error } = await api.POST('/v1/households/{identifier}/dependents', {
        params: { path: { identifier: selected } },
        body: {
          display_name: dependent,
          facts: [{ key: 'age', value: age === '' ? null : Number(age) }],
          guardian_responsibility_confirmed: true,
          relationship: 'legal_guardian',
        },
      });
      return data ?? fail(error);
    },
    onSuccess: () => {
      void cache.invalidateQueries({ queryKey: ['workspaces'] });
      setDependent('');
      setAge('');
      setResponsibility(false);
    },
  });
  const revoke = useMutation({
    mutationFn: async (identifier: string) => {
      const { data, error } = await api.POST('/v1/people/{identifier}/guardian-access/revoke', {
        params: { path: { identifier } },
        body: { confirm_revocation: true },
      });
      return data ?? fail(error);
    },
    onSuccess: () => {
      void cache.invalidateQueries({ queryKey: ['workspaces'] });
      cache.removeQueries({ queryKey: ['plan'] });
      cache.removeQueries({ queryKey: ['personal-profile'] });
    },
  });
  const title = kind === 'household' ? t.family : t.businesses;
  if (query.isPending)
    return (
      <div className="page" role="status">
        {t.loading}
      </div>
    );
  if (query.isError)
    return (
      <div className="page narrow">
        <section className="panel">
          <h1>{title}</h1>
          <p role="alert">{query.error.message}</p>
          <Link className="button" to="/profile">
            {t.profile}
          </Link>
          <Link className="text-button" to="/settings">
            {t.signIn}
          </Link>
        </section>
      </div>
    );
  return (
    <div className="page">
      <div className="page-heading">
        <span className="eyebrow">{hi ? 'आपका कार्यक्षेत्र' : 'YOUR WORKSPACE'}</span>
        <h1>{title}</h1>
        <p>
          {kind === 'household'
            ? hi
              ? 'जिम्मेदारी के साथ परिवार की तैयारी करें। वयस्कों की निजी जानकारी के लिए उनकी अनुमति आवश्यक है।'
              : 'Plan together, with permission. Adult records stay private until explicitly shared.'
            : hi
              ? 'हर व्यवसाय के लिए एक जगह — पंजीकृत होना आवश्यक नहीं।'
              : 'A clear starting point for every business, including unregistered enterprises.'}
        </p>
      </div>
      <section className="context-identity">
        <div className="context-monogram">
          {kind === 'household' ? <UsersRound size={32} /> : <BriefcaseBusiness size={32} />}
        </div>
        <div>
          <span className="eyebrow">
            {kind === 'household'
              ? hi
                ? 'अनुमति के साथ तैयारी'
                : 'PREPARE TOGETHER, WITH PERMISSION'
              : hi
                ? 'अलग व्यवसाय संदर्भ'
                : 'YOUR INDEPENDENT BUSINESS CONTEXT'}
          </span>
          <h2>
            {current?.name ??
              (kind === 'household'
                ? hi
                  ? 'हर व्यक्ति का अपना रास्ता'
                  : 'Every person has their own path'
                : hi
                  ? 'हर उद्यम का एक आरंभ'
                  : 'Every enterprise starts somewhere')}
          </h2>
          <p>
            {current
              ? kind === 'household'
                ? `${current.members.length} ${hi ? 'दिखाई देने वाली सदस्य प्रविष्टियाँ · तथ्यों का मिश्रण नहीं' : 'visible member entries · facts stay separate'}`
                : `${displayLabel(current.role, hi)} · ${current.legal_status ?? (hi ? 'स्वरूप अज्ञात' : 'structure unknown')}`
              : hi
                ? 'सिर्फ आवश्यक जानकारी से शुरू करें।'
                : 'Start small. Add only the information a relevant opportunity needs.'}
          </p>
        </div>
        <span className="context-boundary">
          <ShieldCheck size={17} />
          {hi ? 'पहुँच सर्वर पर जाँची जाती है' : 'Access checked on the server'}
        </span>
      </section>
      <div className="workspace-grid context-workbench">
        <section className="panel context-list">
          <h2>{hi ? 'कार्यस्थल चुनें' : 'Your contexts'}</h2>
          {list.map((w) => (
            <button
              className={`context-card ${selected === w.id ? 'selected' : ''}`}
              key={w.id}
              onClick={() => {
                if (context.key !== `${kind}:${w.id}`) {
                  context.select(`${kind}:${w.id}`);
                  return;
                }
                if (guard.confirmLeave()) {
                  baseline.current = null;
                  setSelected(w.id);
                }
              }}
            >
              {kind === 'household' ? <UsersRound /> : <BriefcaseBusiness />}
              <span>
                <strong>{w.name}</strong>
                <small>
                  {displayLabel(w.role, hi)} ·{' '}
                  {w.kind === 'household'
                    ? `${w.members.length} ${hi ? 'सदस्य' : 'members'}`
                    : w.legal_status}
                </small>
              </span>
              <ArrowRight size={16} />
            </button>
          ))}
          <button
            className="text-button"
            onClick={() => {
              if (!guard.confirmLeave()) return;
              baseline.current = null;
              setSelected('');
              setName('');
              setDescription('');
              setLegal('unregistered');
              setRegistered('');
              setState('');
              setDistrict('');
              setTurnover('');
              setDependent('');
              setAge('');
              setResponsibility(false);
            }}
          >
            <Plus size={16} />
            {hi ? 'नया बनाएं' : 'Create another'}
          </button>
          {!list.length && (
            <p>
              {hi
                ? 'पहले अपना व्यक्तिगत प्रोफ़ाइल बनाएं, फिर शुरू करें।'
                : 'Create your personal profile first, then add your first context.'}
            </p>
          )}
        </section>
        <div>
          {kind === 'household' && current ? (
            <>
              <section className="panel">
                <h2>{hi ? 'परिवार का प्रबंधन' : 'Manage household'}</h2>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    submitted.current = signature;
                    save.mutate();
                  }}
                >
                  <label className="field">
                    {hi ? 'परिवार का नाम' : 'Household name'}
                    <input
                      required
                      maxLength={100}
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                    />
                  </label>
                  <button className="text-button" disabled={save.isPending}>
                    {hi ? 'सहेजें और मुख्य परिवार चुनें' : 'Save and make primary household'}
                  </button>
                  {current.primary && <small>{hi ? 'मुख्य परिवार' : 'Primary household'}</small>}
                  {save.isError && <p role="alert">{save.error.message}</p>}
                </form>
                <p className="trust-line">
                  <ShieldCheck size={16} />
                  {hi ? 'केवल अधिकृत जानकारी' : 'Only authorized information'}
                </p>
                {current.members.map((m, i) => (
                  <div className="member-row" key={i}>
                    <span className="member-initial" aria-hidden="true">
                      {m.id ? String(m.name).slice(0, 1) : '—'}
                    </span>
                    <strong>{String(m.name)}</strong>
                    <small>{displayLabel(String(m.access), hi)}</small>
                    {m.id != null && (
                      <Link to={`/people/${String(m.id)}/edit`}>
                        {hi ? 'प्रोफ़ाइल संपादित करें' : 'Edit profile'} <ArrowRight size={14} />
                      </Link>
                    )}
                    {m.id != null && (
                      <Link className="member-plan" to={`/plan?kind=person&id=${String(m.id)}`}>
                        {hi ? 'इस व्यक्ति की योजना' : 'This person’s plan'}
                        <ArrowRight size={14} />
                      </Link>
                    )}
                    {m.managed === true && (
                      <button
                        className="text-button"
                        disabled={revoke.isPending}
                        onClick={() => {
                          if (
                            window.confirm(
                              hi
                                ? 'इस आश्रित का प्रबंधन बंद करें? जानकारी और इतिहास सुरक्षित रहेंगे। पुनः पहुँच के लिए प्रशासक की सहायता आवश्यक होगी।'
                                : 'Stop managing this dependent? Records and history remain preserved. Restoring access requires administrator assistance.',
                            )
                          )
                            revoke.mutate(String(m.id));
                        }}
                      >
                        {hi ? 'प्रबंधन बंद करें' : 'Stop managing'}
                      </button>
                    )}
                  </div>
                ))}
                {revoke.isError && <p role="alert">{revoke.error.message}</p>}
                <Link className="button" to={`/plan?kind=household&id=${current.id}`}>
                  {hi ? 'परिवार की योजना' : 'Household plan'}
                </Link>
                <p className="muted">
                  {hi
                    ? 'परिवार की आय नहीं जोड़ी जाती। नियम-विशिष्ट आय अस्पष्ट होने पर परिणाम अज्ञात रहेगा।'
                    : 'Household income is never automatically summed. Scheme-specific definitions remain unknown until supported.'}
                </p>
              </section>
              <form
                className="panel"
                onSubmit={(e) => {
                  e.preventDefault();
                  add.mutate();
                }}
              >
                <h2>{hi ? 'अधिकृत आश्रित जोड़ें' : 'Add a managed dependent'}</h2>
                <p>
                  {hi
                    ? 'डेमो में केवल काल्पनिक जानकारी प्रयोग करें।'
                    : 'Use fictional information in this prototype. Adult connections require consent and are not yet available.'}
                </p>
                <label className="field">
                  {t.displayName}
                  <input
                    required
                    maxLength={80}
                    value={dependent}
                    onChange={(e) => setDependent(e.target.value)}
                  />
                </label>
                <label className="field">
                  {hi ? 'आयु (अज्ञात छोड़ सकते हैं)' : 'Age (leave blank if unknown)'}
                  <input
                    type="number"
                    min="0"
                    max="130"
                    value={age}
                    onChange={(e) => setAge(e.target.value)}
                  />
                </label>
                <label className="check-label">
                  <input
                    required
                    type="checkbox"
                    checked={responsibility}
                    onChange={(e) => setResponsibility(e.target.checked)}
                  />
                  {hi
                    ? 'मैं इस आश्रित की जानकारी संभालने के लिए अधिकृत अभिभावक हूँ।'
                    : 'I am the legal guardian authorized to manage this dependent’s information.'}
                </label>
                <button className="button" disabled={add.isPending}>
                  {hi ? 'आश्रित जोड़ें' : 'Add dependent'}
                </button>
                {add.isError && <p role="alert">{add.error.message}</p>}
              </form>
            </>
          ) : (
            <form
              className="panel"
              onSubmit={(e) => {
                e.preventDefault();
                submitted.current = signature;
                save.mutate();
              }}
            >
              <h2>
                {selected
                  ? hi
                    ? 'व्यवसाय संपादित करें'
                    : 'Edit business'
                  : hi
                    ? 'एक नया आरंभ'
                    : 'Start a new context'}
              </h2>
              <label className="field">
                {hi ? 'नाम' : 'Name'}
                <input
                  required
                  maxLength={100}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </label>
              {kind === 'business' && (
                <>
                  <label className="field">
                    {hi ? 'विवरण' : 'Description'}
                    <textarea
                      maxLength={1000}
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                    />
                  </label>
                  <label className="field">
                    {hi ? 'व्यवसाय का स्वरूप' : 'Business structure'}
                    <select
                      value={legal}
                      onChange={(e) => setLegal(e.target.value as typeof legal)}
                    >
                      {['unregistered', 'sole_proprietor', 'partnership', 'company', 'other'].map(
                        (v) => (
                          <option key={v} value={v}>
                            {hi
                              ? {
                                  unregistered: 'अपंजीकृत',
                                  sole_proprietor: 'एकल स्वामित्व',
                                  partnership: 'साझेदारी',
                                  company: 'कंपनी',
                                  other: 'अन्य',
                                }[v] || v
                              : v.replace('_', ' ')}
                          </option>
                        ),
                      )}
                    </select>
                  </label>
                  <label className="field">
                    {hi ? 'पंजीकरण की स्थिति' : 'Registration status'}
                    <select value={registered} onChange={(e) => setRegistered(e.target.value)}>
                      <option value="">{t.unknown}</option>
                      <option value="true">{t.yes}</option>
                      <option value="false">{t.no}</option>
                    </select>
                  </label>
                  <div className="form-grid">
                    <label className="field">
                      {hi ? 'संचालन का राज्य' : 'Operating state'}
                      <input value={state} onChange={(e) => setState(e.target.value)} />
                    </label>
                    <label className="field">
                      {hi ? 'संचालन का जिला' : 'Operating district'}
                      <input value={district} onChange={(e) => setDistrict(e.target.value)} />
                    </label>
                  </div>
                  <label className="field">
                    {hi ? 'टर्नओवर (₹, वैकल्पिक)' : 'Turnover (₹, optional)'}
                    <input
                      type="number"
                      min="0"
                      value={turnover}
                      onChange={(e) => setTurnover(e.target.value)}
                    />
                    <small>
                      {hi
                        ? 'अवधि और परिभाषा अस्पष्ट होने पर नियम अज्ञात रहेगा।'
                        : 'A rule stays unknown when its assessment period or definition is missing. No registration number is required.'}
                    </small>
                  </label>
                </>
              )}
              <button className="button" disabled={save.isPending || current?.role === 'viewer'}>
                {save.isPending ? t.saving : hi ? 'सहेजें' : 'Save context'}
              </button>
              {save.isError && <p role="alert">{save.error.message}</p>}
              {save.isSuccess && !dirty && <p role="status">{hi ? 'सहेजा गया' : 'Saved'}</p>}
              {current && (
                <Link className="text-button" to={`/plan?kind=business&id=${current.id}`}>
                  {hi ? 'व्यवसाय की योजना देखें' : 'Open business plan'} <ArrowRight size={16} />
                </Link>
              )}
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
export type { Workspace };
