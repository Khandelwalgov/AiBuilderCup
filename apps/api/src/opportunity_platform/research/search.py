"""Local research ranking: public cached vectors, private request-scoped context."""

import json
import logging
import re
from datetime import date

from opportunity_platform.retrieval.neural import (
    PolicyRepresentation,
    SubjectRepresentation,
    neural_retriever,
)

from .conditions import definitions

log = logging.getLogger(__name__)


# Closed selection: names, IDs, documents and free-form private text never become queries.
# Legacy education_level is intentionally omitted: enrollment vs completion is ambiguous.
PROFILE_FIELDS = {
    "person": {
        "age": "Age in years",
        "student_status": "Currently studying",
        "current_education_level": "Current education course",
        "highest_completed_education": "Highest completed qualification",
        "enrollment_mode": "Study mode",
        "employment_status": "Employment status",
        "domicile_state": "Domicile state",
        "domicile_district": "Domicile district",
        "residence_state": "Residence state",
        "residence_district": "Residence district",
        "beneficiary_category": "Recorded beneficiary category",
        "disability_percentage": "Recorded disability percentage",
    },
    "business": {
        "business_sector": "Business sector",
        "business_size": "Enterprise size",
        "business_operating_status": "Business operating status",
        "business_registered": "Business registered",
        "business_udyam_registered": "Udyam registration",
        "business_udyam_assist_registered": "Udyam Assist registration",
        "business_gst_registered": "GST registration",
        "business_online_trade_scope": "Online trading scope",
        "business_registration_state": "Business registration state",
        "business_registration_district": "Business registration district",
    },
}


def profile_context(kind, facts, category=""):
    """Ephemeral semantic context, never an eligibility inference or a saved vector.

    Use only current, unambiguous supported facts. No assumed goals, income pooling,
    inferred enrollment or category. The optional category is an expressed filter,
    not a guessed interest. Saved interests/goals are not modeled by current profiles.
    """
    labels = PROFILE_FIELDS.get(kind, {})
    today = date.today()
    values = {}
    for fact in facts:
        if (
            fact.key in labels
            and fact.value is not None
            and fact.value != "unknown"
            and (fact.valid_from is None or fact.valid_from <= today)
            and (fact.valid_until is None or fact.valid_until >= today)
        ):
            values.setdefault(fact.key, set()).add(json.dumps(fact.value, ensure_ascii=False))
    known = [
        {"key": key, "value": json.loads(next(iter(choices)))}
        for key, choices in sorted(values.items())
        if len(choices) == 1
    ]
    # No generic-person query: an unknown profile has no evidence of semantic intent.
    if not known and not category:
        return None
    passages = []
    for fact in known:
        value = fact["value"]
        value = ("yes" if value else "no") if isinstance(value, bool) else str(value)
        passages.append(f"{labels[fact['key']]}: {value.replace('_', ' ')[:120]}.")
    if category:
        passages.append(f"Selected opportunity category: {category[:80]}.")
    return SubjectRepresentation(kind, known, [], " ".join(passages))


def representations(rows):
    mapped = {}
    for condition in definitions():
        mapped.setdefault(condition["listing_key"], []).append(condition["title"])
    return [
        PolicyRepresentation(
            str(r.id),
            str(r.id),
            r.payload_hash,
            " ".join([r.title, r.summary, r.payload.get("benefit") or ""]),
            [{"source_condition": text} for text in mapped.get(r.identity_key, [])],
            {"category": r.category, "jurisdiction": r.jurisdiction},
            "research-v1",
        )
        for r in rows
    ]


def rank_profile(rows, subject):
    if subject is None:
        return {}, "not_requested: no usable profile context"
    if not rows:
        return {}, "not_requested: empty catalogue"
    try:
        retriever = neural_retriever()
        if retriever.status.startswith("unavailable"):
            return {}, retriever.status
        # Rank the entire catalogue, never a top-k recall gate. Only public vectors cache.
        order = retriever.retrieve(representations(rows), subject, len(rows))
        return {key: 1 / (20 + index) for index, key in enumerate(order)}, retriever.status
    except (OSError, ValueError, RuntimeError, ImportError):
        log.warning("research_profile_embedding_unavailable", extra={"fallback": "deterministic"})
        return {}, "unavailable: deterministic fallback"


def rank(rows, query, *, subject=None):
    if not query.strip():
        return rank_profile(rows, subject)
    terms = set(re.findall(r"\w+", query.casefold()))
    terms.add(query.strip().casefold())
    translations = {
        "छात्रवृत्ति": "scholarship",
        "शिक्षा": "education",
        "व्यवसाय": "business",
        "उद्यम": "enterprise",
        "पढ़ाई": "study",
    }
    terms.update(translation for word, translation in translations.items() if word in query)
    mapped = {}
    for condition in definitions():
        mapped.setdefault(condition["listing_key"], []).append(condition["title"])
    lexical = {}
    for row in rows:
        text = " ".join(
            [
                row.title,
                row.summary,
                row.payload.get("benefit") or "",
                row.search_text,
                *mapped.get(row.identity_key, []),
            ]
        ).casefold()
        score = sum(term in text for term in terms)
        if score:
            lexical[str(row.id)] = score
    try:
        retriever = (
            neural_retriever()
        )  # public vectors cached by content/model hash in existing encoder
        semantic = retriever.retrieve(
            representations(rows),
            SubjectRepresentation("public", [], [], query),
            min(12, len(rows)),
        )
        status = retriever.status
    except (OSError, ValueError, RuntimeError, ImportError):
        log.warning("research_embedding_unavailable", extra={"fallback": "lexical"})
        semantic, status = [], "unavailable: lexical fallback"
    lexical_order = sorted(lexical, key=lambda key: (-lexical[key], key))
    scores = {key: 1 / (20 + index) for index, key in enumerate(lexical_order)}
    for index, key in enumerate(semantic):
        scores[key] = scores.get(key, 0) + 1 / (20 + index)
    return scores, status
