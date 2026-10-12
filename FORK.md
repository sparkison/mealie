# sparkison/mealie fork

This fork tracks upstream [`mealie-recipes/mealie`](https://github.com/mealie-recipes/mealie) `mealie-next` and adds:

- **Meal plan recipe scale**: per-entry servings scale in the meal planner, carried into shopping lists
- **Custom meal plans**: named, undated plans that can be applied to a week
- **Filter by favorites** on the recipe explorer

`sparkison` is the only long-lived branch. Every push to it runs the tests and publishes `ghcr.io/sparkison/mealie:dev` (`.github/workflows/fork-dev-build.yml`).

## Upstream sync

`.github/workflows/fork-upstream-sync.yml` runs daily (or from the Actions tab):

1. Merges upstream `mealie-next` into a `sync/upstream` branch.
2. Runs `dev/scripts/fork_migrations.py` to keep the alembic chain linear (see below).
3. Opens a PR into `sparkison` and merges it once the Fork Dev Build checks pass, which publishes a new image.

Anything that needs a person (merge conflicts, a migration chain the script doesn't recognise, failing tests) is reported in one issue labelled `upstream-sync`. The next successful sync closes it.

### Resolving a sync by hand

```sh
git switch sparkison && git pull
git fetch upstream && git merge upstream/mealie-next
python3 dev/scripts/fork_migrations.py   # after resolving conflicts, before committing
task py:test && task ui:check
git push
```

## Migrations

Upstream requires a single alembic chain whose files sort by name in chain order (`tests/unit_tests/test_alembic.py`), and existing databases are stamped somewhere along this fork's version of that chain. So:

- **Every fork migration's revision goes in `dev/scripts/fork_migrations.txt`.** Create one as usual (`task py:migrate -- "message"`), then add its revision there.
- **Never edit or remove a fork migration once it has been deployed**, since databases depend on it being in their history. Make new ones skip what already exists if they might overlap with upstream later.
- After merging upstream, `fork_migrations.py` restores fork migrations the merge deleted, re-points upstream's newest migration to come after a run of fork migrations that ends at the tip (so databases already past the fork migrations still run it), and renames fork files to keep the filename order. It never renames upstream files, and stops with an error on anything else.

The first fork migrations (`a8f3b2c1d4e5`, `d1e2f3a4b5c6`, `e2f3a4b5c6d7`) sit between upstream's `4395a04f7784` and `c7427796f7b6`, whose `down_revision` is edited to `e2f3a4b5c6d7`. Keep that edit if a merge ever touches it.

## Local development

```sh
task setup   # dependencies
task py      # backend, using .env
task ui      # frontend
```

Use a separate database for experiments (for example `DB_ENGINE=sqlite task py`): once a database has run a migration this branch doesn't have, this branch can no longer start against it.
