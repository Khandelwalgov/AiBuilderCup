# AGENTS.md — Opportunity Intelligence Platform

> **Working codename:** Unclaimed (public product name undecided)  
> **Hackathon:** Google AI Builder Cup 2026 · **Theme:** Sustainability & Social Impact  
> **Submission target:** 18 October 2026  
> **Delivery principle:** A truthful, working end-to-end product beats an impressive-looking but unverified catalogue.

This file is the source of truth for coding agents and contributors working in this repository. Read it **before** proposing architecture, editing code, adding features, or creating demo data. When implementation conflicts with this document, explain the conflict and propose the smallest justified change; do not silently redefine the product.

---

## 1. Mission

**Opportunities should not depend on knowing where to look.**

Build an India-first, multilingual **opportunity intelligence and unlocking platform** that discovers programs and opportunities, checks their current requirements against authorized personal/family/business information, explains uncertainty, identifies missing evidence, and produces a practical path to application readiness.

This is **not** simply a government-scheme search engine, a generic RAG chatbot, or an automatic benefit-approval service. The product must connect:

`People / households / businesses → profile facts + evidence → verified opportunities + rules → eligibility evaluation → blockers → reusable actions → monitored changes`

### Product outcomes

1. **Discover** opportunities across trusted sources and geographic levels.
2. **Understand** benefits, requirements, eligibility, documents, deadlines, and constraints.
3. **Match** opportunities to individual people, households, and organizations, with permissions.
4. **Unlock** opportunities by identifying realistic, lawful next steps and shared blockers.
5. **Monitor** source changes and re-evaluate affected profiles when verified rules change.

A compelling demo should show **one new verified document or verified rule amendment changing several opportunity evaluations**, with transparent reasons and links back to official sources.

---

## 2. Product scope

### Supported subjects

- **Personal account:** Every authenticated user starts here. Authentication identity is separate from eligibility facts.
- **Person profile:** One human being, whether an authenticated user or a managed dependent.
- **Family / household:** Relationships, dependents, household memberships, and shared evidence **with permission**.
- **Business:** Any size or legal status—not limited to registered MSMEs. One person may administer multiple businesses; one business may have multiple authorized administrators.

### Supported opportunity categories

- Public welfare and social assistance; pensions and senior benefits.
- Child, school, healthcare, education, scholarship, grant, and financial-aid programs.
- Employment, skilling, agriculture, and livelihood assistance.
- MSME/startup/business incentives, grants, subsidies, and financing support.
- Government procurement, tenders, and supplier qualification.
- **International expansion:** scholarships, fellowships, and university aid, initially as a limited demonstration.

### Geography and applicability

- **Primary operational scope:** India (national → state/UT → district → local/institutional).
- Geographical scope must be modeled as **rules**, not just a location filter. Domicile, residence, business registration location, school location, and place of study can differ.
- Support multiple overlapping jurisdictions and institutional programs.
- **Architecture supports all categories; live coverage is never represented as comprehensive unless verified.** Show actual source and opportunity coverage in the UI.

### Accounts, families, and consent

- A user can have one **primary household shown in the MVP UI**. Do **not** encode a lifelong one-family constraint in the database.
- Model people independently, with `Person`, dated `HouseholdMembership`, and relationship/guardian records. Marriage, relocation, and household changes must not delete a person's history.
- Support **managed dependents** and **invited/connected adults**. Adult members explicitly authorize what another member can see. Kinship alone is never permission to view sensitive data.
- Household/family income is **scheme-specific**: never blindly sum everyone labeled “family.” Store relationship, period, income definition, source, and unknown values. Ask for clarification when necessary.
- Guardianship and dependent access are explicit; protect minors' information.
- A basic personal account is required before administering business profiles, but personal and business eligibility data remain logically separate.

---

## 3. Non-negotiable product behavior

