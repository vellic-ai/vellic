import { useRef, useState } from "react";
import Editor from "@monaco-editor/react";
import { Shell, PageHeader, EmptyState, Skeleton } from "@/components/Shell";
import { Icons, Spinner } from "@/components/icons";
import { Button } from "@/components/ui/button";
import {
  usePrompts,
  useCreatePrompt,
  useSavePrompt,
  useSetPromptEnabled,
  useDeletePrompt,
  useImportPrompts,
  useExportPrompts,
} from "@/api";
import { useToast } from "@/lib/toast";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Types (inline — generated schema types will be updated separately)
// ---------------------------------------------------------------------------

interface FrontmatterOut {
  scope: string[];
  triggers: string[];
  priority: number;
  inherits: string | null;
  variables: Record<string, string>;
}

interface PromptOut {
  name: string;
  source: string;
  frontmatter: FrontmatterOut;
  body: string;
  db_override: string | null;
  enabled: boolean;
}

// ---------------------------------------------------------------------------
// Source badge
// ---------------------------------------------------------------------------

function SourceBadge({ source }: { source: string }) {
  if (source === "db") {
    return (
      <span className="inline-flex items-center gap-1 text-[11px] font-medium px-1.5 py-0.5 rounded bg-accent/10 text-accent border border-accent/20">
        DB only
      </span>
    );
  }
  if (source === "preset+db") {
    return (
      <span className="inline-flex items-center gap-1 text-[11px] font-medium px-1.5 py-0.5 rounded bg-accent/10 text-accent border border-accent/20">
        DB override
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-[11px] px-1.5 py-0.5 rounded bg-surface-2 text-text-muted border border-border">
      preset default
    </span>
  );
}

// ---------------------------------------------------------------------------
// Monaco editor modal (shared for create + edit)
// ---------------------------------------------------------------------------

function EditorModal({
  title,
  subtitle,
  initialValue,
  onSave,
  onClose,
  isPending,
}: {
  title: string;
  subtitle?: string;
  initialValue: string;
  onSave: (body: string) => void;
  onClose: () => void;
  isPending: boolean;
}) {
  const [value, setValue] = useState(initialValue);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} aria-hidden="true" />
      <div className="relative bg-surface border border-border rounded-lg shadow-xl w-full max-w-3xl mx-4 flex flex-col max-h-[90vh]">
        <div className="flex items-center justify-between px-5 py-4 border-b border-border shrink-0">
          <div>
            <h2 className="text-[15px] font-semibold">{title}</h2>
            {subtitle && <p className="text-xs text-text-muted mt-0.5">{subtitle}</p>}
          </div>
          <button
            onClick={onClose}
            className="inline-flex w-7 h-7 items-center justify-center rounded text-text-muted hover:text-text hover:bg-surface-2"
            aria-label="Close"
          >
            <Icons.x size={16} />
          </button>
        </div>

        <div className="flex-1 overflow-hidden border-b border-border">
          <Editor
            height="420px"
            defaultLanguage="markdown"
            value={value}
            onChange={(v) => setValue(v ?? "")}
            theme="vs-dark"
            options={{
              fontSize: 13,
              lineNumbers: "on",
              minimap: { enabled: false },
              wordWrap: "on",
              scrollBeyondLastLine: false,
              renderLineHighlight: "gutter",
              tabSize: 2,
            }}
          />
        </div>

        <div className="flex items-center justify-end gap-2 px-5 py-3 shrink-0">
          <Button variant="ghost" size="sm" onClick={onClose} disabled={isPending}>
            Cancel
          </Button>
          <Button variant="primary" size="sm" onClick={() => onSave(value)} disabled={isPending}>
            {isPending && <Spinner size={12} />}
            Save
          </Button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Create prompt modal (name + editor)
// ---------------------------------------------------------------------------

const BLANK_PROMPT = `---
scope: []
triggers: []
priority: 50
---

Write your prompt instructions here.
`;

function CreateModal({ onClose }: { onClose: () => void }) {
  const [name, setName] = useState("");
  const [body, setBody] = useState(BLANK_PROMPT);
  const create = useCreatePrompt();
  const toast = useToast();

  const handleSave = () => {
    if (!name.trim()) {
      toast.error("Name is required");
      return;
    }
    create.mutate(
      { name: name.trim(), body },
      {
        onSuccess: () => {
          toast.success(`Created prompt "${name.trim()}"`);
          onClose();
        },
        onError: (e: Error) => toast.error(e.message || "Failed to create"),
      },
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} aria-hidden="true" />
      <div className="relative bg-surface border border-border rounded-lg shadow-xl w-full max-w-3xl mx-4 flex flex-col max-h-[90vh]">
        <div className="flex items-center justify-between px-5 py-4 border-b border-border shrink-0">
          <div>
            <h2 className="text-[15px] font-semibold">Create prompt</h2>
            <p className="text-xs text-text-muted mt-0.5">
              New prompts are stored in DB and served to workers immediately.
            </p>
          </div>
          <button
            onClick={onClose}
            className="inline-flex w-7 h-7 items-center justify-center rounded text-text-muted hover:text-text hover:bg-surface-2"
            aria-label="Close"
          >
            <Icons.x size={16} />
          </button>
        </div>

        <div className="px-5 pt-4 pb-2 shrink-0">
          <label className="block text-xs font-medium text-text-muted mb-1" htmlFor="prompt-name">
            Name <span className="text-error">*</span>
          </label>
          <input
            id="prompt-name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. security-review"
            className={cn(
              "w-full px-3 py-1.5 text-sm bg-surface-2 border border-border rounded",
              "focus:outline-none focus:ring-2 focus:ring-accent text-text font-mono",
            )}
          />
        </div>

        <div className="flex-1 overflow-hidden border-b border-border">
          <Editor
            height="360px"
            defaultLanguage="markdown"
            value={body}
            onChange={(v) => setBody(v ?? "")}
            theme="vs-dark"
            options={{
              fontSize: 13,
              lineNumbers: "on",
              minimap: { enabled: false },
              wordWrap: "on",
              scrollBeyondLastLine: false,
              tabSize: 2,
            }}
          />
        </div>

        <div className="flex items-center justify-end gap-2 px-5 py-3 shrink-0">
          <Button variant="ghost" size="sm" onClick={onClose} disabled={create.isPending}>
            Cancel
          </Button>
          <Button variant="primary" size="sm" onClick={handleSave} disabled={create.isPending}>
            {create.isPending && <Spinner size={12} />}
            Create
          </Button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Prompt card
// ---------------------------------------------------------------------------

function PromptCard({
  prompt,
  onEdit,
}: {
  prompt: PromptOut;
  onEdit: (p: PromptOut) => void;
}) {
  const setEnabled = useSetPromptEnabled();
  const deletePrompt = useDeletePrompt();
  const toast = useToast();

  const isDisabled = !prompt.enabled;
  const hasDbEntry = prompt.db_override !== null;

  const handleToggle = () => {
    setEnabled.mutate(
      { name: prompt.name, enabled: !prompt.enabled },
      {
        onSuccess: () =>
          toast.success(`Prompt "${prompt.name}" ${prompt.enabled ? "disabled" : "enabled"}`),
        onError: (e: Error) => toast.error(e.message || "Failed to update"),
      },
    );
  };

  const handleDelete = () => {
    const label = prompt.source === "preset" ? "revert to preset default" : "delete this prompt";
    if (!confirm(`Are you sure you want to ${label}?`)) return;
    deletePrompt.mutate(prompt.name, {
      onSuccess: () =>
        toast.success(
          prompt.source === "preset"
            ? `Reverted "${prompt.name}" to preset default`
            : `Deleted "${prompt.name}"`,
        ),
      onError: (e: Error) => toast.error(e.message || "Failed to delete"),
    });
  };

  return (
    <div
      className={cn(
        "bg-surface border rounded p-4 flex flex-col gap-3 transition-opacity",
        hasDbEntry ? "border-accent/30" : "border-border",
        isDisabled && "opacity-50",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <code className="font-mono text-[13px] font-semibold text-text">{prompt.name}</code>
            <SourceBadge source={prompt.source} />
            {isDisabled && (
              <span className="text-[11px] px-1.5 py-0.5 rounded bg-surface-2 text-text-muted border border-border">
                disabled
              </span>
            )}
          </div>
          <div className="text-xs text-text-muted mt-1">
            Priority {prompt.frontmatter.priority}
            {prompt.frontmatter.triggers.length > 0 && (
              <> · triggers: {prompt.frontmatter.triggers.join(", ")}</>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleToggle}
            disabled={setEnabled.isPending}
            className="text-xs text-text-muted"
            title={prompt.enabled ? "Disable" : "Enable"}
          >
            {setEnabled.isPending ? <Spinner size={12} /> : prompt.enabled ? "Disable" : "Enable"}
          </Button>
          {hasDbEntry && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleDelete}
              disabled={deletePrompt.isPending}
              className="text-xs text-text-muted hover:text-error"
              title={prompt.source === "preset" ? "Revert to preset" : "Delete"}
            >
              {deletePrompt.isPending ? <Spinner size={12} /> : prompt.source === "preset" ? "Revert" : "Delete"}
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={() => onEdit(prompt)} className="text-xs">
            Edit
          </Button>
        </div>
      </div>

      <div className="rounded border border-border bg-surface-2/30 p-3">
        <div className="text-[10.5px] uppercase tracking-[.07em] text-text-muted font-medium mb-1.5">
          {hasDbEntry ? "Active body (DB)" : "Preset body (active)"}
        </div>
        <pre className="text-xs text-text leading-relaxed whitespace-pre-wrap font-mono max-h-32 overflow-y-auto">
          {prompt.body}
        </pre>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Import button
// ---------------------------------------------------------------------------

function ImportButton() {
  const importPrompts = useImportPrompts();
  const toast = useToast();
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    if (!files.length) return;
    importPrompts.mutate(files, {
      onSuccess: ({ imported, errors }) => {
        if (imported.length) toast.success(`Imported: ${imported.join(", ")}`);
        if (errors.length) toast.error(`Errors: ${errors.join("; ")}`);
      },
      onError: (e: Error) => toast.error(e.message || "Import failed"),
    });
    e.target.value = "";
  };

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept=".md"
        multiple
        className="hidden"
        onChange={handleFiles}
      />
      <Button
        variant="outline"
        size="sm"
        onClick={() => inputRef.current?.click()}
        disabled={importPrompts.isPending}
        className="text-xs"
      >
        {importPrompts.isPending ? <Spinner size={12} /> : null}
        Import .md
      </Button>
    </>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function PromptsPage() {
  const { data, isLoading, isError } = usePrompts();
  const save = useSavePrompt();
  const exportPrompts = useExportPrompts();
  const toast = useToast();

  const [editing, setEditing] = useState<PromptOut | null>(null);
  const [creating, setCreating] = useState(false);

  const prompts = (data?.items ?? []) as PromptOut[];
  const dbCount = prompts.filter((p) => p.db_override !== null).length;
  const disabledCount = prompts.filter((p) => !p.enabled).length;

  const handleSave = (body: string) => {
    if (!editing) return;
    save.mutate(
      { name: editing.name, body },
      {
        onSuccess: () => {
          toast.success(`Saved "${editing.name}"`);
          setEditing(null);
        },
        onError: (e: Error) => toast.error(e.message || "Failed to save"),
      },
    );
  };

  return (
    <Shell>
      <PageHeader
        title="Prompts"
        subtitle="Manage review prompts. DB entries are served to workers; presets are the built-in fallback."
        extra={
          <div className="flex items-center gap-2 flex-wrap">
            {dbCount > 0 && (
              <span className="inline-flex items-center text-[11px] font-medium px-1.5 py-0.5 rounded bg-accent/10 text-accent border border-accent/20">
                {dbCount} in DB
              </span>
            )}
            {disabledCount > 0 && (
              <span className="inline-flex items-center text-[11px] px-1.5 py-0.5 rounded bg-surface-2 text-text-muted border border-border">
                {disabledCount} disabled
              </span>
            )}
            <ImportButton />
            <Button
              variant="outline"
              size="sm"
              onClick={() => exportPrompts.mutate(undefined)}
              disabled={exportPrompts.isPending || dbCount === 0}
              className="text-xs"
              title="Download all DB prompts as zip"
            >
              Export .zip
            </Button>
            <Button variant="primary" size="sm" onClick={() => setCreating(true)} className="text-xs">
              <Icons.plus size={14} />
              New prompt
            </Button>
          </div>
        }
      />

      {isLoading ? (
        <div className="flex flex-col gap-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="bg-surface border border-border rounded p-4">
              <Skeleton className="h-4 w-40 mb-2" />
              <Skeleton className="h-3 w-64 mb-3" />
              <Skeleton className="h-20 w-full" />
            </div>
          ))}
        </div>
      ) : isError ? (
        <div className="bg-surface border border-error/30 rounded p-6 text-center">
          <div className="inline-flex w-9 h-9 rounded-lg bg-error/10 text-error items-center justify-center mb-3">
            <Icons.warn size={18} />
          </div>
          <div className="text-sm font-medium mb-1">Failed to load prompts</div>
          <div className="text-xs text-text-muted">
            The Prompt DSL feature may be disabled. Enable it in Feature Flags → platform.prompt_dsl.
          </div>
        </div>
      ) : prompts.length === 0 ? (
        <EmptyState
          icon={<Icons.flags size={20} />}
          title="No prompts found"
          body="No presets were loaded. Check VELLIC_PRESETS_DIR and that platform.prompt_dsl is enabled."
        />
      ) : (
        <div className="flex flex-col gap-4">
          {prompts.map((prompt) => (
            <PromptCard key={prompt.name} prompt={prompt} onEdit={setEditing} />
          ))}
        </div>
      )}

      {editing && (
        <EditorModal
          title={`Edit: ${editing.name}`}
          subtitle="Changes are saved to DB and served to workers immediately. Revert removes the DB entry."
          initialValue={editing.db_override ?? editing.body}
          onSave={handleSave}
          onClose={() => setEditing(null)}
          isPending={save.isPending}
        />
      )}

      {creating && <CreateModal onClose={() => setCreating(false)} />}
    </Shell>
  );
}
