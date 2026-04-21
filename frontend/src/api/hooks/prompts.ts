import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";

export const promptKeys = {
  all: () => ["prompts"] as const,
};

export function usePrompts() {
  return useQuery({
    queryKey: promptKeys.all(),
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/prompts");
      if (error) throw error;
      return data;
    },
    staleTime: 30_000,
  });
}

export function useCreatePrompt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { name: string; body: string }) => {
      const { data, error } = await api.POST("/admin/prompts", { body });
      if (error) throw error;
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: promptKeys.all() }),
  });
}

export function useSavePrompt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ name, body }: { name: string; body: string }) => {
      const { data, error } = await api.PUT("/admin/prompts/{name}", {
        params: { path: { name } },
        body: { body },
      });
      if (error) throw error;
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: promptKeys.all() }),
  });
}

export function useSetPromptEnabled() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ name, enabled }: { name: string; enabled: boolean }) => {
      const { data, error } = await api.PATCH("/admin/prompts/{name}/enabled", {
        params: { path: { name } },
        body: { enabled },
      });
      if (error) throw error;
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: promptKeys.all() }),
  });
}

export function useDeletePrompt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (name: string) => {
      const { data, error } = await api.DELETE("/admin/prompts/{name}", {
        params: { path: { name } },
      });
      if (error) throw error;
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: promptKeys.all() }),
  });
}

export function useImportPrompts() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (files: File[]) => {
      const formData = new FormData();
      for (const f of files) formData.append("files", f);
      const res = await fetch("/admin/prompts/import", {
        method: "POST",
        credentials: "include",
        body: formData,
      });
      if (!res.ok) throw new Error(await res.text());
      return res.json() as Promise<{ imported: string[]; errors: string[] }>;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: promptKeys.all() }),
  });
}

export function useExportPrompts() {
  return useMutation({
    mutationFn: async () => {
      const res = await fetch("/admin/prompts/export", { credentials: "include" });
      if (!res.ok) throw new Error("Export failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "prompts.zip";
      a.click();
      URL.revokeObjectURL(url);
    },
  });
}
