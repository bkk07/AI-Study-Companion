# Implementation Status — AI Study Companion

**Last updated:** 2026-09-15 — Phase 14 complete, awaiting `CONTINUE`
**Roadmap:** `ai-study-companion-detailed-opencode-roadmap.md` (58 phases)
**Blueprint:** `ai-study-companion-blueprint.md` v2
**Protocol:** One phase at a time, runnable after every phase, no silent next-phase start.

---

## Phase Overview

| Phase | Name | Status | Completed | Verification | Notes |
|------:|------|--------|-----------|--------------|-------|
| 01 | Repository & Blueprint Analysis | ✅ Complete | 2026-09-15 | Pass (docs-only; see § Verification below) | Blueprint frozen as contract; no product code |
| 02 | Project Skeleton & Monorepo Layout | ✅ Complete | 2026-09-15 | Pass (skeleton, no product code) | `.gitignore` + `.env.example`×2 + `README` + `.gitkeep`; verified no secrets/service drift |
| 03 | Frontend Initialization | ✅ Complete | 2026-09-15 | Pass (`npm run build` ✓ 24 modules) | Vite+React+TS+Tailwind+shadcn+Router+Axios; `src/lib/axios.ts` + routing shell; `npm run build` 260kB gzip 82.85kB |
| 04 | Backend Initialization | ✅ Complete | 2026-09-15 | Pass (pytest 3/3, health 200) | FastAPI shell `app/main.py`+`api/v1/health`+`pyproject.toml`/`requirements.txt`+`tests/test_health.py`; `/api/v1/health` 200 |
| 05 | Docker Compose Foundation | ✅ Complete | 2026-09-15 | Pass (config --quiet + dry-run) | 5 services `api/worker/web/postgres/redis`; Dockerfiles + `uploads` shared; `VITE localhost` vs `postgres/redis` service names |
| 06 | PostgreSQL Setup | ✅ Complete | 2026-09-15 | Pass (SELECT 1 via host 5433 + container) | `core/config.py`+`db/session.py`+`psycopg`; `postgres:16-alpine` 5433:5432 `SELECT 1` true |
| 07 | pgvector Setup | ✅ Complete | 2026-09-15 | Pass (vector 0.8.6 + throwaway) | `pgvector/pgvector:pg16` + `CREATE EXTENSION` + `vector(3)` test; 1536 dims |
| 08 | SQLAlchemy & DB Session Management | ✅ Complete | 2026-09-15 | Pass (6 db +3 health, DI) | `Base` + `UUIDTimestampMixin` + `SessionLocal`/`get_db` (yield/rollback/close) |
| 09 | Alembic Migrations | ✅ Complete | 2026-09-15 | Pass (upgrade head idempotent) | `alembic.ini` + `env.py` (Base.metadata + get_settings url) + `5257ffa81b36` no-op |
| 10 | User Model | ✅ Complete | 2026-09-15 | Pass (migration + round-trip) | `users` UUID email unique + schemas + `d65fb0219416` + 3 tests |
| 11 | Password Hashing | ✅ Complete | 2026-09-15 | Pass (Argon2id 6 tests) | `security.py` hash/verify + `test_security.py` 6 tests |
| 12 | JWT Authentication | ✅ Complete | 2026-09-15 | Pass (register/login+jwt 5 tests) | `jwt.py` + `auth.py` + `get_current_user` + 5 tests |
| 13 | Auth Frontend | ✅ Complete | 2026-09-15 | Pass (`npm run build` 84 modules) | `AuthContext` + axios Bearer + ProtectedRoute + Login/Register |
| 14 | Spaces | ✅ Complete | 2026-09-15 | Pass (create/list isolation) | `spaces` FK user + service + `3bfb01f2ee6b` + 4 tests |
| 15 | Projects | ⏳ Pending | — | — | — |
| 16 | Project Isolation & Authorization | ⏳ Pending | — | — | — |
| 17 | Spaces/Projects Frontend | ⏳ Pending | — | — | — |
| 18 | Materials Model | ⏳ Pending | — | — | — |
| 19 | PDF Upload | ⏳ Pending | — | — | — |
| 20 | Shared Upload Volume | ⏳ Pending | — | — | — |
| 21 | Celery + Redis | ⏳ Pending | — | — | — |
| 22 | Background Job Tracking | ⏳ Pending | — | — | — |
| 23 | PDF Text Extraction | ⏳ Pending | — | — | — |
| 24 | Learning Structure Extraction | ⏳ Pending | — | — | — |
| 25 | Topic/Subtopic/Concept Persistence | ⏳ Pending | — | — | — |
| 26 | Structure API + Frontend | ⏳ Pending | — | — | — |
| 27 | Chunking & Embeddings | ⏳ Pending | — | — | — |
| 28 | Retrieval (RAG) | ⏳ Pending | — | — | — |
| 29 | Tutor (Grounded Q&A) | ⏳ Pending | — | — | — |
| 30 | Tutor Frontend | ⏳ Pending | — | — | — |
| 31 | Confidence Capture | ⏳ Pending | — | — | — |
| 32 | Quiz Generation | ⏳ Pending | — | — | — |
| 33 | Quiz Attempt & Answer Flow | ⏳ Pending | — | — | — |
| 34 | Quiz Frontend | ⏳ Pending | — | — | — |
| 35 | Open-Ended Assessment | ⏳ Pending | — | — | — |
| 36 | Explain-It-Back | ⏳ Pending | — | — | — |
| 37 | Mastery Engine | ⏳ Pending | — | — | — |
| 38 | Confidence Engine | ⏳ Pending | — | — | — |
| 39 | Mismatch Detection | ⏳ Pending | — | — | — |
| 40 | Decision / Recommendation Engine | ⏳ Pending | — | — | — |
| 41 | Recommendations API + Frontend | ⏳ Pending | — | — | — |
| 42 | Growth Analysis | ⏳ Pending | — | — | — |
| 43 | Project Analytics | ⏳ Pending | — | — | — |
| 44 | Global/Admin Analytics | ⏳ Pending | — | — | — |
| 45 | Admin Dashboard (Read-Only) | ⏳ Pending | — | — | — |
| 46 | Activity Events & AI Usage | ⏳ Pending | — | — | — |
| 47 | Error Handling & Edge Cases | ⏳ Pending | — | — | — |
| 48 | Observability & Health | ⏳ Pending | — | — | — |
| 49 | Security Hardening | ⏳ Pending | — | — | — |
| 50 | Rate Limiting & CORS | ⏳ Pending | — | — | — |
| 51 | Frontend Polish & Navigation | ⏳ Pending | — | — | — |
| 52 | Docker Production Notes | ⏳ Pending | — | — | — |
| 53 | Testing & Coverage | ⏳ Pending | — | — | — |
| 54 | Docs & Onboarding | ⏳ Pending | — | — | — |
| 55 | Demo Seed Data | ⏳ Pending | — | — | — |
| 56 | E2E Verification | ⏳ Pending | — | — | — |
| 57 | Performance & Polish | ⏳ Pending | — | — | — |
| 58 | Release Readiness | ⏳ Pending | — | — | — |

