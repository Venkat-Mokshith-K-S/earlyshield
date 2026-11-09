import { apiClient } from "@/shared/lib/apiClient";
import type { APIResponse } from "@/shared/types/api.types";

export interface FileActivityFeatures {
  file_modification_rate: number;
  file_rename_rate: number;
  file_deletion_rate: number;
  entropy_mean: number;
  entropy_delta: number;
  extension_change_ratio: number;
  unique_dirs_touched: number;
  avg_size_change_ratio: number;
  process_cpu_percent: number;
  io_write_rate_mb_s: number;
  read_write_ratio: number;
}

export interface FeatureContribution {
  feature: string;
  value: number;
  shap_value: number;
  direction: "increases_risk" | "decreases_risk";
}

export interface DetectionResult {
  prediction: "benign" | "ransomware_like";
  confidence: number;
  threat_score: number;
  top_contributing_features: FeatureContribution[];
  explanation_summary: string;
}

export interface ModelInfo {
  model_type: string;
  feature_names: string[];
  training_accuracy: number;
  training_f1_score: number;
  training_roc_auc: number;
}

export interface SimulationScenario {
  scenario: "benign" | "ransomware_typical" | "ransomware_stealthy";
  features: FileActivityFeatures;
  result: DetectionResult;
}

export const detectionApi = {
  getModelInfo: async (): Promise<ModelInfo> => {
    const res = await apiClient.get<APIResponse<ModelInfo>>("/detection/model-info");
    return res.data.data;
  },
  analyze: async (features: FileActivityFeatures): Promise<DetectionResult> => {
    const res = await apiClient.post<APIResponse<DetectionResult>>("/detection/analyze", features);
    return res.data.data;
  },
  simulate: async (
    scenario: "benign" | "ransomware_typical" | "ransomware_stealthy"
  ): Promise<SimulationScenario> => {
    const res = await apiClient.get<APIResponse<SimulationScenario>>(
      `/detection/simulate?scenario=${scenario}`
    );
    return res.data.data;
  },
};
