/**
 * Hand-maintained until `npm run gen:api` is executed against a running admin server.
 * Run: npm run gen:api
 * Source: http://localhost:8001/openapi.json
 *
 * Types mirror admin/app/{auth,stats,repos,settings}_router.py Pydantic models exactly.
 */

export interface paths {
  "/health": {
    get: {
      responses: {
        200: { content: { "application/json": components["schemas"]["HealthResponse"] } };
      };
    };
  };

  "/admin/auth/status": {
    get: {
      responses: {
        200: { content: { "application/json": components["schemas"]["AuthStatus"] } };
      };
    };
  };

  "/admin/auth/setup": {
    put: {
      requestBody: { content: { "application/json": components["schemas"]["SetupBody"] } };
      responses: {
        204: { content?: never };
        409: { content: { "application/json": components["schemas"]["ErrorDetail"] } };
      };
    };
  };

  "/admin/auth/login": {
    post: {
      requestBody: { content: { "application/json": components["schemas"]["LoginBody"] } };
      responses: {
        200: { content: { "application/json": components["schemas"]["LoginResponse"] } };
        401: { content: { "application/json": components["schemas"]["ErrorDetail"] } };
      };
    };
  };

  "/admin/auth/logout": {
    post: {
      responses: {
        204: { content?: never };
      };
    };
  };

  "/admin/auth/change-password": {
    post: {
      requestBody: {
        content: { "application/json": components["schemas"]["ChangePasswordBody"] };
      };
      responses: {
        204: { content?: never };
        401: { content: { "application/json": components["schemas"]["ErrorDetail"] } };
      };
    };
  };

  "/admin/stats": {
    get: {
      responses: {
        200: { content: { "application/json": components["schemas"]["StatsResponse"] } };
      };
    };
  };

  "/admin/deliveries": {
    get: {
      parameters: {
        query?: {
          limit?: number;
          offset?: number;
          status?: string;
          event_type?: string;
        };
      };
      responses: {
        200: { content: { "application/json": components["schemas"]["DeliveryList"] } };
      };
    };
  };

  "/admin/replay/{delivery_id}": {
    post: {
      parameters: {
        path: { delivery_id: string };
      };
      responses: {
        202: { content: { "application/json": components["schemas"]["ReplayResponse"] } };
        404: { content: { "application/json": components["schemas"]["ErrorDetail"] } };
      };
    };
  };

  "/admin/jobs": {
    get: {
      parameters: {
        query?: {
          limit?: number;
          offset?: number;
          status?: string;
        };
      };
      responses: {
        200: { content: { "application/json": components["schemas"]["JobList"] } };
      };
    };
  };

  "/admin/settings/llm": {
    get: {
      responses: {
        200: { content: { "application/json": components["schemas"]["LLMSettingsOut"] } };
        404: { content: { "application/json": components["schemas"]["ErrorDetail"] } };
      };
    };
    put: {
      requestBody: { content: { "application/json": components["schemas"]["LLMSettingsIn"] } };
      responses: {
        200: { content: { "application/json": components["schemas"]["LLMSettingsOut"] } };
        422: { content: { "application/json": components["schemas"]["ErrorDetail"] } };
      };
    };
  };

  "/admin/settings/webhook": {
    get: {
      responses: {
        200: { content: { "application/json": components["schemas"]["WebhookSettingsOut"] } };
        404: { content: { "application/json": components["schemas"]["ErrorDetail"] } };
      };
    };
    put: {
      requestBody: {
        content: { "application/json": components["schemas"]["WebhookEndpointIn"] };
      };
      responses: {
        200: { content: { "application/json": components["schemas"]["WebhookSettingsOut"] } };
      };
    };
  };

  "/admin/settings/webhook/rotate": {
    post: {
      responses: {
        200: { content: { "application/json": components["schemas"]["RotateHmacResponse"] } };
      };
    };
  };

  "/admin/settings/github": {
    put: {
      requestBody: { content: { "application/json": components["schemas"]["GitHubAppIn"] } };
      responses: {
        200: { content: { "application/json": components["schemas"]["WebhookSettingsOut"] } };
      };
    };
  };

  "/admin/settings/github/test": {
    post: {
      responses: {
        200: { content: { "application/json": components["schemas"]["TestConnectionResponse"] } };
        422: { content: { "application/json": components["schemas"]["ErrorDetail"] } };
        502: { content: { "application/json": components["schemas"]["ErrorDetail"] } };
      };
    };
  };

  "/admin/settings/gitlab": {
    put: {
      requestBody: { content: { "application/json": components["schemas"]["GitLabIn"] } };
      responses: {
        200: { content: { "application/json": components["schemas"]["WebhookSettingsOut"] } };
        422: { content: { "application/json": components["schemas"]["ErrorDetail"] } };
      };
    };
  };

