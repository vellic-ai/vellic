import * as React from "react";
import { useNavigate } from "react-router";
import { Shell, PageHeader, Skeleton, EmptyState, StatusDot } from "@/components/Shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Icons } from "@/components/icons";
import { useStats, useJobs, useRepos } from "@/api";
import { useToast } from "@/lib/toast";
import { useQueryClient } from "@tanstack/react-query";
import { statsKeys } from "@/api/hooks/stats";
import { jobKeys } from "@/api/hooks/jobs";
import { cn } from "@/lib/utils";
import type { components } from "@/api/schema";

type JobItem = components["schemas"]["JobItem"];

// ─── Helpers ────────────────────────────────────────────────────────────────

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

function fmtDuration(ms: number | null | undefined) {
  if (ms == null) return null;
  if (ms < 1000) return `${ms}ms`;
  const s = ms / 1000;
  if (s < 60) return `${s.toFixed(1)}s`;
  return `${Math.floor(s / 60)}m ${Math.round(s % 60)}s`;
}

function jobStatusVariant(status: string): "success" | "error" | "default" | "warning" {
  if (status === "done" || status === "processed") return "success";
  if (status === "failed" || status === "error") return "error";
  if (status === "running") return "warning";
  return "default";
}

function jobStatusDot(status: string): "processed" | "failed" | "running" | "queued" {
  if (status === "done" || status === "processed") return "processed";
  if (status === "failed" || status === "error") return "failed";
  if (status === "running") return "running";
  return "queued";
}

// ─── Stat Tile ───────────────────────────────────────────────────────────────

function StatTile({
  label,
  value,
  sub,
  accent,
  loading,
  icon,
}: {
  label: string;
  value: string | number | null | undefined;
  sub?: string;
  accent?: "error" | "success" | null;
  loading?: boolean;
  icon?: React.ReactNode;
}) {
  return (
    <div data-testid="metric-card" className="bg-surface border border-border rounded-lg p-5">
      <div className="flex items-start justify-between mb-3">
        <div className="text-xs text-text-muted uppercase tracking-[.04em] font-medium">
          {label}
        </div>
        {icon && (
          <span className="inline-flex w-7 h-7 items-center justify-center rounded-md bg-surface-2 text-text-muted shrink-0">
            {icon}
          </span>
        )}
      </div>
      {loading ? (
        <Skeleton className="h-7 w-20 mb-1" />
      ) : (
        <div
          className={cn(
            "text-[26px] font-semibold tracking-tight mb-0.5",
            accent === "error" && "text-error",
            accent === "success" && "text-success",
          )}
        >
          {value ?? "—"}
        </div>
      )}
      {sub && <div className="text-xs text-text-muted mt-0.5">{sub}</div>}
    </div>
  );
}

// ─── LLM Cost Bar ────────────────────────────────────────────────────────────

interface CostBarProps {
  label: string;
  value: number;
  max: number;
  color?: string;
}

function CostBar({ label, value, max, color = "bg-accent" }: CostBarProps) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  return (
    <div className="flex items-center gap-3 text-xs">
      <span className="text-text-muted w-24 shrink-0 truncate">{label}</span>
      <div className="flex-1 bg-surface-2 rounded-full h-1.5 overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all duration-500", color)}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-text-muted w-10 text-right font-mono">{value}</span>
    </div>
  );
}

// ─── LLM Cost Panel ──────────────────────────────────────────────────────────

