import { describe, expect, it } from "vitest";

import {
  ANNUAL_DISCOUNT,
  BUILDER_MODULES,
  TIERS,
  formatEgp,
} from "./pricingData";

describe("formatEgp", () => {
  it("groups thousands with Latin digits and no minor units", () => {
    expect(formatEgp(2800)).toBe("2,800");
    expect(formatEgp(1284500)).toBe("1,284,500");
    expect(formatEgp(0)).toBe("0");
  });

  it("rounds fractional totals to whole EGP", () => {
    // 12 months at the annual discount can produce a fraction — display stays whole.
    expect(formatEgp(500 * 12 * (1 - ANNUAL_DISCOUNT))).toBe("5,400");
  });
});

describe("builder totals", () => {
  const priceOf = Object.fromEntries(BUILDER_MODULES.map((m) => [m.id, m.price]));

  it("sums the selected modules for a user", () => {
    const mods = ["gl", "inv"]; // 500 + 400
    const total = mods.reduce((s, id) => s + (priceOf[id] ?? 0), 0);
    expect(total).toBe(900);
  });

  it("applies the annual discount as roughly one month free", () => {
    const monthly = 2800;
    const yearly = monthly * 12 * (1 - ANNUAL_DISCOUNT);
    expect(yearly).toBe(30240);
    expect(monthly * 12 - yearly).toBeCloseTo(monthly * 12 * ANNUAL_DISCOUNT);
  });
});

describe("tier config", () => {
  it("has exactly one popular tier and one custom (Enterprise) tier", () => {
    expect(TIERS.filter((t) => t.popular)).toHaveLength(1);
    expect(TIERS.filter((t) => t.perUser === null)).toHaveLength(1);
  });
});
