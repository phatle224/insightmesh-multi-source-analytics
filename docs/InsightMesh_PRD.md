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

V1 supports two datasource types:

- PostgreSQL
- MySQL

Users first connect and activate a datasource. Every question in that session is interpreted against that active datasource only. PostgreSQL and MySQL requests generate dialect-aware SQL.

The central architectural concept is a **Lightweight Harness Runtime** rather than a fixed multi-agent pipeline. This custom, deterministic state machine maintains execution state and orchestrates semantic retrieval, query generation, validation, execution, bounded repair, and final response preparation.

InsightMesh also includes an automatically generated semantic knowledge layer. Instead of requiring an administrator to manually configure business metrics or glossary definitions, the system introspects the connected datasource and uses AI-assisted metadata enrichment to infer table meanings, relationships, business concepts, and candidate metrics. These semantic artifacts are embedded and stored in pgvector for retrieval during question answering.

The project intentionally stops short of building a full enterprise BI platform. Its purpose is to demonstrate engineering depth in metadata discovery, multi-datasource SQL abstraction, semantic retrieval, RAG, lightweight runtime design, Text-to-SQL, deterministic guardrails, visualization, dashboard persistence, and formal evaluation.

---

## 2. Product Vision

> **InsightMesh enables users to explore connected PostgreSQL and MySQL databases using natural language without requiring them to know SQL or the physical database schema.**

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
Generate Dialect-Aware SQL
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

1. **Schema understanding** — identify relevant tables, fields, and relationships.
2. **Business terminology** — map user language to database concepts.
3. **Datasource dialect differences** — PostgreSQL and MySQL require different SQL dialect strategies.
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

1. Connect to PostgreSQL and MySQL.
2. Allow one datasource to be selected as active for a session/workspace.
3. Automatically inspect datasource metadata after connection.
4. Build a normalized semantic representation from datasource metadata.
5. Embed semantic metadata into pgvector.
6. Retrieve only relevant schema and semantic context for each question.
7. Use a Lightweight Harness Runtime with deterministic state transitions to orchestrate retrieval, query generation, validation, execution, and bounded repair.
8. Generate PostgreSQL or MySQL SQL depending on the active datasource.
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
- MongoDB and other non-SQL datasource connectors, query generation, validation, demo data, and evaluation;
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

- table names;
- field names and data types;
- primary/foreign keys;
- relationships;
- inferred descriptions;
- inferred business terms;
- candidate metrics;
- validated query examples.

The LLM must not receive full raw tables, credentials, or raw PII by default.

### 7.3 Lightweight Harness Runtime

The core AI workflow uses a custom deterministic state machine rather than a fixed multi-agent pipeline, an orchestration framework such as LangGraph, or a standalone LLM planner/router. Code determines the next workflow transition; LLM calls are limited to semantic interpretation, dialect-aware SQL generation, and bounded query repair.

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

The user opens **Data Sources → Add Connection** and chooses PostgreSQL or MySQL.

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

For PostgreSQL/MySQL, show the generated SQL. Data Analysts should always be able to inspect the generated query.

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
                     ┌─────────────┴─────────────┐
                     ▼                           ▼
                PostgreSQL                    MySQL
                     │                           │
                     └─────────────┬─────────────┘
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
explicit write/destructive intent ──→ blocked (terminal)

received
  ↓
retrieve_context
  ↓
context sufficient? ── no ──→ clarification_required (terminal)
context outside datasource scope ──→ out_of_scope (terminal)
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
                                                 ├── verification failure ──→ failed (terminal)
                                                 └── checks complete ──→ select_visualization
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

Out-of-scope question:

```text
retrieve context
→ deterministic relevance/domain gate
→ no relevant datasource context
→ out_of_scope (terminal)
→ do not generate or execute a query
```

The scope guard must use two deterministic layers. A pre-retrieval check rejects
explicit questions about the application's model, prompt, or system configuration. A
post-retrieval relevance/domain gate requires either an entity, field, business-term,
or metric anchor, or the configured minimum semantic similarity. The semantic index is
the language-agnostic signal for relevant questions;
lexical/entity anchors remain a deterministic fallback. The gate must not ship
demo-schema synonym dictionaries or rely on an LLM-only classification. Questions such as “What is the weather today?”
or “Bạn đang dùng model gì?” must be stopped safely with a message that InsightMesh
only answers analytical questions about the active datasource. A relevant question
with missing detail remains `clarification_required` instead.

The clarification response must ask the user to rewrite or select a complete question. If the user chooses a metric such as `revenue`, the UI should construct a new complete question (for example, `Top customers by revenue`) and submit it as a new independent request. V1 does not retain clarification turns as conversational query context.

