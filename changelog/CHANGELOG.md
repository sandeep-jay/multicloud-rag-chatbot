# Changelog

Notable changes to **Campus RAG Assistant** — independent extension of the UC Berkeley ETS Chabot platform
([campus-rag-assistant](https://github.com/sandeep-jay/campus-rag-assistant)).

[Keep a Changelog](https://keepachangelog.com/) format.  
Attribution and license: [README](../README.md#license).

**Author & maintainer:** [sandeep-jay](https://github.com/sandeep-jay) — sole implementation author
of the upstream Berkeley ETS Chabot codebase (copyright UC Regents) and author of
this **independent extension**. Distributed under the UC Regents
[LICENSE](../LICENSE); see [`NOTICE`](../NOTICE). Not an official UC Berkeley product.

**Convention:** sections use **session dates** (when work happened). GitHub PR numbers are noted
where the public merge story matters.

Edit **`[Unreleased]`** while you work. When a session is done, rename it to
`## [YYYY-MM-DD] — short title` and open a new `[Unreleased]`.

## [Unreleased]

- **GCP provider registry** — Added `gcp` LLM provider (`ChatGoogleGenerativeAI` on Vertex AI) and `gcp` retriever provider (`VertexAISearchRetriever` with metadata normalization). Select via `LLM_PROVIDER=gcp` / `RETRIEVER_PROVIDER=gcp` or `RAG_PROVIDER=gcp`. RAGAS judge supports `gcp` embeddings. Docs: ADR-001, ARCHITECTURE.md, DESIGN.md, OPERATIONS.md, `.env.example`.
### Fixed

- **CI — disable scheduled live helpdesk trajectory eval.** Removed the `agent-eval-live` GitHub Actions job and the daily `schedule` trigger; live supervisor comparison remains available locally via `tox -e agent-eval-live` when AWS/LangSmith are configured.
- **CI — agent-eval tox env fails on pytest 9.x.** GitHub Actions resolves `pytest>=8.0.0` to pytest 9.1.x; `pytest-ruff==0.2.1` still declares the removed `path` arg on `pytest_collect_file`, so pytest aborts during plugin registration (`PluginValidationError`) before any trajectory scenario runs. Bumped `pytest-ruff` to `0.5` for pytest 8.1+/9.x hook compatibility; `tox -e backend,agent-eval` passes locally.

### Added

- **Helpdesk agent — score-based KB confidence gate and evidence trimming.** The agent now reads the top-1 similarity `score` from the KB retry's documents and only proposes a KB-grounded solution when it clears `HELPDESK_AGENT_KB_CONFIDENCE_FLOOR` (default `0.55`). Below the floor — or zero hits — the agent escalates to the existing web-consent flow instead of confidently surfacing irrelevant articles. Fixes the Panopto case where a 15-doc Kaltura retrieval was being marketed as the answer without ever asking the user about live web search. The retry log now includes `top_score`/`floor` so the threshold can be tuned. The agent also caps surfaced evidence at `HELPDESK_AGENT_EVIDENCE_TOP_N` (default `3`) sources/document contents so the chat bubble shows the top supporting hits rather than the full retrieved list. The activity timeline now renders the agent's KB pass as **"Knowledge base (agent retry)"** and the web pass as **"Public web search"** so they're visually distinct from the chat-level KB retrieval.
- **Helpdesk agent — surfaced GitHub error detail in ticket-create failures.** `create_github_issue` now extracts GitHub's `message` and `errors[*].message` payload into the surfaced `HTTPException` detail, and the Vue ticket modal reads `response.data.detail` so the toast tells the user *why* GitHub refused the issue (auth scope, validation, rate limit) instead of a generic "Failed to file agent ticket. Please try again."

### Fixed

- **Helpdesk chat — scroll dead-space after agent resume.** `MessageList.vue` was set to `min-h-full` regardless of whether messages were present; combined with `scrollTop = scrollHeight`, that left short follow-up bubbles stranded at the top of an otherwise empty viewport. The full-height pad now only applies to the empty welcome state, so the new agent turn and "Thinking…" indicator sit in the natural reading position.
- **Helpdesk agent — activity trace discoverability.** The current actionable agent turn now expands its **"What the agent did"** trace by default and keeps the header visible, so users can immediately see KB retry, low-confidence gating, web-search consent, and web-search steps without hunting for a collapsed control.

- **Helpdesk agent — structured sources and live-web consent** — `AgentTurn` now carries `sources`, `document_contents`, `source_kind`, and `disclaimer` on propose-solution turns, populated from KB retry or web-search documents using the same shape as chat metadata. Persisted `agent_summary` rows retain that evidence for reloads. When KB retry finds no fix and the configured web provider is live (`WEB_SEARCH_PROVIDER=tavily` with `TAVILY_API_KEY`), the agent pauses with a radio consent question (`Search the web` / `Skip and draft a ticket`) before calling Tavily; mock web search remains automatic for CI/demo. Vue `MessageBubble.vue` renders the existing sources panel and web disclaimer for live and persisted agent bubbles.
- **Campus router and agent capability registry (Phase 5)** — added `backend/app/services/agents/registry.py` (`AgentSpec{name, subgraph_factory, tools, enabled_flag, description}` with `register_agent` / `get_agent` / `enabled_domains` / `unregister_agent`; helpdesk registers at import time) and `backend/app/services/agents/router.py` (`RouterDecision{domain, confidence, reason}`, `classify_domain(...)`, `helpdesk_should_escalate(...)`). The router is off by default (`CAMPUS_ROUTER_ENABLED=false`); the mock provider drives a deterministic sentinel router for PR CI, the live LLM path uses `with_structured_output(RouterDecision)` and falls back to `kb_answer` on any error. Chat metadata now carries `router_decision` on both the JSON (`/api/chat/chat`, `/api/chat/sessions/{id}/messages`) and SSE (`/api/chat/stream`) paths. Vue `MessageBubble.vue` promotes the escalation chip when `kb_resolved == false` **or** the router classifies the turn as `helpdesk` with confidence at or above `ROUTER_HELPDESK_FLOOR` (default `0.6`). Tests cover the seam (`test_echo_agent_registers_without_router_changes`), router contract, and chat-API end-to-end behaviour. Docs: new ADR-007 (Proposed), `docs/roadmap/AGENT_REGISTRY.md` contract, updated `AGENTIC_HELPDESK_REBUILD.md` Phase 5 status, mkdocs nav.
- **Helpdesk agent — compiled LangGraph `StateGraph`** — added `backend/app/services/helpdesk_graph/graph.py` with nodes `supervisor`, `tools`, `clarifier`, `classifier`, `writer`, `solution`, `await_user`, `await_confirm`, and terminals (`link_existing`, `file_ticket`, `resolved`, `aborted`). `start_session` / `resume_session` / `confirm_session` / `abort_session` now invoke `HELPDESK_GRAPH.ainvoke(...)`; supervisor routing is deterministic (`select_supervisor_action`) so user-visible behaviour, `AgentTurn` shape, and `debug_trace` byte-shape are unchanged. LangSmith now renders one nested graph tree per session instead of a flat span. Phase 1b swaps the custom JSON checkpoint for an `AsyncPostgresSaver` and the pause nodes for `langgraph.types.interrupt()`.
- **Helpdesk agent — LangGraph checkpointers** — added configurable checkpoint backends (`postgres`, `sqlite`, `memory`) with Postgres as the default, Alembic-owned LangGraph checkpoint tables, and `interrupt()`/`Command(resume=...)` pause-resume flow for user clarification and HITL ticket confirmation. The legacy JSON SQLite checkpoint path remains behind `HELPDESK_AGENT_USE_LANGGRAPH_CHECKPOINT=false` for one release. The `sqlite` backend is an opt-in dev fallback: `langgraph-checkpoint-sqlite` is intentionally **not pinned** in `requirements.txt` (2.0.x carries `GHSA-9rwj-6rc7-p77c` and 3.x requires a LangGraph 1.x bump); install it manually when you actually want SQLite locally.
- **Helpdesk agent — live supervisor adapter** — added bindable LangChain tool wrappers for KB retry, web search, duplicate search, and HITL ticket filing plus a structured-output supervisor/classifier adapter behind `HELPDESK_AGENT_LLM_SUPERVISOR=false`. Invalid or disallowed supervisor decisions fall back to a safe draft path or the deterministic supervisor.
- **Helpdesk agent — specialist routing** — added help-first supervisor gating, classifier confidence tracking (`HELPDESK_AGENT_CLARIFY_CONFIDENCE_FLOOR`), targeted clarification, and `Idempotency-Key` handling on `/api/helpdesk/agent/confirm`.
- **Helpdesk agent — live graph stream trace** — `/api/helpdesk/agent/start/stream` and `/api/helpdesk/agent/resume/stream` now emit real LangGraph node/tool `step` events with status, summary, and latency instead of canned progress strings. Vue renders those events in a live "What the agent did" timeline and still falls back to persisted `debug_trace` on refresh.
- **Helpdesk agent — Phase 3 metrics** — added Prometheus series for tool latency, supervisor decisions, estimated tokens, and turns taken: `chatbot_helpdesk_agent_tool_latency_seconds`, `chatbot_helpdesk_agent_decision_total`, `chatbot_helpdesk_agent_tokens_total`, and `chatbot_helpdesk_agent_turns_taken`.
- **Helpdesk agent — trajectory eval gate** — added `backend/tests/eval/helpdesk_agent_scenarios.json`, `test_helpdesk_agent_scenarios.py`, `tox -e agent-eval` for PR-gated mock trajectory metrics, and `tox -e agent-eval-live` for nightly/manual live LLM supervisor comparison.
- **Helpdesk agent guardrails** — added `HELPDESK_AGENT_MAX_TURNS`, `HELPDESK_AGENT_MAX_QUESTIONS`, `HELPDESK_AGENT_MAX_TOOL_RETRIES`, `HELPDESK_AGENT_MAX_TOKENS_PER_SESSION`, and `HELPDESK_AGENT_DEADLINE_SECONDS` defaults for Phase 0 budget enforcement.
- **Local Postgres via Docker Compose** — added a repo-root `docker-compose.yml` with a `postgres:14` `db` service, first-run database bootstrap SQL, and backend runner startup/health-check wiring so local development no longer depends on Homebrew Postgres by default.
- **Database listener guard** — the backend runner now detects non-Docker listeners on port 5432 and asks developers to stop them or opt into `SKIP_DOCKER_DB=1`, preventing accidental connections to an old local Postgres.

### Changed

- **Quick start database setup** — README and operations docs now lead with `docker compose --env-file /dev/null up -d db`, document `SKIP_DOCKER_DB=1` for existing Postgres services, and preserve a one-release Homebrew fallback path.
- **Development database URL** — local development defaults now use `127.0.0.1` instead of `localhost` so macOS does not accidentally route `localhost` to an existing Homebrew Postgres listener while Docker publishes IPv4.

### Fixed

- **Backend pytest no longer hangs forever on a fresh Docker Postgres (macOS).** `backend/tests/conftest.py` shelled out to `psql -lqt` / `createdb -h localhost` to bootstrap the `chatbot_test` database. On macOS, `localhost` resolves to `::1` first and Docker Desktop publishes the Postgres listener on IPv4 only; the IPv6 TCP handshake completes through vpnkit/gVisor but the Postgres backend never receives the startup packet, so libpq blocks indefinitely on the server greeting and pytest's main thread parks in `os.waitpid` before any test runs — looking like `tests/api/test_auth.py::test_register` is "stuck in a loop" when in fact the first session fixture never returned. The conftest now (1) forces `127.0.0.1` (rewriting `localhost` if set), (2) passes `PGPASSWORD` and `-w` so libpq fails fast instead of waiting on a closed stdin password prompt, (3) caps the connect handshake with `PGCONNECT_TIMEOUT=5` and the subprocess with a 30 s wall-clock `timeout`, and (4) re-raises a clear `RuntimeError` ("On macOS this usually means localhost resolved to IPv6…") so the next person hits a loud error instead of an open-ended stall. `.env.test` is updated to default `POSTGRES_HOST=127.0.0.1` to match `DATABASE_URL` in dev.
- **Helpdesk agent multi-turn UI — next question now appears below the user reply.** `frontend-vue/src/components/chat/AgentTurnActions.vue` previously upserted the existing assistant bubble in place when a follow-up turn arrived after a pill/radio click, which left the next question above the just-added user message — once the chat was scrolled to the bottom it read as "nothing happened" after the user picked an option. The button-driven path now matches the free-text reply path (`addAssistantMessage`), so each new agent turn appends a fresh bubble directly under the user's answer. `MessageBubble.vue` gates `<AgentTurnActions>` and the "agent is running" timeline pulse by `isLastMessage`, so older bubbles freeze into read-only history and don't expose stale clickable pills/radios. The `recordAgentTurnIntoChat` upsert is retained for the genuinely-terminal callers that swap a pending bubble for a final result without an intervening user reply (abort-on-mode-change, manual ticket file, helpdesk-escalation chip). New tests: `MessageBubble.test.ts` covers the `isLastMessage` gate (renders on last, hidden otherwise) and `AgentTurnActions.test.ts` asserts the bubble order `[prior agent → user reply → new agent]` after a pill click.
- **Helpdesk docs truth-in-advertising** — README and helpdesk docs now separate the shipped deterministic runner from the target LLM supervisor / compiled `StateGraph` / `AsyncPostgresSaver` migration tracked in ADR-006.

### Security

- **Helpdesk tool input redaction** — redacts outbound KB retry, Tavily/web-search, and GitHub duplicate-search queries before provider calls so cloud keys or tokens pasted by a user do not leave the app in tool parameters.

## [v3.0.0] — 2026-05-31

### Added (docs refresh pass — PRs #50, #51)

- **Docs — releases hub** — consolidated `docs/release-notes/index.md` (v1.0 / v2.0 / v3.0.0); dropped duplicate `docs/README.md` ([#50](https://github.com/sandeep-jay/campus-rag-assistant/pull/50)).
- **Docs — ADR-006** — [ADR-006](../docs/adr/ADR-006-live-llm-supervisor-migration.md) records the LLM supervisor migration plan; [helpdesk/index.md](../docs/helpdesk/index.md) gains a shipped-vs-target row table ([#51](https://github.com/sandeep-jay/campus-rag-assistant/pull/51)).

### Changed (docs refresh pass — PRs #52–#57)

- **Docs — reviewer introductions** ([#57](https://github.com/sandeep-jay/campus-rag-assistant/pull/57)) — aligned README, docs landing, Reviewer Guide, Case Study, and Architecture around one canonical product introduction; reordered first-visit sections around product features and architecture; added Azure retrieval parity in Architecture/Design; extended `scripts/check_docs.py` to enforce intro + capability rows.
- **Docs — first-visit polish** ([#56](https://github.com/sandeep-jay/campus-rag-assistant/pull/56)) — moved operational runbooks into `docs/operations-manual/`, added an operations-manual landing page, and tightened the root README, docs landing, Reviewer Guide, and Case Study so first-time reviewers see crisp portfolio value before release history or deep reference material; collapsible primary nav on the docs site.
- **Docs cleanup arc** ([#50](https://github.com/sandeep-jay/campus-rag-assistant/pull/50)–[#54](https://github.com/sandeep-jay/campus-rag-assistant/pull/54)) — six-PR documentation consolidation: releases hub; helpdesk shipped-vs-target labels + ADR-006; ARCHITECTURE + DESIGN refresh with LANGGRAPH/WEB_RESEARCH folded into DESIGN; operations surface consolidated (PERFORMANCE, PRODUCTION_TLS, E2E, TENANT_CONFIG absorbed); `eval_baseline_2026-05-19` renamed to [eval_baseline_v2.md](../docs/eval_baseline_v2.md); SECURITY dependency floor + PRODUCT_ROADMAP Phase 6d shipped status refreshed.
- **Docs — OPERATIONS.md** ([#53](https://github.com/sandeep-jay/campus-rag-assistant/pull/53)) — absorbs local OAuth, production HTTPS/HTTP/2, Playwright E2E, campus Phase 0 performance guardrails.
- **Docs — DESIGN.md** ([#52](https://github.com/sandeep-jay/campus-rag-assistant/pull/52)) — absorbs tenant config and LangGraph KB path + opt-in web research sections; documents Azure AI Search retrieval in parity with AWS Bedrock KB.
- **Docs — EVALUATION.md** ([#54](https://github.com/sandeep-jay/campus-rag-assistant/pull/54)) — helpdesk eval distinguishes shipped metrics from planned trajectory scenario rig (Agentic Rebuild Phase 4).
- **Docs — PRODUCT_ROADMAP.md** ([#55](https://github.com/sandeep-jay/campus-rag-assistant/pull/55)) — Phase 6d marked **shipped** (`v3.0.0`); Agentic Helpdesk Rebuild is the live forward track.

### Fixed (docs refresh pass)

- **Docs drift** — helpdesk spec and ADR-005 no longer overstate LLM supervisor, compiled StateGraph, enforced budgets, and trajectory eval as shipped.


### Added

- Helpdesk agent frontend wiring: Vue now starts the helpdesk agent from unresolved KB answers or AGENT-mode chat input, renders each agent journey as one assistant bubble with an activity timeline, resumes sessions from in-chat actions, streams start/resume progress over SSE with fallback to non-streaming calls, and hands `draft_ready` turns to the existing ticket review modal.
- Helpdesk agent UX controls: added the ASK/AGENT mode switch, agent outcome badge, accessible radio/pill action rendering, cancel-on-mode-exit behavior, and sanitized telemetry for mode changes, start/resume, stream fallback, draft review, confirmation, and abort flows.

- Helpdesk agent backend Phase A-D: added the LangGraph-backed `/api/helpdesk/agent/{start,resume,confirm,abort}` flow plus `/start/stream` and `/resume/stream` SSE endpoints, SQLite checkpoint persistence, stale-question guards, classifier-driven ticket facts, retrieval/web solver tools, duplicate GitHub issue search, and HITL-gated ticket filing.
- Durable agent chat persistence: `services/helpdesk/persist.py::upsert_agent_summary` maintains one assistant `chat_messages` row per agent journey, updates it across question/info/draft/terminal turns, and stores a trimmed trace for later UI rendering.
- Helpdesk agent observability: added backend funnel/error metrics and LangSmith tracing wrappers for agent entry points, tools, and LLM helpers, all gated so tracing failures do not affect user responses.

- Design tokens v2 / chat cohesion: rebuilt the light + dark palettes around a single accent family + neutral surfaces. New tokens (`--surface-raised`, `--sidebar*`, `--accent-subtle`, `--success-subtle`, `--warning-subtle`, `--user-message*`) and elevation utilities (`shadow-soft`, `shadow-pop`, `shadow-modal`, `chat-reading-column`, `surface-dotgrid`).
- Sidebar UX: `SessionList.vue` now groups sessions by recency (`Today` / `Yesterday` / `This Week` / `Older`) with collapsible groups (state persisted in `localStorage`) and `Show more` pagination so long histories stay scannable.
- Always-visible copy-to-clipboard on every assistant message (next to like/dislike), with a transient `Copied` confirmation.
- Vue test hygiene: raised the test-only Node EventTarget listener ceiling for MSW so the full Vitest suite no longer emits the `MaxListenersExceededWarning`.
- Backend: deterministic `chat_messages` ordering — added `order_by='ChatMessage.id'` to the `ChatSession.messages` relationship and an explicit `sorted(..., key=lambda m: m.id)` in `GET /api/chat/sessions/{id}` so reloaded transcripts never reshuffle around updated rows.
- Helpdesk escalation (post-RAG): when `metadata.kb_resolved=false`, Vue shows two independent LLM-backed actions with distinct output shapes. **Summarize issue** posts a narrative `ConversationSummary` inline as an assistant message; **Create ticket** extracts a structured `TicketDraft`, opens an accessible review modal, and files the reviewed draft to GitHub.
- `POST /api/helpdesk/summarize` (recap), `POST /api/helpdesk/draft-ticket` (structured `TicketDraft`), and `POST /api/helpdesk/create-issue` (file GitHub issue) — all feature-flagged via `HELPDESK_ENABLED` and inheriting chat auth + rate limits.
- `kb_resolved` heuristic on KB chat responses (fuzzy out-of-scope detection + optional rerank score floor); propagated through SSE `done` and message metadata.
- Prometheus metrics: `chatbot_helpdesk_recap_*`, `chatbot_helpdesk_draft_ticket_*`, `chatbot_helpdesk_create_issue_total`, `chatbot_helpdesk_kb_resolved_total`.
- Mock-mode demo sentinel query: `Oracle Financials 403 error on budget reports`.

### Documentation

- **v3 documentation refresh** — versioned asset layout under `docs/assets/{architecture,product,auth}/{v1,v2,v3}/`; v3 architecture diagrams (overview, detailed, topology) and helpdesk agent screenshots; updated README, ARCHITECTURE.md, mkdocs nav; high-level release notes for v0.1, v2.0, and v3.0.0 under `docs/release-notes/`; [AGENTIC_HELPDESK_REBUILD.md](../docs/roadmap/AGENTIC_HELPDESK_REBUILD.md) roadmap added to nav.

- **Helpdesk agent surfacing** — added top-level **Helpdesk Agent** section to MkDocs nav with a new overview page (`docs/helpdesk/index.md`), pulled the existing product spec (`CONVERSATION_FLOW.md`) and engineering spec (`HELPDESK_AGENT.md`) out of the orphaned roadmap subtree into nav, replaced the ASCII topology in the engineering spec with a Mermaid diagram, expanded the helpdesk evaluation section, and cross-linked the new hub from README, docs landing, REVIEWER_GUIDE, PORTFOLIO_CASE_STUDY, DESIGN, and docs/README. Also surfaced previously-orphaned `TENANT_CONFIG.md` and `PERFORMANCE.md` in nav and broke the four ADR files out as individual nav entries (previously only `adr/README.md` was reachable).
- **ADR-005 — Bounded helpdesk agent** — recorded the decision to ship a single-supervisor LangGraph with hard tool budgets and a HITL gate on `file_ticket` rather than open multi-agent autonomy; added to the ADR index and case-study decision table.
- **`docs/PERFORMANCE.md` reframed** as a forward-looking backlog tracker (campus production-scale track) so readers do not confuse Phase 1-3 with implementation status.
- **Repository hygiene** — removed `docs/.DS_Store` from the working tree (already covered by `.gitignore`).
- Updated `docs/ARCHITECTURE.md` to mark the AGENT-mode Vue wiring as shipped on top of the backend helpdesk agent endpoints.

- Documented the backend helpdesk-agent endpoint surface, state/checkpoint model, tool flow, and HITL confirmation path in `docs/ARCHITECTURE.md`.

- Helpdesk agent design freeze (2026-05-25): new RFCs at [docs/roadmap/CONVERSATION_FLOW.md](../docs/roadmap/CONVERSATION_FLOW.md) (product spec: ASK vs AGENT modes, intent router, cross-mode behaviors) and [docs/roadmap/HELPDESK_AGENT.md](../docs/roadmap/HELPDESK_AGENT.md) (engineering spec: helpdesk LangGraph, multi-turn checkpointer, supervisor + clarifier/classifier/writer specialists, tools, HITL gate, budgets, and full P0+P1 hardening). PRODUCT_ROADMAP.md Phase 6d now points at both RFCs.
- Reposition README and MkDocs landing page to lead with ownership and architecture; move upstream attribution into a dedicated "Origin and Scope" section.
- Add `docs/REVIEWER_GUIDE.md` with 90-second read, senior-signal evidence map, and per-persona review paths; surfaced in MkDocs nav near the top.
- Replace "Demo readiness" with "Review artifacts" framing in README and docs site.
- Rewrite `docs/PORTFOLIO_CASE_STUDY.md` "My role" section so platform ownership leads and upstream context follows.
- Drop weak phrases ("not a weekend chatbot", "portfolio-grade") near the top of public-facing docs.

### Security

- **PR #44** — `no tool attribution` workflow (`.github/workflows/no-tool-attribution.yml`) scans PR title, body, and commit messages via `.githooks/tool_attribution_guard.py --check`; required on `Protect main`.
- **PR #45** — PR template trimmed to **Summary** and **Test plan** only (no Notes section).
- Patched frontend test-tooling transitive `js-cookie` advisory (`GHSA-qjx8-664m-686j`) by refreshing the lockfile to `js-cookie` `3.0.7`; `npm ci` now reports zero frontend vulnerabilities.
- Redaction pass before summarization/issue filing (emails, JWT-like tokens, AWS keys, GitHub tokens, bearer tokens, and keyed secrets).
- GitHub issue creation targets a separate private demo repo (`GITHUB_REPO`); documented in `.env.example` and `docs/operations-manual/security.md`.
- **Frontend dev-tool CVEs remediated** — upgraded `frontend-vue` test/build tooling so `npm audit --audit-level=moderate` is clean: `vite` `6.4.2`, `esbuild` `0.25.0`, `vitest` / `@vitest/coverage-v8` `4.1.7`, plus lockfile transitive fixes for `ws` `8.20.1` and `brace-expansion` `5.0.6`. Verified with `npm run typecheck`, `npm test -- --run` (130 tests), `npm run build`, and `npm audit --audit-level=moderate`. `langgraph` / `langgraph-checkpoint` alerts remain deferred because patched checkpoint/LangGraph combinations require `langchain-core` 1.x and conflict with the current LangChain 0.3 stack.
- **Vulnerable Python pins bumped to patched releases** (closes 7 Dependabot alerts on `main`):
  - `authlib==1.3.2` → `1.6.12` — patches 1 **CRITICAL** JWS injection (`GHSA-9ggr-2464-2j32`) and 5 HIGH advisories (OIDC bypass, padding oracle, DoS, account takeover).
  - `langchain==0.3.20` → `0.3.30` — patches HIGH LangSmith deserialize advisory.
  - `langchain-community==0.3` → `0.3.27` — patches HIGH advisory.
  - `streamlit==1.30.0` → `1.54.0` — patches 2 MEDIUM Windows-only path-traversal / SSRF advisories.
  Verified by running the full `backend` test suite (118 passed, 0 new regressions vs baseline) and restarting the local backend/frontend; OAuth import paths and Streamlit demo all clean. The riskier `langgraph` / `langgraph-checkpoint` major-version migration and the `vite` / `esbuild` (frontend dev tooling) bumps are tracked separately as follow-up work in the Dependabot alert queue.

### Fixed

- **Frontend theme tokens compile correctly (delete-conversation dialog overlap)** — `frontend-vue/src/assets/main.css` was using Tailwind v4 (`@tailwindcss/vite` + `@import 'tailwindcss';`) without a `@theme` block, so design-token utilities (`bg-background`, `bg-card`, `bg-muted`, `border-border`, `text-foreground`, `text-muted-foreground`, etc.) were silent no-ops. Surfaces appeared opaque only because `body` set `background-color: hsl(var(--background))`; inside the scrolling session list, the sidebar's sticky delete-confirmation panel had no actual background and rendered transparently over the session items. Added an `@theme inline` mapping for the existing `--background`, `--foreground`, `--card`, `--popover`, `--primary`, `--secondary`, `--muted`, `--accent`, `--destructive`, `--border`, `--input`, and `--ring` CSS variables so the utilities compile. Fixes the delete-conversation dialog overlap and the `UserMenu` dropdown which used the same pattern.

- **Dependency review PR guard** — added `dependency review (new high/critical CVEs)` to CI using `actions/dependency-review-action@v4`. It runs on pull requests and fails when a dependency diff introduces a new high/critical advisory. Dependabot alerts remain enabled, while Dependabot security auto-update PRs remain disabled for manual triage.
- **Secret-leak defense in depth (gitleaks layers)** — five independent guards now sit between a credential and a public push:
  1. `.gitignore` `.env*` catch-all plus pattern blocks for keys/credentials/tfvars/secrets dirs;
  2. `backend/tests/core/test_env_template.py` (every `Settings` field documented; no real-looking `SecretStr` values in `.env.example`);
  3. local `.githooks/pre-push` runs `gitleaks detect --log-opts="<remote>..HEAD"` and fails the push on any finding (`scripts/install-hooks.sh` wires it locally and, with `--global`, into `~/.config/git/hooks`);
  4. new `tox -e secrets` env and `gitleaks (history + diff)` job in `.github/workflows/ci.yml` run `gitleaks detect --all --reflog --no-merges` on every PR and push;
  5. GitHub repo settings now have **Secret Scanning**, **Push Protection**, and **Dependabot alerts** enabled — even `git push --no-verify` is blocked at GitHub's edge for known-provider patterns. (Dependabot **security updates** / auto-PR bumps are intentionally left off — they kept breaking the build; vulnerabilities are triaged manually from the alert queue.)
- **Tool attribution guard** — `.githooks/commit-msg` delegates to `.githooks/tool_attribution_guard.py` (local strip + `--check` for CI). Strips AI-tool authorship lines (`Co-authored-by:`, `Signed-off-by:`, vendor URL footers) from commit messages. `scripts/install-hooks.sh --global` installs commit-msg + pre-push protections into `~/.config/git/hooks/`.
- **Secret hardening (Pydantic `SecretStr`)** — `SECRET_KEY`, `AWS_SECRET_ACCESS_KEY`, `AZURE_OPENAI_API_KEY`, `AZURE_SEARCH_KEY`, `OAUTH_GOOGLE_CLIENT_SECRET`, `OAUTH_GITHUB_CLIENT_SECRET`, `LANGCHAIN_API_KEY`, and `TAVILY_API_KEY` in `backend/app/config/default.py` are now typed `SecretStr`, so they redact in `repr`, logs, exceptions, and `model_dump_json`. Cleartext is read only at the boundary (JWT codec, OAuth client, Azure SDK, Tavily, LangSmith). `simple_tracer.py` no longer logs the LangSmith key in env-var dumps.
- **Pydantic settings tightening** — `DefaultSettings.model_config` switched from `extra='allow'` to `extra='ignore'` with explicit `SettingsConfigDict` (case-sensitive, UTF-8, optional `secrets_dir` for Docker/K8s secret mounts). Previously-undeclared `AZURE_SEARCH_VECTOR_FIELD` now declared (`text_vector` default) and documented in `.env.example`.
- **CI guard for env template** — `backend/tests/core/test_env_template.py` asserts every `DefaultSettings` field is documented in `.env.example` (per-field for `SecretStr` fields) and that no `SecretStr` field carries a non-placeholder uncommented value.
- **Secrets management doc** — `docs/operations-manual/security.md` now describes the load precedence, the list of `SecretStr` fields, a production checklist (secret stores, instance roles, rotation), and the leak-response runbook.

### Changed

- **Generic terminology pass** — replaced institution-specific brand names so the repo reads as a generic campus platform: `bCourses` → `Canvas LMS` across app code, prompt templates, frontend strings, and eval fixtures (~330 occurrences across 15 files); FastAPI app title, description, and welcome message rebranded to `Campus AI Assistant API`.

- **Sample tenant renamed** — `samples/berkeley/tenant_rag_config.json` → `samples/acme-university/tenant_rag_config.json`; `assistant_name` becomes "Acme University Teaching & Learning Assistant" so the sample reads as a generic placeholder rather than a real institution.

- **Documentation accuracy pass** — aligned CI/branch-protection docs with `Protect main` required checks, local tox parity (`secrets` without mandatory `docs`), `PIP_SYNC=0` backend startup, helpdesk agent API surface, and roadmap status after helpdesk merge (PRs #37–#43). Also surfaced the helpdesk agent in README, docs landing page, REVIEWER_GUIDE, PORTFOLIO_CASE_STUDY, DESIGN, OPERATIONS (runtime flags + metrics), SECURITY (privacy/redaction/kill-switch), CI (env vars), and EVALUATION (agent scenario eval).

- **Environment identifier consolidated** — dropped the legacy `ENVIRONMENT` field from `DefaultSettings`/`DevelopmentSettings`/`TestSettings`; `APP_ENV` is now the only source of truth. Updated `backend/app/main.py`, `backend/app/api/oauth_routes.py`, `backend/verify_configs.py`, `frontend-streamlit/app/{config,main}.py`, `scripts/verify_oauth.py`, `tox.ini` (removed three redundant `ENVIRONMENT = test` lines), `.env.example`, and `docs/ARCHITECTURE.md`.
- **GitHub Pages documentation site** — added MkDocs Material scaffold, docs CI build/deploy workflow, `tox -e docs`, a Pages landing page, and README/documentation positioning polish around the independent extension framing.
- **`.env.example` rewritten** into 16 numbered sections with explicit `[REQUIRED]` / `[REQUIRED IF <cond>]` / `[OPTIONAL — default: <v>]` labels on every entry; duplicates removed and previously-undocumented fields added.
- **`.env.test` reorganized** to mirror the same section numbering as `.env.example`; `APP_ENV=test` set explicitly.

---

## [2026-05-19] — Portfolio polish (PR #24)

### Changed

- **Docs (portfolio polish)** — README restructured for progressive disclosure (pitch, role alignment, highlights, upstream delta, quality baseline); added [PORTFOLIO_CASE_STUDY.md](../docs/PORTFOLIO_CASE_STUDY.md), [docs/adr/](../docs/adr/) (4 ADRs), [PRODUCTION_HARDENING.md](../docs/operations-manual/production-hardening.md); reframed [EVALUATION.md](../docs/EVALUATION.md) baseline paragraph; updated [docs/README.md](../docs/README.md) index.
- **README** — Overview without `<details>` collapsibles (full architecture, design, screenshots, LangSmith traces visible); CI status badge.
- **Eval** — expanded [eval_baseline_2026-05-19.md](../docs/eval_baseline_2026-05-19.md) (retained AWS scores, Azure sweep table, findings); eval respects LangGraph when `RAGAS_EVAL=1`; Phase 5 script precision-balanced profile; `RAGAS_DO_NOT_TRACK` in tox eval.
- **Logging** — `RequestIdFilter` on handlers; redact JWT payloads and chat queries at INFO; cap vendor loggers; optional `LOG_JSON`; access log via `app.access`; single idempotent `initialize_logger()`.
- **Docs** — documentation cohesion: [DESIGN.md](../docs/DESIGN.md) (product boundaries, decisions); README problem/quality sections; rename [PRODUCT_ROADMAP.md](../docs/roadmap/PRODUCT_ROADMAP.md); de-portfolio language; generic campus/Canvas LMS framing; document Bedrock KB + OpenSearch Serverless alongside Azure Search; expanded [docs/README.md](../docs/README.md) index; [ARCHITECTURE.md](../docs/ARCHITECTURE.md) LangGraph/OAuth/research_mode; [WEB_RESEARCH.md](../docs/roadmap/WEB_RESEARCH.md) KB path diagram; [CI.md](../docs/operations-manual/ci-cd.md) portfolio quick tox note; [E2E.md](../docs/E2E.md) OAuth note; [RELEASE.md](../docs/operations-manual/release.md) tag message; deduped CHANGELOG `[Unreleased]`.

---

## [2026-05-19] — Portfolio features (PRs #13–#17)

### Added

- **Phase 5 retrieval** — multi-query expansion/fusion, optional Bedrock/client metadata filters, rerank node (condense → multi_query → retrieve → rerank → generate).
- **Phase 5 rerank** — LangGraph `rerank` node; FlashRank + keyword fallback; `RERANK_*` settings; candidate fetch via `RERANK_CANDIDATE_K`.
- **Phase 3 lite** — README Quality & observability; LangSmith `chat-session-*` run names; curated golden `ground_truth`; `scripts/promote_golden_draft.py`.
- **RAGAS golden bootstrap** — `scripts/bootstrap_golden_dataset.py`, `backend/tests/eval/seed_questions.json`; golden set refreshed from live AWS KB (10 rows).
- **OAuth (dev)** — API-port OAuth + one-time handoff to Vue (`/oauth/handoff`) fixes GitHub `state_mismatch` across Vite proxy ports.

### Changed

- **Docs** — README refresh (highlights, LangGraph/web/eval features, stack table); screenshot gallery under `docs/assets/{product,observability,auth}/`; doc index ([docs/README.md](../docs/README.md)), [ARCHITECTURE.md](../docs/ARCHITECTURE.md), [WEB_RESEARCH.md](../docs/roadmap/WEB_RESEARCH.md); consolidated LangSmith capture in [EVALUATION.md](../docs/EVALUATION.md); `.gitignore` for `.cursor/` and golden draft.
- **Phase 5 retrieval tuning** — RRF document fusion, keyword prefilter before rerank; tuned eval profile in `scripts/run_eval_phase5.sh` (faithfulness/recall up vs initial Phase 5; precision still below gate).
- **Phase 3 lite** — portfolio RAGAS baseline policy; LangSmith trace screenshots in README; Phase 3 roadmap marked done (lite).

### Fixed

---

## [2026-05-19] — GitHub Actions CI/CD

### Added

- **CI/CD** — GitHub Actions: [`ci.yml`](../.github/workflows/ci.yml) (tox on `main` + PRs), [`cd.yml`](../.github/workflows/cd.yml) (Vue build + optional EB deploy on `qa`/`release`); [docs/operations-manual/ci-cd.md](../docs/operations-manual/ci-cd.md). Removed `.travis.yml`.

### Fixed

- **CI** — pin `@rollup/rollup-*` platform packages in `frontend-vue` optionalDependencies (fixes Linux `npm ci` optional-deps bug).
- **CI** — use `HUSKY=0 npm ci` (not `--ignore-scripts`) so Rollup native bindings install on Linux runners.
- **CI** — `frontend-vue` tox env skips `nvm use` when `CI=true` (GHA) or nvm is absent; CI workflow runs tox sequentially.

### Changed

- **CI** — `tox -e lint,backend,frontend-vue` green; ruff format/fix, LangGraph import fixes, ChatView `research-mode` binding.
- **Docs** — roadmap cleanup: [PRODUCT_ROADMAP.md](../docs/roadmap/PRODUCT_ROADMAP.md) is the single index; removed `TODAY_SPRINT.md` and `roadmap/README.md`; campus scale track moved to [archive/PHASED_IMPROVEMENT_ROADMAP.md](../docs/roadmap/archive/PHASED_IMPROVEMENT_ROADMAP.md).
- **Tests** — `conftest` forces `RAG_ENGINE=chain` so API stream tests stay isolated from developer `.env`.

---

## [2026-05-18] — Security dependency bumps

### Changed

- **Runtime dependencies** — FastAPI 0.115.x (Starlette CVE fixes), `python-multipart>=0.0.27`, `python-jose>=3.4`, `PyJWT>=2.12`, `requests`/`urllib3`/`httpx` upgrades, `gunicorn>=22`, `python-dotenv>=1.2.2`.
- **LangGraph pins** — exact `langgraph==0.2.76` + `langgraph-checkpoint==2.0.26` (resolves `httpx` conflict with LangChain 0.3).

### Added

- **[docs/operations-manual/security.md](../docs/operations-manual/security.md)** — audit commands, production hardening checklist, dependency policy.

---

## [2026-05-18] — LangGraph live validation (AWS KB parity)

### Added

- **LangGraph live path** — `run_rag_graph` import fix; live AWS KB smoke validated with `RAG_ENGINE=langgraph` (sources + coherent answers).
- **LangGraph SSE** — status event while graph runs in `asyncio.to_thread`; paced token chunks for progressive UI (simulated streaming until graph-native stream).
- **Web research (frontend)** — `research_mode` on API; Pinia + `ChatInput` toggle when `VITE_WEB_RESEARCH_ENABLED=true` (server `WEB_RESEARCH_ENABLED` required).
- **Docs** — sprint checklist updates; LangGraph latency notes in [LANGGRAPH.md](../docs/roadmap/LANGGRAPH.md).

### Changed

- **Dependencies** — pin `langgraph` 0.2.x + `langgraph-checkpoint` 2.x for LangChain 0.3 compatibility (see upcoming security branch for broader bumps).
- **`scripts/run-backend-venv.sh`** — start via `./venv/bin/python -m uvicorn` so reload uses project venv.

### Fixed

- **Answer leakage** — stronger `_strip_condensed_question_leakage` (backend + `normalizeAssistantContent`).
- **Empty-state prompts** — `{{ prompt }}` mustache in `MessageList.vue`.
- **SSE burst render** — `requestAnimationFrame` between tokens in `chat.ts`.
- **Graph unit tests** — mock patch fixture and KB-path LLM stub.

---

## [2026-05-18] — GitHub OAuth, LangGraph scaffold, and chat UI polish

### Added

- **GitHub OAuth** — `POST /api/auth/oauth/{provider}/start` and callback routes; `OAuthButtons.vue`; Alembic `0003` user OAuth fields; `scripts/verify_oauth.py`.
- **`backend/app/core/auth_cookies.py`** — shared HTTP-only JWT cookie helpers for login and OAuth.
- **RAG streaming** — `stream_query_async()` via LangChain `astream_events`; SSE `status` events; condensed-question leakage stripping in `rag.py`.
- **LangGraph scaffold** — `backend/app/services/graph/` (runner, nodes, state); opt-in `web_search` tool; `RAG_ENGINE=langgraph` config (default remains `chain`).
- **Docs** — [PRODUCTION_TLS.md](../docs/PRODUCTION_TLS.md) (HTTPS + OAuth redirects); [SPRINT_2026-05-18_LANGGRAPH.md](../docs/roadmap/archive/SPRINT_2026-05-18_LANGGRAPH.md); [WEB_RESEARCH.md](../docs/roadmap/WEB_RESEARCH.md).
- **Vue chat UI** — typography scale (`text-chat-*`, `.chat-prose`); wider layout; mobile sidebar overlay; accessible user message accent; assistant sources stacked below replies; sticky composer.

### Changed

- **Local dev defaults** — Vite on `http://127.0.0.1:5173` (`strictPort`); `FRONTEND_URL` / `OAUTH_REDIRECT_BASE_URL` aligned to avoid `MismatchingStateError` (see [PRODUCTION_TLS.md](../docs/PRODUCTION_TLS.md#local-oauth-development)).
- **Frontend** — Pinia chat store appends stream tokens immediately; dedicated `/api/chat/stream` Vite proxy (no buffering).
- **Auth API** — login/register use shared cookie helpers; OAuth links or creates users by provider subject.
- **Roadmap docs** — LangGraph and portfolio roadmap updated for sprint status.
- **`requirements.txt`** — LangGraph-related dependencies for graph scaffold.




## [2026-05-18] — Generic tenant-hydrated RAG prompts

### Added

- **`backend/app/services/tenant_rag_config.py`** — load branding from env + `tenant.rag_config` (JSONB).
- **Alembic `0002`** — `tenant.rag_config` column.
- **`docs/TENANT_CONFIG.md`** — config shape and resolution order.
- **`samples/acme-university/tenant_rag_config.json`** — generic campus sample tenant profile (not default; renamed from the original `samples/berkeley/` path during the documentation accuracy pass).

### Changed

- **Prompt templates** — generic `prompt_prefix.txt` / `few_shot_examples.json` with `{{placeholders}}`.
- **Chat + RAG** — hydrate prompts per request from the signed-in user's tenant.
- **`PROJECT_NAME`** / **`.env.example`** — `ASSISTANT_NAME`, `SUPPORTED_TOPICS`, `OUT_OF_SCOPE_MESSAGE`.
- **README** — bring-your-own KB + tenant config.

---

## [2026-05-18] — Performance Phase 0 quick wins

### Added

- **`docs/PERFORMANCE.md`** — Phase 0 shipped tuning; documentation checklists for Phase 1–3.
- **Config:** `CHAT_HISTORY_MAX_MESSAGES`, `STREAM_ARTIFICIAL_DELAY_MS`, `SQLALCHEMY_POOL_SIZE`, `SQLALCHEMY_MAX_OVERFLOW` (see `.env.example`).
- **Prometheus:** `chatbot_chat_first_token_latency_seconds` (SSE time-to-first-token).
- **Test:** `test_get_session_messages_respects_max_messages`.

### Changed

- **Streaming:** removed fixed `time.sleep` on SSE tokens; optional demo delay via `STREAM_ARTIFICIAL_DELAY_MS` in RAG only.
- **Chat API:** `_load_chat_history()` caps messages passed to LangChain.
- **DB:** SQLAlchemy engine uses configured pool + `pool_pre_ping`.
- **`run_services.sh`:** multi-worker uvicorn via `API_WORKERS` / `UVICORN_WORKERS` (default 2).
- **`docs/operations-manual/operations.md`:** SLOs split for auth/session vs live RAG; first-token alert hint.
- **`docs/roadmap/PHASED_IMPROVEMENT_ROADMAP.md`:** Phase 0 perf shipped note; FlashRank marked Phase 2 / not in `rag.py` yet.

---

## [2026-05-18] — Docs cleanup and Campus RAG Assistant rebrand

### Changed

- README: product-first **Campus RAG Assistant** opening; license/attribution under License.
- GitHub repo renamed to [**campus-rag-assistant**](https://github.com/sandeep-jay/campus-rag-assistant); About description updated.
- **changelog/CHANGELOG.md** — single session-based log under `changelog/` (other files in folder gitignored).
- Trimmed **ARCHITECTURE.md**; clarified known gaps (buffered chat vs SSE).

### Removed

- `docs/PORTFOLIO.md`, `docs/EXECUTION_PLAN.md`, `docs/DOC_AUDIT.md`, `scripts/new-changelog.sh`.

### Added

- Full session history in **changelog/CHANGELOG.md** (2025 Berkeley baseline + 2026 fork sessions).

---

## [2026-05-17] — tox and Vue in CI

*Merged as PR #9.*

### Added

- **tox** `frontend-vue` env: `npm ci`, typecheck, ESLint, Vitest (Node 20 via `.nvmrc`).
- **requirements.txt**: `langchain-openai`, Azure SDKs; `bcrypt>=4.0.1,<4.1.0` for passlib in tox.
- Lazy Azure provider imports in `backend/app/services/providers/__init__.py`.

### Changed

- **tox** `backend`: `RATE_LIMIT_ENABLED=false`, exclude `slow` (RAGAS) by default.
- **README** Testing: `tox -e lint,backend,frontend-streamlit,frontend-vue`.
- Ruff/pytest marker cleanups.

---

## [2026-05-17] — Portfolio publish to GitHub

*PRs #1–#8 → [campus-rag-assistant](https://github.com/sandeep-jay/campus-rag-assistant) `main`.*
*Packages work from May 2026 dev sessions into reviewable commits.*

### PR #1 — Dev tooling

- `.githooks/pre-commit`, `scripts/install-hooks.sh`, `run-backend-venv.sh`, `run-frontend-vue.sh`, `kill-dev-servers.sh`, load-test helpers.
- `.gitignore` portfolio hygiene.

### PR #2 — Alembic

- `alembic.ini`, `backend/alembic/`, `0001_initial_schema.py`.

### PR #3 — Platform middleware

- `request_context.py`, `metrics.py`, `rate_limit.py`, `dev_routes.py`; wired in `main.py`, `auth.py`, `chat.py`.

### PR #4 — Providers, RAG, eval

- `backend/app/services/providers/` (AWS / Azure / mock); `rag.py` registry wiring.
- `backend/tests/eval/` RAGAS golden harness.

### PR #5 — Vue 3 SPA

- `frontend-vue/` scaffold, API/auth, chat UI, sessions, sources, Vitest + Playwright scaffolding.

### PR #6 — Streamlit client

- `frontend-streamlit/` (auth, chat services, UI components, pytest).

### PR #7 — Load tests

- `load-tests/` k6 smoke + auth-chat-session; user seed script.

### PR #8 — Docs and README

- `docs/` architecture, operations, E2E, evaluation, roadmaps, LangGraph design.
- Portfolio **README**, mock **`.env.example`**.

### Post-publish cleanup (PR #7–#8 follow-ups)

- Removed duplicate **`frontend/`** tree; **`run_services.sh` / tox** → `frontend-streamlit/`.
- **`main.py`**: `create_all` only in dev/test; **`requirements.txt`**: `alembic`, `redis`.
- Removed root **`root-open-k6.js`**, empty root **`package-lock.json`**.

---

## [2026-05-01] — RAG platform, Vue, providers (dev session)

*Implementation work; landed on `main` via 2026-05-17 PRs above. Some session notes describe features not merged.*

### Added — on `main`

- **Vue 3 SPA**, **Streamlit** tree, **provider registry**, **Redis rate limiter**, **Prometheus metrics**, **dev routes**, **RAGAS eval**, core **scripts**.

### Added — session plan only (**not** on `main`)

- **`POST /api/chat/stream` (SSE)**; **FlashRank** `RERANK_*`; extra tox envs (`eval`, `load-smoke`, …).

### Changed / fixed / security

- **`rag.py`**, **`chat.py`**, schemas, **`.env.example`**, **requirements**, **ruff** / **pytest**; password rules; `MessageBubble.vue`; generic chat 500s; EB health proxy.

### Follow-ups

- RAGAS golden Q&A; production `REDIS_URL`; LangGraph / SSE / rerank — [docs/roadmap/LANGGRAPH.md](../docs/roadmap/LANGGRAPH.md).

---

## [2026-05-01] — Logging and request correlation (dev session)

### Summary

One **request id** per HTTP request (`X-Request-ID`); optional **JSON** logs; quieter **auth** logs.

### Added

- `request_context.py`, `LOG_JSON`, tests, `kill-dev-servers.sh`, Vue `interceptors.ts` for `X-Request-ID`.

### Changed / removed / security

- `logger.py`, `main.py`, `security.py`, config; removed unused `LOGGING_PROPAGATION_LEVEL`; no JWT dumps at INFO.

---

## Berkeley ETS Chabot (baseline)

**Chabot** — campus RAG chatbot for **UC Berkeley ETS** over AWS Bedrock.  
Upstream: [ets-berkeley-edu/chabot](https://github.com/ets-berkeley-edu/chabot).  
© The Regents of the University of California — [LICENSE](../LICENSE).

**[sandeep-jay](https://github.com/sandeep-jay)** led implementation (CBO-tracked PRs below). Regents headers remain on derived files in this fork.

---

## [2025-08-01] — Streamlit UX and frontend tests

### Added

- Streamlit refactor: chat interface, message display, feedback UI and stylesheets ([CBO-86]).
- Frontend test suite covering auth, chat, and message modules ([CBO-89]).

---

## [2025-06-13] — Backend and API test suites

### Added

- Pytest for RAG workflow, AWS/Bedrock/LangSmith, auth, DB/models/services ([CBO-69], [CBO-71], [CBO-72], [CBO-84]).
- Chat API interaction tests: CRUD, feedback, sources, mocks ([CBO-70]).
- **`pyproject.toml`** tool config; tox/travis alignment ([CBO-72]).

---

## [2025-06-05] — Streamlit cleanup

### Changed

- Removed basic Streamlit prototype in favor of modular refactor ([CBO-99]).

---

## [2025-05-30] — Chat API and Streamlit auth

### Added

- Chat endpoints: sessions, messages, feedback, `test_langsmith` ([CBO-45]–[CBO-47]).
- Streamlit login, auth module, client services ([CBO-65], [CBO-66], [CBO-80], [CBO-81]).

---

## [2025-05-29] — JWT auth and advanced RAG

### Added

- JWT authentication module and auth endpoints ([CBO-74], [CBO-75]).
- Advanced RAG with Bedrock integration ([CBO-85]).

---

## [2025-05-28] — Elastic Beanstalk deploy sketch

### Added

- `.ebextensions` and Nginx config for FastAPI + Streamlit ([CBO-63]).

---

## [2025-05-12] — Bedrock RAG and first UI

### Added

- AWS, LangChain, Bedrock; simple RAG and `/chat` integration; prompt templates ([CBO-31], [CBO-34], [CBO-36], [CBO-41]).
- Basic Streamlit chat UI + LangSmith tracing ([CBO-36], [CBO-42]).
- **ruff** and **tox** ([CBO-67]).

---

## [2025-05-05] — FastAPI foundation

### Added

- FastAPI boilerplate (`/`, `/health`) ([CBO-30]).
- Pydantic-settings config manager ([CBO-32]).
- Modular logger ([CBO-35]).
- SQLAlchemy + chatbot table design ([CBO-49]).

---

## [2025-05-13] — CI and README

### Added

- Travis CI linters ([CBO-82]).
- README instructions ([CBO-82]).

### Changed

- `.gitignore` for `.tox` and `.ruff*` ([NOJIRA]).
