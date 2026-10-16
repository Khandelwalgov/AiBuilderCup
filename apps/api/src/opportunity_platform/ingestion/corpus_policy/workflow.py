"""Independent review and at most two feedback repairs; final authority is human."""

from typing import Protocol

from .contracts import Outcome, Stage
from .validation import digest, issue, validate, validate_review


class Extractor(Protocol):
    identity: str

    def extract(self, audited, focus, feedback=None, previous=None): ...


class Reviewer(Protocol):
    identity: str

    def review(self, audited, candidate): ...


def run_pipeline(audited, focus, extractor, reviewer, *, max_repairs=2):
    if not 0 <= max_repairs <= 2:
        raise ValueError("At most two repair cycles are permitted")
    if extractor is reviewer:
        raise ValueError("Extraction and independent review require separate role instances")
    if not focus.strip() or len(focus) > 2000:
        raise ValueError("An explicit bounded opportunity focus is required")
    stages, usage, calls, candidate, feedback, previous = [], [], 0, None, [], None
    # No model is invoked for unreadable/irrelevant/amendment-without-context sources.
    if not audited.suitable_for_extraction:
        problem = issue(
            "source_requires_human_triage",
            "source",
            "Source is unreadable, irrelevant, ambiguous or needs amendment context.",
            human=True,
        )
        return Outcome(
            status="human_escalation",
            candidate=None,
            stages=[
                Stage(attempt=0, candidate_hash=digest(None), candidate=None, issues=[problem])
            ],
            repair_cycles=0,
            model_calls=0,
            usage=[],
        )
    for attempt in range(max_repairs + 1):
        try:
            calls += 1
            raw, consumed = extractor.extract(audited, focus, feedback, previous)
            usage.append({"role": "extract" if attempt == 0 else "repair", **consumed})
        except Exception:
            problem = issue(
                "extraction_provider_failed",
                "provider",
                "Extraction failed; no fallback provider or automatic retry.",
                human=True,
            )
            stages.append(
                Stage(
                    attempt=attempt,
                    candidate_hash=digest(previous),
                    candidate=previous,
                    issues=[problem],
                )
            )
            break
        if hasattr(raw, "model_dump"):
            raw = raw.model_dump(mode="json")
        previous = raw
        candidate, problems = validate(raw, audited)
        review = None
        if candidate:
            try:
                calls += 1
                output, consumed = reviewer.review(audited, candidate)
                usage.append({"role": "independent_review", **consumed})
                review = validate_review(output, candidate, audited)
                problems.extend(review.issues)
            except Exception:
                problems.append(
                    issue(
                        "independent_review_failed",
                        "review",
                        "Review failed validation or provider execution; human review required.",
                        human=True,
                    )
                )
        stages.append(
            Stage(
                attempt=attempt,
                candidate_hash=digest(candidate or raw),
                candidate=candidate.model_dump(mode="json") if candidate else raw,
                issues=problems,
                independent_review=review,
            )
        )
        errors = [i for i in problems if i.severity in ("error", "critical")]
        if candidate and review and not errors:
            candidate.candidate.review_flags = list(
                dict.fromkeys(
                    [
                        "CORPUS: human completeness and consequential-criteria review required",
                        *candidate.candidate.review_flags,
                        *[f"{p.code}: {p.message}"[:500] for p in problems if p.human_required],
                    ]
                )
            )[:50]
            return Outcome(
                status="draft_for_human_review",
                candidate=candidate,
                stages=stages,
                repair_cycles=attempt,
                model_calls=calls,
                usage=usage,
            )
        if any(
            i.code
            in {"independent_review_failed", "amendment_context_unresolved", "source_not_readable"}
            or i.severity == "critical"
            for i in problems
        ):
            break
        feedback = [p.model_dump(mode="json") for p in problems]
    return Outcome(
        status="human_escalation",
        candidate=None,
        stages=stages,
        repair_cycles=max(0, len(stages) - 1),
        model_calls=calls,
        usage=usage,
    )
