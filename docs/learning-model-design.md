# Learning Model Design — Knowledge Map, Learning Objects & Quiz UX Redesign

Status: **DESIGN ONLY — no application code changed.** Implementation proceeds in
Phases A → D only on explicit user approval, one phase at a time.

Decisions below marked **[DECIDED]** were confirmed by the user 2026-09-16.
Items marked **[OPEN]** need a call before/during implementation.

---

## 1. Current architecture (verified against the codebase)

### 1.1 Hierarchy tables — titles only, no semantics

| Table | Columns (relevant) | Identity |
|---|---|---|
| `topics` | `project_id`, `title` | unique `(project_id, title)` |
| `subtopics` | `project_id`, `topic_id`, `title` | unique `(topic_id, title)` |
| `concepts` | `project_id`, `subtopic_id`, `title`, `summary` | unique `(subtopic_id, title)` |

A concept carries **no** type, importance, page numbers, or material link. It does
not know which PDF or which pages produced it.
(`backend/app/models/topic.py`, `subtopic.py`, `concept.py`)

Five tables hold FKs into `concepts.id` — this is the blast-radius inventory for
any schema change:

- `mastery_evidence.concept_id` (NOT NULL) — append-only learning evidence
- `quiz_questions.concept_id` (NOT NULL) — evidence stays concept-tied
- `document_chunks.concept_id` (nullable; **NULL for all production rows** —
  chunking never tags concepts, quiz generation survives via project-wide fallback)
- `mismatch.concept_id`
- `recommendation.concept_id`

### 1.2 Extraction pipeline (single-call, provenance-free)

`extract_pages` (PyMuPDF) produces per-page text → pages are joined into one blob
→ `extract_structure` sends the **first 12,000 chars** to one LLM call →
`StructureOutline` (1–10 topics × 1–10 subtopics × 1–20 concepts, titles ≤200,
summaries ≤1000) → `persist_structure` upserts Topic → Subtopic → Concept by
normalized title within parent scope.
(`services/structure_extraction_service.py`, `structure_persistence_service.py`,
`schemas/structure.py`, `worker/tasks/structure.py` — job keyed by `material_id`.)

Page boundaries exist at `extract_pages` time and are **discarded** before the
structure call. This is the root cause of both keyword-soup and zero
provenance. Proven failures at this layer (all fixed, all still relevant):
Groq `json_validate_failed` on dirty unicode (fixed by prompt sanitization in
`groq_client`), free-tier 429s (fixed by backoff), empty-text 422s (fixed by
project-chunk fallback in quiz `_load_source`).

### 1.3 Quiz system

- Generation: `generate_quiz(db, project_id, concept_id, ...)` — any concept,
  no importance/type gate. Source = concept-tagged chunks → project-wide
  fallback, capped at `MAX_SOURCE_CHARS = 6_000`. (`services/quiz_generation_service.py`)
- Selection UI: `QuizTaker.tsx` setup stage renders a `<select>` over **all**
  project concepts (line 151–162) — the dropdown this redesign removes.
- Adaptivity: `adaptive_quiz_service.select_questions` — weakest-mastery-first,
  difficulty matched to mastery (<34 easy / 34–66 medium / >66 hard),
  exposure-balanced, fully deterministic. Operates on `concept_id` keys; it does
  not care what a concept *is*, only its id + mastery map.

### 1.4 Mastery / recommendation (reuse, do not redesign)

- `mastery_evidence`: append-only `(user, project, concept, evidence_type, raw_score)`.
- `mastery_service.compute_mastery`: pure deterministic EMA per stream
  (`mcq` vs `applied`), user-confirmed formula, derived on read, no state table.
- `recommendation_service`: deterministic score
  (`weakness + uncertainty + recency + goal + base − repetition ± mismatch`),
  persists exactly one `active` row per (user, project), templated reason
  strings (never LLM-written). Already ~70% of the "Recommended practice" ask.
- Confidence lives on `quiz_answers.confidence` (1–5), structurally separated
  from mastery — keep that separation.

### 1.5 Retrieval / RAG

