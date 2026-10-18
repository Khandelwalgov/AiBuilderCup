import { ConditionLogic } from './ConditionLogic';
import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { useLanguage } from '../../app/App';
import { ContextLink, useSubject } from '../../app/subject-context';
import { api, fail, RequestError } from '../../lib/api/client';
import { RankedCards } from '../intelligence/Recommendations';
import type { components } from '../../lib/api/schema';

type Fact = components['schemas']['FactInput'];
type Props = {
  variant?: 'discover' | 'overview' | 'plan' | 'scenario';
  overrides?: Fact[];
  memberOverrides?: Record<string, Fact[]>;
  people?: components['schemas']['FictionalPerson'][];
  excluded?: string[];
  mode?: 'me' | 'family' | 'member' | 'business' | 'explore';
  scenario?: boolean;
};
export function ResearchGuidance(props: Props) {
  const context = useSubject();
  // Remount pagination and local controls when the selected subject changes.
  return <SubjectResearch key={`${context.key}:${props.mode}`} {...props} />;
}
function SubjectResearch({
  variant = 'discover',
  overrides = [],
  memberOverrides = {},
  people = [],
  excluded = [],
  mode,
  scenario = false,
}: Props) {
  const context = useSubject();
  const hi = useLanguage() === 'hi';
  const [params] = useSearchParams();
  const [offset, setOffset] = useState(0);
  const [q, setQ] = useState(params.get('q') || '');
  const [category, setCategory] = useState(params.get('category') || '');
  const subject = mode === 'me' ? { kind: 'person' as const, id: null } : context.subject;
  const correct =
    !mode ||
    mode === 'me' ||
    (mode === 'family' && subject.kind === 'household') ||
    (mode === 'business' && subject.kind === 'business') ||
    (mode === 'member' && subject.kind === 'person' && !!subject.id);
  const limit = variant === 'overview' ? 4 : 8;
  const query = useQuery({
    queryKey: [
      'research-guidance',
      subject,
      context.authenticated,
      overrides,
      memberOverrides,
      people,
      excluded,
      scenario,
      variant,
      offset,
      q,
      category,
    ],
    enabled:
      context.authenticated && (mode === 'me' || context.available) && correct && !context.pending,
    retry: false,
    staleTime: 0,
    refetchOnMount: 'always',
    refetchOnWindowFocus: false,
    queryFn: async () => {
      const { data, error } = await api.POST(
        variant === 'plan'
          ? '/v1/research-opportunities/plan'
          : '/v1/research-opportunities/guidance',
        {
          body: {
            subject,
            overrides,
            member_overrides: memberOverrides,
            people,
            excluded_subject_keys: excluded,
            scenario,
            limit,
            offset,
            q,
            category,
          },
        },
      );
      return data ?? fail(error);
    },
  });
  const progress = useMutation({
    mutationFn: async ({ id, status }: { id: string; status: 'pending' | 'completed' }) => {
      const { data, error } = await api.PATCH('/v1/actions/{identifier}', {
        params: { path: { identifier: id } },
        body: { status },
      });
      return data ?? fail(error);
    },
    onSuccess: () => {
      void query.refetch();
    },
  });
  if (!context.authenticated) return null;
  if ((!context.available && mode !== 'me') || !correct)
    return (
      <p className="notice" role="status">
        {hi
          ? 'पहले व्यक्ति, परिवार या व्यवसाय चुनें।'
          : 'Choose an existing person, family or business first.'}
      </p>
    );
  if (query.isError)
    return (
      <section className="notice" role="alert">
        <p>
          {query.error instanceof RequestError && query.error.code === 'profile_not_found'
            ? hi
              ? 'पहले अपना प्रोफ़ाइल बनाएँ।'
              : 'Create your profile first to personalize discovery.'
            : hi
              ? 'शोध अभी उपलब्ध नहीं है।'
              : 'Personalized research is temporarily unavailable.'}
        </p>
        <ContextLink to="/profile">{hi ? 'प्रोफ़ाइल देखें' : 'Open profile'}</ContextLink>
      </section>
    );
  const response = query.data;
  const outcome = (value: string) =>
    hi
      ? {
          satisfied: 'बताई गई जानकारी से शर्त पूरी',
          unsatisfied: 'बताई गई जानकारी में अंतर',
          unknown: 'जानकारी या पुष्टि बाकी',
          not_applicable: 'लागू नहीं',
        }[value] || value
      : {
          satisfied: 'Condition met by supplied facts',
          unsatisfied: 'Known mismatch',
          unknown: 'Unknown / confirmation needed',
          not_applicable: 'Not applicable',
        }[value] || value;
  return (
    <section
      className="research-guidance"
      aria-label={hi ? 'आपके लिए स्रोत-आधारित अवसर' : 'Personalized source-backed opportunities'}
    >
      <span className="eyebrow">
        {hi
          ? 'स्रोत-आधारित शोध · पात्रता असत्यापित'
          : 'SOURCE-BACKED RESEARCH · ELIGIBILITY NOT VERIFIED'}
      </span>
      <h2>
        {variant === 'plan'
          ? hi
            ? 'शोध और तैयारी के अगले कदम'
            : 'Research and preparation steps'
          : variant === 'scenario'
            ? hi
              ? 'इस स्थिति में शोध और शर्तें'
              : 'Research conditions in this scenario'
            : hi
              ? 'आपके लिए सरकारी अवसर'
              : 'Government opportunities for you'}
      </h2>
      <p className="notice">
        {hi
          ? 'सरकारी स्रोतों और आपकी बताई जानकारी की प्रारंभिक तुलना। आवेदन अवधि, शेष शर्तें और प्रमाण की पुष्टि बाकी है।'
          : 'Provisional comparisons of official sources and your supplied facts. Remaining conditions, documentary evidence and current application windows still need confirmation.'}{' '}
        {response?.hypothetical &&
          (hi
            ? 'कोई तथ्य या कार्य प्रगति सहेजी नहीं गई।'
            : 'No profile facts or action progress were saved.')}
      </p>
      {variant === 'discover' && (
        <div className="filter-grid">
          <label>
            {hi ? 'खोजें (वैकल्पिक)' : 'Search (optional)'}
            <input
              value={q}
              maxLength={200}
              onChange={(e) => {
                setQ(e.target.value);
                setOffset(0);
              }}
            />
          </label>
          <label>
            {hi ? 'श्रेणी' : 'Category'}
            <select
              value={category}
              onChange={(e) => {
                setCategory(e.target.value);
                setOffset(0);
              }}
            >
              <option value="">{hi ? 'सभी' : 'All'}</option>
              {[
                ['education', 'Education', 'शिक्षा'],
                ['welfare', 'Welfare', 'कल्याण'],
                ['business', 'Business', 'व्यवसाय'],
                ['employment', 'Employment', 'रोज़गार'],
                ['healthcare', 'Healthcare', 'स्वास्थ्य'],
              ].map(([v, en, h]) => (
                <option value={v} key={v}>
                  {hi ? h : en}
                </option>
              ))}
            </select>
          </label>
        </div>
      )}
      {(context.pending || query.isPending) && (
        <p role="status">
          {hi ? 'स्रोत-आधारित अवसर खोज रहे हैं…' : 'Finding source-backed opportunities…'}
        </p>
      )}
      {response && (
        <>
          <p role="status">
            {response.candidate_count}{' '}
            {hi ? 'योजना–व्यक्ति शोध परिणाम' : 'programme–subject research results'} ·{' '}
            {hi
              ? 'वर्तमान आवेदन की पुष्टि अलग है'
              : 'Current application availability is a separate check'}
          </p>
          {response.reviewed?.catalogue_count > 0 && !response.reviewed.items.length && (
            <p>
              {hi
                ? 'प्रकाशित अवसर हैं, लेकिन इस संदर्भ में आकलन नहीं हो सका।'
                : 'Published opportunities are available, but none could be assessed for this context.'}
            </p>
          )}
          {response.reviewed?.items.length > 0 && <RankedCards response={response.reviewed} />}
          {!response.items.length && (
            <p>
              {hi
                ? 'इस संदर्भ में परिणाम नहीं मिले। पूरे सार्वजनिक कैटलॉग में भी देख सकते हैं।'
                : 'No research matches this context and these filters. You can also browse the full public catalogue.'}
            </p>
          )}
          {!!response.actions?.length && (
            <section aria-label={hi ? 'शोध तैयारी के कार्य' : 'Research readiness tasks'}>
              <h3>{hi ? 'दोबारा उपयोग होने वाले तैयारी के कदम' : 'Reusable readiness steps'}</h3>
              {response.actions.map((action) => (
                <article className="panel" key={action.id}>
                  <h4>{action.title}</h4>
                  <p>
                    {action.opportunities.length}{' '}
                    {hi ? 'संबंधित घटक / अवसर' : 'affected components / opportunities'} ·{' '}
                    {action.status}
                  </p>
                  <p>
                    {hi
                      ? 'कार्य पूरा करना प्रमाण या पात्रता सत्यापित नहीं करता।'
                      : action.explanation}
                  </p>
                  {action.opportunities.map((op, i) => (
                    <p key={i}>
                      <ContextLink
                        to={`/government-sources?source=${op.snapshot_id}&page=${op.page}`}
                      >
                        {String(op.title)} · {hi ? 'पृष्ठ' : 'Page'} {String(op.page)}
                      </ContextLink>
                    </p>
                  ))}
                  {!response.hypothetical && (
                    <button
                      disabled={progress.isPending}
                      onClick={() =>
                        progress.mutate({
                          id: action.id,
                          status: action.status === 'completed' ? 'pending' : 'completed',
                        })
                      }
                    >
                      {action.status === 'completed'
                        ? hi
                          ? 'दोबारा खोलें'
                          : 'Reopen task'
                        : hi
                          ? 'अपनी तैयारी का कार्य पूरा चिह्नित करें'
                          : 'Mark my preparation task complete'}
                    </button>
                  )}
                </article>
              ))}
            </section>
          )}
          <div className="card-grid">
            {response.items.map((item) => (
              <article
                className="panel research-guide-card"
                key={`${item.subject_id}:${item.parent_key || item.listing.id}`}
              >
                <span className="eyebrow">
                  {item.subject_name} · {item.listing.jurisdiction}
                </span>
                <h3>
                  <ContextLink to={`/research-opportunities/${item.listing.id}`}>
                    {item.parent_key === 'msme-team' ? 'MSME TEAM' : item.listing.title}
                  </ContextLink>
                </h3>
                <p>{item.listing.summary}</p>
                <p>
                  <strong>{hi ? 'क्यों दिखाई दे रहा है' : 'Why it may fit'}:</strong> {item.reason}{' '}
                  {item.conditions?.length > 0 && (
                    <span>
                      {item.conditions.filter((c) => c.result.outcome === 'satisfied').length}{' '}
                      {hi
                        ? 'उद्धृत तुलनाएँ बताई जानकारी से मेल खाती हैं।'
                        : 'cited comparisons match supplied facts.'}
                    </span>
                  )}
                </p>
                <p>
                  {hi ? 'लाभ का स्रोत-विवरण' : 'Source-described benefit'}:{' '}
                  {item.listing.benefit || (hi ? 'स्थापित नहीं' : 'Not established')}
                </p>
                {!!item.components?.length && (
                  <details>
                    <summary>
                      {hi ? 'कार्यक्रम के घटक' : 'Programme components'} (
                      {item.components.length + 1})
                    </summary>
                    {[item.listing, ...item.components].map((c) => (
                      <p key={c.id}>
                        <ContextLink to={`/research-opportunities/${c.id}`}>{c.title}</ContextLink>
                      </p>
                    ))}
                  </details>
                )}
                {item.conditions?.length ? (
                  <details open={variant === 'scenario' && item.conditions.some((c) => c.changed)}>
                    <summary>
                      {hi ? 'शर्तें, अंतर और अगले कदम' : 'Conditions, gaps and next steps'}
                    </summary>
                    {item.conditions.map((c, i) => (
                      <section key={i} className="research-condition">
                        <h4>{c.title}</h4>
                        <strong>{outcome(c.result.outcome)}</strong>
                        {response.hypothetical && (
                          <p>
                            {hi ? 'वास्तविक → काल्पनिक' : 'Actual → hypothetical'}:{' '}
                            {outcome(c.baseline.outcome)} → {outcome(c.result.outcome)} ·{' '}
                            {c.changed
                              ? hi
                                ? 'बदला'
                                : 'Changed'
                              : hi
                                ? 'अपरिवर्तित'
                                : 'Unchanged'}
                          </p>
                        )}
                        <p>
                          {hi
                            ? {
                                potentially_actionable_gap: 'परिस्थिति बदलने पर तैयारी का संभव कदम',
                                information_gap: 'जानकारी की कमी',
                                evidence_gap: 'सत्यापित प्रमाण बाकी',
                                unknown_policy: 'नीति की व्याख्या अधूरी',
                                known_substantive_mismatch: 'ज्ञात शर्त में अंतर',
                                condition_met_by_supplied_facts: 'बताई जानकारी पर तुलना',
                              }[c.gap_kind] || ''
                            : c.gap_kind.replaceAll('_', ' ')}
                        </p>
                        <p>{c.result.reason}</p>
                        {c.rule.op !== 'condition' && (
                          <ConditionLogic rule={c.rule} result={c.result} hi={hi} />
                        )}
                        {c.rule.op === 'condition' && c.rule.condition?.income_definition && (
                          <ConditionLogic rule={c.rule} hi={hi} />
                        )}
                        {c.interpretation_note && <p role="note">{c.interpretation_note}</p>}
                        {!!c.exceptions?.length && (
                          <details>
                            <summary>
                              {hi ? 'स्रोत के अपवाद और सीमाएँ' : 'Source exceptions and limits'}
                            </summary>
                            <ul>
                              {c.exceptions.map((x, i) => (
                                <li key={i}>{x}</li>
                              ))}
                            </ul>
                          </details>
                        )}
                        {!!c.unresolved_conditions?.length && (
                          <details>
                            <summary>
                              {hi ? 'कौनसी शर्तें अभी अज्ञात हैं' : 'Conditions still unassessed'}
                            </summary>
                            <ul>
                              {c.unresolved_conditions.map((x, i) => (
                                <li key={i}>{x}</li>
                              ))}
                            </ul>
                          </details>
                        )}
                        {!response.hypothetical &&
                          !item.fictional &&
                          c.result.missing.map((key) => (
                            <p key={key}>
                              <ContextLink
                                to={`${item.subject_kind === 'business' ? '/businesses' : '/profile'}?kind=${item.subject_kind}${context.options.some((o) => o.id === item.subject_id) ? `&id=${item.subject_id}` : ''}&mode=${item.subject_kind === 'business' ? 'business' : context.options.some((o) => o.id === item.subject_id) ? 'member' : 'me'}&field=${key}&research_listing=${item.listing.id}&criterion=${encodeURIComponent(c.semantic)}`}
                              >
                                {hi ? 'यह जानकारी जाँचें / दें' : 'Check or provide this fact'}:{' '}
                                {key.replaceAll('_', ' ')}
                              </ContextLink>
                            </p>
                          ))}
                        {c.result.facts.map((f) => (
                          <p key={f.id}>
                            {f.key.replaceAll('_', ' ')}: {String(f.value ?? 'unknown')} ·{' '}
                            {f.origin === 'verified_document' && f.verification === 'verified'
                              ? hi
                                ? 'सत्यापित प्रमाण'
                                : 'Verified document fact'
                              : hi
                                ? 'स्वयं बताई जानकारी · प्रमाण सत्यापित नहीं'
                                : 'Supplied fact · documentary evidence unverified'}
                          </p>
                        ))}
                        {c.action && (
                          <p>
                            <strong>{hi ? 'तैयारी का कदम' : 'Readiness step'}:</strong> {c.action}{' '}
                            {hi
                              ? 'यह स्वीकृति की गारंटी नहीं है।'
                              : 'This does not guarantee admission, selection or funding.'}
                          </p>
                        )}
                        <ContextLink
                          to={`/government-sources?source=${c.snapshot_id}&page=${c.page}`}
                        >
                          {hi ? 'आधिकारिक साक्ष्य · पृष्ठ' : 'Official evidence · Page'} {c.page}
                        </ContextLink>
                        <details>
                          <summary>
                            {hi ? 'उद्धृत मूल अंश पढ़ें' : 'Read the cited original passage'}
                          </summary>
                          <blockquote>{c.passage}</blockquote>
                        </details>
                      </section>
                    ))}
                  </details>
                ) : (
                  <p>
                    {hi
                      ? 'इस रिकॉर्ड में विस्तृत शर्तों की तुलना उपलब्ध नहीं है।'
                      : 'Detailed conditions have not been mapped for comparison in this record.'}
                  </p>
                )}
                {(item.listing.documents || []).map((doc) => (
                  <p key={doc.snapshot_id}>
                    <ContextLink
                      to={`/government-sources?source=${doc.snapshot_id}&page=${doc.pages[0]}`}
                    >
                      {hi ? 'दस्तावेज़ पढ़ें · पृष्ठ' : 'Read captured document · Pages'}{' '}
                      {doc.pages.join(', ')}
                    </ContextLink>
                  </p>
                ))}
                <p>
                  {hi ? 'आवेदन अवधि' : 'Application window'}:{' '}
                  {item.listing.application_status === 'not_established'
                    ? hi
                      ? 'स्थापित नहीं'
                      : 'Not established'
                    : item.listing.application_status}
                </p>
                <a
                  href={item.listing.apply_url || item.listing.source_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  {item.listing.apply_url
                    ? hi
                      ? 'आवेदन जानकारी'
                      : 'Application information'
                    : hi
                      ? 'मूल आधिकारिक स्रोत · आवेदन पोर्टल की पुष्टि नहीं'
                      : 'Original official source · application route unconfirmed'}
                </a>
                <p>
                  <ContextLink to={`/research-opportunities/${item.listing.id}`}>
                    {hi ? 'स्रोत और विवरण' : 'Official evidence and details'}{' '}
                    <ArrowRight size={14} />
                  </ContextLink>
                </p>
              </article>
            ))}
          </div>
          {variant === 'discover' && (
            <div className="document-actions">
              <button disabled={!offset} onClick={() => setOffset(Math.max(0, offset - limit))}>
                {hi ? 'पिछले परिणाम' : 'Previous results'}
              </button>
              <button
                disabled={offset + limit >= response.candidate_count}
                onClick={() => setOffset(offset + limit)}
              >
                {hi ? 'अगले परिणाम' : 'More personalized results'}
              </button>
            </div>
          )}
          {progress.isError && <p role="alert">{progress.error.message}</p>}
        </>
      )}
      <p>
        <ContextLink to="/discover?mode=explore&research_view=catalogue">
          {hi ? 'पूरा सार्वजनिक शोध कैटलॉग देखें' : 'Browse the full public research catalogue'}{' '}
          <ArrowRight size={14} />
        </ContextLink>
      </p>
    </section>
  );
}
