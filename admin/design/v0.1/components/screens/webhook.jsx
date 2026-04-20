// Route: /settings/webhook  — Webhook config
// Entry: <WebhookSettingsScreen navigate={...} />

function WebhookSettingsScreen({ navigate }) {
  const toast = useToast();
  const [url, setUrl] = useState(MOCK.webhook.url);
  const [urlDirty, setUrlDirty] = useState(false);
  const [hmac, setHmac] = useState(MOCK.webhook.hmac);
  const [hmacRevealed, setHmacRevealed] = useState(false);
  const [confirmRotate, setConfirmRotate] = useState(false);

  const [ghAppId, setGhAppId] = useState(MOCK.webhook.github_app_id);
  const [ghInst, setGhInst] = useState(MOCK.webhook.github_installation_id);
  const [ghKeyMode, setGhKeyMode] = useState('masked'); // masked | editing
  const [ghKeyValue, setGhKeyValue] = useState('');
  const [ghTesting, setGhTesting] = useState(false);
  const [ghTestResult, setGhTestResult] = useState(null); // 'ok' | 'err'

  const [glMode, setGlMode] = useState('masked');
  const [glToken, setGlToken] = useState('');
  const [glTesting, setGlTesting] = useState(false);
  const [glTestResult, setGlTestResult] = useState(null);

  const [savingWh, setSavingWh] = useState(false);
  const [savingGh, setSavingGh] = useState(false);
  const [savingGl, setSavingGl] = useState(false);

  const saveCard = (setter, msg) => {
    setter(true);
    setTimeout(() => { setter(false); toast.success(msg); }, 700);
  };

  const rotateHmac = () => {
    const fresh = 'whsec_' + Array.from({length: 32}, () => 'abcdefghijklmnopqrstuvwxyz0123456789'[Math.floor(Math.random()*36)]).join('');
    setHmac(fresh);
    setHmacRevealed(true);
    setConfirmRotate(false);
    toast.success('HMAC secret rotated — update it in your VCS');
  };

  const testGh = () => {
    setGhTesting(true); setGhTestResult(null);
    setTimeout(() => { setGhTesting(false); setGhTestResult('ok'); toast.success('GitHub App authenticated'); }, 900);
  };
  const testGl = () => {
    setGlTesting(true); setGlTestResult(null);
    setTimeout(() => { setGlTesting(false); setGlTestResult('ok'); toast.success('GitLab token valid'); }, 900);
  };

  return (
    <>
      <PageHeader title="Webhook" subtitle="Inbound endpoint + VCS authentication" />

      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

        {/* Webhook card */}
        <section className="card" style={{ padding: 22 }}>
          <SectionHead title="Webhook endpoint" desc="Public URL receives signed POSTs from GitHub & GitLab." />
          <div className="field">
            <label className="label">Public URL</label>
            <input className="input mono" value={url} onChange={(e) => { setUrl(e.target.value); setUrlDirty(true); }} />
            <div className="field-hint">Must be reachable from the internet and terminate TLS.</div>
          </div>
          <div className="field" style={{ marginBottom: 0 }}>
            <label className="label">HMAC signing secret</label>
            <SecretField
              value={hmac}
              masked={!hmacRevealed}
              readOnly
              canCopy
            />
            <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
              <button className="btn btn-sm" onClick={() => setHmacRevealed(r => !r)}>
                {hmacRevealed ? I.eyeOff : I.eye} {hmacRevealed ? 'Hide' : 'Reveal'}
              </button>
              <button className="btn btn-sm btn-danger" onClick={() => setConfirmRotate(true)}>Rotate</button>
            </div>
          </div>
          <CardFooter onSave={() => saveCard(setSavingWh, 'Webhook endpoint saved')} saving={savingWh} disabled={!urlDirty} />
        </section>

        {/* GitHub App */}
        <section className="card" style={{ padding: 22 }}>
          <SectionHead title="GitHub App" desc="Authenticates vellic to post review comments." />
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
            <div className="field">
              <label className="label">App ID</label>
              <input className="input mono" value={ghAppId} onChange={(e) => setGhAppId(e.target.value)} />
            </div>
            <div className="field">
              <label className="label">Installation ID</label>
              <input className="input mono" value={ghInst} onChange={(e) => setGhInst(e.target.value)} />
            </div>
          </div>
          <div className="field">
            <label className="label">Private key</label>
            {ghKeyMode === 'masked' ? (
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <div className="input mono" style={{ display: 'flex', alignItems: 'center', color: 'var(--text-muted)' }}>
                  —— BEGIN RSA PRIVATE KEY ——  ••••••••••
                </div>
                <button className="btn btn-sm" onClick={() => setGhKeyMode('editing')}>Replace</button>
              </div>
            ) : (
              <>
                <textarea className="textarea mono" rows={6} placeholder="-----BEGIN RSA PRIVATE KEY-----&#10;…&#10;-----END RSA PRIVATE KEY-----"
                          value={ghKeyValue} onChange={(e) => setGhKeyValue(e.target.value)} style={{ fontSize: 12 }} />
                <button className="btn btn-sm btn-ghost" onClick={() => { setGhKeyMode('masked'); setGhKeyValue(''); }} style={{ marginTop: 6 }}>Cancel</button>
              </>
            )}
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 4 }}>
            <button className="btn btn-sm" onClick={testGh} disabled={ghTesting}>
              {ghTesting ? <Spinner /> : null} Test connection
            </button>
            {ghTestResult === 'ok' && <span className="badge badge-success"><span className="dot dot-success" /> OK</span>}
            {ghTestResult === 'err' && <span className="badge badge-error"><span className="dot dot-error" /> Failed</span>}
          </div>
          <CardFooter onSave={() => saveCard(setSavingGh, 'GitHub App saved')} saving={savingGh} />
        </section>

        {/* GitLab */}
        <section className="card" style={{ padding: 22 }}>
          <SectionHead title="GitLab" desc="Personal access token with api + write_repository scopes." />
          <div className="field">
            <label className="label">Access token</label>
            {glMode === 'masked' ? (
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <div className="input mono" style={{ display: 'flex', alignItems: 'center', color: 'var(--text-muted)' }}>
                  glpat-••••••••••••••••••
                </div>
                <button className="btn btn-sm" onClick={() => setGlMode('editing')}>Replace</button>
              </div>
            ) : (
              <>
                <input className="input mono" type="password" placeholder="glpat-…" value={glToken} onChange={(e) => setGlToken(e.target.value)} />
                <button className="btn btn-sm btn-ghost" onClick={() => { setGlMode('masked'); setGlToken(''); }} style={{ marginTop: 6 }}>Cancel</button>
              </>
            )}
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <button className="btn btn-sm" onClick={testGl} disabled={glTesting}>
              {glTesting ? <Spinner /> : null} Test connection
            </button>
            {glTestResult === 'ok' && <span className="badge badge-success"><span className="dot dot-success" /> OK</span>}
          </div>
          <CardFooter onSave={() => saveCard(setSavingGl, 'GitLab token saved')} saving={savingGl} />
        </section>
      </div>

      <ConfirmModal
        open={confirmRotate}
        title="Rotate HMAC secret?"
        danger
        body={<>The current secret will stop working immediately. You'll need to update it in every webhook configuration on GitHub and GitLab. This cannot be undone.</>}
        confirmLabel="Rotate secret"
        requireType="rotate"
        onCancel={() => setConfirmRotate(false)}
        onConfirm={rotateHmac}
      />
    </>
  );
}

function SectionHead({ title, desc }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ fontSize: 14, fontWeight: 600 }}>{title}</div>
      {desc && <div style={{ fontSize: 12.5, color: 'var(--text-muted)', marginTop: 3 }}>{desc}</div>}
    </div>
  );
}
function CardFooter({ onSave, saving, disabled }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 18, paddingTop: 14, borderTop: '1px solid var(--border)' }}>
      <button className="btn btn-primary btn-sm" onClick={onSave} disabled={saving || disabled}>
        {saving ? <Spinner /> : null} Save
      </button>
    </div>
  );
}

window.WebhookSettingsScreen = WebhookSettingsScreen;