1. **Never fabricate** an opportunity, source, official deadline, benefit amount, eligibility rule, approval, or application status.
2. **Show provenance:** official source URL, issuing authority, captured/extracted evidence, relevant clause/page where available, and last successful check/review.
3. **Separate fact from inference:** `verified source rule`, `user-supplied fact`, `verified document fact`, `AI inference`, and `unknown` are different states.
4. **Do not declare official eligibility or approval.** Label results preliminary / evidence-based; authorities make final decisions.
5. **AI does not silently publish policy changes.** New or revised requirements enter a review queue; an authorized admin approves publication.
6. **A crawl failure is not discontinuation.** A timeout, 403, CAPTCHA, rate limit, or missing response produces `source_unreachable` / `needs_review`, not `scheme_removed`.
7. **Humans remain in control.** Application submissions, notifications to third parties, and access to another adult's information need explicit authorization.
8. **Progressive profiling:** collect only what is necessary. If a rule requires information we do not have, ask for it instead of guessing.
9. **Unknown ≠ false.** Missing evidence does not imply ineligibility; a source's silence is not evidence of a requirement.
10. **Build for accessibility:** plain language, responsive/mobile-first UI, keyboard usability, understandable status labels, and accessible colors.

---

## 4. Product journeys

### Journey A — Citizen / household

1. User signs in, selects preferred language, creates a minimal personal profile.
2. User optionally adds a managed dependent or invites a family member with granular consent.
3. User enters domicile/current location, education and other relevant facts as needed.
4. The app discovers relevant opportunities and states why each may or may not match.
5. Uploading evidence resolves some unknown conditions; the application-readiness checklist updates.
6. A **shared blocker** (e.g. one missing certificate) appears across multiple opportunities, with a prioritized action plan.

### Journey B — Business / tender

1. User creates a business profile (registered, unregistered, micro, small, or large).
2. The system matches applicable business programs and selected tender opportunities.
3. It distinguishes **repairable document gaps** from **substantive disqualifiers** and unverified conditions.
4. It prepares a cited bid/readiness checklist, never an unsupported guarantee of qualification.

### Journey C — Continuous monitoring

1. A registered source is checked by a scheduled job.
2. A new notice or changed rule is detected and recorded as a **candidate version**.
3. Admin reviews source evidence and approves the version.
4. Affected opportunity matches are recomputed; users are shown an accurate change explanation.
5. Relevant users may receive opt-in alerts, subject to verified status and notification preferences.

### Journey D — International education (extension)

A student with an India-based profile explores a foreign institution's financial-aid policy. The system clarifies **potential relevance**, admissions dependencies, institution-specific requirements, and evidence gaps without promising an award or admission.

---

## 5. Signature feature: Opportunity Unlock Graph

The graph is **functional logic**, not decorative visualization.

Represent relationships among:

- Subject (person / household / business)
- Profile fact and supporting evidence
- Opportunity and **versioned** requirement
- Evaluation state and reason
- Blocking/missing prerequisite
- Action that might resolve one or more blockers
- Deadline, restriction, or mutually exclusive benefit

The planner should:

1. Evaluate all requirements for an opportunity against authorized, timestamped facts.
2. Identify shared requirements across opportunities.
3. Group redundant actions (e.g. a single document supporting several applications).
4. Prioritize actions using explainable signals: deadlines, reversibility, blocker count, effort, and opportunity relevance.
5. Keep actual disqualifiers distinct from evidence gaps or legitimate future scenarios.
6. Support **what-if simulations** that never mutate real user facts until explicitly saved and validated.

An action can **improve application readiness**, not make an applicant eligible by changing protected or immutable facts. Do not suggest manipulation of documents, misrepresentation, or unlawful workarounds.

---

## 6. Architecture — one monorepo, independent deployables

**Decision: monorepo.** Two developers, one cohesive product, one PR/review history, shared docs, and generated API types. Do not split into independent frontend/backend repositories for the hackathon.

