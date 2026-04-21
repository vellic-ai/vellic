// Route: /settings/danger — Danger zone
// Entry: <DangerScreen navigate={...} />
// Covers: reset config, clear cache, wipe data — all destructive, all behind confirm dialogs

function DangerScreen({ navigate }) {
  const toast = useToast();
  const [confirm, setConfirm] = useState(null); // { action, title, body, label, requireType, onConfirm }
  const [running, setRunning] = useState(null);

  const run = (key, successMsg) => {
    setRunning(key);
    setConfirm(null);
    setTimeout(() => { setRunning(null); toast.success(successMsg); }, 900);
  };

  const ACTIONS = [
    {
      key: 'clear_cache',
      title: 'Clear analysis cache',
      desc: 'Removes cached LLM responses and diff analysis results. Next reviews will be slower while the cache warms up. Does not affect configuration or stored review comments.',
      label: 'Clear cache',
      impact: 'low',
      confirm: {
        title: 'Clear analysis cache?',
        body: 'Cached responses will be deleted. The next batch of reviews will be slower while the cache warms up. This does not affect your config or any stored review data.',
        label: 'Clear cache',
        requireType: null,
        danger: false,
      },
    },
    {
      key: 'reset_config',
      title: 'Reset configuration',
      desc: 'Resets all settings to installation defaults: provider credentials, webhook URLs, rule overrides, and repo configuration. Your review history is preserved.',
      label: 'Reset config',
      impact: 'medium',
      confirm: {
        title: 'Reset all configuration?',
        body: 'Provider credentials, webhook endpoints, rule overrides, and all repository settings will be wiped and reset to defaults. Stored review history is not affected.',
        label: 'Reset to defaults',
        requireType: 'reset',
        danger: true,
      },
    },
    {
      key: 'wipe_data',
      title: 'Wipe all data',
      desc: 'Permanently deletes all review history, delivery logs, job records, and configuration. The installation will be reset to a blank state. This cannot be undone.',
      label: 'Wipe data',
      impact: 'critical',
      confirm: {
        title: 'Wipe ALL data?',
        body: (
          <>
            <p style={{ marginTop: 0 }}>This will permanently delete:</p>
            <ul style={{ paddingLeft: 18, margin: '8px 0' }}>
              <li>All review history and comments</li>
              <li>All delivery and job records</li>
              <li>All configuration and credentials</li>
              <li>All API keys</li>
            </ul>
            <p style={{ marginBottom: 0 }}>
              Your vellic installation will be reset to a blank state.
              <strong> There is no backup and no undo.</strong>
            </p>
          </>
        ),
        label: 'Wipe everything',
        requireType: 'wipe',
        danger: true,
      },
    },
  ];

  const impactColors = {
    low:      { bg: 'rgba(108,99,255,.08)',  border: 'rgba(108,99,255,.25)',  text: 'var(--accent)',       badge: 'Low impact' },
    medium:   { bg: 'var(--warning-bg)',      border: 'var(--warning-border)', text: 'var(--warning-text)', badge: 'Medium impact' },
    critical: { bg: 'rgba(239,68,68,.08)',    border: 'rgba(239,68,68,.25)',   text: 'var(--error)',        badge: 'Irreversible' },
  };

  return (
    <>
      <PageHeader
        title="Danger zone"
        subtitle="Destructive operations. All actions require explicit confirmation."
      />

      <div style={{
        marginBottom: 20,
        padding: '12px 16px',
        background: 'rgba(239,68,68,.06)',
        border: '1px solid rgba(239,68,68,.2)',
        borderRadius: 'var(--radius)',
        display: 'flex', alignItems: 'center', gap: 10,
        fontSize: 13,
      }}>
        <span style={{ color: 'var(--error)', flexShrink: 0 }}>{I.warn}</span>
        <span style={{ color: 'var(--text-muted)' }}>Actions on this page affect your entire vellic installation and may not be reversible.</span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {ACTIONS.map(action => {
          const col = impactColors[action.impact];
          const isRunning = running === action.key;
          return (
            <section key={action.key} className="card" style={{
              padding: 20,
              border: `1px solid ${col.border}`,
              background: col.bg,
            }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 16 }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 14 }}>{action.title}</span>
                    <span style={{
                      fontSize: 11, fontWeight: 500,
                      padding: '2px 7px', borderRadius: 10,
                      background: 'rgba(0,0,0,.2)',
                      color: col.text,
                    }}>{col.badge}</span>
                  </div>
                  <p style={{ margin: 0, fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.5 }}>{action.desc}</p>
                </div>
                <button
                  className="btn btn-sm"
                  disabled={isRunning}
                  onClick={() => setConfirm({ ...action.confirm, key: action.key })}
                  style={{
                    flexShrink: 0,
                    borderColor: col.border,
                    color: col.text,
                    background: 'transparent',
                  }}
                >
                  {isRunning ? <Spinner /> : null}
                  {isRunning ? 'Running…' : action.label}
                </button>
              </div>
            </section>
          );
        })}
      </div>

      {confirm && (
        <ConfirmModal
          open
          title={confirm.title}
          body={confirm.body}
          confirmLabel={confirm.label}
          danger={confirm.danger}
          requireType={confirm.requireType}
          onCancel={() => setConfirm(null)}
          onConfirm={() => {
            const key = confirm.key;
            const msgs = {
              clear_cache:  'Cache cleared',
              reset_config: 'Configuration reset to defaults',
              wipe_data:    'All data wiped — vellic reset to blank state',
            };
            run(key, msgs[key]);
          }}
        />
      )}
    </>
  );
}

window.DangerScreen = DangerScreen;
