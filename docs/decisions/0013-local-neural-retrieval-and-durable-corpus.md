# Local neural retrieval and durable public-corpus workers

17 October 2026.

The user's selected Neon architecture supersedes AGENTS.md's original Cloud SQL hosting choice. Firebase Hosting and the existing Cloud Run API remain independent deployables. No Cloud SQL, graph database, vector service, extra model service or service-account JSON key is introduced.

Authenticated Discover and the homepage automatically retrieve from the saved personal profile, with an empty query. Explicit Explore All stays public. For at most 150 published versions, every applicable authorized subject–policy pair is assessed, independently of neural shortlist limits. Family permissions and exact deterministic rules remain authoritative; vectors never decide eligibility.

Use the Apache-2.0 multilingual MiniLM quantized ONNX export, pinned by repository revision and SHA-256, with CPU-only ONNX Runtime and tokenizers. The container bundles weights; serving makes no hosted embedding request. The tokenizer's exported truncation/padding is disabled before bounded 126-token chunking and mean pooling. Policy representations are version/source/text/model keyed. PostgreSQL JSON vectors and bounded exact cosine scoring suffice initially. Private query/profile vectors are transient and never enter the public index. Real-source benchmark limitations are reported, not disguised as production accuracy.

Reuse the API image for bounded corpus jobs. GCS stores immutable public blobs by SHA-256 and a generation-checked SQLite/metadata checkpoint. PostgreSQL stores sources, captured pages, ingestion runs, drafts and audit events. Workers require a direct TLS application connection: session advisory locks do not survive commits safely through Neon transaction pooling. API pooling and the separate migration credential remain intact. No worker receives paid-provider keys in the zero-budget deployment.

Interactive Codex prepares bounded candidate packets, not an unattended subscription API. A missing independent semantic pass remains explicitly pending. Schema/evidence-valid disputed drafts remain reviewable; failed candidates retain diagnostics. Real semantic reviewers must return claim-level evidence and cannot downgrade contradictions/outdated claims into successful verification. At most one repair is permitted. Human publication approval remains mandatory.

All external inference paths now require worker-only authorization and durable, conservative spending reservations before remote requests. Defaults are zero; keys alone confer no permission. Failed/ambiguous requests retain reservations. Provider/model price ceilings require explicit operator review; recorded usage-based estimates are not invoices. Local CPU embeddings/OCR do not consume provider API credits. Initial source import, administrator bootstrap, schema upgrade and deployment remain protected human authorization boundaries.
