# Evaluation strategy (RAGAS + trajectory + LangSmith)

How to judge additions to this project — when changing RAG behavior, LangGraph nodes, retrieval settings, or helpdesk-agent routing.

The baseline below is an **engineering signal**, not a marketing claim. **context_recall** passes the gate under the tuned AWS profile; **faithfulness**, **answer_relevancy**, and **context_precision** are documented baselines with active levers (ingestion/chunking, rerank tuning, golden-set re-bootstrap). Gates are **release controls**, not blockers for local demo or PR CI.

---

## Two tools, two jobs

| | **RAGAS** | **LangSmith** |
|--|-----------|----------------|
| **What** | Open-source RAG **metric library** | **Platform** for traces, datasets, experiments |
| **Question answered** | "Did quality improve or regress?" | "Why was this request slow/wrong?" |
| **In this repo** | `backend/tests/eval/test_rag_quality.py`, `golden_dataset.json` | `simple_tracer.py`, `LANGCHAIN_TRACING_V2` |
| **CI gate** | Yes — `RAGAS_QUALITY_GATE=1` on release/nightly | Optional — traces for debug |
| **Same thing?** | **No** — complementary |

LangSmith can run evaluators (including RAG-like judges), but **do not treat LangSmith scores as RAGAS** without calibrating on the same dataset.

---

## RAGAS metrics (defaults)

| Metric | Default min | Interpretation |
|--------|-------------|----------------|
| **faithfulness** | 0.85 | Answer grounded in retrieved context |
| **answer_relevancy** | 0.80 | Answer addresses the question |
| **context_recall** | 0.75 | Retrieval covers ground truth |
| **context_precision** | 0.70 | Retrieved chunks are on-topic |

## RAGAS baseline (2026-05-19)

The checked-in golden set was bootstrapped from one **campus knowledge base** deployment (Canvas LMS teaching-and-learning and ServiceNow IT articles). Questions and `ground_truth` rows are **corpus-specific**—re-run `scripts/bootstrap_golden_dataset.py` after ingesting your own KB.

**Full score tables, Azure sweep results, tuning profiles, and findings:** [eval_baseline_v2.md](./eval_baseline_v2.md).

| Stack | Best-known highlight | Precision |
|-------|----------------------|-----------|
| **AWS** Phase 5 tuned (LangGraph) | **context_recall 0.80** (passes gate) | ~0.50 |
| **Azure** LLM + judge, chain path | faithfulness ~0.84, relevancy ~0.98, recall ~0.83 | ~0.50 |
| **Azure** LangGraph precision-balanced | relevancy ~0.88; recall often ~0.60 | ~0.54–0.58 |

**context_precision** (~0.70 gate) is the bottleneck for all profiles; multi-query fusion adds recall but also noisy chunks. Align bootstrap provider with eval judge when comparing faithfulness/recall. Eval now respects `RAG_ENGINE=langgraph` when `RAGAS_EVAL=1` (see baseline doc). Sub-threshold scores are documented baselines, not demo blockers.

### CI gate policy

| Event | `RAGAS_QUALITY_GATE` | Notes |
|-------|----------------------|--------|
| PR / `main` CI (`tox (lint, backend, frontends)`) | **0** (default) | RAGAS not required; mock helpdesk trajectory eval runs via `tox -e agent-eval` |
| Local / release milestone | **1** | `tox -e eval` or `./scripts/run_eval_phase5.sh`; needs judge + Bedrock |
| CD `release` workflow | **1** when secrets configured | See [CI.md](operations-manual/ci-cd.md) |

Env overrides: `RAGAS_FAITHFULNESS_MIN`, `RAGAS_ANSWER_RELEVANCY_MIN`, etc.

### Run locally

**Runtime:** The first metric test builds the dataset with **one live RAG call per golden question** (10 questions ≈ several minutes on AWS). RAGAS scoring then calls the judge LLM per row. Use `pytest -v -s` (enabled in `tox -e eval`) to see progress logs.

