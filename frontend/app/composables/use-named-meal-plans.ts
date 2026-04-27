import { useUserApi } from "~/composables/api";
import type { ReadNamedMealPlan, ReadNamedPlanEntry } from "~/lib/api/types/meal-plan";

export const useNamedMealPlans = () => {
  const api = useUserApi();
  const plans = ref<ReadNamedMealPlan[]>([]);
  const loading = ref(false);
  const planEntries = ref<ReadNamedPlanEntry[]>([]);
  const entriesLoading = ref(false);

  async function fetchAll() {
    loading.value = true;
    const { data } = await api.namedMealPlans.getAll(1, -1, { orderBy: "name", orderDirection: "asc" });
    if (data) plans.value = data.items;
    loading.value = false;
  }

  async function createOne(name: string): Promise<ReadNamedMealPlan | null> {
    const { data } = await api.namedMealPlans.createOne({ name });
    if (data) await fetchAll();
    return data ?? null;
  }

  async function deleteOne(id: string): Promise<void> {
    await api.namedMealPlans.deleteOne(id);
    await fetchAll();
  }

  async function applyToWeek(id: string, startDate: string) {
    return api.namedMealPlans.applyToWeek(id, startDate);
  }

  async function fetchEntries(id: string) {
    entriesLoading.value = true;
    const { data } = await api.namedMealPlans.getEntries(id);
    planEntries.value = data ?? [];
    entriesLoading.value = false;
  }

  async function updateEntryScale(planId: string, entryId: string, scale: number) {
    const entry = planEntries.value.find(e => e.id === entryId);
    if (!entry) return;
    await api.namedMealPlans.updateEntry(planId, entryId, {
      recipeId: entry.recipeId,
      entryType: entry.entryType,
      title: entry.title,
      text: entry.text,
      recipeScale: scale,
    });
    await fetchEntries(planId);
  }

  onMounted(fetchAll);

  return { plans, loading, planEntries, entriesLoading, fetchAll, createOne, deleteOne, applyToWeek, fetchEntries, updateEntryScale };
};
