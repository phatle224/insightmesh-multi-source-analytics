# InsightMesh Implementation Plan

**Status:** Active tracker  
**Delivery strategy:** Docker-first, PostgreSQL-first vertical slice  
**Last updated:** 2026-09-21
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
- [x] Responsive frontend shell, design tokens, typed API client, and frontend quality tooling
- [x] PostgreSQL connector, datasource onboarding APIs, Sources UI, and Docker browser flow
- [x] Bounded local profiling, privacy exclusions, semantic provider boundary, embeddings, and safe profile UI
- [x] Phase 6 PostgreSQL retrieval benchmark runner
- [x] Deterministic Phase 7 PostgreSQL query runtime, safety, repair, and trace APIs
- [x] Deterministic datasource relevance guard with terminal `out_of_scope` state
- [x] Phase 8 Ask workspace with complete-question runs, explicit runtime states, safe trace, and verified result table
- [x] Phase 9 deterministic visualizations, dashboard persistence, and provider-free widget refresh
- [x] Phase 10 PostgreSQL evaluation, adversarial guardrails, and hybrid-retrieval quality gate
- [~] Phase 11 query history and semantic explainability
- [x] Immutable privacy-safe semantic manifests with deterministic versioning and JSON export

Overall implementation status: **Phase 11 is in progress. Cursor-paginated query history and privacy-safe versioned semantic manifests are Docker-verified; the accessible relationship graph and expanded relationship/trace explainability are next. Phase 10 remains complete with 100% result/status/execution/safety/scope/ambiguity accuracy on 20 PostgreSQL cases and hybrid retrieval precision of 65.38% versus 46.92% vector-only**.

## 3. Current Focus

### Active Phase

**Phase 11 — Query History and Semantic Explainability (in progress)**

### Current Tasks

- [x] Add paginated/filterable query-run history API and `/history` UI; rerun always creates a new independent request.
- [x] Expose a versioned semantic manifest without raw rows, credentials, embedding vectors, or raw PII, with client-side JSON export.
- [ ] Add an accessible datasource relationship graph with table/list fallback and join-path highlighting.
- [ ] Add relationship provenance/confidence and expanded safe trace evidence.
- [ ] Implement retrieval-context caching only if the Phase 10 latency/provider evidence justifies it.

### Next Recommended Task

Continue **Phase 11 — Query History and Semantic Explainability** with the accessible datasource relationship graph, table/list fallback, and join-path highlighting.

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
| Charts | Recharts behind the local deterministic visualization adapter |
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
docker compose --profile test run --rm e2e
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

**Status:** Done

- [x] Scaffold Next.js App Router with strict TypeScript and Tailwind.
- [x] Implement approved design tokens from `design-system/insightmesh/MASTER.md`.
- [x] Select and document accessible component primitives and one icon family.
- [x] Build responsive application shell and routes for Sources, Ask, Dashboards, and Settings.
- [x] Implement typed API client and canonical error handling.
- [x] Add frontend test, lint, type-check, and build scripts.
- [x] Add loading, empty, error, focus, keyboard, and reduced-motion foundations.

**Definition of Done:** shell routes render through Docker at 375, 768, 1024, and 1440 px widths; lint, type-check, tests, and production build pass.

### Phase 4 — PostgreSQL Connector and Datasource Onboarding

**Status:** Done

- [x] Implement connector protocol and PostgreSQL connector.
- [x] Implement connection test without persistence.
- [x] Store connection configuration through the credential boundary.
- [x] Implement PostgreSQL schema/key/relationship introspection.
- [x] Enforce read-only transaction behavior, allowed schemas, timeout, and row limit.
- [x] Implement datasource list, create, detail, activate, refresh, and onboarding-status APIs.
- [x] Build Sources list, Add PostgreSQL Connection, and datasource status UI.
- [x] Seed a reproducible e-commerce `demo-postgres` database and read-only user.

**Definition of Done:** a user can add, test, save, introspect, and activate the demo PostgreSQL datasource entirely through the Docker environment.

### Phase 5 — Metadata, Profiling, and Semantic Index

**Status:** Complete

