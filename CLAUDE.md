# Registro de horas (proxy de Clockify)

Web de registro de horas (Hourli-fy). Cualquiera se registra con email y contraseña (o entra con
Google) y crea espacios aislados (un estudio, un equipo) a los que invita por link: al espacio
entero o a un solo proyecto. Los miembros registran tiempo (manual o
cronómetro) por proyecto, tipología y subtipología; el dueño del espacio ve totales quincenales
de todos con filtros. Es un registro: no hay aprobaciones, cierres ni exportaciones.

Especificación completa: ver el doc "Registro de horas — Especificación y plan".

## Stack

- **Frontend** (`frontend/`): React + TypeScript + Vite, TanStack Query, Tailwind + shadcn/ui.
- **Backend** (`backend/`): FastAPI + SQLModel + Alembic, Python 3.12.
- **Base de datos**: PostgreSQL en Supabase (en local, Postgres en Docker Compose).
- **Tiempo real**: Supabase Realtime sobre `time_entries` (fase extra).
- **Deploy**: un solo servicio de Google Cloud Run (`Dockerfile` de la raíz): la API sirve también
  la web compilada. Guía en `docs/DESPLIEGUE.md`.

## Comandos

```bash
docker compose up -d db                             # Postgres local
cd backend && uv run fastapi dev app/main.py        # API en :8000
cd backend && uv run python -m pytest               # tests backend (pytest.exe lo bloquea Windows)
cd backend && uv run python -m alembic upgrade head # aplicar migraciones (alembic.exe lo bloquea Windows)
cd frontend && npm run dev                          # front en :5173
cd frontend && npm run lint && npm run build        # comprobar front
```

## Modelo de datos

`users`, `workspaces`, `memberships`, `project_members`, `invitations`, `password_reset_tokens`,
`projects`, `categories`, `subcategories`, `time_entries`.
- Todo cuelga de un espacio (`workspace_id`) y toda consulta filtra por él tras comprobar la
  pertenencia (`MemberAccess` / `OwnerAccess` en `api/deps.py`; 404 si no eres miembro).
- Roles por espacio: el dueño es `workspaces.owner_id`; máx. 5 espacios propios sin archivar.
- Acceso por proyecto: `memberships.all_projects` (todos) o filas en `project_members`; las reglas
  están en `services/access.py` y un proyecto sin acceso da 404.
- Login con email + contraseña (argon2) o con Google → JWT propio en cookie `httpOnly`.
- Admins (`ADMIN_EMAILS` en `.env`): panel SQLAdmin en `/admin`.
- `time_entries.end_at IS NULL` = cronómetro en marcha; índice único parcial: uno por usuario.
- La duración no se guarda: `end_at - start_at`.
- Fechas en UTC en BD; se muestran en Europe/Madrid.
- Nada con registros se borra: se archiva (`archived = true`). Espacios y proyectos sin tareas
  sí se pueden borrar.
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