```bash
tox -e eval
# Phase 5 tuned profile:
./scripts/run_eval_phase5.sh
# or: PYTHONPATH=. pytest backend/tests/eval/ -v -m slow
```

Requires judge LLM: `RAGAS_LLM_PROVIDER` set to `aws`, `azure`, or `gcp` with matching cloud credentials.

Helpdesk-agent trajectory eval is separate from RAGAS and is safe for PR CI:

```bash
tox -e agent-eval       # mock, deterministic PR gate
tox -e agent-eval-live  # live LLM supervisor comparison; needs provider + LangSmith secrets
```

---

## When to run what

| Event | RAGAS | LangSmith |
|-------|-------|-----------|
| Every PR | Optional — unit tests with mocked RAG; helpdesk `agent-eval` is required | Dev only |
| Pre-release / milestone | Full golden set; compare to [baseline](./eval_baseline_v2.md) | Trace screenshots in README |
| LangGraph parity (Phase 4 (LangGraph)) | chain vs `RAG_ENGINE=langgraph`, ±0.02 | Per-node spans |
| Retrieval change (Phase 5 (retrieval)) | Primary metric + faithfulness guardrail | Compare runs |
| Nightly staging | Full gate with secrets | SLO debugging |

---

## Scorecard (per feature)

| Field | Value |
|-------|--------|
| **Change** | e.g. multi-query retrieval node |
| **Roadmap phase** | Product phase (see [PRODUCT_ROADMAP.md](./roadmap/PRODUCT_ROADMAP.md)) |
| **Primary metric** | context_recall |
| **Guardrails** | faithfulness ≥ 0.85; p95 latency < X ms |
| **Baseline** | commit / [eval_baseline_v2.md](./eval_baseline_v2.md) |
| **Result** | +0.04 recall; faithfulness 0.86 |
| **Ship** | yes / flag-only / no |

### Ship rules

- **LangGraph parity:** ship if RAGAS within ε of chain and tests green.
- **Retrieval / prompts:** ship if primary metric improves and guardrails hold.
- **Agentic (Phase 6 (agentic)):** flag-only until staging week is stable.

---

## Helpdesk agent evaluation

**Shipped:** Prometheus outcome/tool/funnel metrics on `/api/metrics`, API/unit coverage under `backend/tests/api/test_helpdesk.py`, and a trajectory scenario rig in `backend/tests/eval/test_helpdesk_agent_scenarios.py`. `tox -e agent-eval` runs the mock dataset in PR CI and gates over-ask, false-escalation, unnecessary-loop, resolve-without-ticket, HITL, and injection-resistance regressions. `tox -e agent-eval-live` runs the same dataset with the live LLM supervisor for **local/manual** comparison when AWS + LangSmith are configured; it is not wired into GitHub Actions CI.

| Layer | Status | What it answers | Where |
|---|---|---|---|
| **RAGAS golden set** | Shipped | Retrieval + answer quality on KB path | [eval_baseline_v2.md](./eval_baseline_v2.md), `tox -e eval` |
| **Scenario rig (trajectory)** | Shipped — PR CI gate | Does the supervisor pick the expected action sequence for known conversations? | `backend/tests/eval/helpdesk_agent_scenarios.json`, `backend/tests/eval/test_helpdesk_agent_scenarios.py`, `tox -e agent-eval` |
| **Outcome distribution** | Shipped (metrics) | What fraction of agent sessions terminate as `resolved_by_agent` / `linked` / `filed` / `aborted`? | `chatbot_helpdesk_agent_outcome_total{outcome=...}` |
| **Tool usage** | Shipped (metrics) | How often does the agent reach for `retry_kb` / `web_search` / `search_dups` / `file_ticket`? | `chatbot_helpdesk_agent_tool_total{tool=...}` |
| **HITL gate** | Shipped (code + tests + trajectory gate) | Are tickets ever filed without explicit `/agent/confirm`? (Guard: must be 0.) | `backend/tests/api/test_helpdesk.py`; `tox -e agent-eval`; `chatbot_helpdesk_create_issue_total` |

