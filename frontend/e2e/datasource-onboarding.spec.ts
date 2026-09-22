import { expect, test } from "@playwright/test";

test("onboards and activates the Docker PostgreSQL demo", async ({ page }, testInfo) => {
  const password = process.env.DEMO_READER_PASSWORD;
  if (!password) throw new Error("DEMO_READER_PASSWORD is required for this Docker E2E test");

  await page.goto("/sources");
  const existingSource = page.getByRole("heading", { name: "Docker demo store" });
  await expect(existingSource.or(page.getByText("No data sources yet"))).toBeVisible();
  if (await existingSource.isVisible()) {
    const sourceCard = existingSource.locator("xpath=ancestor::div[contains(@class,'shadow-card')][1]");
    await sourceCard.getByRole("link", { name: "View" }).click();
  } else {
    await page.goto("/sources/new");
    await page.getByLabel("Password").fill(password);
    await page.getByRole("button", { name: "Test connection" }).click();
    await expect(page.getByText("Connection test passed")).toBeVisible();
    await expect(page.getByRole("button", { name: "Save connection" })).toBeEnabled();
    await page.getByRole("button", { name: "Save connection" }).click();
  }

  await expect(page).toHaveURL(/\/sources\/[0-9a-f-]+$/);
  const detailUrl = page.url();
  await expect(page.getByRole("heading", { name: "Docker demo store" })).toBeVisible();
  await expect(page.getByText("public.orders", { exact: true }).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Relationship map" })).toBeVisible();
  await expect(page.getByText("4 relationships across 6 entities.", { exact: false })).toBeVisible();
  const refresh = page.getByRole("button", { name: "Refresh metadata" });
  await refresh.click();
  await expect(refresh).toBeEnabled();
  await expect(page.getByText("Fields profiled locally")).toBeVisible();
  await expect(page.getByText(/Searchable|API key required/)).toBeVisible();
  await expect(page.getByRole("heading", { name: "Semantic manifest" })).toBeVisible();
  await expect(page.getByText("Version and configuration")).toBeVisible();
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export JSON" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/semantic-manifest-v\d+\.json$/);
  await page.locator("summary").filter({ hasText: "public.customers" }).click();
  await expect(page.getByText("Excluded by privacy policy")).toBeVisible();
  await page.getByRole("button", { name: "public.orders" }).click();
  await expect(page.getByRole("status")).toContainText("Selected entity: public.orders");
  await page.getByRole("button", { name: "Arrange / drag" }).click();
  await expect(page.getByText("Drag entities to arrange the map.")).toBeVisible();
  await page.getByRole("button", { name: "Reset layout" }).click();

  const activate = page.getByRole("button", { name: "Activate source" });
  if (await activate.isVisible()) await activate.click();
  await expect(page.getByText("Active", { exact: true })).toBeVisible();

  await page.goto("/sources");
  await expect(page.getByRole("heading", { name: "Docker demo store" })).toBeVisible();

  for (const [name, width] of [["mobile", 375], ["tablet", 768]] as const) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/sources/new");
    const pageWidth = await page.evaluate(() => ({
      viewport: window.innerWidth,
      content: document.documentElement.scrollWidth,
    }));
    expect(pageWidth.content).toBeLessThanOrEqual(pageWidth.viewport);
    await page.screenshot({ path: testInfo.outputPath(`source-form-${name}.png`), fullPage: true });
  }

  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(detailUrl);
  await expect(page.getByRole("heading", { name: "Relationship map" })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath("source-detail-desktop.png"), fullPage: true });

  await page.setViewportSize({ width: 375, height: 900 });
  await page.goto(detailUrl);
  await expect(page.getByRole("heading", { name: "Docker demo store" })).toBeVisible({ timeout: 15000 });
  const detailPageWidth = await page.evaluate(() => ({
    viewport: window.innerWidth,
    content: document.documentElement.scrollWidth,
  }));
  expect(detailPageWidth.content).toBeLessThanOrEqual(detailPageWidth.viewport);
  await page.screenshot({ path: testInfo.outputPath("source-detail-mobile.png"), fullPage: true });
});
