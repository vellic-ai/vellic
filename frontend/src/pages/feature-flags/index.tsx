import { useState, useMemo } from "react";
import { Shell, PageHeader, Skeleton } from "@/components/Shell";
import { Icons, Spinner } from "@/components/icons";
import { Input } from "@/components/ui/input";
import { useFeatureFlags, useSetFeatureFlag } from "@/api";
import { useToast } from "@/lib/toast";
import { cn } from "@/lib/utils";
import type { components } from "@/api/schema";

type FlagItem = components["schemas"]["FeaturesResponse"]["catalog"][number];

const SCOPE_LABELS: Record<string, string> = {
  global: "Global",
  tenant: "Tenant",
  repo: "Repo",
};


function FlagToggle({
  flag,
  onToggle,
  pending,
}: {
  flag: FlagItem;
  onToggle: (flag: FlagItem) => void;
  pending: boolean;
}) {
  const isOn = flag.enabled;

  return (
    <label className="inline-flex items-center gap-2 cursor-pointer select-none">
      {pending ? (
        <span className="inline-flex w-9 h-5 items-center justify-center">
          <Spinner size={12} />
        </span>
      ) : (
        <button
          role="switch"
          aria-checked={isOn}
          aria-label={`${isOn ? "Disable" : "Enable"} ${flag.key}`}
          onClick={() => onToggle(flag)}
          className={cn(
            "relative inline-flex h-5 w-9 shrink-0 rounded-full border-2 border-transparent",
            "transition-colors duration-[120ms] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent",
            isOn ? "bg-accent" : "bg-surface-2 border border-border",
          )}
        >
          <span
            className={cn(
              "pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow-sm transition-transform duration-[120ms]",
              isOn ? "translate-x-4" : "translate-x-0",
            )}
          />
        </button>
      )}
      <span
        className={cn(
          "text-xs min-w-[38px]",
          isOn ? "text-success" : "text-text-muted",
        )}
      >
        {isOn ? "On" : "Off"}
      </span>
    </label>
  );
}

function FlagRow({
  flag,
  onToggle,
  pendingKey,
}: {
  flag: FlagItem;
  onToggle: (flag: FlagItem) => void;
  pendingKey: string | null;
}) {
  const isPending = pendingKey === flag.key;

  return (
    <tr className="border-b border-border last:border-0">
      <td className="py-3 pl-4 pr-3 align-top">
        <code className="font-mono text-[12.5px] text-text">{flag.key}</code>
        {flag.description && (
          <div className="text-xs text-text-muted mt-0.5 leading-snug">
            {flag.description}
          </div>
        )}
      </td>

      <td className="py-3 px-3 align-top">
        <span
          className={cn(
            "inline-flex text-[11px] px-1.5 py-0.5 rounded border font-mono",
            flag.default
              ? "text-success bg-success/10 border-success/20"
              : "text-text-muted bg-surface-2 border-border",
          )}
        >
          {flag.default ? "true" : "false"}
        </span>
      </td>

      <td className="py-3 px-3 align-top hidden sm:table-cell">
        <span className="text-xs text-text-muted">
          {SCOPE_LABELS[flag.scope] ?? flag.scope}
        </span>
      </td>

      <td className="py-3 pl-3 pr-4 align-middle text-right">
        <FlagToggle flag={flag} onToggle={onToggle} pending={isPending} />
      </td>
    </tr>
  );
}

export default function FeatureFlagsPage() {
  const toast = useToast();
  const { data, isLoading, isError } = useFeatureFlags();
  const setFlag = useSetFeatureFlag();
  const [search, setSearch] = useState("");
  const [pendingKey, setPendingKey] = useState<string | null>(null);

  const flags = data?.catalog ?? [];

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return flags;
    return flags.filter(
      (f) =>
        f.key.toLowerCase().includes(q) ||
        f.description.toLowerCase().includes(q),
    );
  }, [flags, search]);

  const handleToggle = (flag: FlagItem) => {
    if (pendingKey) return;
    const next = !flag.enabled;
    setPendingKey(flag.key);
    setFlag.mutate(
      { key: flag.key, body: { enabled: next } },
      {
        onSuccess: () => {
          toast.success(`${flag.key} ${next ? "enabled" : "disabled"}`);
        },
        onError: (e) => {
          toast.error(e.message || "Failed to update flag");
        },
        onSettled: () => {
          setPendingKey(null);
        },
      },
    );
  };

  return (
    <Shell>
      <PageHeader
        title="Feature Flags"
        subtitle="Toggle runtime flags without redeploying. Overrides persist in the database."
      />

      <div className="relative mb-4 max-w-sm">
        <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-text-muted pointer-events-none">
          <Icons.search size={14} />
        </span>
        <Input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search flags…"
          className="pl-8"
          aria-label="Search feature flags"
        />
      </div>

      {isLoading ? (
        <div className="bg-surface border border-border rounded overflow-hidden">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="px-4 py-3.5 border-b border-border last:border-0">
              <Skeleton className="h-4 w-48 mb-1.5" />
              <Skeleton className="h-3 w-72" />
            </div>
          ))}
        </div>
      ) : isError ? (
        <div className="bg-surface border border-error/30 rounded p-6 text-center">
          <div className="inline-flex w-9 h-9 rounded-lg bg-error/10 text-error items-center justify-center mb-3">
            <Icons.warn size={18} />
          </div>
          <div className="text-sm font-medium mb-1">Failed to load flags</div>
          <div className="text-xs text-text-muted">Check the admin service is reachable.</div>
        </div>
      ) : filtered.length === 0 ? (
        <div className="bg-surface border border-border rounded p-10 text-center">
          <div className="inline-flex w-9 h-9 rounded-lg bg-surface-2 text-text-muted items-center justify-center mb-3">
            <Icons.flags size={18} />
          </div>
          <div className="text-sm font-medium mb-1">
            {search ? "No flags match your search" : "No feature flags configured"}
          </div>
          {search && (
            <button
              className="text-xs text-accent hover:underline mt-1"
              onClick={() => setSearch("")}
            >
              Clear search
            </button>
          )}
        </div>
      ) : (
        <div className="bg-surface border border-border rounded overflow-hidden">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b border-border bg-surface-2/50">
                <th className="py-2.5 pl-4 pr-3 text-left text-[11px] uppercase tracking-[.06em] text-text-muted font-medium">
                  Flag
                </th>
                <th className="py-2.5 px-3 text-left text-[11px] uppercase tracking-[.06em] text-text-muted font-medium">
                  Default
                </th>
                <th className="py-2.5 px-3 text-left text-[11px] uppercase tracking-[.06em] text-text-muted font-medium hidden sm:table-cell">
                  Scope
                </th>
                <th className="py-2.5 pl-3 pr-4 text-right text-[11px] uppercase tracking-[.06em] text-text-muted font-medium">
                  Value
                </th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((flag) => (
                <FlagRow
                  key={flag.key}
                  flag={flag}
                  onToggle={handleToggle}
                  pendingKey={pendingKey}
                />
              ))}
            </tbody>
          </table>
          {search && filtered.length < flags.length && (
            <div className="px-4 py-2.5 border-t border-border text-xs text-text-muted">
              Showing {filtered.length} of {flags.length} flags
            </div>
          )}
        </div>
      )}
    </Shell>
  );
}
