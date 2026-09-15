# AI Study Companion — Detailed Phase-by-Phase OpenCode Implementation Roadmap

## Purpose

This document is an expanded execution guide for the supplied roadmap. It is intentionally **implementation-oriented** so an OpenCode coding agent can execute the project phase by phase with minimal ambiguity.

The original roadmap is the baseline contract. Its rule is explicit: implement phases **one at a time, in order**, keep the repository runnable after every phase, and do not proceed without an explicit `CONTINUE`. The source roadmap also identifies four behavior decisions that must remain open until their respective phases: mastery formula, mismatch thresholds, recommendation weights, and adaptive quiz selection. fileciteturn0file0L331-L338

## ARCHITECTURE FREEZE — READ BEFORE CODING

**Do not change the architecture while implementing this roadmap.** The purpose of this file is to expand implementation detail, not redesign the system.

### Fixed stack

**Frontend**
- React
- Vite
- TypeScript
- Tailwind CSS
- shadcn/ui
- React Router
- Axios

**Backend**
- Python
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic

**Database**
- PostgreSQL
- pgvector

**Authentication**
- JWT
- Argon2id

**AI**
- Groq for LLM generation/assessment
- OpenAI Embeddings for vector embeddings

**Documents**
- PyMuPDF

**Background processing**
- Celery
- Redis

**Runtime**
- Docker Compose with exactly these application/infrastructure services:
  `api`, `worker`, `web`, `postgres`, `redis`

The supplied roadmap explicitly defines this five-service Compose architecture and the browser/container communication rule. fileciteturn0file0L39-L43

### Required architectural boundaries

1. Browser → FastAPI API. The browser must not call Groq/OpenAI/Redis/PostgreSQL directly.
2. FastAPI → PostgreSQL/Redis and task dispatch. Long-running document/AI work goes to Celery workers.
3. Worker → shared upload volume + PostgreSQL/Redis + AI providers.
4. PostgreSQL is the relational source of truth.
5. pgvector lives inside PostgreSQL; do not introduce a separate vector database.
6. Project ownership is the isolation boundary for study material, concepts, chunks, retrieval, tutor, quizzes, mastery, and analytics.
7. Uploaded document text is untrusted data. Never execute or obey instructions found inside uploaded content.
8. LLM output is untrusted structured data. Validate it before persistence.
9. Derived learning metrics are deterministic application outputs over recorded evidence; do not let an LLM directly decide mastery, mismatch, or recommendation.
10. Every database schema change after Phase 09 must be represented by an Alembic migration.
11. Every phase must end in a runnable repository state and a focused verification result.
12. When a phase exposes a product behavior explicitly marked as unresolved by the source roadmap, stop and ask for/record the approved decision rather than inventing one.

## OpenCode execution protocol

For **every phase**, use this exact loop:

1. Read the current phase only plus the architecture freeze above.
2. Inspect the existing repository before editing.
3. Implement the phase in small commits/changes.
4. Run the phase verification commands/tests.
5. Review the diff for accidental architecture changes.
6. Update `docs/implementation-status.md`.
7. Report:
   - what changed,
   - files changed,
   - commands/tests run,
   - pass/fail result,
   - known issues,
   - whether the phase is complete.
8. **Stop and wait for `CONTINUE`.**
9. Never silently start the next phase.

### Definition of done for every phase

A phase is complete only when:
- its scope is implemented,
- no unrelated architecture changes were introduced,
- the repository still starts/builds as applicable,
- its verification checks pass,
- tests cover the important failure path where relevant,
- documentation/status is updated,
- and the phase is explicitly presented as ready for `CONTINUE`.

---

## Original roadmap traceability

The following phases preserve the exact order and scope of the supplied 58-phase roadmap; the sections below only expand the instructions. The source roadmap itself establishes the phase order and runnable-state gate. fileciteturn0file0L6-L7

---

# PHASE 01 — Repository & Blueprint Analysis ✅ COMPLETE

## 1. Phase objective
Establish the blueprint as the immutable architectural contract before implementation starts.

## 2. Source roadmap contract
- Read blueprint fully; extract domain scope, mandated stack, exclusions, hard rules.
- Log unresolved ambiguities (schema, API shapes, mastery/mismatch/recommendation formulas,
  quiz format) with a plan for when each will be confirmed.
- Initialize git repo, `docs/` folder.

## 3. Detailed implementation sequence
1. Read the complete blueprint and the existing blueprint-analysis document before changing code.
2. Create a decision/ambiguity log. Record every unresolved behavior without inventing a final answer.
3. Record the mandated stack, service boundaries, security boundaries, and excluded technologies as architecture constraints.
4. Do not implement product logic in this phase; this phase is documentation and repository-baseline work.

## 4. Files / areas expected to change
- `docs/00-blueprint-analysis.md`
- `docs/architecture-decisions.md`
- `docs/implementation-status.md`

## 5. Architecture guard
**No framework, database, queue, vector store, AI provider, or API architecture may be substituted because later phases depend on these decisions.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 02 — Project Skeleton & Monorepo Layout

## 1. Phase objective
Create the repository shape that every later phase will build inside.

## 2. Source roadmap contract
- Create `backend/`, `frontend/`, `docs/`, top-level `.gitignore`.
- Add `.env.example` files (backend + frontend) listing required env vars (DB URL, JWT
  secret, Groq API key, OpenAI API key, Redis URL, upload path) without real secrets.
- Add root `README.md` describing structure and how to run.

## 3. Detailed implementation sequence
1. Create exactly the backend/frontend/docs top-level structure from the source roadmap.
2. Keep frontend and backend independently runnable while sharing only documented contracts.
3. Create environment examples with variable names only; never commit secrets.
4. Document local development commands before feature implementation begins.

## 4. Files / areas expected to change
- `README.md`
- `.gitignore`
- `backend/.env.example`
- `frontend/.env.example`

## 5. Architecture guard
**Do not add a third application service or move product code outside backend/frontend without an explicit architecture decision.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 03 — Frontend Initialization

## 1. Phase objective
Create the browser application shell without introducing business logic.

## 2. Source roadmap contract
- Scaffold Vite + React + TypeScript app in `frontend/`.
- Install Tailwind CSS, configure `tailwind.config`, base styles.
- Install and configure shadcn/ui (components.json, base theme).
- Install React Router and Axios; set up a base `App.tsx` with routing shell and an Axios
  instance pointed at `VITE_API_BASE_URL`.
- Verify: `npm run build` succeeds.

## 3. Detailed implementation sequence
1. Initialize Vite + React + TypeScript in frontend/.
2. Configure Tailwind and shadcn/ui as the shared visual/component foundation.
3. Create the router shell and a single Axios client using VITE_API_BASE_URL.
4. Keep API calls centralized through the client; do not scatter hard-coded URLs through components.

## 4. Files / areas expected to change
- `frontend/src/main.tsx`
- `frontend/src/App.tsx`
- `frontend/src/lib/axios.ts`
- `frontend/components.json`

## 5. Architecture guard
**Keep React/Vite/TypeScript/Tailwind/shadcn/ui/React Router/Axios as the frontend stack.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 04 — Backend Initialization

## 1. Phase objective
Create the FastAPI application shell and backend layering.

## 2. Source roadmap contract
- Scaffold FastAPI app in `backend/` (`app/main.py`, `app/api/`, `app/core/`, `app/services/`,
  `app/models/`, `app/schemas/`).
