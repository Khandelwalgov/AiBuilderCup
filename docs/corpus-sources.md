# Corpus source registry and access findings

Access review: 16 October 2026 (Asia/Kolkata). This is a selected source inventory, not comprehensive Indian opportunity coverage. Source identity means a registered department/portal index, not an opportunity or a PDF. The versioned registry is `data/corpus/sources.json`. Only four reviewed source groups are enabled for acquisition; the other entries retain the reason for exclusion.

Public index ownership is recorded separately from legal verification of the individual document issuer. Rajasthan documents can contain central guidelines or district-issued notices; the registry authority and its explicit provenance basis must not be mistaken for a reviewed document signatory. All acquisitions remain unreviewed.

## Registered source groups

| Source | Authority | Jurisdiction / category | Acquisition access | Evidence / limitation |
|---|---|---|---|---|
| [rajasthan-scholarships](https://sje.rajasthan.gov.in/scholarship_portal.aspx/Scholarship_Portal.aspx) | Department of Social Justice and Empowerment, Government of Rajasthan | Rajasthan / scholarships | `public` | Public static scholarship index exposed 123 PDF links during inspection. Policy permits accurate reproduction with attribution; at most 85 candidate documents in initial run. [Policy](https://sje.rajasthan.gov.in/default.aspx?PageID=2246). |
| [rajasthan-welfare](https://sje.rajasthan.gov.in/Default.aspx?PageID=2) | Department of Social Justice and Empowerment, Government of Rajasthan | Rajasthan / welfare | `public` | Public scheme index with PDF and selected HTML detail pages. Same reviewed Rajasthan reproduction policy; bounded named page IDs only. [Policy](https://sje.rajasthan.gov.in/default.aspx?PageID=2246). |
| [rajasthan-tenders](https://sje.rajasthan.gov.in/searchDocuments.aspx?doctype=8) | Department of Social Justice and Empowerment, Government of Rajasthan | Rajasthan / procurement | `public` | Public notice index exposed 728 PDF links, largely historical. Only 20 tender/bid candidates selected; no claim that these bids remain open. [Policy](https://sje.rajasthan.gov.in/default.aspx?PageID=2246). |
| [msme-ramp](https://ramp.msme.gov.in/ramp/scheme-guidelines) | Ministry of Micro, Small and Medium Enterprises, Government of India | India / msme | `public` | Public static PDF links; robots.txt returned 404 (not present). Website terms reviewed; only Ministry-owned scheme documents on this host. Initial quicktabs responses yielded no additional links; selected named initiative pages added for incremental discovery. [Policy](https://ramp.msme.gov.in/ramp/website-policy). |
| [depwd](https://depwd.gov.in/en/scholarship/) | Department of Empowerment of Persons with Disabilities, Government of India | India / disability | `needs_review` | Copyright policy requires prior permission for reproduction. Existing DEPwD drafts are untouched. [Policy](https://depwd.gov.in/en/copyright-policy/). |
| [nsp](https://scholarships.gov.in/All-Scholarships) | National Scholarship Portal, Government of India (index publisher; multiple issuing ministries) | India / scholarships | `needs_review` | Public static PDF links exist, but copyright policy requires prior reproduction permission. [Policy](https://scholarships.gov.in/copyright-policy). |
| [myscheme](https://www.myscheme.gov.in/) | National e-Governance Division, Ministry of Electronics and Information Technology | India / cross-category | `manual_access_required` | Terms of Use prohibit bots/scrapers without express written authorization. Do not crawl, including with Playwright. [Policy](https://www.myscheme.gov.in/terms-of-use). |
| [maharashtra-welfare](https://sjsa.maharashtra.gov.in/en/schemes-programmes/) | Social Justice and Special Assistance Department, Government of Maharashtra | Maharashtra / welfare | `needs_review` | Website policy requires reproduction permission by email before archiving. [Policy](https://sjsa.maharashtra.gov.in/en/website-policies/). |
| [gem](https://gem.gov.in/) | Government e Marketplace, Department of Commerce, Government of India | India / procurement | `needs_review` | Public HTML links to bid portal exist. Conflicting hyperlink restrictions and reuse terms require review; no bid API or document download verified. [Policy](https://gem.gov.in/websitePolicies). |
| [mission-shakti](https://missionshakti.wcd.gov.in/) | Ministry of Women and Child Development, Government of India | India / women-child | `needs_review` | Terms permit personal non-commercial download only; platform corpus reuse requires permission. [Policy](https://missionshakti.wcd.gov.in/termsconditions). |
| [startup-india](https://www.startupindia.gov.in/content/sih/en/government-schemes.html) | Department for Promotion of Industry and Internal Trade, Government of India | India / startup | `needs_review` | Static PDF links found. Terms-of-use review pending; login-only documents must be skipped. [Policy](https://www.startupindia.gov.in/content/sih/en/terms-of-use.html). |
| [central-social-justice](https://socialjustice.gov.in/schemes) | Department of Social Justice and Empowerment, Government of India | India / welfare | `needs_review` | Initial robots/TLS/HTTP probe unsuccessful or challenge/empty response. Acquisition disabled until both public access and terms are reviewed. |
| [tribal-scholarships](https://tribal.nic.in/ScholarshiP.aspx) | Ministry of Tribal Affairs, Government of India | India / scholarships | `needs_review` | Initial robots/TLS/HTTP probe unsuccessful or challenge/empty response. Acquisition disabled until both public access and terms are reviewed. |
| [central-education](https://www.education.gov.in/scholarships-education-loan-0) | Ministry of Education, Government of India | India / education | `needs_review` | Initial robots/TLS/HTTP probe unsuccessful or challenge/empty response. Acquisition disabled until both public access and terms are reviewed. |
| [central-msme](https://www.msme.gov.in/all-schemes) | Ministry of Micro, Small and Medium Enterprises, Government of India | India / msme | `needs_review` | Initial robots/TLS/HTTP probe unsuccessful or challenge/empty response. Acquisition disabled until both public access and terms are reviewed. |
| [central-skills](https://www.msde.gov.in/en/schemes-initiatives) | Ministry of Skill Development and Entrepreneurship, Government of India | India / employment-skills | `needs_review` | Initial robots/TLS/HTTP probe unsuccessful or challenge/empty response. Acquisition disabled until both public access and terms are reviewed. |
| [central-rural](https://www.rural.gov.in/en/documents/schemes-guidelines) | Ministry of Rural Development, Government of India | India / rural | `needs_review` | Initial robots/TLS/HTTP probe unsuccessful or challenge/empty response. Acquisition disabled until both public access and terms are reviewed. |
| [central-agriculture](https://agriwelfare.gov.in/en/Guidelines) | Department of Agriculture and Farmers Welfare, Government of India | India / agriculture | `needs_review` | Initial robots/TLS/HTTP probe unsuccessful or challenge/empty response. Acquisition disabled until both public access and terms are reviewed. |
| [cppp](https://eprocure.gov.in/eprocure/app) | Central Public Procurement Portal, Government of India; individual tender issuers vary | India / procurement | `needs_review` | Initial robots/TLS/HTTP probe unsuccessful or challenge/empty response. Acquisition disabled until both public access and terms are reviewed. |
| [kerala-welfare](https://sjd.kerala.gov.in/schemes.php) | Social Justice Department, Government of Kerala | Kerala / welfare | `needs_review` | Initial robots/TLS/HTTP probe unsuccessful or challenge/empty response. Acquisition disabled until both public access and terms are reviewed. |
| [delhi-women](https://wcd.delhi.gov.in/wcd/schemes) | Department of Women and Child Development, Government of NCT of Delhi | Delhi / women-child | `needs_review` | Initial robots/TLS/HTTP probe unsuccessful or challenge/empty response. Acquisition disabled until both public access and terms are reviewed. |
| [delhi-welfare](https://socialwelfare.delhi.gov.in/social/schemes) | Department of Social Welfare, Government of NCT of Delhi | Delhi / welfare | `needs_review` | Initial robots/TLS/HTTP probe unsuccessful or challenge/empty response. Acquisition disabled until both public access and terms are reviewed. |
| [gujarat-welfare](https://sje.gujarat.gov.in/schemes) | Social Justice and Empowerment Department, Government of Gujarat | Gujarat / welfare | `needs_review` | Initial robots/TLS/HTTP probe unsuccessful or challenge/empty response. Acquisition disabled until both public access and terms are reviewed. |

## Actual portal access methods

- MyScheme serves a public JavaScript interface, but its published Terms of Use prohibits automated access without written authorization. It is disabled, including for Playwright. No private/internal API was used.
- NSP exposes public static scheme-guideline and FAQ links in an HTML accordion. Its copyright policy requires reproduction permission, so the collector makes no NSP requests and archives no NSP PDFs.
- CPPP did not provide a usable response during bounded initial inspection; it is disabled pending access and terms review. No CAPTCHA, login or tender-document access control was bypassed.
- GeM exposes public navigation to a separate bid portal. Its policy has restrictions requiring review; no public machine-readable bid feed or public bid download was assumed, and acquisition is disabled.
- DEPwD scholarship, ADIP, DDRS and skill-development pages expose useful public PDF tables on the S3WaaS CDN. The DEPwD copyright restriction prevents corpus acquisition under the current permission state. Its pre-existing drafts and source snapshots were not altered.
- Maharashtra Social Justice exposes public scheme HTML and PDF policy indexes on S3WaaS, but its reproduction policy asks for prior permission by email. No permission request was sent and no documents were acquired.
- Mission Shakti exposes public guideline PDFs, but its terms limit downloads to personal non-commercial use and require permission for reproduction/distribution. It is disabled for this platform corpus.
- Startup India exposes some static PDF links and login-only flows. It remains disabled pending a completed review of its actual Terms of Use; no logged-in resource was accessed.

## Other bounded investigations and failed responses

These are access probes, not successful collector coverage:

| Site | Observed result |
|---|---|
| `socialjustice.gov.in` | Read timeout while inspecting official schemes listing. |
| `tribal.nic.in`, `pmkisan.gov.in` | TLS certificate validation failed; TLS checks retained. |
| `scdd.kerala.gov.in` | TLS DH key too small; no TLS weakening. |
| `nrlm.gov.in` | TLS hostname mismatch; no alternate insecure access. |
| `sjd.kerala.gov.in`, `wcd.delhi.gov.in`, `socialwelfare.delhi.gov.in`, `womenchild.maharashtra.gov.in` | Robots request returned 403; listing not crawled. |
| `sje.gujarat.gov.in`, `pmfby.gov.in`, `www.spniwcd.wcd.gov.in` | Robots endpoint returned HTML, not a valid robots policy. |
| `agriwelfare.gov.in`, `dcmsme.gov.in`, `nhm.gov.in`, `dsel.education.gov.in`, `www.nabard.org` | Robots endpoint redirected; automatic acquisition requires review. |
| `www.education.gov.in`, `www.msme.gov.in`, `www.msde.gov.in`, `www.dst.gov.in` | HTTP 200 but no ordinary listing links/title in the inspected response; no supported public document discovery verified. |
| `www.rural.gov.in/en/documents/schemes-guidelines` | Listing HTTP 404. |
| `megeducation.gov.in/dhte/scholarship/scholarship.html` | Listing HTTP 404. |
| `nsap.nic.in`, `dbtindia.gov.in`, `www.pmkvyofficial.org`, `www.kviconline.gov.in`, `swd.tn.gov.in` | DNS/connect failure from this environment; not evidence of permanent closure. |
| `industries.rajasthan.gov.in`, `agriculture.rajasthan.gov.in` | Sectoral landing page with one link; no usable document index verified. |
| `rajkisan.rajasthan.gov.in` | Public agriculture links found, but the attempted policy URL redirected to an error page. No corpus acquisition before policy review. |
| `www.niti.gov.in` | Public site/robots accessible; no sufficiently relevant primary opportunity index selected for this run. |

No authenticated, private, undocumented or paid API was used. Public feeds and Playwright adapters are implemented but have no enabled live source in this registry. No source is represented as discontinued solely because access failed.

## Expansion procedure

1. Confirm the exact official issuer, canonical HTTPS host, access method, robots and current reuse terms. Record evidence in this file and the registry access note.
2. Allow only named hosts and, for shared CDNs, issuing-authority paths. Select relevant index paths and small page/document budgets; do not crawl whole domains.
3. Use a dry-run, then a small live source-selected run. Review candidate relevance and originals before expanding.
4. Keep unknown dates, issuer/signatory details and amendment effects explicit. Feed extraction and any future AI processing must produce review candidates, never automatically published rules.
5. Obtain any required source permissions through the user’s authorized process; do not contact departments automatically.