---

## Phase 01 — Detail

**Scope:** Documentation baseline only; no framework/DB/queue/AI substitution.

**Files created in this phase:**
- `docs/00-blueprint-analysis.md` — full blueprint extraction, stack, boundaries, hard rules, ambiguity log with per-phase confirmation plan
- `docs/architecture-decisions.md` — ADRs 001–009 (stack, service/DB/security boundaries, background processing, AI wrappers, migrations, exclusions, deferrals)
- `docs/implementation-status.md` — this file
- `docs/opencode-prompts.md` — pre/post prompt log for Phase 01 (required by execution protocol)

**Out of scope for this phase (correctly deferred):**
- No `backend/` or `frontend/` scaffolding (Phase 02–05)
- No DB/migration/model code (Phases 06–10)
- No product logic, no dependency additions, no schema changes

**Verification (2026-09-15):**
- Blueprint fully read; stack/boundaries/exclusions/hard rules extracted (see `00-blueprint-analysis.md §4–9`)
- Ambiguity log recorded without invention (mastery/mismatch/recommendation/quiz formulas logged as provisional, gated on their phases — `00-blueprint-analysis.md §10`)
- `docs/` folder + git repo present; only the 4 docs files changed
- No cross-project data paths yet (no IDs, endpoints, jobs, retrieval, or UI flows to test — N/A for this phase)
- Diff inspected: no dependency, folder, schema, or service-boundary changes beyond the 4 documentation files
- `docs/implementation-status.md` updated; ready for `CONTINUE`

