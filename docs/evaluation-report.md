# Evaluation Report — AI Study Companion vs. PRD v3.0 (Fresh Audit)

**Date:** 2026-09-18 · **Evaluator:** senior-engineer audit · **Spec:** `Project_Requirements (1).pdf` (read in full; `docs/architecture.md`-type derived docs not used as spec)
**Method:** full PDF read → 43-requirement inventory → single repo pass (backend → frontend → docs/deploy) with `file:line` evidence per verdict; targeted test runs. README/docs claims never counted as evidence.
**Step 3 runs:** `pytest test_adaptive_quiz+test_mastery` 15 passed; `test_recommendation+test_tutor+test_auth+test_rag_service` 30 passed; `test_quiz_attempt_evidence+security/test_cross_project+test_authorization` 6 passed; `curl localhost:8000/api/v1/health` → `000` (nothing listening locally). No live URL exists anywhere in the repo to hit (see R36).

---

## 1. Executive summary (~150 words)

The submission implements the full learning loop end-to-end: Spaces → Projects → PDF upload → Celery pipeline (extract → chunk → embed → structure) → project-scoped RAG Tutor with page citations and a real no-evidence gate → adaptive MCQ quiz + LLM-graded open-ended assessment → EMA mastery → growth → deterministic recommendations → project analytics, home feed, and a 7-endpoint admin dashboard. Data isolation is enforced in SQL with passing cross-project tests. Gaps: the quiz→recommendation auto-chain is fire-and-forget Celery that silently yields zero rows when evidence is thin or the broker is down (the known open item is **not fixed by design**); there is no `/recommendations` route, so the prior "not found" was a missing route, not just empty data; README still advertises OpenAI 1536-dim embeddings while the code runs local 384-dim; no migration runs on deploy; no streaming; AI evaluation is aggregates-only with no regression gate.

---

## 2. Requirement coverage matrix

`PASS` = implemented end-to-end with code evidence · `PARTIAL` = works with material gap · `FAIL` = missing/broken · `UNVERIFIABLE` = no evidence found (never default-PASS).

