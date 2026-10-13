<template>
  <div>
    <GroupMealPlanEntryDialog
      v-model="dialog.open"
      :entry="dialog.entry"
      :date="dialog.date"
      @create="actions.createOne($event)"
      @update="actions.updateOne($event)"
    />
    <GroupMealPlanEntryDialog
      v-model="namedDialog.open"
      :entry="namedDialog.entry"
      named-plan
      @save-named="saveNamedEntry"
    />

    <!-- Custom plan mode -->
    <template v-if="viewMode === 'named-plan'">
      <v-alert
        v-if="!namedPlanId"
        type="info"
        variant="tonal"
        class="my-3"
      >
        {{ $t('meal-plan.custom-plan-select-edit-prompt') }}
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
          <SpinTransition>
            <v-card
              v-for="entry in namedPlanEntries"
              :key="entry.id"
              class="my-2 ml-4 mr-1"
            >
              <RecipeCardLineItem
                v-if="entry.recipe"
                class="py-2"
                :recipe="entry.recipe"
                disable-link
                @click="editNamedEntry(entry)"
              />
              <v-list-item
                v-else
                class="py-2"
                @click="editNamedEntry(entry)"
              >
                <template #prepend>
                  <v-avatar>
                    <v-icon>
                      {{ $globals.icons.primary }}
                    </v-icon>
                  </v-avatar>
                </template>
                <v-list-item-title>
                  {{ entry.title }}
                </v-list-item-title>
                <v-list-item-subtitle v-if="entry.text">
                  {{ entry.text }}
                </v-list-item-subtitle>
              </v-list-item>
              <v-divider class="mx-2" />
              <div class="py-2 px-2 d-flex align-center">
                <v-menu offset-y>
                  <template #activator="{ props: menuProps }">
                    <v-chip
                      v-bind="menuProps"
                      label
                      variant="elevated"
                      size="small"
                      color="accent"
                      @click.prevent
                    >
                      <v-icon start>
                        {{ $globals.icons.tags }}
                      </v-icon>
                      {{ getEntryTypeText(entry.entryType ?? "dinner") }}
                    </v-chip>
                  </template>
                  <v-list>
                    <v-list-item
                      v-for="mealType in planTypeOptions"
                      :key="mealType.value"
                      @click="namedPlanActions?.updateEntry(entry.id, { ...entry, entryType: mealType.value })"
                    >
                      <v-list-item-title> {{ mealType.text }} </v-list-item-title>
                    </v-list-item>
                  </v-list>
                </v-menu>
                <v-chip
                  v-if="entry.recipe && entry.recipeScale && entry.recipeScale !== 1"
                  size="small"
                  color="primary"
                  variant="tonal"
                  label
                  class="ml-2"
                >
                  {{ entry.recipeScale }}x
                </v-chip>
                <v-btn class="ml-auto" size="small" variant="text" icon @click="namedPlanActions?.deleteEntry(entry.id)">
                  <v-icon>{{ $globals.icons.delete }}</v-icon>
                </v-btn>
              </div>
            </v-card>
          </SpinTransition>
          <!-- Custom plan actions -->
          <div class="d-flex justify-end">
            <BaseButtonGroup
              :buttons="[
                { icon: $globals.icons.createAlt, text: $t('general.new'), event: 'create' },
                { icon: $globals.icons.potSteam, text: $t('meal-plan.random-dinner'), event: 'randomDinner' },
                { icon: $globals.icons.bowlMixOutline, text: $t('meal-plan.random-side'), event: 'randomSide' },
                {
                  icon: $globals.icons.diceMultiple,
                  text: $t('meal-plan.random-meal'),
                  event: 'random',
                  children: [
                    { icon: $globals.icons.diceMultiple, text: $t('meal-plan.breakfast'), event: 'randomBreakfast' },
                    { icon: $globals.icons.diceMultiple, text: $t('meal-plan.lunch'), event: 'randomLunch' },
                    { icon: $globals.icons.diceMultiple, text: $t('meal-plan.side'), event: 'randomSide' },
                    { icon: $globals.icons.diceMultiple, text: $t('meal-plan.snack'), event: 'randomSnack' },
                    { icon: $globals.icons.diceMultiple, text: $t('meal-plan.drink'), event: 'randomDrink' },
                    { icon: $globals.icons.diceMultiple, text: $t('meal-plan.dessert'), event: 'randomDessert' },
                  ],
                },
              ]"
              @create="editNamedEntry(null)"
              @random-breakfast="namedPlanActions?.addRandomEntry('breakfast')"
              @random-lunch="namedPlanActions?.addRandomEntry('lunch')"
              @random-dinner="namedPlanActions?.addRandomEntry('dinner')"
              @random-side="namedPlanActions?.addRandomEntry('side')"
              @random-snack="namedPlanActions?.addRandomEntry('snack')"
              @random-drink="namedPlanActions?.addRandomEntry('drink')"
              @random-dessert="namedPlanActions?.addRandomEntry('dessert')"
            />
          </div>
        </v-col>
      </v-row>
    </template>

    <!-- Date mode -->
    <MealPlanLayout v-else :mealplans="mealplans">
      <template #default="{ plan, index, day }">
        <MealPlanDay :day="day.date" :recipes="day.recipes" :actions="actions" inline-actions>
          <VueDraggable
            v-model="mealplansByDate[plan.date.toString()]!"
            tag="div"
            handle=".handle"
            :delay="250"
            :delay-on-touch-only="true"
            group="meals"
            :data-index="index"
            :data-box="plan.date"
            style="min-height: 150px"
            @end="onMoveCallback"
          >
            <SpinTransition>
              <v-card
                v-for="mealplan in mealplansByDate[plan.date.toString()]"
                :key="mealplan.id"
                class="my-2 ml-4 mr-1"
                :class="{ handle: $vuetify.display.smAndUp }"
              >
                <RecipeCardLineItem
                  v-if="mealplan.recipe"
                  class="py-2"
                  :recipe="mealplan.recipe"
                  disable-link
                  @click="editMeal(mealplan)"
                />
                <v-list-item
                  v-else
                  class="py-2"
                  @click="editMeal(mealplan)"
                >
                  <template #prepend>
                    <v-avatar>
                      <v-icon>
                        {{ $globals.icons.primary }}
                      </v-icon>
                    </v-avatar>
                  </template>
                  <v-list-item-title>
                    {{ mealplan.title }}
                  </v-list-item-title>
                  <v-list-item-subtitle v-if="mealplan.text">
                    {{ mealplan.text }}
                  </v-list-item-subtitle>
                </v-list-item>
                <v-divider class="mx-2" />
                <div class="py-2 px-2 d-flex" style="align-items: center">
                  <v-btn size="small" icon variant="text" :class="{ handle: !$vuetify.display.smAndUp }">
                    <v-icon>
                      {{ $globals.icons.arrowUpDown }}
                    </v-icon>
                  </v-btn>
                  <v-menu offset-y>
                    <template #activator="{ props: menuProps }">
                      <v-chip
                        v-bind="menuProps"
                        label
                        variant="elevated"
                        size="small"
                        color="accent"
                        @click.prevent
                      >
                        <v-icon start>
                          {{ $globals.icons.tags }}
                        </v-icon>
                        {{ getEntryTypeText(mealplan.entryType!) }}
                      </v-chip>
                    </template>
                    <v-list>
                      <v-list-item
                        v-for="mealType in planTypeOptions"
                        :key="mealType.value"
                        @click="actions.setType(mealplan, mealType.value)"
                      >
                        <v-list-item-title> {{ mealType.text }} </v-list-item-title>
                      </v-list-item>
                    </v-list>
                  </v-menu>
                  <v-chip
                    v-if="mealplan.recipe && (mealplan.recipeScale ?? 1) !== 1"
                    class="ml-2"
                    label
                    size="small"
                    color="secondary"
                  >
                    {{ $n(mealplan.recipeScale ?? 1, { maximumFractionDigits: 2 }) }}x
                  </v-chip>
                  <v-btn
                    v-if="mealplan.recipe && mealplan.entryType"
                    class="ml-auto"
                    size="small"
                    variant="text"
                    icon
                    :title="$t('meal-plan.randomize-recipe')"
                    @click="randomizeMeal(mealplan)"
                  >
                    <v-icon>{{ $globals.icons.diceMultiple }}</v-icon>
                  </v-btn>
                  <v-btn :class="{ 'ml-auto': !mealplan.recipe || !mealplan.entryType }" size="small" variant="text" icon @click="actions.deleteOne(mealplan.id)">
                    <v-icon>{{ $globals.icons.delete }}</v-icon>
                  </v-btn>
                </div>
              </v-card>
            </SpinTransition>
          </VueDraggable>
        </MealPlanDay>
      </template>
    </MealPlanLayout>
  </div>
