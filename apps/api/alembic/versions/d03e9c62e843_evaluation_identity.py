"""Add documentary dependency and evaluation fingerprint without rewriting history."""

import sqlalchemy as sa

from alembic import op

revision = "d03e9c62e843"
down_revision = "c92d8b51d732"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("requirements", sa.Column("document_dependency", sa.JSON(), nullable=True))
    op.add_column("match_evaluations", sa.Column("fingerprint", sa.String(64), nullable=True))
    op.create_index("ix_match_evaluations_fingerprint", "match_evaluations", ["fingerprint"])


def downgrade():
    op.drop_index("ix_match_evaluations_fingerprint", "match_evaluations")
    op.drop_column("match_evaluations", "fingerprint")
    op.drop_column("requirements", "document_dependency")
