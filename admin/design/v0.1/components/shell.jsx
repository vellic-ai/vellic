// Shared app shell: sidebar + breadcrumbs + toast region + small atoms
// Provides: useToast(), <Shell>, <Breadcrumbs>, <PageHeader>, <Skeleton>, icons

const { useState, useEffect, useRef, useCallback, useMemo, createContext, useContext } = React;

// ---------- Icons (minimal, hand-drawn strokes) ----------
const Icon = ({ d, size = 16, stroke = 1.6, fill = 'none', style }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill={fill} stroke="currentColor"
       strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round" style={style}>
    {typeof d === 'string' ? <path d={d} /> : d}
  </svg>
);
const I = {
  dashboard: <Icon d="M3 12l9-8 9 8M5 10v10h4v-6h6v6h4V10" />,
  deliveries: <Icon d={<><path d="M3 7l9-4 9 4-9 4-9-4z"/><path d="M3 12l9 4 9-4"/><path d="M3 17l9 4 9-4"/></>} />,
  jobs: <Icon d={<><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>} />,
  llm: <Icon d={<><path d="M12 2a4 4 0 00-4 4v2a4 4 0 008 0V6a4 4 0 00-4-4z"/><path d="M5 11v1a7 7 0 0014 0v-1"/><path d="M12 19v3"/></>} />,
  repos: <Icon d={<><path d="M4 5a2 2 0 012-2h10l4 4v12a2 2 0 01-2 2H6a2 2 0 01-2-2V5z"/><path d="M8 13h8M8 17h5"/></>} />,
  webhook: <Icon d={<><circle cx="6" cy="18" r="3"/><circle cx="18" cy="18" r="3"/><circle cx="12" cy="6" r="3"/><path d="M12 9v4M10.5 14l-3 2M13.5 14l3 2"/></>} />,
  prompts: <Icon d={<><path d="M4 5h10M4 9h6M4 13h8"/><path d="M14 9l4 4-4 4"/></>} />,
  logout: <Icon d={<><path d="M15 4h4a1 1 0 011 1v14a1 1 0 01-1 1h-4"/><path d="M10 8l-4 4 4 4M6 12h10"/></>} />,
  copy: <Icon d={<><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 012-2h10"/></>} />,
  eye: <Icon d={<><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></>} />,
  eyeOff: <Icon d={<><path d="M3 3l18 18"/><path d="M10.6 6.2A9.9 9.9 0 0112 6c6.5 0 10 6 10 6a15 15 0 01-3 3.6M6.4 6.4A15 15 0 002 12s3.5 6 10 6a9.9 9.9 0 003.4-.6"/><path d="M9.9 9.9a3 3 0 104.2 4.2"/></>} />,
  refresh: <Icon d={<><path d="M21 12a9 9 0 11-3-6.7"/><path d="M21 4v5h-5"/></>} />,
  chevronDown: <Icon d="M6 9l6 6 6-6" />,
  chevronRight: <Icon d="M9 6l6 6-6 6" />,
  chevronLeft: <Icon d="M15 6l-6 6 6 6" />,
  x: <Icon d="M6 6l12 12M18 6L6 18" />,
  check: <Icon d="M5 12l5 5L20 7" />,
  plus: <Icon d="M12 5v14M5 12h14" />,
  trash: <Icon d={<><path d="M4 7h16"/><path d="M9 7V4h6v3"/><path d="M6 7l1 13a2 2 0 002 2h6a2 2 0 002-2l1-13"/></>} />,
  warn: <Icon d={<><path d="M12 3l10 18H2L12 3z"/><path d="M12 10v5M12 18v.1"/></>} />,
  info: <Icon d={<><circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8v.1"/></>} />,
  search: <Icon d={<><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></>} />,
  external: <Icon d={<><path d="M14 4h6v6"/><path d="M20 4l-9 9"/><path d="M18 14v5a1 1 0 01-1 1H5a1 1 0 01-1-1V7a1 1 0 011-1h5"/></>} />,
  menu: <Icon d="M4 7h16M4 12h16M4 17h16" />,
  github: <Icon d="M12 2a10 10 0 00-3.16 19.49c.5.09.68-.22.68-.48v-1.7c-2.78.6-3.37-1.34-3.37-1.34-.45-1.16-1.11-1.47-1.11-1.47-.91-.62.07-.6.07-.6 1 .07 1.53 1.03 1.53 1.03.9 1.54 2.36 1.09 2.94.83.09-.65.35-1.09.63-1.34-2.22-.25-4.56-1.11-4.56-4.94 0-1.09.39-1.98 1.03-2.68-.1-.25-.45-1.27.1-2.64 0 0 .84-.27 2.75 1.02a9.5 9.5 0 015 0c1.91-1.29 2.75-1.02 2.75-1.02.55 1.37.2 2.39.1 2.64.64.7 1.03 1.59 1.03 2.68 0 3.84-2.34 4.68-4.57 4.93.36.31.68.92.68 1.85v2.74c0 .27.18.58.69.48A10 10 0 0012 2z" stroke="none" fill="currentColor" />,
  gitlab: <Icon d="M12 21l-3.5-11H15.5L12 21zM4 10L2 16l10 5L4 10zM20 10l2 6-10 5 8-11zM8.5 10H4l2-6 2.5 6zM15.5 10H20l-2-6-2.5 6z" stroke="none" fill="currentColor" />,
  apikey: <Icon d={<><circle cx="8" cy="15" r="4"/><path d="M19 8l-5 5"/><path d="M17 6l2 2"/><path d="M15 8l2 2"/></>} />,
  rules: <Icon d={<><path d="M3 6h18M3 12h12M3 18h8"/><circle cx="18" cy="18" r="3"/><path d="M18 15v3l2 1"/></>} />,
  danger: <Icon d={<><path d="M12 3l10 18H2L12 3z"/><path d="M12 10v5M12 18v.1"/></>} fill="none" />,
  spinner: null, // custom below
};

const Spinner = ({ size = 14, color }) => (
  <span style={{
    display: 'inline-block',
    width: size, height: size,
    border: '2px solid rgba(255,255,255,.15)',
    borderTopColor: color || 'currentColor',
    borderRadius: '50%',
    animation: 'spin .7s linear infinite',
    verticalAlign: 'middle',
  }} />
);
// inject @keyframes spin once
if (!document.getElementById('spin-kf')) {
  const s = document.createElement('style');
  s.id = 'spin-kf';
  s.textContent = '@keyframes spin { to { transform: rotate(360deg); } }';
  document.head.appendChild(s);
}

// ---------- Wordmark (Λ logo + mono text) ----------
const Wordmark = ({ subtitle = 'admin', size = 20 }) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <defs>
        <linearGradient id="vellicG" x1="0" y1="24" x2="24" y2="0">
          <stop offset="0%" stopColor="#4b7cff" />
          <stop offset="100%" stopColor="#8c7cff" />
        </linearGradient>
      </defs>
      <path d="M4 21L12 3L20 21" stroke="url(#vellicG)" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 14, fontWeight: 600, letterSpacing: '.01em' }}>
      vellic <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>{subtitle}</span>
    </span>
  </div>
);

