import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { useStrings } from '../../app/App';
import { api, fail } from '../../lib/api/client';
import type { components } from '../../lib/api/schema';
type Review = components['schemas']['ReviewView'];
type Decision = components['schemas']['ReviewWrite']['decision'];
export function Admin() {
  const t = useStrings();
  const cache = useQueryClient();
  const [selected, setSelected] = useState<string | null>(null);
  const account = useQuery({
    queryKey: ['admin-account'],
    retry: false,
    queryFn: async () => {
      const { data, error } = await api.GET('/v1/me');
      return data ?? fail(error);
    },
  });
  const enabled = account.data?.is_admin === true;
  const sources = useQuery({
    queryKey: ['admin-sources'],
    enabled,
    queryFn: async () => {
      const { data, error } = await api.GET('/v1/admin/sources');
      return data ?? fail(error);
    },
  });
  const reviews = useQuery({
    queryKey: ['admin-reviews'],
    enabled,
    queryFn: async () => {
      const { data, error } = await api.GET('/v1/admin/reviews');
      return data ?? fail(error);
    },
  });
  const runs = useQuery({
    queryKey: ['admin-runs'],
    enabled,
    queryFn: async () => {
      const { data, error } = await api.GET('/v1/admin/ingestion-runs');
      return data ?? fail(error);
    },
  });
  const ingest = useMutation({
    mutationFn: async (key: string) => {
      const { data, error } = await api.POST('/v1/admin/sources/{key}/ingest', {
        params: { path: { key } },
      });
      return data ?? fail(error);
    },
    onSuccess: () => {
      void cache.invalidateQueries({ queryKey: ['admin-reviews'] });
      void cache.invalidateQueries({ queryKey: ['admin-runs'] });
      void cache.invalidateQueries({ queryKey: ['admin-sources'] });
    },
  });
  return (
    <div className="page">
      <div className="page-heading">
        <span className="eyebrow">{t.adminOnly}</span>
        <h1>{t.adminReview}</h1>
        <p>{t.adminIntro}</p>
      </div>
      {account.isPending ? (
        <p>{t.loading}</p>
      ) : !enabled ? (
        <section className="panel" role="alert">
          <p>{account.isError ? account.error.message : t.adminRequired}</p>
          <Link to="/settings" className="button">
            {t.signIn}
          </Link>
        </section>
      ) : (
        <>
          <section className="panel">
            <h2>{t.officialSources}</h2>
            {sources.isError && <p role="alert">{sources.error.message}</p>}
            {sources.data?.map((source) => (
              <div key={source.key} className="source-row">
                <div>
                  <strong>{source.name}</strong>
                  <p>
                    <a href={source.context_url} target="_blank" rel="noreferrer">
                      {t.officialIndex}
                    </a>{' '}
                    · {source.status}
                  </p>
                  <small>{source.last_checked_at || t.notChecked}</small>
                </div>
                <button
                  className="button"
                  disabled={ingest.isPending}
                  onClick={() => ingest.mutate(source.key)}
                >
                  {ingest.isPending ? t.ingesting : t.ingestSource}
                </button>
              </div>
            ))}
            {ingest.isError && <p role="alert">{ingest.error.message}</p>}
            {ingest.data && (
              <p role="status">
                {ingest.data.status} · {ingest.data.diagnostic_code || t.noDiagnostic}
              </p>
            )}
          </section>
          <section className="panel">
            <h2>{t.reviewQueue}</h2>
            {reviews.isError && <p role="alert">{reviews.error.message}</p>}
            {reviews.isPending ? (
              <p>{t.loading}</p>
            ) : reviews.data?.length === 0 ? (
              <p>{t.noCandidates}</p>
            ) : (
              reviews.data?.map((candidate) => (
                <button
                  className="review-row"
                  key={candidate.id}
                  onClick={() => setSelected(candidate.id)}
                >
                  <span>{candidate.title}</span>
                  <small>
                    v{candidate.version} · {candidate.publication_state}
                  </small>
                </button>
              ))
            )}
          </section>
          {selected && <CandidateEditor key={selected} id={selected} />}
          <section className="panel">
            <h2>{t.ingestionHistory}</h2>
            {runs.isError && <p role="alert">{runs.error.message}</p>}
            {runs.data?.map((run) => (
              <div className="run-row" key={run.id}>
                <strong>{run.status}</strong>
                <span>{run.diagnostic_code || t.noDiagnostic}</span>
                <small>
                  {new Date(run.created_at).toLocaleString()} · {run.provider} · {run.model}
                </small>
              </div>
            ))}
          </section>
        </>
      )}
    </div>
  );
}
function CandidateEditor({ id }: { id: string }) {
  const t = useStrings();
  const cache = useQueryClient();
  const [text, setText] = useState('');
  const [note, setNote] = useState('');
  const [flags, setFlags] = useState(false);
  const [complete, setComplete] = useState(false);
  const query = useQuery({
    queryKey: ['admin-review', id],
    queryFn: async () => {
      const { data, error } = await api.GET('/v1/admin/reviews/{identifier}', {
        params: { path: { identifier: id } },
      });
      return data ?? fail(error);
    },
  });
  useEffect(() => {
    if (query.data) {
      setText(JSON.stringify(query.data.candidate, null, 2));
      setFlags(false);
      setComplete(false);
      setNote('');
    }
  }, [query.data]);
  const mutate = useMutation({
    mutationFn: async (decision: Decision) => {
      const candidate = JSON.parse(text) as Review['candidate'];
      const { data, error } = await api.POST('/v1/admin/reviews/{identifier}', {
        params: { path: { identifier: id } },
        body: {
          decision,
          candidate,
          note,
          expected_hash: query.data!.candidate_hash,
          acknowledge_flags: flags,
          source_completeness_confirmed: complete,
        },
      });
      return data ?? fail(error);
    },
    onSuccess: (data) => {
      cache.setQueryData(['admin-review', id], data);
      void cache.invalidateQueries({ queryKey: ['admin-reviews'] });
      void cache.invalidateQueries({ queryKey: ['opportunities'] });
      void cache.invalidateQueries({ queryKey: ['facets'] });
    },
  });
  if (query.isPending)
    return (
      <section className="panel" role="status">
        {t.loading}
      </section>
    );
  if (query.isError)
    return (
      <section className="panel" role="alert">
        {query.error.message}
      </section>
    );
  const candidate = query.data!;
  let edited = candidate.candidate;
  try {
    edited = JSON.parse(text) as Review['candidate'];
  } catch {
    /* Advanced editor errors are reported on save. */
  }
  const patch = (values: Partial<Review['candidate']>) =>
    setText(JSON.stringify({ ...edited, ...values }, null, 2));
  const hi = document.documentElement.lang === 'hi';
  return (
    <section className="panel candidate-editor">
      <p>
        {t.extractionProvider}: {candidate.extraction_provider ?? t.unknown} ·{' '}
        {candidate.extraction_model ?? t.unknown} · {candidate.extractor_version ?? t.unknown}
      </p>
      <p>
        {t.tokenUsage}: {JSON.stringify(candidate.extraction_usage ?? {})}
      </p>
      <span className="eyebrow">
        {candidate.publication_state} · v{candidate.version}
      </span>
      <h2>{candidate.title}</h2>
      <p>
        {t.snapshotHash}: <code>{candidate.content_hash}</code>
      </p>
      <div className="review-summary-grid">
        <div>
          <span>{hi ? 'शर्तें' : 'Conditions'}</span>
          <strong>{edited.requirements?.length ?? 0}</strong>
        </div>
        <div>
          <span>{hi ? 'दस्तावेज़ प्रमाण' : 'Document citations'}</span>
          <strong>
            {edited.document_evidence?.length ?? 0} / {edited.required_documents?.length ?? 0}
          </strong>
        </div>
        <div>
          <span>{t.reviewFlags}</span>
          <strong>{edited.review_flags?.length ?? 0}</strong>
        </div>
      </div>
      <section className="panel structured-correction">
        <h3>{hi ? 'स्रोत-आधारित सुधार' : 'Source-backed corrections'}</h3>
        <p>
          {hi
            ? 'संशोधन मसौदे में सहेजें। उद्धरणों का मिलान सहेजते समय होता है।'
            : 'Save corrections as a draft. Each evidence passage is checked against the captured page on save.'}
        </p>
        <label className="field">
          {hi ? 'शीर्षक' : 'Title'}
          <input
            value={edited.title}
            maxLength={300}
            onChange={(e) => patch({ title: e.target.value })}
          />
        </label>
        <label className="field">
          {hi ? 'सारांश' : 'Summary'}
          <textarea
            value={edited.summary}
            maxLength={3000}
            onChange={(e) => patch({ summary: e.target.value })}
          />
        </label>
        {(edited.requirements ?? []).map((req, i) => (
          <details key={i}>
            <summary>
              {i + 1}. {req.description}
              <small>
                {' '}
                · {req.kind ?? 'eligibility'} · {req.application_context ?? 'all'}
              </small>
            </summary>
            <label className="field">
              {hi ? 'शर्त का विवरण' : 'Condition description'}
              <textarea
                value={req.description}
                onChange={(e) =>
                  patch({
                    requirements: edited.requirements!.map((r, j) =>
                      j === i ? { ...r, description: e.target.value } : r,
                    ),
                  })
                }
              />
            </label>
            <div className="form-grid">
              <label className="field">
                {hi ? 'श्रेणी' : 'Policy category'}
                <select
                  value={req.kind ?? 'eligibility'}
                  onChange={(e) =>
                    patch({
                      requirements: edited.requirements!.map((r, j) =>
                        j === i ? { ...r, kind: e.target.value as typeof req.kind } : r,
                      ),
                    })
                  }
                >
                  {[
                    'eligibility',
                    'document',
                    'procedure',
                    'renewal',
                    'selection',
                    'interpretation',
                  ].map((v) => (
                    <option key={v}>{v}</option>
                  ))}
                </select>
              </label>
              <label className="field">
                {hi ? 'आवेदन संदर्भ' : 'Application context'}
                <select
                  value={req.application_context ?? 'all'}
                  onChange={(e) =>
                    patch({
                      requirements: edited.requirements!.map((r, j) =>
                        j === i
                          ? {
                              ...r,
                              application_context: e.target.value as typeof req.application_context,
                            }
                          : r,
                      ),
                    })
                  }
                >
                  {['all', 'fresh', 'renewal'].map((v) => (
                    <option key={v}>{v}</option>
                  ))}
                </select>
              </label>
            </div>
            <label className="field">
              {hi ? 'सटीक स्रोत अंश' : 'Exact source passage'}
              <textarea
                value={req.evidence.passage}
                onChange={(e) =>
                  patch({
                    requirements: edited.requirements!.map((r, j) =>
                      j === i ? { ...r, evidence: { ...r.evidence, passage: e.target.value } } : r,
                    ),
                  })
                }
              />
            </label>
            <a href={req.evidence.source_url} target="_blank" rel="noreferrer">
              {t.originalDocument} · {t.page} {req.evidence.page}
            </a>
            <details>
              <summary>{hi ? 'टाइप किया गया नियम' : 'Typed rule'}</summary>
              <pre>{JSON.stringify(req.rule, null, 2)}</pre>
            </details>
          </details>
        ))}
        <h3>{hi ? 'दस्तावेज़-विशिष्ट प्रमाण' : 'Document-specific evidence'}</h3>
        {edited.document_evidence?.map((d) => (
          <details key={d.document}>
            <summary>{d.document}</summary>
            <blockquote>{d.evidence.passage}</blockquote>
            <a href={d.evidence.source_url} target="_blank" rel="noreferrer">
              {t.originalDocument} · {t.page} {d.evidence.page}
            </a>
          </details>
        ))}
      </section>
      <div className="review-columns">
        <div>
          <h3>{t.sourceEvidence}</h3>
          {candidate.pages.map((page, i) => (
            <details key={i}>
              <summary>
                {t.page} {page.page} ·{' '}
                <a href={page.source_url} target="_blank" rel="noreferrer">
                  {t.originalDocument}
                </a>
              </summary>
              <pre>{page.text}</pre>
            </details>
          ))}
        </div>
        <div>
          <h3>{t.versionDiff}</h3>
          <p>{candidate.changes.join(', ') || t.noChanges}</p>
          {candidate.published && (
            <details>
              <summary>{t.previousPublished}</summary>
              <pre>{JSON.stringify(candidate.published, null, 2)}</pre>
            </details>
          )}
          <h3>{t.reviewFlags}</h3>
          <ul>
            {(candidate.candidate.review_flags ?? []).map((flag) => (
              <li key={flag}>{flag}</li>
            ))}
          </ul>
          <h3>{t.missingFields}</h3>
          <p>{(candidate.candidate.missing_fields ?? []).join(', ') || t.noneReported}</p>
          <h3>{t.extractedConditions}</h3>
          {(candidate.candidate.requirements ?? []).map((req, i) => (
            <details key={i}>
              <summary>{req.description}</summary>
              <pre>{JSON.stringify(req.rule, null, 2)}</pre>
              <blockquote>
                {req.evidence.passage}
                <p>
                  {req.evidence.basis} · {req.evidence.language} · {t.page} {req.evidence.page}
                </p>
              </blockquote>
            </details>
          ))}
        </div>
      </div>
      <details className="advanced-editor">
        <summary>{hi ? 'उन्नत JSON संपादक' : 'Advanced JSON correction editor'}</summary>
        <label className="field">
          {t.correctCandidate}
          <textarea
            aria-label={t.correctCandidate}
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={18}
            spellCheck={false}
            disabled={candidate.publication_state !== 'draft'}
          />
        </label>
        <p>{t.correctionHelp}</p>
      </details>
      <label className="field">
        {t.reviewNote}
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          maxLength={2000}
          required
        />
      </label>
      <label className="checkbox-field">
        <input type="checkbox" checked={flags} onChange={(e) => setFlags(e.target.checked)} />
        {t.acknowledgeFlags}
      </label>
      <label className="checkbox-field">
        <input type="checkbox" checked={complete} onChange={(e) => setComplete(e.target.checked)} />
        {t.confirmSource}
      </label>
      <div className="review-actions">
        {(['correct', 'request_review', 'reject', 'approve'] as const).map((action) => (
          <button
            key={action}
            className="button"
            disabled={
              mutate.isPending ||
              candidate.publication_state !== 'draft' ||
              !note.trim() ||
              (action === 'approve' &&
                (!complete || ((candidate.candidate.review_flags ?? []).length > 0 && !flags)))
            }
            onClick={() => mutate.mutate(action)}
          >
            {t.decisions[action]}
          </button>
        ))}
      </div>
      {mutate.isError && <p role="alert">{mutate.error.message}</p>}
      {mutate.isSuccess && (
        <p role="status">
          {t.reviewSaved} · {mutate.data.publication_state}
        </p>
      )}
      <details>
        <summary>{t.reviewAudit}</summary>
        {candidate.history.map((event, i) => (
          <pre key={i}>{JSON.stringify(event, null, 2)}</pre>
        ))}
      </details>
    </section>
  );
}
