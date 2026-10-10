"""Panel del dueño: totales y registros de todo el espacio, con filtros.

Todo se resuelve en SQL (WHERE dinámico + GROUP BY): Postgres suma, Python solo da forma.
"""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlmodel import select

from app.api.deps import OwnerAccess, SessionDep
from app.models import Category, Project, TimeEntry, User
from app.schemas import (
    CategoryTotal,
    DayTotal,
    ProjectTotal,
    ReportEntriesPage,
    ReportEntry,
    ReportSummary,
    UserTotal,
)
from app.services.entries import LOCAL_TZ, entry_read
from app.services.reports import ReportFilters, resolve_period

router = APIRouter(prefix="/workspaces/{wid}/reports", tags=["reports"])

# Segundos de un registro (terminado), calculados en Postgres.
DURATION = func.extract("epoch", TimeEntry.end_at - TimeEntry.start_at)
TOTAL = func.coalesce(func.sum(DURATION), 0)


def get_report_filters(
    period: Annotated[str | None, Query(description="Quincena: AAAA-MM-A o AAAA-MM-B")] = None,
    from_date: Annotated[date | None, Query(alias="from")] = None,
    to_date: Annotated[date | None, Query(alias="to")] = None,
    user_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
    category_id: uuid.UUID | None = None,
    subcategory_id: uuid.UUID | None = None,
    q: Annotated[str | None, Query(max_length=200, description="Texto en el título")] = None,
) -> ReportFilters:
    """Los filtros de la URL, comunes a las dos rutas del panel."""
    start, end = resolve_period(period, from_date, to_date)
    return ReportFilters(
        from_date=start,
        to_date=end,
        user_id=user_id,
        project_id=project_id,
        category_id=category_id,
        subcategory_id=subcategory_id,
        q=q.strip() if q else None,
    )


Filters = Annotated[ReportFilters, Depends(get_report_filters)]


@router.get("/summary")
def report_summary(session: SessionDep, access: OwnerAccess, filters: Filters) -> ReportSummary:
    """Total del grupo filtrado y desgloses por trabajador, proyecto, label y día."""
    where = filters.conditions(access.workspace.id)

    count, total = session.exec(select(func.count(), TOTAL).where(*where)).one()

    by_user = session.exec(
        select(User.id, User.name, TOTAL)
        .join(User, User.id == TimeEntry.user_id)
        .where(*where)
        .group_by(User.id, User.name)
        .order_by(TOTAL.desc(), User.name)
    ).all()
    by_project = session.exec(
        select(Project.id, Project.name, Project.color, TOTAL)
        .join(Project, Project.id == TimeEntry.project_id)
        .where(*where)
        .group_by(Project.id, Project.name, Project.color)
        .order_by(TOTAL.desc(), Project.name)
    ).all()
    by_category = session.exec(
        select(Category.id, Category.name, TOTAL)
        .join(Category, Category.id == TimeEntry.category_id)
        .where(*where)
        .group_by(Category.id, Category.name)
        .order_by(TOTAL.desc(), Category.name)
    ).all()
    # Día en hora de España: timezone() convierte el instante UTC a la hora local.
    local_day = func.date(func.timezone(str(LOCAL_TZ), TimeEntry.start_at))
    by_day = session.exec(
        select(local_day, TOTAL).where(*where).group_by(local_day).order_by(local_day)
    ).all()

    return ReportSummary(
        from_date=filters.from_date,
        to_date=filters.to_date,
        total_seconds=int(total),
        entry_count=count,
        by_user=[UserTotal(user_id=i, name=n, total_seconds=int(t)) for i, n, t in by_user],
        by_project=[
            ProjectTotal(project_id=i, name=n, color=c, total_seconds=int(t))
            for i, n, c, t in by_project
        ],
        by_category=[
            CategoryTotal(category_id=i, name=n, total_seconds=int(t)) for i, n, t in by_category
        ],
        by_day=[DayTotal(day=d, total_seconds=int(t)) for d, t in by_day],
    )


@router.get("/entries")
def report_entries(
    session: SessionDep,
    access: OwnerAccess,
    filters: Filters,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ReportEntriesPage:
    """Registros que cumplen los filtros, los más recientes primero, paginados."""
    where = filters.conditions(access.workspace.id)
    total = session.exec(select(func.count()).select_from(TimeEntry).where(*where)).one()
    rows = session.exec(
        select(TimeEntry, User.name)
        .join(User, User.id == TimeEntry.user_id)
        .where(*where)
        # Desempate estable (mismo inicio): por nombre y luego id, para que paginar no repita.
        .order_by(TimeEntry.start_at.desc(), User.name, TimeEntry.id)
        .offset(offset)
        .limit(limit)
    ).all()
    items = [
        ReportEntry(**entry_read(entry).model_dump(), user_id=entry.user_id, user_name=name)
        for entry, name in rows
    ]
    return ReportEntriesPage(total=total, items=items)
