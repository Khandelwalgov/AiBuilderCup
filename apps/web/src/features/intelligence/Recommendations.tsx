import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useSubject, ContextLink } from '../../app/subject-context';
import { useLanguage } from '../../app/App';
import { api, fail, RequestError } from '../../lib/api/client';
import { displayLabel, displayDate } from '../../i18n/format';
import { useSearchParams } from 'react-router-dom';
import type { components } from '../../lib/api/schema';
import type { Mode } from './SearchModes';
type Response = components['schemas']['SearchResponse'];
function officialUrl(value: string | null) {
  try {
    const url = new URL(value || '');
    return url.protocol === 'https:' ? url.href : undefined;
  } catch {
    return undefined;
  }
}
export function RankedCards({ response }: { response: Response }) {
  const hi = useLanguage() === 'hi';
  const [limit, setLimit] = useState(6);
  const groups = response.items
    .slice(0, limit)
    .reduce<Record<string, Response['items']>>((result, item) => {
      (result[item.opportunity.category] ??= []).push(item);
      return result;
    }, {});
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
      {Object.entries(groups).map(([category, items]) => (
        <section key={category} aria-label={displayLabel(category, hi)}>
          <h2>{displayLabel(category, hi)}</h2>
          <div className="card-grid">
            {items?.map((item) => (
              <article className="panel" key={item.opportunity.id} style={{ padding: 20 }}>
                <span className="eyebrow">
                  {item.opportunity.is_synthetic
                    ? hi
                      ? 'काल्पनिक परीक्षण'
                      : 'FICTIONAL TEST'
                    : item.opportunity.issuer}
                </span>
                <h2>{item.opportunity.title}</h2>
                {['source_unreachable', 'needs_review'].includes(
                  item.opportunity.source.status,
                ) && (
                  <p className="notice">
                    {hi
                      ? 'नवीनतम स्रोत जाँच की समीक्षा आवश्यक है। पहले से समीक्षित संस्करण दिखाया गया है।'
                      : 'The latest source check needs review. This is the previously reviewed version.'}
                  </p>
                )}
                <p>{item.opportunity.summary}</p>
                <p>
                  <strong>{hi ? 'लाभ' : 'Benefits'}: </strong>
                  {item.opportunity.benefits ||
                    (hi ? 'स्रोत में स्थापित नहीं' : 'Not established in the published source')}
                </p>
                <p>
                  {[item.opportunity.district, item.opportunity.state].filter(Boolean).join(', ') ||
                    (hi ? 'राष्ट्रीय' : 'National')}{' '}
                  · {hi ? 'अंतिम तिथि' : 'Deadline'}:{' '}
                  {item.opportunity.closes_on || (hi ? 'ज्ञात नहीं' : 'Not established')}
                </p>
                {officialUrl(item.opportunity.apply_url) && (
                  <a
                    href={officialUrl(item.opportunity.apply_url)}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {hi ? 'आधिकारिक आवेदन' : 'Official application'}
                  </a>
                )}
                {officialUrl(item.opportunity.source_url) && (
                  <p>
                    <a
                      href={officialUrl(item.opportunity.source_url)}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {hi ? 'आधिकारिक स्रोत' : 'Official source'}
                    </a>{' '}
                    · {hi ? 'अंतिम समीक्षा' : 'Last reviewed'}:{' '}
                    {displayDate(
                      item.opportunity.last_verified_at,
                      hi,
                      hi ? 'ज्ञात नहीं' : 'Not recorded',
                    )}
                  </p>
                )}
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
                        : a.evaluation.status === 'known_blocker'
                          ? hi
                            ? 'ज्ञात बाधा'
                            : 'Known blocker'
                          : a.evaluation.status === 'ready_for_application_preflight'
                            ? hi
                              ? 'आवेदन की प्रारंभिक जाँच के लिए तैयार'
                              : 'Ready for application preflight'
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
                    <details>
                      <summary>{hi ? 'उद्धृत शर्तें' : 'Cited conditions'}</summary>
                      {a.evaluation.requirements.map((r) => (
                        <div key={r.requirement_id}>
                          <p>
                            {r.requirement}: {r.result.reason}
                          </p>
                          {r.citations.map((c, i) => (
                            <p key={i}>
                              <a href={officialUrl(c.source_url)} target="_blank" rel="noreferrer">
                                {hi ? 'स्रोत' : 'Source'} {c.page}
                              </a>{' '}
                              · {c.passage}
                            </p>
                          ))}
                        </div>
                      ))}
                    </details>
                  </section>
                ))}
              </article>
            ))}
          </div>
        </section>
      ))}
      {!response.items.length && (
        <p>
          {hi
            ? 'इस संदर्भ या फ़िल्टर के लिए अभी कोई समीक्षित अवसर प्रकाशित नहीं है। यह आपकी अपात्रता का निर्णय नहीं है।'
            : 'No reviewed opportunities are published for this context or filter yet. This is a coverage gap, not a finding that you are ineligible.'}
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
export function Recommendations({ mode, useFilters = true }: { mode: Mode; useFilters?: boolean }) {
  const context = useSubject();
  const hi = useLanguage() === 'hi';
  const [routeParams] = useSearchParams();
  const params = useFilters ? routeParams : new URLSearchParams();
  const correct =
    mode === 'me' ||
    (mode === 'member' && context.subject.kind === 'person') ||
    (mode === 'family' && context.subject.kind === 'household') ||
    (mode === 'business' && context.subject.kind === 'business');
  const query = useQuery({
    queryKey: ['hybrid-search', mode, context.key, params.toString()],
    enabled: context.authenticated && (mode === 'me' || context.available) && correct,
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
      {query.error instanceof RequestError && query.error.code === 'profile_not_found' ? (
        <p>
          <ContextLink to="/profile?kind=person">
            {hi
              ? 'सुझावों के लिए अपना प्रोफ़ाइल बनाएँ'
              : 'Create your profile to see recommendations'}
          </ContextLink>
        </p>
      ) : (
        query.error && <p role="alert">{query.error.message}</p>
      )}
      {query.isLoading && (
        <p role="status">{hi ? 'खोज जारी है…' : 'Searching reviewed policies…'}</p>
      )}
      {query.data && (
        <RankedCards key={mode + context.key + params.toString()} response={query.data} />
      )}
    </section>
  );
}
