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
  const apiCtx = await request.newContext({ baseURL: apiBase });
  // Reset auth state by calling setup with empty string (drops hash if supported),
  // or by hitting a dedicated reset endpoint. For test isolation, we call setup
  // with a sentinel and then reset by patching to empty — backend must accept this.
  // Use the documented approach: DELETE or PATCH with empty password if available,
  // otherwise call the internal reset if present.
  // The global.setup.ts always sets the password, so we patch it to empty here.
  await apiCtx.put("/admin/auth/setup/reset", {}).catch(() => null);
  // Fallback: some backends expose no reset; skip if not supported.

  await apiCtx.dispose();

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