- **Frontend:** React + TypeScript + Vite; Tailwind/shadcn-style accessible components if useful. Deploy static app to **Firebase Hosting**.
- **Backend:** Python + FastAPI + Pydantic; deploy container to **Cloud Run**.
- **Auth:** Firebase Authentication. The API validates Firebase ID tokens and enforces object-level permissions server-side.
- **Database:** PostgreSQL with SQLAlchemy + Alembic, locally via Docker Compose and in GCP via **Cloud SQL for PostgreSQL** (costs must be monitored).
- **Document blobs:** Google Cloud Storage with scoped access; only metadata and evidence pointers in PostgreSQL.
- **GenAI:** Google **Gemini** for multilingual interaction, document understanding, extraction, and explanations. Use the official Google GenAI SDK; add **Google ADK only if a genuinely tool-using flow benefits**.
- **Ingestion:** Python source adapters inside the backend codebase. Run batch commands as **Cloud Run Jobs**, triggered by **Cloud Scheduler**. Reuse the API image or Python package; no dedicated microservices required.
- **Background tasks:** Start with synchronous/simple job execution and scheduled batches; use Cloud Tasks/Pub/Sub only when actual workload demands it.
- **API contract:** FastAPI/Pydantic is authoritative. Export OpenAPI and **generate TypeScript API types/client**; never maintain inconsistent request/response interfaces by hand.
- **Observability:** Structured application/job logs, source run records, health checks, error handling; redact sensitive information.

**Avoid:** premature microservices, Kubernetes, a separate graph DB, an unnecessary vector database, complex multi-agent theatrics, unsupported scraping claims, and adding cloud services just for the architecture diagram.

### Repository structure

```text
/
├── AGENTS.md                       # this file — repository-wide instructions
├── README.md                       # local setup, architecture, demo, deployments
├── Makefile                        # friendly dev/test/contract/deploy commands
├── compose.yaml                    # local PostgreSQL
├── .env.example                     # names only, never secrets
├── .github/workflows/ci.yml        # focused lint/type/test checks
├── apps/
│   ├── web/                         # React + TypeScript + Vite
│   │   ├── src/
│   │   │   ├── app/                 # routing, providers, authentication
│   │   │   ├── features/            # profiles, family, business, opportunities,
│   │   │   │                       # matching, documents, action-graph, admin
│   │   │   ├── components/          # shared accessible UI primitives
│   │   │   ├── lib/api/             # generated client + thin API helpers
│   │   │   └── i18n/                # static EN/HI strings
│   │   └── package.json
│   └── api/                         # FastAPI + domain modules + job entrypoints
│       ├── pyproject.toml
│       ├── alembic/                 # versioned database migrations
│       ├── src/opportunity_platform/
│       │   ├── main.py
│       │   ├── core/                # config, auth, permissions, errors, logging
│       │   ├── db/                  # engine, sessions, common persistence
│       │   ├── profiles/            # people, user facts, consent
│       │   ├── households/          # membership, relations, guardians
│       │   ├── businesses/          # org data and user roles
│       │   ├── opportunities/       # sources, versions, rules, browse/search
│       │   ├── eligibility/         # deterministic evaluator
│       │   ├── evidence/            # uploads, extracted facts, validation
│       │   ├── planning/            # blockers, dependencies, next actions
│       │   ├── assistant/           # Gemini grounded explanations, tools
│       │   ├── ingestion/           # source connectors, parsers, diffs
│       │   ├── admin/               # review and publication workflows
│       │   └── jobs/                # daily discovery, refresh, re-evaluation
│       └── tests/
├── packages/
│   └── contracts/                   # generated OpenAPI schema (not hand-authored)
├── infra/                           # Cloud Run, Scheduler, Firebase deploy configs
├── data/fixtures/                   # clearly marked synthetic demo data
├── scripts/                         # seed, generate client, smoke tests, demo
└── docs/                            # schema, decisions, source policy, demo plan
```

No Nx/Turborepo is necessary. A root `Makefile` plus `pnpm` in `apps/web` and `uv` in `apps/api` is enough. Frontend and backend remain separately testable and deployable even though their code lives together.

### Local development workflow

1. `docker compose up -d db`
2. `cd apps/api && uv sync && uv run alembic upgrade head`
3. `cd apps/api && uv run uvicorn opportunity_platform.main:app --reload`
4. `cd apps/web && pnpm install && pnpm dev`
5. Generate the typed frontend API client from current backend OpenAPI whenever schemas change.

