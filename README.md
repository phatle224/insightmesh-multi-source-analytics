<div>
  <img width="100%" src="https://capsule-render.vercel.app/api?type=waving&amp;height=120&amp;section=header&amp;reversal=true&amp;text=InsightMesh&amp;fontSize=34&amp;fontColor=ffffff&amp;fontAlign=50&amp;fontAlignY=45&amp;animation=twinkling&amp;desc=Privacy-bounded%20natural-language%20analytics%20for%20PostgreSQL%20%26amp%3B%20MySQL&amp;descSize=15&amp;descAlign=50&amp;descAlignY=65&amp;color=gradient" />
</div>

<div align="center">
  <strong>English</strong> | <a href="README_VI.md">Tiếng Việt</a>
</div>

<h3 align="center">Ask Questions in Plain Language. Explore Your Data Safely.</h3>

<div align="center">
  <img src="https://img.shields.io/badge/BACKEND-FastAPI-009688?style=flat-square" alt="FastAPI backend" />
  <img src="https://img.shields.io/badge/FRONTEND-Next.js-262626?style=flat-square" alt="Next.js frontend" />
  <img src="https://img.shields.io/badge/DATABASE-PostgreSQL%20%2B%20MySQL-355C7D?style=flat-square" alt="PostgreSQL and MySQL" />
  <img src="https://img.shields.io/badge/QUERY-SQLGlot%20%2B%20read--only%20safety-4F6EDB?style=flat-square" alt="SQL query safety" />