</template>

<script setup lang="ts">
import { format } from "date-fns";
import type { SortableEvent } from "sortablejs";
import { VueDraggable } from "vue-draggable-plus";
import GroupMealPlanEntryDialog from "~/components/Domain/Household/GroupMealPlanEntryDialog.vue";
import RecipeCardLineItem from "~/components/Domain/Recipe/RecipeCardLineItem.vue";
import { useUserApi } from "~/composables/api";
import type { MealsByDate, useMealplans } from "~/composables/use-group-mealplan";
import { getEntryTypeText, usePlanTypeOptions } from "~/composables/use-group-mealplan";
import type { CreateNamedPlanEntry, ReadNamedPlanEntry, ReadPlanEntry } from "~/lib/api/types/meal-plan";

type NamedPlanActions = {
  addEntry: (data: CreateNamedPlanEntry) => Promise<void>;
  updateEntry: (entryId: string, data: CreateNamedPlanEntry) => Promise<void>;
  deleteEntry: (entryId: string) => Promise<void>;
  addRandomEntry: (entryType: string) => Promise<void>;
};

const props = defineProps<{
  mealplans: MealsByDate[];
  actions: ReturnType<typeof useMealplans>["actions"];
  viewMode?: string;
  namedPlanEntries?: ReadNamedPlanEntry[];
  namedPlanId?: string | null;
  namedPlanActions?: NamedPlanActions;
}>();