**Result:** ✅ Pass

**Known issues:** None. Blueprint v2 formulas for mastery/mismatch/recommendation/quiz are intentionally left as provisional pending their dedicated phases per the source roadmap.

**Next:** Await `CONTINUE` before starting Phase 02 (Project Skeleton & Monorepo Layout). Do not start Phase 02 silently.

---

## Phase 02 — Detail

**Scope:** Repository skeleton only — no framework install, no Docker, no DB, no product logic.

**Files created/changed in this phase:**
- `.gitignore` (new) — ignores `.env`/`*.env` (not `.env.example`), Python/Node/OS/editor artifacts, `uploads/` volume, `docker-compose.override.yml`
- `backend/.env.example` (new) — placeholders for `DATABASE_URL`, `JWT_SECRET` (+ algorithm/expiry), `GROQ_API_KEY`, `OPENAI_API_KEY`, `REDIS_URL`/`CELERY_*`, `UPLOAD_DIR=/data/uploads`, `API_V1_PREFIX`/`CORS_ORIGINS`
- `frontend/.env.example` (new) — `VITE_API_BASE_URL=http://localhost:8000` with Docker vs host networking comment
- `README.md` (modified, 46 B → 6287 B / 120 lines) — frozen stack, layout diagram, prerequisites, env setup, Docker Compose + local dev commands, docs index, phase note, out-of-scope + security
- `backend/.gitkeep` / `frontend/.gitkeep` (new) — keep empty dirs tracked
- `docs/opencode-prompts.md` — Phase 02 verbatim prompt recorded before edits, updated post-verification
- `docs/implementation-status.md` — this file (Phase 02 row updated)

**Out of scope for this phase (correctly deferred):**
- No `backend/app/` or `frontend/src/` scaffolding (Phases 03–04)
- No `docker-compose.yml` / Dockerfiles (Phase 05)
- No `requirements.txt` / `package.json` dependency installs
- No product code, migrations, or service logic

**Verification (2026-09-15):**
- Verified exactly `backend/` + `frontend/` + `docs/` top-level dirs — no third service (`Get-ChildItem -Directory` → `backend, docs, frontend`)
- Verified `.gitignore` ignores real `.env` (`git check-ignore backend/.env` → `.gitignore:*.env`) but not `.env.example` (no output — not ignored)
- Scanned `*.env.example` for real secrets (`sk-`/`gsk_` regex → false); confirmed placeholders (`change-me`, `your-groq-api-key-here`) present; real `backend/.env`/`frontend/.env` absent
- Verified `README.md` documents structure and how to run before feature code; 120 lines
- Diff inspection: only `.gitignore`, `README.md`, `backend/.env.example`, `frontend/.env.example`, `*.gitkeep` plus docs logs changed — no dependency, schema, or service-boundary drift
- No cross-project data paths to test (skeleton phase, N/A)
- No automated tests applicable to skeleton (nearest regression: none); structural checks suffice
- `docs/implementation-status.md` updated; protocol `CONTINUE` gate respected

**Result:** ✅ Pass

**Known issues:** None.

**Next:** Await `CONTINUE` before starting Phase 03 (Frontend Initialization). Do not start Phase 03 silently.

---

## Phase 03 — Detail

**Scope:** Browser application shell only — no business logic, no API calls beyond centralized client.

