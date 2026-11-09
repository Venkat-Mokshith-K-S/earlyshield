import { useQuery } from "@tanstack/react-query";
import { systemApi } from "@/domains/system/api/systemApi";

export function useSystemHealth() {
  return useQuery({
    queryKey: ["system", "health"],
    queryFn: systemApi.getHealth,
    refetchInterval: 15_000,
  });
}

export function useSystemVersion() {
  return useQuery({
    queryKey: ["system", "version"],
    queryFn: systemApi.getVersion,
    staleTime: Infinity,
  });
}
