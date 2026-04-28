<template>
  <v-container>
    <RecipeDialogAddToShoppingList
      v-if="shoppingLists"
      v-model="state.shoppingListDialog"
      :recipes="weekRecipesWithScales"
      :shopping-lists="shoppingLists"
    />

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
          :items="plans"
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
        {{ $t('meal-plan.custom-plan-delete-confirm', { name: plans.find(p => p.id === selectedPlanId)?.name ?? '' }) }}
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
        <v-date-picker
          v-model="applyStartDateObj"
          hide-header
          show-adjacent-months
          color="primary"
          class="mx-auto"
        />
      </v-card-text>
    </BaseDialog>

    <!-- Header row: date picker (date mode) / plan controls (custom plan mode) + mode toggle -->
    <div class="d-flex flex-wrap align-center gap-2 mb-2">
      <!-- Date mode: date range picker -->
      <v-menu
        v-if="viewMode === 'date'"
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
          <v-date-picker
            v-model="state.range"
            hide-header
            :multiple="'range'"
            :first-day-of-week="firstDayOfWeek"
            :local="$i18n.locale"
          />

          <v-card-text>
            <v-number-input
              v-model="numberOfDaysPast"
              :min="0"
              control-variant="stacked"
              inset
              :label="$t('meal-plan.numberOfDaysPast-label')"
              :hint="$t('meal-plan.numberOfDaysPast-hint')"
              persistent-hint
            />
          </v-card-text>

          <v-card-text>
            <v-number-input
              v-model="numberOfDays"
              :min="1"
              control-variant="stacked"
              inset
              :label="$t('meal-plan.numberOfDays-label')"
              :hint="$t('meal-plan.numberOfDays-hint')"
              persistent-hint
            />
          </v-card-text>
        </v-card>
      </v-menu>

      <!-- Custom plan mode: plan selector + actions -->
      <template v-if="viewMode === 'named-plan'">
        <v-select
          v-model="selectedPlanId"
          :items="plans"
          item-title="name"
          item-value="id"
          :label="$t('meal-plan.custom-plan')"
          clearable
          density="compact"
          hide-details
          style="max-width: 300px"
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
      </template>

      <!-- Mode toggle (always at right) -->
      <v-btn-toggle
        v-model="viewMode"
        mandatory
        density="compact"
        class="ml-auto"
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
    </div>

    <!-- Tabs + action buttons -->
    <div class="d-flex flex-wrap align-center justify-space-between mb-2">
      <v-tabs style="width: fit-content;">
        <v-tab :to="{ name: TABS.view, query: route.query }">
          {{ $t('meal-plan.meal-planner') }}
        </v-tab>
        <v-tab :to="{ name: TABS.edit, query: route.query }">
          {{ $t('general.edit') }}
        </v-tab>
      </v-tabs>
      <BaseButton
        v-if="route.name === TABS.view && viewMode === 'date'"
        color="info"
        :icon="$globals.icons.cartCheck"
        :text="$t('meal-plan.add-all-to-list')"
        :disabled="!hasRecipes"
        :loading="state.addAllLoading"
        class="ml-auto mr-4"
        @click="addAllToList"
      />
      <BaseButton
        v-if="route.name === TABS.view && viewMode === 'date'"
        color="primary"
        :icon="$globals.icons.tags"
        :text="$t('meal-plan.custom-plan-move-all')"
        :disabled="!hasMeals"
        class="mr-4"
        @click="addToPlanDialog = true"
      />
      <BaseButton
        v-if="viewMode === 'named-plan'"
        color="primary"
        :icon="$globals.icons.calendar"
        :text="$t('meal-plan.custom-plan-apply-btn')"
        :disabled="!selectedPlanId || planEntries.length === 0"
        class="ml-auto mr-4"
        @click="applyDialog = true"
      />
      <ButtonLink
        :icon="$globals.icons.calendar"
        :to="`/household/mealplan/settings`"
        :text="$t('general.settings')"
      />
    </div>

    <div>
      <NuxtPage
        :mealplans="viewMode === 'date' ? mealsByDate : []"
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
import { isSameDay, addDays, parseISO, format, isValid } from "date-fns";
import RecipeDialogAddToShoppingList from "~/components/Domain/Recipe/RecipeDialogAddToShoppingList.vue";
import { useHouseholdSelf } from "~/composables/use-households";
import { useMealplans } from "~/composables/use-group-mealplan";
import { useNamedMealPlans } from "~/composables/use-named-meal-plans";
import { useUserMealPlanPreferences } from "~/composables/use-users/preferences";
import type { ShoppingListSummary } from "~/lib/api/types/household";
import type { CreateNamedPlanEntry } from "~/lib/api/types/meal-plan";
import { useUserApi } from "~/composables/api";

const TABS = {
  view: "household-mealplan-planner-view",
  edit: "household-mealplan-planner-edit",
};

