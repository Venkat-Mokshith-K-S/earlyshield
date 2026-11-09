import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { detectionApi } from "@/domains/detection/api/detectionApi";

export function useModelInfo() {
  return useQuery({
    queryKey: ["detection", "model-info"],
    queryFn: detectionApi.getModelInfo,
    staleTime: Infinity, // trained metrics don't change during a session
  });
}

export function useSimulateScenario() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: detectionApi.simulate,
    onSuccess: () => {
      // A manual simulation doesn't feed the monitoring event log, but if
      // the person is also watching live events, refresh them so the UI
      // stays consistent.
      queryClient.invalidateQueries({ queryKey: ["monitoring", "events"] });
    },
  });
}