- Add `pyproject.toml`/`requirements.txt` (fastapi, uvicorn, pydantic, sqlalchemy, alembic,
  argon2-cffi, python-jose or pyjwt, celery, redis, pymupdf, httpx).
- Add health-check endpoint `GET /api/v1/health`.
- Verify: app boots, health check returns 200; basic pytest smoke test.

## 3. Detailed implementation sequence
1. Create app/main.py plus api, core, services, models, and schemas packages.
2. Add only the dependencies required by the roadmap.
3. Add the versioned health route under /api/v1/health.
4. Add one smoke test proving the application can start and answer HTTP requests.

## 4. Files / areas expected to change
- `backend/app/main.py`
- `backend/app/api/`
- `backend/app/core/`
- `backend/app/services/`
- `backend/app/models/`
- `backend/app/schemas/`

## 5. Architecture guard
**Keep FastAPI as the HTTP boundary and retain the service-layer separation; do not put database/AI logic directly into route functions.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 05 — Docker Compose Foundation

## 1. Phase objective
Make all five runtime services reproducibly runnable together.

## 2. Source roadmap contract
- `docker-compose.yml` with services: `api`, `worker`, `web`, `postgres`, `redis`.
- Dockerfiles for backend and frontend.
- Confirm the Docker rule: browser talks to `localhost:8000`; backend/worker talk to each
  other via service names (`postgres`, `redis`).
- Verify: `docker compose config` validates; containers build.

## 3. Detailed implementation sequence
1. Define api, worker, web, postgres, and redis services.
2. Use Docker service names for container-to-container communication.
3. Keep browser-to-API communication on localhost:8000 as specified by the roadmap.
4. Build every container from a clean checkout before continuing.

## 4. Files / areas expected to change
- `docker-compose.yml`
- `backend/Dockerfile`
- `frontend/Dockerfile`

## 5. Architecture guard
**Do not collapse api and worker into one runtime service; the worker boundary is required by the background-processing architecture.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 06 — PostgreSQL Setup

## 1. Phase objective
Establish PostgreSQL as the single relational persistence layer.

## 2. Source roadmap contract
- Wire Postgres service, volume, credentials via env vars.
- Backend DB connection config (`DATABASE_URL`) using SQLAlchemy engine.
- Verify: backend can connect and run `SELECT 1` against the containerized DB.

## 3. Detailed implementation sequence
1. Configure credentials and the persistent Postgres volume through environment variables.
2. Build the SQLAlchemy DATABASE_URL from environment configuration.
3. Run a real connection check from the API container.
4. Keep database connectivity behind the application session layer introduced in the next phases.

## 4. Files / areas expected to change
- `backend/app/core/config.py`
- `backend/app/db/`

## 5. Architecture guard
**Do not introduce a second relational database or a document database.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 07 — pgvector Setup

## 1. Phase objective
Enable vector persistence inside the same PostgreSQL database.

## 2. Source roadmap contract
- Enable `pgvector` extension via init SQL or first migration.
- Verify: `CREATE EXTENSION IF NOT EXISTS vector;` succeeds; a throwaway vector column test
  passes.

## 3. Detailed implementation sequence
1. Enable pgvector through init SQL or migration.
2. Verify extension availability from the actual containerized database.
3. Use a temporary vector-column test only for verification; real embedding storage comes later.
4. Record the vector dimension/provider contract once the embedding model is fixed by the blueprint.

## 4. Files / areas expected to change
- `backend/alembic/`
- `docker/postgres/`

## 5. Architecture guard
**Do not replace pgvector with a hosted vector database.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 08 — SQLAlchemy & DB Session Management

## 1. Phase objective
Create one consistent SQLAlchemy session pattern for all repositories/services.

## 2. Source roadmap contract
- Declarative `Base`, `SessionLocal`, FastAPI dependency `get_db()`.
- Base model mixin (UUID primary key, `created_at`/`updated_at`).
- Verify: dependency-injected session works in a test route.

## 3. Detailed implementation sequence
1. Define the SQLAlchemy declarative Base and session factory.
2. Create a FastAPI get_db dependency.
3. Add shared UUID/timestamp behavior without embedding business fields in the base class.
4. Prove the session lifecycle works in a test route and closes/rolls back correctly.

## 4. Files / areas expected to change
- `backend/app/db/base.py`
- `backend/app/db/session.py`

## 5. Architecture guard
**All relational access must use the centralized SQLAlchemy session pattern.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 09 — Alembic Migrations

## 1. Phase objective
Make database schema changes reproducible and reviewable.

## 2. Source roadmap contract
- Initialize Alembic, point at SQLAlchemy metadata, configure env for the Docker DB URL.
- Verify: `alembic upgrade head` runs cleanly on an empty DB (no models yet, so no-op
  migration acceptable as a placeholder).

## 3. Detailed implementation sequence
1. Initialize Alembic and connect it to SQLAlchemy metadata.
2. Configure migrations to use the Docker database environment.
3. Run upgrade head on a clean database.
4. From this point onward, schema changes must be migrations rather than manual production SQL.

## 4. Files / areas expected to change
- `backend/alembic.ini`
- `backend/alembic/env.py`
- `backend/alembic/versions/`

## 5. Architecture guard
**Never solve schema drift by manually editing the database while leaving Alembic behind.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 10 — User Model

## 1. Phase objective
Introduce the identity record required by authentication and ownership.

## 2. Source roadmap contract
- `User` table: id (UUID), email (unique), hashed_password, is_admin, created_at.
- Alembic migration for the table.
- Pydantic schemas: `UserCreate`, `UserRead`.
- Verify: migration applies; model round-trips via a test insert.

## 3. Detailed implementation sequence
1. Implement the User model exactly with UUID id, unique email, hashed password, admin flag, and timestamps.
2. Create migration and Pydantic input/output schemas.
3. Keep password fields out of the public read schema.
4. Test insert/read behavior against the real test database.

## 4. Files / areas expected to change
- `backend/app/models/user.py`
- `backend/app/schemas/user.py`
- `backend/alembic/versions/`

## 5. Architecture guard
**User ownership is the root authorization boundary for spaces, projects, materials, and downstream data.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 11 — Password Hashing

## 1. Phase objective
Centralize password security before authentication endpoints exist.

## 2. Source roadmap contract
- Argon2id hashing service (`hash_password`, `verify_password`) in `app/core/security.py`.
- Verify: unit tests — correct password verifies, wrong password fails, hash format is
  Argon2id.

## 3. Detailed implementation sequence
1. Implement Argon2id hashing and verification in the core security module.
2. Never store plaintext passwords.
3. Keep hashing parameters/configuration centralized rather than duplicated.
4. Test correct-password success, wrong-password failure, and Argon2id format.

## 4. Files / areas expected to change
- `backend/app/core/security.py`
- `backend/tests/unit/test_security.py`

## 5. Architecture guard
**Do not replace Argon2id with plaintext, reversible encryption, or a different hashing design unless the architecture is explicitly revised.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 12 — JWT Authentication

## 1. Phase objective
Create the backend authentication contract used by the entire application.

## 2. Source roadmap contract
- Token issuance (access token, expiry from env), verification dependency
  (`get_current_user`), `POST /api/v1/auth/register`, `POST /api/v1/auth/login`.
- Verify: unit tests — register, login, invalid credentials rejected, expired JWT rejected,
  protected route rejects missing/invalid token.

