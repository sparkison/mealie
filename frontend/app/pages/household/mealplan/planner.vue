<template>
  <v-container>
    <RecipeDialogAddToShoppingList
      v-if="shoppingLists"
      v-model="shoppingListDialog"
      :recipes="viewMode === 'named-plan' ? planEntryRecipesWithScales : weekRecipesWithScales"
      :shopping-lists="shoppingLists"
      @list-created="addShoppingList"
    />
    <GroupMealPlanCalendarDialog v-model="calendarDialog" />

    <!-- New Custom Plan dialog -->
    <BaseDialog
      v-model="newPlanDialog"
      :title="$t('meal-plan.custom-plan-new')"
      :submit-text="$t('general.create')"
      color="primary"
      :icon="$globals.icons.createAlt"
      :submit-disabled="!newPlanName.trim()"
      can-submit
      @submit="onCreatePlan"
      @close="newPlanName = ''"
    >
      <v-card-text>
        <v-text-field
          v-model="newPlanName"
          :label="$t('meal-plan.custom-plan-name-label')"
          autofocus
          @keydown.enter="onCreatePlan"
        />
      </v-card-text>
    </BaseDialog>

    <!-- Move all to Custom Plan dialog -->
    <BaseDialog
      v-model="addToPlanDialog"
      :title="$t('meal-plan.custom-plan-move-all')"
      :submit-text="$t('general.move')"
      color="primary"
      :icon="$globals.icons.tags"
      :submit-disabled="!addToPlanId && !newPlanNameForAdd.trim()"
      :loading="addToPlanLoading"
      can-submit
      @submit="addAllToCustomPlan"
      @close="addToPlanId = null; newPlanNameForAdd = ''"
    >
      <v-card-text>
        <p class="mb-3 text-body-2">
          {{ $t('meal-plan.custom-plan-move-hint') }}
        </p>
        <v-select
          v-model="addToPlanId"
          :items="namedPlans"
          item-title="name"
          item-value="id"
          :label="$t('meal-plan.custom-plan-move-existing-label')"
          clearable
          :disabled="!!newPlanNameForAdd.trim()"
        />
        <div class="d-flex align-center my-2">
          <v-divider />
          <span class="mx-2 text-caption text-medium-emphasis">{{ $t('general.or') }}</span>
          <v-divider />
        </div>
        <v-text-field
          v-model="newPlanNameForAdd"
          :label="$t('meal-plan.custom-plan-move-new-label')"
          :disabled="!!addToPlanId"
        />
      </v-card-text>
    </BaseDialog>

    <!-- Rename Plan dialog -->
    <BaseDialog
      v-model="renamePlanDialog"
      :title="$t('meal-plan.custom-plan-rename')"
      :submit-text="$t('general.save')"
      color="primary"
      :icon="$globals.icons.edit"
      :submit-disabled="!renamePlanName.trim()"
      can-submit
      @submit="onRenamePlan"
      @close="renamePlanName = ''"
    >
      <v-card-text>
        <v-text-field
          v-model="renamePlanName"
          :label="$t('meal-plan.custom-plan-name-label')"
          autofocus
          @keydown.enter="onRenamePlan"
        />
      </v-card-text>
    </BaseDialog>

    <!-- Delete Plan confirmation dialog -->
    <BaseDialog
      v-model="deletePlanDialog"
      :title="$t('meal-plan.custom-plan-delete')"
      color="error"
      :icon="$globals.icons.alertCircle"
      can-confirm
      @confirm="onDeletePlan"
    >
      <v-card-text>
        {{ $t('meal-plan.custom-plan-delete-confirm', { name: namedPlans.find(p => p.id === selectedPlanId)?.name ?? '' }) }}
      </v-card-text>
    </BaseDialog>

    <!-- Apply to Week dialog -->
    <BaseDialog
      v-model="applyDialog"
      :title="$t('meal-plan.custom-plan-apply')"
      :submit-text="$t('meal-plan.custom-plan-apply-btn')"
      color="primary"
      :icon="$globals.icons.calendar"
      can-submit
      @submit="onApplyToWeek"
    >
      <v-card-text>
        <p class="mb-2 text-body-2">
          {{ $t('meal-plan.custom-plan-apply-hint') }}
        </p>
        <MealPlanDatePicker v-model="applyStartDateObj" />
      </v-card-text>
    </BaseDialog>

    <!-- range navigation and page actions share one toolbar, kept apart from the plan below -->
    <div class="d-flex flex-wrap align-center ga-2">
      <!-- Date mode: range navigation -->
      <template v-if="viewMode === 'date'">
        <v-btn :icon="$globals.icons.chevronLeft" flat rounded="md" density="comfortable" @click="() => changeWeek(-1)" />
        <v-menu
          v-model="state.picker"
          :close-on-content-click="false"
          transition="scale-transition"
          offset-y
          min-width="auto"
        >
          <template #activator="{ props }">
            <v-btn
              color="primary"
              v-bind="props"
            >
              <v-icon start>
                {{ $globals.icons.calendar }}
              </v-icon>
              {{ $d(weekRange.start, "short") }} - {{ $d(weekRange.end, "short") }}
            </v-btn>
          </template>

          <v-card>
            <MealPlanDatePicker
              v-model="state.range"
              hide-header
              :multiple="'range'"
              :first-day-of-week="firstDayOfWeek"
              :local="$i18n.locale"
            />

            <v-card-text>
              <v-number-input
                v-model="numberOfWeeksPast"
                :min="0"
                inset
                :label="$t('meal-plan.numberOfWeeksPast-label')"
                :hint="$t('meal-plan.numberOfWeeksPast-hint')"
                persistent-hint
              />
            </v-card-text>

            <v-card-text>
              <v-number-input
                v-model="numberOfWeeks"
                :min="1"
                inset
                :label="$t('meal-plan.numberOfWeeks-label')"
                :hint="$t('meal-plan.numberOfWeeks-hint')"
                persistent-hint
              />
            </v-card-text>
          </v-card>
        </v-menu>
        <v-btn :icon="$globals.icons.chevronRight" flat rounded="md" density="comfortable" @click="() => changeWeek(1)" />
      </template>
      <!-- Custom plan mode: plan selector + actions -->
      <div v-else class="d-flex align-center ga-2 flex-grow-1 flex-sm-grow-0">
        <v-select
          v-model="selectedPlanId"
          :items="namedPlans"
          item-title="name"
          item-value="id"
          :label="$t('meal-plan.custom-plan')"
          clearable
          density="compact"
          hide-details
          class="flex-grow-1"
          style="min-width: 200px; max-width: 400px"
        />
        <v-btn
          icon
          variant="text"
          size="small"
          :title="$t('meal-plan.custom-plan-new')"
          @click="newPlanDialog = true"
        >
          <v-icon>{{ $globals.icons.createAlt }}</v-icon>
        </v-btn>
        <v-btn
          icon
          variant="text"
          size="small"
          :disabled="!selectedPlanId"
          :title="$t('meal-plan.custom-plan-rename')"
          @click="onOpenRenamePlan"
        >
          <v-icon>{{ $globals.icons.edit }}</v-icon>
        </v-btn>
        <v-btn
          icon
          variant="text"
          size="small"
          :disabled="!selectedPlanId"
          :title="$t('meal-plan.custom-plan-delete')"
          @click="deletePlanDialog = true"
        >
          <v-icon>{{ $globals.icons.delete }}</v-icon>
        </v-btn>
      </div>

      <!-- Mode toggle -->
      <v-btn-toggle
        v-model="viewMode"
        mandatory
        density="compact"
      >
        <v-btn value="date" size="small">
          <v-icon start>
            {{ $globals.icons.calendar }}
          </v-icon>
          {{ $t('general.date') }}
        </v-btn>
        <v-btn value="named-plan" size="small">
          <v-icon start>
            {{ $globals.icons.tags }}
          </v-icon>
          {{ $t('meal-plan.custom-plans') }}
        </v-btn>
      </v-btn-toggle>
      <BaseButtonGroup
        class="d-flex ms-auto"
        :buttons="[
          edit ? {
            icon: $globals.icons.calendar,
            text: $t('general.view'),
            event: 'view',
          } : {
            icon: $globals.icons.edit,
            text: $t('general.edit'),
            event: 'edit',
          },
          {
            icon: $globals.icons.dotsVertical,
            text: '',
            event: 'three-dot',
            children: menuItems,
          },
        ]"
        @add-to-list="addAllToList"
        @move-to-plan="addToPlanDialog = true"
        @apply-plan="applyDialog = true"
        @edit="router.push({ name: TABS.edit, query: route.query })"
        @view="router.push({ name: TABS.view, query: route.query })"
        @settings="router.push('/household/mealplan/settings')"
        @calendar-feed="calendarDialog = true"
      />
    </div>
    <v-divider class="my-4" />
    <div>
      <NuxtPage
        :mealplans="viewMode === 'date' ? plans : []"
        :actions="actions"
        :named-plan-entries="viewMode === 'named-plan' ? planEntries : []"
        :named-plan-id="viewMode === 'named-plan' ? selectedPlanId : null"
        :view-mode="viewMode"
        :on-named-entry-scale="(entryId: string, scale: number) => selectedPlanId && updateEntryScale(selectedPlanId, entryId, scale)"
        :named-plan-actions="namedPlanActions"
      />
    </div>

    <v-row />
  </v-container>