  "/admin/settings/gitlab/test": {
    post: {
      responses: {
        200: { content: { "application/json": components["schemas"]["TestConnectionResponse"] } };
        422: { content: { "application/json": components["schemas"]["ErrorDetail"] } };
        502: { content: { "application/json": components["schemas"]["ErrorDetail"] } };
      };
    };
  };

  "/admin/features": {
    get: {
      responses: {
        200: { content: { "application/json": components["schemas"]["FeaturesResponse"] } };
      };
    };
  };

  "/admin/settings/repos": {
    get: {
      responses: {
        200: { content: { "application/json": components["schemas"]["RepoList"] } };
      };
    };
    post: {
      requestBody: { content: { "application/json": components["schemas"]["RepoBody"] } };
      responses: {
        201: { content: { "application/json": components["schemas"]["RepoItem"] } };
        409: { content: { "application/json": components["schemas"]["ErrorDetail"] } };
        422: { content: { "application/json": components["schemas"]["ErrorDetail"] } };
      };
    };
  };

  "/admin/settings/repos/{repo_id}": {
    patch: {
      parameters: {
        path: { repo_id: string };
      };
      requestBody: { content: { "application/json": components["schemas"]["RepoBody"] } };
      responses: {
        200: { content: { "application/json": components["schemas"]["RepoItem"] } };
        404: { content: { "application/json": components["schemas"]["ErrorDetail"] } };
        422: { content: { "application/json": components["schemas"]["ErrorDetail"] } };
      };
    };
    delete: {
      parameters: {
        path: { repo_id: string };
      };
      responses: {
        204: { content?: never };
        404: { content: { "application/json": components["schemas"]["ErrorDetail"] } };
      };
    };
  };

  "/admin/settings/repos/{repo_id}/toggle": {
    post: {
      parameters: {
        path: { repo_id: string };
      };
      responses: {
        200: { content: { "application/json": components["schemas"]["RepoItem"] } };
        404: { content: { "application/json": components["schemas"]["ErrorDetail"] } };
      };
    };
  };

  "/admin/settings/repos/{repo_id}/plugins": {
    get: {
      parameters: { path: { repo_id: string } };
      responses: {
        200: { content: { "application/json": components["schemas"]["PluginList"] } };
        404: { content: { "application/json": components["schemas"]["ErrorDetail"] } };
      };
    };
  };

  "/admin/settings/repos/{repo_id}/plugins/{plugin_id}": {
    patch: {
      parameters: { path: { repo_id: string; plugin_id: string } };
      requestBody: { content: { "application/json": components["schemas"]["PluginPatchBody"] } };
      responses: {
        200: { content: { "application/json": components["schemas"]["PluginItem"] } };
        404: { content: { "application/json": components["schemas"]["ErrorDetail"] } };
      };
    };
    delete: {
      parameters: { path: { repo_id: string; plugin_id: string } };
      responses: {
        204: { content?: never };
        404: { content: { "application/json": components["schemas"]["ErrorDetail"] } };
      };
    };
  };

  "/admin/settings/repos/{repo_id}/mcp-servers": {
    get: {
      parameters: { path: { repo_id: string } };
      responses: {
        200: { content: { "application/json": components["schemas"]["McpServerList"] } };
        404: { content: { "application/json": components["schemas"]["ErrorDetail"] } };
      };
    };
    post: {
      parameters: { path: { repo_id: string } };
      requestBody: { content: { "application/json": components["schemas"]["McpServerBody"] } };
      responses: {
        201: { content: { "application/json": components["schemas"]["McpServerItem"] } };
        404: { content: { "application/json": components["schemas"]["ErrorDetail"] } };
        422: { content: { "application/json": components["schemas"]["ErrorDetail"] } };
      };
    };
  };

  "/admin/settings/repos/{repo_id}/mcp-servers/{server_id}": {
    patch: {
      parameters: { path: { repo_id: string; server_id: string } };
      requestBody: { content: { "application/json": components["schemas"]["McpServerPatchBody"] } };
      responses: {
        200: { content: { "application/json": components["schemas"]["McpServerItem"] } };
        404: { content: { "application/json": components["schemas"]["ErrorDetail"] } };
      };
    };
    delete: {
      parameters: { path: { repo_id: string; server_id: string } };
      responses: {
        204: { content?: never };
        404: { content: { "application/json": components["schemas"]["ErrorDetail"] } };
      };
    };
  };

