import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";

interface DeliveryFilters {
  limit?: number;
  offset?: number;
  status?: string;
  event_type?: string;
}

export const deliveryKeys = {
  all: () => ["deliveries"] as const,
  list: (filters: DeliveryFilters) => ["deliveries", "list", filters] as const,
};

export function useDeliveries(filters: DeliveryFilters = {}) {
  return useQuery({
    queryKey: deliveryKeys.list(filters),
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/deliveries", {
        params: { query: filters },
      });
      if (error) throw error;
      return data;
    },
    staleTime: 5_000,
  });
}

export function useReplayDelivery() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (deliveryId: string) => {
      const { data, error } = await api.POST("/admin/replay/{delivery_id}", {
        params: { path: { delivery_id: deliveryId } },
      });
      if (error) throw error;
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: deliveryKeys.all() });
    },
  });
}
