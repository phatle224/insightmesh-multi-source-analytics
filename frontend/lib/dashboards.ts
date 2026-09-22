import { apiRequest } from "@/lib/api-client";
import type { QueryResult } from "@/lib/query-runs";
import type { ChartType } from "@/lib/visualization";

export interface DashboardSummary {
  id: string;
  name: string;
  description: string | null;
  widget_count: number;
  created_at: string;
  updated_at: string;
}

export interface DashboardWidget {
  id: string;
  dashboard_id: string;
  datasource_id: string;
  source_query_run_id: string | null;
  title: string;
  question: string;
  validated_query: { sql: string; expected_columns: string[] };
  query_type: string;
  chart_type: ChartType;
  chart_config: Record<string, unknown>;
  compatible_chart_types: ChartType[];
  position: number;
  result: QueryResult | null;
  status: "ready" | "empty" | "stale" | "failed";
  row_count: number | null;
  duration_ms: number | null;
  last_refreshed_at: string | null;
  error: { code: string; message: string } | null;
  created_at: string;
  updated_at: string;
}

export interface DashboardDetail extends DashboardSummary {
  widgets: DashboardWidget[];
}

export const listDashboards = () => apiRequest<DashboardSummary[]>("/api/v1/dashboards");

export const createDashboard = (name: string, description?: string) =>
  apiRequest<DashboardSummary>("/api/v1/dashboards", {
    method: "POST",
    body: JSON.stringify({ name, description: description || null }),
  });

export const getDashboard = (id: string) =>
  apiRequest<DashboardDetail>(`/api/v1/dashboards/${id}`);

export const addDashboardWidget = (
  dashboardId: string,
  payload: {
    query_run_id?: string;
    saved_analysis_id?: string;
    title: string;
    chart_type: ChartType;
  },
) =>
  apiRequest<DashboardWidget>(`/api/v1/dashboards/${dashboardId}/widgets`, {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const updateDashboardWidget = (
  widgetId: string,
  payload: { title?: string; chart_type?: ChartType; position?: number },
) =>
  apiRequest<DashboardWidget>(`/api/v1/dashboard-widgets/${widgetId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });

export const deleteDashboardWidget = (widgetId: string) =>
  apiRequest<void>(`/api/v1/dashboard-widgets/${widgetId}`, { method: "DELETE" });

export const refreshDashboardWidget = (widgetId: string) =>
  apiRequest<DashboardWidget>(`/api/v1/dashboard-widgets/${widgetId}/refresh`, {
    method: "POST",
  });
