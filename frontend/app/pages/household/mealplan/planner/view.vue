<template>
  <div class="my-3">
    <!-- Custom plan mode: single column -->
    <template v-if="viewMode === 'named-plan'">
      <v-alert
        v-if="!namedPlanEntries || namedPlanEntries.length === 0"
        type="info"
        variant="tonal"
        class="mb-4"
      >
        {{ namedPlanEntries !== undefined ? $t('meal-plan.custom-plan-no-entries') : $t('meal-plan.custom-plan-select-prompt') }}
      </v-alert>
      <v-row v-else>
        <v-col
          cols="12"
          sm="12"
          md="6"
          lg="4"
          xl="3"
          xxl="2"
          class="col-borders my-1 d-flex flex-column"
        >
          <v-card class="mb-2 border-left-primary rounded-sm px-2">
            <v-container class="px-0 d-flex align-center" height="56px">
              <p class="pl-2 my-1">
                Custom Plan
              </p>
            </v-container>
          </v-card>
          <div v-for="section in namedPlanSections" :key="section.title">
            <div class="py-2 d-flex flex-column">
              <div class="primary" style="width: 50px; height: 2.5px" />
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
                :tags="entry.recipe ? (entry.recipe.tags ?? []) : []"
                :scale="entry.recipeScale ?? 1"
                :named-plan-entry-id="entry.id"
                :named-plan-id="props.namedPlanId ?? undefined"
              />
              <div
                v-if="entry.recipe && props.onNamedEntryScale"
                class="d-flex justify-center pt-1 pb-2"
              >
                <NamedPlanScaleControl
                  :entry="entry"
                  :on-scale-change="(scale: number) => props.onNamedEntryScale!(entry.id, scale)"
                />
              </div>
            </div>
          </div>
        </v-col>
      </v-row>
    </template>

    <!-- Date mode: existing per-day columns -->
    <v-row v-else>
      <v-col
        v-for="(day, index) in plan"
        :key="index"
        cols="12"
        sm="12"
        md="6"
        lg="4"
        xl="3"
        xxl="2"
        class="col-borders my-1 d-flex flex-column"
      >
        <v-card class="mb-2 border-left-primary rounded-sm px-2">
          <v-container class="px-0 d-flex align-center" height="56px">
            <v-row no-gutters style="width: 100%;">
              <v-col cols="10" class="d-flex align-center">
                <p class="pl-2 my-1" :class="{ 'text-primary': isToday(day.date) }">
                  {{ $d(day.date, "short") }}
                </p>
              </v-col>
              <v-col class="d-flex align-center" cols="2">
                <GroupMealPlanDayContextMenu v-if="day.recipes.length" :recipes="day.recipes" />
              </v-col>
            </v-row>
          </v-container>
        </v-card>
        <div v-for="section in day.sections" :key="section.title">
          <div class="py-2 d-flex flex-column">
            <div class="primary" style="width: 50px; height: 2.5px" />
            <p class="text-overline my-0">
              {{ section.title }}
            </p>
          </div>

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
              :tags="mealplan.recipe ? (mealplan.recipe.tags ?? []) : []"
              :scale="mealplan.recipeScale ?? 1"
              :meal-plan-id="mealplan.id"
            />
            <div
              v-if="mealplan.recipe"
              class="d-flex justify-center pt-1 pb-2"
            >
              <MealPlanScaleControl :meal="mealplan" :actions="props.actions" />
            </div>
          </div>
        </div>
      </v-col>
    </v-row>
  </div>
</template>

<script setup lang="ts">
import { isSameDay } from "date-fns";

import type { ReadNamedPlanEntry, ReadPlanEntry } from "~/lib/api/types/meal-plan";
import GroupMealPlanDayContextMenu from "~/components/Domain/Household/GroupMealPlanDayContextMenu.vue";
import MealPlanScaleControl from "~/components/Domain/Household/MealPlanScaleControl.vue";
import NamedPlanScaleControl from "~/components/Domain/Household/NamedPlanScaleControl.vue";
import RecipeCardMobile from "~/components/Domain/Recipe/RecipeCardMobile.vue";
import type { useMealplans } from "~/composables/use-group-mealplan";

