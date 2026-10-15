import { useDocumentNeeds, documentsHref, documentStatus } from '../documents/Documents';
import { useLanguage } from '../../app/App';
import { useState } from 'react';
import { ContextLink as Link, useSubject } from '../../app/subject-context';
import { useMutation, useQuery } from '@tanstack/react-query';
import { MessageCircle, ArrowUpRight } from 'lucide-react';
import { api, fail } from '../../lib/api/client';
export function Assistant({
  evaluationId,
  opportunityId,
}: {
  evaluationId: string;
  opportunityId: string;
}) {
  const context = useSubject();
  const language = useLanguage();
  return (
    <AssessmentAssistant
      key={`${evaluationId}:${opportunityId}:${context.key}:${language}`}
      evaluationId={evaluationId}
      opportunityId={opportunityId}
    />
  );
}
function AssessmentAssistant({
  evaluationId,
  opportunityId,
}: {
  evaluationId: string;
  opportunityId: string;
}) {
  const needs = useDocumentNeeds();
  const context = useSubject();
  const hi = useLanguage() === 'hi';
  const [question, setQuestion] = useState('');
  const [useAi, setUseAi] = useState(false);
  const capabilities = useQuery({
    queryKey: ['assistant-capabilities'],
    retry: false,
    queryFn: async () => {
      const { data, error } = await api.GET('/v1/assistant/capabilities');
      return data ?? fail(error);
    },
  });
  const query = useMutation({
    mutationFn: async (q: string) => {
      const { data, error } = await api.POST('/v1/assistant/explain', {
        body: {
          evaluation_id: evaluationId,
          question: q,
          language: hi ? 'hi' : 'en',
          use_ai: useAi,
        },
      });
      return data ?? fail(error);
    },
  });
  const suggestions = hi
    ? [
        'मुझे कौनसे दस्तावेज़ चाहिए और क्यों?',
        'मैं पात्र क्यों नहीं हूँ?',
        'मेरा अगला कदम क्या है?',
      ]
    : [
        'Which documents are still needed?',
        'Why is this condition unknown?',
        'What can I do next?',
      ];
  return (
    <section className="panel assistant-panel">
      <span className="eyebrow">
        <MessageCircle size={15} />
        {hi ? 'प्रमाण के साथ समझें' : 'UNDERSTAND WITH EVIDENCE'}
      </span>
      <h2>{hi ? 'अपनी तैयारी के बारे में पूछें' : 'Ask about this assessment'}</h2>
      <p>
        {hi
          ? 'उत्तर केवल समीक्षित शर्तों और अधिकृत आकलन पर आधारित हैं। निजी पहचान या दस्तावेज़ यहाँ न डालें।'
          : 'Answers use reviewed conditions and your authorized assessment. Do not enter identity details or private documents.'}
      </p>
      <div className="question-topics">
        {suggestions.map((q) => (
          <button
            key={q}
            className="topic-chip"
            onClick={() => {
              setQuestion(q);
              query.mutate(q);
            }}
            disabled={query.isPending}
          >
            {q}
            <ArrowUpRight size={13} />
          </button>
        ))}
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          query.mutate(question);
        }}
      >
        <label className="field">
          {hi ? 'आपका प्रश्न' : 'Your question'}
          <input
            value={question}
            maxLength={300}
            required
            onChange={(e) => setQuestion(e.target.value)}
          />
        </label>
        <label className="check-label">
          <input
            type="checkbox"
            disabled={!capabilities.data?.gemini_intent_enabled}
            checked={useAi}
            onChange={(e) => setUseAi(e.target.checked)}
          />
          {hi
            ? 'Gemini से प्रश्न का आशय समझें (उपलब्ध होने पर)'
            : 'Use Gemini to interpret question intent (when available)'}
        </label>
        <button className="button" disabled={query.isPending}>
          {query.isPending
            ? hi
              ? 'समझ रहे हैं…'
              : 'Preparing explanation…'
            : hi
              ? 'समझाएँ'
              : 'Explain assessment'}
        </button>
      </form>
      {query.isError && <p role="alert">{query.error.message}</p>}
      {query.data && !query.isError && (
        <div aria-live="polite" className="assistant-answer">
          <span className="eyebrow">
            {query.data.model
              ? `${query.data.model} · ${hi ? 'केवल प्रश्न का आशय' : 'intent only'}`
              : hi
                ? 'स्थानीय, स्रोत-आधारित व्याख्या'
                : 'Local cited explanation · no AI call'}
          </span>
          <p>{query.data.answer}</p>
          {query.data.items.map((item) => (
            <details key={item.requirement_id} open>
              <summary>{item.condition}</summary>
              <p>{item.explanation}</p>
              {needs.data
                ?.filter((n) => n.requirement_id === item.requirement_id)
                .map((n) => (
                  <div className="notice" key={n.requirement_id}>
                    <p>{documentStatus(n.documentary_status, hi)}</p>
                    <Link className="button secondary" to={documentsHref(n.requirement_id)}>
                      {hi ? 'संबंधित दस्तावेज़ प्रबंधित करें' : 'Manage this document requirement'}
                    </Link>
                  </div>
                ))}
              <Link
                className="field-followup"
                to={context.href(
                  `/opportunities/${opportunityId}#source-requirement-${item.requirement_id}`,
                )}
              >
                {hi ? 'आकलन में शर्त देखें' : 'Locate condition in assessment'}
              </Link>
              <Link className="field-followup" to="/plan">
                {hi ? 'संबंधित कदम देखें' : 'See related readiness actions'}
              </Link>
              {item.citations.map((c, i) => (
                <blockquote key={i}>
                  {String(c.passage)}
                  <a href={String(c.source_url)} target="_blank" rel="noreferrer">
                    {hi ? 'मूल स्रोत' : 'Original source'} · {String(c.page)}
                  </a>
                </blockquote>
              ))}
            </details>
          ))}
          {!query.data.items.length && (
            <p>
              {hi
                ? 'इस प्रश्न के लिए कोई संबंधित शर्त नहीं मिली।'
                : 'No relevant condition was recorded for this question.'}
            </p>
          )}
          <p className="notice">{query.data.disclaimer}</p>
        </div>
      )}
    </section>
  );
}
