/**
 * Critical path 5: Settings save
 * Change LLM provider, save, hard-reload — value persists.
 */
import { test, expect } from "@playwright/test";

const PROVIDERS = ["openai", "anthropic", "ollama"] as const;

test("settings: change provider, save, reload — value persists", async ({
  page,
}) => {
  await page.goto("/settings");

  // Settings form is visible.
  const form = page
    .locator("[data-testid=settings-form]")
    .or(page.getByRole("form", { name: /llm|settings|provider/i }))
    .or(page.locator("form").first());
  await expect(form).toBeVisible({ timeout: 10_000 });

  // Read the current provider so we can switch to a different one.
  const providerSelect = page
    .locator("[data-testid=provider-select]")
    .or(page.getByRole("combobox", { name: /provider/i }))
    .or(page.getByLabel(/provider/i));

  const currentValue = await providerSelect
    .inputValue()
    .catch(() => providerSelect.textContent());
  const nextProvider =
    PROVIDERS.find((p) => p !== currentValue?.trim()) ?? "openai";

  // Select the new provider.
  await providerSelect.click();
  const option = page
    .getByRole("option", { name: new RegExp(nextProvider, "i") })
    .or(page.locator(`[data-value=${nextProvider}]`))
    .first();
  await expect(option).toBeVisible({ timeout: 5_000 });
  await option.click();

  // Fill required model field if it becomes empty after provider change.
  const modelInput = page
    .locator("[data-testid=model-input]")
    .or(page.getByLabel(/model/i))
    .first();
  if (await modelInput.isVisible()) {
    const modelVal = await modelInput.inputValue();
    if (!modelVal) {
      await modelInput.fill("gpt-4o");
    }
  }

  // Save settings.
  const saveBtn = page
    .locator("[data-testid=settings-save]")
    .or(page.getByRole("button", { name: /save/i }));
  await saveBtn.click();

  // A success indicator appears.
  const successEl = page
    .locator("[data-testid=settings-success]")
    .or(page.getByRole("status").filter({ hasText: /saved|success/i }))
    .or(page.getByText(/saved|settings updated/i).first());
  await expect(successEl).toBeVisible({ timeout: 5_000 });

  // Hard-reload and confirm the provider value was persisted.
  await page.reload();
  await expect(form).toBeVisible({ timeout: 10_000 });

  const savedProvider = page
    .locator("[data-testid=provider-select]")
    .or(page.getByRole("combobox", { name: /provider/i }))
    .or(page.getByLabel(/provider/i));

  const persistedValue = await savedProvider
    .inputValue()
    .catch(() => savedProvider.textContent());
  expect(persistedValue?.toLowerCase()).toContain(nextProvider.toLowerCase());
});
