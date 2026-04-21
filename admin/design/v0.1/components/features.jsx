// Feature-flag snapshot loader, useFeature hook, and FeatureGate component.
// Requires shell.jsx to be loaded first (React destructuring already done there).

// ---------------------------------------------------------------------------
// Context + Provider
// ---------------------------------------------------------------------------

const FeatureFlagsCtx = createContext({ flags: {}, catalog: [], loading: true, error: null });

/**
 * FeatureFlagsProvider — fetch /admin/features once, cache for the session.
 *
 * Wrap the app root with this provider so useFeature() and FeatureGate work
 * anywhere in the tree without prop-drilling.
 */
function FeatureFlagsProvider({ children }) {
  const [state, setState] = useState({ flags: {}, catalog: [], loading: true, error: null });

  useEffect(() => {
    let cancelled = false;
    fetch('/admin/features')
      .then(r => r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)))
      .then(data => {
        if (!cancelled) setState({ flags: data.flags, catalog: data.catalog, loading: false, error: null });
      })
      .catch(err => {
        if (!cancelled) setState(s => ({ ...s, loading: false, error: err.message }));
      });
    return () => { cancelled = true; };
  }, []);

  return React.createElement(FeatureFlagsCtx.Provider, { value: state }, children);
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

/**
 * useFeature(key) — returns true when the named flag is enabled.
 * Returns false while the snapshot is loading or on error.
 *
 * @param {string} key  e.g. "vcs.gitlab" or "pipeline.security_scan"
 * @returns {boolean}
 */
function useFeature(key) {
  const { flags } = useContext(FeatureFlagsCtx);
  return flags[key] === true;
}

/**
 * useFeatureFlags() — returns the full context: { flags, catalog, loading, error }.
 * Use when you need the loading state or the catalog metadata.
 */
function useFeatureFlags() {
  return useContext(FeatureFlagsCtx);
}

// ---------------------------------------------------------------------------
// Components
// ---------------------------------------------------------------------------

/**
 * FeatureGate — renders children only when the named flag is enabled.
 *
 * Props:
 *   name      {string}    Feature flag key, e.g. "pipeline.security_scan"
 *   fallback  {ReactNode} Content to render when flag is off (default: null)
 *   children  {ReactNode} Content to render when flag is on
 *
 * Examples:
 *   <FeatureGate name="pipeline.security_scan">
 *     <SecurityScanPanel />
 *   </FeatureGate>
 *
 *   <FeatureGate name="platform.multi_tenant" fallback={<p>Upgrade required</p>}>
 *     <TenantList />
 *   </FeatureGate>
 */
function FeatureGate({ name, fallback = null, children }) {
  const enabled = useFeature(name);
  return enabled ? children : fallback;
}

// ---------------------------------------------------------------------------
// FeaturesScreen — Settings > Features page (design-system version)
// ---------------------------------------------------------------------------

const CATEGORY_ORDER = ['vcs', 'llm', 'pipeline', 'ast', 'vector', 'platform'];
const CATEGORY_LABELS = {
  vcs:      'VCS Adapters',
  llm:      'LLM Providers',
  pipeline: 'Pipeline Stages',
  ast:      'AST Providers',
  vector:   'Vector Stores',
  platform: 'Platform',
};

function ToggleSwitch({ checked, onChange, disabled }) {
  return (
    <div
      onClick={disabled ? undefined : onChange}
      role="switch"
      aria-checked={checked}
      style={{
        display: 'inline-flex', alignItems: 'center', width: 36, height: 20,
        borderRadius: 10, background: checked ? 'var(--accent)' : 'var(--border)',
        cursor: disabled ? 'not-allowed' : 'pointer', transition: 'background .15s',
        position: 'relative', flexShrink: 0,
      }}
    >
      <span style={{
        position: 'absolute', top: 2, left: checked ? 18 : 2, width: 16, height: 16,
        borderRadius: '50%', background: '#fff', transition: 'left .15s',
        boxShadow: '0 1px 3px rgba(0,0,0,.3)',
      }} />
    </div>
  );
}

function FlagRow({ flag, onToggle }) {
  const [saving, setSaving] = useState(false);

  async function handleToggle() {
    if (saving) return;
    setSaving(true);
    try {
      const res = await fetch(`/admin/features/${encodeURIComponent(flag.key)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: !flag.enabled }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      onToggle(flag.key, !flag.enabled);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div style={{
      display: 'flex', alignItems: 'center', padding: '14px 20px',
      borderBottom: '1px solid var(--border)', gap: 16,
    }}>
      <div style={{ flex: 1, minWidth: 0 }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)', display: 'block' }}>
          {flag.name}
        </span>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-muted)', display: 'block', marginTop: 1 }}>
          {flag.key}
        </span>
        <span style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginTop: 3 }}>
          {flag.description}
        </span>
      </div>
      <ToggleSwitch checked={flag.enabled} onChange={handleToggle} disabled={saving} />
    </div>
  );
}

function FlagGroup({ category, flags, onToggle }) {
  return (
    <div style={{
      marginBottom: 24, background: 'var(--surface)',
      border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden',
    }}>
      <div style={{
        padding: '10px 20px', fontSize: 11, fontWeight: 600, textTransform: 'uppercase',
        letterSpacing: '0.7px', color: 'var(--text-muted)', background: 'var(--surface-2)',
        borderBottom: '1px solid var(--border)',
      }}>
        {CATEGORY_LABELS[category] || category}
      </div>
      {flags.map(f => <FlagRow key={f.key} flag={f} onToggle={onToggle} />)}
    </div>
  );
}

function FeatureFlagsScreen() {
  const { catalog, loading, error } = useFeatureFlags();
  const [localCatalog, setLocalCatalog] = useState([]);

  useEffect(() => { setLocalCatalog(catalog); }, [catalog]);

  function handleToggle(key, newEnabled) {
    setLocalCatalog(prev => prev.map(f => f.key === key ? { ...f, enabled: newEnabled } : f));
  }

  if (loading) return <p style={{ color: 'var(--text-muted)', padding: '24px 0' }}>Loading feature flags…</p>;
  if (error)   return <p style={{ color: 'var(--error)', padding: '24px 0' }}>Failed to load: {error}</p>;

  const grouped = localCatalog.reduce((acc, f) => {
    (acc[f.category] = acc[f.category] || []).push(f);
    return acc;
  }, {});

  return (
    <div>
      {CATEGORY_ORDER.filter(c => grouped[c]).map(c => (
        <FlagGroup key={c} category={c} flags={grouped[c]} onToggle={handleToggle} />
      ))}
    </div>
  );
}
