# InsightMesh Technical Design

**Status:** Implementation baseline  
**Scope:** V1 — independent questions, one active datasource, PostgreSQL-first  
**Product requirements:** `docs/InsightMesh_PRD.md`  
**Frontend behavior:** `docs/FRONTEND_SPEC.md`

## 1. Purpose and Decision Authority

This document translates the PRD into implementation constraints, component boundaries, state transitions, and API contracts. It exists to prevent implementation decisions from being inferred differently across sessions.

Authority order:

1. `InsightMesh_PRD.md` defines product scope and acceptance criteria.
2. `TECHNICAL_DESIGN.md` defines backend and cross-system implementation contracts.
3. `FRONTEND_SPEC.md` defines UI behavior and presentation contracts.
4. Tests and code must conform to these documents; they do not silently redefine them.

When a required decision is absent or contradictory, mark it `TBD` and request a decision. Do not invent product behavior.

## 2. Fixed V1 Boundaries

- Build and validate one PostgreSQL vertical slice before MySQL and MongoDB.
- One datasource is active per workspace/session. No cross-datasource joins or federation.
- Every analytical question is an independent request. V1 has no conversation memory.
- The orchestration layer is a custom deterministic state machine. Do not add LangGraph, a standalone LLM planner/router, or a multi-agent system.
- LLM usage is limited to semantic enrichment, semantic interpretation when deterministic retrieval is insufficient, query generation, bounded query repair, and optional result summary/title generation.
- Datasource execution is read-only. Raw rows, credentials, and raw PII are not sent to the LLM by default.
- Dashboard refresh validates and re-executes the saved query without invoking the LLM.

## 3. System Context

```text
Next.js UI
   │ HTTPS / JSON
   ▼
FastAPI API
   │
   ├── Lightweight Harness Runtime
   │      ├── Metadata / Semantic Retrieval
   │      ├── Query Generation / Repair
   │      ├── Deterministic Validators
   │      ├── Read-only Execution
   │      └── Result Verification / Visualization Selection
   │
   ├── Application PostgreSQL + pgvector
   │      └── metadata, semantics, embeddings, runs, dashboards
   │
   └── Connector Abstraction
          ├── PostgreSQL — first vertical slice
          ├── MySQL — after PostgreSQL baseline
          └── MongoDB — after MySQL
```

## 4. Backend Module Boundaries

```text
backend/
├── api/                 HTTP routes, request/response schemas, error mapping
├── harness/             runtime.py, state.py, transitions.py, trace.py
├── skills/              static versioned instruction assets
├── tools/               approved runtime-callable operations
├── connectors/          datasource-specific introspection and execution
├── semantic/            normalization, profiling, enrichment, embeddings, retrieval
├── query/               generation contracts, validators, execution policies
├── visualization/       deterministic chart compatibility and selection
├── persistence/         application database models and repositories
└── config.py            validated environment configuration
```

No module may bypass the connector abstraction to execute an analytical query. API routes must not call an LLM provider or datasource driver directly.

## 5. Core Interfaces

### 5.1 Connector

```python
class DataSourceConnector(Protocol):
    def capabilities(self) -> ConnectorCapabilities: ...
    def test_connection(self) -> ConnectionTestResult: ...
    def introspect(self) -> RawDataSourceMetadata: ...
    def profile(
        self, metadata: RawDataSourceMetadata, policy: ProfilingPolicy
    ) -> ProfileResult: ...
    def explain(self, query: NativeQuery) -> ExplainResult: ...
    def execute_readonly(self, query: NativeQuery, limits: QueryLimits) -> QueryResult: ...
    def close(self) -> None: ...
```

Connector invariants:

- `execute_readonly` accepts only a query that has passed the matching deterministic validator.
- Timeouts and returned-row limits are enforced at execution time, not only requested in prompts.
- Credentials are never included in logs, traces, exceptions returned to clients, or query history.
- PostgreSQL and MySQL use read-only accounts and transactions where supported.
- MongoDB credentials must permit read operations only.

`ConnectorCapabilities` explicitly reports support for native explain/dry validation,
relationship introspection, aggregation pipelines, transactions, and schema/database
namespaces. Shared conformance tests enforce the universal invariants and each
advertised capability so runtime code does not scatter datasource-type conditionals.

