# Operations and Observability

## Runtime model (production)

- Run the API with multiple workers via gunicorn + uvicorn workers.
- Set `API_WORKERS` according to available CPU (start with `2 * cores`, cap based on DB pool).
- `run_services.sh` now traps `SIGTERM`/`SIGINT` and performs graceful child shutdown.

Example API startup:

```bash
API_WORKERS=4 API_TIMEOUT=60 API_GRACEFUL_TIMEOUT=30 USE_GUNICORN=1 ./run_services.sh
```

## Local development database

Local development uses Docker Compose Postgres by default. The repo-root `docker-compose.yml` starts a `postgres:14` service named `db`, creates `chatbot_dev`, and runs `scripts/init-db.sql` on first volume initialization.

Fresh setup:

```bash
docker compose --env-file /dev/null up -d db
alembic upgrade head
PIP_SYNC=0 ./scripts/run-backend-venv.sh
```

`scripts/run-backend-venv.sh` also starts and health-checks `db` before launching Uvicorn. If a non-Docker Postgres still owns port 5432, the runner exits instead of silently connecting to the wrong database. To use an existing Homebrew/Postgres service instead, set `SKIP_DOCKER_DB=1` and ensure `DATABASE_URL` points at that database.

Homebrew-to-Docker cutover:

```bash
# Optional: preserve local history before switching services.
pg_dump chatbot_dev > /tmp/chatbot_dev_pre_docker.sql

# Free port 5432 if Homebrew Postgres is running there.
brew services stop postgresql@14

docker compose --env-file /dev/null up -d db
alembic upgrade head

# Optional: restore history into the Compose database.
psql -h localhost -U chatbot -d chatbot_dev -f /tmp/chatbot_dev_pre_docker.sql
```

`docker compose --env-file /dev/null down` stops the database while preserving the named `pgdata` volume. Use `docker compose --env-file /dev/null down -v` only when you intentionally want to delete local database state. The explicit empty env file keeps Docker Compose from parsing the app `.env`; the backend still reads `.env` normally.


## RAG cloud providers

Select LLM and retriever backends independently via `.env` (see `.env.example`):

| Stack | `LLM_PROVIDER` | `RETRIEVER_PROVIDER` | Key settings |
|-------|----------------|----------------------|--------------|
| Mock (CI / local demo) | `mock` | `mock` | Defaults; or `RAG_FORCE_MOCK=true` |
| AWS | `aws` | `aws` | `AWS_REGION`, `BEDROCK_MODEL_ID`, `BEDROCK_KNOWLEDGE_BASE_ID` (§5) |
| Azure | `azure` | `azure` | `AZURE_OPENAI_*`, `AZURE_SEARCH_*` (§6) |
| GCP | `gcp` | `gcp` | `GCP_PROJECT_ID`, `GCP_LLM_MODEL`, `VERTEX_SEARCH_DATA_STORE_ID` (§6b) |

Mixed stacks are supported (e.g. `LLM_PROVIDER=aws` with `RETRIEVER_PROVIDER=azure`). Placeholder KB/datastore IDs fall back to mock providers. Restart the API after changing provider env vars.

## Database migration workflow (Alembic)

Alembic scaffolding is included (`alembic.ini`, `backend/alembic/`).

Create migration:

```bash
alembic revision --autogenerate -m "add_new_table"
```

Apply migrations:

```bash
alembic upgrade head
```

Rollback one migration:

```bash
alembic downgrade -1
```

LangGraph helpdesk checkpoints use the same Alembic workflow. The app does **not** call `AsyncPostgresSaver.setup()` at startup; checkpoint tables (`checkpoints`, `checkpoint_blobs`, `checkpoint_writes`) are created and versioned by migrations so saver-version bumps are explicit schema changes.

### Deploy order

1. Build artifact/container.
2. Run `alembic upgrade head` against target DB.
3. Start/restart API workers.
4. Verify `/api/health` and `/api/metrics`.


## Logging

| Setting | Purpose |
|---------|---------|
| `LOGGING_LEVEL` | App log level (`INFO` recommended for production) |
| `LOGGING_FORMAT` | Include `%(request_id)s` — wired via `RequestIdFilter` on all handlers |
| `LOGGING_LOCATION` | Rotating file path when `LOG_TO_FILE=true` (default `backend_logs.log`) |
| `LOG_JSON` | When `true`, emit one JSON object per line (for aggregators) |
| `LOG_TO_FILE` | Enable rotating file handler (10 MB × 20 backups) |

