// Route: /settings/repos  — Repo Allow-list (with per-repo model)
// Entry: <ReposSettingsScreen navigate={...} state={...} setState={...} />

function ReposSettingsScreen({ navigate, state, setState }) {
  const toast = useToast();
  const [editing, setEditing] = useState(null); // { mode: 'new' | 'edit', repo }
  const [confirmDel, setConfirmDel] = useState(null);

  const toggle = (id) => {
    setState(s => ({ ...s, repos: s.repos.map(r => r.id === id ? { ...r, enabled: !r.enabled } : r) }));
  };
  const del = (repo) => {
    setState(s => ({ ...s, repos: s.repos.filter(r => r.id !== repo.id) }));
    toast.success(`Removed ${repo.slug}`);
    setConfirmDel(null);
  };
  const save = (payload) => {
    const slug = payload.repo === '*' ? `${payload.org}/*` : `${payload.org}/${payload.repo}`;
    if (editing.mode === 'new') {
      setState(s => ({ ...s, repos: [...s.repos, { id: Date.now(), platform: payload.platform, slug, enabled: true, provider: payload.provider, model: payload.model }] }));
      toast.success(`Added ${slug}`);
    } else {
      setState(s => ({ ...s, repos: s.repos.map(r => r.id === editing.repo.id ? { ...r, platform: payload.platform, slug, provider: payload.provider, model: payload.model } : r) }));
      toast.success(`Updated ${slug}`);
    }
    setEditing(null);
  };

  return (
    <>
      <PageHeader
        title="Repositories"
        subtitle="Each repo picks its own model. Bring your own keys via Providers."
        action={<button className="btn btn-primary" onClick={() => setEditing({ mode: 'new' })}>{I.plus} Add repository</button>}
      />

      {state.repos.length === 0 ? (
        <EmptyState
          icon={I.repos}
          title="No repositories — analysis is paused"
          body="Add a repository to start listening for pull requests."
          action={<button className="btn btn-primary" onClick={() => setEditing({ mode: 'new' })}>{I.plus} Add repository</button>}
        />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {state.repos.map(r => (
            <div key={r.id} className="card" style={{ padding: '14px 18px', display: 'grid', gridTemplateColumns: '30px 1fr auto auto auto', alignItems: 'center', gap: 14 }}>
              <span style={{ width: 30, height: 30, borderRadius: 6, background: 'var(--surface-2)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', color: r.platform === 'github' ? '#e8eaf0' : '#f0a05a' }}>
                {r.platform === 'github' ? I.github : I.gitlab}
              </span>
              <div style={{ minWidth: 0 }}>
                <div className="mono" style={{ fontSize: 13.5 }}>{r.slug}</div>
                <div style={{ fontSize: 11.5, color: 'var(--text-muted)', marginTop: 3, display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                  <span className="mono">{PROVIDER_LABELS[r.provider]} · {r.model}</span>
                  {isCloud(r.provider) && (
                    <span className="badge badge-warning" style={{ height: 16, fontSize: 10, padding: '0 6px' }}>
                      <span style={{ display: 'inline-flex', transform: 'scale(.75)' }}>{I.warn}</span> cloud
                    </span>
                  )}
                </div>
              </div>
              <button className="btn btn-ghost btn-sm" onClick={() => setEditing({ mode: 'edit', repo: r })} style={{ color: 'var(--text-muted)' }}>Edit</button>
              <label style={{ display: 'inline-flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                <span style={{ fontSize: 12, color: r.enabled ? 'var(--success)' : 'var(--text-muted)', minWidth: 48, textAlign: 'right' }}>{r.enabled ? 'Enabled' : 'Disabled'}</span>
                <button className={`toggle ${r.enabled ? 'on' : ''}`} onClick={() => toggle(r.id)} />
              </label>
              <button className="btn btn-ghost btn-sm" onClick={() => setConfirmDel(r)} title="Remove" style={{ color: 'var(--text-muted)', padding: '0 8px' }}>
                {I.trash}
              </button>
            </div>
          ))}
        </div>
      )}

      {editing && <RepoModal editing={editing} onClose={() => setEditing(null)} onSave={save} />}
      <ConfirmModal
        open={!!confirmDel}
        title="Remove repository?"
        body={confirmDel && <>Vellic will stop analyzing <code style={{ color: 'var(--text)' }}>{confirmDel.slug}</code>. Incoming webhooks will be ignored.</>}
        confirmLabel="Remove"
        danger
        onCancel={() => setConfirmDel(null)}
        onConfirm={() => del(confirmDel)}
      />
    </>
  );
}

const MODEL_SUGGESTIONS = {
  ollama:      ['qwen2.5-coder:14b', 'qwen2.5-coder:32b', 'deepseek-coder-v2:16b', 'codellama:34b'],
  vllm:        ['Qwen2.5-Coder-32B', 'DeepSeek-Coder-V2-Lite', 'Llama-3.1-70B-Instruct'],
  openai:      ['gpt-4o-mini', 'gpt-4o', 'o4-mini'],
  anthropic:   ['claude-sonnet-4', 'claude-opus-4', 'claude-haiku-4'],
  claude_code: ['claude-sonnet-4', 'claude-opus-4'],
};

function RepoModal({ editing, onClose, onSave }) {
  const existing = editing.mode === 'edit' ? editing.repo : null;
  const [platform, setPlatform] = useState(existing?.platform || 'github');
  const [org, setOrg] = useState(existing ? existing.slug.split('/')[0] : '');
  const [repo, setRepo] = useState(existing ? existing.slug.split('/')[1] : '');
  const [provider, setProvider] = useState(existing?.provider || 'ollama');
  const [model, setModel] = useState(existing?.model || MODEL_SUGGESTIONS.ollama[0]);

  // when provider switches, offer a sensible default model
  const changeProvider = (p) => {
    setProvider(p);
    if (!MODEL_SUGGESTIONS[p].includes(model)) setModel(MODEL_SUGGESTIONS[p][0]);
  };

  const valid = org.trim() && repo.trim() && model.trim();

  return (
    <>
      <div className="overlay" onClick={onClose} />
      <div className="modal" style={{ width: 'min(540px, calc(100vw - 32px))' }}>
        <div className="modal-head">
          <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>{editing.mode === 'new' ? 'Add repository' : 'Edit repository'}</h3>
        </div>
        <div className="modal-body">
          <div style={{ display: 'grid', gridTemplateColumns: '140px 1fr', gap: 12, marginBottom: 16 }}>
            <div className="field" style={{ marginBottom: 0 }}>
              <label className="label">Platform</label>
              <select className="select input" value={platform} onChange={(e) => setPlatform(e.target.value)}>
                <option value="github">GitHub</option>
                <option value="gitlab">GitLab</option>
              </select>
            </div>
            <div className="field" style={{ marginBottom: 0 }}>
              <label className="label">Organization</label>
              <input className="input mono" value={org} onChange={(e) => setOrg(e.target.value)} placeholder="acme" autoFocus />
            </div>
          </div>
          <div className="field">
            <label className="label">Repository</label>
            <input className="input mono" value={repo} onChange={(e) => setRepo(e.target.value)} placeholder="api-gateway or * for all" />
            <div className="field-hint">Use <code>*</code> to match every repo in this org.</div>
          </div>

          <div style={{ borderTop: '1px solid var(--border)', margin: '18px -20px 16px' }} />

          <div style={{ fontSize: 11.5, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.06em', fontWeight: 500, marginBottom: 12 }}>Model</div>

          <div className="field">
            <label className="label">Provider</label>
            <select className="select input" value={provider} onChange={(e) => changeProvider(e.target.value)}>
              <option value="ollama">Ollama — local</option>
              <option value="vllm">vLLM — self-hosted</option>
              <option value="openai">OpenAI — cloud</option>
              <option value="anthropic">Anthropic — cloud</option>
              <option value="claude_code">Claude Code — cloud</option>
            </select>
            <div className="field-hint">Credentials & base URL are configured in <a style={{ color: 'var(--accent)' }} href="/settings/llm" onClick={(e) => e.preventDefault()}>Providers</a>.</div>
          </div>

          {isCloud(provider) && (
            <div className="warn-banner" style={{ marginBottom: 14, fontSize: 12.5 }}>
              <span style={{ display: 'inline-flex' }}>{I.warn}</span>
              <span>Source for this repo will leave your network to {PROVIDER_LABELS[provider]}.</span>
            </div>
          )}

          <div className="field" style={{ marginBottom: 0 }}>
            <label className="label">Model</label>
            <input
              className="input mono"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder={MODEL_SUGGESTIONS[provider][0]}
              list={`models-${provider}`}
            />
            <datalist id={`models-${provider}`}>
              {MODEL_SUGGESTIONS[provider].map(m => <option key={m} value={m} />)}
            </datalist>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 8 }}>
              {MODEL_SUGGESTIONS[provider].map(m => (
                <button
                  key={m}
                  className="btn btn-sm"
                  onClick={() => setModel(m)}
                  style={{ height: 22, fontSize: 11, padding: '0 8px', background: model === m ? 'var(--accent)' : 'var(--surface-2)', borderColor: model === m ? 'var(--accent)' : 'var(--border)', color: model === m ? '#fff' : 'var(--text-muted)' }}
                >
                  {m}
                </button>
              ))}
            </div>
          </div>
        </div>
        <div className="modal-foot">
          <button className="btn" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" disabled={!valid} onClick={() => onSave({ platform, org: org.trim(), repo: repo.trim(), provider, model: model.trim() })}>
            {editing.mode === 'new' ? 'Add' : 'Save'}
          </button>
        </div>
      </div>
    </>
  );
}

window.ReposSettingsScreen = ReposSettingsScreen;
