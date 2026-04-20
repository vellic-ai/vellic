import { useState } from "react";
import { Shell, PageHeader, EmptyState, StatusDot, Skeleton } from "@/components/Shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";
import { Icons, Spinner } from "@/components/icons";
import { useDeliveries, useReplayDelivery } from "@/api";
import { useToast } from "@/lib/toast";

const PAGE_SIZE = 10;

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

function DeliveryStatusBadge({ status }: { status: string }) {
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

export default function DeliveriesPage() {
  const toast = useToast();
  const [statusFilter, setStatusFilter] = useState("all");
  const [eventFilter, setEventFilter] = useState("");
  const [page, setPage] = useState(0);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [replayingId, setReplayingId] = useState<string | null>(null);

  const { data, isLoading, isFetching, refetch } = useDeliveries({
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
    status: statusFilter !== "all" ? statusFilter : undefined,
    event_type: eventFilter || undefined,
  });

  const replay = useReplayDelivery();

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const start = page * PAGE_SIZE;

  const handleReplay = (id: string) => {
    setReplayingId(id);
    replay.mutate(id, {
      onSuccess: () => {
        toast.success("Queued for replay");
        setReplayingId(null);
      },
      onError: (err) => {
        toast.error(err.message || "Replay failed");
        setReplayingId(null);
      },
    });
  };

  const handleCopy = (id: string) => {
    navigator.clipboard?.writeText(id);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1200);
  };

  const handleRefresh = () => {
    refetch();
    toast.info("Refreshed");
  };

  return (
    <Shell>
      <PageHeader title="Deliveries" subtitle="Inbound webhooks from GitHub & GitLab" />

      {/* Filter bar */}
      <div className="flex flex-wrap gap-2.5 mb-3.5 items-center">
        <NativeSelect
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(0); }}
          className="w-36"
          aria-label="Filter by status"
        >
          <option value="all">All statuses</option>
          <option value="queued">Queued</option>
          <option value="processed">Processed</option>
          <option value="failed">Failed</option>
        </NativeSelect>

        <div className="relative flex-1 min-w-[200px] max-w-[340px]">
          <span className="absolute left-2.5 top-[9px] text-text-muted pointer-events-none">
            <Icons.search size={14} />
          </span>
          <Input
            placeholder="Filter by event type…"
            value={eventFilter}
            onChange={(e) => { setEventFilter(e.target.value); setPage(0); }}
            className="pl-8"
            aria-label="Filter by event type"
          />
        </div>

        <div className="flex-1" />

        <Button
          size="sm"
          variant="default"
          onClick={handleRefresh}
          disabled={isFetching}
          aria-label="Refresh deliveries"
        >
          {isFetching ? <Spinner size={13} /> : <Icons.refresh size={13} />}
          Refresh
        </Button>
      </div>

      {isLoading ? (
        <div className="bg-surface border border-border rounded overflow-hidden">
          <div className="p-5 flex flex-col gap-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-4 w-full" />
            ))}
          </div>
        </div>
      ) : total === 0 && !statusFilter && !eventFilter ? (
        <EmptyState
          icon={<Icons.deliveries size={22} />}
          title="No webhook deliveries yet"
          body="Send a test webhook from your VCS to see it appear here."
        />
      ) : (
        <>
          <div className="bg-surface border border-border rounded overflow-hidden">
            <table className="w-full text-sm border-collapse" role="table">
              <thead>
                <tr className="bg-surface border-b border-border text-text-muted text-xs uppercase tracking-[.04em]">
                  <th className="text-left px-4 py-2.5 font-medium w-[180px]">Delivery ID</th>
                  <th className="text-left px-4 py-2.5 font-medium">Event</th>
                  <th className="text-left px-4 py-2.5 font-medium w-[140px]">Received</th>
                  <th className="text-left px-4 py-2.5 font-medium w-[140px]">Processed</th>
                  <th className="text-left px-4 py-2.5 font-medium w-[120px]">Status</th>
                  <th className="text-right px-4 py-2.5 font-medium w-[90px]"></th>
                </tr>
              </thead>
              <tbody>
                {items.length === 0 ? (
                  <tr>
                    <td
                      colSpan={6}
                      className="text-center py-10 text-text-muted text-sm"
                    >
                      No deliveries match your filters.
                    </td>
                  </tr>
                ) : (
                  items.map((d) => (
                    <tr
                      key={d.delivery_id}
                      className={`border-b border-border last:border-b-0 hover:bg-surface-2/30 transition-colors ${d.status === "failed" ? "bg-error/[0.02]" : ""}`}
                    >
                      <td className="px-4 py-2.5">
                        <span className="font-mono text-xs inline-flex items-center gap-1.5">
                          {d.delivery_id.slice(0, 14)}
                          <button
                            className="inline-flex items-center justify-center w-5 h-5 rounded text-text-muted hover:text-text hover:bg-surface-2 transition-colors"
                            onClick={() => handleCopy(d.delivery_id)}
                            aria-label="Copy delivery ID"
                          >
                            {copiedId === d.delivery_id ? (
                              <Icons.check size={12} />
                            ) : (
                              <Icons.copy size={12} />
                            )}
                          </button>
                        </span>
                      </td>
                      <td className="px-4 py-2.5">
                        <span className="font-mono text-xs">{d.event_type}</span>
                      </td>
                      <td className="px-4 py-2.5">
                        <span
                          className="text-xs text-text-muted"
                          title={fmtAbsolute(d.received_at)}
                        >
                          {fmtRelative(d.received_at)}
                        </span>
                      </td>
                      <td className="px-4 py-2.5">
                        <span
                          className="text-xs text-text-muted"
                          title={fmtAbsolute(d.processed_at)}
                        >
                          {fmtRelative(d.processed_at)}
                        </span>
                      </td>
                      <td className="px-4 py-2.5">
                        <DeliveryStatusBadge status={d.status ?? "queued"} />
                      </td>
                      <td className="px-4 py-2.5 text-right">
                        <Button
                          size="sm"
                          variant="default"
                          disabled={replayingId === d.delivery_id}
                          onClick={() => handleReplay(d.delivery_id)}
                        >
                          {replayingId === d.delivery_id && <Spinner size={11} />}
                          Replay
                        </Button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between mt-3.5 text-sm text-text-muted">
            <span>
              {total === 0
                ? "No results"
                : `Showing ${start + 1}–${Math.min(start + PAGE_SIZE, total)} of ${total}`}
            </span>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="default"
                disabled={page === 0}
                onClick={() => setPage((p) => p - 1)}
                aria-label="Previous page"
              >
                <Icons.chevronLeft size={13} /> Prev
              </Button>
              <Button
                size="sm"
                variant="default"
                disabled={start + PAGE_SIZE >= total}
                onClick={() => setPage((p) => p + 1)}
                aria-label="Next page"
              >
                Next <Icons.chevronRight size={13} />
              </Button>
            </div>
          </div>
        </>
      )}
    </Shell>
  );
}
