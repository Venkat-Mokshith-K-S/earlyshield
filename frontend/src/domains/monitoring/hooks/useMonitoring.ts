import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { monitoringApi } from "@/domains/monitoring/api/monitoringApi";

export function useMonitorStatus() {
  return useQuery({
    queryKey: ["monitoring", "status"],
    queryFn: monitoringApi.getStatus,
    refetchInterval: 5_000,
  });
}

export function useMonitorEvents(enabled: boolean) {
  return useQuery({
    queryKey: ["monitoring", "events"],
    queryFn: () => monitoringApi.getEvents(30),
    refetchInterval: enabled ? 5_000 : false,
  });
}

export function useStartMonitor() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ watchPath, windowSeconds }: { watchPath: string; windowSeconds: number }) =>
      monitoringApi.start(watchPath, windowSeconds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["monitoring", "status"] });
    },
  });
}

export function useStopMonitor() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: monitoringApi.stop,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["monitoring", "status"] });
    },
  });
}
