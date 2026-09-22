import type { QueryResult } from "@/lib/query-runs";

export const chartTypes = ["table", "kpi", "bar", "line", "pie", "area"] as const;
export type ChartType = (typeof chartTypes)[number];

export type DashboardFit = "recommended" | "limited" | "not_ready";

export interface DashboardRecommendation {
  fit: DashboardFit;
  chartType: ChartType;
  dashboardName: string;
  dashboardDescription: string;
  message: string;
}

export interface ChartDatum {
  [key: string]: string | number | null;
}

function columnOfType(result: QueryResult, type: string) {
  return result.columns.find((column) => column.type === type)?.name;
}

export function compatibleChartTypes(result: QueryResult): ChartType[] {
  const metric = columnOfType(result, "number");
  const temporal = columnOfType(result, "temporal");
  const category = result.columns.find((column) => ["string", "boolean"].includes(column.type))?.name;
  const compatible: ChartType[] = ["table"];
  if (result.row_count === 1 && metric) compatible.push("kpi");
  if (category && metric && result.row_count >= 1 && result.row_count <= 50) compatible.push("bar");
  if (temporal && metric && result.row_count >= 2) compatible.push("line", "area");
  if (category && metric && result.row_count >= 2 && result.row_count <= 5) compatible.push("pie");
  return compatible;
}

export function chartKeys(result: QueryResult, chartType: ChartType) {
  const metric = columnOfType(result, "number") ?? "";
  const dimension = chartType === "line" || chartType === "area"
    ? columnOfType(result, "temporal") ?? ""
    : result.columns.find((column) => ["string", "boolean"].includes(column.type))?.name ?? "";
  return { dimension, metric };
}

export function toChartData(result: QueryResult): ChartDatum[] {
  return result.rows.map((row) =>
    Object.fromEntries(
      result.columns.map((column, index) => {
        const value = row[index];
        if (column.type === "number" && value !== null && value !== undefined) {
          const numeric = Number(value);
          return [column.name, Number.isFinite(numeric) ? numeric : null];
        }
        return [column.name, value === null || value === undefined ? null : String(value)];
      }),
    ),
  );
}

export function describeChart(result: QueryResult, chartType: ChartType) {
  const { dimension, metric } = chartKeys(result, chartType);
  if (chartType === "table") return `Table containing ${result.row_count} result rows.`;
  if (chartType === "kpi") return `Single key metric for ${metric}.`;
  return `${chartType} chart of ${metric} by ${dimension}, based on ${result.row_count} rows.`;
}

export function getDashboardRecommendation(result: QueryResult): DashboardRecommendation {
  const metric = columnOfType(result, "number");
  const temporal = columnOfType(result, "temporal");
  const category = result.columns.find((column) => ["string", "boolean"].includes(column.type))?.name;

  if (result.row_count === 0 || result.rows.length === 0) {
    return {
      fit: "not_ready",
      chartType: "table",
      dashboardName: "New analysis",
      dashboardDescription: "A dashboard created from verified query results.",
      message: "No rows were returned, so there is nothing useful to add to a dashboard yet. Try broadening the filters or time range.",
    };
  }

  if (temporal && metric && result.row_count >= 2) {
    return {
      fit: "recommended",
      chartType: "line",
      dashboardName: "Trend overview",
      dashboardDescription: `Time-based trend for ${metric}.`,
      message: `Recommended for a dashboard: a line chart showing ${metric} over ${temporal}.`,
    };
  }

  if (category && metric && result.row_count >= 2 && result.row_count <= 50) {
    return {
      fit: "recommended",
      chartType: "bar",
      dashboardName: "Breakdown overview",
      dashboardDescription: `Category breakdown for ${metric}.`,
      message: `Recommended for a dashboard: a bar chart showing ${metric} by ${category}.`,
    };
  }

  if (metric && result.row_count === 1) {
    return {
      fit: "limited",
      chartType: "kpi",
      dashboardName: "KPI snapshot",
      dashboardDescription: `Verified KPI for ${metric}.`,
      message: `This result is a single KPI (${metric}). It can be saved as one dashboard tile, but a meaningful dashboard will need more related metrics or breakdowns.`,
    };
  }

  return {
    fit: "limited",
    chartType: "table",
    dashboardName: "Data table overview",
    dashboardDescription: "A dashboard created from verified tabular results.",
    message: "This result is suitable for a saved table, but its current shape does not support a useful chart recommendation.",
  };
}

export function isChartType(value: string | null | undefined): value is ChartType {
  return chartTypes.includes(value as ChartType);
}
