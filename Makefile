# Atajos de desarrollo. Uso: make <acción>
# Las recetas solo usan "cd x && comando" para funcionar igual con sh (Git Bash) que con cmd.

.PHONY: up down db-reset install dev dev-api dev-web

# Arranca Postgres local y espera a que esté sano.
up:
	docker compose up -d --wait db

# Para los contenedores (los datos se conservan en el volumen).
down:
	docker compose down

# BORRA la BD local (volumen incluido), la vuelve a crear y aplica las migraciones.
db-reset:
	docker compose down -v
	docker compose up -d --wait db
	cd backend && uv run python -m alembic upgrade head

# Instala dependencias de backend y frontend.
install:
	cd backend && uv sync
	cd frontend && npm install

# BD + API (:8000) + front (:5173) a la vez. Ctrl+C para todo.
dev: up
	"$(MAKE)" -j2 dev-api dev-web

dev-api:
	cd backend && uv run fastapi dev app/main.py

dev-web:
	cd frontend && npm run dev