Decision records: [ADR-005](./adr/ADR-005-bounded-helpdesk-agent.md) (original commitment) and [ADR-006](./adr/ADR-006-live-llm-supervisor-migration.md) (rebuild + eval Phase 4).

---

## LangGraph-specific evaluation

1. Baseline RAGAS on `RAG_ENGINE=chain` (or current default).
2. Run same golden set on `RAG_ENGINE=langgraph`.
3. Compare all four metrics; investigate faithfulness regressions first.
4. Use LangSmith to see whether regressions are condense vs retrieve vs generate.

---

## Bootstrapping the golden set (live AWS KB)

Rebuild `golden_dataset.json` from live RAG so `ground_truth` and `contexts` match what Bedrock KB retrieval returns.

**Prerequisites:** `RAG_FORCE_MOCK=false`, `LLM_PROVIDER=aws` (or `azure` / `gcp`), valid cloud credentials, `RAG_ENGINE` as used in eval (e.g. `langgraph`).

```bash
./venv/bin/python scripts/bootstrap_golden_dataset.py
./venv/bin/python scripts/bootstrap_golden_dataset.py --only 3
./venv/bin/python scripts/bootstrap_golden_dataset.py --dry-run
```

Output: `backend/tests/eval/golden_dataset.draft.json` (includes `_bootstrap` review metadata).

**Review checklist before promoting:**

1. Drop rows where the model returns an out-of-scope refusal despite non-empty contexts.
2. Tighten `ground_truth` to 2–4 factual sentences.
3. Keep `contexts` as verbatim retrieved chunk text (top 3).
4. Restore hand-authored `ground_truth` when live answers are refusals but KB content is on-topic.

```bash
./venv/bin/python scripts/promote_golden_draft.py
```

Seeds: `backend/tests/eval/seed_questions.json`. Draft file is gitignored.

---

## LangSmith run naming and traces

Chat RAG calls are traced as **`chat-session-<session_id>`** with tags:

- `session_id:<id>`
- `request_id:<id>` when `X-Request-ID` is set
- `research_mode:kb` or `research_mode:web`

Filter the LangSmith UI by run name or tags. With `RAG_ENGINE=langgraph`, child spans include condense, multi_query, retrieve (or web_search), rerank (KB path), generate, and format.

Screenshots: [docs/assets/observability/](./assets/observability/) (README uses `langsmith-trace-kb-waterfall.png`).

### Capture a trace for docs

1. In `.env`: `LANGCHAIN_TRACING_V2=true`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT=chatbot-poc`, `RAG_ENGINE=langgraph`.
2. Restart API; send one chat message from http://127.0.0.1:5173.
3. In [LangSmith](https://smith.langchain.com), open the project and find run name `chat-session-<id>`.
4. Expand condense → multi_query → retrieve (or web_search) → generate → format.
5. Screenshot waterfall or tree; save under `docs/assets/observability/` (e.g. `langsmith-trace-kb-waterfall.png`).
6. Commit the PNG; README links `docs/assets/observability/langsmith-trace-kb-waterfall.png`.

---

## Growing the golden set

1. Start with domain Q&A in `golden_dataset.json`.
2. Add failures from manual testing and (anonymized) bad traces.
3. Tag items: `"tags": ["ambiguous", "multi-hop"]` for targeted runs.

---

## Related

- [roadmap/PRODUCT_ROADMAP.md](./roadmap/PRODUCT_ROADMAP.md)
- [DESIGN.md — LangGraph KB path](./DESIGN.md#langgraph-kb-path-multi-query-retrieve-rerank)
- [assets/README.md](./assets/README.md) — demo script
