from collections.abc import Iterator

from sqlmodel import Session, create_engine

from app.core.config import settings

# pool_pre_ping descarta conexiones muertas (Supabase y Cloud Run cortan conexiones inactivas).
engine = create_engine(settings.database_url, pool_pre_ping=True)


def get_session() -> Iterator[Session]:
    """Dependencia de FastAPI: una sesión de BD por petición."""
    with Session(engine) as session:
        yield session
