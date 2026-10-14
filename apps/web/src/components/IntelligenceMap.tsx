import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Focus, Minus, Plus, Fingerprint, GitBranch, FileCheck2, ArrowUpRight } from 'lucide-react';
import { useLanguage, useStrings } from '../app/App';
import type { components } from '../lib/api/schema';
type Plan = components['schemas']['PlanView'];
type Action = components['schemas']['ActionView'];
export function IntelligenceMap({
  plan,
  selected,
  onSelect,
  title,
}: {
  plan: Plan;
  selected: Action | null;
  onSelect: (action: Action) => void;
  title: (action: Action) => string;
}) {
  const hi = useLanguage() === 'hi';
  const t = useStrings();
  const [zoom, setZoom] = useState(1);
  const viewport = useRef<HTMLDivElement>(null);
  const fit = useRef(1);
  useEffect(() => {
    const el = viewport.current;
    if (!el) return;
    const observer = new ResizeObserver(([entry]) => {
      fit.current = Math.min(1, (entry.contentRect.width - 30) / 1100);
      setZoom(Math.max(0.4, fit.current));
      setOffset({ x: 0, y: 0 });
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [hover, setHover] = useState<string | null>(null);
  const drag = useRef<{ x: number; y: number; ox: number; oy: number } | null>(null);
  const actions = plan.actions.slice(0, 6);
  const evaluations = plan.evaluations.slice(0, 6);
  const height = Math.max(510, actions.length * 136 + 70, evaluations.length * 180 + 70);
  const active = hover ?? selected?.id;
  return (
    <section className="intelligence-map">
      <header className="map-header">
        <div>
          <span className="eyebrow">{hi ? 'आपका इंटेलिजेंस एटलस' : 'YOUR INTELLIGENCE ATLAS'}</span>
          <h2>{hi ? 'एक कदम। जुड़े अवसर।' : 'One step. Connected possibilities.'}</h2>
        </div>
        <span className="map-live">
          <span className="signal-dot" />
          {plan.hypothetical
            ? hi
              ? 'काल्पनिक'
              : 'Hypothetical'
            : hi
              ? 'समीक्षित संस्करण'
              : 'Reviewed versions'}
        </span>
      </header>
      <div className="map-legend">
        <span>
          <Fingerprint size={15} />
          {hi ? 'संदर्भ' : 'Context'}
        </span>
        <span>
          <FileCheck2 size={15} />
          {hi ? 'प्रमाण / जानकारी' : 'Evidence / information'}
        </span>
        <span>
          <GitBranch size={15} />
          {hi ? 'अवसर' : 'Opportunities'}
        </span>
        <small>
          {hi
            ? 'साझा कदम चुनकर उसके संबंध देखें'
            : 'Select a shared step to illuminate its connections'}
        </small>
      </div>
      <div
        ref={viewport}
        style={{ height: Math.min(760, Math.max(320, height * zoom + 30)) }}
        className="map-viewport"
        onPointerDown={(e) => {
          if ((e.target as HTMLElement).closest('button,a')) return;
          drag.current = { x: e.clientX, y: e.clientY, ox: offset.x, oy: offset.y };
          e.currentTarget.setPointerCapture(e.pointerId);
        }}
        onPointerMove={(e) => {
          if (drag.current)
            setOffset({
              x: drag.current.ox + e.clientX - drag.current.x,
              y: drag.current.oy + e.clientY - drag.current.y,
            });
        }}
        onPointerUp={() => {
          drag.current = null;
        }}
        onPointerCancel={() => {
          drag.current = null;
        }}
      >
        <div
          className="map-stage"
          style={{ height, transform: `translate(${offset.x}px,${offset.y}px) scale(${zoom})` }}
        >
          <svg className="atlas-edges" viewBox={`0 0 1100 ${height}`} aria-hidden="true">
            <defs>
              <marker
                id="atlas-arrow"
                viewBox="0 0 10 10"
                refX="9"
                refY="5"
                markerWidth="5"
                markerHeight="5"
                orient="auto-start-reverse"
              >
                <path d="M 0 0 L 10 5 L 0 10 z" />
              </marker>
            </defs>
            {actions.map((a, i) => (
              <path
                key={`subject-${a.id}`}
                className={active === a.id ? 'illuminated' : ''}
                d={`M 200 ${height / 2} C 260 ${height / 2} 250 ${i * 136 + 110} 330 ${i * 136 + 110}`}
              />
            ))}
            {actions.flatMap((a, i) =>
              evaluations
                .filter((e) => a.opportunities.some((o) => o.id === e.opportunity_id))
                .map((e) => {
                  const y = evaluations.indexOf(e) * 180 + 120;
                  return (
                    <path
                      markerEnd="url(#atlas-arrow)"
                      key={`${a.id}-${e.id}`}
                      className={active === a.id ? 'illuminated' : ''}
                      d={`M 610 ${i * 136 + 110} C 705 ${i * 136 + 110} 680 ${y} 790 ${y}`}
                    />
                  );
                }),
            )}
          </svg>
          <div className="map-subject" style={{ top: height / 2 - 65 }}>
            <Fingerprint size={30} />
            <strong>{hi ? 'चुना गया संदर्भ' : 'Selected context'}</strong>
            <span>
              {plan.subject.kind === 'person'
                ? hi
                  ? 'व्यक्ति'
                  : 'Person'
                : plan.subject.kind === 'household'
                  ? hi
                    ? 'परिवार'
                    : 'Household'
                  : hi
                    ? 'व्यवसाय'
                    : 'Business'}
            </span>
          </div>
          {actions.map((a, i) => (
            <button
              key={a.id}
              className={`atlas-node action ${active === a.id ? 'selected' : ''} ${new Set(a.opportunities.map((o) => o.id)).size > 1 ? 'shared' : ''}`}
              style={{ left: 330, top: i * 136 + 55 }}
              onClick={() => onSelect(a)}
              onMouseEnter={() => setHover(a.id)}
              onMouseLeave={() => setHover(null)}
              aria-pressed={selected?.id === a.id}
            >
              <span className="node-overline">
                {String(i + 1).padStart(2, '0')} /{' '}
                {a.kind === 'document'
                  ? hi
                    ? 'प्रमाण'
                    : 'EVIDENCE'
                  : hi
                    ? 'अगला कदम'
                    : 'NEXT STEP'}
              </span>
              <strong>{title(a)}</strong>
              <span className="node-impact">
                {new Set(a.opportunities.map((o) => o.id)).size}{' '}
                {hi ? 'जुड़े अवसर' : 'connected opportunities'}
                <ArrowUpRight size={14} />
              </span>
            </button>
          ))}
          {evaluations.map((e, i) => (
            <Link
              key={e.id}
              to={`/opportunities/${e.opportunity_id}`}
              className={`atlas-node destination ${active && actions.find((a) => a.id === active)?.opportunities.some((o) => o.id === e.opportunity_id) ? 'connected' : ''}`}
              style={{ left: 790, top: i * 180 + 55 }}
            >
              <span className="node-overline">
                {hi ? 'समीक्षित संस्करण' : 'REVIEWED VERSION'} {e.version}
              </span>
              <strong>{e.opportunity_title}</strong>
              <span
                className={`node-status ${e.status === 'not_eligible_on_known_facts' ? 'blocked' : ''}`}
              >
                {t.assessmentStatuses[e.status as keyof typeof t.assessmentStatuses] || e.status}
              </span>
            </Link>
          ))}
        </div>
      </div>
      <footer className="map-footer">
        <p>
          {hi
            ? 'प्राथमिकता वाले अधिकतम 6 कदम और 6 अवसर। पूरी सूची नीचे।'
            : 'Up to 6 priority steps and 6 opportunities shown. Full checklist below.'}
        </p>
        <div className="map-controls">
          <button aria-label="Zoom out" onClick={() => setZoom((v) => Math.max(0.4, v - 0.15))}>
            <Minus size={17} />
          </button>
          <output aria-label="Graph zoom">{Math.round(zoom * 100)}%</output>
          <button aria-label="Zoom in" onClick={() => setZoom((v) => Math.min(1.7, v + 0.15))}>
            <Plus size={17} />
          </button>
          <button
            aria-label="Fit graph to view"
            onClick={() => {
              setZoom(0.75);
              setOffset({ x: 0, y: 0 });
            }}
          >
            <Focus size={17} />
          </button>
        </div>
      </footer>
    </section>
  );
}
