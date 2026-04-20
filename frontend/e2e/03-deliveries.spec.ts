/**
 * Critical path 3: Delivery list
 * Open /deliveries, filter by status=done, see at least 1 row.
 *
 * The CI seed script inserts webhook_deliveries + pipeline_jobs rows with
 * status 'done' so this filter always returns results.
 */
import { test, expect } from "@playwright/test";

test("deliveries list: filter by done shows results", async ({ page }) => {
  await page.goto("/deliveries");

  // Table is rendered.
  const table = page
    .locator("[data-testid=deliveries-table]")
    .or(page.getByRole("table"));
  await expect(table).toBeVisible({ timeout: 10_000 });

  // Select "done" status using selectOption — the filter is a native <select>.
  await page.locator("[data-testid=status-filter]").selectOption("done");

  // At least one delivery row appears.
  const rows = page
    .locator("[data-testid=delivery-row]")
    .or(page.getByRole("row").filter({ hasText: /done|success/i }));
  await expect(rows.first()).toBeVisible({ timeout: 10_000 });
});
