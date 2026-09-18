# PRD — InsightMesh: AI-Powered Multi-Source Analytics Platform

**Document Type:** Product Requirements Document  
**Project Name:** InsightMesh  
**Subtitle:** AI-Powered Multi-Source Analytics Platform  
**Project Type:** Portfolio / Production-style Engineering Project  
**Target Role:** Data Engineer Intern / Junior Data Engineer  
**Primary Users:** Data Analysts and Business Users  
**Status:** Draft v1.0  
**Product Scope:** V1 — Independent Questions, Runtime-Driven Analytics  
**Planned V2:** Multi-turn Conversational Analytics

---

## 1. Executive Summary

InsightMesh is an AI-powered self-service analytics application that allows Data Analysts and non-technical business users to connect an existing database, ask analytical questions in natural language, receive a generated database query, execute it safely, and visualize the result as a table or dashboard widget.

V1 supports three datasource types:

- PostgreSQL
- MySQL
- MongoDB

Users first connect and activate a datasource. Every question in that session is interpreted against that active datasource only. PostgreSQL and MySQL requests generate dialect-aware SQL, while MongoDB requests generate MongoDB queries or aggregation pipelines.

The central architectural concept is a **Lightweight Harness Runtime** rather than a fixed multi-agent pipeline. This custom, deterministic state machine maintains execution state and orchestrates semantic retrieval, query generation, validation, execution, bounded repair, and final response preparation.

InsightMesh also includes an automatically generated semantic knowledge layer. Instead of requiring an administrator to manually configure business metrics or glossary definitions, the system introspects the connected datasource and uses AI-assisted metadata enrichment to infer table/collection meanings, relationships, business concepts, and candidate metrics. These semantic artifacts are embedded and stored in pgvector for retrieval during question answering.

The project intentionally stops short of building a full enterprise BI platform. Its purpose is to demonstrate engineering depth in metadata discovery, multi-datasource abstraction, semantic retrieval, RAG, lightweight runtime design, Text-to-SQL/NL-to-Query, deterministic guardrails, visualization, dashboard persistence, and formal evaluation.

---

## 2. Product Vision

> **InsightMesh enables users to explore connected business databases using natural language without requiring them to know SQL, MongoDB query syntax, or the physical database schema.**

Core experience:

```text
Connect Data Source
    ↓
Activate Data Source
    ↓
Ask a Question
    ↓
Retrieve Relevant Semantic Context
    ↓
Generate Database-Native Query
    ↓
Validate + Execute Safely
    ↓
Return Table + Visualization
    ↓
Save Useful Result to Dashboard
```

The user should not need to manually configure relationships, metrics, synonyms, or business definitions before first use.

---

## 3. Problem Statement

Business users frequently depend on Data Analysts for questions that could technically be answered directly from existing databases, such as:

- “What was total revenue last month?”
- “Which category grew the most compared with last quarter?”
- “How many active customers do we have?”
- “Which cities generated the highest order value?”
- “Show the top 10 products by sales.”

The problem is broader than SQL generation. A practical natural-language analytics system must solve:

1. **Schema understanding** — identify relevant tables, fields, collections, and relationships.
2. **Business terminology** — map user language to database concepts.
3. **Datasource dialect differences** — PostgreSQL, MySQL, and MongoDB require different query strategies.
4. **Large schemas** — avoid dumping the entire schema into every prompt.
5. **Unsafe generated queries** — never trust AI output blindly.
6. **Ambiguity** — detect underspecified questions instead of guessing.
7. **Result usability** — return meaningful tables and charts, not SQL alone.
8. **Evaluation** — measure semantic correctness, not only syntax validity.

Example business-language mapping:

```text
"revenue"
   ↓
orders.total_amount
   +
possible status filter
```

The system must distinguish inference from known metadata and should request clarification when confidence is too low.

---

## 4. Product Goals

### 4.1 Primary Goals

InsightMesh V1 must:

1. Connect to PostgreSQL, MySQL, and MongoDB.
2. Allow one datasource to be selected as active for a session/workspace.
3. Automatically inspect datasource metadata after connection.
4. Build a normalized semantic representation from datasource metadata.
5. Embed semantic metadata into pgvector.
6. Retrieve only relevant schema and semantic context for each question.
7. Use a Lightweight Harness Runtime with deterministic state transitions to orchestrate retrieval, query generation, validation, execution, and bounded repair.
8. Generate PostgreSQL SQL, MySQL SQL, or MongoDB queries depending on the active datasource.
9. Apply deterministic query validation before execution.
10. Execute through read-only connections.
11. Return structured results.
12. Recommend an appropriate visualization.
13. Support six visualization types: Table, KPI Card, Bar, Line, Pie/Donut, Area.
14. Allow successful results to be saved as dashboard widgets.
15. Evaluate query accuracy with a reproducible benchmark.
16. Prevent raw datasource rows from being sent to the LLM by default.

### 4.2 Secondary Goals

The project should also demonstrate:

- clean connector abstractions;
- reusable procedural skills;
- structured tool calling;
- query repair;
- runtime execution tracing;
- containerized local deployment;
- reproducible demo databases;
- extensibility for future connectors.

---

## 5. Non-Goals

V1 will not attempt to build a full enterprise BI platform. The following are out of scope:

- multi-turn conversational analytics;
- follow-up questions using previous question context;
- manual admin semantic configuration;
- advanced drag-and-drop BI editing;
- scheduled reports;
- alerting;
- streaming analytics;
- ETL/ELT orchestration;
- fine-tuned LLMs;
- multi-agent swarms;
- autonomous database writes;
- enterprise RBAC;
- cross-datasource joins;
- data federation across multiple active databases;
- machine-learning forecasting or recommendation systems.

---

## 6. Target Users

### 6.1 Data Analyst

