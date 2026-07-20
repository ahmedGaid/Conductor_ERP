import { describe, expect, it } from "vitest";
import { codeAndName, isArabic, localizedName, searchableNames } from "./bilingualName";

const cash = { code: "1000", name: "Cash", name_ar: "النقدية" };
const legacy = { code: "1010", name: "Bank", name_ar: "" };

describe("isArabic", () => {
  it("accepts the bare tag and any region form", () => {
    expect(isArabic("ar")).toBe(true);
    expect(isArabic("ar-EG")).toBe(true);
  });

  it("rejects English and an unset language", () => {
    expect(isArabic("en")).toBe(false);
    expect(isArabic(undefined)).toBe(false);
  });
});

describe("localizedName", () => {
  it("picks the Arabic name on Arabic screens", () => {
    expect(localizedName(cash, "ar")).toBe("النقدية");
  });

  it("picks the canonical name on English screens", () => {
    expect(localizedName(cash, "en")).toBe("Cash");
  });

  it("falls back to the canonical name when the Arabic one is blank", () => {
    expect(localizedName(legacy, "ar")).toBe("Bank");
  });

  it("treats a whitespace-only Arabic name as blank", () => {
    expect(localizedName({ name: "Bank", name_ar: "   " }, "ar")).toBe("Bank");
  });

  it("falls back when the field is missing entirely", () => {
    expect(localizedName({ name: "Bank" }, "ar")).toBe("Bank");
  });
});

describe("codeAndName", () => {
  it("keeps the code first in both languages", () => {
    expect(codeAndName(cash, "ar")).toBe("1000 · النقدية");
    expect(codeAndName(cash, "en")).toBe("1000 · Cash");
  });
});

describe("searchableNames", () => {
  it("matches on either script", () => {
    expect(searchableNames(cash)).toBe("Cash النقدية");
  });

  it("does not append a trailing blank", () => {
    expect(searchableNames(legacy)).toBe("Bank");
  });
});
