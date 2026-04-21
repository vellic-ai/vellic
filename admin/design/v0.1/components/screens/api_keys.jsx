// Route: /settings/api-keys — API keys management
// Entry: <ApiKeysScreen navigate={...} />
// Covers: create, revoke, masked display, test-connection, per-key usage stats

const MOCK_KEYS = [
  {
    id: 'key_3f7a2b9e1c',
    name: 'CI pipeline',
    prefix: 'vk_live_3f7a…',
    scopes: ['reviews:read', 'repos:read'],
    created_at: Date.now() - 1000 * 60 * 60 * 24 * 18,
    last_used_at: Date.now() - 1000 * 60 * 14,
    usage_7d: 1842,
    status: 'active',
  },
  {
    id: 'key_8c2d4e6f1a',
    name: 'Staging webhook relay',
    prefix: 'vk_live_8c2d…',
    scopes: ['webhooks:write', 'reviews:read'],
    created_at: Date.now() - 1000 * 60 * 60 * 24 * 7,
    last_used_at: Date.now() - 1000 * 60 * 60 * 2,
    usage_7d: 374,
    status: 'active',
  },
  {
    id: 'key_1a9b5c3d2e',
    name: 'Local dev (old)',
    prefix: 'vk_live_1a9b…',
    scopes: ['reviews:read'],
    created_at: Date.now() - 1000 * 60 * 60 * 24 * 91,
    last_used_at: Date.now() - 1000 * 60 * 60 * 24 * 30,
    usage_7d: 0,
    status: 'active',
  },
];

const ALL_SCOPES = [
  { key: 'reviews:read',    label: 'Reviews · read',    desc: 'Read review comments and results' },
  { key: 'reviews:write',   label: 'Reviews · write',   desc: 'Trigger and post review comments' },
  { key: 'repos:read',      label: 'Repos · read',      desc: 'List repositories and their config' },
  { key: 'repos:write',     label: 'Repos · write',     desc: 'Add, remove, and configure repos' },
  { key: 'webhooks:write',  label: 'Webhooks · write',  desc: 'Register and rotate webhook endpoints' },
  { key: 'admin',           label: 'Admin',             desc: 'Full access — use sparingly' },
];

