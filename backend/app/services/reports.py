"""Filtros del panel: de los parámetros de la URL a las condiciones del WHERE."""

import calendar
import re
import uuid
from dataclasses import dataclass
from datetime import date, timedelta

from fastapi import HTTPException, status
from sqlalchemy import ColumnElement

from app.models import TimeEntry
from app.models.common import utc_now
from app.services.entries import LOCAL_TZ, local_day_start

PERIOD_PATTERN = re.compile(r"^(\d{4})-(\d{2})-([AB])$")


def fortnight_range(year: int, month: int, half: str) -> tuple[date, date]:
    """Quincena A = días 1–15; B = del 16 al último día del mes."""
    if half == "A":
        return date(year, month, 1), date(year, month, 15)
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 16), date(year, month, last_day)


def current_fortnight() -> tuple[date, date]:
    today = utc_now().astimezone(LOCAL_TZ).date()
    return fortnight_range(today.year, today.month, "A" if today.day <= 15 else "B")


def resolve_period(
    period: str | None, from_date: date | None, to_date: date | None
) -> tuple[date, date]:
    """`period=2026-10-A` o `from`/`to`; sin nada, la quincena actual."""
    if period is not None:
        if from_date is not None or to_date is not None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, "Usa period o from/to, no los dos"
            )
        match = PERIOD_PATTERN.match(period)
        if match is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, "period debe ser AAAA-MM-A o AAAA-MM-B"
            )
        year, month, half = int(match[1]), int(match[2]), match[3]
        if not 1 <= month <= 12:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Mes no válido")
        return fortnight_range(year, month, half)
    if from_date is None and to_date is None:
        return current_fortnight()
    if from_date is None or to_date is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Indica from y to (o ninguno de los dos)"
        )
    if to_date < from_date:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "to es anterior a from")
    return from_date, to_date


@dataclass
class ReportFilters:
    """Filtros ya resueltos. Todos se combinan con AND."""

    from_date: date
    to_date: date
    user_id: uuid.UUID | None = None
    project_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    subcategory_id: uuid.UUID | None = None
    q: str | None = None

    def conditions(self, workspace_id: uuid.UUID) -> list[ColumnElement[bool]]:
        """El WHERE dinámico: solo se añade lo que llega.

        Solo cuentan registros terminados: el cronómetro en marcha aún no tiene duración.
        Un registro cuenta en el día en que empieza (regla de las quincenas).
        """
        where: list[ColumnElement[bool]] = [
            TimeEntry.workspace_id == workspace_id,
            TimeEntry.end_at.is_not(None),
            TimeEntry.start_at >= local_day_start(self.from_date),
            TimeEntry.start_at < local_day_start(self.to_date + timedelta(days=1)),
        ]
        if self.user_id is not None:
            where.append(TimeEntry.user_id == self.user_id)
        if self.project_id is not None:
            where.append(TimeEntry.project_id == self.project_id)
        if self.category_id is not None:
            where.append(TimeEntry.category_id == self.category_id)
        if self.subcategory_id is not None:
            where.append(TimeEntry.subcategory_id == self.subcategory_id)
        if self.q:
            # autoescape: un "%" o "_" escrito por el usuario se busca tal cual, no como comodín.
            where.append(TimeEntry.title.icontains(self.q, autoescape=True))
        return where
