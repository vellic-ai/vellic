import { useState, useRef } from "react";
import { useParams, NavLink } from "react-router";
import { Shell, PageHeader, EmptyState, Skeleton } from "@/components/Shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";
import { Badge } from "@/components/ui/badge";
import { Icons, Spinner } from "@/components/icons";
import {
  useRepos,
  useRepoPlugins,
  useInstallPlugin,
  usePatchPlugin,
  useRemovePlugin,
  useRepoMcpServers,
  useAttachMcpServer,
  usePatchMcpServer,
  useDetachMcpServer,
} from "@/api";
import { useToast } from "@/lib/toast";
import type { components } from "@/api/schema";
import { cn } from "@/lib/utils";

type PluginItem = components["schemas"]["PluginItem"];
type McpServerItem = components["schemas"]["McpServerItem"];

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatRelative(iso: string | null): string {
  if (!iso) return "—";
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

// ─── Toggle switch ─────────────────────────────────────────────────────────────

function Toggle({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
}) {
  return (
    <button
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className={cn(
        "relative inline-flex h-5 w-9 shrink-0 rounded-full border-2 border-transparent",
        "transition-colors duration-[120ms] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent",
        checked ? "bg-accent" : "bg-surface-2 border border-border",
      )}
    >
      <span
        className={cn(
          "pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow-sm transition-transform duration-[120ms]",
          checked ? "translate-x-4" : "translate-x-0",
        )}
      />
    </button>
  );
}

// ─── Confirm modal ─────────────────────────────────────────────────────────────

function ConfirmModal({
  title,
  body,
  confirmLabel,
  pending,
  onCancel,
  onConfirm,
}: {
  title: string;
  body: React.ReactNode;
  confirmLabel: string;
  pending: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
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
          <h3 className="text-base font-semibold m-0">{title}</h3>
        </div>
        <div className="px-5 py-4 text-sm text-text-muted">{body}</div>
        <div className="flex items-center justify-end gap-2 px-5 py-3.5 border-t border-border">
          <Button variant="default" onClick={onCancel}>
            Cancel
          </Button>
          <Button variant="danger" onClick={onConfirm} disabled={pending}>
            {pending && <Spinner size={13} />}
            {confirmLabel}
          </Button>
        </div>
      </div>
    </>
  );
}

// ─── Add Plugin modal ──────────────────────────────────────────────────────────

function AddPluginModal({
  repoId,
  onClose,
}: {
  repoId: string;
  onClose: () => void;
}) {
  const toast = useToast();
  const install = useInstallPlugin(repoId);
  const [mode, setMode] = useState<"zip" | "git">("zip");
  const [gitUrl, setGitUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const valid = mode === "zip" ? Boolean(file) : gitUrl.trim().startsWith("http");

  const handleSubmit = () => {
    const payload =
      mode === "zip"
        ? { type: "zip" as const, file: file! }
        : { type: "git" as const, url: gitUrl.trim() };
    install.mutate(payload, {
      onSuccess: () => {
        toast.success("Plugin installed");
        onClose();
      },
      onError: (e) => toast.error(e.message || "Failed to install plugin"),
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
        className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-[min(500px,calc(100vw-32px))] bg-surface border border-border rounded shadow-[0_12px_40px_rgba(0,0,0,0.5)] animate-modal-in"
        role="dialog"
        aria-modal="true"
        aria-label="Install plugin"
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <h3 className="text-base font-semibold m-0">Install plugin</h3>
          <button
            className="inline-flex items-center justify-center w-7 h-7 rounded text-text-muted hover:text-text hover:bg-surface-2 transition-colors"
            onClick={onClose}
            aria-label="Close"
          >
            <Icons.x size={16} />
          </button>
        </div>

        <div className="p-5">
          <div className="flex gap-2 mb-5">
            {(["zip", "git"] as const).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={cn(
                  "flex-1 h-9 rounded text-sm font-medium border transition-colors",
                  mode === m
                    ? "bg-accent/10 border-accent text-accent"
                    : "border-border text-text-muted hover:text-text hover:bg-surface-2",
                )}
              >
                {m === "zip" ? "ZIP archive" : "Git URL"}
              </button>
            ))}
          </div>

          {mode === "zip" ? (
            <div>
              <label className="block text-[12.5px] text-text-muted font-medium mb-1.5">
                Plugin archive (.zip)
              </label>
              <input
                ref={fileRef}
                type="file"
                accept=".zip"
                className="hidden"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
              <button
                onClick={() => fileRef.current?.click()}
                className={cn(
                  "w-full h-24 rounded border-2 border-dashed flex flex-col items-center justify-center gap-2 transition-colors text-sm",
                  file
                    ? "border-accent/50 bg-accent/5 text-accent"
                    : "border-border text-text-muted hover:border-accent/40 hover:text-text",
                )}
              >
                <Icons.plugin size={22} />
                {file ? (
                  <span className="font-mono text-xs">{file.name}</span>
                ) : (
                  <span>Click to select .zip file</span>
                )}
              </button>
            </div>
          ) : (
            <div>
              <label className="block text-[12.5px] text-text-muted font-medium mb-1.5">
                Git repository URL
              </label>
              <Input
                value={gitUrl}
                onChange={(e) => setGitUrl(e.target.value)}
                placeholder="https://github.com/org/vellic-plugin"
                className="font-mono"
                autoFocus
              />
              <p className="text-xs text-text-muted mt-1.5">
                Public repo or one accessible by your Vellic instance.
              </p>
            </div>
          )}
        </div>

        <div className="flex items-center justify-end gap-2 px-5 py-3.5 border-t border-border">
          <Button variant="default" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="primary"
            disabled={!valid || install.isPending}
            onClick={handleSubmit}
          >
            {install.isPending && <Spinner size={13} />}
            Install
          </Button>
        </div>
      </div>
    </>
  );
}

// ─── Attach MCP modal ──────────────────────────────────────────────────────────

function AttachMcpModal({
  repoId,
  onClose,
}: {
  repoId: string;
  onClose: () => void;
}) {
  const toast = useToast();
  const attach = useAttachMcpServer(repoId);
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [transport, setTransport] = useState<"sse" | "stdio" | "streamable_http">("sse");
  const [credKey, setCredKey] = useState("");
  const [credVal, setCredVal] = useState("");

  const credentials: Record<string, string> =
    credKey.trim() ? { [credKey.trim()]: credVal } : {};

  const valid = name.trim() && url.trim().startsWith("http");

  const handleSubmit = () => {
    attach.mutate(
      { name: name.trim(), url: url.trim(), transport, credentials: Object.keys(credentials).length ? credentials : null },
      {
        onSuccess: () => {
          toast.success(`Attached ${name.trim()}`);
          onClose();
        },
        onError: (e) => toast.error(e.message || "Failed to attach MCP server"),
      },
    );
  };

  return (
    <>
      <div
        className="fixed inset-0 z-40 bg-black/50 animate-fade-in"
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-[min(500px,calc(100vw-32px))] bg-surface border border-border rounded shadow-[0_12px_40px_rgba(0,0,0,0.5)] animate-modal-in"
        role="dialog"
        aria-modal="true"
        aria-label="Attach MCP server"
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <h3 className="text-base font-semibold m-0">Attach MCP server</h3>
          <button
            className="inline-flex items-center justify-center w-7 h-7 rounded text-text-muted hover:text-text hover:bg-surface-2 transition-colors"
            onClick={onClose}
            aria-label="Close"
          >
            <Icons.x size={16} />
          </button>
        </div>

        <div className="p-5 flex flex-col gap-4">
          <div>
            <label className="block text-[12.5px] text-text-muted font-medium mb-1.5">
              Name
            </label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="GitHub MCP"
              autoFocus
            />
          </div>

          <div>
            <label className="block text-[12.5px] text-text-muted font-medium mb-1.5">
              Server URL
            </label>
            <Input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://mcp.example.com/sse"
              className="font-mono"
            />
          </div>

          <div>
            <label className="block text-[12.5px] text-text-muted font-medium mb-1.5">
              Transport
            </label>
            <NativeSelect
              value={transport}
              onChange={(e) => setTransport(e.target.value as typeof transport)}
              className="w-full"
            >
              <option value="sse">SSE (Server-Sent Events)</option>
              <option value="streamable_http">Streamable HTTP</option>
              <option value="stdio">stdio</option>
            </NativeSelect>
          </div>

          <div className="border-t border-border -mx-5 px-5 pt-4">
            <div className="text-[11.5px] text-text-muted uppercase tracking-[.06em] font-medium mb-3">
              Credentials (optional)
            </div>
            <div className="grid grid-cols-[1fr_1fr] gap-2">
              <div>
                <label className="block text-[12.5px] text-text-muted font-medium mb-1.5">
                  Header / key
                </label>
                <Input
                  value={credKey}
                  onChange={(e) => setCredKey(e.target.value)}
                  placeholder="Authorization"
                  className="font-mono"
                />
              </div>
              <div>
                <label className="block text-[12.5px] text-text-muted font-medium mb-1.5">
                  Value
                </label>
                <Input
                  value={credVal}
                  onChange={(e) => setCredVal(e.target.value)}
                  placeholder="Bearer token…"
                  className="font-mono"
                  type="password"
                />
              </div>
            </div>
            <p className="text-xs text-text-muted mt-1.5">
              Stored encrypted. Add more via API after attaching.
            </p>
          </div>
        </div>

        <div className="flex items-center justify-end gap-2 px-5 py-3.5 border-t border-border">
          <Button variant="default" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="primary"
            disabled={!valid || attach.isPending}
            onClick={handleSubmit}
          >
            {attach.isPending && <Spinner size={13} />}
            Attach
          </Button>
        </div>
      </div>
    </>
  );
}

// ─── Plugin row ────────────────────────────────────────────────────────────────

function PluginRow({
  plugin,
  repoId,
  onRemove,
}: {
  plugin: PluginItem;
  repoId: string;
  onRemove: (p: PluginItem) => void;
}) {
  const toast = useToast();
  const patch = usePatchPlugin(repoId);
  const [editingPin, setEditingPin] = useState(false);
  const [pinValue, setPinValue] = useState(plugin.version_pin ?? "");

  const handleToggle = () => {
    patch.mutate(
      { pluginId: plugin.id, body: { enabled: !plugin.enabled } },
      { onError: (e) => toast.error(e.message || "Failed to toggle") },
    );
  };

  const handlePinSave = () => {
    patch.mutate(
      { pluginId: plugin.id, body: { version_pin: pinValue.trim() || null } },
      {
        onSuccess: () => setEditingPin(false),
        onError: (e) => toast.error(e.message || "Failed to update pin"),
      },
    );
  };

  return (
    <div className="bg-surface border border-border rounded px-4 py-3 flex items-center gap-3.5">
      <span className="w-8 h-8 rounded-[6px] bg-surface-2 inline-flex items-center justify-center shrink-0 text-accent">
        <Icons.plugin size={16} />
      </span>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium text-[13.5px] truncate">{plugin.name}</span>
          <Badge variant={plugin.type === "git" ? "default" : "warning"} className="h-4 text-[10px] px-1.5">
            {plugin.type}
          </Badge>
        </div>
        <div className="text-[11.5px] text-text-muted font-mono truncate mt-0.5">
          {plugin.source}
        </div>
      </div>

      {/* Version pin */}
      <div className="shrink-0 min-w-[90px]">
        {editingPin ? (
          <div className="flex items-center gap-1">
            <Input
              value={pinValue}
              onChange={(e) => setPinValue(e.target.value)}
              placeholder="e.g. 1.2.0"
              className="h-7 text-xs font-mono w-24"
              autoFocus
              onKeyDown={(e) => {
                if (e.key === "Enter") handlePinSave();
                if (e.key === "Escape") setEditingPin(false);
              }}
            />
            <Button size="sm" variant="primary" className="h-7 px-2" onClick={handlePinSave} disabled={patch.isPending}>
              {patch.isPending ? <Spinner size={11} /> : <Icons.check size={12} />}
            </Button>
            <Button size="sm" variant="ghost" className="h-7 px-1.5" onClick={() => setEditingPin(false)}>
              <Icons.x size={12} />
            </Button>
          </div>
        ) : (
          <button
            onClick={() => { setPinValue(plugin.version_pin ?? ""); setEditingPin(true); }}
            className="text-[11.5px] font-mono text-text-muted hover:text-text transition-colors group flex items-center gap-1"
            aria-label="Edit version pin"
          >
            <span>{plugin.version_pin ?? plugin.version ?? "latest"}</span>
            <Icons.external size={10} className="opacity-0 group-hover:opacity-60" />
          </button>
        )}
      </div>

      {/* Last used */}
      <div className="text-[11.5px] text-text-muted shrink-0 w-20 text-right tabular-nums">
        {formatRelative(plugin.last_used_at)}
      </div>

      {/* Toggle */}
      <Toggle
        checked={plugin.enabled}
        onChange={handleToggle}
        label={`${plugin.enabled ? "Disable" : "Enable"} ${plugin.name}`}
      />

      {/* Remove */}
      <Button
        size="sm"
        variant="ghost"
        className="text-text-muted px-2 shrink-0"
        onClick={() => onRemove(plugin)}
        aria-label={`Remove ${plugin.name}`}
      >
        <Icons.trash size={14} />
      </Button>
    </div>
  );
}

// ─── MCP server row ────────────────────────────────────────────────────────────

function McpServerRow({
  server,
  repoId,
  onDetach,
}: {
  server: McpServerItem;
  repoId: string;
  onDetach: (s: McpServerItem) => void;
}) {
  const toast = useToast();
  const patch = usePatchMcpServer(repoId);

  const handleToggle = () => {
    patch.mutate(
      { serverId: server.id, body: { enabled: !server.enabled } },
      { onError: (e) => toast.error(e.message || "Failed to toggle") },
    );
  };

  const TRANSPORT_LABELS: Record<string, string> = {
    sse: "SSE",
    stdio: "stdio",
    streamable_http: "HTTP",
  };

  return (
    <div className="bg-surface border border-border rounded px-4 py-3 flex items-center gap-3.5">
      <span className="w-8 h-8 rounded-[6px] bg-surface-2 inline-flex items-center justify-center shrink-0 text-text-muted">
        <Icons.mcpServer size={16} />
      </span>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium text-[13.5px] truncate">{server.name}</span>
          <Badge variant="default" className="h-4 text-[10px] px-1.5">
            {TRANSPORT_LABELS[server.transport] ?? server.transport}
          </Badge>
          {server.credentials_set && (
            <Badge variant="success" className="h-4 text-[10px] px-1.5">
              auth
            </Badge>
          )}
        </div>
        <div className="text-[11.5px] text-text-muted font-mono truncate mt-0.5">
          {server.url}
        </div>
      </div>

      {/* Last used */}
      <div className="text-[11.5px] text-text-muted shrink-0 w-20 text-right tabular-nums">
        {formatRelative(server.last_used_at)}
      </div>

      {/* Toggle */}
      <Toggle
        checked={server.enabled}
        onChange={handleToggle}
        label={`${server.enabled ? "Disable" : "Enable"} ${server.name}`}
      />

      {/* Detach */}
      <Button
        size="sm"
        variant="ghost"
        className="text-text-muted px-2 shrink-0"
        onClick={() => onDetach(server)}
        aria-label={`Detach ${server.name}`}
      >
        <Icons.trash size={14} />
      </Button>
    </div>
  );
}

// ─── Section header ────────────────────────────────────────────────────────────

function SectionHeader({
  icon,
  title,
  count,
  action,
}: {
  icon: React.ReactNode;
  title: string;
  count?: number;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between mb-3">
      <div className="flex items-center gap-2">
        <span className="text-text-muted">{icon}</span>
        <h2 className="text-[13px] font-semibold uppercase tracking-[.06em] text-text-muted m-0">
          {title}
        </h2>
        {count !== undefined && (
          <span className="inline-flex h-4 min-w-[16px] items-center justify-center rounded-full bg-surface-2 text-[10.5px] font-medium text-text-muted px-1">
            {count}
          </span>
        )}
      </div>
      {action}
    </div>
  );
}

// ─── Page ──────────────────────────────────────────────────────────────────────

export default function RepoExtensionsPage() {
  const { repoId } = useParams<{ repoId: string }>();
  const toast = useToast();

  const { data: repoList } = useRepos();
  const repo = repoList?.items.find((r) => r.id === repoId);

  const { data: pluginData, isLoading: pluginsLoading } = useRepoPlugins(repoId!);
  const { data: mcpData, isLoading: mcpLoading } = useRepoMcpServers(repoId!);
  const removePlugin = useRemovePlugin(repoId!);
  const detachServer = useDetachMcpServer(repoId!);

  const [showAddPlugin, setShowAddPlugin] = useState(false);
  const [showAttachMcp, setShowAttachMcp] = useState(false);
  const [confirmRemovePlugin, setConfirmRemovePlugin] = useState<PluginItem | null>(null);
  const [confirmDetachServer, setConfirmDetachServer] = useState<McpServerItem | null>(null);

  const plugins = pluginData?.items ?? [];
  const mcpServers = mcpData?.items ?? [];

  const handleRemovePlugin = () => {
    if (!confirmRemovePlugin) return;
    removePlugin.mutate(confirmRemovePlugin.id, {
      onSuccess: () => {
        toast.success(`Removed ${confirmRemovePlugin.name}`);
        setConfirmRemovePlugin(null);
      },
      onError: (e) => toast.error(e.message || "Failed to remove plugin"),
    });
  };

  const handleDetachServer = () => {
    if (!confirmDetachServer) return;
    detachServer.mutate(confirmDetachServer.id, {
      onSuccess: () => {
        toast.success(`Detached ${confirmDetachServer.name}`);
        setConfirmDetachServer(null);
      },
      onError: (e) => toast.error(e.message || "Failed to detach server"),
    });
  };

  const repoSlug = repo?.slug ?? repoId ?? "…";

  return (
    <Shell>
      <nav className="flex items-center gap-1.5 text-sm mb-1" aria-label="Breadcrumb">
        <NavLink
          to="/repos"
          className="text-text-muted hover:text-text transition-colors"
        >
          Repositories
        </NavLink>
        <span className="text-text-muted">/</span>
        <span className="font-mono text-text truncate">{repoSlug}</span>
      </nav>
      <PageHeader
        title="Extensions"
        subtitle="Plugins and MCP servers installed for this repository."
      />

      {/* ── Plugins ── */}
      <div className="mb-8">
        <SectionHeader
          icon={<Icons.plugin size={14} />}
          title="Plugins"
          count={plugins.length}
          action={
            <Button variant="primary" size="sm" onClick={() => setShowAddPlugin(true)}>
              <Icons.plus size={13} />
              Install plugin
            </Button>
          }
        />

        {pluginsLoading ? (
          <div className="flex flex-col gap-2">
            {[0, 1].map((i) => (
              <div key={i} className="bg-surface border border-border rounded p-4">
                <Skeleton className="h-5 w-48" />
              </div>
            ))}
          </div>
        ) : plugins.length === 0 ? (
          <EmptyState
            icon={<Icons.plugin size={20} />}
            title="No plugins installed"
            body="Upload a .zip archive or point to a Git repository."
            action={
              <Button variant="primary" size="sm" onClick={() => setShowAddPlugin(true)}>
                <Icons.plus size={13} />
                Install plugin
              </Button>
            }
          />
        ) : (
          <>
            <div className="grid grid-cols-[1fr_90px_80px_36px_32px] text-[11px] uppercase tracking-[.06em] text-text-muted px-4 mb-1.5 gap-3.5">
              <span>Plugin</span>
              <span className="text-right">Version pin</span>
              <span className="text-right">Last used</span>
              <span />
              <span />
            </div>
            <div className="flex flex-col gap-2">
              {plugins.map((p) => (
                <PluginRow
                  key={p.id}
                  plugin={p}
                  repoId={repoId!}
                  onRemove={setConfirmRemovePlugin}
                />
              ))}
            </div>
          </>
        )}
      </div>

      {/* ── MCP Servers ── */}
      <div>
        <SectionHeader
          icon={<Icons.mcpServer size={14} />}
          title="MCP Servers"
          count={mcpServers.length}
          action={
            <Button variant="primary" size="sm" onClick={() => setShowAttachMcp(true)}>
              <Icons.plus size={13} />
              Attach server
            </Button>
          }
        />

        {mcpLoading ? (
          <div className="flex flex-col gap-2">
            {[0].map((i) => (
              <div key={i} className="bg-surface border border-border rounded p-4">
                <Skeleton className="h-5 w-56" />
              </div>
            ))}
          </div>
        ) : mcpServers.length === 0 ? (
          <EmptyState
            icon={<Icons.mcpServer size={20} />}
            title="No MCP servers attached"
            body="Attach an MCP server by URL to give the worker model additional tools."
            action={
              <Button variant="primary" size="sm" onClick={() => setShowAttachMcp(true)}>
                <Icons.plus size={13} />
                Attach server
              </Button>
            }
          />
        ) : (
          <>
            <div className="grid grid-cols-[1fr_80px_36px_32px] text-[11px] uppercase tracking-[.06em] text-text-muted px-4 mb-1.5 gap-3.5">
              <span>Server</span>
              <span className="text-right">Last used</span>
              <span />
              <span />
            </div>
            <div className="flex flex-col gap-2">
              {mcpServers.map((s) => (
                <McpServerRow
                  key={s.id}
                  server={s}
                  repoId={repoId!}
                  onDetach={setConfirmDetachServer}
                />
              ))}
            </div>
          </>
        )}
      </div>

      {/* ── Modals ── */}
      {showAddPlugin && (
        <AddPluginModal repoId={repoId!} onClose={() => setShowAddPlugin(false)} />
      )}
      {showAttachMcp && (
        <AttachMcpModal repoId={repoId!} onClose={() => setShowAttachMcp(false)} />
      )}

      {confirmRemovePlugin && (
        <ConfirmModal
          title="Remove plugin?"
          body={
            <>
              <strong className="font-mono text-text">{confirmRemovePlugin.name}</strong> will be
              uninstalled from this repository. Running jobs will not be affected until they finish.
            </>
          }
          confirmLabel="Remove"
          pending={removePlugin.isPending}
          onCancel={() => setConfirmRemovePlugin(null)}
          onConfirm={handleRemovePlugin}
        />
      )}

      {confirmDetachServer && (
        <ConfirmModal
          title="Detach MCP server?"
          body={
            <>
              <strong className="font-mono text-text">{confirmDetachServer.name}</strong> will be
              detached. The server itself is not affected; you can re-attach it at any time.
            </>
          }
          confirmLabel="Detach"
          pending={detachServer.isPending}
          onCancel={() => setConfirmDetachServer(null)}
          onConfirm={handleDetachServer}
        />
      )}
    </Shell>
  );
}
