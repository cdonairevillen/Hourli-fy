from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.admin import setup_admin
from app.api import auth, catalog, entries, health, invitations, reports, workspaces
from app.core.config import settings
from app.frontend import setup_frontend

app = FastAPI(title="Registro de horas", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Todas las rutas cuelgan de /api (así el proxy de Vite y el despliegue usan un único prefijo).
api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(workspaces.router)
api_router.include_router(invitations.router)
api_router.include_router(catalog.router)
api_router.include_router(entries.router)
api_router.include_router(reports.router)

app.include_router(api_router)

# Panel de administración en /admin (solo emails de ADMIN_EMAILS). Ver app/admin.py.
setup_admin(app)

# En producción la web de React se sirve desde aquí (STATIC_DIR, ver Dockerfile). En local no:
# la sirve Vite en :5173. Va la última para no tapar /api ni /admin.
if settings.static_dir:
    setup_frontend(app, Path(settings.static_dir))
