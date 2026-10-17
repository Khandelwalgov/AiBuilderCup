"""Fail-closed source checks, not a proof of legal correctness or completeness."""

import hashlib
import json
import re
from datetime import datetime
from decimal import Decimal

from pydantic import ValidationError

from opportunity_platform.ingestion.schemas import Citation, normalize, validate_evidence

from .contracts import AIReview, Issue, PolicyCandidate


def digest(value):
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def issue(code, field, message, evidence=None, *, severity="error", human=False):
    return Issue(
        code=code,
        field=field,
        message=message,
        evidence=evidence,
        severity=severity,
        suggested_correction="Compare the original cited clause and correct or escalate.",
        human_required=human,
    )


def numbers(text):
    result = set()
    for value, unit in re.findall(
        r"(?i)(?<![\w])([0-9][0-9,]*(?:\.[0-9]+)?)\s*(lakh|lac|crore|million|thousand)?", text
    ):
        factor = {
            "lakh": 100000,
            "lac": 100000,
            "crore": 10000000,
            "million": 1000000,
            "thousand": 1000,
        }.get(unit.lower(), 1)
        result.add(Decimal(value.replace(",", "")) * factor)
    return result


def leaves(rule):
    if rule.condition:
        yield rule.condition
    for child in rule.children:
        yield from leaves(child)


def cited(citation, pages):
    return any(
        p["page"] == citation.page
        and p["source_url"] == citation.source_url
        and normalize(citation.passage) in normalize(p["text"])
        for p in pages
    )


def date_supported(value, passage):
    text = passage.lower()
    variants = {
        value.isoformat(),
        value.strftime("%d/%m/%Y"),
        value.strftime("%d-%m-%Y"),
        value.strftime("%d.%m.%Y"),
        value.strftime("%d %B %Y").lower(),
        value.strftime("%d %b %Y").lower(),
    }
    if any(v in text for v in variants):
        return True
    for day, month, year in re.findall(r"\b(\d{1,2})\s+([A-Za-z]{3,9})\s*,?\s*(\d{4})\b", text):
        for fmt in ("%d %B %Y", "%d %b %Y"):
            try:
                if datetime.strptime(f"{day} {month} {year}", fmt).date() == value:
                    return True
            except ValueError:
                continue
    return False


def validate_claim_findings(review, candidate, audited):
    """Real semantic providers must examine each material field, not just quote existence."""
    data = candidate.candidate
    expected = {f"requirements.{i}" for i in range(len(data.requirements))}
    expected |= {
        name
        for name in [
            "title",
            "summary",
            "issuer",
            "category",
            "country",
            "state",
            "district",
            "benefits",
            "restrictions",
            "required_documents",
            "opens_on",
            "closes_on",
            "apply_url",
        ]
        if getattr(data, name)
    }
    if {finding.field for finding in review.findings} != expected:
        raise ValueError("Semantic findings must cover every material candidate field exactly")
    if len(review.findings) != len(expected):
        raise ValueError("Duplicate semantic claim findings")
    disputed = False
    for finding in review.findings:
        if not cited(finding.evidence, audited.pages):
            raise ValueError("Semantic finding lacks captured source evidence")
        disputed |= finding.assessment != "supported"
    if disputed and review.assessment != "issues_found":
        raise ValueError("Disputed claims cannot be reported as no issues detected")
    if disputed and not review.issues:
        raise ValueError("Disputed claims require targeted discrepancy reports")
    for finding in review.findings:
        if finding.assessment != "supported":
            review.issues.append(
                issue(
                    "semantic_claim_disputed",
                    finding.field,
                    finding.explanation,
                    finding.evidence,
                    severity="critical"
                    if finding.assessment in {"contradicted", "outdated"}
                    else "error",
                    human=True,
                )
            )


