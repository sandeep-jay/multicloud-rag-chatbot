# ADR-001: Provider registry (AWS / Azure / GCP / mock)

**Status:** Accepted  
**Date:** 2026-05-19

## Context

The upstream chabot targeted a single cloud stack (Bedrock + OpenSearch). Portfolio and production goals require running locally without credentials, testing in CI, and supporting AWS, Azure, and GCP retrieval paths without forking the API or UI.

## Decision

Introduce a **provider registry** selected by environment variables:

- `LLM_PROVIDER` — `aws` | `azure` | `gcp` | `mock`
- `RETRIEVER_PROVIDER` — `aws` | `azure` | `gcp` | `mock`
- `RAG_FORCE_MOCK=true` — forces mock for demos and CI regardless of other settings

Implementations live under `backend/app/services/providers/`. The API and Vue client stay provider-agnostic.

## Consequences

**Positive**

- Clone → mock mode → chat in minutes without cloud accounts.
- `tox (lint, backend, frontends)` runs on every PR without AWS secrets.
- Same response shape (`message`, `metadata`, `sources`) across providers.

**Negative**

- Operators must understand env var matrix (documented in `.env.example` and [OPERATIONS.md](../operations-manual/operations.md)).
- Azure, AWS, and GCP paths can drift in retrieval behavior; RAGAS baselines are stack-specific.

## Alternatives considered

| Alternative | Why not |
|-------------|---------|
| Single-cloud only | Blocks Azure demos and multicloud portfolio narrative |
| Implicit provider from `.env` only | Hard to support and debug; explicit vars beat magic |
| Separate repos per cloud | Duplicates API, UI, and eval harness |

## References

- [DESIGN.md — Provider registry](../DESIGN.md#provider-registry-llm-retriever)
- `backend/app/services/providers/`
- `backend/app/config/default.py`
- `.env.example`