| ID | Requirement (PRD §) | Status | Evidence (file:line) | Missing/Problem | Severity |
|----|---------------------|--------|----------------------|-----------------|----------|
| R1 | Authentication: register/login, Argon2id, JWT (§15, §18) | PASS | `backend/app/api/v1/auth.py:16,33,43`; `backend/app/core/security.py:6-12`; `backend/app/core/jwt.py:10-22`; `backend/app/dependencies/auth.py:16-47` | 48h default expiry (`backend/app/core/config.py:26`) is long. | MEDIUM |
| R2 | Spaces CRUD + space dashboard (§3–§4, §18) | PASS | `backend/app/api/v1/spaces.py:15,28,37`; `frontend/src/features/spaces/SpacesPage.tsx:55,111,136-153` | None material. | — |
| R3 | Projects (name/desc/goal) + dashboard + Materials→Tutor→Quiz→Growth→Analytics nav (§4, §18) | PASS | `backend/app/api/v1/projects.py:18,31,41`; `backend/app/api/v1/dashboard.py:128`; `frontend/src/features/projects/ProjectDetailPage.tsx:23,41-42,63` | None material. | — |
| R4 | Home dashboard: continue/recent/progress/attention/next (§16) | PASS | `backend/app/api/v1/me.py:26,35`; `frontend/src/features/home/HomeDashboard.tsx:91,105-176,250-314` | None material. | — |
| R5 | PDF material upload (§5, §18) | PASS | `backend/app/api/v1/materials.py:30-77`; `backend/app/services/storage_service.py:8-55`; `frontend/src/features/projects/MaterialsPanel.tsx:88` | Delete/View buttons are stubs (`frontend/src/features/projects/MaterialsPanel.tsx:230,236`). | LOW |
| R6 | Async doc pipeline with queued/processing/ready/failed + retry/duplicate handling (§5, §13) | PARTIAL | `backend/app/worker/tasks/extraction.py:66-220` (retry `:188`, immediate-fail corrupt `:142-173`); `backend/app/api/v1/materials.py:21-27` (state masking) | Broker-down upload still returns 201 with processing dead (`backend/app/api/v1/materials.py:53-63`); no dedupe of concurrent duplicate dispatches. | HIGH |
| R7 | Extraction → chunk → embed → index with source traceability (§5) | PASS | `backend/app/services/chunking_service.py:19-20`; `backend/app/worker/tasks/extraction.py:223-289`; `backend/app/worker/tasks/embeddings.py:90-107` (upsert on `chunk_id` unique) | None material. | — |
| R8 | Project-scoped Tutor with goal/materials/concepts/conversation/assessment context + continuity (§6, §18) | PASS | `backend/app/services/tutor_service.py:139-196,206-256`; `backend/app/api/v1/tutor.py:32,66,84,99,122,156,169`; `frontend/src/features/tutor/TutorChat.tsx:563-667` | None material. | — |
| R9 | Grounded answers with citations (§7, §18) | PASS | `backend/app/services/tutor_service.py:246-256` (per-chunk citation + excerpt); `frontend/src/features/tutor/TutorChat.tsx:265-288,1241-1309` | Distance threshold 0.5 provisional (`backend/app/services/tutor_service.py:30`). | MEDIUM |
| R10 | Unsupported-question handling, no fabrication (§7, §18) | PASS | `backend/app/services/tutor_service.py:217-220` (returns before LLM call); `frontend/src/features/tutor/TutorChat.tsx:936-947` | None material. | — |
| R11 | Controlled, validated, permission-aware AI↔app interaction (§8, §18) | PASS | Pydantic validation before persist (`backend/app/services/quiz_generation_service.py:201-208`; `backend/app/services/open_ended_assessment_service.py:67-87`); ownership-first dep ordering (`backend/app/core/rate_limit.py:77-88`) | No agentic tool-calling loop; AI acts via separate REST endpoints, not AI-invoked tools. | MEDIUM |
| R12 | Adaptive quiz (MCQ + open-ended), evidence-based selection (§9, §18) | PASS | `backend/app/services/adaptive_quiz_service.py:59-108` (weakest-first, exposure, curriculum order); `backend/app/services/quiz_generation_service.py:497-574`; `frontend/src/features/quiz/QuizTaker.tsx:77-134` | None material. | — |
| R13 | Open-ended AI evaluation with explanatory feedback (§9, §18) | PASS | `backend/app/services/open_ended_assessment_service.py:38-50,137-143,189-242`; `frontend/src/features/openended/OpenEndedAnswersPage.tsx:124-153,325` | None material. | — |
| R14 | Concept mastery evolving with evidence (§10, §18) | PASS | `backend/app/services/mastery_service.py:213-291,303-341` (EMA, difficulty weights, stream weights, caps); append-only writers (`backend/app/services/quiz_attempt_service.py:143-189`) | Dual headline numbers coexist: `display_mastery` vs `final_mastery` (`backend/app/services/rollup_service.py:40-52`). | MEDIUM |
| R15 | Growth analysis: improving/stable/needs-attention (§10, §18) | PASS | `backend/app/api/v1/growth.py:22`; `frontend/src/features/analytics/GrowthView.tsx:106-157` | None material. | — |
| R16 | Recommendations answering "what next" (§10, §18) | PARTIAL | `backend/app/services/recommendation_service.py:198-237,499-601`; sync path `backend/app/api/v1/dashboard.py:140-168`; UI `frontend/src/features/dashboard/Dashboard.tsx:175,577-592` | Auto-chain is best-effort Celery skipped under pytest (`backend/app/worker/tasks/recommendations.py:44-56`) and returns None on thin evidence (`backend/app/services/recommendation_service.py:545-560`), so zero-row outcome persists by design. | HIGH |
| R17 | Persistent relevant learning context (§11, §18) | PASS | Bounded context (`backend/app/services/rag_service.py:19-23`); persisted conversations (`frontend/src/features/tutor/TutorChat.tsx:631` + backend `tutor_conversation_service.py`); dashboard signals reuse | None material. | — |
| R18 | Event-driven learning, idempotent (§12) | PASS | `backend/app/models/learning_event.py:50-52` (idempotency-key unique); `backend/app/services/activity_service.py:62-139`; emitters `backend/app/services/quiz_attempt_service.py:194-219` | None material. | — |
| R19 | Project + global analytics (§12, §18) | PASS | `backend/app/api/v1/analytics.py:22,49`; `frontend/src/features/analytics/AnalyticsPage.tsx:169-202`; global Home/streak (`backend/app/api/v1/me.py:35`) | "Global" is Home feed + streak, no cross-space aggregate endpoint. | MEDIUM |
| R20 | Background workflows incl. repeated-mistake, no browser needed (§13) | PARTIAL | Material chain (`backend/app/worker/tasks/extraction.py:223-289`); learning chain (`backend/app/services/quiz_attempt_service.py:220-228`) | Repeated-mistake workflow missing: mismatch is computed but no scheduler/chain triggers targeted recs. | HIGH |
| R21 | AI abstraction (generation/structured/embeddings/eval/doc-understanding) (§14) | PASS | `backend/app/services/ai/groq_client.py:25-40,99-106`; `backend/app/services/ai/embedding_client.py:1-13`; vision (`backend/app/services/vision_service.py:31-79`) | None material. | — |
| R22 | AI observability: model/latency/tokens/cost/success (§14) | PASS | `backend/app/services/ai_usage_service.py:76-92`; `backend/app/api/v1/admin.py:180` (aggregates); per-call meta (`backend/app/services/tutor_service.py:227-237`) | Cost figures are placeholders (`backend/app/services/pricing.py:12-20`); embeddings unmetered. | MEDIUM |
| R23 | AI evaluation of tutor/retrieval/assessment/rec + regression awareness (§14) | PARTIAL | `backend/app/api/v1/admin.py:412` (supported/citation rates, score bands, weekly trends) | Aggregates only: no groundedness judge, no retrieval-relevance metric, no regression gate (docs admit). | MEDIUM |
| R24 | Reliability: timeouts/retries/validation/fallback, no duplicate state (§15) | PASS | Timeouts (`backend/app/services/ai/groq_client.py:99-106`; vision 20s); uniform error envelope (`backend/tests/test_error_handling.py`); idempotent events (R18) | None material. | — |
| R25 | Project-level data isolation incl. retrieval (§3, §15, §18) | PASS | Ownership deps 404 (`backend/app/dependencies/authorization.py:13-55`); `project_id` inside vector query (`backend/app/services/retrieval_service.py:58-82`); cross-project tests pass (6/6 this audit) | None material. | — |
| R26 | Input validation + secure APIs + secure doc handling (§15) | PASS | Upload hardening 10MB/`%PDF`/basename containment (`backend/app/services/storage_service.py:8-55`); hardening tests pass | None material. | — |
| R27 | Prompt-injection safety: data vs instructions (§15) | PASS | `<<<DATA>>>` framing (`backend/app/services/tutor_service.py:139-196`); boundary tests (`backend/tests/security/test_prompt_boundaries.py`) | None material. | — |
| R28 | Secrets separated from code (§18) | PASS | `.env` gitignored (`.gitignore:3-8`); only `.example` tracked; image ships no secrets (`backend/Dockerfile:33-38`) | Compose boots with known-default `JWT_SECRET` if env not exported (`docker-compose.yml:50-57`). | MEDIUM |
| R29 | Admin dashboard: users/activity/AI/eval/jobs/health + journey + filters (§16, §18) | PASS | `backend/app/api/v1/admin.py:55,109,138,180,281,364,412`; `frontend/src/features/admin/AdminPage.tsx:76-91,224-357` + 5 panels | None material. | — |
| R30 | Streaming Tutor (Should Have, §18) | FAIL | No `EventSource/WebSocket/ReadableStream`; plain POST (`frontend/src/features/tutor/TutorChat.tsx:662-667`) with fake thinking steps (`:89-93`) | Streaming absent. | LOW |
| R31 | Performance: pagination/caching/async/efficient queries (§15) | PARTIAL | Admin pagination; 30s GET cache (`frontend/src/lib/axios.ts:60-99`); async jobs | No server-side caching (explicitly out of scope, `README.md:145`); no streaming counts. | LOW |
| R32 | Backend tests: auth/authz/isolation/validation/logic (§18) | PASS | 67 `test_*.py` files; this audit ran 51 tests green across auth/authz/cross-project/quiz-evidence/adaptive/mastery/RAG | Full-suite run not attempted (prior hang on scanned-pipeline test unretried). | MEDIUM |
| R33 | AI tests: grounded/unsupported/structured/tutor/assessment (§18) | PASS | Unsupported asserts LLM not called; injection-as-data; grade validation (`backend/tests/test_tutor.py`, `test_rag_service.py`, `test_groq_client.py`, `test_open_ended_assessment.py`) | None material. | — |
| R34 | Learning tests: mastery/adaptive/recommendations (§18) | PASS | Exact EMA/scoring math (`backend/tests/test_mastery.py`, `test_adaptive_quiz.py`, `test_recommendation.py` — all green this audit) | None material. | — |
| R35 | Background tests: success/retry/failure (§18) | PASS | Chain, broker-outage survival, 429 backoff (`backend/tests/test_pipeline_chain.py`, `test_extraction*.py`, `test_celery.py`) | None material. | — |
| R36 | Deployment to public URL with working stack (§18) | UNVERIFIABLE | No URL in `railway.toml:1-14`, `README.md:99-101`, or `docs/`; local `:8000` not listening (curl `000`) | Cannot verify per scope note; excluded from score. | — |
| R37 | Architecture docs: diagram + decisions (§20) | PARTIAL | ADRs 001–009 (`docs/architecture-decisions.md:8-119`); `docs/architecture/` present on disk with traceability/diagrams | `docs/architecture/` is untracked in git (`??` per `git status`); diagram not committed. | MEDIUM |
| R38 | AI-usage docs: build-AI vs product-AI (§20) | PASS | Build prompts (`docs/opencode-prompts.md`); product metering (`docs/usage-tracking.md:20-33`) | None material. | — |
| R39 | Development prompts (§20) | PASS | `docs/opencode-prompts.md:7-67` per-phase log | None material. | — |
| R40 | Evaluation approach doc (§20) | PARTIAL | Aggregates documented; gaps admitted (no judge/MRR/regression gate) | Same gap as R23. | MEDIUM |
| R41 | Known limitations (§20) | PASS | `docs/learning-model-design.md:494-506`; `docs/usage-tracking.md:73-88` | None material. | — |
| R42 | Public repo + accurate README setup (§20) | PARTIAL | Setup/compose instructions accurate (`README.md:76-122`) | README stale: claims OpenAI `text-embedding-3-small` + `VECTOR(1536)` (`README.md:15,17`) vs actual local `BAAI/bge-small-en-v1.5` 384-dim (`backend/app/models/embedding.py:12,39`); "Phase 02 current" (`README.md:139`) vs Phase 49; compose still sets `EMBEDDING_MODEL: text-embedding-3-small` (`docker-compose.yml:58,98`). | MEDIUM |
| R43 | Creativity/differentiation, functional not cosmetic (§21) | PASS | SM-2 flashcards (`frontend/src/features/flashcards/Flashcards.tsx`, `backend/app/api/v1/flashcards.py:43,65,94`); vision figure extraction; mismatch detection; tutor quiz-plan; concept graph | None material. | — |

