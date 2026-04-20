import { useState } from "react";
import { Shell, PageHeader, EmptyState, Skeleton } from "@/components/Shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";
import { Icons, Spinner } from "@/components/icons";
import {
  useRepos,
  useCreateRepo,
  useUpdateRepo,
  useDeleteRepo,
  useToggleRepo,
} from "@/api";
import { useToast } from "@/lib/toast";
import type { components } from "@/api/schema";
import { cn } from "@/lib/utils";

type RepoItem = components["schemas"]["RepoItem"];
type RepoBody = components["schemas"]["RepoBody"];

const CLOUD_PROVIDERS = ["openai", "anthropic", "claude_code"];
const PROVIDER_LABELS: Record<string, string> = {
  ollama: "Ollama",
  vllm: "vLLM",
  openai: "OpenAI",
  anthropic: "Anthropic",
  claude_code: "Claude Code",
};
const MODEL_SUGGESTIONS: Record<string, string[]> = {
  ollama: ["qwen2.5-coder:14b", "qwen2.5-coder:32b", "deepseek-coder-v2:16b", "codellama:34b"],
  vllm: ["Qwen2.5-Coder-32B", "DeepSeek-Coder-V2-Lite", "Llama-3.1-70B-Instruct"],
  openai: ["gpt-4o-mini", "gpt-4o", "o4-mini"],
  anthropic: ["claude-sonnet-4", "claude-opus-4", "claude-haiku-4"],
  claude_code: ["claude-sonnet-4", "claude-opus-4"],
};

function isCloud(provider: string) {
  return CLOUD_PROVIDERS.includes(provider);
}

interface RepoModalProps {
  mode: "new" | "edit";
  repo?: RepoItem;
  onClose: () => void;
  onSave: (body: RepoBody) => void;
  saving: boolean;
}

function RepoModal({ mode, repo, onClose, onSave, saving }: RepoModalProps) {
  const [platform, setPlatform] = useState(repo?.platform ?? "github");
  const [org, setOrg] = useState(repo?.org ?? "");
  const [repoName, setRepoName] = useState(repo?.repo ?? "");
  const [provider, setProvider] = useState(repo?.provider ?? "ollama");
  const [model, setModel] = useState(
    repo?.model ?? MODEL_SUGGESTIONS["ollama"][0],
  );

  const changeProvider = (p: string) => {
    setProvider(p);
    if (!MODEL_SUGGESTIONS[p]?.includes(model)) {
      setModel(MODEL_SUGGESTIONS[p]?.[0] ?? "");
    }
  };

  const valid = org.trim() && repoName.trim() && model.trim();

  const handleSave = () => {
    onSave({
      platform,
      org: org.trim(),
      repo: repoName.trim(),
      slug: null,
      provider,
      model: model.trim(),
      enabled: true,
    });
  };

  return (
    <>
      <div
        className="fixed inset-0 z-40 bg-black/50 animate-fade-in"
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-[min(540px,calc(100vw-32px))] bg-surface border border-border rounded shadow-[0_12px_40px_rgba(0,0,0,0.5)] animate-modal-in"
        role="dialog"
        aria-modal="true"
        aria-label={mode === "new" ? "Add repository" : "Edit repository"}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <h3 className="text-base font-semibold m-0">
            {mode === "new" ? "Add repository" : "Edit repository"}
          </h3>
          <button
            className="inline-flex items-center justify-center w-7 h-7 rounded text-text-muted hover:text-text hover:bg-surface-2 transition-colors"
            onClick={onClose}
            aria-label="Close"
          >
            <Icons.x size={16} />
          </button>
        </div>

        {/* Body */}
        <div className="p-5">
          <div className="grid grid-cols-[140px_1fr] gap-3 mb-4">
            <div>
              <label className="block text-[12.5px] text-text-muted font-medium mb-1.5">
                Platform
              </label>
              <NativeSelect
                value={platform}
                onChange={(e) => setPlatform(e.target.value)}
                className="w-full"
              >
                <option value="github">GitHub</option>
                <option value="gitlab">GitLab</option>
              </NativeSelect>
            </div>
            <div>
              <label className="block text-[12.5px] text-text-muted font-medium mb-1.5">
                Organization
              </label>
              <Input
                value={org}
                onChange={(e) => setOrg(e.target.value)}
                placeholder="acme"
                autoFocus
                className="font-mono"
              />
            </div>
          </div>

          <div className="mb-4">
            <label className="block text-[12.5px] text-text-muted font-medium mb-1.5">
              Repository
            </label>
            <Input
              value={repoName}
              onChange={(e) => setRepoName(e.target.value)}
              placeholder="api-gateway or * for all"
              className="font-mono"
            />
            <p className="text-xs text-text-muted mt-1.5">
              Use <code className="text-text">*</code> to match every repo in this org.
            </p>
          </div>

          <div className="border-t border-border -mx-5 my-4" />

          <div className="text-[11.5px] text-text-muted uppercase tracking-[.06em] font-medium mb-3">
            Model
          </div>

          <div className="mb-4">
            <label className="block text-[12.5px] text-text-muted font-medium mb-1.5">
              Provider
            </label>
            <NativeSelect
              value={provider}
              onChange={(e) => changeProvider(e.target.value)}
              className="w-full"
            >
              <option value="ollama">Ollama — local</option>
              <option value="vllm">vLLM — self-hosted</option>
              <option value="openai">OpenAI — cloud</option>
              <option value="anthropic">Anthropic — cloud</option>
              <option value="claude_code">Claude Code — cloud</option>
            </NativeSelect>
            <p className="text-xs text-text-muted mt-1.5">
              Credentials & base URL configured in Providers.
            </p>
          </div>

          {isCloud(provider) && (
            <div className="flex items-start gap-2 bg-warning-bg border border-warning-border rounded p-3 mb-4 text-xs text-warning-text">
              <Icons.warn size={13} className="shrink-0 mt-0.5" />
              <span>
                Source for this repo will leave your network to {PROVIDER_LABELS[provider]}.
              </span>
            </div>
          )}

          <div>
            <label className="block text-[12.5px] text-text-muted font-medium mb-1.5">
              Model
            </label>
            <Input
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder={MODEL_SUGGESTIONS[provider]?.[0] ?? ""}
              className="font-mono mb-2"
              list={`models-${provider}`}
            />
            <datalist id={`models-${provider}`}>
              {MODEL_SUGGESTIONS[provider]?.map((m) => <option key={m} value={m} />)}
            </datalist>
            <div className="flex flex-wrap gap-1.5">
              {MODEL_SUGGESTIONS[provider]?.map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => setModel(m)}
                  className={cn(
                    "h-[22px] px-2 text-[11px] rounded border font-mono transition-colors",
                    model === m
                      ? "bg-accent border-accent text-white"
                      : "bg-surface-2 border-border text-text-muted hover:text-text",
                  )}
                >
                  {m}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 px-5 py-3.5 border-t border-border">
          <Button variant="default" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="primary"
            disabled={!valid || saving}
            onClick={handleSave}
          >
            {saving && <Spinner size={13} />}
            {mode === "new" ? "Add" : "Save"}
          </Button>
        </div>
      </div>
    </>
  );
}

