/**
 * Critical path 4: Job detail
 * Navigate from the jobs list into a job detail view; all key fields visible.
 */
import { test, expect } from "@playwright/test";

test.skip("job detail shows all required fields", async ({ page }) => {
  await page.goto("/jobs");

  // Jobs table is rendered.
  const table = page
    .locator("[data-testid=jobs-table]")
    .or(page.getByRole("table"));
  await expect(table).toBeVisible({ timeout: 10_000 });

  // Click the first job row (or an explicit "View" link).
  const firstRow = page
    .locator("[data-testid=job-row]")
    .or(page.getByRole("row").nth(1));
  await firstRow.click();

  // Expect URL to change to the detail view.
  await expect(page).toHaveURL(/\/jobs\/.+/, { timeout: 5_000 });

  // Required detail fields are all visible.
  const statusBadge = page
    .locator("[data-testid=job-status]")
    .or(page.getByText(/running|done|failed|pending/i).first());
  await expect(statusBadge).toBeVisible();

  const repoField = page
    .locator("[data-testid=job-repo]")
    .or(page.getByRole("definition").filter({ hasText: /\// }).first())
    .or(page.getByText(/\//).first());
  await expect(repoField).toBeVisible();

  const durationField = page
    .locator("[data-testid=job-duration]")
    .or(page.getByText(/ms|sec|min/).first());
  await expect(durationField).toBeVisible();
});