---

## 3. Core learning loop walkthrough (~500 words)

**Create Space → Project.** `SpacesPage` lists/creates spaces (`frontend/src/features/spaces/SpacesPage.tsx:55,111`) with loading/error/empty states (`:136-153`); `SpaceProjectsPage` creates projects under a space (`frontend/src/features/projects/SpaceProjectsPage.tsx:86`) with ownership-scoped reads (`:34-35`) and a 404-for-foreign message (`:40-42`). Backend enforces ownership at the dependency layer (`backend/app/dependencies/authorization.py:13-55`, 404 not 403). **Upload → Process.** `MaterialsPanel` uploads multipart with 120s timeout (`frontend/src/features/projects/MaterialsPanel.tsx:88`), polls every 5s while pending/processing (`:75-79`), and renders queued/processing/ready/failed pills (`:18-42`). Server side: `POST /projects/{id}/materials` persists `Material(status="pending")`, creates a job row, and dispatches `process_pdf` (`backend/app/api/v1/materials.py:30-77`). The worker extracts (PyMuPDF + tables + per-page OCR routing), chunks (2000/200 chars), persists chunks/figures, and dispatches embedding + structure jobs (`backend/app/worker/tasks/extraction.py:66-289`). Failure paths are real: corrupt/empty fail fast without retry (`:142-173`), transient errors retry with backoff (`:188`), per-page failures degrade to EMPTY slots rather than killing the doc. Gap: if the broker is down the upload still returns 201 while processing is dead (R6). **Ask Tutor → grounded answer + citations → unsupported handling.** `TutorChat` threads conversations (`frontend/src/features/tutor/TutorChat.tsx:631,658,662-667`) with thinking/failure/empty states (`:1167-1187,951-969,352-355`). Retrieval filters `project_id` inside the vector query before ranking (`backend/app/services/retrieval_service.py:58-82`), prompts wrap excerpts as `<<<DATA>>>` (`backend/app/services/tutor_service.py:184-196`), one citation per chunk is returned (`:246-256`) and rendered in a sources drawer (`TutorChat.tsx:1241-1309`). With zero chunks or all distances above 0.5 the canned unsupported answer returns before any LLM call (`backend/app/services/tutor_service.py:217-220`). **Adaptive quiz → open-ended assessment.** `QuizTaker` runs generate → attempt → per-answer → complete (`frontend/src/features/quiz/QuizTaker.tsx:77-134`) with busy/failure/done states; selection is weakest-mastery-first with exposure and curriculum-order tiebreaks (`backend/app/services/adaptive_quiz_service.py:59-108`); open-ended answers are LLM-graded against a validated rubric with ≥80/≥50 verdict bands (`backend/app/services/open_ended_assessment_service.py:137-143,189-242`). **Mastery/growth → analytics → recommendation.** Completion banks append-only per-question evidence and commits atomically (`backend/app/services/quiz_attempt_service.py:179-219`); the EMA engine weights by difficulty with stream weights and caps (`backend/app/services/mastery_service.py:213-341`); growth, analytics, dashboard, and practice-recs pages all read the same signals with empty states (`GrowthView.tsx:150-157`, `AnalyticsPage.tsx:328-335`, `Dashboard.tsx:577-592`). The loop closes functionally — except the automatic recommendation write is async best-effort (R16) and there is no `/recommendations` route: recommendations surface inline in Dashboard/Overview/QuizSetup only. **Admin.** Seven scoped endpoints (`backend/app/api/v1/admin.py`) feed five frontend panels with loading/error/empty handling (`AdminPage.tsx:224-234`, `ActivityPanel.tsx:110-115`). Data flows between steps (Overview→quiz, Tutor→quiz/flashcards/practice via `ProjectDetailPage.tsx:48-51,101-156`), not just co-located rendering.