**Files created/changed in this phase:**
- `frontend/` Vite scaffold: `package.json` (react 19, vite 8, TS 6), `vite.config.ts` (alias `@`→`src` via `import.meta.dirname`), `tsconfig*.json` (`paths @/*`, `ignoreDeprecations:6.0`), `index.html`, `public/*`, `src/main.tsx` (`StrictMode`→`App`), `src/assets/*`
- Tailwind: `tailwind.config.js` (darkMode class, content `src/**/*`, shadcn theme extend + `tailwindcss-animate`), `postcss.config.js`, `src/index.css` (`@tailwind` + CSS vars `--background/...--radius` + `* { @apply border-border }`)
- shadcn/ui: `components.json` (`css:src/index.css`, `baseColor:neutral`, `cssVariables:true`), `src/lib/utils.ts` (`cn` via `clsx`+`twMerge`), deps `cva`/`clsx`/`tailwind-merge`/`lucide-react`/`tailwindcss-animate`
- Router + Axios: `src/lib/axios.ts` (central `apiClient`, `baseURL` from `VITE_API_BASE_URL`/`VITE_API_V1_PREFIX` → `http://localhost:8000/api/v1`), `src/App.tsx` ( `BrowserRouter`/`Routes` `"/"`→`Home` `*`→`NotFound`, no hard-coded URLs), deps `react-router-dom`/`axios`
- Removed boilerplate `src/App.css`; preserved `frontend/.env.example` (`VITE_API_BASE_URL`); cleaned stray `C/` scaffold dirs
- `docs/opencode-prompts.md` — Phase 03 verbatim prompt before edits, updated post-verification
- `docs/implementation-status.md` — this file (Phase 03 row updated)

**Out of scope for this phase (correctly deferred):**
- No `backend/` FastAPI scaffolding (Phase 04), no `docker-compose.yml` (Phase 05), no auth/middleware, no feature pages/components, no store/context
- No API calls outside `src/lib/axios.ts`; no hard-coded URLs in components

**Verification (2026-09-15):**
- `npm run build` → `tsc -b && vite build` succeeds: `24 modules`, `dist/index.html 0.46kB`, `index-*.css 5.72kB`, `index-*.js 260kB gzip 82.85kB`; second run confirms `__dirname`→`import.meta.dirname` warning gone
- Verified `tailwind.config.js` content globs, `index.css` `@tailwind` directives + CSS vars, `components.json` aliases match `vite.config.ts`/`tsconfig`
- Verified `src/lib/utils.ts` `cn()` and `src/lib/axios.ts` centralized client; `App.tsx` routing shell uses `react-router-dom` only
- Diff inspection: only `frontend/` scaffold + docs logs; no `backend/` changes, no `docker-compose.yml`, no third service, no secrets
- Cross-project isolation N/A (shell only, no data paths); no automated tests applicable (build is gate); top-level + `frontend/.gitignore` ignore `node_modules`/`dist`/`.env`

**Result:** ✅ Pass

**Known issues:** None.

**Next:** Await `CONTINUE` before starting Phase 04 (Backend Initialization). Do not start Phase 04 silently.

---

## Phase 04 — Detail

**Scope:** FastAPI application shell and backend layering — thin HTTP boundary + service separation, no DB/AI logic in routes.

**Files created/changed in this phase:**
- `backend/pyproject.toml` (new) — deps `fastapi`/`uvicorn[standard]`/`pydantic`/`pydantic-settings`/`sqlalchemy`/`alembic`/`argon2-cffi`/`pyjwt`/`celery`/`redis`/`pymupdf`/`httpx`; dev `pytest`/`pytest-asyncio`/`httpx`/`anyio`; `testpaths=tests`
- `backend/requirements.txt` (new) — mirror of pyproject (no secrets)
- `backend/app/main.py` (new) — `FastAPI` + `CORSMiddleware` (`localhost:5173`), `include_router(health, prefix="/api/v1")`, `GET /` root
- `backend/app/api/v1/health.py` (new) — `GET /health` → `{"status":"ok"}` thin handler
- `backend/app/{api,api/v1,core,services,models,schemas}/__init__.py` (new, empty) — package markers for layering
- `backend/tests/__init__.py` (new) + `tests/test_health.py` (new) — 3 smoke tests (`health 200`, `root 200`, `wrong path 404`)
- Removed `backend/.gitkeep` (replaced by `app/` tree)
- `docs/opencode-prompts.md` — Phase 04 verbatim prompt before edits, updated post-verification
- `docs/implementation-status.md` — this file (Phase 04 row updated)

