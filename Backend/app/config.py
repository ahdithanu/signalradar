from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

_backend_dir = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_backend_dir / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    database_url: str = "postgresql://signal_user:signal_pass@localhost:5432/signal_radar"
    app_env: str = "development"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    cors_origins: str = "http://localhost:3000,http://localhost:5173,http://localhost:8080"
    crunchbase_api_key: str = ""

    # Supabase Auth
    supabase_jwt_secret: str = ""
    supabase_url: str = ""
    auth_enabled: bool = False  # Set True in production or when Supabase is configured

    # FMP (Financial Modeling Prep) API
    fmp_api_key: str = ""  # Required for real funding feed ingestion
    fmp_base_url: str = "https://financialmodelingprep.com/api/v3"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    def validate_production_config(self) -> list[str]:
        """Return a list of fatal configuration errors for production.

        Called at startup. If non-empty, the app must refuse to start.
        """
        errors: list[str] = []
        if not self.auth_enabled:
            errors.append(
                "AUTH_ENABLED must be true in production. "
                "Running without authentication is not allowed."
            )
        if not self.supabase_jwt_secret or self.supabase_jwt_secret == "your-jwt-secret-from-supabase-settings":
            errors.append(
                "SUPABASE_JWT_SECRET is missing or still set to the placeholder value."
            )
        if not self.supabase_url or self.supabase_url == "https://your-project.supabase.co":
            errors.append(
                "SUPABASE_URL is missing or still set to the placeholder value."
            )
        return errors


settings = Settings()
