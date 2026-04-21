import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { components } from "@/api/schema";

export const settingsKeys = {
  llm: () => ["settings", "llm"] as const,
  webhook: () => ["settings", "webhook"] as const,
};

export function useLLMSettings() {
  return useQuery({
    queryKey: settingsKeys.llm(),
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/settings/llm");
      if (error) throw error;
      return data;
    },
    staleTime: 60_000,
  });
}

export function useSaveLLMSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: components["schemas"]["LLMSettingsIn"]) => {
      const { data, error } = await api.PUT("/admin/settings/llm", { body });
      if (error) throw error;
      return data;
    },
    onSuccess: (data) => {
      qc.setQueryData(settingsKeys.llm(), data);
    },
  });
}

export function useWebhookSettings() {
  return useQuery({
    queryKey: settingsKeys.webhook(),
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/settings/webhook");
      if (error) throw error;
      return data;
    },
    staleTime: 60_000,
  });
}

export function useSaveWebhookUrl() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: components["schemas"]["WebhookEndpointIn"]) => {
      const { data, error } = await api.PUT("/admin/settings/webhook", { body });
      if (error) throw error;
      return data;
    },
    onSuccess: (data) => {
      qc.setQueryData(settingsKeys.webhook(), data);
    },
  });
}

export function useRotateWebhookHmac() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data, error } = await api.POST("/admin/settings/webhook/rotate");
      if (error) throw error;
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: settingsKeys.webhook() });
    },
  });
}

export function useSaveGitHubSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: components["schemas"]["GitHubAppIn"]) => {
      const { data, error } = await api.PUT("/admin/settings/github", { body });
      if (error) throw error;
      return data;
    },
    onSuccess: (data) => {
      qc.setQueryData(settingsKeys.webhook(), data);
    },
  });
}

export function useTestGitHubConnection() {
  return useMutation({
    mutationFn: async () => {
      const { data, error } = await api.POST("/admin/settings/github/test");
      if (error) throw error;
      return data;
    },
  });
}

export function useSaveGitLabSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: components["schemas"]["GitLabIn"]) => {
      const { data, error } = await api.PUT("/admin/settings/gitlab", { body });
      if (error) throw error;
      return data;
    },
    onSuccess: (data) => {
      qc.setQueryData(settingsKeys.webhook(), data);
    },
  });
}

export function useTestGitLabConnection() {
  return useMutation({
    mutationFn: async () => {
      const { data, error } = await api.POST("/admin/settings/gitlab/test");
      if (error) throw error;
      return data;
    },
  });
}
