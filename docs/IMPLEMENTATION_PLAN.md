# InsightMesh Implementation Plan

**Status:** Active tracker  
**Delivery strategy:** Docker-first, PostgreSQL-first vertical slice  
**Last updated:** 2026-09-18  
**Product requirements:** `docs/InsightMesh_PRD.md`  
**Technical contracts:** `docs/TECHNICAL_DESIGN.md`  
**Frontend behavior:** `docs/FRONTEND_SPEC.md`

## 1. How to Use This File

This file is the project execution tracker and the source of truth for implementation order, current focus, phase gates, and verification evidence.

Status legend:

```text
[ ] Not started
[~] In progress
[x] Done and verified
[!] Blocked; blocker must be documented
```

Rules:

1. Work on the first incomplete item in **Current Focus** unless the user explicitly reprioritizes.
2. Do not start the next phase until the current phase Definition of Done is satisfied.
3. Do not mark an item `[x]` based only on code presence. Record the successful validation command in the Evidence Log.
4. Run the application, migrations, tests, lint, and builds through Docker Compose. The host machine should only require Git and Docker Desktop/Engine with Compose.
5. Keep each implementation task to one bounded vertical slice. Do not silently add features from later phases.
6. Update this file after each completed task: checkboxes, phase status, Current Focus, Next Recommended Task, and Evidence Log.
7. If the PRD, technical design, frontend spec, and this tracker conflict, stop and resolve the documentation conflict before coding.

## 2. Current Project Snapshot

Implemented artifacts currently present:

- [x] Product requirements: `docs/InsightMesh_PRD.md`
- [x] Technical design: `docs/TECHNICAL_DESIGN.md`
- [x] Frontend functional specification: `docs/FRONTEND_SPEC.md`
- [x] UI/UX skill installed at `.agents/skills/ui-ux-pro-max/`
- [x] Persisted InsightMesh design system: `design-system/insightmesh/MASTER.md`
- [x] Minimal application foundation source (health endpoints and bootstrap page only)
- [x] Docker Compose environment — four healthy services and successful one-shot migration
- [x] Backend automated test/lint/type-check infrastructure
- [ ] Evaluation runner

Overall implementation status: **Phase 2 complete; Docker foundation, backend contracts, credential boundary, and product persistence schema verified. Product APIs and analytics UI remain unimplemented**.

## 3. Current Focus

### Active Phase

**Phase 3 — Frontend shell and design system (next; not started)**

### Current Tasks

- [ ] Scaffold the strict Next.js/Tailwind frontend foundation.
- [ ] Implement the approved InsightMesh tokens and responsive application shell.
- [ ] Add typed API/error handling plus frontend test, lint, type-check, and build scripts.

### Next Recommended Task

Begin **Phase 3 — Frontend shell and design system**. Reuse the running backend and the approved tokens in `design-system/insightmesh/MASTER.md`; do not add datasource onboarding behavior scheduled for Phase 4.

### Current Design-System Proposal

Generated with `ui-ux-pro-max` using:

```text
query: internal analytics SaaS dashboard data-dense professional accessible
variance: 4/10
motion: 3/10
density: 8/10
```

Candidate direction:

