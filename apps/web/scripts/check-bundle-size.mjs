// Bundle budget gate — fails the build when the main JS chunk outgrows its budget.
//
// Speed is brand: the budget stops a stray import from quietly dragging a heavy library into
// the eagerly-loaded chunk (route-split screens like the workflow canvas own their own chunks).
// Runs as `postbuild`, so `npm run build` (and every gate that builds) enforces it. Budgets are
// recorded in DECISIONS.md "Perf budgets 2026-07" — raise them there, deliberately, not here.
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { gzipSync } from "node:zlib";

const MAIN_CHUNK_GZIP_BUDGET_KB = 230;

const assetsDir = join(import.meta.dirname, "..", "dist", "assets");
let files;
try {
  files = readdirSync(assetsDir).filter((f) => f.endsWith(".js"));
} catch {
  console.error("check-bundle-size: dist/assets not found — run `vite build` first.");
  process.exit(1);
}
if (files.length === 0) {
  console.error("check-bundle-size: no JS chunks in dist/assets — build looks broken.");
  process.exit(1);
}

// The main chunk is the largest one: everything eagerly imported lands there.
const chunks = files
  .map((name) => {
    const raw = readFileSync(join(assetsDir, name));
    return { name, rawKb: raw.length / 1024, gzipKb: gzipSync(raw).length / 1024 };
  })
  .sort((a, b) => b.gzipKb - a.gzipKb);

const main = chunks[0];
const fmt = (chunk) =>
  `${chunk.name} — ${chunk.gzipKb.toFixed(1)} kB gzip (${chunk.rawKb.toFixed(0)} kB raw)`;

if (main.gzipKb > MAIN_CHUNK_GZIP_BUDGET_KB) {
  console.error(
    `Bundle budget EXCEEDED: main chunk ${fmt(main)} > ${MAIN_CHUNK_GZIP_BUDGET_KB} kB gzip budget.\n` +
      "Route-split the newly-heavy screen (React.lazy) or move the heavy import into a lazy chunk.",
  );
  process.exit(1);
}
console.log(
  `Bundle budget OK — main chunk ${fmt(main)} within ${MAIN_CHUNK_GZIP_BUDGET_KB} kB gzip budget` +
    ` (${chunks.length} JS chunks).`,
);
