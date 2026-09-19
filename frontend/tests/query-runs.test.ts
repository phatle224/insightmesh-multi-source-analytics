import { afterEach, describe, expect, it, vi } from "vitest";

import { createQueryRun, getQueryTrace } from "@/lib/query-runs";

afterEach(() => vi.unstubAllGlobals());

describe("query run API", () => {
  it("creates a new independent run with the complete question", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ run_id: "run-1", status: "completed" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetcher);

    await createQueryRun("source-1", "Revenue by category");

    expect(fetcher).toHaveBeenCalledWith(
      "/api/v1/query-runs",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          datasource_id: "source-1",
          question: "Revenue by category",
        }),
      }),
    );
  });

  it("loads the safe trace through the typed client", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ run_id: "run-1", status: "completed", trace: [] }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetcher);

    await getQueryTrace("run-1");

    expect(fetcher).toHaveBeenCalledWith("/api/v1/query-runs/run-1/trace", expect.any(Object));
  });
});
