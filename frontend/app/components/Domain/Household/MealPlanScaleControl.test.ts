import { mount, type VueWrapper } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { nextTick } from "vue";
import MealPlanScaleControl from "./MealPlanScaleControl.vue";
import type { ReadPlanEntry } from "~/lib/api/types/meal-plan";

const wrappers: VueWrapper[] = [];

function meal(overrides: Partial<ReadPlanEntry> = {}): ReadPlanEntry {
  return {
    id: 1,
    date: "2026-10-12",
    entryType: "dinner",
    groupId: "group",
    userId: "user",
    householdId: "household",
    recipeId: "recipe",
    recipeScale: 1,
    recipe: { id: "recipe", recipeServings: 4 },
    ...overrides,
  } as ReadPlanEntry;
}

function mountControl(entry: ReadPlanEntry) {
  const updateOne = vi.fn();
  const wrapper = mount(MealPlanScaleControl, {
    props: {
      meal: entry,
      actions: { updateOne } as any,
    },
    global: {
      mocks: {
        $globals: { icons: { edit: "edit", undo: "undo", minus: "minus", createAlt: "createAlt" } },
      },
      stubs: {
        VMenu: { template: "<div><slot name=\"activator\" :props=\"{}\" /><slot /></div>" },
        VTooltip: { template: "<div><slot name=\"activator\" :props=\"{}\" /><slot /></div>" },
        VCard: { template: "<div><slot /></div>" },
        VCardTitle: { template: "<div><slot /></div>" },
        VCardText: { template: "<div><slot /></div>" },
        VIcon: { template: "<i><slot /></i>" },
        VNumberInput: {
          props: ["modelValue"],
          template: "<input class=\"yield-input\" :value=\"modelValue\" @input=\"$emit('update:modelValue', Number($event.target.value))\">",
        },
        VBtn: {
          props: ["disabled"],
          template: "<button type=\"button\" :disabled=\"disabled\"><slot /></button>",
        },
      },
    },
  });

  wrappers.push(wrapper);
  return { wrapper, updateOne };
}

function button(wrapper: VueWrapper, icon: string) {
  const match = wrapper.findAll("button").find(btn => btn.text() === icon);
  if (!match) throw new Error(`no button with icon ${icon}`);
  return match;
}

describe("mealPlanScaleControl", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    wrappers.forEach(wrapper => wrapper.unmount());
    wrappers.length = 0;
    vi.useRealTimers();
  });

  test("shows the scaled servings for the stored scale", () => {
    const { wrapper } = mountControl(meal({ recipeScale: 1.5 }));

    expect(wrapper.text()).toContain("6");
  });

  test("adding a serving recalculates the scale and saves after the debounce", async () => {
    const { wrapper, updateOne } = mountControl(meal());

    await button(wrapper, "createAlt").trigger("click");
    vi.advanceTimersByTime(399);
    expect(updateOne).not.toHaveBeenCalled();

    vi.advanceTimersByTime(1);
    expect(updateOne).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({ id: 1, recipeScale: 1.25 }));
  });

  test("removing a serving recalculates the scale", async () => {
    const { wrapper, updateOne } = mountControl(meal());

    await button(wrapper, "minus").trigger("click");
    vi.runAllTimers();

    expect(updateOne).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({ recipeScale: 0.75 }));
  });

  test("rapid changes are debounced into a single save of the last value", async () => {
    const { wrapper, updateOne } = mountControl(meal());

    await button(wrapper, "createAlt").trigger("click");
    vi.advanceTimersByTime(200);
    await button(wrapper, "createAlt").trigger("click");
    vi.advanceTimersByTime(200);
    expect(updateOne).not.toHaveBeenCalled();

    vi.runAllTimers();
    expect(updateOne).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({ recipeScale: 1.5 }));
  });

  test("typing a servings count converts it to a scale", async () => {
    const { wrapper, updateOne } = mountControl(meal());

    await wrapper.find(".yield-input").setValue("8");
    vi.runAllTimers();

    expect(updateOne).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({ recipeScale: 2 }));
  });

  test("ignores invalid servings counts", async () => {
    const { wrapper, updateOne } = mountControl(meal());

    await wrapper.find(".yield-input").setValue("0");
    await wrapper.find(".yield-input").setValue("-2");
    vi.runAllTimers();

    expect(updateOne).not.toHaveBeenCalled();
  });

  test("returning to the stored scale before the debounce does not save", async () => {
    const { wrapper, updateOne } = mountControl(meal());

    await button(wrapper, "createAlt").trigger("click");
    await button(wrapper, "minus").trigger("click");
    vi.runAllTimers();

    expect(updateOne).not.toHaveBeenCalled();
  });

  test("resetting saves a scale of 1", async () => {
    const { wrapper, updateOne } = mountControl(meal({ recipeScale: 2 }));

    await button(wrapper, "undo").trigger("click");
    vi.runAllTimers();

    expect(updateOne).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({ recipeScale: 1 }));
  });

  test("follows scale changes made elsewhere without saving them again", async () => {
    const { wrapper, updateOne } = mountControl(meal());

    await wrapper.setProps({ meal: meal({ recipeScale: 2 }) });
    await nextTick();
    vi.runAllTimers();

    expect(wrapper.text()).toContain("8");
    expect(updateOne).not.toHaveBeenCalled();
  });

  test("falls back to one serving for recipes without a yield", async () => {
    const { wrapper, updateOne } = mountControl(meal({ recipe: { id: "recipe" } as ReadPlanEntry["recipe"] }));

    await button(wrapper, "createAlt").trigger("click");
    vi.runAllTimers();

    expect(updateOne).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({ recipeScale: 2 }));
  });
});
