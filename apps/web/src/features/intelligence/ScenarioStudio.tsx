import { ResearchGuidance } from '../opportunities/ResearchGuidance';
import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { useSubject } from '../../app/subject-context';
import { useLanguage } from '../../app/App';
import { api, fail } from '../../lib/api/client';
import type { components } from '../../lib/api/schema';
import { IntelligenceMap } from '../../components/IntelligenceMap';
import { SearchModes, type Mode } from './SearchModes';
import { RankedCards } from './Recommendations';
type Fact = components['schemas']['FactInput'];
type Person = components['schemas']['FictionalPerson'];
type Action = components['schemas']['ActionView'];
const fields: Array<{
  key: Fact['key'];
  en: string;
  hi: string;
  type?: 'number' | 'boolean';
  options?: string[];
  income?: boolean;
}> = [
  { key: 'school_government', en: 'Government school', hi: 'सरकारी विद्यालय', type: 'boolean' },
  {
    key: 'business_udyam_registered',
    en: 'Udyam registered',
    hi: 'उद्यम पंजीकृत',
    type: 'boolean',
  },
  {
    key: 'business_size',
    en: 'Udyam classification',
    hi: 'उद्यम वर्ग',
    options: ['micro', 'small', 'medium', 'other'],
  },
  {
    key: 'business_sector',
    en: 'Business sector',
    hi: 'व्यवसाय क्षेत्र',
    options: ['manufacturing', 'services', 'trading', 'other'],
  },
  {
    key: 'business_similar_assistance',
    en: 'Received similar government assistance',
    hi: 'समान सरकारी सहायता प्राप्त',
    type: 'boolean',
  },
  { key: 'age', en: 'Age', hi: 'उम्र', type: 'number' },
  {
    key: 'annual_personal_income',
    en: 'Annual personal income (₹)',
    hi: 'वार्षिक व्यक्तिगत आय (₹)',
    type: 'number',
    income: true,
  },
  {
    key: 'annual_parental_income',
    en: 'Annual parental income (₹)',
    hi: 'वार्षिक माता-पिता की आय (₹)',
    type: 'number',
    income: true,
  },
  {
    key: 'annual_household_income',
    en: 'Annual household income (₹)',
    hi: 'वार्षिक घरेलू आय (₹)',
    type: 'number',
    income: true,
  },
  { key: 'student_status', en: 'Currently enrolled', hi: 'अभी अध्ययनरत', type: 'boolean' },
  {
    key: 'current_education_level',
    en: 'Current course',
    hi: 'वर्तमान पाठ्यक्रम',
    options: ['below_IX', 'IX', 'X', 'XI', 'XII', 'undergraduate', 'postgraduate', 'other'],
  },
  {
    key: 'highest_completed_education',
    en: 'Highest completed education',
    hi: 'उच्चतम पूर्ण शिक्षा',
    options: ['none', 'below_IX', 'IX', 'X', 'XI', 'XII', 'undergraduate', 'postgraduate', 'other'],
  },
  {
    key: 'enrollment_mode',
    en: 'Enrollment mode',
    hi: 'अध्ययन का प्रकार',
    options: ['full_time', 'part_time', 'distance'],
  },
  {
    key: 'school_recognized_or_government',
    en: 'Recognized or government school',
    hi: 'मान्यता प्राप्त या सरकारी विद्यालय',
    type: 'boolean',
  },
  { key: 'domicile_state', en: 'Domicile state', hi: 'मूल निवास राज्य' },
  { key: 'domicile_district', en: 'Domicile district', hi: 'मूल निवास जिला' },
  { key: 'residence_state', en: 'Residence state', hi: 'वर्तमान निवास राज्य' },
  { key: 'residence_district', en: 'Residence district', hi: 'वर्तमान निवास जिला' },
  {
    key: 'employment_status',
    en: 'Employment',
    hi: 'रोज़गार',
    options: ['employed', 'unemployed', 'self_employed', 'other'],
  },
  { key: 'business_registered', en: 'Business registered', hi: 'व्यवसाय पंजीकृत', type: 'boolean' },
  {
    key: 'business_operating_status',
    en: 'Business operating status',
    hi: 'व्यवसाय संचालन',
    options: ['active', 'inactive', 'prelaunch'],
  },
  {
    key: 'business_registration_state',
    en: 'Business registration state',
    hi: 'व्यवसाय पंजीकरण राज्य',
  },
  {
    key: 'business_registration_district',
    en: 'Business registration district',
    hi: 'व्यवसाय पंजीकरण जिला',
  },
  {
    key: 'business_turnover',
    en: 'Annual business turnover (₹)',
    hi: 'वार्षिक कारोबार (₹)',
    type: 'number',
    income: true,
  },
  {
    key: 'beneficiary_category',
    en: 'Beneficiary category, if you choose to provide it',
    hi: 'लाभार्थी वर्ग, यदि आप बताना चाहें',
    options: ['SC', 'ST', 'OBC', 'EBC', 'DNT', 'other'],
  },
  {
    key: 'category_domicile_recognized',
    en: 'Category recognized for your domicile state?',
    hi: 'क्या मूल निवास राज्य में यह वर्ग मान्य है?',
    type: 'boolean',
  },
  {
    key: 'institution_recognized',
    en: 'Is the current institution recognized?',
    hi: 'क्या वर्तमान शिक्षण संस्था मान्यता प्राप्त है?',
    type: 'boolean',
  },
  {
    key: 'course_recognized',
    en: 'Is the current course recognized?',
    hi: 'क्या वर्तमान पाठ्यक्रम मान्यता प्राप्त है?',
    type: 'boolean',
  },
  {
    key: 'studying_in_india',
    en: 'Is your current study in India?',
    hi: 'क्या आप अभी भारत में पढ़ रहे हैं?',
    type: 'boolean',
  },
  {
    key: 'receives_other_scholarship',
    en: 'Currently receiving another scholarship or stipend?',
    hi: 'क्या अभी अन्य छात्रवृत्ति या वृत्तिका मिल रही है?',
    type: 'boolean',
  },
  {
    key: 'other_support_only_incidental',
    en: 'Is all other support only books, equipment or lodging expenses?',
    hi: 'क्या अन्य सहायता केवल पुस्तक, उपकरण या आवास व्यय है?',
    type: 'boolean',
  },
  {
    key: 'same_stage_second_course',
    en: 'A second course at an already completed education stage?',
    hi: 'क्या पूर्ण किए स्तर पर दूसरा पाठ्यक्रम है?',
    type: 'boolean',
  },
  {
    key: 'top_class_school_listed',
    en: 'Current school on the applicable Top Class School list?',
    hi: 'क्या वर्तमान विद्यालय लागू टॉप क्लास सूची में है?',
    type: 'boolean',
  },
  {
    key: 'top_class_college_listed',
    en: 'Current institution on the applicable Top Class College list?',
    hi: 'क्या वर्तमान संस्था लागू टॉप क्लास कॉलेज सूची में है?',
    type: 'boolean',
  },
  {
    key: 'orphan_supported_by_guardian',
    en: 'Orphan supported by a guardian, as this source defines?',
    hi: 'क्या स्रोत की परिभाषा अनुसार अभिभावक के संरक्षण में अनाथ हैं?',
    type: 'boolean',
  },
  {
    key: 'parental_income_salary_basis',
    en: 'Does the cited salaried-parent income timing apply?',
    hi: 'क्या उद्धृत वेतनभोगी माता-पिता की आय अवधि लागू है?',
    type: 'boolean',
  },
  {
    key: 'education_admission_year',
    en: 'Academic year of admission to this course (e.g. 2026-27)',
    hi: 'इस पाठ्यक्रम में प्रवेश का शैक्षणिक वर्ष (जैसे 2026-27)',
  },
  {
    key: 'business_udyam_assist_registered',
    en: 'Registered on Udyam Assist Platform',
    hi: 'उद्यम असिस्ट प्लेटफ़ॉर्म पर पंजीकृत',
    type: 'boolean',
  },
  { key: 'business_gst_registered', en: 'GST registered', hi: 'जीएसटी पंजीकृत', type: 'boolean' },
  {
    key: 'business_online_trade_scope',
    en: 'Online business across state boundaries',
    hi: 'ऑनलाइन व्यवसाय की राज्य सीमा',
    options: ['intra_state', 'inter_state', 'unknown'],
  },
];
const labels: Record<string, [string, string]> = {
  below_IX: ['Below class IX', 'कक्षा IX से नीचे'],
  undergraduate: ['Undergraduate', 'स्नातक'],
  postgraduate: ['Postgraduate', 'स्नातकोत्तर'],
  none: ['None completed', 'कोई पूर्ण नहीं'],
  other: ['Other', 'अन्य'],
  full_time: ['Full time', 'पूर्णकालिक'],
  part_time: ['Part time', 'अंशकालिक'],
  distance: ['Distance', 'दूरस्थ'],
  employed: ['Employed', 'नौकरी'],
  unemployed: ['Unemployed', 'बेरोज़गार'],
  self_employed: ['Self employed', 'स्वरोज़गार'],
  active: ['Active', 'सक्रिय'],
  inactive: ['Inactive', 'निष्क्रिय'],
  prelaunch: ['Before launch', 'शुरू होने से पहले'],
};
function FactEditor({
  facts,
  onChange,
  kind,
}: {
  facts: Fact[];
  onChange: (facts: Fact[]) => void;
  kind: string;
}) {
  const hi = useLanguage() === 'hi';
  const [key, setKey] = useState<Fact['key']>(
    kind === 'business' ? 'business_registered' : kind === 'household' ? 'residence_state' : 'age',
  );
  const available = fields.filter((f) =>
    kind === 'business'
      ? f.key.startsWith('business_') || f.key.startsWith('residence_')
      : kind === 'household'
        ? f.key === 'annual_household_income' ||
          f.key.startsWith('residence_') ||
          f.key.startsWith('domicile_')
        : !f.key.startsWith('business_') && f.key !== 'annual_household_income',
  );
  function update(index: number, change: Partial<Fact>) {
    onChange(facts.map((f, i) => (i === index ? { ...f, ...change } : f)));
  }
  return (
    <div>
      {facts.map((fact, index) => {
        const field = fields.find((f) => f.key === fact.key)!;
        const choices = field.type === 'boolean' ? ['true', 'false'] : field.options;
        return (
          <fieldset key={fact.key} style={{ margin: '12px 0', minWidth: 0 }}>
            <legend>{hi ? field.hi : field.en}</legend>
            <label>
              {hi ? 'काल्पनिक मान' : 'Hypothetical value'}
              {choices ? (
                <select
                  value={fact.value === null ? '' : String(fact.value)}
                  onChange={(e) =>
                    update(index, {
                      value:
                        e.target.value === ''
                          ? null
                          : field.type === 'boolean'
                            ? e.target.value === 'true'
                            : e.target.value,
                    })
                  }
                >
                  <option value="">{hi ? 'अज्ञात' : 'Unknown'}</option>
                  {choices.map((v) => (
                    <option value={v} key={v}>
                      {v === 'true'
                        ? hi
                          ? 'हाँ'
                          : 'Yes'
                        : v === 'false'
                          ? hi
                            ? 'नहीं'
                            : 'No'
                          : labels[v]?.[hi ? 1 : 0] || v}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type={field.type === 'number' ? 'number' : 'text'}
                  min={field.type === 'number' ? 0 : undefined}
                  step={fact.key === 'age' ? 1 : 'any'}
                  value={fact.value === null ? '' : String(fact.value)}
                  onChange={(e) =>
                    update(index, {
                      value:
                        e.target.value === ''
                          ? null
                          : field.type === 'number'
                            ? Number(e.target.value)
                            : e.target.value,
                    })
                  }
                />
              )}
            </label>
            {field.income && (
              <>
                <label>
                  {hi ? 'आय अवधि (जैसे 2026-27)' : 'Income period (e.g. 2026-27)'}
                  <input
                    value={fact.income_period || ''}
                    onChange={(e) => update(index, { income_period: e.target.value || null })}
                  />
                </label>
                <label>
                  {hi ? 'स्रोत की सटीक आय परिभाषा' : 'Exact income definition from the policy'}
                  <input
                    value={fact.income_definition || ''}
                    onChange={(e) => update(index, { income_definition: e.target.value || null })}
                  />
                </label>
                <small>
                  {hi
                    ? 'गलत या अज्ञात परिभाषा का परिणाम अज्ञात रहेगा। आय स्वचालित रूप से नहीं जोड़ी जाती।'
                    : 'An unknown or different definition stays unknown. Family incomes are never summed automatically.'}
                </small>
              </>
            )}
            <button type="button" onClick={() => onChange(facts.filter((_, i) => i !== index))}>
              {hi ? 'बदलाव हटाएँ' : 'Remove override'}
            </button>
          </fieldset>
        );
      })}
      <label>
        {hi ? 'बदलने वाली जानकारी' : 'Fact to change'}
        <select
          value={available.some((f) => f.key === key) ? key : available[0]?.key}
          onChange={(e) => setKey(e.target.value as Fact['key'])}
        >
          {available.map((f) => (
            <option key={f.key} value={f.key}>
              {hi ? f.hi : f.en}
            </option>
          ))}
        </select>
      </label>
      <button
        type="button"
        onClick={() => {
          const chosen = available.some((f) => f.key === key) ? key : available[0].key;
          if (!facts.some((f) => f.key === chosen))
            onChange([...facts, { key: chosen, value: null }]);
        }}
      >
        {hi ? 'जानकारी का बदलाव जोड़ें' : 'Add fact override'}
      </button>
    </div>
  );
}
export function ScenarioStudio() {
  const context = useSubject();
  return <Studio key={context.key} />;
}
function Studio() {
  const context = useSubject();
  const hi = useLanguage() === 'hi';
  const [params] = useSearchParams();
  const [mode, setMode] = useState<Mode>(
    context.subject.kind === 'household'
      ? 'family'
      : context.subject.kind === 'business'
        ? 'business'
        : context.subject.id
          ? 'member'
          : 'me',
  );
  const [facts, setFacts] = useState<Fact[]>([]);
  const [household, setHousehold] = useState<Fact[]>([]);
  const [people, setPeople] = useState<Person[]>([]);
  const [selected, setSelected] = useState<Action | null>(null);
  const [excluded, setExcluded] = useState<string[]>([]);
  const [memberFacts, setMemberFacts] = useState<Record<string, Fact[]>>({});
  const [applicationType, setApplicationType] = useState<'fresh' | 'renewal' | null>(null);
  const correct =
    mode === 'me' ||
    (mode === 'family' && context.subject.kind === 'household') ||
    (mode === 'business' && context.subject.kind === 'business') ||
    (mode === 'member' && context.subject.kind === 'person' && !!context.subject.id);
  const base = {
    q: '',
    include_national: true,
    mode,
    subject_id: mode === 'me' ? null : context.subject.id,
    application_type: applicationType,
    development: params.get('development') === 'true',
  };
  const baseQuery = useQuery({
    queryKey: ['scenario-base', base],
    enabled: correct && context.available,
    retry: false,
    queryFn: async () => {
      const { data, error } = await api.POST('/v1/search', { body: base });
      return data ?? fail(error);
    },
  });
  const mutation = useMutation({
    mutationFn: async () => {
      const actual = baseQuery.data;
      if (!actual)
        throw new Error(hi ? 'पहले आधार संदर्भ चुनें।' : 'Select and load the actual base first.');
      const actualSubject = actual.subjects.find((s) =>
        mode === 'me' ? s.kind === 'person' : s.id === context.subject.id,
      );
      const subjectKey = String(actualSubject?.key || '');
      const { data, error } = await api.POST('/v1/scenarios/evaluate', {
        body: {
          base,
          overrides: [
            ...(facts.length ? [{ subject_key: subjectKey, facts }] : []),
            ...Object.entries(memberFacts)
              .filter(([, value]) => value.length)
              .map(([key, value]) => ({ subject_key: key, facts: value })),
          ],
          people,
          household_facts: household,
          excluded_subject_keys: excluded,
        },
      });
      return data ?? fail(error);
    },
  });
  function changed() {
    mutation.reset();
    setSelected(null);
  }
  function reset() {
    setFacts([]);
    setHousehold([]);
    setPeople([]);
    setExcluded([]);
    setMemberFacts({});
    changed();
  }
  return (
    <div className="page">
      <header>
        <span className="eyebrow">{hi ? 'केवल काल्पनिक' : 'HYPOTHETICAL ONLY'}</span>
        <h1>{hi ? 'परिदृश्य स्टूडियो' : 'Scenario Studio'}</h1>
        <p>
          {hi
            ? 'एक संभावित भविष्य देखें। वास्तविक प्रोफ़ाइल, परिवार, दस्तावेज़ और योजना नहीं बदलेंगे।'
            : 'Explore a possible future. Your actual profile, family, documents and plan stay unchanged.'}
        </p>
      </header>
      <SearchModes
        mode={mode}
        explore={false}
        onChange={(value) => {
          if (value === 'me') context.select('person:');
          setMode(value);
          reset();
        }}
      />
      <section className="panel" style={{ padding: 20 }}>
        <h2>
          {hi ? 'वास्तविक आधार' : 'Actual base'} ·{' '}
          {mode === 'me' ? (hi ? 'मैं' : 'Me') : context.label}
        </h2>
        <p>
          {hi
            ? 'सहेजी गई अधिकृत जानकारी आधार है। बदलाव काल्पनिक हैं। केवल उद्धृत और दर्ज शर्तों की तुलना होती है; शेष शर्तें और पात्रता असत्यापित हैं।'
            : 'The server uses your saved facts as the starting point. Changes below are hypothetical. Research comparisons respond only to mapped, cited conditions. Unmapped conditions remain unknown and eligibility policies still require review.'}
        </p>
        <FactEditor
          kind={mode === 'business' ? 'business' : mode === 'family' ? 'household' : 'person'}
          facts={facts}
          onChange={(value) => {
            setFacts(value);
            changed();
          }}
        />
      </section>
      <label>
        {hi ? 'आवेदन का प्रकार' : 'Application context'}
        <select
          value={applicationType || ''}
          onChange={(e) => {
            setApplicationType((e.target.value || null) as 'fresh' | 'renewal' | null);
            changed();
          }}
        >
          <option value="">{hi ? 'अज्ञात' : 'Unknown'}</option>
          <option value="fresh">{hi ? 'नया' : 'Fresh'}</option>
          <option value="renewal">{hi ? 'नवीनीकरण' : 'Renewal'}</option>
        </select>
      </label>
      {baseQuery.error && <p role="alert">{baseQuery.error.message}</p>}
      {mode === 'family' &&
        baseQuery.data?.subjects
          .filter((subject) => subject.kind === 'person')
          .map((subject) => (
            <section className="panel" key={String(subject.key)} style={{ padding: 20 }}>
              <h3>{String(subject.name)}</h3>
              <label>
                <input
                  type="checkbox"
                  checked={!excluded.includes(String(subject.key))}
                  onChange={(e) => {
                    setExcluded(
                      e.target.checked
                        ? excluded.filter((key) => key !== subject.key)
                        : [...excluded, String(subject.key)],
                    );
                    changed();
                  }}
                />
                {hi ? 'इस परिदृश्य में शामिल रखें' : 'Include in this scenario'}
              </label>
              {!excluded.includes(String(subject.key)) && (
                <FactEditor
                  kind="person"
                  facts={memberFacts[String(subject.key)] || []}
                  onChange={(value) => {
                    setMemberFacts({ ...memberFacts, [String(subject.key)]: value });
                    changed();
                  }}
                />
              )}
            </section>
          ))}
      {mode !== 'business' && (
        <section className="panel" style={{ padding: 20 }}>
          <h2>{hi ? 'काल्पनिक परिवार' : 'Fictional family'}</h2>
          <p>
            {hi
              ? 'ये वास्तविक खाते या अनुमतियाँ नहीं हैं। किसी अन्य वयस्क का निजी डेटा नहीं लिया जाता।'
              : 'These are fictional nodes, not accounts or permissions. No other adult’s private facts are loaded.'}
          </p>
          {people.map((person, index) => (
            <fieldset key={person.key} style={{ minWidth: 0 }}>
              <legend>
                {hi ? 'काल्पनिक व्यक्ति' : 'Fictional person'} {index + 1}
              </legend>
              <label>
                {hi ? 'नाम' : 'Name'}
                <input
                  value={person.name}
                  maxLength={60}
                  onChange={(e) => {
                    setPeople(
                      people.map((p, i) => (i === index ? { ...p, name: e.target.value } : p)),
                    );
                    changed();
                  }}
                />
              </label>
              <label>
                {hi ? 'काल्पनिक संबंध' : 'Fictional relationship'}
                <select
                  value={person.relationship}
                  onChange={(e) => {
                    setPeople(
                      people.map((p, i) =>
                        i === index
                          ? { ...p, relationship: e.target.value as Person['relationship'] }
                          : p,
                      ),
                    );
                    changed();
                  }}
                >
                  <option value="child">{hi ? 'बच्चा' : 'Child'}</option>
                  <option value="spouse">{hi ? 'जीवनसाथी' : 'Spouse'}</option>
                  <option value="dependent">{hi ? 'आश्रित' : 'Dependent'}</option>
                </select>
              </label>
              <FactEditor
                kind="person"
                facts={person.facts || []}
                onChange={(value) => {
                  setPeople(people.map((p, i) => (i === index ? { ...p, facts: value } : p)));
                  changed();
                }}
              />
              <button
                onClick={() => {
                  setPeople(people.filter((_, i) => i !== index));
                  changed();
                }}
              >
                {hi ? 'व्यक्ति हटाएँ' : 'Remove fictional person'}
              </button>
            </fieldset>
          ))}
          <button
            disabled={people.length >= 10}
            onClick={() => {
              setPeople([
                ...people,
                {
                  key: crypto.randomUUID().replaceAll('-', '').slice(0, 20),
                  name: hi ? 'काल्पनिक व्यक्ति' : 'Fictional person',
                  relationship: 'child',
                  facts: [],
                },
              ]);
              changed();
            }}
          >
            {hi ? 'काल्पनिक व्यक्ति जोड़ें' : 'Add fictional person'}
          </button>
          {!!people.length && (
            <>
              <h3>{hi ? 'परिदृश्य में घरेलू जानकारी' : 'Scenario household facts'}</h3>
              <FactEditor
                kind="household"
                facts={household}
                onChange={(value) => {
                  setHousehold(value);
                  changed();
                }}
              />
            </>
          )}
        </section>
      )}
      <div className="filter-bar">
        <button
          disabled={!correct || !baseQuery.data || mutation.isPending}
          onClick={() => mutation.mutate()}
        >
          {hi ? 'परिदृश्य चलाएँ' : 'Run scenario'}
        </button>
        <button onClick={reset}>{hi ? 'रीसेट / त्यागें' : 'Reset / discard'}</button>
      </div>
      {!mutation.data && correct && context.available && params.get('development') !== 'true' && (
        <ResearchGuidance variant="scenario" mode={mode} />
      )}
      {mutation.isPending && (
        <p role="status">
          {hi
            ? 'नई सूची खोजी और आकलित की जा रही है…'
            : 'Retrieving and assessing the scenario again…'}
        </p>
      )}
      {mutation.error && <p role="alert">{mutation.error.message}</p>}
      {mutation.data && (
        <section aria-label="Scenario results">
          {params.get('development') !== 'true' && (
            <ResearchGuidance
              variant="scenario"
              mode={mode}
              overrides={facts}
              memberOverrides={memberFacts}
              people={people}
              excluded={excluded}
              scenario
            />
          )}
          <h2>{hi ? 'वास्तविक बनाम काल्पनिक' : 'Actual versus hypothetical'}</h2>
          <p>
            {hi
              ? 'नई सूची का अर्थ पात्रता या अपात्रता नहीं है। सीमित सूची से अवसर बाहर रह सकते हैं।'
              : 'Newly or no longer retrieved describes the shortlist, not a definitive eligibility change. Bounded retrieval can omit candidates.'}
          </p>
          <p>{hi ? 'कोई डेटा सहेजा नहीं गया।' : 'No scenario data was saved.'}</p>
          <ul>
            {mutation.data.graph.map((n, i) => (
              <li key={i}>
                {String(n.name)} · {String(n.relationship || n.kind)}{' '}
                {n.fictional ? (hi ? '(काल्पनिक)' : '(fictional)') : ''}
              </li>
            ))}
          </ul>
          {(['newly_retrieved', 'no_longer_retrieved', 'changed', 'unchanged'] as const).map(
            (change, i) => (
              <details key={change} open={i === 0}>
                <summary>
                  {
                    (hi
                      ? ['नए मिले अवसर', 'अब सूची में नहीं', 'बदले आकलन', 'अपरिवर्तित आकलन']
                      : [
                          'Newly retrieved opportunities',
                          'No longer retrieved',
                          'Changed assessments',
                          'Unchanged assessments',
                        ])[i]
                  }{' '}
                  ({mutation.data!.changes.filter((c) => c.change === change).length})
                </summary>
                {mutation
                  .data!.changes.filter((c) => c.change === change)
                  .map((c, j) => (
                    <div key={j}>
                      <strong>
                        {String(c.title)} · {String(c.subject_name)}
                      </strong>
                      <p>
                        {String(c.before || '—')} → {String(c.after || '—')}
                      </p>
                      {change === 'changed' && (
                        <details>
                          <summary>
                            {hi ? 'कौन सी शर्त बदली?' : 'Which conditions changed?'}
                          </summary>
                          <strong>{hi ? 'पहले' : 'Before'}</strong>
                          <ul>
                            {Array.isArray(c.before_reasons) &&
                              c.before_reasons.map((reason, k) => (
                                <li key={k}>{String(reason)}</li>
                              ))}
                          </ul>
                          <strong>{hi ? 'परिदृश्य में' : 'In this scenario'}</strong>
                          <ul>
                            {Array.isArray(c.reasons) &&
                              c.reasons.map((reason, k) => <li key={k}>{String(reason)}</li>)}
                          </ul>
                        </details>
                      )}
                    </div>
                  ))}
              </details>
            ),
          )}
          <IntelligenceMap
            plan={mutation.data.plan}
            selected={selected}
            onSelect={setSelected}
            title={(a) => a.title}
            subjectLabel={hi ? 'काल्पनिक विषय' : 'Hypothetical subjects'}
          />
          <h3>{hi ? 'साझा कदम और जानकारी की कमी' : 'Shared actions and missing information'}</h3>
          <ul>
            {mutation.data.plan.actions.map((a) => (
              <li key={a.id}>
                {a.title} · {a.opportunities.length} {hi ? 'अवसर' : 'opportunities'}
              </li>
            ))}
          </ul>
          {!!mutation.data.plan.known_blockers.length && (
            <>
              <h3>{hi ? 'ज्ञात बाधाएँ' : 'Known blockers'}</h3>
              <ul>
                {mutation.data.plan.known_blockers.map((blocker, index) => (
                  <li key={index}>
                    {String(blocker.subject)}: {String(blocker.reason)}
                  </li>
                ))}
              </ul>
            </>
          )}
          <RankedCards response={mutation.data.hypothetical} />
        </section>
      )}
    </div>
  );
}
