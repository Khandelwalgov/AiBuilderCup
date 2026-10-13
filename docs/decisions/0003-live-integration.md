# 0003 — Bounded integrations and explicit releases

Phase 2.5 preserves the existing monorepo and reviewed-publication boundary. No new platform features or graph implementation are introduced.

The Gemini extractor retains the official SDK's GenerateContent structured JSON-schema interface and configured `gemini-3.8-flash` model. Deprecated sampling configuration is removed. A separate countTokens request includes instruction/schema text plus a 1,024-token framing reserve; this is a conservative input guard, not an exact billing estimate. Developer API countTokens does not accept `system_instruction` configuration in the locked SDK. Each request has a 120-second timeout and one attempt. Output is bounded to 16,384 tokens and accepted only after STOP, schema validation and exact page-quote checks. Model acceptance/output quality remain unverified without a real key.

Candidate extraction/insertion runs in a savepoint so known model failures and unexpected candidate errors retain captured source pages and sanitized run diagnostics. A process crash/database outage can still roll back the outer transaction; this is not a durable asynchronous job system. A nonblocking advisory lock rejects overlapping runs for a source rather than tying up API connections waiting for a lock.

Production settings fail closed for development catalogue/default local database/invalid CORS. Existing Firebase Admin app project must match backend settings, and bootstrap requires an explicit matching `--project-id`. Bootstrap remains a privileged operator action, not an HTTP role-grant endpoint.

Cloud releases use a plan-first runner, explicit project, pinned secret versions, separate migration identity and migration-before-service order. Public Cloud Run invocation serves the catalogue; Firebase protects private routes. No credentials, cloud resource provisioning or deployment authorization is inferred from a local CLI default. Actual deployment is not validated in Phase 2.5; see the validation record for external blockers.
