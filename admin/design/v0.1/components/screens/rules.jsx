// Route: /settings/rules — Pipeline rules config
// Entry: <RulesScreen navigate={...} state={...} setState={...} />
// Covers: enable/disable rules, severity config, per-repo overrides

const RULE_CATALOG = [
  // Security
  { id: 'security.secret_leak',     cat: 'Security',     label: 'Secret / credential leak',    desc: 'Flags hardcoded tokens, passwords, and private keys.',     default_sev: 'error',  fixable: true },
  { id: 'security.sql_injection',   cat: 'Security',     label: 'SQL injection risk',           desc: 'Detects string-concatenated queries without parameterisation.', default_sev: 'error', fixable: true },
  { id: 'security.open_redirect',   cat: 'Security',     label: 'Open redirect',                desc: 'Detects user-controlled redirect targets.',                default_sev: 'warning', fixable: false },
  // Quality
  { id: 'quality.long_function',    cat: 'Quality',      label: 'Long function',                desc: 'Functions exceeding the configured line threshold.',        default_sev: 'warning', fixable: false },
  { id: 'quality.dead_code',        cat: 'Quality',      label: 'Dead code',                    desc: 'Unreachable branches and unused exports.',                 default_sev: 'info',   fixable: true },
  { id: 'quality.duplicate_block',  cat: 'Quality',      label: 'Duplicate block',              desc: 'Copy-pasted logic that should be extracted.',              default_sev: 'warning', fixable: false },
  // Tests
  { id: 'tests.missing_coverage',   cat: 'Tests',        label: 'Missing test coverage',        desc: 'Changed functions with no corresponding test update.',     default_sev: 'warning', fixable: false },
  { id: 'tests.skipped_test',       cat: 'Tests',        label: 'Skipped / disabled test',      desc: 'Tests marked skip, xit, or xtest.',                       default_sev: 'info',   fixable: false },
  // Perf
  { id: 'perf.n_plus_one',          cat: 'Performance',  label: 'N+1 query pattern',            desc: 'Loops containing ORM/DB calls that may fan out.',          default_sev: 'warning', fixable: false },
  { id: 'perf.large_payload',       cat: 'Performance',  label: 'Large response payload',       desc: 'Endpoints returning unfiltered collections.',              default_sev: 'info',   fixable: false },
];

const SEV_ORDER = ['error', 'warning', 'info', 'off'];
const SEV_COLORS = { error: 'var(--error)', warning: 'var(--warning-text)', info: 'var(--accent)', off: 'var(--text-muted)' };
const SEV_BG    = { error: 'rgba(239,68,68,.12)', warning: 'var(--warning-bg)', info: 'rgba(108,99,255,.1)', off: 'var(--surface-2)' };

