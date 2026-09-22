import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ResultVisualization } from "@/components/result-visualization";
import type { QueryResult } from "@/lib/query-runs";
import { compatibleChartTypes, getDashboardRecommendation } from "@/lib/visualization";

const categoryResult: QueryResult = {
  columns: [
    { name: "status", type: "string", semantic_type: "dimension" },
    { name: "orders", type: "number", semantic_type: "metric" },
  ],
  rows: [["paid", 8], ["new", 3]],
  row_count: 2,
  truncated: false,
  duration_ms: 4,
  warnings: [],
};

describe("deterministic visualization adapter", () => {
  it("only exposes compatible category charts", () => {
    expect(compatibleChartTypes(categoryResult)).toEqual(["table", "bar", "pie"]);
  });

  it("keeps an exact accessible table when another presentation is selected", () => {
    render(<ResultVisualization result={categoryResult} initialType="table" />);

    fireEvent.click(screen.getByRole("button", { name: "Bar" }));

    expect(screen.getByRole("button", { name: "Bar" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("table")).toHaveTextContent("paid");
    expect(screen.getByText(/bar chart of orders by status/i)).toBeVisible();
  });

  it("recommends a KPI tile for a single metric result", () => {
    const recommendation = getDashboardRecommendation({
      ...categoryResult,
      columns: [{ name: "total_categories", type: "number", semantic_type: "metric" }],
      rows: [[3]],
      row_count: 1,
    });

    expect(recommendation.fit).toBe("limited");
    expect(recommendation.chartType).toBe("kpi");
    expect(recommendation.message).toMatch(/single KPI/i);
  });

  it("marks empty results as not ready for a dashboard", () => {
    const recommendation = getDashboardRecommendation({
      ...categoryResult,
      rows: [],
      row_count: 0,
    });

    expect(recommendation.fit).toBe("not_ready");
    expect(recommendation.message).toMatch(/No rows were returned/i);
  });
});