const api = useUserApi();
const planTypeOptions = usePlanTypeOptions();

// Local mutable meals object
const mealplansByDate = reactive<{ [date: string]: ReadPlanEntry[] }>({});
watch(
  () => props.mealplans,
  (plans) => {
    for (const plan of plans) {
      mealplansByDate[plan.date.toString()] = plan.meals ? [...plan.meals] : [];
    }
    // Remove any dates that no longer exist
    Object.keys(mealplansByDate).forEach((date) => {
      if (!plans.find(p => p.date.toString() === date)) {
        mealplansByDate[date] = [];
      }
    });
  },
  { immediate: true, deep: true },
);

function onMoveCallback(evt: SortableEvent) {
  // A Meal was moved, set the new date value and make an update request and refresh the meals
  const fromMealsByIndex = parseInt(evt.from.getAttribute("data-index") ?? "");
  const toMealsByIndex = parseInt(evt.to.getAttribute("data-index") ?? "");

  if (!isNaN(fromMealsByIndex) && !isNaN(toMealsByIndex)) {
    const destDate = props.mealplans[toMealsByIndex].date;
    const mealData = mealplansByDate[destDate.toString()][evt.newIndex as number];

    mealData.date = format(destDate, "yyyy-MM-dd");

    props.actions.updateOne(mealData);
  }
}

// =====================================================
// Meal Entry Dialog

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

async function randomizeMeal(mealplan: ReadPlanEntry) {
  if (!mealplan.entryType) {
    return;
  }

  // Create the new random entry first, so a failure here doesn't lose the current entry
  const { data: created } = await api.mealplans.setRandom({
    date: mealplan.date,
    entryType: mealplan.entryType,
  });

  if (created) {
    await api.mealplans.deleteOne(mealplan.id);
    props.actions.refreshAll();
  }
}

// =====================================================
// Named Plan Entry Dialog

const namedDialog = reactive({
  open: false,
  entry: null as ReadNamedPlanEntry | null,
});

function editNamedEntry(entry: ReadNamedPlanEntry | null) {
  namedDialog.entry = entry;
  namedDialog.open = true;
}

async function saveNamedEntry(data: CreateNamedPlanEntry, entryId: string | null) {
  if (!props.namedPlanActions) return;

  if (entryId) {
    await props.namedPlanActions.updateEntry(entryId, data);
  }
  else {
    await props.namedPlanActions.addEntry(data);
  }
}
</script>
