import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

from tests.utils.alembic_reader import ALEMBIC_MIGRATIONS, import_file


def _migration():
    path = next(ALEMBIC_MIGRATIONS.glob("*56b63fbd7a5f*.py"))
    return import_file("add_named_meal_plans", path)


migration = _migration()

PLANS = "group_meal_plan_named_plans"
ENTRIES = "group_meal_plan_named_plan_entries"


@pytest.fixture()
def connection():
    engine = sa.create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(sa.text("CREATE TABLE groups (id CHAR(32) PRIMARY KEY)"))
        conn.execute(sa.text("CREATE TABLE recipes (id CHAR(32) PRIMARY KEY)"))
        yield conn
    engine.dispose()


def run(conn: sa.Connection, fn) -> None:
    with Operations.context(MigrationContext.configure(conn)):
        fn()


def column_names(conn: sa.Connection, table: str) -> list[str]:
    return [column["name"] for column in sa.inspect(conn).get_columns(table)]


def index_names(conn: sa.Connection, table: str) -> set[str]:
    return {index["name"] for index in sa.inspect(conn).get_indexes(table)}


def create_prerelease_schema(conn: sa.Connection) -> None:
    """The schema left behind by the pre-release migrations: no recipe_scale, no created_at indexes"""
    conn.execute(
        sa.text(
            f"CREATE TABLE {PLANS} (id CHAR(32) PRIMARY KEY, name VARCHAR NOT NULL, group_id CHAR(32) NOT NULL, "
            "created_at DATETIME, update_at DATETIME)"
        )
    )
    conn.execute(sa.text(f"CREATE INDEX ix_{PLANS}_group_id ON {PLANS} (group_id)"))
    conn.execute(sa.text(f"CREATE INDEX ix_{PLANS}_name ON {PLANS} (name)"))
    conn.execute(
        sa.text(
            f"CREATE TABLE {ENTRIES} (id CHAR(32) PRIMARY KEY, plan_id CHAR(32) NOT NULL, recipe_id CHAR(32), "
            "entry_type VARCHAR NOT NULL DEFAULT 'dinner', title VARCHAR NOT NULL DEFAULT '', "
            "text VARCHAR NOT NULL DEFAULT '', created_at DATETIME, update_at DATETIME)"
        )
    )
    conn.execute(sa.text(f"CREATE INDEX ix_{ENTRIES}_plan_id ON {ENTRIES} (plan_id)"))
    conn.execute(sa.text(f"CREATE INDEX ix_{ENTRIES}_recipe_id ON {ENTRIES} (recipe_id)"))
    conn.execute(sa.text(f"INSERT INTO {PLANS} (id, name, group_id) VALUES ('p1', 'Week A', 'g1')"))
    conn.execute(sa.text(f"INSERT INTO {ENTRIES} (id, plan_id, title) VALUES ('e1', 'p1', 'Tacos')"))


def test_upgrade_creates_tables(connection: sa.Connection):
    run(connection, migration.upgrade)

    assert "recipe_scale" in column_names(connection, ENTRIES)
    assert index_names(connection, PLANS) == {
        f"ix_{PLANS}_group_id",
        f"ix_{PLANS}_name",
        f"ix_{PLANS}_created_at",
    }
    assert index_names(connection, ENTRIES) == {
        f"ix_{ENTRIES}_plan_id",
        f"ix_{ENTRIES}_recipe_id",
        f"ix_{ENTRIES}_created_at",
    }


def test_upgrade_completes_prerelease_schema_and_keeps_data(connection: sa.Connection):
    create_prerelease_schema(connection)

    run(connection, migration.upgrade)

    assert "recipe_scale" in column_names(connection, ENTRIES)
    assert f"ix_{PLANS}_created_at" in index_names(connection, PLANS)
    assert f"ix_{ENTRIES}_created_at" in index_names(connection, ENTRIES)

    row = connection.execute(sa.text(f"SELECT title, recipe_scale FROM {ENTRIES} WHERE id = 'e1'")).one()
    assert row.title == "Tacos"
    assert row.recipe_scale == 1
    assert connection.execute(sa.text(f"SELECT name FROM {PLANS}")).scalar_one() == "Week A"


def test_upgrade_is_idempotent(connection: sa.Connection):
    run(connection, migration.upgrade)
    run(connection, migration.upgrade)

    assert column_names(connection, ENTRIES).count("recipe_scale") == 1


def test_downgrade_drops_tables(connection: sa.Connection):
    run(connection, migration.upgrade)
    run(connection, migration.downgrade)

    inspector = sa.inspect(connection)
    assert not inspector.has_table(PLANS)
    assert not inspector.has_table(ENTRIES)
