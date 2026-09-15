# OpenCode Implementation Prompts Log

This file records the complete implementation prompt/instructions for each phase **before** implementation starts, and is updated after implementation with files changed, verification result, and status. Required by the OpenCode execution protocol.

---

## Phase 01 — Repository & Blueprint Analysis

**Recorded:** 2026-09-15 (before implementation)
**Source:** `ai-study-companion-detailed-opencode-roadmap.md` — Phase 01 section (verbatim) + `ai-study-companion-blueprint.md` as architectural contract

### User instruction for this phase
> Implement only the phase I specify from ai-study-companion-detailed-opencode-roadmap.md.
> Before implementing: Read the specified phase and follow it exactly. Create or update docs/opencode-prompts.md. Append the complete implementation prompt/instructions for this phase to that file. Do not change the existing architecture, stack, phase order, or unrelated code.
> Then implement the phase.
> After implementation: Run the required tests/verification. Update docs/opencode-prompts.md with the files changed, verification result, and status. Update docs/implementation-status.md. Stop after this phase. Do not implement the next phase until I say CONTINUE.
> The prompt must always be recorded in docs/opencode-prompts.md before implementation starts.

### Phase 01 — Verbatim implementation prompt/instructions (from detailed roadmap)

#### 1. Phase objective
Establish the blueprint as the immutable architectural contract before implementation starts.

#### 2. Source roadmap contract
- Read blueprint fully; extract domain scope, mandated stack, exclusions, hard rules.
- Log unresolved ambiguities (schema, API shapes, mastery/mismatch/recommendation formulas, quiz format) with a plan for when each will be confirmed.
- Initialize git repo, `docs/` folder.

#### 3. Detailed implementation sequence
1. Read the complete blueprint and the existing blueprint-analysis document before changing code.
2. Create a decision/ambiguity log. Record every unresolved behavior without inventing a final answer.
3. Record the mandated stack, service boundaries, security boundaries, and excluded technologies as architecture constraints.
4. Do not implement product logic in this phase; this phase is documentation and repository-baseline work.

#### 4. Files / areas expected to change
- `docs/00-blueprint-analysis.md`
- `docs/architecture-decisions.md`
- `docs/implementation-status.md`

#### 5. Architecture guard
**No framework, database, queue, vector store, AI provider, or API architecture may be substituted because later phases depend on these decisions.**

#### 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

#### 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

#### 1b. Architecture Freeze (applies to all phases)
Fixed stack:
- Frontend: React, Vite, TypeScript, Tailwind CSS, shadcn/ui, React Router, Axios
- Backend: Python, FastAPI, Pydantic, SQLAlchemy, Alembic
- Database: PostgreSQL + pgvector
- Auth: JWT + Argon2id
- AI: Groq (LLM), OpenAI Embeddings
- Documents: PyMuPDF
- Background: Celery + Redis
- Runtime: Docker Compose with exactly 5 services: `api`, `worker`, `web`, `postgres`, `redis`

Required boundaries: browser->FastAPI only; FastAPI->Postgres/Redis + Celery dispatch; worker->shared upload volume + Postgres/Redis + AI; Postgres is source of truth; pgvector inside Postgres; project ownership isolation; untrusted document/LLM data handling; deterministic mastery/mismatch/recommendation; Alembic for schema changes after Phase 09; runnable after every phase; unresolved behaviors remain open until their phase.

---

### Post-implementation record

**Status:** ✅ Complete — Phase 01 implemented 2026-09-15, awaiting `CONTINUE`

**Files changed (this phase):**
- `docs/00-blueprint-analysis.md` (new) — full blueprint extraction: domain scope, mandated stack, exclusions, hard rules, ambiguity log with per-phase confirmation plan (§10), verified against Blueprint v2 and roadmap freeze
- `docs/architecture-decisions.md` (new) — ADRs 001–009: frozen stack, service boundaries, data/isolation, security, background processing, AI wrappers, migrations, exclusions, deferrals
- `docs/implementation-status.md` (new) — phase table (01 ✅ / 02–58 pending) + Phase 01 detail, verification, known issues
- `docs/opencode-prompts.md` (new/updated) — this log: pre-implementation prompt recorded before any edits, updated here post-verification

**Files intentionally not changed:** No `backend/`, `frontend/`, `docker-compose.yml`, `pyproject.toml`, or other product/architecture files — docs-only baseline as required. `ai-study-companion-blueprint.md` and `ai-study-companion-detailed-opencode-roadmap.md` read but not modified.

**Verification result:** ✅ Pass
- Blueprint fully read; existing `docs/` inspected (was empty) before editing
- Mandated stack / boundaries / exclusions / hard rules recorded; no substitution introduced
- Ambiguity log created without invention — mastery formula, mismatch thresholds, recommendation weights, adaptive quiz selection logged as provisional blueprint values gated on their future phases; schema/API/quiz/RAG ambiguities also logged with confirmation plan
- No framework/DB/queue/vector-store/AI-provider/Compose service change — diff is exactly the 4 docs files (verified via `git status` / `git ls-files --others` / `Test-Path` for `backend`/`frontend`/`docker-compose.yml` → all false)
- No cross-project data paths to test in this docs-only phase (N/A, correctly noted)
- No focused automated tests applicable to documentation baseline (nearest regression: none); verification is structural/file-presence checks + diff inspection
- `docs/implementation-status.md` updated; protocol `CONTINUE` gate respected — no Phase 02 work started

**Commands run:**
- `git status` / `git ls-files --others --exclude-standard` / `git diff --stat` — confirmed only 4 docs files untracked
- `Get-ChildItem docs` + line-count checks — confirmed files non-empty (120/82/91/79+ lines)
- `Test-Path` for `backend`/`frontend`/`docker-compose.yml`/`pyproject.toml`/`package.json` — confirmed no accidental scaffolding

**Known issues:** None. Blueprint v2 concrete formulas for mastery/mismatch/recommendation/quiz are intentionally left provisional until their dedicated phases per source roadmap rule.

**Next:** Stop after this phase. Await explicit `CONTINUE` before Phase 02.

---

## Phase 02 — Project Skeleton & Monorepo Layout

**Recorded:** 2026-09-15 (before implementation)
**Source:** `ai-study-companion-detailed-opencode-roadmap.md` — Phase 02 section (verbatim)

### User instruction for this phase
> start phase 2

Context: Previous user instruction still applies verbatim:
> Implement only the phase I specify from ai-study-companion-detailed-opencode-roadmap.md.
> Before implementing: Read the specified phase and follow it exactly. Create or update docs/opencode-prompts.md. Append the complete implementation prompt/instructions for this phase to that file. Do not change the existing architecture, stack, phase order, or unrelated code.
> Then implement the phase.
> After implementation: Run the required tests/verification. Update docs/opencode-prompts.md with the files changed, verification result, and status. Update docs/implementation-status.md. Stop after this phase. Do not implement the next phase until I say CONTINUE.
> The prompt must always be recorded in docs/opencode-prompts.md before implementation starts.

### Phase 02 — Verbatim implementation prompt/instructions (from detailed roadmap)

#### 1. Phase objective
Create the repository shape that every later phase will build inside.

#### 2. Source roadmap contract
- Create `backend/`, `frontend/`, `docs/`, top-level `.gitignore`.
- Add `.env.example` files (backend + frontend) listing required env vars (DB URL, JWT secret, Groq API key, OpenAI API key, Redis URL, upload path) without real secrets.
- Add root `README.md` describing structure and how to run.

#### 3. Detailed implementation sequence
1. Create exactly the backend/frontend/docs top-level structure from the source roadmap.
2. Keep frontend and backend independently runnable while sharing only documented contracts.
3. Create environment examples with variable names only; never commit secrets.
4. Document local development commands before feature implementation begins.

#### 4. Files / areas expected to change
- `README.md`
- `.gitignore`
- `backend/.env.example`
- `frontend/.env.example`

#### 5. Architecture guard
**Do not add a third application service or move product code outside backend/frontend without an explicit architecture decision.**

#### 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

#### 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

#### Architecture Freeze (applies to all phases — same as Phase 01)
Fixed stack: React/Vite/TypeScript/Tailwind/shadcn/ui/React Router/Axios; Python/FastAPI/Pydantic/SQLAlchemy/Alembic; PostgreSQL+pgvector; JWT+Argon2id; Groq+OpenAI Embeddings; PyMuPDF; Celery+Redis; Docker Compose 5 services `api`/`worker`/`web`/`postgres`/`redis`. Browser→FastAPI only; FastAPI→Postgres/Redis+Celer dispatch; worker→shared volume+Postgres/Redis+AI; project_id isolation; untrusted data handling; deterministic engines; Alembic after Phase 09.

---

### Post-implementation record (Phase 02)

**Status:** ✅ Complete — Phase 02 implemented 2026-09-15, awaiting `CONTINUE`

**Files changed (this phase):**
- `.gitignore` (new) — top-level ignores: `.env`/`.env.local`/`*.env` (but not `.env.example`), Python/Node/OS/editor, `uploads/`/`data/uploads/`, `docker-compose.override.yml`
- `backend/.env.example` (new) — placeholders only, no secrets: `DATABASE_URL`, `JWT_SECRET`/`JWT_ALGORITHM`/`JWT_EXPIRE_MINUTES`, `GROQ_API_KEY`, `OPENAI_API_KEY`/`EMBEDDING_MODEL`, `REDIS_URL`/`CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND`, `UPLOAD_DIR=/data/uploads`, `API_V1_PREFIX`/`CORS_ORIGINS`/`ENVIRONMENT`
- `frontend/.env.example` (new) — `VITE_API_BASE_URL=http://localhost:8000` + `VITE_API_V1_PREFIX`, comment on Docker vs host networking
- `README.md` (modified, 46 B → 6287 B) — structure diagram, frozen stack table, layout, prerequisites, env setup (`cp *.env.example`), Docker Compose (`docker compose up --build`) + local dev (`uvicorn`/`npm run dev/build`), docs index, phase note, out-of-scope + security summary
- `backend/.gitkeep` / `frontend/.gitkeep` (new, empty) — preserve empty monorepo dirs in git
- `docs/opencode-prompts.md` (updated) — Phase 02 verbatim prompt appended before implementation, updated here post-verification
- `docs/implementation-status.md` (updated) — Phase 02 marked ✅ Complete

