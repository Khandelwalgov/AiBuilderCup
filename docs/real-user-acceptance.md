# Real-user acceptance — local release candidate, 16 October 2026

Automation proves the fictional local workflow. A human still needs to confirm Google popup authentication, actual reading effort and hosted configuration. Use a dedicated fictional test account and the supplied `data/fixtures/documents/` files. Do not upload real Aadhaar, PAN, financial or identity documents. Do not approve the real drafts just to populate the catalogue.

## Normal local app

1. Run `make db`, `make migrate`, `make api`, `make web` using the existing ignored Firebase configuration. Do not overwrite existing `.env` files. Local fictional uploads need `ENVIRONMENT=development`, `DOCUMENT_STORAGE_BACKEND=local`, `DOCUMENT_UPLOADS_ENABLED=true`; restart API after changing them. Examples/defaults are disabled. The current local API setting was enabled for fictional files; no provider key/config was changed.
2. Open `http://127.0.0.1:5173`. Browse while signed out, search/filter and inspect coverage. Sign in with Google. Confirm Account/Settings says the backend recognized the identity. Record popup/domain/API errors without posting tokens.
3. Time a fresh fictional profile from start to saved summary. Enter nickname, choose Education, student=yes, undergraduate; skip age/state/study mode. Confirm no school-recognition, disability/income or business fields. Record elapsed time and whether any wording needed explanation. Target: approximately two minutes; no human timing has been claimed yet.
4. Reload; confirm summary, then Edit education/about you. Unchanged Save is disabled. Change an answer, cancel/discard, repeat and save. Confirm summary and no redundant active Save. Changing student to no after study mode asks before clearing; cancel retains old answers. Repeat in Hindi at phone width.
5. Create a fictional household and guardian-managed dependent. Check the owner's own card is clearly personal; edit dependent answers and open their Documents. Create an unregistered fictional business, optionally add Rajasthan/Dausa, return to overview and edit. Switch contexts and confirm the labels/files change correctly. Adult invitations remain unavailable.
6. My Documents → Upload a document → fictional fixture + recognizable name + explicit readiness permission. Reload, preview/download, replace, remove. Verify there is no “verified” choice. Upload only fictional files locally. Settings links to this same context's removal controls.
7. With a second fictional account, attempt the old document URL: expect unavailable, no metadata. Revoke guardian management in the first account; confirm dependent records and previously granted retrieval are unavailable.
8. The normal real catalogue has zero approved opportunities. Do not treat this as broken or publish without substantive review. Run the isolated suite below for the complete fictional missing-information/shared-evidence demonstration.
9. Admin may inspect the two DEPwD drafts and captured source pages **without** ingestion/approval. Confirm 36 and 34 citations, draft state and review warnings. Any real publication requires substantive source/amendment review and explicit human approval.

## Repeatable real local persistence suite

Prerequisites: local PostgreSQL, locked dependencies (`make setup`), installed Playwright Chromium and Firebase CLI. This creates only random disposable database schemas, temporary private files and local emulator accounts. It does not use your Google account, deploy or call an AI provider.

Write a temporary emulator config, then run the official local emulator in one terminal:

```sh
cat > /tmp/opportunity-product-firebase.json <<'JSON'
{"emulators":{"auth":{"host":"127.0.0.1","port":19299},"hub":{"host":"127.0.0.1","port":19400},"logging":{"host":"127.0.0.1","port":19401},"ui":{"enabled":false},"singleProjectMode":true}}
JSON
XDG_CONFIG_HOME=/tmp/opportunity-product-firebase-config FIREBASE_CLI_DISABLE_UPDATE_CHECK=true \
  firebase emulators:start --only auth --project demo-opportunity-completion \
  --config /tmp/opportunity-product-firebase.json
```

In another terminal:

```sh
make test-product-e2e
```

Use `PLAYWRIGHT_BROWSERS_PATH=/tmp/opportunity-browsers` if using this workspace's cached browser installation. Product tests own ports 15210/18210 and require emulator 19299; they refuse reuse of unrelated listeners. The API test server uses graceful shutdown so its own schema/files are removed; hard-killing a test process can require operator cleanup of its explicitly fictional resources. Stop the task-owned emulator with Ctrl-C afterwards. The normal app's credentials and listeners are untouched. The test-login page is development-only and excluded from `dist`; production rejects emulator configuration. Mocked browser contracts run separately through `make test-e2e`.

The real suite demonstrates Discover → fictional published requirement → exact age follow-up → save/evaluate → certificate gap → actual file → two compatible links → graph → replacement/removal. It also exercises dependent/business isolation, guardian revocation, failed transport/retry/refresh, stale concurrent edits and pending-save duplication prevention.

## Human release gates

Record real Google sign-in and hosted frontend/API CORS/permissions separately from emulator success. Do not deploy as part of this checklist without separate authorization. Production sensitive uploads remain disabled until malware scanning/quarantine, private GCS/IAM and key/retention/privacy controls pass review. Full adult invitations, authenticity verification, account export/erasure, submission and alerts remain unavailable. Review every official draft clause/amendment before publication; quoted evidence presence alone does not establish legal correctness.
