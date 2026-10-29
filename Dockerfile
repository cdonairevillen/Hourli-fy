# Imagen única para Cloud Run: la API (FastAPI) sirve también la web de React ya compilada.
# Una sola URL: la cookie de sesión es del propio dominio y no hace falta proxy ni CORS.
# Se construye desde la raíz del repo: gcloud run deploy --source .

# --- 1. Web: compilar React con Vite ---
FROM node:22-slim AS web
WORKDIR /web
# El Client ID de Google no es secreto (va en el JavaScript que descarga el navegador).
ARG VITE_GOOGLE_CLIENT_ID=1009909897559-ov239hdhrcig71abd36qk4l759s1obno.apps.googleusercontent.com
ENV VITE_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- 2. API ---
FROM python:3.12-slim

# uv con versión fija: la misma que en local, para que el uv.lock se lea igual.
COPY --from=ghcr.io/astral-sh/uv:0.11.6 /uv /bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1

# Primero solo las dependencias: si no cambia el uv.lock, Docker reutiliza esta capa.
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev

COPY backend/alembic.ini ./
COPY backend/alembic ./alembic
COPY backend/app ./app
COPY --from=web /web/dist ./static
ENV PATH="/app/.venv/bin:$PATH" STATIC_DIR=/app/static

# Al arrancar aplica las migraciones pendientes (si no hay, no hace nada) y levanta la API.
# --proxy-headers: Cloud Run llega por HTTPS pero reenvía en HTTP; así la app sabe que es HTTPS
# (SQLAdmin monta sus links y redirecciones con https://).
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --proxy-headers --forwarded-allow-ips='*'"]
