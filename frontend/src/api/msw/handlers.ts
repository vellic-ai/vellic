import { http, HttpResponse } from "msw";
import type { components } from "@/api/schema";

const pluginStore: Record<string, components["schemas"]["PluginItem"][]> = {
  "repo-001": [
    {
      id: "plug-001",
      name: "acme-lint",
      type: "git",
      source: "https://github.com/acme/vellic-lint-plugin",
      version: "1.2.0",
      version_pin: null,
      enabled: true,
      last_used_at: new Date(Date.now() - 3_600_000).toISOString(),
      installed_at: new Date(Date.now() - 86_400_000 * 7).toISOString(),
    },
    {
      id: "plug-002",
      name: "security-scanner",
      type: "zip",
      source: "security-scanner-v0.9.zip",
      version: "0.9.0",
      version_pin: "0.9.0",
      enabled: false,
      last_used_at: null,
      installed_at: new Date(Date.now() - 86_400_000 * 2).toISOString(),
    },
  ],
};

const mcpStore: Record<string, components["schemas"]["McpServerItem"][]> = {
  "repo-001": [
    {
      id: "mcp-001",
      name: "GitHub MCP",
      url: "https://mcp.github.com/sse",
      transport: "sse",
      credentials_set: true,
      enabled: true,
      last_used_at: new Date(Date.now() - 7_200_000).toISOString(),
      attached_at: new Date(Date.now() - 86_400_000 * 3).toISOString(),
    },
  ],
};

const authStatus: components["schemas"]["AuthStatus"] = {
  setup_required: false,
  authenticated: true,
};

const stats: components["schemas"]["StatsResponse"] = {
  prs_reviewed_24h: 12,
  prs_reviewed_7d: 84,
  latency_p50_ms: 3200,
  latency_p95_ms: 8900,
  failure_rate_pct: 1.5,
  llm_provider: "ollama",
  llm_model: "qwen2.5-coder:14b",
  recent_deliveries: [
    {
      delivery_id: "del-001",
      event_type: "pull_request",
      repo: "acme/frontend",
      received_at: new Date().toISOString(),
      status: "done",
    },
  ],
};

const deliveries: components["schemas"]["DeliveryItem"][] = [
  {
    delivery_id: "del-001",
    event_type: "pull_request",
    received_at: new Date().toISOString(),
    processed_at: new Date().toISOString(),
    status: "done",
    job_id: "job-001",
  },
  {
    delivery_id: "del-002",
    event_type: "pull_request",
    received_at: new Date().toISOString(),
    processed_at: null,
    status: "pending",
    job_id: null,
  },
];

const jobs: components["schemas"]["JobItem"][] = [
  {
    id: "job-001",
    delivery_id: "del-001",
    status: "done",
    retry_count: 0,
    created_at: new Date().toISOString(),
    duration_ms: 4200,
    repo: "acme/frontend",
    pr_number: "42",
    platform: "github",
    error: null,
  },
  {
    id: "job-002",
    delivery_id: "del-002",
    status: "failed",
    retry_count: 1,
    created_at: new Date().toISOString(),
    duration_ms: 1000,
    repo: "acme/backend",
    pr_number: "7",
    platform: "github",
    error: "LLM timeout",
  },
];

const llmSettings: components["schemas"]["LLMSettingsOut"] = {
  provider: "ollama",
  base_url: "http://localhost:11434",
  model: "qwen2.5-coder:14b",
  api_key: null,
  extra: {},
  updated_at: new Date().toISOString(),
};

const webhookSettings: components["schemas"]["WebhookSettingsOut"] = {
  url: "https://example.com/webhook",
  hmac: "whsec_example",
  github_app_id: "123456",
  github_installation_id: "789",
  github_key_set: true,
  gitlab_token_set: false,
};

const repos: components["schemas"]["RepoItem"][] = [
  {
    id: "repo-001",
    platform: "github",
    org: "acme",
    repo: "frontend",
    slug: "acme/frontend",
    enabled: true,
    provider: "ollama",
    model: "qwen2.5-coder:14b",
    created_at: new Date().toISOString(),
  },
];