**Out of scope for this phase (correctly deferred):**
- No `app/core/config.py`/`app/db/`/engine/session (Phases 06-08), no `alembic/` (Phase 09), no models/schemas logic (Phases 10+), no `Dockerfile`/`docker-compose.yml` (Phase 05), no frontend changes (regression `npm run build` still passes)

**Verification (2026-09-15):**
- `python -c "import app.main"` OK (`fastapi 0.135.2`); `TestClient(app).get("/api/v1/health")` → 200 `{"status":"ok"}`, `GET /` → 200, `GET /health` → 404 (prefix enforced)
- `python -m pytest tests/test_health.py -v` → 3 passed in 0.14s
- `npm run build` regression → `24 modules` `260kB gzip 82.85kB` still passes
- Diff inspection: only `backend/app/**`, `pyproject.toml`/`requirements.txt`, `tests/**`, docs; no `frontend/` changes, no `docker-compose.yml`, no DB/migration, no secrets, no third service
- Cross-project isolation N/A (shell only); architecture guard: `health.py` thin, `services/` exists empty — no DB/AI logic in route

**Result:** ✅ Pass

**Known issues:** None.

**Next:** Await `CONTINUE` before starting Phase 05 (Docker Compose Foundation). Do not start Phase 05 silently.

---

## Phase 05 — Detail

**Scope:** Five-service Compose foundation — reproducibly runnable `api`/`worker`/`web`/`postgres`/`redis`; shared volume; Docker networking rule.

**Files created/changed in this phase:**
- `docker-compose.yml` (new) — 5 services exactly; `postgres` `pgvector/pgvector:pg16` + `postgres_data` + healthcheck, `redis` `redis:7-alpine` + `redis_data`, `api` build `backend/Dockerfile` `8000:8000` env `DATABASE_URL=postgres:5432`/`REDIS_URL=redis:6379`/`UPLOAD_DIR=/data/uploads` + `uploads` volume + healthy `postgres`/`redis`, `worker` same build `command celery -A app.worker.celery_app worker` (placeholder for Phase 21) same env+volume, `web` build `frontend/Dockerfile` args `VITE_API_BASE_URL=http://localhost:8000` `5173:80` + `api` dependency; volumes `postgres_data`/`redis_data`/`uploads`
- `backend/Dockerfile` (new) — `python:3.11-slim` + `build-essential` + `pip install -r requirements.txt` + `mkdir -p /data/uploads` + `EXPOSE 8000` + `CMD uvicorn app.main:app`
- `frontend/Dockerfile` (new) — `node:20-alpine` build stage `npm ci` + `ARG VITE_API_BASE_URL` + `npm run build` → `nginx:alpine` runtime `COPY dist` + SPA `try_files` `EXPOSE 80`
- `docs/opencode-prompts.md` — Phase 05 verbatim prompt before edits, updated post-verification
- `docs/implementation-status.md` — this file (Phase 05 row updated)

**Out of scope for this phase (correctly deferred):**
- No `app/core/config.py`/`app/db/` engine, no `alembic/` (Phases 06-09), no `app/worker/celery_app.py` implementation (Phase 21 — command is placeholder until then), no `frontend/src` changes

