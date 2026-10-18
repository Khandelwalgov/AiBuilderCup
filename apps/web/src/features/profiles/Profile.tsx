import { useEffect, useRef, useState } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useDirtyForm } from '../../app/dirty-forms';
import { useSubject, ContextLink as Link } from '../../app/subject-context';
import { useLanguage, useStrings } from '../../app/App';
import { api, fail, RequestError } from '../../lib/api/client';
import { displayDate } from '../../i18n/format';
import { DocumentSummary } from '../documents/Documents';
import {
  questions,
  valuesOf,
  conflicts,
  semanticIssues,
  answered,
  answerLabel,
  documentKeys,
  incomeKeys,
  type Fact,
  type Goal,
  type Category,
  type Question,
} from './questions';
import type { components } from '../../lib/api/schema';
type View = components['schemas']['ProfileView'];
type Draft = { name: string; facts: Fact[] };
type SourceRule = components['schemas']['Rule-Output'];
function incomeClause(
  rule: SourceRule,
  key: string,
): components['schemas']['Condition'] | undefined {
  if (rule.op === 'condition') return rule.condition?.fact === key ? rule.condition : undefined;
  return rule.children?.map((child) => incomeClause(child, key)).find(Boolean);
}
const today = () => new Date().toLocaleDateString('en-CA');
const yesterday = () => {
  const date = new Date();
  date.setDate(date.getDate() - 1);
  return date.toLocaleDateString('en-CA');
};
const signature = (d: Draft) =>
  JSON.stringify({ name: d.name, facts: [...d.facts].sort((a, b) => a.key.localeCompare(b.key)) });
