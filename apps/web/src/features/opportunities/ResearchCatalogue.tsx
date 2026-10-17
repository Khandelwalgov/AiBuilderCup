import { useEffect, useState } from 'react';
import { useInfiniteQuery, useQuery } from '@tanstack/react-query';
import { useParams, useSearchParams } from 'react-router-dom';
import { ArrowRight, ExternalLink } from 'lucide-react';
import { useLanguage } from '../../app/App';
import { ContextLink } from '../../app/subject-context';
import { api, fail } from '../../lib/api/client';
import type { components } from '../../lib/api/schema';

type Card = components['schemas']['ResearchCard'];
const copy = {
  en: {
    title: 'Explore Government Opportunities',
    catalogue: 'Programmes and awards',
    archive: 'Historical and procurement archive',
    substantive_document: 'Substantive official document',
    procurement_notice: 'Procurement notice · open round not established',
    source_overview: 'Official overview · details need confirmation',
    charter_summary: 'Citizen Charter summary · later rules unverified',
    directory_reference: 'Directory name only · terms unavailable',
    unassessed: 'Source strength not assessed',
    scheme: 'Programme',
    scheme_component: 'Programme component',
    award: 'Award',
    tender: 'Procurement notice',
    institutional_admission: 'Institutional admission',
    document: 'Read captured document',
    pages: 'Pages',
    researchCountNote:
      'Programme components are counted separately. These are research records, not approved eligibility policies.',

    notice: 'Source-backed research · Eligibility not yet verified',
    explanation:
      'Browse real programmes and procurement notices without completing a profile. These informational listings do not establish eligibility, available funding or an open application round.',
    search: 'Search government research listings',
    category: 'All research categories',
    jurisdiction: 'All jurisdictions',
    availability: 'All availability states',
    applications: 'All application states',
    count: 'research listings',
    unknown: 'Availability unknown',
    verified_current: 'Current availability verified',
    historical: 'Historical record',
    potentially_expired: 'Continuation not established',
    open: 'Cited application window open',
    closed: 'Closed / historical application',
    not_established: 'Application window not established',
    education: 'Scholarships and education',
    welfare: 'Welfare and financial assistance',
    business: 'MSME and business',
    procurement: 'Procurement and tenders',
    healthcare: 'Healthcare',
    employment: 'Employment and skilling',
    loading: 'Loading government opportunities…',
    empty: 'No research listings match these filters.',
    reset: 'Clear research filters',
    more: 'Load more research listings',
    inspect: 'Read opportunity and evidence',
    source: 'Original official source',
    application: 'Official application information',
    deadline: 'Cited closing date',
    unknownDeadline: 'No verified closing date',
    limitations: 'What remains unknown',
    evidence: 'Source evidence',
    captured: 'Read captured text',
    ocr: 'Local OCR derivative · not independently verified',
    original: 'Captured source text · not an eligibility decision',
    back: 'Back to government opportunities',
    error: 'Government research is temporarily unavailable.',
    retry: 'Try again',
  },
  hi: {
    title: 'सरकारी अवसर देखें',
    catalogue: 'योजनाएँ और पुरस्कार',
    archive: 'पुरानी और खरीद सूचनाओं का अभिलेख',
    substantive_document: 'विस्तृत आधिकारिक दस्तावेज़',
    procurement_notice: 'खरीद सूचना · खुले आवेदन की पुष्टि नहीं',
    source_overview: 'आधिकारिक सारांश · विवरण की पुष्टि बाकी',
    charter_summary: 'नागरिक चार्टर सारांश · बाद के नियम असत्यापित',
    directory_reference: 'केवल निर्देशिका का नाम · शर्तें उपलब्ध नहीं',
    unassessed: 'स्रोत का आकलन बाकी',
    scheme: 'योजना',
    scheme_component: 'योजना का घटक',
    award: 'पुरस्कार',
    tender: 'खरीद सूचना',
    institutional_admission: 'संस्थागत प्रवेश',
    document: 'संग्रहित दस्तावेज़ पढ़ें',
    pages: 'पृष्ठ',
    researchCountNote:
      'योजना के घटक अलग गिने जाते हैं। ये शोध रिकॉर्ड हैं, स्वीकृत पात्रता नीतियाँ नहीं।',

    notice: 'आधिकारिक स्रोत पर आधारित शोध · पात्रता अभी सत्यापित नहीं',
    explanation:
      'प्रोफ़ाइल पूरा किए बिना वास्तविक योजनाएँ और खरीद सूचनाएँ देखें। ये शोध रिकॉर्ड पात्रता, उपलब्ध बजट या खुले आवेदन की पुष्टि नहीं करते।',
    search: 'सरकारी शोध अवसर खोजें',
    category: 'सभी शोध श्रेणियाँ',
    jurisdiction: 'सभी क्षेत्र',
    availability: 'उपलब्धता की सभी स्थितियाँ',
    applications: 'आवेदन की सभी स्थितियाँ',
    count: 'शोध अवसर',
    unknown: 'उपलब्धता ज्ञात नहीं',
    verified_current: 'वर्तमान उपलब्धता सत्यापित',
    historical: 'पुराना रिकॉर्ड',
    potentially_expired: 'जारी रहने की पुष्टि नहीं',
    open: 'उद्धृत आवेदन अवधि खुली है',
    closed: 'बंद / पुराना आवेदन',
    not_established: 'आवेदन अवधि स्थापित नहीं',
    education: 'छात्रवृत्ति और शिक्षा',
    welfare: 'कल्याण और आर्थिक सहायता',
    business: 'एमएसएमई और व्यवसाय',
    procurement: 'खरीद और निविदाएँ',
    healthcare: 'स्वास्थ्य',
    employment: 'रोज़गार और कौशल',
    loading: 'सरकारी अवसर लोड हो रहे हैं…',
    empty: 'इन फ़िल्टर के लिए कोई शोध अवसर नहीं मिला।',
    reset: 'शोध फ़िल्टर हटाएँ',
    more: 'और शोध अवसर देखें',
    inspect: 'अवसर और साक्ष्य पढ़ें',
    source: 'मूल आधिकारिक स्रोत',
    application: 'आधिकारिक आवेदन जानकारी',
    deadline: 'स्रोत में अंतिम तिथि',
    unknownDeadline: 'सत्यापित अंतिम तिथि नहीं',
    limitations: 'क्या अभी अज्ञात है',
    evidence: 'स्रोत साक्ष्य',
    captured: 'संग्रहित पाठ पढ़ें',
    ocr: 'स्थानीय OCR पाठ · स्वतंत्र सत्यापन नहीं हुआ',
    original: 'संग्रहित स्रोत पाठ · पात्रता का निर्णय नहीं',
    back: 'सरकारी अवसरों पर वापस जाएँ',
    error: 'सरकारी शोध अभी उपलब्ध नहीं है।',
    retry: 'फिर प्रयास करें',
  },
};
function useCopy() {
  return copy[useLanguage() === 'hi' ? 'hi' : 'en'];
}
function labels(t: ReturnType<typeof useCopy>, value: string) {
  return (t as Record<string, string>)[value] || value;
}

