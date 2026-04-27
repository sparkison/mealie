from datetime import date, datetime
from uuid import UUID

from pydantic import ConfigDict
from sqlalchemy.orm import selectinload

from mealie.db.models.household.mealplan import GroupMealPlanNamedPlan, GroupMealPlanNamedPlanEntry
from mealie.db.models.recipe import RecipeModel
from mealie.schema._mealie import MealieModel
from mealie.schema.recipe.recipe import RecipeSummary
from mealie.schema.response.pagination import PaginationBase


class CreateNamedMealPlan(MealieModel):
    name: str


class SaveNamedMealPlan(CreateNamedMealPlan):
    group_id: UUID


class ReadNamedMealPlan(MealieModel):
    id: UUID
    name: str
    group_id: UUID
    created_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class NamedMealPlanPagination(PaginationBase):
    items: list[ReadNamedMealPlan]


class CreateNamedPlanEntry(MealieModel):
    recipe_id: UUID | None = None
    entry_type: str = "dinner"
    title: str = ""
    text: str = ""
    recipe_scale: float = 1.0

    @classmethod
    def loader_options(cls):
        return [
            selectinload(GroupMealPlanNamedPlanEntry.recipe).joinedload(RecipeModel.recipe_category),
            selectinload(GroupMealPlanNamedPlanEntry.recipe).joinedload(RecipeModel.tags),
            selectinload(GroupMealPlanNamedPlanEntry.recipe).joinedload(RecipeModel.tools),
        ]


class SaveNamedPlanEntry(CreateNamedPlanEntry):
    plan_id: UUID


class ReadNamedPlanEntry(MealieModel):
    id: UUID
    plan_id: UUID
    recipe_id: UUID | None = None
    entry_type: str = "dinner"
    title: str = ""
    text: str = ""
    recipe_scale: float = 1.0
    recipe: RecipeSummary | None = None
    created_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def loader_options(cls):
        return [
            selectinload(GroupMealPlanNamedPlanEntry.recipe).joinedload(RecipeModel.recipe_category),
            selectinload(GroupMealPlanNamedPlanEntry.recipe).joinedload(RecipeModel.tags),
            selectinload(GroupMealPlanNamedPlanEntry.recipe).joinedload(RecipeModel.tools),
        ]


class ApplyNamedPlanPayload(MealieModel):
    start_date: date


class AddRandomNamedPlanEntry(MealieModel):
    entry_type: str = "dinner"


class ReadNamedMealPlanWithEntries(ReadNamedMealPlan):
    entries: list[ReadNamedPlanEntry] = []

    @classmethod
    def loader_options(cls):
        return [
            selectinload(GroupMealPlanNamedPlan.entries)
            .selectinload(GroupMealPlanNamedPlanEntry.recipe)
            .joinedload(RecipeModel.recipe_category),
            selectinload(GroupMealPlanNamedPlan.entries)
            .selectinload(GroupMealPlanNamedPlanEntry.recipe)
            .joinedload(RecipeModel.tags),
            selectinload(GroupMealPlanNamedPlan.entries)
            .selectinload(GroupMealPlanNamedPlanEntry.recipe)
            .joinedload(RecipeModel.tools),
        ]
