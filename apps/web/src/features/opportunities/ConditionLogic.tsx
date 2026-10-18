import type { components } from '../../lib/api/schema';
type Rule = components['schemas']['Rule-Output'];
type Result = components['schemas']['Result'];

export function ConditionLogic({ rule, result, hi }: { rule: Rule; result?: Result; hi: boolean }) {
  if (rule.op !== 'condition')
    return (
      <div>
        <strong>
          {rule.op === 'all'
            ? hi
              ? 'इन सभी शर्तों की आवश्यकता है'
              : 'All of these conditions'
            : hi
              ? 'इनमें से कम से कम एक शर्त'
              : 'At least one of these conditions'}
        </strong>
        <ul>
          {(rule.children ?? []).map((child, index) => (
            <li key={index}>
              <ConditionLogic rule={child} result={result?.children?.[index]} hi={hi} />
            </li>
          ))}
        </ul>
      </div>
    );
  const c = rule.condition;
  if (!c || c.op === 'unknown')
    return (
      <span>
        {hi ? 'स्रोत की मानवीय व्याख्या बाकी है।' : 'Human source clarification remains necessary.'}
      </span>
    );
  const operators = {
    eq: '=',
    in: hi ? 'इनमें से' : 'one of',
    gte: '≥',
    lte: '≤',
    gt: '>',
    lt: '<',
    document: hi ? 'सत्यापित प्रमाण' : 'verified evidence',
  };
  return (
    <div>
      <span>
        {c.fact?.replaceAll('_', ' ')} {operators[c.op]}{' '}
        {Array.isArray(c.value)
          ? c.value.join(', ')
          : typeof c.value === 'boolean'
            ? c.value
              ? hi
                ? 'हाँ'
                : 'Yes'
              : hi
                ? 'नहीं'
                : 'No'
            : String(c.value ?? '')}
      </span>
      {result && (
        <span>
          {' '}
          ·{' '}
          {result.outcome === 'satisfied'
            ? hi
              ? 'बताई जानकारी पर मेल'
              : 'matches supplied facts'
            : result.outcome === 'unsatisfied'
              ? hi
                ? 'ज्ञात अंतर'
                : 'known mismatch'
              : hi
                ? 'अज्ञात'
                : 'unknown'}
        </span>
      )}
      {c.income_definition && (
        <p>
          {hi ? 'आय का सटीक आधार' : 'Exact income basis'}: {c.income_definition}
        </p>
      )}
      {c.income_period && (
        <p>
          {hi ? 'आय अवधि' : 'Income period'}:{' '}
          {c.income_period === 'previous_admission_financial_year'
            ? hi
              ? 'वास्तविक प्रवेश वर्ष से पिछला वित्त वर्ष; प्रवेश वर्ष अज्ञात हो तो तुलना अज्ञात रहेगी।'
              : 'Financial year before actual admission; an unknown admission year keeps this comparison unknown.'
            : c.income_period}
        </p>
      )}
    </div>
  );
}