- [x] Normalize PostgreSQL metadata into the canonical model (completed as the Phase 4 persistence boundary).
- [x] Implement bounded local profiling with timeout and PII exclusions.
- [x] Persist derived profile statistics; never persist raw samples.
- [x] Implement relationship discovery and graph representation.
- [x] Implement semantic enrichment with structured output validation and confidence/source metadata.
- [x] Implement embedding provider abstraction and pgvector storage.
- [x] Implement hash-based refresh for changed metadata/profile artifacts.
- [x] Expose safe metadata/profile summaries on datasource detail UI.
- [x] Verify Gemini 2.5 Flash, OpenRouter fallback boundary, and embedding calls against the live providers.

**Definition of Done:** onboarding the demo datasource produces a searchable semantic index without sending raw rows, credentials, or raw PII to the LLM.

### Phase 6 — Semantic Retrieval

**Status:** Complete

- [x] Implement question embeddings and datasource-scoped Top-K retrieval.
- [x] Expand retrieved entities through the relationship graph.
- [x] Build compact query-generation context.
- [x] Record retrieved context IDs for observability and evaluation.
- [x] Add benchmark fixtures for schema-selection and retrieval precision.

**Definition of Done:** relevant entities and join paths are retrieved for the PostgreSQL benchmark questions with measured schema-selection accuracy.

### Phase 7 — Lightweight Harness and PostgreSQL Query Path

**Status:** Complete

- [x] Implement runtime state model and deterministic transition table.
- [x] Implement static skill registry for query generation and repair assets.
- [x] Implement PostgreSQL structured query generation.
- [x] Implement SQLGlot AST validation and `EXPLAIN` validation.
- [x] Implement read-only execution with enforced timeout and row limit.
- [x] Implement deterministic result verification.
- [x] Implement bounded repair with maximum two attempts.
- [x] Implement terminal states: completed, clarification required, out-of-scope, blocked, failed.
- [x] Persist safe structured execution traces and query history.
- [x] Add query-run and trace APIs.

**Definition of Done:** benchmark questions follow deterministic state transitions; safe PostgreSQL queries execute; unsafe requests are blocked; recoverable failures repair within the retry limit.

### Phase 8 — Ask Workspace

**Status:** Complete

- [x] Build complete-question input with active datasource guard.
- [x] Map every runtime state, including out-of-scope, to explicit UI feedback.
- [x] Implement clarification suggestions as new independent requests.
- [x] Implement blocked, failed, empty, truncated, and warning states.
- [x] Implement read-only generated SQL panel with copy action.
- [x] Implement structured execution-trace panel without hidden reasoning.
- [x] Implement accessible result table with typed formatting and null handling.
- [x] Preserve layout space during asynchronous states to avoid content shift.

**Definition of Done:** PostgreSQL acceptance scenarios for success, ambiguity, unsafe request, repair, empty result, and execution failure work end to end in Docker.

### Phase 9 — Visualization and Dashboard

**Status:** Complete

- [x] Select Recharts or ECharts behind a chart adapter and record the decision.
- [x] Implement deterministic chart compatibility and selection.
- [x] Implement Table, KPI, Bar, Line, Pie/Donut, and Area views.
- [x] Provide accessible data table and text summary for every chart.
- [x] Implement dashboard creation and widget save/remove/reorder/rename.
- [x] Implement widget refresh using stored validated query with no LLM call.
- [x] Preserve last successful widget result when refresh fails.

**Definition of Done:** a completed PostgreSQL result can be visualized, saved, reordered, refreshed without LLM usage, and read through an accessible table fallback.

### Phase 10 — PostgreSQL Evaluation and Retrieval Quality Gate

**Status:** Complete

- [x] Create PostgreSQL Easy, Medium, Hard, Ambiguous, Out-of-scope, and Unsafe cases.
- [x] Store expected result fixtures independent of SQL string formatting.
- [x] Add adversarial guardrail cases for prompt injection, SQL fragments, Unicode/whitespace obfuscation, model-meta questions, and false-positive business wording.
- [x] Implement the evaluation runner and freeze a vector-only baseline before retrieval tuning.
- [x] Measure execution rate, result accuracy, entity recall/precision, join-path accuracy, repair success, safety/out-of-scope/ambiguity detection, false-block rate, provider calls, and p50/p95 latency.
- [x] Persist reproducibility metadata: datasource seed version, model/provider configuration, skill versions, metadata/profile hashes, and retrieval configuration.
- [x] Add exact identifier and lexical/business-term retrieval sourced from persisted datasource metadata, then fuse it deterministically with vector similarity before relationship expansion.
- [x] Record lexical, semantic, and fused score evidence without prompts or hidden reasoning.
- [x] Compare hybrid retrieval against the frozen baseline and fix critical safety/correctness regressions before adding connectors.