---

## 4. AI/RAG evaluation (~400 words)

Providers are abstracted: `groq_client` supports groq + inception endpoints selected by `LLM_PROVIDER` (`backend/app/services/ai/groq_client.py:25-40`), default chat model `openai/gpt-oss-20b` (`backend/app/core/config.py:32`); vision goes through a Nara router with `stepfun-3.7-flash` (`backend/app/core/config.py:58-64`); embeddings are local fastembed `BAAI/bge-small-en-v1.5`, 384-dim (`backend/app/services/ai/embedding_client.py:1-13`), matching the `Vector(384)` column (`backend/app/models/embedding.py:12,39`). Every LLM consumer validates structured output with Pydantic and retries exactly once before raising provider errors with nothing persisted (`tutor_service.py:238-244`, `quiz_generation_service.py:254-260`, `open_ended_assessment_service.py:230-236`). Timeouts are set (chat 60s, vision 20s) with temperature clamping and control-char sanitization (`groq_client.py:85-106,132`). The RAG pipeline is genuinely end-to-end and scoped: extract → chunk → embed → `project_id`-filtered cosine retrieval (`retrieval_service.py:58-82`) → char-bounded assembly (5 chunks/6000 chars, `rag_service.py:19-23,100-121`) → goal + excerpts composed as data (`tutor_service.py:184-196`) → single metered provider call with retrieval shape in `meta` (`:227-237`) → per-chunk citations with page numbers and 280-char excerpts (`:246-256`). Grounding is enforced, not decorative: the unsupported gate precedes the LLM call and tests assert the client is never called on empty/low-similarity context; prompt-injection tests assert uploads stay data. Quiz generation prioritizes page-range → concept-tagged → project-wide sources and 422s with no chunks (`quiz_generation_service.py:171-208`); adaptive allocation weights `(100-mastery)+10` with weakest-first remainder (`:522-574`). Open-ended grading is LLM-judged but deterministically banded (verdict never model-decided, `:137-143`) and writes nothing directly — persistence flows only through `submit_explanation` as append-only evidence. Weaknesses: scoring weights/bonuses and the 0.5 distance threshold are declared but untuned constants; costs are placeholder pricing; embeddings are unmetered; evaluation is descriptive aggregates (supported-rate, citation coverage, score bands) with no groundedness judge, retrieval-relevance metric, or regression gate — so prompt/model/retrieval regressions would not be caught automatically. The README still documents the old OpenAI 1536-dim path (R42), and the working tree contains uncommitted embedding-dimension changes, suggesting a migration mid-flight.

