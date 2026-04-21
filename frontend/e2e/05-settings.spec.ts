/**
 * Critical path 5: Settings save
 * Change LLM provider, save, hard-reload — value persists.
 */
import { test, expect } from "@playwright/test";

// Label→value map mirrors PROVIDER_LABELS in settings/index.tsx.
const LABEL_TO_VALUE: Record<string, string> = {
  Ollama: "ollama",
  "vLLM": "vllm",
  OpenAI: "openai",
  Anthropic: "anthropic",
  "Claude Code": "claude_code",
};

test("settings: change provider, save, reload — value persists", async ({
  page,
}) => {
  await page.goto("/settings");

  // Settings form is visible (seeded LLM row guarantees form renders, not skeleton).
  const form = page
    .locator("[data-testid=settings-form]")
    .or(page.getByRole("form", { name: /llm|settings|provider/i }))
    .or(page.locator("form").first());
  await expect(form).toBeVisible({ timeout: 10_000 });

  // Read current provider value from the Radix SelectTrigger's text content.
  // The trigger renders the selected label ("Ollama", "OpenAI", etc.) as textContent.
  const trigger = page.locator("[data-testid=provider-select]");
  const currentLabel = ((await trigger.textContent()) ?? "").trim();
  const currentValue = LABEL_TO_VALUE[currentLabel] ?? "ollama";

  // Pick a target that differs from the current one.
  const targetValue = currentValue === "openai" ? "ollama" : "openai";
  const targetLabel = targetValue === "openai" ? "OpenAI" : "Ollama";

  // Open the Radix Select dropdown and click the target option.
  await trigger.click();
  const option = page.getByRole("option", { name: new RegExp(targetLabel, "i") }).first();
  await expect(option).toBeVisible({ timeout: 5_000 });
  await option.click();

  // Fill model field — it clears when provider changes.
  const modelInput = page.locator("[data-testid=model-input]");
  if (await modelInput.isVisible()) {
    const modelVal = await modelInput.inputValue();
    if (!modelVal) {
      await modelInput.fill(targetValue === "openai" ? "gpt-4o" : "llama3.2");
    }
  }

  // Save.
  await page.locator("[data-testid=settings-save]").click();
  await expect(page.locator("[data-testid=settings-success]")).toBeVisible({ timeout: 5_000 });

  // Hard-reload and confirm the provider persisted.
  await page.reload();
  await expect(form).toBeVisible({ timeout: 10_000 });

  const savedLabel = ((await page.locator("[data-testid=provider-select]").textContent()) ?? "").trim();
  expect(savedLabel.toLowerCase()).toContain(targetLabel.toLowerCase());
});
