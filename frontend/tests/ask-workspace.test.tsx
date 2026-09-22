import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AskWorkspace, RUN_STATUS_PRESENTATION } from "@/components/ask-workspace";
import type { DatasourceSummary } from "@/lib/datasources";
import type { QueryRun, QueryTrace } from "@/lib/query-runs";

const mocks = vi.hoisted(() => ({
  createQueryRun: vi.fn(),
  getQueryTrace: vi.fn(),
  useDatasources: vi.fn(),
}));

vi.mock("@/lib/query-runs", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/query-runs")>()),
  createQueryRun: mocks.createQueryRun,
  getQueryTrace: mocks.getQueryTrace,
}));

vi.mock("@/components/datasource-provider", () => ({
  useDatasources: mocks.useDatasources,
}));

const activeSource: DatasourceSummary = {
  id: "source-1",
  name: "Docker demo store",
  source_type: "postgresql",
  database_name: "insightmesh_demo",
  safe_host: "demo-postgres",
  port: 5432,
  ssl_mode: "disable",
  allowed_schemas: ["public"],
  status: "ready",
  is_active: true,
  entity_count: 6,
  relationship_count: 4,
  profile_count: 20,
  semantic_term_count: 64,
  metric_count: 19,
  embedding_count: 6,
  pii_excluded_count: 1,
  semantic_status: "ready",
  semantic_error_code: null,
  last_refreshed_at: "2026-09-20T00:00:00Z",
  last_error_code: null,
  created_at: "2026-09-20T00:00:00Z",
  updated_at: "2026-09-20T00:00:00Z",
};

const completedRun: QueryRun = {
  run_id: "run-completed",
  datasource_id: activeSource.id,
  question: "Order count by status",
  status: "completed",
  generated_query: {
    sql: "SELECT status, COUNT(*) AS order_count FROM public.orders GROUP BY status",
    expected_columns: ["status", "order_count"],
  },
  validation: { ast_valid: true, explain_valid: true },
  result: {
    columns: [
      { name: "status", type: "string", semantic_type: "dimension" },
      { name: "order_count", type: "number", semantic_type: "metric" },
    ],
    rows: [["completed", 5]],
    row_count: 1,
    truncated: false,
    duration_ms: 14,
    warnings: [],
  },
  repair_count: 0,
  provider_call_count: 2,
  visualization_type: "table",
  clarification_suggestions: [],
  warnings: [],
  error: null,
  created_at: "2026-09-20T00:00:00Z",
};

const completedTrace: QueryTrace = {
  run_id: completedRun.run_id,
  status: "completed",
  trace: [
    {
      sequence: 1,
      timestamp: "2026-09-20T00:00:00Z",
      state: "received",
      event: "resolve_datasource",
      outcome: "datasource_ready",
      duration_ms: 2,
      details: { provider_call_count: 0 },
    },
    {
      sequence: 2,
      timestamp: "2026-09-20T00:00:01Z",
      state: "generate_query",
      event: "generate_query",
      outcome: "structured_output_valid",
      duration_ms: 120,
      details: {
        provider: "gemini",
        model: "gemini-2.5-flash",
        fallback_used: false,
        provider_call_count: 2,
        repair_count: 0,
      },
    },
  ],
};

beforeEach(() => {
  vi.clearAllMocks();
  mocks.useDatasources.mockReturnValue({
    sources: [activeSource],
    activeSource,
    loading: false,
    error: null,
    refresh: vi.fn(),
  });
  mocks.getQueryTrace.mockResolvedValue(completedTrace);
});

describe("Ask workspace", () => {
  it("defines explicit copy for every runtime status", () => {
    expect(Object.keys(RUN_STATUS_PRESENTATION)).toHaveLength(13);
    expect(RUN_STATUS_PRESENTATION.repair_query.label).toBe("Repairing query");
    expect(RUN_STATUS_PRESENTATION.out_of_scope.tone).toBe("warning");
    expect(RUN_STATUS_PRESENTATION.blocked.tone).toBe("danger");
  });

  it("blocks submission and links to Sources when no datasource is active", () => {
    mocks.useDatasources.mockReturnValue({
      sources: [],
      activeSource: null,
      loading: false,
      error: null,
      refresh: vi.fn(),
    });

    render(<AskWorkspace />);

    expect(screen.getByRole("heading", { name: "Choose a ready datasource first" })).toBeVisible();
    expect(screen.getByRole("link", { name: "Go to Sources" })).toHaveAttribute("href", "/sources");
    expect(screen.queryByLabelText("Complete analytical question")).not.toBeInTheDocument();
  });

  it("submits a complete question and renders SQL, trace, and verified rows", async () => {
    mocks.createQueryRun.mockResolvedValue(completedRun);
    render(<AskWorkspace />);

    fireEvent.change(screen.getByLabelText("Complete analytical question"), {
      target: { value: "Order count by status" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Run question" }));

    expect(await screen.findByRole("heading", { name: "Query completed" })).toBeVisible();
    fireEvent.click(screen.getByText("Technical details"));
    expect(screen.getByText("Generated PostgreSQL")).toBeVisible();
    expect(screen.getByText("Execution trace")).toBeVisible();
    fireEvent.click(screen.getByText("Execution trace"));
    expect(screen.getByText("2 provider calls")).toBeVisible();
    fireEvent.click(screen.getByText("Safe evidence (5)"));
    expect(screen.getByText("gemini-2.5-flash")).toBeVisible();
    expect(screen.getByRole("table")).toHaveTextContent("completed");
    expect(mocks.createQueryRun).toHaveBeenCalledWith("source-1", "Order count by status");
    expect(mocks.getQueryTrace).toHaveBeenCalledWith("run-completed");
  });

  it("submits a clarification choice as a new complete request", async () => {
    const ambiguousRun: QueryRun = {
      ...completedRun,
      run_id: "run-ambiguous",
      status: "clarification_required",
      generated_query: null,
      result: null,
      clarification_suggestions: ["Top customers by revenue"],
    };
    mocks.createQueryRun
      .mockResolvedValueOnce(ambiguousRun)
      .mockResolvedValueOnce(completedRun);

    render(<AskWorkspace />);
    fireEvent.change(screen.getByLabelText("Complete analytical question"), {
      target: { value: "Who are our best customers?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Run question" }));
    fireEvent.click(await screen.findByRole("button", { name: "Top customers by revenue" }));

    await waitFor(() =>
      expect(mocks.createQueryRun).toHaveBeenLastCalledWith(
        "source-1",
        "Top customers by revenue",
      ),
    );
  });

  it("renders a blocked state without an execute or retry action", async () => {
    mocks.createQueryRun.mockResolvedValue({
      ...completedRun,
      run_id: "run-blocked",
      status: "blocked",
      generated_query: null,
      result: null,
      error: {
        code: "unsafe_request_blocked",
        message: "The request asks to modify datasource data and was blocked",
      },
    });

    render(<AskWorkspace />);
    fireEvent.change(screen.getByLabelText("Complete analytical question"), {
      target: { value: "Delete all cancelled orders" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Run question" }));

    expect(await screen.findByRole("heading", { name: "Request blocked" })).toBeVisible();
    expect(screen.queryByRole("button", { name: /retry/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });
});