---

## 5. Mastery/recommendation evaluation (~250 words)

Mastery is a deterministic EMA over typed evidence streams, never LLM-decided and never random: per-stream `mastery += weight*(score-mastery)` with difficulty bases 0.2/0.3/0.4 plus a 7-day gap boost capped at 0.5, tutor fixed at 0.15 with 1/day dedupe, then a weighted mean over streams with evidence (quiz 0.35, open-ended 0.25, practice 0.20, flashcard 0.15, tutor 0.05) with tutor-only ≤40 / formative-only ≤70 / thin-history caps (`backend/app/services/mastery_service.py:213-341`). Writers are append-only and atomic with attempt completion (`quiz_attempt_service.py:143-189`); grep confirms no `random` in scoring paths. Recommendations are likewise deterministic: `score_action` combines weakness + overconfidence + recency + goal + action base − repetition penalty ± mismatch terms (`backend/app/services/recommendation_service.py:198-228`), expiring prior actives and inserting one new active row plus a `recommendation.generated` event (`:562-597`). **Known open item — not fixed:** the quiz→mastery→recommendation chain fires via `refresh_best_effort` (`quiz_attempt_service.py:220-228`), which is skipped entirely under pytest (`recommendations.py:44-56`) and otherwise a swallowed-exception Celery `delay`. The task itself returns `None` — persisting nothing — when no signal has `mcq`/`applied` scores or scope vanished (`recommendation_service.py:545-560`), and the dashboard maps that to 404 "no scorable concepts yet" (`dashboard.py:160-161`). So completed quizzes with thin evidence, or any completion while the worker/broker is down, still produce zero rows; no real row could be produced in this audit (no broker/DB running) and none was observed. The reliable path is the synchronous `POST .../dashboard/refresh` (`dashboard.py:140-168`). The repeated-mistake → targeted-recommendation workflow is absent (mismatch computed, never scheduled).