</template>

<script setup lang="ts">
import { addDays, addWeeks, differenceInCalendarDays, format, isSameDay, isValid, parseISO } from "date-fns";
import GroupMealPlanCalendarDialog from "~/components/Domain/Household/GroupMealPlanCalendarDialog.vue";
import RecipeDialogAddToShoppingList from "~/components/Domain/Recipe/RecipeDialogAddToShoppingList.vue";
import { useAddToShoppingListDialog } from "~/composables/shopping-list-page/use-add-to-shopping-list-dialog";
import type { MealsByDate } from "~/composables/use-group-mealplan";
import { getScaledRecipes, getWeekRange, useMealplans } from "~/composables/use-group-mealplan";
import { useHouseholdSelf } from "~/composables/use-households";
import { useNamedMealPlans } from "~/composables/use-named-meal-plans";
import { useUserMealPlanPreferences } from "~/composables/use-users/preferences";
import { useUserApi } from "~/composables/api";
import type { CreateNamedPlanEntry } from "~/lib/api/types/meal-plan";

definePageMeta({
  middleware: ["auth"],
});

const TABS = {
  view: "household-mealplan-planner-view",
  edit: "household-mealplan-planner-edit",
};

const route = useRoute();
const router = useRouter();
const i18n = useI18n();
const api = useUserApi();
const { $globals } = useNuxtApp();
const { household, actions: householdActions } = useHouseholdSelf();
const { shoppingLists, open: shoppingListDialog, addAllToList, addShoppingList } = useAddToShoppingListDialog();
const calendarDialog = ref(false);

