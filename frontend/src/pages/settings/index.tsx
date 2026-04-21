import { useState, useEffect } from "react";
import { useNavigate } from "react-router";
import { Shell, PageHeader, Skeleton } from "@/components/Shell";
import { Button } from "@/components/ui/button";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Icons, Spinner } from "@/components/icons";
import {
  useLLMSettings,
  useSaveLLMSettings,
  useRepos,
  useWebhookSettings,
  useSaveGitHubSettings,
  useTestGitHubConnection,
  useSaveGitLabSettings,
  useTestGitLabConnection,
  useRotateWebhookHmac,
  useFeatureFlags,
} from "@/api";
import { useToast } from "@/lib/toast";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// LLM provider constants
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Shared field primitives
// ---------------------------------------------------------------------------

function FieldLabel({ htmlFor, children }: { htmlFor?: string; children: React.ReactNode }) {
  return (
    <label className="text-sm font-medium text-text-muted" htmlFor={htmlFor}>
      {children}
    </label>
  );
}

const inputClass = cn(
  "h-[34px] w-full rounded border bg-input-bg border-border text-text px-3 text-sm font-mono",
  "transition-[border-color,box-shadow] duration-[120ms]",
  "focus:border-accent focus:shadow-[0_0_0_3px_rgba(108,99,255,0.18)] focus:outline-none",
);

const textareaClass = cn(
  "w-full rounded border bg-input-bg border-border text-text px-3 py-2 text-sm font-mono",
  "min-h-[90px] resize-y",
  "transition-[border-color,box-shadow] duration-[120ms]",
  "focus:border-accent focus:shadow-[0_0_0_3px_rgba(108,99,255,0.18)] focus:outline-none",
);

// ---------------------------------------------------------------------------
// Status badge
// ---------------------------------------------------------------------------

function StatusBadge({ connected }: { connected: boolean }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium",
        connected
          ? "bg-success/15 text-success"
          : "bg-surface-2 text-text-muted",
      )}
    >
      <span
        className={cn(
          "w-1.5 h-1.5 rounded-full inline-block",
          connected ? "bg-success" : "bg-text-muted",
        )}
      />
      {connected ? "Connected" : "Not configured"}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Test connection result indicator
// ---------------------------------------------------------------------------

type TestStatus = "idle" | "testing" | "ok" | "error";

