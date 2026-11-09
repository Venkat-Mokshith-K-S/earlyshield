import { apiClient } from "@/shared/lib/apiClient";
import type { APIResponse } from "@/shared/types/api.types";

export interface HealthCheckResponse {
  status: "ok" | "degraded";
  environment: string;
  database_connected: boolean;
}

export interface VersionResponse {
  project_name: string;
  project_full_title: string;
  version: string;
}

export const systemApi = {
  getHealth: async (): Promise<HealthCheckResponse> => {
    const response = await apiClient.get<APIResponse<HealthCheckResponse>>("/system/health");
    return response.data.data;
  },
  getVersion: async (): Promise<VersionResponse> => {
    const response = await apiClient.get<APIResponse<VersionResponse>>("/system/version");
    return response.data.data;
  },
};
