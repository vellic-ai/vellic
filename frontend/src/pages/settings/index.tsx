import { useState, useEffect } from "react";
import { useNavigate } from "react-router";
import { Shell, PageHeader, Skeleton } from "@/components/Shell";
import { Button } from "@/components/ui/button";
import { Icons, Spinner } from "@/components/icons";
import { useLLMSettings, useSaveLLMSettings, useRepos } from "@/api";
import { useToast } from "@/lib/toast";
import { cn } from "@/lib/utils";

const CLOUD_PROVIDERS = ["openai", "anthropic", "claude_code"];
const PROVIDER_LABELS: Record<string, string> = {
  ollama: "Ollama",
  vllm: "vLLM",
  openai: "OpenAI",
  anthropic: "Anthropic",
  claude_code: "Claude Code",
};
const PROVIDER_ORDER = ["ollama", "vllm", "openai", "anthropic", "claude_code"];

function isCloud(kind: string) {
  return CLOUD_PROVIDERS.includes(kind);
}

export default function SettingsPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const { data: llmData, isLoading } = useLLMSettings();
  const { data: repos } = useRepos();
  const saveLLM = useSaveLLMSettings();

  const [provider, setProvider] = useState("");
  const [model, setModel] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [keyEdited, setKeyEdited] = useState(false);
  const [showKey, setShowKey] = useState(false);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (llmData) {
      setProvider(llmData.provider ?? "ollama");
      setModel(llmData.model ?? "");
      setBaseUrl(llmData.base_url ?? "");
      setApiKey("");
      setKeyEdited(false);
    }
  }, [llmData]);

  const reposUsingProvider = (repos?.items ?? []).filter((r) => r.provider === provider);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSaved(false);
    saveLLM.mutate(
      {
        provider,
        base_url: isCloud(provider) ? null : (baseUrl || null),
        model,
        api_key: keyEdited ? (apiKey || null) : null,
        extra: llmData?.extra ?? {},
      },
      {
        onSuccess: () => {
          setSaving(false);
          setSaved(true);
          setKeyEdited(false);
          setApiKey("");
          toast.success(`${PROVIDER_LABELS[provider] ?? provider} settings saved`);
          setTimeout(() => setSaved(false), 4000);
        },
        onError: (err) => {
          setSaving(false);
          toast.error(err.message || "Save failed");
        },
      },
    );
  };

  return (
    <Shell>
      <PageHeader
        title="Providers"
        subtitle="Credentials & endpoints. Choose models per-repository under Repositories."
        action={
          <Button size="sm" variant="default" onClick={() => navigate("/repos")}>
            <Icons.repos size={13} />
            Manage repositories
          </Button>
        }
      />

      {isLoading ? (
        <div className="bg-surface border border-border rounded p-5 flex flex-col gap-3">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-[34px] w-full" />
          <Skeleton className="h-[34px] w-full" />
        </div>
      ) : (
        <form
          data-testid="settings-form"
          aria-label="LLM Settings"
          onSubmit={handleSave}
          className="bg-surface border border-border rounded p-5 flex flex-col gap-4"
        >
          {/* Provider */}
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-text-muted" htmlFor="provider-select">
              Provider
            </label>
            <select
              id="provider-select"
              data-testid="provider-select"
              aria-label="Provider"
              value={provider}
              onChange={(e) => {
                setProvider(e.target.value);
                setModel("");
                setBaseUrl("");
                setApiKey("");
                setKeyEdited(false);
                setSaved(false);
              }}
              className={cn(
                "h-[34px] w-full rounded border bg-input-bg border-border text-text px-3 text-sm",
                "transition-[border-color,box-shadow] duration-[120ms]",
                "focus:border-accent focus:shadow-[0_0_0_3px_rgba(108,99,255,0.18)] focus:outline-none",
              )}
            >
              {PROVIDER_ORDER.map((p) => (
                <option key={p} value={p}>
                  {PROVIDER_LABELS[p]}
                </option>
              ))}
            </select>
          </div>

          {/* Model */}
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-text-muted" htmlFor="model-input">
              Model
            </label>
            <input
              id="model-input"
              data-testid="model-input"
              aria-label="Model"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder={
                provider === "ollama"
                  ? "llama3.2"
                  : provider === "openai"
                    ? "gpt-4o"
                    : provider === "anthropic"
                      ? "claude-3-5-sonnet-20241022"
                      : "model-name"
              }
              className={cn(
                "h-[34px] w-full rounded border bg-input-bg border-border text-text px-3 text-sm font-mono",
                "transition-[border-color,box-shadow] duration-[120ms]",
                "focus:border-accent focus:shadow-[0_0_0_3px_rgba(108,99,255,0.18)] focus:outline-none",
              )}
            />
          </div>

          {/* Cloud: API key / Self-hosted: Base URL */}
          {isCloud(provider) ? (
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-text-muted" htmlFor="api-key-input">
                API Key
              </label>
              <div className="relative">
                <input
                  id="api-key-input"
                  aria-label={`${PROVIDER_LABELS[provider] ?? provider} API key`}
                  type={showKey ? "text" : "password"}
                  value={keyEdited ? apiKey : "••••••••••••••••••••••••"}
                  onFocus={() => {
                    if (!keyEdited) {
                      setKeyEdited(true);
                      setApiKey("");
                    }
                  }}
                  onChange={(e) => {
                    setKeyEdited(true);
                    setApiKey(e.target.value);
                  }}
                  placeholder="sk-…"
                  className={cn(
                    "h-[34px] w-full rounded border bg-input-bg border-border text-text px-3 pr-10 text-sm font-mono",
                    "transition-[border-color,box-shadow] duration-[120ms]",
                    "focus:border-accent focus:shadow-[0_0_0_3px_rgba(108,99,255,0.18)] focus:outline-none",
                  )}
                />
                <button
                  type="button"
                  className="absolute right-1 top-1 inline-flex items-center justify-center w-7 h-7 rounded text-text-muted hover:text-text transition-colors"
                  onClick={() => setShowKey((s) => !s)}
                  aria-label={showKey ? "Hide key" : "Reveal key"}
                >
                  {showKey ? <Icons.eyeOff size={14} /> : <Icons.eye size={14} />}
                </button>
              </div>
              <p className="text-xs text-text-muted">
                {keyEdited ? "Key will be written on save." : "Stored encrypted. Type to replace."}
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-text-muted" htmlFor="base-url-input">
                Base URL
              </label>
              <input
                id="base-url-input"
                aria-label={`${PROVIDER_LABELS[provider] ?? provider} base URL`}
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                placeholder={provider === "ollama" ? "http://ollama:11434" : "http://vllm:8000/v1"}
                className={cn(
                  "h-[34px] w-full rounded border bg-input-bg border-border text-text px-3 text-sm font-mono",
                  "transition-[border-color,box-shadow] duration-[120ms]",
                  "focus:border-accent focus:shadow-[0_0_0_3px_rgba(108,99,255,0.18)] focus:outline-none",
                )}
              />
              <p className="text-xs text-text-muted">OpenAI-compatible endpoint.</p>
            </div>
          )}

          {/* Repos using this provider */}
          {reposUsingProvider.length > 0 && (
            <div className="p-2.5 bg-input-bg rounded text-xs">
              <div className="text-text-muted mb-1.5">Used by</div>
              <div className="flex flex-wrap gap-1.5">
                {reposUsingProvider.map((r) => (
                  <span key={r.id} className="font-mono px-2 py-0.5 bg-surface-2 rounded text-[11.5px]">
                    {r.slug} <span className="text-text-muted">· {r.model}</span>
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Footer */}
          <div className="flex items-center justify-between pt-2 border-t border-border">
            <div>
              {saved && (
                <span
                  data-testid="settings-success"
                  role="status"
                  className="text-sm text-success inline-flex items-center gap-1"
                >
                  <Icons.check size={14} /> Saved
                </span>
              )}
            </div>
            <Button
              type="submit"
              data-testid="settings-save"
              variant="primary"
              size="sm"
              disabled={saving}
            >
              {saving && <Spinner size={11} />}
              Save
            </Button>
          </div>
        </form>
      )}
    </Shell>
  );
}