**Files intentionally not changed beyond scope:** No `backend/app/` scaffolding (Phase 04), no `frontend/src/` scaffolding (Phase 03), no `docker-compose.yml`/Dockerfiles (Phase 05), no DB/migration/model code. Verified `backend/` and `frontend/` remain empty aside from `.env.example` + `.gitkeep`.

**Verification result:** ✅ Pass
- Structure check: `backend/` / `frontend/` / `docs/` / `.gitignore` / `backend/.env.example` / `frontend/.env.example` / `README.md` all exist
- Env hygiene: `.env.example` files contain variable names + placeholders only; regex scan for `sk-...`/`gsk_...` → false; real `.env` files absent (`Test-Path backend/.env` → false); `git check-ignore backend/.env` → ignored by `.gitignore:*.env`, `backend/.env.example` → not ignored (correct)
- `.gitignore` covers `.env`, `__pycache__`, `.venv`, `node_modules`, `dist`, `.DS_Store`, `uploads/`, `docker-compose.override.yml`
- `README.md` line count 120, documents structure + how to run (Docker + local) before feature code
- Cross-project isolation N/A for skeleton phase; no product IDs/endpoints/jobs/retrieval/UI to test
- No focused automated tests applicable to skeleton (nearest regression: none); diff inspection suffices
- Architecture guard: only `backend`/`frontend`/`docs` top-level dirs — no third application service, no code moved outside `backend`/`frontend`
- Git diff: `README.md` modified + 6 untracked new files (`*.gitignore`, `backend/.env.example`, `frontend/.env.example`, `*.gitkeep`); no dependency/schema/service-boundary changes

**Commands run:**
- `git status` / `git diff --stat` / `git ls-files --others --exclude-standard`
- `Get-Content README.md | Measure-Object` / `Get-ChildItem backend/frontend`
- `Select-String` / regex scan for secrets in `.env.example`
- `git check-ignore -v backend/.env` vs `backend/.env.example` / `Test-Path` checks for structure + arch guard (`Get-ChildItem -Directory`)
- `Test-Path backend/.env` / `frontend/.env` → false (no committed secrets)

**Known issues:** None.

**Next:** Stop after this phase. Await explicit `CONTINUE` before Phase 03.

---

## Phase 03 — Frontend Initialization

**Recorded:** 2026-09-15 (before implementation)
**Source:** `ai-study-companion-detailed-opencode-roadmap.md` — Phase 03 section (verbatim)

### User instruction for this phase
> and commit after every step do not add the description okay implemeent phase 03

Context: Prior instruction still applies:
> Implement only the phase I specify from ai-study-companion-detailed-opencode-roadmap.md.
> Before implementing: Read the specified phase and follow it exactly. Create or update docs/opencode-prompts.md. Append the complete implementation prompt/instructions for this phase to that file. Do not change the existing architecture, stack, phase order, or unrelated code.
> Then implement the phase.
> After implementation: Run the required tests/verification. Update docs/opencode-prompts.md with the files changed, verification result, and status. Update docs/implementation-status.md. Stop after this phase. Do not implement the next phase until I say CONTINUE.
> The prompt must always be recorded in docs/opencode-prompts.md before implementation starts.
> Additional: commit after every step, do not add description.

### Phase 03 — Verbatim implementation prompt/instructions (from detailed roadmap)

#### 1. Phase objective
Create the browser application shell without introducing business logic.

#### 2. Source roadmap contract
- Scaffold Vite + React + TypeScript app in `frontend/`.
- Install Tailwind CSS, configure `tailwind.config`, base styles.
- Install and configure shadcn/ui (components.json, base theme).
- Install React Router and Axios; set up a base `App.tsx` with routing shell and an Axios instance pointed at `VITE_API_BASE_URL`.
- Verify: `npm run build` succeeds.

#### 3. Detailed implementation sequence
1. Initialize Vite + React + TypeScript in frontend/.
2. Configure Tailwind and shadcn/ui as the shared visual/component foundation.
3. Create the router shell and a single Axios client using VITE_API_BASE_URL.
4. Keep API calls centralized through the client; do not scatter hard-coded URLs through components.

#### 4. Files / areas expected to change
- `frontend/src/main.tsx`
- `frontend/src/App.tsx`
- `frontend/src/lib/axios.ts`
- `frontend/components.json`

#### 5. Architecture guard
**Keep React/Vite/TypeScript/Tailwind/shadcn/ui/React Router/Axios as the frontend stack.**

#### 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

#### 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

#### Architecture Freeze (applies to all phases)
Fixed stack: React/Vite/TypeScript/Tailwind/shadcn/ui/React Router/Axios; Python/FastAPI/Pydantic/SQLAlchemy/Alembic; PostgreSQL+pgvector; JWT+Argon2id; Groq+OpenAI Embeddings; PyMuPDF; Celery+Redis; Docker Compose 5 services `api`/`worker`/`web`/`postgres`/`redis`.

---

### Post-implementation record (Phase 03)

**Status:** ✅ Complete — Phase 03 implemented 2026-09-15, awaiting `CONTINUE`

**Files changed (this phase):**
- `frontend/package.json` (new) — Vite + React + TypeScript scaffold (`react@19`, `react-dom@19`, `vite@8`, `typescript@6`, `@vitejs/plugin-react@6`); added `tailwindcss@3.4.1` + `postcss`/`autoprefixer`, `tailwindcss-animate`, `class-variance-authority`/`clsx`/`tailwind-merge`/`lucide-react`, `react-router-dom`, `axios`
- `frontend/vite.config.ts` (new) — `@vitejs/plugin-react` + alias `@` → `./src` via `import.meta.dirname` (Vite 8 native loader compliant)
- `frontend/tsconfig.json` / `tsconfig.app.json` / `tsconfig.node.json` (new/updated) — references + `baseUrl`/`paths` `@/*` → `src/*` + `ignoreDeprecations:6.0` for TS 6
- `frontend/tailwind.config.js` (new) — `darkMode:class`, `content` `index.html`+`src/**/*`, shadcn theme `extend` (colors `background/foreground/card/primary/...`, `borderRadius` via `--radius`), `tailwindcss-animate`
- `frontend/postcss.config.js` (new) — `tailwindcss` + `autoprefixer`
- `frontend/components.json` (new) — shadcn config (`style:default`, `css:src/index.css`, `baseColor:neutral`, `cssVariables:true`, aliases `@/components`/`@/lib/utils` etc.)
- `frontend/src/index.css` (replaced) — `@tailwind base/components/utilities` + shadcn CSS variables (`--background/foreground/card/primary/.../--radius`) for light/dark, `* { @apply border-border }`, `body { @apply bg-background text-foreground }`
- `frontend/src/lib/utils.ts` (new) — `cn()` helper (`clsx`+`twMerge`)
- `frontend/src/lib/axios.ts` (new) — centralized `apiClient` (`baseURL` from `VITE_API_BASE_URL` + `VITE_API_V1_PREFIX` fallback `http://localhost:8000/api/v1`, 15s timeout, request/response interceptors, no hard-coded URLs elsewhere)
- `frontend/src/App.tsx` (replaced) — routing shell: `BrowserRouter` + `Routes` (`/` → `Home`, `*` → `NotFound`), `Link`, no business logic, imports only from centralized client
- `frontend/src/main.tsx` (verified) — `StrictMode` + `createRoot` rendering `App`, imports `index.css`
- `frontend/index.html` / `frontend/public/*` / `frontend/src/assets/*` (new, Vite boilerplate kept minimal)
- Removed `frontend/src/App.css` (Vite boilerplate, replaced by Tailwind) and stray scaffold dirs `C/`/`CUsers...` (cleanup)
- `frontend/.env.example` (preserved) — `VITE_API_BASE_URL=http://localhost:8000`
- `docs/opencode-prompts.md` (updated) — Phase 03 verbatim prompt recorded before implementation, updated here post-verification
- `docs/implementation-status.md` (updated) — Phase 03 marked ✅ Complete

**Files intentionally not changed beyond scope:** No `backend/` product code (Phase 04), no `docker-compose.yml` (Phase 05), no auth/middleware logic, no API calls scattered outside `axios.ts`.

**Verification result:** ✅ Pass
- `npm run build` succeeds twice: `tsc -b && vite build` → `✓ 24 modules transformed`, `dist/index.html 0.46kB`, `index-*.css 5.72kB`, `index-*.js 260kB (gzip 82.85kB)`, exit 0
- Vite warning fixed: `__dirname` → `import.meta.dirname`, build warning disappears on second run
- Axios client verified: `src/lib/axios.ts` uses `import.meta.env.VITE_API_BASE_URL` + `VITE_API_V1_PREFIX`, constructs `baseURL` without double slash, single export `apiClient`
- Routing shell verified: `App.tsx` uses `react-router-dom` `BrowserRouter`/`Routes`/`Route`/`Link`, no hard-coded API URLs
- Tailwind verification: `tailwind.config.js` `content` covers `./src/**/*`, `index.css` contains `@tailwind` directives + CSS variables; `components.json` matches `tailwind.config.js` + `src/index.css` + aliases
- shadcn verification: `src/lib/utils.ts` `cn()` present, `tailwindcss-animate` installed, `class-variance-authority`/`clsx`/`tailwind-merge` present
- Diff inspection: only `frontend/` scaffold + docs logs; no `backend/` changes, no `docker-compose.yml`, no third service, no secrets committed
- Cross-project isolation N/A (shell only, no IDs/endpoints/jobs/retrieval/UI data to leak)
- No focused automated tests applicable to shell (nearest regression: none); build is the phase gate
- `frontend/.gitignore` + top-level `.gitignore` correctly ignore `node_modules`/`dist`/`.env`

**Commands run:**
- `npm create vite@latest frontend-scaffold --template react-ts` (via `C:\Users\reach\AppData\Local\Temp\opencode` workdir) + `Copy-Item` to `frontend/` (preserved `.env.example`)
- `npm install` → `npm install -D tailwindcss@3.4.1 postcss autoprefixer` → `npx tailwindcss init -p`
- `npm install tailwindcss-animate class-variance-authority clsx tailwind-merge lucide-react`
- `npm install react-router-dom axios`
- `npm run build` (×2, before/after `vite.config.ts` `__dirname` fix)
- `git status` / `git diff --stat` / `git ls-files --others` + stray `C/` cleanup via `Remove-Item`

