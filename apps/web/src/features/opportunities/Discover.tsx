import { useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { useInfiniteQuery, useQuery } from '@tanstack/react-query';
import {
  ArrowLeft,
  ArrowRight,
  BookOpen,
  BriefcaseBusiness,
  CalendarDays,
  Check,
  ChevronDown,
  ExternalLink,
  HeartPulse,
  Info,
  Leaf,
  MapPin,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Sprout,
  Wrench,
} from 'lucide-react';
import { useFacets, useStrings } from '../../app/App';
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
  const facets = useFacets();
  const [params, setParams] = useSearchParams();
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
    queryKey: ['opportunities', q, category, state, district],
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
          },
        },
      });
      return data ?? fail(error);
    },
    getNextPageParam: (last) => last.next_cursor ?? undefined,
  });
  const items = query.data?.pages.flatMap((p) => p.items) ?? [];
  const total = query.data?.pages[0]?.total;
  return (
    <div className="page discovery">
      <section className="hero">
        <div className="hero-copy">
          <span className="eyebrow">
            <span className="tiny-spark">✳</span>
            {t.eyebrow}
          </span>
          <h1>
            {t.title}
            <br />
            <em>{t.titleAccent}</em>
          </h1>
          <p>{t.subtitle}</p>
          <form
            className="search-box"
            onSubmit={(e) => {
              e.preventDefault();
              filter('q', search);
            }}
          >
            <Search size={20} />
            <input
              aria-label={t.search}
              placeholder={t.search}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <button type="submit" aria-label={t.search}>
              <ArrowRight size={19} />
            </button>
          </form>
          <div className="hero-note">
            <ShieldCheck size={14} />
            <span>{t.coverage}</span>
            <span className="separator">·</span>
            <span>{t.foundation}</span>
          </div>
        </div>
        <div className="hero-art" aria-hidden="true">
          <div className="orbit orbit-one" />
          <div className="orbit orbit-two" />
          <div className="art-line line-one" />
          <div className="art-line line-two" />
          <div className="art-tile tile-book">
            <BookOpen size={34} />
            <span>LEARN</span>
          </div>
          <div className="art-tile tile-leaf">
            <Leaf size={32} />
          </div>
          <div className="art-tile tile-business">
            <BriefcaseBusiness size={30} />
            <span>GROW</span>
          </div>
          <div className="art-center">
            <span className="art-spark">✳</span>
          </div>
          <span className="art-dot dot-one" />
          <span className="art-dot dot-two" />
          <div className="art-tag">
            <span>
              <Check size={11} />
            </span>{' '}
            Possibility, connected.
          </div>
        </div>
      </section>
      <div className="notice">
        <Info size={18} />
        <div>
          <strong>{t.notice}</strong>
          <span>{t.noticeText}</span>
        </div>
      </div>
      <div className="catalogue-heading">
        <div>
          <h2>{t.browseHeading}</h2>
          <p>{t.browseSub}</p>
        </div>
        <span className="result-count">
          {total ?? '—'} {t.results}
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
                {categories[c]?.label || c}
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
          <button className="text-button" onClick={() => setParams({})}>
            {t.reset}
          </button>
        )}
      </div>
      {query.isPending ? (
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
          <button className="button" onClick={() => setParams({})}>
            {t.reset}
          </button>
        </div>
      ) : (
        <>
          <div className="card-grid">
            {items.map((item) => (
              <Card key={item.id} item={item} />
            ))}
          </div>
          {query.hasNextPage && (
            <button
              className="button load-more"
              disabled={query.isFetchingNextPage}
              onClick={() => void query.fetchNextPage()}
            >
              {query.isFetchingNextPage ? t.loading : 'Load more'}
              <ArrowRight size={16} />
            </button>
          )}
        </>
      )}
      <div className="catalogue-footnote">
        <ShieldCheck size={16} />
        <p>{t.coverageText}</p>
      </div>
    </div>
  );
}
function Card({ item }: { item: Opportunity }) {
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
      <span className="category-name">{category.label}</span>
      <h3>
        <Link to={`/opportunities/${item.id}`}>{item.title}</Link>
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
        <Link to={`/opportunities/${item.id}`} aria-label={`${t.detail}: ${item.title}`}>
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
  const { id } = useParams();
  const t = useStrings();
  const query = useQuery({
    queryKey: ['opportunity', id],
    queryFn: async () => {
      const { data, error } = await api.GET('/v1/opportunities/{identifier}', {
        params: { path: { identifier: id! } },
      });
      return data ?? fail(error);
    },
  });
  const item = query.data;
  const sourceUrl = safeUrl(item?.source_url ?? null);
  return (
    <div className="page detail-page">
      <Link to="/discover" className="back-link">
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
                </section>
                <section className="panel">
                  <h2>{t.requirements}</h2>
                  <p>{t.notEstablished}</p>
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
                    v{item.version} · {item.status.replaceAll('_', ' ')}
                  </dd>
                  <dt>{t.firstSeen}</dt>
                  <dd>
                    {new Date(item.first_seen_at).toLocaleDateString(
                      document.documentElement.lang,
                      { year: 'numeric', month: 'short', day: 'numeric' },
                    )}
                  </dd>
                  <dt>{t.lastCheck}</dt>
                  <dd>{item.source.last_successful_check_at || t.notChecked}</dd>
                  <dt>{t.lastReview}</dt>
                  <dd>{item.last_verified_at || t.notVerified}</dd>
                </dl>
              </aside>
            </div>
          </>
        )
      )}
    </div>
  );
}
