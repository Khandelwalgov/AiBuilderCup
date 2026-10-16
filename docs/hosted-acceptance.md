# Real hosted acceptance — operator checklist

**Not executed against hosted services in this sprint.** Local emulator, mocked tests, Docker validation and public health checks do not establish live Google Sign-In or hosted product acceptance. Paid generation/ingestion are off; no Gemini/OpenAI acceptance is claimed.

Use project `venuesignal`, existing Firebase Web app `AiBuilderCup`, Hosting site `unclaimed-ai-cup` and region `asia-south1`. The project Auth domain remains `venuesignal.firebaseapp.com`; it is not the frontend URL.

Record approved project, reviewed Git SHA, image digest, migration head, actual API/Hosting URLs, browser/device, timestamp, testers and result for each item below. Use two dedicated Google accounts with fictional profile values; do not upload real identity or financial documents. Keep tokens, UIDs, private screenshots and test-account details out of public GitHub artifacts. A source record may be inspected, but never publish/approve an opportunity as part of this checklist.

## Public deployment and safety checks

1. Open the Hosting root, `/profile`, `/discover` and `/scenarios` directly and refresh each. SPA routing and TLS must work. An unauthenticated protected route asks for sign-in without leaking a cached prior account. Confirm the build points at the intended API/project, with no emulator banner/test login page.
2. Run `python3 infra/smoke.py --api-url https://ACTUAL.run.app --hosting-origin https://unclaimed-ai-cup.web.app --hosting-origin https://unclaimed-ai-cup.firebaseapp.com`. It checks `/live`, DB `/health`, catalogue shape, no synthetic/unreviewed items, production `development=true` denial, unauthenticated identity/profile/workspace/admin/search/scenario denial (401), invalid bearer denial, allowed CORS and untrusted-origin rejection.
3. Inspect deployed revision environment/secret **references** in restricted Console. Confirm production, matching Firebase project/CORS, fictional catalogue false, document uploads false, ingestion false, assistant live generation false, Gemini provider default, numeric DB/signing secret versions and no emulator host/OpenAI/AI key. Never export full service metadata to a public report.
4. Confirm the default read-only Neon schema gate reports `f24a1000abcd`, no initialization/seed/upgrade ran, runtime SQL role lacks DDL and migration credentials differ. Cold-start `/health` after scale-to-zero should become healthy within the configured startup window. Observe connection counts/error logs while using search/scenarios; no billing/model call should occur.

## Actual Google Sign-In and persistence

1. In a new browser profile, click the actual Google sign-in button, select **Account A** and complete Google's own consent/login. Verify Console authorized domains/provider/support email and backend project match if it fails. The emulator login page cannot substitute for this.
2. Confirm `/v1/me` returns Account A's expected Firebase UID, non-admin role, and the backend accepts an ID token issued by the intended project. Merely decoding a JWT locally is not verification; the API verifies signatures/project/expiry/revocation. Do not print/store the token in logs.
3. Create a minimal **fictional** personal profile, save a benign fact, hard refresh, sign out/in and verify persistence. Edit age or education and verify the known/unknown distinction, stable facts and visible save/revision behavior. This profile write is an explicit tester action, not performed by the smoke script.
4. Create one fictional household and managed dependent with explicit guardian confirmation, then one fictional business using its own registration/operating/turnover context. Refresh and verify each survives. Do not invite another real adult or imply kinship grants access; connected adult consent remains limited by implemented support.

## All five search contexts

| Mode | Required observation |
|---|---|
| Just Me | Uses A's actual person facts even when another workspace was previously selected. |
| My Family | Household plus authorized members; each result identifies the actual member and keeps household rules separate. A known failure for the parent cannot be hidden by a dependent's potential match. |
| Specific Family Member | Explicit dependent/person selection, exact same member retained through detail → eligibility → plan → grounded assistant. |
| My Business | Business-only typed facts; personal/parental income never substitutes for turnover or business registration. |
| Explore All | Complete paginated reviewed real catalogue; incomplete profile does not hide records. Full browse remains accessible when recommendations are truncated. |

Try query/category/state/district filters. National opportunities must remain visible when national inclusion is enabled. Verify cited original clauses, dates, unknown conditions, known blockers and shortlist coverage notices. **The current saved real dataset has no published opportunities:** empty states are a valid deployment check but do not pass populated-result/matching acceptance. Those cells remain **blocked pending separate substantive human review/publication of real policies**; never publish drafts just to make this checklist green. Local fictional acceptance covers the populated mechanics only.

