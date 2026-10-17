"""Public-only local semantic retrieval with deterministic lexical fallback."""

import logging
import re

from opportunity_platform.retrieval.neural import (
    PolicyRepresentation,
    SubjectRepresentation,
    neural_retriever,
)

from .conditions import definitions

log = logging.getLogger(__name__)


def rank(rows, query):
    if not query.strip():
        return {}, "not_requested"
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
    representations = [
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
    try:
        retriever = (
            neural_retriever()
        )  # public vectors cached by content/model hash in existing encoder
        semantic = retriever.retrieve(
            representations, SubjectRepresentation("public", [], [], query), min(12, len(rows))
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
