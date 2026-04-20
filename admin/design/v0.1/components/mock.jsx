// Mock data + tiny helpers shared across screens.

const MOCK = {
  stats: {
    prs_24h: 47,
    prs_7d: 312,
    p50_ms: 2840,
    p95_ms: 8120,
    failure_rate: 2.3,
  },
  provider: {
    kind: 'ollama', // ollama | vllm | openai | anthropic | claude_code
    model: 'qwen2.5-coder:14b',
    base_url: 'http://ollama:11434',
    api_key_masked: true,
  },
  recent_deliveries: [
    { id: 'dlv_8f3a2b9e1c', event: 'pull_request.opened', status: 'processed', repo: 'acme/api-gateway', received_at: Date.now() - 1000*60*2 },
    { id: 'dlv_7e2c4a1d9f', event: 'pull_request.synchronize', status: 'processed', repo: 'acme/api-gateway', received_at: Date.now() - 1000*60*11 },
    { id: 'dlv_6d1b3c9e8a', event: 'pull_request.opened', status: 'failed', repo: 'acme/web-client', received_at: Date.now() - 1000*60*24 },
    { id: 'dlv_5c0a2b8d7f', event: 'merge_request.open', status: 'processed', repo: 'acme/infra', received_at: Date.now() - 1000*60*41 },
    { id: 'dlv_4b9f1a7c6e', event: 'pull_request.synchronize', status: 'queued', repo: 'acme/api-gateway', received_at: Date.now() - 1000*60*58 },
  ],
  deliveries: Array.from({ length: 67 }, (_, i) => {
    const events = ['pull_request.opened', 'pull_request.synchronize', 'pull_request.reopened', 'merge_request.open', 'merge_request.update'];
    const statuses = ['processed', 'processed', 'processed', 'queued', 'failed'];
    const repos = ['acme/api-gateway', 'acme/web-client', 'acme/infra', 'acme/worker-queue', 'acme/docs'];
    const received = Date.now() - i * 1000 * 60 * (3 + (i % 7));
    const status = statuses[i % statuses.length];
    return {
      id: `dlv_${Math.random().toString(36).slice(2, 14)}`,
      event: events[i % events.length],
      status,
      repo: repos[i % repos.length],
      received_at: received,
      processed_at: status === 'queued' ? null : received + 1000 * (2 + (i % 15)),
    };
  }),
  jobs: Array.from({ length: 42 }, (_, i) => {
    const statuses = ['processed', 'running', 'processed', 'failed', 'processed', 'queued'];
    const repos = ['acme/api-gateway', 'acme/web-client', 'acme/infra', 'acme/worker-queue', 'acme/docs'];
    const created = Date.now() - i * 1000 * 60 * (4 + (i % 9));
    const status = statuses[i % statuses.length];
    return {
      id: `job_${Math.random().toString(36).slice(2, 14)}`,
      repo: repos[i % repos.length],
      pr: 1200 + i * 3,
      platform: i % 3 === 0 ? 'gitlab' : 'github',
      status,
      retry_count: status === 'failed' ? 1 + (i % 3) : (i % 4 === 0 ? 1 : 0),
      duration_ms: status === 'running' ? null : 1500 + (i * 137) % 12000,
      created_at: created,
      stages: status === 'processed'
        ? ['done','done','done','done']
        : status === 'running' ? ['done','done','running','pending']
        : status === 'failed' ? ['done','done','failed','pending']
        : ['pending','pending','pending','pending'],
      error: status === 'failed' ? `LLMTimeoutError: request to https://api.openai.com/v1/chat/completions exceeded 60s\n  at OpenAIClient.complete (providers/openai.py:142)\n  at AnalyzeStage.run (pipeline/analyze.py:78)\n  at Job.execute (pipeline/job.py:211)` : null,
    };
  }),
  repos: [
    { id: 1, platform: 'github', slug: 'acme/api-gateway', enabled: true,  provider: 'ollama',    model: 'qwen2.5-coder:14b' },
    { id: 2, platform: 'github', slug: 'acme/web-client',  enabled: true,  provider: 'ollama',    model: 'qwen2.5-coder:14b' },
    { id: 3, platform: 'github', slug: 'acme/worker-queue', enabled: false, provider: 'vllm',      model: 'Qwen2.5-Coder-32B' },
    { id: 4, platform: 'gitlab', slug: 'acme/infra',       enabled: true,  provider: 'anthropic', model: 'claude-sonnet-4' },
    { id: 5, platform: 'github', slug: 'acme/docs',        enabled: true,  provider: 'openai',    model: 'gpt-4o-mini' },
  ],
  webhook: {
    url: 'https://vellic.acme-corp.internal/webhooks',
    hmac: 'whsec_4p7x9q2mEzF3nKj5vL8bR1yTcU6wH0aS',
    github_app_id: '428371',
    github_installation_id: '52918374',
    gitlab_token_set: true,
  },
};

const PROVIDER_LABELS = {
  ollama: 'Ollama',
  vllm: 'vLLM',
  openai: 'OpenAI',
  anthropic: 'Anthropic',
  claude_code: 'Claude Code',
};
const CLOUD_PROVIDERS = ['openai', 'anthropic', 'claude_code'];
const isCloud = (p) => CLOUD_PROVIDERS.includes(p);

function fmtRelative(ts) {
  if (!ts) return '—';
  const diff = Date.now() - ts;
  const s = Math.floor(diff / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
}
function fmtAbsolute(ts) {
  if (!ts) return '—';
  return new Date(ts).toISOString().replace('T', ' ').slice(0, 19) + 'Z';
}
function fmtDuration(ms) {
  if (ms == null) return '—';
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms/1000).toFixed(1)}s`;
  return `${Math.floor(ms/60000)}m ${Math.round((ms%60000)/1000)}s`;
}
function trunc(s, n = 10) {
  if (!s) return '';
  return s.length > n + 2 ? s.slice(0, n) + '…' : s;
}

Object.assign(window, { MOCK, PROVIDER_LABELS, CLOUD_PROVIDERS, isCloud, fmtRelative, fmtAbsolute, fmtDuration, trunc });