// ---------- Toast system ----------
const ToastCtx = createContext(null);
const useToast = () => useContext(ToastCtx);

function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const push = useCallback((msg, variant = 'info') => {
    const id = Math.random().toString(36).slice(2);
    setToasts((t) => [...t, { id, msg, variant }]);
    setTimeout(() => setToasts((t) => t.filter(x => x.id !== id)), 4000);
  }, []);
  const api = useMemo(() => ({
    success: (m) => push(m, 'success'),
    error: (m) => push(m, 'error'),
    info: (m) => push(m, 'info'),
  }), [push]);
  return (
    <ToastCtx.Provider value={api}>
      {children}
      <div className="toast-region">
        {toasts.map(t => (
          <div key={t.id} className={`toast toast-${t.variant}`}>
            <span style={{ marginTop: 1, color: t.variant === 'success' ? 'var(--success)' : t.variant === 'error' ? 'var(--error)' : 'var(--accent)' }}>
              {t.variant === 'success' ? I.check : t.variant === 'error' ? I.warn : I.info}
            </span>
            <span style={{ flex: 1, fontSize: 13 }}>{t.msg}</span>
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

// ---------- Sidebar ----------
const NAV = [
  { label: 'Dashboard', route: '/', icon: I.dashboard },
  { section: 'Observe', items: [
    { label: 'Deliveries', route: '/deliveries', icon: I.deliveries },
    { label: 'Jobs', route: '/jobs', icon: I.jobs },
  ]},
  { section: 'Settings', items: [
    { label: 'Providers', route: '/settings/llm', icon: I.llm },
    { label: 'Repositories', route: '/settings/repos', icon: I.repos },
    { label: 'Webhook', route: '/settings/webhook', icon: I.webhook },
    { label: 'API Keys', route: '/settings/api-keys', icon: I.apikey },
    { label: 'Rules', route: '/settings/rules', icon: I.rules },
    { label: 'Feature flags', route: '/settings/feature-flags', icon: <Icon d={<><path d="M4 21V5"/><path d="M4 5h12l-3 5 3 5H4"/></>} /> },
    { label: 'Prompt Editor', route: '/settings/prompts', icon: I.prompts },
    { label: 'Danger zone', route: '/settings/danger', icon: I.danger },
  ]},
];

function Sidebar({ route, navigate, onClose }) {
  const NavItem = ({ item }) => {
    const active = route === item.route;
    return (
      <a
        href={item.route}
        onClick={(e) => { e.preventDefault(); navigate(item.route); onClose && onClose(); }}
        className="nav-item"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          height: 32,
          padding: '0 10px',
          marginLeft: 8,
          marginRight: 8,
          borderRadius: 6,
          color: active ? 'var(--text)' : 'var(--text-muted)',
          background: active ? 'var(--surface-2)' : 'transparent',
          borderLeft: active ? '2px solid var(--accent)' : '2px solid transparent',
          paddingLeft: active ? 8 : 10,
          fontSize: 13,
          fontWeight: active ? 500 : 400,
          transition: 'background .12s ease, color .12s ease',
        }}
        onMouseEnter={e => { if (!active) e.currentTarget.style.background = 'rgba(34,38,58,.5)'; }}
        onMouseLeave={e => { if (!active) e.currentTarget.style.background = 'transparent'; }}
      >
        <span style={{ display: 'inline-flex', width: 16, color: active ? 'var(--accent)' : 'currentColor' }}>{item.icon}</span>
        <span>{item.label}</span>
      </a>
    );
  };

  return (
    <aside style={{
      width: 220,
      flexShrink: 0,
      background: 'var(--surface)',
      borderRight: '1px solid var(--border)',
      height: '100vh',
      display: 'flex',
      flexDirection: 'column',
      position: 'sticky',
      top: 0,
    }}>
      <div style={{ padding: '18px 16px 14px' }}>
        <a href="/" onClick={(e) => { e.preventDefault(); navigate('/'); onClose && onClose(); }}>
          <Wordmark />
        </a>
      </div>
      <nav style={{ flex: 1, paddingTop: 4, overflowY: 'auto' }}>
        {NAV.map((entry, idx) => entry.section ? (
          <div key={idx} style={{ marginTop: 18 }}>
            <div style={{
              fontSize: 10.5,
              textTransform: 'uppercase',
              letterSpacing: '.08em',
              color: 'var(--text-muted)',
              padding: '0 18px 6px',
              fontWeight: 500,
            }}>{entry.section}</div>
            {entry.items.map(item => <NavItem key={item.route} item={item} />)}
          </div>
        ) : (
          <NavItem key={entry.route} item={entry} />
        ))}
      </nav>
      <div style={{ borderTop: '1px solid var(--border)', padding: '12px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
        <a
          href="#"
          onClick={(e) => { e.preventDefault(); navigate('/login'); onClose && onClose(); }}
          style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: 'var(--text-muted)', fontSize: 12.5 }}
        >
          <span style={{ display: 'inline-flex', width: 14 }}>{I.logout}</span> Logout
        </a>
        <span className="mono" style={{ fontSize: 10.5, color: 'var(--text-muted)', padding: '2px 6px', background: 'var(--surface-2)', borderRadius: 4 }}>v0.4.2</span>
      </div>
    </aside>
  );
}

// ---------- Shell ----------
function Shell({ route, navigate, crumbs, children }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const isMobile = useIsMobile();

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg)' }}>
      {!isMobile && <Sidebar route={route} navigate={navigate} />}
      {isMobile && mobileOpen && (
        <>
          <div className="overlay" onClick={() => setMobileOpen(false)} />
          <div style={{ position: 'fixed', top: 0, left: 0, height: '100vh', zIndex: 52 }}>
            <Sidebar route={route} navigate={navigate} onClose={() => setMobileOpen(false)} />
          </div>
        </>
      )}
      <main style={{ flex: 1, minWidth: 0 }}>
        {isMobile && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 10,
            padding: '12px 16px',
            borderBottom: '1px solid var(--border)',
            background: 'var(--surface)',
            position: 'sticky', top: 0, zIndex: 10,
          }}>
            <button className="btn btn-ghost btn-sm" onClick={() => setMobileOpen(true)} style={{ padding: '0 8px' }}>
              {I.menu}
            </button>
            <Wordmark size={18} />
          </div>
        )}
        <div style={{ maxWidth: 1100, margin: '0 auto', padding: isMobile ? '20px 16px' : '32px' }}>
          {crumbs && <Breadcrumbs crumbs={crumbs} navigate={navigate} />}
          {children}
        </div>
      </main>
    </div>
  );
}

