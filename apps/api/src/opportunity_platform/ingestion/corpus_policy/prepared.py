"""Interactive Codex staging, not an unattended subscription API.

A prepared candidate cannot assert its own independent review. Missing separate review
is explicitly escalated; only an authorized human can publish the resulting draft.
"""

from .contracts import PolicyCandidate
from .validation import digest


class PreparedExtractor:
    identity = "codex:interactive:prepared-corpus-v1"
    model = "interactive-session-model-not-programmatically-attested"
    invokes_model = False

    def __init__(self, packet, source_hash):
        if packet.get("source_hash") != source_hash:
            raise ValueError("Prepared candidate source hash differs from captured artifact")
        self.candidate = PolicyCandidate.model_validate(packet["candidate"])
        self.input_hash = digest(self.candidate)

    def extract(self, audited, focus, feedback=None, previous=None):
        return self.candidate, {
            "provider": "codex_interactive",
            "external_api_calls": 0,
            "estimated_external_inference_usd": 0,
            "token_usage": "interactive session usage not separately attributable to this document",
        }


class PendingIndependentReview:
    identity = "unavailable:separate-semantic-review-not-performed"
    invokes_model = False

    def review(self, audited, candidate):
        raise ValueError("Independent semantic review is pending; cannot self-verify")