Safety blocks, out-of-scope responses, clarification-required responses, and retry exhaustion are terminal states. V1 questions are independent; earlier questions are not used as conversational context.

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
get_relationships()
get_metric_candidates()
validate_sql()
explain_query_plan()
execute_sql()
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
  ├─ Exact entity/field/metric matching
  ├─ Lexical business-term matching
  └─ Embedding + pgvector similarity
  ↓
Deterministic score fusion
  ↓
Top-K grounded matches
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

Exact and lexical matching must be derived from the active datasource's persisted
metadata, semantic terms, metrics, and privacy-safe profile summaries. V1 must not
ship hard-coded synonyms tied to the demo schema. Retrieval records lexical,
semantic, and fused ranking evidence. A vector-only baseline is measured before
hybrid retrieval is enabled, and the hybrid strategy is retained only when it improves
precision without reducing result accuracy or safety.

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
semantic_manifests
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

## 19. Query Safety

### 19.1 Database Permissions

PostgreSQL/MySQL connectors must use read-only accounts.

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

### 19.3 Runtime Limits

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
pgvector
```

LLM provider should be abstracted:

```python
class LLMProvider:
    def generate_structured(self, ...): ...
    def embed(self, ...): ...
```

Avoid tightly coupling the Lightweight Harness Runtime to one model provider.

### V1 Model Selection and Rollback

For the student/portfolio deployment, V1 uses Google AI Studio's direct Gemini API
as the primary generation provider:

- structured SQL generation, bounded repair, and semantic enrichment:
  `gemini-2.5-flash` through the direct Gemini API;
- semantic retrieval embeddings: `openai/text-embedding-3-large` through
  OpenRouter;
- fallback generation: `openai/gpt-4o-mini` through OpenRouter.

The fallback is attempted only after Gemini exhausts its bounded retry on a timeout
or rate-limit response. Authentication failures, invalid structured output, safety
failures, and business-validation failures do not trigger fallback. Direct Gemini
requests use `GEMINI_API_KEY` from Google AI Studio and never expose that key in
logs, traces, prompts, or API responses.

Provider/model configuration must be versioned. Before activation, a candidate
must pass connectivity, strict structured-output validation, embedding-dimension
compatibility, safety checks, and the PostgreSQL benchmark smoke suite. If the
candidate fails, restore the previous known-good provider/model pair. Runtime
fallback is optional and must be explicitly enabled; when no fallback is enabled,
the request ends safely rather than trying known-failing providers. Rollback logs
may contain model IDs, versions, and safe error categories, but never keys, prompts,
raw rows, PII, or hidden reasoning.

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
│   │   └── dashboard.py
│   │
│   ├── connectors/
│   │   ├── base.py
│   │   ├── postgres.py
│   │   └── mysql.py
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
│   └── mysql/
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
7. invalidate stale retrieval cache if a later evidence-gated cache is introduced.

---

## 29. Query History

Store:

```text
run_id
datasource_id
question
retrieved_context_ids
semantic_manifest_id
retrieval_config_version
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

V1 exposes a reverse-chronological, filterable, cursor-paginated history over these
records. Opening a historical run may show its safe trace, retrieval evidence,
generated query, verified result, and reproducibility metadata. **Run again** always
submits the stored complete question as a new independent request with a new `run_id`;
history is never conversational memory.

Each datasource also has an immutable versioned semantic-manifest snapshot containing
normalized entities, fields, relationship provenance, privacy-safe profile summaries,
semantic terms, metrics, artifact IDs, metadata/profile hashes, and relevant
configuration versions. It must never contain credentials, raw rows, or raw PII.

---

## 30. Runtime Observability

Expose a structured execution trace such as:

```text
1. deterministic scope precheck
2. retrieve_context with lexical/semantic/fused scores
3. load query-generation skill
4. generate_query
5. validate_sql
6. explain_query
7. execute_sql
8. verify_result
9. select_visualization
```

The UI may expose **View Execution Trace**, but it should display tools/actions and structured decisions, not hidden chain-of-thought.

The trace should also capture per-state duration, provider/model identity, fallback
usage, provider-call count, retrieval counts and ranking scores, validation category,
repair count, execution duration, and safe error category. It must not store prompts,
hidden reasoning, secrets, raw rows, or raw PII.

---

## 31. Evaluation Strategy

Evaluation is a core deliverable.

V1 should include approximately **30–50 questions** across PostgreSQL and MySQL.

The evaluation runner must report results both overall and broken down by datasource, difficulty group, and safety/ambiguity category. A single aggregate score is not sufficient to identify dialect-specific weaknesses.

Difficulty and behavior groups:

### Easy

Single table.

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

### Out-of-scope

Includes social/model-meta questions and requests unrelated to the active datasource.

Expected: terminal `out_of_scope` before generation or execution.

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

### 32.8 Entity Recall and Join-Path Accuracy

