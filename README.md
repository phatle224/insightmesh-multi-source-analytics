# InsightMesh

Natural-language analytics for PostgreSQL and MySQL. Both V1 datasource paths are implemented; MongoDB is intentionally out of scope. The Docker foundation, datasource onboarding, privacy-bounded semantic index/retrieval, dialect-aware deterministic query runtime, responsive Ask workspace, dashboards, evaluation, query history, and semantic manifests use SQLGlot safety, read-only execution, bounded repair, datasource relevance guardrails, result verification, inspectable SQL, and safe traces.

## Local development

Prerequisites: Git and Docker Desktop with Linux containers (or Docker Engine + Compose). Node and Python are installed inside images; no host language runtime is required.

From the repository root:

```powershell
docker compose config --quiet
docker compose up --build -d --wait --wait-timeout 240
docker compose ps
```

The first build downloads images and dependencies. Local defaults work without an `.env` file. To override ports, passwords, or the local credential-encryption key, copy `.env.example` to `.env` and edit it. These defaults are public, local-development values, not production credentials. The documented encryption key is rejected outside development/test. Do not commit real secrets. Database init credentials apply when volumes are first initialized; changing `.env` does not rotate existing database passwords.

- Frontend: http://localhost:3000
- Backend health: http://localhost:8000/api/v1/health
- API docs: http://localhost:8000/docs
- Frontend-to-backend health: http://localhost:3000/api/health

Only frontend and backend bind to localhost. Database services have no host port. Compose's internal `data` network connects backend/migration and databases; `app` connects frontend and backend and permits future outbound provider calls.

| Service | Role |
|---|---|
| `metadata-db` | PostgreSQL 16 + pgvector, named volume |
| `demo-postgres` | Separate PostgreSQL demo database, named volume |
| `demo-mysql` | Optional MySQL 8 demo database under the `mysql` profile, named volume |
| `migrate` | One-shot Alembic upgrade; exits successfully before backend starts |
| `backend` | FastAPI application, datasource/query APIs, deterministic runtime, PostgreSQL/MySQL connectors, and persistence layer |
| `frontend` | Next.js/Tailwind Sources and Ask experiences, typed API client, and responsive product routes |
| `e2e` | One-shot Playwright browser test under the optional `test` profile |

Four long-running services should be healthy. `migrate` with `Exited (0)` is expected. Application processes use non-root users. The local stack still uses one metadata-database owner; separate runtime and migration roles remain required before production deployment.

## Commands

```powershell
# Connectivity, pgvector, migration state, demo read/write isolation
docker compose exec backend python tests/foundation_smoke.py

# Backend quality gate
docker compose run --rm backend uv run pytest
docker compose run --rm backend uv run ruff check .
docker compose run --rm backend uv run mypy .
docker compose run --rm migrate alembic check

# Run query-run retention cleanup manually or from a scheduled job
docker compose exec backend python -m scripts.cleanup_query_runs

# Live PostgreSQL schema-selection and join-path retrieval benchmark
docker compose exec backend python -m evals.run_retrieval_benchmark

# Start and evaluate the optional MySQL demo path
docker compose --profile mysql up -d demo-mysql
docker compose exec backend python -m evals.run_mysql_evaluation --strategy hybrid

# Run the 37-case PostgreSQL + MySQL release evaluation and write combined metrics
docker compose exec backend python -m evals.run_combined_evaluation --strategy hybrid

# Safe to repeat; does not drop data
docker compose run --rm migrate
docker compose exec demo-postgres sh /docker-entrypoint-initdb.d/001-demo.sh

# Frontend quality gate
docker compose run --rm --no-deps frontend npm run lint
docker compose run --rm --no-deps frontend npm run typecheck
docker compose run --rm --no-deps frontend npm run test
docker compose run --rm --no-deps frontend npm run build

# Full browser onboarding and Ask acceptance flows
docker compose --profile test run --rm e2e

docker compose logs --tail 100 backend frontend migrate
docker compose down
```

`docker compose down` preserves database volumes. Do not add `--volumes` unless intentionally deleting local database contents. After dependency/config/migration changes rebuild with `docker compose up --build -d --wait`; bind mounts cover only application source, so dependencies always come from the image lockfiles. Re-run `docker compose run --rm migrate` explicitly when adding migrations to an already-running stack.

Lockfiles are generated in Docker and must be committed. Builds use `uv sync --frozen` and `npm ci`. Base-image tags receive upstream updates; package versions are locked but image digests are not pinned yet.

PostgreSQL demo connection inside Compose: host `demo-postgres`, port `5432`, database `insightmesh_demo`, user `demo_reader`. MySQL uses host `demo-mysql`, port `3306`, and allowed database `insightmesh_demo`. Both use the password from `DEMO_READER_PASSWORD`, contain equivalent synthetic e-commerce data, and grant the reader SELECT only.

## Progress and specifications

- [Implementation tracker](docs/IMPLEMENTATION_PLAN.md)
- [PRD](docs/InsightMesh_PRD.md)
- [Technical design](docs/TECHNICAL_DESIGN.md)
- [Frontend specification](docs/FRONTEND_SPEC.md)
- [Approved visual system](design-system/insightmesh/MASTER.md)

Phase numbers in the tracker are delivery milestones; the PRD groups requirements differently. The product persistence schema covers datasources, encrypted credentials, metadata/profiles, semantic artifacts, embeddings, query runs, saved analyses, dashboards, and widgets. `POST /api/v1/query-runs` selects PostgreSQL or MySQL deterministically and runs through fixed states; `GET /api/v1/query-runs/{run_id}/trace` exposes a safe structured trace without prompts, rows, credentials, or hidden reasoning. Query-run artifacts are retained for 7 days by default and run summaries for 90 days; saved analyses copy validated query definitions and survive that cleanup. The frontend exposes datasource onboarding, semantic-index status, complete independent question runs, saved/recent history, clarification choices, out-of-scope/blocked/failed states, generated SQL, safe traces, verified paginated result tables, and dashboard management.

The combined evaluation expects ready semantic indexes for the named Docker demo
datasources (`Docker demo store` and `Docker demo MySQL store`). It writes separate
reports plus `evals/reports/combined-latest.json`, including per-datasource,
per-difficulty, and overall metrics. Reports are generated artifacts and are ignored
by Git.

Implementation references: [Compose startup dependencies](https://docs.docker.com/compose/how-tos/startup-order/) and [Next.js installation](https://nextjs.org/docs/app/getting-started/installation).

V1 model note: Gemini 2.5 Flash from Google AI Studio is the primary structured-
generation model. OpenRouter `openai/gpt-4o-mini` is the bounded fallback for Gemini
timeouts/rate limits, and OpenRouter `openai/text-embedding-3-large` handles
embeddings. Set both provider keys in the local, uncommitted `.env`; local
introspection and profiling still complete if semantic provider configuration is
missing. Provider calls use strict structured output, one bounded retry, and no
fallback for authentication, safety, or schema failures.