useSeoMeta({
  title: i18n.t("meal-plan.dinner-this-week"),
});

// useHouseholdSelf() caches data in a module-level singleton for the lifetime of the tab,
// so revisiting this page via client-side navigation can otherwise use a stale
// firstDayOfWeek value if household preferences were changed elsewhere (e.g. Admin
// Households panel) in the same session. Force a revalidation whenever this page is entered.
onMounted(() => {
  householdActions.refresh();
});

const mealPlanPreferences = useUserMealPlanPreferences();
const numberOfWeeksPast = ref<number>(mealPlanPreferences.value.numberOfWeeksPast || 0);
const numberOfWeeks = ref<number>(mealPlanPreferences.value.numberOfWeeks || 1);
watch(numberOfWeeksPast, (val) => {
  mealPlanPreferences.value.numberOfWeeksPast = Number(val);
});
watch(numberOfWeeks, (val) => {
  mealPlanPreferences.value.numberOfWeeks = Number(val);
});

// Force to /view if current route is /planner
if (route.path === "/household/mealplan/planner") {
  router.push({
    name: TABS.view,
    query: route.query,
  });
}

const edit = computed(() => {
  return route.path.startsWith("/household/mealplan/planner/edit");
});

function safeParseISO(date: string, fallback: Date | undefined = undefined) {
  try {
    const parsed = parseISO(date);
    return isValid(parsed) ? parsed : fallback;
  }
  catch {
    return fallback;
  }
}

