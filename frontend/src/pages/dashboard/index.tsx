import { useNavigate } from "react-router";
import { Shell, PageHeader, Skeleton, EmptyState, StatusDot } from "@/components/Shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Icons } from "@/components/icons";
import { useStats } from "@/api";
import { useDeliveries } from "@/api";
import { useRepos } from "@/api";
import { useToast } from "@/lib/toast";
import { useQueryClient } from "@tanstack/react-query";
import { statsKeys } from "@/api/hooks/stats";
import { cn } from "@/lib/utils";

function fmtRelative(ts: string | null | undefined) {
  if (!ts) return "—";
  const diff = Date.now() - new Date(ts).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

function StatTile({
  label,
  value,
  sub,
  accent,
  loading,
}: {
  label: string;
  value: string | number | null | undefined;
  sub?: string;
  accent?: "error" | null;
  loading?: boolean;
}) {
  return (
    <div className="bg-surface border border-border rounded p-5">
      <div className="text-xs text-text-muted mb-2 uppercase tracking-[.04em] font-medium">
        {label}
      </div>
      {loading ? (
        <Skeleton className="h-7 w-20 mb-1" />
      ) : (
        <div
          className={cn(
            "text-[26px] font-semibold tracking-tight mb-0.5",
            accent === "error" && "text-error",
          )}
        >
          {value ?? "—"}
        </div>
      )}
      {sub && (
        <div className="text-xs text-text-muted">{sub}</div>
      )}
    </div>
  );
}

const CLOUD_PROVIDERS = ["openai", "anthropic", "claude_code"];

function isCloud(provider: string) {
  return CLOUD_PROVIDERS.includes(provider);
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const qc = useQueryClient();

  const { data: stats, isLoading: statsLoading, isError: statsError } = useStats(30_000);
  const { data: deliveries, isLoading: delivLoading } = useDeliveries({ limit: 6 });
  const { data: repos } = useRepos();

  const activeRepos = (repos?.items ?? []).filter((r) => r.enabled);
  const cloudRepos = activeRepos.filter((r) => isCloud(r.provider));
  const providers = Array.from(new Set(activeRepos.map((r) => r.provider)));
  const hasRepos = (repos?.items.length ?? 0) > 0;
  const recentDeliveries = deliveries?.items ?? [];

  const handleRetry = () => {
    qc.invalidateQueries({ queryKey: statsKeys.all() });
    toast.info("Refreshing stats…");
  };

  return (
    <Shell>
      <PageHeader
        title="Dashboard"
        extra={
          <>
            {activeRepos.length > 0 && (
              <Badge variant="info" className="text-xs">
                <StatusDot status="processed" />
                {activeRepos.length} active {activeRepos.length === 1 ? "repo" : "repos"} ·{" "}
                {providers.length} {providers.length === 1 ? "provider" : "providers"}
              </Badge>
            )}
            {cloudRepos.length > 0 && (
              <Badge variant="warning" className="text-xs gap-1">
                <Icons.warn size={12} />
                {cloudRepos.length} {cloudRepos.length === 1 ? "repo uses" : "repos use"} a cloud
                provider
              </Badge>
            )}
          </>
        }
      />

      {statsError && (
        <div className="flex items-center justify-between gap-3 bg-warning-bg border border-warning-border rounded p-3 mb-4 text-sm text-warning-text">
          <span className="flex items-center gap-2">
            <Icons.warn size={14} />
            Could not load stats — connection refused
          </span>
          <Button size="sm" variant="default" onClick={handleRetry}>
            <Icons.refresh size={13} />
            Retry
          </Button>
        </div>
      )}

      {/* Stats grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5 mb-6">
        <StatTile
          label="PRs reviewed"
          value={statsError ? "—" : stats?.prs_reviewed_24h}
          sub={statsError ? "unavailable" : `${stats?.prs_reviewed_7d ?? "—"} past 7d`}
          loading={statsLoading}
        />
        <StatTile
          label="p50 latency"
          value={
            statsError
              ? "—"
              : stats?.latency_p50_ms != null
                ? `${(stats.latency_p50_ms / 1000).toFixed(2)}s`
                : null
          }
          sub="time to post review"
          loading={statsLoading}
        />
        <StatTile
          label="p95 latency"
          value={
            statsError
              ? "—"
              : stats?.latency_p95_ms != null
                ? `${(stats.latency_p95_ms / 1000).toFixed(2)}s`
                : null
          }
          sub="tail latency"
          loading={statsLoading}
        />
        <StatTile
          label="Failure rate"
          value={
            statsError
              ? "—"
              : stats?.failure_rate_pct != null
                ? `${stats.failure_rate_pct}%`
                : null
          }
          sub="past 24h"
          accent={!statsError && (stats?.failure_rate_pct ?? 0) > 5 ? "error" : null}
          loading={statsLoading}
        />
      </div>

      {/* Recent activity */}
      {!hasRepos ? (
        <EmptyState
          icon={<Icons.repos size={22} />}
          title="No repositories yet"
          body="Vellic is idle until you add a repository for it to watch."
          action={
            <Button variant="primary" onClick={() => navigate("/repos")}>
              <Icons.plus size={14} />
              Add your first repository
            </Button>
          }
        />
      ) : (
        <div className="bg-surface border border-border rounded">
          <div className="flex items-center justify-between px-[18px] py-3.5 border-b border-border">
            <span className="text-sm font-medium">Recent activity</span>
            <button
              className="text-sm text-text-muted hover:text-text inline-flex items-center gap-1 transition-colors"
              onClick={() => navigate("/deliveries")}
            >
              View all <Icons.chevronRight size={14} />
            </button>
          </div>

          {delivLoading ? (
            <div className="p-5 flex flex-col gap-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="flex items-center gap-4">
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-4 flex-1" />
                  <Skeleton className="h-4 w-20" />
                </div>
              ))}
            </div>
          ) : recentDeliveries.length === 0 ? (
            <div className="p-10 text-center text-text-muted text-sm">
              No deliveries yet. Send a test webhook from your VCS.
            </div>
          ) : (
            <div>
              {recentDeliveries.map((d) => (
                <div
                  key={d.delivery_id}
                  className={cn(
                    "grid items-center px-[18px] py-2.5 border-b border-border last:border-b-0",
                    "gap-3",
                  )}
                  style={{ gridTemplateColumns: "100px 1fr 140px 110px" }}
                >
                  <span className="font-mono text-xs text-text-muted truncate">
                    {d.delivery_id.slice(0, 8)}…
                  </span>
                  <span className="font-mono text-xs truncate">{d.event_type}</span>
                  <span className="text-xs text-text-muted" title={d.received_at ?? ""}>
                    {fmtRelative(d.received_at)}
                  </span>
                  <DeliveryStatus status={d.status ?? "queued"} />
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </Shell>
  );
}

function DeliveryStatus({ status }: { status: string }) {
  if (status === "processed")
    return (
      <Badge variant="success" className="text-xs">
        <StatusDot status="processed" /> processed
      </Badge>
    );
  if (status === "failed")
    return (
      <Badge variant="error" className="text-xs">
        <StatusDot status="failed" /> failed
      </Badge>
    );
  return (
    <Badge variant="default" className="text-xs">
      <StatusDot status="queued" /> queued
    </Badge>
  );
}
