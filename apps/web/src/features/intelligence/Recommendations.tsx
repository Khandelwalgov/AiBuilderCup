import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useSubject, ContextLink } from '../../app/subject-context';
import { useLanguage } from '../../app/App';
import { api, fail } from '../../lib/api/client';
import { useSearchParams } from 'react-router-dom';
import type { components } from '../../lib/api/schema';
import type { Mode } from './SearchModes';
type Response = components['schemas']['SearchResponse'];
export function RankedCards({ response }: { response: Response }) {
  const hi = useLanguage() === 'hi';
  const [limit, setLimit] = useState(6);
  return (
    <>
      <p role="status">
        {hi ? 'समीक्षित रिकॉर्ड' : 'Reviewed records'}: {response.catalogue_count} ·{' '}
        {hi ? 'आकलन' : 'Assessed subject–opportunity pairs'}: {response.assessed_pair_count} /{' '}
        {response.eligible_pair_count}
      </p>
      {response.truncated && (
        <div className="notice">
          {hi
            ? 'यह सीमित सूची है। सभी संभावित अवसर शामिल होने की गारंटी नहीं है।'
            : 'This is a bounded shortlist. Potentially relevant opportunities may be absent; use Explore All for the full catalogue.'}
        </div>
      )}
      <div className="opportunity-grid">
        {response.items.slice(0, limit).map((item) => (
          <article className="surface" key={item.opportunity.id} style={{ padding: 20 }}>
            <span className="eyebrow">
              {item.opportunity.is_synthetic
                ? hi
                  ? 'काल्पनिक परीक्षण'
                  : 'FICTIONAL TEST'
                : item.opportunity.issuer}
            </span>
            <h2>{item.opportunity.title}</h2>
            {item.assessments.map((a) => (
              <section key={a.subject_key}>
                <h3>
                  {a.subject_name} {a.hypothetical && (hi ? '· काल्पनिक' : '· Hypothetical')}
                </h3>
                <strong>
                  {a.evaluation.status === 'not_eligible_on_known_facts'
                    ? hi
                      ? 'ज्ञात बाधा'
                      : 'Known blocker'
                    : a.evaluation.status === 'potential_match'
                      ? hi
                        ? 'संभावित मेल'
                        : 'Potential match'
                      : hi
                        ? 'जानकारी आवश्यक'
                        : 'Missing information'}
                </strong>
                <ul>
                  {a.reasons.slice(1, 4).map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
                {!a.hypothetical && (
                  <ContextLink
                    to={`/opportunities/${item.opportunity.id}?kind=${a.subject_kind}${a.subject_id ? `&id=${a.subject_id}` : ''}`}
                  >
                    {hi ? 'शर्तें और साक्ष्य देखें' : 'Inspect conditions and evidence'}
                  </ContextLink>
                )}
                {a.hypothetical && (
                  <details>
                    <summary>{hi ? 'उद्धृत शर्तें' : 'Cited conditions'}</summary>
                    {a.evaluation.requirements.map((r) => (
                      <div key={r.requirement_id}>
                        <p>
                          {r.requirement}: {r.result.reason}
                        </p>
                        {r.citations.map((c, i) => (
                          <p key={i}>
                            <a href={c.source_url} target="_blank" rel="noreferrer">
                              {hi ? 'स्रोत' : 'Source'} {c.page}
                            </a>{' '}
                            · {c.passage}
                          </p>
                        ))}
                      </div>
                    ))}
                  </details>
                )}
              </section>
            ))}
          </article>
        ))}
      </div>
      {!response.items.length && (
        <p>
          {hi
            ? 'इस संदर्भ में कोई प्रकाशित अवसर नहीं मिला।'
            : 'No published opportunities found for this context.'}
        </p>
      )}
      {response.items.length > limit && (
        <button onClick={() => setLimit((n) => n + 6)}>
          {hi ? 'और देखें' : 'Show more recommendations'}
        </button>
      )}
    </>
  );
}
export function Recommendations({ mode }: { mode: Mode }) {
  const context = useSubject();
  const hi = useLanguage() === 'hi';
  const [params] = useSearchParams();
  const correct =
    mode === 'me' ||
    (mode === 'member' && context.subject.kind === 'person') ||
    (mode === 'family' && context.subject.kind === 'household') ||
    (mode === 'business' && context.subject.kind === 'business');
  const query = useQuery({
    queryKey: ['hybrid-search', mode, context.key, params.toString()],
    enabled: context.authenticated && context.available && correct,
    retry: false,
    queryFn: async () => {
      const { data, error } = await api.POST('/v1/search', {
        body: {
          mode,
          subject_id: mode === 'me' ? null : context.subject.id,
          q: params.get('q') || '',
          category: params.get('category') || null,
          state: params.get('state') || null,
          district: params.get('district') || null,
          include_national: params.get('national') !== 'false',
          development: params.get('development') === 'true',
        },
      });
      return data ?? fail(error);
    },
  });
  return (
    <section>
      <p>
        {hi
          ? 'प्रारंभिक, स्रोत-आधारित सुझाव। अंतिम निर्णय संबंधित प्राधिकरण करता है।'
          : 'Recommended for the selected context. These are preliminary assessments; authorities make final decisions.'}
      </p>
      {!correct && (
        <p>
          {hi
            ? 'इस खोज के लिए सही संदर्भ चुनें।'
            : 'Select the appropriate authorized context for this search.'}
        </p>
      )}
      {query.isLoading && (
        <p role="status">{hi ? 'खोज जारी है…' : 'Searching reviewed policies…'}</p>
      )}
      {query.error && <p role="alert">{query.error.message}</p>}
      {query.data && (
        <RankedCards key={mode + context.key + params.toString()} response={query.data} />
      )}
    </section>
  );
}
