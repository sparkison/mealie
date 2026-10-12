"""add named meal plans

Revision ID: 56b63fbd7a5f
Revises: 4bb08e6c422a
Create Date: 2026-10-12 08:09:30.000000

"""

import sqlalchemy as sa
from alembic import op

import mealie.db.migration_types

# revision identifiers, used by Alembic.
revision = "56b63fbd7a5f"
down_revision: str | None = "4bb08e6c422a"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

PLANS = "group_meal_plan_named_plans"
ENTRIES = "group_meal_plan_named_plan_entries"

# Installs that ran a pre-release build of this feature already have some of this schema,
# so every step only creates what is missing
INDEXES = {
    PLANS: ["group_id", "name", "created_at"],
    ENTRIES: ["plan_id", "recipe_id", "created_at"],
}


def inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def create_missing_indexes(table: str) -> None:
    existing = {index["name"] for index in inspector().get_indexes(table)}
    with op.batch_alter_table(table, schema=None) as batch_op:
        for column in INDEXES[table]:
            name = f"ix_{table}_{column}"
            if name not in existing:
                batch_op.create_index(name, [column], unique=False)


def upgrade():
    if not inspector().has_table(PLANS):
        op.create_table(
            PLANS,
            sa.Column("id", mealie.db.migration_types.GUID(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("group_id", mealie.db.migration_types.GUID(), nullable=False),
            sa.Column("created_at", mealie.db.migration_types.NaiveDateTime(), nullable=True),
            sa.Column("update_at", mealie.db.migration_types.NaiveDateTime(), nullable=True),
            sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    create_missing_indexes(PLANS)

    if not inspector().has_table(ENTRIES):
        op.create_table(
            ENTRIES,
            sa.Column("id", mealie.db.migration_types.GUID(), nullable=False),
            sa.Column("plan_id", mealie.db.migration_types.GUID(), nullable=False),
            sa.Column("recipe_id", mealie.db.migration_types.GUID(), nullable=True),
            sa.Column("entry_type", sa.String(), nullable=False, server_default="dinner"),
            sa.Column("title", sa.String(), nullable=False, server_default=""),
            sa.Column("text", sa.String(), nullable=False, server_default=""),
            sa.Column("recipe_scale", sa.Float(), nullable=False, server_default=sa.text("1")),
            sa.Column("created_at", mealie.db.migration_types.NaiveDateTime(), nullable=True),
            sa.Column("update_at", mealie.db.migration_types.NaiveDateTime(), nullable=True),
            sa.ForeignKeyConstraint(["plan_id"], [f"{PLANS}.id"]),
            sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    elif "recipe_scale" not in {column["name"] for column in inspector().get_columns(ENTRIES)}:
        with op.batch_alter_table(ENTRIES, schema=None) as batch_op:
            batch_op.add_column(sa.Column("recipe_scale", sa.Float(), nullable=False, server_default=sa.text("1")))
    create_missing_indexes(ENTRIES)


def downgrade():
    for table in (ENTRIES, PLANS):
        if inspector().has_table(table):
            op.drop_table(table)
