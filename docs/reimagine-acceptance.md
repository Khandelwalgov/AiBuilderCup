# Reimagine acceptance — 15 October 2026

Engineering acceptance is local. No deployed or real Firebase-authenticated acceptance is claimed.

| Criterion | Executed evidence | Result / boundary |
|---|---|---|
| Logo from Settings → canonical home, correct breadcrumb/active navigation; menu same URL; Back/Forward/refresh | `reimagine-navigation.spec.ts`, actual ApplicationFrame with fictional session, guest + signed-in, Hindi/mobile | Passed |
| Auth initialization and private cache boundaries | Ready-delay browser test, profile/account-switch/sign-out fixture; sanitized sign-in-error test | Passed fictional contracts; real Firebase popup and callback hook inspected, not accepted with a live account |
| Global authorized person/dependent/household/business context | `reimagine-context.spec.ts`, URL/options/request assertions; hidden adult and unavailable UUID | Passed |
| Eligibility honors subject and fresh/renewal, rejects unsupported safely | Browser 4subjects×2application-type requests; real ASGI owner/dependent facts, stranger denial; existing fresh/renewal and workspace tests | Passed; browser unsupported results mocked, server behavior real isolated DB |
| Cross-origin PATCH | Allowed/disallowed Origin OPTIONS via actual FastAPI middleware plus action API authorization/persistence tests | Passed; deployed frontend origin not tested |
| Dirty forms and account switch | Explicit query invalidation refresh while editing, declined navigation, account remount, sign-out; code audit other form guards; candidate hash/concurrency server tests | Passed tested paths; no browser crash recovery/local draft storage promised |
| Progressive profile, family/business create/edit | Minimal age save; missing-field-only followup; household PUT, dependent POST, unregistered business flows | Passed fictional browser + real server persistence tests |
| Functional graph, task update, simulation | Action/evidence selection, connected edges, opportunity inspector, arrow-key pan, measured zoom/fit, PATCH, hypothetical facts | Passed; mobile uses complete checklist, no canvas panning |
| Assistant condition anchor | Browser local answer → stable published source requirement anchor | Passed with mock answer; live Gemini disabled |
| Ingestion safeguards | Dialog shows actual configured settings; disabled flag prevents POST; negative server gates replace entire ingestion service with fail-fast stub | Passed; zero live ingestion/model calls |
| Evidence reader and publication | Public68page-copy search/page navigation; missing cited999page explicit error/manual recovery; synthetic approve second dialog; isolated saved-source review/version tests | Passed without changing real drafts |
| Visual redesign / responsive localization | Before120 and after 89 PNGs; ten required screens EN/HI at1440/1024/390/320; representatives visually viewed, two refinements documented | Passed local visual review; original source/free text remains original language |
| Contracts, preflight, backend/frontend checks | Logs linked in final report | Passed; one live-provider test intentionally skipped |
| Container + local smoke | Fresh no-cache API image, temporary local container health/catalogue/private401 checks; existing local API public smoke | Passed; no deployment |
| Saved real draft integrity | Read-only SQL/Pydantic exact citation validation, compared to saved public fixture | Both still draft, unchanged hash/pages/candidate;36 + 34 citations;3 + 1 reviews;0 published real |

## Human acceptance still required

1. Open the local app and sign in using your existing Firebase account. From Settings, click the logo; confirm Overview, then change an authorized subject and repeat on Detail/Plan. Test a cancelled dirty-form navigation.
2. As your existing authorized reviewer, inspect each saved DEPwD draft and its full source bundle. Decide substantive corrections/completeness and whether to publish. No approval was supplied by this sprint.
3. Leave live ingestion disabled unless you deliberately authorize a provider call and accept the configured cost boundary. Optional budget is not a billing cap. Gemini remains the default path; your local explicit OpenAI provider setting was retained.
4. Deployment remains a separate future authorized task; no cloud provisioning, billing change, Git push or publication occurred.
