# Profile UX and persistence — 16 October 2026

The reported schema editor was reproduced before changes in `.live-validation/product-profile-before.png`. Topic chips created batches of unknown facts; certificate fields inherited income inputs; returning users saw the editor; repeat saves replaced fact rows. The new flow keeps the existing Opportunity OS design.

## Guided questions

`apps/web/src/features/profiles/questions.ts` owns EN/HI labels, typed mappings, categories, goal relevance, choices, help, numeric limits and visibility predicates. Questions are optional; a name/nickname is required to create the profile. Interests control the initial questions and do not become eligibility facts. Public discovery is reachable without completing setup.

| Representative goal | Initial details after name/interest | Conditional additions | Required eligibility answers |
|---|---|---|---|
| Explore/general | Age, permanent-home state | None | None |
| Work/livelihood | Age, permanent-home state, work situation | None | None |
| Education, student unknown/no | Age, permanent-home state, student status, current/highest education | None | None |
| Education, undergraduate student | Same four | Study mode | None |
| Education, school-class student | Same four | Study mode and school recognition | None |

Thus name plus an optional interest selection and 2–6 optional questions replace the flat 17-field editor. Income, disability, residence district, nationality and business information are absent from initial onboarding. They are available through relevant section editing or a supported published requirement. Country selection maps “Indian” to `IN` internally. Unknown/skipped fields are not expanded into rows. Review shows answered facts; specific opportunity conditions remain visible as unknown when needed.

The automated real local learner journey measured approximately one second including emulator login, with two answers saved and three visible optional questions skipped. This is machine execution, **not a human completion-time measurement**. The two-minute usability target requires the timed human checklist in `real-user-acceptance.md`.

A returning person sees saved name, last-save time, answers by category, document summary and next actions. Edit opens one category; Cancel discards only after confirmation. A source-linked missing-age action was exercised from a published fictional requirement through its captured citation, exact age question, save and re-evaluation. Unsupported rule semantics are never converted into legal questions by an LLM. Document keys route to the vault, not certificate Boolean or income forms.

## Consistency and preservation

Active “not a student” plus enrolment/school details is rejected; undergraduate/postgraduate plus current school-recognition details is rejected. Changing a parent answer prompts before clearing its active dependent answers. Cancel preserves everything. Historical dated education facts do not create current contradictions. Unrelated and verified/document-sourced facts survive edits. Existing validity dates appear only when a saved answer has a window. No date-of-birth fact is implemented; age-versus-DOB consistency is consequently not claimed.

Only annual parental/personal income and business turnover use income period/definition controls. A certificate never does. Income comparisons remain unknown if scope/period does not match; family income is never guessed or summed.

## Save model

Explicit states: new, unsaved, saving, saved, failed, conflict. Save is disabled when unchanged or pending. Inputs are disabled while saving, and the submitted payload is captured. Successful save returns to summary with no redundant active Save. Failure preserves answers and offers retry. Navigation/context changes use the shared discard guard. Background refetch does not replace dirty input. A conflict preserves the draft and offers explicit reload, returning to the newer saved summary.

Backend reconciliation updates changed editable rows in place and preserves unchanged IDs/provenance. Omitted editable facts are removed only when explicitly submitted that way; verified facts are excluded from editable replacement. Identical saves do not add audit/re-evaluation churn. Optional `expected_revision` maintains older client compatibility; the new personal, dependent, household and business editors send it. Actor/subject row locks serialize writes and revision checks reject stale edits with 409. Legacy clients omitting the revision do not gain optimistic-conflict detection.

Tests include actual PostgreSQL repeat/partial/stale saves, two concurrent transactions, historical dates, dependent/business persistence, and two actual browser tabs demonstrating one winner, preserved stale draft, reload and a single pending submission.
