// Route: /jobs  — Analysis Jobs
// Entry: <JobsScreen navigate={...} />

function JobsScreen({ navigate }) {
  const [statusFilter, setStatusFilter] = useState('all');
  const [selectedId, setSelectedId] = useState(null);

  const filtered = MOCK.jobs.filter(j => statusFilter === 'all' || j.status === statusFilter);
  const selected = filtered.find(j => j.id === selectedId) || MOCK.jobs.find(j => j.id === selectedId);

  const statusCell = (j) => {
    if (j.status === 'processed') return <span className="badge badge-success"><span className="dot dot-success" /> processed</span>;
    if (j.status === 'failed') return <span className="badge badge-error"><span className="dot dot-error" /> failed</span>;
    if (j.status === 'running') return <span className="badge badge-info"><Spinner size={10} /> running</span>;
    return <span className="badge"><span className="dot dot-muted" /> queued</span>;
  };

  return (
    <>
      <PageHeader title="Jobs" subtitle="Analysis pipeline runs per PR/MR" />

      <div style={{ display: 'flex', gap: 10, marginBottom: 14, alignItems: 'center' }}>
        <select className="select input" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} style={{ width: 160 }}>
          <option value="all">All statuses</option>
          <option value="queued">Queued</option>
          <option value="running">Running</option>
          <option value="processed">Processed</option>
          <option value="failed">Failed</option>
        </select>
        <span style={{ color: 'var(--text-muted)', fontSize: 12.5 }}>{filtered.length} jobs</span>
      </div>

      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th style={{ width: 160 }}>Job ID</th>
              <th>Repo</th>
              <th style={{ width: 80 }}>PR</th>
              <th style={{ width: 120 }}>Status</th>
              <th style={{ width: 90 }}>Retries</th>
              <th style={{ width: 100 }}>Duration</th>
              <th style={{ width: 130 }}>Created</th>
            </tr>
          </thead>
          <tbody>
            {filtered.slice(0, 15).map(j => (
              <tr key={j.id} className={`clickable ${j.status === 'failed' ? 'row-failed' : ''}`} onClick={() => setSelectedId(j.id)}>
                <td><span className="mono" style={{ fontSize: 12.5 }}>{trunc(j.id, 14)}</span></td>
                <td><span className="mono" style={{ fontSize: 12.5, color: 'var(--text-muted)' }}>{j.repo}</span></td>
                <td>
                  <a
                    href={`https://${j.platform}.com/${j.repo}/pull/${j.pr}`}
                    target="_blank"
                    rel="noopener"
                    onClick={(e) => e.stopPropagation()}
                    style={{ color: 'var(--accent)', display: 'inline-flex', alignItems: 'center', gap: 3, fontSize: 12.5 }}
                  >#{j.pr} <span style={{ display: 'inline-flex', opacity: .7 }}>{I.external}</span></a>
                </td>
                <td>{statusCell(j)}</td>
                <td>
                  <span style={{ fontSize: 12.5, color: j.retry_count >= 2 ? 'var(--warning-text)' : 'var(--text-muted)' }}>
                    {j.retry_count}
                  </span>
                </td>
                <td><span style={{ fontSize: 12.5, color: 'var(--text-muted)' }}>{fmtDuration(j.duration_ms)}</span></td>
                <td><span style={{ fontSize: 12.5, color: 'var(--text-muted)' }} title={fmtAbsolute(j.created_at)}>{fmtRelative(j.created_at)}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selected && <JobDrawer job={selected} onClose={() => setSelectedId(null)} />}
    </>
  );
}

function JobDrawer({ job, onClose }) {
  const stages = [
    { key: 'fetch', label: 'Fetch' },
    { key: 'analyze', label: 'Analyze' },
    { key: 'format', label: 'Format' },
    { key: 'post', label: 'Post' },
  ];
  const statusIcon = (s) => {
    if (s === 'done') return <span style={{ color: 'var(--success)', display: 'inline-flex' }}>{I.check}</span>;
    if (s === 'running') return <Spinner size={12} color="var(--accent)" />;
    if (s === 'failed') return <span style={{ color: 'var(--error)', display: 'inline-flex' }}>{I.x}</span>;
    return <span style={{ width: 10, height: 10, borderRadius: '50%', border: '1.5px solid var(--border)', display: 'inline-block' }} />;
  };

  return (
    <>
      <div className="overlay" onClick={onClose} />
      <div className="drawer">
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.06em' }}>Job</div>
            <div className="mono" style={{ fontSize: 13, marginTop: 2 }}>{job.id}</div>
          </div>
          <button className="btn btn-ghost btn-sm" onClick={onClose} style={{ padding: '0 8px' }}>{I.x}</button>
        </div>
        <div style={{ flex: 1, overflowY: 'auto', padding: 20 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', rowGap: 10, columnGap: 12, fontSize: 13, marginBottom: 20 }}>
            <DrawerField label="Repo" value={<span className="mono">{job.repo}</span>} />
            <DrawerField label="PR" value={<a style={{ color: 'var(--accent)' }} target="_blank" rel="noopener" href={`https://${job.platform}.com/${job.repo}/pull/${job.pr}`}>#{job.pr} ↗</a>} />
            <DrawerField label="Platform" value={job.platform} />
            <DrawerField label="Status" value={job.status} />
            <DrawerField label="Retries" value={job.retry_count} />
            <DrawerField label="Duration" value={fmtDuration(job.duration_ms)} />
            <DrawerField label="Created" value={fmtAbsolute(job.created_at)} />
          </div>

          <div style={{ fontSize: 11.5, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.06em', marginBottom: 10, fontWeight: 500 }}>Pipeline</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 0, marginBottom: 24, padding: 14, background: 'var(--surface-2)', borderRadius: 'var(--radius)' }}>
            {stages.map((s, i) => (
              <React.Fragment key={s.key}>
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
                  <div style={{ width: 24, height: 24, borderRadius: '50%', background: 'var(--surface)', display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px solid var(--border)' }}>
                    {statusIcon(job.stages[i])}
                  </div>
                  <span style={{ fontSize: 11.5, color: job.stages[i] === 'running' ? 'var(--text)' : 'var(--text-muted)' }}>{s.label}</span>
                </div>
                {i < stages.length - 1 && <div style={{ flex: .4, height: 1, background: 'var(--border)', marginTop: -18 }} />}
              </React.Fragment>
            ))}
          </div>

          {job.error && (
            <>
              <div style={{ fontSize: 11.5, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.06em', marginBottom: 8, fontWeight: 500 }}>Error</div>
              <pre className="mono" style={{
                background: 'var(--input-bg)',
                border: '1px solid var(--border)',
                borderLeft: '3px solid var(--error)',
                borderRadius: 'var(--radius)',
                padding: 12,
                fontSize: 11.5,
                lineHeight: 1.55,
                color: '#ffb5bf',
                overflowX: 'auto',
                whiteSpace: 'pre',
                margin: 0,
              }}>{job.error}</pre>
            </>
          )}
        </div>
      </div>
    </>
  );
}

function DrawerField({ label, value }) {
  return (
    <>
      <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>{label}</div>
      <div style={{ fontSize: 13 }}>{value}</div>
    </>
  );
}

window.JobsScreen = JobsScreen;