function RulesScreen({ navigate, state, setState }) {
  const toast = useToast();
  const [overrides, setOverrides] = useState(() => Object.fromEntries(
    RULE_CATALOG.map(r => [r.id, { sev: r.default_sev, enabled: r.default_sev !== 'off' }])
  ));
  const [repoOverrides, setRepoOverrides] = useState({});
  const [expandedRepo, setExpandedRepo] = useState(null);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const repos = state?.repos || [];

  const patch = (id, patch) => {
    setOverrides(o => ({ ...o, [id]: { ...o[id], ...patch } }));
    setDirty(true);
  };

  const patchRepo = (repoId, ruleId, p) => {
    setRepoOverrides(o => ({
      ...o,
      [repoId]: { ...o[repoId], [ruleId]: { ...(o[repoId]?.[ruleId] || {}), ...p } },
    }));
    setDirty(true);
  };

  const save = () => {
    setSaving(true);
    setTimeout(() => { setSaving(false); setDirty(false); toast.success('Rules saved'); }, 700);
  };

  const cats = [...new Set(RULE_CATALOG.map(r => r.cat))];

  return (
    <>
      <PageHeader
        title="Rules"
        subtitle="Configure which pipeline checks run and how they surface in review comments."
        action={
          <button className="btn btn-primary btn-sm" onClick={save} disabled={saving || !dirty}>
            {saving ? <Spinner /> : null} Save changes
          </button>
        }
      />

      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {cats.map(cat => (
          <section key={cat} className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <div style={{
              padding: '12px 20px', borderBottom: '1px solid var(--border)',
              fontSize: 12, fontWeight: 600, textTransform: 'uppercase',
              letterSpacing: '.06em', color: 'var(--text-muted)',
            }}>{cat}</div>

            {RULE_CATALOG.filter(r => r.cat === cat).map((rule, idx, arr) => {
              const ov = overrides[rule.id];
              const enabled = ov.enabled;
              return (
                <div key={rule.id} style={{
                  padding: '14px 20px',
                  borderBottom: idx < arr.length - 1 ? '1px solid var(--border)' : 'none',
                  opacity: enabled ? 1 : .5,
                  transition: 'opacity .15s ease',
                }}>
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
                    {/* Toggle */}
                    <button
                      type="button"
                      role="switch"
                      aria-checked={enabled}
                      onClick={() => patch(rule.id, { enabled: !enabled })}
                      style={{
                        flexShrink: 0, marginTop: 2,
                        width: 36, height: 20,
                        borderRadius: 10,
                        background: enabled ? 'var(--accent)' : 'var(--surface-2)',
                        border: '1px solid ' + (enabled ? 'var(--accent)' : 'var(--border)'),
                        position: 'relative',
                        transition: 'background .15s ease, border-color .15s ease',
                        cursor: 'pointer',
                        padding: 0,
                      }}
                    >
                      <span style={{
                        position: 'absolute',
                        top: 2, left: enabled ? 17 : 2,
                        width: 14, height: 14,
                        borderRadius: '50%',
                        background: enabled ? '#fff' : 'var(--text-muted)',
                        transition: 'left .15s ease',
                      }} />
                    </button>

                    {/* Info */}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                        <span style={{ fontWeight: 500, fontSize: 13.5 }}>{rule.label}</span>
                        {rule.fixable && (
                          <span className="badge badge-info" style={{ fontSize: 11 }}>auto-fix</span>
                        )}
                        <span className="mono" style={{ fontSize: 11, color: 'var(--text-muted)', padding: '2px 6px', background: 'var(--input-bg)', borderRadius: 4 }}>{rule.id}</span>
                      </div>
                      <div style={{ fontSize: 12.5, color: 'var(--text-muted)', marginTop: 3 }}>{rule.desc}</div>
                    </div>

                    {/* Severity picker */}
                    <div style={{ flexShrink: 0 }}>
                      <select
                        className="select input"
                        value={ov.sev}
                        disabled={!enabled}
                        onChange={(e) => patch(rule.id, { sev: e.target.value })}
                        style={{
                          fontSize: 12, height: 28, padding: '0 8px',
                          color: SEV_COLORS[ov.sev],
                          background: SEV_BG[ov.sev],
                          borderColor: 'transparent',
                          fontWeight: 500,
                        }}
                      >
                        {SEV_ORDER.map(s => <option key={s} value={s}>{s}</option>)}
                      </select>
                    </div>
                  </div>

                  {/* Per-repo overrides */}
                  {enabled && repos.length > 0 && (
                    <div style={{ marginTop: 10, marginLeft: 50 }}>
                      <button
                        className="btn btn-ghost btn-sm"
                        onClick={() => setExpandedRepo(ev => ev === rule.id ? null : rule.id)}
                        style={{ fontSize: 12, color: 'var(--text-muted)' }}
                      >
                        {expandedRepo === rule.id ? I.chevronDown : I.chevronRight}
                        Per-repo overrides
                        {Object.keys(repoOverrides).filter(rid =>
                          repoOverrides[rid]?.[rule.id]
                        ).length > 0 && (
                          <span className="badge badge-info" style={{ fontSize: 10, marginLeft: 4 }}>
                            {Object.keys(repoOverrides).filter(rid => repoOverrides[rid]?.[rule.id]).length}
                          </span>
                        )}
                      </button>

                      {expandedRepo === rule.id && (
                        <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 6 }}>
                          {repos.map(repo => {
                            const rov = repoOverrides[repo.id]?.[rule.id];
                            const repoEnabled = rov ? rov.enabled : true;
                            const repoSev = rov?.sev || ov.sev;
                            return (
                              <div key={repo.id} style={{
                                display: 'flex', alignItems: 'center', gap: 10,
                                padding: '8px 12px',
                                background: rov ? 'rgba(108,99,255,.06)' : 'var(--input-bg)',
                                border: '1px solid ' + (rov ? 'rgba(108,99,255,.2)' : 'var(--border)'),
                                borderRadius: 6,
                              }}>
                                <span style={{ display: 'inline-flex', width: 14, color: repo.platform === 'github' ? 'var(--text)' : '#e24329' }}>
                                  {repo.platform === 'github' ? I.github : I.gitlab}
                                </span>
                                <span className="mono" style={{ flex: 1, fontSize: 12 }}>{repo.slug}</span>
                                <button
                                  type="button"
                                  role="switch"
                                  aria-checked={repoEnabled}
                                  onClick={() => patchRepo(repo.id, rule.id, { enabled: !repoEnabled, sev: repoSev })}
                                  style={{
                                    width: 30, height: 16, borderRadius: 8,
                                    background: repoEnabled ? 'var(--accent)' : 'var(--surface-2)',
                                    border: '1px solid ' + (repoEnabled ? 'var(--accent)' : 'var(--border)'),
                                    position: 'relative', cursor: 'pointer', padding: 0, flexShrink: 0,
                                  }}
                                >
                                  <span style={{
                                    position: 'absolute', top: 1,
                                    left: repoEnabled ? 13 : 1,
                                    width: 12, height: 12, borderRadius: '50%',
                                    background: repoEnabled ? '#fff' : 'var(--text-muted)',
                                    transition: 'left .12s ease',
                                  }} />
                                </button>
                                <select
                                  className="select input"
                                  value={repoSev}
                                  disabled={!repoEnabled}
                                  onChange={(e) => patchRepo(repo.id, rule.id, { enabled: true, sev: e.target.value })}
                                  style={{ fontSize: 11.5, height: 26, padding: '0 6px', width: 80 }}
                                >
                                  {SEV_ORDER.map(s => <option key={s} value={s}>{s}</option>)}
                                </select>
                                {rov && (
                                  <button
                                    className="btn btn-ghost btn-sm"
                                    onClick={() => {
                                      setRepoOverrides(o => {
                                        const next = { ...o };
                                        if (next[repo.id]) { delete next[repo.id][rule.id]; }
                                        return next;
                                      });
                                      setDirty(true);
                                    }}
                                    title="Reset to global default"
                                    style={{ padding: '0 6px', height: 24, color: 'var(--text-muted)' }}
                                  >
                                    {I.refresh}
                                  </button>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </section>
        ))}
      </div>
    </>
  );
}

window.RulesScreen = RulesScreen;
