// Route: /login  — pre-auth
// Entry: <LoginScreen navigate={...} />

function LoginScreen({ navigate }) {
  const [pw, setPw] = useState('');
  const [err, setErr] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = (e) => {
    e.preventDefault();
    if (!pw) return;
    setLoading(true);
    setErr('');
    setTimeout(() => {
      setLoading(false);
      if (pw === 'fail') setErr('Incorrect password.');
      else navigate('/');
    }, 700);
  };

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
      <div style={{ width: '100%', maxWidth: 380 }}>
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 24 }}>
          <Wordmark size={28} subtitle="admin" />
        </div>
        <form onSubmit={submit} className="card" style={{ padding: 28 }}>
          <div className="field" style={{ marginBottom: 18 }}>
            <label className="label">Admin password</label>
            <input
              className={`input ${err ? 'error' : ''}`}
              type="password"
              value={pw}
              onChange={(e) => { setPw(e.target.value); setErr(''); }}
              autoFocus
              placeholder="Enter password"
            />
            {err && <div className="field-error">{err}</div>}
          </div>
          <button type="submit" className="btn btn-primary btn-lg" style={{ width: '100%' }} disabled={!pw || loading}>
            {loading ? <Spinner /> : null} Sign in
          </button>
        </form>
        <div style={{ textAlign: 'center', marginTop: 16, fontSize: 12, color: 'var(--text-muted)' }}>
          Self-hosted instance · v0.4.2
        </div>
      </div>
    </div>
  );
}

window.LoginScreen = LoginScreen;
