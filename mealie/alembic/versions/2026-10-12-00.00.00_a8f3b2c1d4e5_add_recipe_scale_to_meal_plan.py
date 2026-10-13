"""add recipe_scale to group_meal_plans

Revision ID: a8f3b2c1d4e5
Revises: 27621d27c7e1
Create Date: 2026-10-12 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a8f3b2c1d4e5"
down_revision: str | None = "27621d27c7e1"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def has_recipe_scale_column() -> bool:
    # sparkison fork: databases that ran this fork's earlier copy of this migration already have the column
    columns = sa.inspect(op.get_bind()).get_columns("group_meal_plans")
    return any(column["name"] == "recipe_scale" for column in columns)


def upgrade():
    if has_recipe_scale_column():
        return

    with op.batch_alter_table("group_meal_plans", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "recipe_scale",
                sa.Float(),
                nullable=False,
                server_default=sa.text("1"),
            )
        )


def downgrade():
    with op.batch_alter_table("group_meal_plans", schema=None) as batch_op:
        batch_op.drop_column("recipe_scale")