def validate(raw, audited):
    problems = []
    try:
        candidate = PolicyCandidate.model_validate(raw)
    except (ValidationError, ValueError, TypeError):
        return None, [issue("schema_invalid", "candidate", "Candidate violates the closed schema.")]
    data, pages = candidate.candidate, audited.pages
    try:
        validate_evidence(data, pages)
    except ValueError as exc:
        problems.append(issue("citation_or_field_evidence_invalid", "candidate", str(exc)))
    if set(data.required_documents) != {e.document for e in data.document_evidence}:
        problems.append(
            issue(
                "document_coverage_incomplete",
                "required_documents",
                "Every required document needs its exact source citation.",
            )
        )
    if not data.requirements:
        problems.append(
            issue(
                "requirements_empty",
                "requirements",
                "No eligibility/readiness rules were extracted.",
                human=True,
            )
        )
    for i, req in enumerate(data.requirements):
        field = f"requirements.{i}"
        if req.evidence.basis != "explicit" or req.kind == "interpretation":
            problems.append(
                issue(
                    "interpretation_requires_human",
                    field,
                    "Source interpretation is not an explicit verified rule.",
                    req.evidence,
                    severity="warning",
                    human=True,
                )
            )
        for condition in leaves(req.rule):
            if condition.op == "unknown":
                problems.append(
                    issue(
                        "unsupported_or_unknown_rule",
                        field,
                        "The closed rule language cannot express this condition.",
                        req.evidence,
                        severity="warning",
                        human=True,
                    )
                )
            if condition.fact == "education_level":
                problems.append(
                    issue(
                        "ambiguous_legacy_education",
                        field,
                        "New candidates must not use ambiguous legacy education.",
                        req.evidence,
                        human=True,
                    )
                )
            values = condition.value if isinstance(condition.value, list) else [condition.value]
            for value in values:
                if type(value) in (float, int) and Decimal(str(value)) not in numbers(
                    req.evidence.passage
                ):
                    problems.append(
                        issue(
                            "numerical_value_not_in_clause",
                            field,
                            "Numeric rule value is absent from its cited clause.",
                            req.evidence,
                        )
                    )
            if (
                condition.op != "unknown"
                and condition.fact
                and ("income" in condition.fact or condition.fact == "business_turnover")
            ):
                text = normalize(req.evidence.passage).lower()
                period = normalize(condition.income_period or "").lower()
                annual = period in {"annual", "per annum", "yearly"}
                if not period or not (
                    any(v in text for v in ("annual", "per annum", "yearly"))
                    if annual
                    else period in text
                ):
                    problems.append(
                        issue(
                            "income_period_not_cited",
                            field,
                            "Income assessment period is not explicit in the clause.",
                            req.evidence,
                            human=True,
                        )
                    )
                definition = normalize(condition.income_definition or "").lower()
                if not definition or definition not in text:
                    problems.append(
                        issue(
                            "income_definition_not_cited",
                            field,
                            "Income definition is not explicit in the clause.",
                            req.evidence,
                            human=True,
                        )
                    )
                if condition.fact == "annual_parental_income" and not re.search(
                    r"parent|mother|father|माता|पिता", text
                ):
                    problems.append(
                        issue(
                            "income_subject_mismatch",
                            field,
                            "Parental income must not be inferred from family income.",
                            req.evidence,
                            human=True,
                        )
                    )
            if condition.fact == "annual_household_income" and condition.op != "unknown":
                if not re.search(r"(?i)household|family|परिवार", req.evidence.passage):
                    problems.append(
                        issue(
                            "income_subject_mismatch",
                            field,
                            "Household income cannot be inferred from a parental clause.",
                            req.evidence,
                            human=True,
                        )
                    )
            if condition.op in {"gte", "lte"}:
                problems.append(
                    issue(
                        "comparison_semantics_review",
                        field,
                        "Exact threshold and inclusive/exclusive interpretation need review.",
                        req.evidence,
                        severity="warning",
                        human=True,
                    )
                )
    for item in data.field_evidence:
        value = getattr(data, item.field, None)
        if item.field not in type(data).model_fields:
            problems.append(
                issue(
                    "unknown_evidence_field",
                    item.field,
                    "Citation names an unsupported candidate field.",
                )
            )
        if item.field in {"benefits", "summary", "restrictions"} and value:
            text = " ".join(value) if isinstance(value, list) else str(value)
            if not numbers(text).issubset(numbers(item.citation.passage)):
                problems.append(
                    issue(
                        "metadata_amount_not_in_clause",
                        item.field,
                        "Numerical metadata claim is absent from its citation.",
                        item.citation,
                    )
                )
        if item.field in {"closes_on", "opens_on"} and value:
            wording = (
                r"clos|last date|deadline|bid.*submission|due date|अंतिम"
                if (item.field == "closes_on")
                else r"open|start|commenc|आरंभ"
            )
            if not date_supported(value, item.citation.passage) or not re.search(
                wording, item.citation.passage, re.I
            ):
                problems.append(
                    issue(
                        "deadline_not_explicit",
                        item.field,
                        "A notice/publication date is not an application deadline.",
                        item.citation,
                        human=True,
                    )
                )
        if (
            item.field == "issuer"
            and value
            and normalize(value).lower() not in normalize(item.citation.passage).lower()
        ):
            problems.append(
                issue(
                    "issuer_not_in_clause",
                    item.field,
                    "Document issuer is not stated in its cited evidence.",
                    item.citation,
                    human=True,
                )
            )
    if data.opens_on and data.closes_on and data.opens_on > data.closes_on:
        problems.append(issue("deadline_order", "closes_on", "Close date precedes open date."))
    if audited.document_type == "amendment":
        problems.append(
            issue(
                "amendment_context_unresolved",
                "source",
                "Standalone amendment needs a reviewed baseline and effects mapping.",
                human=True,
            )
        )
    if audited.needs_ocr or not audited.technically_ingestible:
        problems.append(
            issue(
                "source_not_readable",
                "source",
                "OCR, encoding or archive integrity requires human intervention.",
                human=True,
            )
        )
    accounted = {row.clause_id: row for row in candidate.coverage}
    if len(accounted) != len(candidate.coverage):
        problems.append(
            issue(
                "duplicate_clause_coverage",
                "coverage",
                "Each material source clause must have one disposition.",
            )
        )
    ids = {clause.id for clause in audited.clauses}
    if set(accounted) - ids:
        problems.append(
            issue("unknown_clause_id", "coverage", "Coverage references invented clauses.")
        )
    for clause in audited.clauses:
        evidence = Citation(
            source_url=clause.source_url,
            page=clause.page,
            passage=clause.passage[:6000],
            language="original",
            basis="explicit",
        )
        row = accounted.get(clause.id)
        if row is None:
            problems.append(
                issue(
                    "clause_unaccounted",
                    "coverage",
                    "A material source block has no coverage disposition.",
                    evidence,
                )
            )
            continue
        if row.disposition != "represented":
            problems.append(
                issue(
                    "clause_needs_human_disposition",
                    "coverage",
                    "An excluded, ambiguous or unrepresentable clause needs human review.",
                    evidence,
                    severity="warning",
                    human=True,
                )
            )
            continue
        citations = []
        for index in row.requirement_indexes:
            if not 0 <= index < len(data.requirements):
                problems.append(
                    issue(
                        "coverage_requirement_missing",
                        "coverage",
                        "Coverage refers to a nonexistent requirement.",
                    )
                )
            else:
                citations.append(data.requirements[index].evidence)
        for name in row.field_names:
            citations.extend(f.citation for f in data.field_evidence if f.field == name)
        if not citations or not any(
            c.source_url == clause.source_url
            and c.page == clause.page
            and normalize(c.passage) in normalize(clause.passage)
            for c in citations
        ):
            problems.append(
                issue(
                    "coverage_not_supported",
                    "coverage",
                    "Coverage mapping is not supported by a citation inside the block.",
                    evidence,
                )
            )
    return candidate, problems


def validate_review(raw, candidate, audited):
    review = AIReview.model_validate(raw)
    if review.candidate_hash != digest(candidate) or review.source_hash != audited.record.sha256:
        raise ValueError("review_hash_mismatch")
    if set(review.examined_clause_ids) != {c.id for c in audited.clauses}:
        raise ValueError("review_coverage_incomplete")
    if (review.assessment == "no_issues_detected") != (not review.issues):
        raise ValueError("review_assessment_inconsistent")
    for problem in review.issues:
        if problem.evidence and not cited(problem.evidence, audited.pages):
            raise ValueError("review_citation_invalid")
        if problem.severity in ("error", "critical") and problem.evidence is None:
            raise ValueError("review_issue_missing_evidence")
    return review
