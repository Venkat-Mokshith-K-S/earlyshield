"""Router for the `recovery` domain."""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.domains.auth.dependencies import get_current_user, require_roles
from app.domains.auth.models import User, UserRole
from app.domains.recovery.schemas import (
    ProtectedFile,
    RecoveryActionOut,
    RecoverySettingsUpdate,
    RecoveryStatusResponse,
    RestoreRequest,
    RestoreResult,
)
from app.domains.recovery.service import RecoveryService
from app.shared.schemas import APIResponse

router = APIRouter(prefix="/recovery", tags=["Recovery"], dependencies=[Depends(get_current_user)])

_analyst = require_roles(UserRole.ADMIN, UserRole.ANALYST)


@router.get("/status", response_model=APIResponse[RecoveryStatusResponse], summary="Vault stats and response settings")
def status() -> APIResponse[RecoveryStatusResponse]:
    return APIResponse(message="Recovery status retrieved", data=RecoveryService.get_status())


@router.patch(
    "/settings",
    response_model=APIResponse[RecoveryStatusResponse],
    summary="Toggle automated response (admin only)",
    description="Runtime change only; values reset to the .env settings when the backend restarts.",
)
def update_settings(
    data: RecoverySettingsUpdate, user: User = Depends(require_roles(UserRole.ADMIN))
) -> APIResponse[RecoveryStatusResponse]:
    return APIResponse(message="Recovery settings updated", data=RecoveryService.update_settings(data, user.email))


@router.get("/actions", response_model=APIResponse[List[RecoveryActionOut]], summary="Recovery audit log, newest first")
def actions(
    limit: int = Query(50, ge=1, le=500),
    incident_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
) -> APIResponse[List[RecoveryActionOut]]:
    rows = RecoveryService.list_actions(db, limit, incident_id)
    return APIResponse(message=f"Retrieved {len(rows)} actions", data=[RecoveryActionOut.model_validate(r) for r in rows])


@router.get("/files", response_model=APIResponse[List[ProtectedFile]], summary="Files with shadow copies")
def files(limit: int = Query(200, ge=1, le=2000)) -> APIResponse[List[ProtectedFile]]:
    result = RecoveryService.list_protected_files(limit)
    return APIResponse(message=f"Retrieved {len(result)} files", data=result)


@router.post("/snapshot", response_model=APIResponse[int], summary="Snapshot the whole watched folder now")
def snapshot(user: User = Depends(_analyst)) -> APIResponse[int]:
    stored = RecoveryService.manual_snapshot(user.email)
    return APIResponse(message=f"{stored} new shadow copies stored", data=stored)


@router.post("/restore", response_model=APIResponse[RestoreResult], summary="Restore files from shadow copies")
def restore(data: RestoreRequest, user: User = Depends(_analyst)) -> APIResponse[RestoreResult]:
    result = RecoveryService.manual_restore(data.paths, data.before, user.email)
    return APIResponse(message="Restore completed", data=result)


@router.post("/processes/{pid}/resume", response_model=APIResponse[None], summary="Resume a suspended process")
def resume(pid: int, user: User = Depends(_analyst)) -> APIResponse[None]:
    RecoveryService.resume_process(pid, user.email)
    return APIResponse(message=f"PID {pid} resumed")