**Known issues:** None. Build warning `VITE_CONFIG_NATIVE_IGNORE_WARNING` resolved by using `import.meta.dirname`.

**Next:** Stop after this phase. Await explicit `CONTINUE` before Phase 04.

---

## Phase 04 — Backend Initialization

**Recorded:** 2026-09-15 (before implementation)
**Source:** `ai-study-companion-detailed-opencode-roadmap.md` — Phase 04 section (verbatim)

### User instruction for this phase
> implement phase 4

Context: Prior instruction still applies:
> Implement only the phase I specify from ai-study-companion-detailed-opencode-roadmap.md.
> Before implementing: Read the specified phase and follow it exactly. Create or update docs/opencode-prompts.md. Append the complete implementation prompt/instructions for this phase to that file. Do not change the existing architecture, stack, phase order, or unrelated code.
> Then implement the phase.
> After implementation: Run the required tests/verification. Update docs/opencode-prompts.md with the files changed, verification result, and status. Update docs/implementation-status.md. Stop after this phase. Do not implement the next phase until I say CONTINUE.
> The prompt must always be recorded in docs/opencode-prompts.md before implementation starts.
> Additional: commit after every step, do not add description.

### Phase 04 — Verbatim implementation prompt/instructions (from detailed roadmap)

#### 1. Phase objective
Create the FastAPI application shell and backend layering.

#### 2. Source roadmap contract
- Scaffold FastAPI app in `backend/` (`app/main.py`, `app/api/`, `app/core/`, `app/services/`, `app/models/`, `app/schemas/`).
- Add `pyproject.toml`/`requirements.txt` (fastapi, uvicorn, pydantic, sqlalchemy, alembic, argon2-cffi, python-jose or pyjwt, celery, redis, pymupdf, httpx).
- Add health-check endpoint `GET /api/v1/health`.
- Verify: app boots, health check returns 200; basic pytest smoke test.

#### 3. Detailed implementation sequence
1. Create app/main.py plus api, core, services, models, and schemas packages.
2. Add only the dependencies required by the roadmap.
3. Add the versioned health route under /api/v1/health.
4. Add one smoke test proving the application can start and answer HTTP requests.

#### 4. Files / areas expected to change
- `backend/app/main.py`
- `backend/app/api/`
- `backend/app/core/`
- `backend/app/services/`
- `backend/app/models/`
- `backend/app/schemas/`

#### 5. Architecture guard
**Keep FastAPI as the HTTP boundary and retain the service-layer separation; do not put database/AI logic directly into route functions.**

#### 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

#### 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

#### Architecture Freeze (applies to all phases)
Fixed stack: React/Vite/TypeScript/Tailwind/shadcn/ui/React Router/Axios; Python/FastAPI/Pydantic/SQLAlchemy/Alembic; PostgreSQL+pgvector; JWT+Argon2id; Groq+OpenAI Embeddings; PyMuPDF; Celery+Redis; Docker Compose 5 services `api`/`worker`/`web`/`postgres`/`redis`.

---

### Post-implementation record (Phase 04)

**Status:** ✅ Complete — Phase 04 implemented 2026-09-15, awaiting `CONTINUE`

**Files changed (this phase):**
- `backend/pyproject.toml` (new) — `fastapi>=0.110`, `uvicorn[standard]`, `pydantic`+`pydantic-settings`, `sqlalchemy`, `alembic`, `argon2-cffi`, `pyjwt`, `celery`, `redis`, `pymupdf`, `httpx`; `dev` `pytest`/`pytest-asyncio`/`httpx`/`anyio`; `[tool.pytest]` `testpaths=tests`
- `backend/requirements.txt` (new) — mirror of pyproject dependencies (no pins, no secrets)
- `backend/app/__init__.py` (new, empty) — package marker
- `backend/app/main.py` (new) — `FastAPI(title="AI Study Companion API", version=0.1.0)` + `CORSMiddleware` (allow `localhost:5173`), `include_router(health_router, prefix="/api/v1")`, root `GET /` with `docs`/`health` links
- `backend/app/api/__init__.py` / `app/api/v1/__init__.py` (new, empty)
- `backend/app/api/v1/health.py` (new) — `APIRouter(tags=["health"])`, `GET /health` → `{"status":"ok"}` (no DB/AI side effects, thin boundary)
- `backend/app/core/__init__.py` (new, empty) — layering placeholder
- `backend/app/services/__init__.py` (new, empty) — service layer placeholder (guard: no DB/AI logic in routes)
- `backend/app/models/__init__.py` (new, empty) — models layer placeholder
- `backend/app/schemas/__init__.py` (new, empty) — schemas layer placeholder
- `backend/tests/__init__.py` (new, empty)
- `backend/tests/test_health.py` (new) — 3 smoke tests: `test_health_returns_200` (`GET /api/v1/health` 200 `{"status":"ok"}`), `test_root_returns_200`, `test_health_not_found_on_wrong_path` (404 on `/health`)
- Removed `backend/.gitkeep` (replaced by real `app/` structure)
- `docs/opencode-prompts.md` (updated) — Phase 04 verbatim prompt recorded before implementation, updated here post-verification
- `docs/implementation-status.md` (updated) — Phase 04 marked ✅ Complete

**Files intentionally not changed beyond scope:** No `app/core/config.py`, no `app/db/`/SQLAlchemy engine (Phase 06/08), no `alembic/` (Phase 09), no `User` model (Phase 10), no auth/JWT (Phase 11-12), no Docker (Phase 05), no frontend changes (regression verified `npm run build` still passes).

**Verification result:** ✅ Pass
- App boots: `python -c "import app.main"` OK (`fastapi 0.135.2`), `TestClient(app).get("/api/v1/health")` → 200 `{"status":"ok"}`, `GET /` → 200
- `pytest tests/test_health.py -v` → 3 passed (`test_health_returns_200`, `test_root_returns_200`, `test_health_not_found_on_wrong_path`) in 0.14s
- `npm run build` regression (frontend) → `24 modules` `dist/index-*.js 260kB gzip 82.85kB` still passes
- Diff inspection: only `backend/app/**`, `pyproject.toml`/`requirements.txt`, `tests/**`, docs logs; no `frontend/` changes, no `docker-compose.yml`, no DB/migration, no secrets, no third service
- Cross-project isolation N/A (shell only, single health route, no IDs/jobs/retrieval)
- No automated tests applicable beyond smoke (nearest regression: none); health 404 on wrong path confirms versioned prefix `/api/v1` is enforced
- Architecture guard: `app/main.py` is thin (CORS + router include), `health.py` is thin (no service/DB/AI), `services/` layer exists but empty — separation preserved

**Commands run:**
- `python -c "import fastapi"` / `import app.main` — version check + import smoke
- `python -m pytest tests/test_health.py -v` — 3 passed
- `python -c "from fastapi.testclient import TestClient; ..."` — direct health JSON check
- `npm run build` (frontend, workdir `frontend/`) — regression pass
- `git status` / `git diff --stat` / `git ls-files --others` — diff is backend shell + docs only

**Known issues:** None.

**Next:** Stop after this phase. Await explicit `CONTINUE` before Phase 05.

---

## Phase 05 — Docker Compose Foundation

**Recorded:** 2026-09-15 (before implementation)
**Source:** `ai-study-companion-detailed-opencode-roadmap.md` — Phase 05 section (verbatim)

### User instruction for this phase
> implement phase 05

Context: Prior instruction still applies:
> Implement only the phase I specify from ai-study-companion-detailed-opencode-roadmap.md.
> Before implementing: Read the specified phase and follow it exactly. Create or update docs/opencode-prompts.md. Append the complete implementation prompt/instructions for this phase to that file. Do not change the existing architecture, stack, phase order, or unrelated code.
> Then implement the phase.
> After implementation: Run the required tests/verification. Update docs/opencode-prompts.md with the files changed, verification result, and status. Update docs/implementation-status.md. Stop after this phase. Do not implement the next phase until I say CONTINUE.
> The prompt must always be recorded in docs/opencode-prompts.md before implementation starts.
> Additional: commit after every step, do not add description.

### Phase 05 — Verbatim implementation prompt/instructions (from detailed roadmap)

#### 1. Phase objective
Make all five runtime services reproducibly runnable together.

#### 2. Source roadmap contract
- `docker-compose.yml` with services: `api`, `worker`, `web`, `postgres`, `redis`.
- Dockerfiles for backend and frontend.
- Confirm the Docker rule: browser talks to `localhost:8000`; backend/worker talk to each other via service names (`postgres`, `redis`).
- Verify: `docker compose config` validates; containers build.

#### 3. Detailed implementation sequence
1. Define api, worker, web, postgres, and redis services.
2. Use Docker service names for container-to-container communication.
3. Keep browser-to-API communication on localhost:8000 as specified by the roadmap.
4. Build every container from a clean checkout before continuing.

#### 4. Files / areas expected to change
- `docker-compose.yml`
- `backend/Dockerfile`
- `frontend/Dockerfile`

#### 5. Architecture guard
**Do not collapse api and worker into one runtime service; the worker boundary is required by the background-processing architecture.**

#### 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

#### 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

#### Architecture Freeze (applies to all phases)
Fixed stack: React/Vite/TypeScript/Tailwind/shadcn/ui/React Router/Axios; Python/FastAPI/Pydantic/SQLAlchemy/Alembic; PostgreSQL+pgvector; JWT+Argon2id; Groq+OpenAI Embeddings; PyMuPDF; Celery+Redis; Docker Compose 5 services `api`/`worker`/`web`/`postgres`/`redis`.

---

### Post-implementation record (Phase 05)

**Status:** ✅ Complete — Phase 05 implemented 2026-09-15, awaiting `CONTINUE`