## 3. Detailed implementation sequence
1. Implement register and login endpoints under /api/v1/auth.
2. Generate access JWTs with configurable expiry.
3. Implement current-user dependency and protected-route behavior.
4. Reject invalid credentials, missing tokens, malformed tokens, and expired tokens.

## 4. Files / areas expected to change
- `backend/app/api/v1/auth.py`
- `backend/app/core/jwt.py`
- `backend/app/dependencies/auth.py`

## 5. Architecture guard
**Authorization downstream must derive from the authenticated user identity; do not introduce a second authentication mechanism.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 13 — Auth Frontend

## 1. Phase objective
Connect the frontend to the backend authentication contract.

## 2. Source roadmap contract
- Login and register pages/forms (shadcn components), Axios calls to auth endpoints.
- Token storage (memory + refresh-safe strategy) and an auth context/hook.
- Route guarding for authenticated pages.
- Verify: manual flow + `npm run build`.

## 3. Detailed implementation sequence
1. Create register/login forms using the existing UI foundation.
2. Centralize authentication state in a provider/hook.
3. Configure Axios to attach authentication credentials according to the chosen token strategy.
4. Guard authenticated routes and make logout/expired-session behavior explicit.

## 4. Files / areas expected to change
- `frontend/src/features/auth/`
- `frontend/src/context/AuthContext.tsx`
- `frontend/src/routes/`

## 5. Architecture guard
**Do not let individual pages invent their own token handling.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 14 — Spaces

## 1. Phase objective
Introduce the first user-owned learning container: Space.

## 2. Source roadmap contract
- `Space` model (id, user_id/owner, name, created_at) + migration.
- Service layer (`SpaceService`) + `POST/GET /api/v1/spaces`.
- Verify: unit + integration tests (create, list own spaces only).

## 3. Detailed implementation sequence
1. Create Space with owner/user relationship.
2. Expose create/list endpoints scoped to the authenticated user.
3. Put validation and ownership-sensitive logic in SpaceService.
4. Test that one user cannot see another user's spaces.

## 4. Files / areas expected to change
- `backend/app/models/space.py`
- `backend/app/services/space_service.py`
- `backend/app/api/v1/spaces.py`

## 5. Architecture guard
**Space ownership is inherited by all nested resources; do not create global/shared spaces unless explicitly required.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 15 — Projects

## 1. Phase objective
Create Project as the parent container for study materials, structure, retrieval, assessment, and analytics.

## 2. Source roadmap contract
- `Project` model (id, space_id, name, created_at) + migration.
- Service layer + `POST/GET /api/v1/spaces/{space_id}/projects`.
- Verify: tests for create/list scoped to a space.

## 3. Detailed implementation sequence
1. Create Project linked to Space.
2. Expose create/list endpoints nested under the owning space.
3. Validate that the referenced space belongs to the authenticated user.
4. Keep project_id as the primary scope key for downstream queries.

## 4. Files / areas expected to change
- `backend/app/models/project.py`
- `backend/app/services/project_service.py`
- `backend/app/api/v1/projects.py`

## 5. Architecture guard
**Do not allow materials or learning data to float outside a project scope.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 16 — Project Isolation & Authorization

## 1. Phase objective
Make authorization consistent before protected domain data grows.

## 2. Source roadmap contract
- Authorization dependency verifying the current user owns the space/project (and later,
  material/concept) referenced by any request.
- Verify: tests — own project access succeeds, foreign project access returns 403/404.

## 3. Detailed implementation sequence
1. Create a reusable ownership/authorization dependency.
2. Resolve the resource chain user → space → project before allowing access.
3. Use 403/404 consistently according to the project API contract.
4. Write negative tests using foreign resource IDs.

## 4. Files / areas expected to change
- `backend/app/dependencies/authorization.py`
- `backend/tests/integration/test_authorization.py`

## 5. Architecture guard
**Every later endpoint that accepts project/material/concept identifiers must preserve this isolation boundary.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 17 — Spaces/Projects Frontend

## 1. Phase objective
Expose the Space/Project hierarchy in the UI before document ingestion.

## 2. Source roadmap contract
- Space list/create UI, project list/create UI within a space, navigation between them.
- Verify: manual flow + build.

## 3. Detailed implementation sequence
1. Build create/list screens for spaces.
2. Build project creation/listing inside a selected space.
3. Add routing and navigation that preserves the selected ownership scope.
4. Test empty states and API failure states, not only the happy path.

## 4. Files / areas expected to change
- `frontend/src/features/spaces/`
- `frontend/src/features/projects/`

## 5. Architecture guard
**Frontend navigation must reflect the backend hierarchy: user → space → project.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 18 — Materials Model

## 1. Phase objective
Create the durable metadata record for uploaded learning materials.

## 2. Source roadmap contract
- `Material` table (id, project_id, filename, storage_path, status, uploaded_at) + migration.
- Verify: migration applies cleanly.

## 3. Detailed implementation sequence
1. Create Material with project ownership, original filename, storage path, status, and upload time.
2. Keep actual PDF bytes outside PostgreSQL according to the existing shared filesystem architecture.
3. Define status values carefully because later background jobs depend on them.
4. Add migration and model tests before upload endpoints are added.

## 4. Files / areas expected to change
- `backend/app/models/material.py`
- `backend/app/schemas/material.py`

## 5. Architecture guard
**Do not store full PDFs inside PostgreSQL or introduce object storage as a replacement for the roadmap's shared upload volume.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 19 — PDF Upload

## 1. Phase objective
Accept PDFs securely and create material records that can enter the background pipeline.

## 2. Source roadmap contract
- `POST /api/v1/projects/{project_id}/materials` — multipart upload, file-type validation
  (PDF only), size limit enforcement, secure storage path generation.
- Verify: tests — valid PDF accepted, non-PDF rejected, oversized file rejected.

## 3. Detailed implementation sequence
1. Accept multipart/form-data only at the project-scoped upload endpoint.
2. Validate PDF type and enforce a hard size limit before writing the file.
3. Generate a server-controlled storage path; never trust a client-provided filesystem path.
4. Create the Material row and initial status consistently with the later job dispatch contract.

## 4. Files / areas expected to change
- `backend/app/api/v1/materials.py`
- `backend/app/services/storage_service.py`

## 5. Architecture guard
**Only PDF ingestion is in scope; do not broaden this phase to DOCX/images/URLs unless the blueprint explicitly requires it.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 20 — Shared Upload Volume

## 1. Phase objective
Guarantee that API and worker see the same uploaded files.

## 2. Source roadmap contract
- Docker Compose volume shared between `api` and `worker` so both can read/write uploaded
  files at the same path.
- Verify: `docker compose up`, write from api container, read from worker container.

## 3. Detailed implementation sequence
1. Create one named Docker volume and mount it at the same internal path in api and worker.
2. Write a file from the API container and confirm the worker can read it using the same path.
3. Keep the database record's storage_path consistent with the mounted path.
4. Document the local filesystem path only as an implementation detail; callers use material IDs, not paths.

## 4. Files / areas expected to change
- `docker-compose.yml`
- `docs/storage.md`

## 5. Architecture guard
**Do not create separate, non-shared upload directories for API and worker.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 21 — Celery + Redis

## 1. Phase objective
Introduce asynchronous background execution without changing the HTTP architecture.

## 2. Source roadmap contract
- Celery app config pointed at Redis broker/backend; `worker` service in Compose runs it.
- A trivial `ping` task to confirm wiring.
- Verify: task dispatched from API, executed by worker, result retrievable.

