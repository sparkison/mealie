from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi.testclient import TestClient

from mealie.schema.recipe.recipe import Recipe
from tests.utils.factories import random_string
from tests.utils.fixture_schemas import TestUser

PLANS = "/api/households/mealplans/named-plans"


def create_recipe(user: TestUser) -> Recipe:
    return user.repos.recipes.create(Recipe(user_id=user.user_id, group_id=UUID(user.group_id), name=random_string()))


def create_plan(api_client: TestClient, user: TestUser) -> dict:
    response = api_client.post(PLANS, json={"name": random_string()}, headers=user.token)
    assert response.status_code == 201
    return response.json()


def test_named_plan_routes_are_not_shadowed_by_mealplan_routes(api_client: TestClient, unique_user: TestUser):
    # The base mealplan router has a /{item_id} route; named plans must be registered before it
    plan = create_plan(api_client, unique_user)

    response = api_client.get(PLANS, headers=unique_user.token)
    assert response.status_code == 200
    assert plan["id"] in [item["id"] for item in response.json()["items"]]


def test_crud_named_plan(api_client: TestClient, unique_user: TestUser):
    plan = create_plan(api_client, unique_user)

    response = api_client.put(f"{PLANS}/{plan['id']}", json={"name": "Week A"}, headers=unique_user.token)
    assert response.status_code == 200
    assert response.json()["name"] == "Week A"

    response = api_client.delete(f"{PLANS}/{plan['id']}", headers=unique_user.token)
    assert response.status_code == 200

    response = api_client.get(f"{PLANS}/{plan['id']}", headers=unique_user.token)
    assert response.status_code == 404


def test_named_plan_entry_keeps_recipe_scale(api_client: TestClient, unique_user: TestUser):
    plan = create_plan(api_client, unique_user)
    recipe = create_recipe(unique_user)

    response = api_client.post(
        f"{PLANS}/{plan['id']}/entries",
        json={"recipeId": str(recipe.id), "entryType": "dinner", "recipeScale": 2.5},
        headers=unique_user.token,
    )
    assert response.status_code == 201
    entry = response.json()
    assert entry["recipeScale"] == 2.5
    assert entry["recipe"]["id"] == str(recipe.id)

    response = api_client.put(
        f"{PLANS}/{plan['id']}/entries/{entry['id']}",
        json={"recipeId": str(recipe.id), "entryType": "dinner", "recipeScale": 0.5},
        headers=unique_user.token,
    )
    assert response.status_code == 200

    response = api_client.get(f"{PLANS}/{plan['id']}/entries/{entry['id']}", headers=unique_user.token)
    assert response.json()["recipeScale"] == 0.5


def test_apply_named_plan_carries_recipe_scale_to_meal_plans(api_client: TestClient, unique_user: TestUser):
    plan = create_plan(api_client, unique_user)
    scales = [2, 0.5]
    for scale in scales:
        response = api_client.post(
            f"{PLANS}/{plan['id']}/entries",
            json={"recipeId": str(create_recipe(unique_user).id), "entryType": "dinner", "recipeScale": scale},
            headers=unique_user.token,
        )
        assert response.status_code == 201

    start = datetime.now(UTC).date() + timedelta(days=30)
    response = api_client.post(
        f"{PLANS}/{plan['id']}/apply", json={"startDate": start.isoformat()}, headers=unique_user.token
    )
    assert response.status_code == 201

    created = sorted(response.json(), key=lambda meal: meal["date"])
    assert [meal["date"] for meal in created] == [start.isoformat(), (start + timedelta(days=1)).isoformat()]
    assert [meal["recipeScale"] for meal in created] == scales


def test_named_plans_are_scoped_to_group(api_client: TestClient, unique_user: TestUser, g2_user: TestUser):
    plan = create_plan(api_client, unique_user)

    response = api_client.get(f"{PLANS}/{plan['id']}", headers=g2_user.token)
    assert response.status_code == 404

    response = api_client.get(PLANS, headers=g2_user.token)
    assert plan["id"] not in [item["id"] for item in response.json()["items"]]