function TestResult({ status, error }: { status: TestStatus; error?: string }) {
  if (status === "idle") return null;
  if (status === "testing") return <Spinner size={12} className="text-text-muted" />;
  if (status === "ok")
    return (
      <span className="text-xs text-success inline-flex items-center gap-1">
        <Icons.check size={12} /> Connected
      </span>
    );
  return (
    <span className="text-xs text-error inline-flex items-center gap-1 max-w-[240px] truncate" title={error}>
      <Icons.warn size={12} /> {error ?? "Connection failed"}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Section wrapper
// ---------------------------------------------------------------------------

function Section({
  icon,
  title,
  badge,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  badge?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-surface border border-border rounded p-5 flex flex-col gap-4">
      <div className="flex items-center gap-2.5">
        <span className="inline-flex w-4 text-text-muted">{icon}</span>
        <span className="font-medium text-[15px]">{title}</span>
        {badge}
      </div>
      {children}
    </div>
  );
}

// ---------------------------------------------------------------------------
// GitHub App section
// ---------------------------------------------------------------------------

function GitHubSection({ webhookLoading }: { webhookLoading: boolean }) {
  const toast = useToast();
  const { data: webhook } = useWebhookSettings();
  const saveGitHub = useSaveGitHubSettings();
  const testGitHub = useTestGitHubConnection();

  const [appId, setAppId] = useState("");
  const [installId, setInstallId] = useState("");
  const [privateKey, setPrivateKey] = useState("");
  const [keyEdited, setKeyEdited] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testStatus, setTestStatus] = useState<TestStatus>("idle");
  const [testError, setTestError] = useState<string | undefined>();

  useEffect(() => {
    if (webhook) {
      setAppId(webhook.github_app_id ?? "");
      setInstallId(webhook.github_installation_id ?? "");
      setPrivateKey("");
      setKeyEdited(false);
    }
  }, [webhook]);

  const keySet = webhook?.github_key_set ?? false;
  const connected = Boolean(webhook?.github_app_id && webhook?.github_installation_id && keySet);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    saveGitHub.mutate(
      {
        app_id: appId,
        installation_id: installId,
        private_key: keyEdited ? (privateKey || null) : null,
      },
      {
        onSuccess: () => {
          setSaving(false);
          setKeyEdited(false);
          setPrivateKey("");
          toast.success("GitHub App settings saved");
        },
        onError: (err) => {
          setSaving(false);
          toast.error(err.message || "Save failed");
        },
      },
    );
  };

  const handleTest = () => {
    setTestStatus("testing");
    setTestError(undefined);
    testGitHub.mutate(undefined, {
      onSuccess: () => setTestStatus("ok"),
      onError: (err) => {
        setTestStatus("error");
        setTestError(err.message);
      },
    });
  };

  return (
    <Section
      icon={<Icons.github size={16} />}
      title="GitHub App"
      badge={webhookLoading ? <Skeleton className="h-5 w-24" /> : <StatusBadge connected={connected} />}
    >
      {webhookLoading ? (
        <>
          <Skeleton className="h-[34px] w-full" />
          <Skeleton className="h-[34px] w-full" />
          <Skeleton className="h-20 w-full" />
        </>
      ) : (
        <form onSubmit={handleSave} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <FieldLabel htmlFor="gh-app-id">App ID</FieldLabel>
            <input
              id="gh-app-id"
              data-testid="github-app-id"
              value={appId}
              onChange={(e) => setAppId(e.target.value)}
              placeholder="123456"
              className={inputClass}
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <FieldLabel htmlFor="gh-install-id">Installation ID</FieldLabel>
            <input
              id="gh-install-id"
              data-testid="github-installation-id"
              value={installId}
              onChange={(e) => setInstallId(e.target.value)}
              placeholder="12345678"
              className={inputClass}
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <FieldLabel htmlFor="gh-private-key">Private Key</FieldLabel>
            <textarea
              id="gh-private-key"
              data-testid="github-private-key"
              value={keyEdited ? privateKey : (keySet ? "••••••••••••••••••••••••" : "")}
              onFocus={() => {
                if (!keyEdited) {
                  setKeyEdited(true);
                  setPrivateKey("");
                }
              }}
              onChange={(e) => {
                setKeyEdited(true);
                setPrivateKey(e.target.value);
              }}
              placeholder="-----BEGIN RSA PRIVATE KEY-----&#10;…"
              className={textareaClass}
            />
            <p className="text-xs text-text-muted">
              {keyEdited ? "New key will be written on save." : keySet ? "Stored encrypted. Click to replace." : "Paste the PEM private key for your GitHub App."}
            </p>
          </div>

          <div className="flex items-center justify-between pt-2 border-t border-border">
            <div className="flex items-center gap-3">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={handleTest}
                disabled={!connected || testGitHub.isPending}
                data-testid="github-test"
              >
                {testGitHub.isPending ? <Spinner size={11} /> : <Icons.refresh size={13} />}
                Test connection
              </Button>
              <TestResult status={testStatus} error={testError} />
            </div>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              disabled={saving}
              data-testid="github-save"
            >
              {saving && <Spinner size={11} />}
              Save
            </Button>
          </div>
        </form>
      )}
    </Section>
  );
}

// ---------------------------------------------------------------------------
// GitLab section
// ---------------------------------------------------------------------------

