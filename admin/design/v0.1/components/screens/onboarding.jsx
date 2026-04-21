// Route: /setup — onboarding wizard (VEL-75)
// Steps: Welcome → Provider → Connect repos → Webhook → Live checklist → First review ready
// Entry: <OnboardingScreen navigate={fn} />

function OnboardingScreen({ navigate }) {
  const { useState, useEffect } = React;

  const TOTAL = 6;
  const STEP_LABELS = ['Welcome', 'Provider', 'Connect', 'Webhook', 'Verifying', 'Ready'];

  const [step, setStep] = useState(1);

  // ── Step 2: Provider ──────────────────────────────────────────────────────
  const [provider, setProvider] = useState({
    kind: 'openai',
    base_url: 'http://localhost:11434',
    model: 'gpt-4o',
    api_key_raw: '',
  });
  const [testState, setTestState]   = useState('idle'); // idle | loading | success | error
  const [testError, setTestError]   = useState('');

  // ── Step 3: VCS connection ────────────────────────────────────────────────
  const [vcsMode, setVcsMode]       = useState('github');
  const [authMethod, setAuthMethod] = useState('oauth');
  const [pat, setPat]               = useState('');
  const [oauthDone, setOauthDone]   = useState(false);
  const [reposLoaded, setReposLoaded] = useState(false);
  const [repos, setRepos]           = useState([
    { id: 1, name: 'acme/api-gateway', selected: false },
    { id: 2, name: 'acme/frontend',    selected: false },
    { id: 3, name: 'acme/worker',      selected: false },
  ]);

  // ── Step 4: Webhook ───────────────────────────────────────────────────────
  const [webhookMode, setWebhookMode] = useState('auto');
  const [whUrl, setWhUrl]             = useState('https://vellic.example.com/webhooks/github');
  const [hmac]                        = useState(
    'whsec_' + Array.from({ length: 32 }, () =>
      'abcdefghijklmnopqrstuvwxyz0123456789'[Math.floor(Math.random() * 36)]
    ).join('')
  );
  const [autoRegState, setAutoRegState] = useState('idle'); // idle | loading | done | error
  const [curlCopied, setCurlCopied]     = useState(false);
  const [hmacCopied, setHmacCopied]     = useState(false);

  // ── Step 5: Live checklist ────────────────────────────────────────────────
  const [checks, setChecks]           = useState([
    { id: 'provider', label: 'LLM provider connected',  status: 'pending' },
    { id: 'webhook',  label: 'Webhook registered',       status: 'pending' },
    { id: 'pr',       label: 'First PR detected',        status: 'pending' },
  ]);
  const [checksStarted, setChecksStarted] = useState(false);

  // ── Step 6: First review ──────────────────────────────────────────────────
  const [firstPR] = useState({
    repo: 'acme/api-gateway', number: 47,
    title: 'feat: add rate limiting middleware', url: '#',
  });

  // ── Simulate: test connection ─────────────────────────────────────────────
  const testConnection = () => {
    setTestState('loading');
    setTestError('');
    setTimeout(() => {
      const hasKey = !isCloud(provider.kind) || provider.api_key_raw.trim();
      if (hasKey) {
        setTestState('success');
      } else {
        setTestState('error');
        setTestError('API key required for cloud providers.');
      }
    }, 1400);
  };

  // ── Simulate: OAuth ───────────────────────────────────────────────────────
  const startOAuth = () => {
    setTimeout(() => { setOauthDone(true); setReposLoaded(true); }, 1200);
  };

  // ── Simulate: PAT verify ──────────────────────────────────────────────────
  const verifyPAT = () => { if (pat.length > 4) setReposLoaded(true); };

  // ── Simulate: auto-register webhook ──────────────────────────────────────
  const autoRegister = () => {
    setAutoRegState('loading');
    setTimeout(() => setAutoRegState('done'), 1600);
  };

  // ── Step 5 polling simulation ─────────────────────────────────────────────
  useEffect(() => {
    if (step === 5 && !checksStarted) {
      setChecksStarted(true);
      [700, 1700, 3400].forEach((delay, i) => {
        setTimeout(() => {
          setChecks(prev => prev.map((c, j) => j === i ? { ...c, status: 'ok' } : c));
        }, delay);
      });
    }
  }, [step]);

  // ── Gate: can proceed? ────────────────────────────────────────────────────
  const canNext = () => {
    if (step === 2) return testState === 'success';
    if (step === 3) return reposLoaded && repos.some(r => r.selected);
    if (step === 4) return autoRegState === 'done' || webhookMode === 'manual';
    if (step === 5) return checks.every(c => c.status === 'ok');
    return true;
  };

  const goNext = () => { if (step < TOTAL) setStep(s => s + 1); };
  const goBack = () => { if (step > 1)    setStep(s => s - 1); };

  const curlCmd = [
    `curl -X POST https://api.github.com/repos/{org}/{repo}/hooks \\`,
    `  -H "Authorization: token YOUR_GH_TOKEN" \\`,
    `  -H "Content-Type: application/json" \\`,
    `  -d '{`,
    `    "name": "web", "active": true,`,
    `    "events": ["pull_request", "push"],`,
    `    "config": {`,
    `      "url": "${whUrl}",`,
    `      "secret": "${hmac}",`,
    `      "content_type": "json"`,
    `    }`,
    `  }'`,
  ].join('\n');

  // ─────────────────────────────────────────────────────────────────────────
  return (
    <div style={{
      minHeight: '100vh', background: 'var(--bg)',
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      padding: '44px 20px 64px',
    }}>

      {/* Wordmark */}
      <div style={{ marginBottom: 32 }}>
        <Wordmark size={26} subtitle="setup" />
      </div>

      {/* ── Stepper ── */}
      <div style={{ width: '100%', maxWidth: 560, marginBottom: 28 }}>
        <div style={{ display: 'flex', alignItems: 'flex-start' }}>
          {STEP_LABELS.map((label, i) => {
            const n    = i + 1;
            const done = step > n;
            const active = step === n;
            const last = i === STEP_LABELS.length - 1;
            return (
              <React.Fragment key={n}>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 5 }}>
                  <div style={{
                    width: 26, height: 26, borderRadius: '50%',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 11, fontWeight: 700, flexShrink: 0,
                    transition: 'all .2s ease',
                    background: done   ? 'var(--success)'
                              : active ? 'var(--accent)'
                              :          'var(--surface-2)',
                    color: (done || active) ? '#fff' : 'var(--text-muted)',
                    border: `2px solid ${done   ? 'var(--success)'
                                       : active ? 'var(--accent)'
                                       :          'var(--border)'}`,
                  }}>
                    {done
                      ? <svg width="11" height="11" viewBox="0 0 11 11" fill="none">
                          <path d="M2 5.5l2.5 2.5 4.5-4.5" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                        </svg>
                      : n}
                  </div>
                  <span style={{
                    fontSize: 10, letterSpacing: '.02em', whiteSpace: 'nowrap',
                    color: active ? 'var(--text)' : 'var(--text-muted)',
                    fontWeight: active ? 600 : 400,
                  }}>{label}</span>
                </div>
                {!last && (
                  <div style={{
                    flex: 1, height: 2, marginTop: 11, marginInline: 4,
                    background: done ? 'var(--success)' : 'var(--border)',
                    transition: 'background .3s ease',
                  }} />
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* ── Card ── */}
      <div className="card" style={{ width: '100%', maxWidth: 560, padding: 30 }}>

        {/* ════════════════════════════════════════════════════════════════
            STEP 1 — Welcome
        ════════════════════════════════════════════════════════════════ */}
        {step === 1 && (
          <div>
            <div style={{ textAlign: 'center', marginBottom: 28 }}>
              <div style={{
                width: 54, height: 54, borderRadius: 14, margin: '0 auto 18px',
                background: 'linear-gradient(135deg, var(--accent) 0%, #a78bfa 100%)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                boxShadow: '0 8px 28px rgba(108,99,255,.32)',
              }}>
                <svg width="26" height="26" viewBox="0 0 24 24" fill="none">
                  <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"
                    stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
              <h1 style={{ margin: '0 0 10px', fontSize: 23, fontWeight: 700, letterSpacing: '-.02em' }}>
                Welcome to Vellic
              </h1>
              <p style={{
                margin: '0 auto', color: 'var(--text-muted)', fontSize: 14, lineHeight: 1.65,
                maxWidth: 380,
              }}>
                AI-powered code review that integrates with GitHub and GitLab —
                from install to your first review in under 10 minutes.
              </p>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 28 }}>
              {[
                { icon: '🔌', title: 'Connect your LLM',   desc: 'Ollama, vLLM, OpenAI, Anthropic — any provider, local or cloud.' },
                { icon: '🔗', title: 'Link your repos',     desc: 'OAuth or personal access token — no admin rights required.' },
                { icon: '⚡', title: 'Get instant reviews', desc: 'Every PR automatically triggers a structured AI review.' },
              ].map(item => (
                <div key={item.title} style={{
                  display: 'flex', gap: 14, padding: '13px 15px',
                  background: 'var(--surface-2)', borderRadius: 8,
                  border: '1px solid var(--border)',
                }}>
                  <span style={{ fontSize: 19, lineHeight: '20px', flexShrink: 0, marginTop: 1 }}>{item.icon}</span>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 3 }}>{item.title}</div>
                    <div style={{ fontSize: 12.5, color: 'var(--text-muted)', lineHeight: 1.5 }}>{item.desc}</div>
                  </div>
                </div>
              ))}
            </div>

            <button className="btn btn-primary btn-lg" style={{ width: '100%' }} onClick={goNext}>
              Get started
              {React.createElement('svg', { width:14, height:14, viewBox:'0 0 14 14', fill:'none', style:{marginLeft:6} },
                React.createElement('path', { d:'M3 7h8M7 3l4 4-4 4', stroke:'currentColor', strokeWidth:'1.5', strokeLinecap:'round', strokeLinejoin:'round' })
              )}
            </button>
          </div>
        )}

        {/* ════════════════════════════════════════════════════════════════
            STEP 2 — Provider + test connection
        ════════════════════════════════════════════════════════════════ */}
        {step === 2 && (
          <div>
            <WizStepHead step={2} title="LLM provider"
              subtitle="Choose which model reviews your PRs. You can change this later in Settings." />

            <div className="field">
              <label className="label">Provider</label>
              <select className="select input" value={provider.kind}
                onChange={e => { setProvider(p => ({ ...p, kind: e.target.value })); setTestState('idle'); }}>
                <option value="ollama">Ollama — local</option>
                <option value="vllm">vLLM — self-hosted</option>
                <option value="openai">OpenAI — cloud</option>
                <option value="anthropic">Anthropic — cloud</option>
                <option value="claude_code">Claude Code — cloud</option>
              </select>
            </div>

            {isCloud(provider.kind) && (
              <div className="warn-banner" style={{ marginBottom: 14 }}>
                {I.warn}
                <span>Source code will leave your network to {PROVIDER_LABELS[provider.kind]}.</span>
              </div>
            )}

            {isCloud(provider.kind) ? (
              <div className="field">
                <label className="label">API key</label>
                <input className="input mono" type="password" placeholder="sk-…"
                  value={provider.api_key_raw}
                  onChange={e => { setProvider(p => ({ ...p, api_key_raw: e.target.value })); setTestState('idle'); }} />
              </div>
            ) : (
              <div className="field">
                <label className="label">Base URL</label>
                <input className="input mono" value={provider.base_url}
                  onChange={e => { setProvider(p => ({ ...p, base_url: e.target.value })); setTestState('idle'); }} />
              </div>
            )}

            <div className="field" style={{ marginBottom: 22 }}>
              <label className="label">Model</label>
              <input className="input mono" value={provider.model}
                onChange={e => { setProvider(p => ({ ...p, model: e.target.value })); setTestState('idle'); }} />
            </div>

            {/* Test connection button */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <button
                className="btn btn-primary"
                onClick={testConnection}
                disabled={testState === 'loading'}
                style={testState === 'success' ? {
                  background: 'rgba(34,197,94,.1)', borderColor: 'rgba(34,197,94,.35)',
                  color: 'var(--success)',
                } : {}}
              >
                {testState === 'loading' && <><Spinner size={12} /> Testing…</>}
                {testState === 'success' && <>{I.check} Connected</>}
                {(testState === 'idle' || testState === 'error') && 'Test connection'}
              </button>
              {testState === 'error' && (
                <span style={{ fontSize: 12.5, color: 'var(--error)' }}>{testError}</span>
              )}
            </div>
          </div>
        )}

        {/* ════════════════════════════════════════════════════════════════
            STEP 3 — GitHub / GitLab connection
        ════════════════════════════════════════════════════════════════ */}
        {step === 3 && (
          <div>
            <WizStepHead step={3} title="Connect your repos"
              subtitle="Authorize Vellic to receive webhook events and read PR metadata." />

            {/* Platform picker */}
            <div style={{
              display: 'flex', gap: 4, padding: 4,
              background: 'var(--surface-2)', borderRadius: 8, marginBottom: 18,
            }}>
              {[['github', I.github, 'GitHub'], ['gitlab', I.gitlab, 'GitLab']].map(([p, icon, label]) => (
                <button key={p} className="btn" onClick={() => {
                  setVcsMode(p); setReposLoaded(false); setOauthDone(false); setPat('');
                }} style={{
                  flex: 1, height: 30, fontSize: 12.5,
                  background: vcsMode === p ? 'var(--surface)' : 'transparent',
                  border: `1px solid ${vcsMode === p ? 'var(--border)' : 'transparent'}`,
                  color: vcsMode === p ? 'var(--text)' : 'var(--text-muted)',
                }}>
                  {icon} {label}
                </button>
              ))}
            </div>

            {/* Auth method */}
            <div style={{ display: 'flex', gap: 8, marginBottom: 18 }}>
              {[['oauth', 'OAuth (recommended)'], ['pat', 'Personal access token']].map(([m, label]) => (
                <label key={m} style={{
                  flex: 1, display: 'flex', alignItems: 'center', gap: 8,
                  padding: '9px 12px', borderRadius: 6, cursor: 'pointer', fontSize: 12.5,
                  border: `1px solid ${authMethod === m ? 'rgba(108,99,255,.45)' : 'var(--border)'}`,
                  background: authMethod === m ? 'rgba(108,99,255,.07)' : 'transparent',
                }}>
                  <input type="radio" name="authMethod" checked={authMethod === m}
                    onChange={() => { setAuthMethod(m); setReposLoaded(false); setOauthDone(false); }}
                    style={{ accentColor: 'var(--accent)' }} />
                  {label}
                </label>
              ))}
            </div>

            {/* OAuth flow */}
            {authMethod === 'oauth' && !oauthDone && (
              <button className="btn btn-primary" style={{ width: '100%', marginBottom: 16 }}
                onClick={startOAuth}>
                {vcsMode === 'github' ? I.github : I.gitlab}
                Authorize with {vcsMode === 'github' ? 'GitHub' : 'GitLab'}
              </button>
            )}
            {authMethod === 'oauth' && oauthDone && (
              <div style={{ marginBottom: 16 }}>
                <span className="badge badge-success" style={{ height: 26, paddingInline: 10, fontSize: 12 }}>
                  <span style={{ display:'inline-flex' }}>{I.check}</span> Authorized
                </span>
              </div>
            )}

            {/* PAT flow */}
            {authMethod === 'pat' && (
              <div className="field" style={{ marginBottom: 16 }}>
                <label className="label">
                  {vcsMode === 'github' ? 'GitHub' : 'GitLab'} personal access token
                </label>
                <div style={{ display: 'flex', gap: 6 }}>
                  <input className="input mono" type="password"
                    placeholder={vcsMode === 'github' ? 'ghp_…' : 'glpat-…'}
                    value={pat} onChange={e => setPat(e.target.value)} />
                  <button className="btn btn-sm btn-primary" onClick={verifyPAT}
                    disabled={pat.length < 5}>Verify</button>
                </div>
                <div className="field-hint">
                  Requires: <code className="mono" style={{ fontSize: 11.5 }}>repo</code>, <code className="mono" style={{ fontSize: 11.5 }}>read:user</code>
                </div>
              </div>
            )}

            {/* Repo selector */}
            {reposLoaded && (
              <div>
                <label className="label" style={{ marginBottom: 8 }}>Select repositories to watch</label>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 10 }}>
                  {repos.map(repo => (
                    <label key={repo.id} style={{
                      display: 'flex', alignItems: 'center', gap: 12,
                      padding: '10px 14px', borderRadius: 6, cursor: 'pointer',
                      transition: 'all .12s ease',
                      background: repo.selected ? 'rgba(108,99,255,.06)' : 'var(--surface-2)',
                      border: `1px solid ${repo.selected ? 'rgba(108,99,255,.35)' : 'var(--border)'}`,
                    }}>
                      <input type="checkbox" checked={repo.selected}
                        style={{ accentColor: 'var(--accent)', width: 14, height: 14 }}
                        onChange={e => setRepos(prev =>
                          prev.map(r => r.id === repo.id ? { ...r, selected: e.target.checked } : r)
                        )} />
                      <span className="mono" style={{ fontSize: 13 }}>{repo.name}</span>
                    </label>
                  ))}
                </div>
                <button className="btn btn-ghost btn-sm" style={{ fontSize: 12 }}>
                  {I.plus} Add repository manually
                </button>
              </div>
            )}
          </div>
        )}

        {/* ════════════════════════════════════════════════════════════════
            STEP 4 — Webhook setup
        ════════════════════════════════════════════════════════════════ */}
        {step === 4 && (
          <div>
            <WizStepHead step={4} title="Webhook setup"
              subtitle="Register a webhook so Vellic is notified on every pull request event." />

            {/* Mode tabs */}
            <div style={{
              display: 'flex', gap: 4, padding: 4,
              background: 'var(--surface-2)', borderRadius: 8, marginBottom: 20,
            }}>
              {[['auto', 'Auto-register'], ['manual', 'Manual (curl)']].map(([m, label]) => (
                <button key={m} onClick={() => setWebhookMode(m)} className="btn" style={{
                  flex: 1, height: 30, fontSize: 12.5,
                  background: webhookMode === m ? 'var(--surface)' : 'transparent',
                  border: `1px solid ${webhookMode === m ? 'var(--border)' : 'transparent'}`,
                  color: webhookMode === m ? 'var(--text)' : 'var(--text-muted)',
                }}>{label}</button>
              ))}
            </div>

            <div className="field">
              <label className="label">Vellic public URL</label>
              <input className="input mono" value={whUrl}
                onChange={e => setWhUrl(e.target.value)} />
              <div className="field-hint">
                Must be reachable from {vcsMode === 'github' ? 'GitHub' : 'GitLab'}'s servers.
              </div>
            </div>

            {/* Auto-register mode */}
            {webhookMode === 'auto' && (
              <>
                {autoRegState === 'idle' && (
                  <button className="btn btn-primary" style={{ width: '100%' }}
                    onClick={autoRegister}>
                    Auto-register webhook
                  </button>
                )}
                {autoRegState === 'loading' && (
                  <button className="btn btn-primary" style={{ width: '100%' }} disabled>
                    <Spinner size={12} /> Registering…
                  </button>
                )}
                {autoRegState === 'done' && (
                  <div style={{
                    display: 'flex', alignItems: 'center', gap: 12,
                    padding: '13px 16px', borderRadius: 8,
                    background: 'rgba(34,197,94,.06)',
                    border: '1px solid rgba(34,197,94,.25)',
                  }}>
                    <span style={{ color: 'var(--success)', display: 'inline-flex' }}>
                      {I.check}
                    </span>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--success)' }}>
                        Webhook registered
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                        Events: pull_request, push
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}

            {/* Manual curl mode */}
            {webhookMode === 'manual' && (
              <div>
                <div className="field" style={{ marginBottom: 14 }}>
                  <label className="label">
                    HMAC signing secret
                    <span style={{ color: 'var(--text-muted)', fontWeight: 400, marginLeft: 6 }}>
                      · shown once, save it now
                    </span>
                  </label>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <input className="input mono" value={hmac} readOnly
                      style={{ fontSize: 11, flex: 1 }} />
                    <button className="btn btn-sm" onClick={() => {
                      navigator.clipboard?.writeText(hmac);
                      setHmacCopied(true);
                      setTimeout(() => setHmacCopied(false), 1200);
                    }}>
                      {hmacCopied ? I.check : I.copy}
                    </button>
                  </div>
                </div>

                <div>
                  <div style={{
                    display: 'flex', alignItems: 'center',
                    justifyContent: 'space-between', marginBottom: 6,
                  }}>
                    <label className="label" style={{ margin: 0 }}>curl command</label>
                    <button className="btn btn-ghost btn-sm" style={{ fontSize: 11.5 }}
                      onClick={() => {
                        navigator.clipboard?.writeText(curlCmd);
                        setCurlCopied(true);
                        setTimeout(() => setCurlCopied(false), 1200);
                      }}>
                      {curlCopied ? I.check : I.copy}
                      {curlCopied ? ' Copied' : ' Copy'}
                    </button>
                  </div>
                  <pre style={{
                    background: 'var(--input-bg)', border: '1px solid var(--border)',
                    borderRadius: 6, padding: '12px 14px', margin: 0,
                    fontSize: 11, lineHeight: 1.75, color: 'var(--text)',
                    fontFamily: 'var(--font-mono)', overflow: 'auto',
                    whiteSpace: 'pre-wrap', wordBreak: 'break-all',
                  }}>{curlCmd}</pre>
                  <div className="field-hint" style={{ marginTop: 8 }}>
                    Run this once per repository. Repeat for additional repos.
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ════════════════════════════════════════════════════════════════
            STEP 5 — Live checklist
        ════════════════════════════════════════════════════════════════ */}
        {step === 5 && (
          <div>
            <WizStepHead step={5} title="Verifying your setup"
              subtitle="Vellic is checking each integration in real time." />

            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 20 }}>
              {checks.map(c => (
                <div key={c.id} style={{
                  display: 'flex', alignItems: 'center', gap: 14,
                  padding: '14px 16px', borderRadius: 8,
                  background: 'var(--surface-2)',
                  border: `1px solid ${c.status === 'ok' ? 'rgba(34,197,94,.25)' : 'var(--border)'}`,
                  transition: 'border-color .3s ease',
                }}>
                  {c.status === 'pending'
                    ? <Spinner size={16} />
                    : <span style={{ color: 'var(--success)', display: 'inline-flex' }}>{I.check}</span>
                  }
                  <div>
                    <div style={{
                      fontSize: 13, fontWeight: 500,
                      color: c.status === 'ok' ? 'var(--text)' : 'var(--text-muted)',
                    }}>{c.label}</div>
                    <div style={{ fontSize: 11.5, marginTop: 2,
                      color: c.status === 'ok' ? 'var(--success)' : 'var(--text-muted)',
                    }}>
                      {c.status === 'ok' ? 'Verified ✓' : 'Checking…'}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {!checks.every(c => c.status === 'ok') && (
              <p style={{
                textAlign: 'center', fontSize: 12.5,
                color: 'var(--text-muted)', margin: 0,
              }}>
                Waiting for a PR on one of your watched repos…
              </p>
            )}
          </div>
        )}

        {/* ════════════════════════════════════════════════════════════════
            STEP 6 — First review ready
        ════════════════════════════════════════════════════════════════ */}
        {step === 6 && (
          <div>
            <div style={{ textAlign: 'center', marginBottom: 24 }}>
              <div style={{
                width: 52, height: 52, borderRadius: '50%', margin: '0 auto 18px',
                background: 'rgba(34,197,94,.1)',
                border: '2px solid rgba(34,197,94,.35)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                  <path d="M5 12l5 5 9-9" stroke="var(--success)"
                    strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
              <h2 style={{ margin: '0 0 8px', fontSize: 22, fontWeight: 700, letterSpacing: '-.02em' }}>
                You're all set!
              </h2>
              <p style={{ margin: '0 auto', color: 'var(--text-muted)', fontSize: 13.5, maxWidth: 340 }}>
                Vellic detected your first PR and is generating a review now.
              </p>
            </div>

            {/* First PR card */}
            <div style={{
              padding: '16px 18px', marginBottom: 20,
              background: 'var(--surface-2)',
              border: '1px solid var(--border)', borderRadius: 8,
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
                <span className="badge badge-info">PR #{firstPR.number}</span>
                <span className="mono trunc" style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  {firstPR.repo}
                </span>
              </div>
              <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 14, lineHeight: 1.4 }}>
                {firstPR.title}
              </div>
              <a href={firstPR.url} className="btn btn-primary btn-sm" style={{ display: 'inline-flex' }}>
                View AI review
                {I.external}
              </a>
            </div>

            <button className="btn btn-primary btn-lg" style={{ width: '100%' }}
              onClick={() => navigate('/')}>
              Open Dashboard
            </button>
            <button className="btn btn-ghost" style={{ width: '100%', marginTop: 8 }}
              onClick={() => navigate('/settings/repos')}>
              Add more repositories
            </button>
          </div>
        )}

        {/* ── Nav footer (steps 2-5) ── */}
        {step > 1 && step < 6 && (
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            marginTop: 26, paddingTop: 18, borderTop: '1px solid var(--border)',
          }}>
            <button className="btn btn-ghost btn-sm" onClick={goBack}>
              {I.chevronLeft} Back
            </button>
            <div style={{ display: 'flex', gap: 8 }}>
              {step === 3 && (
                <button className="btn btn-ghost btn-sm" onClick={goNext}>
                  Skip for now
                </button>
              )}
              <button className="btn btn-primary" onClick={goNext} disabled={!canNext()}>
                {step === 5 ? 'Continue' : 'Next'} {I.chevronRight}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function WizStepHead({ step, title, subtitle }) {
  return (
    <div style={{ marginBottom: 22 }}>
      <div style={{
        fontSize: 10.5, color: 'var(--accent)', textTransform: 'uppercase',
        letterSpacing: '.08em', fontWeight: 700, marginBottom: 6,
      }}>Step {step}</div>
      <h2 style={{ margin: '0 0 6px', fontSize: 20, fontWeight: 700, letterSpacing: '-.015em' }}>
        {title}
      </h2>
      <p style={{ margin: 0, fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.5 }}>
        {subtitle}
      </p>
    </div>
  );
}

window.OnboardingScreen = OnboardingScreen;