Did retrieval include every required entity and the correct relationship path?

### 32.9 Out-of-Scope and False-Block Rates

Measure both unrelated requests correctly stopped and valid analytical requests
incorrectly rejected. The safety report is incomplete without the false-block rate.

### 32.10 Provider Usage and Latency

Report generation/embedding call counts, fallback usage, and end-to-end plus per-state
p50/p95 latency. Do not invent targets before the baseline is measured.

Every report records datasource seed version, model/provider configuration, skill
versions, metadata/profile hashes, semantic-manifest version, and retrieval
configuration so results are reproducible.

Example evaluation report format:

```text
InsightMesh Evaluation
────────────────────────
                         PostgreSQL   MySQL   Overall
Questions                    XX         XX       XX
Execution Rate               XX%        XX%      XX%
Result Accuracy              XX%        XX%      XX%
Schema Retrieval Accuracy    XX%        XX%      XX%
Entity Recall / Precision    XX/XX      XX/XX    XX/XX
Repair Success               XX%        XX%      XX%
Safety Blocking              XX%        XX%      XX%
Ambiguity Detection          XX%        XX%      XX%
Out-of-Scope Blocking        XX%        XX%      XX%
False-Block Rate             XX%        XX%      XX%
Join-Path Accuracy           XX%        XX%      XX%
Latency p50 / p95            XX/XX      XX/XX    XX/XX

Breakdown by difficulty:
Easy / Medium / Hard / Ambiguous / Out-of-scope / Unsafe
```

Never use placeholder numbers as portfolio claims.

---
## 33. Demo Dataset

Ship equivalent reproducible PostgreSQL and MySQL demo data using an e-commerce domain because it is intuitive and supports joins, time-series analysis, and business metrics.

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

---

## 34. Security Requirements

Mandatory:

- no secrets committed to Git;
- `.env` excluded from tracking;
- `.env.example` uses placeholders only;
- database credentials encrypted at rest if persisted;
- read-only datasource accounts;
- SQL AST validation;
- no multi-statement SQL;
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

- retrieval-context caching is not implemented in V1 because the PostgreSQL evaluation
  measured independent questions and did not establish repeated-question hit rate or a
  material embedding-cost saving; if later evidence justifies it, cache keys include
  datasource ID, normalized question fingerprint, metadata hash, profile hash, and
  retrieval-configuration version;
- cache invalidation is hash/version driven rather than global TTL alone;
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
3. user can activate one datasource;
4. system can introspect the active datasource;
5. system can generate normalized metadata;
6. system can compute bounded local profile statistics without sending raw rows to the LLM;
7. system can generate semantic metadata automatically;
8. embeddings are stored in pgvector;
9. user can ask an independent natural-language question;
10. Lightweight Harness Runtime deterministically retrieves relevant context;
11. Lightweight Harness Runtime selects the applicable query-generation procedure from current state and datasource type;
12. PostgreSQL questions generate PostgreSQL SQL;
13. MySQL questions generate MySQL SQL;
14. SQL queries pass AST-level validation;
15. database execution uses read-only permissions;
16. recoverable query failures can be repaired;
17. results pass deterministic post-execution verification;
18. results display in a table;
19. visualization recommendation works;
20. six visualization types are supported;
21. successful results can be saved to dashboards;
22. dashboard widgets refresh without LLM regeneration;
23. an evaluation suite exists;
24. an evaluation report can be generated reproducibly by datasource and difficulty;
25. vector-only and hybrid-retrieval results can be compared using the same fixtures;
26. user can inspect and rerun independent query-history records;
27. user can inspect relationship provenance through a graph and accessible list;
28. a versioned semantic manifest can reproduce the context used by evaluation.

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

### Scenario 3 — Unsafe Request

> “Delete all cancelled orders.”

Expected:

```text
blocked
no database execution
```

### Scenario 4 — Ambiguous Question

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

### Scenario 5 — Out-of-Scope Question

> “What is the weather today?”

Expected:

```text
retrieve context
→ relevance/domain gate finds no datasource match
→ out_of_scope
no query generation
no database execution
```

The UI explains that the active datasource only supports analytical questions about
its known schema and metrics. This is a terminal response, not a conversational
follow-up.

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

### Scenario 8 — Historical Run

User opens a completed run and selects **Run again**.

Expected:

```text
historical record remains unchanged
→ stored complete question is copied
→ new independent query run is created
→ new run_id and current semantic context are used
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

The MySQL connector was implemented after the PostgreSQL vertical slice validated the shared connector contract and runtime flow.

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
exact/lexical matching from datasource metadata
question embedding and vector search
deterministic score fusion
Top-K retrieval with score evidence
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

Implement PostgreSQL SQL generation first. Add MySQL SQL generation only after the PostgreSQL baseline is validated; the required order is PostgreSQL → MySQL.

**Definition of Done:** the PostgreSQL baseline benchmark executes with correct dialect, deterministic validation, safe read-only execution, and result verification.

### Phase 6 — Guardrails

Implement:

```text
SQLGlot AST validation for PostgreSQL and MySQL
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

