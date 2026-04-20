// Route: /  — Dashboard
// Entry: <DashboardScreen navigate={...} state={...} />

function DashboardScreen({ navigate, state, setState }) {
  const toast = useToast();
  const [loading, setLoading] = useState(false);
  const [statsError, setStatsError] = useState(state.dashError || false);
  const stats = MOCK.stats;
  const hasRepos = state.repos.length > 0;
  const activeRepos = state.repos.filter(r => r.enabled);
  const cloudRepos = activeRepos.filter(r => isCloud(r.provider));
  const providersInUse = Array.from(new Set(activeRepos.map(r => r.provider)));
  const hasDeliveries = MOCK.recent_deliveries.length > 0 && hasRepos;

  const retry = () => {
    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      setStatsError(false);
      setState(s => ({ ...s, dashError: false }));
      toast.success('Stats refreshed');
    }, 600);
  };

  const statusDot = (s) =>
    s === 'processed' ? <span className="badge badge-success"><span className="dot dot-success" /> processed</span>
    : s === 'failed' ? <span className="badge badge-error"><span className="dot dot-error" /> failed</span>
    : <span className="badge"><span className="dot dot-muted" /> queued</span>;

  return (
    <>
      <PageHeader
        title="Dashboard"
        extra={
          <>
            {activeRepos.length > 0 && (
              <span className="badge badge-info" style={{ fontSize: 11 }}>
                <span className="dot dot-success" />
                {activeRepos.length} active {activeRepos.length === 1 ? 'repo' : 'repos'} · {providersInUse.length} {providersInUse.length === 1 ? 'provider' : 'providers'}
              </span>
            )}
            {cloudRepos.length > 0 && (
              <span className="badge badge-warning">
                <span style={{ display: 'inline-flex' }}>{I.warn}</span>
                {cloudRepos.length} {cloudRepos.length === 1 ? 'repo uses' : 'repos use'} a cloud provider — code leaves your network
              </span>
            )}
          </>
        }
      />

      {statsError && (
        <div className="err-banner" style={{ marginBottom: 18 }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 10 }}>
            <span style={{ display: 'inline-flex' }}>{I.warn}</span>
            Could not load stats: connection refused (http://clickhouse:8123)
          </span>
          <button className="btn btn-sm" onClick={retry} disabled={loading}>
            {loading ? <Spinner /> : I.refresh} Retry
          </button>
        </div>
      )}

      {/* Stats row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14, marginBottom: 24 }}>
        <StatTile label="PRs reviewed" value={loading ? null : (statsError ? '—' : stats.prs_24h)} sub={statsError ? 'unavailable' : `${stats.prs_7d} past 7d`} />
        <StatTile label="p50 latency" value={loading ? null : (statsError ? '—' : `${(stats.p50_ms/1000).toFixed(2)}s`)} sub="time to post review" />
        <StatTile label="p95 latency" value={loading ? null : (statsError ? '—' : `${(stats.p95_ms/1000).toFixed(2)}s`)} sub="tail latency" />
        <StatTile label="Failure rate" value={loading ? null : (statsError ? '—' : `${stats.failure_rate}%`)} sub="past 24h" accent={stats.failure_rate > 5 ? 'error' : null} />
      </div>

      {!hasRepos ? (
        // Empty state: no repos ever
        <div className="card" style={{ padding: 56, textAlign: 'center' }}>
          <div style={{ display: 'inline-flex', width: 48, height: 48, borderRadius: 12, background: 'var(--surface-2)', color: 'var(--text-muted)', alignItems: 'center', justifyContent: 'center', marginBottom: 14 }}>
            {React.cloneElement(I.repos, { props: { size: 22 } })}
            <span style={{ display: 'none' }}>{I.repos}</span>
          </div>
          <div style={{ fontSize: 15, fontWeight: 500, marginBottom: 6 }}>No repositories yet</div>
          <div style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 20 }}>
            Vellic is idle until you add a repository for it to watch.
          </div>
          <button className="btn btn-primary" onClick={() => navigate('/settings/repos')}>
            {I.plus} Add your first repository
          </button>
        </div>
      ) : (
        <div className="card" style={{ padding: 0 }}>
          <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ fontSize: 13, fontWeight: 500 }}>Recent activity</div>
            <a href="/deliveries" onClick={(e) => { e.preventDefault(); navigate('/deliveries'); }} style={{ fontSize: 12.5, color: 'var(--text-muted)', display: 'inline-flex', alignItems: 'center', gap: 4 }}>
              View all <span style={{ display: 'inline-flex' }}>{I.chevronRight}</span>
            </a>
          </div>
          <div>
            {MOCK.recent_deliveries.map((d, i) => (
              <div key={d.id} style={{
                display: 'grid',
                gridTemplateColumns: '100px 1fr 140px 110px',
                alignItems: 'center',
                gap: 12,
                padding: '12px 18px',
                borderBottom: i === MOCK.recent_deliveries.length - 1 ? 'none' : '1px solid var(--border)',
                fontSize: 13,
              }}>
                <span style={{ color: 'var(--text-muted)', fontSize: 12 }} title={fmtAbsolute(d.received_at)}>{fmtRelative(d.received_at)}</span>
                <span className="mono" style={{ fontSize: 12.5 }}>{d.event}</span>
                <span className="mono" style={{ fontSize: 12, color: 'var(--text-muted)' }}>{d.repo}</span>
                <span>{statusDot(d.status)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  );
}

function StatTile({ label, value, sub, accent }) {
  return (
    <div className="card" style={{ padding: 18 }}>
      <div style={{ fontSize: 11.5, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.05em', fontWeight: 500 }}>{label}</div>
      <div style={{
        fontSize: 28,
        fontWeight: 600,
        marginTop: 8,
        letterSpacing: '-.02em',
        color: accent === 'error' ? 'var(--error)' : 'var(--text)',
      }}>
        {value == null ? <Skeleton w={80} h={28} /> : value}
      </div>
      <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>{sub}</div>
    </div>
  );
}

window.DashboardScreen = DashboardScreen;
