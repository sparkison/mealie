import { BaseCRUDAPI } from "../base/base-clients";
import type {
  ApplyNamedPlanPayload,
  CreateNamedMealPlan,
  CreateNamedPlanEntry,
  NamedMealPlanPagination,
  ReadNamedMealPlan,
  ReadNamedPlanEntry,
  ReadPlanEntry,
} from "~/lib/api/types/meal-plan";

const prefix = "/api";

const routes = {
  namedPlans: `${prefix}/households/mealplans/named-plans`,
  namedPlanId: (id: string | number) => `${prefix}/households/mealplans/named-plans/${id}`,
};

export class NamedMealPlansAPI extends BaseCRUDAPI<
  CreateNamedMealPlan,
  ReadNamedMealPlan,
  ReadNamedMealPlan
> {
  baseRoute = routes.namedPlans;
  itemRoute = routes.namedPlanId;

  async getAll(page = 1, perPage = -1, params = {}) {
    return await this.requests.get<NamedMealPlanPagination>(this.baseRoute, {
      params: { page, perPage, ...params },
    });
  }

  async getEntries(namedPlanId: string) {
    return await this.requests.get<ReadNamedPlanEntry[]>(`${this.itemRoute(namedPlanId)}/entries`);
  }

  async getEntry(namedPlanId: string, entryId: string) {
    return await this.requests.get<ReadNamedPlanEntry>(`${this.itemRoute(namedPlanId)}/entries/${entryId}`);
  }

  async addEntry(namedPlanId: string, data: CreateNamedPlanEntry) {
    return await this.requests.post<ReadNamedPlanEntry>(`${this.itemRoute(namedPlanId)}/entries`, data);
  }

  async updateEntry(namedPlanId: string, entryId: string, data: CreateNamedPlanEntry) {
    return await this.requests.put<ReadNamedPlanEntry, CreateNamedPlanEntry>(
      `${this.itemRoute(namedPlanId)}/entries/${entryId}`,
      data,
    );
  }

  async removeEntry(namedPlanId: string, entryId: string) {
    return await this.requests.delete(`${this.itemRoute(namedPlanId)}/entries/${entryId}`);
  }

  async addRandomEntry(namedPlanId: string, entryType: string) {
    return await this.requests.post<ReadNamedPlanEntry>(
      `${this.itemRoute(namedPlanId)}/random`,
      { entryType },
    );
  }

  async applyToWeek(namedPlanId: string, startDate: string) {
    return await this.requests.post<ReadPlanEntry[]>(
      `${this.itemRoute(namedPlanId)}/apply`,
      { startDate } as ApplyNamedPlanPayload,
    );
  }
}