Make these commands work in `README.md` before adding large features. Never commit service-account keys, access tokens, user documents, or real identification numbers.

---

## 7. Canonical domain model

Design around these logical entities (naming can evolve, relationships must not disappear):

| Entity | Purpose |
|---|---|
| `User` | Login identity, language, notification preferences |
| `Person` | Individual eligibility subject, possibly managed rather than logged in |
| `Household`, `HouseholdMembership`, `Relationship` | Dated household composition and authorized kinship/guardian relationships |
| `ConsentGrant` | Which person/role can view or use which other person's facts/documents |
| `Business`, `BusinessMembership` | Organization profile plus owner/admin/editor/viewer permissions |
| `ProfileFact` | Typed value, validity interval, origin, confidence/verification, subject |
| `Document`, `EvidenceLink` | Encrypted file reference, extracted attributes, owner, approved uses |
| `Source`, `IngestionRun` | Authority, URL, connector, last success/failure, crawl policy |
| `Opportunity`, `OpportunityVersion` | Stable identity, category, jurisdiction, source, status, version history |
| `Requirement`, `RequirementEvidence` | Typed eligibility conditions with exact source passages |
| `MatchEvaluation` | Rule-level results, snapshot/version, status, missing facts, rationale |
| `ActionItem`, `ActionDependency` | Required/optional next steps and links to multiple opportunities |
| `ApplicationRecord` | User-maintained/authorized application stage; no fabricated government status |
| `Notification`, `AuditEvent` | Opt-in alert tracking and sensitive change history |

### Versioned opportunity records must capture

- Publisher/issuing authority, category, descriptive name, official apply URL.
- Jurisdiction and institution applicability; all relevant location dimensions.
- Effective date, open/close dates, expiry and supersession when known.
- Benefits, restrictions, exclusions, eligibility requirements, required documents.
- `source_url`, source content hash/snapshot pointer, exact extracted clause/page when possible.
- `first_seen_at`, `last_checked_at`, `last_successful_check_at`, `last_verified_at`, reviewer and publication state.
- Explicit status: `discovered`, `parsed`, `needs_review`, `verified`, `superseded`, `closed`, `source_unreachable` (do not collapse these).

### Eligibility engine contract

- AI converts documents into **structured candidate requirements** with provenance; admins review published rules.
- Deterministic code evaluates typed rules (`AND`, `OR`, comparisons, dates, locations, membership, evidence dependencies) without executing arbitrary expressions from crawled pages.
- Every requirement result is `satisfied`, `unsatisfied`, `unknown`, or `not_applicable`, with a reason and evidence references.
- Overall opportunity view distinguishes `potential_match`, `possibly_eligible_missing_information`, `known_blocker`, `not_eligible_on_known_facts`, and `ready_for_application_preflight`.
- Re-evaluations are **version-aware** and reproducible. Record rule version, relevant fact snapshot, and evaluation timestamp.
- Business, family and individual conditions use the same evaluator with **different subject contexts**, not separate hardcoded engines.

---

## 8. Ingestion and verification pipeline

**Source registry → discovery/fetch → snapshot → Gemini extraction → schema validation → deduplication → diff → review → publish → selective re-evaluation.**

- Prefer official APIs/feeds and public authoritative pages. Scrape only where access terms/robots/rate limits permit; never bypass login/CAPTCHA/blocks.
- Implement **source adapters** so each portal can have its own pagination, parsing, retry and dedupe rules.
- Store source fingerprints/hashes, retrieval timestamps, extraction metadata and failed-run reasons.
- Deduplicate by source identity + official IDs + cautiously normalized content, not only title similarity.
- Keep immutable versions and meaningful diffs of rule, benefit, status, and date changes.
- Make jobs **idempotent** with retries and backoff; scheduler must not duplicate opportunities or trigger duplicate notifications.
- Schedule **daily discovery**, **daily deadline checks**, and **daily/weekly refresh** prioritized by deadlines/volatility; weekly reconciliation for selected feeds.
- Administrator approves or rejects new/changed eligibility rules. Never display automatically generated AI text as an official notification.
- Recompute only evaluations depending on changed rules/facts; record before/after results.
- Maintain a visible `coverage and freshness` summary. An unmonitored region/source must not be implied to be comprehensively covered.