function GitLabSection({ webhookLoading }: { webhookLoading: boolean }) {
  const toast = useToast();
  const { data: webhook } = useWebhookSettings();
  const saveGitLab = useSaveGitLabSettings();
  const testGitLab = useTestGitLabConnection();

  const [token, setToken] = useState("");
  const [tokenEdited, setTokenEdited] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testStatus, setTestStatus] = useState<TestStatus>("idle");
  const [testError, setTestError] = useState<string | undefined>();

  const connected = webhook?.gitlab_token_set ?? false;

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    if (!tokenEdited || !token) {
      toast.error("Enter a token to save.");
      return;
    }
    setSaving(true);
    saveGitLab.mutate(
      { token },
      {
        onSuccess: () => {
          setSaving(false);
          setTokenEdited(false);
          setToken("");
          toast.success("GitLab token saved");
        },
        onError: (err) => {
          setSaving(false);
          toast.error(err.message || "Save failed");
        },
      },
    );
  };

  const handleTest = () => {
    setTestStatus("testing");
    setTestError(undefined);
    testGitLab.mutate(undefined, {
      onSuccess: () => setTestStatus("ok"),
      onError: (err) => {
        setTestStatus("error");
        setTestError(err.message);
      },
    });
  };

  return (
    <Section
      icon={<Icons.gitlab size={16} />}
      title="GitLab"
      badge={webhookLoading ? <Skeleton className="h-5 w-24" /> : <StatusBadge connected={connected} />}
    >
      {webhookLoading ? (
        <Skeleton className="h-[34px] w-full" />
      ) : (
        <form onSubmit={handleSave} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <FieldLabel htmlFor="gl-token">Personal Access Token</FieldLabel>
            <input
              id="gl-token"
              data-testid="gitlab-token"
              type="password"
              value={tokenEdited ? token : (connected ? "••••••••••••••••••••••••" : "")}
              onFocus={() => {
                if (!tokenEdited) {
                  setTokenEdited(true);
                  setToken("");
                }
              }}
              onChange={(e) => {
                setTokenEdited(true);
                setToken(e.target.value);
              }}
              placeholder="glpat-…"
              className={inputClass}
            />
            <p className="text-xs text-text-muted">
              {tokenEdited ? "Token will be written on save." : connected ? "Stored encrypted. Click to replace." : "Requires api scope."}
            </p>
          </div>

          <div className="flex items-center justify-between pt-2 border-t border-border">
            <div className="flex items-center gap-3">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={handleTest}
                disabled={!connected || testGitLab.isPending}
                data-testid="gitlab-test"
              >
                {testGitLab.isPending ? <Spinner size={11} /> : <Icons.refresh size={13} />}
                Test connection
              </Button>
              <TestResult status={testStatus} error={testError} />
            </div>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              disabled={saving}
              data-testid="gitlab-save"
            >
              {saving && <Spinner size={11} />}
              Save
            </Button>
          </div>
        </form>
      )}
    </Section>
  );
}

// ---------------------------------------------------------------------------
// Webhook section
// ---------------------------------------------------------------------------