  "/admin/prompts": {
    get: {
      responses: {
        200: { content: { "application/json": components["schemas"]["PromptList"] } };
        404: { content: { "application/json": components["schemas"]["ErrorDetail"] } };
      };
    };
    post: {
      requestBody: { content: { "application/json": components["schemas"]["PromptCreate"] } };
      responses: {
        200: { content: { "application/json": components["schemas"]["PromptOut"] } };
        404: { content: { "application/json": components["schemas"]["ErrorDetail"] } };
        409: { content: { "application/json": components["schemas"]["ErrorDetail"] } };
        422: { content: { "application/json": components["schemas"]["ErrorDetail"] } };
      };
    };
  };

  "/admin/prompts/{name}": {
    get: {
      parameters: { path: { name: string } };
      responses: {
        200: { content: { "application/json": components["schemas"]["PromptOut"] } };
        404: { content: { "application/json": components["schemas"]["ErrorDetail"] } };
      };
    };
    put: {
      parameters: { path: { name: string } };
      requestBody: { content: { "application/json": components["schemas"]["PromptBody"] } };
      responses: {
        200: { content: { "application/json": components["schemas"]["PromptOut"] } };
        404: { content: { "application/json": components["schemas"]["ErrorDetail"] } };
        422: { content: { "application/json": components["schemas"]["ErrorDetail"] } };
      };
    };
    delete: {
      parameters: { path: { name: string } };
      responses: {
        200: { content: { "application/json": components["schemas"]["PromptDeleteOut"] } };
        404: { content: { "application/json": components["schemas"]["ErrorDetail"] } };
      };
    };
  };

  "/admin/prompts/{name}/enabled": {
    patch: {
      parameters: { path: { name: string } };
      requestBody: { content: { "application/json": components["schemas"]["PromptEnableBody"] } };
      responses: {
        200: { content: { "application/json": components["schemas"]["PromptOut"] } };
        404: { content: { "application/json": components["schemas"]["ErrorDetail"] } };
      };
    };
  };

  "/admin/features/{flag_key}": {
    put: {
      parameters: { path: { flag_key: string } };
      requestBody: { content: { "application/json": components["schemas"]["FeatureFlagOverride"] } };
      responses: {
        200: { content: { "application/json": components["schemas"]["FeatureFlagToggleOut"] } };
        404: { content: { "application/json": components["schemas"]["ErrorDetail"] } };
      };
    };
  };
}

