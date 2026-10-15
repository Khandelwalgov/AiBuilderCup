import { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useLanguage } from '../../app/App';
import { useSubject, ContextLink as Link } from '../../app/subject-context';
import { useDirtyForm } from '../../app/dirty-forms';
import { api, authorizedFetch, fail } from '../../lib/api/client';
import { displayDate } from '../../i18n/format';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import type { components } from '../../lib/api/schema';
type Doc = components['schemas']['DocumentView'];
type Need = components['schemas']['RequirementDocumentView'];
type DocType = components['schemas']['DocumentCreate']['document_type'];
const names: Record<DocType, [string, string]> = {
  income_certificate: ['Income certificate', 'आय प्रमाणपत्र'],
  parental_income_certificate: ['Parents’ income certificate', 'माता-पिता का आय प्रमाणपत्र'],
  personal_income_certificate: ['Personal income certificate', 'व्यक्तिगत आय प्रमाणपत्र'],
  disability_certificate: ['Disability certificate', 'दिव्यांगता प्रमाणपत्र'],
  udid: ['UDID card', 'यूडीआईडी कार्ड'],
  registration_certificate: ['Business registration evidence', 'व्यवसाय पंजीकरण का प्रमाण'],
  age_proof: ['Proof of age', 'उम्र का प्रमाण'],
  education_certificate: ['Education certificate', 'शिक्षा प्रमाणपत्र'],
  other: ['Another document', 'अन्य दस्तावेज़'],
};
export function documentStatus(status: string | null | undefined, hi: boolean) {
  const labels: Record<string, [string, string]> = {
    not_provided: ['Not provided', 'अभी नहीं दिया गया'],
    pending_upload: ['Upload incomplete — retry', 'अपलोड अधूरा — दोबारा प्रयास करें'],
    uploaded_unverified: ['Uploaded — not verified', 'अपलोड हुआ — सत्यापित नहीं'],
    awaiting_verification: ['Awaiting verification', 'सत्यापन बाकी'],
    verified: ['Verified by an authorized process', 'अधिकृत प्रक्रिया से सत्यापित'],
    expired: ['Expired — replace required', 'समाप्त — नया प्रमाणपत्र दें'],
    rejected: ['Rejected — review needed', 'अस्वीकृत — समीक्षा आवश्यक'],
    replaced: ['Replaced', 'नए दस्तावेज़ से बदला गया'],
    deleted: ['Removed', 'हटाया गया'],
    legacy_unavailable: ['File unavailable — upload required', 'फ़ाइल उपलब्ध नहीं — अपलोड करें'],
  };
  return (labels[status ?? 'not_provided'] ?? labels.not_provided)[hi ? 1 : 0];
}
export function documentsHref(requirementId?: string) {
  return `/documents?upload=1${requirementId ? `&requirement=${requirementId}` : ''}`;
}
export function useDocumentNeeds() {
  const c = useSubject();
  return useQuery({
    queryKey: ['document-needs', c.subject],
    enabled: c.authenticated && c.available && !c.pending,
    retry: false,
    queryFn: async () => {
      const { data, error } = await api.GET('/v1/documents/requirements', {
        params: { query: { kind: c.subject.kind, subject_id: c.subject.id ?? undefined } },
      });
      return data ?? fail(error);
    },
  });
}
export function Documents() {
  const c = useSubject();
  const [params] = useSearchParams();
  return <Vault key={`${c.key}:${params.get('requirement') ?? ''}`} />;
}
function Vault() {
  const hi = useLanguage() === 'hi',
    c = useSubject(),
    cache = useQueryClient();
  const [params] = useSearchParams();
  const requested = params.get('requirement');
  const [open, setOpen] = useState(params.get('upload') === '1'),
    [name, setName] = useState(''),
    [kind, setKind] = useState<DocType>('other'),
    [issuer, setIssuer] = useState(''),
    [issued, setIssued] = useState(''),
    [expires, setExpires] = useState(''),
    [file, setFile] = useState<File | null>(null),
    [approved, setApproved] = useState(false),
    [selected, setSelected] = useState<string[]>(requested ? [requested] : []),
    [intent, setIntent] = useState<Doc | null>(null),
    [replace, setReplace] = useState<Doc | null>(null),
    [removing, setRemoving] = useState<Doc | null>(null),
    [dirty, setDirty] = useState(false),
    [message, setMessage] = useState(''),
    [preview, setPreview] = useState<{ url: string; type: string; name: string } | null>(null);
  const guard = useDirtyForm(dirty);
  const lifecycle = useRef(new AbortController());
  const previewUrl = useRef<string | null>(null);
  const input = useRef<HTMLInputElement>(null);
  useEffect(() => {
    const controller = new AbortController();
    lifecycle.current = controller;
    return () => {
      controller.abort();
      if (previewUrl.current) URL.revokeObjectURL(previewUrl.current);
    };
  }, []);
  const query = useQuery({
    queryKey: ['documents', c.subject],
    enabled: c.authenticated && c.available && !c.pending,
    retry: false,
    queryFn: async () => {
      const { data, error } = await api.GET('/v1/documents', {
        params: { query: { kind: c.subject.kind, subject_id: c.subject.id ?? undefined } },
      });
      return data ?? fail(error);
    },
  });
  const needs = useDocumentNeeds();
  const capabilities = useQuery({
    queryKey: ['document-capabilities'],
    retry: false,
    queryFn: async () => {
      const { data, error } = await api.GET('/v1/documents/capabilities');
      return data ?? fail(error);
    },
  });
  const requestedNeed = needs.data?.find((n) => n.requirement_id === requested);
  useEffect(() => {
    if (requestedNeed && !dirty) {
      setKind(requestedNeed.document_type as DocType);
      setSelected([requestedNeed.requirement_id]);
    }
  }, [requestedNeed, dirty]);
  function refresh() {
    for (const key of ['documents', 'document-needs', 'plan'])
      void cache.invalidateQueries({ queryKey: [key] });
  }
  function closePreview() {
    if (previewUrl.current) URL.revokeObjectURL(previewUrl.current);
    previewUrl.current = null;
    setPreview(null);
  }
  function clear() {
    guard.markSaved();
    setOpen(false);
    setFile(null);
    setIntent(null);
    setReplace(null);
    setName('');
    setIssuer('');
    setIssued('');
    setExpires('');
    setApproved(false);
    setSelected([]);
    setDirty(false);
    if (input.current) input.current.value = '';
  }
  const upload = useMutation({
    mutationFn: async () => {
      if (!file || !approved)
        throw new Error(
          hi ? 'फ़ाइल और उपयोग की अनुमति चुनें।' : 'Choose a file and approve its readiness use.',
        );
      if (
        !['application/pdf', 'image/jpeg', 'image/png'].includes(file.type) ||
        file.size > (capabilities.data?.max_file_bytes ?? 0)
      )
        throw new Error(
          hi
            ? 'समर्थित प्रकार और आकार की फ़ाइल चुनें।'
            : 'Choose a supported file within the size limit.',
        );
      let pending = intent;
      if (!pending) {
        const { data, error } = await api.POST('/v1/documents', {
          body: {
            subject: c.subject,
            display_name: name.trim(),
            document_type: kind,
            issuer: issuer || null,
            issued_on: issued || null,
            expires_on: expires || null,
            approved_uses: ['readiness'],
            requirement_ids: selected,
            replaces_id: replace?.id ?? null,
          },
          signal: lifecycle.current.signal,
        });
        pending = data ?? fail(error);
        setIntent(pending);
      }
      const response = await authorizedFetch(`/v1/documents/${pending.id}/content`, {
        method: 'PUT',
        body: file,
        headers: { 'Content-Type': file.type },
        signal: lifecycle.current.signal,
      });
      return (await response.json()) as Doc;
    },
    onSuccess: () => {
      closePreview();
      clear();
      setMessage('saved');
      refresh();
    },
    onError: () => refresh(),
  });
  const remove = useMutation({
    mutationFn: async (doc: Doc) => {
      closePreview();
      const { data, error } = await api.DELETE('/v1/documents/{identifier}', {
        params: { path: { identifier: doc.id } },
        body: { expected_revision: doc.revision },
      });
      return data ?? fail(error);
    },
    onSuccess: () => {
      setRemoving(null);
      closePreview();
      setMessage('removed');
      refresh();
    },
    onError: () => refresh(),
  });
  const linking = useMutation({
    mutationFn: async ({ doc, need }: { doc: Doc; need: Need }) => {
      const { data, error } = await api.POST('/v1/documents/{identifier}/links', {
        params: { path: { identifier: doc.id } },
        body: { requirement_ids: [need.requirement_id], expected_revision: doc.revision },
      });
      return data ?? fail(error);
    },
    onSuccess: () => {
      setMessage('linked');
      refresh();
    },
  });
  const access = useMutation({
    mutationFn: async ({ doc, purpose }: { doc: Doc; purpose: 'preview' | 'download' }) => {
      const { data, error } = await api.POST('/v1/documents/{identifier}/access', {
        params: { path: { identifier: doc.id } },
        body: { purpose },
        signal: lifecycle.current.signal,
      });
      const token = data ?? fail(error);
      const response = await authorizedFetch(`/v1/documents/${doc.id}/content?purpose=${purpose}`, {
        headers: { 'X-Document-Access': token.token },
        signal: lifecycle.current.signal,
      });
      const blob = await response.blob();
      if (lifecycle.current.signal.aborted) return;
      closePreview();
      const url = URL.createObjectURL(blob);
      previewUrl.current = url;
      if (purpose === 'preview') {
        setPreview({ url, type: doc.media_type, name: doc.display_name });
      } else {
        const a = document.createElement('a');
        a.href = url;
        a.download = `document.${doc.media_type === 'application/pdf' ? 'pdf' : doc.media_type === 'image/png' ? 'png' : 'jpg'}`;
        a.click();
        URL.revokeObjectURL(url);
        previewUrl.current = null;
      }
    },
  });
  function start(doc?: Doc) {
    if (!guard.confirmLeave()) return;
    clear();
    setOpen(true);
    setMessage('');
    upload.reset();
    if (doc) {
      setKind(doc.document_type as DocType);
      setName(doc.display_name);
      setIssuer(doc.issuer ?? '');
      setIssued(doc.status === 'pending_upload' ? (doc.issued_on ?? '') : '');
      setExpires(doc.status === 'pending_upload' ? (doc.expires_on ?? '') : '');
      if (doc.status === 'pending_upload') {
        setIntent(doc);
        setSelected(doc.linked_requirements.map((l) => String(l.requirement_id)));
      } else setReplace(doc);
    } else {
      setKind((requestedNeed?.document_type as DocType) ?? 'other');
      setSelected(requestedNeed ? [requestedNeed.requirement_id] : []);
    }
  }
  function compatible(doc: Doc, need: Need) {
    if (doc.document_type !== need.document_type || doc.status !== 'uploaded_unverified')
      return false;
    return doc.linked_requirements.every((l) => {
      const n = needs.data?.find((n) => n.requirement_id === l.requirement_id);
      return n && JSON.stringify(n.compatibility) === JSON.stringify(need.compatibility);
    });
  }
  if (!c.available)
    return (
      <div className="page panel" role="alert">
        {c.label}
      </div>
    );
  const live = (query.data ?? []).filter(
    (d) => !['deleted', 'replaced'].includes(d.status) || d.purge_pending,
  );
  const messages: Record<string, [string, string]> = {
    saved: [
      'Document saved privately. It has not been verified.',
      'दस्तावेज़ निजी रूप से सहेजा गया। सत्यापन अभी नहीं हुआ है।',
    ],
    removed: [
      'Document removed. Linked readiness states will update.',
      'दस्तावेज़ हटाया गया। जुड़े अवसरों की स्थिति अद्यतन होगी।',
    ],
    linked: [
      'Existing document linked. Verification is still required.',
      'मौजूदा दस्तावेज़ जोड़ा गया। सत्यापन अभी बाकी है।',
    ],
  };
  const primary = needs.data?.find((n) => n.requirement_id === selected[0]);
  return (
    <div className="page document-vault">
      <div className="page-heading">
        <span className="eyebrow">{c.label}</span>
        <h1>{hi ? 'मेरे दस्तावेज़' : 'My Documents'}</h1>
        <p>
          {hi
            ? 'एक निजी फ़ाइल, सही व्यक्ति या व्यवसाय के लिए। अपलोड और आधिकारिक सत्यापन अलग हैं।'
            : 'Private files for the right person or business. Uploading and official verification are separate.'}
        </p>
      </div>
      <div className="document-toolbar">
        <button
          className="button"
          onClick={() => start()}
          disabled={!capabilities.data?.uploads_enabled || upload.isPending}
        >
          {hi ? 'दस्तावेज़ अपलोड करें' : 'Upload a document'}
        </button>
        <span>
          {live.length} {hi ? 'दस्तावेज़' : 'documents'} · {c.label}
        </span>
      </div>
      {!capabilities.data?.uploads_enabled && (
        <p className="notice">
          {hi
            ? 'नए अपलोड फिलहाल बंद हैं। सुरक्षा और निजी भंडारण की तैयारी आवश्यक है।'
            : 'New uploads are currently disabled. Private storage and security prerequisites must be ready.'}
        </p>
      )}
      {capabilities.data?.uploads_enabled && (
        <p className="notice">
          {hi
            ? 'स्थानीय प्रदर्शन: केवल काल्पनिक PDF या चित्र प्रयोग करें। निजी पहचान के वास्तविक दस्तावेज़ अभी न दें।'
            : 'Local demonstration: use fictional PDFs or images only. Real sensitive identity uploads are not enabled for production.'}
        </p>
      )}
      {message && (
        <p role="status" className="notice">
          {messages[message]?.[hi ? 1 : 0] ?? message}
        </p>
      )}
      {[query, needs, capabilities]
        .filter((q) => q.isError)
        .map((q, i) => (
          <div role="alert" key={i}>
            <p>{q.error?.message}</p>
            <button className="text-button" onClick={() => void q.refetch()}>
              {hi ? 'दोबारा कोशिश करें' : 'Try again'}
            </button>
          </div>
        ))}
      {requested && !requestedNeed && !needs.isPending && (
        <p role="alert">
          {hi
            ? 'यह प्रकाशित दस्तावेज़ शर्त अब उपलब्ध नहीं है। अवसर की वर्तमान शर्तें फिर देखें।'
            : 'This published document requirement is no longer available. Review the opportunity’s current requirements.'}
        </p>
      )}
      {open && (
        <form
          className="panel document-upload"
          onSubmit={(e) => {
            e.preventDefault();
            if (!upload.isPending) upload.mutate();
          }}
        >
          <h2>
            {replace
              ? hi
                ? 'पुराना दस्तावेज़ बदलें'
                : 'Replace an outdated document'
              : hi
                ? 'निजी दस्तावेज़ जोड़ें'
                : 'Add a private document'}
          </h2>
          <p>
            {hi ? 'मालिक' : 'Owner'}: <strong>{c.label}</strong>
          </p>
          {replace && (
            <p>
              {hi
                ? 'नया अपलोड पूरा होने तक पुरानी फ़ाइल बनी रहेगी।'
                : 'The existing file stays available until the replacement upload succeeds.'}
            </p>
          )}
          <fieldset disabled={upload.isPending || !!intent}>
            <div className="document-metadata">
              <label className="field">
                {hi ? 'पहचानने योग्य नाम' : 'Recognizable name'}
                <input
                  required
                  maxLength={100}
                  value={name}
                  onChange={(e) => {
                    setName(e.target.value);
                    setDirty(true);
                  }}
                />
              </label>
              <label className="field">
                {hi ? 'दस्तावेज़ का प्रकार' : 'Document type'}
                <select
                  disabled={!!replace || !!requestedNeed}
                  value={kind}
                  onChange={(e) => {
                    setKind(e.target.value as DocType);
                    setSelected([]);
                    setDirty(true);
                  }}
                >
                  {Object.entries(names).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label[hi ? 1 : 0]}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <details>
              <summary>
                {hi ? 'जारी करने वाली संस्था और तारीखें (वैकल्पिक)' : 'Issuer and dates (optional)'}
              </summary>
              <label className="field">
                {hi ? 'जारी करने वाली संस्था' : 'Issuing organization'}
                <input
                  value={issuer}
                  maxLength={120}
                  onChange={(e) => {
                    setIssuer(e.target.value);
                    setDirty(true);
                  }}
                />
              </label>
              <div className="document-metadata">
                <label className="field">
                  {hi ? 'जारी होने की तारीख' : 'Issue date'}
                  <input
                    type="date"
                    value={issued}
                    onChange={(e) => {
                      setIssued(e.target.value);
                      setDirty(true);
                    }}
                  />
                </label>
                <label className="field">
                  {hi ? 'समाप्ति की तारीख' : 'Expiry date'}
                  <input
                    type="date"
                    min={issued || undefined}
                    value={expires}
                    onChange={(e) => {
                      setExpires(e.target.value);
                      setDirty(true);
                    }}
                  />
                </label>
              </div>
            </details>
            {primary && (
              <div className="notice">
                <p>
                  {primary.opportunity_title} · {primary.requirement}
                </p>
                <p>
                  {hi
                    ? 'इसी प्रमाण को स्वीकार करने वाली समान शर्तों में पुनः उपयोग चुन सकते हैं।'
                    : 'Choose reuse only for compatible published evidence requirements.'}
                </p>
                {needs.data
                  ?.filter(
                    (n) =>
                      n.requirement_id !== primary.requirement_id &&
                      JSON.stringify(n.compatibility) === JSON.stringify(primary.compatibility),
                  )
                  .map((n) => (
                    <label className="check-label" key={n.requirement_id}>
                      <input
                        type="checkbox"
                        checked={selected.includes(n.requirement_id)}
                        onChange={(e) => {
                          setSelected((prev) =>
                            e.target.checked
                              ? [...prev, n.requirement_id]
                              : prev.filter((id) => id !== n.requirement_id),
                          );
                          setDirty(true);
                        }}
                      />
                      {hi ? 'इसके लिए भी प्रयोग करें:' : 'Also use for:'} {n.opportunity_title}
                    </label>
                  ))}
              </div>
            )}
          </fieldset>
          <label className="field">
            {hi ? 'PDF, JPEG या PNG चुनें' : 'Choose a PDF, JPEG or PNG'}
            <input
              ref={input}
              type="file"
              accept="application/pdf,image/jpeg,image/png"
              required
              disabled={upload.isPending}
              onChange={(e) => {
                setFile(e.target.files?.[0] ?? null);
                setDirty(true);
                upload.reset();
              }}
            />
          </label>
          <p>
            {hi ? 'अधिकतम आकार' : 'Maximum size'}:{' '}
            {((capabilities.data?.max_file_bytes ?? 0) / 1048576).toFixed(0)} MB ·{' '}
            {hi ? 'निजी रूप से सहेजा जाएगा' : 'Stored privately'}
          </p>
          <label className="check-label">
            <input
              type="checkbox"
              checked={approved}
              disabled={upload.isPending}
              onChange={(e) => {
                setApproved(e.target.checked);
                setDirty(true);
              }}
            />
            {hi
              ? 'मैं इस संदर्भ और चुनी शर्तों की तैयारी के लिए फ़ाइल का उपयोग अधिकृत करता हूँ।'
              : 'I authorize using this file for this subject’s readiness and the selected requirements.'}
          </label>
          <div className="form-actions">
            <button
              className="button"
              disabled={
                upload.isPending ||
                !file ||
                !approved ||
                !name.trim() ||
                !capabilities.data?.uploads_enabled ||
                !!(requested && !requestedNeed)
              }
            >
              {upload.isPending
                ? hi
                  ? 'निजी रूप से अपलोड हो रहा है…'
                  : 'Uploading privately…'
                : intent
                  ? hi
                    ? 'अपलोड दोबारा करें'
                    : 'Retry upload'
                  : hi
                    ? 'निजी फ़ाइल सहेजें'
                    : 'Save private file'}
            </button>
            <button
              type="button"
              className="button secondary"
              disabled={upload.isPending}
              onClick={() => {
                if (guard.confirmLeave()) clear();
              }}
            >
              {hi ? 'रद्द करें' : 'Cancel'}
            </button>
          </div>
          {upload.isError && (
            <p role="alert">
              {upload.error.message}{' '}
              {hi
                ? 'फ़ाइल और विवरण यहीं हैं। दोबारा प्रयास कर सकते हैं।'
                : 'Your file selection and details remain here for retry.'}
            </p>
          )}
        </form>
      )}
      <div className="vault-layout">
        <section>
          <h2>{hi ? 'निजी दस्तावेज़' : 'Your private files'}</h2>
          {query.isPending && <p role="status">{hi ? 'लोड हो रहा है…' : 'Loading…'}</p>}
          {!query.isPending && !live.length && (
            <div className="panel">
              <h3>{hi ? 'अभी कोई दस्तावेज़ नहीं' : 'No documents yet'}</h3>
              <p>
                {hi
                  ? 'अवसर जब प्रमाण माँगे तब जोड़ें। नाम से फ़ाइल का स्वामित्व तय नहीं होता।'
                  : 'Add evidence when an opportunity needs it. Files belong to the selected subject, not to a filename.'}
              </p>
            </div>
          )}
          {live.map((doc) => (
            <article className="panel document-card" data-document-id={doc.id} key={doc.id}>
              <div>
                <span className="eyebrow">
                  {names[doc.document_type as DocType]?.[hi ? 1 : 0] ?? doc.document_type}
                </span>
                <h3>{doc.display_name}</h3>
                <p className="document-state">{documentStatus(doc.status, hi)}</p>
                {doc.purge_pending && (
                  <p role="alert">
                    {hi
                      ? 'फ़ाइल हटाने की प्रक्रिया अधूरी है। हटाएँ बटन से दोबारा प्रयास करें।'
                      : 'Private file removal is pending. Use Remove to retry safely.'}
                  </p>
                )}
              </div>
              <p>
                {c.label} ·{' '}
                {doc.byte_size
                  ? (doc.byte_size / 1024).toFixed(1) + ' KB'
                  : hi
                    ? 'फ़ाइल अभी नहीं पहुँची'
                    : 'No file received yet'}
              </p>
              <p>{displayDate(doc.uploaded_at ?? doc.created_at, hi, '')}</p>
              {doc.expires_on && (
                <p>
                  {hi ? 'समाप्ति' : 'Expiry'}: {doc.expires_on}
                </p>
              )}
              {doc.linked_requirements.map((link, i) => (
                <p key={i}>
                  <Link
                    to={`/opportunities/${link.opportunity_id}#source-requirement-${link.requirement_id}`}
                  >
                    {String(link.opportunity_title)}
                  </Link>{' '}
                  ·{' '}
                  {link.current
                    ? hi
                      ? 'वर्तमान प्रकाशित संस्करण'
                      : 'Current published version'
                    : hi
                      ? 'पुराना संस्करण — फिर जाँचें'
                      : 'Earlier version — review again'}
                </p>
              ))}
              <div className="document-actions">
                {['uploaded_unverified', 'expired'].includes(doc.status) && (
                  <>
                    <button
                      className="button secondary"
                      disabled={access.isPending}
                      onClick={() => access.mutate({ doc, purpose: 'preview' })}
                    >
                      {hi ? 'पूर्वावलोकन' : 'Preview'}
                    </button>
                    <button
                      className="text-button"
                      disabled={access.isPending}
                      onClick={() => access.mutate({ doc, purpose: 'download' })}
                    >
                      {hi ? 'डाउनलोड' : 'Download'}
                    </button>
                    <button
                      className="text-button"
                      disabled={!capabilities.data?.uploads_enabled || upload.isPending}
                      onClick={() => start(doc)}
                    >
                      {hi ? 'बदलें' : 'Replace'}
                    </button>
                  </>
                )}
                {doc.status === 'pending_upload' && (
                  <button className="button secondary" onClick={() => start(doc)}>
                    {hi ? 'अपलोड दोबारा करें' : 'Retry upload'}
                  </button>
                )}
                <button
                  className="text-button"
                  disabled={remove.isPending}
                  onClick={() => {
                    remove.reset();
                    setRemoving(doc);
                  }}
                >
                  {hi ? 'हटाएँ' : 'Remove'}
                </button>
              </div>
            </article>
          ))}
        </section>
        <aside>
          <h2>{hi ? 'अवसरों के लिए आवश्यक प्रमाण' : 'Evidence needed for opportunities'}</h2>
          {!needs.isPending && !needs.data?.length && (
            <div className="panel">
              <p>
                {hi
                  ? 'इस संदर्भ के लिए कोई प्रकाशित दस्तावेज़ शर्त अभी उपलब्ध नहीं है।'
                  : 'No published document requirements are available for this subject yet.'}
              </p>
              <Link to="/discover">{hi ? 'अवसर खोजें' : 'Explore opportunities'}</Link>
            </div>
          )}
          {needs.data?.map((need) => (
            <article className="panel requirement-document" key={need.requirement_id}>
              <h3>{need.opportunity_title}</h3>
              <p>{need.requirement}</p>
              <p>{documentStatus(need.documentary_status, hi)}</p>
              {need.documents.map((doc) => (
                <small key={doc.id}>
                  {doc.display_name} · {documentStatus(doc.status, hi)}
                </small>
              ))}
              <p>
                {hi
                  ? 'अपलोड पात्रता या प्रमाण की प्रामाणिकता की पुष्टि नहीं है।'
                  : 'A file upload does not establish eligibility or authenticity.'}
              </p>
              <Link
                className="text-button"
                to={`/opportunities/${need.opportunity_id}#source-requirement-${need.requirement_id}`}
              >
                {hi ? 'मूल शर्त देखें' : 'View the requirement'}
              </Link>
              {need.documentary_status !== 'uploaded_unverified' && (
                <Link
                  className="button secondary"
                  to={documentsHref(need.requirement_id)}
                  onClick={(event) => {
                    if (!guard.confirmLeave()) {
                      event.preventDefault();
                      return;
                    }
                    clear();
                    setOpen(true);
                    setKind(need.document_type as DocType);
                    setSelected([need.requirement_id]);
                  }}
                >
                  {hi ? 'दस्तावेज़ जोड़ें' : 'Add document'}
                </Link>
              )}
              {live
                .filter(
                  (d) =>
                    compatible(d, need) &&
                    !d.linked_requirements.some((l) => l.requirement_id === need.requirement_id),
                )
                .map((doc) => (
                  <button
                    className="text-button"
                    key={doc.id}
                    disabled={linking.isPending}
                    onClick={() => linking.mutate({ doc, need })}
                  >
                    {hi ? 'मौजूदा फ़ाइल प्रयोग करें:' : 'Use existing file:'} {doc.display_name}
                  </button>
                ))}
            </article>
          ))}
        </aside>
      </div>
      {access.isError && <p role="alert">{access.error.message}</p>}
      {linking.isError && <p role="alert">{linking.error.message}</p>}
      {preview && (
        <section
          className="panel private-preview"
          aria-label={hi ? 'निजी पूर्वावलोकन' : 'Private preview'}
        >
          <div className="page-heading">
            <h2>{preview.name}</h2>
            <button className="button secondary" onClick={closePreview}>
              {hi ? 'पूर्वावलोकन बंद करें' : 'Close preview'}
            </button>
          </div>
          {preview.type.startsWith('image/') ? (
            <img
              src={preview.url}
              alt={hi ? 'निजी दस्तावेज़ का पूर्वावलोकन' : 'Private document preview'}
            />
          ) : (
            <iframe
              title={hi ? 'निजी PDF पूर्वावलोकन' : 'Private PDF preview'}
              src={preview.url}
              sandbox="allow-same-origin"
            />
          )}
          <p>
            {hi
              ? 'यदि ब्राउज़र पूर्वावलोकन न दिखाए, अधिकृत डाउनलोड प्रयोग करें।'
              : 'If your browser cannot display the preview, use the authorized download.'}
          </p>
        </section>
      )}
      {removing && (
        <ConfirmDialog
          title={hi ? 'निजी फ़ाइल हटाएँ?' : 'Remove this private file?'}
          confirm={hi ? 'फ़ाइल हटाएँ' : 'Remove file'}
          cancel={hi ? 'रद्द करें' : 'Cancel'}
          busy={remove.isPending}
          onCancel={() => setRemoving(null)}
          onConfirm={() => remove.mutate(removing)}
        >
          <p>{removing.display_name}</p>
          <p>
            {hi
              ? 'फ़ाइल निजी भंडारण से हटेगी। जुड़े अवसर फिर दस्तावेज़ माँगेंगे; न्यूनतम इतिहास बना रहेगा।'
              : 'The private file will be removed. Linked requirements will need evidence again; minimal audit history remains.'}
          </p>
          {remove.isError && <p role="alert">{remove.error.message}</p>}
        </ConfirmDialog>
      )}
    </div>
  );
}

