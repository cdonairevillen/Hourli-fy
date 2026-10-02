# Backend — Registro de horas

FastAPI + SQLModel + Alembic sobre PostgreSQL, Python 3.12 gestionado con [uv](https://docs.astral.sh/uv/).

```bash
cp .env.example .env                      # configuración local
uv run fastapi dev app/main.py            # API en http://localhost:8000 (Swagger en /docs)
uv run pytest                             # tests
uv run ruff check .                       # lint
uv run python -m alembic upgrade head     # aplicar migraciones (necesita el Postgres de docker compose)
uv run python scripts/export_openapi.py   # regenerar specs/api/openapi.yaml
```

> En este equipo Smart App Control de Windows bloquea `alembic.exe`; por eso se usa
> `python -m alembic`, que es equivalente y funciona en cualquier sitio.

## Estructura

```
app/
├── main.py          crea la app, CORS y monta los routers bajo /api
├── core/config.py   Settings (pydantic-settings): lee DATABASE_URL, SECRET_KEY, CORS_ORIGINS de .env
├── db.py            engine de SQLAlchemy + get_session() (dependencia por petición)
├── api/             un módulo por grupo de rutas (health.py, ...)
└── models/          tablas SQLModel; se importan en models/__init__.py para que Alembic las vea
alembic/             migraciones (env.py toma la URL y el metadata de la app)
scripts/             utilidades (export_openapi.py)
tests/               pytest, un archivo por grupo de rutas
```

## Endpoints

| Método | Ruta          | Uso                        | Rol     |
| ------ | ------------- | -------------------------- | ------- |
| GET    | `/api/health` | Comprueba que la API responde | Público |

El contrato completo está en [`specs/api/openapi.yaml`](../specs/api/openapi.yaml).

## Decisiones

- **pydantic-settings**: un único objeto `settings` tipado; los valores salen de `.env` (nunca del repo).
- **psycopg 3** como driver (`postgresql+psycopg://`): funciona igual con el Postgres local y con Supabase.
- **`pool_pre_ping`**: descarta conexiones cortadas por Supabase o Cloud Run antes de usarlas.
- **Alembic lee la URL de `settings`** y no de `alembic.ini`, para no duplicar credenciales.
  La plantilla de migraciones importa `sqlmodel` porque los modelos usan sus tipos (`AutoString`).
- **httpx2** en dev: Starlette marca `httpx` como obsoleto para `TestClient`.
