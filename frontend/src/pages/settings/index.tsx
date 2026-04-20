import { useState } from "react";
import { useNavigate } from "react-router";
import { Shell, PageHeader, Skeleton } from "@/components/Shell";
import { Badge } from "@/components/ui/badge";
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

interface ProviderState {
  base_url?: string;
  api_key_raw?: string;
  key_edited?: boolean;
  base_dirty?: boolean;
}

function ProviderCard({
  kind,
  reposUsing,
  onSave,
}: {
  kind: string;
  reposUsing: { id: string; full_name: string; model: string }[];
  onSave: (kind: string, patch: ProviderState) => void;
}) {
  const cloud = isCloud(kind);
  const [localState, setLocalState] = useState<ProviderState>({
    base_url: "",
    api_key_raw: "",
    key_edited: false,
    base_dirty: false,
  });
  const [showKey, setShowKey] = useState(false);
  const [saving, setSaving] = useState(false);
  const toast = useToast();

  const dirty = localState.key_edited || localState.base_dirty;

  const handleSave = () => {
    setSaving(true);
    onSave(kind, localState);
    setTimeout(() => {
      setSaving(false);
      setLocalState((s) => ({ ...s, key_edited: false, base_dirty: false, api_key_raw: "" }));
      toast.success(`${PROVIDER_LABELS[kind]} saved`);
    }, 600);
  };

  return (
    <section className="bg-surface border border-border rounded p-5">
      <div className="flex items-center gap-3 mb-3.5">
        <div
          className={cn(
            "w-8 h-8 rounded-lg inline-flex items-center justify-center border shrink-0",
            cloud
              ? "bg-warning-bg border-warning-border text-warning-text"
              : "bg-surface-2 border-border text-text-muted",
          )}
        >
          {cloud ? <Icons.warn size={15} /> : <Icons.llm size={15} />}
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-semibold">{PROVIDER_LABELS[kind]}</div>
          <div className="text-xs text-text-muted mt-0.5">
            {cloud ? "Cloud · source code leaves your network" : "Self-hosted · stays in your infra"}
          </div>
        </div>
        {reposUsing.length > 0 ? (
          <Badge variant="info" className="text-xs shrink-0">
            <span className="w-1.5 h-1.5 rounded-full bg-success inline-block" />
            {reposUsing.length} {reposUsing.length === 1 ? "repo" : "repos"}
          </Badge>
        ) : (
          <Badge variant="default" className="text-xs shrink-0">
            <span className="w-1.5 h-1.5 rounded-full bg-text-muted inline-block" /> unused
          </Badge>
        )}
      </div>

      {cloud ? (
        <div className="mb-0">
          <label className="block text-[12.5px] text-text-muted font-medium mb-1.5">
            API Key
          </label>
          <div className="relative">
            <input
              className={cn(
                "h-[34px] w-full rounded border bg-input-bg border-border text-text px-3 pr-10 text-sm font-mono",
                "transition-[border-color,box-shadow] duration-[120ms]",
                "focus:border-accent focus:shadow-[0_0_0_3px_rgba(108,99,255,0.18)] focus:outline-none",
              )}
              type={showKey ? "text" : "password"}
              value={localState.key_edited ? (localState.api_key_raw ?? "") : "••••••••••••••••••••••••"}
              onFocus={() => {
                if (!localState.key_edited) {
                  setLocalState((s) => ({ ...s, key_edited: true, api_key_raw: "" }));
                }
              }}
              onChange={(e) =>
                setLocalState((s) => ({ ...s, key_edited: true, api_key_raw: e.target.value }))
              }
              placeholder="sk-…"
              aria-label={`${PROVIDER_LABELS[kind]} API key`}
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
          <p className="text-xs text-text-muted mt-1.5">
            {localState.key_edited ? "Key will be written on save." : "Stored encrypted. Type to replace."}
          </p>
        </div>
      ) : (
        <div className="mb-0">
          <label className="block text-[12.5px] text-text-muted font-medium mb-1.5">
            Base URL
          </label>
          <input
            className={cn(
              "h-[34px] w-full rounded border bg-input-bg border-border text-text px-3 text-sm font-mono",
              "transition-[border-color,box-shadow] duration-[120ms]",
              "focus:border-accent focus:shadow-[0_0_0_3px_rgba(108,99,255,0.18)] focus:outline-none",
            )}
            value={localState.base_url ?? ""}
            onChange={(e) =>
              setLocalState((s) => ({ ...s, base_url: e.target.value, base_dirty: true }))
            }
            placeholder={kind === "ollama" ? "http://ollama:11434" : "http://vllm:8000/v1"}
            aria-label={`${PROVIDER_LABELS[kind]} base URL`}
          />
          <p className="text-xs text-text-muted mt-1.5">OpenAI-compatible endpoint.</p>
        </div>
      )}

      {reposUsing.length > 0 && (
        <div className="mt-3.5 p-2.5 bg-input-bg rounded text-xs">
          <div className="text-text-muted mb-1.5">Used by</div>
          <div className="flex flex-wrap gap-1.5">
            {reposUsing.map((r) => (
              <span
                key={r.id}
                className="font-mono px-2 py-0.5 bg-surface-2 rounded text-[11.5px]"
              >
                {r.full_name} <span className="text-text-muted">· {r.model}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="flex justify-end mt-4 pt-3.5 border-t border-border">
        <Button
          size="sm"
          variant="primary"
          onClick={handleSave}
          disabled={saving || !dirty}
        >
          {saving && <Spinner size={11} />}
          Save
        </Button>
      </div>
    </section>
  );
}

export default function SettingsPage() {
  const navigate = useNavigate();
  const { data: llmData, isLoading } = useLLMSettings();
  const { data: repos } = useRepos();
  const saveLLM = useSaveLLMSettings();

  const reposUsing = (kind: string) =>
    (repos?.items ?? [])
      .filter((r) => r.provider === kind)
      .map((r) => ({ id: r.id, full_name: r.slug, model: r.model ?? "" }));

  const handleSave = (_kind: string, _state: ProviderState) => {
    if (!llmData) return;
    saveLLM.mutate(llmData as import("@/api").LLMSettingsIn);
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
        <div className="flex flex-col gap-3.5">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="bg-surface border border-border rounded p-5">
              <Skeleton className="h-5 w-32 mb-3" />
              <Skeleton className="h-[34px] w-full" />
            </div>
          ))}
        </div>
      ) : (
        <div className="flex flex-col gap-3.5">
          {PROVIDER_ORDER.map((kind) => (
            <ProviderCard
              key={kind}
              kind={kind}
              reposUsing={reposUsing(kind)}
              onSave={handleSave}
            />
          ))}
        </div>
      )}
    </Shell>
  );
}