## 3. Detailed implementation sequence
1. Configure Celery with Redis as broker/backend.
2. Keep worker code separate from FastAPI request handling.
3. Implement a trivial ping task to prove serialization, dispatch, execution, and result retrieval.
4. Use the same environment configuration inside api and worker.

## 4. Files / areas expected to change
- `backend/app/worker/celery_app.py`
- `backend/app/worker/tasks.py`

## 5. Architecture guard
**Long-running extraction, embedding, and generation work must not block request handlers.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 22 — Background Job Tracking

## 1. Phase objective
Make background work observable and retry/failure-safe at the application level.

## 2. Source roadmap contract
- `BackgroundJob` model (id, type, status, material_id/target, error, timestamps).
- Job status endpoint `GET /api/v1/jobs/{id}`.
- Verify: tests — job created on dispatch, status transitions recorded.

## 3. Detailed implementation sequence
1. Create BackgroundJob with type, status, target, error, and timestamps.
2. Create a job-status endpoint protected by ownership rules.
3. Define allowed status transitions before implementing real tasks.
4. Ensure a task failure leaves a diagnosable error rather than a silent stuck material.

## 4. Files / areas expected to change
- `backend/app/models/background_job.py`
- `backend/app/services/job_service.py`
- `backend/app/api/v1/jobs.py`

## 5. Architecture guard
**BackgroundJob is the application's status record; do not rely only on Celery internals for user-facing state.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 23 — PDF Text Extraction

## 1. Phase objective
Turn an uploaded PDF into durable source text.

## 2. Source roadmap contract
- PyMuPDF-based extraction service; Celery task triggered on material upload; stores raw
  extracted text (e.g. on the material row or a related table).
- Verify: test PDF → extraction task → text persisted; job status becomes COMPLETE.

## 3. Detailed implementation sequence
1. Load the PDF from the shared storage path inside the worker.
2. Extract text with PyMuPDF while retaining enough metadata to support later citations where available.
3. Persist extracted text in the database or related table specified by the architecture.
4. Update job/material status atomically enough that a completed extraction cannot appear as pending.

## 4. Files / areas expected to change
- `backend/app/services/document_extraction_service.py`
- `backend/app/worker/tasks/extraction.py`

## 5. Architecture guard
**PyMuPDF is the document extraction implementation; do not replace it with an LLM or browser-side parser.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 24 — Learning Structure Extraction

## 1. Phase objective
Convert extracted source text into a structured learning outline.

## 2. Source roadmap contract
- Groq-backed service that turns extracted text into a structured
  Topic → Subtopic → Concept outline (structured/JSON output from the LLM).
- Malformed-output handling: validate before persisting; retry once; no partial persistence
  on failure.
- Verify: tests — valid output persists correctly, malformed output triggers retry and does
  not partially write, idempotent re-run does not duplicate concepts.

## 3. Detailed implementation sequence
1. Send only the required extracted text and explicit schema instructions to Groq.
2. Require structured Topic → Subtopic → Concept output.
3. Validate the response against a strict Pydantic schema before touching persistent structure data.
4. Retry once for malformed output and leave the database unchanged when validation still fails.

## 4. Files / areas expected to change
- `backend/app/services/ai/groq_client.py`
- `backend/app/services/structure_extraction_service.py`
- `backend/app/schemas/structure.py`

## 5. Architecture guard
**LLM output is untrusted data. The model never directly writes SQL or decides persistence behavior.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 25 — Topic/Subtopic/Concept Persistence

## 1. Phase objective
Persist the learning hierarchy while keeping repeated material processing safe.

## 2. Source roadmap contract
- `Topic`, `Subtopic`, `Concept` models + migrations, all denormalized with `project_id` for
  fast project-scoped queries.
- Stable `concept_id`s — re-processing a material updates, never blindly recreates, concepts.
- Verify: tests for idempotent persistence across repeated extraction runs.

## 3. Detailed implementation sequence
1. Create Topic, Subtopic, and Concept tables/migrations.
2. Keep project_id available for fast project-scoped lookup as required by the roadmap.
3. Define stable identity/matching behavior for concepts before implementing reprocessing.
4. Make repeated extraction idempotent: update/match existing concepts instead of blindly duplicating them.

## 4. Files / areas expected to change
- `backend/app/models/topic.py`
- `backend/app/models/subtopic.py`
- `backend/app/models/concept.py`
- `backend/alembic/versions/`

## 5. Architecture guard
**Do not create per-run duplicate concept trees that would later corrupt mastery or recommendations.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 26 — Structure API + Frontend

## 1. Phase objective
Expose the persisted learning map and establish the frontend representation used by later study features.

## 2. Source roadmap contract
- `GET /api/v1/projects/{project_id}/structure` (topics/subtopics/concepts tree).
- Frontend tree/list view of the learning structure per project.
- Verify: manual flow + build; integration test on the endpoint.

## 3. Detailed implementation sequence
1. Return a stable nested structure from the project-scoped endpoint.
2. Ensure only concepts belonging to the requested project are returned.
3. Render topics, subtopics, and concepts as a navigable tree/list.
4. Show loading, empty, processing, and failure states.

## 4. Files / areas expected to change
- `backend/app/api/v1/structure.py`
- `frontend/src/features/structure/`

## 5. Architecture guard
**The API tree must remain project-scoped and must not leak storage paths or internal AI prompts.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 27 — Chunking

## 1. Phase objective
Prepare source text for semantic retrieval.

## 2. Source roadmap contract
- Chunking service splitting material text into retrieval-sized chunks, linked to
  `concept_id` where determinable, `material_id`, `project_id`.
- Verify: unit tests on chunk boundaries/sizes.

## 3. Detailed implementation sequence
1. Split extracted text into deterministic chunks using retrieval-sized boundaries.
2. Preserve material_id and project_id on every chunk.
3. When concept association is determinable, store concept_id as well.
4. Make chunk generation repeatable so the same source text produces stable results.

## 4. Files / areas expected to change
- `backend/app/models/chunk.py`
- `backend/app/services/chunking_service.py`

## 5. Architecture guard
**Chunking is deterministic application logic; do not ask an LLM to choose retrieval boundaries.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 28 — Embedding Client

## 1. Phase objective
Isolate the OpenAI embeddings dependency behind a tiny, mockable interface.

## 2. Source roadmap contract
- Thin OpenAI Embeddings client wrapper (no LangChain) in `app/services/ai/`.
- Verify: unit test with a mocked API response.

## 3. Detailed implementation sequence
1. Create a thin client wrapper under app/services/ai/.
2. Centralize API key, model name, timeout, and error translation.
3. Return a predictable embedding representation to the worker.
4. Mock the HTTP/provider response in unit tests.

## 4. Files / areas expected to change
- `backend/app/services/ai/embedding_client.py`

## 5. Architecture guard
**Keep embeddings separate from Groq generation; do not route embedding generation through the tutor model.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 29 — Embedding Generation Worker

## 1. Phase objective
Generate and persist vectors for chunks asynchronously.

## 2. Source roadmap contract
- Celery task: chunk → embed → store vector (pgvector column) per chunk.
- Retry/idempotency: re-running does not duplicate embeddings for the same chunk.
- Verify: task test with mocked embedding client; row count stable across retries.

## 3. Detailed implementation sequence
1. Create a Celery task that reads chunks, calls the embedding client, and stores the vector in pgvector.
2. Associate each vector with the exact chunk it represents.
3. Make the operation idempotent so retrying a task does not create duplicate embedding rows.
4. Record failures through the background-job mechanism.

