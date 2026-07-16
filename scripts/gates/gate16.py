"""Gate 16 — cross-version upgrade drill (twenty-harvest FILE_03).

Proves `manage.py upgrade` actually works on someone else's data, not just a fresh dev DB:
restores a seeded fixture from the previous release into a scratch database, runs the real
upgrade command against it, and checks its own post-checks passed (system-check + trial balance)
plus a row-count spot check. Twenty's `ci-cross-version-upgrade.yaml` reference — upgrades are
TESTED, not hoped.

Needs the PostgreSQL client tools (pg_dump/pg_restore/psql) under `PG_BIN`; skips with a loud
warning (never silently) when they're absent — e.g. a CI box with no local Postgres binary.

The fixture (`scripts/gates/fixtures/prev_release.dump`) is a pg_dump of a freshly seeded
database. First run creates it (drill = self-upgrade against the current release, since there's
no prior release yet); every later release should refresh it per Docs/RUNBOOK.md's Release
subsection (FILE_01 release steps).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURE = REPO_ROOT / "scripts" / "gates" / "fixtures" / "prev_release.dump"

# Row-count spot check after restore+upgrade — this schema has no separate "Invoice" model, so
# sales_order stands in for it (the closest revenue-document analogue; seed_demo.py creates one).
SPOT_TABLES = ["sales_customer", "inventory_item", "sales_order"]


def _pg_bin() -> Path:
    return Path(os.environ.get("PG_BIN", r"C:\Program Files\PostgreSQL\16\bin"))


def _db_config() -> dict:
    from django.conf import settings

    return settings.DATABASES["default"]


def _database_url(cfg: dict, name: str) -> str:
    return (
        f"postgresql://{cfg['USER']}:{cfg.get('PASSWORD') or ''}"
        f"@{cfg['HOST'] or 'localhost'}:{cfg['PORT'] or 5432}/{name}"
    )


def _psql(pg_bin: Path, cfg: dict, dbname: str, sql: str, *, tuples_only: bool = False):
    env = {**os.environ, "PGPASSWORD": cfg.get("PASSWORD") or ""}
    args = [str(pg_bin / "psql.exe")]
    if tuples_only:
        args += ["--tuples-only", "--no-align", "--field-separator=,"]
    args += [
        "--host", cfg["HOST"] or "localhost",
        "--port", str(cfg["PORT"] or 5432),
        "--username", cfg["USER"],
        "--dbname", dbname,
        "--command", sql,
    ]
    return subprocess.run(args, capture_output=True, text=True, env=env)


def _dropdb(pg_bin: Path, cfg: dict, name: str) -> None:
    _psql(pg_bin, cfg, "postgres", f"DROP DATABASE IF EXISTS {name};")


def _createdb(pg_bin: Path, cfg: dict, name: str) -> None:
    result = _psql(pg_bin, cfg, "postgres", f"CREATE DATABASE {name};")
    if result.returncode != 0:
        raise AssertionError(f"createdb {name} failed: {result.stderr}")


def _pg_dump(pg_bin: Path, cfg: dict, name: str, out_path: Path) -> None:
    env = {**os.environ, "PGPASSWORD": cfg.get("PASSWORD") or ""}
    result = subprocess.run(
        [
            str(pg_bin / "pg_dump.exe"), "--format=custom", "--no-owner", "--no-privileges",
            "--host", cfg["HOST"] or "localhost", "--port", str(cfg["PORT"] or 5432),
            "--username", cfg["USER"], "--dbname", name, "--file", str(out_path),
        ],
        capture_output=True, text=True, env=env,
    )
    if result.returncode != 0:
        raise AssertionError(f"pg_dump {name} failed: {result.stderr}")


def _pg_restore(pg_bin: Path, cfg: dict, name: str, dump_path: Path) -> None:
    env = {**os.environ, "PGPASSWORD": cfg.get("PASSWORD") or ""}
    result = subprocess.run(
        [
            str(pg_bin / "pg_restore.exe"), "--clean", "--if-exists", "--no-owner", "--no-privileges",
            "--host", cfg["HOST"] or "localhost", "--port", str(cfg["PORT"] or 5432),
            "--username", cfg["USER"], "--dbname", name, str(dump_path),
        ],
        capture_output=True, text=True, env=env,
    )
    # pg_restore commonly exits non-zero on benign --clean drop-notices against a fresh DB.
    if result.returncode != 0 and "does not exist, skipping" not in result.stderr:
        raise AssertionError(f"pg_restore into {name} failed: {result.stderr}")


def _run_manage(*args: str, database_url: str) -> str:
    env = {**os.environ, "DATABASE_URL": database_url}
    result = subprocess.run(
        [sys.executable, "manage.py", *args],
        cwd=str(REPO_ROOT), capture_output=True, text=True, env=env,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"manage.py {' '.join(args)} failed:\n{result.stdout[-2000:]}\n{result.stderr[-800:]}"
        )
    return result.stdout


def _spot_counts(pg_bin: Path, cfg: dict, dbname: str) -> dict[str, int]:
    query = " UNION ALL ".join(f"SELECT '{t}', count(*) FROM {t}" for t in SPOT_TABLES)
    result = _psql(pg_bin, cfg, dbname, query, tuples_only=True)
    if result.returncode != 0:
        raise AssertionError(f"spot row-count query failed: {result.stderr}")
    counts: dict[str, int] = {}
    for line in result.stdout.strip().splitlines():
        name, _, n = line.partition(",")
        if name.strip():
            counts[name.strip()] = int(n.strip())
    return counts


def _build_fixture(pg_bin: Path, cfg: dict, seed_db: str) -> None:
    print(f"GATE 16: fixture missing — seeding scratch DB '{seed_db}' to create it (first run only)")
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    _dropdb(pg_bin, cfg, seed_db)
    _createdb(pg_bin, cfg, seed_db)
    seed_url = _database_url(cfg, seed_db)
    try:
        _run_manage("migrate", database_url=seed_url)
        _run_manage("seed_identity", database_url=seed_url)
        _run_manage("seed_accounting", database_url=seed_url)
        env = {**os.environ, "DATABASE_URL": seed_url}
        result = subprocess.run(
            [sys.executable, "scripts/seed_demo.py"],
            cwd=str(REPO_ROOT), capture_output=True, text=True, env=env,
        )
        if result.returncode != 0:
            raise AssertionError(
                "seed_demo.py failed while building the drill fixture:\n"
                f"{result.stdout[-2000:]}\n{result.stderr[-800:]}"
            )
        _pg_dump(pg_bin, cfg, seed_db, FIXTURE)
    finally:
        _dropdb(pg_bin, cfg, seed_db)
    print(f"GATE 16: fixture created at {FIXTURE} — commit it")


def check() -> None:
    pg_bin = _pg_bin()
    tools = ["psql.exe", "pg_dump.exe", "pg_restore.exe"]
    if not all((pg_bin / t).exists() for t in tools):
        print(
            f"GATE 16 WARN: PostgreSQL client tools not found under {pg_bin} — skipping upgrade "
            "drill (CI/dev-box mismatch). Set PG_BIN to override."
        )
        return

    cfg = _db_config()
    source_db = cfg["NAME"]
    seed_db = f"{source_db}_upgrade_seed"
    drill_db = f"{source_db}_upgrade_drill"

    if not FIXTURE.exists():
        _build_fixture(pg_bin, cfg, seed_db)

    _dropdb(pg_bin, cfg, drill_db)
    _createdb(pg_bin, cfg, drill_db)
    try:
        _pg_restore(pg_bin, cfg, drill_db, FIXTURE)
        drill_url = _database_url(cfg, drill_db)
        _run_manage("upgrade", "--yes", "--skip-backup-check", database_url=drill_url)

        counts = _spot_counts(pg_bin, cfg, drill_db)
        empty = [name for name, n in counts.items() if n == 0]
        if empty:
            raise AssertionError(f"post-upgrade spot check found empty tables: {empty} (counts={counts})")
        print(f"GATE 16: upgrade drill OK — row counts {counts}")
    finally:
        _dropdb(pg_bin, cfg, drill_db)
