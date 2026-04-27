from uuid import UUID

from sqlalchemy import select

from mealie.db.models.household.mealplan import GroupMealPlanNamedPlan, GroupMealPlanNamedPlanEntry
from mealie.repos.repository_generic import GroupRepositoryGeneric
from mealie.schema.meal_plan.plan_named import (
    CreateNamedPlanEntry,
    ReadNamedMealPlan,
    ReadNamedMealPlanWithEntries,
    ReadNamedPlanEntry,
    SaveNamedPlanEntry,
)

PK = "id"


class RepositoryNamedMealPlans(GroupRepositoryGeneric[ReadNamedMealPlan, GroupMealPlanNamedPlan]):
    def get_with_entries(self, plan_id: UUID) -> ReadNamedMealPlanWithEntries | None:
        stmt = select(GroupMealPlanNamedPlan).where(
            GroupMealPlanNamedPlan.id == plan_id,
            GroupMealPlanNamedPlan.group_id == self.group_id,
        )
        for opt in ReadNamedMealPlanWithEntries.loader_options():
            stmt = stmt.options(opt)

        result = self.session.execute(stmt).scalars().first()
        if result is None:
            return None
        return ReadNamedMealPlanWithEntries.model_validate(result)

    def get_entries(self, plan_id: UUID) -> list[ReadNamedPlanEntry]:
        stmt = (
            select(GroupMealPlanNamedPlanEntry)
            .where(GroupMealPlanNamedPlanEntry.plan_id == plan_id)
            .order_by(GroupMealPlanNamedPlanEntry.created_at)
        )
        for opt in ReadNamedPlanEntry.loader_options():
            stmt = stmt.options(opt)

        results = self.session.execute(stmt).scalars().all()
        return [ReadNamedPlanEntry.model_validate(r) for r in results]

    def add_entry(self, data: SaveNamedPlanEntry) -> ReadNamedPlanEntry:
        entry = GroupMealPlanNamedPlanEntry(
            session=self.session,
            plan_id=data.plan_id,
            recipe_id=data.recipe_id,
            entry_type=data.entry_type,
            title=data.title,
            text=data.text,
        )
        self.session.add(entry)
        self.session.commit()
        self.session.refresh(entry)

        stmt = select(GroupMealPlanNamedPlanEntry).where(GroupMealPlanNamedPlanEntry.id == entry.id)
        for opt in ReadNamedPlanEntry.loader_options():
            stmt = stmt.options(opt)

        result = self.session.execute(stmt).scalars().first()
        return ReadNamedPlanEntry.model_validate(result)

    def get_entry(self, plan_id: UUID, entry_id: UUID) -> ReadNamedPlanEntry | None:
        stmt = select(GroupMealPlanNamedPlanEntry).where(
            GroupMealPlanNamedPlanEntry.id == entry_id,
            GroupMealPlanNamedPlanEntry.plan_id == plan_id,
        )
        for opt in ReadNamedPlanEntry.loader_options():
            stmt = stmt.options(opt)
        result = self.session.execute(stmt).scalars().first()
        if result is None:
            return None
        return ReadNamedPlanEntry.model_validate(result)

    def update_entry(self, plan_id: UUID, entry_id: UUID, data: CreateNamedPlanEntry) -> ReadNamedPlanEntry | None:
        stmt = select(GroupMealPlanNamedPlanEntry).where(
            GroupMealPlanNamedPlanEntry.id == entry_id,
            GroupMealPlanNamedPlanEntry.plan_id == plan_id,
        )
        entry = self.session.execute(stmt).scalars().first()
        if entry is None:
            return None

        entry.recipe_id = data.recipe_id
        entry.entry_type = data.entry_type
        entry.title = data.title
        entry.text = data.text
        entry.recipe_scale = data.recipe_scale
        self.session.commit()
        self.session.refresh(entry)

        stmt = select(GroupMealPlanNamedPlanEntry).where(GroupMealPlanNamedPlanEntry.id == entry.id)
        for opt in ReadNamedPlanEntry.loader_options():
            stmt = stmt.options(opt)

        result = self.session.execute(stmt).scalars().first()
        return ReadNamedPlanEntry.model_validate(result)

    def delete_entry(self, plan_id: UUID, entry_id: UUID) -> bool:
        stmt = select(GroupMealPlanNamedPlanEntry).where(
            GroupMealPlanNamedPlanEntry.id == entry_id,
            GroupMealPlanNamedPlanEntry.plan_id == plan_id,
        )
        entry = self.session.execute(stmt).scalars().first()
        if entry is None:
            return False
        self.session.delete(entry)
        self.session.commit()
        return True
