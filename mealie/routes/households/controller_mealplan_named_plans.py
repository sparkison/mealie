from datetime import UTC, datetime, timedelta
from functools import cached_property

from fastapi import Depends, HTTPException
from pydantic import UUID4

from mealie.repos.all_repositories import get_repositories
from mealie.routes._base import controller
from mealie.routes._base.base_controllers import BaseCrudController
from mealie.routes._base.mixins import HttpRepo
from mealie.routes._base.routers import UserAPIRouter
from mealie.schema import mapper
from mealie.schema.meal_plan.new_meal import PlanEntryType, ReadPlanEntry, SavePlanEntry
from mealie.schema.meal_plan.plan_named import (
    AddRandomNamedPlanEntry,
    ApplyNamedPlanPayload,
    CreateNamedMealPlan,
    CreateNamedPlanEntry,
    NamedMealPlanPagination,
    ReadNamedMealPlan,
    ReadNamedPlanEntry,
    SaveNamedMealPlan,
    SaveNamedPlanEntry,
)
from mealie.schema.meal_plan.plan_rules import PlanRulesDay
from mealie.schema.response.pagination import PaginationQuery
from mealie.schema.response.responses import ErrorResponse

router = UserAPIRouter(prefix="/households/mealplans/named-plans", tags=["Households: Named Meal Plans"])


@controller(router)
class NamedMealPlansController(BaseCrudController):
    @cached_property
    def repo(self):
        return self.repos.named_meal_plans

    @cached_property
    def mixins(self):
        return HttpRepo[CreateNamedMealPlan, ReadNamedMealPlan, ReadNamedMealPlan](self.repo, self.logger)

    @router.get("", response_model=NamedMealPlanPagination)
    def get_all(self, q: PaginationQuery = Depends(PaginationQuery)):
        response = self.repo.page_all(pagination=q, override=ReadNamedMealPlan)
        response.set_pagination_guides(router.url_path_for("get_all"), q.model_dump())
        return response

    @router.post("", response_model=ReadNamedMealPlan, status_code=201)
    def create_one(self, data: CreateNamedMealPlan):
        save = mapper.cast(data, SaveNamedMealPlan, group_id=self.group.id)
        return self.mixins.create_one(save)

    @router.get("/{item_id}", response_model=ReadNamedMealPlan)
    def get_one(self, item_id: UUID4):
        return self.mixins.get_one(item_id)

    @router.put("/{item_id}", response_model=ReadNamedMealPlan)
    def update_one(self, item_id: UUID4, data: CreateNamedMealPlan):
        return self.mixins.update_one(data, item_id)

    @router.delete("/{item_id}", response_model=ReadNamedMealPlan)
    def delete_one(self, item_id: UUID4):
        return self.mixins.delete_one(item_id)  # type: ignore

    # ================================================================
    # Entries

    @router.get("/{item_id}/entries", response_model=list[ReadNamedPlanEntry])
    def get_entries(self, item_id: UUID4):
        return self.repos.named_meal_plans.get_entries(item_id)

    @router.post("/{item_id}/entries", response_model=ReadNamedPlanEntry, status_code=201)
    def add_entry(self, item_id: UUID4, data: CreateNamedPlanEntry):
        # Verify plan belongs to this group
        plan = self.repos.named_meal_plans.get_one(item_id)
        if plan is None:
            raise HTTPException(status_code=404, detail=ErrorResponse.respond("Plan not found"))
        save = SaveNamedPlanEntry(
            plan_id=item_id,
            recipe_id=data.recipe_id,
            entry_type=data.entry_type,
            title=data.title,
            text=data.text,
            recipe_scale=data.recipe_scale,
        )
        return self.repos.named_meal_plans.add_entry(save)

    @router.get("/{item_id}/entries/{entry_id}", response_model=ReadNamedPlanEntry)
    def get_entry(self, item_id: UUID4, entry_id: UUID4):
        entry = self.repos.named_meal_plans.get_entry(item_id, entry_id)
        if entry is None:
            raise HTTPException(status_code=404, detail=ErrorResponse.respond("Entry not found"))
        return entry

    @router.put("/{item_id}/entries/{entry_id}", response_model=ReadNamedPlanEntry)
    def update_entry(self, item_id: UUID4, entry_id: UUID4, data: CreateNamedPlanEntry):
        updated = self.repos.named_meal_plans.update_entry(item_id, entry_id, data)
        if updated is None:
            raise HTTPException(status_code=404, detail=ErrorResponse.respond("Entry not found"))
        return updated

    @router.delete("/{item_id}/entries/{entry_id}", status_code=204)
    def remove_entry(self, item_id: UUID4, entry_id: UUID4):
        deleted = self.repos.named_meal_plans.delete_entry(item_id, entry_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=ErrorResponse.respond("Entry not found"))

    @router.post("/{item_id}/random", response_model=ReadNamedPlanEntry, status_code=201)
    def add_random_entry(self, item_id: UUID4, data: AddRandomNamedPlanEntry):
        """Pick a random recipe (following household meal-plan rules) and add it to the named plan."""
        plan = self.repos.named_meal_plans.get_one(item_id)
        if plan is None:
            raise HTTPException(status_code=404, detail=ErrorResponse.respond("Plan not found"))

        entry_type = PlanEntryType(data.entry_type) if data.entry_type else PlanEntryType.dinner
        today = datetime.now(UTC).date()
        rules = self.repos.group_meal_plan_rules.get_rules(PlanRulesDay.from_date(today), entry_type.value)
        cross_household_recipes = get_repositories(
            self.session, group_id=self.group_id, household_id=None
        ).recipes.by_user(self.user.id)

        qf_string = " AND ".join([f"({rule.query_filter_string})" for rule in rules if rule.query_filter_string])
        recipes_data = cross_household_recipes.page_all(
            pagination=PaginationQuery(
                page=1,
                per_page=1,
                query_filter=qf_string,
                order_by="random",
                pagination_seed=self.repo._random_seed(),
            )
        )
        if not recipes_data.items:
            raise HTTPException(
                status_code=404, detail=ErrorResponse.respond(self.t("mealplan.no-recipes-match-your-rules"))
            )

        recipe = recipes_data.items[0]
        save = SaveNamedPlanEntry(
            plan_id=item_id,
            recipe_id=recipe.id,
            entry_type=entry_type,
            title="",
            text="",
            recipe_scale=1.0,
        )
        return self.repos.named_meal_plans.add_entry(save)

    # ================================================================
    # Apply to week

    @router.post("/{item_id}/apply", response_model=list[ReadPlanEntry], status_code=201)
    def apply_to_week(self, item_id: UUID4, data: ApplyNamedPlanPayload):
        """
        Copy all entries in the named plan to consecutive dates starting at start_date,
        creating standard dated meal plan entries. The original plan is preserved.
        """
        entries = self.repos.named_meal_plans.get_entries(item_id)
        if not entries:
            raise HTTPException(status_code=400, detail=ErrorResponse.respond("Plan has no entries"))

        created: list[ReadPlanEntry] = []
        for i, entry in enumerate(entries):
            new_date = data.start_date + timedelta(days=i)
            new_entry = self.repos.meals.create(
                SavePlanEntry(
                    date=new_date,
                    entry_type=entry.entry_type or PlanEntryType.dinner,
                    title=entry.title or "",
                    text=entry.text or "",
                    recipe_id=entry.recipe_id,
                    recipe_scale=entry.recipe_scale,
                    group_id=self.group_id,
                    user_id=self.user.id,
                )
            )
            created.append(new_entry)
        return created