- `retrieval_service.retrieve(db, project_id, query, top_k, concept_id?)` —
  pgvector cosine over `embeddings` joined to `document_chunks`, project-scoped
  in SQL. The `concept_id` filter exists but matches nothing in production
  (chunks untagged).
- `DocumentChunk` already has `material_id`, `page_number`, `source_name`,
  `chunk_index` — page-level provenance exists for *chunks*, just not for
  *concepts*.

### 1.6 Search

No search infrastructure exists: no ILIKE usage, no `pg_trgm`, no search
endpoint. v1 search is greenfield but small.

---

## 2. Proposed architecture

```
PDF (material)
 ↓  extract_pages (unchanged — PyMuPDF, per-page text)
 ↓
PASS 1 — topics/subtopics (+ page spans)            [extraction v2, §5]
 ↓
PASS 2 — learning objects per topic, page-tagged source,
         type + importance + provenance + semantic edges   [§5–§8]
 ↓
persist: topics / subtopics / concepts (extended) + concept_relationships
         identity-preserving upsert (§9)
 ↓
 ┌─ LEARNING MODEL (CORE only) ─────┐  ┌─ KNOWLEDGE MODEL (all) ──────────┐
 │ mastery, rollups + coverage      │  │ RAG, tutor, search, explanations │
 │ quiz targeting + context enrich  │  │ quiz supporting context          │
 │ recommendations (top-N)          │  │ flashcards, prerequisites        │
 │ progress drill-down              │  │ citation / provenance display    │
 └──────────────────────────────────┘  └──────────────────────────────────┘
```

**[DECIDED]** Extend `concepts` in place; keep `topics`/`subtopics` names;
add `concept_relationships`. No parallel `learning_objects` table, no
`learning_areas` rename.

---

## 3. Schema changes (Phase A)

### 3.1 `concepts` — new columns (all nullable first, backfilled, then constrained)

| Column | Type | Notes |
|---|---|---|
| `type` | TEXT + CHECK in `('CONCEPT','DEFINITION','TERM','FORMULA','PROCESS','SKILL','OTHER')` | **[DECIDED]** v1 set = 7. CHECK keeps junk out; adding a type later = small migration that extends the CHECK (documented procedure, §3.3). |
| `importance` | TEXT + CHECK in `('CORE','SUPPORTING','REFERENCE')` | Default `'CORE'` |
| `page_start` / `page_end` | INTEGER, nullable | 1-based inclusive; NULL = unknown (legacy rows) |
| `material_id` | UUID nullable → FK `materials.id ON DELETE SET NULL` | Which document produced this LO. SET NULL (not CASCADE): deleting a PDF must not vaporize history. |
| `metadata` | JSONB NOT NULL DEFAULT `'{}'` | Extensibility: `{"status": "active"|"obsolete", "obsolete_at", "extraction_pass": 2, ...}`. Never dump raw technical fields to the UI. |

**[DECIDED]** Backfill: `type='CONCEPT'`, `importance='CORE'` for existing rows.
Readers additionally use `COALESCE(type,'CONCEPT')` / `COALESCE(importance,'CORE')`
so legacy rows behave identically even if a backfill is missed.

### 3.2 `concept_relationships` — new table (semantic edges only)

```sql
concept_relationships (
  id UUID PK,
  from_concept_id UUID NOT NULL → concepts.id ON DELETE CASCADE,
  to_concept_id   UUID NOT NULL → concepts.id ON DELETE CASCADE,
  relation TEXT NOT NULL CHECK (relation IN
    ('PREREQUISITE_OF','RELATED_TO','EXAMPLE_OF','USES','DERIVED_FROM')),
  evidence_span TEXT NULL,          -- REQUIRED when created_by='llm'
  created_by TEXT NOT NULL CHECK (created_by IN ('structure','llm')),
  created_at / updated_at,
  UNIQUE (from_concept_id, to_concept_id, relation),
  CHECK (from_concept_id <> to_concept_id)
);
```

Direction convention: `from ferent → to` reads as
"`from` PREREQUISITE_OF `to`" (from must be learned first).
Indexes on `(from_concept_id)`, `(to_concept_id)`.

