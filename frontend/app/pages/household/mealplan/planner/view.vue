<template>
  <v-container class="mx-0 pa-0">
    <GroupMealPlanEntryDialog
      v-model="dialog.open"
      :entry="dialog.entry"
      :date="dialog.date"
      @create="actions.createOne($event)"
      @update="actions.updateOne($event)"
    />
    <!-- Custom plan mode: single column grouped by entry type -->
    <template v-if="viewMode === 'named-plan'">
      <v-alert
        v-if="!namedPlanId || !namedPlanEntries?.length"
        type="info"
        variant="tonal"
        class="my-3"
      >
        {{ namedPlanId ? $t('meal-plan.custom-plan-no-entries') : $t('meal-plan.custom-plan-select-prompt') }}
      </v-alert>
      <v-row v-else>
        <v-col
          cols="12"
          md="12"
          lg="6"
          xl="4"
          class="col-borders my-1 d-flex flex-column"
        >
          <v-card border="primary s-lg opacity-100" class="rounded-sm px-2">
            <v-container class="px-0 d-flex align-center" height="56px">
              <p class="pl-2">
                {{ $t('meal-plan.custom-plan') }}
              </p>
            </v-container>
          </v-card>
          <v-card variant="flat" class="pl-4 pr-2">
            <div v-for="section in namedPlanSections" :key="section.title">
              <div class="py-2 d-flex flex-column">
                <p class="text-overline my-0">
                  {{ section.title }}
                </p>
              </div>
              <div
                v-for="entry in section.meals"
                :key="entry.id"
                class="mb-2"
              >
                <RecipeCardMobile
                  :recipe-id="entry.recipe ? entry.recipe.id! : ''"
                  :rating="entry.recipe ? entry.recipe.rating! : 0"
                  :slug="entry.recipe ? entry.recipe.slug! : entry.title!"
                  :description="entry.recipe ? entry.recipe.description! : entry.text!"
                  :name="entry.recipe ? entry.recipe.name! : entry.title!"
                  :image="entry.recipe ? entry.recipe.image! : undefined"
                  :tags="entry.recipe ? (entry.recipe.tags ?? []) : []"
                  :scale="entry.recipeScale ?? 1"
                  :named-plan-entry-id="entry.id"
                  :named-plan-id="namedPlanId ?? undefined"
                />
                <div
                  v-if="entry.recipe && onNamedEntryScale"
                  class="d-flex justify-center pt-1 pb-2"
                >
                  <NamedPlanScaleControl
                    :entry="entry"
                    :on-scale-change="(scale: number) => onNamedEntryScale!(entry.id, scale)"
                  />
                </div>
              </div>
            </div>
          </v-card>
        </v-col>
      </v-row>
    </template>

    <!-- Date mode -->
    <MealPlanLayout v-else :mealplans="mealplans">
      <template #default="{ day }">
        <MealPlanDay :day="day.date" :actions="actions" :recipes="day.recipes">
          <SpinTransition>
            <v-card v-if="day.sections.length" variant="flat" class="pl-4 pr-2">
              <SpinTransition>
                <div v-for="section in day.sections" :key="section.title">
                  <div class="py-2 d-flex flex-column">
                    <p class="text-overline my-0">
                      {{ section.title }}
                    </p>
                  </div>
                  <SpinTransition>
                    <div
                      v-for="mealplan in section.meals"
                      :key="mealplan.id"
                      class="mb-2"
                    >
                      <RecipeCardMobile
                        :recipe-id="mealplan.recipe ? mealplan.recipe.id! : ''"
                        :rating="mealplan.recipe ? mealplan.recipe.rating! : 0"
                        :slug="mealplan.recipe ? mealplan.recipe.slug! : mealplan.title!"
                        :description="mealplan.recipe ? mealplan.recipe.description! : mealplan.text!"
                        :name="mealplan.recipe ? mealplan.recipe.name! : mealplan.title!"
                        :image="mealplan.recipe ? mealplan.recipe.image! : undefined"
                        :tags="mealplan.recipe ? (mealplan.recipe.tags ?? []) : []"
                        :scale="mealplan.recipeScale ?? 1"
                        :meal-plan-id="mealplan.id"
                        :context-menu-leading-items="[
                          {
                            title: $t('meal-plan.remove-from-plan'),
                            icon: $globals.icons.calendarRemove,
                            color: undefined,
                            event: 'mealplanRemove',
                            isPublic: false,
                          },
                          {
                            title: $t('meal-plan.edit-meal-plan'),
                            icon: $globals.icons.calendarEdit,
                            color: undefined,
                            event: 'mealplanEdit',
                            isPublic: false,
                          },
                        ]"
                        @mealplan-remove="actions.deleteOne(mealplan.id)"
                        @mealplan-edit="editMeal(mealplan)"
                      >
                        <template v-if="!mealplan.recipe" #context-menu>
                          <MealPlanNoteMenu
                            @mealplan-remove="actions.deleteOne(mealplan.id)"
                            @mealplan-edit="editMeal(mealplan)"
                          />
                        </template>
                      </RecipeCardMobile>
                      <div
                        v-if="mealplan.recipe"
                        class="d-flex justify-center pt-1 pb-2"
                      >
                        <MealPlanScaleControl :meal="mealplan" :actions="actions" />
                      </div>
                    </div>
                  </SpinTransition>
                </div>
              </SpinTransition>
            </v-card>
          </SpinTransition>
        </MealPlanDay>
      </template>
    </MealPlanLayout>
  </v-container>
</template>

<script setup lang="ts">
import MealPlanScaleControl from "~/components/Domain/Household/MealPlanScaleControl.vue";
import NamedPlanScaleControl from "~/components/Domain/Household/NamedPlanScaleControl.vue";
import MealPlanNoteMenu from "~/components/Domain/Mealplan/MealPlanNoteMenu.vue";
import RecipeCardMobile from "~/components/Domain/Recipe/RecipeCardMobile.vue";
import type { MealsByDate } from "~/composables/use-group-mealplan";
import type { ReadNamedPlanEntry, ReadPlanEntry } from "~/lib/api/types/meal-plan";

const props = defineProps<{
  mealplans: MealsByDate[];
  actions: ReturnType<typeof useMealplans>["actions"];
  viewMode?: string;
  namedPlanEntries?: ReadNamedPlanEntry[];
  namedPlanId?: string | null;
  onNamedEntryScale?: (entryId: string, scale: number) => void;
}>();

const planTypeOptions = usePlanTypeOptions();

// Named plan entries grouped by entry type; entries without a type fall under dinner
const namedPlanSections = computed(() => {
  const entries = props.namedPlanEntries ?? [];
  return planTypeOptions
    .map(({ text, value }) => ({
      title: text,
      meals: entries.filter(({ entryType }) => (entryType ?? "dinner") === value),
    }))
    .filter(({ meals }) => meals.length > 0);
});

const dialog = reactive({
  open: false,
  entry: null as ReadPlanEntry | null,
  date: null as Date | null,
});

function editMeal(mealplan: ReadPlanEntry) {
  if (!mealplan.entryType) return;

  dialog.entry = mealplan;
  dialog.date = null;
  dialog.open = true;
}
</script>

<style scoped>
/*
  RecipeCardMobile lays out a fixed-width thumbnail + a favorite/rating/menu action row
  side-by-side. Below ~320px the action row no longer fits and the "..." menu button gets
  clipped by the card's overflow:hidden. Enforcing a min-width here makes the day columns
  wrap to fewer per row instead of shrinking past that point.
*/
.col-borders {
  min-width: 340px;
}
</style>
