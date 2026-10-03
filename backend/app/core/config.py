from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración del backend. Se lee de variables de entorno o de `backend/.env`."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://clockify:clockify@localhost:5432/clockify"
    secret_key: str = "cambia-esto-en-produccion"
    cors_origins: list[str] = ["http://localhost:5173"]
    # Client ID de OAuth de Google: el ID token del login debe ir emitido para este cliente.
    google_client_id: str = ""
    # Días que dura la sesión (cookie + JWT).
    session_days: int = 30
    # En producción (HTTPS y front en otro dominio) la cookie necesita Secure y SameSite=None.
    cookie_secure: bool = False
    cookie_samesite: str = "lax"


settings = Settings()
