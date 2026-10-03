# Registro de horas (proxy de Clockify)

Web de registro de horas (Hourli-fy). Cualquiera entra con Google y crea espacios aislados
(un estudio, un equipo) a los que invita por link. Los miembros registran tiempo (manual o
cronómetro) por proyecto, tipología y subtipología; el dueño del espacio ve totales quincenales
de todos con filtros. Es un registro: no hay aprobaciones, cierres ni exportaciones.

Especificación completa: ver el doc "Registro de horas — Especificación y plan".

## Stack

- **Frontend** (`frontend/`): React + TypeScript + Vite, TanStack Query, Tailwind + shadcn/ui.
- **Backend** (`backend/`): FastAPI + SQLModel + Alembic, Python 3.12.
- **Base de datos**: PostgreSQL en Supabase (en local, Postgres en Docker Compose).
- **Tiempo real**: Supabase Realtime sobre `time_entries` (fase extra).
- **Deploy**: backend en Google Cloud Run (Docker), frontend en Cloudflare Pages.

## Comandos

```bash
docker compose up -d db                             # Postgres local
cd backend && uv run fastapi dev app/main.py        # API en :8000
cd backend && uv run pytest                         # tests backend
cd backend && uv run python -m alembic upgrade head # aplicar migraciones (alembic.exe lo bloquea Windows)
cd frontend && npm run dev                          # front en :5173
cd frontend && npm run lint && npm run build        # comprobar front
```

## Modelo de datos

`users`, `workspaces`, `memberships`, `invitations`, `projects`, `categories`, `subcategories`, `time_entries`.
- Todo cuelga de un espacio (`workspace_id`) y toda consulta filtra por él tras comprobar la
  pertenencia (`MemberAccess` / `OwnerAccess` en `api/deps.py`; 404 si no eres miembro).
- Roles por espacio: el dueño es `workspaces.owner_id`; máx. 5 espacios propios sin archivar.
- Login con Google → JWT propio en cookie `httpOnly`. No hay contraseñas.
- `time_entries.end_at IS NULL` = cronómetro en marcha; índice único parcial: uno por usuario.
- La duración no se guarda: `end_at - start_at`.
- Fechas en UTC en BD; se muestran en Europe/Madrid.
- Nada con registros se borra: se archiva (`archived = true`).
- Quincenas: A = días 1–15, B = 16–fin de mes; cuenta el día de `start_at`.

## Convenciones

- Cambios mínimos y quirúrgicos: no tocar declaraciones, docstrings ni código ajeno a la tarea.
- No usar funciones con guion bajo (`_foo`); todas las funciones son normales y visibles.
- Atributos nuevos al final del `__init__`, con un comentario.
- Toda ruta nueva del backend lleva su test en pytest; ejecútalos antes de dar algo por terminado.
- Cambios de esquema siempre con una migración de Alembic, nunca a mano.
- Secretos solo en `.env` (nunca en el repo); mantener `.env.example` actualizado.
- Un commit por paso con mensaje claro en español.

## Forma de trabajar

- Una tarea del plan por sesión. Empieza en modo plan y espera aprobación antes de editar.
- Explica brevemente las decisiones no obvias: el objetivo también es que el autor aprenda.
