/**
 * Critical path 6: First-run setup onboarding
 * No password set → navigate / → land on /setup → fill password → auto-login → /dashboard.
 */
import { test, expect, request } from "@playwright/test";

test.use({ storageState: { cookies: [], origins: [] } });

test("first-run setup: / redirects to /setup, set password auto-logs in", async ({
  page,
}) => {
  const apiBase =
    process.env["E2E_API_BASE"] ??
    (process.env["E2E_BASE_URL"]
      ? process.env["E2E_BASE_URL"].replace(/:5173/, ":8001")
      : "http://localhost:8001");

  const newPassword = "vellic_setup_test";

  // Drop the existing password so setup_required becomes true.
  // Requires VELLIC_TEST_MODE=true on the backend (set in CI; skips locally if absent).
  const apiCtx = await request.newContext({ baseURL: apiBase });
  const resetRes = await apiCtx.delete("/admin/auth/setup/reset").catch(() => null);
  await apiCtx.dispose();

  if (!resetRes || !resetRes.ok()) {
    test.skip(true, "Backend test-reset endpoint unavailable (VELLIC_TEST_MODE not set)");
    return;
  }

  // Navigate to root — AuthGuard should redirect to /setup because setup_required=true.
  await page.goto("/");

  // Should land on /setup.
  await expect(page).toHaveURL(/\/setup/, { timeout: 10_000 });

  // Setup form is visible.
  await expect(page.getByRole("button", { name: /set password/i })).toBeVisible();

  // Fill both fields.
  await page.fill("#password", newPassword);
  await page.fill("#confirm", newPassword);
  await page.getByRole("button", { name: /set password/i }).click();

  // After setup + auto-login, should reach dashboard.
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 10_000 });
});

test("/setup redirects to /login when setup already done", async ({ page }) => {
  // global.setup always runs first and sets a password, so setup_required=false.
  await page.goto("/setup");
  await expect(page).toHaveURL(/\/login/, { timeout: 10_000 });
});
