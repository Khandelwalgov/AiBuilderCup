"""Version-aware public policy full-text index (queries enforce review state)."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import TSVECTOR

from alembic import op

revision = "f24a1000abcd"
down_revision = "e14a7d63f954"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "opportunity_versions",
        sa.Column(
            "search_vector",
            TSVECTOR(),
            sa.Computed(
                "to_tsvector('english'::regconfig, coalesce(title, '') || ' ' || "
                "coalesce(summary, '') || ' ' || coalesce(issuer, '') || ' ' || "
                "coalesce(category, ''))",
                persisted=True,
            ),
        ),
    )
    op.create_index(
        "ix_version_search_vector",
        "opportunity_versions",
        ["search_vector"],
        postgresql_using="gin",
    )


def downgrade():
    op.drop_index("ix_version_search_vector", table_name="opportunity_versions")
    op.drop_column("opportunity_versions", "search_vector")