A Data Analyst wants to quickly understand an unfamiliar datasource, inspect generated queries, validate analytical logic, create lightweight visualizations, and reuse results.

Example:

> “Show monthly revenue and order count for 2026.”

### 6.2 Business User

A business user may not know SQL and wants to ask normal business questions, receive a direct answer, see a chart, and save useful results.

Example:

> “Which product category made the most money last quarter?”

---

## 7. Core Product Principles

### 7.1 Datasource First

The user must select the datasource before asking questions.

```text
User
  ↓
Connect Data Source
  ↓
Activate Data Source
  ↓
Ask Questions Against That Source
```

InsightMesh does not attempt to infer which datasource a question should use.

### 7.2 Metadata-First AI

The LLM may receive:

- table/collection names;
- field names and data types;
- primary/foreign keys;
- relationships;
- inferred descriptions;
- inferred business terms;
- candidate metrics;
- validated query examples.

The LLM must not receive full raw tables, credentials, or raw PII by default.

### 7.3 Lightweight Harness Runtime

The core AI workflow uses a custom deterministic state machine rather than a fixed multi-agent pipeline, an orchestration framework such as LangGraph, or a standalone LLM planner/router. Code determines the next workflow transition; LLM calls are limited to semantic interpretation, database-native query generation, and bounded query repair.

The runtime behaves as:

```text
Question
  ↓
Runtime inspects state
  ↓
Apply deterministic transition
  ↓
Invoke approved tool or LLM operation
  ↓
Observe result
  ↓
Update state
  ↓
Continue / repair / clarify / finish
```

### 7.4 Deterministic Safety Where Possible

Use deterministic mechanisms for:

- AST validation;
- read-only credentials;
- query timeout;
- row limits;
- allowed schemas/databases;
- basic chart selection.

---

## 8. User Journey

### 8.1 Connect Data Source

The user opens **Data Sources → Add Connection** and chooses PostgreSQL, MySQL, or MongoDB.

PostgreSQL/MySQL fields:

```text
Connection Name
Host
Port
Database
Username
Password
SSL
```

MongoDB fields:

```text
Connection Name
Connection URI
Database
```

Actions:

```text
Test Connection
Save Connection
Activate
```

### 8.2 Automatic Datasource Discovery

After successful connection:

```text
Datasource
  ↓
Schema Introspection
  ↓
Metadata Normalization
  ↓
Relationship Discovery
  ↓
Semantic Enrichment
  ↓
Embedding Generation
  ↓
pgvector
```

No admin semantic setup is required in V1.

### 8.3 Ask Question

Example:

> “What were the top 5 product categories by revenue last month?”

System flow:

```text
Question
  ↓
Lightweight Harness Runtime
  ↓
Retrieve semantic context
  ↓
Generate query
  ↓
Validate
  ↓
Execute
  ↓
Verify
  ↓
Return answer
```

### 8.4 View Generated Query

For PostgreSQL/MySQL, show SQL. For MongoDB, show a structured aggregation/query representation. Data Analysts should always be able to inspect the generated query.

### 8.5 Visualization

Show:

```text
Result Table
+
Recommended Visualization
```

Users may switch to another compatible visualization type.

### 8.6 Save Dashboard Widget

Saved widget metadata:

```text
title
question
datasource_id
query
query_type
chart_type
chart_config
created_at
```

Dashboard refresh must re-run the saved validated query without invoking the LLM.

---
## 9. High-Level Architecture

```text
                           ┌─────────────────────┐
                           │       User          │
                           └──────────┬──────────┘
                                      │
                                      ▼
                           ┌─────────────────────┐
                           │      Next.js UI     │
                           │ Sources / Ask / BI  │
                           └──────────┬──────────┘
                                      │
                                      ▼
                           ┌─────────────────────┐
                           │       FastAPI       │
                           └──────────┬──────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────┐
                    │   LIGHTWEIGHT HARNESS RUNTIME   │
                    │ Deterministic State Transitions │
                    │ Tool Orchestration / Trace      │
                    │ Bounded Repair                  │
                    └──────────────┬──────────────────┘
                                   │
            ┌──────────────────────┼──────────────────────┐
            │                      │                      │
            ▼                      ▼                      ▼
       ┌─────────┐            ┌─────────┐           ┌──────────────┐
       │ Skills  │            │  Tools  │           │ Semantic RAG │
       └────┬────┘            └────┬────┘           └──────┬───────┘
            │                      │                        │
            │                metadata/query                ▼
            │                validation/execution      PostgreSQL
            │                                       + pgvector
            └──────────────────────┬────────────────────────┘
                                   │
                                   ▼
                          Connector Abstraction
                     ┌─────────────┼─────────────┐
                     ▼             ▼             ▼
                PostgreSQL       MySQL        MongoDB
                     │             │             │
                     └─────────────┼─────────────┘
                                   ▼
                              Query Result
                                   │
                          ┌────────┴─────────┐
                          ▼                  ▼
                        Table          Visualization
                                             │
                                             ▼
                                         Dashboard
```

---

## 10. Lightweight Harness Runtime

The Lightweight Harness Runtime is the deterministic orchestration layer of InsightMesh. It maintains request state, invokes approved tools and bounded LLM operations, records structured observations, and transitions through a predefined workflow. It does not use a standalone LLM planner or autonomous router.

### 10.1 Runtime State

Example:

```json
{
  "question": "Top 5 categories by revenue last month",
  "datasource_id": "ds_123",
  "datasource_type": "postgresql",
  "intent": "analytical_query",
  "retrieved_context": [],
  "selected_entities": [],
  "selected_metrics": [],
  "query": null,
  "validation": null,
  "execution": null,
  "visualization": null,
  "repair_count": 0,
  "status": "received"
}
```

### 10.2 Deterministic State Transitions

