# Product completion audit — 16 October 2026

The user-reported onboarding defects were reproduced against the old component, then repaired in the existing theme. This audit records implementation and observed behavior, not a claim of production readiness. All new private-data exercises used fictional accounts/documents; official candidates stayed untouched.

| Journey | Concrete outcome / repair | Evidence level and remaining limit |
|---|---|---|
| Public entry/discovery | Browse without creating a profile; truthful empty real coverage, source links and filters retained | Actual public API/browser; no new official publication |
| Google sign-in/account initialization | Existing Google flow retained; unnamed signed-in users no longer say Public browsing; backend identity initialization retained | Actual official Firebase **Auth emulator** tokens/browser/API; real Google popup and hosted domain acceptance still human |
| Personal creation | Name/interest, short goal-dependent questions, answered-only review, saved summary | Real browser/API/PostgreSQL; conditional contradictions also browser contracts |
| Returning/editing | Section edits, last-save state, no redundant Save, explicit discard/retry/conflict reload | Real browser failure/reload/two-tab stale edit; stable IDs/audit and simultaneous transactions in PostgreSQL |
| Missing information | Published requirement/citation → exact supported question → save → age requirement satisfied | Real fictional publication/API/browser; unsupported semantics remain unknown |
| Fresh/renewal | Existing explicit application context and context-sensitive rules preserved | Database and browser contract regressions; no real application claim |
| Family creation | Name-first household; overview separate from editing/dependent addition | Real emulator/API/database |
| Managed dependent | Own questionnaire/profile/document links; explicit guardian confirmation; self member labeled correctly | Real dependent age edit, PNG upload, unrelated-account denial and revocation |
| Adult sharing | Kinship never grants private access | Negative database/API test; invitations/consent UI still deferred |
| Business | Minimal unregistered creation; optional location/registration; separate edit overview; no forced turnover/identifier | Real creation, edit/reload semantics, PNG and personal-context isolation; role checks in API tests |
| My Documents | Actual private PDF/JPEG/PNG, metadata, retry, preview/download, replacement/removal and expiry display | Real local files/PostgreSQL/browser; GCS adapter not live-tested; production uploads blocked |
| Requirement linking | Direct upload action, current immutable version links, explicit reuse across exact compatible requirements | One PDF shared by two fictional opportunities, actual byte download; incompatible income scopes/version change API tests |
| Eligibility | Uploaded evidence changes documentary readiness without authenticated/verified fact or legal decision | Actual unknown legal results before/after upload; existing typed evaluator retained |
| Unlock Graph/checklist | One shared action links two opportunities, documentary status, source clauses, relevant question/file links; evidence panel stacks links legibly | Actual real local graph capture; task progress contract and DB regressions |
| What-if | Existing nonmutating age-correction simulation retained | Database/browser contract; no general scenario engine or profile mutation |
| English/Hindi explanations | Existing deterministic cited explanation and optional Gemini intent path retained; new static forms/statuses translated | EN/HI browser captures/contracts; no live Gemini call, source passages and some backend errors retain original language |
| Settings/privacy | Current-subject vault/removal link; immediate access removal and retry/preserved minimal history explained | Implemented and browser regression; full account export/erasure unavailable |
| Admin ingestion | Existing operator gate and explicit provider/model confirmation retained | Mocked browser confirmation + backend denial/staleness tests; no actual ingestion/model call |
| Candidate corrections/review | Existing structured editor/evidence/review retained | API/database/browser contract; no changes to either real draft |
| Publication/change | Immutable versions; historical document links not silently applied to new period/version | Isolated synthetic version switch and existing admin workflow tests; no real publication |
| Source evidence/freshness | Existing official snapshot/page citations retained; failure is not discontinuation | Read-only actual-draft audit; source-fetch tests mocked, live-fetch test deliberately skipped |
| Error recovery | Draft preservation, failed upload retry after refresh, quota replacement, purge retry, missing/stale permission states | Browser transport interruption forwards successful retries to actual API; storage failures injected in integration tests |

## Usability review

Viewed actual captures of initial, incomplete, edited/saved profile, vault/preview, shared graph and family/business states. EN desktop and HI mobile exercise the new flow. Fixed raw certificate/income coupling, false unsaved/saved loops, owner duplication, source follow-up mismatch, StrictMode upload cancellation, localization of post-upload feedback, short-screen navigation overflow and a squeezed multi-link evidence panel. Screenshot assertions wait for actual content/fonts/images, reset scroll and check horizontal overflow; screenshots alone are not the persistence evidence.

The existing browser regression suite includes mocked authenticated data and actual public pages. The separate product suite uses actual emulator authentication, API routes, PostgreSQL, temporary private files and synthetic published requirements. No production authentication override exists. See `product-completion-report.md` for final commands/counts and `real-user-acceptance.md` for the remaining human gates.
