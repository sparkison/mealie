import subprocess
from pathlib import Path

import pytest

from tests.utils.alembic_reader import import_file

fork_migrations = import_file("fork_migrations", Path(__file__).parents[2] / "dev" / "scripts" / "fork_migrations.py")


def write_migration(versions: Path, timestamp: str, revision: str, down_revision: str | None) -> Path:
    down = f'"{down_revision}"' if down_revision else "None"
    path = versions / f"{timestamp}_{revision}_migration_{revision}.py"
    path.write_text(
        f'"""migration {revision}\n\nRevision ID: {revision}\nRevises: {down_revision or ""}\n"""\n\n'
        f'revision = "{revision}"\n'
        f"down_revision: str | None = {down}\n"
    )
    return path


@pytest.fixture()
def versions(tmp_path: Path) -> Path:
    path = tmp_path / "versions"
    path.mkdir()
    return path


@pytest.fixture()
def fork_list(tmp_path: Path) -> Path:
    path = tmp_path / "fork_migrations.txt"
    path.write_text("# fork revisions\nf1  # first\nf2\n")
    return path


def chain_by_filename(versions: Path) -> list[tuple[str, str | None]]:
    migrations = [fork_migrations.parse_migration(path) for path in sorted(versions.glob("*.py"))]
    return [(m.revision, m.down_revision) for m in migrations]


def assert_linear_in_filename_order(versions: Path) -> None:
    # The same invariant tests/unit_tests/test_alembic.py checks on the real migrations
    chain = chain_by_filename(versions)
    for (previous, _), (_, down) in zip(chain, chain[1:], strict=False):
        assert down == previous


def test_linear_chain_needs_no_changes(versions: Path, fork_list: Path):
    write_migration(versions, "2026-01-01-00.00.00", "u1", None)
    write_migration(versions, "2026-02-01-00.00.00", "f1", "u1")
    write_migration(versions, "2026-02-02-00.00.00", "f2", "f1")
    write_migration(versions, "2026-03-01-00.00.00", "u2", "f2")

    assert fork_migrations.run(versions, fork_list) == []


def test_upstream_migration_is_moved_after_fork_migrations(versions: Path, fork_list: Path):
    write_migration(versions, "2026-01-01-00.00.00", "u1", None)
    write_migration(versions, "2026-02-01-00.00.00", "f1", "u1")
    write_migration(versions, "2026-02-02-00.00.00", "f2", "f1")
    # Upstream added a migration on top of its own head, which the fork migrations also follow
    upstream = write_migration(versions, "2026-03-01-00.00.00", "u2", "u1")

    log = fork_migrations.run(versions, fork_list)

    assert log == [f"re-point upstream {upstream.name}: u1 -> f2"]
    assert fork_migrations.parse_migration(upstream).down_revision == "f2"
    assert "Revises: f2" in upstream.read_text()
    assert_linear_in_filename_order(versions)


def test_fork_migrations_dated_after_upstream_are_renamed(versions: Path, fork_list: Path):
    write_migration(versions, "2026-01-01-00.00.00", "u1", None)
    write_migration(versions, "2026-04-01-00.00.00", "f1", "u1")
    write_migration(versions, "2026-04-02-00.00.00", "f2", "f1")
    # Written upstream before the fork migrations, but merged after them
    upstream = write_migration(versions, "2026-03-01-00.00.00", "u2", "u1")

    fork_migrations.run(versions, fork_list)

    assert upstream.exists(), "upstream migrations are never renamed"
    assert sorted(path.name[:19] for path in versions.glob("*_f*_*.py")) == [
        "2026-02-28-23.59.58",
        "2026-02-28-23.59.59",
    ]
    assert_linear_in_filename_order(versions)


