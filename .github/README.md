# Mealie (sparkison fork)

A fork of [Mealie](https://github.com/mealie-recipes/mealie), the self-hosted recipe manager and meal planner, with a few extra meal planning features. It follows upstream's `mealie-next` branch closely: upstream changes are merged in automatically every day, tested, and published as a new image.

For everything else (features, configuration, API), see the [upstream project](https://github.com/mealie-recipes/mealie) and the [Mealie docs](https://docs.mealie.io/).

## What this fork adds

- **Meal plan servings scale**: set a servings scale on each meal plan entry. The scale carries into "Add to shopping list" (per recipe, per day or for the whole week) and into the recipe page when you open the recipe from the planner.
- **Custom meal plans**: named, undated plans (e.g. "Week A", "Holidays") alongside the calendar. Add recipes to them directly, move a week's meals into one, and apply a plan to any week to fill in the calendar.
- **Filter by favorites**: show only your favorite recipes on the recipe search page.
- **New shopping list on the fly**: create a shopping list straight from the "Add to shopping list" dialog.

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
