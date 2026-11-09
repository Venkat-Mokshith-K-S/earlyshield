"""Application-wide exception hierarchy and FastAPI exception handlers."""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppException(Exception):
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, details: dict | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class NotFoundError(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "NOT_FOUND"


class ValidationError(AppException):
    status_code = 422
    error_code = "VALIDATION_ERROR"


class UnauthorizedError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "UNAUTHORIZED"


class ForbiddenError(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "FORBIDDEN"


class ConflictError(AppException):
    status_code = status.HTTP_409_CONFLICT
    error_code = "CONFLICT"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error_code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
                "path": str(request.url.path),
            },
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Same envelope as AppException, so the frontend's error normalizer
        # can show e.g. "password: Password must be at least 8 characters"
        # instead of falling back to a generic network-error message.
        errors = exc.errors()
        first = errors[0] if errors else {}
        field = ".".join(str(p) for p in first.get("loc", ())[1:])
        message = first.get("msg", "Invalid request").removeprefix("Value error, ")
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "error_code": "VALIDATION_ERROR",
                "message": f"{field}: {message}" if field else message,
                "details": {"errors": [{"field": ".".join(str(p) for p in e.get("loc", ())), "message": e.get("msg")} for e in errors]},
                "path": str(request.url.path),
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error_code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred.",
                "details": {},
                "path": str(request.url.path),
            },
        )
