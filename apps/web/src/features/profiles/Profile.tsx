import { ReadinessJourney } from '../../components/Atlas';
import { useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Plus, Trash2, UserRound } from 'lucide-react';
import { useStrings, useLanguage } from '../../app/App';
import { api, fail } from '../../lib/api/client';
import type { components } from '../../lib/api/schema';
type Fact = components['schemas']['FactInput'];
const fields: { key: Fact['key']; kind: 'text' | 'number' | 'boolean' }[] = [
  { key: 'age', kind: 'number' },
  { key: 'education_level', kind: 'text' },
  { key: 'student_status', kind: 'boolean' },
  { key: 'enrollment_mode', kind: 'text' },
  { key: 'school_recognized_or_government', kind: 'boolean' },
  { key: 'nationality', kind: 'text' },
  { key: 'disability_percentage', kind: 'number' },
  { key: 'annual_parental_income', kind: 'number' },
  { key: 'annual_personal_income', kind: 'number' },
  { key: 'domicile_state', kind: 'text' },
  { key: 'domicile_district', kind: 'text' },
  { key: 'residence_state', kind: 'text' },
  { key: 'residence_district', kind: 'text' },
  { key: 'employment_status', kind: 'text' },
  { key: 'has_income_certificate', kind: 'boolean' },
  { key: 'has_disability_certificate', kind: 'boolean' },
  { key: 'has_udid_certificate', kind: 'boolean' },
];
export function Profile() {
  const t = useStrings();
  const hi = useLanguage() === 'hi';
  const { personId } = useParams();
  const [params] = useSearchParams();
  const requestedField = fields.find((f) => f.key === params.get('field'))?.key;
  const cache = useQueryClient();
  const [name, setName] = useState('');
  const [facts, setFacts] = useState<Fact[]>([]);
  const [saved, setSaved] = useState(false);
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
    if (query.data) {
      setName(query.data.display_name);
      setFacts(
        query.data.facts
          .filter((f) => f.origin === 'user_supplied' || f.origin === 'unknown')
          .map((f) => ({
            key: f.key as Fact['key'],
            value: f.value,
            valid_from: f.valid_from,
            valid_until: f.valid_until,
            income_period: (f.context?.income_period as string) ?? null,
            income_definition: (f.context?.income_definition as string) ?? null,
          })),
      );
    }
  }, [query.data]);
  useEffect(() => {
    if (!query.isPending && !query.isError && requestedField) {
      setFacts((previous) =>
        previous.some((f) => f.key === requestedField)
          ? previous
          : [...previous, { key: requestedField, value: null }],
      );
      window.setTimeout(
        () =>
          document
            .getElementById(`fact-${requestedField}`)
            ?.scrollIntoView({ block: 'center', behavior: 'smooth' }),
        150,
      );
    }
  }, [requestedField, query.isPending, query.isError]);
  const save = useMutation({
    mutationFn: async () => {
      if (personId) {
        const { data, error } = await api.PUT('/v1/people/{identifier}', {
          params: { path: { identifier: personId } },
          body: { display_name: name, facts },
        });
        if (!data) return fail(error);
        return { id: data.id, display_name: data.name, facts: data.facts };
      }
      const { data, error } = await api.PUT('/v1/profile/me', {
        body: { display_name: name, facts },
      });
      return data ?? fail(error);
    },
    onSuccess: (data) => {
      cache.setQueryData(['personal-profile', personId], data);
      void cache.invalidateQueries({ queryKey: ['workspaces'] });
      void cache.invalidateQueries({ queryKey: ['dashboard-summary'] });
      void cache.invalidateQueries({ queryKey: ['plan'] });
      setSaved(true);
    },
  });
  function update(index: number, patch: Partial<Fact>) {
    setSaved(false);
    setFacts((previous) => previous.map((fact, i) => (i === index ? { ...fact, ...patch } : fact)));
  }
  if (query.isPending)
    return (
      <div className="page" role="status">
        {t.loading}
      </div>
    );
  if (query.isError)
    return (
      <div className="page">
        <section className="panel" role="alert">
          <h1>{t.profile}</h1>
          <p>{query.error.message}</p>
          <Link className="button" to="/settings">
            {t.signIn}
          </Link>
        </section>
      </div>
    );
  return (
    <div className="page narrow">
      <div className="page-heading">
        <span className="eyebrow">{t.profileEyebrow}</span>
        <h1>{t.profile}</h1>
        <p>{t.profileIntro}</p>
      </div>
      <div className="notice">
        <UserRound size={18} />
        <div>
          <strong>{t.syntheticProfile}</strong>
          <span>{t.syntheticProfileNote}</span>
        </div>
      </div>
      <ReadinessJourney
        steps={
          hi
            ? ['अपनी पहचान', 'ज़रूरी जानकारी', 'सहेजें और जाँचें']
            : ['Your context', 'Relevant questions', 'Save and assess']
        }
        active={saved ? 2 : facts.length ? 1 : 0}
      />
      <section className="profile-guide">
        <span className="step-dot">1</span>
        <div>
          <strong>{hi ? 'जो जानते हैं, उससे शुरू करें' : 'Start with what you know'}</strong>
          <p>
            {hi
              ? 'जानकारी वैकल्पिक है। अज्ञात को खाली छोड़ें।'
              : 'Answer only relevant questions. Leave uncertain information blank; you can return later.'}
          </p>
        </div>
      </section>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          setSaved(false);
          save.mutate();
        }}
      >
        <section className="panel">
          <label className="field">
            {t.displayName}
            <input
              value={name}
              maxLength={80}
              required
              onChange={(e) => {
                setName(e.target.value);
                setSaved(false);
              }}
              placeholder="Demo learner"
            />
          </label>
        </section>
        <section className="panel">
          <h2>{t.profileFacts}</h2>
          <p>{t.factHelp}</p>
          <div className="question-topics">
            {[
              {
                label: hi ? 'शिक्षा' : 'Education',
                keys: [
                  'education_level',
                  'student_status',
                  'enrollment_mode',
                  'school_recognized_or_government',
                ],
              },
              {
                label: hi ? 'स्थान' : 'Where you live',
                keys: [
                  'domicile_state',
                  'domicile_district',
                  'residence_state',
                  'residence_district',
                ],
              },
              {
                label: hi ? 'रोजगार' : 'Employment',
                keys: ['employment_status'],
              },
              {
                label: hi ? 'आय' : 'Relevant income',
                keys: ['annual_parental_income', 'annual_personal_income'],
              },
              {
                label: hi ? 'दस्तावेज़' : 'Evidence gaps',
                keys: [
                  'has_income_certificate',
                  'has_disability_certificate',
                  'has_udid_certificate',
                ],
              },
            ].map((topic) => (
              <button
                type="button"
                key={topic.label}
                className="topic-chip"
                onClick={() =>
                  setFacts((previous) => [
                    ...previous,
                    ...topic.keys
                      .filter((key) => !previous.some((f) => f.key === key))
                      .map((key) => ({ key: key as Fact['key'], value: null })),
                  ])
                }
              >
                {topic.label}
                <Plus size={14} />
              </button>
            ))}
          </div>
          {facts.map((fact, index) => {
            const kind = fields.find((f) => f.key === fact.key)?.kind || 'text';
            const income = fact.key.includes('income');
            return (
              <div id={`fact-${fact.key}`} className="fact-editor" key={fact.key}>
                <h3 className="question-label">
                  {t.factNames[fact.key as keyof typeof t.factNames] || fact.key}
                </h3>
                <label className="field">
                  {hi ? 'आपका उत्तर' : 'Your answer'}
                  {['enrollment_mode', 'education_level'].includes(fact.key) ? (
                    <select
                      aria-label={`${t.value} ${index + 1}`}
                      value={fact.value == null ? '' : String(fact.value)}
                      onChange={(e) => update(index, { value: e.target.value || null })}
                    >
                      <option value="">{t.unknown}</option>
                      {(fact.key === 'enrollment_mode'
                        ? ['full_time', 'part_time', 'distance']
                        : ['IX', 'X', 'XI', 'XII', 'undergraduate', 'postgraduate', 'other']
                      ).map((v) => (
                        <option key={v} value={v}>
                          {hi
                            ? {
                                full_time: 'नियमित पूर्णकालिक',
                                part_time: 'अंशकालिक',
                                distance: 'दूरस्थ',
                                undergraduate: 'स्नातक',
                                postgraduate: 'स्नातकोत्तर',
                                other: 'अन्य',
                              }[v] || v
                            : v.replaceAll('_', ' ')}
                        </option>
                      ))}
                    </select>
                  ) : kind === 'boolean' ? (
                    <select
                      aria-label={`${t.value} ${index + 1}`}
                      value={fact.value === true ? 'true' : fact.value === false ? 'false' : ''}
                      onChange={(e) =>
                        update(index, {
                          value: e.target.value === '' ? null : e.target.value === 'true',
                        })
                      }
                    >
                      <option value="">{t.unknown}</option>
                      <option value="true">{t.yes}</option>
                      <option value="false">{t.no}</option>
                    </select>
                  ) : (
                    <input
                      aria-label={`${t.value} ${index + 1}`}
                      type={kind === 'number' ? 'number' : 'text'}
                      min={kind === 'number' ? 0 : undefined}
                      max={
                        fact.key === 'age'
                          ? 130
                          : fact.key === 'disability_percentage'
                            ? 100
                            : undefined
                      }
                      step={fact.key === 'age' ? 1 : 'any'}
                      value={fact.value == null ? '' : String(fact.value)}
                      placeholder={t.unknown}
                      maxLength={100}
                      onChange={(e) =>
                        update(index, {
                          value:
                            e.target.value === ''
                              ? null
                              : kind === 'number'
                                ? Number(e.target.value)
                                : e.target.value,
                        })
                      }
                    />
                  )}
                </label>
                <button
                  className="icon-button remove-fact"
                  type="button"
                  aria-label={`${t.removeFact} ${index + 1}`}
                  onClick={() => {
                    setFacts((prev) => prev.filter((_, i) => i !== index));
                    setSaved(false);
                  }}
                >
                  <Trash2 size={17} />
                </button>
                {income && (
                  <>
                    <label className="field">
                      {t.incomePeriod}
                      <input
                        value={fact.income_period || ''}
                        onChange={(e) => update(index, { income_period: e.target.value || null })}
                      />
                    </label>
                    <label className="field">
                      {t.incomeDefinition}
                      <input
                        value={fact.income_definition || ''}
                        onChange={(e) =>
                          update(index, { income_definition: e.target.value || null })
                        }
                      />
                    </label>
                  </>
                )}
                <details className="fact-dates">
                  <summary>{t.validity}</summary>
                  <label className="field">
                    {t.validFrom}
                    <input
                      type="date"
                      value={fact.valid_from || ''}
                      onChange={(e) => update(index, { valid_from: e.target.value || null })}
                    />
                  </label>
                  <label className="field">
                    {t.validUntil}
                    <input
                      type="date"
                      value={fact.valid_until || ''}
                      onChange={(e) => update(index, { valid_until: e.target.value || null })}
                    />
                  </label>
                </details>
                <small className="fact-origin">
                  {fact.value === null ? t.unknown : t.userSupplied}
                </small>
              </div>
            );
          })}
          <button
            className="text-button add-fact"
            type="button"
            onClick={() => {
              setFacts((prev) => [
                ...prev,
                {
                  key: fields.find((f) => !prev.some((v) => v.key === f.key))?.key || 'age',
                  value: null,
                },
              ]);
              setSaved(false);
            }}
            disabled={facts.length >= fields.length}
          >
            <Plus size={16} />
            {t.addFact}
          </button>
        </section>
        {query.data?.facts
          .filter((f) => f.origin === 'verified_document')
          .map((f) => (
            <section className="panel" key={f.id}>
              <strong>{f.key}</strong>
              <p>
                {String(f.value)} · {f.origin} · {f.verification}
              </p>
            </section>
          ))}
        <div className="form-actions">
          <button className="button" disabled={save.isPending}>
            {save.isPending ? t.saving : t.saveProfile}
          </button>
          {saved && (
            <div role="status">
              <p>{t.profileSaved}</p>
              <Link
                className="field-followup"
                to={personId ? `/plan?kind=person&id=${personId}` : '/plan'}
              >
                {hi ? 'अद्यतन कार्ययोजना देखें' : 'See your updated plan'}
              </Link>
            </div>
          )}
          {save.isError && <p role="alert">{save.error.message}</p>}
        </div>
      </form>
    </div>
  );
}
