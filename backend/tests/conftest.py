"""Fixtures compartidas: BD de pruebas, clientes con sesión iniciada y login de Google falso.

Los tests usan una BD aparte (`<nombre>_test` en el mismo Postgres de docker compose).
Cada test corre dentro de una transacción que se deshace al acabar: los `commit()` de las
rutas se convierten en savepoints y nada queda guardado entre tests.
"""

from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlmodel import Session, SQLModel

import app.models  # noqa: F401  (registra las tablas en SQLModel.metadata)
from app.core.config import settings
from app.core.google import GoogleIdentity, GoogleLoginError, get_google_verifier
from app.db import get_session
from app.main import app

TEST_DATABASE_URL = make_url(settings.database_url).set(
    database=f"{make_url(settings.database_url).database}_test"
)


def fake_google_verifier(credential: str) -> GoogleIdentity:
    """En los tests el "ID token" es simplemente `sub|email|nombre`."""
    parts = credential.split("|")
    if len(parts) != 3:
        raise GoogleLoginError("token falso mal formado")
    sub, email, name = parts
    return GoogleIdentity(sub=sub, email=email, email_verified=True, name=name, picture=None)


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    """Crea la BD de pruebas si no existe y sus tablas desde los modelos."""
    admin = create_engine(settings.database_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        exists = connection.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": TEST_DATABASE_URL.database},
        ).first()
        if exists is None:
            connection.execute(text(f'CREATE DATABASE "{TEST_DATABASE_URL.database}"'))
    admin.dispose()

    test_engine = create_engine(TEST_DATABASE_URL)
    SQLModel.metadata.drop_all(test_engine)
    SQLModel.metadata.create_all(test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    """Sesión dentro de una transacción que se deshace al final del test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def make_client(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> Iterator[Callable[..., TestClient]]:
    """Fábrica de clientes. `make_client("ana")` devuelve uno con la sesión de Ana iniciada;
    sin argumento, uno anónimo. Cada cliente guarda sus propias cookies."""
    monkeypatch.setattr(settings, "google_client_id", "test-client-id")
    app.dependency_overrides[get_session] = lambda: db
    app.dependency_overrides[get_google_verifier] = lambda: fake_google_verifier

    def build(name: str | None = None) -> TestClient:
        client = TestClient(app)
        if name is not None:
            credential = f"sub-{name}|{name}@example.com|{name.capitalize()}"
            response = client.post("/api/auth/google", json={"credential": credential})
            assert response.status_code == 200, response.text
        return client

    yield build
    app.dependency_overrides.clear()
