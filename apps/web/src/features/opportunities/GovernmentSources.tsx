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
  const selectedPage = Number(params.get('page') || '0');
  const reviewStates = [
    'processing_pending',
    'needs_ocr',
    'human_review_pending',
    'reviewed_and_published',
  ] as const;
  const reviewLabel = (value: string) =>
    ({
      processing_pending: hi ? 'पात्रता समीक्षा नहीं हुई' : 'No eligibility review',
      needs_ocr: hi
        ? 'अपठनीय पाठ; पात्रता समीक्षा नहीं हुई'
        : 'Unreadable text; no eligibility review',
      human_review_pending: hi ? 'पात्रता समीक्षा बाकी' : 'Eligibility review pending',
      reviewed_and_published: hi ? 'पात्रता नीति प्रकाशित' : 'Eligibility policy published',
    })[value] || value;
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
            format: (params.get('format') || '') as '' | 'pdf' | 'html',
            department: params.get('department') || '',
            review_state: reviewState,
            text_state: (params.get('text_state') || '') as
              '' | 'text_available' | 'partial_text' | 'unreadable',
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
      <p>
        {hi
          ? 'संग्रहित रिकॉर्ड, अलग दस्तावेज़, पात्रता मसौदे और शोध अवसर अलग गिनतियाँ हैं। OCR उपलब्ध होना नीति स्वीकृति नहीं है।'
          : 'Capture records, unique document hashes, eligibility drafts and research listings are separate counts. Available OCR text does not mean a policy was approved.'}
      </p>
      {detail.data && (
        <section className="panel" aria-label={hi ? 'संग्रहित स्रोत पाठ' : 'Captured source text'}>
          <h2>{detail.data.title}</h2>
          <a href={detail.data.source_url} target="_blank" rel="noreferrer">
            {hi ? 'मूल सरकारी दस्तावेज़' : 'Original official document'}
          </a>
          <p>{detail.data.notice}</p>
          <p>SHA-256: {detail.data.content_hash}</p>
          {detail.data.pages.map((page) => (
            <details
              key={page.page}
              id={`page-${page.page}`}
              open={page.page === selectedPage || undefined}
            >
              <summary>
                {hi ? 'पृष्ठ' : 'Page'} {page.page} ·{' '}
                {page.basis === 'offline_ocr'
                  ? hi
                    ? 'स्थानीय OCR · स्वतंत्र सत्यापन नहीं'
                    : 'Local OCR · not independently verified'
                  : hi
                    ? 'मूल संग्रहित पाठ'
                    : 'Original captured text'}{' '}
                · {page.readability}
              </summary>
              {page.readability !== 'readable' && (
                <p role="note">
                  {hi
                    ? 'यह पृष्ठ अस्पष्ट या कम विश्वास वाला है। मूल दस्तावेज़ देखें।'
                    : 'This page is unreadable or requires text-quality review. Consult the original document.'}
                </p>
              )}
              <pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>
                {page.text || (hi ? 'पाठ उपलब्ध नहीं' : 'No readable text available')}
              </pre>
              {page.image_sha256 && (
                <p>
                  OCR render SHA-256: {page.image_sha256} · Text SHA-256: {page.text_sha256}
                </p>
              )}
              {page.original_text?.trim() && (
                <details>
                  <summary>{hi ? 'मूल निष्कर्षण देखें' : 'Inspect original extraction'}</summary>
                  <pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>
                    {page.original_text}
                  </pre>
                </details>
              )}
            </details>
          ))}
        </section>
      )}
      {listing.data && (
        <p className="notice">
          {listing.data.all_capture_records} {hi ? 'संग्रहित रिकॉर्ड' : 'capture records'} ·{' '}
          {listing.data.all_unique_document_hashes}{' '}
          {hi ? 'अलग दस्तावेज़ हैश' : 'unique document hashes'} ·{' '}
          {listing.data.public_research_listings} {hi ? 'शोध अवसर' : 'research listings'} ·{' '}
          {listing.data.unpublished_eligibility_versions}{' '}
          {hi ? 'अप्रकाशित पात्रता संस्करण' : 'unpublished eligibility versions'} ·{' '}
          {listing.data.published_eligibility_policies}{' '}
          {hi ? 'प्रकाशित पात्रता नीतियाँ' : 'published eligibility policies'}
        </p>
      )}
      <form
        className="source-filters panel"
        onSubmit={(event) => {
          event.preventDefault();
          update('q', String(new FormData(event.currentTarget).get('q') || ''));
        }}
      >
        <div className="source-search-row">
          <label>
            {hi ? 'स्रोत का पाठ खोजें' : 'Search source text'}
            <input key={params.get('q')} name="q" defaultValue={params.get('q') || ''} />
          </label>
          <div className="document-actions">
            <button>{hi ? 'खोजें' : 'Search sources'}</button>
            <button type="button" onClick={() => setParams(new URLSearchParams())}>
              {hi ? 'फ़िल्टर साफ़ करें' : 'Clear filters'}
            </button>
          </div>
        </div>
        <div className="source-primary-filters">
          <label>
            {hi ? 'समीक्षा अवस्था' : 'Review state'}
            <select
              value={reviewState}
              onChange={(event) => update('review_state', event.target.value)}
            >
              <option value="">{hi ? 'सभी' : 'All'}</option>
              {reviewStates.map((value) => (
                <option value={value} key={value}>
                  {reviewLabel(value)}
                </option>
              ))}
            </select>
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
        </div>
        <details className="source-advanced-filters">
          <summary>{hi ? 'अतिरिक्त फ़िल्टर' : 'Advanced filters'}</summary>
          <div className="source-primary-filters">
            <label>
              {hi ? 'पाठ उपलब्धता' : 'Text availability'}
              <select
                value={params.get('text_state') || ''}
                onChange={(e) => update('text_state', e.target.value)}
              >
                <option value="">{hi ? 'सभी' : 'All'}</option>
                <option value="text_available">{hi ? 'पाठ उपलब्ध' : 'Text available'}</option>
                <option value="partial_text">
                  {hi ? 'कुछ पृष्ठों की समीक्षा बाकी' : 'Some pages need review'}
                </option>
                <option value="unreadable">{hi ? 'अपठनीय' : 'Unreadable'}</option>
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
                  'institution_compliance',
                  'procedure_or_faq',
                  'administrative_reference',
                ].map((value) => (
                  <option key={value} value={value}>
                    {displayLabel(value, hi)}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </details>
      </form>
      {(listing.isPending || detail.isFetching) && (
        <p role="status">{hi ? 'लोड हो रहा है…' : 'Loading sources…'}</p>
      )}
      {(listing.error || detail.error) && (
        <p role="alert">{listing.error?.message || detail.error?.message}</p>
      )}
      {listing.data && (
        <p>
          {listing.data.total}{' '}
          {hi
            ? 'मिलते संग्रहित रिकॉर्ड'
            : 'matching capture records (includes repeated document hashes)'}
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
              {reviewLabel(item.review_state)} · {item.format.toUpperCase()}
            </span>
            <h2>{item.title}</h2>
            <p>
              {item.department || (hi ? 'जारीकर्ता की पुष्टि बाकी' : 'Issuer attribution pending')}
            </p>
            {item.attribution_evidence && (
              <p>
                {hi ? 'जारीकर्ता पाठ से उद्धृत; पृष्ठ' : 'Issuer transcribed from source; page'}{' '}
                {String(item.attribution_evidence.page)} · {String(item.attribution_evidence.basis)}
              </p>
            )}
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
            <p>
              {item.ocr_pages} {hi ? 'पृष्ठों का OCR उपलब्ध' : 'pages with completed OCR'} ·{' '}
              {item.text_state}
            </p>
            {!!item.review_required_pages?.length && (
              <p>
                {hi ? 'पाठ समीक्षा वाले पृष्ठ' : 'Text-quality review pages'}:{' '}
                {item.review_required_pages.join(', ')}
              </p>
            )}
            {item.needs_ocr && (
              <p>
                {hi
                  ? 'OCR या एन्कोडिंग की समीक्षा आवश्यक'
                  : `Unreadable pages: ${item.unreadable_pages.join(', ')}`}
              </p>
            )}
            <a href={item.source_url} target="_blank" rel="noreferrer">
              {hi ? 'मूल सरकारी स्रोत' : 'Original government source'}
            </a>{' '}
            <button
              onClick={() => {
                const next = new URLSearchParams(params);
                next.set('source', item.id);
                next.set('page', '1');
                setParams(next);
              }}
            >
              {hi ? 'संग्रहित पाठ देखें' : 'Read captured text'}
            </button>
            {(item.related_research || []).slice(0, 5).map((id) => (
              <p key={id}>
                <ContextLink to={`/research-opportunities/${id}`}>
                  {hi ? 'संबंधित शोध अवसर' : 'Related research listing'}
                </ContextLink>
              </p>
            ))}
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
    </div>
  );
}
