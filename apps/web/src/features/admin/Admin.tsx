import { displayLabel, displayDate } from '../../i18n/format';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { useDirtyForm } from '../../app/dirty-forms';
import { useParams, useNavigate } from 'react-router-dom';
import { ContextLink as Link } from '../../app/subject-context';
import { CapturedReader } from '../../components/CapturedReader';
import { useEffect, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useStrings, useLanguage } from '../../app/App';
import { api, fail } from '../../lib/api/client';
import type { components } from '../../lib/api/schema';
type Review = components['schemas']['ReviewView'];
type Decision = components['schemas']['ReviewWrite']['decision'];
export function Admin() {
  const t = useStrings();
  const hi = useLanguage() === 'hi';
  const [pendingSource, setPendingSource] = useState<components['schemas']['SourceItem'] | null>(
    null,
  );
  const cache = useQueryClient();
  const { candidateId } = useParams();
  const navigate = useNavigate();
  const selected = candidateId ?? null;
  const [reviewSearch, setReviewSearch] = useState('');
  const account = useQuery({
    queryKey: ['admin-account'],
    retry: false,
    queryFn: async () => {
      const { data, error } = await api.GET('/v1/me');
      return data ?? fail(error);
    },
  });
  const enabled = account.data?.is_admin === true;
  const intelligence = useQuery({
    queryKey: ['admin-intelligence-status'],
    enabled,
    retry: false,
    queryFn: async () => {
      const { data, error } = await api.GET('/v1/admin/intelligence-status');
      return data ?? fail(error);
    },
  });
  const sources = useQuery({
    queryKey: ['admin-sources'],
    enabled,
    queryFn: async () => {
      const { data, error } = await api.GET('/v1/admin/sources');
      return data ?? fail(error);
    },
  });
  const reviews = useQuery({
    queryKey: ['admin-reviews', reviewSearch],
    enabled,
    queryFn: async () => {
      const { data, error } = await api.GET('/v1/admin/reviews', {
        params: { query: { q: reviewSearch, limit: 100 } },
      });
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
  const permission = useQuery({
    queryKey: ['ingestion-settings'],
    enabled,
    retry: false,
    queryFn: async () => {
      const { data, error } = await api.GET('/v1/admin/ingestion-settings');
      return data ?? fail(error);
    },
  });
  const ingest = useMutation({
    mutationFn: async (key: string) => {
      const { data, error } = await api.POST('/v1/admin/sources/{key}/ingest', {
        params: { path: { key } },
        body: {
          expected_provider: permission.data!.provider as 'gemini' | 'openai',
          expected_model: permission.data!.model,
          confirm_potential_paid_use: true,
        },
      });
      return data ?? fail(error);
    },
    onSuccess: () => {
      setPendingSource(null);
      void cache.invalidateQueries({ queryKey: ['admin-reviews'] });
      void cache.invalidateQueries({ queryKey: ['admin-runs'] });
      void cache.invalidateQueries({ queryKey: ['admin-sources'] });
      void cache.invalidateQueries({ queryKey: ['admin-intelligence-status'] });
    },
  });
  return (
    <div className="page">
      {pendingSource && (
        <ConfirmDialog
          title={hi ? 'स्रोत जाँच शुरू करें?' : 'Start source ingestion?'}
          cancel={hi ? 'रद्द करें' : 'Cancel'}
          confirm={hi ? 'स्रोत जाँच की पुष्टि करें' : 'Confirm source ingestion'}
          busy={ingest.isPending}
          disabled={!permission.data?.live_enabled}
          onCancel={() => setPendingSource(null)}
          onConfirm={() => ingest.mutate(pendingSource.key)}
        >
          <h3>{pendingSource.name}</h3>
          <dl>
            <dt>{hi ? 'प्रदाता / मॉडल' : 'Provider / model'}</dt>
            <dd>
              {permission.data
                ? `${permission.data.provider} / ${permission.data.model}`
                : t.loading}
            </dd>
            <dt>{hi ? 'मौजूदा मसौदे' : 'Existing drafts'}</dt>
            <dd>{pendingSource.draft_count ?? (hi ? 'अज्ञात' : 'Unknown')}</dd>
            <dt>{hi ? 'ऑपरेटर अनुमति' : 'Operator permission'}</dt>
            <dd>
              {permission.data?.live_enabled
                ? hi
                  ? 'सक्षम'
                  : 'Enabled'
                : hi
                  ? 'अक्षम — कोई कॉल नहीं होगी'
                  : 'Disabled — no call will be made'}
            </dd>
            <dt>{hi ? 'कॉन्फ़िगर किया परीक्षण बजट' : 'Configured test budget'}</dt>
            <dd>
              {permission.data?.test_budget_usd == null
                ? hi
                  ? 'निर्धारित नहीं'
                  : 'Not configured'
                : `US$${permission.data.test_budget_usd}`}
            </dd>
          </dl>
          <p>
            {hi
              ? 'भुगतान वाली AI केवल स्पष्ट रूप से अधिकृत, बजट-सीमित पृष्ठभूमि कार्यों में उपलब्ध है। इस पृष्ठ से खर्च की अनुमति नहीं दी जा सकती।'
              : 'Paid AI requires an explicitly authorized background worker with durable spending limits. This page cannot authorize paid inference.'}
          </p>
          <p>
            {hi
              ? 'अधिकतम एक मॉडल प्रयास। परिणाम केवल समीक्षा योग्य मसौदा होगा। त्रुटि पर स्वचालित प्रदाता बदलाव या इस संवाद से पुनः प्रयास नहीं होगा।'
              : 'At most one model attempt. Output is a reviewable draft only. Errors do not switch providers or automatically resubmit this dialog.'}
          </p>
          {permission.isError && <p role="alert">{permission.error.message}</p>}
          {ingest.isError && <p role="alert">{ingest.error.message}</p>}
        </ConfirmDialog>
      )}
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
          {intelligence.data && (
            <section
              className="panel"
              aria-label={hi ? 'स्रोत प्रसंस्करण स्थिति' : 'Corpus processing status'}
            >
              <dl>
                <dt>
                  {hi
                    ? 'संग्रहित दस्तावेज़ / मसौदे / प्रकाशित अवसर'
                    : 'Captured documents / drafts / published opportunities'}
                </dt>
                <dd>
                  {intelligence.data.unique_document_hashes} /{' '}
                  {intelligence.data.draft_opportunities} /{' '}
                  {intelligence.data.published_real_opportunities}
                </dd>
                <dt>
                  {hi
                    ? 'OCR / प्रसंस्करण बाकी / मानव समीक्षा'
                    : 'OCR / processing backlog / human escalations'}
                </dt>
                <dd>
                  {intelligence.data.documents_requiring_ocr} /{' '}
                  {intelligence.data.processing_backlog} / {intelligence.data.human_escalations}
                </dd>
                <dt>
                  {hi ? 'स्वतंत्र रूप से सत्यापित उम्मीदवार' : 'Independently verified candidates'}
                </dt>
                <dd>{intelligence.data.independently_verified_candidates}</dd>
                <dt>{hi ? 'अंतिम सफल संग्रहण' : 'Last successful collection'}</dt>
                <dd>
                  {displayDate(
                    intelligence.data.last_successful_collection,
                    hi,
                    hi ? 'अभी नहीं चला' : 'Not run',
                  )}
                </dd>
                <dt>{hi ? 'AI आरक्षण / दर्ज खर्च' : 'AI reserved / recorded expenditure'}</dt>
                <dd>
                  US${intelligence.data.reserved_inference_usd} / US$
                  {intelligence.data.recorded_inference_usd}
                </dd>
              </dl>
            </section>
          )}
          {intelligence.error && <p role="alert">{intelligence.error.message}</p>}
          <div className="review-console">
            <aside className="review-queue">
              {' '}
              <section className="panel">
                <h2>{t.reviewQueue}</h2>
                <label>
                  {hi ? 'शीर्षक या जारीकर्ता से मसौदे छाँटें' : 'Filter drafts by title or issuer'}
                  <input
                    value={reviewSearch}
                    onChange={(event) => setReviewSearch(event.target.value)}
                  />
                </label>
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
                      onClick={() => navigate(`/admin/reviews/${candidate.id}`)}
                    >
                      <span>{candidate.title}</span>
                      <small>
                        v{candidate.version} · {displayLabel(candidate.publication_state, hi)}
                      </small>
                    </button>
                  ))
                )}
              </section>
            </aside>
            <div className="review-main">
              {selected ? (
                <CandidateEditor key={selected} id={selected} />
              ) : (
                <section className="empty-state">
                  <h2>{hi ? 'समीक्षा के लिए मसौदा चुनें' : 'Choose a candidate to review'}</h2>
                  <p>
                    {hi
                      ? 'मूल स्रोत और मानव निर्णय के बीच एक स्पष्ट कार्यक्षेत्र।'
                      : 'A focused workspace between source evidence and a human decision.'}
                  </p>
                </section>
              )}
            </div>
          </div>
          <details className="admin-tools">
            <summary>
              {hi ? 'स्रोत संचालन और रन इतिहास' : 'Source operations and run history'}
            </summary>{' '}
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
                    onClick={() => {
                      ingest.reset();
                      setPendingSource(source);
                    }}
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
              <h2>{t.ingestionHistory}</h2>
              {runs.isError && <p role="alert">{runs.error.message}</p>}
              {runs.data?.map((run) => (
                <div className="run-row" key={run.id}>
                  <strong>{displayLabel(run.status, hi)}</strong>
                  <span>{run.diagnostic_code || t.noDiagnostic}</span>
                  <small>
                    {displayDate(run.created_at, hi, t.unknown)} · {run.provider} · {run.model}
                  </small>
                </div>
              ))}
            </section>
          </details>
        </>
      )}
    </div>
  );
}
function CandidateEditor({ id }: { id: string }) {
  const t = useStrings();
  const hi = useLanguage() === 'hi';
  const cache = useQueryClient();
  const [sourcePage, setSourcePage] = useState(0);
  const [conditionIndex, setConditionIndex] = useState(0);
  const [decisionConfirmation, setDecisionConfirmation] = useState<Decision | null>(null);
  const editorRef = useRef<HTMLElement>(null);
  const [text, setText] = useState('');
  const [note, setNote] = useState('');
  const [flags, setFlags] = useState(false);
  const [complete, setComplete] = useState(false);
  const baseline = useRef<string | null>(null);
  const baselineHash = useRef('');
  const signature = JSON.stringify({ text, note, flags, complete });
  const dirty = baseline.current !== null && signature !== baseline.current;
  useDirtyForm(dirty);
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
    if (query.data && !dirty) {
      baselineHash.current = query.data.candidate_hash;
      baseline.current = JSON.stringify({
        text: JSON.stringify(query.data.candidate, null, 2),
        note: '',
        flags: false,
        complete: false,
      });
      setText(JSON.stringify(query.data.candidate, null, 2));
      setFlags(false);
      setComplete(false);
      setNote('');
    }
  }, [query.data, dirty]);
  const mutate = useMutation({
    mutationFn: async (decision: Decision) => {
      const candidate = JSON.parse(text) as Review['candidate'];
      const { data, error } = await api.POST('/v1/admin/reviews/{identifier}', {
        params: { path: { identifier: id } },
        body: {
          decision,
          candidate,
          note,
          expected_hash: baselineHash.current,
          acknowledge_flags: flags,
          source_completeness_confirmed: complete,
        },
      });
      return data ?? fail(error);
    },
    onSuccess: (data) => {
      baseline.current = null;
      cache.setQueryData(['admin-review', id], data);
      void cache.invalidateQueries({ queryKey: ['admin-reviews'] });
      void cache.invalidateQueries({ queryKey: ['opportunities'] });
      void cache.invalidateQueries({ queryKey: ['facets'] });
      void cache.invalidateQueries({ queryKey: ['plan'] });
      void cache.invalidateQueries({ queryKey: ['dashboard-summary'] });
      void cache.invalidateQueries({ queryKey: ['hybrid-search'] });
      void cache.invalidateQueries({ queryKey: ['scenario-base'] });
      void cache.invalidateQueries({ queryKey: ['admin-intelligence-status'] });
    },
  });
  useEffect(() => {
    if (query.isSuccess) editorRef.current?.scrollIntoView({ block: 'start' });
  }, [id, query.isSuccess]);
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

  const locate = (citation: { source_url: string; page: number }) =>
    setSourcePage(
      candidate.pages.findIndex(
        (p) => p.source_url === citation.source_url && p.page === citation.page,
      ),
    );
  return (
    <section ref={editorRef} className="panel candidate-editor">
      {decisionConfirmation && (
        <ConfirmDialog
          title={
            decisionConfirmation === 'approve'
              ? hi
                ? 'समीक्षित नीति प्रकाशित करें?'
                : 'Publish the reviewed policy?'
              : hi
                ? 'यह मसौदा अस्वीकार करें?'
                : 'Reject this draft?'
          }
          confirm={t.decisions[decisionConfirmation]}
          cancel={hi ? 'रद्द करें' : 'Cancel'}
          busy={mutate.isPending}
          onCancel={() => setDecisionConfirmation(null)}
          onConfirm={() => {
            mutate.mutate(decisionConfirmation, { onSuccess: () => setDecisionConfirmation(null) });
          }}
        >
          <h3>{candidate.title}</h3>
          <p>
            {decisionConfirmation === 'approve'
              ? hi
                ? 'आप स्रोत की पूर्णता, संशोधनों और प्रत्येक नियम की जिम्मेदार मानव समीक्षा की पुष्टि कर रहे हैं। AI ने इसे मंजूरी नहीं दी है।'
                : 'You are confirming substantive human review of source completeness, amendments and every requirement. AI has not approved this policy.'
              : hi
                ? 'यह अस्वीकृति समीक्षा इतिहास में दर्ज होगी।'
                : 'This rejection will be recorded in review history.'}{' '}
            {hi ? 'संस्करण' : 'Version'} {candidate.version}
          </p>
          <p>{note}</p>
          {mutate.isError && <p role="alert">{mutate.error.message}</p>}
        </ConfirmDialog>
      )}
      <p>
        {t.extractionProvider}: {candidate.extraction_provider ?? t.unknown} ·{' '}
        {candidate.extraction_model ?? t.unknown} · {candidate.extractor_version ?? t.unknown}
      </p>
      <p>
        {t.tokenUsage}: {JSON.stringify(candidate.extraction_usage ?? {})}
      </p>
      {candidate.processing_review && (
        <details>
          <summary>
            {hi
              ? 'प्रसंस्करण और स्वतंत्र समीक्षा का विवरण'
              : 'Processing and independent review findings'}
          </summary>
          <pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>
            {JSON.stringify(candidate.processing_review, null, 2)}
          </pre>
        </details>
      )}
      <span className="eyebrow">
        {displayLabel(candidate.publication_state, hi)} · v{candidate.version}
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
      <div className="review-workbench">
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
          <label className="field condition-picker">
            {hi ? 'समीक्षा के लिए शर्त चुनें' : 'Choose a condition to review'}
            <select
              value={conditionIndex}
              onChange={(e) => {
                const index = Number(e.target.value);
                setConditionIndex(index);
                const citation = edited.requirements?.[index]?.evidence;
                if (citation) locate(citation);
              }}
            >
              {edited.requirements?.map((req, i) => (
                <option key={i} value={i}>
                  {i + 1}. {req.description}
                </option>
              ))}
            </select>
          </label>
          {(edited.requirements ?? [])
            .map((req, i) => ({ req, i }))
            .filter(({ i }) => i === conditionIndex)
            .map(({ req, i }) => (
              <details key={i} open>
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
                                  application_context: e.target
                                    .value as typeof req.application_context,
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
                          j === i
                            ? { ...r, evidence: { ...r.evidence, passage: e.target.value } }
                            : r,
                        ),
                      })
                    }
                  />
                </label>
                <button
                  type="button"
                  className="field-followup"
                  onClick={() => locate(req.evidence)}
                >
                  {hi ? 'कैप्चर पृष्ठ देखें' : 'Inspect captured page'} {req.evidence.page}
                </button>
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
              <button type="button" className="field-followup" onClick={() => locate(d.evidence)}>
                {hi ? 'कैप्चर पृष्ठ देखें' : 'Inspect captured page'} {d.evidence.page}
              </button>
              <a href={d.evidence.source_url} target="_blank" rel="noreferrer">
                {t.originalDocument} · {t.page} {d.evidence.page}
              </a>
            </details>
          ))}
        </section>
        <CapturedReader pages={candidate.pages} selected={sourcePage} onSelect={setSourcePage} />
      </div>
      <div className="review-columns">
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
            onClick={() =>
              action === 'approve' || action === 'reject'
                ? setDecisionConfirmation(action)
                : mutate.mutate(action)
            }
          >
            {t.decisions[action]}
          </button>
        ))}
      </div>
      {mutate.isError && <p role="alert">{mutate.error.message}</p>}
      {mutate.isSuccess && (
        <p role="status">
          {t.reviewSaved} · {displayLabel(mutate.data.publication_state, hi)}
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
