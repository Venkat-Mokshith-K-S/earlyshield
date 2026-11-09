import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { recoveryApi } from "@/domains/recovery/api/recoveryApi";

export function useRecoveryStatus() {
  return useQuery({
    queryKey: ["recovery", "status"],
    queryFn: recoveryApi.getStatus,
    refetchInterval: 5_000,
  });
}

export function useRecoveryActions() {
  return useQuery({
    queryKey: ["recovery", "actions"],
    queryFn: () => recoveryApi.getActions(50),
    refetchInterval: 5_000,
  });
}

function useInvalidateRecovery() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: ["recovery"] });
}

export function useUpdateRecoverySettings() {
  const invalidate = useInvalidateRecovery();
  return useMutation({ mutationFn: recoveryApi.updateSettings, onSuccess: invalidate });
}

export function useSnapshotNow() {
  const invalidate = useInvalidateRecovery();
  return useMutation({ mutationFn: recoveryApi.snapshot, onSuccess: invalidate });
}

export function useProtectedFiles() {
  return useQuery({
    queryKey: ["recovery", "files"],
    queryFn: () => recoveryApi.getFiles(),
    refetchInterval: 10_000,
  });
}

export function useRestoreFiles() {
  const invalidate = useInvalidateRecovery();
  return useMutation({ mutationFn: recoveryApi.restore, onSuccess: invalidate });
}

export function useResumeProcess() {
  const invalidate = useInvalidateRecovery();
  return useMutation({ mutationFn: recoveryApi.resumeProcess, onSuccess: invalidate });
}