// A day in the first and last week of the default range; `weekRange` rounds them out to whole weeks
function defaultStartDate() {
  return addWeeks(new Date(), -numberOfWeeksPast.value);
}

function defaultEndDate() {
  return addWeeks(new Date(), numberOfWeeks.value - 1);
}

// Initialize dates from query parameters or defaults
const initialStartDate = safeParseISO(route.query.start as string, defaultStartDate());
const initialEndDate = safeParseISO(route.query.end as string, defaultEndDate());

const state = ref({
  range: [initialStartDate, initialEndDate] as [Date, Date],
  start: initialStartDate,
  picker: false,
  end: initialEndDate,
});

const firstDayOfWeek = computed(() => {
  return household.value?.preferences?.firstDayOfWeek || 0;
});

function changeWeek(step: number) {
  const { start, end } = weekRange.value;
  const stepSize = differenceInCalendarDays(end, start) + 1;
  state.value.range = [
    addDays(start, step * stepSize),
    addDays(end, step * stepSize),
  ];
}

// The planner always shows whole weeks, so the selected range is rounded out to the weeks it touches
const weekRange = computed(() => {
  const sorted = [...state.value.range].sort((a, b) => a.getTime() - b.getTime());

  const start = sorted[0] ?? defaultStartDate();
  const end = sorted[sorted.length - 1] ?? defaultEndDate();

  return {
    start: getWeekRange(start, firstDayOfWeek.value).start,
    end: getWeekRange(end, firstDayOfWeek.value).end,
  };
});

// Once a range is fully picked, show the whole weeks in the picker too. A half-picked range (one date)
// is left alone, so the picker can still take the second click.
watch(weekRange, ({ start, end }) => {
  const [first, last] = state.value.range;
  if (state.value.range.length === 2 && !(first && last && isSameDay(first, start) && isSameDay(last, end))) {
    state.value.range = [start, end];
  }
});

// Update query parameters when date range changes
watch(weekRange, (newRange) => {
  // Keep current route name and params, just update the query
  router.replace({
    name: route.name || TABS.view,
    params: route.params,
    query: {
      ...route.query,
      start: format(newRange.start, "yyyy-MM-dd"),
      end: format(newRange.end, "yyyy-MM-dd"),
    },
  });
}, { immediate: true });

const { mealplans, actions } = useMealplans(weekRange);

function filterMealByDate(date: Date) {
  if (!mealplans.value) return [];
  return mealplans.value.filter((meal) => {
    // week entries aren't planned for a specific day
    if (meal.endDate) return false;

    const mealDate = parseISO(meal.date);
    return isSameDay(mealDate, date);
  });
}

const days = computed(() => {
  const numDays
    = Math.floor((weekRange.value.end.getTime() - weekRange.value.start.getTime()) / (1000 * 60 * 60 * 24)) + 1;

  // Calculate absolute value
  if (numDays < 0) return [];

  return Array.from(Array(numDays).keys()).map(
    (i) => {
      const date = new Date(weekRange.value.start.getTime());
      date.setDate(date.getDate() + i);
      return date;
    },
  );
});

const mealsByDate = computed(() => {
  return days.value.map((day) => {
    return { date: day, meals: filterMealByDate(day) };
  });
});

/**
 * The visible days grouped by week, each with that week's entries, so meals can be planned for any visible week.
 * Week entries are grouped by their own dates rather than the current weeks, so they still show up (as a week
 * without days) if the household's first day of the week has changed since they were planned.
 */
