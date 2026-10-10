# Imagen de la API para Cloud Run. Cloud Build la construye desde esta carpeta (gcloud run deploy --source).
FROM python:3.12-slim

# uv con versión fija: la misma que en local, para que el uv.lock se lea igual.
COPY --from=ghcr.io/astral-sh/uv:0.11.6 /uv /bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1

# Primero solo las dependencias: si no cambia el uv.lock, Docker reutiliza esta capa.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
ENV PATH="/app/.venv/bin:$PATH"

# Al arrancar aplica las migraciones pendientes (si no hay, no hace nada) y levanta la API.
# --proxy-headers: Cloud Run llega por HTTPS pero reenvía en HTTP; así la app sabe que es HTTPS
# (SQLAdmin monta sus links y redirecciones con https://).
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --proxy-headers --forwarded-allow-ips='*'"]