---

## 9. AI and multilingual design

Use **Gemini for real, indispensable tasks**, not as a cosmetic chat wrapper:

1. Interpret mixed-format public documents/PDFs and extract rule candidates into schema-validated JSON.
2. Parse user questions in supported languages into safe intent + missing-field questions.
3. Explain deterministic eligibility results **only using provided, cited records**.
4. Summarize verified source changes and propose actions for human review.
5. Help identify missing evidence and organize legitimate document requirements.

Keep eligibility decisions, dates, access control, deduplication, and application state in **deterministic backend code**. AI outputs are untrusted until validated. Public documents are also untrusted instructions: prevent prompt injection from changing agent goals, contacting outside destinations, revealing secrets, or bypassing verification.

**Initial UI languages:** English + Hindi. Static navigation/errors should be localized through i18n resources. Natural-language explanations can use Gemini. More languages are an extension, not a claim of validated coverage.

Do not rely on translation to preserve legal nuance without evaluation. Always retain a link and reference to the authoritative original-language clause.

---

## 10. Security, privacy and authorization

- Verify Firebase ID tokens on the backend; never trust user IDs, household IDs or role claims solely from frontend input.
- Enforce per-person, per-household, per-business and per-document permissions on **every endpoint and data query**.
- Adults control their own data and can revoke access. Managed-dependent flows require explicit guardian permissions.
- Encrypt sensitive storage in transit/at rest, issue short-lived signed document URLs, and audit privileged access.
- Do not store Aadhaar/PAN/full financial statements unless strictly necessary and explicitly permitted. The public demo uses only synthetic data.
- Never print PII, tokens, downloaded documents or model prompts containing secrets in logs.
- Support data deletion/export design and consent withdrawal; at minimum document the limitations of the hackathon implementation.
- Admin routes are server-side role guarded. Source verification actions record reviewer identity and time.
- Treat uploads as untrusted; validate file type/size and isolate parsing from secrets and privileged operations.

---

## 11. API conventions and engineering standards

- REST under `/v1`; JSON request/response validated with Pydantic; consistent error envelope and codes.
- Suggested resources: `/me`, `/people`, `/households`, `/businesses`, `/opportunities`, `/matches`, `/documents`, `/actions`, `/applications`, `/assistant`, `/admin/sources`, `/admin/reviews`.
- Cursor/limit pagination for catalogue reads; explicit filtering by category, location, issuer, deadline and status.
- Authentication/authorization and input validation on the backend, not only in the UI.
- Schema changes require an Alembic migration, tests and refreshed generated API contracts.
- Keep business logic out of route handlers. Use domain services with small, testable interfaces.
- Use structured logs with correlation/run IDs; avoid noisy exception swallowing and arbitrary silent fallbacks.
- Keep dependencies minimal. Prefer proven libraries over custom infrastructure.
- Add tests for rules, family permissions, source ingestion, version changes, and the demo critical path.

### Minimum test matrix

- National + Rajasthan + Dausa opportunity matching with different domicile/residence rules.
- Adult family member refuses sharing; parent cannot access their private documents.
- Scholarship parental-income rule versus a different household-income definition.
- Unknown income/document → **unknown**, not rejection or approval.
- Missing document shared across several opportunities → one prioritized action.
- Real disqualifier remains disqualifier after adding an unrelated document.
- Verified source amendment → new version and affected user re-evaluation.
- Source 403/timeout → last verified opportunity preserved, freshness warning added.
- Prompt injection in crawled PDF → no secret leak, tool misuse, or fake verification.
- Non-admin cannot verify opportunities or read privileged ingestion runs.

---

## 12. Hackathon execution priorities

**Submission deadline: 18 October 2026.** Optimize for a reliable, live, three-minute demonstration. Scope is deliberately narrower than the eventual universal platform.

### P0 — must work end-to-end