Hierarchical edges (`PART_OF` / `PARENT_OF` / `CHILD_OF`) are **derived at read
time** from the existing topic → subtopic → concept FK chain and UNIONed with
stored rows by the relationship reader — never stored, never duplicated,
never hallucinated. **[DECIDED]** per user §6.

### 3.3 Extensibility procedure (new LO type, no redesign)

1. New Alembic migration extending the `type` CHECK with the new value.
2. Add the constant + crisp definition to the extraction prompt definitions.
3. Add tests (validation accepts; readers treat unknown types as display-only).
Nothing else changes: mastery, quiz, search, and rollups key off
`importance`, never `type`.

### 3.4 What does NOT change

`topics`, `subtopics`, `mastery_evidence`, `quiz_questions`, `quiz_attempts`,
`document_chunks`, `recommendation`, `mismatch` — untouched. All five
`concepts.id` FKs keep pointing at the same table, so **no history migration**.

---

## 4. Learning-object classification (v1: 7 types) **[DECIDED]**

Crisp prompt definitions (mirrored verbatim in the Pass-2 system prompt):

- **CONCEPT** — an idea, model, or principle to *understand* ("Supervised Learning").
- **DEFINITION** — the stated meaning of a term ("Overfitting is…").
- **TERM** — vocabulary to *recognize* ("Feature", "Label").
- **FORMULA** — a symbolic/mathematical expression ("F = ma").
- **PROCESS** — an ordered sequence or pipeline ("Training pipeline").
- **SKILL** — something the learner must *do* ("Free-body diagrams", "Integration by parts").
- **OTHER** — none of the above fit. **Ambiguity rule: prefer OTHER over a
  forced wrong type.** Misclassification into OTHER is recoverable;
  misclassification into FORMULA is not.

Subject-agnosticism is structural: the prompt defines types by *epistemic role*,
never by subject. No `if subject == …` logic anywhere — application or prompt.

---

## 5. Importance model **[DECIDED]**

- **CORE** — mastery target. Appears in recommendations, browse, progress,
  rollups; eligible for quiz targeting.
- **SUPPORTING** — context. Feeds quiz-generation context, RAG, tutor,
  search, flashcards. Never a mastery node, never in rollups.
- **REFERENCE** — background. RAG + search + explanations only.

Routing rule (single choke point, e.g. `is_mastery_target(concept)` helper):
every mastery/rollup/recommendation/browse query filters
`COALESCE(importance,'CORE') = 'CORE'`. Search and RAG paths never filter on
importance. "Never discard" is enforced by construction: non-CORE rows live in
the same table, fully linked to provenance and relationships.

