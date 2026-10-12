import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

from tests.utils.alembic_reader import ALEMBIC_MIGRATIONS, import_file


def _migration():
    path = next(ALEMBIC_MIGRATIONS.glob("*4bb08e6c422a*.py"))
    return import_file("add_recipe_scale_to_meal_plan", path)


migration = _migration()


@pytest.fixture()
def connection():
    engine = sa.create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(sa.text("CREATE TABLE group_meal_plans (id INTEGER PRIMARY KEY, title VARCHAR NOT NULL)"))
        conn.execute(sa.text("INSERT INTO group_meal_plans (id, title) VALUES (1, 'existing entry')"))
        yield conn
    engine.dispose()


def run(conn: sa.Connection, fn) -> None:
    with Operations.context(MigrationContext.configure(conn)):
        fn()


def column_names(conn: sa.Connection) -> list[str]:
    return [column["name"] for column in sa.inspect(conn).get_columns("group_meal_plans")]


def test_upgrade_adds_column_defaulting_existing_rows(connection: sa.Connection):
    run(connection, migration.upgrade)

    assert "recipe_scale" in column_names(connection)
    scale = connection.execute(sa.text("SELECT recipe_scale FROM group_meal_plans WHERE id = 1")).scalar_one()
    assert scale == 1


def test_upgrade_skips_existing_column(connection: sa.Connection):
    # Simulates a database that already ran a pre-release build of this migration
    connection.execute(sa.text("ALTER TABLE group_meal_plans ADD COLUMN recipe_scale FLOAT NOT NULL DEFAULT 2"))

    run(connection, migration.upgrade)

    assert column_names(connection).count("recipe_scale") == 1
    scale = connection.execute(sa.text("SELECT recipe_scale FROM group_meal_plans WHERE id = 1")).scalar_one()
    assert scale == 2


def test_downgrade_drops_column(connection: sa.Connection):
    run(connection, migration.upgrade)
    run(connection, migration.downgrade)

    assert "recipe_scale" not in column_names(connection)


def test_downgrade_skips_missing_column(connection: sa.Connection):
    run(connection, migration.downgrade)

    assert "recipe_scale" not in column_names(connection)
