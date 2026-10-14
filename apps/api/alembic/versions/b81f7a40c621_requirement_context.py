"""Preserve policy category and application context without changing historical rules."""

import sqlalchemy as sa

from alembic import op

revision = "b81f7a40c621"
down_revision = "a70d81ea2f20"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "requirements", sa.Column("kind", sa.String(), nullable=False, server_default="eligibility")
    )
    op.add_column(
        "requirements",
        sa.Column("application_context", sa.String(), nullable=False, server_default="all"),
    )


def downgrade():
    op.drop_column("requirements", "application_context")
    op.drop_column("requirements", "kind")
