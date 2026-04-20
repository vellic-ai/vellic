import { useState } from "react";
import { Shell, PageHeader, StatusDot, EmptyState, Skeleton } from "@/components/Shell";
import { Badge } from "@/components/ui/badge";
import { NativeSelect } from "@/components/ui/native-select";
import { Icons, Spinner } from "@/components/icons";
import { useJobs } from "@/api";
import type { components } from "@/api/schema";
import { cn } from "@/lib/utils";

type Job = components["schemas"]["JobItem"];

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

function fmtAbsolute(ts: string | null | undefined) {
  if (!ts) return "";
  return new Date(ts).toLocaleString();
}

function fmtDuration(ms: number | null | undefined) {
  if (ms == null) return "—";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function JobStatusBadge({ status }: { status: string }) {
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
  if (status === "running")
    return (
      <Badge variant="info" className="text-xs">
        <Spinner size={10} /> running
      </Badge>
    );
  return (
    <Badge variant="default" className="text-xs">
      <StatusDot status="queued" /> queued
    </Badge>
  );
}

const STAGES = [
  { key: "fetch", label: "Fetch" },
  { key: "analyze", label: "Analyze" },
  { key: "format", label: "Format" },
  { key: "post", label: "Post" },
] as const;

function StageIcon({ status }: { status: string }) {
  if (status === "done") return <Icons.check size={12} className="text-success" />;
  if (status === "running") return <Spinner size={12} />;
  if (status === "failed") return <Icons.x size={12} className="text-error" />;
  return (
    <span className="w-2.5 h-2.5 rounded-full border border-border inline-block" />
  );
}

function JobDrawer({ job, onClose }: { job: Job; onClose: () => void }) {
  const stageStatus = (i: number): string => {
    if (job.status === "processed") return "done";
    if (job.status === "failed") return i === 0 ? "failed" : "pending";
    if (job.status === "running") return i === 0 ? "running" : "pending";
    return "pending";
  };

  return (
    <>
      <div
        className="fixed inset-0 z-40 bg-black/50 animate-fade-in"
        onClick={onClose}
        aria-hidden="true"
      />
      <aside
        className="fixed top-0 right-0 h-full w-[420px] max-w-[95vw] bg-surface border-l border-border z-50 flex flex-col animate-drawer-in"
        aria-label="Job details"
        role="dialog"
        aria-modal="true"
      >
        {/* Header */}
        <div className="flex items-start justify-between px-5 py-4 border-b border-border">
          <div>
            <div className="text-[10.5px] uppercase tracking-[.06em] text-text-muted mb-1">Job</div>
            <div className="font-mono text-sm">{job.id}</div>
          </div>
          <button
            className="inline-flex items-center justify-center w-7 h-7 rounded text-text-muted hover:text-text hover:bg-surface-2 transition-colors"
            onClick={onClose}
            aria-label="Close drawer"
          >
            <Icons.x size={16} />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-5">
          {/* Fields */}
          <div
            className="grid text-sm mb-5"
            style={{ gridTemplateColumns: "120px 1fr", rowGap: 10, columnGap: 12 }}
          >
            <Field label="Repo" value={<span className="font-mono">{job.repo}</span>} />
            <Field
              label="PR"
              value={
                <a
                  className="text-accent inline-flex items-center gap-1"
                  href={`https://${job.platform === "gitlab" ? "gitlab.com" : "github.com"}/${job.repo}/pull/${job.pr_number}`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  #{job.pr_number} <Icons.external size={12} />
                </a>
              }
            />
            <Field label="Status" value={<JobStatusBadge status={job.status ?? "queued"} />} />
            <Field label="Duration" value={fmtDuration(job.duration_ms)} />
            <Field label="Created" value={fmtAbsolute(job.created_at)} />
          </div>

          {/* Pipeline */}
          <div className="text-[11.5px] uppercase tracking-[.06em] text-text-muted font-medium mb-2.5">
            Pipeline
          </div>
          <div className="flex items-center bg-surface-2 rounded p-3.5 mb-6">
            {STAGES.map((s, i) => (
              <div key={s.key} className="flex items-center flex-1">
                <div className="flex flex-col items-center gap-1.5 flex-1">
                  <div className="w-6 h-6 rounded-full bg-surface border border-border flex items-center justify-center">
                    <StageIcon status={stageStatus(i)} />
                  </div>
                  <span
                    className={cn(
                      "text-[11.5px]",
                      stageStatus(i) === "running" ? "text-text" : "text-text-muted",
                    )}
                  >
                    {s.label}
                  </span>
                </div>
                {i < STAGES.length - 1 && (
                  <div className="h-px bg-border flex-[0.4] mb-4" />
                )}
              </div>
            ))}
          </div>

          {/* Error */}
          {job.error && (
            <>
              <div className="text-[11.5px] uppercase tracking-[.06em] text-text-muted font-medium mb-2">
                Error
              </div>
              <pre className="font-mono text-xs bg-input-bg border border-border border-l-[3px] border-l-error rounded p-3 text-[#ffb5bf] overflow-x-auto whitespace-pre leading-relaxed m-0">
                {job.error}
              </pre>
            </>
          )}
        </div>
      </aside>
    </>
  );
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <>
      <div className="text-xs text-text-muted">{label}</div>
      <div className="text-sm">{value}</div>
    </>
  );
}

export default function JobsPage() {
  const [statusFilter, setStatusFilter] = useState("all");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data, isLoading } = useJobs({
    limit: 50,
    status: statusFilter !== "all" ? statusFilter : undefined,
  });

  const jobs = (data?.items ?? []) as Job[];
  const selected = jobs.find((j) => j.id === selectedId);

  return (
    <Shell>
      <PageHeader title="Jobs" subtitle="Analysis pipeline runs per PR/MR" />

      <div className="flex items-center gap-2.5 mb-3.5">
        <NativeSelect
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="w-44"
          aria-label="Filter by status"
        >
          <option value="all">All statuses</option>
          <option value="queued">Queued</option>
          <option value="running">Running</option>
          <option value="processed">Processed</option>
          <option value="failed">Failed</option>
        </NativeSelect>
        {!isLoading && (
          <span className="text-sm text-text-muted">{jobs.length} jobs</span>
        )}
      </div>

      {isLoading ? (
        <div className="bg-surface border border-border rounded p-5 flex flex-col gap-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-4 w-full" />
          ))}
        </div>
      ) : jobs.length === 0 ? (
        <EmptyState
          icon={<Icons.jobs size={22} />}
          title="No jobs found"
          body="Jobs appear when Vellic processes pull request webhooks."
        />
      ) : (
        <div className="bg-surface border border-border rounded overflow-hidden">
          <table className="w-full text-sm border-collapse" role="table">
            <thead>
              <tr className="bg-surface border-b border-border text-text-muted text-xs uppercase tracking-[.04em]">
                <th className="text-left px-4 py-2.5 font-medium w-[160px]">Job ID</th>
                <th className="text-left px-4 py-2.5 font-medium">Repo</th>
                <th className="text-left px-4 py-2.5 font-medium w-20">PR</th>
                <th className="text-left px-4 py-2.5 font-medium w-[120px]">Status</th>
                <th className="text-left px-4 py-2.5 font-medium w-24">Duration</th>
                <th className="text-left px-4 py-2.5 font-medium w-[130px]">Created</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((j) => (
                <tr
                  key={j.id}
                  className={cn(
                    "border-b border-border last:border-b-0 cursor-pointer hover:bg-surface-2/40 transition-colors",
                    j.status === "failed" && "bg-error/[0.02]",
                    selectedId === j.id && "bg-surface-2",
                  )}
                  onClick={() => setSelectedId(j.id)}
                  tabIndex={0}
                  onKeyDown={(e) => e.key === "Enter" && setSelectedId(j.id)}
                  role="button"
                  aria-label={`View job ${j.id}`}
                >
                  <td className="px-4 py-2.5">
                    <span className="font-mono text-xs">{j.id.slice(0, 14)}</span>
                  </td>
                  <td className="px-4 py-2.5">
                    <span className="font-mono text-xs text-text-muted">{j.repo}</span>
                  </td>
                  <td className="px-4 py-2.5">
                    <span className="text-xs text-accent">#{j.pr_number}</span>
                  </td>
                  <td className="px-4 py-2.5">
                    <JobStatusBadge status={j.status ?? "queued"} />
                  </td>
                  <td className="px-4 py-2.5">
                    <span className="text-xs text-text-muted">{fmtDuration(j.duration_ms)}</span>
                  </td>
                  <td className="px-4 py-2.5">
                    <span
                      className="text-xs text-text-muted"
                      title={fmtAbsolute(j.created_at)}
                    >
                      {fmtRelative(j.created_at)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selected && (
        <JobDrawer job={selected} onClose={() => setSelectedId(null)} />
      )}
    </Shell>
  );
}