const mealsByWeek = computed(() => {
  const weeks = new Map<string, { week: MealsByDate; days: MealsByDate[] }>();
  const getWeek = (start: Date, end: Date) => {
    const key = format(start, "yyyy-MM-dd");
    if (!weeks.has(key)) {
      weeks.set(key, { week: { date: start, endDate: end, meals: [] }, days: [] });
    }
    return weeks.get(key)!;
  };

  for (const day of mealsByDate.value) {
    const { start, end } = getWeekRange(day.date, firstDayOfWeek.value);
    getWeek(start, end).days.push(day);
  }

  for (const meal of mealplans.value ?? []) {
    if (meal.endDate) {
      getWeek(parseISO(meal.date), parseISO(meal.endDate)).week.meals.push(meal);
    }
  }

  return [...weeks.values()].sort((a, b) => a.week.date.getTime() - b.week.date.getTime());
});

/** Each week followed by its days, the order the planner pages lay them out in */
const plans = computed(() => mealsByWeek.value.flatMap(({ week, days }) => [week, ...days]));

const allMeals = computed(() => plans.value.flatMap(({ meals }) => meals));

const hasRecipes = computed(() => {
  return allMeals.value.some(meal => meal.recipe);
});

const weekRecipesWithScales = computed(() => {
  return getScaledRecipes(allMeals.value);
});

const hasMeals = computed(() => allMeals.value.length > 0);

// ================================================================
// Named plan mode

const viewMode = ref<"date" | "named-plan">(
  route.query.mode === "named-plan" ? "named-plan" : "date",
);
const selectedPlanId = ref<string | null>(
  (route.query.plan as string) || null,
);
const newPlanDialog = ref(false);
const newPlanName = ref("");
const renamePlanDialog = ref(false);
const renamePlanName = ref("");
const deletePlanDialog = ref(false);
const applyDialog = ref(false);
const applyStartDateObj = ref<Date>(new Date());

const { plans: namedPlans, planEntries, fetchAll, fetchEntries, createOne: createPlan, deleteOne: deletePlan, applyToWeek, updateEntryScale } = useNamedMealPlans();

const hasPlanEntryRecipes = computed(() => {
  return planEntries.value.some(entry => entry.recipe);
});

const planEntryRecipesWithScales = computed(() => {
  return planEntries.value
    .filter(({ recipe }) => recipe)
    .map(({ recipe, recipeScale }) => ({ ...recipe!, scale: recipeScale ?? 1 }));
});

const menuItems = computed(() => {
  const calendarFeed = {
    icon: $globals.icons.calendar,
    text: i18n.t("meal-plan.calendar-feed"),
    event: "calendar-feed",
  };
  const settings = {
    icon: $globals.icons.cog,
    text: i18n.t("general.settings"),
    event: "settings",
  };

  if (viewMode.value === "named-plan") {
    return [
      {
        icon: $globals.icons.cartCheck,
        text: i18n.t("meal-plan.add-all-to-list"),
        event: "add-to-list",
        disabled: !hasPlanEntryRecipes.value,
      },
      {
        icon: $globals.icons.calendar,
        text: i18n.t("meal-plan.custom-plan-apply-btn"),
        event: "apply-plan",
        disabled: !selectedPlanId.value || planEntries.value.length === 0,
      },
      calendarFeed,
      settings,
    ];
  }

  return [
    {
      icon: $globals.icons.cartCheck,
      text: i18n.t("meal-plan.add-all-to-list"),
      event: "add-to-list",
      disabled: !hasRecipes.value,
    },
    {
      icon: $globals.icons.tags,
      text: i18n.t("meal-plan.custom-plan-move-all"),
      event: "move-to-plan",
      disabled: !hasMeals.value,
    },
    calendarFeed,
    settings,
  ];
});

// Sync viewMode + selectedPlanId into URL
watch([viewMode, selectedPlanId], ([mode, planId]) => {
  router.replace({
    name: route.name || TABS.view,
    params: route.params,
    query: {
      ...route.query,
      mode: mode === "named-plan" ? "named-plan" : undefined,
      plan: mode === "named-plan" && planId ? planId : undefined,
    },
  });
});

watch(selectedPlanId, async (id) => {
  if (id) await fetchEntries(id);
  else planEntries.value = [];
}, { immediate: true });

// Auto-select the only plan when in named-plan mode with exactly one option
watch([() => viewMode.value, namedPlans], ([mode]) => {
  if (mode === "named-plan" && !selectedPlanId.value && namedPlans.value.length === 1) {
    selectedPlanId.value = namedPlans.value[0]!.id;
  }
});