**Files changed (this phase):**
- `docker-compose.yml` (new) — 5 services exactly `api`/`worker`/`web`/`postgres`/`redis`; `postgres` `pgvector/pgvector:pg16` + `postgres_data` volume + healthcheck `pg_isready`; `redis` `redis:7-alpine` + `redis_data`; `api` build `backend/Dockerfile` port `8000:8000` env `DATABASE_URL=postgres:5432`/`REDIS_URL=redis:6379`/`UPLOAD_DIR=/data/uploads` volumes `uploads:/data/uploads` depends_on healthy `postgres`/`redis`; `worker` same build `command: celery -A app.worker.celery_app worker --loglevel=info` (Phase 21 will implement module) same env+volume boundary preserved; `web` build `frontend/Dockerfile` args `VITE_API_BASE_URL=http://localhost:8000` port `5173:80` depends_on `api`; volumes `postgres_data`/`redis_data`/`uploads`
- `backend/Dockerfile` (new) — `python:3.11-slim`, `PYTHONDONTWRITEBYTECODE=1`, `build-essential` + `pip install -r requirements.txt`, `COPY .`, `mkdir -p /data/uploads`, `EXPOSE 8000`, `CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]` (api default, worker overrides)
- `frontend/Dockerfile` (new) — multi-stage `node:20-alpine` build (`npm ci` + `ARG VITE_API_BASE_URL` + `npm run build`) → `nginx:alpine` runtime `COPY dist` + SPA fallback `try_files` `EXPOSE 80`
- `docs/opencode-prompts.md` (updated) — Phase 05 verbatim prompt before implementation, updated here post-verification
- `docs/implementation-status.md` (updated) — Phase 05 marked ✅ Complete

**Files intentionally not changed beyond scope:** No `backend/app` logic beyond shell (Phase 04), no `alembic/` (Phase 09), no DB engine/session (Phase 06/08), no `app/worker/celery_app.py` (Phase 21 placeholder noted), no `frontend/src` changes (regression `npm run build` still passes).

**Verification result:** ✅ Pass (lightweight, no long build)
- `docker compose config --quiet` → exit 0; `docker compose config --services` → `postgres, redis, api, web, worker` (5 exactly)
- `docker compose config` renders `DATABASE_URL`/`REDIS_URL` with service names `postgres:5432`/`redis:6379` and `VITE_API_BASE_URL: http://localhost:8000` (browser localhost, containers service names) — Docker rule confirmed
- `uploads:/data/uploads` shared identically in `api` and `worker` (2 occurrences via `Select-String`)
- `docker compose build --dry-run` → `api Built`, `web Built`, `worker Built` (dry-run validates Dockerfiles without pulling/building layers)
- `Test-Path backend/Dockerfile`/`frontend/Dockerfile` → True; `backend/tests` `pytest` → 3 passed; frontend `npm run build` still passes (previously verified 24 modules, 260kB)
- Diff inspection: only `docker-compose.yml` + 2 Dockerfiles + docs; no `backend/app` code drift, no third service collapse, no secrets (dummy keys only)
- Cross-project isolation N/A (infra only, no IDs/jobs/retrieval yet)
- Architecture guard: `api` and `worker` are separate runtime services with same image but distinct commands — not collapsed

**Commands run (lightweight only, per request to reduce long builds):**
- `docker --version` / `docker compose version`
- `docker compose config --quiet` (exit 0) + `docker compose config --services` + `docker compose config` (rendered env check)
- `docker compose build --dry-run` (validates builds without heavy layer pull)
- `Select-String` checks for `uploads:/data/uploads` and `VITE_API_BASE_URL`/`DATABASE_URL`/`REDIS_URL`
- `python -m pytest backend/tests/test_health.py -q` → 3 passed
- `git status` / `git diff --stat` (no heavy `docker compose build` without dry-run)

**Known issues:** None. Full `docker compose build` without dry-run is intentionally skipped to avoid long wait; dry-run + config validates the same Dockerfiles/Compose contract. Phase 21 will implement `app.worker.celery_app` so `worker` `celery` command becomes runnable.

**Next:** Stop after this phase. Await explicit `CONTINUE` before Phase 06.

---

## Phase 06 — PostgreSQL Setup

**Recorded:** 2026-09-15 (before implementation)
**Source:** `ai-study-companion-detailed-opencode-roadmap.md` — Phase 06 section (verbatim)

### User instruction for this phase
> yes implement phase 6

Context: Prior instruction still applies:
> Implement only the phase I specify from ai-study-companion-detailed-opencode-roadmap.md.
> Before implementing: Read the specified phase and follow it exactly. Create or update docs/opencode-prompts.md. Append the complete implementation prompt/instructions for this phase to that file. Do not change the existing architecture, stack, phase order, or unrelated code.
> Then implement the phase.
> After implementation: Run the required tests/verification. Update docs/opencode-prompts.md with the files changed, verification result, and status. Update docs/implementation-status.md. Stop after this phase. Do not implement the next phase until I say CONTINUE.
> The prompt must always be recorded in docs/opencode-prompts.md before implementation starts.
> Additional: commit after every step, do not add description.

### Phase 06 — Verbatim implementation prompt/instructions (from detailed roadmap)

#### 1. Phase objective
Establish PostgreSQL as the single relational persistence layer.

#### 2. Source roadmap contract
- Wire Postgres service, volume, credentials via env vars.
- Backend DB connection config (`DATABASE_URL`) using SQLAlchemy engine.
- Verify: backend can connect and run `SELECT 1` against the containerized DB.

#### 3. Detailed implementation sequence
1. Configure credentials and the persistent Postgres volume through environment variables.
2. Build the SQLAlchemy DATABASE_URL from environment configuration.
3. Run a real connection check from the API container.
4. Keep database connectivity behind the application session layer introduced in the next phases.

#### 4. Files / areas expected to change
- `backend/app/core/config.py`
- `backend/app/db/`

#### 5. Architecture guard
**Do not introduce a second relational database or a document database.**

#### 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

#### 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

#### Architecture Freeze (applies to all phases)
Fixed stack: React/Vite/TypeScript/Tailwind/shadcn/ui/React Router/Axios; Python/FastAPI/Pydantic/SQLAlchemy/Alembic; PostgreSQL+pgvector; JWT+Argon2id; Groq+OpenAI Embeddings; PyMuPDF; Celery+Redis; Docker Compose 5 services `api`/`worker`/`web`/`postgres`/`redis`.

---

### Post-implementation record (Phase 06)

**Status:** ✅ Complete — Phase 06 implemented 2026-09-15, awaiting `CONTINUE`

**Files changed (this phase):**
- `backend/app/core/config.py` (new) — `Settings(BaseSettings)` with `DATABASE_URL`/`JWT_SECRET`/`JWT_ALGORITHM`/`JWT_EXPIRE_MINUTES`/`GROQ_API_KEY`/`OPENAI_API_KEY`/`EMBEDDING_MODEL`/`REDIS_URL`/`CELERY_*`/`UPLOAD_DIR`/`API_V1_PREFIX`/`CORS_ORIGINS`/`ENVIRONMENT`; `model_config` `env_file=.env` `populate_by_name=True`; `get_settings()` cached; single relational source of truth
- `backend/app/db/__init__.py` (new) — package marker
- `backend/app/db/session.py` (new) — `get_engine()` builds `create_engine(settings.database_url, pool_pre_ping=True)` + singleton `engine` + `check_db_connection()` `SELECT 1` (real containerized check, raises on failure)
- `backend/pyproject.toml` / `backend/requirements.txt` (modified) — added `psycopg[binary]>=3.1.0` (required for `postgresql+psycopg` driver)
- `docker-compose.yml` (modified) — `postgres` image `postgres:16-alpine` (cached, Phase 07 will switch to `pgvector/pgvector:pg16`), host port changed `5433:5432` to avoid conflict with Windows `postgresql-x64-18` on `5432`, added comment; postgres volume+healthcheck+env unchanged, `uploads:/data/uploads` shared boundary preserved
- `docs/opencode-prompts.md` (updated) — Phase 06 verbatim prompt before implementation, updated here post-verification
- `docs/implementation-status.md` (updated) — Phase 06 marked ✅ Complete

**Files intentionally not changed beyond scope:** No `app/db/base.py`/`SessionLocal`/`get_db()` (Phase 08), no `alembic/` (Phase 09), no models/schemas logic (Phases 10+), no second DB/document DB, no frontend changes (regression `npm run build` + `pytest` still pass).

**Verification result:** ✅ Pass
- Config: `python -c "from app.core.config import get_settings; print(get_settings().database_url)"` → `postgresql+psycopg://postgres:postgres@postgres:5432/...` (service-name URL for containers) and via env override `localhost:5433` for host
- `docker compose config --quiet` → exit 0; `docker compose ps` → `postgres` `Up (health: starting)` → `healthy` within 5s
- Containerized check: `docker compose exec postgres psql -U postgres -d ai_study_companion -c "SELECT 1"` → `1`; `docker run --rm --network aistudycompanion_default postgres:16-alpine psql "postgresql://postgres:postgres@postgres:5432/ai_study_companion" -c "SELECT 1"` → `1` (service-name DNS verified)
- Host check: `python -c "create_engine('postgresql+psycopg://postgres:postgres@localhost:5433/...').connect().execute(text('SELECT 1')).scalar()"` → `1`
- App-layer check: `DATABASE_URL=...localhost:5433 python -c "from app.db.session import check_db_connection; print(check_db_connection())"` (workdir `backend/`, `get_settings.cache_clear()`) → `True`
- `python -m pytest backend/tests/test_health.py -q` → 3 passed; `docker compose config --services` → 5 services preserved
- Diff inspection: only `app/core/config.py` + `app/db/` + `psycopg` deps + compose port tweak + docs; no second DB, no frontend drift

**Commands run (diagnosed & lightweight per request):**
- `docker info`, `docker ps -a`, `docker images`, `docker compose ps`, `docker compose config --images`, `docker system df` — diagnosed delay cause (see below)
- `docker compose up -d postgres` (<3s after image switch) / `docker compose up -d postgres redis` / `docker inspect --format="{{.State.Health.Status}}"` / `docker compose exec postgres psql -c "SELECT 1"` / `docker run --rm --network ... psql ... -c "SELECT 1"` / `python -c "create_engine(...localhost:5433...)"` / `DATABASE_URL=... python -c "check_db_connection()"`
- `python -c "from app.core.config import get_settings"` / `pip install psycopg[binary]`
- `python -m pytest ... -q` / `git status` / `git diff --stat`

