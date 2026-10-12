import { flushPromises, mount, type VueWrapper } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import RecipeDialogAddToShoppingList from "./RecipeDialogAddToShoppingList.vue";
import type { ShoppingListSummary } from "~/lib/api/types/household";
import type { RecipeWithScale } from "./RecipeDialogAddToShoppingList.vue";

const wrappers: VueWrapper[] = [];

const mocks = vi.hoisted(() => ({
  createOne: vi.fn(),
  alertError: vi.fn(),
}));

vi.mock("~/composables/api", () => ({
  useUserApi: () => ({
    shopping: { lists: { createOne: mocks.createOne, addRecipes: vi.fn() } },
    recipes: { getOne: vi.fn() },
  }),
}));

vi.mock("~/composables/use-toast", () => ({
  alert: { error: mocks.alertError, success: vi.fn() },
}));

vi.mock("~/composables/use-users/preferences", () => ({
  useShoppingListPreferences: () => ref({ viewAllLists: false }),
}));

function list(id: string, name: string): ShoppingListSummary {
  return { id, name, userId: "user-1", groupId: "group", householdId: "household" } as ShoppingListSummary;
}

const recipe = {
  id: "recipe-1",
  slug: "recipe-1",
  name: "Recipe",
  recipeIngredient: [],
  scale: 1,
} as unknown as RecipeWithScale;

function mountDialog(shoppingLists: ShoppingListSummary[]) {
  const wrapper: VueWrapper<any> = mount(RecipeDialogAddToShoppingList, {
    props: {
      "modelValue": false,
      "recipes": [recipe],
      shoppingLists,
      // Behave like a parent using v-model:shopping-lists
      "onUpdate:shoppingLists": (value: ShoppingListSummary[]) => wrapper.setProps({ shoppingLists: value }),
    },
    global: {
      mocks: {
        $globals: { icons: { cartCheck: "cartCheck", create: "create" } },
      },
      stubs: {
        BaseDialog: {
          props: ["title"],
          template: "<section class=\"dialog\" :data-title=\"title\"><slot /><slot name=\"card-actions\" /></section>",
        },
        BasePageTitle: { template: "<div><slot name=\"title\" /></div>" },
        RecipeIngredientListItem: { template: "<div />" },
        VExpandTransition: { template: "<div><slot /></div>" },
        VTextField: {
          props: ["modelValue"],
          template: "<input class=\"new-list-name\" :value=\"modelValue\" @input=\"$emit('update:modelValue', $event.target.value)\">",
        },
        VCheckbox: { template: "<div />" },
        VBtn: {
          props: ["disabled"],
          template: "<button type=\"button\" :disabled=\"disabled\"><slot /></button>",
        },
        VCard: { template: "<div class=\"list-card\"><slot /></div>" },
      },
    },
  });

  wrappers.push(wrapper);
  return wrapper;
}

function button(wrapper: VueWrapper, text: string) {
  const match = wrapper.findAll("button").find(btn => btn.text() === text);
  if (!match) throw new Error(`no button "${text}"`);
  return match;
}

function listNames(wrapper: VueWrapper) {
  return wrapper.findAll(".list-card").map(card => card.text());
}

async function open(wrapper: VueWrapper) {
  await wrapper.setProps({ modelValue: true });
  await flushPromises();
}

async function createList(wrapper: VueWrapper, name: string) {
  await button(wrapper, "New List").trigger("click");
  await wrapper.find(".new-list-name").setValue(name);
  await button(wrapper, "Create").trigger("click");
  await flushPromises();
}

describe("recipeDialogAddToShoppingList new list", () => {
  beforeEach(() => {
    mocks.createOne.mockReset();
    mocks.alertError.mockReset();
    vi.stubGlobal("useMealieAuth", () => ({ user: ref({ id: "user-1", householdSlug: "home" }) }));
    vi.stubGlobal("useRouter", () => ({ push: vi.fn() }));
  });

  afterEach(() => {
    wrappers.forEach(wrapper => wrapper.unmount());
    wrappers.length = 0;
    vi.unstubAllGlobals();
  });

  test("create is disabled until a name is entered", async () => {
    const wrapper = mountDialog([list("a", "Groceries"), list("b", "Costco")]);
    await open(wrapper);

    await button(wrapper, "New List").trigger("click");
    expect(button(wrapper, "Create").attributes("disabled")).toBeDefined();

    await wrapper.find(".new-list-name").setValue("   ");
    expect(button(wrapper, "Create").attributes("disabled")).toBeDefined();

    await wrapper.find(".new-list-name").setValue("Weekend");
    expect(button(wrapper, "Create").attributes("disabled")).toBeUndefined();
  });

  test("creates the list and moves straight to picking ingredients for it", async () => {
    mocks.createOne.mockResolvedValue({ data: list("c", "Weekend") });
    const wrapper = mountDialog([list("a", "Groceries"), list("b", "Costco")]);
    await open(wrapper);

    await createList(wrapper, "  Weekend  ");

    expect(mocks.createOne).toHaveBeenCalledExactlyOnceWith({ name: "Weekend" });
    expect(wrapper.find(".dialog").attributes("data-title")).toBe("Weekend");
  });

  test("passes the new list to the parent so it is still listed when the dialog is reopened", async () => {
    mocks.createOne.mockResolvedValue({ data: list("c", "Weekend") });
    const wrapper = mountDialog([list("a", "Groceries"), list("b", "Costco")]);
    await open(wrapper);

    await createList(wrapper, "Weekend");
    expect(wrapper.emitted("update:shoppingLists")).toEqual([[
      [list("a", "Groceries"), list("b", "Costco"), list("c", "Weekend")],
    ]]);

    await wrapper.setProps({ modelValue: false });
    await open(wrapper);

    expect(listNames(wrapper)).toEqual(["Groceries", "Costco", "Weekend"]);
  });

  test("shows an error and stays on the list picker when creation fails", async () => {
    mocks.createOne.mockResolvedValue({ data: null });
    const wrapper = mountDialog([list("a", "Groceries"), list("b", "Costco")]);
    await open(wrapper);

    await createList(wrapper, "Weekend");

    expect(mocks.alertError).toHaveBeenCalledOnce();
    expect(wrapper.emitted("update:shoppingLists")).toBeUndefined();
    expect(listNames(wrapper)).toEqual(["Groceries", "Costco"]);
  });
});
