import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ResultVisualization } from "@/components/result-visualization";
import type { QueryResult } from "@/lib/query-runs";
import { compatibleChartTypes } from "@/lib/visualization";

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
});