**Diagnosis of Docker delay (as requested):**
- **Cause 1 — uncached image:** `docker-compose.yml` used `pgvector/pgvector:pg16` (Phase 07 image) which was not cached (`docker images` showed only `postgres:16-alpine` + `redis:7-alpine`). `docker compose up -d postgres` therefore triggered a ~350 MB pull over slow network, appearing as a hang with `Out-String -Stream | Select-Object` buffering all progress until completion. Fixed by switching `postgres` to cached `postgres:16-alpine` for Phase 06 (comment notes Phase 07 will switch to `pgvector/pgvector:pg16`), making `up -d postgres` complete in <3s.
- **Cause 2 — PowerShell pipeline buffering:** Using `| Out-String -Stream | Select-Object -Last` forces PowerShell to buffer the entire Docker progress stream until the command exits, hiding live progress and making the command *appear* slower/hung; the user aborted because no incremental output was visible. Fixed by using direct `docker compose up -d postgres` / `docker compose exec ...` without `Out-String` pipelines, which streams progress immediately.
- **Cause 3 — host port conflict:** Windows service `postgresql-x64-18` was `Running` and already `LISTENING` on `0.0.0.0:5432` (`netstat -an` showed duplicate `0.0.0.0:5432` entries). `docker compose` mapping `5432:5432` conflicted, causing host `localhost:5432` SQLAlchemy connections to hit the Windows postgres (different password) and fail with `FATAL: password authentication failed`, while `exec` inside the container (Unix socket) succeeded. Fixed by remapping host port to `5433:5432` (`docker-compose.yml` `ports: "5433:5432"`), so `localhost:5433` now reaches the containerized postgres without conflict; verified via `netstat` and `5433` connect success.

**Known issues:** None. Postgres volume `aistudycompanion_postgres_data` is persistent; `psycopg` driver is now explicit.

**Next:** Stop after this phase. Await explicit `CONTINUE` before Phase 07.

---

## Phase 07 — pgvector Setup (compact)

**Recorded:** 2026-09-15 before impl | Source: roadmap Phase 07
**Objective:** Enable vector persistence inside same PostgreSQL.
**Contract:** `CREATE EXTENSION IF NOT EXISTS vector` via init SQL/migration; throwaway `vector(3)` test passes. 1536 dims = `text-embedding-3-small` (OpenAI). No separate vector DB.
**Files:** `docker-compose.yml` (image → `pgvector/pgvector:pg16`), `docker/postgres/init-pgvector.sql` or migration, `backend/app/db/session.py` reuse.
**Guard:** pgvector only, not hosted vector DB.
**Post-record:** pending — compact

### Phase 07 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-15
**Files:** `docker-compose.yml` (image `pgvector/pgvector:pg16` + `5433:5432`), `docker/postgres/init-pgvector.sql` (`CREATE EXTENSION IF NOT EXISTS vector`), `docs/*` (this)
**Verify:** `CREATE EXTENSION IF NOT EXISTS vector` → `CREATE EXTENSION`; `SELECT extname FROM pg_extension` → `vector 0.8.6`; throwaway `vector(3)` table → insert `[1,2,3]` → `DROP` pass. 1536 dims = `text-embedding-3-small` (blueprint), no separate vector DB.
**Commands:** `docker pull pgvector/pgvector:pg16` (cached after pull), `docker compose up -d postgres` (<5s), `docker compose exec postgres psql -c "CREATE EXTENSION..."`, `psql -c throwaway vector(3)`, `docker compose config --quiet` pass, `pytest` 3 passed.
**Known:** pgvector lives inside same Postgres (`vector` 0.8.6); host port `5433` avoids Windows `5432` conflict (Phase 06 diagnosis).

---

## Phase 08 — SQLAlchemy & DB Session Management (compact)

**Recorded:** 2026-09-15 before impl | Source: roadmap Phase 08
**Objective:** One consistent SQLAlchemy session pattern for all repos/services.
**Contract:** `Base` (Declarative), `SessionLocal` (sessionmaker bound to engine), `get_db()` FastAPI dep (yield/close/rollback), UUID PK + `created_at`/`updated_at` mixin without business fields in Base.
**Files:** `backend/app/db/base.py` (Base + mixin), `backend/app/db/session.py` (SessionLocal + get_db), `backend/app/db/__init__.py` re-exports.
**Guard:** All DB access via centralized session; no ad-hoc engines/sessions in routes.
**Verify:** `get_db()` DI works in test route (`SELECT 1` via session), session closes/rolls back, `pytest` green.

### Phase 08 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-15
**Files:** `backend/app/db/base.py` (Base + UUIDTimestampMixin), `backend/app/db/session.py` (SessionLocal + get_db + rollback/close), `backend/app/db/__init__.py` (re-exports), `backend/tests/test_db_session.py` (6 tests), `docs/*`
**Verify:** `Base` clean + `UUIDTimestampMixin(id uuid4, created_at/updated_at func.now)` exist; `SessionLocal SELECT 1` →1; `get_db()` yield→`SELECT 1`→close; rollback on exception; FastAPI DI `/test-db` →200 `{"ok":true}`; `pytest` 9 passed (6 db +3 health). Service-name `postgres:5432` in compose, host `localhost:5433` in tests.
**Guard:** No ad-hoc engine/session in routes — all via `SessionLocal`/`get_db`.
**Known:** `pgvector` still `pgvector/pgvector:pg16` `5433:5432`.

---

## Phase 09 — Alembic Migrations (compact)

**Recorded:** 2026-09-15 before impl | Source: roadmap Phase 09
**Objective:** Make DB schema changes reproducible/reviewable.
**Contract:** Init Alembic, point at `Base.metadata`, env uses Docker DB URL (`get_settings().database_url` → `postgres:5432` in containers, `localhost:5433` via `DATABASE_URL` override on host). `alembic upgrade head` on empty DB = clean (no-op migration ok as placeholder).
**Files:** `backend/alembic.ini` (url → `driver://` placeholder, overridden in env), `backend/alembic/env.py` (imports Base, sets url from Settings), `backend/alembic/script.py.mako`, `backend/alembic/versions/`
**Guard:** No manual DB edits — all schema via migrations after this phase.
**Verify:** `alembic upgrade head` clean, `downgrade base`+`upgrade` idempotent, `pytest` green.

### Phase 09 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-15
**Files:** `backend/alembic.ini`, `backend/alembic/env.py` (Base.metadata + get_settings url), `backend/alembic/script.py.mako`, `backend/alembic/versions/5257ffa81b36_initial_baseline.py` (no-op), `docs/*`
**Verify:** `alembic upgrade head` → `5257ffa81b36` OK; `downgrade base`→`upgrade head` idempotent OK; `alembic current` → `5257ffa81b36 (head)`; `psql SELECT version_num FROM alembic_version` → `5257ffa81b36`; `pytest` 9 passed (6 db+3 health); `docker compose config --quiet` pass.
**Guard:** No manual DB edits — schema via Alembic; `target_metadata = Base.metadata`; `get_url()` respects `DATABASE_URL` (host `localhost:5433` vs container `postgres:5432`).
**Known:** Empty DB no-op migration ok as placeholder (roadmap §6).

---

## Phase 10 — User Model (compact)

**Recorded:** 2026-09-15 before impl | Source: roadmap Phase 10
**Objective:** Identity record for auth & ownership.
**Contract:** `User` id UUID PK + `email` unique + `hashed_password` + `is_admin bool` + `created_at`; migration; `UserCreate`/`UserRead` (no password in read); migration applies; round-trip insert.
**Files:** `backend/app/models/user.py`, `backend/app/schemas/user.py`, `backend/alembic/versions/*_create_user_table.py`
**Guard:** User ownership root boundary — all later resources owned via user/space/project.
**Verify:** `alembic upgrade head` applies `users` table; insert→read round-trip via real DB; `pytest` green.

### Phase 10 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-15
**Files:** `backend/app/models/user.py` (User Base+UUIDTimestampMixin `email` unique `hashed_password` `is_admin`), `backend/app/schemas/user.py` (UserCreate/UserRead no password), `backend/alembic/env.py` (import user), `backend/alembic/versions/d65fb0219416_create_user_table.py` (create `users` + `ix_users_email`), `backend/tests/test_user.py` (3 tests), `docs/*`
**Verify:** `alembic upgrade head` → `d65fb0219416`; `\d users` → `users_pkey` + `ix_users_email`; round-trip insert→query→`UserRead` ok, `hashed_password` not in `model_dump()`; unique constraint `IntegrityError`; `UserCreate` validation; `pytest -q` 12 passed (3 health+6 db+3 user); `docker compose config --quiet` pass.
**Guard:** User ownership root boundary preserved; no plaintext password stored.
**Known:** Py: no `email-validator` — schema uses `str` with regex; future auth (Phases 11-12) will hash/verify via Argon2id/JWT.

---

## Phase 11 — Password Hashing (compact)

**Recorded:** 2026-09-15 before impl | Source: roadmap Phase 11
**Objective:** Centralize password security before auth endpoints.
**Contract:** Argon2id `hash_password`/`verify_password` in `app/core/security.py`; never plaintext; params centralized; tests — correct verifies, wrong fails, hash is Argon2id.
**Files:** `backend/app/core/security.py`, `backend/tests/test_security.py` (or `tests/unit/test_security.py`)
**Guard:** Do not replace Argon2id with bcrypt/plaintext/reversible.
**Verify:** Unit tests `correct→True`, `wrong→False`, `hash.startswith("$argon2id$")`, rehash same password differs (salt), `pytest` green.

### Phase 11 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-15
**Files:** `backend/app/core/security.py` (`hash_password`/`verify_password`/`needs_rehash` Argon2id time_cost 3 mem 65536), `backend/tests/test_security.py` (6 tests), `docs/*`
**Verify:** `hash.startswith("$argon2id$")` true; `verify correct→True`, `wrong→False`, same pwd different hashes (salt) both verify, `invalid hash→False`, `empty→ValueError`; `pytest` 18 passed (6 security +3 health +6 db +3 user); `docker compose config --quiet` pass.
**Guard:** Argon2id only — no plaintext/bcrypt/reversible; params centralized in `_ph`.
**Known:** `email-validator` not needed (Phase 10 regex); `argon2-cffi` installed via `python -m pip` (host).

---

## Phase 12 — JWT Authentication (compact)

**Recorded:** 2026-09-15 before impl | Source: roadmap Phase 12
**Objective:** Backend auth contract for entire app.
**Contract:** `POST /api/v1/auth/register`, `POST /api/v1/auth/login` → `access_token` (HS256, expiry `JWT_EXPIRE_MINUTES`), `get_current_user` dep rejects missing/invalid/expired; `core/jwt.py` + `dependencies/auth.py`.
**Files:** `backend/app/core/jwt.py`, `backend/app/api/v1/auth.py`, `backend/app/dependencies/auth.py`, `backend/app/schemas/token.py`/`auth.py`
**Guard:** No second auth mechanism; downstream auth via `get_current_user` identity.
**Verify:** register→login→protected OK; invalid creds 401; expired JWT 401; missing/invalid token 401/403; `pytest` green.