**Definition of Done:** one Docker command generates reproducible baseline and optimized PostgreSQL reports; hybrid retrieval improves measured precision without reducing result accuracy or safety, and all claims use non-placeholder results.

### Phase 11 — Query History and Semantic Explainability

**Status:** In progress

- [x] Add paginated/filterable query-run history API and `/history` UI; rerun always creates a new independent request.
- [x] Expose a versioned semantic manifest containing normalized entities, fields, relationships, privacy-filtered profile summaries, terms, metrics, artifact IDs, hashes, and configuration versions without raw rows, embedding vectors, PII, or secrets.
- [ ] Add an accessible datasource relationship graph with a table/list fallback and join-path highlighting.
- [ ] Mark relationships as database-declared or inferred; inferred edges include confidence and evidence and are excluded from generation below the configured threshold.
- [ ] Extend safe traces with per-state duration, provider/model identity, fallback usage, provider-call count, retrieval counts/scores, repair count, and validation category.
- [ ] Add a datasource/hash-scoped retrieval-context cache only after benchmark evidence shows a material latency or provider-cost benefit; invalidate by metadata hash, profile hash, and retrieval-config version rather than TTL alone.

**Definition of Done:** a user can inspect and rerun prior requests, inspect the versioned semantic context and relationship graph, and reproduce retrieval evidence without exposing secrets, raw rows, PII, or hidden reasoning.

### Phase 12 — MySQL Expansion

**Status:** Not started

- [ ] Add `demo-mysql` Compose profile and reproducible seed data.
- [ ] Define connector capability flags and a reusable connector conformance suite, then implement the MySQL connector contract.
- [ ] Implement MySQL introspection, profiling, dialect generation, `EXPLAIN`, validation, and read-only execution.
- [ ] Reuse runtime, normalized metadata, UI, chart, and dashboard contracts.
- [ ] Add MySQL benchmark cases and report breakdown.

**Definition of Done:** MySQL acceptance scenarios pass without PostgreSQL regressions, and evaluation reports MySQL separately.

### Phase 13 — MongoDB Expansion

**Status:** Not started

- [ ] Add `demo-mongodb` Compose profile and reproducible seed data.
- [ ] Run the same connector capability/conformance contract for MongoDB-supported operations.
- [ ] Implement MongoDB collection/schema inference and bounded local profiling.
- [ ] Implement structured `find` and aggregation generation.
- [ ] Validate operations, nested stages, and expressions.
- [ ] Block `$out`, `$merge`, `$function`, `$where`, server-side JavaScript, and all write paths.
- [ ] Implement read-only execution and JSON-safe value serialization.
- [ ] Add MongoDB pipeline viewer and benchmark cases.

**Definition of Done:** MongoDB acceptance scenarios pass, unsafe nested pipelines are blocked, and evaluation reports MongoDB separately.

