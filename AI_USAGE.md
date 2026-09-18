# AI Usage Documentation

## AI Study Companion

**Date:** 18 September 2026

---

## 1. AI Used During Development

The following AI tools and models were used to assist in building the application.

### OpenCode

- Used as the primary AI-assisted development agent.
- Used for implementation, debugging, testing, documentation, and development workflows.
- Models used:
  - Meta Muse Spark 1.3 Contributor
  - Meta Muse Spark 1.2 Contributor
  - Inception Labs Mercury 2.5

### VS Code Copilot

- Used for coding assistance and implementation support.
- Models used:
  - Claude Haiku
  - GPT-5.6

### Antigravity

- Used for AI-assisted development.
- Gemini models were used through Antigravity.

### Figma Make

- Used for UI/prototype generation and frontend design exploration.

### ChatGPT

- Used for architecture decisions.
- Used for deployment guidance and troubleshooting.
- Used for creating and refining prompts for development tools.

### Claude

- Used for architecture decisions.
- Used for deployment guidance.
- Used for creating and refining prompts for development tools.

### Gemini

- Used for architecture decisions.
- Used for deployment guidance.
- Used for creating and refining prompts for development tools.
- Gemini models were also used through Antigravity.

---

## 2. AI Used in the Final Product

AI is integrated into the AI Study Companion for learning and document-processing features.

### LLM Generation

- Document structure extraction: topics, subtopics, and concepts.
- AI Tutor grounded-answer generation.
- Tutor thread title generation.
- Tutor-to-quiz concept mapping.
- Multiple-choice question generation.
- Open-ended question generation and grading.
- Explain-It-Back and tutor-check grading.
- Structured JSON generation with validation and retry handling.

### Vision-Language AI

- Used for processing and captioning figures, charts, and tables extracted from documents.
- Uses the NaraRouter OpenAI-compatible endpoint with `stepfun-3.7-flash`.
- Includes best-effort OCR/placeholder fallback.

### Embeddings and Retrieval

- Uses `BAAI/bge-small-en-v1.5` through FastEmbed.
- Generates 384-dimensional embeddings.
- Stores vectors in PostgreSQL with pgvector.
- Used for project-scoped semantic retrieval and grounded AI responses.

### Document Processing

- PyMuPDF and Tesseract are used for document extraction and OCR.
- These are deterministic document-processing tools rather than LLM-based generation.

---

## 3. AI Is Not Used for All Application Logic

Several components are implemented deterministically:

- Mastery EMA calculation.
- Growth replay.
- Recommendations.
- Mismatch detection.
- Adaptive quiz selection.
- Confidence calibration.
- Flashcard SM-2 scheduling.
- Text chunking.
- RAG context assembly.
- Cost estimation.

---

## 4. Development AI vs Product AI

**Development AI:**

AI tools were used by the developer to design, implement, debug, test, document, and deploy the application.

**Product AI:**

AI models are integrated into the application to perform document understanding, tutoring, question generation, assessment, grading, vision-language processing, and semantic retrieval.

This distinction separates AI-assisted software development from AI capabilities delivered to end users by the final product.

---

## 5. Evidence / Traceability

Development AI usage is supported by the project's development workflow, configuration, prompt-history records, documentation, and source repository.

### Relevant Records

- `docs/opencode-prompts.md`
- `ai-prompts-history.txt`
- `opencode.json`
- Backend AI services
- Frontend implementation
- Repository Git history

> Not every external AI conversation is necessarily stored in the repository. In particular, architecture discussions, deployment guidance, and prompt creation performed through ChatGPT, Claude, and Gemini may not have complete repository-side interaction logs.
