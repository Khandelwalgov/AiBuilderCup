"""Private document metadata/lifecycle and immutable versioned requirement links."""

import sqlalchemy as sa

from alembic import op

revision = "e14a7d63f954"
down_revision = "d03e9c62e843"
branch_labels = None
depends_on = None


def upgrade():
    for column in [
        sa.Column("display_name", sa.String(), nullable=False, server_default="Document"),
        sa.Column("document_type", sa.String(), nullable=False, server_default="other"),
        sa.Column("byte_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sha256", sa.String(), nullable=True),
        sa.Column("issuer", sa.String(), nullable=True),
        sa.Column("issued_on", sa.Date(), nullable=True),
        sa.Column("expires_on", sa.Date(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="legacy_unavailable"),
        sa.Column("storage_backend", sa.String(), nullable=False, server_default="local"),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaces_id", sa.Uuid(), nullable=True),
        sa.Column("purge_pending", sa.Boolean(), nullable=False, server_default="false"),
    ]:
        op.add_column("documents", column)
    op.create_foreign_key("fk_document_replaces", "documents", "documents", ["replaces_id"], ["id"])
    op.create_table(
        "document_requirement_links",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("document_id", sa.Uuid(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("requirement_id", sa.Uuid(), sa.ForeignKey("requirements.id"), nullable=False),
        sa.Column(
            "version_id", sa.Uuid(), sa.ForeignKey("opportunity_versions.id"), nullable=False
        ),
        sa.Column("compatibility", sa.JSON(), nullable=False),
        sa.UniqueConstraint("document_id", "requirement_id"),
    )
    op.create_index(
        "ix_document_requirement_links_document_id", "document_requirement_links", ["document_id"]
    )
    op.create_index(
        "ix_document_requirement_links_requirement_id",
        "document_requirement_links",
        ["requirement_id"],
    )


def downgrade():
    op.drop_table("document_requirement_links")
    op.drop_constraint("fk_document_replaces", "documents", type_="foreignkey")
    for name in [
        "display_name",
        "document_type",
        "byte_size",
        "sha256",
        "issuer",
        "issued_on",
        "expires_on",
        "status",
        "storage_backend",
        "uploaded_at",
        "replaces_id",
        "purge_pending",
    ]:
        op.drop_column("documents", name)