function ResearchCard({ item }: { item: Card }) {
  const t = useCopy();
  return (
    <article className="panel research-opportunity-card">
      <span className="eyebrow">{labels(t, item.category)}</span>
      <h3>
        <ContextLink to={`/research-opportunities/${item.id}`}>{item.title}</ContextLink>
      </h3>
      <p className="research-verification">{t.notice}</p>
      <p>
        {labels(t, item.kind)} · {labels(t, item.evidence_strength || 'unassessed')}
      </p>
      <p>{item.summary}</p>
      <div className="research-documents">
        {(item.documents || []).map((doc) => (
          <div key={doc.snapshot_id}>
            <ContextLink to={`/government-sources?source=${doc.snapshot_id}&page=${doc.pages[0]}`}>
              {t.document} · {t.pages} {doc.pages.join(', ')}
            </ContextLink>
            <blockquote>{doc.excerpt}…</blockquote>
          </div>
        ))}
      </div>
      {item.benefit && <p>{item.benefit}</p>}
      <p>
        <strong>
          {item.jurisdiction}
          {item.district ? ` · ${item.district}` : ''}
        </strong>
      </p>
      <p className="notice">
        {labels(t, item.availability)} · {labels(t, item.application_status)}
      </p>
      <p>{item.availability_note}</p>
      <p>{item.closes_on ? `${t.deadline}: ${item.closes_on}` : t.unknownDeadline}</p>
      <div className="research-card-links">
        <ContextLink to={`/research-opportunities/${item.id}`}>
          {t.inspect} <ArrowRight size={15} />
        </ContextLink>
        <a href={item.source_url} target="_blank" rel="noreferrer">
          {t.source} <ExternalLink size={14} />
        </a>
      </div>
    </article>
  );
}