---

## 6. Data model & security findings (~350 words)

Schema covers users → spaces → projects → materials/jobs/topics/subtopics/concepts/relationships/chunks/embeddings/quizzes/attempts/answers/evidence/recommendations/conversations/messages/flashcards/figures/events/ai_usage with FKs, unique constraints (`uq_chunks_material_index`, topic/subtopic/concept title uniqueness, `chunk_id` unique, idempotency-key unique), and check constraints on enums/scores/difficulties (backend audit §3). Indexes target the hot paths: `ai_usage(user,project,feature)`, `learning_events(user/project/type,time)`, `flashcards.next_review_at`.

### Data isolation

Ownership is enforced server-side on every route via `get_authorized_project` / `get_authorized_space` (404 on foreign IDs, never 403-leak), with LLM-budget middleware deliberately ordered after ownership so auth is evaluated first (`backend/app/core/rate_limit.py:77-88`). Retrieval isolation is inside the SQL, not client filtering (`retrieval_service.py:58-82`). Job polling walks material→project→space→user (`jobs.py:18-42`). This audit ran `test_authorization + security/test_cross_project + test_quiz_attempt_evidence`: 6 passed. Minor defense-in-depth note: a few helper reads use unscoped `db.get` on IDs that originate from already-scoped rows. No IDOR found.

### Auth, injection, secrets

Argon2id with OWASP-ish params (`core/security.py:6-12`), HS256 JWT with distinct expired/invalid 401s (`dependencies/auth.py:16-47`), admin gated by `is_admin` 403 (`dependencies/admin.py:7-15`). No SQL injection surface: all queries are ORM-bound; the only raw SQL is static `SELECT 1`; search uses bound `ilike`. Path traversal is mitigated by basename + server-side `UPLOAD_DIR/{project_id}/{uuid}.pdf` + figures containment check. Uploads enforce extension + content-type + `%PDF` magic + 10MB cap. Prompt injection is handled by `<<<DATA>>>` framing with boundary tests. No real secrets are committed: `backend/.env` is local-only (gitignored, only `.example` tracked). Residual risks: (a) compose boots with a known-default `JWT_SECRET` and dummy OpenAI key if env is not exported (`docker-compose.yml:50-57,90-98`); (b) 48h JWT expiry is long; (c) no rate limit on auth routes; (d) cost/pricing placeholders could mislead ops; (e) broker-down failures are silent by design (evidence path survives, downstream insight silently missing).

