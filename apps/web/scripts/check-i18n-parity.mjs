/*
 * i18n key-parity check. Fails (exit 1) if any translation key exists in one
 * locale but not the other — in EITHER direction. Wired as `prebuild`, so a
 * production build cannot ship with a missing/extra translation key. gate03
 * runs this same script.
 */
import { readFileSync, readdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
// Optional arg lets a test point the check at a fixture dir; defaults to the app locales.
const localesDir = process.argv[2]
  ? process.argv[2]
  : join(here, "..", "src", "i18n", "locales");

/** Flatten nested keys into dotted paths: { a: { b: 1 } } -> ["a.b"]. */
function flatten(obj, prefix = "") {
  const keys = [];
  for (const [key, value] of Object.entries(obj)) {
    const path = prefix ? `${prefix}.${key}` : key;
    if (value && typeof value === "object" && !Array.isArray(value)) {
      keys.push(...flatten(value, path));
    } else {
      keys.push(path);
    }
  }
  return keys;
}

function loadLocale(file) {
  const raw = readFileSync(join(localesDir, file), "utf8");
  return new Set(flatten(JSON.parse(raw)));
}

const files = readdirSync(localesDir).filter((f) => f.endsWith(".json"));
if (files.length < 2) {
  console.error(`i18n parity: expected >= 2 locale files, found ${files.length}`);
  process.exit(1);
}

const locales = new Map(files.map((f) => [f.replace(/\.json$/, ""), loadLocale(f)]));
const allKeys = new Set();
for (const set of locales.values()) for (const k of set) allKeys.add(k);

let failed = false;
for (const [lang, set] of locales) {
  const missing = [...allKeys].filter((k) => !set.has(k)).sort();
  if (missing.length > 0) {
    failed = true;
    console.error(`\n[${lang}] missing ${missing.length} key(s):`);
    for (const k of missing) console.error(`  - ${k}`);
  }
}

if (failed) {
  console.error("\ni18n parity check FAILED.");
  process.exit(1);
}

console.log(
  `i18n parity OK — ${allKeys.size} keys present in all ${locales.size} locales (${[...locales.keys()].join(", ")}).`,
);