### Phase 14 — Full Evaluation and Portfolio Readiness

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
| 2026-09-19 | 3 | Frontend lint, strict typing, component/API tests, production build | Docker Compose `npm run lint`, `typecheck`, `test`, and `build` | Pass; 4 tests and all 7 routes built |
| 2026-09-19 | 3 | Responsive rendering and visual review | Browser container screenshots at 375, 768, 1024, and 1440 px | Pass; mobile bottom navigation, desktop sidebar, loading and empty states reviewed |
| 2026-09-19 | 3 | Dependency security | Docker Compose `npm audit --omit=dev` and full `npm audit` after Vitest upgrade | Pass; 0 vulnerabilities |
| 2026-09-19 | 4 | Connector, safety boundaries, onboarding API, and credential persistence | `docker compose run --rm backend uv run pytest`; Ruff; strict Mypy | Pass; 9 tests, including read-only denial, timeout, row cap, schema allowlist, no-persistence test, encrypted credential, introspection, activation, and refresh |
| 2026-09-19 | 4 | Migration/model parity and demo seed | `docker compose run --rm migrate`; `alembic check`; empty-volume project `insightmesh-phase4check`; repeated demo init; foundation smoke | Pass; clean migration to `37c8d3abd7cf`, idempotent seed, read-only demo user; temporary volume removed |
| 2026-09-19 | 4 | Sources UI quality gate | Docker Compose `npm run lint`, `typecheck`, `test`, `build`; full `npm audit` | Pass; 6 tests, 9 routes, 0 vulnerabilities |
| 2026-09-19 | 4 | Browser onboarding and responsive review | `docker compose --profile test run --rm e2e`; screenshots at 375, 768, and 1440 px | Pass; test, save, introspect, activate, active-source shell, relationships, and no horizontal overflow verified |
| 2026-09-19 | 5 | Bounded profiling, PII exclusion, structured enrichment, embeddings, and hash refresh | `docker compose run --rm backend uv run --frozen pytest`; Ruff; strict Mypy | Pass; 14 tests, including bounded profiles, excluded customer PII, strict provider request shapes, fake-provider indexing, pgvector persistence, and unchanged-index reuse |
| 2026-09-19 | 5 | Migration and empty-volume reproducibility | `docker compose run --rm migrate alembic check`; temporary `insightmesh-phase5check` stack migrated and tested | Pass; head `6f2b3a91c4de`, no pending operations, 12 tests on fresh volumes; temporary volumes removed |
| 2026-09-19 | 5 | Safe metadata/profile UI and responsive browser flow | Docker Compose frontend test/lint/build; `docker compose --profile test run --rm e2e`; screenshots at 375 and 1440 px | Pass; profile/PII/provider states visible, progressive disclosure and no horizontal page overflow verified |
| 2026-09-19 | 5 | Live Gemini/OpenRouter semantic refresh | Backend structured-output smoke plus demo datasource refresh via `POST /api/v1/datasources/{id}/refresh` | Pass; 20 profiles, 64 terms, 19 metrics, 6 embeddings, `semantic_status=ready` |
| 2026-09-19 | 6 | Datasource-scoped vector retrieval, relationship expansion, compact context, and persisted context IDs | `docker compose run --rm --no-deps backend uv run --frozen pytest`; Ruff; strict Mypy; `docker compose run --rm migrate alembic check`; live `POST /api/v1/retrieval/preview` | Pass; 15 tests, 39 files type-checked, no pending migration operations; live request returned 4 entities, 3 join edges, and persisted run/context IDs |
| 2026-09-19 | 6 | Live PostgreSQL retrieval benchmark | `docker compose exec backend python -m evals.run_retrieval_benchmark` | Pass; 5 cases, schema selection 100%, entity recall 100%, mean precision 60%, join-path accuracy 100% |
| 2026-09-20 | 7 | Deterministic runtime, static skills, SQLGlot policy, EXPLAIN, read-only execution, verification, bounded repair, and trace APIs | Docker Compose Pytest, Ruff, strict Mypy, Alembic check, and foundation smoke | Pass; 25 tests, 55 files type-checked, validation and execution failures repair deterministically, repair stops at two attempts, no pending migration operations |
| 2026-09-20 | 7 | Live Gemini/PostgreSQL runtime acceptance | Live `POST /api/v1/query-runs` for unsafe, ambiguous, out-of-scope, simple success, plus all five Phase 6 benchmark questions | Pass; unsafe and out-of-scope requests stop before generation/database execution, ambiguity returned three complete questions, simple query and 5/5 benchmark questions completed with AST + EXPLAIN validation and read-only execution |
| 2026-09-20 | 7 | Datasource relevance guard | Backend Pytest, Ruff, strict Mypy, and live `POST /api/v1/query-runs` with weather, model-meta, and valid Vietnamese analytical questions | Pass; model-meta request stops at one precheck trace event with no generated query/result; valid Vietnamese aggregation completes without repair |
| 2026-09-20 | 8 | Ask workspace, typed query-run client, all runtime states, independent clarification, generated SQL, safe trace, and accessible verified results | Docker Compose frontend lint, strict type-check, unit/component tests, and production build | Pass; 15 tests, `/ask` production route built, empty/truncated/warning/null states covered |
| 2026-09-20 | 8 | Browser acceptance and responsive review | `docker compose --profile test run --rm e2e`; screenshots at 375, 768, and 1440 px | Pass; blocked, clarification-as-new-request, success, repaired/truncated, empty, and execution-failure states verified with no horizontal page overflow |
| 2026-09-20 | 9 | Deterministic chart selection, stored-query widget refresh, and stale snapshot preservation | Docker Compose Pytest, Ruff, strict Mypy, Alembic check | Pass; 30 backend tests, revision `b8d2e41c730a`, no pending migration operations |
| 2026-09-20 | 9 | Recharts adapter, six result views, dashboard CRUD interactions, and exact table fallback | Docker Compose frontend lint, strict type-check, Vitest, and production build | Pass; 19 frontend tests and all dashboard routes built |
| 2026-09-20 | 9 | Dashboard browser flow and responsive review | `docker compose --profile test run --rm e2e` | Pass; 3 browser flows, including create/reorder/refresh and 375/1440 px overflow checks |
| 2026-09-21 | 10 | Result-based PostgreSQL evaluation, adversarial guardrails, and vector/hybrid comparison | `docker compose exec backend python -m evals.run_postgres_evaluation --strategy both --datasource-name "Docker demo store"` | Pass; 20 cases, 100% result/status/execution/safety/out-of-scope/ambiguity accuracy, 0% false blocks, 100% entity recall and join-path accuracy; hybrid precision 65.38% vs vector 46.92%; comparison gate passed |
| 2026-09-21 | 10 | Hybrid retrieval regression against the original Phase 6 fixture | `docker compose exec backend python -m evals.run_retrieval_benchmark` | Pass; fixture selects its named Docker demo datasource deterministically; 5/5 schema selections and join paths, 100% entity recall, 76.67% mean precision |
| 2026-09-21 | 10 | Hybrid retrieval, normalized/obfuscated safety precheck, CTE/alias-aware SQL validation, and evaluation regression tests | Docker Compose Pytest plus targeted Ruff and strict Mypy | Pass; 37 tests; changed-file quality checks clean |
| 2026-09-21 | 11 | Cursor-paginated/filterable query history API, safe retained-run details, and independent rerun | Docker Compose backend Pytest plus changed-file Ruff/strict Mypy and Alembic check; frontend ESLint/TypeScript/Vitest/build; full Playwright suite | Pass; 38 backend tests, 23 frontend tests, production `/history` route, 4 browser flows, and responsive 375/1440 px history checks |
| 2026-09-21 | 11 | Immutable versioned semantic-manifest persistence/API, privacy-safe artifact contract, datasource-detail summary, and JSON export | Docker Compose migration/Alembic check, 38 backend tests, changed-file Ruff and strict Mypy; frontend ESLint/TypeScript, 26 Vitest tests, production build; live API probe; Playwright run sequentially | Pass; unchanged refreshes deduplicate by stable content hash, semantic changes create a new immutable version, excluded PII and embedding vectors/content stay out of the manifest; live Docker demo returns v1 with 6 entities/4 relationships and Gemini 2.5 Flash configuration; all 4 browser flows pass including versioned export and responsive source detail |

