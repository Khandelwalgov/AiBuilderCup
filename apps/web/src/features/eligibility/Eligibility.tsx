import { AssessmentLedger } from '../../components/Atlas';
import { Assistant } from '../assistant/Assistant';
import { useState } from 'react';
import { useLanguage } from '../../app/App';
import { useMutation } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { CheckCircle2, CircleHelp, XCircle } from 'lucide-react';
import { useStrings } from '../../app/App';
import { api, fail } from '../../lib/api/client';
export function Eligibility({ id }: { id: string }) {
  const t = useStrings();
  const hi = useLanguage() === 'hi';
  const [applicationType, setApplicationType] = useState<'fresh' | 'renewal' | ''>('');
  const query = useMutation({
    mutationFn: async () => {
      const { data, error } = await api.POST('/v1/opportunities/{identifier}/evaluate', {
        params: { path: { identifier: id } },
        body: { subject: { kind: 'person' }, application_type: applicationType || null },
      });
      return data ?? fail(error);
    },
  });
  return (
    <section className="panel evaluation">
      <span className="eyebrow">{t.preliminary}</span>
      <h2>{t.checkEligibility}</h2>
      <p>{t.evaluationIntro}</p>
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
        <button className="button" onClick={() => query.mutate()} disabled={query.isPending}>
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
                {req.result.kind === 'evidence_gap' && (
                  <strong className="evidence-gap">{t.evidenceGap}</strong>
                )}
                {req.result.facts.length > 0 && (
                  <details>
                    <summary>{t.factsUsed}</summary>
                    {req.result.facts.map((f, i) => (
                      <p key={`${f.id}-${i}`}>
                        {f.key}: {String(f.value)} · {f.origin} · {f.verification}
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
                        {child.missing.length > 0 && ` (${child.missing.join(', ')})`}
                      </p>
                    ))}
                  </details>
                )}
                {req.next_steps.length > 0 && (
                  <ul>
                    {req.next_steps.map((step) => (
                      <li key={step}>{step}</li>
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
          <Assistant evaluationId={query.data.id} />
          <small>
            {t.version} {query.data.version} · {new Date(query.data.evaluated_at).toLocaleString()}{' '}
            · {t.preliminary}
          </small>
        </div>
      )}
    </section>
  );
}
