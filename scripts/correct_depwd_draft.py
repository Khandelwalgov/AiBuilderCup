"""Source-backed draft correction only. No model call and no publication path."""
import argparse
import json
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from opportunity_platform.admin.service import ReviewWrite, read, review
from opportunity_platform.db.session import engine
from opportunity_platform.profiles.service import require_admin
from opportunity_platform.ingestion.schemas import CandidateRequirement, Citation, DocumentEvidence, validate_evidence
from opportunity_platform.eligibility.rules import Condition, Rule

ID = UUID("9588fed8-1f25-423d-8b5f-890636e68695")


def corrected(view):
    candidate = view.candidate.model_copy(deep=True)
    if any(f.startswith("Nightfall correction:") for f in candidate.review_flags):
        candidate.requirements = [r for r in candidate.requirements if not r.description.startswith("For a fresh application,")]
        return candidate
    def cite(year, page, start=None, end=None):
        p = next(p for p in view.pages if f"/{year}/" in p.source_url and p.page == page)
        text = p.text
        if start:
            text = text[text.index(start):]
        if end:
            text = text[:text.index(end)]
        return Citation(source_url=p.source_url, page=page, passage=text.strip(), language="en", basis="explicit")
    unknown = Rule(op="condition", condition=Condition(op="unknown"))
    # Retain the original supported conditions; split the school group and cross-state procedures.
    candidate.requirements = [r for r in candidate.requirements if not ("regular" in r.description.lower() or "cross-state" in r.description.lower())]
    def add(description, evidence, kind="eligibility", context="all", subject="person"):
        candidate.requirements.append(CandidateRequirement(description=description, evidence=evidence, rule=unknown, kind=kind, application_context=context, subject_context=subject))
    school = cite(2024, 7, "The candidate", "4.2")
    for text in ["The student must study in class IX or X.", "The student must be a regular, full-time student.", "The school must be a Government school or recognized by Government or a Central/State Board of Secondary Education."]:
        add(text, school)
    add("Scholarship for a class is available for one year only; repeating the same class does not qualify for a second or subsequent year's scholarship.", cite(2024,5,"v. Scholarship", "vi. A scholarship"))
    renewal = cite(2024,11,"i. The award", "ii. If a student")
    for text in ["Renewal is subject to good conduct.", "Renewal is subject to regular attendance.", "Renewal normally requires promotion to the next higher class in the continuous course; applicable exceptions require separate authority review."]:
        add(text,renewal,"renewal","renewal")
    add("Illness or unforeseen-event renewal requires sufficient medical or other proof and institutional certification; no automatic exception is inferred.",cite(2024,11,"iii. If a scholar", "iv. If according"),"renewal","renewal")
    add("Promotion with a junior-class examination still pending may retain scholarship for the higher class if otherwise eligible.",cite(2024,11,"iv. If according", "9. OTHER"),"renewal","renewal")
    amendment=cite(2025,3)
    add("Fresh cross-state applications require verification by the State of study under the 2025 amendment.",amendment,"procedure","fresh")
    add("Renewals do not require State Nodal Officer verification under the 2025 amendment.",amendment,"procedure","renewal")
    candidate.document_evidence = [DocumentEvidence(document=d,evidence=cite(2025,2) if ('UDID' in d or 'Aadhaar' in d) else cite(2024,10,"b. The applicants", "c. The institutions")) for d in candidate.required_documents]
    flag="Nightfall correction: separated eligibility, renewal and administrative conditions. Unknowns require human interpretation; Post-Matric first-failure exception is not applied. Document-specific evidence added."
    if flag not in candidate.review_flags:
        candidate.review_flags.append(flag)
    validate_evidence(candidate,[p.model_dump() for p in view.pages])
    return candidate


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--actor-uid",required=True)
    parser.add_argument("--apply",action="store_true")
    args=parser.parse_args()
    with Session(engine) as session:
        actor=require_admin(session,args.actor_uid)
        view=read(session,ID)
        candidate=corrected(view)
        original_path=Path("../../.live-validation/nightfall-original-draft.json")
        if not original_path.exists():
            original_path.write_text(view.model_dump_json(indent=2))
        Path("../../.live-validation/nightfall-corrected-draft.json").write_text(candidate.model_dump_json(indent=2))
        if args.apply:
            view=review(session,ID,actor,ReviewWrite(decision="correct",note="Source-backed Nightfall correction. Separate repeated-class, renewal and school conditions; document-specific citations. All unsupported interpretations remain unknown. No publication approval.",expected_hash=view.candidate_hash,candidate=candidate))
        print(json.dumps({"candidate":str(view.id),"requirements":len(candidate.requirements),"document_citations":len(candidate.document_evidence),"publication_state":view.publication_state,"applied":args.apply}))