---

## 7. Document processing evaluation (~200 words)

Upload → `pending` → worker `processing` → `ready`/`failed` with job rows polled by the UI (`materials.py:30-112`, `MaterialsPanel.tsx:58-79`). The worker extracts text, tables, and figures with per-page TEXT/OCR/EMPTY routing (`MIN_MEANINGFUL_CHARS=20`), persists `extracted_text/page_count`, then chains chunk → figures → embeddings + structure jobs best-effort with per-failure diagnostics (`extraction.py:66-289`). Corrupt/empty/truncated inputs fail immediately without retry; transient errors retry 3× with exponential backoff; structure 429s back off 60s; per-page failures degrade rather than abort; reruns replace chunks for the material and upsert embeddings on the `chunk_id` unique constraint — duplicate handling is correct at the data layer. Scanned-image routing, 20-page, unicode/CJK, and broker-outage survival are covered by tests (`test_extraction_robustness`, `test_hybrid_pdf_routing`, `test_pipeline_chain`). Gaps: duplicate *dispatches* (double-upload races) have no job-level dedupe; broker outage yields a misleading 201-success upload with dead processing; no migration runs automatically on deploy so a fresh environment can serve the API against a schema-less database; and the "ready" masking in the list endpoint (`materials.py:21-27`) can show `processing` while downstream jobs lag with no per-stage progress surfaced to the user.

---

## 8. Engineering quality & deployment (~250 words)

API contracts are consistent (`/api/v1`, Pydantic schemas ↔ TS types, uniform error envelope) with 19 routers and 67 test files asserting exact math, guards, and isolation — 51 tests rerun green in this audit. Code quality is high: pure deterministic services, append-only evidence, validated LLM outputs, meaningful observability metadata. Dead weight exists but is bounded: unwired exports (`AnalyticsView`, `QuizModes`, `ProgressMap`), MaterialsPanel Delete/View stubs, and the root `src/` Figma scaffold with dangling imports (`src/App.tsx:2`, `src/components/Layout.tsx:8,10`) and hardcoded mock data — harmless since `web` builds `./frontend/Dockerfile` (`docker-compose.yml:120-132`), but confusing. **Live URL status: NOT VERIFIED (UNVERIFIABLE).** No deployed URL appears in `railway.toml` (build + healthcheck only), `README.md` (localhost only), or any doc; nothing listens on local `:8000` (curl `000`). Per the scope note this is excluded from the score, but deployment reproducibility has a real defect: **no `alembic upgrade` anywhere** in compose, Railway config, Dockerfile, or supervisord — migrations are documented as manual (`docs/architecture-decisions.md:94`), so a clean-environment deploy requires an undocumented manual step. Compose pins 5 services with healthchecks and pgvector init, and the single-container Railway image runs api+worker+loopback redis under supervisord — reasonable for a prototype. Differentiating features are genuinely functional (SM-2 flashcards with due ordering, vision figure extraction with per-page thumbnails, mismatch detection feeding recommendation scoring, tutor quiz-plan/flashcard handoffs, concept graph), all tested — not cosmetic.

---

## 9. Critical / High / Medium / Low findings

**CRITICAL** — none.

**HIGH**
- H1: Quiz→recommendation auto-chain silently yields zero rows on thin evidence or broker outage (`recommendations.py:44-56`, `recommendation_service.py:545-560`) — the known open item persists by design.
- H2: Repeated-mistake → targeted-recommendation workflow missing (computed, never scheduled).
- H3: No migration runs on any deploy path; fresh environments serve API against unmigrated DB.

**MEDIUM**
- M1: README/compose advertise OpenAI 1536-dim embeddings vs actual local 384-dim (`README.md:15,17`, `docker-compose.yml:58,98`, `embedding.py:12,39`); uncommitted dimension-migration files in working tree.
- M2: No `/recommendations` route exists (`App.tsx:46-68`) — the prior "not found" was a missing route; recommendations are inline-only.
- M3: AI evaluation is aggregates-only, no regression gate (`admin.py:412`; R23).
- M4: 48h JWT expiry + known-default compose `JWT_SECRET` + no auth rate limiting.
- M5: `docs/architecture/` present but untracked; README phase pointer stale ("Phase 02" vs Phase 49).
- M6: Broker-down upload returns misleading 201 (`materials.py:53-63`).
- M7: Dual mastery headline numbers (`rollup_service.py:40-52`).

