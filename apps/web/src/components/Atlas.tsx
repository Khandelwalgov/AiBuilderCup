import { useState } from 'react';
import { ContextLink as Link } from '../app/subject-context';

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
  const [context, setContext] = useState(0);
  const [selected, setSelected] = useState(false);
  const contexts = hi ? ['व्यक्ति', 'परिवार', 'व्यवसाय'] : ['Personal', 'Family', 'Business'];
  return (
    <div className="page landing-page">
      <section className="landing-intro">
        <div className="launch-label">
          <span className="signal-dot" />
          {hi ? 'प्रमाण के साथ अवसरों की समझ' : 'OPPORTUNITY INTELLIGENCE, WITH EVIDENCE'}
        </div>
        <h1>
          {hi ? (
            <>
              अवसर समझें।
              <br />
              <span>अगला कदम पहचानें।</span>
            </>
          ) : (
            <>
              Good opportunities.
              <br />
              <span>Clear next steps.</span>
            </>
          )}
        </h1>
        <p>
          {hi
            ? 'अपने संदर्भ से ज़रूरी शर्तें जोड़ें। जानें कौनसी जानकारी बाकी है और एक कदम कहाँ-कहाँ मदद करता है।'
            : 'Connect your context to the conditions that matter. See what’s missing—and where one step can help more than once.'}
        </p>
        <div className="landing-actions">
          <Link className="button" to="/discover">
            {hi ? 'अवसर खोजें' : 'Explore opportunities'}
            <ArrowRight size={18} />
          </Link>
          <Link className="button secondary" to="/profile">
            {hi ? 'अपना संदर्भ बनाएँ' : 'Build your context'}
            <ArrowRight size={18} />
          </Link>
        </div>
      </section>
      <section
        className={`product-preview ${selected ? 'is-connected' : ''}`}
        aria-label={hi ? 'उदाहरण वाला इंटरैक्टिव पूर्वावलोकन' : 'Interactive illustrative preview'}
      >
        <header>
          <span className="preview-label">
            {hi ? 'उदाहरण, वास्तविक मिलान नहीं' : 'ILLUSTRATIVE · NOT A MATCH'}
          </span>
          <div
            className="preview-tabs"
            role="group"
            aria-label={hi ? 'उदाहरण का संदर्भ' : 'Illustrative context'}
          >
            {contexts.map((label, i) => (
              <button key={label} aria-pressed={context === i} onClick={() => setContext(i)}>
                {label}
              </button>
            ))}
          </div>
        </header>
        <div className="preview-flow">
          <div className="preview-context">
            <Fingerprint size={26} />
            <small>{hi ? 'चुना गया उदाहरण' : 'ILLUSTRATIVE CONTEXT'}</small>
            <h3>{contexts[context]}</h3>
            <p>{hi ? 'अधिकृत तथ्य अलग रहते हैं' : 'Authorized facts stay separate'}</p>
          </div>
          <div className="preview-connector" aria-hidden="true">
            →
          </div>
          <button
            className="preview-junction"
            aria-pressed={selected}
            onClick={() => setSelected((v) => !v)}
          >
            <ScanLine size={26} />
            <small>{hi ? 'एक साझा ज़रूरी कदम' : 'ONE SHARED PREREQUISITE'}</small>
            <strong>{hi ? 'एक कदम के संबंध देखें' : 'See what one step connects'}</strong>
            <span>
              {selected
                ? hi
                  ? 'संबंध दिखाई दे रहे हैं'
                  : 'Connections highlighted'
                : hi
                  ? 'संबंध देखने के लिए चुनें'
                  : 'Select to reveal connections'}{' '}
              <ArrowRight size={16} />
            </span>
          </button>
          <div className="preview-connector branching" aria-hidden="true">
            ↗<br />↘
          </div>
          <div className="preview-pathways">
            {[0, 1].map((i) => (
              <div key={i}>
                <span>{i ? 'B' : 'A'}</span>
                <div>
                  <strong>
                    {hi ? 'अवसर का रास्ता' : 'Opportunity pathway'} {i ? 'B' : 'A'}
                  </strong>
                  <p>{hi ? 'स्रोत-आधारित शर्तें' : 'Source-backed conditions'}</p>
                </div>
                <ArrowRight size={16} />
              </div>
            ))}
          </div>
        </div>
        <footer role="status">
          {selected
            ? hi
              ? 'उदाहरण: एक प्रमाण की ज़रूरत कई अवसरों से जुड़ सकती है। इससे पात्रता या सत्यापन की गारंटी नहीं मिलती।'
              : 'Illustration: one evidence requirement can connect several opportunities. It does not guarantee eligibility or verification.'
            : hi
              ? 'साझा कदम चुनें। यहाँ दिख रहे रास्ते केवल उत्पाद का उदाहरण हैं।'
              : 'Select the shared step. These pathways illustrate the product, not actual personalized results.'}
        </footer>
      </section>
      <section id="how-it-works" className="landing-method">
        <div>
          <span className="eyebrow">
            {hi ? 'जटिल जानकारी से उपयोगी कदम तक' : 'FROM COMPLEXITY TO A USEFUL NEXT MOVE'}
          </span>
          <h2>
            {hi
              ? `सिर्फ खोज नहीं।
समझ और तैयारी।`
              : `More than discovery.
A way through.`}
          </h2>
        </div>
        <ReadinessJourney
          steps={
            hi
              ? ['ज़रूरी संदर्भ दें', 'मूल शर्तों को समझें', 'साझा तैयारी के कदम देखें']
              : [
                  'Choose your context',
                  'Understand cited conditions',
                  'Act on shared prerequisites',
                ]
          }
        />
      </section>
      <section className="trust-banner">
        <ShieldCheck size={26} />
        <div>
          <h3>
            {hi ? 'प्रमाण पहले। अंतिम निर्णय प्राधिकरण का।' : 'Evidence first. Authorities decide.'}
          </h3>
          <p>
            {hi
              ? 'आधिकारिक स्रोत, मानव समीक्षा और स्पष्ट अनिश्चितता। कोई स्वचालित स्वीकृति नहीं।'
              : 'Official sources, human review and visible uncertainty. No automatic approvals.'}
          </p>
        </div>
        <Link to="/discover">
          {hi ? 'समीक्षित संग्रह देखें' : 'See reviewed coverage'}
          <ArrowRight size={17} />
        </Link>
      </section>
    </div>
  );
}
