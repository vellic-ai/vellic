// Route: /deliveries  — Webhook Deliveries
// Entry: <DeliveriesScreen navigate={...} />

function DeliveriesScreen({ navigate }) {
  const toast = useToast();
  const [statusFilter, setStatusFilter] = useState('all');
  const [eventFilter, setEventFilter] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  const [replayId, setReplayId] = useState(null);
  const [page, setPage] = useState(0);
  const [copiedId, setCopiedId] = useState(null);
  const pageSize = 10;

  const filtered = MOCK.deliveries.filter(d =>
    (statusFilter === 'all' || d.status === statusFilter) &&
    (!eventFilter || d.event.toLowerCase().includes(eventFilter.toLowerCase()))
  );
  const total = filtered.length;
  const start = page * pageSize;
  const pageRows = filtered.slice(start, start + pageSize);

  const refresh = () => {
    setRefreshing(true);
    setTimeout(() => { setRefreshing(false); toast.info('Refreshed'); }, 500);
  };

  const replay = (id) => {
    setReplayId(id);
    setTimeout(() => {
      setReplayId(null);
      if (id.endsWith('x')) toast.error('Replay failed — webhook endpoint unreachable');
      else toast.success('Queued');
    }, 800);
  };

  const copy = (id) => {
    navigator.clipboard?.writeText(id);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1000);
  };

  const statusBadge = (s) =>
    s === 'processed' ? <span className="badge badge-success"><span className="dot dot-success" /> processed</span>
    : s === 'failed' ? <span className="badge badge-error"><span className="dot dot-error" /> failed</span>
    : <span className="badge"><span className="dot dot-muted" /> queued</span>;

  const hasAny = MOCK.deliveries.length > 0;

  return (
    <>
      <PageHeader
        title="Deliveries"
        subtitle="Inbound webhooks from GitHub & GitLab"
      />

      {/* Filter bar */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 14, flexWrap: 'wrap', alignItems: 'center' }}>
        <select className="select input" value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(0); }} style={{ width: 140 }}>
          <option value="all">All statuses</option>
          <option value="queued">Queued</option>
          <option value="processed">Processed</option>
          <option value="failed">Failed</option>
        </select>
        <div style={{ position: 'relative', flex: '1 1 260px', maxWidth: 340 }}>
          <span style={{ position: 'absolute', left: 10, top: 9, color: 'var(--text-muted)' }}>{I.search}</span>
          <input className="input" placeholder="Filter by event type…" value={eventFilter} onChange={(e) => { setEventFilter(e.target.value); setPage(0); }} style={{ paddingLeft: 32 }} />
        </div>
        <div style={{ flex: 1 }} />
        <button className="btn btn-sm" onClick={refresh} disabled={refreshing}>
          {refreshing ? <Spinner /> : I.refresh} Refresh
        </button>
      </div>

      {!hasAny ? (
        <EmptyState
          icon={I.deliveries}
          title="No webhook deliveries yet"
          body="Send a test webhook from your VCS to see it appear here."
        />
      ) : (
        <>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th style={{ width: 180 }}>Delivery ID</th>
                  <th>Event</th>
                  <th style={{ width: 140 }}>Received</th>
                  <th style={{ width: 140 }}>Processed</th>
                  <th style={{ width: 120 }}>Status</th>
                  <th style={{ width: 90 }}></th>
                </tr>
              </thead>
              <tbody>
                {pageRows.map(d => (
                  <tr key={d.id} className={d.status === 'failed' ? 'row-failed' : ''}>
                    <td>
                      <span className="mono" style={{ fontSize: 12.5, display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                        {trunc(d.id, 14)}
                        <button className="btn btn-ghost btn-sm" onClick={() => copy(d.id)} title="Copy" style={{ padding: '0 4px', height: 20 }}>
                          {copiedId === d.id ? I.check : I.copy}
                        </button>
                      </span>
                    </td>
                    <td><span className="mono" style={{ fontSize: 12.5 }}>{d.event}</span></td>
                    <td><span style={{ color: 'var(--text-muted)', fontSize: 12.5 }} title={fmtAbsolute(d.received_at)}>{fmtRelative(d.received_at)}</span></td>
                    <td><span style={{ color: 'var(--text-muted)', fontSize: 12.5 }} title={fmtAbsolute(d.processed_at)}>{fmtRelative(d.processed_at)}</span></td>
                    <td>{statusBadge(d.status)}</td>
                    <td style={{ textAlign: 'right' }}>
                      <button className="btn btn-sm" onClick={() => replay(d.id)} disabled={replayId === d.id}>
                        {replayId === d.id ? <Spinner /> : null} Replay
                      </button>
                    </td>
                  </tr>
                ))}
                {pageRows.length === 0 && (
                  <tr><td colSpan={6} style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>No deliveries match your filters.</td></tr>
                )}
              </tbody>
            </table>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 14, fontSize: 12.5, color: 'var(--text-muted)' }}>
            <span>Showing {total === 0 ? 0 : start + 1}–{Math.min(start + pageSize, total)} of {total}</span>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn btn-sm" disabled={page === 0} onClick={() => setPage(p => p - 1)}>{I.chevronLeft} Prev</button>
              <button className="btn btn-sm" disabled={start + pageSize >= total} onClick={() => setPage(p => p + 1)}>Next {I.chevronRight}</button>
            </div>
          </div>
        </>
      )}
    </>
  );
}

function EmptyState({ icon, title, body, action }) {
  return (
    <div className="card" style={{ padding: 56, textAlign: 'center' }}>
      <div style={{ display: 'inline-flex', width: 44, height: 44, borderRadius: 10, background: 'var(--surface-2)', color: 'var(--text-muted)', alignItems: 'center', justifyContent: 'center', marginBottom: 14 }}>
        {icon}
      </div>
      <div style={{ fontSize: 15, fontWeight: 500, marginBottom: 6 }}>{title}</div>
      <div style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: action ? 20 : 0 }}>{body}</div>
      {action}
    </div>
  );
}

Object.assign(window, { DeliveriesScreen, EmptyState });
