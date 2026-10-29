from datetime import UTC, datetime

from sqlalchemy import DateTime


def utc_now() -> datetime:
    """Momento actual en UTC (las fechas se guardan siempre en UTC)."""
    return datetime.now(UTC)


# timestamptz en Postgres: guarda el instante exacto y lo devuelve con zona horaria.
TZDateTime = DateTime(timezone=True)
