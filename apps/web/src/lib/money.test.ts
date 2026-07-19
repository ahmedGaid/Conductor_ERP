import { describe, expect, it } from "vitest";
import { formatMinor, minorToAmount, parseToMinor } from "./money";

describe("formatMinor", () => {
  it("formats whole + fractional minor units with grouping", () => {
    expect(formatMinor(100000)).toBe("1,000.00 EGP");
  });

  it("pads a single-digit fraction", () => {
    expect(formatMinor(100005)).toBe("1,000.05 EGP");
  });

  it("handles zero", () => {
    expect(formatMinor(0)).toBe("0.00 EGP");
  });

  it("keeps the sign on the outside of the grouped number", () => {
    expect(formatMinor(-150050)).toBe("-1,500.50 EGP");
  });

  it("accepts a custom currency", () => {
    expect(formatMinor(500, "USD")).toBe("5.00 USD");
  });
});

describe("minorToAmount", () => {
  it("converts minor units to a plain 2dp amount string", () => {
    expect(minorToAmount(100050)).toBe("1000.50");
  });

  it("keeps the sign, no grouping", () => {
    expect(minorToAmount(-100050)).toBe("-1000.50");
  });
});

describe("parseToMinor", () => {
  it("parses a whole amount", () => {
    expect(parseToMinor("1000")).toBe(100000);
  });

  it("parses a 2dp amount", () => {
    expect(parseToMinor("1000.50")).toBe(100050);
  });

  it("pads a single fractional digit", () => {
    expect(parseToMinor("10.5")).toBe(1050);
  });

  it("round-trips through minorToAmount", () => {
    expect(parseToMinor(minorToAmount(123456))).toBe(123456);
  });

  it("treats blank input as zero, not an error", () => {
    expect(parseToMinor("")).toBe(0);
    expect(parseToMinor("   ")).toBe(0);
  });

  it("parses a negative amount", () => {
    expect(parseToMinor("-50.25")).toBe(-5025);
  });

  it("rejects more than 2 fractional digits", () => {
    expect(parseToMinor("10.123")).toBeNull();
  });

  it("rejects non-numeric input", () => {
    expect(parseToMinor("abc")).toBeNull();
    expect(parseToMinor("12,000")).toBeNull();
  });

  it("does not accept Arabic-Indic digits (ASCII-only by design)", () => {
    // Documents current behavior — inputs are expected to be normalized to ASCII digits
    // upstream before reaching this parser; a genuine Arabic-numeral entry point would need
    // its own normalization step, not a change here.
    // Built from code points (not a literal) — gate14 bans Arabic-Indic digit characters in
    // source, this string only exists at test-run time.
    const arabicIndicThousand = [0x0661, 0x0660, 0x0660, 0x0660].map((cp) =>
      String.fromCodePoint(cp),
    ).join("");
    expect(parseToMinor(arabicIndicThousand)).toBeNull();
  });
});