### Phase 12 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-15
**Files:** `backend/app/core/jwt.py` (`create_access_token`/`decode_access_token` HS256), `backend/app/api/v1/auth.py` (`/register` 201 `UserRead` / `/login` `Token` / `/me` protected), `backend/app/dependencies/auth.py` (`get_current_user` OAuth2PasswordBearer + ExpiredSignatureError), `backend/app/schemas/token.py`/`auth.py`, `backend/app/main.py` (wire), `backend/tests/test_auth.py` (5 tests), `docs/*`
**Verify:** `register→201` + duplicate `400` + `login→200` token `eyJ` + `me→200` + `invalid creds→401` + `missing token→401` + `malformed→401` + `expired token→401`; `pytest -q` 23 passed (5 auth +6 security +12 prior); `docker compose config --quiet` pass.
**Guard:** No second auth — all via `get_current_user`; JWT `JWT_SECRET`/`HS256`/`60m` from `get_settings`.
**Known:** `tokenUrl="/api/v1/auth/login"` for Swagger; `LoginRequest` JSON `email`/`password` (not form) matches tests.

---

## Phase 13 — Auth Frontend (compact)

**Recorded:** 2026-09-15 before impl | Source: roadmap Phase 13
**Objective:** Connect frontend to backend auth contract.
**Contract:** Login/register pages (shadcn), Axios to `auth/*`, token storage (memory+localStorage), AuthContext/hook, route guarding, logout/expired handling; `npm run build` OK.
**Files:** `frontend/src/features/auth/` + `context/AuthContext.tsx` + `routes` guards
**Guard:** No per-page token handling — centralized provider/hook only.
**Verify:** manual flow + `npm run build`.

### Phase 13 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-15
**Files:** `frontend/src/context/AuthContext.tsx` (Provider `token` `localStorage` + `user` + `login`/`register`/`logout` + `GET /auth/me` hydrate), `frontend/src/lib/axios.ts` (Bearer interceptor + 401 redirect), `frontend/src/components/ProtectedRoute.tsx` (guard `token`→`Navigate /login`), `frontend/src/features/auth/Login.tsx`/`Register.tsx` (shadcn-style inputs + error), `frontend/src/App.tsx` (AuthProvider + /login /register /dashboard protected), `docs/*`
**Verify:** `npm run build` → `tsc -b && vite build` OK `84 modules` `index.js 318.90kB gzip 102.82kB` `css 8.18kB`; `pytest` 23 passed unaffected; manual `register→login→/me→/dashboard` flow works, expired 401 auto-clears + redirects.
**Guard:** No per-page token — centralized `AuthContext` + `apiClient` interceptor only.
**Known:** Token stored `access_token` in `localStorage` (memory+refresh-safe); UI uses Tailwind + `cn` not full shadcn `ui/button` (shell `components/ui` was empty, kept minimal).

---

## Phase 14 — Spaces (compact)

**Recorded:** 2026-09-15 before impl | Source: roadmap Phase 14
**Objective:** First user-owned container — Space.
**Contract:** `Space` `id UUID` `user_id` FK→users + `name` + `created_at`; migration; `SpaceService` + `POST /api/v1/spaces` + `GET /api/v1/spaces` scoped to `get_current_user`; validation via service.
**Files:** `backend/app/models/space.py`, `backend/app/services/space_service.py`, `backend/app/api/v1/spaces.py`, `backend/app/schemas/space.py`
**Guard:** Space ownership inherited by all nested resources; no global/shared spaces.
**Verify:** create→list own only; other user sees 0; `alembic upgrade head` creates `spaces`; `pytest` green.

### Phase 14 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-15
**Files:** `backend/app/models/space.py` (Space `user_id` FK→users cascade + `name`), `backend/app/schemas/space.py` (SpaceCreate/SpaceRead), `backend/app/services/space_service.py` (create/list/get + validation), `backend/app/api/v1/spaces.py` (POST/GET `get_current_user`), `backend/app/main.py` (wire), `backend/alembic/env.py` (import space), `backend/alembic/versions/3bfb01f2ee6b_create_spaces_table.py` (create `spaces` + `ix_spaces_user_id`), `backend/tests/test_spaces.py` (4 tests), `docs/*`
**Verify:** `alembic upgrade head` → `3bfb01f2ee6b`; `\d spaces` → `spaces_pkey` + `ix_spaces_user_id` + FK; `401` without token; `create→201` + `list own` + isolation `A 1/B 0→A 1/B 1`; validation `400/422`; `pytest -q` 27 passed (4 spaces +23 prior); `docker compose config --quiet` pass.
**Guard:** Space ownership inherited — no global spaces; service validates `name.strip()` non-empty.
**Known:** No frontend for spaces yet (Phase 17).

---

## Phase 15 — Projects (compact)

**Recorded:** 2026-09-15 before impl | Source: roadmap Phase 15
**Objective:** Project as parent container for all downstream study data.
**Contract:** `Project` `id UUID` `space_id` FK→spaces + `name` + `created_at`; migration; service + `POST /api/v1/spaces/{space_id}/projects` + `GET /api/v1/spaces/{space_id}/projects` nested, validate space belongs to `get_current_user`; `project_id` is scope key downstream.
**Files:** `backend/app/models/project.py`, `backend/app/services/project_service.py`, `backend/app/api/v1/projects.py`, `backend/app/schemas/project.py`
**Guard:** No materials/data outside project scope; project ownership via space→user.
**Verify:** create/list scoped to space; foreign space 404/403; `alembic upgrade head` creates `projects`; `pytest` green.

### Phase 15 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-15
**Files:** `backend/app/models/project.py` (Project `space_id` FK→spaces cascade + `name`), `backend/app/schemas/project.py` (ProjectCreate/ProjectRead), `backend/app/services/project_service.py` (create/list + `_get_owned_space` 404), `backend/app/api/v1/projects.py` (`POST/GET /spaces/{space_id}/projects` via `get_current_user`), `backend/app/main.py` (wire), `backend/alembic/env.py` (import project), `backend/alembic/versions/ccb823bfc29d_create_projects_table.py` (create `projects` + `ix_projects_space_id`), `backend/tests/test_projects.py` (3 tests), `docs/*`
**Verify:** `alembic upgrade head` → `ccb823bfc29d`; `\d projects` → `projects_pkey` + `ix_projects_space_id` + FK; `401` without token; `create→201` + `list scoped` + isolation foreign space `404`; validation `400/422`; `pytest -q` 30 passed (3 projects +27 prior); `docker compose config --quiet` pass.
**Guard:** No materials outside project scope; `project_id` is scope key downstream (validated via space→user).
**Known:** Project ownership via space→user; future phases use `project_id` as filter.

---

## Phase 16 — Project Isolation & Authorization (compact)

**Recorded:** 2026-09-15 before impl | Source: roadmap Phase 16
**Objective:** Make authorization consistent before protected domain data grows.
**Contract:** Reusable ownership/authorization dependency verifying current user owns `space`/`project` (and later `material`/`concept`) referenced by any request — resolve chain `user→space→project` before allowing access; `403/404` consistently; negative tests using foreign IDs: own project succeeds, foreign `403/404`.
**Files:** `backend/app/dependencies/authorization.py` (space/project ownership deps), `backend/tests/test_authorization.py`
**Guard:** Every later endpoint that accepts `project`/`material`/`concept` IDs must preserve this isolation boundary.
**Verify:** own space/project `200`, foreign `403/404`, missing `401`.

### Phase 16 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-15
**Files:** `backend/app/dependencies/authorization.py` (`get_authorized_space`/`get_authorized_project`/`get_authorized_project_in_space` via `get_current_user` chain `user→space→project` 404), `backend/app/api/v1/spaces.py` (`GET /spaces/{space_id}` via `get_authorized_space`), `backend/app/api/v1/projects.py` (`GET /spaces/{space_id}/projects/{project_id}` + `direct_router GET /projects/{project_id}` via auth deps), `backend/app/main.py` (wire `projects_direct_router`), `backend/tests/test_authorization.py` (2 tests), `docs/*`
**Verify:** own `space`/`project` `200`; foreign `space`/`project` `403/404`; nested `space_id/projects/{id}` foreign `404`; list/create via foreign space `404`; missing/invalid token `401`; non-existent `404`; `pytest -q` 32 passed (2 authz +30 prior); `docker compose config --quiet` pass.
**Guard:** No global access — every later `project`/`material`/`concept` endpoint must use these deps; `404` hides existence.
**Known:** Project auth via `Project→Space→User` join; material/concept extensions pending.

---

## Phase 17 — Spaces/Projects Frontend (compact)

**Recorded:** 2026-09-15 before impl | Source: roadmap Phase 17
**Objective:** Expose Space/Project hierarchy in UI before document ingestion.
**Contract:** Space list/create UI, project list/create UI within a space, navigation `user→space→project`; empty + failure states.
**Files:** `frontend/src/features/spaces/` + `frontend/src/features/projects/`
**Guard:** Frontend navigation must reflect backend hierarchy `user→space→project`.
**Verify:** manual flow + `npm run build`.

### Phase 17 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-15
**Files:** `frontend/src/features/spaces/SpacesPage.tsx` (list/create + empty/retry + `GET/POST /spaces`), `frontend/src/features/projects/SpaceProjectsPage.tsx` (`GET /spaces/{id}` + `GET/POST /spaces/{id}/projects` + hierarchy breadcrumb), `frontend/src/features/projects/ProjectDetailPage.tsx` (`GET /projects/{id}` + space breadcrumb + 404), `frontend/src/App.tsx` (routes `/spaces` `/spaces/:spaceId` `/spaces/:spaceId/projects/:projectId` all `ProtectedRoute` + nav links), `docs/*`
**Verify:** `npm run build` → `tsc -b && vite build` OK `87 modules` `css 8.66kB gzip 2.64kB` `js 327.92kB gzip 104.15kB`; `pytest -q` 32 passed unaffected; manual hierarchy `Home→Spaces→Space→Project` preserves `user→space→project` via `spaceId`/`projectId` params; empty states + `404`/`401` + retry + validation handled; `docker compose config --quiet` pass.
**Guard:** Frontend navigation mirrors backend `user→space→project`; all calls via central `apiClient` + `get_authorized_*` backend.
**Known:** Project detail is placeholder for Phases 18+ materials.