function useIsMobile() {
  const [m, setM] = useState(() => typeof window !== 'undefined' && window.innerWidth <= 600);
  useEffect(() => {
    const onResize = () => setM(window.innerWidth <= 600);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);
  return m;
}

function Breadcrumbs({ crumbs, navigate }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12.5, color: 'var(--text-muted)', marginBottom: 14 }}>
      {crumbs.map((c, i) => (
        <React.Fragment key={i}>
          {i > 0 && <span style={{ color: '#3a4058' }}>/</span>}
          {c.route ? (
            <a href={c.route} onClick={(e) => { e.preventDefault(); navigate(c.route); }}
               style={{ color: i === crumbs.length - 1 ? 'var(--text)' : 'var(--text-muted)' }}>
              {c.label}
            </a>
          ) : <span style={{ color: i === crumbs.length - 1 ? 'var(--text)' : 'var(--text-muted)' }}>{c.label}</span>}
        </React.Fragment>
      ))}
    </div>
  );
}

function PageHeader({ title, subtitle, action, extra }) {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16, marginBottom: 20 }}>
      <div style={{ minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
          <h1 style={{ fontSize: 22, fontWeight: 600, margin: 0, letterSpacing: '-.01em' }}>{title}</h1>
          {extra}
        </div>
        {subtitle && <div style={{ color: 'var(--text-muted)', fontSize: 13, marginTop: 4 }}>{subtitle}</div>}
      </div>
      {action && <div style={{ flexShrink: 0 }}>{action}</div>}
    </div>
  );
}