```text
received
  ↓
retrieve_context
  ↓
context sufficient? ── no ──→ clarification_required (terminal)
  │ yes
  ▼
generate_query
  ↓
validate_query
  ├── unsafe or invalid and not repairable ──→ blocked (terminal)
  ├── invalid and repair_count < 2 ──→ repair_query ──→ validate_query
  └── valid ──→ execute_query
                    ├── execution failure and repair_count < 2 ──→ repair_query
                    ├── execution failure after retry limit ──→ failed (terminal)
                    └── execution success ──→ verify_result
                                                 ↓
                                          select_visualization
                                                 ↓
                                          completed (terminal)
```

The runtime selects the applicable procedure by current state and datasource type. Skills provide reusable procedural guidance and prompt assets; they do not autonomously choose the next state or tool.

### 10.3 V1 Runtime Behavior

Simple question:

```text
retrieve schema
→ generate query
→ validate
→ execute
→ answer
```

Validation failure:

```text
generate
→ validate
→ fail
→ repair
→ validate
→ execute
```

Execution failure:

```text
generate
→ validate
→ execute
→ DB error
→ inspect error
→ repair
→ execute again
```

Ambiguous question:

```text
retrieve context
→ insufficient semantic confidence
→ request clarification
```

The clarification response must ask the user to rewrite or select a complete question. If the user chooses a metric such as `revenue`, the UI should construct a new complete question (for example, `Top customers by revenue`) and submit it as a new independent request. V1 does not retain clarification turns as conversational query context.

Safety blocks, clarification-required responses, and retry exhaustion are terminal states. V1 questions are independent; earlier questions are not used as conversational context.

---

## 11. Skills

Skills are reusable procedural playbooks and prompt assets consumed by the runtime. They are **not independent agents** and do not perform autonomous routing.

Skill contract:

```text
Skill
≠ agent
≠ service
≠ autonomous runtime

Skill
= versioned instructions
  + input/output schema
  + datasource and safety constraints
```

Skills are loaded as static, versioned project assets. V1 does not require a dynamic skill marketplace, plugin loader, or autonomous skill discovery mechanism. The core V1 assets are `query-generation` and `query-repair`; `result-analysis` is optional and may provide summaries or titles. Schema understanding is primarily handled by metadata retrieval and relationship graph expansion rather than a separate LLM skill.

Suggested V1 structure:

```text
skills/
├── query-generation/
│   └── SKILL.md
├── query-repair/
│   └── SKILL.md
└── result-analysis/
    └── SKILL.md
```

### 11.1 Schema Understanding Procedure

Schema understanding is primarily a deterministic retrieval procedure, not a required standalone LLM skill. The runtime retrieves relevant metadata and expands connected relationship paths before query generation.

Responsibilities:

- identify relevant entities;
- identify likely relationships;
- interpret inferred descriptions;
- identify candidate metrics;
- detect missing context;
- avoid inventing unsupported relationships.

Expected output:

```json
{
  "entities": ["orders", "products"],
  "metrics": ["revenue"],
  "relationships": ["orders.product_id -> products.id"],
  "confidence": 0.91,
  "needs_clarification": false
}
```

### 11.2 Query Generation Skill

Responsibilities:

- use only retrieved schema/context;
- use the correct datasource dialect;
- generate read-only queries;
- preserve business meaning;
- apply reasonable row limits;
- avoid unsupported tables/fields.

For MongoDB, prefer aggregation pipelines for analytical questions and use only known collections/fields.

### 11.3 Query Repair Skill

Inputs:

```text
question
generated query
database error
semantic context
datasource type
```

Responsibilities:

- identify the likely cause of failure;
- produce a corrected query;
- preserve analytical intent;
- stop after the configured retry limit.

### 11.4 Result Analysis Skill

Responsibilities:

- summarize returned results;
- create a useful title;
- avoid unsupported causal claims;
- assist visualization choice only when deterministic rules are insufficient.

This skill may summarize verified result metadata and create a title, but it must not claim that a result is semantically correct based only on the returned rows.

---

## 12. Tool Layer

The Lightweight Harness Runtime interacts with datasources only through approved tools.

Suggested tool registry:

```text
get_datasource_metadata()
search_semantic_context()
get_table_schema()
get_collection_schema()
get_relationships()
get_metric_candidates()
validate_sql()
validate_mongo_query()
explain_query_plan()
execute_sql()
execute_mongo_query()
save_dashboard_widget()
```

The LLM never receives unrestricted database access.

---

## 13. Connector Layer

### 13.1 Connector Interface

```python
class DataSourceConnector:
    def test_connection(self): ...
    def introspect(self): ...
    def execute_readonly(self, query): ...
    def explain(self, query): ...
    def close(self): ...
```

Implementations:

```text
PostgresConnector
MySQLConnector
MongoConnector
```

### 13.2 PostgreSQL

Capabilities:

- information_schema metadata;
- pg_catalog relationship information;
- EXPLAIN;
- SELECT / WITH execution;
- read-only transaction mode.

### 13.3 MySQL

Capabilities:

- information_schema metadata;
- foreign-key discovery;
- EXPLAIN;
- SELECT / WITH execution;
- read-only account usage.

### 13.4 MongoDB

Capabilities:

- list collections;
- infer fields/data types;
- inspect indexes;
- infer sample document structure locally;
- execute find queries;
- execute aggregation pipelines.

Raw sampled documents used for schema inference should remain inside the application environment. The LLM receives derived metadata, not the sampled documents themselves by default.

---

## 14. Metadata Model

InsightMesh normalizes database metadata into a common internal representation.

Example:

```json
{
  "datasource_id": "ds_123",
  "entity_type": "table",
  "name": "orders",
  "description": "Customer purchase orders",
  "fields": [
    {
      "name": "order_id",
      "type": "integer",
      "nullable": false
    }
  ],
  "primary_key": ["order_id"],
  "relationships": [],
  "profile_statistics": {},
  "semantic_tags": []
}
```