### 5.2 LLM Provider

```python
class LLMProvider(Protocol):
    def generate_structured(self, request: StructuredGenerationRequest) -> dict: ...
    def embed(self, inputs: list[str]) -> list[list[float]]: ...
```

The runtime depends on this abstraction, not a provider SDK. Every structured-generation call must validate its output against a declared schema before use.

#### V1 provider and model decision (budget-conscious portfolio build)

The initial implementation uses direct Google AI Studio Gemini for generation and
OpenRouter for fallback generation plus embeddings. Direct OpenAI is not used as a
primary provider.

Active configuration:

| Capability | Provider | Model | Status |
|---|---|---|---|
| SQL generation, repair, and semantic enrichment | Google AI Studio Gemini API | `gemini-2.5-flash` | primary |
| Embeddings | OpenRouter | `openai/text-embedding-3-large` | live-verified |
| Generation fallback | OpenRouter | `openai/gpt-4o-mini` | timeout/rate-limit only |

The following models are retained as evaluation/history records, but are disabled by
default until a connectivity and structured-output check succeeds:

| Model | Route | Status |
|---|---|---|
| `gemini-1.5-flash` | direct Gemini | failed during model/provider testing |
| `gemini-2.0-flash` | direct Gemini | failed during model/provider testing |
| `gemini-1.5-pro` | direct Gemini | failed during model/provider testing |
| `gpt-4o-mini` | direct OpenAI | unavailable because no OpenAI key is configured |

The OpenRouter model identifier must include its provider prefix. Gemini uses the
direct `generativelanguage.googleapis.com` endpoint with `GEMINI_API_KEY`.

#### Rollback and fallback policy

Model changes are configuration changes, not code changes. Each deployment records an
active model configuration and the immediately previous known-good configuration.

1. A candidate must pass connectivity, structured-schema, embedding-dimension, and
   PostgreSQL benchmark smoke checks before activation.
2. Gemini timeout and rate-limit failures may retry once, then use the configured
   OpenRouter fallback for generation if it is explicitly enabled.
3. A schema-validation, safety, or benchmark-regression failure does not trigger an
   uncontrolled model cascade; the active configuration is rolled back to the
   previous known-good version.
4. Rollback restores the complete provider/model pair, not only the model name. This
   prevents incompatible embedding dimensions or provider-specific response formats.
5. Logs record the failed candidate, error category, configuration version, and
   rollback event without API keys, prompts, raw rows, or hidden reasoning.

For the first low-cost release, Gemini is the primary generation model and
`openai/gpt-4o-mini` is the only enabled generation fallback. Embeddings remain an
independent OpenRouter capability; if they are unavailable, the semantic index must
fail safely without sending raw rows or credentials elsewhere.

### 5.3 Skill Asset

```text
Skill = versioned instructions + input schema + output schema + constraints
Skill ≠ agent ≠ service ≠ autonomous runtime
```

V1 core assets:

- `query-generation`
- `query-repair`
- `result-analysis` — optional

Skills are loaded from known application paths or a static registry. V1 has no plugin marketplace, autonomous discovery, or LLM-based skill routing. Schema understanding is primarily metadata retrieval plus relationship graph expansion.

## 6. Canonical Data Contracts

### 6.1 Identifiers and Serialization

- Public identifiers are opaque strings; UUIDs are recommended internally.
- Timestamps cross API boundaries as ISO 8601 UTC strings.
- Decimal database values serialize as strings plus column type metadata to avoid precision loss.
- Null remains JSON `null`; it is never converted to an empty string or zero.
- MongoDB-specific values such as `ObjectId` and dates must be converted to typed, JSON-safe values by the connector.

### 6.2 Normalized Metadata

```json
{
  "datasource_id": "ds_123",
  "entity_type": "table",
  "name": "orders",
  "description": "Customer purchase orders",
  "fields": [
    {"name": "order_id", "type": "integer", "nullable": false}
  ],
  "primary_key": ["order_id"],
  "relationships": [],
  "profile_statistics": {},
  "semantic_tags": []
}
```

The normalized model represents SQL tables/views and MongoDB collections without erasing datasource-specific details needed for query generation.

### 6.3 Local Profiling

Allowed derived statistics:

- null ratio;
- distinct count;
- numeric/temporal minimum and maximum;
- MongoDB field presence rate;
- observed data-type distribution;
- low-cardinality enum candidates.

Profiling policy must include a sample/scan bound, timeout, allowed schemas/databases, and PII exclusions. Raw samples remain local and are not persisted in V1. Only derived, privacy-reviewed metadata may enter LLM context.

### 6.4 Query Result

```json
{
  "columns": [
    {"name": "category", "type": "string", "semantic_type": "dimension"},
    {"name": "revenue", "type": "decimal", "semantic_type": "metric"}
  ],
  "rows": [["Electronics", "125000.50"]],
  "row_count": 1,
  "truncated": false,
  "duration_ms": 42,
  "warnings": []
}
```

The LLM does not receive `rows` by default. Optional result summaries may use deterministic aggregates or a future explicitly approved privacy policy.

## 7. Lightweight Harness Runtime

### 7.1 Runtime State

Required fields:

```text
run_id
question
datasource_id
datasource_type
status
retrieved_context
selected_entities
selected_metrics
query
validation
execution
verification
visualization
repair_count
trace
error
```

`repair_count` starts at `0`; the maximum is `2`.

The V1 implementation stores static `query-generation` and `query-repair` instruction
assets under `backend/skills/`; code selects them by datasource type and runtime state.
The runtime also performs a deterministic write-intent precheck before retrieval so an
explicit destructive request terminates as `blocked` without a provider or datasource
call. This safety precheck supplements, and never replaces, SQL AST validation.

### 7.2 States and Transitions

| Current state | Condition | Next state |
|---|---|---|
| `received` | explicit write/destructive intent | `blocked` |
| `received` | active datasource exists | `retrieve_context` |
| `received` | no active datasource | `failed` |
| `retrieve_context` | context sufficient | `generate_query` |
| `retrieve_context` | ambiguous/low confidence | `clarification_required` |
| `retrieve_context` | no relevant datasource context | `out_of_scope` |
| `generate_query` | structured output valid | `validate_query` |
| `generate_query` | provider/schema failure | `failed` |
| `validate_query` | unsafe | `blocked` |
| `validate_query` | valid | `execute_query` |
| `validate_query` | repairable and retries remain | `repair_query` |
| `validate_query` | invalid and retries exhausted | `failed` |
| `execute_query` | success | `verify_result` |
| `execute_query` | repairable DB error and retries remain | `repair_query` |
| `execute_query` | non-repairable or exhausted | `failed` |
| `repair_query` | structured repair returned | `validate_query` |
| `verify_result` | deterministic checks complete | `select_visualization` |
| `verify_result` | serialization or enforced-bound check fails | `failed` |
| `select_visualization` | config produced | `completed` |

Terminal states are `completed`, `clarification_required`, `out_of_scope`, `blocked`, and `failed`. State selection is code-driven; the LLM never chooses the next state.

### 7.3 Clarification Contract

A clarification response terminates the current run and returns complete suggested questions. Selecting a suggestion creates a new request and new `run_id`. V1 must not accept a fragment such as `revenue` as implicit continuation context.

### 7.4 Out-of-Scope Contract

The runtime applies two deterministic scope layers. Before retrieval, an explicit
meta/system precheck rejects questions about the application's model, prompt, or system
configuration. After datasource-scoped retrieval, the relevance/domain gate requires
either a lexical anchor from retrieved entities, fields, business terms, or metrics, or
both an analytical-intent cue and the configured minimum semantic similarity. Semantic
similarity alone is not sufficient. If either layer rejects the question, the run
terminates as `out_of_scope` with error code `question_out_of_scope`; query generation,
validation, repair, and execution are not called. This state is distinct from
`clarification_required`: the latter means the question is about the datasource but is
missing a metric, filter, grouping, or time range.

### 7.5 Deterministic Result Verification

`verify_result` checks:

- execution succeeded;
- expected columns/fields exist;
- result shape is compatible with the requested aggregation;
- row count is within the configured limit;
- values are serializable;
- empty-result state is explicit;
- truncation and null warnings are recorded.

It does not prove semantic correctness and is not an agent. Result accuracy is measured by the evaluation suite.

## 8. Query Safety

### 8.1 SQL