function editable(data: View | null): Draft {
  return {
    name: data?.display_name ?? '',
    facts: (data?.facts ?? [])
      .filter((f) => ['user_supplied', 'unknown'].includes(f.origin))
      .map((f) => ({
        key: f.key as Fact['key'],
        value: f.value,
        valid_from: f.valid_from ?? null,
        valid_until: f.valid_until ?? null,
        income_period: (f.context?.income_period as string) ?? null,
        income_definition: (f.context?.income_definition as string) ?? null,
      })),
  };
}
export function Profile() {
  const [routeParams] = useSearchParams();
  const c = useSubject(),
    hi = useLanguage() === 'hi';
  if (c.pending)
    return (
      <div className="page" role="status">
        {hi ? 'लोड हो रहा है…' : 'Loading…'}
      </div>
    );
  if (!c.available || c.subject.kind !== 'person')
    return (
      <div className="page panel">
        <h1>{hi ? 'व्यक्तिगत जानकारी' : 'Person profile'}</h1>
        <p>{hi ? 'किसी व्यक्ति को चुनें।' : 'Select a person to view their profile.'}</p>
        <Link to={c.subject.kind === 'business' ? '/businesses' : '/family'}>
          {hi ? 'कार्यस्थल खोलें' : 'Open workspace'}
        </Link>
      </div>
    );
  return (
    <PersonProfile
      key={`${c.key}:${routeParams.get('field') ?? ''}:${routeParams.get('section') ?? ''}`}
    />
  );
}
function PersonProfile() {
  const hi = useLanguage() === 'hi',
    t = useStrings(),
    c = useSubject(),
    cache = useQueryClient();
  const { personId: routeId } = useParams();
  const personId = routeId ?? c.subject.id ?? undefined;
  const [params] = useSearchParams();
  const requested = questions.find((q) => q.key === params.get('field'));
  const routeSection = ['basics', 'education', 'employment', 'income', 'support'].includes(
    params.get('section') ?? '',
  )
    ? (params.get('section') as Category)
    : null;
  const researchId = params.get('research_listing');
  const researchSource = useQuery({
    queryKey: ['profile-research-source', researchId],
    enabled: !!researchId,
    retry: false,
    queryFn: async () => {
      const { data, error } = await api.GET('/v1/research-opportunities/{identifier}', {
        params: { path: { identifier: researchId! } },
      });
      return data ?? fail(error);
    },
  });
  const researchCondition = researchSource.data?.provisional_conditions.find(
    (c) => c.semantic === params.get('criterion') && c.evidence_available,
  );
  const citedIncome =
    researchCondition && requested && incomeKeys.has(requested.key)
      ? incomeClause(researchCondition.rule, requested.key)
      : undefined;
  const opportunityId = params.get('opportunity');
  const source = useQuery({
    queryKey: ['profile-opportunity', opportunityId, params.get('development')],
    enabled: !!opportunityId,
    retry: false,
    queryFn: async () => {
      const { data, error } = await api.GET('/v1/opportunities/{identifier}', {
        params: {
          path: { identifier: opportunityId! },
          query: { development: params.get('development') === 'true' },
        },
      });
      return data ?? fail(error);
    },
  });
  const mentions = (rule: unknown, key: string | undefined, depth = 0): boolean => {
    if (!key || depth > 8 || !rule || typeof rule !== 'object') return false;
    const node = rule as Record<string, unknown>;
    const condition = node.condition as Record<string, unknown> | null;
    if (node.op === 'condition')
      return (
        !!condition &&
        ['eq', 'gte', 'lte', 'in'].includes(String(condition.op)) &&
        (condition.fact === key ||
          (key === 'student_status' &&
            [
              'current_education_level',
              'enrollment_mode',
              'school_recognized_or_government',
            ].includes(String(condition.fact))))
      );
    return (
      ['all', 'any'].includes(String(node.op)) &&
      Array.isArray(node.children) &&
      node.children.slice(0, 100).some((child) => mentions(child, key, depth + 1))
    );
  };
  const sourceRequirement = source.data?.requirements.find(
    (r) => r.id === params.get('requirement') && mentions(r.rule, requested?.key),
  );
  const requestedDocument = documentKeys.has(params.get('field') as Fact['key']);
  const [draft, setDraft] = useState<Draft | null>(null),
    [editing, setEditing] = useState(false),
    [stage, setStage] = useState(0),
    [goal, setGoal] = useState<Goal>('general'),
    [section, setSection] = useState<Category | null>(null);
  const baseline = useRef(''),
    revision = useRef<string | undefined>(undefined),
    initialized = useRef(false);
  const sectionNames: Record<Category, [string, string]> = {
    basics: ['about you', 'मूल जानकारी'],
    education: ['education', 'शिक्षा'],
    employment: ['work', 'कामकाज'],
    income: ['income', 'आय'],
    support: ['support', 'सहायता'],
  };
  const dirty = draft !== null && signature(draft) !== baseline.current;
  const guard = useDirtyForm(dirty);
  const query = useQuery({
    queryKey: ['personal-profile', personId],
    retry: false,
    queryFn: async () => {
      const { data, error } = personId
        ? await api.GET('/v1/people/{identifier}', { params: { path: { identifier: personId } } })
        : await api.GET('/v1/profile/me');
      if (error?.error.code === 'profile_not_found') return null;
      return data ?? fail(error);
    },
  });
  useEffect(() => {
    if (query.isPending || query.isError || dirty) return;
    const next = editable(query.data ?? null);
    baseline.current = signature(next);
    revision.current = query.data?.revision || undefined;
    setDraft(next);
    if (!initialized.current) {
      setEditing(!query.data || !!requested || !!routeSection);
      setStage(requested || routeSection ? 1 : 0);
      setSection(requested?.category ?? routeSection);
      if (
        next.facts.some((f) =>
          [
            'education_level',
            'current_education_level',
            'highest_completed_education',
            'student_status',
          ].includes(f.key),
        )
      )
        setGoal('education');
      initialized.current = true;
    }
  }, [query.data, query.isPending, query.isError, dirty, requested, routeSection]);
  useEffect(() => {
    if (requested && initialized.current) {
      setEditing(true);
      setSection(requested.category);
      setStage(1);
    }
  }, [requested]);
  const submitted = useRef<Draft | null>(null);
  const save = useMutation({
    mutationFn: async () => {
      const payload = {
        display_name: submitted.current!.name.trim(),
        facts: submitted.current!.facts,
        ...(revision.current ? { expected_revision: revision.current } : {}),
      };
      if (personId) {
        const { data, error } = await api.PUT('/v1/people/{identifier}', {
          params: { path: { identifier: personId } },
          body: payload,
        });
        if (!data) return fail(error);
        return {
          id: data.id,
          display_name: data.name,
          facts: data.facts,
          revision: data.revision,
        } as View;
      }
      const { data, error } = await api.PUT('/v1/profile/me', { body: payload });
      return data ?? fail(error);
    },
    onSuccess: (data) => {
      const next = editable(data);
      baseline.current = signature(next);
      revision.current = data.revision || undefined;
      setDraft(next);
      setEditing(false);
      setSection(null);
      cache.setQueryData(['personal-profile', personId], data);
      for (const key of [
        'workspaces',
        'dashboard-summary',
        'plan',
        'hybrid-search',
        'scenario-base',
        'research-guidance',
      ])
        void cache.invalidateQueries({ queryKey: [key] });
    },
  });
  if (query.isError)
    return (
      <div className="page panel" role="alert">
        <p>{query.error.message}</p>
        <button className="button" onClick={() => void query.refetch()}>
          {t.retry}
        </button>
      </div>
    );
  if (query.isPending || !draft)
    return (
      <div className="page" role="status">
        {t.loading}
      </div>
    );
  const values = valuesOf(draft.facts),
    invalid = conflicts(draft.facts, editable(query.data ?? null).facts),
    isNew = !query.data;
  function update(key: Fact['key'], value: Fact['value'], extra: Partial<Fact> = {}) {
    let next = [...draft!.facts];
    const clearing: Fact['key'][] =
      key === 'student_status' && value === false
        ? ['current_education_level', 'enrollment_mode', 'school_recognized_or_government']
        : key === 'current_education_level' &&
            ['undergraduate', 'postgraduate', 'other'].includes(String(value))
          ? ['school_recognized_or_government']
          : [];
    if (next.some((f) => clearing.includes(f.key) && valuesOf(next)[f.key] != null)) {
      if (
        !window.confirm(
          hi
            ? 'सहेजे गए पढ़ाई के उत्तर कल तक के ऐतिहासिक उत्तर रहेंगे। नए अनसहेजे पढ़ाई के उत्तर खाली होंगे। बाकी उत्तर बने रहेंगे। जारी रखें? पहले देखने के लिए रद्द करें।'
            : 'Saved current-study answers will be kept as historical answers ending yesterday. New unsaved study answers will be cleared. Other answers will stay. Continue? Cancel to review first.',
        )
      )
        return;
      next = next.flatMap((f) => {
        if (!clearing.includes(f.key) || valuesOf(next)[f.key] == null) return [f];
        return query.data?.facts.some((saved) => saved.key === f.key)
          ? [{ ...f, valid_until: yesterday() }]
          : [];
      });
    }
    const old = next.find((f) => f.key === key);
    if (old?.valid_until && old.valid_until < today() && !Object.keys(extra).length) {
      if (
        !window.confirm(
          hi
            ? 'पुराने उत्तर का इतिहास बना रहेगा। इसे आज से वर्तमान उत्तर बनाएँ?'
            : 'The earlier answer will remain in history. Use this new answer from today?',
        )
      )
        return;
      extra = { valid_from: today(), valid_until: null };
    }
    next = old
      ? next.map((f) => (f.key === key ? { ...f, value, ...extra } : f))
      : [
          ...next,
          {
            key,
            value,
            valid_from: null,
            valid_until: null,
            income_period: null,
            income_definition: null,
            ...extra,
          },
        ];
    setDraft({ ...draft!, facts: next });
    save.reset();
  }
  function begin(category: Category) {
    setEditing(true);
    setSection(category);
    setStage(1);
    save.reset();
  }
  function discard() {
    if (!guard.confirmLeave()) return;
    const next = editable(query.data ?? null);
    baseline.current = signature(next);
    setDraft(next);
    setEditing(false);
    setSection(null);
    save.reset();
  }
  function renderQuestion(q: Question) {
    const f = draft!.facts.find((f) => f.key === q.key),
      value = values[q.key];
    if (q.when && !q.when(values)) return null;
    const label = q.label[hi ? 1 : 0];
    return (
      <div className="guided-question" id={`fact-${q.key}`} key={q.key}>
        {semanticIssues(draft!.facts, editable(query.data ?? null).facts)
          .filter((issue) => issue.fields.includes(q.key) && issue.severity === 'error')
          .map((issue) => (
            <p role="alert" key={issue.code}>
              {issue.message[hi ? 1 : 0]}
            </p>
          ))}
        <label className="field">
          <span>
            {label} <small>{hi ? 'वैकल्पिक' : 'Optional'}</small>
          </span>
          {q.type === 'boolean' || q.type === 'select' ? (
            <select
              aria-label={label}
              disabled={save.isPending}
              aria-invalid={
                semanticIssues(draft!.facts, editable(query.data ?? null).facts).some(
                  (issue) => issue.severity === 'error' && issue.fields.includes(q.key),
                ) ||
                (save.error instanceof RequestError &&
                  save.error.issues.some((issue) => issue.fields?.includes(q.key)))
              }
              value={
                value == null
                  ? ''
                  : q.key === 'nationality'
                    ? answerLabel({ key: q.key, value }, hi)
                    : String(value)
              }
              onChange={(e) =>
                update(
                  q.key,
                  e.target.value === ''
                    ? null
                    : q.type === 'boolean'
                      ? e.target.value === 'true'
                      : e.target.value,
                )
              }
            >
              <option value="">{hi ? 'अभी पता नहीं / छोड़ें' : 'Not sure yet / skip'}</option>
              {q.type === 'boolean' ? (
                <>
                  <option value="true">{t.yes}</option>
                  <option value="false">{t.no}</option>
                </>
              ) : (
                q.choices?.map((choice) => (
                  <option key={choice[0]} value={choice[0]}>
                    {choice[hi ? 2 : 1]}
                  </option>
                ))
              )}
              {q.type === 'select' && value != null && !q.choices?.some((x) => x[0] === value) && (
                <option value={String(value)}>{String(value)}</option>
              )}
            </select>
          ) : (
            <input
              aria-label={label}
              disabled={save.isPending}
              type={q.type === 'number' ? 'number' : 'text'}
              min={q.min}
              max={q.max}
              step={q.key === 'age' ? 1 : 'any'}
              maxLength={100}
              value={
                value == null
                  ? ''
                  : q.key === 'nationality'
                    ? answerLabel({ key: q.key, value }, hi)
                    : String(value)
              }
              onChange={(e) =>
                update(
                  q.key,
                  e.target.value === ''
                    ? null
                    : q.type === 'number'
                      ? Number(e.target.value)
                      : e.target.value,
                )
              }
            />
          )}
        </label>
        {q.help && <p className="muted">{q.help[hi ? 1 : 0]}</p>}
        {(f?.valid_from || f?.valid_until) && (
          <details>
            <summary>
              {hi ? 'इस उत्तर की लागू अवधि जाँचें' : 'Check when this answer applies'}
            </summary>
            <p>
              {hi
                ? 'पहले सहेजी अवधि इस उत्तर के साथ रहेगी। ज़रूरत हो तो स्पष्ट रूप से बदलें।'
                : 'The previously saved dates stay with this answer. Change them explicitly if needed.'}
            </p>
            <label className="field">
              {hi ? 'कब से लागू है?' : 'Applies from'}
              <input
                type="date"
                disabled={save.isPending}
                value={f.valid_from ?? ''}
                onChange={(e) =>
                  update(q.key, f?.value ?? null, { valid_from: e.target.value || null })
                }
              />
            </label>
            <label className="field">
              {hi ? 'कब तक लागू है?' : 'Applies until'}
              <input
                type="date"
                disabled={save.isPending}
                value={f.valid_until ?? ''}
                onChange={(e) =>
                  update(q.key, f?.value ?? null, { valid_until: e.target.value || null })
                }
              />
            </label>
          </details>
        )}
        {incomeKeys.has(q.key) && value != null && (
          <div className="notice">
            <p>
              {hi
                ? 'इस आय का उपयोग तभी होगा जब अवधि और शामिल आय अवसर की शर्त से मेल खाएँ।'
                : 'This amount can only be assessed when its period and included income match the opportunity.'}
            </p>
            {citedIncome?.income_definition && (
              <div>
                <p>
                  {hi ? 'स्रोत का आय आधार' : 'Cited income basis'}: {citedIncome.income_definition}
                </p>
                <button
                  type="button"
                  disabled={save.isPending}
                  onClick={() => {
                    const admission = values.education_admission_year;
                    const period =
                      citedIncome.income_period === 'previous_admission_financial_year'
                        ? typeof admission === 'string' && /^20[0-9]{2}-[0-9]{2}$/.test(admission)
                          ? `${Number(admission.slice(0, 4)) - 1}-${admission.slice(2, 4)}`
                          : null
                        : citedIncome.income_period;
                    update(q.key, value, {
                      income_definition: citedIncome.income_definition,
                      income_period: period,
                    });
                  }}
                >
                  {hi ? 'स्रोत का आधार ड्राफ्ट में इस्तेमाल करें' : 'Use cited basis in this draft'}
                </button>
                <p>
                  {hi
                    ? 'राशि अपनी वास्तविक जानकारी से दें; अज्ञात प्रवेश वर्ष से अवधि नहीं मानी जाएगी। सहेजने से पहले जाँचें।'
                    : 'Supply your actual amount. An unknown admission year leaves the period blank. Review before saving.'}
                </p>
              </div>
            )}
            <label className="field">
              {hi ? 'किस वर्ष या अवधि की आय?' : 'Which year or period does this cover?'}
              <input
                disabled={save.isPending}
                value={f?.income_period ?? ''}
                onChange={(e) =>
                  update(q.key, value ?? null, { income_period: e.target.value || null })
                }
              />
            </label>
            <label className="field">
              {hi
                ? 'किसकी आय और कौनसे स्रोत शामिल हैं?'
                : 'Whose income and which sources are included?'}
              <input
                disabled={save.isPending}
                value={f?.income_definition ?? ''}
                onChange={(e) =>
                  update(q.key, value ?? null, { income_definition: e.target.value || null })
                }
              />
            </label>
            <p>
              {hi
                ? 'यदि पता नहीं, आकलन में यह अज्ञात रहेगा।'
                : 'If unknown, the income condition remains unknown.'}
            </p>
          </div>
        )}
      </div>
    );
  }
  const visible = questions.filter((q) =>
    requested
      ? q.key === requested.key
      : section
        ? q.category === section
        : isNew
          ? ['age', 'domicile_state'].includes(q.key) || q.goals?.includes(goal)
          : false,
  );
  return (
    <div className="page narrow profile-journey">
      <div className="page-heading">
        <span className="eyebrow">{c.label}</span>
        <h1>{hi ? 'आपकी जानकारी' : 'Your profile'}</h1>
        <p>
          {hi
            ? 'छोटी शुरुआत करें। अवसर के अनुसार बाकी जानकारी बाद में जोड़ें।'
            : 'Start small. Add other information when an opportunity needs it.'}
        </p>
      </div>
      {sourceRequirement && (
        <section className="panel">
          <h2>{hi ? 'यह जानकारी क्यों चाहिए?' : 'Why are we asking?'}</h2>
          <p>
            {source.data?.title} · {sourceRequirement.description}
          </p>
          {sourceRequirement.citations.map((citation, i) => (
            <blockquote key={i}>
              {citation.passage}
              <a href={citation.source_url} target="_blank" rel="noreferrer">
                {hi ? 'मूल शर्त' : 'Original condition'} · {citation.page}
              </a>
            </blockquote>
          ))}
        </section>
      )}
      {researchCondition && (
        <section className="panel">
          <h2>{hi ? 'स्रोत-आधारित अस्थायी तुलना' : 'Source-backed provisional comparison'}</h2>
          <p>{researchCondition.title}</p>
          <blockquote>{researchCondition.passage}</blockquote>
          <Link
            to={`/government-sources?source=${researchCondition.snapshot_id}&page=${researchCondition.page}`}
          >
            {hi ? 'स्रोत पृष्ठ पढ़ें' : 'Read captured source page'} · {researchCondition.page}
          </Link>
          <p>
            {hi
              ? 'उत्तर देना प्रमाणपत्र सत्यापन या आधिकारिक पात्रता नहीं है।'
              : 'Supplying an answer does not verify a certificate or establish official eligibility.'}
          </p>
        </section>
      )}
      {requestedDocument && (
        <div className="notice">
          <p>
            {hi
              ? 'प्रमाणपत्र का प्रबंधन दस्तावेज़ों में करें। अपलोड से सत्यापन नहीं होता।'
              : 'Manage certificates in My Documents. Uploading does not verify them.'}
          </p>
          <Link className="button" to="/documents">
            {hi ? 'मेरे दस्तावेज़' : 'My Documents'}
          </Link>
        </div>
      )}
      {semanticIssues(draft.facts, editable(query.data ?? null).facts).map((issue) => (
        <section
          className="panel semantic-issue"
          key={issue.code}
          role={issue.severity === 'error' ? 'alert' : 'status'}
        >
          <h2>{hi ? 'इन उत्तरों की अवधि स्पष्ट करें' : 'Clarify when these answers apply'}</h2>
          <p>{issue.message[hi ? 1 : 0]}</p>
          <dl>
            {issue.fields.map((key) => {
              const fact = draft.facts.find((f) => f.key === key);
              return (
                fact && (
                  <div key={key}>
                    <dt>
                      {questions.find((q) => q.key === key)?.label[hi ? 1 : 0] ??
                        (hi
                          ? 'पहले सहेजा गया शिक्षा उत्तर (अर्थ अस्पष्ट)'
                          : 'Earlier education answer (meaning unclear)')}
                    </dt>
                    <dd>
                      {answerLabel(fact, hi)} ·{' '}
                      {hi
                        ? issue.code === 'legacy_education_ambiguous'
                          ? 'अर्थ और लागू अवधि स्पष्ट करना बाकी है'
                          : 'उसी वर्तमान अवधि के उत्तर'
                        : issue.code === 'legacy_education_ambiguous'
                          ? 'Meaning and applicable period need clarification'
                          : `Applies ${fact.valid_from ?? '…'} – ${fact.valid_until ?? 'no end date'}; active now`}
                    </dd>
                  </div>
                )
              );
            })}
          </dl>
          {issue.fields
            .filter((key) =>
              [
                'education_level',
                'current_education_level',
                'enrollment_mode',
                'school_recognized_or_government',
              ].includes(key),
            )
            .map((key) => (
              <button
                type="button"
                className="button secondary"
                key={key}
                onClick={() => {
                  if (
                    !window.confirm(
                      hi
                        ? 'यह उत्तर आज से वर्तमान नहीं रहेगा। मान और इतिहास बने रहेंगे। जारी रखें?'
                        : 'Mark this answer as no longer current from today? Its value and history will be preserved.',
                    )
                  )
                    return;
                  setDraft({
                    ...draft,
                    facts: draft.facts.map((f) =>
                      f.key === key ? { ...f, valid_until: yesterday() } : f,
                    ),
                  });
                  setEditing(true);
                  setSection('education');
                  setStage(1);
                  save.reset();
                }}
              >
                {hi ? 'पुराना उत्तर ऐतिहासिक रखें: ' : 'Keep previous answer as historical: '}
                {questions.find((q) => q.key === key)?.label[hi ? 1 : 0] ??
                  (hi
                    ? 'पहले सहेजा गया शिक्षा उत्तर (अर्थ अस्पष्ट)'
                    : 'Earlier education answer (meaning unclear)')}
              </button>
            ))}
          {issue.code === 'legacy_education_ambiguous' && (
            <button className="text-button" onClick={() => begin('education')}>
              {hi
                ? 'वर्तमान और पूरी की गई शिक्षा अलग बताएँ'
                : 'Clarify current study and completed education separately'}
            </button>
          )}
        </section>
      ))}
      {!editing && !isNew ? (
        <>
          <section className="panel profile-summary">
            <div className="page-heading">
              <h2>{draft.name}</h2>
              <span role="status">{hi ? 'सहेजा गया और अद्यतन' : 'Saved and up to date'}</span>
            </div>
            <p>
              {displayDate(
                query.data?.last_saved_at,
                hi,
                hi ? 'आपकी सहेजी जानकारी' : 'Your saved information',
              )}
            </p>
            <p>
              {hi
                ? 'उत्तर आपके द्वारा दिए गए हैं। प्रमाणपत्रों का सत्यापन अलग है।'
                : 'These are your own answers. Document verification is separate.'}
            </p>
            {(['basics', 'education', 'employment', 'income', 'support'] as Category[]).map(
              (category) => {
                const entries = answered(draft.facts).filter(
                  (f) =>
                    (!f.valid_from || f.valid_from <= today()) &&
                    (!f.valid_until || f.valid_until >= today()) &&
                    questions.find((q) => q.key === f.key)?.category === category,
                );
                if (!entries.length && ['income', 'support'].includes(category)) return null;
                return (
                  <section className="profile-section" key={category}>
                    <h3>
                      {hi
                        ? {
                            basics: 'मूल जानकारी',
                            education: 'शिक्षा',
                            employment: 'कामकाज',
                            income: 'संबंधित आय',
                            support: 'सहायता',
                          }[category]
                        : {
                            basics: 'About you',
                            education: 'Education',
                            employment: 'Work',
                            income: 'Relevant income',
                            support: 'Support',
                          }[category]}
                    </h3>
                    <dl>
                      {entries.map((f) => (
                        <div key={f.key}>
                          <dt>{questions.find((q) => q.key === f.key)?.label[hi ? 1 : 0]}</dt>
                          <dd>
                            {answerLabel(f, hi)}
                            {f.key === 'age' && (
                              <small>
                                {hi ? 'उम्र दर्ज की गई: ' : 'Age recorded on: '}
                                {query.data?.facts.find((row) => row.key === 'age')?.context
                                  ?.recorded_at
                                  ? String(
                                      query.data.facts.find((row) => row.key === 'age')?.context
                                        ?.recorded_at,
                                    ).slice(0, 10)
                                  : hi
                                    ? 'तारीख़ उपलब्ध नहीं; सही होने की पुष्टि करें'
                                    : 'date unavailable; confirm it is still accurate'}
                                {hi
                                  ? '। जन्मतिथि से अपने आप नहीं बढ़ती।'
                                  : '. It does not advance automatically from a birth date.'}
                              </small>
                            )}
                            {(f.valid_from || f.valid_until) && (
                              <small>
                                {' '}
                                · {hi ? 'लागू अवधि' : 'Applies'}: {f.valid_from ?? '…'} –{' '}
                                {f.valid_until ?? '…'}
                              </small>
                            )}
                          </dd>
                        </div>
                      ))}
                    </dl>
                    <button className="text-button" onClick={() => begin(category)}>
                      {hi
                        ? `${sectionNames[category][1]} संपादित करें`
                        : `Edit ${sectionNames[category][0]}`}
                    </button>
                  </section>
                );
              },
            )}
            <button
              className="button secondary"
              onClick={() =>
                begin(
                  goal === 'education'
                    ? 'education'
                    : goal === 'employment'
                      ? 'employment'
                      : 'basics',
                )
              }
            >
              {hi ? 'जानकारी जोड़ें' : 'Add relevant information'}
            </button>
          </section>
          {draft.facts.some(
            (f) =>
              f.key === 'education_level' ||
              (f.valid_until && f.valid_until < today()) ||
              (f.valid_from && f.valid_from > today()),
          ) && (
            <section className="panel">
              <h2>{hi ? 'पहले के उत्तर और उनकी अवधि' : 'Earlier answers and when they applied'}</h2>
              {draft.facts
                .filter(
                  (f) =>
                    f.key === 'education_level' ||
                    (f.valid_until && f.valid_until < today()) ||
                    (f.valid_from && f.valid_from > today()),
                )
                .map((f) => (
                  <p key={f.key}>
                    {(
                      {
                        current_education_level: hi
                          ? 'पहले दर्ज पाठ्यक्रम'
                          : 'Previously recorded course',
                        enrollment_mode: hi
                          ? 'पहले दर्ज पढ़ाई का तरीका'
                          : 'Previously recorded study mode',
                        school_recognized_or_government: hi
                          ? 'पहले दर्ज स्कूल मान्यता'
                          : 'Previously recorded school recognition',
                      } as Record<string, string>
                    )[f.key] ??
                      questions.find((q) => q.key === f.key)?.label[hi ? 1 : 0] ??
                      (hi ? 'पुराना शिक्षा उत्तर' : 'Legacy education answer')}
                    : {answerLabel(f, hi)} · {f.valid_from ?? '…'} –{' '}
                    {f.valid_until ??
                      (hi ? 'अर्थ स्पष्ट करना बाकी है' : 'meaning needs clarification')}
                  </p>
                ))}
            </section>
          )}
          <DocumentSummary />
          <section className="panel">
            <h2>{hi ? 'आपके अगले कदम' : 'Your next steps'}</h2>
            <Link className="button" to="/discover">
              {hi ? 'अवसर खोजें' : 'Explore opportunities'}
            </Link>{' '}
            <Link className="button secondary" to="/documents">
              {hi ? 'मेरे दस्तावेज़' : 'My Documents'}
            </Link>{' '}
            <Link to="/plan">{hi ? 'तैयारी की योजना' : 'View readiness plan'}</Link>
          </section>
        </>
      ) : (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (stage === 0) {
              setStage(1);
              return;
            }
            if (stage === 1 && isNew) {
              setStage(2);
              return;
            }
            if (save.isPending || !dirty || invalid) return;
            submitted.current = structuredClone(draft);
            save.mutate();
          }}
        >
          <p role="status">
            {save.isPending
              ? t.saving
              : save.error instanceof RequestError && save.error.code === 'profile_conflict'
                ? hi
                  ? 'पुरानी प्रति — दूसरे टैब या सत्र में नई जानकारी सहेजी गई है। आपके अनसहेजे उत्तर बने रहेंगे।'
                  : 'Stale edit — another tab or session saved newer information. Your unsaved answers are preserved.'
                : save.isError
                  ? hi
                    ? 'बदलाव सहेजे नहीं गए'
                    : 'Changes were not saved'
                  : dirty
                    ? hi
                      ? 'सहेजे नहीं गए बदलाव'
                      : 'Unsaved changes'
                    : isNew
                      ? hi
                        ? 'अभी प्रोफ़ाइल नहीं बना'
                        : 'Not yet created'
                      : hi
                        ? 'कोई बदलाव नहीं'
                        : 'No changes to save'}
          </p>
          {isNew && stage === 0 ? (
            <section className="panel">
              <h2>{hi ? 'आप क्या खोजना चाहते हैं?' : 'What would you like to explore?'}</h2>
              <p>
                {hi
                  ? 'यह सवाल चुनने में मदद करता है। सभी अवसर फिर भी देख सकते हैं।'
                  : 'This helps us keep your questions relevant. You can still browse every opportunity.'}
              </p>
              <label className="field">
                {hi ? 'नाम या उपनाम' : 'Name or nickname'}
                <input
                  aria-label="Profile name"
                  disabled={save.isPending}
                  required
                  maxLength={80}
                  value={draft.name}
                  onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                />
              </label>
              <div className="question-topics">
                {(['education', 'employment', 'general'] as Goal[]).map((g) => (
                  <button
                    type="button"
                    className="topic-chip"
                    aria-pressed={goal === g}
                    key={g}
                    onClick={() => setGoal(g)}
                  >
                    {hi
                      ? { education: 'शिक्षा', employment: 'रोज़गार', general: 'अभी खोज रहा हूँ' }[
                          g
                        ]
                      : {
                          education: 'Education',
                          employment: 'Work and skills',
                          general: 'Just exploring',
                        }[g]}
                  </button>
                ))}
              </div>
              <Link to="/discover">{hi ? 'पहले अवसर देखें' : 'Explore before setting up'}</Link>
            </section>
          ) : stage === 2 && isNew ? (
            <section className="panel profile-review">
              <h2>{hi ? 'अपनी जानकारी की समीक्षा करें' : 'Review your answers'}</h2>
              <h3>{draft.name}</h3>
              <dl>
                {answered(draft.facts).map((f) => (
                  <div key={f.key}>
                    <dt>
                      {questions.find((q) => q.key === f.key)?.label[hi ? 1 : 0] ??
                        t.factNames[f.key as keyof typeof t.factNames]}
                    </dt>
                    <dd>
                      {answerLabel(f, hi)}
                      {(f.valid_from || f.valid_until) && (
                        <small>
                          {' '}
                          · {hi ? 'लागू अवधि' : 'Applies'}: {f.valid_from ?? '…'} –{' '}
                          {f.valid_until ?? '…'}
                        </small>
                      )}
                    </dd>
                  </div>
                ))}
              </dl>
              <p>
                {hi
                  ? 'छोड़े गए सवाल अज्ञात रहेंगे। बाद में जोड़ सकते हैं।'
                  : 'Skipped answers stay unknown. You can add them later.'}
              </p>
            </section>
          ) : (
            <section className="panel">
              <h2>
                {requested
                  ? requested.label[hi ? 1 : 0]
                  : hi
                    ? 'केवल उपयोगी सवाल'
                    : 'Only the questions that help'}
              </h2>
              {!isNew && section === 'basics' && (
                <label className="field">
                  {hi ? 'नाम या उपनाम' : 'Name or nickname'}
                  <input
                    aria-label="Profile name"
                    disabled={save.isPending}
                    required
                    value={draft.name}
                    maxLength={80}
                    onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                  />
                </label>
              )}
              <p>
                {hi
                  ? 'सभी सवाल वैकल्पिक हैं। उत्तर आपके द्वारा दिए गए हैं।'
                  : 'Every question is optional. Answers are self-reported.'}
              </p>
              {visible.map(renderQuestion)}
              {requested?.when && !requested.when(values) && (
                <p role="status">
                  {hi
                    ? 'यह सवाल आपकी वर्तमान स्थिति पर लागू नहीं होता। पहले शिक्षा संबंधी जानकारी स्पष्ट करें।'
                    : 'This question does not apply to your current study context. Clarify your education details first.'}
                  <Link to="/profile?section=education">
                    {hi ? 'शिक्षा की जानकारी खोलें' : 'Open education details'}
                  </Link>
                </p>
              )}
            </section>
          )}
          <div className="form-actions">
            {isNew && stage > 0 && (
              <button
                type="button"
                className="button secondary"
                disabled={save.isPending}
                onClick={() => setStage(stage - 1)}
              >
                {hi ? 'पीछे' : 'Back'}
              </button>
            )}
            {!isNew && (
              <button
                type="button"
                className="button secondary"
                disabled={save.isPending}
                onClick={discard}
              >
                {hi ? 'रद्द करें' : 'Cancel'}
              </button>
            )}
            <button
              className="button"
              disabled={
                save.isPending ||
                !draft.name.trim() ||
                invalid ||
                ((!isNew || stage === 2) && !dirty)
              }
            >
              {save.isPending
                ? t.saving
                : isNew
                  ? stage === 0
                    ? hi
                      ? 'आगे बढ़ें'
                      : 'Continue'
                    : stage === 1
                      ? hi
                        ? 'समीक्षा करें'
                        : 'Review your answers'
                      : hi
                        ? 'सेटअप पूरा करें'
                        : 'Finish setup'
                  : hi
                    ? 'बदलाव सहेजें'
                    : 'Save changes'}
            </button>
          </div>
          {save.isError && (
            <div role="alert">
              <p>{save.error.message}</p>
              {save.error instanceof RequestError &&
                save.error.issues.map((issue, index) => (
                  <p key={index}>
                    {issue.fields
                      ?.map(
                        (key) =>
                          questions.find((q) => q.key === key)?.label[hi ? 1 : 0] ??
                          (hi ? 'संबंधित प्रश्न' : 'The indicated question'),
                      )
                      .join(' · ')}
                    {issue.message ? `: ${issue.message[hi ? 1 : 0]}` : ''}
                  </p>
                ))}
              <p>
                {hi
                  ? 'आपके उत्तर यहीं सुरक्षित हैं। दोबारा कोशिश करें। पुरानी प्रति होने पर सहेजी जानकारी पुनः लोड करें।'
                  : save.error instanceof RequestError && save.error.code === 'profile_conflict'
                    ? 'Another tab or session saved newer information. Your draft is preserved. Review it before choosing Reload saved version.'
                    : save.error instanceof RequestError &&
                        ['subject_not_found', 'authentication_required', 'invalid_token'].includes(
                          save.error.code,
                        )
                      ? 'Your subject access or session is unavailable. Sign in or select an authorized person. Your draft has not been saved.'
                      : save.error instanceof RequestError &&
                          save.error.code === 'semantic_conflict'
                        ? 'Review the identified questions and their dates. Other answers remain here.'
                        : save.error instanceof RequestError && save.error.code === 'invalid_value'
                          ? 'Check the indicated value or date. Your answers are still here.'
                          : 'Your answers are still here. The request failed; retry when the connection or service is available.'}
              </p>
              <button
                type="button"
                className="text-button"
                onClick={() => {
                  if (guard.confirmLeave()) {
                    baseline.current = signature(draft);
                    initialized.current = false;
                    setDraft(null);
                    void query.refetch();
                  }
                }}
              >
                {hi ? 'सहेजी जानकारी पुनः लोड करें' : 'Reload saved version'}
              </button>
            </div>
          )}
        </form>
      )}
    </div>
  );
}
