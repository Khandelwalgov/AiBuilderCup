import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowRight, BriefcaseBusiness, UsersRound, Plus, ShieldCheck } from 'lucide-react';
import { api, fail } from '../../lib/api/client';
import type { components } from '../../lib/api/schema';
import { useStrings } from '../../app/App';
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
  const t = useStrings();
  const hi = document.documentElement.lang === 'hi';
  const cache = useQueryClient();
  const query = useWorkspaces();
  const [selected, setSelected] = useState<string>('');
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
  const list = query.data?.filter((w) => w.kind === kind) ?? [];
  const current = list.find((w) => w.id === selected);
  useEffect(() => {
    setName(current?.name ?? '');
    setDescription(current?.description ?? '');
    setLegal((current?.legal_status as typeof legal) ?? 'unregistered');
    const value = (key: string) => String(current?.facts.find((f) => f.key === key)?.value ?? '');
    setRegistered(value('business_registered'));
    setState(value('residence_state'));
    setDistrict(value('residence_district'));
    setTurnover(value('business_turnover'));
  }, [current]);
  const save = useMutation({
    mutationFn: async () => {
      if (kind === 'household') {
        const { data, error } = await api.POST('/v1/households', { body: { name, primary: true } });
        return data ?? fail(error);
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
      await cache.invalidateQueries({ queryKey: ['workspaces'] });
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
      <div className="workspace-grid">
        <section className="panel context-list">
          <h2>{hi ? 'कार्यस्थल चुनें' : 'Your contexts'}</h2>
          {list.map((w) => (
            <button
              className={`context-card ${selected === w.id ? 'selected' : ''}`}
              key={w.id}
              onClick={() => setSelected(w.id)}
            >
              {kind === 'household' ? <UsersRound /> : <BriefcaseBusiness />}
              <span>
                <strong>{w.name}</strong>
                <small>
                  {w.role} ·{' '}
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
              setSelected('');
              setName('');
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
                <h2>{current.name}</h2>
                <p className="trust-line">
                  <ShieldCheck size={16} />
                  {hi ? 'केवल अधिकृत जानकारी' : 'Only authorized information'}
                </p>
                {current.members.map((m, i) => (
                  <div className="member-row" key={i}>
                    <strong>{String(m.name)}</strong>
                    <small>{String(m.access)}</small>
                    {m.id != null && (
                      <Link to={`/people/${String(m.id)}/edit`}>
                        {hi ? 'तैयारी देखें' : 'View readiness'} <ArrowRight size={14} />
                      </Link>
                    )}
                  </div>
                ))}
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
                            {v.replace('_', ' ')}
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
              {save.isSuccess && <p role="status">{hi ? 'सहेजा गया' : 'Saved'}</p>}
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
