import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { QueryResultTable } from "@/components/query-result-table";
import type { QueryResult } from "@/lib/query-runs";

const result: QueryResult = {
  columns: [
    { name: "status", type: "string", semantic_type: "dimension" },
    { name: "total", type: "number", semantic_type: "metric" },
  ],
  rows: [[null, 1200]],
  row_count: 1,
  truncated: true,
  duration_ms: 9,
  warnings: ["Some source values were normalized."],
};

describe("QueryResultTable", () => {
  it("formats typed values and exposes truncation and result warnings", () => {
    render(<QueryResultTable result={result} />);

    expect(screen.getByRole("table")).toHaveTextContent("1,200");
    expect(screen.getByLabelText("Null value")).toBeVisible();
    expect(screen.getByText(/configured row limit/i)).toBeVisible();
    expect(screen.getByText("Some source values were normalized.")).toBeVisible();
  });

  it("distinguishes a successful empty result from an error", () => {
    render(<QueryResultTable result={{ ...result, rows: [], row_count: 0, truncated: false, warnings: [] }} />);

    expect(screen.getByRole("heading", { name: "No matching rows" })).toBeVisible();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });
});
