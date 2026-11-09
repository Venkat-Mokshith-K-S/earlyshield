"""Router for the `detection` domain."""

import numpy as np
from fastapi import APIRouter, Depends, Query

from app.domains.detection.schemas import (
    DetectionResult,
    FileActivityFeatures,
    ModelInfoResponse,
    SimulationScenario,
)
from app.domains.auth.dependencies import get_current_user
from app.domains.detection.service import DetectionService
from app.shared.schemas import APIResponse

router = APIRouter(prefix="/detection", tags=["Detection"], dependencies=[Depends(get_current_user)])


@router.post(
    "/analyze",
    response_model=APIResponse[DetectionResult],
    summary="Analyze behavioral features for ransomware-like activity",
    description="Accepts a window of file-system/process behavioral features "
    "and returns a prediction with a SHAP-based, human-readable explanation.",
)
def analyze(features: FileActivityFeatures) -> APIResponse[DetectionResult]:
    result = DetectionService.analyze(features)
    return APIResponse(message="Analysis completed", data=result)


@router.get(
    "/model-info",
    response_model=APIResponse[ModelInfoResponse],
    summary="Get detection model metadata and training metrics",
)
def model_info() -> APIResponse[ModelInfoResponse]:
    result = DetectionService.get_model_info()
    return APIResponse(message="Model info retrieved", data=result)


@router.get(
    "/simulate",
    response_model=APIResponse[SimulationScenario],
    summary="Generate and analyze a synthetic demo scenario",
    description="For demoing the detection engine before the real-time file-system "
    "monitor (Module 3) exists.",
)
def simulate(
    scenario: str = Query(
        "benign",
        pattern="^(benign|ransomware_typical|ransomware_stealthy)$",
        description="Which behavioral scenario to simulate",
    )
) -> APIResponse[SimulationScenario]:
    rng = np.random.default_rng()
    features = DetectionService.simulate_features(scenario, rng)
    result = DetectionService.analyze(features)
    payload = SimulationScenario(scenario=scenario, features=features, result=result)
    return APIResponse(message=f"Simulated '{scenario}' scenario analyzed", data=payload)
