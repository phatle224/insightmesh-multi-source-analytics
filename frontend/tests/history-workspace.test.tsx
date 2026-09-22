import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { HistoryWorkspace } from "@/components/history-workspace";
import type { QueryRunPage } from "@/lib/query-runs";

const mocks = vi.hoisted(() => ({
  listQueryRuns: vi.fn(),
  createQueryRun: vi.fn(),
  getQueryRun: vi.fn(),
  getQueryTrace: vi.fn(),
  listSavedAnalyses: vi.fn(),
  refreshSavedAnalysis: vi.fn(),
}));

vi.mock("@/lib/query-runs", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/query-runs")>()),
  listQueryRuns: mocks.listQueryRuns,
  createQueryRun: mocks.createQueryRun,
  getQueryRun: mocks.getQueryRun,
  getQueryTrace: mocks.getQueryTrace,
}));

vi.mock("@/lib/saved-analyses", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/saved-analyses")>()),
  listSavedAnalyses: mocks.listSavedAnalyses,
  refreshSavedAnalysis: mocks.refreshSavedAnalysis,
}));

vi.mock("@/components/datasource-provider", () => ({
  useDatasources: () => ({
    sources: [{ id: "source-1", name: "Docker demo store" }],
  }),
}));

const page: QueryRunPage = {
  limit: 20,
  total: 1,
  next_cursor: null,
  has_more: false,
  items: [
    {
      run_id: "run-1",
      datasource_id: "source-1",
      datasource_name: "Docker demo store",
      question: "Revenue by category",
      status: "completed",
      row_count: 4,
      duration_ms: 20,
      repair_count: 0,
      provider_call_count: 2,
      visualization_type: "bar",
      error_code: null,
      created_at: "2026-09-21T00:00:00Z",
    },
  ],
};

describe("HistoryWorkspace", () => {
  beforeEach(() => {
    mocks.listQueryRuns.mockReset().mockResolvedValue(page);
    mocks.createQueryRun.mockReset().mockResolvedValue({ run_id: "run-2" });
    mocks.getQueryRun.mockReset().mockResolvedValue({
      run_id: "run-1",
      datasource_id: "source-1",
      question: "Revenue by category",
      status: "completed",
      generated_query: { sql: "SELECT 1", expected_columns: ["value"] },
      validation: { explain_valid: true },
      result: null,
      repair_count: 0,
      provider_call_count: 2,
      visualization_type: "table",
      clarification_suggestions: [],
      warnings: [],
      error: null,
      created_at: "2026-09-21T00:00:00Z",
    });
    mocks.getQueryTrace.mockReset().mockResolvedValue({
      run_id: "run-1",
      status: "completed",
      trace: [],
    });
    mocks.listSavedAnalyses.mockReset().mockResolvedValue([]);
    mocks.refreshSavedAnalysis.mockReset();
  });

  it("shows safe run summaries and reruns as a new request", async () => {
    render(<HistoryWorkspace />);

    expect(await screen.findByText("Revenue by category")).toBeInTheDocument();
    expect(screen.getAllByText("Docker demo store")).toHaveLength(2);

    fireEvent.click(screen.getByRole("button", { name: "Rerun as new" }));

    await waitFor(() =>
      expect(mocks.createQueryRun).toHaveBeenCalledWith("source-1", "Revenue by category"),
    );
    expect(await screen.findByText("Created independent run run-2.")).toBeInTheDocument();
  });

  it("opens retained safe run details on demand", async () => {
    render(<HistoryWorkspace />);
    await screen.findByText("Revenue by category");

    fireEvent.click(screen.getByRole("button", { name: "View details" }));

    expect(await screen.findByText("Generated PostgreSQL")).toBeInTheDocument();
    expect(screen.getByText("Execution trace")).toBeInTheDocument();
    expect(mocks.getQueryRun).toHaveBeenCalledWith("run-1");
    expect(mocks.getQueryTrace).toHaveBeenCalledWith("run-1");
  });

  it("applies explicit question and status filters", async () => {
    render(<HistoryWorkspace />);
    await screen.findByText("Revenue by category");

    fireEvent.change(screen.getByLabelText("Search questions"), {
      target: { value: "customers" },
    });
    fireEvent.change(screen.getByLabelText("Status"), {
      target: { value: "failed" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Apply filters" }));

    await waitFor(() =>
      expect(mocks.listQueryRuns).toHaveBeenLastCalledWith(
        expect.objectContaining({ search: "customers", status: "failed", cursor: undefined }),
      ),
    );
  });

  it("refreshes a saved analysis in place instead of creating a recent run", async () => {
    const saved = {
      id: "saved-1",
      datasource_id: "source-1",
      datasource_name: "Docker demo store",
      name: "Revenue snapshot",
      description: null,
      question: "Revenue by category",
      validated_query: { sql: "SELECT 1", expected_columns: ["value"] },
      query_type: "postgresql" as const,
      visualization_type: "table",
      result: null,
      tags: [],
      source_query_run_id: "run-1",
      created_at: "2026-09-21T00:00:00Z",
      updated_at: "2026-09-21T00:00:00Z",
    };
    mocks.listSavedAnalyses.mockResolvedValue([saved]);
    mocks.refreshSavedAnalysis.mockResolvedValue({
      ...saved,
      result: {
        columns: [{ name: "value", type: "number", semantic_type: "metric" }],
        rows: [[42]],
        row_count: 1,
        truncated: false,
        duration_ms: 4,
        warnings: [],
      },
      updated_at: "2026-09-21T00:01:00Z",
    });

    render(<HistoryWorkspace />);
    fireEvent.click(screen.getByRole("tab", { name: /Saved analyses/ }));
    expect(await screen.findByText("Revenue snapshot")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Refresh result" }));

    await waitFor(() => expect(mocks.refreshSavedAnalysis).toHaveBeenCalledWith("saved-1"));
    expect(mocks.createQueryRun).not.toHaveBeenCalled();
    expect(await screen.findByText("Updated saved analysis Revenue snapshot.")).toBeInTheDocument();
  });
});
