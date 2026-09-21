import { fireEvent, render, screen } from "@testing-library/react";
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
    expect(screen.getByText("Showing 1 of 1 returned row")).toBeVisible();
  });

  it("distinguishes a successful empty result from an error", () => {
    render(<QueryResultTable result={{ ...result, rows: [], row_count: 0, truncated: false, warnings: [] }} />);

    expect(screen.getByRole("heading", { name: "No matching rows" })).toBeVisible();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("slices rows client-side and navigates between pages", () => {
    const multiRowResult: QueryResult = {
      columns: [
        { name: "id", type: "number", semantic_type: "dimension" },
        { name: "title", type: "string", semantic_type: "dimension" },
      ],
      rows: Array.from({ length: 30 }, (_, index) => [index + 1, `Item ${index + 1}`]),
      row_count: 30,
      truncated: false,
      duration_ms: 25,
      warnings: [],
    };

    const { rerender } = render(<QueryResultTable result={multiRowResult} />);

    // Default pageSize is 10: shows 1-10
    expect(screen.getByText("Showing 1–10 of 30 returned rows")).toBeVisible();
    expect(screen.getByText("Item 1")).toBeInTheDocument();
    expect(screen.getByText("Item 10")).toBeInTheDocument();
    expect(screen.queryByText("Item 11")).not.toBeInTheDocument();

    const prevButtons = screen.getAllByRole("button", { name: /previous page/i });
    const nextButtons = screen.getAllByRole("button", { name: /next page/i });

    expect(prevButtons[0]).toBeDisabled();
    expect(nextButtons[0]).not.toBeDisabled();

    // Navigate to page 2 via footer next button
    fireEvent.click(nextButtons[nextButtons.length - 1]);

    expect(screen.getByText("Showing 11–20 of 30 returned rows")).toBeVisible();
    expect(screen.queryByText("Item 1")).not.toBeInTheDocument();
    expect(screen.getByText("Item 11")).toBeInTheDocument();
    expect(screen.getByText("Item 20")).toBeInTheDocument();

    // Change page size to 25
    const select = screen.getByLabelText(/rows per page:/i);
    fireEvent.change(select, { target: { value: "25" } });

    expect(screen.getByText("Showing 1–25 of 30 returned rows")).toBeVisible();
    expect(screen.getByText("Item 1")).toBeInTheDocument();
    expect(screen.getByText("Item 25")).toBeInTheDocument();
    expect(screen.queryByText("Item 26")).not.toBeInTheDocument();

    // Rerender with a new result resets page to 1
    const nextResult: QueryResult = {
      ...multiRowResult,
      rows: Array.from({ length: 15 }, (_, index) => [index + 101, `Fresh ${index + 1}`]),
      row_count: 15,
    };
    rerender(<QueryResultTable result={nextResult} />);

    expect(screen.getByText("Showing 1–15 of 15 returned rows")).toBeVisible();
    expect(screen.getByText("Fresh 1")).toBeInTheDocument();
  });
});
