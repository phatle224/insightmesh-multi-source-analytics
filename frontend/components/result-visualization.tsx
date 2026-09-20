"use client";

import { useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { QueryResultTable } from "@/components/query-result-table";
import { Card } from "@/components/ui/card";
import type { QueryResult } from "@/lib/query-runs";
import {
  chartKeys,
  compatibleChartTypes,
  describeChart,
  isChartType,
  toChartData,
  type ChartType,
} from "@/lib/visualization";
import { cn } from "@/lib/utils";

const labels: Record<ChartType, string> = {
  table: "Table",
  kpi: "KPI",
  bar: "Bar",
  line: "Line",
  pie: "Donut",
  area: "Area",
};
const pieColors = ["#1e40af", "#d97706", "#3b82f6", "#15803d", "#7e22ce"];

function formatMetric(value: unknown) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? new Intl.NumberFormat().format(numeric) : String(value ?? "—");
}

function ChartCanvas({ type, result }: { type: Exclude<ChartType, "table" | "kpi">; result: QueryResult }) {
  const data = toChartData(result);
  const { dimension, metric } = chartKeys(result, type);
  const common = {
    data,
    margin: { top: 12, right: 20, left: 4, bottom: 12 },
  };
  if (type === "pie") {
    return (
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            dataKey={metric}
            nameKey={dimension}
            innerRadius="48%"
            outerRadius="76%"
            isAnimationActive={false}
          >
            {data.map((entry, index) => (
              <Cell key={`${entry[dimension]}-${index}`} fill={pieColors[index % pieColors.length]} />
            ))}
          </Pie>
          <Tooltip formatter={(value) => formatMetric(value)} />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    );
  }
  const axes = (
    <>
      <CartesianGrid strokeDasharray="3 3" stroke="#dbeafe" />
      <XAxis dataKey={dimension} tick={{ fontSize: 12 }} minTickGap={18} />
      <YAxis tick={{ fontSize: 12 }} width={56} />
      <Tooltip formatter={(value) => formatMetric(value)} />
      <Legend />
    </>
  );
  if (type === "bar") {
    return (
      <ResponsiveContainer width="100%" height="100%">
        <BarChart {...common}>
          {axes}
          <Bar dataKey={metric} fill="#1e40af" radius={[4, 4, 0, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    );
  }
  if (type === "area") {
    return (
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart {...common}>
          {axes}
          <Area dataKey={metric} stroke="#1e40af" fill="#93c5fd" isAnimationActive={false} />
        </AreaChart>
      </ResponsiveContainer>
    );
  }
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart {...common}>
        {axes}
        <Line dataKey={metric} stroke="#1e40af" strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function ResultVisualization({
  result,
  initialType,
  selectedType,
  onTypeChange,
}: {
  result: QueryResult;
  initialType?: string | null;
  selectedType?: ChartType;
  onTypeChange?: (type: ChartType) => void;
}) {
  const compatible = compatibleChartTypes(result);
  const safeInitial = isChartType(initialType) && compatible.includes(initialType) ? initialType : "table";
  const [internalType, setInternalType] = useState<ChartType>(safeInitial);
  const activeType = selectedType && compatible.includes(selectedType) ? selectedType : internalType;
  const setType = (type: ChartType) => {
    setInternalType(type);
    onTypeChange?.(type);
  };
  const { metric } = chartKeys(result, activeType);
  const metricIndex = result.columns.findIndex((column) => column.name === metric);

  return (
    <section className="space-y-4" aria-labelledby="visualization-heading">
      <Card className="min-w-0 overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-3">
          <div>
            <h2 id="visualization-heading" className="font-semibold text-text">Result visualization</h2>
            <p className="text-xs text-muted-foreground">Only structurally compatible views are available.</p>
          </div>
          <div className="flex flex-wrap gap-1" aria-label="Visualization type">
            {compatible.map((type) => (
              <button
                key={type}
                type="button"
                aria-pressed={activeType === type}
                onClick={() => setType(type)}
                className={cn(
                  "min-h-9 rounded-md border px-3 text-sm font-semibold transition-colors",
                  activeType === type
                    ? "border-primary bg-primary text-on-primary"
                    : "border-border bg-card text-muted-foreground hover:border-border-strong hover:text-text",
                )}
              >
                {labels[type]}
              </button>
            ))}
          </div>
        </div>
        {activeType === "table" ? (
          <p className="px-4 py-5 text-sm text-muted-foreground">
            The exact verified rows are shown in the accessible data table below.
          </p>
        ) : activeType === "kpi" ? (
          <div className="px-5 py-8 text-center" role="img" aria-label={describeChart(result, activeType)}>
            <p className="text-sm font-semibold text-muted-foreground">{metric}</p>
            <p className="mt-2 font-mono text-4xl font-semibold tabular-nums text-primary">
              {formatMetric(result.rows[0]?.[metricIndex])}
            </p>
          </div>
        ) : (
          <div
            className="h-80 min-w-0 px-2 py-3"
            role="img"
            aria-label={describeChart(result, activeType)}
          >
            <ChartCanvas type={activeType} result={result} />
          </div>
        )}
        <p className="border-t border-border px-4 py-3 text-sm text-muted-foreground">
          {describeChart(result, activeType)}
        </p>
      </Card>
      <QueryResultTable result={result} />
    </section>
  );
}
