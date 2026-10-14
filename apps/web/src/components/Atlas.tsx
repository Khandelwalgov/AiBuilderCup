import { Link } from 'react-router-dom';
import { ArrowRight, Fingerprint, ScanLine, ShieldCheck } from 'lucide-react';
import { useLanguage } from '../app/App';
import type { components } from '../lib/api/schema';
type Evaluation = components['schemas']['EvaluationView'];

export function AssessmentLedger({ evaluation }: { evaluation: Evaluation }) {
  const hi = useLanguage() === 'hi';
  const statuses = ['satisfied', 'unknown', 'unsatisfied', 'not_applicable'] as const;
  const labels = hi
    ? ['दिए तथ्यों से पूरी', 'स्पष्टीकरण शेष', 'ज्ञात बाधा', 'लागू नहीं']
    : ['Supported by supplied facts', 'Needs clarification', 'Known restriction', 'Not applicable'];
  return (
    <section
      className="assessment-ledger"
      aria-label={hi ? 'शर्तों का विवरण' : 'Condition breakdown'}
    >
      <div className="ledger-track" aria-hidden="true">
        {evaluation.requirements.map((r) => (
          <span key={r.requirement_id} className={r.result.outcome} />
        ))}
      </div>
      <div className="ledger-labels">
        {statuses.map((status, i) => (
          <span key={status}>
            <i className={status} />
            <strong>
              {evaluation.requirements.filter((r) => r.result.outcome === status).length}
            </strong>{' '}
            {labels[i]}
          </span>
        ))}
      </div>
    </section>
  );
}

export function ReadinessJourney({ steps, active = 0 }: { steps: string[]; active?: number }) {
  return (
    <ol className="readiness-journey">
      {steps.map((step, i) => (
        <li
          key={step}
          className={i === active ? 'current' : ''}
          aria-current={i === active ? 'step' : undefined}
        >
          <span>{String(i + 1).padStart(2, '0')}</span>
          <strong>{step}</strong>
        </li>
      ))}
    </ol>
  );
}

