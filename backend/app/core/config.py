from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración del backend. Se lee de variables de entorno o de `backend/.env`."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://clockify:clockify@localhost:5432/clockify"
    secret_key: str = "cambia-esto-en-produccion"
    cors_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