**Verification (2026-09-15 — lightweight per request):**
- `docker compose config --quiet` → exit 0; `docker compose config --services` → `postgres, redis, api, web, worker` (5)
- Rendered `docker compose config` confirms `DATABASE_URL`/`REDIS_URL` use service names `postgres`/`redis` and `VITE_API_BASE_URL` is `http://localhost:8000` (browser localhost, containers service names)
- `uploads:/data/uploads` shared in `api` and `worker` (2 occurrences)
- `docker compose build --dry-run` → `api Built`, `web Built`, `worker Built` (validates Dockerfiles without heavy pull/build)
- `Test-Path` Dockerfiles → True; `pytest backend/tests/test_health.py -q` → 3 passed
- Diff inspection: only `docker-compose.yml` + 2 Dockerfiles + docs; no `backend/app` code drift, no third-service collapse, no secrets (dummy keys)

**Result:** ✅ Pass

**Known issues:** None. Full `docker compose build` (non-dry-run) skipped to reduce wait; dry-run + config validates same contract. `worker` celery module will be implemented in Phase 21.

**Next:** Await `CONTINUE` before starting Phase 06 (PostgreSQL Setup). Do not start Phase 06 silently.

---

## Phase 06 — Detail

**Scope:** Single relational persistence layer — Postgres wiring + SQLAlchemy DATABASE_URL + SELECT 1 verification.

**Files created/changed in this phase:**
- `backend/app/core/config.py` (new) — `Settings(BaseSettings)` covering `DATABASE_URL`/`JWT_*`/`GROQ`/`OPENAI`/`REDIS`/`CELERY`/`UPLOAD_DIR`/etc, `env_file=.env` `populate_by_name=True`, cached `get_settings()`
- `backend/app/db/__init__.py` (new) + `app/db/session.py` (new) — `get_engine()` `create_engine(settings.database_url, pool_pre_ping=True)` + `engine` singleton + `check_db_connection()` `SELECT 1`
- `backend/pyproject.toml`/`requirements.txt` (modified) — added `psycopg[binary]>=3.1.0`
- `docker-compose.yml` (modified) — `postgres` `postgres:16-alpine` (cached; Phase 07 → `pgvector`), host port `5433:5432` to avoid Windows `postgresql-x64-18` conflict on `5432`, comment added; volumes/healthcheck/env preserved

**Out of scope for this phase (correctly deferred):**
- No `app/db/base.py`/`SessionLocal`/`get_db()` (Phase 08), no `alembic/` (Phase 09), no models (Phase 10+), no second DB, no frontend changes

**Verification (2026-09-15):**
- `get_settings().database_url` default `postgres:5432` (service name) and host override `localhost:5433` both parse
- `docker compose ps` → `postgres` `healthy` + `redis` `healthy`; `docker compose exec postgres psql -c "SELECT 1"` → `1`
- `docker run --rm --network aistudycompanion_default postgres:16-alpine psql "postgresql://postgres:postgres@postgres:5432/..." -c "SELECT 1"` → `1` (service-name DNS)
- Host SQLAlchemy: `create_engine('...localhost:5433...').execute(text('SELECT 1'))` → `1`; `DATABASE_URL=...localhost:5433 python -c "check_db_connection()"` → `True`
- `pytest backend/tests/test_health.py -q` → 3 passed; `docker compose config --services` → 5 services preserved
- Diff inspection: only `core/config.py` + `db/` + `psycopg` + compose port tweak + docs; no second DB

**Result:** ✅ Pass

**Known issues:** None. Note: host port is `5433` due to Windows postgres conflict (see diagnosis in `opencode-prompts.md`); Phase 07 will switch image to `pgvector/pgvector:pg16` and retain `5433:5432`.

**Next:** Await `CONTINUE` before starting Phase 07 (pgvector Setup). Do not start Phase 07 silently.

---

## Phase 07 — Detail (compact)

**Scope:** Vector persistence inside same Postgres (pgvector), not separate DB.
**Files:** `docker-compose.yml` → `pgvector/pgvector:pg16` `5433:5432`, `docker/postgres/init-pgvector.sql` (`CREATE EXTENSION IF NOT EXISTS vector`), `docs/*`
**Verify:** `CREATE EXTENSION IF NOT EXISTS vector` → `CREATE EXTENSION`; `SELECT extversion FROM pg_extension` → `0.8.6`; throwaway `CREATE TABLE _pgvector_test (embedding vector(3))` → `INSERT [1,2,3]` → `SELECT` → `DROP` pass. 1536 dims = `text-embedding-3-small`. `docker compose config --quiet` pass, `pytest` 3 passed.
**Guard:** pgvector only, 5433 host port avoids Windows `5432` conflict (Phase 06).
**Result:** ✅ Pass | **Next:** Await `CONTINUE` before Phase 08.