export function Landing() {
  const hi = useLanguage() === 'hi';
  return (
    <div className="page atlas-landing">
      <section className="atlas-hero">
        <div className="atlas-hero-copy">
          <span className="eyebrow">
            <span className="signal-dot" />
            {hi ? 'अवसरों तक एक स्पष्ट रास्ता' : 'THE OPPORTUNITY INTELLIGENCE ATLAS'}
          </span>
          <h1>
            {hi ? (
              <>
                अवसर खोजें।
                <br />
                अपना रास्ता
                <br />
                <em>समझें।</em>
              </>
            ) : (
              <>
                Possibility,
                <br />
                with a path
                <br />
                <em>forward.</em>
              </>
            )}
          </h1>
          <p>
            {hi
              ? 'अपने लिए अवसर खोजें। जानें क्या बाकी है। अगला कदम साफ़ देखें।'
              : 'Find opportunities that apply to you. Understand what’s missing. Know what to do next.'}
          </p>
          <Link className="button atlas-cta" to="/discover">
            {hi ? 'अवसर खोजें' : 'Explore opportunities'}
            <ArrowRight size={19} />
          </Link>
          <Link className="atlas-secondary" to="/profile">
            {hi ? 'अपना प्रोफ़ाइल बनाएँ' : 'Start with your profile'} <ArrowRight size={16} />
          </Link>
        </div>
        <div className="atlas-specimen">
          <div className="specimen-caption">
            <span>01 / {hi ? 'जुड़ी तैयारी' : 'CONNECTED READINESS'}</span>
            <span>{hi ? 'केवल उदाहरण' : 'ILLUSTRATIVE · NOT A MATCH'}</span>
          </div>
          <div
            className="specimen-network"
            aria-label={
              hi
                ? 'उदाहरण: एक साझा कदम दो अवसरों से जुड़ता है'
                : 'Illustration: one shared action connects two opportunities'
            }
          >
            <svg viewBox="0 0 500 450" aria-hidden="true">
              <path d="M80 215 C150 215 145 215 215 215 M290 215 C365 215 330 100 395 100 M290 215 C365 215 330 330 395 330" />
              <circle cx="290" cy="215" r="6" />
              <circle cx="215" cy="215" r="6" />
            </svg>
            <div className="specimen-person">
              <Fingerprint size={28} />
              <strong>{hi ? 'आपका संदर्भ' : 'Your context'}</strong>
              <small>{hi ? 'अनुमति के साथ तथ्य' : 'Facts, with permission'}</small>
            </div>
            <div className="specimen-action">
              <span className="specimen-tag">{hi ? 'साझा कदम' : 'ONE SHARED ACTION'}</span>
              <ScanLine size={26} />
              <strong>
                {hi ? 'एक प्रमाण।\nकई संभावनाएँ।' : 'One piece of evidence.\nMore possibilities.'}
              </strong>
              <small>{hi ? 'सत्यापन अभी बाकी' : 'Verification still required'}</small>
            </div>
            <div className="specimen-opportunity first">
              <span>01</span>
              <strong>{hi ? 'अवसर' : 'Opportunity'}</strong>
              <small>{hi ? 'स्रोत-आधारित शर्तें' : 'Source-backed conditions'}</small>
            </div>
            <div className="specimen-opportunity second">
              <span>02</span>
              <strong>{hi ? 'दूसरा अवसर' : 'Another opportunity'}</strong>
              <small>{hi ? 'वही तैयारी का कदम' : 'The same readiness step'}</small>
            </div>
          </div>
          <p className="specimen-foot">
            {hi
              ? 'सिर्फ सूची नहीं। अवसरों और उनकी तैयारी के बीच संबंध।'
              : 'Beyond a list. See the connections between opportunities and the steps that unlock readiness.'}
          </p>
        </div>
      </section>
      <div className="atlas-trust">
        <ShieldCheck size={23} />
        <strong>
          {hi ? 'प्रमाण पहले। अनिश्चितता स्पष्ट।' : 'Evidence first. Uncertainty, made visible.'}
        </strong>
        <span>
          {hi
            ? 'आधिकारिक स्रोत · मानव समीक्षा · अंतिम निर्णय प्राधिकरण का'
            : 'Official sources · Human review · Authorities make final decisions'}
        </span>
      </div>
      <section className="atlas-method">
        <div>
          <span className="eyebrow">{hi ? 'कैसे काम करता है' : 'A CLEARER WAY THROUGH'}</span>
          <h2>{hi ? 'खोज से\nअगले कदम तक।' : 'From discovery\nto a doable next step.'}</h2>
        </div>
        <ReadinessJourney
          steps={
            hi
              ? ['अपना संदर्भ चुनें', 'प्रमाण सहित शर्तें समझें', 'साझा तैयारी के कदम देखें']
              : [
                  'Choose your context',
                  'Understand cited conditions',
                  'Act on shared prerequisites',
                ]
          }
        />
      </section>
      <section className="atlas-contexts">
        {(hi
          ? [
              ['01', 'व्यक्ति', 'केवल ज़रूरी सवाल। आपके तथ्य, आपके नियंत्रण में।', '/profile'],
              ['02', 'परिवार', 'आश्रित की अलग पहचान और स्पष्ट अभिभावक अनुमति।', '/family'],
              ['03', 'व्यवसाय', 'अपंजीकृत उद्यम से कंपनी तक। अपनी अलग कार्ययोजना।', '/businesses'],
            ]
          : [
              ['01', 'For you', 'Relevant questions. Your facts, under your control.', '/profile'],
              [
                '02',
                'For your family',
                'Independent profiles. Explicit guardian permissions.',
                '/family',
              ],
              [
                '03',
                'For your business',
                'From an unregistered enterprise to a company. A separate workspace.',
                '/businesses',
              ],
            ]
        ).map(([n, title, text, url]) => (
          <Link key={n} to={url}>
            <span>{n}</span>
            <h3>{title}</h3>
            <p>{text}</p>
            <ArrowRight size={22} />
          </Link>
        ))}
      </section>
    </div>
  );
}