async function onCreatePlan() {
  if (!newPlanName.value.trim()) return;
  const plan = await createPlan(newPlanName.value.trim());
  if (plan) selectedPlanId.value = plan.id;
  newPlanName.value = "";
  newPlanDialog.value = false;
}

function onOpenRenamePlan() {
  const current = namedPlans.value.find(p => p.id === selectedPlanId.value);
  renamePlanName.value = current?.name ?? "";
  renamePlanDialog.value = true;
}

async function onRenamePlan() {
  if (!selectedPlanId.value || !renamePlanName.value.trim()) return;
  await api.namedMealPlans.updateOne(selectedPlanId.value, { name: renamePlanName.value.trim() });
  await fetchAll();
  renamePlanDialog.value = false;
  renamePlanName.value = "";
}

async function onDeletePlan() {
  if (!selectedPlanId.value) return;
  await deletePlan(selectedPlanId.value);
  selectedPlanId.value = null;
  deletePlanDialog.value = false;
}

const namedPlanActions = {
  async addEntry(data: CreateNamedPlanEntry) {
    if (!selectedPlanId.value) return;
    await api.namedMealPlans.addEntry(selectedPlanId.value, data);
    await fetchEntries(selectedPlanId.value);
  },
  async updateEntry(entryId: string, data: CreateNamedPlanEntry) {
    if (!selectedPlanId.value) return;
    await api.namedMealPlans.updateEntry(selectedPlanId.value, entryId, data);
    await fetchEntries(selectedPlanId.value);
  },
  async deleteEntry(entryId: string) {
    if (!selectedPlanId.value) return;
    await api.namedMealPlans.removeEntry(selectedPlanId.value, entryId);
    await fetchEntries(selectedPlanId.value);
  },
  async addRandomEntry(entryType: string) {
    if (!selectedPlanId.value) return;
    await api.namedMealPlans.addRandomEntry(selectedPlanId.value, entryType);
    await fetchEntries(selectedPlanId.value);
  },
};

async function onApplyToWeek() {
  if (!selectedPlanId.value) return;
  const startDate = format(applyStartDateObj.value, "yyyy-MM-dd");
  await applyToWeek(selectedPlanId.value, startDate);
  applyDialog.value = false;
  // Switch to date view showing the newly populated week
  viewMode.value = "date";
  const start = applyStartDateObj.value;
  const end = addDays(start, Math.max(planEntries.value.length - 1, 0));
  state.value.range = [start, end];
}

// Add all current week's meals to a named plan
const addToPlanDialog = ref(false);
const addToPlanId = ref<string | null>(null);
const addToPlanLoading = ref(false);
const newPlanNameForAdd = ref("");

async function addAllToCustomPlan() {
  addToPlanLoading.value = true;
  let targetPlanId = addToPlanId.value;

  if (newPlanNameForAdd.value.trim()) {
    const plan = await createPlan(newPlanNameForAdd.value.trim());
    if (plan) targetPlanId = plan.id;
  }

  if (!targetPlanId) {
    addToPlanLoading.value = false;
    return;
  }

  const mealsToMove = allMeals.value;
  for (const meal of mealsToMove) {
    await api.namedMealPlans.addEntry(targetPlanId, {
      recipeId: meal.recipeId || meal.recipe?.id || null,
      entryType: meal.entryType,
      title: meal.title || "",
      text: meal.text || "",
      recipeScale: meal.recipeScale ?? 1,
    });
  }

  // Move: remove from calendar after copying to the plan
  for (const meal of mealsToMove) {
    await api.mealplans.deleteOne(meal.id);
  }
  await actions.refreshAll();

  addToPlanLoading.value = false;
  addToPlanDialog.value = false;
  addToPlanId.value = null;
  newPlanNameForAdd.value = "";

  // Auto-navigate to the newly populated plan
  selectedPlanId.value = targetPlanId;
  viewMode.value = "named-plan";
  await fetchEntries(targetPlanId);
}
</script>
