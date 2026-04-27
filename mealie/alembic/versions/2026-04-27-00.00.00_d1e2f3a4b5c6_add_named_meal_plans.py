"""add named meal plans

Revision ID: d1e2f3a4b5c6
Revises: a8f3b2c1d4e5
Create Date: 2026-04-27 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

from mealie.db.migration_types import GUID

# revision identifiers, used by Alembic.
revision: str = "d1e2f3a4b5c6"
down_revision: str | None = "a8f3b2c1d4e5"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    op.create_table(
        "group_meal_plan_named_plans",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("group_id", GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_group_meal_plan_named_plans_group_id", "group_meal_plan_named_plans", ["group_id"])
    op.create_index("ix_group_meal_plan_named_plans_name", "group_meal_plan_named_plans", ["name"])

    op.create_table(
        "group_meal_plan_named_plan_entries",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("plan_id", GUID(), nullable=False),
        sa.Column("recipe_id", GUID(), nullable=True),
        sa.Column("entry_type", sa.String(), nullable=False, server_default="dinner"),
        sa.Column("title", sa.String(), nullable=False, server_default=""),
        sa.Column("text", sa.String(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["plan_id"], ["group_meal_plan_named_plans.id"]),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_group_meal_plan_named_plan_entries_plan_id", "group_meal_plan_named_plan_entries", ["plan_id"])
    op.create_index(
        "ix_group_meal_plan_named_plan_entries_recipe_id", "group_meal_plan_named_plan_entries", ["recipe_id"]
    )


def downgrade():
    op.drop_index("ix_group_meal_plan_named_plan_entries_recipe_id", "group_meal_plan_named_plan_entries")
    op.drop_index("ix_group_meal_plan_named_plan_entries_plan_id", "group_meal_plan_named_plan_entries")
    op.drop_table("group_meal_plan_named_plan_entries")
    op.drop_index("ix_group_meal_plan_named_plans_name", "group_meal_plan_named_plans")
    op.drop_index("ix_group_meal_plan_named_plans_group_id", "group_meal_plan_named_plans")
    op.drop_table("group_meal_plan_named_plans")