export type MealsByDate = {
  date: Date;
  meals: ReadPlanEntry[];
};

const props = defineProps<{
  mealplans: MealsByDate[];
  actions: ReturnType<typeof useMealplans>["actions"];
  viewMode?: string;
  namedPlanEntries?: ReadNamedPlanEntry[];
  namedPlanId?: string | null;
  onNamedEntryScale?: (entryId: string, scale: number) => void;
}>();

type DaySection = {
  title: string;
  meals: ReadPlanEntry[];
};

type NamedPlanSection = {
  title: string;
  meals: ReadNamedPlanEntry[];
};

type Days = {
  date: Date;
  sections: DaySection[];
  recipes: ReadPlanEntry[];
};

const i18n = useI18n();

// Named plan sections: group entries by entry type
const namedPlanSections = computed<NamedPlanSection[]>(() => {
  const entries = props.namedPlanEntries ?? [];
  const sections: NamedPlanSection[] = [
    { title: i18n.t("meal-plan.breakfast"), meals: [] },
    { title: i18n.t("meal-plan.lunch"), meals: [] },
    { title: i18n.t("meal-plan.dinner"), meals: [] },
    { title: i18n.t("meal-plan.side"), meals: [] },
    { title: i18n.t("meal-plan.snack"), meals: [] },
    { title: i18n.t("meal-plan.drink"), meals: [] },
    { title: i18n.t("meal-plan.dessert"), meals: [] },
  ];
  for (const entry of entries) {
    if (entry.entryType === "breakfast") sections[0].meals.push(entry);
    else if (entry.entryType === "lunch") sections[1].meals.push(entry);
    else if (entry.entryType === "dinner") sections[2].meals.push(entry);
    else if (entry.entryType === "side") sections[3].meals.push(entry);
    else if (entry.entryType === "snack") sections[4].meals.push(entry);
    else if (entry.entryType === "drink") sections[5].meals.push(entry);
    else if (entry.entryType === "dessert") sections[6].meals.push(entry);
    else sections[2].meals.push(entry);
  }
  return sections.filter(s => s.meals.length > 0);
});

const plan = computed<Days[]>(() => {
  return props.mealplans.reduce((acc, day) => {
    const out: Days = {
      date: day.date,
      sections: [
        { title: i18n.t("meal-plan.breakfast"), meals: [] },
        { title: i18n.t("meal-plan.lunch"), meals: [] },
        { title: i18n.t("meal-plan.dinner"), meals: [] },
        { title: i18n.t("meal-plan.side"), meals: [] },
        { title: i18n.t("meal-plan.snack"), meals: [] },
        { title: i18n.t("meal-plan.drink"), meals: [] },
        { title: i18n.t("meal-plan.dessert"), meals: [] },
      ],
      recipes: [],
    };

    for (const meal of day.meals) {
      if (meal.entryType === "breakfast") {
        out.sections[0].meals.push(meal);
      }
      else if (meal.entryType === "lunch") {
        out.sections[1].meals.push(meal);
      }
      else if (meal.entryType === "dinner") {
        out.sections[2].meals.push(meal);
      }
      else if (meal.entryType === "side") {
        out.sections[3].meals.push(meal);
      }
      else if (meal.entryType === "snack") {
        out.sections[4].meals.push(meal);
      }
      else if (meal.entryType === "drink") {
        out.sections[5].meals.push(meal);
      }
      else if (meal.entryType === "dessert") {
        out.sections[6].meals.push(meal);
      }

      if (meal.recipe) {
        out.recipes.push(meal);
      }
    }

    // Drop empty sections
    out.sections = out.sections.filter(section => section.meals.length > 0);

    acc.push(out);

    return acc;
  }, [] as Days[]);
});

const isToday = (date: Date) => {
  return isSameDay(date, new Date());
};
</script>
