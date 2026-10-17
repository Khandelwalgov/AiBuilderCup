import { SearchModes, type Mode } from '../intelligence/SearchModes';
import { Recommendations } from '../intelligence/Recommendations';
import { documentStatus, documentsHref, useDocumentNeeds } from '../documents/Documents';
import { displayLabel, displayDate } from '../../i18n/format';
import { ContextLink as Link, useSubject } from '../../app/subject-context';
import { Eligibility } from '../eligibility/Eligibility';
import { useEffect, useState } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { useInfiniteQuery, useQuery } from '@tanstack/react-query';
import {
  ArrowLeft,
  ArrowRight,
  BookOpen,
  BriefcaseBusiness,
  CalendarDays,
  ChevronDown,
  ExternalLink,
  HeartPulse,
  Info,
  MapPin,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Sprout,
  Wrench,
} from 'lucide-react';
import { useFacets, useStrings, useLanguage } from '../../app/App';
import { api, fail } from '../../lib/api/client';
import type { components } from '../../lib/api/schema';
type Opportunity = components['schemas']['OpportunityView'];
const categories: Record<string, { label: string; icon: typeof BookOpen; tone: string }> = {
  education: { label: 'Education', icon: BookOpen, tone: 'lavender' },
  business: { label: 'Business', icon: BriefcaseBusiness, tone: 'peach' },
  employment: { label: 'Employment', icon: Wrench, tone: 'blue' },
  agriculture: { label: 'Agriculture', icon: Sprout, tone: 'sage' },
  healthcare: { label: 'Healthcare', icon: HeartPulse, tone: 'rose' },
  procurement: { label: 'Procurement', icon: BriefcaseBusiness, tone: 'sand' },
};
export function Discover() {
  const t = useStrings();
  const hi = useLanguage() === 'hi';
  const [params, setParams] = useSearchParams();
  const context = useSubject();
  const mode = (
    ['me', 'family', 'member', 'business', 'explore'].includes(params.get('mode') || '')
      ? params.get('mode')
      : context.authenticated
        ? 'me'
        : 'explore'
  ) as Mode;
  const nationalParam = params.get('national');
  const [includeNational, setIncludeNational] = useState(nationalParam !== 'false');
  useEffect(() => setIncludeNational(nationalParam !== 'false'), [nationalParam]);
  const development = params.get('development') === 'true';
  const facets = useFacets(development);
  const q = params.get('q') || '';
  const category = params.get('category') || '';
  const state = params.get('state') || '';
  const district = params.get('district') || '';
  const [search, setSearch] = useState(q);
  useEffect(() => setSearch(q), [q]);
  function filter(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    if (key === 'state') next.delete('district');
    setParams(next);
  }
  const query = useInfiniteQuery({
    enabled: mode === 'explore',
    queryKey: ['opportunities', q, category, state, district, development, includeNational],
    initialPageParam: undefined as string | undefined,
    queryFn: async ({ pageParam }) => {
      const { data, error } = await api.GET('/v1/opportunities', {
        params: {
          query: {
            q: q || undefined,
            category: category || undefined,
            state: state || undefined,
            district: district || undefined,
            cursor: pageParam,
            limit: 6,
            development,
            include_national: includeNational,
          },
        },
      });
      return data ?? fail(error);
    },
    getNextPageParam: (last) => last.next_cursor ?? undefined,
  });
  const items = mode === 'explore' ? (query.data?.pages.flatMap((p) => p.items) ?? []) : [];
  const total = query.data?.pages[0]?.total;
  return (
    <div className="page discovery">
      <header className="research-header">
        <div>
          <span className="eyebrow">{hi ? 'स्रोत-आधारित शोध' : 'SOURCE-BACKED RESEARCH'}</span>
          <h1>{hi ? 'अवसर खोजें' : 'Discover opportunities'}</h1>
          <p>
            {hi
              ? 'आपके सहेजे गए प्रोफ़ाइल के अनुसार समीक्षित अवसर अपने आप दिखते हैं। खोज और फ़िल्टर वैकल्पिक हैं।'
              : 'Reviewed opportunities load automatically from your saved profile. Search and filters are optional.'}
          </p>
        </div>
        <span className="catalogue-state">
          <ShieldCheck size={17} />
          {development ? t.synthetic : t.publishedCatalogue}
        </span>
      </header>
      <SearchModes mode={mode} onChange={(value) => filter('mode', value)} />
      <form
        className="research-search search-box"
        onSubmit={(e) => {
          e.preventDefault();
          filter('q', search);
        }}
      >
        <Search size={22} />
        <input
          aria-label={t.search}
          placeholder={t.search}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <button type="submit" aria-label={t.search}>
          {hi ? 'खोजें' : 'Search'}
          <ArrowRight size={17} />
        </button>
      </form>
      <div className="notice">
        <Info size={18} />
        <div>
          <strong>{development ? t.notice : t.publishedCatalogue}</strong>
          <span>{development ? t.noticeText : t.publishedNotice}</span>
          {development ? (
            <Link to="/discover">{t.publicView}</Link>
          ) : (
            import.meta.env.VITE_ENABLE_DEVELOPMENT_CATALOGUE === 'true' && (
              <Link to="/discover?development=true">{t.developmentView}</Link>
            )
          )}
        </div>
      </div>
      {(state || district) && (
        <div className="geography-note">
          <label className="checkbox-field">
            <input
              type="checkbox"
              checked={includeNational}
              onChange={(e) => {
                setIncludeNational(e.target.checked);
                filter('national', e.target.checked ? 'true' : 'false');
              }}
            />
            {hi ? 'राष्ट्रीय अवसर भी दिखाएँ' : 'Include nationally applicable opportunities'}
          </label>
          <p>
            {hi
              ? 'यह केवल खोज का फ़िल्टर है। निवास, मूल निवास और अध्ययन स्थान की पात्रता अलग शर्तें हैं।'
              : 'This is a browsing filter. Residence, domicile and place of study are separate eligibility conditions.'}
          </p>
        </div>
      )}
      <div className="catalogue-heading">
        <div>
          <h2>
            {mode === 'explore' ? t.browseHeading : hi ? 'आपके लिए अवसर' : 'Opportunities for you'}
          </h2>
          <p>
            {mode === 'explore'
              ? t.browseSub
              : hi
                ? 'आपकी जानकारी और प्रकाशित शर्तों पर आधारित।'
                : 'Based on your saved facts and published requirements.'}
          </p>
        </div>
        <span className="result-count">
          {mode === 'explore'
            ? `${total ?? '—'} ${t.results}`
            : hi
              ? 'संदर्भ के अनुसार सुझाव'
              : 'Context recommendations'}
        </span>
      </div>
      <div className="filters" aria-label={t.filters}>
        <SlidersHorizontal size={17} />
        <label>
          <span className="sr-only">{t.category}</span>
          <select value={category} onChange={(e) => filter('category', e.target.value)}>
            <option value="">{t.category}</option>
            {facets.data?.categories.map((c) => (
              <option key={c} value={c}>
                {displayLabel(c, hi)}
              </option>
            ))}
          </select>
          <ChevronDown size={14} />
        </label>
        <label>
          <MapPin size={15} />
          <span className="sr-only">{t.state}</span>
          <select value={state} onChange={(e) => filter('state', e.target.value)}>
            <option value="">{t.state}</option>
            {facets.data?.states.map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
          <ChevronDown size={14} />
        </label>
        <label>
          <span className="sr-only">{t.district}</span>
          <select value={district} onChange={(e) => filter('district', e.target.value)}>
            <option value="">{t.district}</option>
            {facets.data?.districts.map((d) => (
              <option key={d}>{d}</option>
            ))}
          </select>
          <ChevronDown size={14} />
        </label>
        {(q || category || state || district) && (
          <button
            className="text-button"
            onClick={() => setParams(development ? { development: 'true' } : {})}
          >
            {t.reset}
          </button>
        )}
      </div>
      {mode !== 'explore' && <Recommendations mode={mode} />}
      {mode !== 'explore' ? null : query.isPending ? (
        <div className="card-grid" role="status" aria-label={t.loading}>
          {[1, 2, 3].map((i) => (
            <div className="skeleton" key={i}>
              <div />
              <div />
              <div />
            </div>
          ))}
          <span className="sr-only">{t.loading}</span>
        </div>
      ) : query.isError ? (
        <ErrorState message={query.error.message} retry={() => void query.refetch()} />
      ) : items.length === 0 ? (
        <div className="empty-state">
          <Search size={30} />
          <h2>{t.empty}</h2>
          <p>{t.emptyText}</p>
          <button
            className="button"
            onClick={() => setParams(development ? { development: 'true' } : {})}
          >
            {t.reset}
          </button>
        </div>
      ) : (
        <>
          <div className="card-grid">
            {items.map((item) => (
              <Card key={item.id} item={item} development={development} />
            ))}
          </div>
          {query.hasNextPage && (
            <button
              className="button load-more"
              disabled={query.isFetchingNextPage}
              onClick={() => void query.fetchNextPage()}
            >
              {query.isFetchingNextPage ? t.loading : hi ? 'और देखें' : 'Load more'}
              <ArrowRight size={16} />
            </button>
          )}
        </>
      )}
      <div className="catalogue-footnote">
        <span>
          {facets.data?.total ?? '—'} {t.publishedCount}
        </span>
        <ShieldCheck size={16} />
        <p>{t.coverageText}</p>
      </div>
    </div>
  );
}
function Card({ item, development }: { item: Opportunity; development: boolean }) {
  const hi = useLanguage() === 'hi';
  const t = useStrings();
  const category = categories[item.category] ?? {
    label: item.category,
    icon: BookOpen,
    tone: 'sage',
  };
  const Icon = category.icon;
  return (
    <article className="opportunity-card">
      <div className="card-top">
        <span className={`category-icon ${category.tone}`}>
          <Icon size={23} />
        </span>
        <span className="tag">
          {item.is_synthetic ? t.synthetic : item.status.replaceAll('_', ' ')}
        </span>
      </div>
      <span className="category-name">{displayLabel(item.category, hi)}</span>
      <h3>
        <Link to={`/opportunities/${item.id}${development ? '?development=true' : ''}`}>
          {item.title}
        </Link>
      </h3>
      <p className="card-summary">{item.summary}</p>
      <div className="card-meta">
        <span>
          <MapPin size={14} />
          {[item.district, item.state].filter(Boolean).join(', ') || t.national}
        </span>
        <span>
          <CalendarDays size={14} />
          {item.closes_on || t.unknownDeadline}
        </span>
      </div>
      <div className="card-bottom">
        <span>{item.is_synthetic ? 'DEVELOPMENT FIXTURE' : item.issuer || t.unknown}</span>
        <Link
          to={`/opportunities/${item.id}${development ? '?development=true' : ''}`}
          aria-label={`${t.detail}: ${item.title}`}
        >
          <ArrowRight size={19} />
        </Link>
      </div>
    </article>
  );
}
function ErrorState({ message, retry }: { message: string; retry: () => void }) {
  const t = useStrings();
  return (
    <div className="empty-state" role="alert">
      <Info size={30} />
      <h2>{t.error}</h2>
      <p>{message}</p>
      <button className="button" onClick={retry}>
        {t.retry}
      </button>
    </div>
  );
}
function safeUrl(value: string | null) {
  if (!value) return null;
  try {
    const u = new URL(value);
    return u.protocol === 'https:' ? u.href : null;
  } catch {
    return null;
  }
}
export function Detail() {
  const documentNeeds = useDocumentNeeds();
  const hi = useLanguage() === 'hi';
  const { id } = useParams();
  const [params] = useSearchParams();
  const development = params.get('development') === 'true';
  const t = useStrings();
  const query = useQuery({
    queryKey: ['opportunity', id, development],
    queryFn: async () => {
      const { data, error } = await api.GET('/v1/opportunities/{identifier}', {
        params: { path: { identifier: id! }, query: { development } },
      });
      return data ?? fail(error);
    },
  });
  const item = query.data;
  const sourceUrl = safeUrl(item?.source_url ?? null);
  const applyUrl = safeUrl(item?.apply_url ?? null);
  return (
    <div className="page detail-page">
      <Link to={development ? '/discover?development=true' : '/discover'} className="back-link">
        <ArrowLeft size={16} />
        {t.back}
      </Link>
      {query.isPending ? (
        <div className="empty-state" role="status">
          {t.loading}
        </div>
      ) : query.isError ? (
        <ErrorState message={query.error.message} retry={() => void query.refetch()} />
      ) : (
        item && (
          <>
            <div className="detail-heading">
              <span className="tag">
                {item.is_synthetic ? t.synthetic : item.status.replaceAll('_', ' ')}
              </span>
              <h1>{item.title}</h1>
              <p>{item.summary}</p>
              <div className="detail-meta">
                <span>
                  <MapPin size={16} />
                  {[item.district, item.state].filter(Boolean).join(', ') || t.national}
                </span>
                <span>
                  <CalendarDays size={16} />
                  {item.closes_on || t.unknownDeadline}
                </span>
              </div>
            </div>
            {item.is_synthetic && (
              <div className="notice">
                <Info size={20} />
                <div>
                  <strong>{t.notice}</strong>
                  <span>{t.noticeText}</span>
                </div>
              </div>
            )}
            {item.source.status === 'source_unreachable' ||
            item.source.status === 'needs_review' ? (
              <div className="notice">
                <p>{t.sourceWarning}</p>
              </div>
            ) : null}
            {(!item.is_synthetic || (development && item.publication_state === 'published')) && (
              <Eligibility id={item.id} />
            )}
            <div className="detail-grid">
              <div>
                <section className="panel">
                  <h2>{t.summary}</h2>
                  <p>{item.benefits || t.noBenefits}</p>
                  <dl>
                    <dt>{t.issuer}</dt>
                    <dd>{item.issuer || t.unknown}</dd>
                    <dt>{t.deadline}</dt>
                    <dd>{item.closes_on || t.unknownDeadline}</dd>
                  </dl>
                  {applyUrl && (
                    <a className="button" href={applyUrl} target="_blank" rel="noreferrer">
                      {t.officialApplication}
                      <ExternalLink size={14} />
                    </a>
                  )}
                  {item.restrictions.length > 0 && (
                    <>
                      <h3>{t.restrictions}</h3>
                      <ul>
                        {item.restrictions.map((r) => (
                          <li key={r}>{r}</li>
                        ))}
                      </ul>
                    </>
                  )}
                  {item.required_documents.length > 0 && (
                    <>
                      <h3>{t.requiredDocuments}</h3>
                      <ul>
                        {item.required_documents.map((d) => (
                          <li key={d}>{d}</li>
                        ))}
                      </ul>
                    </>
                  )}
                  {item.field_evidence.length > 0 && (
                    <details>
                      <summary>{t.sourceEvidence}</summary>
                      {item.field_evidence.map((entry, i) => (
                        <blockquote key={i}>
                          <strong>{entry.field}</strong>
                          <p>{entry.citation.passage}</p>
                          <a href={entry.citation.source_url} target="_blank" rel="noreferrer">
                            {t.officialCitation} · {t.page} {entry.citation.page}
                          </a>
                          <p>
                            {entry.citation.language} · {entry.citation.basis}
                          </p>
                        </blockquote>
                      ))}
                    </details>
                  )}
                  {item.review_flags.length > 0 && (
                    <details>
                      <summary>{t.reviewFlags}</summary>
                      <ul>
                        {item.review_flags.map((f) => (
                          <li key={f}>{f}</li>
                        ))}
                      </ul>
                    </details>
                  )}
                  {item.missing_fields.length > 0 && (
                    <details>
                      <summary>{t.missingFields}</summary>
                      <p>{item.missing_fields.join(', ')}</p>
                    </details>
                  )}
                </section>
                <section className="panel">
                  <h2>{t.requirements}</h2>
                  {item.requirements.length === 0 ? (
                    <p>{t.notEstablished}</p>
                  ) : (
                    item.requirements.map((req) => (
                      <div
                        className="source-requirement"
                        id={`source-requirement-${req.id}`}
                        key={req.id}
                      >
                        <h3>{req.description}</h3>
                        {documentNeeds.data
                          ?.filter((n) => n.requirement_id === req.id)
                          .map((n) => (
                            <div className="notice" key={n.requirement_id}>
                              <p>{documentStatus(n.documentary_status, hi)}</p>
                              <Link className="button secondary" to={documentsHref(req.id)}>
                                {hi ? 'दस्तावेज़ जोड़ें या देखें' : 'Add or view document'}
                              </Link>
                            </div>
                          ))}
                        {req.citations.map((citation, i) => (
                          <blockquote key={i}>
                            <p>{citation.passage}</p>
                            <a href={citation.source_url} target="_blank" rel="noreferrer">
                              {t.officialCitation} · {t.page} {citation.page}
                            </a>
                          </blockquote>
                        ))}
                      </div>
                    ))
                  )}
                </section>
                <section className="panel">
                  <h2>{t.geography}</h2>
                  <p>{t.geographyNote}</p>
                </section>
              </div>
              <aside className="panel provenance">
                <ShieldCheck size={25} />
                <h2>{t.source}</h2>
                <p>{item.is_synthetic ? t.noSource : item.source.name}</p>
                {sourceUrl && (
                  <a className="external" href={sourceUrl} target="_blank" rel="noreferrer">
                    {t.source}
                    <ExternalLink size={14} />
                  </a>
                )}
                <dl>
                  <dt>{t.version}</dt>
                  <dd>
                    v{item.version} · {displayLabel(item.status, hi)}
                  </dd>
                  <dt>{t.firstSeen}</dt>
                  <dd>
                    {new Date(item.first_seen_at).toLocaleDateString(
                      document.documentElement.lang,
                      { year: 'numeric', month: 'short', day: 'numeric' },
                    )}
                  </dd>
                  <dt>{t.lastCheck}</dt>
                  <dd>{displayDate(item.source.last_successful_check_at, hi, t.notChecked)}</dd>
                  <dt>{t.lastReview}</dt>
                  <dd>{displayDate(item.last_verified_at, hi, t.notVerified)}</dd>
                </dl>
              </aside>
            </div>
          </>
        )
      )}
    </div>
  );
}