// ---------- Skeleton helper ----------
const Skeleton = ({ w = '100%', h = 14, style }) => (
  <span className="skel" style={{ width: w, height: h, ...style }} />
);

// ---------- Secret input (mask/reveal, copy) ----------
function SecretField({ value, masked = true, onReveal, onChange, readOnly, placeholder, onCopy, canCopy = true }) {
  const [show, setShow] = useState(false);
  const [copied, setCopied] = useState(false);
  const display = masked && !show ? '•'.repeat(Math.min(value?.length || 24, 28)) : (value || '');
  return (
    <div style={{ position: 'relative' }}>
      <input
        className="input mono"
        value={display}
        readOnly={readOnly || (masked && !show)}
        onChange={(e) => onChange && onChange(e.target.value)}
        placeholder={placeholder}
        style={{ paddingRight: canCopy ? 70 : 38, fontSize: 12.5 }}
      />
      <div style={{ position: 'absolute', right: 4, top: 3, display: 'flex', gap: 2 }}>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => setShow(s => !s)} title={show ? 'Hide' : 'Reveal'} style={{ padding: '0 8px', height: 28 }}>
          {show ? I.eyeOff : I.eye}
        </button>
        {canCopy && (
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => {
            navigator.clipboard?.writeText(value || '');
            setCopied(true);
            setTimeout(() => setCopied(false), 1200);
            onCopy && onCopy();
          }} title="Copy" style={{ padding: '0 8px', height: 28 }}>
            {copied ? I.check : I.copy}
          </button>
        )}
      </div>
    </div>
  );
}

// ---------- Confirm modal ----------
function ConfirmModal({ open, title, body, confirmLabel = 'Confirm', danger, onConfirm, onCancel, requireType }) {
  const [typed, setTyped] = useState('');
  useEffect(() => { if (!open) setTyped(''); }, [open]);
  if (!open) return null;
  const disabled = requireType && typed !== requireType;
  return (
    <>
      <div className="overlay" onClick={onCancel} />
      <div className="modal">
        <div className="modal-head">
          <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>{title}</h3>
        </div>
        <div className="modal-body" style={{ fontSize: 13.5, color: 'var(--text-muted)' }}>
          {body}
          {requireType && (
            <div style={{ marginTop: 14 }}>
              <label className="label">Type <code style={{ color: 'var(--text)' }}>{requireType}</code> to confirm</label>
              <input className="input" value={typed} onChange={(e) => setTyped(e.target.value)} autoFocus />
            </div>
          )}
        </div>
        <div className="modal-foot">
          <button className="btn" onClick={onCancel}>Cancel</button>
          <button
            className={`btn ${danger ? 'btn-danger' : 'btn-primary'}`}
            onClick={onConfirm}
            disabled={disabled}
            style={danger ? { background: 'var(--danger)', borderColor: 'var(--danger)', color: '#fff' } : undefined}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </>
  );
}

Object.assign(window, {
  I, Spinner, Wordmark,
  ToastProvider, useToast,
  Shell, Sidebar, Breadcrumbs, PageHeader,
  Skeleton, SecretField, ConfirmModal,
  useIsMobile,
});