- Firebase login, individual profile, one household with a managed dependent, and one business profile.
- Curated **real official sources**, traceable data, India-ready geography model; truthful actual coverage count.
- Opportunity search/browse/detail with full sources and timestamps.
- Source ingestion for at least one live accessible official source; admin review and version diff.
- Deterministic requirement matching: satisfied/unsatisfied/unknown, grounded explanations.
- Shared blocker analysis, action checklist and a **functional Opportunity Unlock Graph**.
- One controlled, repeatable source-change / new-evidence re-evaluation demo.
- English/Hindi questions and grounded answers through Gemini.
- Deployed web + API on Firebase Hosting + Cloud Run; documented, reproducible setup.

### P1 — add only when P0 is stable

- Connected adult invitations and granular consent UI.
- Secure document upload + extraction, ideally with synthetic PDFs for the demo.
- Scheduled Cloud Run Job actually executing, plus monitored run history.
- Real sourced MSME example and a real sourced tender example.
- Email/in-app change alerts with opt-in controls.
- One international scholarship/institutional aid example.

### P2 — post-hackathon

- Wide-scale multi-source cataloguing, broader districts/states/institutions, and stronger freshness SLAs.
- Advanced document validation, multilingual quality evaluations, and household lifecycle transitions.
- Authorized official submission integrations and cross-portal application tracking.
- Dedicated tender workflows, partner integrations, and additional countries.

Do not claim P1/P2 capabilities work when they have not been built. A seeded demo is acceptable **only if explicitly labelled synthetic**; real sourced records need visible source provenance.

### Demo narrative (about 3 minutes)

1. Set up a family and business; show **individual vs household-aware** matching.
2. Open two real opportunities and inspect rule-level citations and remaining unknowns.
3. Show a shared evidence blocker across both and a prioritized next action.
4. Add a **synthetic but clearly labelled** supporting document/fact, then re-evaluate live.
5. Show an administrator-approved rule-version change from a sourced document and its downstream impact.
6. Ask in Hindi why a requirement is or isn't satisfied; show an evidence-grounded explanation.

### Definition of done

A feature is complete only if it has working UI + backend + persistence where needed, server-side permissions, correct empty/loading/error states, traceable data, one meaningful test, and is reachable in the deployed prototype. A convincing screenshot does **not** count.

---

## 13. Working agreement for agents and contributors

**Before coding:**

1. Inspect existing code and current decisions; do not duplicate implementations.
2. State the smallest vertical slice that solves the requested problem.
3. Identify source data and any security/consent implications.
4. Preserve architecture boundaries; add infrastructure only when needed.

**While coding:**

1. Prefer small, reviewable changes; keep API and web contracts synchronized.
2. Never hardcode fabricated opportunity metadata to appear real.
3. Never skip auth, permission checks or verification for convenience.
4. Write tests for rule and privacy edge cases.
5. Record non-obvious architectural choices in `docs/decisions/`.

**After coding:**

1. Run relevant format/lint/type/test commands and report exactly what ran.
2. Update migrations, OpenAPI-generated types and environment examples as needed.
3. Verify at least one real user path end to end locally or on deployment.
4. Report known gaps explicitly; never describe partially built functionality as finished.

**When uncertain:** Preserve user safety, source fidelity, explicit unknown states, small scope, and the live demo path. Ask for a product decision only if the decision materially changes behavior or risks breaking an existing workflow.

---

## 14. Success measures

Evaluate the prototype on a documented, labeled set of representative opportunities and synthetic profiles:

- **Rule extraction accuracy** and percentage of claims backed by correct official clauses.
- **Eligibility classification correctness**, especially unknown vs ineligible distinctions.
- **Missing-document precision** and correctness of action dependencies.
- **Source-change detection accuracy** and duplicate/idempotency handling.
- **Time to an actionable, cited checklist** compared with manually navigating sources.
- **Privacy/permission tests passed**, not merely privacy statements written.

Never invent impact numbers, approval rates, eligible-benefit totals, model accuracy, or production coverage. Measure and report what the working implementation actually achieves.

---

**One-line reminder:** Build the system that **finds, explains, and helps unlock verifiable opportunities**—not one that merely lists schemes or confidently guesses who qualifies.