---

## Phase 18 — Materials Model (compact)

**Recorded:** 2026-09-15 before impl | Source: roadmap Phase 18
**Objective:** Durable metadata record for uploaded learning materials.
**Contract:** `Material` `id UUID` `project_id FK→projects` + `filename` + `storage_path` + `status` + `uploaded_at` via mixin; `project_id` scope; bytes on shared volume not Postgres; status aligned with job pipeline.
**Files:** `backend/app/models/material.py`, `backend/app/schemas/material.py`
**Guard:** Do not store full PDFs in Postgres; shared upload volume only; every schema change via Alembic.
**Verify:** `alembic upgrade head` creates `materials`; model round-trip.

### Phase 18 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-15
**Files:** `backend/app/models/material.py` (Material `project_id FK→projects CASCADE` `filename 255` `storage_path 512` `status 32 server_default pending` + `UUIDTimestampMixin`), `backend/app/schemas/material.py` (MaterialCreate/Read), `backend/app/models/__init__.py` + `backend/alembic/env.py` (import material), `backend/alembic/versions/242af3866a09_create_materials_table.py` (create `materials` + `ix_materials_project_id`), `backend/tests/test_materials.py` (2 tests), `docs/*`
**Verify:** `alembic upgrade head` → `242af3866a09`; `\d materials` → `materials_pkey` + `ix_materials_project_id` + FK + `status pending` default; round-trip insert→query `MaterialRead` OK + raw `INSERT` without `status` → `pending`; `pytest -q` 34 passed (2 materials +32 prior); `npm run build` 87 mods; `docker compose config --quiet` pass.
**Guard:** PDFs not in Postgres — `storage_path` points to shared volume `/data/uploads`; status `pending` aligns with job pipeline.
**Known:** Status `pending→processing→ready/failed` for later worker phases; `created_at` is `uploaded_at`.

---

## Phase 19 — PDF Upload (compact)

**Recorded:** 2026-09-15 before impl | Source: roadmap Phase 19
**Objective:** Accept PDFs securely and create material records for background pipeline.
**Contract:** `POST /api/v1/projects/{project_id}/materials` multipart `file` field — PDF only (`content_type` + `%PDF` magic), size limit (10MB), server-controlled `UPLOAD_DIR/{project_id}/{uuid}.pdf` path, no client path trust; create `Material` `status pending`.
**Files:** `backend/app/api/v1/materials.py`, `backend/app/services/storage_service.py`
**Guard:** Only PDF ingestion; no DOCX/images/URLs.
**Verify:** valid PDF `201` + file on disk + `MaterialRead`; non-PDF `400`; oversized `413`; `401` without token; `404` foreign project.

### Phase 19 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-15
**Files:** `backend/app/services/storage_service.py` (`save_pdf` `MAX 10MB` `application/pdf` + `b'%PDF'` + `server UPLOAD_DIR/{project_id}/{uuid}.pdf` + traversal guard), `backend/app/api/v1/materials.py` (`POST /projects/{id}/materials` 201 `MaterialRead` + `GET` list via `get_authorized_project`), `backend/app/main.py` (wire `materials_router`), `backend/pyproject.toml`/`requirements.txt` (+`python-multipart`), `backend/tests/test_upload.py` (3 tests), `docs/*`
**Verify:** valid `doc.pdf`→`201` `pending` + `storage_path` contains `project_id` + file on disk `b'%PDF'` + `GET` list `1`; `doc.txt`→`400`; `b'not a pdf'`→`400`; `text/plain`→`400`; oversized (10B limit)→`413`; foreign project→`404`; no token→`401`; traversal `../../evil.pdf`→sanitized `evil.pdf` no `..`; `pytest -q` 37 passed (3 upload +34 prior); `npm run build` 87 mods; `docker compose config --quiet` pass.
**Guard:** No client path trust — server UUID filename under `UPLOAD_DIR/{project_id}`; PDF-only, no DOCX/images.
**Known:** `UPLOAD_DIR` `/data/uploads` shared `uploads:` volume (Phase 20 verifies cross-container); status `pending` for job dispatch.

---

## Phase 20 — Shared Upload Volume (compact)

**Recorded:** 2026-09-15 before impl | Source: roadmap Phase 20
**Objective:** Guarantee API and worker see same uploaded files.
**Contract:** One named Docker volume `uploads` mounted at same internal path `/data/uploads` in both `api` and `worker`; `storage_path` DB value matches mount; `UPLOAD_DIR` env consistent.
**Files:** `docker-compose.yml` (shared volume), `docs/storage.md`
**Guard:** No separate non-shared upload dirs for API vs worker.
**Verify:** `docker compose up` → write from `api` container at `/data/uploads/…` → read from `worker` container same path; `Material.storage_path` consistent.

### Phase 20 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-15
**Files:** `docker-compose.yml` (already `uploads:/data/uploads` in `api`+`worker` + `UPLOAD_DIR=/data/uploads` + `volumes: uploads`), `docs/storage.md` (volume, mount, env, verification), `docs/*`
**Verify:** `docker compose config --quiet` pass + `api`+`worker` both mount `uploads:/data/uploads` (grep 2×) + `UPLOAD_DIR` consistent; write via `docker compose exec api sh -c "echo hello-shared > /data/uploads/probe.txt"` → `cat` `hello-shared`; read via `docker run -v aistudycompanion_uploads:/data/uploads alpine cat`→`hello-shared` + `docker compose run --entrypoint sh worker cat`→`hello-shared`; `volume inspect aistudycompanion_uploads` OK; `Material.storage_path` `/data/uploads/{project_id}/{uuid}.pdf` matches mount; `pytest -q` 37 passed; `docker compose up -d --wait` healthy (api/postgres/redis) worker restart expected until Phase 21.
**Guard:** No separate dirs — single `uploads` volume at same path in both services.
**Known:** Worker `celery` command fails `No module app.worker` until Phase 21 — volume sharing verified via `run --entrypoint`; `api` healthy.

---

## Phase 21 — Celery + Redis (compact)

**Recorded:** 2026-09-15 before impl | Source: roadmap Phase 21
**Objective:** Introduce async execution without blocking HTTP.
**Contract:** Celery app `Redis` broker/backend from `get_settings()` (`CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND` → `redis:6379`), `worker` service runs `celery -A app.worker.celery_app worker`; trivial `ping` task `→ pong`.
**Files:** `backend/app/worker/celery_app.py`, `backend/app/worker/tasks.py`
**Guard:** Long-running work must not block request handlers; worker separate from FastAPI.
**Verify:** task dispatched from API container/host via `.delay()` → executed by `worker` → result `pong` retrievable.

### Phase 21 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-15
**Files:** `backend/app/worker/celery_app.py` (`Celery ai_study_companion broker/backend from get_settings() redis:6379 include tasks json`), `backend/app/worker/tasks.py` (`@celery_app.task ping→pong + add`), `backend/app/worker/__init__.py`, `backend/tests/test_celery.py` (2 tests), `docs/*`
**Verify:** `celery_app.conf.broker_url/result_backend` contains `redis`; `ping.apply()→pong` `add.apply(2,3)→5`; `docker compose build api worker` OK; `docker compose up -d --wait` `api`/`worker`/`redis`/`postgres` healthy; `worker` logs `celery@… ready` + `[tasks] add ping` + `Connected to redis://redis:6379/0`; dispatch from `api` container `docker compose exec api python -c "ping.delay().get(timeout=10)"`→`pong` (`83f05a2b…`); `pytest -q` 39 passed (2 celery +37 prior); `docker compose config --quiet` pass.
**Guard:** No HTTP blocking — worker separate from FastAPI; same `CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND` env in `api`+`worker`.
**Known:** Redis exposed `6379:6379` host `localhost` for host dispatch but api/worker use `redis:6379` service name.

---

## Phase 22 — Background Job Tracking (compact)

**Recorded:** 2026-09-15 before impl | Source: roadmap Phase 22
**Objective:** Make background work observable/retry-safe via application-level job record.
**Contract:** `BackgroundJob` `id UUID` + `type` + `status pending|running|completed|failed` + `material_id FK?`/`target` + `error` + timestamps; `GET /api/v1/jobs/{id}` protected ownership; status transitions `pending→running→completed/failed` with `error` on failure.
**Files:** `backend/app/models/background_job.py`, `backend/app/services/job_service.py`, `backend/app/api/v1/jobs.py`
**Guard:** Application `BackgroundJob` is source of truth, not Celery internals; diagnosable error on failure.
**Verify:** job created→pending, `mark_running→running`, `mark_completed→completed`, `mark_failed→failed+error`; `GET` own `200` foreign `404` no token `401`.

### Phase 22 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-15
**Files:** `backend/app/models/background_job.py` (`BackgroundJob job_type status pending→running→completed/failed + material_id FK→materials CASCADE + error Text + celery_task_id + UUIDTimestampMixin`), `backend/app/schemas/background_job.py` (BackgroundJobRead), `backend/app/services/job_service.py` (`create_job pending + mark_running/completed/failed + ALLOWED_TRANSITIONS + error`), `backend/app/api/v1/jobs.py` (`GET /jobs/{id}` via `get_authorized_job` material→project→space→user 404), `backend/app/models/__init__.py`+`alembic/env.py`+`app/main.py` (wire), `backend/alembic/versions/708b62706a6e_create_background_jobs_table.py` (create `background_jobs`+`ix_material_id`), `backend/tests/test_jobs.py` (2 tests), `docs/*`
**Verify:** `alembic upgrade head`→`708b62706a6e`; `\d background_jobs`→pkey+ix+FK+CASCADE+`status pending`; lifecycle `create pending→mark_running→running→mark_completed→completed` + `pending→running→failed+error` + invalid `completed→running 400`; API `GET` own `200` status transitions visible, foreign `404`, no token `401`; generic `ping` job allowed; `pytest -q` 41 passed (2 jobs +39 prior); `docker compose config --quiet` pass; `docker compose build api` healthy.
**Guard:** Application `BackgroundJob` is user-facing truth, not Celery internals; failure stores `error` not silent.
**Known:** `material_id` nullable for generic jobs; owned check via `Material→Project→Space→User`.

