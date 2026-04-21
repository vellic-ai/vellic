import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { components } from "@/api/schema";

export const pluginKeys = {
  all: (repoId: string) => ["repos", repoId, "plugins"] as const,
  list: (repoId: string) => ["repos", repoId, "plugins", "list"] as const,
};

export const mcpKeys = {
  all: (repoId: string) => ["repos", repoId, "mcp-servers"] as const,
  list: (repoId: string) => ["repos", repoId, "mcp-servers", "list"] as const,
};

// --- Plugins ---

export function useRepoPlugins(repoId: string) {
  return useQuery({
    queryKey: pluginKeys.list(repoId),
    queryFn: async () => {
      const { data, error } = await api.GET(
        "/admin/settings/repos/{repo_id}/plugins",
        { params: { path: { repo_id: repoId } } },
      );
      if (error) throw error;
      return data;
    },
    enabled: Boolean(repoId),
    staleTime: 15_000,
  });
}

export function useInstallPlugin(repoId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (form: { type: "zip"; file: File } | { type: "git"; url: string }) => {
      const baseUrl =
        typeof window !== "undefined" && window.location.origin !== "null"
          ? window.location.origin
          : "http://localhost:5173";
      const fd = new FormData();
      fd.append("type", form.type);
      if (form.type === "zip") {
        fd.append("file", form.file);
      } else {
        fd.append("url", form.url);
      }
      const res = await fetch(
        `${baseUrl}/admin/settings/repos/${repoId}/plugins`,
        { method: "POST", body: fd, credentials: "include" },
      );
      if (!res.ok) {
        const json = await res.json().catch(() => ({}));
        throw new Error((json as Record<string, string>).detail ?? `HTTP ${res.status}`);
      }
      return res.json() as Promise<components["schemas"]["PluginItem"]>;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: pluginKeys.all(repoId) }),
  });
}

export function usePatchPlugin(repoId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      pluginId,
      body,
    }: {
      pluginId: string;
      body: components["schemas"]["PluginPatchBody"];
    }) => {
      const { data, error } = await api.PATCH(
        "/admin/settings/repos/{repo_id}/plugins/{plugin_id}",
        { params: { path: { repo_id: repoId, plugin_id: pluginId } }, body },
      );
      if (error) throw error;
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: pluginKeys.all(repoId) }),
  });
}

export function useRemovePlugin(repoId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (pluginId: string) => {
      const { error } = await api.DELETE(
        "/admin/settings/repos/{repo_id}/plugins/{plugin_id}",
        { params: { path: { repo_id: repoId, plugin_id: pluginId } } },
      );
      if (error) throw error;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: pluginKeys.all(repoId) }),
  });
}

// --- MCP Servers ---

export function useRepoMcpServers(repoId: string) {
  return useQuery({
    queryKey: mcpKeys.list(repoId),
    queryFn: async () => {
      const { data, error } = await api.GET(
        "/admin/settings/repos/{repo_id}/mcp-servers",
        { params: { path: { repo_id: repoId } } },
      );
      if (error) throw error;
      return data;
    },
    enabled: Boolean(repoId),
    staleTime: 15_000,
  });
}

export function useAttachMcpServer(repoId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: components["schemas"]["McpServerBody"]) => {
      const { data, error } = await api.POST(
        "/admin/settings/repos/{repo_id}/mcp-servers",
        { params: { path: { repo_id: repoId } }, body },
      );
      if (error) throw error;
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: mcpKeys.all(repoId) }),
  });
}

export function usePatchMcpServer(repoId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      serverId,
      body,
    }: {
      serverId: string;
      body: components["schemas"]["McpServerPatchBody"];
    }) => {
      const { data, error } = await api.PATCH(
        "/admin/settings/repos/{repo_id}/mcp-servers/{server_id}",
        { params: { path: { repo_id: repoId, server_id: serverId } }, body },
      );
      if (error) throw error;
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: mcpKeys.all(repoId) }),
  });
}

export function useDetachMcpServer(repoId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (serverId: string) => {
      const { error } = await api.DELETE(
        "/admin/settings/repos/{repo_id}/mcp-servers/{server_id}",
        { params: { path: { repo_id: repoId, server_id: serverId } } },
      );
      if (error) throw error;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: mcpKeys.all(repoId) }),
  });
}
