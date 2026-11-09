"""
Pydantic schemas for the `detection` domain.

FileActivityFeatures mirrors the exact feature schema the model was trained
on (see /ml/data/generate_dataset.py) and matches what the Module 3
Watchdog/Psutil monitor will emit once it exists — this is the contract
between real-time monitoring and the ML classifier.
"""

from typing import List, Literal

from pydantic import BaseModel, ConfigDict, Field


class FileActivityFeatures(BaseModel):
    """Behavioral features computed over one observation window (e.g. 10s)."""

    file_modification_rate: float = Field(..., ge=0, description="Files modified per second")
    file_rename_rate: float = Field(..., ge=0, description="Files renamed per second")
    file_deletion_rate: float = Field(..., ge=0, description="Files deleted per second")
    entropy_mean: float = Field(..., ge=0, le=8, description="Mean Shannon entropy of modified content (bits/byte)")
    entropy_delta: float = Field(..., description="Change in entropy vs. historical baseline")
    extension_change_ratio: float = Field(..., ge=0, le=1, description="Fraction of modified files with changed extension")
    unique_dirs_touched: float = Field(..., ge=0, description="Distinct directories touched in the window")
    avg_size_change_ratio: float = Field(..., ge=0, description="Mean (new_size / old_size) across modified files")
    process_cpu_percent: float = Field(..., ge=0, le=100, description="CPU utilization of the responsible process")
    io_write_rate_mb_s: float = Field(..., ge=0, description="Process write throughput, MB/s")
    read_write_ratio: float = Field(..., ge=0, description="Ratio of read ops to write ops")

    class Config:
        json_schema_extra = {
            "example": {
                "file_modification_rate": 42.5,
                "file_rename_rate": 21.0,
                "file_deletion_rate": 7.3,
                "entropy_mean": 7.36,
                "entropy_delta": 3.72,
                "extension_change_ratio": 0.77,
                "unique_dirs_touched": 8,
                "avg_size_change_ratio": 1.40,
                "process_cpu_percent": 51.6,
                "io_write_rate_mb_s": 18.0,
                "read_write_ratio": 1.29,
            }
        }


class FeatureContribution(BaseModel):
    feature: str
    value: float
    shap_value: float
    direction: Literal["increases_risk", "decreases_risk"]


class DetectionResult(BaseModel):
    prediction: Literal["benign", "ransomware_like"]
    confidence: float = Field(..., ge=0, le=1)
    threat_score: float = Field(..., ge=0, le=100)
    top_contributing_features: List[FeatureContribution]
    explanation_summary: str


class ModelInfoResponse(BaseModel):
    # `model_type` is a field name here, not Pydantic's reserved model_* API.
    model_config = ConfigDict(protected_namespaces=())

    model_type: str
    feature_names: List[str]
    training_accuracy: float
    training_f1_score: float
    training_roc_auc: float


class SimulationScenario(BaseModel):
    scenario: Literal["benign", "ransomware_typical", "ransomware_stealthy"]
    features: FileActivityFeatures
    result: DetectionResult
