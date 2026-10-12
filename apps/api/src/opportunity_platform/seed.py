"""Explicit, idempotent synthetic fixtures. Never runs on application startup."""

import json
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from opportunity_platform.db.models import Opportunity, OpportunityVersion, Source
from opportunity_platform.db.session import engine

NAMESPACE = uuid.UUID("fbd2fb9a-58a5-4a96-9a18-141823ab0200")


def seed(session: Session, fixture_path: Path):
    source_id = uuid.uuid5(NAMESPACE, "synthetic-source")
    if session.get(Source, source_id) is None:
        session.add(
            Source(
                id=source_id,
                name="Synthetic development fixtures",
                authority=None,
                url=None,
                is_synthetic=True,
                status="needs_review",
            )
        )
        session.flush()
    for item in json.loads(fixture_path.read_text()):
        identifier = uuid.uuid5(NAMESPACE, item["key"])
        if session.get(Opportunity, identifier):
            continue
        session.add(
            Opportunity(
                id=identifier,
                source_id=source_id,
                source_key=item["key"],
                category=item["category"],
                is_synthetic=True,
            )
        )
        session.flush()
        session.add(
            OpportunityVersion(
                opportunity_id=identifier,
                version=1,
                title=item["title"],
                summary=item["summary"],
                country="IN",
                state=item["state"],
                district=item["district"],
                status="needs_review",
                issuer="Fictional issuer · development only",
                applicability=[],
                restrictions=[],
                required_documents=[],
            )
        )
    session.commit()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures", type=Path, required=True)
    args = parser.parse_args()
    with Session(engine) as session:
        seed(session, args.fixtures)
    print("Synthetic fixtures seeded; existing records preserved.")
