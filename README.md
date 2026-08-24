# BA Agent

A **business analytics agent**: an autonomous system that perceives its environment, plans, decides, and acts to answer business questions through an enforced 6-stage methodology — Problem Definition → Data Collection → Data Preparation → Analysis → Interpretation → Recommendation — with human-in-the-loop governance at configurable stage boundaries.

> Full specification: [PRD.md](PRD.md)

## Core ideas

- **Enforced methodology** — stages are graph nodes; they cannot be skipped or reordered.
- **Stage Contracts** — every stage exits only through a validated contract with hard rules (**No-Debt-Forward**: problems are resolved in the stage where they arise).
- **HITL gates** — G1 (Problem Definition) and G6 (Recommendation) are mandatory human gates; G2–G5 are reviewable and configurable.
- **Evidence chain** — every recommendation traces back to Stage 1 success criteria through Stage 4 evidence.
- **Sandboxed computation** — all analysis code executes in E2B; no hallucinated numbers.
- **One analyst first** — architecture ready to fan out to a specialist team later without harness changes.

## Stack

| Layer | Choice |
|---|---|
| Harness | LangGraph |
| Agent loop | LangChain Deep Agents |
| Brain | OpenRouter (per-stage model routing) |
| Contracts | Pydantic v2 |
| Backend | FastAPI + WebSocket streaming + JWT auth |
| Frontend | Vite + React + TypeScript + Tailwind |
| Database | PostgreSQL + pgvector (Docker) |
| Tools | Tavily (research) · E2B (sandboxed computation) |

## Quickstart (backend dev)

```bash
# 1. Start PostgreSQL
docker compose up -d postgres

# 2. Install dependencies
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt

# 3. Configure environment
copy .env.example .env        # then fill in API keys

# 4. Run tests
pytest
```

## Layout

```
PRD.md            # the specification (source of truth)
backend/app/      # FastAPI backend: config, state, hitl, contracts, graph
tests/            # contract tests, gate policy tests, smoke tests
frontend/         # React frontend (M4)
docker-compose.yml
```

## Status

| Milestone | Scope | Status |
|---|---|---|
| M1 | Scaffold + contracts + graph core | In progress |
| M2 | Deep Agents missions + tools | Planned |
| M3 | Backend API + auth + WebSocket | Planned |
| M4 | React frontend | Planned |
| M5 | Hardening + full Docker Compose | Planned |
