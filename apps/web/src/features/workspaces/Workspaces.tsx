import { useEffect, useRef, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useDirtyForm, useDiscardGuard } from '../../app/dirty-forms';
import { useSubject, ContextLink as Link } from '../../app/subject-context';
import { useStrings, useLanguage } from '../../app/App';
import { api, fail, RequestError } from '../../lib/api/client';
import { displayLabel } from '../../i18n/format';
import type { components } from '../../lib/api/schema';
type Workspace = components['schemas']['WorkspaceView'];
type Fact = components['schemas']['FactInput'];
type Kind = 'household' | 'business';
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
export function Workspaces({ kind }: { kind: Kind }) {
  const c = useSubject();
  const [params] = useSearchParams();
  return <WorkspacePage key={c.key + kind + (params.get('field') ?? '')} kind={kind} />;
}
function WorkspacePage({ kind }: { kind: Kind }) {
  const c = useSubject(),
    hi = useLanguage() === 'hi',
    cache = useQueryClient();
  const navigate = useNavigate();
  const discardGuard = useDiscardGuard();
  const query = useWorkspaces();
  const [params] = useSearchParams();
  const [creating, setCreating] = useState(false),
    [editing, setEditing] = useState(Boolean(params.get('field'))),
    [selected, setSelected] = useState(c.subject.kind === kind ? (c.subject.id ?? '') : '');
  const list = query.data?.filter((w) => w.kind === kind) ?? [];
  const current =
    list.find((w) => w.id === selected) ??
    (!creating ? (list.find((w) => w.primary) ?? list[0]) : undefined);
  const revoke = useMutation({
    mutationFn: async (id: string) => {
      const { data, error } = await api.POST('/v1/people/{identifier}/guardian-access/revoke', {
        params: { path: { identifier: id } },
        body: { confirm_revocation: true },
      });
      return data ?? fail(error);
    },
    onSuccess: () => {
      void cache.invalidateQueries({ queryKey: ['workspaces'] });
      cache.removeQueries({ queryKey: ['personal-profile'] });
      cache.removeQueries({ queryKey: ['documents'] });
      cache.removeQueries({ queryKey: ['document-needs'] });
      cache.removeQueries({ queryKey: ['plan'] });
    },
  });
  async function saved(data: Workspace) {
    await cache.invalidateQueries({ queryKey: ['workspaces'] });
    for (const key of [
      'dashboard-summary',
      'plan',
      'hybrid-search',
      'scenario-base',
      'research-guidance',
    ])
      void cache.invalidateQueries({ queryKey: [key] });
    setCreating(false);
    setEditing(false);
    setSelected(data.id);
    navigate(
      c.href(`/${kind === 'household' ? 'family' : 'businesses'}?kind=${kind}&id=${data.id}`),
    );
  }
  if (c.subject.kind === kind && c.subject.id && !c.available && !c.pending)
    return (
      <div className="page panel" role="alert">
        {c.label}
      </div>
    );
  if (query.isPending)
    return (
      <div className="page" role="status">
        {hi ? 'लोड हो रहा है…' : 'Loading…'}
      </div>
    );
  if (query.isError)
    return (
      <div className="page panel" role="alert">
        <h1>{hi ? 'कार्यस्थल' : 'Workspace'}</h1>
        <p>{query.error.message}</p>
        <button className="button" onClick={() => void query.refetch()}>
          {hi ? 'दोबारा कोशिश करें' : 'Try again'}
        </button>
      </div>
    );
  return (
    <div className="page workspace-journey">
      <div className="page-heading">
        <span className="eyebrow">
          {kind === 'household'
            ? hi
              ? 'साथ में तैयारी'
              : 'PREPARE TOGETHER'
            : hi
              ? 'आपका उद्यम'
              : 'YOUR ENTERPRISE'}
        </span>
        <h1>{kind === 'household' ? (hi ? 'परिवार' : 'Family') : hi ? 'व्यवसाय' : 'Businesses'}</h1>
        <p>
          {kind === 'household'
            ? hi
              ? 'परिवार के लोगों की जानकारी और दस्तावेज़ अलग रखें। केवल अधिकृत आश्रितों का प्रबंधन करें।'
              : 'Keep each person’s information and documents separate. Manage dependents only with guardian authorization.'
            : hi
              ? 'छोटी शुरुआत करें। पंजीकृत और अपंजीकृत, दोनों उद्यमों के लिए।'
              : 'Start small, whether your enterprise is registered or informal.'}
        </p>
      </div>
      {list.length > 0 && (
        <div className="workspace-tabs" aria-label={hi ? 'आपके कार्यस्थल' : 'Your workspaces'}>
          {list.map((w) => (
            <Link
              className={`context-card ${current?.id === w.id ? 'selected' : ''}`}
              key={w.id}
              to={`/${kind === 'household' ? 'family' : 'businesses'}?kind=${kind}&id=${w.id}`}
            >
              {w.name}
            </Link>
          ))}
          <button
            className="text-button"
            onClick={() => {
              if (!discardGuard.confirmLeave()) return;
              setCreating(true);
              setEditing(false);
              setSelected('');
            }}
          >
            {hi ? 'नया बनाएं' : 'Create another'}
          </button>
        </div>
      )}
      {!current || creating || editing ? (
        <WorkspaceForm
          key={current?.id ?? 'new'}
          kind={kind}
          current={creating ? undefined : current}
          onSaved={saved}
          onCancel={() => {
            setCreating(false);
            setEditing(false);
          }}
          requested={params.get('field')}
        />
      ) : (
        <>
          <section className="panel workspace-overview">
            <div className="page-heading">
              <div>
                <span className="eyebrow">{hi ? 'सहेजा गया कार्यस्थल' : 'SAVED WORKSPACE'}</span>
                <h2>{current.name}</h2>
                <p role="status">{hi ? 'सहेजा गया और अद्यतन' : 'Saved and up to date'}</p>
              </div>
              {current.role !== 'viewer' && (
                <button className="button secondary" onClick={() => setEditing(true)}>
                  {hi ? 'जानकारी संपादित करें' : 'Edit details'}
                </button>
              )}
            </div>
            {kind === 'business' ? (
              <>
                <p>
                  {current.legal_status === 'unknown'
                    ? hi
                      ? 'कानूनी संरचना नहीं बताई गई'
                      : 'Legal structure not specified'
                    : displayLabel(current.legal_status ?? 'unknown', hi)}{' '}
                  · {displayLabel(current.role, hi)}
                </p>
                {current.description && <p>{current.description}</p>}
                <dl>
                  {current.facts
                    .filter((f) => f.value != null)
                    .map((f) => (
                      <div key={f.id}>
                        <dt>{workspaceLabel(f.key, hi)}</dt>
                        <dd>
                          {typeof f.value === 'boolean'
                            ? f.value
                              ? hi
                                ? 'हाँ'
                                : 'Yes'
                              : hi
                                ? 'नहीं'
                                : 'No'
                            : f.key === 'business_operating_status'
                              ? displayLabel(String(f.value), hi)
                              : String(f.value)}
                        </dd>
                      </div>
                    ))}
                </dl>
                <p>
                  {hi
                    ? 'ये व्यवसाय के उत्तर हैं; व्यक्तिगत जानकारी इसमें नहीं जोड़ी जाती।'
                    : 'These answers belong to this business. Personal information is not added to them.'}
                </p>
              </>
            ) : (
              <>
                <p>
                  {hi
                    ? 'हर आश्रित का अपना प्रोफ़ाइल, प्रमाण और योजना है। वयस्कों के निजी रिकॉर्ड के लिए अलग अनुमति आवश्यक है।'
                    : 'Each dependent has their own profile, evidence and plan. Adults’ private records require their own permission.'}
                </p>
                {current.members.length === 0 && (
                  <p>
                    {hi
                      ? 'अभी कोई आश्रित नहीं जोड़ा गया। नीचे से शुरू करें।'
                      : 'No dependents added yet. Start below when you are ready.'}
                  </p>
                )}
                {current.members.map((member, i) => (
                  <article className="member-row" key={i}>
                    {member.id && member.access === 'authorized' ? (
                      <>
                        <div>
                          <h3>{String(member.name)}</h3>
                          <p>
                            {member.self === true
                              ? hi
                                ? 'आपका व्यक्तिगत प्रोफ़ाइल'
                                : 'Your personal profile'
                              : member.managed
                                ? hi
                                  ? 'आपके द्वारा प्रबंधित आश्रित'
                                  : 'Dependent you manage'
                                : hi
                                  ? 'अधिकृत व्यक्ति'
                                  : 'Authorized person'}
                          </p>
                        </div>
                        <div className="document-actions">
                          <Link
                            className="button secondary"
                            to={
                              member.self === true
                                ? '/profile?kind=person'
                                : `/people/${member.id}/edit`
                            }
                          >
                            {member.self === true
                              ? hi
                                ? 'मेरा प्रोफ़ाइल'
                                : 'My profile'
                              : hi
                                ? 'प्रोफ़ाइल और सवाल'
                                : 'Profile and questions'}
                          </Link>
                          <Link
                            to={
                              member.self === true
                                ? '/documents?kind=person'
                                : `/documents?kind=person&id=${member.id}`
                            }
                          >
                            {hi ? 'इस व्यक्ति के दस्तावेज़' : 'This person’s documents'}
                          </Link>
                          <Link
                            to={
                              member.self === true
                                ? '/plan?kind=person'
                                : `/plan?kind=person&id=${member.id}`
                            }
                          >
                            {hi ? 'इस व्यक्ति की योजना' : 'This person’s plan'}
                          </Link>
                          {member.managed === true && (
                            <button
                              className="text-button"
                              disabled={revoke.isPending}
                              onClick={() => {
                                if (
                                  window.confirm(
                                    hi
                                      ? 'इस आश्रित का प्रबंधन बंद करें? रिकॉर्ड सुरक्षित रहेंगे, लेकिन आपकी पहुँच हट जाएगी।'
                                      : 'Stop managing this dependent? Records stay preserved, but your access will be removed.',
                                  )
                                )
                                  revoke.mutate(String(member.id));
                              }}
                            >
                              {hi ? 'प्रबंधन बंद करें' : 'Stop managing'}
                            </button>
                          )}
                        </div>
                      </>
                    ) : (
                      <p>
                        {hi
                          ? 'वयस्क की अनुमति आवश्यक — निजी पहचान या रिकॉर्ड साझा नहीं हैं।'
                          : 'Adult permission required — private identity and records are not shared.'}
                      </p>
                    )}
                  </article>
                ))}
              </>
            )}
            <div className="document-actions">
              <Link className="button" to={`/plan?kind=${kind}&id=${current.id}`}>
                {hi ? 'तैयारी की योजना खोलें' : 'Open readiness plan'}
              </Link>
              <Link className="button secondary" to={`/documents?kind=${kind}&id=${current.id}`}>
                {kind === 'business'
                  ? hi
                    ? 'व्यवसाय के दस्तावेज़'
                    : 'Business documents'
                  : hi
                    ? 'परिवार के साझा दस्तावेज़'
                    : 'Household documents'}
              </Link>
            </div>
            {revoke.isError && <p role="alert">{revoke.error.message}</p>}
          </section>
          {kind === 'household' && current.role !== 'viewer' && (
            <DependentForm
              household={current.id}
              onSaved={() => cache.invalidateQueries({ queryKey: ['workspaces'] })}
            />
          )}
        </>
      )}
    </div>
  );
}
function workspaceLabel(key: string, hi: boolean) {
  const labels: Record<string, [string, string]> = {
    business_registered: ['Registered business', 'पंजीकृत व्यवसाय'],
    business_turnover: ['Annual turnover', 'वार्षिक टर्नओवर'],
    business_registration_state: ['Registration state', 'पंजीकरण का राज्य'],
    business_registration_district: ['Registration district', 'पंजीकरण का जिला'],
    business_operating_status: ['Business activity', 'व्यवसाय की गतिविधि'],
    residence_state: ['Operating state', 'संचालन राज्य'],
    residence_district: ['Operating district', 'संचालन जिला'],
    has_registration_certificate: [
      'Registration document (self-reported)',
      'पंजीकरण प्रमाणपत्र (स्वयं बताया)',
    ],
  };
  return labels[key]?.[hi ? 1 : 0] ?? (hi ? 'अन्य जानकारी' : 'Other information');
}
function initial(current?: Workspace) {
  const get = (key: string) =>
    String(
      current?.facts.find((f) => f.key === key && ['user_supplied', 'unknown'].includes(f.origin))
        ?.value ?? '',
    );
  const turnover = current?.facts.find(
    (f) => f.key === 'business_turnover' && ['user_supplied', 'unknown'].includes(f.origin),
  );
  return {
    name: current?.name ?? '',
    description: current?.description ?? '',
    legal: current?.legal_status ?? 'unknown',
    registered: get('business_registered'),
    udyam: get('business_udyam_registered'),
    size: get('business_size'),
    sector: get('business_sector'),
    similar: get('business_similar_assistance'),
    state: get('residence_state'),
    district: get('residence_district'),
    registrationState: get('business_registration_state'),
    registrationDistrict: get('business_registration_district'),
    activity: get('business_operating_status'),
    turnover: get('business_turnover'),
    period: String(turnover?.context?.income_period ?? ''),
    definition: String(turnover?.context?.income_definition ?? ''),
  };
}
function WorkspaceForm({
  kind,
  current,
  onSaved,
  onCancel,
  requested,
}: {
  kind: Kind;
  current?: Workspace;
  onSaved: (w: Workspace) => void;
  onCancel: () => void;
  requested: string | null;
}) {
  const hi = useLanguage() === 'hi',
    t = useStrings();
  const [draft, setDraft] = useState(() => initial(current));
  const baseline = useRef(JSON.stringify(initial(current))),
    revision = useRef(current?.revision);
  const [optional, setOptional] = useState(Boolean(current || requested)),
    [financial, setFinancial] = useState(
      requested === 'business_turnover' ||
        current?.facts.some((f) => f.key === 'business_turnover' && f.value != null),
    );
  const dirty = JSON.stringify(draft) !== baseline.current;
  const guard = useDirtyForm(dirty);
  useEffect(() => {
    if (!dirty && current) {
      const next = initial(current);
      setDraft(next);
      baseline.current = JSON.stringify(next);
      revision.current = current.revision;
    }
  }, [current, dirty]);
  const [stage, setStage] = useState(current ? 1 : 0);
  const mutation = useMutation({
    mutationFn: async () => {
      if (kind === 'household') {
        const body = {
          name: draft.name.trim(),
          primary: true,
          ...(revision.current ? { expected_revision: revision.current } : {}),
        };
        const result = current
          ? await api.PUT('/v1/households/{identifier}', {
              params: { path: { identifier: current.id } },
              body,
            })
          : await api.POST('/v1/households', { body });
        return result.data ?? fail(result.error);
      }
      const factMap = new Map<Fact['key'], Fact>(
        (current?.facts ?? [])
          .filter((f) => ['user_supplied', 'unknown'].includes(f.origin))
          .map((f) => [
            f.key as Fact['key'],
            {
              key: f.key as Fact['key'],
              value: f.value,
              valid_from: f.valid_from,
              valid_until: f.valid_until,
              income_period: (f.context?.income_period as string) ?? null,
              income_definition: (f.context?.income_definition as string) ?? null,
            },
          ]),
      );
      const supplied: Fact[] = [
        {
          key: 'business_udyam_registered',
          value: draft.udyam === '' ? null : draft.udyam === 'true',
        },
        { key: 'business_size', value: draft.size || null },
        { key: 'business_sector', value: draft.sector || null },
        {
          key: 'business_similar_assistance',
          value: draft.similar === '' ? null : draft.similar === 'true',
        },
        {
          key: 'business_registered',
          value: draft.registered === '' ? null : draft.registered === 'true',
        },
        { key: 'residence_state', value: draft.state || null },
        { key: 'residence_district', value: draft.district || null },
        { key: 'business_registration_state', value: draft.registrationState || null },
        { key: 'business_registration_district', value: draft.registrationDistrict || null },
        { key: 'business_operating_status', value: draft.activity || null },
        {
          key: 'business_turnover',
          value: draft.turnover === '' ? null : Number(draft.turnover),
          income_period: draft.period || null,
          income_definition: draft.definition || null,
        },
      ];
      for (const fact of supplied)
        if (factMap.has(fact.key) || fact.value != null)
          factMap.set(fact.key, { ...factMap.get(fact.key), ...fact });
      const body = {
        name: draft.name.trim(),
        description: draft.description || null,
        legal_status: draft.legal as components['schemas']['BusinessWrite']['legal_status'],
        facts: Array.from(factMap.values()),
        ...(revision.current ? { expected_revision: revision.current } : {}),
      };
      const result = current
        ? await api.PUT('/v1/businesses/{identifier}', {
            params: { path: { identifier: current.id } },
            body,
          })
        : await api.POST('/v1/businesses', { body });
      return result.data ?? fail(result.error);
    },
    onSuccess: (data) => {
      baseline.current = JSON.stringify(draft);
      guard.markSaved();
      onSaved(data);
    },
  });
  function change(patch: Partial<typeof draft>) {
    setDraft({ ...draft, ...patch });
    mutation.reset();
  }
  return (
    <form
      className={`panel guided-workspace ${kind}`}
      onSubmit={(e) => {
        e.preventDefault();
        if (kind === 'business' && !current && stage === 0) {
          setStage(1);
          return;
        }
        if (dirty && !mutation.isPending) mutation.mutate();
      }}
    >
      <span className="eyebrow">
        {kind === 'household'
          ? hi
            ? 'पहले घर को पहचान दें'
            : 'FIRST, NAME YOUR HOUSEHOLD'
          : current
            ? hi
              ? 'व्यवसाय की जानकारी'
              : 'BUSINESS DETAILS'
            : hi
              ? 'अपने उद्यम से शुरू करें'
              : 'START WITH YOUR ENTERPRISE'}
      </span>
      <h2>
        {current
          ? hi
            ? 'सहेजी जानकारी बदलें'
            : 'Edit saved details'
          : kind === 'household'
            ? hi
              ? 'अपना परिवार बनाएं'
              : 'Create your household'
            : hi
              ? 'अपना व्यवसाय बनाएं'
              : 'Create your business'}
      </h2>
      <p>
        {kind === 'household'
          ? hi
            ? 'एक नाम से शुरू करें। फिर अधिकृत आश्रित जोड़ सकते हैं।'
            : 'Start with a name. You can add guardian-authorized dependents next.'
          : hi
            ? 'पंजीकरण संख्या या वित्तीय विवरण शुरू करने के लिए आवश्यक नहीं हैं।'
            : 'No registration number or financial details are required to get started.'}
      </p>
      <p role="status">
        {mutation.isPending
          ? t.saving
          : dirty
            ? hi
              ? 'सहेजे नहीं गए बदलाव'
              : 'Unsaved changes'
            : current
              ? hi
                ? 'कोई बदलाव नहीं'
                : 'No changes to save'
              : hi
                ? 'अभी नहीं बना'
                : 'Not yet created'}
      </p>
      <fieldset disabled={mutation.isPending}>
        <label className="field">
          {kind === 'household'
            ? hi
              ? 'परिवार का नाम'
              : 'Household name'
            : hi
              ? 'व्यवसाय का नाम'
              : 'Business name'}
          <input
            required
            maxLength={100}
            value={draft.name}
            onChange={(e) => change({ name: e.target.value })}
          />
        </label>
        {kind === 'business' && (
          <>
            <label className="field">
              {hi ? 'व्यवसाय किस तरह बना है?' : 'How is your business set up?'}
              <select value={draft.legal} onChange={(e) => change({ legal: e.target.value })}>
                {(
                  [
                    'unknown',
                    'unregistered',
                    'sole_proprietor',
                    'partnership',
                    'company',
                    'other',
                  ] as const
                ).map((value) => (
                  <option key={value} value={value}>
                    {hi
                      ? {
                          unknown: 'अभी पता नहीं / छोड़ें',
                          unregistered: 'अपंजीकृत / अनौपचारिक',
                          sole_proprietor: 'एकल स्वामित्व',
                          partnership: 'साझेदारी',
                          company: 'कंपनी',
                          other: 'अन्य',
                        }[value]
                      : {
                          unknown: 'Not sure yet / skip',
                          unregistered: 'Unregistered or informal',
                          sole_proprietor: 'Sole proprietor',
                          partnership: 'Partnership',
                          company: 'Company',
                          other: 'Another structure',
                        }[value]}
                  </option>
                ))}
              </select>
            </label>
            {stage === 1 && (
              <>
                <button
                  type="button"
                  className="text-button"
                  onClick={() => setOptional(!optional)}
                >
                  {optional
                    ? hi
                      ? 'वैकल्पिक जानकारी छिपाएँ'
                      : 'Hide optional details'
                    : hi
                      ? 'ज़रूरत हो तो स्थान या पंजीकरण जानकारी जोड़ें'
                      : 'Add location or registration details if useful'}
                </button>
                {optional && (
                  <div className="business-optional">
                    {(
                      [
                        ['udyam', 'Udyam registered', 'उद्यम पंजीकृत', ['true', 'false']],
                        [
                          'size',
                          'Udyam classification',
                          'उद्यम वर्ग',
                          ['micro', 'small', 'medium', 'other'],
                        ],
                        [
                          'sector',
                          'Business sector',
                          'व्यवसाय क्षेत्र',
                          ['manufacturing', 'services', 'trading', 'other'],
                        ],
                        [
                          'similar',
                          'Received similar government assistance',
                          'समान सरकारी सहायता प्राप्त',
                          ['true', 'false'],
                        ],
                      ] as const
                    ).map(([key, en, h, values]) => (
                      <label className="field" key={key}>
                        {hi ? h : en}
                        <select
                          value={draft[key]}
                          onChange={(e) => change({ [key]: e.target.value })}
                        >
                          <option value="">{hi ? 'अज्ञात / छोड़ें' : 'Unknown / skip'}</option>
                          {values.map((v) => (
                            <option key={v} value={v}>
                              {v === 'true'
                                ? hi
                                  ? 'हाँ'
                                  : 'Yes'
                                : v === 'false'
                                  ? hi
                                    ? 'नहीं'
                                    : 'No'
                                  : v}
                            </option>
                          ))}
                        </select>
                      </label>
                    ))}

                    <label className="field">
                      {hi
                        ? 'व्यवसाय क्या करता है? (वैकल्पिक)'
                        : 'What does your business do? (optional)'}
                      <textarea
                        value={draft.description}
                        maxLength={1000}
                        onChange={(e) => change({ description: e.target.value })}
                      />
                    </label>
                    <label className="field">
                      {hi ? 'क्या व्यवसाय पंजीकृत है?' : 'Is the business registered?'}
                      <select
                        value={draft.registered}
                        onChange={(e) => change({ registered: e.target.value })}
                      >
                        <option value="">{hi ? 'अभी पता नहीं' : 'Not sure yet'}</option>
                        <option value="true">{t.yes}</option>
                        <option value="false">{t.no}</option>
                      </select>
                    </label>
                    <div className="form-grid">
                      <label className="field">
                        {hi ? 'संचालन का राज्य' : 'Operating state'}
                        <input
                          maxLength={100}
                          value={draft.state}
                          onChange={(e) => change({ state: e.target.value })}
                        />
                      </label>
                      <label className="field">
                        {hi ? 'संचालन का जिला' : 'Operating district'}
                        <input
                          maxLength={100}
                          value={draft.district}
                          onChange={(e) => change({ district: e.target.value })}
                        />
                      </label>
                    </div>
                    <p>
                      {hi
                        ? 'संचालन का स्थान पंजीकरण के स्थान से अलग हो सकता है। कानूनी संरचना से पंजीकरण या वर्तमान काम का अनुमान नहीं लगाया जाएगा।'
                        : 'Operating location can differ from registration location. Legal structure does not automatically answer registration or current activity.'}
                    </p>
                    <div className="form-grid">
                      <label className="field">
                        {hi
                          ? 'पंजीकरण का राज्य (यदि लागू हो)'
                          : 'Registration state (if applicable)'}
                        <input
                          value={draft.registrationState}
                          maxLength={100}
                          onChange={(e) => change({ registrationState: e.target.value })}
                        />
                      </label>
                      <label className="field">
                        {hi
                          ? 'पंजीकरण का जिला (यदि लागू हो)'
                          : 'Registration district (if applicable)'}
                        <input
                          value={draft.registrationDistrict}
                          maxLength={100}
                          onChange={(e) => change({ registrationDistrict: e.target.value })}
                        />
                      </label>
                      <label className="field">
                        {hi ? 'व्यवसाय अभी किस स्थिति में है?' : 'What is the business doing now?'}
                        <select
                          value={draft.activity}
                          onChange={(e) => change({ activity: e.target.value })}
                        >
                          <option value="">
                            {hi ? 'अभी पता नहीं / छोड़ें' : 'Not sure yet / skip'}
                          </option>
                          <option value="active">{hi ? 'काम चल रहा है' : 'Operating'}</option>
                          <option value="inactive">
                            {hi ? 'अभी काम बंद है' : 'Not operating now'}
                          </option>
                          <option value="prelaunch">
                            {hi ? 'शुरू करने की तैयारी' : 'Preparing to start'}
                          </option>
                        </select>
                      </label>
                    </div>
                    <button
                      type="button"
                      className="text-button"
                      onClick={() => setFinancial(!financial)}
                    >
                      {financial
                        ? hi
                          ? 'टर्नओवर सवाल छिपाएँ'
                          : 'Hide turnover question'
                        : hi
                          ? 'किसी अवसर को टर्नओवर चाहिए?'
                          : 'Does an opportunity need your turnover?'}
                    </button>
                    {financial && (
                      <div className="notice">
                        <label className="field">
                          {hi ? 'वार्षिक टर्नओवर (₹)' : 'Annual turnover (₹)'}
                          <input
                            type="number"
                            min={0}
                            value={draft.turnover}
                            onChange={(e) => change({ turnover: e.target.value })}
                          />
                        </label>
                        <label className="field">
                          {hi ? 'किस वर्ष या अवधि का?' : 'Which year or period?'}
                          <input
                            value={draft.period}
                            onChange={(e) => change({ period: e.target.value })}
                          />
                        </label>
                        <label className="field">
                          {hi ? 'कौनसी आय शामिल है?' : 'Which business receipts are included?'}
                          <input
                            value={draft.definition}
                            onChange={(e) => change({ definition: e.target.value })}
                          />
                        </label>
                        <p>
                          {hi
                            ? 'अवधि या शामिल आय अस्पष्ट होने पर आकलन अज्ञात रहेगा।'
                            : 'Assessment stays unknown if its period or included income is unclear.'}
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </>
            )}
          </>
        )}
      </fieldset>
      <div className="form-actions">
        {kind === 'business' && !current && stage === 1 && (
          <button
            type="button"
            className="button secondary"
            onClick={() => setStage(0)}
            disabled={mutation.isPending}
          >
            {hi ? 'पीछे' : 'Back'}
          </button>
        )}
        <button className="button" disabled={!dirty || !draft.name.trim() || mutation.isPending}>
          {mutation.isPending
            ? t.saving
            : kind === 'business' && !current && stage === 0
              ? hi
                ? 'आगे बढ़ें'
                : 'Continue'
              : current
                ? hi
                  ? 'बदलाव सहेजें'
                  : 'Save changes'
                : kind === 'household'
                  ? hi
                    ? 'परिवार बनाएं'
                    : 'Create household'
                  : hi
                    ? 'व्यवसाय बनाएं'
                    : 'Create business'}
        </button>
        {current && (
          <button
            type="button"
            className="button secondary"
            disabled={mutation.isPending}
            onClick={() => {
              if (guard.confirmLeave()) onCancel();
            }}
          >
            {hi ? 'रद्द करें' : 'Cancel'}
          </button>
        )}
      </div>
      {mutation.isError && (
        <div role="alert">
          <p>{mutation.error.message}</p>
          <p>
            {hi
              ? 'बदलाव सहेजे नहीं गए; आपके उत्तर यहीं हैं।'
              : 'Changes were not saved; your answers are still here.'}
          </p>
          {mutation.error instanceof RequestError &&
            mutation.error.code === 'workspace_conflict' && (
              <>
                <p>
                  {hi
                    ? 'दूसरे टैब या सत्र में नई जानकारी सहेजी गई है। यहाँ के अनसहेजे उत्तर बने हुए हैं।'
                    : 'Another tab or session saved newer information. Your unsaved answers remain here.'}
                </p>
                <button
                  type="button"
                  className="button secondary"
                  onClick={() => {
                    if (guard.confirmLeave()) {
                      guard.markSaved();
                      window.location.reload();
                    }
                  }}
                >
                  {hi ? 'सहेजी जानकारी पुनः लोड करें' : 'Reload saved workspace'}
                </button>
              </>
            )}
        </div>
      )}
    </form>
  );
}
function DependentForm({
  household,
  onSaved,
}: {
  household: string;
  onSaved: () => Promise<unknown>;
}) {
  const hi = useLanguage() === 'hi';
  const [name, setName] = useState(''),
    [age, setAge] = useState(''),
    [consent, setConsent] = useState(false);
  useDirtyForm(Boolean(name || age || consent));
  const mutation = useMutation({
    mutationFn: async () => {
      const { data, error } = await api.POST('/v1/households/{identifier}/dependents', {
        params: { path: { identifier: household } },
        body: {
          display_name: name.trim(),
          facts: age ? [{ key: 'age', value: Number(age) }] : [],
          guardian_responsibility_confirmed: true,
          relationship: 'legal_guardian',
        },
      });
      return data ?? fail(error);
    },
    onSuccess: () => {
      setName('');
      setAge('');
      setConsent(false);
      void onSaved();
    },
  });
  return (
    <form
      className="panel dependent-onboarding"
      onSubmit={(e) => {
        e.preventDefault();
        if (consent && !mutation.isPending) mutation.mutate();
      }}
    >
      <h2>{hi ? 'अपने प्रबंधन में आश्रित जोड़ें' : 'Add a dependent you manage'}</h2>
      <p>
        {hi
          ? 'इस व्यक्ति का अपना प्रोफ़ाइल और दस्तावेज़ होंगे। वयस्कों को जोड़ने के निमंत्रण अभी उपलब्ध नहीं हैं।'
          : 'This person will have their own profile and documents. Invitations for adults are not available yet.'}
      </p>
      <fieldset disabled={mutation.isPending}>
        <label className="field">
          {hi ? 'आश्रित का नाम या उपनाम' : 'Dependent’s name or nickname'}
          <input required maxLength={80} value={name} onChange={(e) => setName(e.target.value)} />
        </label>
        <label className="field">
          {hi ? 'उम्र (वैकल्पिक)' : 'Age (optional)'}
          <input
            type="number"
            min={0}
            max={130}
            step={1}
            value={age}
            onChange={(e) => setAge(e.target.value)}
          />
        </label>
        <label className="check-label">
          <input
            type="checkbox"
            required
            checked={consent}
            onChange={(e) => setConsent(e.target.checked)}
          />
          {hi
            ? 'मैं इस आश्रित का कानूनी अभिभावक हूँ और इसकी जानकारी का प्रबंधन अधिकृत है।'
            : 'I am the legal guardian authorized to manage this dependent’s information.'}
        </label>
      </fieldset>
      <button className="button" disabled={!name.trim() || !consent || mutation.isPending}>
        {mutation.isPending
          ? hi
            ? 'जोड़ा जा रहा है…'
            : 'Adding…'
          : hi
            ? 'आश्रित जोड़ें'
            : 'Add dependent'}
      </button>
      {mutation.isError && <p role="alert">{mutation.error.message}</p>}
    </form>
  );
}
export type { Workspace };
