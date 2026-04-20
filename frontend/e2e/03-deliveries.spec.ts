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

  // Open the status filter and select "done" (labelled "Success" or "Done" in UI).
  const statusFilter = page
    .locator("[data-testid=status-filter]")
    .or(page.getByRole("combobox", { name: /status/i }))
    .or(page.getByLabel(/status/i));
  await statusFilter.click();

  const doneOption = page
    .getByRole("option", { name: /done|success/i })
    .or(page.locator("[data-value=done]"))
    .first();
  await expect(doneOption).toBeVisible({ timeout: 5_000 });
  await doneOption.click();

  // At least one delivery row appears.
  const rows = page
    .locator("[data-testid=delivery-row]")
    .or(page.getByRole("row").filter({ hasText: /done|success/i }));
  await expect(rows.first()).toBeVisible({ timeout: 10_000 });
});
