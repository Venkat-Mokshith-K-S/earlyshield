import { apiClient } from "@/shared/lib/apiClient";
import type { APIResponse } from "@/shared/types/api.types";

export interface SuspendedProcess {
  pid: number;
  name: string;
  suspended_at: string;
  incident_id: string | null;
}

export interface RecoveryStatus {
  auto_response: boolean;
  auto_suspend: boolean;
  confidence_threshold: number;
  vault_path: string;
  files_protected: number;
  versions_stored: number;
  vault_size_bytes: number;
  quarantined_files: number;
  suspended_processes: SuspendedProcess[];
  active_incident_id: string | null;
}

export type RecoveryActionType =
  | "baseline_snapshot"
  | "manual_snapshot"
  | "suspend_process"
  | "resume_process"
  | "quarantine_file"
  | "restore_file"
  | "incident_summary";

export interface RecoveryAction {
  id: string;
  created_at: string;
  incident_id: string | null;
  action_type: RecoveryActionType;
  status: "success" | "failed" | "skipped";
  target: string | null;
  detail: string;
  triggered_by: string;
}

export interface RecoverySettingsUpdate {
  auto_response?: boolean;
  auto_suspend?: boolean;
  confidence_threshold?: number;
}

export const recoveryApi = {
  getStatus: async (): Promise<RecoveryStatus> => {
    const res = await apiClient.get<APIResponse<RecoveryStatus>>("/recovery/status");
    return res.data.data;
  },
  getActions: async (limit = 50): Promise<RecoveryAction[]> => {
    const res = await apiClient.get<APIResponse<RecoveryAction[]>>(`/recovery/actions?limit=${limit}`);
    return res.data.data;
  },
  updateSettings: async (data: RecoverySettingsUpdate): Promise<RecoveryStatus> => {
    const res = await apiClient.patch<APIResponse<RecoveryStatus>>("/recovery/settings", data);
    return res.data.data;
  },
  snapshot: async (): Promise<number> => {
    const res = await apiClient.post<APIResponse<number>>("/recovery/snapshot");
    return res.data.data;
  },
  resumeProcess: async (pid: number): Promise<void> => {
    await apiClient.post(`/recovery/processes/${pid}/resume`);
  },
  getFiles: async (limit = 2000): Promise<ProtectedFile[]> => {
    const res = await apiClient.get<APIResponse<ProtectedFile[]>>(`/recovery/files?limit=${limit}`);
    return res.data.data;
  },
  restore: async (data: { paths: string[]; before?: string }): Promise<RestoreResult> => {
    const res = await apiClient.post<APIResponse<RestoreResult>>("/recovery/restore", data);
    return res.data.data;
  },
};

export interface ProtectedFile {
  path: string;
  versions: number;
  latest_captured_at: string | null;
  exists: boolean;
}

export interface RestoreResult {
  restored: number;
  skipped: number;
  failed: number;
}
