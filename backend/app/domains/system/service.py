"""Service layer for the `system` domain."""

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging_config import get_logger
from app.domains.system.schemas import HealthCheckResponse, VersionResponse

logger = get_logger(__name__)


class SystemService:
    @staticmethod
    def check_health(db: Session) -> HealthCheckResponse:
        database_connected = False
        try:
            db.execute(text("SELECT 1"))
            database_connected = True
        except Exception as exc:  # noqa: BLE001
            logger.error("Database health check failed: %s", exc)
        return HealthCheckResponse(
            status="ok" if database_connected else "degraded",
            environment=settings.ENVIRONMENT,
            database_connected=database_connected,
        )

    @staticmethod
    def get_version() -> VersionResponse:
        return VersionResponse(
            project_name=settings.PROJECT_NAME,
            project_full_title=settings.PROJECT_FULL_TITLE,
            version=settings.PROJECT_VERSION,
        )