**Privacy:** JWT payloads and full chat queries are not logged at `INFO`. Use `DEBUG` locally for verbose auth/RAG text. Access lines: `app.access` logger (`METHOD path status duration`).

## Local logs

`*.log` files (`app.log`, `backend/app.log`, etc.) are gitignored. After stopping uvicorn/Vite, remove them to reclaim disk:

```bash
find . -name '*.log' -not -path './venv/*' -not -path './node_modules/*' -delete
```

## Security

See [SECURITY.md](./security.md) for `pip-audit`, bandit, and production hardening.

## Metrics baseline

Exposed endpoints:

- `GET /api/metrics` (Prometheus format)
- `GET /api/metrics/db-pool` (JSON snapshot)

Included metrics:

- HTTP request count/latency/errors
- Provider call latency and provider error reasons
- DB pool size/checkouts/overflow/usage ratio

## Dashboard and alerts baseline

### Suggested SLOs

- API availability: `>= 99.9%` monthly (`5xx` responses considered failures).
- **Auth / session API** (no LLM): `p95 < 1.2s`, `p99 < 2.5s` at steady load.
- **Chat with RAG** (live LLM + retrieval): use phase-aware targets — see [LOAD_TESTING.md](./load-testing.md) (`K6_LATENCY_PROFILE=live` allows chat `p95` up to ~45s under ramp; `mock` profile targets sub-second HTTP).
- **SSE time-to-first-token**: track `chatbot_chat_first_token_latency_seconds` (lower is better; dominated by condense + retrieve on live providers).
- Error budget: `<= 0.1%` failed requests over 30 days.

### Alerts

- **High 5xx rate**: `rate(chatbot_http_requests_total{status_code=~"5.."}[5m]) > 0.02`.
- **Slow auth/session**: same histogram on `/api/auth/*` and `/api/chat/sessions` with `> 1.2` threshold.
- **Slow buffered chat**: `histogram_quantile(0.95, sum(rate(chatbot_http_request_latency_seconds_bucket{path="/api/chat/chat"}[5m])) by (le)) > 45` for live RAG, or `> 1.2` when using mock providers.
- **Slow first token**: `histogram_quantile(0.95, rate(chatbot_chat_first_token_latency_seconds_bucket[5m])) > 30` (tune per provider).
- **Provider failures spike**: `increase(chatbot_provider_errors_total[10m]) > 20`.
- **DB pool pressure**: `avg_over_time(chatbot_db_pool_usage_ratio[5m]) > 0.85`.

## Runbook

### High latency

1. Check `chatbot_http_request_latency_seconds` by path.
2. Check `chatbot_provider_latency_seconds` for degraded providers.
3. Increase `API_WORKERS` only if CPU has headroom.
4. If DB bound, raise `SQLALCHEMY_POOL_SIZE` and validate DB connection limits.

### Elevated 5xx

1. Correlate with `chatbot_provider_errors_total` and application logs.
2. If provider timeouts dominate, tune `PROVIDER_TIMEOUT_SECONDS` and retries.
3. If DB pool saturation is high, increase pool and reduce worker count temporarily.

### DB pool saturation

1. Inspect `/api/metrics/db-pool` and dashboard for `usage_ratio` and overflow.
2. Reduce worker count or per-worker concurrency to lower connection demand.
3. Increase DB max connections and corresponding app pool settings.


## Shipped performance guardrails (campus Phase 0)

These items are **shipped on `main`** — they bound latency, cost, and connection pressure without requiring Redis or a response cache. Unbuilt campus-scale items (Redis HA, exact/semantic cache, idempotency) live in [PRODUCTION_HARDENING.md](./production-hardening.md).

| Change | Config / code | Notes |
|--------|----------------|-------|
| Chat history window | `CHAT_HISTORY_MAX_MESSAGES` | Caps prompt size on long sessions |
| Optional stream demo delay | `STREAM_ARTIFICIAL_DELAY_MS` (default `0`) | Local demo pacing only |
| SQLAlchemy pool | `SQLALCHEMY_POOL_SIZE`, `SQLALCHEMY_MAX_OVERFLOW` | Tune with worker count |
| Multi-worker API (EB) | `API_WORKERS` in [run_services.sh](../../run_services.sh) | `2 * cores` starting point |
| SSE first-token metric | `chatbot_chat_first_token_latency_seconds` | Dominated by condense + retrieve on live providers |

Load validation: [LOAD_TESTING.md](./load-testing.md). Release promotion: [RELEASE.md](./release.md), [release-notes/](../release-notes/index.md).

## Helpdesk agent runtime

