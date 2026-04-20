/**
 * Critical path 1: Login
 * Valid credentials → redirect to /dashboard.
 */
import { test, expect } from "@playwright/test";

// This test runs without stored auth — use a fresh browser context.
test.use({ storageState: { cookies: [], origins: [] } });

test("valid login redirects to dashboard", async ({ page }) => {
  const password = process.env["E2E_ADMIN_PASSWORD"] ?? "vellic_dev";

  await page.goto("/login");

  // Page renders the login card.
  await expect(page.getByRole("heading", { name: /vellic/i })).toBeVisible();

  // Fill credentials and submit.
  await page.fill("#password", password);
  await page.getByRole("button", { name: /sign in/i }).click();

  // Successful login navigates to dashboard.
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 10_000 });
});

test("wrong password shows error", async ({ page }) => {
  await page.goto("/login");
  await page.fill("#password", "wrong-password-xyz");
  await page.getByRole("button", { name: /sign in/i }).click();

  // Should stay on login and show an error message.
  await expect(page).toHaveURL(/\/login|^\/$/, { timeout: 5_000 });
  await expect(
    page.getByRole("alert").or(page.locator("[data-testid=login-error]"))
  ).toBeVisible({ timeout: 5_000 });
});