## Scenario non-persistence and comparison

1. Record A's current profile/workspace facts and existing evaluations/actions without triggering new persisted checks/plans. In Studio choose that actual authorized base. A no-change scenario should report unchanged assessments.
2. Override income by a very large amount, then around a cited exact threshold. Preserve personal/parental/household/turnover definitions and periods. Unknown or mismatched definitions must stay unknown; adding unrelated evidence cannot fix a substantive known failure.
3. Add a **fictional** spouse/child/dependent with temporary facts and optionally exclude an authorized member from this scenario. In a family base, edit members separately. Review actual/future differences, newly retrieved candidates, cited conditions, shared actions and known blockers. A newly retrieved item is not an official entitlement; a shortlist omission is not automatic ineligibility.
4. Where published data supports it, verify a temporary household/new person can retrieve a policy absent from the actual personal shortlist. If catalogue coverage cannot demonstrate this, mark the populated-data step pending; do not fabricate it.
5. Reset/discard, navigate away, refresh, reopen personal/family/business pages and verify actual facts, memberships and documentary verification remain unchanged. No scenario becomes a persisted evaluation/action or assistant ID. The local commit-after-simulation DB test proves service-level behavior, but this hosted step still needs operator execution.

## Hindi, mobile and accessibility

Switch interface language to Hindi; verify navigation, context selection, Studio controls, loading/error/empty states and reset. Preserve original authoritative passages and do not claim legally validated translation. Test ~390px viewport, touch controls, no horizontal overflow, keyboard-only context selection, visible focus and screen-reader labels. The graph's narrow-screen text checklist should expose the same actions without a dense diagram. Record layout issues; do not redesign the product as part of deployment acceptance.

## Cross-account and revocation boundaries

1. Open a separate browser profile as **Account B**. B must not see A's private names, facts, documents or cached recommendations after sign-out/account switching.
2. Using A's actual person/dependent/business ID, B's direct API request must return generic 404/403 (for search/scenario subject resolution this implementation uses 404). Test both `/v1/search` with member/business selection and `/v1/scenarios/evaluate` with A's base. Unauthenticated requests must be 401.
3. Revoke the test dependent's guardian access through the implemented A flow; old detail/assessment/document references must fail on subsequent access. Another adult's refusal/absence of permission must not contribute to family retrieval.
4. Non-admin A/B must receive 403 from admin reviews. No upload/verify/review/publication button should bypass server authorization. Production uploads should fail even if a forged client request tries to enable them.

## Optional authenticated API smoke — private local tokens

After both dedicated accounts exist and A has a saved fictional profile, save fresh Firebase ID tokens from the **actual hosted sessions** in temporary private local files outside the repository. Use a trusted private developer console; never copy bearer tokens into shell arguments, tickets, screenshots or GitHub variables. The following commands refer only to file paths/public identifiers:

```sh
chmod 600 /PRIVATE_TEMP/account-a.token /PRIVATE_TEMP/account-b.token
python3 infra/smoke.py --api-url https://ACTUAL.run.app --hosting-origin https://unclaimed-ai-cup.web.app --hosting-origin https://unclaimed-ai-cup.firebaseapp.com --token-file /PRIVATE_TEMP/account-a.token --second-token-file /PRIVATE_TEMP/account-b.token --expected-uid ACCOUNT_A_EXPECTED_FIREBASE_UID
rm /PRIVATE_TEMP/account-a.token /PRIVATE_TEMP/account-b.token
```

The script checks the intended non-admin identity, actual authenticated search/scenario responses, private cache headers, no-change scenario comparison, unchanged profile/workspace API snapshots, denied cross-account member/scenario requests and denied admin access. It does not create profiles/workspaces, invoke models, publish policies, upload documents or save evaluations/actions. It does not prove all database tables unchanged in hosted production; combine API snapshots with the browser checks and, if authorized, a scoped private database audit. Use fresh tokens; token expiry/revocation is a failure to resolve, never a reason to bypass Firebase.

## Acceptance record and remaining gates

Use `PASS / FAIL / BLOCKED / NOT RUN`, with actual evidence. Report public smoke, authenticated API smoke, Google Sign-In, populated catalogue behavior, scenario non-persistence, mobile/Hindi, cross-account denial and rollback rehearsal independently. A healthy empty catalogue is not a verified end-to-end opportunity demonstration. No successful hosted acceptance, Google provider call or paid model call has been recorded by this release-readiness assignment.
