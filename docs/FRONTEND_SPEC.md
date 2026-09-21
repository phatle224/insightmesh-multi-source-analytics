# InsightMesh Frontend Specification

**Status:** Functional baseline; visual direction approved in `design-system/insightmesh/MASTER.md`
**Scope:** V1  
**Product requirements:** `docs/InsightMesh_PRD.md`  
**Technical contracts:** `docs/TECHNICAL_DESIGN.md`

## 1. Purpose and Rules

This document defines frontend information architecture, user flows, UI states, component responsibilities, and backend expectations. Visual direction is governed by `design-system/insightmesh/MASTER.md` and must be applied without changing the functional contracts below.

Fixed rules:

- Do not create conversational memory or a chat transcript in V1.
- Do not show fake query results or optimistic success before the backend confirms execution.
- Do not expose hidden chain-of-thought. Execution trace shows named actions, states, durations, and safe summaries only.
- Always show the active datasource on analytical and dashboard surfaces.
- Generated PostgreSQL/MySQL SQL remains inspectable.
- Unsafe requests have no Execute/Continue action.
- Dashboard refresh never requests query regeneration.

## 2. Frontend Stack

```text
Next.js
React
TypeScript with strict mode
Tailwind CSS
Local shadcn-style components over Radix UI primitives
Phosphor SVG icons
Recharts behind a local deterministic chart adapter
```

Phase 3 selects Tailwind CSS v4, Radix UI as the accessible headless primitive layer, and Phosphor as the single icon family. Components are owned in `frontend/components/` rather than hidden behind a runtime component service.

Use server components for static shell/data where helpful and client components only for interactive forms, tables, charts, reordering, and live run status. API access must pass through one typed client layer; components must not construct endpoint URLs ad hoc.

## 3. Information Architecture

Primary routes:

```text
/sources                 datasource list and onboarding
/sources/new             add/test/save connection
/sources/[id]            metadata, onboarding state, refresh
/ask                     independent analytical question workspace
/history                 query-run history and reproducibility details
/dashboards              dashboard list
/dashboards/[id]         dashboard canvas and widgets
/settings                non-secret user-visible preferences
```

Primary navigation:

```text
InsightMesh
├── Sources
├── Ask
├── History
├── Dashboards
└── Settings
```

The shell includes the current active datasource indicator. When no datasource is active, `/ask` renders a blocking empty state linking to `/sources`; it does not show an enabled question submission form.

## 4. Global UI State

The frontend maintains:

```text
active datasource summary
datasource list and onboarding statuses
current independent query run
query-history filters and cursor
dashboard list/current dashboard
display preferences
```

The frontend does not maintain prior-question context for query generation. Query
history is a read-only record of independent runs; selecting **Run again** submits the
stored complete question as a new request with a new `run_id`, never as a follow-up
turn.

## 5. Sources Experience

### 5.1 Sources List

Each datasource card/row shows:

- connection name;
- datasource type;
- database name or safe host label;
- onboarding status;
- active badge;
- last metadata refresh time;
- actions: View, Activate, Refresh Metadata.

Statuses:

```text
testing
introspecting
profiling
enriching
embedding
ready
failed
```

Only `ready` sources expose Activate. Refresh shows progress and preserves the last usable semantic index until the refresh succeeds.

### 5.2 Add Connection

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

Form behavior:

1. Test Connection validates transport/authentication without saving.
2. Save Connection is enabled only after a successful test for the unchanged form values.
3. Saving starts onboarding and navigates to the datasource detail/status page.
4. Password values are never redisplayed after save.

Errors distinguish connection refused, authentication failure, permission failure, timeout, and unsupported configuration without exposing driver secrets.

### 5.3 Datasource Detail

Show:

- safe connection summary;
- onboarding/refresh progress;
- discovered entities and relationships;
- profile-statistics summary, never raw samples;
- semantic-index status;
- versioned semantic-manifest summary and export action;
- relationship provenance (`declared` or `inferred`) and confidence where applicable;
- last successful refresh and latest failure;
- Activate and Refresh Metadata actions.

The profile summary shows derived counts, ratios, ranges, and privacy exclusions
through progressive disclosure. Semantic status uses text and iconography, not color
alone: `API key required`, `Indexing`, `Searchable`, `Stale index retained`, or
`Index unavailable`. A missing provider key must not hide successfully completed
local profiling or make the datasource appear unusable.

The implemented semantic-manifest card loads the latest immutable version without
blocking the rest of datasource detail. It shows entity/field/term/metric/relationship
counts first, places hashes and provider configuration behind keyboard-accessible
progressive disclosure, and exports the already-sanitized API payload as a versioned
JSON file. Export is client-side and must not add hidden fields or refetch raw data.

The detail page provides Table and Relationship Graph views. The graph supports
keyboard entity selection and join-path highlighting and always has an equivalent
table/list representation. Low-confidence inferred relationships remain inspectable
but are visibly marked as excluded from query-generation context.

## 6. Ask Workspace