interface ConfirmModalProps {
  repo: RepoItem;
  onCancel: () => void;
  onConfirm: () => void;
  pending: boolean;
}

function ConfirmDeleteModal({ repo, onCancel, onConfirm, pending }: ConfirmModalProps) {
  return (
    <>
      <div
        className="fixed inset-0 z-40 bg-black/50 animate-fade-in"
        onClick={onCancel}
        aria-hidden="true"
      />
      <div
        className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-[min(420px,calc(100vw-32px))] bg-surface border border-border rounded shadow-[0_12px_40px_rgba(0,0,0,0.5)] animate-modal-in"
        role="dialog"
        aria-modal="true"
      >
        <div className="px-5 py-4 border-b border-border">
          <h3 className="text-base font-semibold m-0">Remove repository?</h3>
        </div>
        <div className="px-5 py-4 text-sm text-text-muted">
          Vellic will stop analyzing{" "}
          <code className="text-text font-mono">{repo.slug}</code>. Incoming webhooks will be
          ignored.
        </div>
        <div className="flex items-center justify-end gap-2 px-5 py-3.5 border-t border-border">
          <Button variant="default" onClick={onCancel}>
            Cancel
          </Button>
          <Button variant="danger" onClick={onConfirm} disabled={pending}>
            {pending && <Spinner size={13} />}
            Remove
          </Button>
        </div>
      </div>
    </>
  );
}

