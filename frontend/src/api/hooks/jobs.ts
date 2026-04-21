import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

interface JobFilters {
  limit?: number;
  offset?: number;
  status?: string;
}

export const jobKeys = {
  all: () => ["jobs"] as const,
  list: (filters: JobFilters) => ["jobs", "list", filters] as const,
};

export function useJobs(filters: JobFilters = {}) {
  return useQuery({
    queryKey: jobKeys.list(filters),
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/jobs", {
        params: { query: filters },
      });
      if (error) throw error;
      return data;
    },
    staleTime: 5_000,
  });
}
