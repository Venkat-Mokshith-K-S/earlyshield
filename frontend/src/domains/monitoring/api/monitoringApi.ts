import { apiClient } from "@/shared/lib/apiClient";
import type { APIResponse } from "@/shared/types/api.types";
import type { DetectionResult, FileActivityFeatures } from "@/domains/detection/api/detectionApi";

export interface MonitorStatus {
  is_running: boolean;
  watch_path: string | null;
  window_seconds: number | null;
  windows_processed: number;
  started_at: string | null;
}

export interface DetectionEvent {
  timestamp: string;
  window_seconds: number;
  raw_event_count: number;
  attributed_process: string | null;
  attributed_pid: number | null;
  features: FileActivityFeatures;
  result: DetectionResult;
  recovery_incident_id: string | null;
}

export const monitoringApi = {
  getStatus: async (): Promise<MonitorStatus> => {
    const res = await apiClient.get<APIResponse<MonitorStatus>>("/monitoring/status");
    return res.data.data;
  },
  getEvents: async (limit = 30): Promise<DetectionEvent[]> => {
    const res = await apiClient.get<APIResponse<DetectionEvent[]>>(`/monitoring/events?limit=${limit}`);
    return res.data.data;
  },
  start: async (watchPath: string, windowSeconds: number): Promise<MonitorStatus> => {
    const res = await apiClient.post<APIResponse<MonitorStatus>>("/monitoring/start", {
      watch_path: watchPath,
      window_seconds: windowSeconds,
    });
    return res.data.data;
  },
  stop: async (): Promise<MonitorStatus> => {
    const res = await apiClient.post<APIResponse<MonitorStatus>>("/monitoring/stop");
    return res.data.data;
  },
};