export function ResearchCatalogue() {
  const t = useCopy();
  const [params, setParams] = useSearchParams();
  const q = params.get('research_q') || '';
  const view = params.get('research_view') === 'archive' ? 'archive' : 'catalogue';
  const [text, setText] = useState(q);
  useEffect(() => setText(q), [q]);
  const category = params.get('research_category') || '';
  const jurisdiction = params.get('research_jurisdiction') || '';
  const availability = params.get('research_availability') || '';
  const applications = params.get('research_applications') || '';
  const filters = useQuery({
    queryKey: ['research-facets'],
    queryFn: async () => {
      const { data, error } = await api.GET('/v1/research-opportunities/facets');
      return data ?? fail(error);
    },
  });
  const query = useInfiniteQuery({
    queryKey: [
      'research-opportunities',
      view,
      q,
      category,
      jurisdiction,
      availability,
      applications,
    ],
    initialPageParam: undefined as string | undefined,
    queryFn: async ({ pageParam }) => {
      const { data, error } = await api.GET('/v1/research-opportunities', {
        params: {
          query: {
            q,
            view,
            category,
            jurisdiction,
            availability: availability ? (availability as Card['availability']) : undefined,
            application_status: applications
              ? (applications as Card['application_status'])
              : undefined,
            cursor: pageParam,
            limit: 9,
          },
        },
      });
      return data ?? fail(error);
    },
    getNextPageParam: (last) => last.next_cursor ?? undefined,
  });
  function filter(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (
      (key === 'research_category' && value === 'procurement') ||
      (key === 'research_availability' && value === 'historical') ||
      (key === 'research_applications' && value === 'closed')
    )
      next.set('research_view', 'archive');
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next);
  }
  const items = query.data?.pages.flatMap((p) => p.items) ?? [];
  return (
    <section id="government-opportunities" className="research-catalogue" aria-label={t.title}>
      <div className="catalogue-heading">
        <div>
          <h2>{t.title}</h2>
          <p>{t.explanation}</p>
        </div>
        <span className="result-count">
          {query.data?.pages[0].total ?? '—'} {t.count}
        </span>
      </div>
      <p className="notice">{t.notice}</p>
      <div className="research-card-links" role="group" aria-label={t.title}>
        <button aria-pressed={view === 'catalogue'} onClick={() => filter('research_view', '')}>
          {t.catalogue} ({filters.data?.catalogue_total ?? '—'})
        </button>
        <button
          aria-pressed={view === 'archive'}
          onClick={() => filter('research_view', 'archive')}
        >
          {t.archive} ({filters.data?.archive_total ?? '—'})
        </button>
      </div>
      <p>{t.researchCountNote}</p>
      <form
        className="research-search search-box"
        onSubmit={(e) => {
          e.preventDefault();
          filter('research_q', text);
        }}
      >
        <input
          aria-label={t.search}
          value={text}
          placeholder={t.search}
          onChange={(e) => setText(e.target.value)}
        />
        <button type="submit">{useLanguage() === 'hi' ? 'खोजें' : 'Search'}</button>
      </form>
      <div className="filters" aria-label={t.title}>
        <select
          aria-label={t.category}
          value={category}
          onChange={(e) => filter('research_category', e.target.value)}
        >
          <option value="">{t.category}</option>
          {filters.data?.categories.map((c) => (
            <option key={c} value={c}>
              {labels(t, c)}
            </option>
          ))}
        </select>
        <select
          aria-label={t.jurisdiction}
          value={jurisdiction}
          onChange={(e) => filter('research_jurisdiction', e.target.value)}
        >
          <option value="">{t.jurisdiction}</option>
          {filters.data?.jurisdictions.map((c) => (
            <option key={c}>{c}</option>
          ))}
        </select>
        <select
          aria-label={t.availability}
          value={availability}
          onChange={(e) => filter('research_availability', e.target.value)}
        >
          <option value="">{t.availability}</option>
          {(['unknown', 'verified_current', 'historical', 'potentially_expired'] as const).map(
            (c) => (
              <option key={c} value={c}>
                {labels(t, c)} ({filters.data?.availability[c] ?? 0})
              </option>
            ),
          )}
        </select>
        <select
          aria-label={t.applications}
          value={applications}
          onChange={(e) => filter('research_applications', e.target.value)}
        >
          <option value="">{t.applications}</option>
          {(['open', 'closed', 'not_established'] as const).map((c) => (
            <option key={c} value={c}>
              {labels(t, c)}
            </option>
          ))}
        </select>
        {(q || category || jurisdiction || availability || applications) && (
          <button
            className="text-button"
            onClick={() => {
              const next = new URLSearchParams(params);
              for (const key of [...next.keys()]) if (key.startsWith('research_')) next.delete(key);
              setParams(next);
            }}
          >
            {t.reset}
          </button>
        )}
      </div>
      {query.isPending ? (
        <p role="status">{t.loading}</p>
      ) : query.isError ? (
        <div role="alert">
          <p>{t.error}</p>
          <button onClick={() => void query.refetch()}>{t.retry}</button>
        </div>
      ) : items.length ? (
        <div className="card-grid">
          {items.map((item) => (
            <ResearchCard key={item.id} item={item} />
          ))}
        </div>
      ) : (
        <p role="status">{t.empty}</p>
      )}
      {query.hasNextPage && (
        <button
          className="button load-more"
          disabled={query.isFetchingNextPage}
          onClick={() => void query.fetchNextPage()}
        >
          {query.isFetchingNextPage ? t.loading : t.more}
        </button>
      )}
    </section>
  );
}

