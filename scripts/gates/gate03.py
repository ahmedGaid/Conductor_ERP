"""Gate 03 — frontend foundation (React + TS + Vite, Arabic/RTL-first, i18n parity).

Asserts:
- the web app installs and BUILDS (tsc typecheck + vite build), which also runs the
  i18n key-parity check as its `prebuild` step (build fails on any missing key);
- i18n key-parity actually CATCHES drift, proven in both directions against a fixture;
- the app boots Arabic/RTL by default (index.html lang=ar dir=rtl) and re-applies
  dir/lang on every language change (live AR<->EN switch);
- styling is token-driven: no raw hex outside the tokens stylesheet;
- styling is direction-agnostic: no physical left/right properties (logical only).
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
WEB = REPO_ROOT / "apps" / "web"
SRC = WEB / "src"
LOCALES = SRC / "i18n" / "locales"
PARITY_SCRIPT = WEB / "scripts" / "check-i18n-parity.mjs"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _strip_comments(text: str) -> str:
    """Blank out /* ... */ comments while preserving line numbers (newlines kept)."""
    def _blank(match: re.Match[str]) -> str:
        return re.sub(r"[^\n]", " ", match.group(0))

    return re.sub(r"/\*.*?\*/", _blank, text, flags=re.DOTALL)


def _npm() -> str:
    exe = shutil.which("npm") or shutil.which("npm.cmd")
    if not exe:
        raise AssertionError("npm not found on PATH (Node toolchain required for Stage 3)")
    return exe


def _node() -> str:
    exe = shutil.which("node") or shutil.which("node.exe")
    if not exe:
        raise AssertionError("node not found on PATH (Node toolchain required for Stage 3)")
    return exe


def check() -> None:
    _assert(WEB.is_dir(), "apps/web does not exist")
    _assert((WEB / "node_modules").is_dir(), "apps/web/node_modules missing — run `npm install` in apps/web")

    npm = _npm()
    node = _node()

    # 1. Build = typecheck (tsc) + vite build, with i18n parity as the prebuild step.
    build = subprocess.run(
        [npm, "run", "build"],
        cwd=str(WEB),
        capture_output=True,
        text=True,
        shell=False,
    )
    if build.returncode != 0:
        raise AssertionError(
            "frontend build failed:\n" + build.stdout[-2500:] + "\n" + build.stderr[-1500:]
        )
    _assert((WEB / "dist" / "index.html").is_file(), "vite build produced no dist/index.html")

    # 2. i18n parity must CATCH drift — proven in both directions against a fixture.
    for drop_from in ("ar", "en"):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            for f in LOCALES.glob("*.json"):
                shutil.copyfile(f, tmp_dir / f.name)
            data = json.loads(_read(tmp_dir / f"{drop_from}.json"))
            data.pop("common", None)  # remove a top-level key to create drift
            (tmp_dir / f"{drop_from}.json").write_text(json.dumps(data), encoding="utf-8")
            res = subprocess.run(
                [node, str(PARITY_SCRIPT), str(tmp_dir)],
                capture_output=True,
                text=True,
                shell=False,
            )
            _assert(
                res.returncode != 0,
                f"i18n parity did NOT fail when keys were dropped from {drop_from!r}",
            )

    # 3. Arabic/RTL is the boot default.
    index_html = _read(WEB / "index.html")
    _assert('lang="ar"' in index_html, "index.html must default to lang=\"ar\"")
    _assert('dir="rtl"' in index_html, "index.html must default to dir=\"rtl\"")

    # 4. Live switch: dir/lang re-applied on language change; Arabic is the fallback.
    i18n_src = _read(SRC / "i18n" / "index.ts")
    _assert('fallbackLng: "ar"' in i18n_src, "i18n fallback language must be Arabic")
    _assert("languageChanged" in i18n_src and "applyDocumentLanguage" in i18n_src,
            "i18n must re-apply document dir/lang on languageChanged (live RTL<->LTR switch)")

    # 5. Token discipline: no raw hex outside tokens.css.
    hex_re = re.compile(r"#[0-9a-fA-F]{3,8}\b")
    for path in list(SRC.rglob("*.css")) + list(SRC.rglob("*.tsx")):
        if path.name == "tokens.css":
            continue
        for i, line in enumerate(_strip_comments(_read(path)).splitlines(), start=1):
            if hex_re.search(line):
                raise AssertionError(f"raw hex colour outside tokens.css: {path.name}:{i}: {line.strip()}")

    # 6. Direction-agnostic CSS: no physical left/right properties (logical only).
    physical = [
        re.compile(r"(margin|padding|border|inset)-(left|right)\b"),
        re.compile(r"(^|[\s;{])(left|right)\s*:"),
        re.compile(r"text-align\s*:\s*(left|right)\b"),
        re.compile(r"float\s*:\s*(left|right)\b"),
    ]
    for path in SRC.rglob("*.css"):
        for i, line in enumerate(_strip_comments(_read(path)).splitlines(), start=1):
            for pat in physical:
                if pat.search(line):
                    raise AssertionError(
                        f"physical left/right in CSS (use logical inline-start/end): {path.name}:{i}: {line.strip()}"
                    )

    # 7. Context-help coverage: every page route declared in App.tsx must have a help guide in the
    #    registry, and the Help center must be mounted once in the app shell. This is the mechanism
    #    that keeps per-page help in sync as the app grows — a new page without a guide fails here.
    app_src = _read(SRC / "App.tsx")
    app_routes = set(re.findall(r'path="([^"]+)"', app_src))
    app_routes -= {"*", "/*", "/login"}  # catch-alls + the shell-less login screen carry no help
    _assert((SRC / "help" / "HelpCenter.tsx").is_file(), "missing src/help/HelpCenter.tsx")
    _assert((SRC / "help" / "registry.ts").is_file(), "missing src/help/registry.ts")
    registry_src = _read(SRC / "help" / "registry.ts")
    covered = set(re.findall(r'^\s*"([^"]+)":', registry_src, flags=re.MULTILINE))
    missing = sorted(app_routes - covered)
    _assert(not missing, f"pages without a help guide — add them to src/help/registry.ts: {missing}")
    _assert("HelpCenter" in _read(SRC / "app" / "AppShell.tsx"),
            "the Help center must be mounted in AppShell so every page gets context help")
