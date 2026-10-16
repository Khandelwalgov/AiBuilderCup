import { useSubject, ContextLink } from '../../app/subject-context';
import { useLanguage } from '../../app/App';
import type { components } from '../../lib/api/schema';
export type Mode = components['schemas']['SearchRequest']['mode'];
export function SearchModes({
  mode,
  onChange,
  explore = true,
}: {
  mode: Mode;
  onChange: (mode: Mode) => void;
  explore?: boolean;
}) {
  const context = useSubject();
  const hi = useLanguage() === 'hi';
  const options = context.options.filter((o) =>
    mode === 'family'
      ? o.kind === 'household'
      : mode === 'business'
        ? o.kind === 'business'
        : o.kind === 'person' && !!o.id,
  );
  return (
    <div className="filter-bar">
      <label>
        {hi ? 'किसके लिए खोजें?' : 'Who is this search for?'}
        <select
          aria-label={hi ? 'खोज का संदर्भ' : 'Search context'}
          value={mode}
          onChange={(e) => onChange(e.target.value as Mode)}
        >
          {explore && <option value="explore">{hi ? 'सभी अवसर देखें' : 'Explore All'}</option>}
          <option value="me">{hi ? 'केवल मेरे लिए' : 'Just Me'}</option>
          <option value="family">{hi ? 'मेरा परिवार' : 'My Family'}</option>
          <option value="member">{hi ? 'परिवार का एक सदस्य' : 'Specific Family Member'}</option>
          <option value="business">{hi ? 'मेरा व्यवसाय' : 'My Business'}</option>
        </select>
      </label>
      {mode !== 'me' && mode !== 'explore' && (
        <label>
          {hi ? 'अधिकृत संदर्भ चुनें' : 'Choose an authorized context'}
          <select
            aria-label="Authorized context"
            value={context.key}
            onChange={(e) => context.select(e.target.value)}
          >
            <option value="">{hi ? 'चुनें' : 'Select'}</option>
            {options.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </label>
      )}
      {mode !== 'explore' && !context.authenticated && (
        <ContextLink to="/">{hi ? 'पहले साइन इन करें' : 'Sign in first'}</ContextLink>
      )}
    </div>
  );
}
