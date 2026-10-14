"""Deliberate documentary aliases. Unknown or conditional labels remain distinct."""

import re

ALIASES = {
    "unique disability identity card udid": "udid",
    "aadhaar card": "aadhaar",
    "photograph": "photograph",
    "proof of age": "age-proof",
    "disability certificate": "disability-certificate",
    "income certificate of the parent": "parental-income-certificate",
    "tuition fee receipt": "tuition-receipt",
    "tuition fees receipt": "tuition-receipt",
    "last academic qualification certificate": "academic-qualification",
}


def dependency(label, citation):
    normalized = " ".join(re.sub(r"[^a-z0-9]+", " ", label.casefold()).split())
    key = ALIASES.get(normalized)
    if key is None:
        return None
    # A certificate's policy basis/period cannot be inferred from its name.
    # Share this unspecified basis only within the exact authoritative page.
    return {
        "document": key,
        "kind": "document",
        "policy_basis": {"url": citation.source_url, "page": str(citation.page)},
        "income_definition": "unspecified-parental"
        if key == "parental-income-certificate"
        else None,
        "income_period": None,
    }