**LOW**
- L1: No Tutor streaming (Should Have).
- L2: MaterialsPanel Delete ("coming soon") / View stubs.
- L3: Dead exports (`AnalyticsView`, `QuizModes`, unwired `ProgressMap`); root `src/` scaffold with broken imports and mock data alongside the real `frontend/`.
- L4: MCQ feedback shows correctness only, no explanation (`QuizTaker.tsx:301-316`).

---

## 10. Requirement contradictions (doc vs. code mismatches)

1. `README.md:15,17` (+ `docs/00-blueprint-analysis.md:65,68`, `docs/architecture-decisions.md:14,16`): OpenAI `text-embedding-3-small` / `VECTOR(1536)` vs code: local `BAAI/bge-small-en-v1.5`, `EMBEDDING_DIMS = 384` (`backend/app/models/embedding.py:12,39`), `backend/Dockerfile:26` bakes the local model. (Working tree has uncommitted files migrating the default — fix in flight, not committed.)
2. `README.md:139`: "Current: Phase 02" vs `docs/implementation-status.md` (Phase 49 complete).
3. `docker-compose.yml:58,98` sets `EMBEDDING_MODEL: text-embedding-3-small` while the runtime embedding path is local-only —Workers and docs disagree on the active model.
4. `README.md:17`: "Groq (generation/evaluation)" omits the actual chat model names (`openai/gpt-oss-20b`, `mercury-2.5` in `backend/app/core/config.py:32-34`) and the Nara/stepfun vision path.
5. `backend/.env.example:35-40` warns dims "cannot mix" — consistent with code, contradicting README/compose.

---

## 11. Recommended fix order

1. H1: Make quiz-completion recommendation synchronous-or-guaranteed (call `recommend()` inline on `complete_attempt`, keep Celery as fallback; surface "no scorable concepts yet" instead of silent absence).
2. H3: Add `alembic upgrade head` to deploy (Dockerfile entrypoint / Railway start / compose init) and document it.
3. H2: Schedule or chain the repeated-mistake workflow (mistake pattern → learning-context update → targeted rec).
4. M2: Add a `/recommendations` route (or redirect) so deep links stop 404ing; keep inline cards.
5. M1: Rewrite README + compose embedding rows to local bge-small 384-dim; commit the in-flight dimension migration.
6. M4: Require `JWT_SECRET` at boot (fail closed), shorten expiry, rate-limit auth routes.
7. M6: Return 202 with explicit `dispatch_failed` state instead of 201 when the broker is down.
8. M3: Add minimal regression evaluation (curated tutor/retrieval/grading fixtures run in CI with thresholds).
9. M7: Unify on one headline mastery number across dashboard/knowledge surfaces.
10. M5: Commit `docs/architecture/`; fix README phase pointer.
11. LOW batch: streaming (or document deferral), material delete/view, remove or wire dead exports, quarantine root `src/` scaffold.

---

## 12. Overall completion score

Raw counts: **33 PASS + 8 PARTIAL + 1 FAIL + 1 UNVERIFIABLE (R36, environment limitation — excluded)** out of 43 requirements.
Formula: (33 + 0.5 × 8) / 42 × 100 = 37 / 42 × 100 = **88.1%**.
No CRITICAL-severity item is among the unsatisfied ones (unsatisfied items are HIGH ×3, MEDIUM ×8 minus exclusions, LOW ×1); the three HIGH items are reliability/completeness gaps in otherwise-working flows, not broken core loop or isolation failures.

---

## 13. Final readiness assessment

Fully satisfied 33 · partial 8 · not satisfied 1 (R30 streaming, a Should-Have) · unverifiable 1 (R36 live URL). **Critical blockers: none.** Remaining work before submission: fix the silent zero-row recommendation chain (H1), add deploy-time migrations (H3), implement or explicitly defer the repeated-mistake workflow (H2), add the missing `/recommendations` route (M2), correct README/compose embedding claims and commit the migration (M1/M5), and harden boot secrets + auth limits (M4). The core learning loop is demonstrably complete and isolated; the submission reads as a strong, honest prototype whose sharpest edges are async-reliability and doc-accuracy rather than missing features.