export interface components {
  schemas: {
    HealthResponse: {
      status: string;
      service: string;
    };

    ErrorDetail: {
      detail: string;
    };

    AuthStatus: {
      setup_required: boolean;
      authenticated: boolean;
    };

    SetupBody: {
      password: string;
    };

    LoginBody: {
      password: string;
    };

    LoginResponse: {
      authenticated: boolean;
    };

    ChangePasswordBody: {
      current_password: string;
      new_password: string;
    };

    RecentDelivery: {
      delivery_id: string;
      event_type: string;
      repo: string | null;
      received_at: string | null;
      status: string;
    };

    StatsResponse: {
      prs_reviewed_24h: number;
      prs_reviewed_7d: number;
      latency_p50_ms: number;
      latency_p95_ms: number;
      failure_rate_pct: number;
      llm_provider: string | null;
      llm_model: string | null;
      recent_deliveries: components["schemas"]["RecentDelivery"][];
    };

    DeliveryItem: {
      delivery_id: string;
      event_type: string;
      received_at: string | null;
      processed_at: string | null;
      status: string;
      job_id: string | null;
    };

    DeliveryList: {
      items: components["schemas"]["DeliveryItem"][];
      total: number;
      limit: number;
      offset: number;
    };

    ReplayResponse: {
      status: string;
      delivery_id: string;
      event_type: string;
    };

    JobItem: {
      id: string;
      delivery_id: string;
      status: string;
      retry_count: number;
      created_at: string | null;
      duration_ms: number | null;
      repo: string | null;
      pr_number: string | null;
      platform: string;
      error: string | null;
    };

    JobList: {
      items: components["schemas"]["JobItem"][];
      total: number;
      limit: number;
      offset: number;
    };

    LLMSettingsIn: {
      provider: string;
      base_url: string | null;
      model: string;
      api_key: string | null;
      extra: Record<string, unknown>;
    };

    LLMSettingsOut: {
      provider: string;
      base_url: string | null;
      model: string;
      api_key: string | null;
      extra: Record<string, unknown>;
      updated_at: string | null;
    };

    FeaturesResponse: {
      flags: Record<string, boolean>;
      catalog: Array<{
        key: string;
        name: string;
        category: string;
        description: string;
        enabled: boolean;
        default: boolean;
        scope: string;
        tags: string[];
        has_consumers: boolean;
      }>;
      snapshot_at: string;
    };

    WebhookSettingsOut: {
      url: string;
      hmac: string;
      github_app_id: string;
      github_installation_id: string;
      github_key_set: boolean;
      gitlab_token_set: boolean;
    };

    WebhookEndpointIn: {
      url: string;
    };

    GitHubAppIn: {
      app_id: string;
      installation_id: string;
      private_key: string | null;
    };

    GitLabIn: {
      token: string | null;
    };

    RotateHmacResponse: {
      hmac: string;
    };

    TestConnectionResponse: {
      ok: boolean;
    };

    RepoBody: {
      platform: string;
      org: string | null;
      repo: string | null;
      slug: string | null;
      provider: string;
      model: string;
      enabled: boolean;
    };

    RepoItem: {
      id: string;
      platform: string;
      org: string;
      repo: string;
      slug: string;
      enabled: boolean;
      provider: string;
      model: string;
      created_at: string | null;
    };

    RepoList: {
      items: components["schemas"]["RepoItem"][];
    };

    PluginItem: {
      id: string;
      name: string;
      type: "zip" | "git";
      source: string;
      version: string | null;
      version_pin: string | null;
      enabled: boolean;
      last_used_at: string | null;
      installed_at: string;
    };

    PluginList: {
      items: components["schemas"]["PluginItem"][];
    };

    PluginPatchBody: {
      enabled?: boolean;
      version_pin?: string | null;
    };

    McpServerItem: {
      id: string;
      name: string;
      url: string;
      transport: "sse" | "stdio" | "streamable_http";
      credentials_set: boolean;
      enabled: boolean;
      last_used_at: string | null;
      attached_at: string;
    };

    McpServerList: {
      items: components["schemas"]["McpServerItem"][];
    };

    McpServerBody: {
      name: string;
      url: string;
      transport: "sse" | "stdio" | "streamable_http";
      credentials: Record<string, string> | null;
    };

    McpServerPatchBody: {
      enabled?: boolean;
    };

    PromptFrontmatter: {
      scope: string[];
      triggers: string[];
      priority: number;
      inherits: string | null;
      variables: Record<string, string>;
    };

    PromptOut: {
      name: string;
      source: "preset" | "db" | "preset+db";
      frontmatter: components["schemas"]["PromptFrontmatter"];
      body: string;
      db_override: string | null;
      enabled: boolean;
    };

    PromptList: {
      items: components["schemas"]["PromptOut"][];
    };

    PromptBody: {
      body: string;
    };

    PromptCreate: {
      name: string;
      body: string;
    };

    PromptEnableBody: {
      enabled: boolean;
    };

    PromptDeleteOut: {
      deleted: boolean;
    };

    PromptImportResult: {
      imported: string[];
      errors: string[];
    };

    FeatureFlagOverride: {
      enabled: boolean;
    };

    FeatureFlagToggleOut: {
      key: string;
      enabled: boolean;
    };
  };
  responses: never;
  parameters: never;
  requestBodies: never;
  headers: never;
  pathItems: never;
}

export type $defs = Record<string, never>;
export type webhooks = Record<string, never>;

export type AuthStatus = components["schemas"]["AuthStatus"];
export type StatsResponse = components["schemas"]["StatsResponse"];
export type DeliveryItem = components["schemas"]["DeliveryItem"];
export type DeliveryList = components["schemas"]["DeliveryList"];
export type JobItem = components["schemas"]["JobItem"];
export type JobList = components["schemas"]["JobList"];
export type LLMSettingsIn = components["schemas"]["LLMSettingsIn"];
export type LLMSettingsOut = components["schemas"]["LLMSettingsOut"];
export type WebhookSettingsOut = components["schemas"]["WebhookSettingsOut"];
export type RepoItem = components["schemas"]["RepoItem"];
export type RepoBody = components["schemas"]["RepoBody"];
export type PluginItem = components["schemas"]["PluginItem"];
export type PluginPatchBody = components["schemas"]["PluginPatchBody"];
export type McpServerItem = components["schemas"]["McpServerItem"];
export type McpServerBody = components["schemas"]["McpServerBody"];
export type McpServerPatchBody = components["schemas"]["McpServerPatchBody"];
export type FeatureFlagOverride = components["schemas"]["FeatureFlagOverride"];
export type FeatureFlagToggleOut = components["schemas"]["FeatureFlagToggleOut"];
export type PromptOut = components["schemas"]["PromptOut"];
export type PromptList = components["schemas"]["PromptList"];
export type PromptBody = components["schemas"]["PromptBody"];
export type PromptCreate = components["schemas"]["PromptCreate"];
export type PromptEnableBody = components["schemas"]["PromptEnableBody"];
export type PromptDeleteOut = components["schemas"]["PromptDeleteOut"];
export type PromptImportResult = components["schemas"]["PromptImportResult"];