## 4. Files / areas expected to change
- `backend/app/models/embedding.py`
- `backend/app/worker/tasks/embeddings.py`

## 5. Architecture guard
**Embeddings belong to chunks; do not store vectors without their project/material/chunk scope.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 30 — pgvector Retrieval

## 1. Phase objective
Create secure, project-aware semantic retrieval.

## 2. Source roadmap contract
- Retrieval service performing similarity search **filtered by `project_id` in the query**
  (and `concept_id` when scoped), never "fetch all then filter."
- Verify: tests — cross-project material never returned; concept-scoped query respects scope.

## 3. Detailed implementation sequence
1. Embed the query using the same embedding contract as stored chunks.
2. Run vector similarity inside PostgreSQL using pgvector.
3. Apply project_id filtering inside the SQL/vector query itself.
4. When concept scope is supplied, apply concept_id in the database query too.
5. Return ranked chunks plus citation metadata needed by downstream services.

## 4. Files / areas expected to change
- `backend/app/services/retrieval_service.py`
- `backend/tests/integration/test_retrieval_isolation.py`

## 5. Architecture guard
**Never fetch all vectors and filter in Python; project isolation must be enforced by the database query.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 31 — RAG Service

## 1. Phase objective
Centralize retrieval + context assembly so tutor, quiz, and assessment consumers share one RAG foundation.

## 2. Source roadmap contract
- Combine retrieval + prompt assembly (context + citations metadata) into a single
  `RagService`, independent of any specific consumer (tutor/quiz/etc.).
- Verify: unit test on context assembly given mocked retrieval results.

## 3. Detailed implementation sequence
1. Accept a query and scope.
2. Call retrieval with the correct project/concept filters.
3. Build a bounded context payload from top-ranked chunks.
4. Keep source metadata alongside every context item so consumers can cite the answer.

## 4. Files / areas expected to change
- `backend/app/services/rag_service.py`
- `backend/app/schemas/rag.py`

## 5. Architecture guard
**RagService is consumer-neutral; do not embed tutor-specific UI or quiz logic inside it.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 32 — Tutor Backend

## 1. Phase objective
Build the grounded tutor backend with explicit unsupported-question behavior.

## 2. Source roadmap contract
- `POST /api/v1/projects/{project_id}/tutor/ask` — RAG-grounded Groq call, returns answer +
  citations (chunk/material references).
- Unsupported-question handling: if retrieval confidence/similarity is below threshold,
  return an explicit "not supported by materials" response instead of hallucinating.
- Prompt-injection guard: uploaded-content text is treated as data, not instructions.
- Verify: tests — grounded question returns citations, out-of-scope question returns the
  unsupported response, project isolation holds.

## 3. Detailed implementation sequence
1. Authenticate and authorize the project before retrieval.
2. Retrieve relevant project-scoped chunks and assemble context.
3. Send the context to Groq with instructions that uploaded text is data, not executable instructions.
4. If similarity/confidence is below the agreed threshold, return an explicit unsupported response.
5. Return answer text plus chunk/material citation metadata.

## 4. Files / areas expected to change
- `backend/app/api/v1/tutor.py`
- `backend/app/services/tutor_service.py`

## 5. Architecture guard
**The tutor must not answer from unrestricted model memory when the project materials do not support the question.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 33 — Tutor Frontend

## 1. Phase objective
Expose grounded tutor behavior without hiding its evidence.

## 2. Source roadmap contract
- Chat-style UI for the tutor, rendering citations and the unsupported-question state.
- Verify: manual flow + build.

## 3. Detailed implementation sequence
1. Build chat state and message rendering.
2. Render citation references returned by the API.
3. Render a distinct unsupported-material response.
4. Show loading and upstream-AI failure states without fabricating an answer.

## 4. Files / areas expected to change
- `frontend/src/features/tutor/`

## 5. Architecture guard
**Frontend must display backend evidence; it must not independently call Groq/OpenAI.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 34 — Quiz Data Model

## 1. Phase objective
Establish the durable assessment records required for quizzes and mastery evidence.

## 2. Source roadmap contract
- `Quiz`, `QuizQuestion`, `QuizAttempt`, `QuizAnswer` models (MCQ: question, options,
  correct_index, concept_id; attempt records answer + confidence + correctness) + migrations.
- Verify: migrations apply; round-trip test.

## 3. Detailed implementation sequence
1. Create Quiz, QuizQuestion, QuizAttempt, and QuizAnswer models.
2. Store MCQ question/options/correct index and concept_id.
3. Store answer correctness and confidence on attempts/answers.
4. Create migrations and round-trip tests before generation logic.

## 4. Files / areas expected to change
- `backend/app/models/quiz.py`
- `backend/app/models/quiz_attempt.py`
- `backend/alembic/versions/`

## 5. Architecture guard
**Assessment evidence must remain tied to concepts and projects so later mastery calculations are explainable.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 35 — Quiz Generation

## 1. Phase objective
Generate validated MCQs from concept material without allowing malformed model output into persistence.

## 2. Source roadmap contract
- Service generating MCQ questions from concept text via Groq, validated/parsed before
  persistence (same malformed-output discipline as Phase 24).
- Verify: tests — valid generation persists, malformed generation retried/rejected safely.

## 3. Detailed implementation sequence
1. Build the generation prompt from concept-scoped source material rather than arbitrary user input.
2. Require structured MCQ output.
3. Validate questions/options/correct index/concept association before persistence.
4. Retry malformed output once and reject safely if validation still fails.

## 4. Files / areas expected to change
- `backend/app/services/quiz_generation_service.py`
- `backend/app/schemas/quiz.py`
- `backend/app/services/ai/`

## 5. Architecture guard
**The LLM proposes question content; deterministic application code validates and persists it.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 36 — Adaptive Quiz Selection

## 1. Phase objective
Choose the next quiz questions using deterministic adaptive-selection logic.

## 2. Source roadmap contract
- Selection service choosing next questions based on current mastery/coverage (deterministic
  logic, not LLM-decided) — concrete rule proposed here and flagged for confirmation since
  it affects product behavior.
- Verify: unit tests on selection given synthetic mastery states.

## 3. Detailed implementation sequence
1. Do not let the LLM decide which concept the student should receive next.
2. Define inputs explicitly: mastery, coverage, recent exposure, and any blueprint-approved constraints.
3. Implement the selected rule as pure application logic that is easy to unit-test.
4. Use synthetic mastery states to prove the selector is deterministic.

## 4. Files / areas expected to change
- `backend/app/services/adaptive_quiz_service.py`

## 5. Architecture guard
**The selection rule remains a deterministic service and waits for confirmation where the source roadmap flags it as an open item.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 37 — Quiz Frontend

## 1. Phase objective
Create the student quiz-taking experience.

## 2. Source roadmap contract
- Quiz-taking UI including a confidence-capture control per answer (e.g. low/medium/high).
- Verify: manual flow + build.

## 3. Detailed implementation sequence
1. Load the selected quiz/question sequence from the backend.
2. Capture one answer and one confidence value per question.
3. Submit answers through the backend rather than calculating authoritative correctness in the browser.
4. Handle completion, retries, and API failures without losing the current attempt.

## 4. Files / areas expected to change
- `frontend/src/features/quiz/`

## 5. Architecture guard
**The frontend is not the source of truth for correctness or mastery.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 38 — Confidence Engine

