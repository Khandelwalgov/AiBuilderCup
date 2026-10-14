"""Explicit household owner and reusable action metadata; preserve legacy records."""

import sqlalchemy as sa

from alembic import op

revision = "c92d8b51d732"
down_revision = "b81f7a40c621"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("households", sa.Column("owner_user_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_household_owner", "households", "users", ["owner_user_id"], ["id"])
    op.create_index("ix_households_owner_user_id", "households", ["owner_user_id"])
    op.add_column("businesses", sa.Column("description", sa.String(), nullable=True))
    op.add_column("action_items", sa.Column("identity", sa.String(), nullable=True))
    op.create_index("ix_action_items_identity", "action_items", ["identity"])
    op.add_column(
        "action_items", sa.Column("details", sa.JSON(), nullable=False, server_default="{}")
    )


def downgrade():
    op.drop_column("action_items", "details")
    op.drop_index("ix_action_items_identity", "action_items")
    op.drop_column("action_items", "identity")
    op.drop_column("businesses", "description")
    op.drop_index("ix_households_owner_user_id", "households")
    op.drop_constraint("fk_household_owner", "households", type_="foreignkey")
    op.drop_column("households", "owner_user_id")
