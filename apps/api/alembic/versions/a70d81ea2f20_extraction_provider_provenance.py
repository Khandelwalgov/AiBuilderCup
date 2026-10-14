"""Record explicit extraction identity and measured usage; retain legacy unknowns."""

import sqlalchemy as sa

from alembic import op

revision = "a70d81ea2f20"
down_revision = "fcc8ecdfdfad"
branch_labels = None
depends_on = None


def upgrade():
    for column in [
        sa.Column("extraction_provider", sa.String(), nullable=True),
        sa.Column("extraction_model", sa.String(), nullable=True),
        sa.Column("extractor_version", sa.String(), nullable=True),
        sa.Column("extraction_usage", sa.JSON(), nullable=True),
    ]:
        op.add_column("opportunity_versions", column)
    for column in [
        sa.Column("provider", sa.String(), nullable=True),
        sa.Column("source_hash", sa.String(), nullable=True),
        sa.Column("usage", sa.JSON(), nullable=True),
        sa.Column("diagnostics", sa.JSON(), nullable=True),
    ]:
        op.add_column("ingestion_runs", column)


def downgrade():
    for name in ["diagnostics", "usage", "source_hash", "provider"]:
        op.drop_column("ingestion_runs", name)
    for name in [
        "extraction_usage",
        "extractor_version",
        "extraction_model",
        "extraction_provider",
    ]:
        op.drop_column("opportunity_versions", name)
