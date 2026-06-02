# PRD — Mechanism: CrewAI Content Pipeline

**Mechanism:** multi-agent content generation (`services/crew_service.py`,
`agents/`). **Version:** 1.00. Parent: [`PRD.md`](PRD.md), [`PLAN.md`](PLAN.md).

---

## 1. Description & theoretical background
CrewAI turns a single long prompt into a **team of role-specialised agents**,
each with a `role`, `goal`, `backstory` (system prompt) and optional `tools`.
A `Task` declares a `description`, an `expected_output`, an `agent`, and a
`context` (outputs of prior tasks). A `Crew` binds agents + tasks under a
`Process` (we use `sequential`). The output of one task flows as **context** to
the next — the glue that lets the Writer build on the Researcher without manual
copying (course materials, CrewAI Part A/B).

Pattern adopted (assignment §12.2): **Researcher → Writer → Reviewer**, extended
with a **LaTeX Engineer** that maps reviewed prose into chapter `.tex` fragments.

## 2. Agents
| Agent | role | goal | tools |
|-------|------|------|-------|
| Researcher | "Startup Research Analyst" | extract accurate, structured facts on each chapter topic | (curated facts; optional web search) |
| Writer | "Senior Startup Author" | turn research into clear Hebrew chapters with English terms where natural | none (works from context) |
| Reviewer | "Senior Editor" | improve accuracy, clarity, structure; never change meaning | none |
| LaTeX Engineer | "LaTeX Typesetter" | map reviewed chapters to LaTeX-ready fragments (headings, lists, emphasis, BiDi markers) | none |

## 3. Tasks (sequential, context-chained)
1. **research_task** → list of key facts + sources per chapter.
   `expected_output`: structured research brief. `context`: —.
2. **write_task** → Hebrew chapter drafts. `context`: [research_task].
3. **review_task** → polished chapters. `context`: [write_task].
4. **latex_task** → per-chapter LaTeX bodies + a sources list for the `.bib`.
   `context`: [review_task].

## 4. Requirements & I/O
- **Input:** `topic: str`, `chapter_outline: list[str]`, `language="he"`,
  resolved `ConfigManager` (model, temperature, limits).
- **Output:** `BookContent` (title, `chapters[]`, `sources[]`, `token_usage`).
- **FR:** every LLM call routes through the **Gatekeeper** (no direct CrewAI→OpenAI
  network call that bypasses rate limiting — enforced by injecting a gatekept LLM
  client / wrapper). Content flows only via `context`. `verbose=True` for
  observability. Token usage captured from `result.token_usage`.
- **Performance:** target ≤ ~30k completion tokens per full book; a run should
  complete within a few minutes on `gpt-4o-mini`.

## 5. Constraints, alternatives, rationale
- **Constraint:** deterministic builds for grading → low temperature, curated
  grounding facts, web search off by default (see ADR-4).
- **Alternatives:** single mega-prompt (rejected — no role separation, harder to
  review); LangGraph (rejected — stateful graph unnecessary for a linear flow);
  AutoGen (rejected — conversational, less reproducible).
- **Rationale:** CrewAI is the architecture-deck "best fit" for bounded
  role-based teams and mirrors the course's canonical example.

## 6. Success criteria & test scenarios
- **SC-1** `crew_service.generate_content(topic)` returns a `BookContent` whose
  `chapters` cover every outline entry. *Test:* integration test with a **mocked**
  LLM returns canned chapter text → assert all chapters present, sources parsed.
- **SC-2** No agent makes a network call that bypasses the gatekeeper. *Test:*
  inject a spy gatekeeper; assert it received ≥1 call per agent step.
- **SC-3** Token usage is recorded and non-negative. *Test:* mock returns usage;
  assert `BookContent.token_usage` populated.
- **SC-4** Graceful failure: on an LLM error the service raises a typed
  `CrewExecutionError` with context. *Test:* mock raises → assert wrapped error.
