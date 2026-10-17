"""Build public embeddings using local weights, not an inference API.

Plan-only by default. Execute only with the database's authorized release/job identity.
Never indexes drafts, synthetic policies or private facts/documents.
"""

import argparse
import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from opportunity_platform.db.models import PolicyEmbedding
from opportunity_platform.db.session import engine
from opportunity_platform.retrieval.model_artifact import MODEL, REVISION
from opportunity_platform.retrieval.neural import (
    PolicyRepresentation,
    encoder_for,
    text_hash,
)
from opportunity_platform.retrieval.service import SearchRequest, load_catalogue


def representations(session):
    rows, reqs, _, _ = load_catalogue(session, SearchRequest())
    return [
        PolicyRepresentation(
            str(o.id),
            str(v.id),
            v.content_hash or "",
            f"{v.title}\n{v.summary}\nBenefits: {v.benefits or 'not established'}",
            [
                {
                    "rule": r.rule,
                    "description": r.description,
                    "subject_context": r.subject_context,
                    "kind": r.kind,
                    "application_context": r.application_context,
                }
                for r in reqs[v.id]
            ],
            {
                "category": v.category or o.category,
                "country": v.country,
                "state": v.state,
                "district": v.district,
            },
        )
        for o, v, _ in rows
    ]


def build(session, encoder, policies):
    changed = 0
    for policy in policies:
        existing = session.scalar(
            select(PolicyEmbedding).where(
                PolicyEmbedding.version_id == uuid.UUID(policy.version_id),
                PolicyEmbedding.model_revision == REVISION,
                PolicyEmbedding.representation_version == policy.representation_version,
            )
        )
        if (
            existing
            and existing.text_hash == text_hash(policy)
            and existing.source_hash == policy.source_hash
        ):
            continue
        values = {
            "version_id": uuid.UUID(policy.version_id),
            "model": MODEL,
            "model_revision": REVISION,
            "representation_version": policy.representation_version,
            "source_hash": policy.source_hash,
            "text_hash": text_hash(policy),
            "dimensions": 384,
            "vector": encoder.public_vector(policy).tolist(),
        }
        statement = insert(PolicyEmbedding).values(**values)
        session.execute(
            statement.on_conflict_do_update(
                index_elements=["version_id", "model_revision", "representation_version"],
                set_={**values, "created_at": statement.excluded.created_at},
            )
        )
        changed += 1
    return changed


def main():
    from opportunity_platform.core.config import settings

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    with Session(engine) as session:
        policies = representations(session)
        if not args.execute:
            print({"mode": "plan", "published_real_versions": len(policies), "paid_calls": 0})
            return
        encoder = encoder_for(settings().neural_model_directory)
        updated = build(session, encoder, policies)
        session.commit()
        print({"indexed": updated, "published_real_versions": len(policies), "paid_calls": 0})


if __name__ == "__main__":
    main()
