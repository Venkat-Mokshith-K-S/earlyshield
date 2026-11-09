"""
Pydantic schemas for the `monitoring` domain.

This domain is the bridge between the real file system and the `detection`
domain: it watches a directory in real time, computes the same 11
behavioral features the model was trained on (see
/ml/data/generate_dataset.py), and feeds them to DetectionService on a
fixed interval.
"""

from datetime import datetime
import uuid
from typing import List, Optional

from pydantic import BaseModel, Field

from app.domains.detection.schemas import DetectionResult, FileActivityFeatures


class MonitorStartRequest(BaseModel):
    watch_path: str = Field(..., description="Absolute path of the directory to monitor")
    window_seconds: float = Field(10.0, ge=2.0, le=120.0, description="Observation window length in seconds")


class MonitorStatusResponse(BaseModel):
    is_running: bool
    watch_path: Optional[str] = None
    window_seconds: Optional[float] = None
    windows_processed: int = 0
    started_at: Optional[datetime] = None


class DetectionEvent(BaseModel):
    timestamp: datetime
    window_seconds: float
    raw_event_count: int = Field(..., description="Number of raw filesystem events observed in this window")
    attributed_process: Optional[str] = Field(
        None, description="Best-effort process name attributed to this window's activity (see monitoring limitations)"
    )
    attributed_pid: Optional[int] = None
    features: FileActivityFeatures
    result: DetectionResult
    recovery_incident_id: Optional[uuid.UUID] = Field(
        None, description="Set when this window triggered an automated recovery response (Module 5)"
    )
    response_ms: Optional[float] = Field(
        None, description="Time the automated response took; `timestamp` is when it finished"
    )
