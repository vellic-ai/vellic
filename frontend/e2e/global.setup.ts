import { test as setup, expect, request } from "@playwright/test";
import path from "path";
import fs from "fs";

const authFile = path.join(__dirname, "../playwright/.auth/state.json");

setup("authenticate and seed", async ({ page }) => {
  const apiBase =
    process.env["E2E_API_BASE"] ??
    (process.env["E2E_BASE_URL"]
      ? process.env["E2E_BASE_URL"].replace(/:5173/, ":8001")
      : "http://localhost:8001");

  const password = process.env["E2E_ADMIN_PASSWORD"] ?? "vellic_dev";

  // Ensure the admin password is set (no-op if already configured).
  const apiCtx = await request.newContext({ baseURL: apiBase });
  await apiCtx.put("/admin/auth/setup", { data: { password } });

  // Authenticate via the login UI so the session cookie is stored.
  await page.goto("/login");
  await page.fill("#password", password);
  await page.getByRole("button", { name: /sign in/i }).click();

  // Expect redirect to dashboard after successful login.
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 10_000 });

  // Persist auth state for all subsequent test projects.
  fs.mkdirSync(path.dirname(authFile), { recursive: true });
  await page.context().storageState({ path: authFile });
  await apiCtx.dispose();
});
