# InsightMesh

Natural-language analytics for PostgreSQL, MySQL, and MongoDB. **Phases 1–2 are complete:** the Docker foundation, backend contracts, and product persistence schema are implemented. Datasource APIs, semantic retrieval, and the analytics UI are not implemented yet.

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
| `migrate` | One-shot Alembic upgrade; exits successfully before backend starts |
| `backend` | FastAPI application, canonical errors/request IDs, and persistence layer |
| `frontend` | Next.js development server, watches mounted `frontend/app` |

Four long-running services should be healthy. `migrate` with `Exited (0)` is expected. Application processes use non-root users. The local stack still uses one metadata-database owner; separate runtime and migration roles remain required before production deployment.

## Commands

```powershell
# Connectivity, pgvector, migration state, demo read/write isolation
docker compose exec backend python tests/foundation_smoke.py

# Phase 2 backend quality gate
docker compose run --rm backend uv run pytest
docker compose run --rm backend uv run ruff check .
docker compose run --rm backend uv run mypy .
docker compose run --rm migrate alembic check

# Safe to repeat; does not drop data
docker compose run --rm migrate
docker compose exec demo-postgres sh /docker-entrypoint-initdb.d/001-demo.sh

# Current frontend checks (lint and test runners arrive in Phase 3)
docker compose run --rm --no-deps frontend npm run typecheck
docker compose run --rm --no-deps frontend npm run build

docker compose logs --tail 100 backend frontend migrate
docker compose down
```

`docker compose down` preserves database volumes. Do not add `--volumes` unless intentionally deleting local database contents. After dependency/config/migration changes rebuild with `docker compose up --build -d --wait`; bind mounts cover only application source, so dependencies always come from the image lockfiles. Re-run `docker compose run --rm migrate` explicitly when adding migrations to an already-running stack.

Lockfiles are generated in Docker and must be committed. Builds use `uv sync --frozen` and `npm ci`. Base-image tags receive upstream updates; package versions are locked but image digests are not pinned yet.

Demo connection inside Compose: host `demo-postgres`, port `5432`, database `insightmesh_demo`, user `demo_reader`; password comes from `DEMO_READER_PASSWORD`. The initial table `foundation_probe` contains one synthetic row. Full e-commerce seeding is scheduled for Phase 4. The reader has SELECT grants only, and the smoke check also verifies write denial with the session read-only flag disabled.

## Progress and specifications

- [Implementation tracker](docs/IMPLEMENTATION_PLAN.md)
- [PRD](docs/InsightMesh_PRD.md)
- [Technical design](docs/TECHNICAL_DESIGN.md)
- [Frontend specification](docs/FRONTEND_SPEC.md)
- [Approved visual system](design-system/insightmesh/MASTER.md)

Phase numbers in the tracker are delivery milestones; the PRD groups requirements differently. The product persistence schema now covers datasources, encrypted credentials, metadata/profiles, semantic artifacts, embeddings, query runs, dashboards, and widgets. Product APIs begin in Phase 4; the frontend shell is Phase 3.

Implementation references: [Compose startup dependencies](https://docs.docker.com/compose/how-tos/startup-order/) and [Next.js installation](https://nextjs.org/docs/app/getting-started/installation).