## 1. Phase objective
Persist confidence as a separate learning signal while protecting the mastery formula boundary.

## 2. Source roadmap contract
- Persist confidence as its own signal; explicitly does not feed into mastery calculation
  (kept independent per the blueprint's mastery rule).
- Verify: tests confirming mastery output is unaffected by varying confidence with
  correctness held constant.

## 3. Detailed implementation sequence
1. Store the student's confidence for each answer.
2. Keep confidence available for analytics and future features.
3. Verify that changing confidence while holding correctness constant does not change mastery.
4. Do not silently feed confidence into the current mastery formula because the roadmap explicitly separates the signal.

## 4. Files / areas expected to change
- `backend/app/services/confidence_service.py`
- `backend/tests/unit/test_confidence.py`

## 5. Architecture guard
**Confidence remains independent of mastery unless the architecture is explicitly revised.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 39 — Open-Ended Assessment

## 1. Phase objective
Add free-text assessment evidence for conceptual understanding.

## 2. Source roadmap contract
- `POST /api/v1/.../assessment/open-ended` — student free-text answer graded via Groq against
  concept content, returns a structured grade + feedback.
- Verify: tests with mocked grading responses across pass/fail/partial cases.

## 3. Detailed implementation sequence
1. Authorize the project/concept before grading.
2. Send the student's answer and relevant concept material to Groq.
3. Require structured grade/feedback output.
4. Persist evidence and return feedback through a stable API schema.

## 4. Files / areas expected to change
- `backend/app/api/v1/assessment.py`
- `backend/app/services/open_ended_assessment_service.py`

## 5. Architecture guard
**Assessment grading is an evidence source; it does not directly mutate a mastery number in the request handler.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 40 — Explain-It-Back

## 1. Phase objective
Implement Explain-It-Back as applied-understanding evidence.

## 2. Source roadmap contract
- Feature where the student explains a concept back in their own words; graded similarly to
  open-ended assessment, feeding `applied_mastery` evidence.
- Verify: tests on evidence recording.

## 3. Detailed implementation sequence
1. Let the student explain one selected concept in their own words.
2. Grade the explanation against the concept content using the same structured assessment discipline.
3. Persist the result as applied_mastery evidence.
4. Keep the evidence append-only so later mastery calculations can be reproduced.

## 4. Files / areas expected to change
- `backend/app/services/explain_it_back_service.py`
- `backend/app/models/mastery_evidence.py`

## 5. Architecture guard
**Explain-It-Back feeds applied evidence; it must not bypass the evidence model.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 41 — Mastery Engine

## 1. Phase objective
Compute MCQ and applied mastery from append-only evidence using a deterministic, bounded formula.

## 2. Source roadmap contract
- **Flag for confirmation:** concrete formula for `mcq_mastery` and `applied_mastery`
  (proposed: bounded 0–1 weighted rolling accuracy over append-only evidence rows, decayed
  by recency) — proposed here, not silently finalized, since it materially affects behavior.
- Evidence table is append-only; mastery is derived/computed, never mutated in place.
- Verify: unit tests — bounds respected (0–1), independence of the two mastery types,
  confidence has zero effect on the computed value.

## 3. Detailed implementation sequence
1. Keep separate evidence streams for mcq_mastery and applied_mastery.
2. Implement the blueprint-confirmed formula once the flagged decision is approved.
3. Clamp results to 0–1 and handle insufficient evidence explicitly.
4. Never mutate historical evidence to force a desired mastery value.
5. Unit-test recency/decay, bounds, independence, and confidence irrelevance.

## 4. Files / areas expected to change
- `backend/app/services/mastery_service.py`
- `backend/app/models/mastery_evidence.py`

## 5. Architecture guard
**Do not silently invent or change the formula; this phase is explicitly flagged as an open product/architecture decision in the source roadmap.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 42 — Mismatch Engine

## 1. Phase objective
Detect meaningful disagreement between MCQ performance and applied performance.

## 2. Source roadmap contract
- **Flag for confirmation:** concrete deterministic rule and thresholds for detecting a
  mismatch between `mcq_mastery` and `applied_mastery` (e.g. divergence beyond X with a
  minimum evidence count before triggering) — proposed here for approval.
- Never delegated to the LLM ("does the student have a mismatch" is never asked of the model).
- Verify: unit tests — threshold behavior, minimum-evidence gating, mismatch priority when
  multiple concepts qualify.

## 3. Detailed implementation sequence
1. Compare the two mastery signals only after the minimum-evidence condition is satisfied.
2. Apply the approved divergence threshold deterministically.
3. Return a stable mismatch record/reason with the concepts that qualify.
4. Never ask the LLM whether a student has a mismatch.

## 4. Files / areas expected to change
- `backend/app/services/mismatch_service.py`
- `backend/app/models/mismatch.py`

## 5. Architecture guard
**Mismatch detection remains deterministic and explainable.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 43 — Recommendation Engine

## 1. Phase objective
Turn learning signals into one explainable current recommendation.

## 2. Source roadmap contract
- **Flag for confirmation:** concrete deterministic scoring formula (e.g. weighting mismatch
  priority, low mastery, staleness, with a repetition penalty to avoid repeatedly
  recommending the same concept) — proposed here for approval.
- Never delegated to the LLM. Returns one current recommendation + human-readable reason
  string generated from the scoring inputs (not free-form LLM invention).
- Verify: unit tests — scoring, mismatch-priority behavior, repetition penalty.

## 3. Detailed implementation sequence
1. Calculate a deterministic score from the approved inputs such as mismatch priority, low mastery, staleness, and repetition penalty.
2. Select one current recommendation according to a stable tie-break rule.
3. Generate the reason string from known scoring inputs rather than free-form model invention.
4. Unit-test scoring and tie/penalty behavior.

## 4. Files / areas expected to change
- `backend/app/services/recommendation_service.py`
- `backend/app/models/recommendation.py`

## 5. Architecture guard
**The recommendation engine is not an LLM classifier; its behavior must be reproducible from stored inputs.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 44 — Mastery/Mismatch/Recommendation UI

## 1. Phase objective
Make mastery, mismatch, and recommendation understandable to students.

## 2. Source roadmap contract
- Dashboard view per project: mastery bars (MCQ vs applied), flagged mismatches,
  current recommendation with its reason.
- Verify: manual flow + build.

## 3. Detailed implementation sequence
1. Display MCQ and applied mastery separately.
2. Show detected mismatches with enough context to understand the signal.
3. Show the current recommendation and its deterministic reason.
4. Keep the UI read-only with respect to the derived metrics.

## 4. Files / areas expected to change
- `frontend/src/features/dashboard/`

## 5. Architecture guard
**Derived learning metrics come from backend APIs; the browser does not recalculate them independently.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 45 — Growth Analysis

## 1. Phase objective
Show whether learning performance is improving over time.

## 2. Source roadmap contract
- Time-series view of mastery evidence to show trend/growth per concept or project.
- Verify: unit test on trend computation given synthetic evidence over time.

## 3. Detailed implementation sequence
1. Build time-series aggregation from append-only mastery evidence.
2. Support concept and project scopes where the API contract allows.
3. Keep the calculation deterministic and based on recorded timestamps/evidence.
4. Render sparse/insufficient histories honestly rather than inventing trends.

## 4. Files / areas expected to change
- `backend/app/services/growth_service.py`
- `frontend/src/features/analytics/`

## 5. Architecture guard
**Growth analytics must derive from evidence/history, not from manually maintained counters.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 46 — Project Analytics

## 1. Phase objective
Provide project-level operational learning analytics.

## 2. Source roadmap contract
- Aggregate stats endpoint (materials count, concepts count, quiz attempts, average mastery,
  tutor usage) + a simple analytics view in the frontend.
- Verify: integration test on the aggregate endpoint.

## 3. Detailed implementation sequence
1. Aggregate material count, concept count, quiz attempts, average mastery, and tutor usage.
2. Return only data belonging to the authorized project/user.
3. Keep aggregate queries efficient and avoid N+1 loops where possible.
4. Expose a simple frontend analytics view.

## 4. Files / areas expected to change
- `backend/app/api/v1/analytics.py`
- `backend/app/services/analytics_service.py`

## 5. Architecture guard
**Analytics is read-model behavior over the existing domain; do not create parallel sources of truth.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 47 — Admin Dashboard

## 1. Phase objective
Add the minimum admin surface with a separate privilege boundary.

## 2. Source roadmap contract
- Admin-only authorization dependency; admin endpoints (user list, usage overview) + minimal
  admin UI gated behind `is_admin`.
- Verify: tests — non-admin forbidden, admin allowed.

## 3. Detailed implementation sequence
1. Reuse the authenticated user identity and check is_admin.
2. Create protected admin endpoints for user list and usage overview.
3. Add an admin-only frontend route.
4. Test both forbidden non-admin access and successful admin access.

## 4. Files / areas expected to change
- `backend/app/dependencies/admin.py`
- `backend/app/api/v1/admin.py`
- `frontend/src/features/admin/`

## 5. Architecture guard
**Admin authorization is separate from ordinary project ownership but still uses the same JWT identity system.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 48 — Error Handling

## 1. Phase objective
Standardize failure behavior across the entire API.

## 2. Source roadmap contract
- Centralized exception handlers (validation errors, auth errors, not-found, rate-limit,
  upstream-AI-failure) with consistent JSON error shape.
- Verify: tests hitting each error path and checking response shape/status code.

## 3. Detailed implementation sequence
1. Define one JSON error envelope with stable machine-readable codes.
2. Map validation, authentication, authorization, not-found, rate-limit, and upstream-AI failures consistently.
3. Keep internal exception details out of public responses.
4. Update tests so clients can rely on status + error code.

## 4. Files / areas expected to change
- `backend/app/core/exceptions.py`
- `backend/app/main.py`
- `backend/app/schemas/errors.py`

## 5. Architecture guard
**Do not let individual routes invent incompatible error payloads.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 49 — Security Hardening

## 1. Phase objective
Close security gaps after the complete feature surface exists.

## 2. Source roadmap contract
- CORS restricted to known frontend origin(s), upload size/type enforcement (revisit Phase
  19), prompt-injection mitigations reviewed end-to-end, AI-cost protection (per-user/
  per-project rate limiting on LLM-calling endpoints), authenticated file access (materials
  only servable to their owning project's users).
- Verify: targeted security tests for each item above.

## 3. Detailed implementation sequence
1. Restrict CORS to documented frontend origins.
2. Re-test upload size/type validation and authenticated material access.
3. Review prompt-injection defenses at extraction, RAG, tutor, quiz, and assessment boundaries.
4. Add per-user/project controls for LLM-calling endpoints.
5. Verify that cross-project resources cannot be accessed through guessed IDs.

## 4. Files / areas expected to change
- `backend/app/core/config.py`
- `backend/app/core/rate_limit.py`
- `backend/tests/security/`

## 5. Architecture guard
**Security hardening must reinforce the existing architecture rather than introduce a different auth/storage/AI architecture.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 50 — Observability & AI Usage

## 1. Phase objective
Make AI usage observable and supportable.

## 2. Source roadmap contract
- Structured logging; AI usage/cost tracking table (tokens/cost per call) for Groq and
  OpenAI Embeddings calls, surfaced in admin analytics.
- Verify: test that a tutor/quiz/assessment call records a usage row.

## 3. Detailed implementation sequence
1. Create structured logs for important request/job lifecycle events.
2. Record provider, operation, model, token usage/cost fields for Groq and OpenAI embedding calls where the providers expose them.
3. Associate usage with user/project where the privacy and schema contract allows.
4. Expose usage in admin analytics without leaking prompts or document contents.

## 4. Files / areas expected to change
- `backend/app/services/ai/usage_tracker.py`
- `backend/app/models/ai_usage.py`

## 5. Architecture guard
**Observability is additive; do not make the product depend on logs for correctness.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 51 — Backend Unit Tests

## 1. Phase objective
Close backend unit-test gaps before end-to-end validation.

## 2. Source roadmap contract
- Fill coverage gaps across auth, authorization, mastery, mismatch, recommendation, and any
  service not yet directly unit-tested in its own phase.
- Verify: `pytest` full run green.

## 3. Detailed implementation sequence
1. Review each backend service for direct deterministic tests.
2. Prioritize auth/security, authorization, parsing/validation, mastery, mismatch, recommendation, chunking, and retrieval helpers.
3. Mock external Groq/OpenAI calls in unit tests.
4. Run the full backend test suite and keep failures actionable.

## 4. Files / areas expected to change
- `backend/tests/unit/`

## 5. Architecture guard
**Tests must validate the architecture already implemented; do not weaken tests to accommodate accidental behavior changes.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 52 — Integration Tests

## 1. Phase objective
Verify boundaries between real backend components and infrastructure.

## 2. Source roadmap contract
- RAG project isolation, concept filtering, similarity threshold behavior, structure
  extraction idempotency/no-partial-persistence, Celery retries/failure handling.
- Verify: `pytest -m integration` green against a test DB/broker.

## 3. Detailed implementation sequence
1. Run tests against a dedicated test database/broker.
2. Verify project isolation in retrieval and RAG.
3. Verify extraction idempotency and no-partial-persistence behavior.
4. Verify Celery retry/failure state transitions.
5. Verify similarity-threshold behavior for supported/unsupported tutor questions.

## 4. Files / areas expected to change
- `backend/tests/integration/`

## 5. Architecture guard
**Integration tests are architecture guards and should fail if a future change breaks isolation or background-processing guarantees.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 53 — Frontend Tests

## 1. Phase objective
Validate frontend behavior at component and feature level.

## 2. Source roadmap contract
- Component/unit tests for auth forms, quiz flow, tutor chat, dashboard.
- Verify: `npm test` green.

## 3. Detailed implementation sequence
1. Test auth forms and route guards.
2. Test quiz answer/confidence interactions.
3. Test tutor message/citation/unsupported states.
4. Test dashboard rendering with mastery/mismatch/recommendation fixtures.
5. Keep network calls mocked at the frontend test boundary.

## 4. Files / areas expected to change
- `frontend/src/**/*.test.*`
- `frontend/src/**/*.spec.*`

## 5. Architecture guard
**Frontend tests should assert the backend API contract, not create a competing client-side business-logic implementation.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 54 — Playwright E2E Setup

## 1. Phase objective
Introduce browser-level end-to-end testing against the real containerized application.

## 2. Source roadmap contract
- Install and configure Playwright against the Dockerized stack.
- Verify: a trivial smoke E2E (load login page) passes.

## 3. Detailed implementation sequence
1. Install and configure Playwright.
2. Launch the stack for E2E runs.
3. Create a smoke test that reaches the login page.
4. Make test data deterministic and isolated.

## 4. Files / areas expected to change
- `frontend/playwright.config.*`
- `frontend/e2e/`

## 5. Architecture guard
**E2E runs must exercise the actual frontend/backend boundary instead of mocking the entire product.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 55 — Complete User Journey E2E Test

## 1. Phase objective
Prove that the architecture works as one user journey.

## 2. Source roadmap contract
- Full journey: register → create space/project → upload PDF → structure appears → ask tutor
  → take quiz → view mastery/recommendation.
- Verify: Playwright suite passes end-to-end.

## 3. Detailed implementation sequence
1. Register a fresh user.
2. Create space and project.
3. Upload a test PDF and wait for processing.
4. Verify structure, then tutor retrieval, quiz submission, and derived mastery/recommendation.
5. Capture failures at the phase boundary rather than skipping broken pipeline stages.

## 4. Files / areas expected to change
- `frontend/e2e/full-journey.spec.*`
- `docs/e2e-runbook.md`

## 5. Architecture guard
**The journey must use the production-shaped API/worker/database path from Docker Compose.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 56 — UI/UX Polish

## 1. Phase objective
Polish the product without changing the functional architecture.

## 2. Source roadmap contract
- Consistency pass across pages (loading states, empty states, error states, responsive
  layout) using shadcn/Tailwind conventions already established.
- Verify: `npm run build` + manual review.

## 3. Detailed implementation sequence
1. Audit every page for loading, empty, error, and success states.
2. Standardize spacing, typography, components, and responsive behavior using existing Tailwind/shadcn conventions.
3. Remove dead UI paths and inconsistent terminology.
4. Run a final frontend build after every polish batch.

## 4. Files / areas expected to change
- `frontend/src/components/`
- `frontend/src/features/`

## 5. Architecture guard
**UI polish must not alter API contracts, data models, worker flow, or derived-learning logic.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 57 — Docker Production Verification

## 1. Phase objective
Prove a clean-machine Docker deployment can reproduce the complete stack.

## 2. Source roadmap contract
- Full `docker compose up` from a clean state; verify all services healthy, migrations run,
  end-to-end journey works against the containerized stack.
- Verify: health checks pass; smoke-run the E2E suite against Docker.

## 3. Detailed implementation sequence
1. Start from a clean database/volume state according to the documented test procedure.
2. Build all containers and run migrations.
3. Verify health checks for API, worker dependencies, Postgres, Redis, and web.
4. Execute the complete E2E journey against the containerized stack.

## 4. Files / areas expected to change
- `docker-compose.yml`
- `docs/docker-runbook.md`

## 5. Architecture guard
**The final runtime remains the five-service Docker architecture defined in Phase 05.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# PHASE 58 — Final Requirement Audit

## 1. Phase objective
Perform a requirement-by-requirement release gate against the source blueprint.

## 2. Source roadmap contract
- Walk the full checklist from the blueprint (feature-by-feature, API-by-API, schema,
  isolation, RAG, pipeline, tutor, quiz, mastery, mismatch, recommendation, analytics, admin,
  error handling, security, Celery/Redis, Docker, all test suites, frontend build).
- Report anything missing or deviating from the blueprint; do not claim completion if
  anything required remains incomplete.

---

## Open items requiring your confirmation before their phase is finalized
1. Mastery formula (Phase 41)
2. Mismatch thresholds (Phase 42)
3. Recommendation scoring weights (Phase 43)
4. Adaptive quiz selection rule (Phase 36)

These will each be presented explicitly, in the blueprint-requirement / technical-issue /
proposed-correction format, when their phase is reached.

## 3. Detailed implementation sequence
1. Review every required feature, API, model, background task, RAG rule, isolation rule, security control, and test suite.
2. Compare implementation against the original blueprint and the phase roadmap.
3. List any missing, partial, or deviating requirement explicitly.
4. Do not mark the project complete merely because the happy-path demo works.

## 4. Files / areas expected to change
- `docs/final-requirement-audit.md`
- `docs/implementation-status.md`

## 5. Architecture guard
**This phase is an audit, not an opportunity to redesign architecture.**

## 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

## 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

---

# Final architecture safety checklist

Use this checklist before accepting **any** architectural change proposed by an AI coding agent.

## Application structure
- [ ] React/Vite frontend remains separate from FastAPI backend.
- [ ] FastAPI routes remain thin; business logic stays in services.
- [ ] Shared models/schemas are not duplicated between unrelated modules.

## Runtime
- [ ] Docker Compose still contains `api`, `worker`, `web`, `postgres`, `redis`.
- [ ] API and worker continue to share the upload volume.
- [ ] Browser continues to call the API through the configured frontend base URL.
- [ ] Worker remains separate from request handling.

## Persistence
- [ ] PostgreSQL remains the relational source of truth.
- [ ] pgvector remains inside PostgreSQL.
- [ ] Alembic remains the schema migration mechanism.
- [ ] Evidence remains append-only where the roadmap requires it.
- [ ] Reprocessing is idempotent where the roadmap requires it.

## AI
- [ ] Groq remains the generation/assessment LLM provider.
- [ ] OpenAI remains the embedding provider.
- [ ] LLM output is validated before persistence.
- [ ] Retrieval is project-scoped in the database query.
- [ ] Uploaded text is treated as untrusted data.
- [ ] Mastery/mismatch/recommendation remain deterministic services.

## Security
- [ ] JWT + Argon2id remain the authentication design.
- [ ] User → Space → Project ownership remains enforced.
- [ ] Authenticated file access remains project-scoped.
- [ ] AI endpoints retain abuse/cost controls.
- [ ] CORS remains restricted to documented frontend origins.

## Verification
- [ ] Backend unit tests pass.
- [ ] Backend integration tests pass.
- [ ] Frontend tests pass.
- [ ] Playwright smoke/E2E tests pass.
- [ ] Docker clean-start verification passes.
- [ ] Final blueprint audit contains no unaddressed required item.

## Explicitly unresolved until their phases

Do **not** pre-decide these silently:
1. Mastery formula — Phase 41.
2. Mismatch thresholds — Phase 42.
3. Recommendation scoring weights — Phase 43.
4. Adaptive quiz selection rule — Phase 36.

The source roadmap intentionally leaves these as confirmation points rather than silently finalizing them. fileciteturn0file0L331-L338

---

# Recommended OpenCode prompt for executing this file

Paste this instruction before asking OpenCode to implement the project:

> You are implementing the AI Study Companion exactly from `ai-study-companion-detailed-opencode-roadmap.md`.
>
> Treat the roadmap's **ARCHITECTURE FREEZE** as a hard constraint. Do not redesign the stack, service boundaries, database strategy, AI providers, background processing architecture, authentication model, project-isolation model, or phase order.
>
> Execute **only one phase at a time**, starting from the first incomplete phase. Before changing code, inspect the existing repository and compare it against the current phase. Implement only the current phase.
>
> After implementation:
> 1. run the required verification,
> 2. run relevant regression tests,
> 3. inspect the diff for architecture drift,
> 4. update `docs/implementation-status.md`,
> 5. report exactly what changed and what passed,
> 6. stop.
>
> Do not continue to the next phase until the user sends `CONTINUE`.
>
> Never invent an unresolved product rule. For Phases 36, 41, 42, and 43, present the proposed behavior clearly and wait for the user's explicit approval before treating it as finalized.
>
> If an implementation choice appears to require an architectural change, **stop before changing architecture**, explain the conflict, identify the exact roadmap constraint involved, and wait for an explicit decision.
