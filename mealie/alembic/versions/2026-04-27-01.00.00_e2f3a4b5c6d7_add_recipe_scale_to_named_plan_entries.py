"""add recipe_scale to named plan entries

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-04-27 01:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e2f3a4b5c6d7"
down_revision: str | None = "d1e2f3a4b5c6"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    with op.batch_alter_table("group_meal_plan_named_plan_entries") as batch_op:
        batch_op.add_column(sa.Column("recipe_scale", sa.Float(), nullable=False, server_default="1.0"))


def downgrade():
    with op.batch_alter_table("group_meal_plan_named_plan_entries") as batch_op:
        batch_op.drop_column("recipe_scale")