MongoDB collections should map into the same high-level representation.

### 14.1 Local Data Profiling

After schema introspection, the application may compute bounded profiling statistics locally before semantic enrichment. Profiling produces derived metadata, never raw rows for the LLM.

Pipeline:

```text
Schema Introspection
  ↓
Local Data Profiling
  ↓
Normalized Metadata + Profile Statistics
  ↓
Semantic Enrichment
```

Supported profile statistics include:

```text
null ratio
distinct count
min / max for numeric and temporal fields
field presence rate for MongoDB documents
data type distribution
low-cardinality enum candidates
```

Example:

```text
orders.status
distinct_count = 4
candidate_values = completed, cancelled, pending, refunded
```

Profiling must use bounded samples or aggregate queries, enforce a timeout, redact or omit obvious PII, and keep raw samples inside the application environment. Profile statistics are datasource-scoped and may be included in semantic retrieval when relevant.

---

## 15. Automatic Semantic Enrichment

InsightMesh V1 automatically bootstraps semantic metadata.

```text
Raw Schema
  ↓
Metadata Normalizer
  ↓
Local Data Profiling
  ↓
Semantic Enrichment
  ↓
Entity Descriptions
Field Descriptions
Relationship Candidates
Business Terms
Metric Candidates
Profile Statistics
  ↓
Embedding
  ↓
pgvector
```

Example raw schema:

```text
orders
- id
- customer_id
- total_amount
- status
- created_at
```

Possible generated semantic metadata:

```text
Entity: orders
Description: Customer purchase transactions
Business Terms: sales, orders, purchases, transactions
Candidate Metric: revenue
Possible Expression: SUM(total_amount)
Caveat: may require status filtering depending on business semantics
```

AI-generated semantic artifacts must include metadata such as:

```text
confidence
source
generated_at
```

Example:

```json
{
  "term": "revenue",
  "entity": "orders",
  "field": "total_amount",
  "confidence": 0.74,
  "source": "ai_inference"
}
```

The system must not present uncertain semantic inference as confirmed business truth.

---

## 16. Semantic RAG

RAG grounds query generation; it does not replace database execution.

Knowledge types:

```text
1. Schema Metadata
2. Relationships
3. AI-Inferred Business Terms
4. Candidate Metrics
5. Validated Query Examples
```

Retrieval flow:

```text
User Question
  ↓
Embedding
  ↓
pgvector
  ↓
Top-K semantic matches
  ↓
Relationship graph expansion
  ↓
Context Builder
  ↓
Lightweight Harness Runtime
```

Example question:

> “Revenue by customer segment last month”

Possible retrieved context:

```text
orders.total_amount
orders.created_at
orders.customer_id
customers.id
customers.segment

Relationship:
orders.customer_id -> customers.id

Business concept:
revenue -> likely orders.total_amount
```

Context should remain compact and datasource-scoped.

---

## 17. pgvector Storage

Use PostgreSQL + pgvector for the application metadata store.

Suggested tables:

```text
datasources
entities
fields
relationships
semantic_terms
metric_candidates
profile_statistics
query_examples
embeddings
dashboards
dashboard_widgets
query_runs
```

Example embedding record:

```text
embedding_id
datasource_id
object_type
object_id
content
embedding
metadata_json
```

---
## 18. Query Generation

### 18.1 PostgreSQL / MySQL

Generation context should include:

```text
QUESTION
DIALECT
RELEVANT ENTITIES
RELATIONSHIPS
METRIC CANDIDATES
BUSINESS TERMS
```

Example:

```text
QUESTION
Top 5 categories by revenue last month

DIALECT
PostgreSQL

RELEVANT ENTITIES
orders
order_items
products

RELATIONSHIPS
orders.id = order_items.order_id
order_items.product_id = products.id

METRIC CANDIDATE
revenue = SUM(order_items.quantity * order_items.unit_price)
```

### 18.2 MongoDB

MongoDB queries should be generated as structured JSON internally whenever possible rather than raw JavaScript only.

Example analytical output:

```json
[
  {
    "$group": {
      "_id": "$category",
      "total_sales": {"$sum": "$amount"}
    }
  },
  {"$sort": {"total_sales": -1}},
  {"$limit": 5}
]
```

---

## 19. Query Safety

### 19.1 Database Permissions

PostgreSQL/MySQL connectors should use read-only accounts. MongoDB access should be limited to read operations.

### 19.2 SQL AST Validation

Use SQLGlot or equivalent AST parsing.

Allowed categories:

```text
SELECT
WITH ... SELECT
```

Disallowed:

```text
INSERT
UPDATE
DELETE
DROP
ALTER
TRUNCATE
CREATE
GRANT
REVOKE
CALL
MERGE
```

Validation should inspect statement type, referenced tables, columns, functions, subqueries, and CTEs.

### 19.3 MongoDB Validation

MongoDB validation must inspect both the operation and every aggregation pipeline stage.

Allowed operations:

```text
find
aggregate
count
distinct
```

Disallowed:

```text
insert
update
delete
drop
rename
server-side JavaScript
$where
```

Allowed analytical aggregation stages include:

```text
$match
$group
$project
$sort
$limit
$skip
$lookup
$unwind
$count
```

Disallowed stages and execution features include:

```text
$out
$merge
$function
$accumulator with server-side JavaScript
server-side JavaScript expressions
$where
```

The validator must reject a pipeline if any stage or expression can write data, execute server-side JavaScript, or bypass the read-only policy.

### 19.4 Runtime Limits

Recommended configurable controls:

```text
max returned rows
query timeout
max retries = 2
read-only credentials
```

---

## 20. Query Validation and Repair

```text
Generated Query
  ↓
Static Validation
  ↓
Explain / Dry Validation
  ↓
Safe?
 ↙   ↘
No    Yes
↓      ↓
Reject Execute
        ↓
     DB Error?
    ↙       ↘
  Yes        No
   ↓          ↓
 Repair      Result
```

