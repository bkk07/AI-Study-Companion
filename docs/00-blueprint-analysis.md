# 00 — Blueprint Analysis — AI Study Companion

**Blueprint:** `ai-study-companion-blueprint.md` — Revised Blueprint v2 (Prototype scope: 3–4 day Full Stack AI Engineer candidate challenge)
**Detailed roadmap:** `ai-study-companion-detailed-opencode-roadmap.md` (58 phases, architecture-freeze contract)
**Date:** 2026-09-15
**Phase:** 01 — Repository & Blueprint Analysis
**Status:** Complete (documentation-baseline only; no product logic)

---

## 1. Purpose

Establish the blueprint as the immutable architectural contract before any code is written. This document extracts the domain scope, mandated stack, service boundaries, security boundaries, exclusions, hard rules, and unresolved ambiguities from the blueprint, and records when each ambiguity will be resolved per the phased roadmap. No product behavior is invented here.

---

## 2. Executive Summary

The AI Study Companion is a **project-scoped learning partner**. Uploaded PDFs are turned into a structured learning map `Topic → Subtopic → Concept` (the leaf `concept_id` is the system's unit of mastery). An append-only `mastery_evidence` table closes the core learning loop:

```
Learning Action (MCQ, open-ended, Explain-It-Back, confidence 1-5)
  -> Learning Evidence (append-only, scored)
  -> Mastery Engine (mcq_mastery / applied_mastery per concept)
  -> Confidence Engine (calibration, not a mastery input)
  -> Mismatch Detection (deterministic)
  -> Decision Engine (deterministic)
  -> Recommended Next Action (ask_tutor | targeted_quiz | explain_back | review_material | exam_mode)
  -> Tutor / Quiz / Explain-Back / Review
  -> More Learning Evidence
```

The differentiator is **deterministic mismatch detection** (`mcq_mastery` >> `applied_mastery`) and a deterministic recommendation engine — the LLM is used only for grounded Tutor answers, quiz generation, and free-text evaluation, never to decide mastery or next steps.

---

## 3. Domain Scope (from Blueprint §1–3, §10–17)

### 3.1 Learning Hierarchy
- Uploaded material → PyMuPDF extraction → Groq structured extraction `LearningStructureExtraction` (`Topic → Subtopic → Concept`) → persistence with denormalized `project_id` on all three tables → chunking (~500–700 tokens, page-aware) → embeddings → `document_chunks` (project_id denormalized, optional best-effort topic/subtopic/concept FKs).
- Empty structure (0 topics) is a valid `ready` state, not a failure.

### 3.2 Core Engines
- **Mastery Engine** (`mastersy`/`mastery_evidence` + `concept_mastery`): two independent scores per `(user, project, concept)` — `mcq_mastery` (recognition) and `applied_mastery` (open_ended + explain_back). Weighted-average update `current + weight*(score-current)`, weight by difficulty + recency boost, no LLM involvement.
- **Confidence Engine**: captured in the same request as the answer; `confidence_records` with explicit nullable FKs + `actual_correct` (NULL until async evaluation for open-ended/Explain-It-Back). `confidence_accuracy` over evaluated records only; feeds recommendation, not mastery.
- **Explain-It-Back**: triggered by correct-streak (3), manual, or mismatch probe; evaluated by Groq grounded in concept chunks.
- **Mismatch Engine**: primary `mcq_high_applied_low` (gap ≥25pp, ≥3 MCQ evidence + ≥1 applied, Part 13), secondary `overconfident`/`underconfident` from `ConfidenceService`; priority `mcq_high_applied_low` > `overconfident` > `underconfident`.
- **Adaptive Quiz**: concept priority = weakness + low-evidence bonus + mismatch bonus − overrepresented penalty; difficulty adaptive (`easy <40, medium <75, hard`).
- **Exam Mode**: config of same quiz engine (`practice=5q` vs `exam=15q`, spread + deferred feedback).
- **Decision Engine**: 5 actions only; deterministic scoring per concept+action with mismatch bonuses/penalties, visible `reasoning`.
- **Growth Analysis**: read-time aggregation over `mastery_evidence`, drill-down by concept/subtopic/topic.
- **RAG/Tutor**: project-scoped `WHERE project_id` inside vector query before ranking; threshold → unsupported; citations; concept detection opportunistic, never guessed.

### 3.3 Analytics / Admin / Activity
- Project analytics + minimal global analytics; lightweight read-only admin dashboard; `activity_events` + `ai_usage` + `background_jobs` for observability.

---

## 4. Mandated Stack (Architecture Freeze — do not substitute)

| Layer | Technology | Notes |
|-------|------------|-------|
| Frontend | React + Vite + TypeScript + Tailwind CSS + shadcn/ui + React Router + Axios | Browser → `localhost:8000` FastAPI; never direct to DB/AI/Redis |
| Backend | Python + FastAPI + Pydantic + SQLAlchemy + Alembic | Thin routes → service layer; `require_project_access` per project route |
| Database | PostgreSQL + pgvector (`VECTOR(1536)`) | Single relational source of truth; pgvector inside Postgres, no separate vector DB |
| Auth | JWT (HS256, 60 min, `JWT_SECRET`) + Argon2id | `hash_password` / `verify_password` centralized |
| AI generation | Groq | LLM for Tutor, quiz gen, structure extraction, free-text evaluation; structured JSON → Pydantic validation |
| Embeddings | OpenAI `text-embedding-3-small` | 1536 dims, `embedding` column |
| Documents | PyMuPDF | Extraction in worker only; content-sniffed MIME |
| Background | Celery + Redis | Broker + result backend; `api`, `worker` share `uploads` volume |
| Runtime | Docker Compose — exactly 5 services: `api`, `worker`, `web`, `postgres`, `redis` | Browser→`localhost:8000`; containers→service names `postgres`/`redis`; shared `uploads:/data/uploads` |

---

## 5. Fixed Service Boundaries

1. `Browser → FastAPI` only (JWT bearer), via `VITE_API_BASE_URL`.
2. `FastAPI → PostgreSQL/Redis + Celery dispatch`; long-running work (extract/chunk/embed/structure/evaluate/recompute) via Celery.
3. `Worker → shared upload volume (`/data/uploads`) + PostgreSQL/Redis + AI providers`.
4. `PostgreSQL` is relational source of truth; `pgvector` extension inside it.
5. `project_id` (and `user_id`→`space_id`→`project_id` chain) is the isolation boundary for all study data, chunks, retrieval, Tutor, quizzes, mastery, recommendations, analytics.
6. Uploaded document text and LLM output are **untrusted data** — never executed, always validated (Pydantic) before persistence; `mastery_evidence`/`concept_mastery` recomputed deterministically.
7. Alembic owns schema after Phase 09; no manual DB drift.

---

## 6. Database Schema Contract (Blueprint §7)

**Conventions:** UUID PKs `gen_random_uuid()`, `created_at`/`updated_at` timestamps; every project-scoped table carries denormalized `project_id` for single-filter isolation.

**Tables (29 in v2):** `users`, `spaces`, `projects`, `materials` (status `queued|processing|ready|failed`), `topics`, `subtopics`, `concepts`, `document_chunks` (VECTOR 1536 + ivfflat index), `conversations`, `messages` (citations JSONB, `is_unsupported`, nullable `concept_id`), `quizzes`/`quiz_questions`/`quiz_attempts`/`quiz_answers`, `assessments`/`assessment_answers`, `explain_back_attempts`, `confidence_records` (3-way exclusive FK, `actual_correct` nullable), `concept_mastery` (unique `user+project+concept`, `mismatch_active/type`), `mastery_evidence` (append-only), `recommendations`, `activity_events`, `ai_usage`, `background_jobs`.

Isolation indexes on `user_id`/`project_id`/`concept_id`; `document_chunks.embedding` ivfflat with `lists=100`; `confidence_records` check ensures exactly one FK set.

---

## 7. Security Boundaries

- JWT short-lived (60 min), no refresh rotation at prototype scope; `require_project_access` (404, not 403 to avoid leaking existence) + `require_admin`.
- Argon2id passwords, never plaintext/reversible.
- Project isolation at service layer via explicit `WHERE project_id=` filters (tested with foreign IDs).
- Uploads in Docker volume outside web-servable path, authenticated download only; size-capped + content-sniffed (not extension).
- RAG `project_id` filter inside vector query before ranking.
- AI has no DB access; chunk text passed as delimited reference data with instruction not to obey instructions inside it; PyMuPDF in worker only; CORS locked to frontend origin; rate-limit on `auth/*` + `tutor/message`.

---

## 8. Explicit Exclusions (do not build)

Blueprint §3 out-of-scope: flashcards, standalone AI notes, concept dependency maps, study planner, spaced repetition, audio/video, collaboration, gamification, notifications, exam readiness score, live lecture features, LangChain/LangGraph/agent frameworks, Kafka/RabbitMQ, microservices, separate vector DB, object storage (S3 is production note, not prototype), ad hoc Redis caching.

---

## 9. Hard Rules Extracted

- Single five-service Compose architecture; do not collapse `api`+`worker` or add a third app service.
- Shared upload volume mounted identically in `api` and `worker`; `materials.file_path` resolves identically in both.
- Three separate post-upload Celery tasks (`process_pdf`/`extract_learning_structure`/`generate_embeddings`) for granular status/retries; `extract_learning_structure` skips if topics already exist (stable concept IDs); `generate_embeddings` deletes existing chunks per material before insert.
- Tutor & (usually) quiz generation are **synchronous** (<3s); everything else via Celery (table in Blueprint §9 & §18).
- API under `/api`; JWT bearer except `auth/*`; every schema change after Phase 09 is an Alembic migration.
- Repository runnable after every phase; `CONTINUE` gate between phases.
- Four behavior decisions remain open until their phases per source roadmap: mastery formula, mismatch thresholds, recommendation weights, adaptive quiz selection — see §10.

---

## 10. Ambiguity / Decision Log (do not invent — record plan)

The source roadmap explicitly keeps four behaviors open until their respective phases. The blueprint v2 does provide concrete formulas, but per the execution protocol we record them as **proposed** and defer final confirmation to the indicated phase, logging the provisional values and the confirmation step.

| # | Ambiguity | Blueprint provisional (v2) | Roadmap defers to | Plan to confirm |
|---|-----------|----------------------------|-------------------|-----------------|
| A1 | **Mastery formula** — weights, recency, caps | `update_mastery = current + weight*(score-current)` (clamped 0-100); `weight = base(difficulty) + recency_boost` where `easy 0.2 / medium 0.3 / hard 0.4`, `+0.1 if >7d`, cap `0.5`; evidence type routing (`mcq→mcq_mastery`, `open_ended/explain_back→applied_mastery`); confidence excluded | Mastery phases (Phases 10–16+; detailed roadmap: Phase 24+ mastery services) | Re-confirm formula verbatim when implementing `MasteryService`; add unit tests for weighted-average behavior; note UI caveat *"estimate based on recent answers"* |
| A2 | **Mismatch thresholds** — gap & evidence minima | `MISMATCH_GAP_THRESHOLD=25`, `MISMATCH_MIN_EVIDENCE=3` (MCQ) + ≥1 applied; priority `mcq_high_applied_low > overconfident > underconfident`; confidence mismatch `avg_conf≥4 & acc≤0.5 → overconfident`, `avg_conf≤2 & acc≥0.8 → underconfident` | Mismatch Engine phase (Roadmap Phase per mismatch detection) | Confirm constants when implementing `MismatchService`; test thin-data non-flag and priority logic |
| A3 | **Recommendation weights / Decision Engine** | `ACTION_BASE_VALUE={ask_tutor:10, targeted_quiz:15, explain_back:20, review_material:5, exam_mode:8}`; `score = weakness + uncertainty(25 if overconfident) + recency(15 if >5d) + goal_relevance(10) + base − repetition_penalty(25*recent) + mismatch bonuses (40 to explain_back/review, −20 to targeted_quiz)`; 5 actions only | Decision Engine phase (Roadmap Phase ~50+) | Confirm weights when implementing `RecommendationService`; test mismatch pull toward applied practice and determinism |
| A4 | **Adaptive quiz selection** — concept & difficulty policy | `priority = (100−min(mcqs,applied)) + low_evidence_bonus(20 if <3) + mismatch_bonus(30) − overrepresented_penalty(10*times_this_session)`; difficulty `easy <40, medium <75, hard`; practice vs exam concept spread | Adaptive Quiz Engine phase | Confirm selection code when implementing `QuizService.select_next_concept`/`select_difficulty`; test low-evidence and mismatch prioritization |
| A5 | **Schema details** — column nullability, index choices, FK cascades | Full DDL in Blueprint §7; `confidence_records` 3-way exclusive check; `concept_mastery` unique `(user,project,concept)` | Schema/migration phases (09 → per-table phases) | Validate each migration against Blueprint §7 verbatim before `alembic upgrade` |
| A6 | **API shapes** — request/response schemas, pagination | Blueprint §19 lists endpoints under `/api`; Pydantic schemas mirror TS types | Per-feature API phases | Lock request/response shapes per endpoint when scaffolding `app/schemas/` and `app/api/` |
| A7 | **Quiz format** — question JSON, options, difficulty, timing | `quiz_questions` with `options JSONB`, `correct_option_id`, `difficulty easy|medium|hard`, `source_chunk_id`; `quizzes.mode practice|exam` with `question_count/time_limit_seconds` | Quiz phases | Confirm `difficulty` enum and `mode` branching when implementing quiz routes |
| A8 | **RAG parameters** — chunk size, overlap, top-k, threshold | `~500–700 tokens, 50–100 overlap, page-aware`; retrieval `top 5`, similarity threshold → unsupported | RAG phases | Confirm chunking constants and `top_k=5` when implementing `RAGService`/retrieval query |

No invention: all values above are taken directly from the blueprint; their **final adoption** is gated on the noted phase's verification.

---

## 11. Stack & Folder Contracts (Blueprint §5–6, §20–21)

- **Backend:** `app/{main.py, core/, db/, auth/, spaces/, projects/, materials/, rag/, tutor/, quiz/, assessment/, mastery/, recommendations/, analytics/, admin/, ai/, workers/, schemas/}` — route thin, service owns logic.
- **Frontend:** `src/{pages/, features/{tutor,quiz,learningStructure,mastery,recommendations,admin}, components/, layouts/, hooks/, services/, contexts/, types/, utils/}`; single recursive `ConceptTree` for learning structure + mastery views.
- **AI clients:** thin `GroqClient`/`EmbeddingClient` wrappers, no orchestration framework.

---

## 12. Verification for This Phase

- Blueprint read fully; stack/boundaries/exclusions/hard rules extracted above (§4–9).
- Ambiguities logged with per-phase confirmation plan (§10) without inventing final values.
- `docs/` folder and git baseline present; this file + `architecture-decisions.md` + `implementation-status.md` are the only changes (no product code).
- No framework/DB/queue/vector-store/AI-provider substitution introduced (architecture guard enforced).

---

## 13. References

- `ai-study-companion-blueprint.md` (v2)
- `ai-study-companion-detailed-opencode-roadmap.md` (Phases 01–58, architecture freeze)
- Source roadmap rule: mastery formula, mismatch thresholds, recommendation weights, adaptive quiz selection remain open until their phases (roadmap §331–338).

---

*Phase 01 produces no product logic; all subsequent phases build inside the frozen architecture documented here.*
