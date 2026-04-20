import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

export const statsKeys = {
  all: () => ["stats"] as const,
};

export function useStats(refetchInterval?: number) {
  return useQuery({
    queryKey: statsKeys.all(),
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/stats");
      if (error) throw error;
      return data;
    },
    refetchInterval,
    staleTime: 10_000,
  });
}
