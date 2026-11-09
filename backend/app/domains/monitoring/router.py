"""Router for the `monitoring` domain."""

from typing import List

from fastapi import APIRouter, Depends, Query

from app.domains.auth.dependencies import get_current_user, require_roles
from app.domains.auth.models import UserRole
from app.domains.monitoring.schemas import (
    DetectionEvent,
    MonitorStartRequest,
    MonitorStatusResponse,
)
from app.domains.monitoring.service import FileSystemMonitorService
from app.shared.schemas import APIResponse

router = APIRouter(prefix="/monitoring", tags=["Monitoring"], dependencies=[Depends(get_current_user)])

# Starting/stopping the watcher changes system state; viewers can only look.
_can_control_monitor = Depends(require_roles(UserRole.ADMIN, UserRole.ANALYST))


@router.post(
    "/start",
    response_model=APIResponse[MonitorStatusResponse],
    summary="Start real-time file-system monitoring",
    dependencies=[_can_control_monitor],
    description="Begins watching the given directory in real time. Every "
    "`window_seconds`, computed behavioral features are sent to the "
    "detection engine automatically.",
)
def start_monitor(request: MonitorStartRequest) -> APIResponse[MonitorStatusResponse]:
    result = FileSystemMonitorService.start(request.watch_path, request.window_seconds)
    return APIResponse(message="Monitor started", data=result)


@router.post(
    "/stop",
    response_model=APIResponse[MonitorStatusResponse],
    summary="Stop the active monitor",
    dependencies=[_can_control_monitor],
)
def stop_monitor() -> APIResponse[MonitorStatusResponse]:
    result = FileSystemMonitorService.stop()
    return APIResponse(message="Monitor stopped", data=result)


@router.get(
    "/status",
    response_model=APIResponse[MonitorStatusResponse],
    summary="Get current monitor status",
)
def monitor_status() -> APIResponse[MonitorStatusResponse]:
    result = FileSystemMonitorService.get_status()
    return APIResponse(message="Status retrieved", data=result)


@router.get(
    "/events",
    response_model=APIResponse[List[DetectionEvent]],
    summary="Get recent detection events from live monitoring",
    description="Returns the most recent windows that were analyzed, newest first.",
)
def monitor_events(limit: int = Query(20, ge=1, le=200)) -> APIResponse[List[DetectionEvent]]:
    result = FileSystemMonitorService.get_recent_events(limit)
    return APIResponse(message=f"Retrieved {len(result)} events", data=result)