Every repair attempt must be logged. Maximum retries in V1: **2**.

### 20.1 Deterministic Result Verification

`verify_result` is a deterministic post-execution check, not a verifier agent. It must check:

```text
query executed successfully
expected columns or fields exist
result shape is compatible with the requested aggregation
row count is within the configured limit
returned values are serializable
empty-result status is recorded
truncation or null-value warnings are recorded when applicable
```

The result-analysis skill may summarize verified metadata or create a title, but the LLM must not declare semantic correctness or invent causal explanations from raw result rows.

---

## 21. Visualization Engine

InsightMesh supports six visualization types.

### 21.1 Table

Default when the result has many dimensions, detail inspection matters, or no clear chart mapping exists.

### 21.2 KPI Card

Use for a single primary metric, e.g.:

```text
Total Revenue
$1.24M
```

### 21.3 Bar Chart

Use for categorical dimension + numeric metric.

### 21.4 Line Chart

Use for temporal dimension + numeric metric.

### 21.5 Pie / Donut Chart

Use only for meaningful part-to-whole results with low category cardinality.

### 21.6 Area Chart

Use for time-based continuous metrics when magnitude over time matters.

---

## 22. Visualization Selection

Prefer deterministic rules.

```python
if rows == 1 and numeric_columns == 1:
    chart = "kpi"
elif has_time_dimension and numeric_columns >= 1:
    chart = "line"
elif categorical_columns == 1 and numeric_columns == 1:
    chart = "bar"
else:
    chart = "table"
```

LLM assistance may be used for titles, descriptions, and fallback recommendations, but basic chart selection should not depend on an LLM call.

---

## 23. Dashboard

V1 minimum functionality:

- create dashboard;
- save widget;
- remove widget;
- reorder widget;
- rename widget;
- refresh widget;
- switch supported visualization type.

Dashboard refresh flow:

```text
Saved Query
  ↓
Validate
  ↓
Execute
  ↓
Updated Result
```

Do not call the LLM during normal dashboard refresh.

---

## 24. Frontend

Recommended stack:

```text
Next.js
React
TypeScript
Tailwind CSS
Recharts or ECharts
```

Core pages:

```text
/sources
/ask
/dashboards
/settings
```

Suggested Ask page:

```text
┌─────────────────────────────────────────────┐
│ InsightMesh                                 │
├─────────────────────────────────────────────┤
│ Active Source: Production PostgreSQL        │
├─────────────────────────────────────────────┤
│ Ask your data                               │
│ > Top categories by revenue last month      │
├─────────────────────────────────────────────┤
│ Generated Query                             │
│ SELECT ...                                  │
├─────────────────────────────────────────────┤
│ Result                                      │
│ [Table] [KPI] [Bar] [Line] [Pie] [Area]     │
│                                             │
│ visualization                               │
│                                             │
│ [Save to Dashboard]                         │
└─────────────────────────────────────────────┘
```

---

## 25. Backend

Recommended stack:

```text
Python
FastAPI
Pydantic
SQLAlchemy
SQLGlot
psycopg
PyMySQL / mysqlclient
PyMongo
pgvector
```

LLM provider should be abstracted:

```python
class LLMProvider:
    def generate_structured(self, ...): ...
    def embed(self, ...): ...
```

Avoid tightly coupling the Lightweight Harness Runtime to one model provider.

---

## 26. Suggested Repository Structure

```text
insightmesh/
│
├── backend/
│   ├── api/
│   │   ├── routes/
│   │   ├── schemas/
│   │   └── main.py
│   │
│   ├── harness/
│   │   ├── runtime.py
│   │   ├── state.py
│   │   ├── transitions.py
│   │   └── trace.py
│   │
│   ├── skills/
│   │   ├── query-generation/SKILL.md
│   │   ├── query-repair/SKILL.md
│   │   └── result-analysis/SKILL.md
│   │
│   ├── tools/
│   │   ├── metadata.py
│   │   ├── retrieval.py
│   │   ├── validation.py
│   │   ├── sql_tools.py
│   │   ├── mongo_tools.py
│   │   └── dashboard.py
│   │
│   ├── connectors/
│   │   ├── base.py
│   │   ├── postgres.py
│   │   ├── mysql.py
│   │   └── mongodb.py
│   │
│   ├── semantic/
│   │   ├── models.py
│   │   ├── introspection.py
│   │   ├── enrichment.py
│   │   ├── embeddings.py
│   │   └── retriever.py
│   │
│   ├── query/
│   │   ├── sql_validator.py
│   │   ├── mongo_validator.py
│   │   └── execution.py
│   │
│   ├── visualization/
│   │   ├── selector.py
│   │   └── schemas.py
│   │
│   ├── persistence/
│   │   ├── models.py
│   │   └── repository.py
│   │
│   └── config.py
│
├── frontend/
├── evals/
│   ├── datasets/
│   ├── expected/
│   ├── runner.py
│   └── reports/
│
├── demo/
│   ├── postgres/
│   ├── mysql/
│   └── mongodb/
│
├── tests/
├── docker-compose.yml
├── .env.example
├── README.md
├── ARCHITECTURE.md
└── pyproject.toml
```

---

## 27. Data Source Onboarding Pipeline

```text
Connection
  ↓
Test
  ↓
Introspect
  ↓
Normalize metadata
  ↓
Infer relationships
  ↓
Generate semantic descriptions
  ↓
Generate candidate business terms
  ↓
Generate candidate metrics
  ↓
Create embeddings
  ↓
Store in pgvector
  ↓
Datasource ready
```

---

## 28. Semantic Refresh

V1 should support **Refresh Metadata**.

The operation should:

