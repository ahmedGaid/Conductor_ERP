# Phase 00 — Scaffold & Gate Runner

## Goal
Stand up the monorepo, toolchain, a running PostgreSQL, and the gate-runner harness so every later phase
can self-verify with `npm run gate:NN`.

## Files to create
```
erp-orchestrator/
├── package.json                 # npm workspaces root
├── tsconfig.base.json
├── .editorconfig
├── .gitignore
├── .env.example
├── docker-compose.yml           # postgres:16
├── DECISIONS.md                 # running log of deviations / forbidden-list temptations
├── README.md
├── scripts/
│   └── gates/
│       ├── _run.ts              # gate harness: takes a phase number, runs its checks
│       └── gate00.ts
├── apps/
│   ├── api/   (package.json, tsconfig.json, src/index.ts, vitest.config.ts)
│   └── web/   (created in Phase 06 — leave a placeholder package.json now)
```

## Changes required

### root `package.json`
- `"private": true`, `"workspaces": ["apps/*"]`.
- Scripts:
  ```jsonc
  {
    "scripts": {
      "db:up": "docker compose up -d db",
      "db:down": "docker compose down",
      "dev:api": "npm -w apps/api run dev",
      "dev:web": "npm -w apps/web run dev",
      "lint": "npm -w apps/api run lint && npm -w apps/web run lint",
      "typecheck": "npm -w apps/api run typecheck && npm -w apps/web run typecheck",
      "test": "npm -w apps/api run test",
      "gate": "tsx scripts/gates/_run.ts",
      "gate:00": "npm run gate -- 00",
      "gate:01": "npm run gate -- 01",
      "gate:02": "npm run gate -- 02",
      "gate:03": "npm run gate -- 03",
      "gate:04": "npm run gate -- 04",
      "gate:05": "npm run gate -- 05",
      "gate:06": "npm run gate -- 06",
      "gate:07": "npm run gate -- 07",
      "gate:08": "npm run gate -- 08",
      "gate:09": "npm run gate -- 09",
      "gate:all": "for n in 00 01 02 03 04 05 06 07 08 09; do npm run gate -- $n || exit 1; done"
    }
  }
  ```
- Dev deps at root: `typescript`, `tsx`, `vitest`, `@types/node`, `eslint`, `prettier`.

### `docker-compose.yml`
```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: erp
      POSTGRES_PASSWORD: erp
      POSTGRES_DB: erp_orchestrator
    ports: ["5432:5432"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U erp -d erp_orchestrator"]
      interval: 3s
      timeout: 3s
      retries: 20
    volumes: ["pgdata:/var/lib/postgresql/data"]
volumes: { pgdata: {} }
```
> A second logical DB `erp_external` (the simulated ERP target for the SQL adapter) is created by a Phase 01
> migration via `CREATE SCHEMA erp_external` inside the same instance — do NOT spin up a second container.

### `.env.example` (copied to `.env`)
```
DATABASE_URL=postgresql://erp:erp@localhost:5432/erp_orchestrator
API_PORT=4000
WEB_PORT=5173
DEV_USER_ID=dev-user
DEV_USER_NAME=Dev User
```

### `scripts/gates/_run.ts`
A tiny harness. It reads the phase arg, dynamically imports `gateNN.ts`, runs its exported
`async function check(): Promise<void>` (which throws on any failure), prints `GATE NN PASSED`, exits 0.
On throw it prints the message and exits 1. No interactivity.

### `scripts/gates/gate00.ts`
`check()` must assert ALL of:
- `apps/api/package.json` and root `package.json` exist and parse.
- `docker compose ps` shows `db` healthy (poll up to 60s).
- A raw `pg` connection to `DATABASE_URL` runs `SELECT 1` successfully.
- `npm -w apps/api run typecheck` exits 0 (empty `src/index.ts` that logs "api up" is fine for now).

### `apps/api` baseline
- `tsconfig.json` extends `../../tsconfig.base.json`, `strict: true`, `noUncheckedIndexedAccess: true`.
- Scripts: `dev` (`tsx watch src/index.ts`), `build` (`tsc -p .`), `typecheck` (`tsc --noEmit`),
  `lint` (`eslint src`), `test` (`vitest run`).
- Deps: `express`, `zod`, `pg`, `@prisma/client`. Dev: `prisma`, `vitest`, `supertest`, `@types/express`, `@types/pg`, `@types/supertest`.
- `src/index.ts`: minimal Express app on `API_PORT` with `GET /health → { ok: true }`. Export `createApp()` for tests.

### `apps/web/package.json` (placeholder only)
Name + empty `typecheck`/`lint`/`build` scripts that exit 0, so root scripts don't fail before Phase 06.

## Verification (gate:00)
- [ ] `npm install` at root completes; workspaces resolve.
- [ ] `npm run db:up` brings Postgres to healthy.
- [ ] `npm run gate:00` prints `GATE 00 PASSED` and exits 0.
- [ ] `GET http://localhost:4000/health` returns `{ ok: true }` when `npm run dev:api` is running.

## Done signal
Monorepo builds, Postgres is reachable, and the gate harness runs. `gate:00` is green.
