import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { components } from "@/api/schema";

export const repoKeys = {
  all: () => ["repos"] as const,
  list: () => ["repos", "list"] as const,
};

export function useRepos() {
  return useQuery({
    queryKey: repoKeys.list(),
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/settings/repos");
      if (error) throw error;
      return data;
    },
    staleTime: 30_000,
  });
}

export function useCreateRepo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: components["schemas"]["RepoBody"]) => {
      const { data, error } = await api.POST("/admin/settings/repos", { body });
      if (error) throw error;
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: repoKeys.all() }),
  });
}

export function useUpdateRepo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      body,
    }: {
      id: string;
      body: components["schemas"]["RepoBody"];
    }) => {
      const { data, error } = await api.PATCH("/admin/settings/repos/{repo_id}", {
        params: { path: { repo_id: id } },
        body,
      });
      if (error) throw error;
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: repoKeys.all() }),
  });
}

export function useToggleRepo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data, error } = await api.POST("/admin/settings/repos/{repo_id}/toggle", {
        params: { path: { repo_id: id } },
      });
      if (error) throw error;
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: repoKeys.all() }),
  });
}

export function useDeleteRepo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { error } = await api.DELETE("/admin/settings/repos/{repo_id}", {
        params: { path: { repo_id: id } },
      });
      if (error) throw error;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: repoKeys.all() }),
  });
}