1. re-introspect the active source;
2. recompute bounded local profile statistics;
3. compare metadata and profile hashes;
4. update changed entities and profile statistics;
5. regenerate affected semantic metadata;
6. regenerate affected embeddings;
7. invalidate stale retrieval cache.

---

## 29. Query History

Store:

```text
run_id
datasource_id
question
retrieved_context_ids
generated_query
query_type
validation_result
execution_status
row_count
duration_ms
repair_count
visualization_type
created_at
```

Never log datasource passwords or API secrets.

---

## 30. Runtime Observability

Expose a structured execution trace such as:

```text
1. retrieve_context
2. load query-generation skill
3. generate_query
4. validate_sql
5. explain_query
6. execute_sql
7. verify_result
8. select_visualization
```

The UI may expose **View Execution Trace**, but it should display tools/actions and structured decisions, not hidden chain-of-thought.

---

## 31. Evaluation Strategy

Evaluation is a core deliverable.

V1 should include approximately **40–60 questions** across PostgreSQL, MySQL, and MongoDB.

The evaluation runner must report results both overall and broken down by datasource, difficulty group, and safety/ambiguity category. A single aggregate score is not sufficient to identify dialect-specific weaknesses.

Difficulty groups:

### Easy

Single table/collection.

> “How many customers are there?”

### Medium

Join/group/filter.

> “Revenue by category last month.”

### Hard

Multiple joins, time comparisons, nested aggregation.

> “Which customer segment had the highest revenue growth compared with the same quarter last year?”

### Ambiguous

> “Who are our best customers?”

Expected: clarification required.

### Unsafe

> “Delete all cancelled orders.”

Expected: blocked before execution.

---

## 32. Evaluation Metrics

### 32.1 Query Execution Rate

```text
queries that execute successfully
/
generated queries
```

### 32.2 Result Accuracy

Primary metric. Equivalent queries should be accepted even if generated query strings differ.

### 32.3 Schema Selection Accuracy

Did retrieval include the entities needed to answer the question?

### 32.4 Safety Blocking Rate

Unsafe requests correctly rejected.

### 32.5 Ambiguity Detection Rate

Ambiguous questions correctly flagged.

### 32.6 Repair Success Rate

Failed first attempts that are correctly repaired.

### 32.7 Retrieval Precision

How much retrieved semantic context was actually relevant?

Example evaluation report format:

```text
InsightMesh Evaluation
────────────────────────
                         PostgreSQL   MySQL   MongoDB   Overall
Questions                    XX         XX       XX        XX
Execution Rate               XX%        XX%      XX%       XX%
Result Accuracy              XX%        XX%      XX%       XX%
Schema Retrieval Accuracy    XX%        XX%      XX%       XX%
Repair Success               XX%        XX%      XX%       XX%
Safety Blocking              XX%        XX%      XX%       XX%
Ambiguity Detection          XX%        XX%      XX%       XX%

Breakdown by difficulty:
Easy / Medium / Hard / Ambiguous / Unsafe
```

Never use placeholder numbers as portfolio claims.

---
## 33. Demo Dataset

Ship reproducible demo data using an e-commerce domain because it is intuitive, supports joins/time-series/business metrics, and maps naturally to MongoDB.

### 33.1 PostgreSQL / MySQL

Suggested tables:

```text
customers
products
categories
orders
order_items
payments
```

Relationships:

```text
customers
   │
   └── orders
         │
         ├── order_items ── products ── categories
         │
         └── payments
```

### 33.2 MongoDB

Suggested collections:

```text
customers
orders
products
```

Orders may embed line items. The MongoDB schema does not need to be identical to the SQL schema; the goal is to demonstrate adaptation to the active datasource.

---

## 34. Security Requirements

Mandatory:

- no secrets committed to Git;
- `.env` excluded from tracking;
- `.env.example` uses placeholders only;
- database credentials encrypted at rest if persisted;
- read-only datasource accounts;
- SQL AST validation;
- MongoDB operation and pipeline-stage validation, including blocking `$out`, `$merge`, `$function`, and `$where`;
- no multi-statement SQL;
- MongoDB write operations disabled;
- query timeouts;
- row limits;
- local profiling uses bounded samples or aggregate queries and excludes obvious PII by default;
- raw PII not sent to the LLM by default;
- credentials removed from logs;
- query history must not contain secrets.

---

## 35. Privacy Model

Default policy:

```text
LLM receives:
✓ metadata
✓ semantic descriptions
✓ schema relationships
✓ user question
✓ validated query examples

LLM does not receive:
✗ full tables
✗ customer rows
✗ credentials
✗ raw PII
```

The application may locally inspect bounded samples or run aggregate profiling queries to infer schema and profile statistics, but raw samples must remain inside the application environment and be transformed into derived metadata before LLM interaction. Obvious PII fields should be excluded or redacted from profiling by default.

---

## 36. Performance Requirements

V1 target behavior:

- metadata retrieval should be cached;
- semantic search should return compact Top-K context;
- simple questions should avoid unnecessary tool calls;
- dashboard refresh should not call the LLM;
- database queries must have configurable timeout and row limit;
- local profiling must have configurable sample size and timeout;
- embeddings should be regenerated only when metadata changes.

Exact latency targets should be measured during implementation instead of invented in the PRD.

---

## 37. Error Handling

The system must handle:

```text
connection failure
authentication failure
schema introspection failure
embedding failure
retrieval failure
invalid generated query
database timeout
permission error
query syntax error
unsupported aggregation
empty result
visualization incompatibility
```

Errors shown to the user should be understandable.

Example:

```text
The generated query referenced a field that does not exist.
InsightMesh attempted a repair but could not safely complete the query.
```

---

## 38. V1 Functional Requirements

V1 is complete when:

