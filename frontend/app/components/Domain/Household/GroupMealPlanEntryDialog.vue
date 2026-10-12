<template>
  <BaseDialog
    v-model="dialog"
    :title="entry ? $t('meal-plan.update-this-meal-plan') : $t('meal-plan.create-a-new-meal-plan')"
    :submit-text="entry ? $t('general.update') : $t('general.create')"
    :icon="$globals.icons.foods"
    :submit-disabled="submitDisabled"
    color="primary"
    width="1000"
    can-submit
    disable-submit-on-enter
    @submit="submit"
  >
    <v-card-text>
      <v-row>
        <v-col
          cols="12"
          md="5"
        >
          <v-btn-toggle
            v-model="entryMode"
            mandatory
            divided
            variant="outlined"
            color="primary"
            class="w-100 mb-4"
          >
            <v-btn
              value="recipe"
              class="flex-grow-1"
            >
              <v-icon start>
                {{ $globals.icons.silverwareForkKnife }}
              </v-icon>
              {{ $t("general.recipe") }}
            </v-btn>
            <v-btn
              value="note"
              class="flex-grow-1"
            >
              <v-icon start>
                {{ $globals.icons.textBox }}
              </v-icon>
              {{ $t("meal-plan.note") }}
            </v-btn>
          </v-btn-toggle>

          <MealPlanDatePicker v-if="!namedPlan" v-model="selectedDate" :entry-type="entryType" />

          <v-select
            v-model="entryType"
            :class="{ 'mt-4': !namedPlan }"
            :items="planTypeOptions"
            :label="$t('recipe.entry-type')"
            item-title="text"
            item-value="value"
            :return-object="false"
            hide-details
          />

          <v-number-input
            v-if="isRecipe"
            v-model="recipeScale"
            class="mt-4"
            :min="0.25"
            :step="0.5"
            :precision="null"
            inset
            hide-details
            :label="$t('recipe.servings-scale')"
          />
        </v-col>

        <!-- both modes fill the same pane, so the dialog doesn't resize when switching between them -->
        <v-col
          cols="12"
          md="7"
          class="entry-detail"
        >
          <RecipeSelector
            v-if="isRecipe"
            ref="selector"
            v-model="recipe"
            height="auto"
            :query-filter="ruleQueryFilter"
          >
            <template #filters>
              <v-switch
                v-model="ignoreRules"
                class="ignore-rules-switch flex-grow-0 ms-auto"
                color="primary"
                density="compact"
                hide-details
                :disabled="!applicableRuleFilter"
                :label="$t('meal-plan.ignore-rules')"
              />
            </template>

            <template #no-results>
              <v-alert
                v-if="ruleQueryFilter"
                type="info"
                variant="tonal"
              >
                <div>{{ $t("meal-plan.no-recipes-match-your-rules") }}</div>
                <v-btn
                  class="mt-2"
                  size="small"
                  color="info"
                  variant="tonal"
                  @click="ignoreRules = true"
                >
                  {{ $t("meal-plan.ignore-rules") }}
                </v-btn>
              </v-alert>
              <v-alert
                v-else
                type="info"
                variant="tonal"
                :text="$t('search.no-results')"
              />
            </template>
          </RecipeSelector>

          <div v-else>
            <v-text-field
              v-model="title"
              :label="$t('meal-plan.meal-title')"
              :rules="[validators.required]"
            />
            <v-textarea
              v-model="text"
              :label="$t('meal-plan.meal-note')"
              rows="6"
            />
          </div>
        </v-col>
      </v-row>
    </v-card-text>
  </BaseDialog>
</template>

<script setup lang="ts">
import { format } from "date-fns";
import RecipeSelector from "~/components/Domain/Recipe/RecipeSelector.vue";
import { usePlanTypeOptions } from "~/composables/use-group-mealplan";
import { buildRuleQueryFilter, useMealplanRules } from "~/composables/use-mealplan-rules";
import { validators } from "~/composables/use-validators";
import type { CreateNamedPlanEntry, CreatePlanEntry, PlanEntryType, ReadNamedPlanEntry, ReadPlanEntry, UpdatePlanEntry } from "~/lib/api/types/meal-plan";
import type { RecipeSummary } from "~/lib/api/types/recipe";