def test_fixing_twice_is_a_no_op(versions: Path, fork_list: Path):
    write_migration(versions, "2026-01-01-00.00.00", "u1", None)
    write_migration(versions, "2026-04-01-00.00.00", "f1", "u1")
    write_migration(versions, "2026-04-02-00.00.00", "f2", "f1")
    write_migration(versions, "2026-03-01-00.00.00", "u2", "u1")

    fork_migrations.run(versions, fork_list)

    assert fork_migrations.run(versions, fork_list) == []


def test_check_reports_without_changing_files(versions: Path, fork_list: Path):
    write_migration(versions, "2026-01-01-00.00.00", "u1", None)
    write_migration(versions, "2026-04-01-00.00.00", "f1", "u1")
    write_migration(versions, "2026-04-02-00.00.00", "f2", "f1")
    upstream = write_migration(versions, "2026-03-01-00.00.00", "u2", "u1")
    before = {path.name: path.read_text() for path in versions.glob("*.py")}

    log = fork_migrations.run(versions, fork_list, check=True)

    assert len(log) == 3
    assert log[0] == f"re-point upstream {upstream.name}: u1 -> f2"
    assert {path.name: path.read_text() for path in versions.glob("*.py")} == before


def test_unexpected_shape_is_an_error(versions: Path, fork_list: Path):
    write_migration(versions, "2026-01-01-00.00.00", "u1", None)
    write_migration(versions, "2026-02-01-00.00.00", "f1", "u1")
    write_migration(versions, "2026-02-02-00.00.00", "f2", "f1")
    # Two upstream migrations branching from the same parent: not something to guess at
    write_migration(versions, "2026-03-01-00.00.00", "u2", "u1")
    write_migration(versions, "2026-03-02-00.00.00", "u3", "u1")

    with pytest.raises(fork_migrations.ForkMigrationError, match="expected one fork and one upstream"):
        fork_migrations.run(versions, fork_list)


def test_fork_run_continuing_into_upstream_is_an_error(versions: Path, fork_list: Path):
    write_migration(versions, "2026-01-01-00.00.00", "u1", None)
    write_migration(versions, "2026-02-01-00.00.00", "f1", "u1")
    write_migration(versions, "2026-02-02-00.00.00", "f2", "f1")
    write_migration(versions, "2026-03-01-00.00.00", "u2", "f2")
    # Upstream re-pointed history behind the fork's splice
    write_migration(versions, "2026-03-02-00.00.00", "u3", "u1")

    with pytest.raises(fork_migrations.ForkMigrationError, match="resolve the chain by hand"):
        fork_migrations.run(versions, fork_list)


def test_deleted_fork_migration_is_restored_from_head(tmp_path: Path, fork_list: Path):
    repo = tmp_path / "repo"
    versions = repo / "versions"
    versions.mkdir(parents=True)
    write_migration(versions, "2026-01-01-00.00.00", "u1", None)
    write_migration(versions, "2026-02-01-00.00.00", "f1", "u1")
    deleted = write_migration(versions, "2026-02-02-00.00.00", "f2", "f1")

    def git(*args: str) -> None:
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)

    git("init", "-q")
    git("add", ".")
    git("-c", "user.name=test", "-c", "user.email=test@example.com", "commit", "-q", "-m", "fork")
    # What a merge from upstream does when it deletes a fork migration without a conflict
    git("rm", "-q", str(deleted.relative_to(repo)))

    log = fork_migrations.run(versions, fork_list)

    assert log == [f"restore deleted fork migration {deleted.name}"]
    assert deleted.exists()
    assert_linear_in_filename_order(versions)


def test_unknown_fork_revision_is_an_error(versions: Path, tmp_path: Path):
    write_migration(versions, "2026-01-01-00.00.00", "u1", None)
    fork_list = tmp_path / "list.txt"
    fork_list.write_text("nope\n")

    with pytest.raises(fork_migrations.ForkMigrationError):
        fork_migrations.run(versions, fork_list)


def test_real_fork_migrations_are_in_order():
    assert fork_migrations.run(check=True) == []