### 6.1 Layout

```text
┌─────────────────────────────────────────────────────────┐
│ Active Source: name / type / ready state                │
├─────────────────────────────────────────────────────────┤
│ Ask your data                                           │
│ [ complete analytical question                       ]  │
│                                             [Run]       │
├─────────────────────────────────────────────────────────┤
│ Status / warnings / clarification                       │
├───────────────────────────┬─────────────────────────────┤
│ Generated Query           │ Execution Trace             │
│ collapsible code panel    │ collapsible structured list │
├───────────────────────────┴─────────────────────────────┤
│ Result: [Table] [KPI] [Bar] [Line] [Pie] [Area]         │
│ verified result / visualization                         │
│                                      [Save to Dashboard]│
└─────────────────────────────────────────────────────────┘
```

On narrower screens, panels stack in this order: question, status, generated query, trace, result, visualization actions.

### 6.2 Run States

| Backend status | UI behavior |
|---|---|
| `received` | Disable duplicate submit; show initial progress. |
| `retrieve_context` | Show “Finding relevant schema and business context”. |
| `generate_query` | Show “Generating a read-only query”. |
| `validate_query` | Show “Checking query safety”. |
| `execute_query` | Show “Running query” with cancel only if backend supports cancellation. |
| `repair_query` | Show attempt number and “Repairing query”; do not expose hidden reasoning. |
| `verify_result` | Show “Checking result shape”. |
| `select_visualization` | Show “Preparing visualization”. |
| `completed` | Render query, verified result, chart, warnings, and save action. |
| `clarification_required` | Render complete suggested questions; current run is terminal. |
| `out_of_scope` | Explain that the question does not match the active datasource; no query or continue action. |
| `blocked` | Render safety explanation; no execute/continue action. |
| `failed` | Render safe error and retry-as-new-request action where appropriate. |

### 6.3 Clarification

For an ambiguous question, show complete alternatives such as:

```text
Top customers by revenue
Top customers by order count
Top customers by average order value
```

Selecting one copies the full text into the question field or immediately submits it as a new independent run with a new `run_id`. Never submit only a fragment such as `revenue`, and never attach hidden prior-turn context.

### 6.3a Out-of-Scope Questions

When the runtime returns `out_of_scope`, explain that Ask only answers analytical
questions grounded in the active datasource's known schema and metrics. Do not show a
retry or query-generation action. The user may submit a new complete analytical
question independently.

### 6.4 Generated Query Panel

- Collapsed by default for business users; user preference may keep it open.
- SQL uses dialect-aware syntax highlighting.
- Provide Copy Query.
- Show query type, validation status, repair count, execution duration, and truncation warning.
- Do not offer an editable-and-execute query editor in V1.

### 6.5 Execution Trace

Display ordered entries containing:

```text
state/action name
status
started_at / duration
safe structured summary
repair attempt number when relevant
```

Never display prompts, model chain-of-thought, credentials, raw database exceptions containing secrets, or raw profiling samples.

### 6.6 Result Table

- Table is always available for a successful result.
- Headers come from backend column metadata.
- Preserve null as a visible null marker, not an empty string.
- Format decimals, currency, dates, and percentages for display without changing underlying values.
- Show returned row count, truncation state, execution duration, and warnings.
- Pagination is client-side only for already returned bounded rows; it must not imply that all database rows were loaded.
- Empty result is a successful empty state, not an error.

### 6.7 Visualization

Supported types:

| Type | Minimum compatible shape |
|---|---|
| Table | Any verified result |
| KPI | One row and one primary numeric metric |
| Bar | One categorical dimension and one or more numeric metrics |
| Line | One temporal dimension and one or more numeric metrics |
| Pie/Donut | One categorical dimension, one numeric metric, low cardinality |
| Area | One temporal dimension and one or more numeric metrics |

The backend recommends the initial type. The UI only enables compatible alternatives. Switching chart type does not rerun the query or call the LLM.

Implementation decision: Recharts is used behind `frontend/lib/visualization.ts`, which owns compatibility, row-to-chart conversion, keys, and accessible text descriptions. Components do not depend on chart-library data inference. Chart animation is disabled, every chart has a visible legend/tooltip where applicable, a concise text summary, and the exact verified data table rendered alongside it.

### 6.8 Save to Dashboard

Enabled only for `completed` runs. Modal fields:

```text
Dashboard
Widget title
Chart type
```

The saved widget uses the validated query, datasource ID, query type, compatible chart config, original complete question, and creation time. Saving must not regenerate the query.

## 7. Dashboards

### 7.1 Dashboard List

Show dashboard name, widget count, last updated time, and Create Dashboard. Empty state explains that completed query results can be saved from `/ask`.

### 7.2 Dashboard Detail

Minimum actions:

- add previously completed result through the Ask flow;
- reorder widgets;
- rename widget;
- switch to a compatible chart type;
- refresh widget;
- remove widget.

Widget states:

```text
loading
ready
empty
stale
failed
```