interface Props {
  entry?: ReadPlanEntry | ReadNamedPlanEntry | null;
  date?: Date | null;
  /** Edit an entry of a named (custom) plan: no date, and saves via `saveNamed` */
  namedPlan?: boolean;
}
const props = withDefaults(defineProps<Props>(), {
  entry: null,
  date: null,
  namedPlan: false,
});

const emit = defineEmits<{
  create: [payload: CreatePlanEntry];
  update: [payload: UpdatePlanEntry];
  saveNamed: [payload: CreateNamedPlanEntry, entryId: string | null];
}>();

const dialog = defineModel<boolean>({ required: true });

const { rules } = useMealplanRules();
const planTypeOptions = usePlanTypeOptions();

const selector = ref<InstanceType<typeof RecipeSelector> | null>(null);

const entryMode = ref<"recipe" | "note">("recipe");
const selectedDate = ref(new Date());
const entryType = ref<PlanEntryType>("dinner");
const recipe = ref<RecipeSummary | null>(null);
const recipeScale = ref(1);
const title = ref("");
const text = ref("");
const ignoreRules = ref(false);

const isRecipe = computed(() => entryMode.value === "recipe");

// Rules are tied to days of the week, so they don't apply to undated named plans
const applicableRuleFilter = computed(() => props.namedPlan ? null : buildRuleQueryFilter(rules.value, selectedDate.value, entryType.value));
const ruleQueryFilter = computed(() => ignoreRules.value ? null : applicableRuleFilter.value);

const submitDisabled = computed(() => isRecipe.value ? !recipe.value : !title.value.trim());

function parseEntryDate(date: string) {
  const [year, month, day] = date.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function initialize() {
  entryMode.value = props.entry && !props.entry.recipeId ? "note" : "recipe";
  selectedDate.value = props.entry && "date" in props.entry ? parseEntryDate(props.entry.date) : props.date ?? new Date();
  entryType.value = props.entry?.entryType ?? "dinner";
  recipe.value = props.entry?.recipe ?? null;
  recipeScale.value = props.entry?.recipeScale ?? 1;
  title.value = props.entry?.title ?? "";
  text.value = props.entry?.text ?? "";
  ignoreRules.value = false;
  selector.value?.reset();
}

function submit() {
  if (props.namedPlan) {
    emit("saveNamed", {
      entryType: entryType.value,
      title: isRecipe.value ? "" : title.value,
      text: isRecipe.value ? "" : text.value,
      recipeId: isRecipe.value ? recipe.value?.id : null,
      recipeScale: isRecipe.value ? recipeScale.value : 1,
    }, props.entry?.id ? String(props.entry.id) : null);
    return;
  }

  const payload = {
    date: format(selectedDate.value, "yyyy-MM-dd"),
    entryType: entryType.value,
    title: isRecipe.value ? "" : title.value,
    text: isRecipe.value ? "" : text.value,
    recipeId: isRecipe.value ? recipe.value?.id : null,
    recipeScale: isRecipe.value ? recipeScale.value : 1,
  };

  if (props.entry && "date" in props.entry) {
    emit("update", {
      ...payload,
      id: props.entry.id,
      groupId: props.entry.groupId,
      userId: props.entry.userId,
    });
  }
  else {
    emit("create", payload);
  }
}

watch(dialog, (isOpen) => {
  if (isOpen) {
    initialize();
  }
});
</script>

<style scoped>
.entry-detail {
  position: relative;
  min-height: clamp(320px, 45vh, 520px);
}

/*
  Take the pane out of flow so a long result list scrolls inside it instead of growing the
  dialog, while it still stretches to the height of the settings column beside it.
  The inset matches the v-col gutter padding.
*/
.entry-detail > * {
  position: absolute;
  inset: 12px;
  overflow-y: auto;
}

/* v-switch reserves a taller control than the filter buttons next to it */
.ignore-rules-switch {
  --v-input-control-height: 28px;
  align-self: flex-start;
}
</style>