- Parse with SQLGlot or equivalent AST parser.
- Allow one `SELECT` or `WITH ... SELECT` statement only.
- Reject write/DDL/control statements, multiple statements, unknown schemas/tables/columns, and disallowed functions.
- Validate with `EXPLAIN` or datasource-native dry validation before execution where supported.
- Enforce allowed schemas, timeout, and maximum returned rows independently of generated SQL.
- Reject side-effecting SELECT constructs/functions such as `SELECT INTO`, sequence
  mutation, server/file access, advisory locks, and server-side delay functions.

### 8.2 MongoDB

Allowed operations: `find`, `aggregate`, `count`, `distinct`.

Allowed analytical stages include `$match`, `$group`, `$project`, `$sort`, `$limit`, `$skip`, `$lookup`, `$unwind`, and `$count`.

Always reject `$out`, `$merge`, `$function`, `$where`, server-side JavaScript, write operations, and any unrecognized stage or expression not explicitly allowed by policy. Validation walks nested pipelines and expressions, including pipelines inside `$lookup`.

## 9. Semantic Indexing and Retrieval

Onboarding pipeline:

```text
test connection
→ introspect
→ normalize
→ bounded local profiling
→ relationship discovery
→ semantic enrichment
→ embedding generation
→ pgvector storage
→ immutable semantic-manifest snapshot
→ ready
```

If `OPENROUTER_API_KEY` is absent, introspection and local profiling still finish and
the datasource remains usable with `semantic_status=configuration_required`. If a
previous index exists, a missing or failed provider refresh retains it as `stale`.
No local heuristic silently substitutes for the configured remote provider.

Question-time retrieval:

```text
exact identifier matching + lexical/business-term matching + question embedding
→ deterministic lexical/vector score fusion
→ datasource-scoped Top-K selection
→ relationship graph expansion
→ compact context builder
→ query generation
```

Exact and lexical candidates come only from persisted datasource metadata, semantic
terms, metric names, and privacy-safe profile summaries; V1 must not ship
demo-schema synonym dictionaries. Phase 10 records the vector-only baseline before
enabling fusion. Hybrid retrieval is retained only when it improves measured precision
without reducing result accuracy or safety. Vector similarity alone must not determine
join paths. Every candidate records lexical, semantic, and fused scores plus its
selection source; retrieved objects and graph-expanded relationships are recorded in
query history.

Semantic manifests are immutable snapshots keyed by datasource, metadata hash,
profile hash, enrichment/embedding configuration, and skill versions. They contain
normalized entities, fields, relationship provenance, derived profiles, semantic
terms, metrics, and artifact IDs, but never credentials, raw rows, or raw PII.

A retrieval-context cache is optional and may be introduced only after the evaluation
runner demonstrates a material latency or provider-cost benefit. Its key is
`datasource_id + normalized_question_fingerprint + metadata_hash + profile_hash +
retrieval_config_version`; hash or configuration changes make old entries unreachable.
Do not use one global active-schema cache or TTL as the sole invalidation mechanism.

## 10. Persistence

Minimum application tables:

```text
datasources
datasource_credentials
entities
fields
relationships
profile_statistics
semantic_terms
metric_candidates
query_examples
embeddings
semantic_manifests
query_runs
dashboards
dashboard_widgets
```

Datasource credentials are encrypted as a canonical JSON payload with Fernet and stored only in the separate `datasource_credentials` table. The local Docker environment receives its key from `CREDENTIAL_ENCRYPTION_KEY`; the documented local key is rejected when `APP_ENV` is not `development` or `test`. Plaintext persistence is forbidden. Production secret-manager integration and key rotation remain deployment decisions.

## 11. HTTP API Contract

All routes use `/api/v1`. Exact framework model names may differ, but behavior and response fields are stable.

### 11.1 Datasources

```text
GET    /datasources
POST   /datasources/test
POST   /datasources
GET    /datasources/{datasource_id}
GET    /datasources/{datasource_id}/semantic-manifest
POST   /datasources/{datasource_id}/activate
POST   /datasources/{datasource_id}/refresh
GET    /datasources/{datasource_id}/onboarding-status
```

Datasource summary/detail responses include profile, PII-exclusion, semantic-term,
metric, and embedding counts plus `semantic_status` and a safe
`semantic_error_code`. Field detail exposes only derived profile statistics and an
exclusion flag; raw sampled rows and credentials are never returned.

