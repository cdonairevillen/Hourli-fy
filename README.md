# not-clockify — Registro de horas

Web interna de registro de horas para un estudio pequeño, pensada para sustituir Clockify.
Cada trabajador registra su tiempo (manual o con cronómetro) por proyecto, tipología y subtipología;
el jefe ve los totales quincenales de todos con filtros.

- Especificación y plan por fases: doc "Registro de horas — Especificación y plan".
- [docs/development-workflow.md](docs/development-workflow.md) — ramas, carpetas y forma de trabajar.
- [docs/CHANGELOG.md](docs/CHANGELOG.md) — qué se ha añadido o cambiado en cada paso.
- [specs/](specs/README.md) — contrato de la API (`openapi.yaml`) y flujos de usuario.

## Estructura

```
not-clockify/
├── backend/    FastAPI + SQLModel + Alembic (Python 3.12, uv)
├── frontend/   React + TypeScript + Vite, Tailwind + shadcn/ui, TanStack Query
├── docs/       documentación compartida
├── specs/      contrato de la API y flujos de usuario
└── docker-compose.yml   Postgres local para desarrollo
```

## Arrancar en local

Requisitos: [uv](https://docs.astral.sh/uv/), Node.js LTS y Docker Desktop.

```bash
cp .env.example .env                      # credenciales del Postgres local
cp backend/.env.example backend/.env      # config del backend
docker compose up -d db                   # Postgres en :5432
cd backend && uv run python -m alembic upgrade head # aplicar migraciones
cd backend && uv run fastapi dev app/main.py   # API en http://localhost:8000 (docs en /docs)
cd frontend && npm install && npm run dev      # web en http://localhost:5173
```

Tests y comprobaciones:

```bash
cd backend && uv run pytest && uv run ruff check .
cd frontend && npm run lint && npm run build
```