export function ResearchDetail() {
  const t = useCopy();
  const { id } = useParams();
  const query = useQuery({
    queryKey: ['research-opportunity', id],
    retry: false,
    queryFn: async () => {
      const { data, error } = await api.GET('/v1/research-opportunities/{identifier}', {
        params: { path: { identifier: id! } },
      });
      return data ?? fail(error);
    },
  });
  if (query.isPending) return <p role="status">{t.loading}</p>;
  if (query.isError)
    return (
      <div className="page" role="alert">
        <p>{t.error}</p>
        <button onClick={() => void query.refetch()}>{t.retry}</button>
      </div>
    );
  const item = query.data;
  const citations = [
    ...new Map(item.citations.map((c) => [`${c.snapshot_id}:${c.page}:${c.passage}`, c])).values(),
  ];
  return (
    <div className="page research-detail">
      <ContextLink to="/discover#government-opportunities">← {t.back}</ContextLink>
      <header className="page-heading">
        <h1>{item.title}</h1>
        <p>{item.authority || item.jurisdiction}</p>
      </header>
      <p className="notice">{t.notice}</p>
      <p>{item.summary}</p>
      {item.benefit && <p>{item.benefit}</p>}
      <p>
        <strong>
          {labels(t, item.availability)} · {labels(t, item.application_status)}
        </strong>
      </p>
      <p>{item.availability_note}</p>
      <p>{item.closes_on ? `${t.deadline}: ${item.closes_on}` : t.unknownDeadline}</p>
      {item.apply_url && (
        <a href={item.apply_url} target="_blank" rel="noreferrer">
          {t.application}
        </a>
      )}
      <section className="panel">
        <h2>{t.limitations}</h2>
        <ul>
          {item.limitations.map((value, i) => (
            <li key={i}>{value}</li>
          ))}
        </ul>
      </section>
      <section className="panel">
        <h2>{t.evidence}</h2>
        {citations.map((c, i) => {
          const source = item.sources.find((s) => s.snapshot_id === c.snapshot_id)!;
          return (
            <blockquote key={i}>
              <p>{c.passage}</p>
              <a
                href={
                  source.source_url.toLowerCase().includes('.pdf')
                    ? `${source.source_url}#page=${c.page}`
                    : source.source_url
                }
                target="_blank"
                rel="noreferrer"
              >
                {t.source} · {c.page}
              </a>
            </blockquote>
          );
        })}
      </section>
      {item.sources.map((source) => (
        <section className="panel" key={source.snapshot_id}>
          <a href={source.source_url} target="_blank" rel="noreferrer">
            {t.source}
          </a>
          <p className="research-source-hash">SHA-256: {source.content_hash}</p>
          <ContextLink to={`/government-sources?source=${source.snapshot_id}`}>
            {t.captured}
          </ContextLink>
          {source.pages.map((page) => (
            <details key={page.page}>
              <summary>
                {t.captured} · {page.page} · {page.basis === 'offline_ocr' ? t.ocr : t.original}
              </summary>
              <pre className="research-source-text">{page.text}</pre>
            </details>
          ))}
        </section>
      ))}
    </div>
  );
}
