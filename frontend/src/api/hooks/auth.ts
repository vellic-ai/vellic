import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { components } from "@/api/schema";

export const authKeys = {
  status: () => ["auth", "status"] as const,
};

export function useAuthStatus() {
  return useQuery({
    queryKey: authKeys.status(),
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/auth/status");
      if (error) throw error;
      return data;
    },
    staleTime: 30_000,
  });
}

export function useSetup() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: components["schemas"]["SetupBody"]) => {
      const { error } = await api.PUT("/admin/auth/setup", { body });
      if (error) throw error;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: authKeys.status() }),
  });
}

export function useLogin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: components["schemas"]["LoginBody"]) => {
      const { data, error } = await api.POST("/admin/auth/login", { body });
      if (error) throw error;
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: authKeys.status() }),
  });
}

export function useLogout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { error } = await api.POST("/admin/auth/logout");
      if (error) throw error;
    },
    onSuccess: () => qc.clear(),
  });
}

export function useChangePassword() {
  return useMutation({
    mutationFn: async (body: components["schemas"]["ChangePasswordBody"]) => {
      const { error } = await api.POST("/admin/auth/change-password", { body });
      if (error) throw error;
    },
  });
}
