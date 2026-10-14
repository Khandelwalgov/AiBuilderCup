import { useState } from 'react';
import { ExternalLink, Search } from 'lucide-react';
import { useLanguage } from '../app/App';
import type { components } from '../lib/api/schema';
type Pages = components['schemas']['ReviewView']['pages'];
export function CapturedReader({
  pages,
  selected,
  onSelect,
}: {
  pages: Pages;
  selected: number;
  onSelect: (index: number) => void;
}) {
  const hi = useLanguage() === 'hi';
  const [search, setSearch] = useState('');
  const page = pages[selected] ?? pages[0];
  const matches = search.trim()
    ? pages
        .map((p, i) => ({ p, i }))
        .filter(({ p }) => p.text.toLocaleLowerCase().includes(search.trim().toLocaleLowerCase()))
    : [];
  if (!page) return null;
  const year = page.source_url.includes('/2025/')
    ? '2025'
    : page.source_url.includes('/2024/')
      ? '2024'
      : hi
        ? 'स्रोत'
        : 'Source';
  return (
    <section
      className="captured-reader"
      aria-label={hi ? 'कैप्चर किया स्रोत' : 'Captured source reader'}
    >
      <span className="eyebrow">{hi ? 'साक्ष्य फोलियो' : 'EVIDENCE FOLIO'}</span>
      <h2>
        {year} / {hi ? 'स्रोत देखें' : 'Inspect the source'}
      </h2>
      <p>
        {hi
          ? 'सहेजे गए पन्ने में शब्द खोजें। मूल कानूनी पाठ को बनाए रखा गया है।'
          : 'Search the captured pages. Original legal wording is preserved.'}
      </p>
      <label className="field">
        <span>
          <Search size={14} /> {hi ? 'सभी पन्नों में खोजें' : 'Search all captured pages'}
        </span>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={hi ? 'जैसे: renewal, UDID' : 'Try “renewal” or “UDID”'}
        />
      </label>
      {search && (
        <div className="source-search-results" role="status">
          <p>
            {matches.length} {hi ? 'मिलते पन्ने' : 'matching pages'}
          </p>
          {matches.map(({ p, i }) => (
            <button key={i} onClick={() => onSelect(i)}>
              {p.source_url.includes('/2025/')
                ? '2025'
                : p.source_url.includes('/2024/')
                  ? '2024'
                  : 'Capture'}{' '}
              · {hi ? 'पृष्ठ' : 'page'} {p.page} ·{' '}
              {p.text.slice(
                Math.max(0, p.text.toLowerCase().indexOf(search.toLowerCase()) - 25),
                Math.max(0, p.text.toLowerCase().indexOf(search.toLowerCase()) - 25) + 100,
              )}
            </button>
          ))}
        </div>
      )}
      <label className="field">
        {hi ? 'कैप्चर किया पृष्ठ' : 'Captured page'}
        <select value={selected} onChange={(e) => onSelect(Number(e.target.value))}>
          {pages.map((p, i) => (
            <option key={i} value={i}>
              {p.source_url.includes('/2025/')
                ? '2025 amendment'
                : p.source_url.includes('/2024/')
                  ? '2024 guidelines'
                  : hi
                    ? 'स्रोत कैप्चर'
                    : 'Source capture'}{' '}
              · {hi ? 'पृष्ठ' : 'page'} {p.page}
            </option>
          ))}
        </select>
      </label>
      <div className="capture-meta">
        <span>
          {hi ? 'पृष्ठ' : 'Page'} {page.page} / {pages.length} {hi ? 'कुल पन्ने' : 'captured pages'}
        </span>
        <a href={`${page.source_url}#page=${page.page}`} target="_blank" rel="noreferrer">
          {hi ? 'मूल दस्तावेज़' : 'Original document'} <ExternalLink size={13} />
        </a>
      </div>
      <pre className="capture-text">{page.text}</pre>
    </section>
  );
}