1. user can add PostgreSQL connection;
2. user can add MySQL connection;
3. user can add MongoDB connection;
4. user can activate one datasource;
5. system can introspect the active datasource;
6. system can generate normalized metadata;
7. system can compute bounded local profile statistics without sending raw rows to the LLM;
8. system can generate semantic metadata automatically;
9. embeddings are stored in pgvector;
10. user can ask an independent natural-language question;
11. Lightweight Harness Runtime deterministically retrieves relevant context;
12. Lightweight Harness Runtime selects the applicable query-generation procedure from current state and datasource type;
13. PostgreSQL questions generate PostgreSQL SQL;
14. MySQL questions generate MySQL SQL;
15. MongoDB questions generate valid MongoDB query/aggregation;
16. SQL queries pass AST-level validation;
17. MongoDB queries pass operation and pipeline-stage validation;
18. database execution uses read-only permissions;
19. recoverable query failures can be repaired;
20. results pass deterministic post-execution verification;
21. results display in a table;
22. visualization recommendation works;
23. six visualization types are supported;
24. successful results can be saved to dashboards;
25. dashboard widgets refresh without LLM regeneration;
26. an evaluation suite exists;
27. an evaluation report can be generated reproducibly by datasource and difficulty.

---

## 39. V1 Acceptance Scenarios

### Scenario 1 — PostgreSQL

User connects PostgreSQL and asks:

> “Top 5 product categories by revenue last month.”

Expected:

```text
retrieve metadata
→ generate PostgreSQL SQL
→ validate
→ execute
→ result table
→ bar chart
```

### Scenario 2 — MySQL

User activates MySQL and asks:

> “Show monthly order count in 2026.”

Expected:

```text
MySQL-compatible SQL
→ execute safely
→ line chart
```

### Scenario 3 — MongoDB

User activates MongoDB and asks:

> “Top 5 cities by total order value.”

Expected:

```text
MongoDB aggregation pipeline
→ validate
→ execute safely
→ bar chart
```

### Scenario 4 — Unsafe Request

> “Delete all cancelled orders.”

Expected:

```text
blocked
no database execution
```

### Scenario 5 — Ambiguous Question

> “Who are our best customers?”

Expected:

```text
clarification required
suggest possible metrics:
- revenue
- order count
- average order value
user rewrites or selects a complete new question
```

### Scenario 6 — Repair

A generated query references a wrong column.

Expected:

```text
database error
→ Runtime records error
→ query-repair skill
→ validation
→ second execution
```

---

## 40. Development Phases

### Phase 0 — Foundation

Build:

```text
repository
FastAPI skeleton
Next.js skeleton
metadata PostgreSQL
pgvector
Docker Compose
environment management
```

**Definition of Done:** frontend, backend, metadata DB, and pgvector run locally.

### Phase 1 — Connector Layer

Implement:

```text
BaseConnector abstraction
PostgresConnector
PostgreSQL test connection, introspection, and read-only execution
```

MySQL and MongoDB connector implementations are deferred until the PostgreSQL vertical slice validates the connector contract and runtime flow.

**Definition of Done:** the PostgreSQL connector can test a connection, introspect metadata, and execute read-only queries through the common connector interface.

### Phase 2 — Metadata and Semantic Layer

Implement:

```text
normalized metadata model
relationship discovery
bounded local data profiling
semantic enrichment
embedding generation
pgvector storage
metadata refresh
```

**Definition of Done:** a PostgreSQL connection automatically produces normalized metadata, bounded profile statistics, semantic artifacts, and a pgvector index without exposing raw rows to the LLM.

### Phase 3 — Semantic Retrieval

Implement:

```text
question embedding
vector search
Top-K retrieval
relationship expansion
context builder
```

**Definition of Done:** relevant entities appear in retrieval results for benchmark questions.

### Phase 4 — Lightweight Harness Runtime

Implement:

```text
runtime state model
deterministic transition engine
tool invocation boundary
structured execution trace
bounded retry / repair policy
```

Do not introduce a standalone LLM planner/router or unnecessary multi-agent abstractions. The runtime selects the next action from its current state and deterministic transition rules.

**Definition of Done:** the Lightweight Harness Runtime deterministically performs retrieve → generate → validate → execute → repair when needed, records an execution trace, and never requires an LLM to choose the next orchestration step.

### Phase 5 — Query Generation

Implement PostgreSQL SQL generation first. Add MySQL SQL and MongoDB query/aggregation generation only after the PostgreSQL baseline is validated; the recommended order is PostgreSQL → MySQL → MongoDB.

**Definition of Done:** the PostgreSQL baseline benchmark executes with correct dialect, deterministic validation, safe read-only execution, and result verification.

### Phase 6 — Guardrails

Implement:

```text
SQLGlot AST validation
MongoDB operation and pipeline-stage validator
read-only enforcement
timeout
row limit
retry limit
```

**Definition of Done:** unsafe benchmark requests are blocked before execution.

### Phase 7 — Visualization and Dashboard

Implement:

```text
Table
KPI
Bar
Line
Pie/Donut
Area
Save Widget
Refresh Widget
```

### Phase 8 — Evaluation

Build:

```text
evaluation dataset
expected results
runner
metrics
report
```

**Definition of Done:** one command generates a reproducible evaluation report.

### Phase 9 — Portfolio Polish

Add:

```text
README
architecture diagram
screenshots
demo GIF/video
measured evaluation results
Docker setup
sample datasource setup
```

---

## 41. Recommended Implementation Order

Build one vertical slice before all connectors.

```text
1. PostgreSQL connector
2. Schema introspection
3. Metadata storage
4. Semantic enrichment
5. pgvector retrieval
6. Minimal Lightweight Harness Runtime
7. PostgreSQL query generation
8. SQLGlot validation
9. Read-only execution
10. Table result
11. Bar/Line visualization
12. Evaluation baseline
13. MySQL connector
14. MongoDB connector
15. MongoDB query generation
16. Remaining charts
17. Dashboard
18. Query repair
19. Full evaluation
```

