import { expect, test } from "@playwright/test";

const source = {
  id: "00000000-0000-0000-0000-000000000001",
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

test("runs independent Ask requests and remains responsive", async ({ page }, testInfo) => {
  let runNumber = 0;
  await page.route("**/api/v1/datasources", (route) => route.fulfill({ json: [source] }));
  await page.route("**/api/v1/query-runs", async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    runNumber += 1;
    const request = route.request().postDataJSON() as { question: string };
    const blocked = request.question.toLowerCase().includes("delete");
    const ambiguous = request.question.toLowerCase().includes("best customers");
    const empty = request.question.toLowerCase().includes("no matching");
    const failed = request.question.toLowerCase().includes("forced failure");
    const repaired = request.question.toLowerCase().includes("repaired result");
    const outOfScope = request.question.toLowerCase().includes("weather");
    await route.fulfill({
      json: {
        run_id: `run-${runNumber}`,
        datasource_id: source.id,
        question: request.question,
        status: blocked
          ? "blocked"
          : ambiguous
            ? "clarification_required"
          : failed
            ? "failed"
            : outOfScope
              ? "out_of_scope"
              : "completed",
        generated_query:
          blocked || ambiguous || failed || outOfScope
            ? null
            : {
                sql: "SELECT status, COUNT(*) AS order_count FROM public.orders GROUP BY status",
                expected_columns: ["status", "order_count"],
              },
        validation: blocked || ambiguous || failed || outOfScope ? {} : { ast_valid: true, explain_valid: true },
        result:
          blocked || ambiguous || failed || outOfScope
            ? null
            : {
                columns: [
                  { name: "status", type: "string", semantic_type: "dimension" },
                  { name: "order_count", type: "number", semantic_type: "metric" },
                ],
                rows: empty ? [] : [["completed", 5]],
                row_count: empty ? 0 : 1,
                truncated: repaired,
                duration_ms: 14,
                warnings: [],
              },
        repair_count: repaired ? 1 : 0,
        visualization_type: blocked || ambiguous || failed || outOfScope ? null : "table",
        clarification_suggestions: ambiguous ? ["Top customers by revenue"] : [],
        warnings: [],
        error: blocked
          ? {
              code: "unsafe_request_blocked",
              message: "The request asks to modify datasource data and was blocked",
            }
          : failed
            ? {
                code: "query_execution_failed",
                message: "The query could not be completed within the bounded repair policy",
              }
          : outOfScope
            ? {
                code: "question_out_of_scope",
                message: "This question is outside the analytical scope of the active datasource",
              }
          : null,
        created_at: "2026-09-20T00:00:00Z",
      },
    });
  });
  await page.route("**/api/v1/query-runs/*/trace", (route) =>
    route.fulfill({
      json: {
        run_id: "trace-run",
        status: "completed",
        trace: [
          {
            sequence: 1,
            timestamp: "2026-09-20T00:00:00Z",
            state: "received",
            event: "resolve_datasource",
            outcome: "datasource_ready",
          },
        ],
      },
    }),
  );

  await page.goto("/ask");
  const question = page.getByLabel("Complete analytical question");
  await question.fill("Delete all cancelled orders");
  await page.getByRole("button", { name: "Run question" }).click();
  await expect(page.getByRole("heading", { name: "Request blocked" })).toBeVisible();

  await question.fill("What is the weather today?");
  await page.getByRole("button", { name: "Run question" }).click();
  await expect(page.getByRole("heading", { name: "Question outside datasource scope" })).toBeVisible();

  await question.fill("Who are our best customers?");
  await page.getByRole("button", { name: "Run question" }).click();
  await expect(page.getByRole("heading", { name: "Clarification required" })).toBeVisible();
  await page.getByRole("button", { name: "Top customers by revenue" }).click();
  await expect(page.getByRole("heading", { name: "Query completed" })).toBeVisible();
  await expect(page.getByRole("table")).toContainText("completed");

  await question.fill("No matching orders this quarter");
  await page.getByRole("button", { name: "Run question" }).click();
  await expect(page.getByRole("heading", { name: "No matching rows" })).toBeVisible();

  await question.fill("Forced failure scenario");
  await page.getByRole("button", { name: "Run question" }).click();
  await expect(page.getByRole("heading", { name: "Query could not be completed" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Retry as new run" })).toBeVisible();

  await question.fill("Repaired result by status");
  await page.getByRole("button", { name: "Run question" }).click();
  await expect(page.getByRole("heading", { name: "Query completed" })).toBeVisible();
  await expect(page.getByText(/configured row limit/i)).toBeVisible();

  for (const [name, width] of [["mobile", 375], ["tablet", 768], ["desktop", 1440]] as const) {
    await page.setViewportSize({ width, height: name === "desktop" ? 1000 : 900 });
    await page.evaluate(() => {
      (document.activeElement as HTMLElement | null)?.blur();
      window.scrollTo(0, 0);
    });
    const pageWidth = await page.evaluate(() => ({
      viewport: window.innerWidth,
      content: document.documentElement.scrollWidth,
    }));
    expect(pageWidth.content).toBeLessThanOrEqual(pageWidth.viewport);
    await page.screenshot({ path: testInfo.outputPath(`ask-${name}.png`), fullPage: true });
  }
});
