"""Separate public research catalogue; no approved policy or source rewrites.

Revision ID: f26c1000abcd
Revises: f25b1000abcd
"""

import sqlalchemy as sa

from alembic import op

revision = "f26c1000abcd"
down_revision = "f25b1000abcd"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "research_listings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("identity_key", sa.String(), nullable=False, unique=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("summary", sa.String(), nullable=False),
        sa.Column("search_text", sa.String(), nullable=False),
        sa.Column("authority", sa.String()),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("jurisdiction", sa.String(), nullable=False),
        sa.Column("availability", sa.String(), nullable=False),
        sa.Column("application_status", sa.String(), nullable=False),
        sa.Column(
            "source_snapshot_id", sa.Uuid(), sa.ForeignKey("source_snapshots.id"), nullable=False
        ),
        sa.Column("source_hash", sa.String(), nullable=False),
        sa.Column("payload_hash", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("is_public", sa.Boolean(), server_default="false", nullable=False),
        sa.CheckConstraint(
            "availability IN ('verified_current','historical','unknown','potentially_expired')"
        ),
        sa.CheckConstraint("application_status IN ('open','closed','not_established')"),
    )
    for column in ["category", "jurisdiction", "availability", "application_status"]:
        op.create_index("ix_research_listings_" + column, "research_listings", [column])


def downgrade():
    op.drop_table("research_listings")
