<template>
  <BaseDialog
    v-model="mealplannerDialog"
    bottom-sheet
    :title="$t('recipe.add-recipe-to-mealplan')"
    color="primary"
    :icon="$globals.icons.calendar"
    can-submit
    :submit-text="$t('general.add')"
    :submit-disabled="addMode === 'named-plan' && !planId && !newPlanName.trim()"
    @submit="onAddToPlan"
  >
    <v-card-text>
      <v-btn-toggle
        v-model="addMode"
        mandatory
        density="compact"
        class="mb-4"
        style="width: 100%"
      >
        <v-btn value="date" style="flex: 1">
          <v-icon start>
            {{ $globals.icons.calendar }}
          </v-icon>
          {{ $t('general.date') }}
        </v-btn>
        <v-btn value="named-plan" style="flex: 1">
          <v-icon start>
            {{ $globals.icons.tags }}
          </v-icon>
          {{ $t('meal-plan.custom-plans') }}
        </v-btn>
      </v-btn-toggle>
      <template v-if="addMode === 'date'">
        <MealPlanDatePicker v-model="pickerModel" :multiple="pickerMultiple" :entry-type="newMealType" />
        <!-- the dates are part of the label, so they stay with the switch instead of floating above the next field -->
        <v-switch
          v-model="isWeekEntry"
          color="primary"
          hide-details
          class="mb-2"
        >
          <template #label>
            <div>
              <div>{{ $t("meal-plan.plan-for-the-whole-week") }}</div>
              <div v-if="isWeekEntry" class="text-caption text-medium-emphasis">
                {{ $d(weekRange.start, "short") }} - {{ $d(weekRange.end, "short") }}
              </div>
            </div>
          </template>
        </v-switch>
      </template>
      <template v-else>
        <v-select
          v-model="planId"
          :items="namedPlans"
          item-title="name"
          item-value="id"
          :label="$t('meal-plan.custom-plan')"
          :loading="namedPlansLoading"
          :disabled="!!newPlanName.trim()"
          clearable
          class="mb-2"
        />
        <div class="d-flex align-center my-2">
          <v-divider />
          <span class="mx-2 text-caption text-medium-emphasis">{{ $t('general.or') }}</span>
          <v-divider />
        </div>
        <v-text-field
          v-model="newPlanName"
          :label="$t('meal-plan.custom-plan-move-new-label')"
          :disabled="!!planId"
          class="mb-2"
        />
      </template>
      <v-select
        v-model="newMealType"
        :return-object="false"
        :items="planTypeOptions"
        :label="$t('recipe.entry-type')"
        item-title="text"
        item-value="value"
      />
    </v-card-text>
  </BaseDialog>
</template>

<script setup lang="ts">
import { useUserApi } from "~/composables/api";
import { useMealPlanEntryDates } from "~/composables/use-group-mealplan";
import { alert } from "~/composables/use-toast";
import type { PlanEntryType, ReadNamedMealPlan } from "~/lib/api/types/meal-plan";

const props = withDefaults(defineProps<{
  recipeId: string;
  recipeScale?: number;
}>(), {
  recipeScale: 1,
});

const mealplannerDialog = defineModel<boolean>({
  default: false,
});

const i18n = useI18n();
const api = useUserApi();
const planTypeOptions = usePlanTypeOptions();
const router = useRouter();

const addMode = ref<"date" | "named-plan">("date");
const newMealType = ref<PlanEntryType>("dinner");
const { isWeekEntry, weekRange, entryDatesPayload, pickerModel, pickerMultiple } = useMealPlanEntryDates();

const planId = ref<string | null>(null);
const newPlanName = ref("");
const namedPlans = ref<ReadNamedMealPlan[]>([]);
const namedPlansLoading = ref(false);

async function fetchNamedPlans() {
  namedPlansLoading.value = true;
  const { data } = await api.namedMealPlans.getAll(1, -1, { orderBy: "name", orderDirection: "asc" });
  if (data) namedPlans.value = data.items;
  namedPlansLoading.value = false;
}

watch(addMode, (mode) => {
  if (mode === "named-plan" && namedPlans.value.length === 0) {
    fetchNamedPlans();
  }
});

async function onAddToPlan() {
  if (addMode.value === "named-plan") {
    await addRecipeToNamedPlan();
  }
  else {
    await addRecipeToPlan();
  }
}

async function addRecipeToNamedPlan() {
  let targetPlanId = planId.value;

  if (newPlanName.value.trim()) {
    const { data: newPlan } = await api.namedMealPlans.createOne({ name: newPlanName.value.trim() });
    if (!newPlan) {
      alert.error(i18n.t("recipe.failed-to-add-recipe-to-mealplan"));
      return;
    }
    targetPlanId = newPlan.id;
    await fetchNamedPlans();
  }

  if (!targetPlanId) return;

  const { data } = await api.namedMealPlans.addEntry(targetPlanId, {
    recipeId: props.recipeId,
    entryType: newMealType.value,
    title: "",
    text: "",
    recipeScale: props.recipeScale,
  });
  if (data) {
    alert.success(i18n.t("recipe.recipe-added-to-mealplan"));
    planId.value = targetPlanId;
    newPlanName.value = "";
  }
  else {
    alert.error(i18n.t("recipe.failed-to-add-recipe-to-mealplan"));
  }
}

async function addRecipeToPlan() {
  const { response } = await api.mealplans.createOne({
    ...entryDatesPayload.value,
    entryType: newMealType.value,
    title: "",
    text: "",
    recipeId: props.recipeId,
    recipeScale: props.recipeScale,
  });

  if (response?.status === 201) {
    alert.success(i18n.t("recipe.recipe-added-to-mealplan"), null, {
      action: {
        message: i18n.t("general.view"),
        onClick: () => router.push("/household/mealplan/planner/view"),
      },
    });
  }
  else {
    alert.error(i18n.t("recipe.failed-to-add-recipe-to-mealplan"));
  }
}
</script>