This sequence validates the architecture early and avoids building three incomplete datasource paths in parallel.

---

## 42. V2 — Multi-Turn Conversational Analytics

V2 introduces conversation state.

Example:

```text
User:
"Revenue by month in 2026."

System:
[result]

User:
"Only Vietnam."

System:
reuses prior analytical context
and adds country filter

User:
"Compare it with 2025."

System:
builds comparative query
```

V2 additions:

```text
conversation state
query context memory
follow-up intent resolution
query revision
reference resolution
```

V2 is deferred until V1 independent-question accuracy is acceptable.

---

## 43. Future Extensions

Possible future work:

- SQL Server connector;
- BigQuery connector;
- Snowflake connector;
- DuckDB connector;
- dashboard filters;
- natural-language dashboard creation;
- scheduled dashboard refresh;
- semantic cache;
- verified-query learning;
- user feedback loops;
- team workspaces;
- human-approved semantic corrections;
- cloud deployment;
- OAuth database connections;
- MCP interface;
- exported analytics APIs.

These are not required for V1.

---

## 44. Technical Risks

### 44.1 Automatic Semantic Inference Can Be Wrong

Example:

```text
total_amount
may not equal
business revenue
```

Mitigation:

- mark generated semantics as inferred;
- store confidence;
- avoid presenting uncertain definitions as facts;
- ask clarification when confidence is low.

### 44.2 MongoDB Schema Inference Is Hard

Mitigation:

- inspect bounded local samples;
- infer field frequency;
- track optional fields;
- avoid assuming one rigid schema.

### 44.3 Vector Retrieval May Miss Join Paths

Mitigation:

```text
semantic retrieval
+
relationship graph expansion
```

Do not rely on vector similarity alone.

### 44.4 Valid SQL May Still Be Semantically Wrong

Mitigation:

- result-based evaluation;
- validated examples;
- semantic grounding;
- ambiguity handling;
- execution verification.

### 44.5 Harness Over-Complexity

Mitigation:

- one lightweight deterministic runtime;
- small skill set;
- limited tool registry;
- max retry policy;
- no multi-agent V1.

---

## 45. Portfolio Positioning

Recommended description:

> **InsightMesh is a self-service analytics platform that enables users to query PostgreSQL, MySQL, and MongoDB using natural language. A lightweight deterministic runtime orchestrates semantic retrieval, database-native query generation, deterministic guardrails, read-only execution, bounded repair, and reusable dashboard visualizations.**

Do not describe the project only as a “Text-to-SQL chatbot.” Text-to-SQL is only one component.

---

## 46. Suggested CV Entry

Use only measured metrics after evaluation.

### InsightMesh — AI-Powered Multi-Source Analytics Platform

Potential bullets after implementation:

- Built a self-service analytics application enabling natural-language querying across PostgreSQL, MySQL, and MongoDB through a lightweight deterministic runtime.
- Implemented automatic schema introspection and semantic metadata enrichment, with pgvector-based retrieval to ground query generation in relevant entities, relationships, and inferred business concepts.
- Designed a lightweight Harness Runtime that orchestrates semantic retrieval, query generation, deterministic validation, read-only execution, bounded repair, and result verification.
- Enforced read-only analytics through AST-level SQL validation, MongoDB operation policies, query timeouts, and restricted database credentials.
- Added automatic result visualization and dashboard persistence across table, KPI, bar, line, pie/donut, and area charts.
- Evaluated query execution, result accuracy, schema retrieval, repair behavior, ambiguity handling, and unsafe-request blocking on a reproducible benchmark.

**Tech:** Python · FastAPI · PostgreSQL · MySQL · MongoDB · pgvector · SQLGlot · LLM · Next.js · React · Docker

---

## 47. Suggested Interview Explanation

> InsightMesh is a self-service analytics platform for users who do not want to write SQL manually. A user connects a PostgreSQL, MySQL, or MongoDB datasource, and the platform automatically inspects the schema and builds semantic metadata. When the user asks a question, a Lightweight Harness Runtime retrieves relevant schema and business context from pgvector, generates a database-native query, validates it deterministically, executes it using read-only access, and returns a table or chart. The runtime uses predefined state transitions and bounded repair based on database feedback, while LLM calls are limited to semantic interpretation, query generation, and repair rather than workflow planning.

---

## 48. Definition of Success

InsightMesh V1 is successful if a new user can:

```text
1. Connect PostgreSQL, MySQL, or MongoDB
2. Activate one datasource
3. Ask a natural-language analytical question
4. Receive a valid database-native query
5. Execute it safely
6. Receive the correct result
7. View an appropriate visualization
8. Save it to a dashboard
```

while:

```text
9. Raw datasource rows are not sent to the LLM by default
10. Unsafe queries are blocked
11. The Lightweight Harness Runtime demonstrates deterministic tool orchestration and bounded repair
12. Performance can be measured with a reproducible evaluation suite
```

---

## 49. Final Recommended V1 Scope

```text
PostgreSQL
MySQL
MongoDB
   │
   ▼
Automatic Schema Introspection
   │
   ▼
Semantic Metadata Generation
   │
   ▼
pgvector RAG
   │
   ▼
Lightweight Harness Runtime
   │
 ┌─┼───────────┐
 ▼ ▼              ▼
Skills Tools  State Transitions
   │
   ▼
Natural Language Question
   │
   ▼
Database-Native Query
   │
   ▼
Deterministic Guardrails
   │
   ▼
Read-Only Execution
   │
   ▼
Verification / Repair
   │
   ▼
Result
   │
 ┌─┴────────────────────────┐
 ▼                          ▼
Table                 Visualization
                             │
                             ▼
                         Dashboard
```

This is the recommended portfolio-ready V1 stopping point. Multi-turn conversation belongs to V2 and should not block the initial release.