export default function ReposPage() {
  const toast = useToast();
  const { data: repoList, isLoading } = useRepos();
  const createRepo = useCreateRepo();
  const updateRepo = useUpdateRepo();
  const deleteRepo = useDeleteRepo();
  const toggleRepo = useToggleRepo();

  const [editing, setEditing] = useState<{ mode: "new" | "edit"; repo?: RepoItem } | null>(null);
  const [confirmDel, setConfirmDel] = useState<RepoItem | null>(null);

  const repos = repoList?.items ?? [];

  const handleSave = (body: RepoBody) => {
    if (!editing) return;
    if (editing.mode === "new") {
      createRepo.mutate(body, {
        onSuccess: () => {
          toast.success(`Added ${body.org}/${body.repo}`);
          setEditing(null);
        },
        onError: (e) => toast.error(e.message || "Failed to add repository"),
      });
    } else {
      updateRepo.mutate(
        { id: editing.repo!.id, body },
        {
          onSuccess: () => {
            toast.success(`Updated ${body.org}/${body.repo}`);
            setEditing(null);
          },
          onError: (e) => toast.error(e.message || "Failed to update repository"),
        },
      );
    }
  };

  const handleDelete = (repo: RepoItem) => {
    deleteRepo.mutate(repo.id, {
      onSuccess: () => {
        toast.success(`Removed ${repo.slug}`);
        setConfirmDel(null);
      },
      onError: (e) => toast.error(e.message || "Failed to remove repository"),
    });
  };

  const handleToggle = (repo: RepoItem) => {
    toggleRepo.mutate(repo.id, {
      onError: (e) => toast.error(e.message || "Failed to toggle"),
    });
  };

  return (
    <Shell>
      <PageHeader
        title="Repositories"
        subtitle="Each repo picks its own model. Bring your own keys via Providers."
        action={
          <Button variant="primary" onClick={() => setEditing({ mode: "new" })}>
            <Icons.plus size={14} />
            Add repository
          </Button>
        }
      />

      {isLoading ? (
        <div className="flex flex-col gap-2.5">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="bg-surface border border-border rounded p-4">
              <Skeleton className="h-5 w-48" />
            </div>
          ))}
        </div>
      ) : repos.length === 0 ? (
        <EmptyState
          icon={<Icons.repos size={22} />}
          title="No repositories — analysis is paused"
          body="Add a repository to start listening for pull requests."
          action={
            <Button variant="primary" onClick={() => setEditing({ mode: "new" })}>
              <Icons.plus size={14} />
              Add repository
            </Button>
          }
        />
      ) : (
        <div className="flex flex-col gap-2.5">
          {repos.map((r) => (
            <div
              key={r.id}
              className="bg-surface border border-border rounded px-4 py-3.5 flex items-center gap-3.5"
              style={{ gridTemplateColumns: "30px 1fr auto auto auto" }}
            >
              {/* Platform icon */}
              <span
                className={cn(
                  "w-[30px] h-[30px] rounded-[6px] bg-surface-2 inline-flex items-center justify-center shrink-0",
                  r.platform === "github" ? "text-text" : "text-warning-text",
                )}
              >
                {r.platform === "github" ? (
                  <Icons.github size={16} />
                ) : (
                  <Icons.gitlab size={16} />
                )}
              </span>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <div className="font-mono text-[13.5px] truncate">{r.slug}</div>
                <div className="flex items-center gap-1.5 mt-0.5 flex-wrap">
                  <span className="font-mono text-[11.5px] text-text-muted">
                    {PROVIDER_LABELS[r.provider] ?? r.provider} · {r.model}
                  </span>
                  {isCloud(r.provider) && (
                    <Badge variant="warning" className="h-4 text-[10px] px-1.5">
                      <Icons.warn size={10} /> cloud
                    </Badge>
                  )}
                </div>
              </div>

              {/* Edit */}
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setEditing({ mode: "edit", repo: r })}
                aria-label={`Edit ${r.slug}`}
              >
                Edit
              </Button>

              {/* Toggle */}
              <label className="inline-flex items-center gap-2 cursor-pointer select-none">
                <span
                  className={cn(
                    "text-xs min-w-[48px] text-right",
                    r.enabled ? "text-success" : "text-text-muted",
                  )}
                >
                  {r.enabled ? "Enabled" : "Disabled"}
                </span>
                <button
                  role="switch"
                  aria-checked={r.enabled}
                  aria-label={`${r.enabled ? "Disable" : "Enable"} ${r.slug}`}
                  onClick={() => handleToggle(r)}
                  className={cn(
                    "relative inline-flex h-5 w-9 shrink-0 rounded-full border-2 border-transparent",
                    "transition-colors duration-[120ms] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent",
                    r.enabled ? "bg-accent" : "bg-surface-2 border border-border",
                  )}
                >
                  <span
                    className={cn(
                      "pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow-sm transition-transform duration-[120ms]",
                      r.enabled ? "translate-x-4" : "translate-x-0",
                    )}
                  />
                </button>
              </label>

              {/* Delete */}
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setConfirmDel(r)}
                className="text-text-muted px-2"
                aria-label={`Remove ${r.slug}`}
              >
                <Icons.trash size={14} />
              </Button>
            </div>
          ))}
        </div>
      )}

      {editing && (
        <RepoModal
          mode={editing.mode}
          repo={editing.repo}
          onClose={() => setEditing(null)}
          onSave={handleSave}
          saving={createRepo.isPending || updateRepo.isPending}
        />
      )}

      {confirmDel && (
        <ConfirmDeleteModal
          repo={confirmDel}
          onCancel={() => setConfirmDel(null)}
          onConfirm={() => handleDelete(confirmDel)}
          pending={deleteRepo.isPending}
        />
      )}
    </Shell>
  );
}