function WebhookSection({ webhookLoading }: { webhookLoading: boolean }) {
  const toast = useToast();
  const { data: webhook } = useWebhookSettings();
  const rotate = useRotateWebhookHmac();
  const [copied, setCopied] = useState(false);

  const url = webhook?.url ?? "";

  const handleCopy = () => {
    if (!url) return;
    void navigator.clipboard.writeText(url).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const handleRotate = () => {
    rotate.mutate(undefined, {
      onSuccess: () => toast.success("Webhook HMAC secret rotated"),
      onError: (err) => toast.error(err.message || "Rotate failed"),
    });
  };

  return (
    <Section icon={<Icons.webhook size={16} />} title="Webhook">
      {webhookLoading ? (
        <Skeleton className="h-[34px] w-full" />
      ) : (
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <FieldLabel>Endpoint URL</FieldLabel>
            <div className="relative">
              <input
                readOnly
                value={url || "Not configured"}
                data-testid="webhook-url"
                className={cn(inputClass, "pr-9 text-text-muted cursor-default")}
              />
              {url && (
                <button
                  type="button"
                  onClick={handleCopy}
                  className="absolute right-1 top-1 inline-flex items-center justify-center w-7 h-7 rounded text-text-muted hover:text-text transition-colors"
                  aria-label="Copy webhook URL"
                >
                  {copied ? <Icons.check size={13} /> : <Icons.copy size={13} />}
                </button>
              )}
            </div>
            <p className="text-xs text-text-muted">Configure your VCS provider to send webhook events to this URL.</p>
          </div>

          <div className="flex items-center justify-between pt-2 border-t border-border">
            <p className="text-xs text-text-muted">Rotating the HMAC secret invalidates all existing webhooks.</p>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={handleRotate}
              disabled={rotate.isPending}
              data-testid="webhook-rotate"
            >
              {rotate.isPending ? <Spinner size={11} /> : <Icons.refresh size={13} />}
              Rotate secret
            </Button>
          </div>
        </div>
      )}
    </Section>
  );
}

// ---------------------------------------------------------------------------
// VCS adapters tab
// ---------------------------------------------------------------------------

function VCSAdaptersTab() {
  const { isLoading } = useWebhookSettings();

  return (
    <div className="flex flex-col gap-4">
      <GitHubSection webhookLoading={isLoading} />
      <GitLabSection webhookLoading={isLoading} />
      <WebhookSection webhookLoading={isLoading} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// LLM providers tab (existing)
// ---------------------------------------------------------------------------

function LLMProvidersTab() {
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

  if (isLoading) {
    return (
      <div className="bg-surface border border-border rounded p-5 flex flex-col gap-3">
        <Skeleton className="h-5 w-32" />
        <Skeleton className="h-[34px] w-full" />
        <Skeleton className="h-[34px] w-full" />
      </div>
    );
  }

  return (
    <form
      data-testid="settings-form"
      aria-label="LLM Settings"
      onSubmit={handleSave}
      className="bg-surface border border-border rounded p-5 flex flex-col gap-4"
    >
      {/* Provider */}
      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium text-text-muted" id="provider-label">
          Provider
        </label>
        <Select
          value={provider}
          onValueChange={(val) => {
            setProvider(val);
            setModel("");
            setBaseUrl("");
            setApiKey("");
            setKeyEdited(false);
            setSaved(false);
          }}
        >
          <SelectTrigger
            data-testid="provider-select"
            aria-label="Provider"
            aria-labelledby="provider-label"
          >
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {PROVIDER_ORDER.map((p) => (
              <SelectItem key={p} value={p}>
                {PROVIDER_LABELS[p]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
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
  );
}

// ---------------------------------------------------------------------------
// Tab bar
// ---------------------------------------------------------------------------

type SettingsTab = "llm" | "vcs";

function TabBar({
  active,
  showVcs,
  onChange,
}: {
  active: SettingsTab;
  showVcs: boolean;
  onChange: (tab: SettingsTab) => void;
}) {
  const tabClass = (t: SettingsTab) =>
    cn(
      "px-3 py-1.5 text-sm rounded-[6px] font-medium transition-colors duration-[120ms]",
      active === t
        ? "bg-surface-2 text-text"
        : "text-text-muted hover:text-text hover:bg-surface-2/50",
    );

  return (
    <div className="flex items-center gap-1 mb-5 border-b border-border pb-3">
      <button type="button" className={tabClass("llm")} onClick={() => onChange("llm")}>
        LLM Providers
      </button>
      {showVcs && (
        <button
          type="button"
          className={tabClass("vcs")}
          onClick={() => onChange("vcs")}
          data-testid="vcs-tab"
        >
          VCS Adapters
        </button>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function SettingsPage() {
  const navigate = useNavigate();
  const [tab, setTab] = useState<SettingsTab>("llm");
  const { data: flags } = useFeatureFlags();
  const showVcs = flags?.flags?.["platform.vcs_settings"] ?? true;

  return (
    <Shell>
      <PageHeader
        title="Settings"
        subtitle="Global configuration for LLM providers and VCS adapters."
        action={
          <Button size="sm" variant="default" onClick={() => navigate("/repos")}>
            <Icons.repos size={13} />
            Manage repositories
          </Button>
        }
      />

      <TabBar active={tab} showVcs={showVcs} onChange={setTab} />

      {tab === "llm" && <LLMProvidersTab />}
      {tab === "vcs" && showVcs && <VCSAdaptersTab />}
    </Shell>
  );
}