function LLMCostPanel({
  provider,
  model,
  jobCount,
  loading,
}: {
  provider: string | null | undefined;
  model: string | null | undefined;
  jobCount: number;
  loading: boolean;
}) {
  // Estimated token usage per job varies by model — rough heuristics for display
  const modelLabel = model ?? "unknown";
  const providerLabel = provider ?? "unknown";

  const isAnthropic = providerLabel === "anthropic" || providerLabel === "claude_code";
  const inputTokensPerJob = isAnthropic ? 3200 : 2800;
  const outputTokensPerJob = isAnthropic ? 480 : 350;

  const totalInput = jobCount * inputTokensPerJob;
  const totalOutput = jobCount * outputTokensPerJob;

  // Rough cost estimates (USD per 1K tokens)
  const inputCostPer1k = isAnthropic ? 0.003 : 0.002;
  const outputCostPer1k = isAnthropic ? 0.015 : 0.008;
  const estimatedCost = (totalInput / 1000) * inputCostPer1k + (totalOutput / 1000) * outputCostPer1k;

  const maxTokens = Math.max(totalInput, totalOutput, 1);

  return (
    <div className="bg-surface border border-border rounded-lg overflow-hidden">
      <div className="flex items-center justify-between px-[18px] py-3.5 border-b border-border">
        <span className="text-sm font-medium flex items-center gap-2">
          <span className="inline-flex w-4 h-4 text-text-muted">
            <Icons.llm size={14} />
          </span>
          LLM usage
        </span>
        {!loading && provider && (
          <Badge variant="default" className="text-xs font-mono">
            {providerLabel}
          </Badge>
        )}
      </div>

      <div className="p-[18px]">
        {loading ? (
          <div className="flex flex-col gap-3">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
          </div>
        ) : !provider ? (
          <div className="text-center py-6">
            <div className="text-text-muted text-sm mb-2">No provider configured</div>
            <div className="text-xs text-text-muted">Set up an LLM provider in Settings to see usage data.</div>
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            {/* Model badge */}
            <div className="flex items-center gap-2 text-xs text-text-muted">
              <span>Model</span>
              <span className="font-mono text-text bg-surface-2 px-1.5 py-0.5 rounded text-[11px]">
                {modelLabel}
              </span>
            </div>

            {/* Token bars */}
            <div className="flex flex-col gap-2.5">
              <div className="text-[10.5px] text-text-muted uppercase tracking-[.06em] mb-1">
                Token usage · last 24h
              </div>
              <CostBar
                label="Input tokens"
                value={totalInput}
                max={maxTokens}
                color="bg-accent"
              />
              <CostBar
                label="Output tokens"
                value={totalOutput}
                max={maxTokens}
                color="bg-success"
              />
            </div>

            {/* Cost estimate */}
            <div className="bg-surface-2 rounded-lg p-3 flex items-center justify-between">
              <div>
                <div className="text-[10.5px] text-text-muted uppercase tracking-[.06em] mb-0.5">
                  Est. cost · 24h
                </div>
                <div className="text-xl font-semibold tracking-tight">
                  ${estimatedCost.toFixed(4)}
                </div>
              </div>
              <div className="text-right text-xs text-text-muted">
                <div>{jobCount} jobs</div>
                <div className="mt-0.5 font-mono">{(totalInput + totalOutput).toLocaleString()} tok</div>
              </div>
            </div>

            <p className="text-[11px] text-text-muted leading-relaxed">
              Estimates based on typical usage patterns. Exact billing is shown in your provider dashboard.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Job Timeline Row ─────────────────────────────────────────────────────────

// Mock checks for drilldown — real data would come from a /admin/jobs/:id endpoint
const MOCK_CHECKS = [
  { name: "code-review", status: "passed", calls: 3 },
  { name: "security-scan", status: "passed", calls: 1 },
  { name: "style-lint", status: "failed", calls: 2 },
  { name: "docs-check", status: "skipped", calls: 0 },
];

function CheckRow({ name, status, calls }: { name: string; status: string; calls: number }) {
  const icon =
    status === "passed" ? (
      <span className="text-success">
        <Icons.check size={13} />
      </span>
    ) : status === "failed" ? (
      <span className="text-error">
        <Icons.x size={13} />
      </span>
    ) : (
      <span className="text-text-muted">
        <Icons.chevronRight size={13} />
      </span>
    );

  return (
    <div className="flex items-center gap-2.5 text-xs">
      <span className="inline-flex w-3.5 shrink-0">{icon}</span>
      <span
        className={cn(
          "font-mono flex-1",
          status === "failed" ? "text-error" : status === "skipped" ? "text-text-muted" : "text-text",
        )}
      >
        {name}
      </span>
      {calls > 0 && (
        <span className="text-text-muted">{calls} LLM {calls === 1 ? "call" : "calls"}</span>
      )}
    </div>
  );
}

function JobTimelineRow({ job }: { job: JobItem }) {
  const [expanded, setExpanded] = React.useState(false);

  const statusVariant = jobStatusVariant(job.status);
  const statusDot = jobStatusDot(job.status);
  const duration = fmtDuration(job.duration_ms);
  const hasError = !!job.error;
  const hasRetries = job.retry_count > 0;

  return (
    <div
      className={cn(
        "border-b border-border last:border-b-0 transition-colors",
        expanded && "bg-surface-2/40",
      )}
    >
      {/* Main row */}
      <button
        className="w-full text-left px-[18px] py-3 flex items-center gap-3 hover:bg-surface-2/30 transition-colors"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
      >
        {/* Status */}
        <span className="shrink-0">
          <StatusDot status={statusDot} />
        </span>

        {/* PR ref */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            {job.repo && (
              <span className="font-mono text-xs text-text-muted truncate max-w-[120px]">
                {job.repo.split("/").pop()}
              </span>
            )}
            {job.pr_number && (
              <span className="font-mono text-xs text-text font-medium">
                #{job.pr_number}
              </span>
            )}
            {!job.repo && !job.pr_number && (
              <span className="font-mono text-xs text-text-muted">no PR ref</span>
            )}
            {hasRetries && (
              <Badge variant="warning" className="text-[10px] px-1.5 py-0">
                {job.retry_count}× retry
              </Badge>
            )}
          </div>
          <div className="text-[11px] text-text-muted mt-0.5 font-mono truncate">
            {job.id.slice(0, 12)}…
          </div>
        </div>

        {/* Meta */}
        <div className="flex items-center gap-3 shrink-0">
          {duration && (
            <span className="text-xs text-text-muted font-mono">{duration}</span>
          )}
          <Badge variant={statusVariant} className="text-xs">
            <StatusDot status={statusDot} />
            {job.status}
          </Badge>
          <span className="text-[11px] text-text-muted">{fmtRelative(job.created_at)}</span>
          <span
            className={cn(
              "inline-flex w-3.5 h-3.5 text-text-muted transition-transform",
              expanded && "rotate-90",
            )}
          >
            <Icons.chevronRight size={13} />
          </span>
        </div>
      </button>

      {/* Drilldown */}
      {expanded && (
        <div className="px-[18px] pb-4 pt-1">
          {/* Error banner */}
          {hasError && (
            <div className="mb-3 flex items-start gap-2 text-xs text-error bg-error/8 border border-error/20 rounded-md p-2.5">
              <span className="inline-flex w-3.5 shrink-0 mt-0.5">
                <Icons.warn size={12} />
              </span>
              <span className="font-mono break-all">{job.error}</span>
            </div>
          )}

          {/* Checks grid */}
          <div className="bg-surface border border-border rounded-md p-3">
            <div className="text-[10.5px] text-text-muted uppercase tracking-[.06em] mb-2.5">
              Checks · {job.platform}
            </div>
            <div className="flex flex-col gap-1.5">
              {MOCK_CHECKS.map((c) => (
                <CheckRow key={c.name} {...c} />
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Job Timeline Section ─────────────────────────────────────────────────────

function JobTimeline() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { data, isLoading, isError, refetch } = useJobs({ limit: 10 });
  const jobs = data?.items ?? [];

  const handleRefresh = () => {
    qc.invalidateQueries({ queryKey: jobKeys.all() });
  };

  return (
    <div className="bg-surface border border-border rounded-lg overflow-hidden">
      <div className="flex items-center justify-between px-[18px] py-3.5 border-b border-border">
        <span className="text-sm font-medium flex items-center gap-2">
          <span className="inline-flex w-4 h-4 text-text-muted">
            <Icons.jobs size={14} />
          </span>
          Job timeline
        </span>
        <div className="flex items-center gap-2">
          <button
            className="inline-flex w-6 h-6 items-center justify-center rounded text-text-muted hover:text-text hover:bg-surface-2 transition-colors"
            onClick={handleRefresh}
            title="Refresh"
          >
            <Icons.refresh size={13} />
          </button>
          <button
            className="text-sm text-text-muted hover:text-text inline-flex items-center gap-1 transition-colors"
            onClick={() => navigate("/jobs")}
          >
            All jobs <Icons.chevronRight size={13} />
          </button>
        </div>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="p-5 flex flex-col gap-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="flex items-center gap-3">
              <Skeleton className="h-3 w-3 rounded-full" />
              <Skeleton className="h-3.5 w-24" />
              <Skeleton className="h-3.5 flex-1" />
              <Skeleton className="h-5 w-16 rounded-full" />
              <Skeleton className="h-3 w-14" />
            </div>
          ))}
        </div>
      )}

      {/* Error state */}
      {isError && !isLoading && (
        <div className="px-[18px] py-10 text-center">
          <div className="inline-flex w-10 h-10 rounded-full bg-error/10 items-center justify-center text-error mb-3">
            <Icons.warn size={16} />
          </div>
          <div className="text-sm font-medium mb-1">Failed to load jobs</div>
          <div className="text-xs text-text-muted mb-4">
            Could not reach the job pipeline. Check that the backend is running.
          </div>
          <Button size="sm" variant="default" onClick={() => refetch()}>
            <Icons.refresh size={13} />
            Retry
          </Button>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !isError && jobs.length === 0 && (
        <div className="px-[18px] py-10 text-center">
          <div className="inline-flex w-10 h-10 rounded-full bg-surface-2 items-center justify-center text-text-muted mb-3">
            <Icons.jobs size={16} />
          </div>
          <div className="text-sm font-medium mb-1">No jobs yet</div>
          <div className="text-xs text-text-muted">
            Jobs will appear here when Vellic processes a PR event.
          </div>
        </div>
      )}

      {/* Job rows */}
      {!isLoading && !isError && jobs.length > 0 && (
        <div>
          {jobs.map((job) => (
            <JobTimelineRow key={job.id} job={job} />
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Main Dashboard ───────────────────────────────────────────────────────────

const CLOUD_PROVIDERS = ["openai", "anthropic", "claude_code"];

function isCloud(provider: string) {
  return CLOUD_PROVIDERS.includes(provider);
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const qc = useQueryClient();

  const { data: stats, isLoading: statsLoading, isError: statsError } = useStats(30_000);
  const { data: repos } = useRepos();
  const { data: jobsData, isLoading: jobsLoading } = useJobs({ limit: 10 });

  const activeRepos = (repos?.items ?? []).filter((r) => r.enabled);
  const cloudRepos = activeRepos.filter((r) => isCloud(r.provider));
  const providers = Array.from(new Set(activeRepos.map((r) => r.provider)));
  const hasRepos = (repos?.items.length ?? 0) > 0;
  const jobCount = jobsData?.total ?? 0;

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

      {/* Stats error banner */}
      {statsError && (
        <div className="flex items-center justify-between gap-3 bg-warning-bg border border-warning-border rounded-lg p-3 mb-5 text-sm text-warning-text">
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

      {/* Stat tiles — always rendered */}
      <div data-testid="dashboard-metrics" className="grid grid-cols-2 lg:grid-cols-4 gap-3.5 mb-6">
        <StatTile
          label="PRs reviewed"
          value={statsError ? "—" : stats?.prs_reviewed_24h}
          sub={statsError ? "unavailable" : `${stats?.prs_reviewed_7d ?? "—"} past 7d`}
          loading={statsLoading}
          icon={<Icons.deliveries size={13} />}
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
          icon={<Icons.jobs size={13} />}
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
          icon={<Icons.jobs size={13} />}
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
          icon={<Icons.warn size={13} />}
        />
      </div>

      {/* No repos: prompt to add one */}
      {!statsLoading && !hasRepos ? (
        <EmptyState
          icon={<Icons.repos size={22} />}
          title="No repositories connected"
          body="Vellic is idle. Add a repository to start reviewing PRs automatically."
          action={
            <Button variant="primary" onClick={() => navigate("/repos")}>
              <Icons.plus size={14} />
              Add your first repository
            </Button>
          }
        />
      ) : (
        /* Main content: timeline + cost panel */
        <div className="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-5">
          {/* Job timeline */}
          <JobTimeline />

          {/* LLM cost panel */}
          <LLMCostPanel
            provider={stats?.llm_provider}
            model={stats?.llm_model}
            jobCount={jobCount}
            loading={statsLoading || jobsLoading}
          />
        </div>
      )}
    </Shell>
  );
}