### Phase 8 — PostgreSQL Evaluation and Retrieval Quality

Build:

```text
result-based evaluation dataset
adversarial guardrail fixtures
vector-only baseline
hybrid retrieval comparison
reproducibility metadata
metrics and report
```

**Definition of Done:** one Docker command generates baseline and optimized PostgreSQL
reports; hybrid retrieval improves precision without reducing result accuracy or
safety.

### Phase 9 — Query History and Semantic Explainability

Add:

```text
filterable query-run history and independent rerun
versioned semantic manifest
relationship graph with accessible list fallback
declared/inferred relationship provenance
expanded safe observability
measured hash-scoped retrieval cache when justified
```

**Definition of Done:** prior runs and the semantic context behind them are inspectable
and reproducible without exposing secrets, raw rows, raw PII, prompts, or hidden
reasoning.

### Phase 10 — MySQL Expansion

Add connector capability flags, a reusable conformance suite, the MySQL connector and
dialect path, and MySQL-specific evaluation reporting.

### Phase 11 — Full Evaluation and Portfolio Polish

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
13. Adversarial guardrail suite
14. Hybrid retrieval comparison
15. Query history and semantic explainability
16. Connector capability/conformance suite
17. MySQL connector
18. Full PostgreSQL/MySQL evaluation
```

This sequence validates the architecture early and avoids building two incomplete datasource paths in parallel.

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
- dashboard filters;
- natural-language dashboard creation;
- scheduled dashboard refresh;
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

### 44.2 Vector Retrieval May Miss Join Paths

Mitigation:

```text
semantic retrieval
+
relationship graph expansion
```

Do not rely on vector similarity alone.

### 44.3 Valid SQL May Still Be Semantically Wrong

Mitigation:

- result-based evaluation;
- validated examples;
- semantic grounding;
- ambiguity handling;
- execution verification.

### 44.4 Harness Over-Complexity

Mitigation:

- one lightweight deterministic runtime;
- small skill set;
- limited tool registry;
- max retry policy;
- no multi-agent V1.

---

## 45. Portfolio Positioning

Recommended description:

> **InsightMesh is a self-service analytics platform that enables users to query PostgreSQL and MySQL using natural language. A lightweight deterministic runtime orchestrates semantic retrieval, dialect-aware SQL generation, deterministic guardrails, read-only execution, bounded repair, and reusable dashboard visualizations.**

Do not describe the project only as a “Text-to-SQL chatbot.” Text-to-SQL is only one component.

---

## 46. Suggested CV Entry

Use only measured metrics after evaluation.

### InsightMesh — AI-Powered Multi-Source Analytics Platform

Potential bullets after implementation:

- Built a self-service analytics application enabling natural-language querying across PostgreSQL and MySQL through a lightweight deterministic runtime.
- Implemented automatic schema introspection and semantic metadata enrichment, with pgvector-based retrieval to ground query generation in relevant entities, relationships, and inferred business concepts.
- Designed a lightweight Harness Runtime that orchestrates semantic retrieval, query generation, deterministic validation, read-only execution, bounded repair, and result verification.
- Enforced read-only analytics through dialect-aware AST-level SQL validation, query timeouts, and restricted database credentials.
- Added automatic result visualization and dashboard persistence across table, KPI, bar, line, pie/donut, and area charts.
- Evaluated query execution, result accuracy, schema retrieval, repair behavior, ambiguity handling, and unsafe-request blocking on a reproducible benchmark.

**Tech:** Python · FastAPI · PostgreSQL · MySQL · pgvector · SQLGlot · LLM · Next.js · React · Docker

---

## 47. Suggested Interview Explanation

> InsightMesh is a self-service analytics platform for users who do not want to write SQL manually. A user connects a PostgreSQL or MySQL datasource, and the platform automatically inspects the schema and builds semantic metadata. When the user asks a question, a Lightweight Harness Runtime retrieves relevant schema and business context from pgvector, generates dialect-aware SQL, validates it deterministically, executes it using read-only access, and returns a table or chart. The runtime uses predefined state transitions and bounded repair based on database feedback, while LLM calls are limited to semantic interpretation, query generation, and repair rather than workflow planning.

---

## 48. Definition of Success

InsightMesh V1 is successful if a new user can:

```text
1. Connect PostgreSQL or MySQL
2. Activate one datasource
3. Ask a natural-language analytical question
4. Receive valid dialect-aware SQL
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
PostgreSQL                MySQL
     └──────────┬──────────┘
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
Dialect-Aware SQL
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
