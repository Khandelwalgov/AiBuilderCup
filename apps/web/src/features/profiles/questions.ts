import specification from './semantics.generated.json';
import type { components } from '../../lib/api/schema';
export type Fact = components['schemas']['FactInput'];
export type Goal = 'education' | 'employment' | 'general';
export type Category = 'basics' | 'education' | 'employment' | 'income' | 'support';
type Values = Partial<Record<Fact['key'], Fact['value']>>;
export type Question = {
  key: Fact['key'];
  category: Category;
  label: [string, string];
  help?: [string, string];
  type: 'text' | 'number' | 'boolean' | 'select';
  choices?: [string, string, string][];
  goals?: Goal[];
  when?: (values: Values) => boolean;
  min?: number;
  max?: number;
};
export const incomeKeys = new Set<Fact['key']>([
  'annual_parental_income',
  'annual_personal_income',
  'business_turnover',
]);
export const documentKeys = new Set<Fact['key']>([
  'has_income_certificate',
  'has_disability_certificate',
  'has_udid_certificate',
  'has_registration_certificate',
]);
const school = ['IX', 'X', 'XI', 'XII'];
export const questions: Question[] = [
  {
    key: 'school_government',
    category: 'education',
    label: ['Is your current school government-run?', 'क्या आपका वर्तमान विद्यालय सरकारी है?'],
    type: 'boolean',
    when: (v) =>
      v.student_status === true &&
      ['below_IX', 'IX', 'X', 'XI', 'XII'].includes(String(v.current_education_level)),
    help: [
      'A recognized private school is different from a government school.',
      'मान्यता प्राप्त निजी विद्यालय सरकारी विद्यालय से अलग है।',
    ],
  },
  {
    key: 'age',
    category: 'basics',
    label: ['How old are you?', 'आपकी उम्र क्या है?'],
    type: 'number',
    min: 0,
    max: 130,
    help: [
      'Optional. Some opportunities have age limits.',
      'वैकल्पिक। कुछ अवसरों में उम्र की सीमा होती है।',
    ],
  },
  {
    key: 'domicile_state',
    category: 'basics',
    label: ['Which state is your permanent home?', 'आपका स्थायी गृह राज्य कौनसा है?'],
    type: 'text',
    help: [
      'Use the state recorded for domicile, if known. This can differ from where you live.',
      'यदि पता हो, मूल निवास का राज्य बताएँ। यह वर्तमान निवास से अलग हो सकता है।',
    ],
  },
  {
    key: 'domicile_district',
    category: 'basics',
    label: ['Permanent home district', 'स्थायी गृह जिला'],
    type: 'text',
  },
  {
    key: 'residence_state',
    category: 'basics',
    label: ['Where do you live now? (state)', 'अभी किस राज्य में रहते हैं?'],
    type: 'text',
  },
  {
    key: 'residence_district',
    category: 'basics',
    label: ['Current district', 'वर्तमान जिला'],
    type: 'text',
  },
  {
    key: 'student_status',
    category: 'education',
    goals: ['education'],
    label: ['Are you studying anywhere right now?', 'क्या आप अभी कहीं पढ़ाई कर रहे हैं?'],
    type: 'boolean',
  },
  {
    key: 'highest_completed_education',
    category: 'education',
    label: [
      "What is the highest level of education you've completed?",
      'आपने शिक्षा का कौनसा उच्चतम स्तर पूरा किया है?',
    ],
    type: 'select',
    choices: [
      ['none', 'No completed qualification yet', 'अभी कोई योग्यता पूरी नहीं हुई'],
      ['below_IX', 'Below Class 9', 'कक्षा 9 से नीचे'],
      ['IX', 'Class 9', 'कक्षा 9'],
      ['X', 'Class 10', 'कक्षा 10'],
      ['XI', 'Class 11', 'कक्षा 11'],
      ['XII', 'Class 12', 'कक्षा 12'],
      ['undergraduate', 'Undergraduate degree', 'स्नातक उपाधि'],
      ['postgraduate', 'Postgraduate degree', 'स्नातकोत्तर उपाधि'],
      ['other', 'Another completed qualification', 'अन्य पूरी की गई योग्यता'],
    ],
    help: [
      'A completed qualification is independent of whether you study or work now.',
      'पूरी की गई योग्यता आपकी वर्तमान पढ़ाई या काम से अलग है।',
    ],
  },
  {
    key: 'current_education_level',
    category: 'education',
    goals: ['education'],
    label: ['What are you currently studying?', 'आप अभी क्या पढ़ रहे हैं?'],
    type: 'select',
    when: (v) => v.student_status === true,
    choices: [
      ['below_IX', 'Below Class 9', 'कक्षा 9 से नीचे'],
      ['IX', 'Class 9', 'कक्षा 9'],
      ['X', 'Class 10', 'कक्षा 10'],
      ['XI', 'Class 11', 'कक्षा 11'],
      ['XII', 'Class 12', 'कक्षा 12'],
      ['undergraduate', 'Undergraduate degree', 'स्नातक पाठ्यक्रम'],
      ['postgraduate', 'Postgraduate degree', 'स्नातकोत्तर पाठ्यक्रम'],
      ['other', 'Another course', 'अन्य पाठ्यक्रम'],
    ],
  },
  {
    key: 'enrollment_mode',
    category: 'education',
    goals: ['education'],
    label: ['How are you studying now?', 'आप अभी किस तरीके से पढ़ रहे हैं?'],
    type: 'select',
    when: (v) => v.student_status === true,
    choices: [
      ['full_time', 'Full time', 'पूर्णकालिक'],
      ['part_time', 'Part time', 'अंशकालिक'],
      ['distance', 'Distance learning', 'दूरस्थ शिक्षा'],
    ],
  },
  {
    key: 'school_recognized_or_government',
    category: 'education',
    goals: ['education'],
    label: [
      'Is your current school government-run or officially recognized?',
      'क्या आपका वर्तमान स्कूल सरकारी या मान्यता प्राप्त है?',
    ],
    type: 'boolean',
    when: (v) =>
      v.student_status === true &&
      [...school, 'below_IX'].includes(String(v.current_education_level)),
  },
  {
    key: 'employment_status',
    category: 'employment',
    goals: ['employment'],
    label: ['What is your current work situation?', 'अभी आपकी कामकाज की स्थिति क्या है?'],
    type: 'select',
    choices: [
      ['employed', 'Employed', 'नौकरी'],
      ['unemployed', 'Looking for work', 'काम की तलाश'],
      ['self_employed', 'Self-employed', 'स्वरोज़गार'],
      ['other', 'Another situation', 'अन्य'],
    ],
  },
  {
    key: 'nationality',
    category: 'basics',
    label: ['What is your nationality?', 'आपकी राष्ट्रीयता क्या है?'],
    type: 'text',
    help: [
      'For example, Indian. Leave it unknown if unclear; nationality is separate from residence or domicile.',
      'जैसे भारतीय। स्पष्ट न हो तो अज्ञात छोड़ें; राष्ट्रीयता निवास या मूल निवास से अलग है।',
    ],
  },
  {
    key: 'annual_parental_income',
    category: 'income',
    label: ['Annual income of your parents', 'माता-पिता की वार्षिक आय'],
    type: 'number',
    min: 0,
  },
  {
    key: 'annual_personal_income',
    category: 'income',
    label: ['Your annual income', 'आपकी वार्षिक आय'],
    type: 'number',
    min: 0,
  },
  {
    key: 'disability_percentage',
    category: 'support',
    label: [
      'Disability percentage recorded on your certificate',
      'प्रमाणपत्र पर दर्ज दिव्यांगता प्रतिशत',
    ],
    type: 'number',
    min: 0,
    max: 100,
  },
];
export function valuesOf(facts: Fact[]): Values {
  const now = new Date();
  const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
  return Object.fromEntries(
    facts
      .filter(
        (f) =>
          (!f.valid_from || f.valid_from <= today) && (!f.valid_until || f.valid_until >= today),
      )
      .map((f) => [f.key, f.value]),
  );
}
export type SemanticIssue = {
  code: string;
  severity: string;
  fields: string[];
  message: string[];
  values: Record<string, Fact['value']>;
  retained: boolean;
};
export function semanticIssues(
  facts: Fact[],
  before: Fact[] = [],
  today?: string,
): SemanticIssue[] {
  const current = today
    ? Object.fromEntries(
        facts
          .filter(
            (f) =>
              (!f.valid_from || f.valid_from <= today) &&
              (!f.valid_until || f.valid_until >= today),
          )
          .map((f) => [f.key, f.value]),
      )
    : valuesOf(facts);
  return specification.rules
    .filter((rule) =>
      rule.when.every((test) => {
        const condition = test as {
          key: string;
          known?: boolean;
          eq?: unknown;
          one_of?: unknown[];
        };
        const value = current[condition.key as Fact['key']];
        return (
          (!condition.known || value != null) &&
          (!('eq' in condition) || value === condition.eq) &&
          (!condition.one_of || condition.one_of.includes(value))
        );
      }),
    )
    .map((rule) => {
      const retained = rule.fields.every((key) => {
        const a = facts.find((f) => f.key === key),
          b = before.find((f) => f.key === key);
        return (
          !!a &&
          !!b &&
          a.value === b.value &&
          (a.valid_from ?? null) === (b.valid_from ?? null) &&
          (a.valid_until ?? null) === (b.valid_until ?? null)
        );
      });
      return {
        ...rule,
        severity: retained ? 'warning' : rule.severity,
        retained,
        values: Object.fromEntries(rule.fields.map((key) => [key, current[key as Fact['key']]])),
      };
    });
}
export function conflicts(facts: Fact[], before: Fact[] = []) {
  return semanticIssues(facts, before).some((issue) => issue.severity === 'error');
}
export function answered(facts: Fact[]) {
  return facts.filter((f) => f.value !== null && f.value !== undefined && f.value !== '');
}
export function answerLabel(fact: Fact, hi: boolean) {
  if (
    fact.key === 'nationality' &&
    ['IN', 'IND', 'India', 'Indian', 'भारतीय', 'भारत'].includes(String(fact.value))
  )
    return hi ? 'भारतीय' : 'Indian';
  const q = questions.find(
    (q) => q.key === (fact.key === 'education_level' ? 'current_education_level' : fact.key),
  );
  if (typeof fact.value === 'boolean')
    return fact.value ? (hi ? 'हाँ' : 'Yes') : hi ? 'नहीं' : 'No';
  return (
    q?.choices?.find((c) => c[0] === fact.value)?.[hi ? 2 : 1] ??
    String(fact.value ?? (hi ? 'अभी पता नहीं' : 'Not sure yet'))
  );
}
