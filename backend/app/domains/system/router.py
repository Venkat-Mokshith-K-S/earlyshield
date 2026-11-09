"""Router for the `system` domain."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.domains.system.schemas import HealthCheckResponse, VersionResponse
from app.domains.system.service import SystemService
from app.shared.schemas import APIResponse

router = APIRouter(prefix="/system", tags=["System"])


@router.get("/health", response_model=APIResponse[HealthCheckResponse], summary="Health check")
def health_check(db: Session = Depends(get_db)) -> APIResponse[HealthCheckResponse]:
    result = SystemService.check_health(db)
    return APIResponse(message="Health check completed", data=result)


@router.get("/version", response_model=APIResponse[VersionResponse], summary="API and project version")
def get_version() -> APIResponse[VersionResponse]:
    result = SystemService.get_version()
    return APIResponse(message="Version retrieved", data=result)
