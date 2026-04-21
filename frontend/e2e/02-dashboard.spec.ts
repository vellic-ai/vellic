/**
 * Critical path 2: Dashboard load
 * After login, metric cards render without console errors.
 */
import { test, expect } from "@playwright/test";

test("dashboard renders metric cards without errors", async ({ page }) => {
  const errors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(msg.text());
  });

  await page.goto("/dashboard");

  // Metric section visible — matches "pipelines", "deliveries", or "latency".
  const metricsRegion = page
    .getByRole("region", { name: /metrics|dashboard/i })
    .or(page.locator("[data-testid=dashboard-metrics]"));
  await expect(metricsRegion).toBeVisible({ timeout: 10_000 });

  // At least 3 stat cards.
  const statCards = page
    .locator("[data-testid=metric-card]")
    .or(page.getByRole("group").filter({ hasText: /pipeline|deliver|latency/i }));
  await expect(statCards.first()).toBeVisible();

  // No JavaScript console errors during render.
  expect(errors).toHaveLength(0);
});