---

## Phase 08 — Detail (compact)

**Scope:** One consistent SQLAlchemy session pattern (Base + SessionLocal + get_db).
**Files:** `backend/app/db/base.py` (Base Declarative + UUIDTimestampMixin uuid4/func.now), `backend/app/db/session.py` (engine singleton + SessionLocal sessionmaker + get_db yield/rollback/close), `backend/app/db/__init__.py` re-exports, `backend/tests/test_db_session.py` (6 tests), `docs/*`.
**Verify:** Base clean, mixin `id/created_at/updated_at` present; `HostSessionLocal SELECT 1` →1; `get_db()` yield→`SELECT 1`→StopIteration close; rollback on `gen.throw`; FastAPI `Depends(get_db)` `/test-db` →200; `pytest 9 passed` (6+3 health); `docker compose config --quiet` pass.
**Guard:** All DB access via centralized `SessionLocal`/`get_db`; no route-level engines.
**Result:** ✅ Pass | **Next:** Await `CONTINUE` before Phase 09.

---

## Phase 09 — Detail (compact)

**Scope:** Reproducible/reviewable schema changes via Alembic.
**Files:** `backend/alembic.ini` (placeholder url, overridden), `backend/alembic/env.py` (sys.path + Base.metadata + get_settings().database_url), `backend/alembic/script.py.mako`, `backend/alembic/versions/5257ffa81b36_initial_baseline.py` (no-op upgrade/downgrade pass), `docs/*`.
**Verify:** `DATABASE_URL=...localhost:5433 alembic upgrade head` → `5257ffa81b36` OK; `downgrade base` → `upgrade head` idempotent OK; `alembic current` → `5257ffa81b36 (head)`; `psql SELECT version_num FROM alembic_version` → `5257ffa81b36`; `python -m pytest` 9 passed; `docker compose config --quiet` pass.
**Guard:** All schema changes after this via migrations; `target_metadata = Base.metadata`; no manual DB edits.
**Result:** ✅ Pass | **Next:** Await `CONTINUE` before Phase 10.

---

## Phase 10 — Detail (compact)

**Scope:** User identity — root ownership boundary.
**Files:** `backend/app/models/user.py` (User `Base+UUIDTimestampMixin` `email unique index` `hashed_password` `is_admin` server_default false), `backend/app/schemas/user.py` (UserCreate `email`/`password` 8+ regex, UserRead `id`/`email`/`is_admin`/`created_at` from_attributes no password), `backend/alembic/env.py` (import `app.models.user`), `backend/alembic/versions/d65fb0219416_create_user_table.py` (create `users` + `ix_users_email`), `backend/tests/test_user.py` (3 tests), `docs/*`.
**Verify:** `alembic upgrade head` → `d65fb0219416`; `psql \d users` → `users_pkey` + `ix_users_email`; round-trip `User(email=...)` insert→`query`→`UserRead.model_validate` ok, `hashed_password` hidden; unique `IntegrityError`; `UserCreate` email/password validation; `pytest -q` 12 passed (3+6+3); `docker compose config --quiet` pass.
**Guard:** User ownership root — no plaintext password in read schema; all later resources inherit via user.
**Result:** ✅ Pass | **Next:** Await `CONTINUE` before Phase 11.

---

## Phase 11 — Detail (compact)

