"""Keep this fork's alembic migrations in one linear chain after merging upstream.

Upstream's migrations form a single chain (tests/unit_tests/test_alembic.py), and existing fork
databases are stamped somewhere along the fork's version of that chain. After merging upstream:

1. Fork migrations a merge silently deleted are restored from HEAD (the pre-merge fork branch).
2. When upstream added a migration branching from the same parent as a run of fork migrations,
   that upstream migration is re-pointed to come after the fork run, so there is one head again.
   It must come *after* the fork run: databases already past the fork run would otherwise treat
   it as applied and skip it.
3. Fork migration files are renamed if needed so that sorting files by name still follows the chain.

Upstream migrations are only ever re-pointed, never renamed. Anything this script does not
recognise is reported as an error instead of being guessed at.

Fork revisions are listed in fork_migrations.txt next to this script.

Usage:
    python dev/scripts/fork_migrations.py           # fix in place
    python dev/scripts/fork_migrations.py --check   # report only, exit 1 if changes are needed
"""

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).parents[2]
VERSIONS_DIR = ROOT / "mealie" / "alembic" / "versions"
FORK_LIST = Path(__file__).with_name("fork_migrations.txt")

TIMESTAMP_FORMAT = "%Y-%m-%d-%H.%M.%S"
FILENAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}-\d{2}\.\d{2}\.\d{2})_(\w+?)_(.+)\.py$")
REVISION_RE = re.compile(r"^revision\s*(?::[^=]*)?=\s*[\"'](\w+)[\"']", re.MULTILINE)
DOWN_REVISION_RE = re.compile(r"^(down_revision\s*(?::[^=]*)?=\s*)(.+)$", re.MULTILINE)
REVISES_RE = re.compile(r"^(Revises:\s*)(\w*)\s*$", re.MULTILINE)


class ForkMigrationError(Exception):
    pass


@dataclass
class Migration:
    path: Path
    revision: str
    down_revision: str | None

    @property
    def timestamp(self) -> datetime:
        # Filenames carry no timezone; only their order matters
        return datetime.strptime(self.path.name[:19], TIMESTAMP_FORMAT).replace(tzinfo=UTC)


def read_fork_revisions(fork_list: Path = FORK_LIST) -> list[str]:
    lines = (line.split("#", 1)[0].strip() for line in fork_list.read_text().splitlines())
    return [line for line in lines if line]


def parse_migration(path: Path) -> Migration:
    if not FILENAME_RE.match(path.name):
        raise ForkMigrationError(f"{path.name}: filename does not match YYYY-MM-DD-HH.MM.SS_<revision>_<slug>.py")

    text = path.read_text()
    revision = REVISION_RE.search(text)
    down = DOWN_REVISION_RE.search(text)
    if not revision or not down:
        raise ForkMigrationError(f"{path.name}: could not find revision/down_revision")

    down_value = down.group(2).strip()
    if down_value == "None":
        down_revision = None
    elif match := re.fullmatch(r"[\"'](\w+)[\"']", down_value):
        down_revision = match.group(1)
    else:
        raise ForkMigrationError(f"{path.name}: unsupported down_revision {down_value} (merge migrations?)")

    return Migration(path=path, revision=revision.group(1), down_revision=down_revision)


def load_migrations(versions_dir: Path) -> dict[str, Migration]:
    migrations: dict[str, Migration] = {}
    for path in sorted(versions_dir.glob("*.py")):
        migration = parse_migration(path)
        if migration.revision in migrations:
            raise ForkMigrationError(f"duplicate revision {migration.revision} in {path.name}")
        migrations[migration.revision] = migration
    return migrations


def restore_deleted(versions_dir: Path, fork_revisions: list[str], log: list[str], check: bool) -> None:
    present = set(load_migrations(versions_dir))
    missing = [rev for rev in fork_revisions if rev not in present]
    if not missing:
        return

    repo_dir = versions_dir
    ls_tree = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", "HEAD", "--", "."],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    if ls_tree.returncode != 0:
        raise ForkMigrationError(f"fork migrations {missing} are missing and git could not list HEAD")
    tracked = ls_tree.stdout.splitlines()

    for rev in missing:
        matches = [name for name in tracked if f"_{rev}_" in Path(name).name]
        if len(matches) != 1:
            raise ForkMigrationError(f"fork migration {rev} is missing and not found in HEAD")
        log.append(f"restore deleted fork migration {Path(matches[0]).name}")
        if not check:
            subprocess.run(["git", "checkout", "HEAD", "--", matches[0]], cwd=repo_dir, check=True)


def set_down_revision(migration: Migration, new_down: str) -> None:
    text = migration.path.read_text()
    text = DOWN_REVISION_RE.sub(lambda m: f'{m.group(1)}"{new_down}"', text, count=1)
    text = REVISES_RE.sub(lambda m: f"{m.group(1)}{new_down}", text, count=1)
    migration.path.write_text(text)
    migration.down_revision = new_down