export const apiHandlers = [
  http.get("/health", () =>
    HttpResponse.json({ status: "ok", service: "admin" }),
  ),

  http.get("/admin/auth/status", () => HttpResponse.json(authStatus)),

  http.put("/admin/auth/setup", () => new HttpResponse(null, { status: 204 })),

  http.post("/admin/auth/login", async ({ request }) => {
    const body = (await request.json()) as { password: string };
    if (body.password === "wrong") {
      return HttpResponse.json({ detail: "Unauthorized" }, { status: 401 });
    }
    return HttpResponse.json({ authenticated: true });
  }),

  http.post("/admin/auth/logout", () => new HttpResponse(null, { status: 204 })),

  http.post("/admin/auth/change-password", () =>
    new HttpResponse(null, { status: 204 }),
  ),

  http.get("/admin/stats", () => HttpResponse.json(stats)),

  http.get("/admin/deliveries", ({ request }) => {
    const url = new URL(request.url);
    const status = url.searchParams.get("status") ?? "";
    const filtered = status
      ? deliveries.filter((d) => d.status === status)
      : deliveries;
    return HttpResponse.json({
      items: filtered,
      total: filtered.length,
      limit: 50,
      offset: 0,
    });
  }),

  http.post("/admin/replay/:delivery_id", ({ params }) =>
    HttpResponse.json(
      {
        status: "queued",
        delivery_id: params.delivery_id,
        event_type: "pull_request",
      },
      { status: 202 },
    ),
  ),

  http.get("/admin/jobs", ({ request }) => {
    const url = new URL(request.url);
    const status = url.searchParams.get("status") ?? "";
    const filtered = status ? jobs.filter((j) => j.status === status) : jobs;
    return HttpResponse.json({
      items: filtered,
      total: filtered.length,
      limit: 50,
      offset: 0,
    });
  }),

  http.get("/admin/settings/llm", () => HttpResponse.json(llmSettings)),

  http.put("/admin/settings/llm", async ({ request }) => {
    const body = (await request.json()) as components["schemas"]["LLMSettingsIn"];
    return HttpResponse.json({ ...llmSettings, ...body, api_key: body.api_key ? "***" : null });
  }),

  http.get("/admin/settings/webhook", () => HttpResponse.json(webhookSettings)),

  http.put("/admin/settings/webhook", async ({ request }) => {
    const body = (await request.json()) as { url: string };
    return HttpResponse.json({ ...webhookSettings, url: body.url });
  }),

  http.post("/admin/settings/webhook/rotate", () =>
    HttpResponse.json({ hmac: "whsec_newrotatedsecret" }),
  ),

  http.put("/admin/settings/github", async ({ request }) => {
    const body = (await request.json()) as components["schemas"]["GitHubAppIn"];
    return HttpResponse.json({
      ...webhookSettings,
      github_app_id: body.app_id,
      github_installation_id: body.installation_id,
      github_key_set: Boolean(body.private_key),
    });
  }),

  http.post("/admin/settings/github/test", () =>
    HttpResponse.json({ ok: true }),
  ),

  http.put("/admin/settings/gitlab", () =>
    HttpResponse.json({ ...webhookSettings, gitlab_token_set: true }),
  ),

  http.post("/admin/settings/gitlab/test", () =>
    HttpResponse.json({ ok: true }),
  ),

  http.get("/admin/settings/repos", () => HttpResponse.json({ items: repos })),

  http.post("/admin/settings/repos", async ({ request }) => {
    const body = (await request.json()) as components["schemas"]["RepoBody"];
    const newRepo: components["schemas"]["RepoItem"] = {
      id: `repo-${Date.now()}`,
      platform: body.platform,
      org: body.org ?? "",
      repo: body.repo ?? "*",
      slug: `${body.org ?? ""}/${body.repo ?? "*"}`,
      enabled: body.enabled,
      provider: body.provider,
      model: body.model,
      created_at: new Date().toISOString(),
    };
    return HttpResponse.json(newRepo, { status: 201 });
  }),

  http.patch("/admin/settings/repos/:repo_id", async ({ params, request }) => {
    const body = (await request.json()) as components["schemas"]["RepoBody"];
    const existing = repos.find((r) => r.id === params.repo_id);
    if (!existing) return HttpResponse.json({ detail: "Not found" }, { status: 404 });
    return HttpResponse.json({ ...existing, ...body });
  }),

  http.post("/admin/settings/repos/:repo_id/toggle", ({ params }) => {
    const existing = repos.find((r) => r.id === params.repo_id);
    if (!existing) return HttpResponse.json({ detail: "Not found" }, { status: 404 });
    return HttpResponse.json({ ...existing, enabled: !existing.enabled });
  }),

  http.delete("/admin/settings/repos/:repo_id", ({ params }) => {
    const existing = repos.find((r) => r.id === params.repo_id);
    if (!existing) return HttpResponse.json({ detail: "Not found" }, { status: 404 });
    return new HttpResponse(null, { status: 204 });
  }),

  // --- Plugins ---
  http.get("/admin/settings/repos/:repo_id/plugins", ({ params }) => {
    const items = pluginStore[params.repo_id as string] ?? [];
    return HttpResponse.json({ items });
  }),

  http.post("/admin/settings/repos/:repo_id/plugins", async ({ params, request }) => {
    const fd = await request.formData();
    const type = fd.get("type") as "zip" | "git";
    const file = fd.get("file") as File | null;
    const url = fd.get("url") as string | null;
    const newPlugin: components["schemas"]["PluginItem"] = {
      id: `plug-${Date.now()}`,
      name: type === "zip" ? (file?.name.replace(/\.zip$/, "") ?? "plugin") : (url?.split("/").pop() ?? "plugin"),
      type,
      source: type === "zip" ? (file?.name ?? "") : (url ?? ""),
      version: null,
      version_pin: null,
      enabled: true,
      last_used_at: null,
      installed_at: new Date().toISOString(),
    };
    const repoId = params.repo_id as string;
    pluginStore[repoId] = [...(pluginStore[repoId] ?? []), newPlugin];
    return HttpResponse.json(newPlugin, { status: 201 });
  }),

  http.patch("/admin/settings/repos/:repo_id/plugins/:plugin_id", async ({ params, request }) => {
    const repoId = params.repo_id as string;
    const pluginId = params.plugin_id as string;
    const body = (await request.json()) as components["schemas"]["PluginPatchBody"];
    const list = pluginStore[repoId] ?? [];
    const idx = list.findIndex((p) => p.id === pluginId);
    if (idx === -1) return HttpResponse.json({ detail: "Not found" }, { status: 404 });
    list[idx] = { ...list[idx], ...body };
    return HttpResponse.json(list[idx]);
  }),

  http.delete("/admin/settings/repos/:repo_id/plugins/:plugin_id", ({ params }) => {
    const repoId = params.repo_id as string;
    const pluginId = params.plugin_id as string;
    pluginStore[repoId] = (pluginStore[repoId] ?? []).filter((p) => p.id !== pluginId);
    return new HttpResponse(null, { status: 204 });
  }),

  // --- MCP Servers ---
  http.get("/admin/settings/repos/:repo_id/mcp-servers", ({ params }) => {
    const items = mcpStore[params.repo_id as string] ?? [];
    return HttpResponse.json({ items });
  }),

  http.post("/admin/settings/repos/:repo_id/mcp-servers", async ({ params, request }) => {
    const body = (await request.json()) as components["schemas"]["McpServerBody"];
    const newServer: components["schemas"]["McpServerItem"] = {
      id: `mcp-${Date.now()}`,
      name: body.name,
      url: body.url,
      transport: body.transport,
      credentials_set: Boolean(body.credentials && Object.keys(body.credentials).length > 0),
      enabled: true,
      last_used_at: null,
      attached_at: new Date().toISOString(),
    };
    const repoId = params.repo_id as string;
    mcpStore[repoId] = [...(mcpStore[repoId] ?? []), newServer];
    return HttpResponse.json(newServer, { status: 201 });
  }),

  http.patch("/admin/settings/repos/:repo_id/mcp-servers/:server_id", async ({ params, request }) => {
    const repoId = params.repo_id as string;
    const serverId = params.server_id as string;
    const body = (await request.json()) as components["schemas"]["McpServerPatchBody"];
    const list = mcpStore[repoId] ?? [];
    const idx = list.findIndex((s) => s.id === serverId);
    if (idx === -1) return HttpResponse.json({ detail: "Not found" }, { status: 404 });
    list[idx] = { ...list[idx], ...body };
    return HttpResponse.json(list[idx]);
  }),

  http.delete("/admin/settings/repos/:repo_id/mcp-servers/:server_id", ({ params }) => {
    const repoId = params.repo_id as string;
    const serverId = params.server_id as string;
    mcpStore[repoId] = (mcpStore[repoId] ?? []).filter((s) => s.id !== serverId);
    return new HttpResponse(null, { status: 204 });
  }),
];
