import { useSearchParams } from 'react-router-dom';
import { documentStatus, documentsHref } from '../documents/Documents';
import { ContextLink as Link } from '../../app/subject-context';
import { IntelligenceMap } from '../../components/IntelligenceMap';
import { AssessmentLedger } from '../../components/Atlas';
import { Assistant } from '../assistant/Assistant';
import { useState } from 'react';

import { useQuery, useMutation } from '@tanstack/react-query';
import { ArrowRight, GitBranch, RefreshCw, FlaskConical } from 'lucide-react';
import { api, fail } from '../../lib/api/client';
import type { components } from '../../lib/api/schema';
import { useStrings, useLanguage } from '../../app/App';
import { useSubject } from '../../app/subject-context';
type Action = components['schemas']['ActionView'];
export function Plan() {
  const context = useSubject();
  return <SubjectPlan key={context.key} />;
}
function SubjectPlan() {
  const t = useStrings();
  const hi = useLanguage() === 'hi';
  const context = useSubject();
  const [params] = useSearchParams();
  const development = params.get('development') === 'true';
  const subject = context.subject;
  const identifier = subject.id;
  const [selected, setSelected] = useState<Action | null>(null);
  const [age, setAge] = useState('');
  const [explanationId, setExplanationId] = useState('');
  const query = useQuery({
    queryKey: ['plan', subject, development],
    enabled: context.available && !context.pending,
    retry: false,
    staleTime: 0,
    refetchOnMount: 'always',
    refetchOnWindowFocus: false,
    queryFn: async () => {
      const { data, error } = await api.POST('/v1/plan', { body: { subject, development } });
      return data ?? fail(error);
    },
  });
  const simulation = useMutation({
    mutationFn: async () => {
      const { data, error } = await api.POST('/v1/plan/simulate', {
        body: { subject, development, facts: [{ key: 'age', value: Number(age) }] },
      });
      return data ?? fail(error);
    },
  });
  const progress = useMutation({
    mutationFn: async (action: Action) => {
      const { data, error } = await api.PATCH('/v1/actions/{identifier}', {
        params: { path: { identifier: action.id } },
        body: { status: action.status === 'in_progress' ? 'pending' : 'in_progress' },
      });
      return data ?? fail(error);
    },
    onSuccess: () => {
      setSelected(null);
      void query.refetch();
    },
  });
  const data = query.isError ? undefined : (simulation.data ?? query.data);
  function actionTitle(action: Action) {
    if (!action.fact)
      return hi
        ? action.title
            .replace(/^Verify evidence: /, 'प्रमाण सत्यापित करें: ')
            .replace(/^Clarify: /, 'स्पष्टीकरण लें: ')
            .replace(/^Provide: /, 'जानकारी दें: ')
        : action.title;
    const name =
      t.factNames[action.fact as keyof typeof t.factNames] || action.fact.replaceAll('_', ' ');
    return (
      (action.kind === 'document'
        ? hi
          ? 'प्रमाण सत्यापित करें: '
          : 'Verify evidence: '
        : hi
          ? 'जानकारी दें: '
          : 'Provide: ') + name
    );
  }
  return (
    <div className="page">
      <div className="page-heading plan-heading">
        <div>
          <span className="eyebrow">{hi ? 'आपका अगला कदम' : 'THE OPPORTUNITY UNLOCK GRAPH'}</span>
          <h1>{hi ? 'अंतर से अगले कदम तक' : 'From missing pieces to next steps'}</h1>
          <p>
            {hi
              ? 'एक साझा कदम कई अवसरों की तैयारी में मदद कर सकता है।'
              : 'One reusable action can improve readiness across several opportunities.'}
          </p>
        </div>
        <GitBranch size={42} />
      </div>
      <div className="plan-toolbar">
        <label className="field">
          {hi ? 'किसके लिए योजना?' : 'Whose plan?'}
          <select
            value={context.key}
            onChange={(e) => {
              context.select(e.target.value);
              simulation.reset();
              setSelected(null);
            }}
          >
            {context.options.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </label>
        <button
          className="button secondary"
          disabled={query.isFetching || !context.available || context.pending}
          onClick={() => {
            simulation.reset();
            void query.refetch();
            setSelected(null);
          }}
        >
          <RefreshCw size={16} />
          {hi ? 'फिर जाँचें' : 'Refresh assessment'}
        </button>
      </div>
      {!context.available && <p role="alert">{context.label}</p>}
      {context.available && query.isPending && (
        <div className="panel" role="status">
          {t.loading}
        </div>
      )}
      {query.isError && (
        <section className="panel" role="alert">
          <p>{query.error.message}</p>
          <Link className="button" to="/profile">
            {t.profile}
          </Link>
        </section>
      )}
      {data && (
        <>
          {data.hypothetical && (
            <div role="status" className="notice">
              <FlaskConical />
              {hi
                ? 'काल्पनिक पूर्वावलोकन। कोई तथ्य सहेजा नहीं गया।'
                : 'Hypothetical preview. No stored facts or evidence have changed.'}
              <button className="text-button" onClick={() => simulation.reset()}>
                {hi ? 'वास्तविक योजना पर लौटें' : 'Return to actual plan'}
              </button>
            </div>
          )}
          {!data.evaluations.length ? (
            <section className="empty-state panel">
              <GitBranch size={36} />
              <h2>
                {hi
                  ? 'सत्यापित अवसर आने पर आपकी योजना यहाँ होगी'
                  : 'Your plan begins with reviewed opportunities'}
              </h2>
              <p>
                {hi
                  ? 'अभी कोई वास्तविक अवसर प्रकाशित नहीं है। मसौदे प्रशासक की समीक्षा में निजी रहते हैं।'
                  : 'No real opportunities have been published yet. Drafts stay private until an administrator completes substantive review.'}
              </p>
              <Link className="button" to="/discover">
                {t.discover}
                <ArrowRight size={16} />
              </Link>
            </section>
          ) : (
            <>
              <div className="stats">
                <div className="stat">
                  <strong>{data.evaluations.length}</strong>
                  <span>{hi ? 'समीक्षित अवसर' : 'Reviewed opportunities'}</span>
                </div>
                <div className="stat">
                  <strong>{data.actions.length}</strong>
                  <span>{hi ? 'तैयारी के कदम' : 'Readiness actions'}</span>
                </div>
                <div className="stat">
                  <strong>{data.known_blockers.length}</strong>
                  <span>{hi ? 'वास्तविक प्रतिबंध' : 'Known restrictions'}</span>
                </div>
              </div>
              <IntelligenceMap
                plan={data}
                selected={selected}
                onSelect={setSelected}
                title={actionTitle}
              />
              {data.hypothetical && query.data && (
                <section className="simulation-comparison panel">
                  <h2>{hi ? 'वास्तविक और काल्पनिक तुलना' : 'Actual vs hypothetical'}</h2>
                  {data.evaluations.map((ev) => (
                    <div key={ev.id}>
                      <h3>{ev.opportunity_title}</h3>
                      <p>
                        {hi ? 'वास्तविक' : 'Actual'}:{' '}
                        {
                          t.assessmentStatuses[
                            query.data!.evaluations.find(
                              (old) => old.opportunity_id === ev.opportunity_id,
                            )?.status as keyof typeof t.assessmentStatuses
                          ]
                        }
                      </p>
                      <p>
                        {hi ? 'पूर्वावलोकन' : 'Preview'}:{' '}
                        {t.assessmentStatuses[ev.status as keyof typeof t.assessmentStatuses]}
                      </p>
                      <AssessmentLedger evaluation={ev} />
                    </div>
                  ))}
                  <p>
                    {hi
                      ? 'कोई तथ्य, प्रमाण या आकलन सहेजा नहीं गया।'
                      : 'No facts, evidence or assessments saved. Unrelated conditions remain in force.'}
                  </p>
                </section>
              )}
              {data.evaluations.some((ev) => ev.changes?.length) && (
                <section className="panel assessment-changes">
                  <span className="eyebrow">{hi ? 'क्या बदला' : 'WHAT CHANGED'}</span>
                  {data.evaluations
                    .filter((ev) => ev.changes?.length)
                    .map((ev) => (
                      <div key={ev.id}>
                        <h3>{ev.opportunity_title}</h3>
                        {ev.changes.map((change, i) => (
                          <p key={i}>
                            {String(change.requirement)} ·{' '}
                            {String(change.before).replaceAll('_', ' ')} →{' '}
                            {String(change.after).replaceAll('_', ' ')}
                          </p>
                        ))}
                      </div>
                    ))}
                </section>
              )}
              <div className="workspace-grid">
                <section className="panel">
                  <h2>{hi ? 'आपकी कार्यसूची' : 'Your action checklist'}</h2>
                  {data.actions.map((a, i) => (
                    <button className="action-row" key={a.identity} onClick={() => setSelected(a)}>
                      <span className="action-number">{String(i + 1).padStart(2, '0')}</span>
                      <span>
                        <strong>{actionTitle(a)}</strong>
                        <small>
                          {new Set(a.opportunities.map((o) => o.id)).size}{' '}
                          {hi ? 'अवसरों से जुड़ा' : 'linked opportunities'} ·{' '}
                          {a.kind === 'document'
                            ? documentStatus(a.documentary_status, hi)
                            : a.status === 'in_progress'
                              ? hi
                                ? 'प्रगति में'
                                : 'In progress'
                              : hi
                                ? 'बाकी'
                                : 'Pending'}
                        </small>
                      </span>
                      <ArrowRight size={16} />
                    </button>
                  ))}
                  {!data.actions.length && (
                    <p>
                      {hi
                        ? 'कोई अज्ञात शर्त शेष नहीं। अंतिम निर्णय प्राधिकरण का है।'
                        : 'No unknown conditions remain in this assessment. The authority makes the final decision.'}
                    </p>
                  )}
                </section>
                <section className="panel" aria-live="polite">
                  <h2>
                    {selected
                      ? actionTitle(selected)
                      : hi
                        ? 'हर कदम के पीछे प्रमाण'
                        : 'Evidence behind every step'}
                  </h2>
                  {selected ? (
                    <>
                      <p>{selected.explanation}</p>
                      {selected.kind === 'document' && (
                        <div className="notice document-action-notice">
                          <strong>{documentStatus(selected.documentary_status, hi)}</strong>
                          <p>
                            {hi
                              ? 'निजी फ़ाइल जोड़ने से आधिकारिक सत्यापन नहीं होता।'
                              : 'Adding a private file does not establish official verification.'}
                          </p>
                          {selected.opportunities.map((o) => (
                            <Link
                              key={String(o.requirement_id)}
                              className="button secondary"
                              to={documentsHref(String(o.requirement_id))}
                            >
                              {hi ? 'दस्तावेज़ जोड़ें या देखें:' : 'Add or manage evidence:'}{' '}
                              {String(o.requirement)}
                            </Link>
                          ))}
                        </div>
                      )}
                      {selected.kind === 'information' &&
                        selected.fact &&
                        subject.kind === 'person' && (
                          <Link
                            className="field-followup"
                            to={`${identifier ? `/people/${identifier}/edit` : '/profile'}?${new URLSearchParams({ field: selected.fact, opportunity: String(selected.opportunities[0]?.id ?? ''), requirement: String(selected.opportunities[0]?.requirement_id ?? '') })}`}
                          >
                            {hi ? 'यह जानकारी दें' : 'Provide this missing information'}
                            <ArrowRight size={16} />
                          </Link>
                        )}
                      <p>
                        {hi ? 'कार्य स्थिति' : 'Task status'}:{' '}
                        {selected.status === 'in_progress'
                          ? hi
                            ? 'जारी है'
                            : 'In progress'
                          : hi
                            ? 'शुरू नहीं हुआ'
                            : 'Pending'}
                      </p>
                      {!data.hypothetical && (
                        <button
                          className="button secondary"
                          disabled={progress.isPending}
                          onClick={() => progress.mutate(selected)}
                        >
                          {selected.status === 'in_progress'
                            ? hi
                              ? 'लंबित पर लौटाएं'
                              : 'Return to pending'
                            : hi
                              ? 'मैंने यह कदम शुरू किया है'
                              : 'Mark in progress'}
                        </button>
                      )}
                      <small className="muted">
                        {hi
                          ? 'कार्य स्थिति बदलने से प्रमाण सत्यापित नहीं होता।'
                          : 'Task progress does not verify evidence or change eligibility.'}
                      </small>
                      {progress.isError && <p role="alert">{progress.error.message}</p>}
                      {selected.opportunities.map((o, i) => (
                        <div className="evidence-card" key={i}>
                          <p>{String(o.requirement)}</p>
                          <Link to={`/opportunities/${String(o.id)}`}>
                            {hi ? 'अवसर देखें' : 'View opportunity'}
                          </Link>
                          {Array.isArray(o.citations) &&
                            o.citations.map((c: Record<string, unknown>, j) => (
                              <blockquote key={j}>
                                {String(c.passage)}
                                <a href={String(c.source_url)} target="_blank" rel="noreferrer">
                                  {hi ? 'मूल स्रोत' : 'Original source'} · {String(c.page)}
                                </a>
                              </blockquote>
                            ))}
                        </div>
                      ))}
                    </>
                  ) : (
                    <p>
                      {hi
                        ? 'कार्यसूची या ग्राफ़ में कदम चुनें।'
                        : 'Select a step in the graph or checklist to see the exact published requirements and citations.'}
                    </p>
                  )}
                </section>
              </div>
              {!data.hypothetical && (
                <section className="plan-assistant">
                  <label className="field">
                    {hi
                      ? 'किस अवसर के बारे में पूछना है?'
                      : 'Which opportunity would you like to understand?'}
                    <select
                      value={
                        data.evaluations.some((e) => e.id === explanationId)
                          ? explanationId
                          : data.evaluations[0].id
                      }
                      onChange={(e) => setExplanationId(e.target.value)}
                    >
                      {data.evaluations.map((ev) => (
                        <option key={ev.id} value={ev.id}>
                          {ev.opportunity_title || ev.opportunity_id}
                        </option>
                      ))}
                    </select>
                  </label>
                  <Assistant
                    opportunityId={
                      (data.evaluations.find((e) => e.id === explanationId) ?? data.evaluations[0])
                        .opportunity_id
                    }
                    key={
                      data.evaluations.some((e) => e.id === explanationId)
                        ? explanationId
                        : data.evaluations[0].id
                    }
                    evaluationId={
                      data.evaluations.some((e) => e.id === explanationId)
                        ? explanationId
                        : data.evaluations[0].id
                    }
                  />
                </section>
              )}
              {data.known_blockers.length > 0 && (
                <section className="panel">
                  <h2>
                    {hi
                      ? 'शर्तें जिन्हें दस्तावेज़ जोड़ने से नहीं बदला जा सकता'
                      : 'Conditions a new document cannot resolve'}
                  </h2>
                  {data.known_blockers.map((b, i) => (
                    <p key={i}>{String(b.requirement)}</p>
                  ))}
                  <p>
                    {hi
                      ? 'केवल गलत तथ्य सुधारें। पात्रता की शर्तों को बदलने के लिए गलत जानकारी न दें।'
                      : 'Correct inaccurate facts where needed. Do not misrepresent information to change an outcome.'}
                  </p>
                </section>
              )}
              {subject.kind === 'person' && (
                <form
                  className="panel simulation"
                  onSubmit={(e) => {
                    e.preventDefault();
                    simulation.mutate();
                    setSelected(null);
                  }}
                >
                  <FlaskConical />
                  <h2>
                    {hi ? 'सहेजे बिना संभावित बदलाव देखें' : 'Explore a correction without saving'}
                  </h2>
                  <p>
                    {hi
                      ? 'आयु की गलती सुधारने का पूर्वावलोकन। दस्तावेज़ सत्यापित नहीं होगा और वास्तविक प्रतिबंध बने रहेंगे।'
                      : 'Preview correcting an inaccurate age. Documentary evidence stays unverified and unrelated restrictions remain.'}
                  </p>
                  <label className="field">
                    {hi ? 'काल्पनिक आयु' : 'Hypothetical age'}
                    <input
                      required
                      type="number"
                      min="0"
                      max="130"
                      step="1"
                      value={age}
                      onChange={(e) => setAge(e.target.value)}
                    />
                  </label>
                  <button className="button secondary" disabled={simulation.isPending}>
                    {hi ? 'पूर्वावलोकन' : 'Preview assessment'}
                  </button>
                  {simulation.isError && <p role="alert">{simulation.error.message}</p>}
                </form>
              )}
              <p className="notice">
                {hi
                  ? 'यह प्रारंभिक, प्रमाण-आधारित आकलन है। अंतिम पात्रता और चयन संबंधित प्राधिकरण तय करता है।'
                  : 'Preliminary, evidence-based assessment. The issuing authority decides eligibility, selection and approval.'}
              </p>
            </>
          )}
        </>
      )}
    </div>
  );
}
