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
