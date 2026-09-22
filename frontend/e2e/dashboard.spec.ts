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
  entity_count: 1,
  relationship_count: 0,
  profile_count: 2,
  semantic_term_count: 2,
  metric_count: 1,
  embedding_count: 1,
  pii_excluded_count: 0,
  semantic_status: "ready",
  semantic_error_code: null,
  last_refreshed_at: "2026-09-20T00:00:00Z",
  last_error_code: null,
  created_at: "2026-09-20T00:00:00Z",
  updated_at: "2026-09-20T00:00:00Z",
};

const result = {
  columns: [
    { name: "status", type: "string", semantic_type: "dimension" },
    { name: "orders", type: "number", semantic_type: "metric" },
  ],
  rows: [["paid", 8], ["new", 3]],
  row_count: 2,
  truncated: false,
  duration_ms: 8,
  warnings: [],
};

function widget(id: string, position: number, title: string) {
  return {
    id,
    dashboard_id: "dashboard-1",
    datasource_id: source.id,
    source_query_run_id: "run-1",
    title,
    question: "Orders by status",
    validated_query: { sql: "SELECT status, COUNT(*) AS orders FROM public.orders GROUP BY status", expected_columns: ["status", "orders"] },
    query_type: "sql",
    chart_type: "bar",
    chart_config: { dimension_key: "status", metric_key: "orders" },
    compatible_chart_types: ["table", "bar", "pie"],
    position,
    result,
    status: "ready",
    row_count: 2,
    duration_ms: 8,
    last_refreshed_at: "2026-09-20T00:00:00Z",
    error: null,
    created_at: "2026-09-20T00:00:00Z",
    updated_at: "2026-09-20T00:00:00Z",
  };
}

test("creates and manages a responsive provider-free dashboard", async ({ page }, testInfo) => {
  let widgets = [widget("widget-1", 0, "Orders by status"), widget("widget-2", 1, "Secondary view")];
  await page.route("**/api/v1/datasources", (route) => route.fulfill({ json: [source] }));
  await page.route("**/api/v1/dashboards", async (route) => {
    if (route.request().method() === "POST") {
      return route.fulfill({ status: 201, json: { id: "dashboard-2", name: "Weekly review", description: null, widget_count: 0, created_at: "2026-09-20T00:00:00Z", updated_at: "2026-09-20T00:00:00Z" } });
    }
    return route.fulfill({ json: [{ id: "dashboard-1", name: "Operations", description: "Verified order metrics", widget_count: 2, created_at: "2026-09-20T00:00:00Z", updated_at: "2026-09-20T00:00:00Z" }] });
  });
  await page.route("**/api/v1/dashboards/dashboard-1", (route) => route.fulfill({ json: { id: "dashboard-1", name: "Operations", description: "Verified order metrics", widget_count: widgets.length, created_at: "2026-09-20T00:00:00Z", updated_at: "2026-09-20T00:00:00Z", widgets } }));
  await page.route("**/api/v1/dashboard-widgets/*", async (route) => {
    const id = route.request().url().split("/").at(-1)!;
    if (route.request().method() === "DELETE") {
      widgets = widgets.filter((item) => item.id !== id).map((item, index) => ({ ...item, position: index }));
      return route.fulfill({ status: 204, body: "" });
    }
    const payload = route.request().postDataJSON() as { title?: string; chart_type?: "table" | "bar"; position?: number };
    const current = widgets.find((item) => item.id === id)!;
    if (payload.position !== undefined) {
      widgets = widgets.filter((item) => item.id !== id);
      widgets.splice(payload.position, 0, current);
      widgets = widgets.map((item, index) => ({ ...item, position: index }));
    }
    const updated = { ...current, ...payload };
    widgets = widgets.map((item) => item.id === id ? { ...item, ...updated } : item);
    return route.fulfill({ json: updated });
  });
  await page.route("**/api/v1/dashboard-widgets/*/refresh", async (route) => {
    const id = route.request().url().split("/").at(-2)!;
    const current = widgets.find((item) => item.id === id)!;
    const refreshed = { ...current, duration_ms: 12, last_refreshed_at: "2026-09-20T01:00:00Z" };
    widgets = widgets.map((item) => item.id === id ? refreshed : item);
    return route.fulfill({ json: refreshed });
  });

  await page.goto("/dashboards");
  await page.getByLabel("Dashboard name").fill("Weekly review");
  await page.getByRole("button", { name: "Create dashboard" }).click();
  await expect(page.getByRole("heading", { name: "Weekly review" })).toBeVisible();

  await page.getByRole("heading", { name: "Operations" }).click();
  await expect(page.getByRole("heading", { name: "Operations" })).toBeVisible();
  await page.getByText("View exact rows").first().click();
  await expect(page.getByRole("table").first()).toContainText("paid");

  await page.getByRole("button", { name: "Move widget down" }).first().click();
  await page.getByRole("button", { name: "Refresh" }).first().click();
  await expect(page.getByText("12 ms").first()).toBeVisible();

  for (const [name, width] of [["mobile", 375], ["desktop", 1440]] as const) {
    await page.setViewportSize({ width, height: 900 });
    await expect.poll(() => page.locator(".recharts-wrapper").first().evaluate((element) => element.clientWidth)).toBeGreaterThan(name === "desktop" ? 800 : 240);
    if (name === "mobile") {
      await expect.poll(() => page.locator('input[name="title"]').first().evaluate((element) => element.clientWidth)).toBeGreaterThan(200);
    }
    const dimensions = await page.evaluate(() => ({ viewport: window.innerWidth, content: document.documentElement.scrollWidth }));
    expect(dimensions.content).toBeLessThanOrEqual(dimensions.viewport);
    await page.screenshot({ path: testInfo.outputPath(`dashboard-${name}.png`), fullPage: true });
  }
});
