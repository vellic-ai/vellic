// Route: /setup  — first-run onboarding wizard
// Entry: <OnboardingScreen navigate={...} />

function OnboardingScreen({ navigate }) {
  const [step, setStep] = useState(1);
  const totalSteps = 5;

  // Step 1
  const [pw, setPw] = useState('');
  const [pw2, setPw2] = useState('');
  // Step 2
  const [provider, setProvider] = useState({ kind: 'ollama', base_url: 'http://ollama:11434', model: 'qwen2.5-coder:14b', api_key_raw: '' });
  // Step 3
  const [whUrl, setWhUrl] = useState('https://vellic.local/webhooks');
  const [hmac] = useState('whsec_' + Array.from({length: 32}, () => 'abcdefghijklmnopqrstuvwxyz0123456789'[Math.floor(Math.random()*36)]).join(''));
  const [hmacSaved, setHmacSaved] = useState(false);
  const [hmacCopied, setHmacCopied] = useState(false);
  const [ghOpen, setGhOpen] = useState(false);
  const [ghAppId, setGhAppId] = useState('');
  const [ghInst, setGhInst] = useState('');
  const [ghKey, setGhKey] = useState('');
  const [glOpen, setGlOpen] = useState(false);
  const [glToken, setGlToken] = useState('');
  // Step 4
  const [platform, setPlatform] = useState('github');
  const [org, setOrg] = useState('');
  const [repoName, setRepoName] = useState('');

  // Password strength
  const pwStrength = (() => {
    let s = 0;
    if (pw.length >= 12) s++;
    if (/[A-Z]/.test(pw) && /[a-z]/.test(pw)) s++;
    if (/\d/.test(pw)) s++;
    if (/[^A-Za-z0-9]/.test(pw)) s++;
    return s;
  })();
  const pwValid = pw.length >= 12 && pw === pw2;

  const canNext = () => {
    if (step === 1) return pwValid;
    if (step === 2) return provider.model && (isCloud(provider.kind) ? provider.api_key_raw : provider.base_url);
    if (step === 3) return whUrl.trim() && hmacSaved;
    return true;
  };

  const next = () => {
    if (step < totalSteps) setStep(s => s + 1);
  };
  const skip2 = () => setStep(3);

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '48px 20px' }}>
      <div style={{ marginBottom: 28 }}><Wordmark size={28} subtitle="admin · setup" /></div>

      <div style={{ width: '100%', maxWidth: 520 }}>
        {/* Progress */}
        <div style={{ marginBottom: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <span style={{ fontSize: 12, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.06em' }}>Step {step} of {totalSteps}</span>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{Math.round((step/totalSteps)*100)}%</span>
          </div>
          <div style={{ height: 4, background: 'var(--surface-2)', borderRadius: 2, overflow: 'hidden' }}>
            <div style={{ height: '100%', width: `${(step/totalSteps)*100}%`, background: 'var(--accent)', transition: 'width .25s ease' }} />
          </div>
        </div>

        <div className="card" style={{ padding: 28 }}>
          {step === 1 && (
            <>
              <StepTitle n={1} t="Set admin password" s="This unlocks the admin console. Store it securely — there is no recovery." />
              <div className="field">
                <label className="label">New password</label>
                <input className="input" type="password" value={pw} onChange={(e) => setPw(e.target.value)} placeholder="At least 12 characters" autoFocus />
                {pw && (
                  <div style={{ display: 'flex', gap: 4, marginTop: 8 }}>
                    {[0,1,2,3].map(i => (
                      <div key={i} style={{ flex: 1, height: 3, borderRadius: 2, background: i < pwStrength ? (pwStrength >= 3 ? 'var(--success)' : pwStrength >= 2 ? 'var(--warning-text)' : 'var(--error)') : 'var(--surface-2)' }} />
                    ))}
                  </div>
                )}
              </div>
              <div className="field" style={{ marginBottom: 0 }}>
                <label className="label">Confirm password</label>
                <input className="input" type="password" value={pw2} onChange={(e) => setPw2(e.target.value)} />
                {pw2 && pw !== pw2 && <div className="field-error">Passwords don't match</div>}
              </div>
            </>
          )}

          {step === 2 && (
            <>
              <StepTitle n={2} t="LLM provider" s="Choose which model reviews your PRs." />
              <div className="field">
                <label className="label">Provider</label>
                <select className="select input" value={provider.kind} onChange={(e) => setProvider(p => ({ ...p, kind: e.target.value }))}>
                  <option value="ollama">Ollama — local</option>
                  <option value="vllm">vLLM — self-hosted</option>
                  <option value="openai">OpenAI — cloud</option>
                  <option value="anthropic">Anthropic — cloud</option>
                  <option value="claude_code">Claude Code — cloud</option>
                </select>
              </div>
              {isCloud(provider.kind) && (
                <div className="warn-banner" style={{ marginBottom: 14 }}>
                  <span style={{ display: 'inline-flex' }}>{I.warn}</span>
                  <span>Source code will leave your network to {PROVIDER_LABELS[provider.kind]}.</span>
                </div>
              )}
              {!isCloud(provider.kind) ? (
                <div className="field">
                  <label className="label">Base URL</label>
                  <input className="input mono" value={provider.base_url} onChange={(e) => setProvider(p => ({ ...p, base_url: e.target.value }))} />
                </div>
              ) : (
                <div className="field">
                  <label className="label">API Key</label>
                  <input className="input mono" type="password" placeholder="sk-…" value={provider.api_key_raw} onChange={(e) => setProvider(p => ({ ...p, api_key_raw: e.target.value }))} />
                </div>
              )}
              <div className="field" style={{ marginBottom: 0 }}>
                <label className="label">Model</label>
                <input className="input mono" value={provider.model} onChange={(e) => setProvider(p => ({ ...p, model: e.target.value }))} />
              </div>
            </>
          )}

          {step === 3 && (
            <>
              <StepTitle n={3} t="Webhook" s="Configure how GitHub and GitLab reach your instance." />
              <div className="field">
                <label className="label">Public URL <span style={{ color: 'var(--text-muted)' }}>· required</span></label>
                <input className="input mono" value={whUrl} onChange={(e) => setWhUrl(e.target.value)} />
              </div>
              <div className="field">
                <label className="label">HMAC signing secret · shown once</label>
                <div style={{ display: 'flex', gap: 6 }}>
                  <input className="input mono" value={hmac} readOnly style={{ fontSize: 11.5 }} />
                  <button className="btn btn-sm" onClick={() => { navigator.clipboard?.writeText(hmac); setHmacCopied(true); setTimeout(() => setHmacCopied(false), 1200); }}>
                    {hmacCopied ? I.check : I.copy}
                  </button>
                </div>
                <label style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 10, cursor: 'pointer', fontSize: 13 }}>
                  <input type="checkbox" checked={hmacSaved} onChange={(e) => setHmacSaved(e.target.checked)} />
                  <span>I've saved this secret somewhere safe.</span>
                </label>
              </div>

              <Collapsible open={ghOpen} onToggle={() => setGhOpen(o => !o)} label="GitHub App (optional)">
                <div className="field"><label className="label">App ID</label><input className="input mono" value={ghAppId} onChange={(e) => setGhAppId(e.target.value)} /></div>
                <div className="field"><label className="label">Installation ID</label><input className="input mono" value={ghInst} onChange={(e) => setGhInst(e.target.value)} /></div>
                <div className="field" style={{ marginBottom: 0 }}><label className="label">Private key (PEM)</label><textarea className="textarea mono" rows={4} value={ghKey} onChange={(e) => setGhKey(e.target.value)} style={{ fontSize: 11.5 }} /></div>
              </Collapsible>
              <Collapsible open={glOpen} onToggle={() => setGlOpen(o => !o)} label="GitLab token (optional)">
                <div className="field" style={{ marginBottom: 0 }}><label className="label">Personal access token</label><input className="input mono" type="password" value={glToken} onChange={(e) => setGlToken(e.target.value)} placeholder="glpat-…" /></div>
              </Collapsible>
            </>
          )}

          {step === 4 && (
            <>
              <StepTitle n={4} t="Add first repository" s="Optional — you can always add more later." />
              <div className="field">
                <label className="label">Platform</label>
                <select className="select input" value={platform} onChange={(e) => setPlatform(e.target.value)}>
                  <option value="github">GitHub</option>
                  <option value="gitlab">GitLab</option>
                </select>
              </div>
              <div className="field"><label className="label">Organization</label><input className="input mono" value={org} onChange={(e) => setOrg(e.target.value)} placeholder="acme" /></div>
              <div className="field" style={{ marginBottom: 0 }}><label className="label">Repository</label><input className="input mono" value={repoName} onChange={(e) => setRepoName(e.target.value)} placeholder="api-gateway or *" /></div>
            </>
          )}

          {step === 5 && (
            <>
              <StepTitle n={5} t="You're set up" s="Vellic is ready to review." />
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 20 }}>
                <SumRow ok label="Admin password" value="Set" />
                <SumRow ok label="LLM provider" value={`${PROVIDER_LABELS[provider.kind]} · ${provider.model}`} />
                <SumRow ok label="Webhook URL" value={whUrl} />
                <SumRow ok={!!(org && repoName)} label="First repository" value={org && repoName ? `${platform}:${org}/${repoName}` : 'Skipped'} />
              </div>
              <button className="btn btn-primary btn-lg" style={{ width: '100%' }} onClick={() => navigate('/')}>Go to Dashboard</button>
            </>
          )}

          {/* Footer nav (not on final step) */}
          {step < 5 && (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 24, paddingTop: 18, borderTop: '1px solid var(--border)' }}>
              <div>
                {step === 2 && <button className="btn btn-ghost btn-sm" onClick={skip2}>Skip for now</button>}
                {step === 4 && <button className="btn btn-ghost btn-sm" onClick={() => setStep(5)}>Skip</button>}
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                {step > 1 && <button className="btn" onClick={() => setStep(s => s - 1)}>Back</button>}
                <button className="btn btn-primary" onClick={next} disabled={!canNext()}>Continue</button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function StepTitle({ n, t, s }) {
  return (
    <div style={{ marginBottom: 20 }}>
      <div style={{ fontSize: 11.5, color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: '.06em', marginBottom: 4, fontWeight: 600 }}>Step {n}</div>
      <h2 style={{ margin: 0, fontSize: 20, fontWeight: 600, letterSpacing: '-.01em' }}>{t}</h2>
      {s && <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 6 }}>{s}</div>}
    </div>
  );
}
function Collapsible({ open, onToggle, label, children }) {
  return (
    <div style={{ border: '1px solid var(--border)', borderRadius: 6, marginBottom: 10 }}>
      <button className="btn btn-ghost" onClick={onToggle} style={{ width: '100%', justifyContent: 'space-between', background: 'transparent', borderColor: 'transparent', padding: '10px 14px', height: 'auto', fontSize: 13 }}>
        <span>{label}</span>
        <span style={{ display: 'inline-flex', transform: open ? 'rotate(180deg)' : 'none', transition: 'transform .15s' }}>{I.chevronDown}</span>
      </button>
      {open && <div style={{ padding: '4px 14px 14px' }}>{children}</div>}
    </div>
  );
}
function SumRow({ ok, label, value }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 12px', background: 'var(--surface-2)', borderRadius: 6 }}>
      <span style={{ color: ok ? 'var(--success)' : 'var(--text-muted)', display: 'inline-flex' }}>
        {ok ? I.check : <span style={{ width: 14, height: 14, borderRadius: '50%', border: '1.5px solid currentColor', display: 'inline-block' }} />}
      </span>
      <span style={{ fontSize: 13 }}>{label}</span>
      <span style={{ flex: 1 }} />
      <span className="mono" style={{ fontSize: 12, color: 'var(--text-muted)' }}>{value}</span>
    </div>
  );
}

window.OnboardingScreen = OnboardingScreen;