**Scope:** Centralize Argon2id hashing before auth endpoints.
**Files:** `backend/app/core/security.py` (`_ph PasswordHasher` time_cost 3 mem 65536 + `hash_password`/`verify_password`/`needs_rehash`), `backend/tests/test_security.py` (6 tests), `docs/*`.
**Verify:** `hash.startswith("$argon2id$")` true; `verify correct→True`, `wrong→False`, same pwd different hashes both verify (salt), `invalid→False`, `empty→ValueError`; `pytest -q` 18 passed (6 security +12 prior); `docker compose config --quiet` pass.
**Guard:** No plaintext/bcrypt/reversible — Argon2id only, params centralized.
**Result:** ✅ Pass | **Next:** Await `CONTINUE` before Phase 12.

---

## Phase 12 — Detail (compact)

**Scope:** Backend auth contract — JWT HS256 + register/login + get_current_user.
**Files:** `backend/app/core/jwt.py` (`create_access_token` `sub` + `exp` `iat` HS256), `backend/app/api/v1/auth.py` (`POST /register` 201 `UserRead`, `POST /login` `Token`, `GET /me` protected), `backend/app/dependencies/auth.py` (`OAuth2PasswordBearer` + `decode_access_token` + Expired/Invalid 401), `backend/app/schemas/token.py`/`auth.py`, `backend/app/main.py` (wire `auth_router`), `backend/tests/test_auth.py` (5 tests), `docs/*`.
**Verify:** `register`→201 `UserRead`; duplicate→400; `login`→200 `access_token`; `invalid creds`→401; `me` missing/malformed→401; `expired token` (timedelta -1s) →401; `pytest -q` 23 passed (5+18 prior); `docker compose config --quiet` pass.
**Guard:** No second auth mechanism — downstream must use `get_current_user`; JWT expiry via `JWT_EXPIRE_MINUTES`.
**Result:** ✅ Pass | **Next:** Await `CONTINUE` before Phase 13.

---

## Phase 13 — Detail (compact)

**Scope:** Frontend auth connection to backend JWT contract.
**Files:** `frontend/src/context/AuthContext.tsx` (AuthProvider token `localStorage` + user + login/register/logout + `/auth/me` hydrate), `frontend/src/lib/axios.ts` (Bearer request interceptor + 401 response redirect), `frontend/src/components/ProtectedRoute.tsx` (guard token→/login), `frontend/src/features/auth/Login.tsx`/`Register.tsx` (forms + error), `frontend/src/App.tsx` (wrap AuthProvider + routes /login /register /dashboard protected), `docs/*`.
**Verify:** `npm run build` → `84 modules` `css 8.18kB` `js 318.90kB gzip 102.82kB` success; `pytest -q` 23 passed; manual `register→login→me→dashboard` protected flow works, 401 auto-clears `localStorage` + redirects.
**Guard:** No per-page token handling — centralized `apiClient` + `AuthContext` only.
**Result:** ✅ Pass | **Next:** Await `CONTINUE` before Phase 14.

---

## Phase 14 — Detail (compact)

**Scope:** First user-owned container — Space.
**Files:** `backend/app/models/space.py` (Space `user_id` FK→users cascade `name` 255), `backend/app/schemas/space.py` (SpaceCreate/SpaceRead), `backend/app/services/space_service.py` (create/list/get + `name.strip()`), `backend/app/api/v1/spaces.py` (`POST` 201 + `GET` list own via `get_current_user`), `backend/app/main.py` (wire), `backend/alembic/env.py` (import space), `backend/alembic/versions/3bfb01f2ee6b_create_spaces_table.py` (create `spaces` + `ix_spaces_user_id`), `backend/tests/test_spaces.py` (4 tests), `docs/*`.
**Verify:** `alembic upgrade head` → `3bfb01f2ee6b`; `\d spaces` → `spaces_pkey` + `ix_spaces_user_id` + FK cascade; `401` without token; `create→201` + `list own`; isolation `A Space` not visible to `B`; validation `400/422`; `pytest -q` 27 passed (4+23 prior); `docker compose config --quiet` pass.
**Guard:** No global/shared spaces — ownership via `user_id`; service owns validation.
**Result:** ✅ Pass | **Next:** Await `CONTINUE` before Phase 15.

---

*This file is updated at the end of every phase with what changed, verification run, pass/fail, known issues, and whether the phase is complete.*
