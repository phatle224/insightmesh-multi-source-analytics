import { apiRequest } from "@/lib/api-client";

export type QueryRunStatus =
  | "received"
  | "retrieve_context"
  | "generate_query"
  | "validate_query"
  | "execute_query"
  | "repair_query"
  | "verify_result"
  | "select_visualization"
  | "completed"
  | "clarification_required"
  | "out_of_scope"
  | "blocked"
  | "failed";

export interface GeneratedQuery {
  sql: string;
  expected_columns: string[];
}

export interface QueryResultColumn {
  name: string;
  type: "string" | "number" | "boolean" | "temporal" | "structured" | "unknown";
  semantic_type: "dimension" | "metric";
}

export interface QueryResult {
  columns: QueryResultColumn[];
  rows: unknown[][];
  row_count: number;
  truncated: boolean;
  duration_ms: number;
  warnings: string[];
}

export interface QueryRunError {
  code: string;
  message: string;
}

export interface QueryRun {
  run_id: string;
  datasource_id: string;
  question: string;
  status: QueryRunStatus;
  generated_query: GeneratedQuery | null;
  validation: Record<string, unknown>;
  result: QueryResult | null;
  repair_count: number;
  provider_call_count: number;
  visualization_type: string | null;
  clarification_suggestions: string[];
  warnings: string[];
  error: QueryRunError | null;
  created_at: string;
}

export interface TraceEvent {
  sequence: number;
  timestamp: string;
  state: QueryRunStatus;
  event: string;
  outcome: string;
  duration_ms?: number;
  error_code?: string;
  details?: Record<string, unknown>;
}

export interface QueryTrace {
  run_id: string;
  status: QueryRunStatus;
  trace: TraceEvent[];
}

export interface QueryRunSummary {
  run_id: string;
  datasource_id: string;
  datasource_name: string;
  question: string;
  status: QueryRunStatus;
  row_count: number | null;
  duration_ms: number | null;
  repair_count: number;
  provider_call_count: number;
  visualization_type: string | null;
  error_code: string | null;
  created_at: string;
}

export interface QueryRunPage {
  items: QueryRunSummary[];
  limit: number;
  total: number;
  next_cursor: string | null;
  has_more: boolean;
}

export interface QueryRunFilters {
  limit?: number;
  cursor?: string;
  status?: QueryRunStatus | "";
  datasourceId?: string;
  createdBefore?: string;
  search?: string;
}

export function createQueryRun(datasourceId: string, question: string) {
  return apiRequest<QueryRun>("/api/v1/query-runs", {
    method: "POST",
    body: JSON.stringify({ datasource_id: datasourceId, question }),
  });
}

export const getQueryRun = (runId: string) =>
  apiRequest<QueryRun>(`/api/v1/query-runs/${runId}`);

export const getQueryTrace = (runId: string) =>
  apiRequest<QueryTrace>(`/api/v1/query-runs/${runId}/trace`);

export function listQueryRuns(filters: QueryRunFilters = {}) {
  const params = new URLSearchParams();
  params.set("limit", String(filters.limit ?? 20));
  if (filters.cursor) params.set("cursor", filters.cursor);
  if (filters.status) params.set("status", filters.status);
  if (filters.datasourceId) params.set("datasource_id", filters.datasourceId);
  if (filters.createdBefore) params.set("created_before", filters.createdBefore);
  if (filters.search?.trim()) params.set("search", filters.search.trim());
  return apiRequest<QueryRunPage>(`/api/v1/query-runs?${params.toString()}`);
}
