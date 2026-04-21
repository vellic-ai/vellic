import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { components } from "@/api/schema";

export const featureFlagKeys = {
  all: () => ["feature-flags"] as const,
};

export function useFeatureFlags() {
  return useQuery({
    queryKey: featureFlagKeys.all(),
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/features");
      if (error) throw error;
      return data;
    },
    staleTime: 30_000,
  });
}

export function useSetFeatureFlag() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      key,
      body,
    }: {
      key: string;
      body: components["schemas"]["FeatureFlagOverride"];
    }) => {
      const { data, error } = await api.PUT("/admin/features/{flag_key}", {
        params: { path: { flag_key: key } },
        body,
      });
      if (error) throw error;
      return data;
    },
    onSuccess: (updated) => {
      qc.setQueryData(
        featureFlagKeys.all(),
        (prev: components["schemas"]["FeatureFlagList"] | undefined) => {
          if (!prev) return prev;
          return {
            items: prev.items.map((f) => (f.key === updated.key ? updated : f)),
          };
        },
      );
    },
  });
}