export function DocumentSummary() {
  const hi = useLanguage() === 'hi';
  const c = useSubject();
  const needs = useDocumentNeeds();
  const documents = useQuery({
    queryKey: ['documents', c.subject],
    enabled: c.authenticated && c.available && !c.pending,
    retry: false,
    queryFn: async () => {
      const { data, error } = await api.GET('/v1/documents', {
        params: { query: { kind: c.subject.kind, subject_id: c.subject.id ?? undefined } },
      });
      return data ?? fail(error);
    },
  });
  const files =
    documents.data?.filter((d) => ['uploaded_unverified', 'expired'].includes(d.status)) ?? [];
  return (
    <section className="panel">
      <h2>{hi ? 'दस्तावेज़ और तैयारी' : 'Documents and readiness'}</h2>
      {files.length > 0 && (
        <ul>
          {files.map((doc) => (
            <li key={doc.id}>
              {doc.display_name} · {documentStatus(doc.status, hi)}
            </li>
          ))}
        </ul>
      )}
      {documents.isError && (
        <p role="alert">
          {hi
            ? 'दस्तावेज़ अभी लोड नहीं हुए। निजी तिजोरी में दोबारा कोशिश करें।'
            : 'Documents could not be loaded. Retry in the private vault.'}
        </p>
      )}
      {needs.data?.length ? (
        <ul>
          {needs.data.map((n) => (
            <li key={n.requirement_id}>
              {n.requirement} · {documentStatus(n.documentary_status, hi)} ·{' '}
              <Link to={documentsHref(n.requirement_id)}>
                {hi ? 'दस्तावेज़ देखें' : 'Manage evidence'}
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <p>
          {hi
            ? 'प्रमाण तभी जोड़ें जब कोई अवसर उसे माँगे। अपने मौजूदा दस्तावेज़ निजी तिजोरी में देख सकते हैं।'
            : 'Add evidence when an opportunity needs it. View your existing documents in the private vault.'}
        </p>
      )}
      <Link className="button secondary" to="/documents">
        {hi ? 'मेरे दस्तावेज़ खोलें' : 'Open My Documents'}
      </Link>
    </section>
  );
}
