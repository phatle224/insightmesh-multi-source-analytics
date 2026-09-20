import { afterEach, describe, expect, it, vi } from "vitest";

import { addDashboardWidget, refreshDashboardWidget } from "@/lib/dashboards";

afterEach(() => vi.unstubAllGlobals());

describe("dashboard API", () => {
  it("saves a completed run with the selected compatible chart", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ id: "widget-1", chart_type: "bar" }), {
        status: 201,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetcher);

    await addDashboardWidget("dashboard-1", {
      query_run_id: "run-1",
      title: "Orders by status",
      chart_type: "bar",
    });

    expect(fetcher).toHaveBeenCalledWith(
      "/api/v1/dashboards/dashboard-1/widgets",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          query_run_id: "run-1",
          title: "Orders by status",
          chart_type: "bar",
        }),
      }),
    );
  });

  it("uses the dedicated provider-free refresh endpoint", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ id: "widget-1", status: "ready" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetcher);

    await refreshDashboardWidget("widget-1");

    expect(fetcher).toHaveBeenCalledWith(
      "/api/v1/dashboard-widgets/widget-1/refresh",
      expect.objectContaining({ method: "POST" }),
    );
  });
});