The semantic-manifest endpoint returns the latest immutable, versioned manifest and
its metadata/profile/configuration hashes. Relationship entries distinguish
`declared` from `inferred`; inferred entries include confidence and privacy-safe
evidence. Low-confidence inferred edges are visible for inspection but excluded from
query-generation context.

Implementation contract:

- `semantic_manifests` stores immutable JSONB snapshots keyed by datasource/version
  and a deterministic content hash;
- a successful metadata refresh creates a snapshot, while the first read lazily
  backfills one for compatible datasources created before this table existed;
- equivalent refreshes reuse the existing version because trace-only artifact UUIDs
  do not participate in the semantic content hash;
- snapshots contain normalized entities/fields, privacy-filtered derived profiles,
  semantic terms, metric candidates, relationship provenance, artifact IDs, and
  provider/model/retrieval/skill/privacy-policy versions;
- embedding vectors/content, credentials, raw rows, profiling samples, and raw PII
  are excluded from both storage and the response;
- the default inferred-relationship generation threshold is `0.8` and is recorded in
  every snapshot rather than treated as an unversioned constant.

- Passwords/URIs are write-only and never returned.
- Test connection does not persist credentials.
- Create starts onboarding and returns a datasource plus status.
- Only `ready` datasources can be activated.

### 11.2 Semantic Retrieval

```text
POST /retrieval/preview
```

The request contains `datasource_id`, a complete independent `question`, and an
optional bounded `top_k`. The runtime performs datasource-derived exact/lexical
matching and pgvector search over entity embeddings, deterministically fuses the
scores, and then adds bridge entities and relationships from the relationship graph.
The response is compact query-generation context: selected entities, bounded fields,
derived profiles, semantic terms, metric candidates, join edges, and stable context
IDs. Each selected candidate includes `selection_source`, `lexical_score`,
`semantic_score`, and `fused_score`; these values are ranking evidence, not hidden
reasoning. The response never contains credentials or raw sampled rows. Every retrieval creates a
`query_runs` record with status `retrieve_context` so later evaluation and runtime
steps can reproduce which artifacts were used.

### 11.3 Query Runs

```text
POST /query-runs
GET  /query-runs?datasource_id=&status=&created_before=&search=&limit=&cursor=
GET  /query-runs/{run_id}
GET  /query-runs/{run_id}/trace
```

`POST /query-runs` input:

```json
{"datasource_id": "ds_123", "question": "Top categories by revenue last month"}
```

The response contains `run_id`, terminal/current status, generated query when available, validation summary, verified result, visualization config, clarification suggestions, warnings, and a safe user-facing error. The transport may begin synchronously and move to background execution if measured latency requires it; the response shape must remain stable.

The collection endpoint returns reverse-chronological, cursor-paginated summaries and
supports optional datasource, status, creation-time, and question-text filters. Selecting `rerun`
client-side submits the stored complete question to `POST /query-runs` and always
creates a new `run_id`; history never supplies conversational context.

### 11.4 Dashboards

```text
GET    /dashboards
POST   /dashboards
GET    /dashboards/{dashboard_id}
POST   /dashboards/{dashboard_id}/widgets
PATCH  /dashboard-widgets/{widget_id}
DELETE /dashboard-widgets/{widget_id}
POST   /dashboard-widgets/{widget_id}/refresh
```

Widget refresh rebuilds validator context from persisted datasource metadata, revalidates the stored query, runs `EXPLAIN`, and executes through the read-only connector. It must not perform retrieval, regenerate the query, or call the LLM. A failed refresh marks an existing snapshot `stale` and preserves its last successful result; a widget without a successful snapshot becomes `failed`.

### 11.5 Visualization Adapter

V1 uses Recharts only behind the local frontend visualization adapter. The backend and frontend implement the same deterministic compatibility rules over verified column types and row count: Table accepts any result; KPI requires one row and a numeric metric; Bar requires a categorical dimension and numeric metric with at most 50 rows; Line/Area require a temporal dimension, numeric metric, and at least two rows; Pie/Donut additionally limits categorical results to two through five rows. The backend recommends `KPI`, then `Line`, then `Bar`, then `Table`. No model participates in compatibility or selection.

### 11.6 Error Envelope