Current limitations: development images only; MySQL/MongoDB are not implemented. Query-run creation is synchronous, so the Ask workspace shows a truthful neutral waiting state before the terminal backend response rather than inventing intermediate progress. Dashboard authoring uses keyboard-accessible move controls rather than drag-and-drop. The 20-case PostgreSQL report is a focused V1 gate rather than the final 40–60-case cross-datasource suite; no live case required repair, so `repair_success` is reported as null with zero attempts while bounded repair remains covered by deterministic runtime tests. The relationship graph and expanded relationship/trace explainability remain in Phase 11. Base image tags are not digest-pinned. No existing user files were reset or committed.

## 9. Blockers and Decisions Queue

Record only unresolved items that prevent the current or next phase.

| Item | Affects phase | Status | Required decision |
|---|---:|---|---|
| Final design system | 0–3 | Resolved | Approved in Phase 0 and persisted in `design-system/insightmesh/MASTER.md`. |
| LLM/embedding providers | 5 | Resolved for V1 design | Gemini 2.5 Flash via Google AI Studio is primary generation; OpenRouter GPT-4o-mini is timeout/rate-limit fallback; OpenRouter embeddings remain separate. Configuration is versioned and retry/fallback are bounded. |
| Live provider acceptance gate | 5 | Resolved | Gemini structured-output smoke and live datasource refresh passed; timeout/rate-limit fallback remains covered by deterministic provider tests. |
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
