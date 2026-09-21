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
  last_refreshed_at: "2026-09-21T00:00:00Z",
  last_error_code: null,
  created_at: "2026-09-21T00:00:00Z",
  updated_at: "2026-09-21T00:00:00Z",
};

test("filters history and reruns a complete question as an independent request", async ({ page }) => {
  let reruns = 0;
  await page.route("**/api/v1/datasources", (route) => route.fulfill({ json: [source] }));
  await page.route("**/api/v1/query-runs?**", (route) =>
    route.fulfill({
      json: {
        items: [
          {
            run_id: "run-1",
            datasource_id: source.id,
            datasource_name: source.name,
            question: "Revenue by category",
            status: "completed",
            row_count: 4,
            duration_ms: 24,
            repair_count: 0,
            visualization_type: "bar",
            error_code: null,
            created_at: "2026-09-21T00:00:00Z",
          },
        ],
        limit: 20,
        total: 1,
        next_cursor: null,
        has_more: false,
      },
    }),
  );
  await page.route("**/api/v1/query-runs", async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    reruns += 1;
    const body = route.request().postDataJSON() as { datasource_id: string; question: string };
    expect(body).toEqual({ datasource_id: source.id, question: "Revenue by category" });
    await route.fulfill({
      json: {
        run_id: "run-2",
        datasource_id: source.id,
        question: body.question,
        status: "completed",
      },
    });
  });

  await page.goto("/history");
  await expect(page.getByRole("heading", { name: "Query history" })).toBeVisible();
  await expect(page.getByText("Revenue by category")).toBeVisible();

  await page.getByLabel("Search questions").fill("revenue");
  await page.getByLabel("Status").selectOption("completed");
  await page.getByRole("button", { name: "Apply filters" }).click();
  await expect(page.getByText("Revenue by category")).toBeVisible();

  await page.getByRole("button", { name: "Rerun as new" }).click();
  await expect(page.getByText("Created independent run run-2.")).toBeAttached();
  expect(reruns).toBe(1);

  for (const width of [375, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    const hasOverflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
    );
    expect(hasOverflow).toBe(false);
  }
});