function fmtRelTime(ts) {
  const s = Math.floor((Date.now() - ts) / 1000);
  if (s < 60) return 'just now';
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

function ApiKeysScreen({ navigate }) {
  const toast = useToast();
  const [keys, setKeys] = useState(MOCK_KEYS);
  const [showCreate, setShowCreate] = useState(false);
  const [newKey, setNewKey] = useState(null); // revealed once after creation
  const [revokeTarget, setRevokeTarget] = useState(null);

  const revoke = () => {
    setKeys(ks => ks.filter(k => k.id !== revokeTarget.id));
    setRevokeTarget(null);
    toast.success(`Key "${revokeTarget.name}" revoked`);
  };

  return (
    <>
      <PageHeader
        title="API Keys"
        subtitle="Machine-readable tokens for CI, scripts, and integrations."
        action={
          <button className="btn btn-primary btn-sm" onClick={() => setShowCreate(true)}>
            {I.plus} New key
          </button>
        }
      />

      {newKey && (
        <div style={{
          marginBottom: 20,
          padding: '14px 16px',
          background: 'rgba(34,197,94,.07)',
          border: '1px solid rgba(34,197,94,.25)',
          borderRadius: 'var(--radius)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <span style={{ color: 'var(--success)', display: 'inline-flex' }}>{I.check}</span>
            <span style={{ fontWeight: 600, fontSize: 13 }}>Key created — copy it now. It won't be shown again.</span>
          </div>
          <SecretField value={newKey} masked={false} canCopy onCopy={() => toast.success('Copied')} readOnly />
          <button className="btn btn-ghost btn-sm" onClick={() => setNewKey(null)} style={{ marginTop: 10 }}>
            {I.x} Dismiss
          </button>
        </div>
      )}

      {keys.length === 0 ? (
        <div className="card" style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
          <div style={{ fontSize: 13 }}>No API keys yet.</div>
          <button className="btn btn-primary btn-sm" onClick={() => setShowCreate(true)} style={{ marginTop: 12 }}>
            {I.plus} Create first key
          </button>
        </div>
      ) : (
        <div className="card" style={{ overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                {['Name', 'Key', 'Scopes', 'Usage (7d)', 'Last used', ''].map((h, i) => (
                  <th key={i} style={{
                    padding: '10px 16px', textAlign: 'left',
                    fontSize: 11.5, fontWeight: 500,
                    color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.05em',
                    whiteSpace: 'nowrap',
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {keys.map((k, idx) => (
                <tr key={k.id} style={{ borderBottom: idx < keys.length - 1 ? '1px solid var(--border)' : 'none' }}>
                  <td style={{ padding: '12px 16px', fontWeight: 500 }}>{k.name}</td>
                  <td style={{ padding: '12px 16px' }}>
                    <span className="mono" style={{
                      fontSize: 12, padding: '3px 8px',
                      background: 'var(--surface-2)', borderRadius: 4, color: 'var(--text-muted)',
                    }}>{k.prefix}</span>
                  </td>
                  <td style={{ padding: '12px 16px' }}>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                      {k.scopes.map(s => (
                        <span key={s} className="badge" style={{ fontSize: 11, padding: '2px 7px' }}>{s}</span>
                      ))}
                    </div>
                  </td>
                  <td style={{ padding: '12px 16px', fontVariantNumeric: 'tabular-nums' }}>
                    {k.usage_7d === 0
                      ? <span style={{ color: 'var(--text-muted)' }}>—</span>
                      : k.usage_7d.toLocaleString()}
                  </td>
                  <td style={{ padding: '12px 16px', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                    {fmtRelTime(k.last_used_at)}
                  </td>
                  <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                    <button
                      className="btn btn-ghost btn-sm"
                      style={{ color: 'var(--danger)', borderColor: 'rgba(255,77,109,.25)' }}
                      onClick={() => setRevokeTarget(k)}
                    >
                      Revoke
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && (
        <CreateKeyModal
          onClose={() => setShowCreate(false)}
          onCreate={(name, scopes) => {
            const id = 'key_' + Math.random().toString(36).slice(2, 12);
            const raw = 'vk_live_' + Array.from({ length: 32 }, () =>
              'abcdefghijklmnopqrstuvwxyz0123456789'[Math.floor(Math.random() * 36)]
            ).join('');
            setKeys(ks => [{
              id, name,
              prefix: raw.slice(0, 12) + '…',
              scopes, created_at: Date.now(),
              last_used_at: Date.now(),
              usage_7d: 0, status: 'active',
            }, ...ks]);
            setNewKey(raw);
            setShowCreate(false);
            toast.success('Key created');
          }}
        />
      )}

      <ConfirmModal
        open={!!revokeTarget}
        title={`Revoke "${revokeTarget?.name}"?`}
        danger
        body="Any service using this key will immediately lose access. This cannot be undone."
        confirmLabel="Revoke key"
        requireType="revoke"
        onCancel={() => setRevokeTarget(null)}
        onConfirm={revoke}
      />
    </>
  );
}

function CreateKeyModal({ onClose, onCreate }) {
  const [name, setName] = useState('');
  const [scopes, setScopes] = useState(['reviews:read']);
  const [dirty, setDirty] = useState(false);
  const nameErr = dirty && !name.trim();

  const toggle = (key) => {
    setScopes(ss => ss.includes(key) ? ss.filter(s => s !== key) : [...ss, key]);
  };

  const submit = () => {
    setDirty(true);
    if (!name.trim()) return;
    if (scopes.length === 0) return;
    onCreate(name.trim(), scopes);
  };

  return (
    <>
      <div className="overlay" onClick={onClose} />
      <div className="modal" style={{ width: 460 }}>
        <div className="modal-head">
          <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>New API key</h3>
        </div>
        <div className="modal-body">
          <div className="field">
            <label className="label">Name</label>
            <input
              className={`input${nameErr ? ' input-error' : ''}`}
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. CI pipeline"
              autoFocus
            />
            {nameErr && <div className="field-error">Name is required</div>}
          </div>
          <div className="field" style={{ marginBottom: 0 }}>
            <label className="label">Scopes</label>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 4 }}>
              {ALL_SCOPES.map(s => (
                <label key={s.key} style={{
                  display: 'flex', alignItems: 'flex-start', gap: 10,
                  padding: '10px 12px',
                  background: scopes.includes(s.key) ? 'rgba(108,99,255,.08)' : 'var(--input-bg)',
                  border: '1px solid ' + (scopes.includes(s.key) ? 'rgba(108,99,255,.35)' : 'var(--border)'),
                  borderRadius: 6, cursor: 'pointer',
                  transition: 'background .1s ease, border-color .1s ease',
                }}>
                  <input
                    type="checkbox"
                    checked={scopes.includes(s.key)}
                    onChange={() => toggle(s.key)}
                    style={{ marginTop: 2, accentColor: 'var(--accent)', flexShrink: 0 }}
                  />
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: 13, fontWeight: 500 }}>{s.label}</div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>{s.desc}</div>
                  </div>
                </label>
              ))}
            </div>
          </div>
        </div>
        <div className="modal-foot">
          <button className="btn" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={submit} disabled={scopes.length === 0}>
            Create key
          </button>
        </div>
      </div>
    </>
  );
}

window.ApiKeysScreen = ApiKeysScreen;