def children_of(migrations: dict[str, Migration]) -> dict[str | None, list[str]]:
    children: dict[str | None, list[str]] = {}
    for migration in migrations.values():
        children.setdefault(migration.down_revision, []).append(migration.revision)
    return children


def linearize(migrations: dict[str, Migration], fork: set[str], log: list[str], check: bool) -> None:
    for _ in range(len(migrations)):
        children = children_of(migrations)
        forks = {parent: kids for parent, kids in children.items() if len(kids) > 1}
        if not forks:
            return

        parent, kids = next(iter(forks.items()))
        fork_kids = [kid for kid in kids if kid in fork]
        upstream_kids = [kid for kid in kids if kid not in fork]
        if len(fork_kids) != 1 or len(upstream_kids) != 1:
            raise ForkMigrationError(f"{parent} has children {kids}; expected one fork and one upstream migration")

        # Follow the run of fork migrations to its end
        end = fork_kids[0]
        while next_kids := children.get(end):
            if len(next_kids) != 1 or next_kids[0] not in fork:
                raise ForkMigrationError(
                    f"fork migrations after {parent} continue into {next_kids}; resolve the chain by hand"
                )
            end = next_kids[0]

        upstream = migrations[upstream_kids[0]]
        log.append(f"re-point upstream {upstream.path.name}: {parent} -> {end}")
        if check:
            upstream.down_revision = end
        else:
            set_down_revision(upstream, end)

    raise ForkMigrationError("could not linearize migrations")


def chain_order(migrations: dict[str, Migration]) -> list[Migration]:
    children = children_of(migrations)
    roots = children.get(None, [])
    if len(roots) != 1:
        raise ForkMigrationError(f"expected one base migration, found {roots}")

    order = [migrations[roots[0]]]
    while next_kids := children.get(order[-1].revision):
        order.append(migrations[next_kids[0]])

    if len(order) != len(migrations):
        raise ForkMigrationError("migrations do not form a single chain")
    return order


def fix_file_order(order: list[Migration], fork: set[str], log: list[str], check: bool) -> None:
    def is_sorted() -> bool:
        names = [m.path.name for m in order]
        return names == sorted(names)

    if is_sorted():
        return

    # Give every out-of-place run of fork migrations timestamps between its upstream neighbours
    i = 0
    while i < len(order):
        if order[i].revision not in fork:
            i += 1
            continue

        start = i
        while i < len(order) and order[i].revision in fork:
            i += 1
        run = order[start:i]
        before = order[start - 1].timestamp if start > 0 else None
        after = order[i].timestamp if i < len(order) else None

        timestamps = [m.timestamp for m in run]
        in_place = timestamps == sorted(set(timestamps)) and (before is None or timestamps[0] > before)
        in_place = in_place and (after is None or timestamps[-1] < after)
        if in_place:
            continue

        if after is None:
            raise ForkMigrationError(f"cannot order fork migrations at the end of the chain: {run[0].path.name}")
        new_timestamps = [after - timedelta(seconds=len(run) - n) for n in range(len(run))]
        if before is not None and new_timestamps[0] <= before:
            raise ForkMigrationError(f"no room to order fork migrations between {before} and {after}")

        for migration, timestamp in zip(run, new_timestamps, strict=True):
            new_path = migration.path.with_name(timestamp.strftime(TIMESTAMP_FORMAT) + migration.path.name[19:])
            log.append(f"rename fork {migration.path.name} -> {new_path.name}")
            if not check:
                migration.path.rename(new_path)
            migration.path = new_path

    if not is_sorted():
        raise ForkMigrationError("upstream migrations are not in filename order; resolve by hand")


def run(versions_dir: Path = VERSIONS_DIR, fork_list: Path = FORK_LIST, check: bool = False) -> list[str]:
    """Apply (or with check=True, only report) the fixes; returns a log of what was or would be done"""
    fork_revisions = read_fork_revisions(fork_list)
    log: list[str] = []

    restore_deleted(versions_dir, fork_revisions, log, check)
    if check and log:
        # Restoring needs git; the remaining steps can't run against missing files
        return log

    migrations = load_migrations(versions_dir)
    unknown = [rev for rev in fork_revisions if rev not in migrations]
    if unknown:
        raise ForkMigrationError(f"fork revisions not found: {unknown}")

    fork = set(fork_revisions)
    linearize(migrations, fork, log, check)
    fix_file_order(chain_order(migrations), fork, log, check)
    return log


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="report needed changes without making them")
    args = parser.parse_args()

    try:
        log = run(check=args.check)
    except ForkMigrationError as e:
        sys.stderr.write(f"error: {e}\n")
        return 2

    for line in log:
        sys.stdout.write(f"{line}\n")
    if not log:
        sys.stdout.write("fork migrations are in order\n")
    return 1 if args.check and log else 0


if __name__ == "__main__":
    sys.exit(main())
