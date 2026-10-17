import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { api, fail } from '../../lib/api/client';
import { ContextLink } from '../../app/subject-context';
import { useLanguage } from '../../app/App';
import { displayLabel } from '../../i18n/format';

export function GovernmentSources() {
  const hi = useLanguage() === 'hi';
  const [params, setParams] = useSearchParams();
  const identifier = params.get('source');
  const reviewStates = [
    'processing_pending',
    'needs_ocr',
    'human_review_pending',
    'reviewed_and_published',
  ] as const;
  const reviewState = reviewStates.find((value) => value === params.get('review_state')) || '';
  const listing = useQuery({
    queryKey: ['government-sources', params.toString()],
    queryFn: async () => {
      const { data, error } = await api.GET('/v1/government-sources', {
        params: {
          query: {
            q: params.get('q') || '',
            category: params.get('category') || '',
            state: params.get('state') || '',
            document_type: params.get('document_type') || '',
            format: params.get('format') || '',
            department: params.get('department') || '',
            review_state: reviewState,
            cursor: params.get('cursor') || undefined,
          },
        },
      });
      return data ?? fail(error);
    },
  });
  const detail = useQuery({
    queryKey: ['government-source', identifier],
    enabled: !!identifier,
    queryFn: async () => {
      const { data, error } = await api.GET('/v1/government-sources/{identifier}', {
        params: { path: { identifier: identifier! } },
      });
      return data ?? fail(error);
    },
  });
  const update = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    next.delete('cursor');
    next.delete('source');
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next);
  };
  return (
    <div className="page">
      <h1>{hi ? 'सरकारी स्रोत' : 'Government Sources'}</h1>
      <p>
        {hi
          ? 'संग्रहित सरकारी दस्तावेज़। संग्रहण, समीक्षा और प्रकाशित अवसर अलग अवस्थाएँ हैं।'
          : 'Captured official documents. Collection, review and publication are separate stages.'}
      </p>
      <form
        className="filters"
        onSubmit={(event) => {
          event.preventDefault();
          update('q', String(new FormData(event.currentTarget).get('q') || ''));
        }}
      >
        <label>
          {hi ? 'स्रोत का पाठ खोजें' : 'Search source text'}
          <input key={params.get('q')} name="q" defaultValue={params.get('q') || ''} />
        </label>
        <button>{hi ? 'खोजें' : 'Search sources'}</button>
        <label>
          {hi ? 'समीक्षा अवस्था' : 'Review state'}
          <select
            value={reviewState}
            onChange={(event) => update('review_state', event.target.value)}
          >
            <option value="">{hi ? 'सभी' : 'All'}</option>
            {reviewStates.map((value) => (
              <option value={value} key={value}>
                {displayLabel(value, hi)}
              </option>
            ))}
          </select>
        </label>
        <label>
          {hi ? 'विभाग' : 'Department'}
          <input
            value={params.get('department') || ''}
            onChange={(event) => update('department', event.target.value)}
          />
        </label>
        <label>
          {hi ? 'श्रेणी' : 'Category'}
          <select
            value={params.get('category') || ''}
            onChange={(event) => update('category', event.target.value)}
          >
            <option value="">{hi ? 'सभी' : 'All'}</option>
            {['scholarships', 'procurement', 'msme', 'welfare'].map((value) => (
              <option key={value}>{value}</option>
            ))}
          </select>
        </label>
        <label>
          {hi ? 'क्षेत्र' : 'Registry geography'}
          <select
            value={params.get('state') || ''}
            onChange={(event) => update('state', event.target.value)}
          >
            <option value="">{hi ? 'सभी' : 'All'}</option>
            <option>India</option>
            <option>Rajasthan</option>
          </select>
        </label>
        <label>
          {hi ? 'फ़ाइल प्रकार' : 'Format'}
          <select
            value={params.get('format') || ''}
            onChange={(event) => update('format', event.target.value)}
          >
            <option value="">{hi ? 'सभी' : 'All'}</option>
            <option value="pdf">PDF</option>
            <option value="html">HTML</option>
          </select>
        </label>
        <label>
          {hi ? 'दस्तावेज़ प्रकार' : 'Document type'}
          <select
            value={params.get('document_type') || ''}
            onChange={(event) => update('document_type', event.target.value)}
          >
            <option value="">{hi ? 'सभी' : 'All'}</option>
            {[
              'policy_guideline',
              'tender_notice',
              'general_announcement',
              'document_index',
              'amendment',
              'unclassified',
              'irrelevant',
            ].map((value) => (
              <option key={value} value={value}>
                {displayLabel(value, hi)}
              </option>
            ))}
          </select>
        </label>
      </form>
      {(listing.isPending || detail.isFetching) && (
        <p role="status">{hi ? 'लोड हो रहा है…' : 'Loading sources…'}</p>
      )}
      {(listing.error || detail.error) && (
        <p role="alert">{listing.error?.message || detail.error?.message}</p>
      )}
      {listing.data && (
        <p>
          {listing.data.total} {hi ? 'संग्रहित रिकॉर्ड' : 'captured records'}
        </p>
      )}
      {listing.data?.total === 0 && (
        <p>
          {hi
            ? 'इस फ़िल्टर में कोई सरकारी स्रोत आयात नहीं हुआ है।'
            : 'No government sources have been imported for this filter yet.'}
        </p>
      )}
      <div className="card-grid">
        {listing.data?.items.map((item) => (
          <article className="panel" key={item.id} style={{ padding: 20 }}>
            <span className="eyebrow">
              {displayLabel(item.review_state, hi)} · {item.format.toUpperCase()}
            </span>
            <h2>{item.title}</h2>
            <p>
              {item.department || (hi ? 'जारीकर्ता की पुष्टि बाकी' : 'Issuer attribution pending')}
            </p>
            <p>
              {item.categories.join(', ')} · {item.jurisdictions.join(', ')}
            </p>
            <p>
              {hi ? 'संग्रहित:' : 'Captured:'}{' '}
              {item.captured_at
                ? new Date(item.captured_at).toLocaleDateString(hi ? 'hi-IN' : 'en-IN')
                : ''}{' '}
              · {item.page_count} {hi ? 'पृष्ठ' : 'pages'}
            </p>
            {item.needs_ocr && (
              <p>{hi ? 'OCR या एन्कोडिंग की समीक्षा आवश्यक' : 'OCR or encoding review required'}</p>
            )}
            <a href={item.source_url} target="_blank" rel="noreferrer">
              {hi ? 'मूल सरकारी स्रोत' : 'Original government source'}
            </a>{' '}
            <button
              onClick={() => {
                const next = new URLSearchParams(params);
                next.set('source', item.id);
                setParams(next);
              }}
            >
              {hi ? 'संग्रहित पाठ देखें' : 'Read captured text'}
            </button>
            {item.related_opportunities.map((id) => (
              <p key={id}>
                <ContextLink to={`/opportunities/${id}`}>
                  {hi ? 'समीक्षित अवसर' : 'Reviewed opportunity'}
                </ContextLink>
              </p>
            ))}
          </article>
        ))}
      </div>
      {listing.data?.next_cursor && (
        <button
          onClick={() => {
            const next = new URLSearchParams(params);
            next.set('cursor', listing.data!.next_cursor!);
            setParams(next);
          }}
        >
          {hi ? 'अगला पृष्ठ' : 'Next page'}
        </button>
      )}
      {detail.data && (
        <section className="panel" aria-label={hi ? 'संग्रहित स्रोत पाठ' : 'Captured source text'}>
          <h2>{detail.data.title}</h2>
          <p>{hi ? 'यह संग्रहित पाठ है, स्वीकृत पात्रता का निर्णय नहीं।' : detail.data.notice}</p>
          {detail.data.pages.map((page) => (
            <details key={page.page} id={`page-${page.page}`}>
              <summary>
                {hi ? 'पृष्ठ' : 'Page'} {page.page}
              </summary>
              <pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{page.text}</pre>
            </details>
          ))}
        </section>
      )}
    </div>
  );
}