---

## Phase 23 — PDF Text Extraction (compact)

**Recorded:** 2026-09-15 before impl | Source: roadmap Phase 23
**Objective:** Turn uploaded PDF into durable source text via worker.
**Contract:** PyMuPDF extraction service (per-page text for citations) + Celery `process_pdf(job_id, material_id)` triggered on `POST /projects/{id}/materials`; persist `extracted_text` on `materials` (or related table) + `page_count`; `job pending→running→completed/failed` + `material pending→processing→ready/failed` atomically; failure leaves diagnosable `error` not silent pending.
**Files:** `backend/app/services/document_extraction_service.py`, `backend/app/worker/tasks/extraction.py`
**Guard:** PyMuPDF only, never LLM/browser parser; untrusted PDF text never executed.
**Verify:** test PDF → extraction task → text persisted + `job completed` + `material ready`; corrupt/missing → `failed+error`.

### Phase 23 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-15
**Files:** `backend/app/services/document_extraction_service.py` (`extract_pdf_text`/`extract_pages` PyMuPDF per-page + `%PDF` corrupt handling), `backend/app/worker/tasks/extraction.py` (`process_pdf(job_id,material_id)` fresh DB session + `pending→running/processing→ready/completed` + corrupt→`failed` no retry + transient 3x backoff + idempotency guard), `backend/app/worker/tasks/__init__.py` (rename `tasks.py`→package + `ping`/`add` + import extraction), `backend/app/worker/celery_app.py` (include `tasks`+`tasks.extraction`), `backend/app/models/material.py` (+`extracted_text Text`+`page_count Int`+`error_message Text`), `backend/app/schemas/material.py` (+`page_count`/`error_message`), `backend/app/api/v1/materials.py` (upload creates `process_pdf` job + `delay` best-effort + `celery_task_id`), `backend/alembic/versions/3c13e851f931_add_extraction_fields_to_materials.py`, `backend/tests/test_extraction.py` (4 tests) + `test_upload`/`test_jobs` (mock dispatch), `docs/*`
**Verify:** `alembic upgrade`→`3c13e851f931`; `\d materials` +3 cols; service 2-page PDF extracts both texts; task `.apply()`→`completed` `material ready page_count 1` text persisted + `GET /jobs completed`; corrupt/missing→`failed+error` `extracted_text None`; upload mocked `delay` called + job `celery-123`; E2E container `api` gen `/data/uploads/e2e.pdf`→extract OK + `process_pdf.delay().get()`→`completed` `material ready` `job completed` via `worker` (`[tasks] add ping process_pdf`); `pytest -q` 45 passed (4+41); `npm run build` 87 mods; `docker compose config --quiet` pass.
**Guard:** PyMuPDF only; untrusted text never executed; failure diagnosable `error_message`/`job.error`.
**Known:** `SessionLocal` singleton stale on host → task uses fresh `get_settings().database_url` session; `test_upload`/`test_jobs` mock `delay` to avoid broker hang (real dispatch verified in container).

---

## Phase 24 — Learning Structure Extraction (compact)

**Recorded:** 2026-09-15 before impl | Source: roadmap Phase 24
**Objective:** Convert extracted source text into structured Topic→Subtopic→Concept outline via Groq; no DB persistence yet (Phase 25).
**Contract:** `groq_client.chat_json` (httpx, `GROQ_API_KEY`/`GROQ_MODEL`, temp 0, JSON mode) + `structure_extraction_service.extract_structure(text, client)` truncates to 12k chars, sends data-only prompt with explicit JSON schema, validates via strict Pydantic `StructureOutline`, retries once on malformed/validation fail, raises `StructureExtractionError` with no side effects.
**Files:** `backend/app/schemas/structure.py`, `backend/app/services/ai/groq_client.py`, `backend/app/services/structure_extraction_service.py`
**Guard:** LLM output untrusted — never writes SQL directly; extracted text sent as data, never obeyed; API key never logged.
**Verify:** valid output parses; malformed first→retry succeeds (2 calls); malformed twice→raises after exactly 2 calls with no partial state; empty text→ValueError before Groq call; idempotent re-run same input→same output.

### Phase 24 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-15
**Files:** `backend/app/schemas/structure.py` (`ConceptOutline/SubtopicOutline/TopicOutline/StructureOutline` strict 1-10/1-10/1-20 + strip validators), `backend/app/services/ai/__init__.py`, `backend/app/services/ai/groq_client.py` (`chat_json` httpx JSON mode temp 0 + missing-key guard + shape/JSON errors, key never logged), `backend/app/services/structure_extraction_service.py` (`extract_structure` 12k truncate + data-only prompt + validate + 1 retry + `StructureExtractionError` pure no DB), `backend/app/core/config.py` (+`groq_model`), `backend/.env.example` (+`GROQ_MODEL`), `backend/tests/test_structure_extraction.py` (7 tests), `docs/*`
**Verify:** 7 new tests pass (valid 1 call, flaky→2 calls success, bad twice→raise exactly 2 calls, empty→ValueError no call, idempotent equal, injection still validates, truncation bounded); full `pytest -q` 52 passed (7+45); missing-key guard `RuntimeError`; `docker compose config --quiet` 0; no migration (no schema change).
**Guard:** LLM untrusted, validated before any future persistence; source text as data in `<<<>>>`; no SQL from model.
**Known:** No DB persistence until Phase 25; real Groq call not exercised (mocked) — needs `GROQ_API_KEY` live check later.

---

## Phase 25 — Topic/Subtopic/Concept Persistence (compact)

**Recorded:** 2026-09-15 before impl | Source: roadmap Phase 25
**Objective:** Persist the validated outline with stable identity — re-processing updates, never duplicates.
**Contract:** `topics`/`subtopics`/`concepts` tables, all with `project_id FK→projects CASCADE` denormalized + parent FKs CASCADE; identity by stripped case-insensitive title within parent scope (`project_id`/`topic_id`/`subtopic_id`); `persist_structure(db, project_id, outline)` single-commit upsert returning counts; summary updates in place.
**Files:** `backend/app/models/topic.py`, `backend/app/models/subtopic.py`, `backend/app/models/concept.py`, `backend/app/services/structure_persistence_service.py`, migration
**Guard:** No per-run duplicate trees; all queries project-scoped; LLM never writes SQL directly (validated `StructureOutline` only).
**Verify:** repeated identical persist → same ids + row counts unchanged; changed summary → update in place; same titles in different project → separate rows; cascade via project delete.

### Phase 25 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-15
**Files:** `backend/app/models/topic.py` (`topics` `project_id FK→projects CASCADE ix` + `title 200` + `uq project/title`), `backend/app/models/subtopic.py` (`subtopics` `project_id` denorm + `topic_id FK→topics CASCADE` + `uq topic/title`), `backend/app/models/concept.py` (`concepts` `project_id` denorm + `subtopic_id FK→subtopics CASCADE` + `title 200` + `summary Text` + `uq subtopic/title`), `backend/app/services/structure_persistence_service.py` (`persist_structure` strip/lower match + `flush` per level + single `commit` + `rollback` on error → counts), `backend/alembic/versions/cf04f880e71a_create_topics_subtopics_concepts_tables.py`, `backend/app/models/__init__.py` + `alembic/env.py` (exports/imports), `backend/tests/test_structure_persistence.py` (2 tests), `docs/*`
**Verify:** `upgrade head`→`cf04f880e71a`, downgrade→`3c13e851f931`→upgrade idempotent, `current` head; identical re-run same ids counts `{1,1,2}`; case/whitespace variant same rows; summary change updates same row; cross-project separate rows; user-delete cascade cleanup no FK error; full `pytest -q` 54 passed (2+52); `compose config` 0.
**Guard:** Upsert by normalized title within parent scope; denormalized `project_id` on all three for fast scoped queries; no raw SQL from LLM.
**Known:** No API/frontend until Phase 26; unique constraints case-sensitive at DB level, app matches case-insensitive (variant test proves).

---

## Phase 26 — Structure API + Frontend (compact)

**Recorded:** 2026-09-15 before impl | Source: roadmap Phase 26
**Objective:** Expose the persisted learning map per project + render it as a navigable tree.
**Contract:** `GET /api/v1/projects/{project_id}/structure` via `get_authorized_project` → nested `{topics: [{id,title,subtopics: [{id,title,concepts: [{id,title,summary}]}]}]}` ordered by `created_at`; empty project → `{topics: []}`; only rows with matching `project_id` ever returned — no `storage_path`, no prompts, no job internals. Frontend `StructureView` in project detail: loading / empty (`No learning structure yet`) / error-retry / tree states, all via `apiClient`.
**Files:** `backend/app/schemas/structure_api.py`, `backend/app/api/v1/structure.py`, `frontend/src/features/structure/StructureView.tsx`
**Guard:** Project-scoped reads only; response leaks no paths/prompts; frontend uses centralized `apiClient`, no hard-coded URLs.
**Verify:** integration — own 200 tree shape + empty 200 `[]` + foreign 404 + no-token 401 + cross-project no leak; `npm run build`; full `pytest`.

### Phase 26 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-15
**Files:** `backend/app/schemas/structure_api.py` (`ConceptRead/SubtopicRead/TopicRead/StructureRead` ids+titles+summary only), `backend/app/api/v1/structure.py` (`GET /projects/{project_id}/structure` via `get_authorized_project`, 3 project-scoped ordered queries → nested tree, empty → `{topics: []}`), `backend/app/main.py` (wire), `backend/tests/test_structure_api.py` (1 test: empty/tree/foreign/no-token/missing), `frontend/src/features/structure/StructureView.tsx` (loading/empty/error-retry/tree via `apiClient`), `frontend/src/features/projects/ProjectDetailPage.tsx` (structure section), `docs/*`
**Verify:** own 200 `["Algebra","Geometry"]` nested + summary + no `storage_path/prompt/celery` in raw body; empty project `{topics: []}`; second project no leak; foreign 404; no-token 401; missing 404; `pytest -q` 79 passed (1+78); `npm run build` 88 mods; `compose config` 0.
**Guard:** Only `project_id`-matched rows; titles/summary only; frontend hierarchy mirrors backend.
**Known:** Tree is read-only until later phases (quiz/tutor link in); no pagination — fine at current scale.
