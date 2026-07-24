import { describe, it, expect } from "vitest";
import { isMeaningfulChange, reconcile, hasConflict } from "./draftRecovery";

describe("isMeaningfulChange", () => {
  it("is false when the value equals the empty baseline", () => {
    expect(isMeaningfulChange({ name: "" }, { name: "" })).toBe(false);
  });
  it("is true once any field differs from the baseline", () => {
    expect(isMeaningfulChange({ name: "A" }, { name: "" })).toBe(true);
  });
});

describe("reconcile", () => {
  const s = { payload: { v: "server" }, clientVersion: 2 };
  const l = { payload: { v: "local" }, clientVersion: 3 };
  it("returns none when both are absent", () => {
    expect(reconcile(null, null)).toEqual({ source: "none", payload: null });
  });
  it("prefers the only side present", () => {
    expect(reconcile(s, null).source).toBe("server");
    expect(reconcile(null, l).source).toBe("local");
  });
  it("prefers the higher clientVersion when both exist (local ahead after a mid-flight crash)", () => {
    expect(reconcile(s, l)).toEqual({ source: "local", payload: { v: "local" } });
  });
  it("prefers the server when it is at least as new", () => {
    expect(reconcile({ payload: { v: "server" }, clientVersion: 5 }, l).source).toBe("server");
  });
});

describe("hasConflict", () => {
  it("is true when this client's expected version trails the stored version", () => {
    expect(hasConflict(1, 2)).toBe(true);
  });
  it("is false when up to date", () => {
    expect(hasConflict(2, 2)).toBe(false);
  });
});