- data-dense dashboard style for BI/reporting;
- light-first blue/navy surfaces with amber accent;
- restrained motion and no ornamental effects;
- accessible contrast, visible focus, keyboard navigation, reduced-motion support;
- Fira Sans for product UI and Fira Code reserved for SQL/query/data presentation (manual adjustment from the tool's raw typography suggestion);
- SVG icon family, no emoji icons;
- responsive checkpoints at 375, 768, 1024, and 1440 px.

Approved and persisted in `design-system/insightmesh/MASTER.md` during Phase 0.

## 4. Default Implementation Decisions

These defaults prevent repeated decisions during implementation. Change them here before the affected phase starts.

| Area | Default |
|---|---|
| Runtime | Docker Compose |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy |
| Python dependency management | `uv` with `pyproject.toml` and lockfile |
| Frontend | Next.js App Router, React, strict TypeScript, Tailwind CSS |
| Node dependency management | `npm` with committed lockfile |
| UI components | Accessible headless components; exact library selected during Phase 3 |
| Icons | One SVG icon family; Phosphor preferred by the UI skill |
| Charts | Adapter interface; Recharts versus ECharts remains a Phase 9 decision |
| Application database | PostgreSQL with pgvector |
| Migrations | Alembic |
| First demo datasource | Separate PostgreSQL container |
| Orchestration | Custom deterministic Lightweight Harness Runtime |
| Tests | Pytest for backend; frontend unit/component runner selected during Phase 3; Playwright for critical flows |

## 5. Docker-First Development Contract

### 5.1 Target Services

Initial vertical slice:

```text
frontend          Next.js development/production build
backend           FastAPI API and application runtime
metadata-db       PostgreSQL + pgvector application store
demo-postgres     read-only analytical demo datasource
```

Added only after the PostgreSQL quality gate:

```text
demo-mysql
demo-mongodb
```

### 5.2 Required Docker Behavior

- Every long-running service has a healthcheck.
- Backend startup waits for a healthy metadata database and completed migrations.
- Frontend configuration contains only public values such as the API base URL; server secrets never use a public environment prefix.
- Metadata and demo databases use named volumes.
- Seed and migration operations are idempotent.
- Datasource credentials used by the application are read-only.
- `.env` is ignored; `.env.example` contains placeholders and safe local defaults only.
- Containers run as non-root where practical.
- Service logs never contain passwords, connection URIs, raw PII, or raw profiling samples.
- MySQL and MongoDB services use Compose profiles or an override so they do not slow the initial PostgreSQL workflow.

### 5.3 Standard Commands

These commands become mandatory once the corresponding files/services exist:

```powershell
docker compose config
docker compose up --build -d
docker compose ps
docker compose logs --tail 100 backend
docker compose logs --tail 100 frontend
docker compose down
```

Validation commands:

Available after Phase 1:

```powershell
docker compose exec backend python tests/foundation_smoke.py
docker compose run --rm migrate
docker compose run --rm --no-deps frontend npm run typecheck
docker compose run --rm --no-deps frontend npm run build
```

The following commands become available in Phases 2–3 when their test/lint dependencies and scripts are added:

```powershell
docker compose run --rm backend uv run pytest
docker compose run --rm backend uv run ruff check .
docker compose run --rm backend uv run mypy .
docker compose run --rm frontend npm run lint
docker compose run --rm frontend npm run typecheck
docker compose run --rm frontend npm run test
docker compose run --rm frontend npm run build
```

If a command changes during implementation, update this section and the root README in the same task.

## 6. Phase Tracker

### Phase 0 — Design and Implementation Readiness

**Status:** Done

- [x] PRD completed and reviewed.
- [x] Technical design completed.
- [x] Frontend functional specification completed.
- [x] UI/UX skill installed and validated.
- [x] Product-wide design-system proposal generated and reviewed against the frontend spec.
- [x] Product-wide design system approved and persisted.
- [x] Frontend spec updated with final visual tokens and component direction.

**Definition of Done:** all implementation documents are internally consistent, visual design decisions are persisted, and no unresolved decision blocks Phase 1.

### Phase 1 — Docker and Repository Foundation

**Status:** Done

Scope note: minimal FastAPI health, Alembic baseline, and Next.js bootstrap files are prerequisites for runnable containers. They do not complete the full Phase 2 persistence or Phase 3 UI work. PRD phase numbering groups requirements differently; this tracker controls delivery milestones.

- [x] Create root project structure for `backend/`, `frontend/`, `tests/`, `evals/`, and `demo/`.
- [x] Add `.gitignore`, `.dockerignore`, `.env.example`, and root README.
- [x] Add backend and frontend Dockerfiles with development targets.
- [x] Add `compose.yaml` with `frontend`, `backend`, `metadata-db`, and `demo-postgres`.
- [x] Add healthchecks, named volumes, internal networks, and dependency conditions.
- [x] Add PostgreSQL + pgvector initialization.
- [x] Add repeatable migration command and container startup flow.

**Validation:**

```powershell
docker compose config
docker compose up --build -d
docker compose ps
```

**Definition of Done:** all four initial services start from a clean checkout, become healthy, and can communicate over the Compose network.

### Phase 2 — Backend and Persistence Skeleton

**Status:** Done

- [x] Create FastAPI application, settings validation, request ID, and health endpoint.
- [x] Configure SQLAlchemy and Alembic against `metadata-db`.
- [x] Implement initial persistence models for datasources, entities, fields, relationships, profile statistics, semantic artifacts, embeddings, query runs, dashboards, and widgets.
- [x] Add credential boundary so secrets are never returned or logged.
- [x] Add canonical API error envelope.
- [x] Add unit-test and lint/type-check infrastructure.

**Definition of Done:** migrations apply from an empty database, the backend healthcheck passes, and backend tests/lint/type-check pass in Docker.

### Phase 3 — Frontend Shell and Design System

**Status:** Not started

- [ ] Scaffold Next.js App Router with strict TypeScript and Tailwind.
- [ ] Implement approved design tokens from `design-system/insightmesh/MASTER.md`.
- [ ] Select and document accessible component primitives and one icon family.
- [ ] Build responsive application shell and routes for Sources, Ask, Dashboards, and Settings.
- [ ] Implement typed API client and canonical error handling.
- [ ] Add frontend test, lint, type-check, and build scripts.
- [ ] Add loading, empty, error, focus, keyboard, and reduced-motion foundations.

**Definition of Done:** shell routes render through Docker at 375, 768, 1024, and 1440 px widths; lint, type-check, tests, and production build pass.

### Phase 4 — PostgreSQL Connector and Datasource Onboarding

**Status:** Not started

- [ ] Implement connector protocol and PostgreSQL connector.
- [ ] Implement connection test without persistence.
- [ ] Store connection configuration through the credential boundary.
- [ ] Implement PostgreSQL schema/key/relationship introspection.
- [ ] Enforce read-only transaction behavior, allowed schemas, timeout, and row limit.
- [ ] Implement datasource list, create, detail, activate, refresh, and onboarding-status APIs.
- [ ] Build Sources list, Add PostgreSQL Connection, and datasource status UI.
- [ ] Seed a reproducible e-commerce `demo-postgres` database and read-only user.

**Definition of Done:** a user can add, test, save, introspect, and activate the demo PostgreSQL datasource entirely through the Docker environment.

### Phase 5 — Metadata, Profiling, and Semantic Index

**Status:** Not started

- [ ] Normalize PostgreSQL metadata into the canonical model.
- [ ] Implement bounded local profiling with timeout and PII exclusions.
- [ ] Persist derived profile statistics; never persist raw samples.
- [ ] Implement relationship discovery and graph representation.
- [ ] Implement semantic enrichment with structured output validation and confidence/source metadata.
- [ ] Implement embedding provider abstraction and pgvector storage.
- [ ] Implement hash-based refresh for changed metadata/profile artifacts.
- [ ] Expose safe metadata/profile summaries on datasource detail UI.

**Definition of Done:** onboarding the demo datasource produces a searchable semantic index without sending raw rows, credentials, or raw PII to the LLM.

### Phase 6 — Semantic Retrieval

**Status:** Not started

- [ ] Implement question embeddings and datasource-scoped Top-K retrieval.
- [ ] Expand retrieved entities through the relationship graph.
- [ ] Build compact query-generation context.
- [ ] Record retrieved context IDs for observability and evaluation.
- [ ] Add benchmark fixtures for schema-selection and retrieval precision.

**Definition of Done:** relevant entities and join paths are retrieved for the PostgreSQL benchmark questions with measured schema-selection accuracy.

### Phase 7 — Lightweight Harness and PostgreSQL Query Path

**Status:** Not started

- [ ] Implement runtime state model and deterministic transition table.
- [ ] Implement static skill registry for query generation and repair assets.
- [ ] Implement PostgreSQL structured query generation.
- [ ] Implement SQLGlot AST validation and `EXPLAIN` validation.
- [ ] Implement read-only execution with enforced timeout and row limit.
- [ ] Implement deterministic result verification.
- [ ] Implement bounded repair with maximum two attempts.
- [ ] Implement terminal states: completed, clarification required, blocked, failed.
- [ ] Persist safe structured execution traces and query history.
- [ ] Add query-run and trace APIs.

**Definition of Done:** benchmark questions follow deterministic state transitions; safe PostgreSQL queries execute; unsafe requests are blocked; recoverable failures repair within the retry limit.

### Phase 8 — Ask Workspace

**Status:** Not started

- [ ] Build complete-question input with active datasource guard.
- [ ] Map every runtime state to explicit UI feedback.
- [ ] Implement clarification suggestions as new independent requests.
- [ ] Implement blocked, failed, empty, truncated, and warning states.
- [ ] Implement read-only generated SQL panel with copy action.
- [ ] Implement structured execution-trace panel without hidden reasoning.
- [ ] Implement accessible result table with typed formatting and null handling.
- [ ] Preserve layout space during asynchronous states to avoid content shift.

**Definition of Done:** PostgreSQL acceptance scenarios for success, ambiguity, unsafe request, repair, empty result, and execution failure work end to end in Docker.

### Phase 9 — Visualization and Dashboard

**Status:** Not started

- [ ] Select Recharts or ECharts behind a chart adapter and record the decision.
- [ ] Implement deterministic chart compatibility and selection.
- [ ] Implement Table, KPI, Bar, Line, Pie/Donut, and Area views.
- [ ] Provide accessible data table and text summary for every chart.
- [ ] Implement dashboard creation and widget save/remove/reorder/rename.
- [ ] Implement widget refresh using stored validated query with no LLM call.
- [ ] Preserve last successful widget result when refresh fails.

**Definition of Done:** a completed PostgreSQL result can be visualized, saved, reordered, refreshed without LLM usage, and read through an accessible table fallback.

### Phase 10 — PostgreSQL Evaluation Gate

**Status:** Not started

- [ ] Create PostgreSQL Easy, Medium, Hard, Ambiguous, and Unsafe cases.
- [ ] Store expected result fixtures independent of SQL string formatting.
- [ ] Implement evaluation runner and report output.
- [ ] Measure execution rate, result accuracy, schema retrieval accuracy, repair success, safety blocking, ambiguity detection, and retrieval precision.
- [ ] Fix critical safety and correctness failures before adding connectors.

**Definition of Done:** one Docker command generates a reproducible PostgreSQL evaluation report with measured, non-placeholder results.

### Phase 11 — MySQL Expansion

**Status:** Not started

- [ ] Add `demo-mysql` Compose profile and reproducible seed data.
- [ ] Implement MySQL connector contract.
- [ ] Implement MySQL introspection, profiling, dialect generation, `EXPLAIN`, validation, and read-only execution.
- [ ] Reuse runtime, normalized metadata, UI, chart, and dashboard contracts.
- [ ] Add MySQL benchmark cases and report breakdown.

**Definition of Done:** MySQL acceptance scenarios pass without PostgreSQL regressions, and evaluation reports MySQL separately.

### Phase 12 — MongoDB Expansion

**Status:** Not started

- [ ] Add `demo-mongodb` Compose profile and reproducible seed data.
- [ ] Implement MongoDB collection/schema inference and bounded local profiling.
- [ ] Implement structured `find` and aggregation generation.
- [ ] Validate operations, nested stages, and expressions.
- [ ] Block `$out`, `$merge`, `$function`, `$where`, server-side JavaScript, and all write paths.
- [ ] Implement read-only execution and JSON-safe value serialization.
- [ ] Add MongoDB pipeline viewer and benchmark cases.

**Definition of Done:** MongoDB acceptance scenarios pass, unsafe nested pipelines are blocked, and evaluation reports MongoDB separately.

### Phase 13 — Full Evaluation and Portfolio Readiness

**Status:** Not started

- [ ] Complete approximately 40–60 benchmark questions across all datasources.
- [ ] Generate per-datasource, per-difficulty, and overall metrics.
- [ ] Run privacy/security regression tests.
- [ ] Run responsive and accessibility review using `ui-ux-pro-max`.
- [ ] Verify clean Docker setup from a fresh clone and empty volumes.
- [ ] Write root README setup, architecture, demo, limitations, and measured results.
- [ ] Add architecture diagram, screenshots, and demo recording/GIF.
- [ ] Replace all portfolio placeholder claims with measured results only.

**Definition of Done:** a reviewer can clone the repository, follow Docker instructions, run the demo and evaluation suite, and verify the claims in the README.

## 7. Cross-Phase Quality Gates

Apply these gates whenever relevant:

### Security and Privacy

- [ ] No committed secrets or real credentials.
- [ ] No credentials, raw PII, raw rows, or raw profiling samples in LLM prompts, logs, traces, fixtures, or API errors.
- [ ] SQL and MongoDB safety tests pass before execution tests.
- [ ] Datasource users are read-only.
- [ ] Timeout, row limit, allowed-schema/database, and retry limit are enforced in code.

### Frontend UX

- [ ] Visible labels and inline errors for forms.
- [ ] Keyboard navigation and visible focus.
- [ ] Normal text contrast of at least 4.5:1.
- [ ] State is not communicated by color alone.
- [ ] Reduced-motion behavior works.
- [ ] No horizontal page scroll at target widths.
- [ ] Charts have legends, exact-value access, and table fallbacks.
- [ ] Loading, empty, error, blocked, clarification, stale, and success states are explicit.

### Engineering

- [ ] Docker build is reproducible.
- [ ] Migrations and seeds are idempotent.
- [ ] Public contracts have typed schemas.
- [ ] Unit and integration tests cover new behavior.
- [ ] Documentation is updated with contract or command changes.
- [ ] Existing passing tests remain green.

## 8. Evidence Log

Add one row for each completed task or phase gate. Do not include secrets or raw datasource content.

| Date | Phase | Scope | Validation command/evidence | Result |
|---|---|---|---|---|
| 2026-09-18 | 0 | PRD, technical design, frontend spec | Documents reviewed for aligned V1 scope | Pass |
| 2026-09-18 | 0 | UI/UX skill availability | Local skill CLI executed successfully with Python 3.13.7 | Pass |
| 2026-09-18 | 0 | InsightMesh design-system proposal | `search.py --design-system --variance 4 --motion 3 --density 8` | Pass; approved |
| 2026-09-18 | 0 | Design-system persistence | `design-system/insightmesh/MASTER.md` created and aligned with approved typography/pattern | Pass |
| 2026-09-18 | 0 | Frontend visual constraints | `docs/FRONTEND_SPEC.md` updated with approved tokens and UI rules | Pass |
| 2026-09-18 | 1 | Compose configuration | `docker compose config --quiet` | Pass |
| 2026-09-18 | 1 | Build and initial startup with new named volumes | `docker compose up --build -d --wait --wait-timeout 240`; `docker compose ps -a` | Four healthy services; migrate exited 0 |
| 2026-09-18 | 1 | Networking, pgvector, migration revision, demo read-only grants | `docker compose exec backend python tests/foundation_smoke.py` | Pass, including write denial after disabling session read-only flag |
| 2026-09-18 | 1 | Migration/init idempotency | `docker compose run --rm migrate`; `docker compose exec demo-postgres sh /docker-entrypoint-initdb.d/001-demo.sh`; smoke check repeated | Pass; one probe row retained |
| 2026-09-18 | 1 | Volume persistence and restart | `docker compose down`; `docker compose up -d --wait --wait-timeout 240`; smoke check | Pass; database volumes preserved |
| 2026-09-18 | 1 | Frontend TypeScript and optimized build | `docker compose run --rm --no-deps frontend npm run typecheck` and `npm run build` | Pass; Next.js 16.3.5 |
| 2026-09-18 | 1 | Non-root application processes | `docker compose exec backend id -u`; `docker compose exec frontend id -u` | UIDs 10001 and 1000 |
| 2026-09-18 | 2 | API/settings contracts and persistence integration | `docker compose run --rm backend uv run pytest` | Pass; 6 tests |
| 2026-09-18 | 2 | Backend lint and static typing | `docker compose run --rm backend uv run ruff check .`; `docker compose run --rm backend uv run mypy .` | Pass; 16 source files type-checked |
| 2026-09-18 | 2 | Model/migration parity | `docker compose run --rm migrate alembic check` | Pass; no new upgrade operations |
| 2026-09-18 | 2 | Empty-database migration gate | temporary project `insightmesh-phase2check`: `docker compose up -d --wait`; revision/query and pytest checks | Pass; revision `963b9a2f25ea`, all services healthy; temporary volumes removed |

Phase 1 limitations: development images only; no product UI, e-commerce dataset, full unit-test suite, or evaluation runner yet. Base image tags are not digest-pinned. No existing user files were reset or committed. Previously modified frontend spec/design-system files were preserved.

## 9. Blockers and Decisions Queue

Record only unresolved items that prevent the current or next phase.

| Item | Affects phase | Status | Required decision |
|---|---:|---|---|
| Final design system | 0–3 | Resolved | Approved in Phase 0 and persisted in `design-system/insightmesh/MASTER.md`. |
| LLM/embedding providers | 5 | Deferred | Select providers and models before semantic enrichment implementation. |
| Credential encryption | 2–4 | Resolved for local V1 | Fernet payload boundary with environment key; production secret manager and rotation remain deployment decisions. |

## 10. Prompt Template for Continuing Work

Use this template for each implementation session:

```text
Read:
- docs/InsightMesh_PRD.md
- docs/TECHNICAL_DESIGN.md
- docs/FRONTEND_SPEC.md
- docs/IMPLEMENTATION_PLAN.md
- design-system/insightmesh/MASTER.md when it exists

Work on the first incomplete task in Current Focus only.
Use Docker Compose for running, building, migrations, lint, type-check, and tests.
Do not expand scope or start the next phase before the Definition of Done passes.

After implementation:
1. run the relevant Docker validation commands;
2. fix failures within scope;
3. update checkboxes, phase status, Current Focus, Next Recommended Task, and Evidence Log;
4. report changed files, validation evidence, remaining risks, and the next task.
```

For UI work, prepend:

```text
Use $ui-ux-pro-max and follow the persisted InsightMesh design system.
Read a page-specific override if one exists.
```