```json
{
  "error": {
    "code": "QUERY_VALIDATION_FAILED",
    "message": "The generated query could not be executed safely.",
    "retryable": false,
    "details": {}
  },
  "request_id": "req_123"
}
```

`details` contains no credentials, raw SQL driver secrets, hidden reasoning, or raw PII.

## 12. Observability

Each query run records a structured trace of state transitions, tool names, timestamps,
per-state durations, provider/model identity, fallback usage, provider-call count,
retrieval counts and ranking scores, retry count, validation category, row count,
execution duration, and safe error category. It must not store hidden chain-of-thought,
prompts, secrets, raw PII, or raw sampled rows.

Required query-run fields:

```text
run_id, datasource_id, question, retrieved_context_ids,
semantic_manifest_id, retrieval_config_version,
generated_query, query_type, validation_result, status,
row_count, duration_ms, repair_count, visualization_type, result_json,
provider_call_count, trace_json, warnings, error_code, error_message, created_at
```

## 13. Configuration

Environment-backed settings must include:

```text
application database host, port, database, username, and secret password
credential encryption key/reference
LLM provider and model identifiers
embedding provider and model identifier
allowed datasource schemas/databases
query timeout
maximum returned rows
maximum repair count = 2
profiling sample/scan bound
profiling timeout
retrieval Top-K
retrieval maximum entities, fields per entity, and relationship hops
retrieval lexical/vector fusion configuration and version
hybrid relative-score threshold (Top-K remains a maximum, not a forced count)
minimum confidence for inferred relationships used by query generation
```

Do not commit secrets. `.env.example` contains placeholders only.

## 14. Testing and Evaluation

Required automated test layers:

- unit tests for state transitions, SQL validator, MongoDB nested-stage validator, result verification, chart selection, and serialization;
- connector contract tests using reproducible demo databases;
- integration tests for datasource onboarding and the complete PostgreSQL question flow;
- security tests for multi-statement SQL, SQL writes, `$out`, `$merge`, `$function`, `$where`, nested unsafe MongoDB stages, timeout, and row limits;
- privacy tests confirming prompts and traces contain no credentials or raw sampled rows;
- dashboard tests confirming refresh performs no LLM call;
- adversarial guardrail tests covering prompt injection, SQL fragments, Unicode/whitespace obfuscation, model-meta requests, out-of-scope requests, and valid business wording that resembles write intent;
- evaluation runner reporting PostgreSQL, MySQL, MongoDB, and overall metrics by Easy, Medium, Hard, Ambiguous, Out-of-scope, and Unsafe groups;
- retrieval comparison tests that freeze the vector-only baseline before hybrid fusion is enabled.

Primary evaluation metric is result accuracy, not query-string equality. Reports also
include execution rate, entity recall/precision, join-path accuracy, repair success,
ambiguity/out-of-scope/safety rates, false-block rate, provider-call count, p50/p95
latency, datasource seed version, model/provider configuration, skill versions,
metadata/profile hashes, and retrieval configuration.

## 15. Implementation Sequence

1. Foundation: FastAPI, Next.js, application PostgreSQL, pgvector, configuration.
2. PostgreSQL connector and read-only execution contract.
3. Metadata normalization, profiling, semantic enrichment, and embeddings.
4. Datasource-scoped retrieval and relationship expansion.
5. Lightweight Harness Runtime and structured trace.
6. PostgreSQL query generation, validation, execution, result verification.
7. Table plus baseline bar/line visualization.
8. PostgreSQL evaluation baseline, adversarial guardrails, and measured hybrid retrieval.
9. Query history, semantic-manifest inspection, relationship graph, and measured cache optimization.
10. Connector capability contract plus MySQL connector and dialect path.
11. MongoDB connector, schema model, query generation, and nested pipeline safety.
12. Full evaluation and remaining release hardening.

## 16. Explicit TBDs

The following decisions are intentionally not made by the PRD and must not be guessed during implementation:

- LLM and embedding providers/models;
- production secret-manager integration and credential-key rotation policy;
- authentication and multi-user workspace model;
- deployment target and production secret manager;
- exact general semantic-enrichment confidence threshold (the inferred-relationship
  generation threshold is implemented and versioned separately);
- exact profiling sample size, Top-K, timeout, and row-limit defaults;
- final visual design system, pending the user-provided UI skill/reference.
