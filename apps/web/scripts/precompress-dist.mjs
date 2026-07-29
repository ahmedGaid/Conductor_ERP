// Pre-compression step — writes a `.gz` next to every compressible file in dist/.
//
// WhiteNoise serves the Vite build straight from apps/web/dist (WHITENOISE_ROOT, see
// config/settings/prod.py). It only ever sends `Content-Encoding: gzip` when a matching `.gz`
// file already sits on disk — it never compresses on the fly, and the
// CompressedManifestStaticFilesStorage backend only covers collectstatic's STATIC_ROOT, not
// WHITENOISE_ROOT. Without this step the demo shipped the main chunk raw (~780 kB instead of
// ~235 kB), which reads as a long white screen on a slow link even though check-bundle-size
// measured the chunk gzipped and passed.
//
// Runs as part of `postbuild`, so every `npm run build` leaves dist ready to serve.
import { readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { extname, join } from "node:path";
import { gzipSync, constants } from "node:zlib";

// Already-compressed formats: a second pass costs build time and gains nothing.
const SKIP_EXTENSIONS = new Set([
  ".gz", ".br", ".zip", ".tgz", ".bz2", ".xz",
  ".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".ico", ".icns",
  ".woff", ".woff2", ".mp4", ".webm", ".mp3",
]);
// Below this, the response fits in a packet or two — the .gz is pure disk noise.
const MIN_BYTES = 1024;
// WhiteNoise's own rule: keep the .gz only when it actually pays for itself.
const MAX_RATIO = 0.95;

const distDir = join(import.meta.dirname, "..", "dist");

function* walk(dir) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) yield* walk(full);
    else if (entry.isFile()) yield full;
  }
}

let files;
try {
  files = [...walk(distDir)];
} catch {
  console.error("precompress-dist: dist/ not found — run `vite build` first.");
  process.exit(1);
}

let compressed = 0;
let rawBytes = 0;
let gzipBytes = 0;

for (const file of files) {
  if (SKIP_EXTENSIONS.has(extname(file).toLowerCase())) continue;
  if (statSync(file).size < MIN_BYTES) continue;

  const raw = readFileSync(file);
  // mtime 0 keeps the output byte-identical across builds of identical input.
  const gz = gzipSync(raw, { level: constants.Z_BEST_COMPRESSION, mtime: 0 });
  if (gz.length >= raw.length * MAX_RATIO) continue;

  writeFileSync(`${file}.gz`, gz);
  compressed += 1;
  rawBytes += raw.length;
  gzipBytes += gz.length;
}

const kb = (bytes) => (bytes / 1024).toFixed(0);
if (compressed === 0) {
  console.error("precompress-dist: nothing compressed — dist/ looks empty or already packed.");
  process.exit(1);
}
console.log(
  `Pre-compressed ${compressed} files — ${kb(rawBytes)} kB raw -> ${kb(gzipBytes)} kB gzip ` +
    `(${Math.round((1 - gzipBytes / rawBytes) * 100)}% smaller on the wire).`,
);
