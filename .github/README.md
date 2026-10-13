# Mealie (sparkison fork)

A fork of [Mealie](https://github.com/mealie-recipes/mealie), the self-hosted recipe manager and meal planner, with a few extra meal planning features. It follows upstream's `mealie-next` branch closely: upstream changes are merged in automatically every day, tested, and published as a new image.

For everything else (features, configuration, API), see the [upstream project](https://github.com/mealie-recipes/mealie) and the [Mealie docs](https://docs.mealie.io/).

## What this fork adds

- **Custom meal plans**: named, undated plans (e.g. "Week A", "Holidays") alongside the calendar. Add recipes to them directly, move a week's meals into one, and apply a plan to any week to fill in the calendar. Each entry keeps its own servings scale.
- **Filter by favorites**: show only your favorite recipes on the recipe search page.
- **Servings saved back from the recipe page**: when you open a recipe from a meal plan or custom plan entry, changing its servings updates that entry.

Per-entry meal plan servings and creating a shopping list on the fly started in this fork and are now part of upstream Mealie ([#8701](https://github.com/mealie-recipes/mealie/pull/8701)).

## Using it

Images are published to [GitHub Container Registry](https://github.com/sparkison/mealie/pkgs/container/mealie) as `ghcr.io/sparkison/mealie:dev` (linux/amd64). It's a drop-in replacement for the upstream image: install Mealie as described in the [upstream docs](https://docs.mealie.io/documentation/getting-started/installation/installation-checklist/) and swap in this image.

```yaml
services:
  mealie:
    image: ghcr.io/sparkison/mealie:dev
```

The `dev` tag tracks this fork's `sparkison` branch, so it updates whenever upstream does. Back up your data before updating, as you would with upstream nightly builds.

## Maintaining

See [FORK.md](../FORK.md) for how upstream syncs, the release pipeline and this fork's database migrations work.
