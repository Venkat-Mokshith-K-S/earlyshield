"""FastAPI application entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging_config import configure_logging, get_logger
from app.domains.auth.router import router as auth_router
from app.domains.detection.router import router as detection_router
from app.domains.detection.service import DetectionService
from app.domains.monitoring.router import router as monitoring_router
from app.domains.recovery.router import router as recovery_router
from app.domains.system.router import router as system_router

configure_logging()
logger = get_logger(__name__)

_PLACEHOLDER_JWT_SECRETS = {"CHANGE_ME_IN_PRODUCTION", "replace-with-a-long-random-secret"}

# The interactive API docs list every endpoint and schema: useful in
# development, needless attack surface in production.
_docs_enabled = settings.ENVIRONMENT != "production"

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description=f"{settings.PROJECT_NAME} — {settings.PROJECT_FULL_TITLE}. API documentation for all backend modules.",
    docs_url="/api/docs" if _docs_enabled else None,
    redoc_url="/api/redoc" if _docs_enabled else None,
    openapi_url="/api/openapi.json" if _docs_enabled else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(system_router, prefix=settings.API_V1_PREFIX)
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(detection_router, prefix=settings.API_V1_PREFIX)
app.include_router(monitoring_router, prefix=settings.API_V1_PREFIX)
app.include_router(recovery_router, prefix=settings.API_V1_PREFIX)


@app.on_event("startup")
async def on_startup() -> None:
    logger.info("%s v%s starting in '%s' mode", settings.PROJECT_NAME, settings.PROJECT_VERSION, settings.ENVIRONMENT)
    if settings.JWT_SECRET_KEY in _PLACEHOLDER_JWT_SECRETS or len(settings.JWT_SECRET_KEY) < 32:
        if settings.ENVIRONMENT == "production":
            raise RuntimeError("JWT_SECRET_KEY must be set to a random value of at least 32 characters in production")
        logger.warning("JWT_SECRET_KEY is a placeholder/short value — fine for local dev, never for production")
    DetectionService.warm_up()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    logger.info("%s shutting down", settings.PROJECT_NAME)