const route = useRoute();
const router = useRouter();
const i18n = useI18n();
const api = useUserApi();
const { household } = useHouseholdSelf();

useSeoMeta({
  title: i18n.t("meal-plan.dinner-this-week"),
});

const mealPlanPreferences = useUserMealPlanPreferences();
const numberOfDaysPast = ref<number>(mealPlanPreferences.value.numberOfDaysPast || 0);
const numberOfDays = ref<number>(mealPlanPreferences.value.numberOfDays || 7);
watch(numberOfDaysPast, (val) => {
  mealPlanPreferences.value.numberOfDaysPast = Number(val);
});
watch(numberOfDays, (val) => {
  mealPlanPreferences.value.numberOfDays = Number(val);
});

// Force to /view if current route is /planner
if (route.path === "/household/mealplan/planner") {
  router.push({
    name: TABS.view,
    query: route.query,
  });
}

function safeParseISO(date: string, fallback: Date | undefined = undefined) {
  try {
    const parsed = parseISO(date);
    return isValid(parsed) ? parsed : fallback;
  }
  catch {
    return fallback;
  }
}

// Initialize dates from query parameters or defaults
const initialStartDate = safeParseISO(route.query.start as string, addDays(new Date(), adjustForToday(-numberOfDaysPast.value)));
const initialEndDate = safeParseISO(route.query.end as string, addDays(new Date(), adjustForToday(numberOfDays.value)));

const state = ref({
  range: [initialStartDate, initialEndDate] as [Date, Date],
  start: initialStartDate,
  picker: false,
  end: initialEndDate,
  shoppingListDialog: false,
  addAllLoading: false,
});

const shoppingLists = ref<ShoppingListSummary[]>();

const firstDayOfWeek = computed(() => {
  return household.value?.preferences?.firstDayOfWeek || 0;
});

const weekRange = computed(() => {
  const sorted = [...state.value.range].sort((a, b) => a.getTime() - b.getTime());

  const start = sorted[0];
  const end = sorted[sorted.length - 1];

  if (start && end) {
    return { start, end };
  }
  return {
    start: addDays(new Date(), adjustForToday(-numberOfDaysPast.value)),
    end: addDays(new Date(), adjustForToday(numberOfDays.value)),
  };
});

// Update query parameters when date range changes
watch(weekRange, (newRange) => {
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
    const mealDate = parseISO(meal.date);
    return isSameDay(mealDate, date);
  });
}

function adjustForToday(days: number) {
  return days > 0 ? days - 1 : days;
}

const days = computed(() => {
  const numDays
    = Math.floor((weekRange.value.end.getTime() - weekRange.value.start.getTime()) / (1000 * 60 * 60 * 24)) + 1;

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

const hasRecipes = computed(() => {
  return mealsByDate.value.some(day => day.meals.some(meal => meal.recipe));
});

const hasMeals = computed(() => {
  return mealsByDate.value.some(day => day.meals.length > 0);
});

const weekRecipesWithScales = computed(() => {
  const allRecipes: any[] = [];
  for (const day of mealsByDate.value) {
    for (const meal of day.meals) {
      if (meal.recipe) {
        allRecipes.push({
          scale: meal.recipeScale ?? 1,
          ...meal.recipe,
        });
      }
    }
  }
  return allRecipes;
});

async function getShoppingLists() {
  const { data } = await api.shopping.lists.getAll(1, -1, { orderBy: "name", orderDirection: "asc" });
  if (data) {
    shoppingLists.value = data.items as ShoppingListSummary[] ?? [];
  }
}

async function addAllToList() {
  state.value.addAllLoading = true;
  await getShoppingLists();
  state.value.shoppingListDialog = true;
  state.value.addAllLoading = false;
}

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

const { plans, planEntries, fetchAll, fetchEntries, createOne: createPlan, deleteOne: deletePlan, applyToWeek, updateEntryScale } = useNamedMealPlans();

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
watch([() => viewMode.value, plans], ([mode]) => {
  if (mode === "named-plan" && !selectedPlanId.value && plans.value.length === 1) {
    selectedPlanId.value = plans.value[0]!.id;
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
  const current = plans.value.find(p => p.id === selectedPlanId.value);
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

  const allMeals = mealsByDate.value.flatMap(day => day.meals);
  for (const meal of allMeals) {
    await api.namedMealPlans.addEntry(targetPlanId, {
      recipeId: meal.recipeId || meal.recipe?.id || null,
      entryType: meal.entryType,
      title: meal.title || "",
      text: meal.text || "",
      recipeScale: meal.recipeScale ?? 1,
    });
  }

  // Move: remove from calendar after copying to the plan
  for (const meal of allMeals) {
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

<style lang="css">
.left-color-border {
  border-left: 5px solid var(--v-primary-base) !important;
}

.bottom-color-border {
  border-bottom: 2px solid var(--v-primary-base) !important;
}
</style>
