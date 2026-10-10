from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración del backend. Se lee de variables de entorno o de `backend/.env`."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://clockify:clockify@127.0.0.1:5432/clockify"
    secret_key: str = "cambia-esto-en-produccion"
    cors_origins: list[str] = ["http://localhost:5173"]
    # Client ID de OAuth de Google: el ID token del login debe ir emitido para este cliente.
    google_client_id: str = ""
    # Días que dura la sesión (cookie + JWT).
    session_days: int = 30
    # En producción (HTTPS y front en otro dominio) la cookie necesita Secure y SameSite=None.
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    # Emails con acceso al panel /admin (en .env como lista JSON: ["a@b.com"]).
    admin_emails: list[str] = []
    # URL del front: con ella se montan los links de los emails (recuperar contraseña).
    frontend_url: str = "http://localhost:5173"
    # "console" escribe los emails en el log (local); "resend" los envía de verdad.
    email_backend: str = "console"
    resend_api_key: str = ""
    email_from: str = "Hourli-fy <no-responder@example.com>"


settings = Settings()