| Flag / variable | Purpose |
|---|---|
| `HELPDESK_ENABLED` | Master flag for ASK-mode `/api/helpdesk/{summarize,draft-ticket,create-issue}` |
| `HELPDESK_AGENT_ENABLED` | Enables AGENT-mode `/api/helpdesk/agent/*` LangGraph endpoints |
| `HELPDESK_AGENT_KILL_SWITCH` | Set `true` to short-circuit all in-flight agent sessions (returns `aborted`) |
| `GITHUB_TOKEN` | Fine-grained PAT (`issues:write`) for the demo repo; **SecretStr**, never log |
| `GITHUB_REPO` | `owner/repo` of the **private** demo repo issues are filed to |
| `GITHUB_DEFAULT_LABELS` | Comma-separated labels added to every filed issue |
| `HELPDESK_KB_RESOLVED_MIN_SCORE` | Optional rerank-score floor for `kb_resolved` heuristic |
| `HELPDESK_DEDUP_WINDOW_SECONDS` | Suppress duplicate filings inside this window |
| `HELPDESK_SUMMARIZE_MAX_TURNS` | Number of recent chat turns fed into recap/draft |
| `HELPDESK_AGENT_LLM_SUPERVISOR` | Default `false`; when enabled, supervisor routing uses the live structured-output LLM adapter with deterministic fallback |
| `HELPDESK_AGENT_USE_LANGGRAPH_CHECKPOINT` | Default `true`; set `false` for the one-release legacy JSON SQLite rollback path |
| `HELPDESK_AGENT_CHECKPOINT_BACKEND` | `postgres` (default), `sqlite`, or `memory`; production should use `postgres`. The `sqlite` backend is an opt-in dev fallback that requires installing the unpinned `langgraph-checkpoint-sqlite` package (2.0.x carries GHSA-9rwj-6rc7-p77c, 3.x needs a LangGraph 1.x bump) |
| `HELPDESK_AGENT_CHECKPOINT_PATH` | SQLite checkpointer path for `sqlite` or legacy fallback (`.helpdesk_agent_checkpoints.sqlite` by default) |
| `HELPDESK_AGENT_CHECKPOINT_TTL_SECONDS` | Checkpoint retention window; normal agent traffic periodically prunes expired checkpoint threads |
| `HELPDESK_AGENT_CLARIFY_CONFIDENCE_FLOOR` | Default `0.75`; below this classifier confidence, the agent may ask one targeted clarification when the missing fact changes severity or routing |

Prometheus metrics: `chatbot_helpdesk_recap_*`, `chatbot_helpdesk_draft_ticket_*`, `chatbot_helpdesk_create_issue_total`, `chatbot_helpdesk_kb_resolved_total`, `chatbot_helpdesk_agent_started_total`, `chatbot_helpdesk_agent_tool_total`, `chatbot_helpdesk_agent_tool_latency_seconds`, `chatbot_helpdesk_agent_decision_total`, `chatbot_helpdesk_agent_tokens_total`, `chatbot_helpdesk_agent_turns_taken`, `chatbot_helpdesk_agent_outcome_total`, `chatbot_helpdesk_agent_funnel_total`, `chatbot_helpdesk_agent_error_total`. Engineering spec: [HELPDESK_AGENT.md](../roadmap/HELPDESK_AGENT.md).

## OAuth and authentication

Enable providers in `.env`: `OAUTH_ENABLED_PROVIDERS=github` (or `google,github`) plus client ID/secret vars (see `.env.example`). Verify setup: `./scripts/verify_oauth.py` (repo root, venv active).

### Local OAuth (Vite + GitHub)

OAuth `state` is stored in a **session cookie on the API host**. Vite's dev proxy does not reliably forward that cookie, so local GitHub login uses the **API origin** for the OAuth redirect, then a **one-time handoff** back to Vue.

| Item | Local example |
|------|----------------|
| Browser (chat UI) | `http://127.0.0.1:5173` |
| `FRONTEND_URL` | `http://127.0.0.1:5173` |
| `OAUTH_REDIRECT_BASE_URL` | `http://127.0.0.1:8000` (API, **not** `:5173`) |
| `frontend-vue/.env.local` | `VITE_OAUTH_API_URL=http://127.0.0.1:8000` |
| GitHub OAuth app callback | `http://127.0.0.1:8000/api/auth/oauth/github/callback` |

Flow: user clicks GitHub on Vue → browser hits `:8000` for OAuth → GitHub callback on `:8000` → API redirects to `http://127.0.0.1:5173/oauth/handoff?code=...` → Vue exchanges code for JWT cookies.