**[OPEN]** Heuristic guardrails for the LLM (e.g. "a subtopic should yield
2–8 CORE objects; the rest SUPPORTING/REFERENCE") — propose defaults in
Phase B, calibrate against the first real reprocessing.

---

## 6. Provenance model **[DECIDED]**

Minimum per learning object: `material_id`, `page_start`, `page_end`,
`source section` (carried in `metadata.source_section`), chunk linkage via
(material_id + page range) → `document_chunks` at read time (no new FK;
chunks already carry both fields).

Capture path (from the beginning, per user §6): Pass-2 source text is
page-tagged (`[p3] …`), and the Pass-2 schema *requires* `page_start/end` per
object (validation rejects objects without them on fresh extractions; legacy
rows keep NULLs and the UI hides the source line when absent).

Bounding boxes: PyMuPDF can supply them, but nothing captures them today.
Schema-ready (`metadata.bbox`), unpopulated in v1 — no work, no false promise.

Citation payoff: quiz questions already carry `source_chunk_id`; LO page spans
let tutor answers and concept-detail pages cite "ML Unit 1, pp. 6–7" from
stored fields, not LLM memory.

---

## 7. Relationship model **[DECIDED]**

- Deterministic (read-time, from FK hierarchy): `PART_OF`, `PARENT_OF`,
  `CHILD_OF`. Zero LLM involvement.
- LLM-proposed (stored): `PREREQUISITE_OF`, `RELATED_TO`, `EXAMPLE_OF`,
  `USES`, `DERIVED_FROM` — each row **requires a non-empty `evidence_span`**
  (short quote/paraphrase from the document supporting the edge); rows without
  one are rejected at validation, and the "no evidence → no edge" rule from
  the user spec is enforced in code, not just prose.
- Cap: max **5 stored semantic edges per object** (per user "cap" requirement;
  exact number tunable in one constant). Overflow is dropped with a logged
  warning, never fails the job.

---

## 8. Extraction v2 (Phase B)

### 8.1 Two passes — never one mega-call

**Pass 1 — structure + page spans.** Input: page-tagged full text
(`[p1] … [p2] …`, truncated to current 12k-char budget). Output
(`TopicMapOutline`): topics → subtopics, each with `page_start/end`
(validation: spans within the document's page count, start ≤ end).
Reuses the existing retry-once + strict-Pydantic discipline.

**Pass 2 — learning objects, per topic.** Input: only that topic's page-range
text (page tags retained) + the topic/subtopic titles for context. Output
(`LearningObjectOutline`): objects with `name`, `type` (7-enum), `importance`,
`summary`, `page_start/end` (must fall inside the topic span), plus ≤5
`relationships` proposals `{to_name, relation, evidence_span}` resolved to ids
at persist time (unresolvable names are dropped, job continues).

Why per-topic calls: bounded prompt/output sizes keep JSON-mode reliable
(lesson from the `json_validate_failed` incident), per-topic failures retry
independently, and token cost on Mercury stays trivial.

### 8.2 Persist (extends `persist_structure`, same transaction discipline)

Upsert topics/subtopics as today → upsert LOs via the identity rule (§9) →
insert validated semantic edges → single commit, rollback on error, no partial
trees. `material_id` stamped on every touched LO row.

### 8.3 Backward compatibility during transition

Old single-pass `extract_structure` stays until Pass-1 replaces it; rows
written by either path are indistinguishable to readers (COALESCE defaults).
No flag day.

---

## 9. Identity / reprocessing strategy **[DECIDED]**

**[DECIDED]** Per-document reprocessing on demand; **no** migration-time
backfill of all documents. Legacy rows keep working via COALESCE defaults.

Match key on reprocess (in order):
1. `(subtopic_id, normalized_title)` — exact-scope hit → update in place,
   **same row id, history intact**.
2. `(topic_id scope, normalized_title)` — object moved subtopics → update
   `subtopic_id` in place, keep id.
3. No match → insert new row.

Obsolete objects (no longer extracted): **never delete the row** — deletion
would CASCADE into `mastery_evidence`, `quiz_questions`, `recommendation`,
and `mismatch` history. Instead set
`metadata.status='obsolete'` (+ timestamp) and exclude
`status='obsolete'` rows from browse/recommend/rollup queries while keeping
them resolvable for historical views. Obsolete handling must be visible in
job results (`{"obsoleted": N}`), never silent.

**[OPEN]** Merge/split handling (two old concepts → one LO): propose
"keep the id with the most evidence, obsolete the other" in Phase B.

---

## 10. Mastery rollup + coverage rules **[DECIDED]**

EMA engine **unchanged**. Only the presentation/rollup layer is new.

- **LO display mastery**: mean of the LO's known streams (`mcq`, `applied`);
  `None` when neither stream has evidence. (Rationale: matches the existing
  "unknown = explicit None" convention; recommendation keeps its own
  `min(known)` weakness semantics untouched.)
- **Practiced** (for a given user): ≥1 evidence row for that (user, LO).
- **Rollup** (subtopic → topic → project): **mean of practiced CORE children
  only**. Unpracticed CORE objects are excluded — never 0.
- **Empty rollup**: no practiced CORE children → mastery `null` → UI shows
  "Not started" (never 0%).
- **Coverage** (always alongside mastery): `practiced / total CORE children`,
  e.g. "Mastery 61% · Coverage 3/5 CORE targets practiced". Coverage 0/N is
  valid and must render.
- Obsolete objects excluded from both numerator and denominator.

### Mastery statuses (centralized, tunable in one module)

Aligned with the existing adaptive thresholds (<34 / 34–66 / >66):

| Status | Rule |
|---|---|
| Not started | mastery is None |
| Needs practice | < 34 |
| Developing | 34 – 66 |
| Strong | 67 – 84 |
| Mastered | ≥ 85 |

Single `mastery_levels` config/service owns these; UI and recommendation
reason strings read from it. Thresholds are operational, not scientific —
documented as such in code.

---

## 11. Quiz architecture (Phase C)

### 11.1 Three modes replace the dropdown **[DECIDED]**

`QuizTaker` setup stage loses the `<select>`; new `QuizModes` UI defaults to
**Recommended**, with **Browse by Topic** and **Search** tabs. Existing visual
identity (Tailwind, violet/fuchsia, `ui.tsx` primitives, Plus Jakarta Sans)
is kept; only information architecture changes (progressive disclosure).

### 11.2 Recommended (default)

New `recommend_many(db, user, project, limit=4)` — pure query reusing the
existing `score_action` + templated reasoning over **CORE-only**
`ConceptSignal`s (signal gains `importance`/`type`; non-CORE never scored).
Each card: name, type, mastery, honest reason (recent misses / low mastery /
stale — all from stored evidence), [Start Practice]. Zero-evidence fallback:
neutral "Start with a core concept from this topic." The existing single-active
`recommend` row keeps feeding the dashboard widget unchanged.

### 11.3 Browse by Topic (progressive narrowing)

Project → Topic → Subtopic → CORE learning targets. Each level shows name,
CORE-target count, mastery + coverage (rollup service). Leaf rows show LO type
chip + mastery + [Practice]. One new composite read endpoint (structure tree +
mastery/coverage join); SUPPORTING/REFERENCE never listed here.

### 11.4 Quiz generation on CORE targets (+ enriched context)

- Target **must** be CORE: non-CORE target → `422` with a clear error
  ("learning object is not a practice target; pick a CORE target or search
  supporting material"). No silent fallback to other objects.
- Context builder (priority-budgeted into the existing 6k-char source cap):
  1. CORE object's summary + its material's page-range chunks,
  2. SUPPORTING objects linked via relationships (names + one-line summaries),
  3. prerequisite/related CORE names,
  4. existing concept-tagged → project-wide chunk fallback (kept as last resort).
- Difficulty default: adaptive-matched from LO mastery (existing
  weakest-first + difficulty-band rule reused at quiz creation).
- Evidence/attempt/completion flow unchanged — `quiz_questions.concept_id`
  keeps pointing at the same row, so all history stays valid.

### 11.5 Concept detail page (new frontend, composed reads)

Name, type chip, description, mastery bar + stream breakdown
(accuracy/recent/consistency/confidence computed from existing
evidence + quiz answers — no new tables), attempts/correct/last-practiced,
prerequisites, related, supporting knowledge, source (material + pages),
[Practice]. One aggregate read endpoint; technical metadata stays hidden.

---

## 12. Recommendation integration

- `ConceptSignal` extended with `importance`, `type`; candidate set = CORE,
  non-obsolete, in-project.
- Scoring formula untouched; reason templates gain one LO-aware variant
  ("prerequisite X is weak" when a PREREQUISITE_OF edge points at a
  low-mastery LO — **[OPEN]**: include in Phase C or defer).
- Exam-mode eligibility ("3+ evidenced concepts") counts evidenced CORE LOs.

---

## 13. Search (v1) **[DECIDED]**

- Scope: **current project only**. No cross-project search.
- Corpus: **all importances** (CORE + SUPPORTING + REFERENCE) over
  title + summary — supporting/reference discoverability is the point.
- Implementation: `ILIKE '%q%'` (no trigram infra exists; adding `pg_trgm` is
  a one-migration upgrade later ifgew scale demands it). Min query length 2,
  limit 20, project-ownership enforced in SQL like all other readers.
- Result rows: name, type + importance chips, breadcrumb
  (Topic → Subtopic), pages/material, mastery if CORE + practiced, [Practice]
  only for CORE targets.

---

## 14. Progress UI (Phase D)

Same hierarchy, drill-down: Project overall → per-Topic → per-Subtopic →
per-LO, each level showing mastery + coverage from the rollup service (§10).
"Overall" = rollup over all CORE LOs in scope (same practiced-only mean rule —
a fresh upload with 50 unpracticed CORE targets shows "Not started", not 0%).
`Dashboard`/`GrowthView`/`AnalyticsView` keep working during transition; the
drill-down view is additive.

---

## 15. Migration / backward compatibility

- **One Alembic migration (Phase A):** add nullable columns → backfill
  `type/importance` → set defaults + NOT NULL on those two (+ CHECKs) →
  create `concept_relationships`. Fully online-safe; downgrade drops the table
  and columns.
- **No document backfill [DECIDED].** Unreprocessed materials behave exactly
  as today (all CONCEPT/CORE via backfill + COALESCE).
- **API compatibility:** existing endpoints keep shapes; new fields are
  additive on concept payloads. New endpoints are additive. The only
  behavior change: quiz generation rejects non-CORE targets (422) — new rows
  only; legacy rows are all CORE.
- **Rollback:** each phase is independently revertible (A: migrate downgrade;
  B: worker still runs old task; C/D: frontend tabs are additive).

---

## 16. API changes (proposed; paths follow existing `/api/v1/projects/{id}/…` style)

| Change | Endpoint | Notes |
|---|---|---|
| New | `GET /projects/{id}/practice/recommendations?limit=4` | CORE-only top-N + templated reasons + neutral fallback |
| New | `GET /projects/{id}/knowledge/tree?importance=CORE` | Browse hierarchy with mastery + coverage per node |
| New | `GET /projects/{id}/knowledge/search?q=&limit=20` | Project-scoped, all importances, ILIKE v1 |
| New | `GET /projects/{id}/concepts/{cid}` | Concept-detail aggregate (mastery, history, relations, source) |
| Changed | `POST /projects/{id}/quizzes` | 422 on non-CORE target; enriched source context |
| Changed | concept payloads | + `type`, `importance`, `page_start/end`, `material`, `coverage` where relevant |
| Internal | worker `build_structure` | two-pass task chain; job result gains `{obsoleted}` |

**[OPEN]** Exact response envelopes (error-code taxonomy follows existing
`schemas/errors.py` conventions — propose in Phase C).

---

## 17. Testing strategy

- Per user instruction: **affected suites only** (no full-suite marathons
  unless warranted), plus one live Mercury reprocess of a real document
  before handover, as established this session.
- Phase A: migration up/down on scratch DB; CHECK-constraint tests;
  COALESCE-reader tests (legacy NULL rows behave as CONCEPT/CORE);
  relationship validation tests (evidence_span required, cap enforced,
  self-edge rejected).
- Phase B: prompt/schema unit tests with mocked client (malformed LO output →
  retry → safe error, mirroring existing extraction tests); identity tests
  (re-persist preserves ids; obsolete flags without deleting; history rows
  intact); page-span validation tests.
- Phase C: recommendation top-N determinism; browse-tree mastery/coverage
  math; search scope tests (cross-project leakage, importance inclusion);
  quiz 422 on non-CORE; context-builder priority tests.
- Phase D: rollup math (practiced-only mean, null-on-empty, obsolete
  exclusion); status-threshold tests; coverage rendering contracts.
- Regression throughout: existing mastery EMA, adaptive selection,
  recommendation scoring, and quiz-attempt tests must stay green untouched.

---

## 18. Remaining limitations (v1, acknowledged upfront)

1. LLM classification is advisory — OTHER-fallback + extensible enum bound
   the damage, but expect some mislabels; no human-override UI in v1.
2. Hierarchical edges derived at read time assume the FK tree is correct;
   cross-topic semantic links depend on LLM edge quality (capped, evidenced).
3. Rollup means treat all CORE targets equally (no per-LO weighting).
4. ILIKE search won't scale past thousands of LOs per project — trigram
   upgrade path reserved.
5. `metadata.bbox` reserved but unpopulated; no bounding-box citations in v1.
6. Merge/split identity edge cases need the Phase-B rule (§9 **[OPEN]**).
7. Reprocessing is per-document and manual in v1 (no bulk "reprocess all").

---

## 19. Phase plan (implementation order, each gated on user approval)

- **Phase A — Schema + statuses.** Migration, COALESCE readers,
  `is_mastery_target` choke point, centralized status thresholds. No behavior change.
- **Phase B — Extraction v2.** Two-pass tasks, 7-type classification,
  importance, provenance, semantic edges, identity-preserving persist +
  obsolete handling.
- **Phase C — Quiz UX.** Recommended/Browse/Search, concept detail,
  CORE-gated generation with enriched context, recommendation top-N.
- **Phase D — Progress + rollups.** Rollup service, coverage, drill-down
  progress UI, status display everywhere.

**STOP after this document. Phase A begins only on explicit user request.**

---

## 20. Phase A implementation notes (recorded 2026-09-16, commit pending review)

- Migration `9f3a7c1e5b28` (revises `e7b2d4a1c6f8`): nullable add → backfill
  CONCEPT/CORE/`'{}'` → NOT NULL + server defaults + CHECKs on
  `type`/`importance`; `material_id` FK `SET NULL`; new
  `concept_relationships` (unique triple, relation/creator CHECKs, self-edge
  ban, llm-evidence rule); indexes `ix_concepts_material_id`,
  `ix_concepts_importance`, `ix_concept_relationships_from/to`.
  `alembic check` clean; downgrade→upgrade round-trip verified lossless on
  1313 dev rows.
- Model gotcha: column `metadata` maps to attribute `meta` — `metadata` is
  reserved by DeclarativeBase. Relationship indexes declared explicitly in
  `__table_args__` to match migration names (autogenerate naming differs).
- Gate applied ONLY in `dashboard_service.build_dashboard` (SQL COALESCE +
  python-side `is_mastery_target` twin for the obsolete guard). Structure
  tree, quiz picker, and `recommend()` ownership check unchanged — their
  gating lands in Phase C.
- Verified: 68 affected-suite tests green; all 1313 existing concepts read
  as CONCEPT/CORE (gate is pass-through); all five `concepts.id` FK holders
  untouched; no reprocessing performed; containers not rebuilt (old code
  ignores new columns).

## 21. Phase B implementation notes (recorded 2026-09-16)

- Built: `TopicMapOutline`/`LearningObjectOutline` schemas (validators reuse
  model vocab constants — single source); `extract_topic_map` (Pass 1,
  12k-char page-tagged budget, span sanity enforced) +
  `extract_learning_objects` (Pass 2 per-topic, 20k-char cap) +
  `build_page_tagged_text`/`slice_topic_source`; `persist_knowledge_map`
  (§9 rules: exact → revive → topic-scope move → alnum-fold merge by evidence
  → insert; obsolete sweep incl. NULL-material rows in touched subtopics;
  edge resolve subtopic → topic → project, cap 5 stored, unresolvable
  dropped with counts); `relationship_service.get_related` (derived hierarchy
  ∪ stored edges); task rewrite (same signature/lifecycle/backoff; Pass-2
  transport errors skip the topic, reported in `failed_topics`).
- Deviations/refinements vs §§8–9: (a) LO-named unknown subtopics materialize
  under the topic (never drop/misfile genuine objects); (b) exact hits on
  obsolete rows revive them; (c) rule-2 moves rename exact-title obsolete
  squatters with " (superseded)" to respect the UQ; (d) material stamp writes
  only when NULL; (e) 2–8 CORE reported as `guideline_notes`, advisory only.
- Edge cases (accepted): shared-subtopic NULL-material rows may obsolete on
  another material's reprocess (visible in job result, reversible by
  reprocessing); legacy case-variant duplicates resolve deterministically
  (earliest created); concurrent same-project reprocesses could race the
  triple-UQ (out of scope, single worker in practice).
- Live verification (scratch project, real Mercury, fully cleaned up after):
  2-page bio PDF → 2 topics with correct page spans, 6 LOs typed
  PROCESS/CONCEPT/TERM (5 CORE + 1 SUPPORTING), pages + material stamped,
  2 evidenced edges, guideline notes fired. Quality watch-items (v1
  acceptable): "Krebs Cycle" → TERM/SUPPORTING is debatable; one USES edge
  direction is debatable. No user documents reprocessed.
- Verified: 94 affected tests green; `alembic check` clean (no schema
  change); legacy `extract_structure`/`persist_structure` frozen and still
  passing. Phase C/D untouched.
