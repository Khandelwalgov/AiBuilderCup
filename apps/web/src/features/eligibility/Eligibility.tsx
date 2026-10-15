import { useSearchParams } from 'react-router-dom';
import { documentStatus, documentsHref } from '../documents/Documents';
import { documentKeys, answerLabel, type Fact } from '../profiles/questions';
import { displayDate } from '../../i18n/format';
import { ContextLink as Link } from '../../app/subject-context';
import { AssessmentLedger } from '../../components/Atlas';
import { Assistant } from '../assistant/Assistant';
import { useState } from 'react';
import { useSubject } from '../../app/subject-context';
import { useLanguage } from '../../app/App';
import { useMutation } from '@tanstack/react-query';

import { CheckCircle2, CircleHelp, XCircle } from 'lucide-react';
import { useStrings } from '../../app/App';
import { api, fail } from '../../lib/api/client';
export function Eligibility({ id }: { id: string }) {
  const context = useSubject();
  return <Assessment key={`${id}:${context.key}`} id={id} />;
}
function Assessment({ id }: { id: string }) {
  const context = useSubject();
  const [params] = useSearchParams();
  const development = params.get('development') === 'true';
  const t = useStrings();
  const hi = useLanguage() === 'hi';
  const [applicationType, setApplicationType] = useState<'fresh' | 'renewal' | ''>('');
  const query = useMutation({
    mutationFn: async () => {
      const { data, error } = await api.POST('/v1/opportunities/{identifier}/evaluate', {
        params: { path: { identifier: id } },
        body: { subject: context.subject, application_type: applicationType || null, development },
      });
      return data ?? fail(error);
    },
  });
  return (
    <section className="panel evaluation">
      <span className="eyebrow">{t.preliminary}</span>
      <h2>{t.checkEligibility}</h2>
      <p>{t.evaluationIntro}</p>
      <p className="selected-subject">
        <strong>{hi ? 'आकलन किसके लिए' : 'Assessing'}:</strong> {context.label}
      </p>
      <label className="field">
        {hi ? 'इस अवसर का आवेदन संदर्भ' : 'Application context for this opportunity'}
        <select
          value={applicationType}
          onChange={(e) => {
            setApplicationType(e.target.value as typeof applicationType);
            query.reset();
          }}
        >
          <option value="">{t.unknown}</option>
          <option value="fresh">{hi ? 'नया आवेदन' : 'Fresh application'}</option>
          <option value="renewal">{hi ? 'नवीनीकरण' : 'Renewal'}</option>
        </select>
      </label>
      <div className="evaluation-actions">
        <button
          className="button"
          onClick={() => query.mutate()}
          disabled={query.isPending || !context.available || context.pending}
        >
          {query.isPending ? t.evaluating : t.checkEligibility}
        </button>
        <Link className="text-button" to="/profile">
          {t.editProfile}
        </Link>
      </div>
      {query.isError && (
        <div role="alert" className="notice">
          <div>
            <strong>{query.error.message}</strong>
            <Link to="/settings">{t.signIn}</Link> · <Link to="/profile">{t.editProfile}</Link>
          </div>
        </div>
      )}
      {query.data && !query.isError && (
        <div aria-live="polite">
          <AssessmentLedger evaluation={query.data} />
          <p className="assessment-status">
            {t.assessmentStatuses[query.data.status as keyof typeof t.assessmentStatuses] ||
              query.data.status}
          </p>
          <div className="notice">
            <p>{query.data.disclaimer}</p>
          </div>
          <p>{t.explanationLanguage}</p>
          {query.data.requirements.map((req) => {
            const outcome = req.result.outcome;
            const Icon =
              outcome === 'satisfied'
                ? CheckCircle2
                : outcome === 'unsatisfied'
                  ? XCircle
                  : CircleHelp;
            return (
              <article
                id={`requirement-${req.requirement_id}`}
                className={`requirement-result ${outcome}`}
                key={req.requirement_id}
              >
                <div className="requirement-title">
                  <Icon size={20} />
                  <h3>{req.requirement}</h3>
                  <span>{t.outcomes[outcome]}</span>
                </div>
                <p>{req.result.reason}</p>
                {(req.result.kind === 'evidence_gap' || req.documentary_status) && (
                  <div className="notice">
                    <strong>{documentStatus(req.documentary_status, hi)}</strong>
                    <p>
                      {hi
                        ? 'अपलोड और आधिकारिक सत्यापन अलग हैं। पात्रता की अनिश्चितता अभी बनी रहती है।'
                        : 'Uploading and official verification are separate. Eligibility uncertainty remains.'}
                    </p>
                    <Link className="button secondary" to={documentsHref(req.requirement_id)}>
                      {hi ? 'दस्तावेज़ जोड़ें या प्रबंधित करें' : 'Add or manage document'}
                    </Link>
                  </div>
                )}
                {req.result.kind !== 'evidence_gap' &&
                  req.result.missing
                    .filter(
                      (field) => !documentKeys.has(field as never) && field !== 'application_type',
                    )
                    .map((field) => (
                      <Link
                        className="field-followup"
                        key={field}
                        to={`/profile?field=${encodeURIComponent(field)}&opportunity=${id}&requirement=${req.requirement_id}`}
                      >
                        {hi ? 'यह जानकारी दें:' : 'Provide missing information:'}{' '}
                        {t.factNames[field as keyof typeof t.factNames] ??
                          (hi ? 'शर्त स्पष्ट करें' : 'Clarify condition')}
                      </Link>
                    ))}
                {req.result.kind === 'evidence_gap' && (
                  <strong className="evidence-gap">{t.evidenceGap}</strong>
                )}
                {req.result.facts.length > 0 && (
                  <details>
                    <summary>{t.factsUsed}</summary>
                    {req.result.facts.map((f, i) => (
                      <p key={`${f.id}-${i}`}>
                        {t.factNames[f.key as keyof typeof t.factNames] ??
                          (hi ? 'संबंधित जानकारी' : 'Relevant answer')}
                        : {answerLabel({ key: f.key as Fact['key'], value: f.value }, hi)} ·{' '}
                        {f.origin === 'verified_document' && f.verification === 'verified'
                          ? hi
                            ? 'अधिकृत प्रमाण से सत्यापित'
                            : 'Verified by an authorized evidence process'
                          : f.origin === 'ai_inference'
                            ? hi
                              ? 'AI की व्याख्या — समीक्षा आवश्यक'
                              : 'AI interpretation — needs review'
                            : hi
                              ? 'आपका उत्तर — स्वतंत्र सत्यापन नहीं हुआ'
                              : 'Your answer — not independently verified'}
                      </p>
                    ))}
                  </details>
                )}
                {req.result.children.length > 0 && (
                  <details>
                    <summary>{t.conditionDetails}</summary>
                    {req.result.children.map((child, i) => (
                      <p key={i}>
                        {t.outcomes[child.outcome]} · {child.reason}
                        {child.missing.length > 0 &&
                          ` (${child.missing.map((field) => t.factNames[field as keyof typeof t.factNames] ?? (hi ? 'स्पष्टीकरण आवश्यक' : 'Clarification needed')).join(', ')})`}
                      </p>
                    ))}
                  </details>
                )}
                {req.next_steps.length > 0 && (
                  <ul>
                    {req.next_steps.map((step) => (
                      <li key={step}>
                        {step.replace(
                          /\b[a-z]+(?:_[a-z]+)+\b/g,
                          (field) =>
                            t.factNames[field as keyof typeof t.factNames] ??
                            (hi ? 'संबंधित शर्त' : 'the relevant condition'),
                        )}
                      </li>
                    ))}
                  </ul>
                )}
                {req.citations.map((citation, i) => (
                  <blockquote key={i}>
                    <p>{citation.passage}</p>
                    <a href={citation.source_url} target="_blank" rel="noreferrer">
                      {t.officialCitation} · {t.page} {citation.page}
                    </a>
                  </blockquote>
                ))}
              </article>
            );
          })}
          <Assistant evaluationId={query.data.id} opportunityId={id} />
          <small>
            {t.version} {query.data.version} · {displayDate(query.data.evaluated_at, hi, t.unknown)}{' '}
            · {t.preliminary}
          </small>
        </div>
      )}
    </section>
  );
}