Refresh revalidates and executes the stored query. Show the last refresh time and safe error without discarding the last successful rendering. No LLM progress state should appear during refresh.

## 8. Query History

`/history` lists query-run summaries in reverse chronological order with cursor-based
pagination and filters for question text, datasource, terminal status, and creation time. Each row
shows question, datasource, status, created time, duration, repair count, result row
count, and visualization type without exposing raw driver errors or hidden reasoning.

Selecting a run opens its generated query, verified result when retained, safe trace,
retrieval evidence, and reproducibility metadata. Available actions are **Copy query**,
**Run again**, and **Save to dashboard** for eligible completed runs. Run again always
calls the normal create-run endpoint and does not mutate the historical record.

## 9. Settings

V1 settings may expose only non-secret, user-actionable preferences supported by the backend, such as default table page size or query-panel visibility. Do not create provider-key forms or controls for server-enforced safety limits unless the backend explicitly supports them.

## 10. Typed API Expectations

The frontend client covers:

```text
datasources: list, test, create, detail, semantic manifest, activate, refresh, onboarding status
query runs: create, paginated/filterable history, detail/status, trace
dashboards: list, create
widgets: create, update, reorder, delete, refresh
```

Every request handles the canonical error envelope from `TECHNICAL_DESIGN.md`. Components consume typed domain objects returned by the API client rather than raw `fetch` responses.

Run-status polling, server-sent events, or another transport is an implementation choice until measured latency requires one. UI behavior must remain identical across transports.

## 11. Loading, Empty, and Error States

Every data surface must define:

- initial loading state;
- background refresh state;
- empty state with a useful next action;
- recoverable error with retry;
- terminal error with safe explanation;
- stale-data state when the last successful result remains visible.

Do not use generic “Something went wrong” when the backend supplies a safe actionable category. Never display stack traces or raw driver errors.

## 12. Accessibility and Responsive Behavior

- All forms have labels, descriptions, and field-level errors.
- Keyboard navigation covers primary actions, tabs, dialogs, tables, and chart alternatives.
- Status is communicated with text/icon in addition to color.
- Focus moves to the status/error/clarification region after submission completes.
- Code panels and tables are horizontally scrollable without breaking the page.
- Charts include an accessible text summary and the equivalent result table.
- Desktop is the primary analytics layout; tablet/mobile must remain usable with stacked panels.

## 13. Visual Design Constraints

Approved visual direction:

- use a restrained data-dense B2B analytics shell with left navigation and a wide content area;
- use the approved blue/navy palette with amber accent tokens from `MASTER.md`;
- use Fira Sans for product UI and Fira Code only for SQL, identifiers, and tabular numeric values;
- prioritize data density, table readability, query readability, and clear state feedback;
- avoid decorative gradients, excessive motion, glass effects, and marketing-page styling in product screens;
- use the shared 4/8px spacing rhythm and semantic design tokens rather than raw per-component values;
- use Phosphor as the default SVG icon family unless a documented component-specific exception is approved;
- respect visible focus, 4.5:1 text contrast, reduced motion, and responsive checkpoints at 375/768/1024/1440px.

Page-specific overrides may be added under `design-system/insightmesh/pages/`; they override `MASTER.md` only for the named page and must not change the functional contracts above.

## 14. Frontend Acceptance Scenarios

1. With no active datasource, `/ask` blocks submission and links to Sources.
2. A ready datasource can be activated and remains visible in the global shell and Ask workspace.
3. PostgreSQL question progress maps to runtime states and ends with inspectable SQL, table, and compatible chart.
4. MySQL question progress maps to the same runtime states and ends with inspectable MySQL-compatible SQL.
5. An unsafe request ends in a blocked state with no execution action.
6. An ambiguous request shows complete alternatives; selection starts a new independent run.
7. Empty results render successfully with a clear empty state.
8. Truncated results show an explicit warning and returned row count.
9. Saving a completed run creates a dashboard widget without regenerating the query.
10. Widget refresh shows ordinary execution progress, retains the last good result on failure, and performs no LLM call.
11. Execution trace contains structured actions but no prompts, hidden reasoning, secrets, or raw PII.
12. All charts have the same data available in an accessible table.
13. History filters and pagination remain keyboard accessible; rerunning a historical question creates a new independent run.
14. Datasource relationships are available as both an interactive graph and an equivalent accessible list, with inferred relationships clearly labeled.
15. Semantic-manifest and retrieval evidence never display credentials, raw rows, raw PII, prompts, or hidden reasoning.

## 15. Explicit Non-Goals

- multi-turn chat UI;
- natural-language follow-up context;
- editable SQL execution console;
- MongoDB and other non-SQL datasource onboarding, query viewers, and execution states;
- drag-and-drop BI report builder beyond widget reorder;
- cross-datasource selection for one question;
- scheduled reports or alerts;
- authentication/RBAC screens until the backend scope defines them;
- provider/model administration UI;
- mobile-first dashboard authoring.
