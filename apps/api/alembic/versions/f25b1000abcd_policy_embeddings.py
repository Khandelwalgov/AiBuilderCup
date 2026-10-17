"""Public version-aware local multilingual policy embeddings.

Revision ID: f25b1000abcd
Revises: f24a1000abcd
"""

import sqlalchemy as sa

from alembic import op

revision = "f25b1000abcd"
down_revision = "f24a1000abcd"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "policy_embeddings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "version_id", sa.Uuid(), sa.ForeignKey("opportunity_versions.id"), nullable=False
        ),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("model_revision", sa.String(), nullable=False),
        sa.Column("representation_version", sa.String(), nullable=False),
        sa.Column("source_hash", sa.String(), nullable=False),
        sa.Column("text_hash", sa.String(), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("vector", sa.JSON(), nullable=False),
        sa.UniqueConstraint("version_id", "model_revision", "representation_version"),
        sa.CheckConstraint("dimensions = 384"),
    )
    op.create_index("ix_policy_embeddings_version_id", "policy_embeddings", ["version_id"])
    op.create_table(
        "inference_reservations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("run_key", sa.String(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("input_bound", sa.Integer(), nullable=False),
        sa.Column("output_bound", sa.Integer(), nullable=False),
        sa.Column("reserved_usd", sa.Numeric(20, 8), nullable=False),
        sa.Column("recorded_usd", sa.Numeric(20, 8)),
        sa.Column("prices", sa.JSON(), nullable=False),
        sa.Column("usage", sa.JSON()),
        sa.Column("status", sa.String(), nullable=False),
    )
    op.create_index("ix_inference_reservations_run_key", "inference_reservations", ["run_key"])


def downgrade():
    op.drop_table("inference_reservations")
    op.drop_table("policy_embeddings")
