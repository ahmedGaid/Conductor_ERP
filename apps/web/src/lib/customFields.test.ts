import { describe, expect, it } from "vitest";
import type { CustomFieldDef } from "../api/customFields";
import { buildCustomData, formatCustomFieldValue, validateCustomFieldValues } from "./customFields";

function def(overrides: Partial<CustomFieldDef>): CustomFieldDef {
  return {
    id: 1,
    entity_key: "sales.customer",
    key: "loyalty_tier",
    label_ar: "فئة الولاء",
    label_en: "Loyalty tier",
    type: "TEXT",
    required: false,
    choices: [],
    is_active: true,
    position: 0,
    ...overrides,
  };
}

describe("validateCustomFieldValues", () => {
  it("flags a required field left blank", () => {
    const errors = validateCustomFieldValues([def({ required: true })], {});
    expect(errors.loyalty_tier).toBeDefined();
  });

  it("passes a blank optional field", () => {
    const errors = validateCustomFieldValues([def({ required: false })], {});
    expect(errors.loyalty_tier).toBeUndefined();
  });

  it("rejects a non-numeric NUMBER value", () => {
    const errors = validateCustomFieldValues(
      [def({ key: "score", type: "NUMBER" })],
      { score: "abc" },
    );
    expect(errors.score).toBeDefined();
  });

  it("accepts a valid MONEY value", () => {
    const errors = validateCustomFieldValues(
      [def({ key: "bonus", type: "MONEY" })],
      { bonus: "1250.50" },
    );
    expect(errors.bonus).toBeUndefined();
  });

  it("rejects a malformed DATE value", () => {
    const errors = validateCustomFieldValues(
      [def({ key: "renewed_at", type: "DATE" })],
      { renewed_at: "19-07-2026" },
    );
    expect(errors.renewed_at).toBeDefined();
  });

  it("accepts an ISO DATE value", () => {
    const errors = validateCustomFieldValues(
      [def({ key: "renewed_at", type: "DATE" })],
      { renewed_at: "2026-07-19" },
    );
    expect(errors.renewed_at).toBeUndefined();
  });

  it("rejects a CHOICE value not in the list", () => {
    const errors = validateCustomFieldValues(
      [def({ key: "tier", type: "CHOICE", choices: ["gold", "silver"] })],
      { tier: "platinum" },
    );
    expect(errors.tier).toBeDefined();
  });

  it("accepts a CHOICE value that is in the list", () => {
    const errors = validateCustomFieldValues(
      [def({ key: "tier", type: "CHOICE", choices: ["gold", "silver"] })],
      { tier: "gold" },
    );
    expect(errors.tier).toBeUndefined();
  });
});

describe("buildCustomData", () => {
  it("drops blank optional fields entirely", () => {
    const out = buildCustomData([def({ required: false })], {});
    expect(out).toEqual({});
  });

  it("converts a MONEY value to integer minor units", () => {
    const out = buildCustomData([def({ key: "bonus", type: "MONEY" })], { bonus: "12.50" });
    expect(out).toEqual({ bonus: 1250 });
  });

  it("passes through a TEXT value unchanged", () => {
    const out = buildCustomData([def({ key: "note", type: "TEXT" })], { note: "vip" });
    expect(out).toEqual({ note: "vip" });
  });
});

describe("formatCustomFieldValue", () => {
  it("formats a MONEY value via formatMinor", () => {
    expect(formatCustomFieldValue(def({ type: "MONEY" }), 1250)).toBe("12.50 EGP");
  });

  it("returns an empty string for null/undefined/blank", () => {
    const d = def({ type: "TEXT" });
    expect(formatCustomFieldValue(d, null)).toBe("");
    expect(formatCustomFieldValue(d, undefined)).toBe("");
    expect(formatCustomFieldValue(d, "")).toBe("");
  });

  it("stringifies a non-money value", () => {
    expect(formatCustomFieldValue(def({ type: "TEXT" }), "vip")).toBe("vip");
  });
});
