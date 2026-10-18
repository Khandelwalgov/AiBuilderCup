# Unclaimed submission freeze audit — 18 October 2026

The deployed prototype is accessible, but the submission is **not ready**. The final PDF deck,
public demo video and publicly accessible repository are outstanding; genuine Gemini policy
extraction has not yet succeeded. Do not substitute passing mocks or hosting for qualifying
Google GenAI evidence.

## Cutoff and organizer requirements

The [organizer timeline](https://aibuildercup.com/) confirms **18 October 2026** but gives no
exact submission time or timezone. The public FAQ and linked terms were also checked; the
signed-in submission dashboard cutoff was not verified. The operator reports **11:59 p.m.**
and directs an internal **8:30 p.m. IST working cutoff** today. Treat that working cutoff as
binding; do not infer that time from the public site or claim independent verification.

The [requirements](https://aibuildercup.com/themes.html) call for a PDF presentation, deployed
working prototype, public video and Google AI integration. The [FAQ](https://aibuildercup.com/Faqs.html)
explicitly requires a public GitHub repository and a video under three minutes. The
[linked terms](https://docs.google.com/document/d/e/2PACX-1vRm7ChZ6Ij9fG7uFDkxzUMpwgVeBmnQ6cMDnAIEEX84AiLBOOQ9cYbl3S5OzFBbcVb8TF55s-eVpiXb/pub)
instead say the video must be three to four minutes. **This is an unresolved organizer
conflict**, not permission to ignore the user's maximum-three-minute limit. Confirm with the
actual submission instructions/organizer; no support message was sent on the user's behalf.

## Actual artifact status

| Required item | Checked result | Remaining work |
|---|---|---|
| PDF presentation | Operator confirms no deck created. Existing Downloads file is only `Submission Template _ AI Builder Cup.pptx`. No final PDF found in the repository. | Create/export/review the submission PDF using the template and accurate measured claims. |
| Public demo video | Operator confirms not made; no public video link supplied. | Record a truthful demo, validate duration/accessibility and resolve the organizer length conflict. |
| Public repository | Configured `https://github.com/Khandelwalgov/AiBuilderCup` returns HTTP 404 to unauthenticated GitHub API access. This does not distinguish private/deleted/renamed, but it is not public-access proof. | Separately authorize any push/visibility change or provide the correct public URL; verify incognito access. |
| Working prototype | `https://unclaimed-ai-cup.web.app` and API `/health` return 200. Read-only metadata confirms Cloud Run `opportunity-api-00013-zoj` at 100%, Hosting `375a1c14fd8ab1fe`. | Preserve the deployed release; no redeployment needed for this audit. |
| Google GenAI evidence | Prior real smoke 504 and three document-generation 400s, including the separately authorized bounded-schema attempt from commit 86075e0; no successful extraction/review. | Approve one bounded request only after reviewing the offline transport report. |
| Secret audit | 852 reachable selected text blobs checked for configured backend keys and PEM material: zero findings. This is a scoped scan, not proof that every possible historic secret is absent. | Scan the final export/new artifacts before any separately authorized public push; exclude environments, ignored corpus, credentials and private user documents. |

Production remains commit `038594fb823136e6468cfaef79cd80e503800a0c`, with **96 research listings,
six unpublished policy versions and zero published eligibility policies**. The 11 programme
parents have provisional cited comparisons; they are not 11 approved eligibility policies.
Earlier hosted personal Discover, source-page, scenario/reset and reversible plan acceptance
passed. Authenticated acceptance was not repeated in this offline audit. Production uses
Neon; older Cloud SQL preparation notes are not the current architecture.

## Freeze boundaries

Only this existing coding agent is working. No production catalogue changes, ingestion/OCR,
model rebuild, Docker build, deployment, IAM/billing mutation, scheduler activation, paid AI,
policy publication or remote push is authorized by this audit. Preserve the existing release
and rollback records. Pending monitoring work stays lower priority until genuine Gemini and
submission-critical tasks are resolved; a future cron command is not an active job.

Next: finish the bounded offline Gemini validation, obtain exact one-request authorization,
then prepare the deck/video with truthful evidence. Do not claim extraction, independent AI
review, current application rounds, complete coverage, official eligibility or measured impact
unless those outcomes were actually demonstrated.
