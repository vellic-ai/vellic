// Route: /settings/llm  — Providers (credentials & base URLs)
// Entry: <LlmSettingsScreen navigate={...} state={...} setState={...} />
// Note: model selection lives on each repo; this screen owns keys & endpoints only.

function LlmSettingsScreen({ navigate, state, setState }) {
  const toast = useToast();
  const [providers, setProviders] = useState(() => ({
    ollama:      { base_url: 'http://ollama:11434' },
    vllm:        { base_url: 'http://vllm:8000/v1' },
    openai:      { api_key_masked: true },
    anthropic:   { api_key_masked: true },
    claude_code: { api_key_masked: true },
  }));
  const [savingKey, setSavingKey] = useState(null);

  const save = (key) => {
    setSavingKey(key);
    setTimeout(() => { setSavingKey(null); toast.success(`${PROVIDER_LABELS[key]} saved`); }, 600);
  };

  const reposUsing = (kind) => state.repos.filter(r => r.provider === kind);

  return (
    <>
      <PageHeader
        title="Providers"
        subtitle="Credentials & endpoints. Choose models per-repository under Repositories."
        action={<button className="btn btn-sm" onClick={() => navigate('/settings/repos')}>{I.repos} Manage repositories</button>}
      />

      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {['ollama','vllm','openai','anthropic','claude_code'].map(kind => (
          <ProviderCard
            key={kind}
            kind={kind}
            data={providers[kind]}
            onChange={(patch) => setProviders(p => ({ ...p, [kind]: { ...p[kind], ...patch } }))}
            reposUsing={reposUsing(kind)}
            onSave={() => save(kind)}
            saving={savingKey === kind}
          />
        ))}
      </div>
    </>
  );
}

function ProviderCard({ kind, data, onChange, reposUsing, onSave, saving }) {
  const cloud = isCloud(kind);
  const [keyEdited, setKeyEdited] = useState(false);
  const [showKey, setShowKey] = useState(false);
  const [keyRaw, setKeyRaw] = useState('');
  const [baseDirty, setBaseDirty] = useState(false);
  const dirty = keyEdited || baseDirty;

  return (
    <section className="card" style={{ padding: 20 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14 }}>
        <div style={{
          width: 32, height: 32, borderRadius: 8,
          background: cloud ? 'var(--warning-bg)' : 'var(--surface-2)',
          color: cloud ? 'var(--warning-text)' : 'var(--text-muted)',
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
          border: '1px solid ' + (cloud ? 'var(--warning-border)' : 'var(--border)'),
        }}>{cloud ? I.warn : I.llm}</div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 14, fontWeight: 600 }}>{PROVIDER_LABELS[kind]}</div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
            {cloud ? 'Cloud · source code leaves your network' : 'Self-hosted · stays in your infra'}
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          {reposUsing.length > 0 ? (
            <span className="badge badge-info" style={{ fontSize: 11 }}>
              <span className="dot dot-success" /> {reposUsing.length} {reposUsing.length === 1 ? 'repo' : 'repos'}
            </span>
          ) : (
            <span className="badge" style={{ fontSize: 11 }}><span className="dot dot-muted" /> unused</span>
          )}
        </div>
      </div>

      {cloud ? (
        <div className="field" style={{ marginBottom: 0 }}>
          <label className="label">API Key</label>
          <div style={{ position: 'relative' }}>
            <input
              className="input mono"
              type={showKey ? 'text' : 'password'}
              value={keyEdited ? keyRaw : '••••••••••••••••••••••••'}
              onFocus={() => { if (!keyEdited) { setKeyEdited(true); setKeyRaw(''); } }}
              onChange={(e) => { setKeyEdited(true); setKeyRaw(e.target.value); }}
              placeholder="sk-…"
              style={{ paddingRight: 40 }}
            />
            <button type="button" className="btn btn-ghost btn-sm"
                    onClick={() => setShowKey(s => !s)}
                    style={{ position: 'absolute', right: 4, top: 3, padding: '0 8px', height: 28 }}>
              {showKey ? I.eyeOff : I.eye}
            </button>
          </div>
          <div className="field-hint">
            {keyEdited ? 'Key will be written on save.' : 'Stored encrypted. Type to replace.'}
          </div>
        </div>
      ) : (
        <div className="field" style={{ marginBottom: 0 }}>
          <label className="label">Base URL</label>
          <input className="input mono" value={data.base_url || ''}
                 onChange={(e) => { setBaseDirty(true); onChange({ base_url: e.target.value }); }}
                 placeholder={kind === 'ollama' ? 'http://ollama:11434' : 'http://vllm:8000/v1'} />
          <div className="field-hint">OpenAI-compatible endpoint.</div>
        </div>
      )}

      {reposUsing.length > 0 && (
        <div style={{ marginTop: 14, padding: '10px 12px', background: 'var(--input-bg)', borderRadius: 6, fontSize: 12 }}>
          <div style={{ color: 'var(--text-muted)', marginBottom: 6 }}>Used by</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {reposUsing.map(r => (
              <span key={r.id} className="mono" style={{ padding: '3px 8px', background: 'var(--surface-2)', borderRadius: 4, fontSize: 11.5 }}>
                {r.slug} <span style={{ color: 'var(--text-muted)' }}>· {r.model}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 16, paddingTop: 14, borderTop: '1px solid var(--border)' }}>
        <button className="btn btn-primary btn-sm" onClick={() => { onSave(); setKeyEdited(false); setBaseDirty(false); setKeyRaw(''); }} disabled={saving || !dirty}>
          {saving ? <Spinner /> : null} Save
        </button>
      </div>
    </section>
  );
}

window.LlmSettingsScreen = LlmSettingsScreen;
