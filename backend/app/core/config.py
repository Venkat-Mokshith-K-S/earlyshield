"""
Centralized application configuration.

All environment-dependent values (database URL, secrets, CORS origins, etc.)
are declared here and loaded from environment variables / a .env file.
No other module should read os.environ directly — everything routes through
this single Settings object so configuration stays in one place (SRP).
"""

from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from typing_extensions import Annotated


class Settings(BaseSettings):
    # --- Application / academic metadata ---
    PROJECT_NAME: str = "EarlyShield"
    PROJECT_FULL_TITLE: str = (
        "An Explainable Behavioral Machine Learning Framework for "
        "Early Ransomware Detection and Secure Automated Recovery"
    )
    PROJECT_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # --- Database ---
    DATABASE_URL: str = (
        "postgresql+psycopg://earlyshield:earlyshield@postgres:5432/earlyshield_db"
    )
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # --- Security (JWT auth, Module 2) ---
    JWT_SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    # Failed logins allowed per account before it's paused for the lockout period.
    LOGIN_MAX_FAILURES: int = 10
    LOGIN_LOCKOUT_MINUTES: int = 15

    # --- Sign in with Google / GitHub (OAuth 2.0) ---
    # The address people open in the browser. OAuth callbacks come back to
    # PUBLIC_URL/api/v1/auth/oauth/<provider>/callback (proxied to the
    # backend by nginx), and that exact URL must be registered with the
    # provider. A provider whose client ID is empty is simply hidden.
    PUBLIC_URL: str = "http://localhost:5173"
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""

    # --- CORS ---
    BACKEND_CORS_ORIGINS: Annotated[List[str], NoDecode] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    # --- Logging ---
    LOG_LEVEL: str = "INFO"

    # --- ML Detection Engine ---
    ML_MODEL_PATH: str = "app/ml_models/ransomware_rf_model.joblib"
    ML_EXPLAINER_PATH: str = "app/ml_models/shap_explainer.joblib"
    ML_FEATURE_NAMES_PATH: str = "app/ml_models/feature_names.joblib"

    # --- Real-time File Monitoring (Module 3) ---
    # PollingObserver actively re-scans the watched directory instead of
    # waiting for OS-level inotify events. This is REQUIRED (not optional)
    # when the watched directory is a Docker Desktop for Windows bind
    # mount, since inotify events from Windows-side file changes don't
    # reliably propagate into the Linux container — a documented Docker
    # Desktop limitation, confirmed during testing (a file created from
    # inside the container was detected instantly; the identical file
    # created from Windows Explorer/PowerShell was never detected at all).
    # Set to false only for native Linux deployments, where inotify is
    # faster and doesn't need this workaround.
    FILE_MONITOR_USE_POLLING: bool = True

    # --- Secure Automated Recovery (Module 5) ---
    # Must be OUTSIDE every watched folder (enforced at monitor start).
    # Relative paths resolve against the backend's working directory, i.e.
    # /app/recovery_vault in Docker = backend/recovery_vault on the host.
    RECOVERY_VAULT_PATH: str = "recovery_vault"
    RECOVERY_AUTO_RESPONSE: bool = True      # quarantine + restore on detection
    # Off by default: process attribution is a heuristic, and in testing on
    # a desktop the "most active process" during a simulated attack was
    # the user's own Claude app, not the attacker. Turn on (dashboard or
    # .env) when the attacker runs where attribution can be trusted.
    RECOVERY_AUTO_SUSPEND: bool = False
    # Chosen from measured data (backend/evaluation/results_calibration/
    # THRESHOLD.md), not guessed: on 99 live runs, every value from 0.50 to
    # 0.75 wrongly triggered on the same benign workloads, while 0.50 was
    # the only value that let recovery cover all 36 attacks (slow in-place
    # encryption scores 0.54-0.57). Quarantine + restore is fully
    # reversible, so acting on every detection is an acceptable default.
    RECOVERY_CONFIDENCE_THRESHOLD: float = 0.50
    RECOVERY_MAX_FILE_MB: float = 50.0
    RECOVERY_MAX_VERSIONS_PER_FILE: int = 5
    RECOVERY_MAX_BASELINE_FILES: int = 20000
    # Never suspended, however strong the detection (case-insensitive).
    RECOVERY_PROTECTED_PROCESSES: Annotated[List[str], NoDecode] = [
        "System", "Registry", "smss.exe", "csrss.exe", "wininit.exe", "winlogon.exe",
        "services.exe", "lsass.exe", "svchost.exe", "explorer.exe", "dwm.exe",
        "MsMpEng.exe", "Docker Desktop.exe", "com.docker.backend.exe", "vmmem", "vmmemWSL",
        "systemd", "init", "sshd", "dockerd", "containerd", "containerd-shim",
        "uvicorn", "postgres",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", "RECOVERY_PROTECTED_PROCESSES", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        """Allow list settings to be supplied as a comma-separated string in .env."""
        if isinstance(v, str) and not v.startswith("["):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Cached Settings instance — .env parsed once per process."""
    return Settings()


settings = get_settings()