`localhost` and `127.0.0.1` are different hosts for cookies. Use **`127.0.0.1` everywhere** if Vite binds to it (see [`scripts/run-frontend-vue.sh`](../../scripts/run-frontend-vue.sh)). Restart the API after changing `.env`. Start a **new** OAuth flow after an error (do not refresh the callback URL).

| Symptom | Likely cause | Fix |
|---------|----------------|-----|
| `MismatchingStateError` / `mismatching_state` | Mixed `localhost` / `127.0.0.1`, or callback on wrong port | Align checklist above; callback on **:8000** |
| Same error on refresh | OAuth `code`/`state` already used or session missing | Open `/login` and try GitHub again once |
| 503 on `/api/auth/oauth/github` | Missing `OAUTH_*` credentials | Set client id/secret in `.env` and restart API |

### Production HTTPS and HTTP/2

TLS termination and HTTP/2 for browsers are handled **outside this application** by infrastructure provisioned with **Terraform** (not in this repo).

```text
Browser --HTTPS (HTTP/2 or HTTP/1.1)--> ALB (ACM certificate)
       --HTTP/1.1--> Nginx on EB instance (port 80)
       --HTTP/1.1--> Uvicorn / FastAPI (127.0.0.1:8000)
```

| Resource | Purpose |
|----------|---------|
| **ACM** | TLS certificate for the public hostname (same region as the ALB) |
| **Route 53** | `A` / `AAAA` alias to the Elastic Beanstalk environment load balancer |
| **ALB** | HTTPS listener on **443** with the ACM cert; optional HTTP **80** → redirect to **443** |
| **EB environment** | App deploy target; set env vars below |

Application configuration on EB:

| Variable | Example | Notes |
|----------|---------|--------|
| `AUTH_COOKIE_SECURE` | `true` | Required so `access_token` cookies are `Secure` over HTTPS |
| `AUTH_COOKIE_SAMESITE` | `lax` | Default; adjust if cross-site frontend |
| `OAUTH_REDIRECT_BASE_URL` | `https://api.example.com` | OAuth callback host (API, not SPA) |
| `FRONTEND_URL` | `https://app.example.com` | CORS and post-login redirect |

Register OAuth redirect URIs against your **public HTTPS** API host:

- `https://<api-host>/api/auth/oauth/google/callback`
- `https://<api-host>/api/auth/oauth/github/callback`

Verification:

```bash
curl -I --http2 https://<api-host>/api/health
curl -I --http1.1 https://<api-host>/api/health
```

Optional instance Nginx tweaks (if cookies show `http` incorrectly or SSE streams stall): forward `X-Forwarded-Proto` from the ALB; `proxy_buffering off` on `/api/` for streaming. See [`.ebextensions/00_ami.config`](../../.ebextensions/00_ami.config).

---

## Playwright E2E (frontend-vue)

Playwright lives under [`frontend-vue/e2e/`](../../frontend-vue/e2e/). Tests assume:

1. **API** is running and reachable at **`http://127.0.0.1:8000`** (default).
2. **Vite dev server** is started by Playwright (`webServer` in `playwright.config.ts`), unless `CI` reuse rules apply.

**Prerequisites:** PostgreSQL available; migrations applied (`alembic upgrade head`); backend serving `/api/health` and `/api/auth/register`.

**Via tox** (after the API is up):

```bash
tox -e e2e
```

**Manual:**

```bash
# Terminal 1
PIP_SYNC=0 ./scripts/run-backend-venv.sh

# Terminal 2
cd frontend-vue && npm run e2e
```

[`frontend-vue/e2e/global-setup.ts`](../../frontend-vue/e2e/global-setup.ts) waits for **`GET /api/health`** before registering a throwaway user and saving cookie state to `e2e/.auth/user.json`.

| Variable | Purpose |
|----------|---------|
| `PLAYWRIGHT_API_BASE_URL` | API base URL (default `http://127.0.0.1:8000`) |

For CI, run Postgres + migrations + backend **before** `npm run e2e`. Playwright global setup uses email/password register today — not OAuth.

---

## Related

- [SECURITY.md](./security.md) — dependency audit, production notes
- [LOAD_TESTING.md](./load-testing.md) — k6 profiles and latency SLOs
- [RELEASE.md](./release.md) — promotion ladder and tagging
- [release-notes/](../release-notes/index.md) — high-level summaries per tag
- [PRODUCTION_HARDENING.md](./production-hardening.md) — campus-scale backlog (Redis HA, cache, idempotency)