</div>

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [System Architecture & Data Flow](#system-architecture--data-flow)
3. [Core Features](#core-features)
4. [System Performance & Benchmarks](#system-performance--benchmarks)
5. [Tech Stack](#tech-stack)
6. [Directory Structure](#directory-structure)
7. [Quick Start Guide](#quick-start-guide)
8. [Service Endpoints](#service-endpoints)
9. [Evaluation & Quality Gates](#evaluation--quality-gates)
10. [Security & Privacy](#security--privacy)
11. [Known Limitations](#known-limitations)
12. [Troubleshooting](#troubleshooting)

---

## Project Overview

InsightMesh is a local-first natural-language analytics workspace for PostgreSQL and MySQL. Users connect a read-only datasource, inspect schema and relationships, ask questions in plain language, review generated SQL and execution traces, and save verified results as analyses or dashboard widgets.

MongoDB is intentionally out of scope for V1. Provider enrichment is optional: local introspection, profiling, semantic retrieval, SQL validation, and deterministic execution remain usable without an external AI provider.

### Problem → Solution → Result (PSR)

| Dimension | Description |
|---|---|
| **Problem** | Business questions use natural language while databases expose technical schemas. Analysts need a safe way to understand tables, generate SQL, verify results, and reuse analyses without exposing raw data to an LLM. |
| **Solution** | Build a privacy-bounded semantic layer from metadata and profiles, retrieve relevant schema context, generate dialect-aware SQL, validate it with SQLGlot, execute through read-only connectors, and present a verified result with traceable states. |
| **Result** | A reproducible Ask workflow across PostgreSQL and MySQL with datasource inspection, ERD interactions, suggestions, chart/table fallback, dashboards, saved analyses, query history, retention, and deterministic evaluation. |

### Portal Management Interface

<div align="center">
  <img src="docs/assets/screenshots/ask.png" alt="InsightMesh Ask workspace with source-aware suggestions" width="49%" />
  <img src="docs/assets/screenshots/explore-data.png" alt="InsightMesh datasource inspect panel and interactive ERD" width="49%" />
</div>

---

## System Architecture & Data Flow

The system boundary, provider privacy boundary, deterministic query path, and datasource separation are documented in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

### End-to-End Query Pipeline

~~~mermaid
flowchart TB
    subgraph "Client Layer"
        USER["User Browser"]
        NEXT["Next.js Frontend<br/>(Sources / Ask / History / Dashboards)"]
    end

    subgraph "API Layer"
        API["FastAPI Backend<br/>(Port: 8000)"]
        HEALTH["Health & OpenAPI<br/>/api/v1/health"]
    end

    subgraph "Semantic Layer (Privacy-Bounded)"
        SEM["Semantic Retrieval<br/>(metadata + profiles only)"]
        EMB["pgvector Embeddings<br/>(schema context)"]
        LLM["Optional LLM Provider<br/>(Gemini 2.5 Flash / OpenRouter)"]
    end

    subgraph "Deterministic Query Path"
        GEN["SQL Generator<br/>(dialect-aware)"]
        VAL["SQLGlot Validator<br/>(read-only AST policy)"]
        CONN["Dialect Connector<br/>(read-only execution)"]
    end

    subgraph "Datasource Layer"
        PG[("PostgreSQL Source")]
        MY[("MySQL 8 Source")]
    end

    subgraph "Persistence Layer"
        META[("Metadata DB<br/>PostgreSQL + pgvector")]
        STORE["Query Runs / Saved Analyses<br/>Dashboards / Widgets"]
    end

    USER --> NEXT
    NEXT --> API
    API --> SEM
    SEM --> EMB
    SEM --> LLM
    API --> GEN
    GEN --> VAL
    VAL --> CONN
    CONN --> PG
    CONN --> MY
    API --> META
    META --> STORE
    CONN --> API
    API --> NEXT
~~~

### Runtime flow

1. **Onboard** — validate credentials, discover schema metadata, profile safe field statistics, and build a privacy-bounded semantic index.
2. **Understand** — show entities, fields, safe sample rows, profiles, relationships, ERD layout, and three source-aware question suggestions.
3. **Ask** — classify the question, retrieve relevant metadata, generate dialect-specific SQL, validate safety, and execute through the selected connector.
4. **Verify** — verify result shape and values, select a table/chart/KPI view, and expose SQL plus a safe structured trace.
5. **Reuse** — save an analysis, save a dashboard widget, refresh results in place, or rerun as a new recent activity.

The browser demo is available at [docs/assets/recordings/insightmesh-ask-demo.webm](docs/assets/recordings/insightmesh-ask-demo.webm).

---

## Core Features

### 1. Read-only datasource onboarding

Connect PostgreSQL or MySQL with encrypted credentials, allowlist databases, verify connectivity, and refresh metadata without persisting raw rows or secrets in API responses.

### 2. Datasource inspection and ERD

Inspect entities, fields, safe sample rows, semantic profiles, and relationships. The ERD supports drag-and-drop, reset-to-default, and relationship highlighting when an entity is selected.

### 3. Source-aware question suggestions

The Ask workspace provides three inline suggestions derived from the active datasource context.

### 4. Dialect-aware natural-language queries

The runtime selects PostgreSQL or MySQL deterministically, generates bounded SQL, validates statements with SQLGlot, blocks unsafe operations, executes with read-only connectors, and supports bounded repair for eligible failures.

### 5. Verified results and visualizations

Results include truthful status transitions, paginated tables, SQL, safe traces, warnings, chart/KPI recommendations, and table fallback when visualization is unsuitable.

<div align="center">
  <img src="docs/assets/screenshots/output.png" alt="InsightMesh verified result with a recommended chart and save actions" width="88%" />
</div>

### 6. Reusable analyses and dashboards

Save validated analyses with query definition and result snapshot, refresh saved results in place, and save compatible results as dashboard widgets. Recent activity is execution history; saved analyses are durable reusable assets.

### 7. Retention-aware history

Recent query artifacts expire after 7 days by default and run summaries after 90 days. Saved analyses copy the validated query definition and survive recent-activity cleanup.

---

## System Performance & Benchmarks

The latest self-authored 37-case hybrid evaluation (25 PostgreSQL and 12 MySQL cases, generated on 2026-09-21) ran in a local Docker environment against PostgreSQL and MySQL variants of the same six-table demo e-commerce schema (five commerce tables plus one foundation/health-check table):

| Metric | Result | Description |
|---|---:|---|
| **Status accuracy** | 100% | Terminal status matches expected for all 37 cases including ambiguous, out-of-scope, and unsafe |
| **Execution rate** | 100% | All completable cases executed without requiring manual intervention |
| **Result accuracy** | 100% | Verified row counts and column structure match reference expectations |
| **Mean entity recall** | 100% | All relevant schema entities retrieved in context |
| **Mean entity precision** | 66.98% | Relevant entities as a share of all retrieved context items |
| **Join-path accuracy** | 100% | Multi-table relationships resolved correctly across all join cases |
| **Easy / medium / hard accuracy** | 100% / 100% / 100% | Consistent across all difficulty tiers |
| **Unsafe case rejection** | 5 / 5 | All unsafe queries blocked before generation and database execution |
| **Out-of-scope detection** | 3 / 3 | Out-of-scope questions stopped deterministically without SQL generation |
| **Live repair usage** | 0 cases | No release case required repair; the two-attempt ceiling remains covered by deterministic runtime tests |

> **Scope and limitations**: These are bounded regression results on a small demo schema, not a claim of general accuracy on unseen production databases. Mean entity precision of 66.98% shows that retrieval still includes irrelevant context. No release case triggered live repair, so repair behavior is supported by deterministic runtime tests rather than this evaluation run.

Versioned evidence: [combined report](evals/reports/combined-latest.json), [PostgreSQL report](evals/reports/postgres-latest.json), [MySQL report](evals/reports/mysql-latest.json), and [evaluation cases](evals/).

---

## Tech Stack

### Frontend

<div align="left">
  <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/nextjs/nextjs-original.svg" height="40" alt="nextjs" />
  <img width="8" />
  <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/react/react-original.svg" height="40" alt="react" />
  <img width="8" />
  <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/typescript/typescript-original.svg" height="40" alt="typescript" />
  <img width="8" />
  <img src="https://cdn.simpleicons.org/tailwindcss/06B6D4" height="40" alt="tailwindcss" />
  <img width="8" />
  <img src="https://cdn.simpleicons.org/playwright/2EAD33" height="40" alt="playwright" />
  <img width="8" />
  <img src="https://cdn.simpleicons.org/vitest/6E9F18" height="40" alt="vitest" />
</div>

* **Next.js 16 & React & TypeScript**: App Router, server components, typed API client, and responsive workspace UIs (Sources, Ask, History, Dashboards).
* **Tailwind CSS**: Design-token-driven utility-first styling with a curated visual system.
* **Playwright + Vitest**: Browser acceptance flows and component/unit coverage.

### Backend & AI

<div align="left">
  <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/python/python-original.svg" height="40" alt="python" />
  <img width="8" />
  <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/fastapi/fastapi-original.svg" height="40" alt="fastapi" />
  <img width="8" />
  <img src="https://cdn.simpleicons.org/sqlalchemy/d71f00" height="40" alt="sqlalchemy" />
  <img width="8" />
  <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/postgresql/postgresql-original.svg" height="40" alt="postgresql" />
  <img width="8" />
  <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/mysql/mysql-original.svg" height="40" alt="mysql" />
  <img width="8" />
  <img src="https://cdn.simpleicons.org/googlegemini/4285F4" height="40" alt="gemini" />
  <img width="8" />
  <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/docker/docker-original.svg" height="40" alt="docker" />
</div>

* **FastAPI + Python**: Typed API, deterministic query state machine, SQLGlot validation, dialect connectors, result verification, and evaluation harness.
* **PostgreSQL 16 + pgvector**: Application metadata, semantic artifacts, embeddings, query runs, saved analyses, dashboards, and widgets.
* **PostgreSQL and MySQL 8**: Supported source engines with read-only execution paths.
* **Gemini 2.5 Flash**: Primary structured-generation provider; OpenRouter is a bounded fallback when configured.
* **Docker Compose + Alembic + uv + npm ci**: Reproducible services, schema migrations, and locked dependencies.

---

## Directory Structure

~~~text
insightmesh-multi-source-analytics/
├── compose.yaml                         # Local app and demo databases
├── .env.example                         # Development environment template
├── README.md / README_VI.md             # Bilingual documentation
├── backend/                             # FastAPI, connectors, query, semantic, services
├── frontend/                            # Next.js routes, components, tests, e2e
├── demo/postgres/                       # PostgreSQL demo store
├── demo/mysql/                          # MySQL demo store
├── docs/                                # Plan, PRD, design, architecture, evidence
├── design-system/insightmesh/           # Approved visual system
└── tests/                               # Backend and foundation test suites
~~~

---

## Quick Start Guide

### Prerequisites

* Docker Desktop with Linux containers, or Docker Engine with Compose v2+.
* Git, if cloning the repository.
* No host Python or Node.js installation is required.

### Step 1: Initialize the environment

~~~powershell
# Windows (PowerShell)
git clone https://github.com/phatle224/insightmesh-multi-source-analytics.git
Set-Location insightmesh-multi-source-analytics
Copy-Item .env.example .env
docker compose config --quiet
~~~

Local defaults work without editing the environment file. Use development-only values and never commit real secrets. Database initialization credentials apply when volumes are first created; changing the environment file does not rotate existing passwords.

### Step 2: Launch the stack

~~~powershell
docker compose up --build -d --wait --wait-timeout 240
docker compose ps
~~~

Four long-running services should become healthy; the migration service exiting with code 0 is expected. To include MySQL:

~~~powershell
docker compose --profile mysql up --build -d --wait --wait-timeout 240
~~~

### Step 3: Connect and ask

Open Sources, choose PostgreSQL or MySQL, enter a read-only account, set host/port/database, and run **Test connection**. For Compose databases use service hosts `demo-postgres` or `demo-mysql`; `localhost` is for a host-published database, not a sibling container.

Activate a datasource, inspect its schema or choose a suggestion, ask a complete question, and review the verified result. **Refresh** updates a saved analysis in place; **Run again** intentionally creates a new recent execution.

### Step 4: Run quality gates

~~~powershell
docker compose exec backend python tests/foundation_smoke.py
docker compose run --rm backend uv run pytest
docker compose run --rm backend uv run ruff check .
docker compose run --rm backend uv run mypy .
docker compose run --rm --no-deps frontend npm run lint
docker compose run --rm --no-deps frontend npm run typecheck
docker compose run --rm --no-deps frontend npm run test
docker compose run --rm --no-deps frontend npm run build
docker compose --profile test run --rm e2e
~~~

---

## Service Endpoints

| Service | URL | Purpose |
|---|---|---|
| **Frontend** | [http://localhost:3000](http://localhost:3000) | Sources, Ask, History, and Dashboards |
| **Backend health** | [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health) | API liveness/readiness |
| **API docs** | [http://localhost:8000/docs](http://localhost:8000/docs) | OpenAPI documentation |
| **Frontend-to-backend health** | [http://localhost:3000/api/health](http://localhost:3000/api/health) | Browser connectivity check |

Metadata and demo databases are internal Compose services and do not bind host ports by default.

### Demo datasource credentials

| Source | Host inside Compose | Port | Database | User | Password |
|---|---|---:|---|---|---|
| PostgreSQL demo | demo-postgres | 5432 | insightmesh_demo | demo_reader | DEMO_READER_PASSWORD |
| MySQL demo | demo-mysql | 3306 | insightmesh_demo | demo_reader | DEMO_READER_PASSWORD |

Both demo accounts are restricted to SELECT. For a host-installed database, use the address reachable from the backend and the actual database account.

---

## Evaluation & Quality Gates

~~~powershell
docker compose --profile mysql up -d demo-mysql
docker compose exec backend python -m evals.run_combined_evaluation --strategy hybrid
~~~

The command writes per-datasource and per-difficulty reports plus the `combined-latest.json` report. The release suite covers easy, medium, hard, ambiguous, out-of-scope, and unsafe questions.

---

## Security & Privacy

* Datasource passwords are encrypted at rest and never returned by the API.
* Connectors enforce read-only execution; SQLGlot blocks write and multi-statement operations.
* Provider context is limited to metadata, profiles, and relevant schema context. Raw rows, credentials, prompts, embeddings, and hidden reasoning are excluded.
* Query traces are structured and inspectable without exposing sensitive internals.
* Recent query artifacts are retention-managed; saved analyses retain validated definitions and result snapshots.
* Compose defaults are for development. Use separate runtime/migration roles, managed secrets, pinned image digests, and TLS before production.

---

## Known Limitations

* MongoDB is intentionally out of scope for V1.
* Query-run creation is synchronous; the UI shows a truthful waiting state.
* Dashboard arrangement currently uses keyboard-accessible move controls.
* Retrieval-context caching is deferred until repeat-hit and cost-saving evidence exists.
* Base-image tags are not pinned by digest yet.
* Provider-backed enrichment requires API keys; local introspection and deterministic tests remain usable without them.

---

## Troubleshooting

* **Connection fails from the browser** — `localhost` refers to the backend container during a connector call. Use `demo-mysql`, `demo-postgres`, `host.docker.internal` for Docker Desktop host services, or a reachable LAN address.
* **No entities are discovered** — check the allowlisted database, `information_schema` permissions, and selected schema tables, then use **Refresh metadata**.
* **Connection succeeds but the result is out of scope** — ask about fields in the active datasource and try a generated suggestion.
* **Chart becomes a table** — the result may lack a categorical dimension and numeric measure; the table is the truthful fallback.
* **MySQL demo is unavailable** — run the MySQL profile and confirm service health.
* **Migrations are stale** — run the migration service and inspect its logs.

Implementation references: [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/InsightMesh_PRD.md](docs/InsightMesh_PRD.md), [docs/TECHNICAL_DESIGN.md](docs/TECHNICAL_DESIGN.md), and [design-system/insightmesh/MASTER.md](design-system/insightmesh/MASTER.md).

<div>
  <img width="100%" src="https://capsule-render.vercel.app/api?type=waving&amp;height=120&amp;section=footer&amp;reversal=true&amp;text=Ask%20clearly%20%E2%80%A2%20Verify%20safely%20%E2%80%A2%20Reuse%20confidently&amp;fontSize=22&amp;fontColor=ffffff&amp;fontAlign=50&amp;fontAlignY=50&amp;rotate=0&amp;stroke=-&amp;animation=twinkling&amp;textBg=false&amp;color=gradient" />
</div>
