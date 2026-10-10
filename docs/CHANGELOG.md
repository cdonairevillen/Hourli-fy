# Changelog

Qué se añade o cambia en cada paso, y por qué. Lo más reciente arriba.
Formato: `## AAAA-MM-DD · rama · resumen`, con una sección por commit.

## 2026-10-10 · master · Preparar el despliegue y copias de seguridad

Guía paso a paso en [DESPLIEGUE.md](DESPLIEGUE.md), pensada para hacerlo solo y desde el navegador.

- `backend/Dockerfile` y `.dockerignore`: imagen para Cloud Run. Al arrancar aplica
  `alembic upgrade head`, así una BD vacía (Supabase nueva) se crea sola. Probada en local contra
  una BD vacía: crea las tablas, registra y el admin redirige con `https://`.
- `frontend/functions/api/[[path]].js`: Pages Function que reenvía `/api/*` a Cloud Run. La web y
  la API comparten dominio, así que la cookie es "propia" (Safari y los bloqueadores no la tiran)
  y no hace falta CORS ni `SameSite=None`.
- Enlace "Admin" con `VITE_ADMIN_URL`: en producción el panel se abre directamente en Cloud Run.
- `alembic/env.py`: el `%` de una contraseña ya no rompe la URL.
- `.github/workflows/backup-db.yml`: copia diaria de la BD (`pg_dump` cifrado con gpg, 30 días
  como artefacto). El plan gratuito de Supabase no da copias descargables. Copia y restauración
  probadas en local.
- "Salir" y "Eliminar cuenta" llevan al login (detalle en la fase 8).

## 2026-10-10 · master · Fase 8: acceso por proyecto y borrar espacios/proyectos

Detalle en [CHANGELOG-fase-8.md](CHANGELOG-fase-8.md). Va antes del despliegue.

## 2026-10-08 · master · Fase 7: cuentas con email y contraseña, y panel de admin

Detalle en [CHANGELOG-fase-7.md](CHANGELOG-fase-7.md). Va antes del despliegue.

## 2026-10-07 · master · Fase 6 (parte): gráficas del panel

Detalle en [CHANGELOG-fase-6.md](CHANGELOG-fase-6.md). Supabase Realtime queda para después del despliegue.

## 2026-10-07 · master · Fase 5 (parte de código): eliminar la cuenta y privacidad

Detalle en [CHANGELOG-fase-5.md](CHANGELOG-fase-5.md). El despliegue en sí se hará en pareja.

## 2026-10-07 · master · Fase 4: panel del dueño

Detalle completo, qué hay que saber y commits propuestos en [CHANGELOG-fase-4.md](CHANGELOG-fase-4.md).

## 2026-10-05 · master · Fase 3: registro de tareas, cronómetro y hoja de horas

Detalle completo, qué hay que saber y commits propuestos en [CHANGELOG-fase-3.md](CHANGELOG-fase-3.md).

## 2026-10-05 · master · Fase 2: catálogo (proyectos, labels y sublabels)

Detalle completo, qué hay que saber y commits propuestos en [CHANGELOG-fase-2.md](CHANGELOG-fase-2.md).

## 2026-10-02 · master · Fase 1: login con Google y espacios

Detalle completo, qué hay que saber y commits propuestos en [CHANGELOG-fase-1.md](CHANGELOG-fase-1.md).

## 2026-10-02 · master · Fase 0: todo arranca en local

### chore: cierre de la Fase 0 tras la prueba en local
- Probado: Postgres 16 en Docker sano, `alembic upgrade head`, `pytest`, `ruff`, API en `:8000` y front en `:5173` mostrando "API: ok" a través del proxy de Vite.
- `backend/alembic/versions/.gitkeep`: git no guarda carpetas vacías y sin ella `alembic revision` falla en un clon nuevo.
- `alembic/env.py` pasado por `ruff format` para que `ruff format --check` quede limpio.
- Los `.env` se crean en local desde los `.env.example` (no se suben al repo).

### docs: estructura del repositorio y convenciones
- `README.md` raíz, `CLAUDE.md`, `.gitignore` raíz.
- `docs/development-workflow.md`: flujo de `ft_trascendance` adaptado a un solo autor (`main` + `feature/*`, `fix/*`, `poc/*`, `hotfix/*`).
- `docs/CHANGELOG.md` (este archivo) y `specs/` (`api/` y `workflows/`), con la misma estructura que trascendance.

### backend: esqueleto FastAPI con config y endpoint de salud
- Proyecto uv con Python 3.12: FastAPI, SQLModel, Alembic, psycopg 3, pydantic-settings; dev: pytest, httpx2, ruff.
- `app/main.py` con CORS y router `/api`; `app/core/config.py` (Settings desde `.env`); `app/db.py` (engine + sesión).
- `GET /api/health` y su test (`tests/test_health.py`).
- `scripts/export_openapi.py` genera `specs/api/openapi.yaml` desde la app, para que el contrato no se desincronice.
- `backend/.env.example` con `DATABASE_URL`, `SECRET_KEY`, `CORS_ORIGINS`.

### backend: Alembic configurado sobre SQLModel
- `alembic/env.py` usa `SQLModel.metadata` y la URL de `settings`; `alembic.ini` ya no lleva credenciales.
- `app/models/` vacío: las tablas llegan en la Fase 1 con su migración.
- Se ejecuta con `uv run python -m alembic` porque Smart App Control bloquea `alembic.exe` en este equipo.

### infra: Postgres local con Docker Compose
- `docker-compose.yml`: servicio `db` (postgres:16, puerto 5432, volumen persistente, healthcheck).
- `.env.example` raíz con las credenciales del Postgres local.

### frontend: React + Vite + TS con Tailwind, shadcn/ui y TanStack Query
- Plantilla Vite 8 `react-ts`, Tailwind v4 (`@tailwindcss/vite`), shadcn/ui (`button`, `card`), TanStack Query.
- Proxy de Vite `/api` → `127.0.0.1:8000` y alias `@/` → `src/`.
- Página inicial que consulta `/api/health` y muestra el estado de la API.
- ESLint en lugar de oxlint: Smart App Control bloquea el binario nativo de oxlint.
