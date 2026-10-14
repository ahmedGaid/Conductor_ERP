// Marketing pricing model (public landing). Prices are whole EGP per user / month; the model is a
// one-time implementation fee + a per-user monthly subscription (see landing.pricing.* i18n). All
// display labels live in i18n — this module carries only ids + numbers so ar/en stay in the locales.

/** Annual billing discount (≈ one month free). */
export const ANNUAL_DISCOUNT = 0.1;

/** A prebuilt tier. `perUser` in whole EGP; `null` = custom (Enterprise, priced on a call). */
export interface Tier {
  id: "core" | "ops" | "ent";
  perUser: number | null;
  /** Highlighted "most chosen" tier. */
  popular?: boolean;
  /** Solid (near-white) primary CTA vs. quiet outline. */
  solidCta?: boolean;
  /** i18n keys (under landing.pricing) of the modules listed on the card. */
  moduleKeys: string[];
  /** Show the "estimate a custom plan" link under the card. */
  estimate?: boolean;
}

export const TIERS: Tier[] = [
  {
    id: "core",
    perUser: 1200,
    moduleKeys: ["mod.gl", "mod.inv", "mod.po"],
  },
  {
    id: "ops",
    perUser: 2800,
    popular: true,
    solidCta: true,
    moduleKeys: ["tiers.ops.incCore", "mod.crm", "mod.fa", "mod.bi"],
  },
  {
    id: "ent",
    perUser: null,
    estimate: true,
    moduleKeys: [
      "tiers.ent.incOps",
      "tiers.ent.mfgHr",
      "tiers.ent.eam",
      "tiers.ent.multiCo",
      "tiers.ent.custom",
    ],
  },
];

/** A single priceable module in the custom per-user builder. `price` = whole EGP / user / month. */
export interface BuilderModule {
  id: string;
  /** i18n key under landing.pricing (shared with the tier module lists). */
  labelKey: string;
  price: number;
}

export const BUILDER_MODULES: BuilderModule[] = [
  { id: "gl", labelKey: "mod.gl", price: 500 },
  { id: "inv", labelKey: "mod.inv", price: 400 },
  { id: "po", labelKey: "mod.po", price: 300 },
  { id: "mfg", labelKey: "mod.mfg", price: 600 },
  { id: "crm", labelKey: "mod.crm", price: 350 },
  { id: "hr", labelKey: "mod.hr", price: 350 },
  { id: "fa", labelKey: "mod.fa", price: 300 },
  { id: "bi", labelKey: "mod.bi", price: 250 },
];

/** Grouped whole-EGP integer — Latin digits in both locales (brand rule), no minor units. */
export function formatEgp(n: number): string {
  return Math.round(n).toLocaleString("en-US");
}
