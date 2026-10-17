"""Local quantized multilingual inference; never contacts an inference API.

Public vectors are version/hash keyed. Private queries and facts stay request-scoped.
Exact cosine scoring is bounded by the existing catalogue size, without pgvector.
"""

import hashlib
import json
import threading
from collections import OrderedDict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from .model_artifact import MODEL, REVISION, verify


@dataclass(frozen=True)
class PolicyRepresentation:
    opportunity_id: str
    version_id: str
    source_hash: str
    text: str
    typed_requirements: list[dict]
    metadata: dict
    representation_version: str = "policy-v3"


@dataclass(frozen=True)
class SubjectRepresentation:
    kind: str
    facts: list[dict]  # Private, request-scoped only. Income contexts stay separate.
    unknown_keys: list[str]
    intent: str


class NeuralRetriever(Protocol):
    status: str

    def retrieve(
        self, policies: list[PolicyRepresentation], subject: SubjectRepresentation, limit: int
    ) -> list[str]: ...


class UnavailableNeuralRetriever:
    status = "unavailable: no local pretrained embedding model integrated"

    def retrieve(self, policies, subject, limit):
        return []


def policy_text(policy: PolicyRepresentation) -> str:
    return (
        policy.text
        + "\n"
        + json.dumps(
            {"requirements": policy.typed_requirements, **policy.metadata},
            ensure_ascii=False,
            sort_keys=True,
        )
    )


def text_hash(policy: PolicyRepresentation) -> str:
    return hashlib.sha256(policy_text(policy).encode()).hexdigest()


class LocalEncoder:
    def __init__(self, directory: Path):
        import onnxruntime as ort
        from tokenizers import Tokenizer

        verify(directory)
        ort.disable_telemetry_events()
        options = ort.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(
            str(directory / "onnx/model_quantized.onnx"),
            options,
            providers=["CPUExecutionProvider"],
        )
        self.tokenizer = Tokenizer.from_file(str(directory / "tokenizer.json"))
        # The exported tokenizer ships with truncation enabled. Disable it before
        # chunking ourselves, otherwise legal conditions in later sections disappear.
        self.tokenizer.no_truncation()
        self.tokenizer.no_padding()
        self.special_tokens = self.tokenizer.encode("").ids
        if len(self.special_tokens) != 2:
            raise ValueError("Unexpected pinned tokenizer special-token layout")
        self.lock = threading.Lock()
        self.public_vectors = OrderedDict()

    def encode(self, text: str):
        import numpy as np

        if len(text) > 100_000:
            raise ValueError("Compact policy representation exceeds encoder input bound")
        # Chunk at model token boundaries; no long-policy tail is silently discarded.
        with self.lock:
            ids = self.tokenizer.encode(" ".join(text.split()), add_special_tokens=False).ids
            chunks = [ids[i : i + 126] for i in range(0, len(ids), 126)] or [[]]
            vectors = []
            cls_id, sep_id = self.special_tokens
            for chunk in chunks:
                tokens = np.asarray([[cls_id, *chunk, sep_id]], dtype=np.int64)
                mask = np.ones_like(tokens)
                inputs = {
                    "input_ids": tokens,
                    "attention_mask": mask,
                    "token_type_ids": np.zeros_like(tokens),
                }
                output = self.session.run(
                    None, {entry.name: inputs[entry.name] for entry in self.session.get_inputs()}
                )[0]
                vector = (output * mask[..., None]).sum(axis=1) / mask.sum(axis=1)[:, None]
                vectors.append(vector[0])
            value = np.mean(vectors, axis=0).astype(np.float32)
            return value / max(float(np.linalg.norm(value)), 1e-12)

    def public_vector(self, policy):
        key = (
            policy.version_id,
            policy.source_hash,
            policy.representation_version,
            text_hash(policy),
        )
        with self.lock:
            vector = self.public_vectors.get(key)
        if vector is None:
            vector = self.encode(policy_text(policy))
            with self.lock:
                self.public_vectors[key] = vector
                while len(self.public_vectors) > 2048:
                    self.public_vectors.popitem(last=False)
        return vector


class LocalNeuralRetriever:
    status = f"local_cpu:{MODEL}@{REVISION}"

    def __init__(self, encoder, session=None):
        self.encoder, self.session = encoder, session
        self.stored_vectors_used = 0

    def retrieve(self, policies, subject, limit):
        import numpy as np
        from sqlalchemy import select

        from opportunity_platform.db.models import PolicyEmbedding

        if not policies:
            return []
        stored = {}
        if self.session is not None:
            stored = {
                str(row.version_id): row
                for row in self.session.scalars(
                    select(PolicyEmbedding).where(
                        PolicyEmbedding.version_id.in_([p.version_id for p in policies]),
                        PolicyEmbedding.model_revision == REVISION,
                    )
                )
            }
        # Only local inference sees this ephemeral representation. No cache, log or DB write.
        query = subject.intent.strip() or json.dumps(
            {"subject": subject.kind, "known_facts": subject.facts},
            ensure_ascii=False,
        )
        query_vector = self.encoder.encode(query)
        scores = []
        for policy in policies:
            row = stored.get(policy.version_id)
            if (
                row
                and row.source_hash == policy.source_hash
                and row.model == MODEL
                and row.representation_version == policy.representation_version
                and row.text_hash == text_hash(policy)
            ):
                vector = np.asarray(row.vector, dtype=np.float32)
                if vector.shape != (384,) or not np.isfinite(vector).all():
                    raise ValueError("Invalid stored public policy embedding")
                vector = vector / max(float(np.linalg.norm(vector)), 1e-12)
                self.stored_vectors_used += 1
            else:
                vector = self.encoder.public_vector(policy)
            scores.append((float(vector @ query_vector), policy.opportunity_id))
        return [key for _, key in sorted(scores, key=lambda item: (-item[0], item[1]))[:limit]]


_encoder_load_lock = threading.Lock()


@lru_cache(maxsize=2)
def _load_encoder(directory: str):
    return LocalEncoder(Path(directory))


def encoder_for(directory: str):
    # lru_cache alone can initialize multiple models on simultaneous cold misses.
    # Serialize the cache lookup as well as construction to stay within 1 GiB.
    with _encoder_load_lock:
        return _load_encoder(directory)


def neural_retriever(session=None):
    from opportunity_platform.core.config import settings

    config = settings()
    if not config.neural_retrieval_enabled or not Path(config.neural_model_directory).is_dir():
        return UnavailableNeuralRetriever()
    return LocalNeuralRetriever(encoder_for(config.neural_model_directory), session)
